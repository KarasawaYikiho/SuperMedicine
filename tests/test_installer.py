from __future__ import annotations

import importlib
import json
import logging
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml
from tests.conftest import _cp1252_stdio_env, _has_exact_child_name, _supports_case_distinct_names
from uninstall_entry import collect_removal_candidates, uninstall


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_SUBPROCESS_TIMEOUT_SECONDS = 30


# ── Shared helper functions ──────────────────────────────────────────────────


def _git_tracks_exact_path(path: str) -> bool:
    """Return whether git index tracks an exact path spelling.

    Windows worktrees often cannot materialize both ``install_entry.py`` case
    variants at once, but the git index can still contain both entries for
    case-sensitive checkout targets.  This keeps the diagnostic meaningful in a
    case-insensitive local checkout while still requiring exact entrypoint support
    in the repository representation.
    """

    result = subprocess.run(
        ["git", "ls-files", "--", path],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return path in result.stdout.splitlines()


def _read_exact_lowercase_install_source() -> str:
    """Read the installer entrypoint source without Windows case-folding ambiguity."""

    if _has_exact_child_name(REPO_ROOT, "install_entry.py"):
        return (REPO_ROOT / "install_entry.py").read_text(encoding="utf-8")
    result = subprocess.run(
        ["git", "show", ":install_entry.py"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _write_minimal_import_stubs(workspace: Path) -> None:
    """Provide non-installer imports so tests isolate optional installer import behavior."""

    core_llm_dir = workspace / "core" / "llm_providers"
    core_llm_dir.mkdir(parents=True)
    (workspace / "core" / "__init__.py").write_text("", encoding="utf-8")
    (core_llm_dir / "__init__.py").write_text("", encoding="utf-8")
    (core_llm_dir / "config.py").write_text(
        textwrap.dedent(
            """
            class LLMProviderConfig:
                def __init__(self, base_url='https://example.test/v1'):
                    self.base_url = base_url

                @classmethod
                def from_mapping(cls, provider, mapping):
                    return cls(mapping.get('base_url', 'https://example.test/v1'))

                def missing_fields(self):
                    return []
            """
        ),
        encoding="utf-8",
    )
    (workspace / "core" / "redaction.py").write_text(
        "def redact_sensitive(value):\n    return value\n",
        encoding="utf-8",
    )
    (workspace / "core" / "serialization.py").write_text(
        "def json_ready(value):\n    return value\n",
        encoding="utf-8",
    )

    permission_dir = workspace / "permission"
    permission_dir.mkdir()
    (permission_dir / "__init__.py").write_text("", encoding="utf-8")
    (permission_dir / "policy.py").write_text(
        "def ensure_default_policy(project_dir, repo_root):\n    return None\n",
        encoding="utf-8",
    )


def _copy_install_entrypoint_without_installer_package(workspace: Path) -> Path:
    install_path = workspace / "install_entry.py"
    install_path.write_text(
        (REPO_ROOT / "install_entry.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    _write_minimal_import_stubs(workspace)
    assert not (workspace / "installer").exists()
    return install_path


def _copy_cli_entrypoint_without_installer_package(workspace: Path) -> Path:
    cli_path = workspace / "cli_entry.py"
    cli_path.write_text(
        (REPO_ROOT / "cli_entry.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (workspace / "install_entry.py").write_text(
        (REPO_ROOT / "install_entry.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    shutil.copytree(REPO_ROOT / "cli", workspace / "cli")
    _write_minimal_import_stubs(workspace)
    assert not (workspace / "installer").exists()
    return cli_path


def _run_isolated_install(
    workspace: Path, *args: str, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "install_entry.py", *args],
        cwd=workspace,
        env=_cp1252_stdio_env(),
        text=True,
        encoding="cp1252",
        input=input_text,
        capture_output=True,
        check=False,
        timeout=INSTALLER_SUBPROCESS_TIMEOUT_SECONDS,
    )


def _run_isolated_lowercase_install(
    workspace: Path,
    *args: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "install_entry.py", *args],
        cwd=workspace,
        env=_cp1252_stdio_env(),
        text=True,
        encoding="cp1252",
        input=input_text,
        capture_output=True,
        check=False,
        timeout=INSTALLER_SUBPROCESS_TIMEOUT_SECONDS,
    )


def _run_isolated_cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "cli_entry.py", *args],
        cwd=workspace,
        env=_cp1252_stdio_env(),
        text=True,
        encoding="cp1252",
        capture_output=True,
        check=False,
        timeout=INSTALLER_SUBPROCESS_TIMEOUT_SECONDS,
    )


def _llm_args() -> list[str]:
    return [
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-installer-exe-release",
        "--model",
        "gpt-test",
    ]


def _make_release_payload(root: Path) -> Path:
    payload = root / "release_payload"
    (payload / "core").mkdir(parents=True)
    (payload / "permission").mkdir()
    (payload / "installer").mkdir()
    (payload / "dist").mkdir()
    shutil.copy2(REPO_ROOT / "install_entry.py", payload / "install_entry.py")
    (payload / "core" / "__init__.py").write_text("", encoding="utf-8")
    (payload / "permission" / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(
        REPO_ROOT / "installer" / "__init__.py", payload / "installer" / "__init__.py"
    )
    shutil.copy2(
        REPO_ROOT / "installer" / "entrypoint.py",
        payload / "installer" / "entrypoint.py",
    )
    shutil.copy2(
        REPO_ROOT / "installer" / "exe_release.py",
        payload / "installer" / "exe_release.py",
    )
    (payload / "dist" / "SuperMedicine.exe").write_bytes(b"app exe")
    (payload / "SuperMedicineGUI.exe").write_bytes(b"gui exe")
    (payload / "README.md").write_text("docs\n", encoding="utf-8")
    return payload


# ═══ Installer Entrypoint Tests ═══════════════════════════════════════════════


def test_lowercase_install_py_entrypoint_is_present_for_case_sensitive_platforms():
    """User-facing ``python install_entry.py`` needs exact support.

    This test is intentionally based on directory-entry spelling rather than
    Path.exists() so it remains diagnostic on Windows case-insensitive filesystems.
    """

    assert _has_exact_child_name(REPO_ROOT, "install_entry.py") or _git_tracks_exact_path(
        "install_entry.py"
    ), (
        "Missing installer entrypoint 'install_entry.py'. "
        "Platforms cannot run the user command `python install_entry.py` "
        "until the entry file is present."
    )


def test_lowercase_install_help_works_when_optional_installer_package_is_absent(
    tmp_path,
):
    """Regression: exact ``python install_entry.py`` delegates to the installer on case-sensitive platforms."""

    if not _supports_case_distinct_names(tmp_path):
        pytest.skip(
            "filesystem cannot materialize both install_entry.py exact spelling"
        )

    _copy_install_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_lowercase_install(tmp_path, "--help")

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "--release-exe" in output
    assert "usage:" in output.lower()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output
    assert "UnicodeEncodeError" not in output


def test_install_help_works_when_optional_installer_package_is_absent(tmp_path):
    """Regression: isolated --help must survive strict Windows cp1252 stdio."""

    _copy_install_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_install(tmp_path, "--help")

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "--release-exe" in output
    assert "usage:" in output.lower()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output
    assert "UnicodeEncodeError" not in output


def test_init_entry_path_does_not_require_optional_exe_release_module(tmp_path):
    """Core install/init should remain usable even without optional Exe release code."""

    _copy_install_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_install(
        tmp_path,
        "--init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-installer-entrypoint",
        "--model",
        "gpt-test",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output


def test_release_exe_dry_run_works_with_install_entry(tmp_path):
    """Explicit --release-exe --exe-dry-run should produce a dry-run summary."""

    _copy_install_entrypoint_without_installer_package(tmp_path)
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")

    result = _run_isolated_install(
        tmp_path, "--release-exe", str(source), "--exe-dry-run"
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "dry-run" in output.lower() or "dry_run" in output.lower() or "release" in output.lower()
    assert "ModuleNotFoundError" not in output
    assert "Traceback" not in output


def test_cli_help_works_when_optional_installer_package_is_absent(tmp_path):
    """Regression: isolated CLI help must survive strict Windows cp1252 stdio."""

    _copy_cli_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_cli(tmp_path, "init", "--help")

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "--release-exe" in output
    assert "usage:" in output.lower()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output
    assert "UnicodeEncodeError" not in output


def test_cli_init_without_release_exe_does_not_require_optional_installer_package(
    tmp_path,
):
    """Core CLI init should remain usable without optional Exe release code."""

    _copy_cli_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_cli(
        tmp_path,
        "init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-cli-entrypoint",
        "--model",
        "gpt-test",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output


def test_cli_release_exe_missing_optional_module_reports_actionable_error(tmp_path):
    """Explicit CLI --release-exe should produce a user-facing missing-package error."""

    _copy_cli_entrypoint_without_installer_package(tmp_path)
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")

    result = _run_isolated_cli(
        tmp_path,
        "init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-cli-release-exe",
        "--model",
        "gpt-test",
        "--release-exe",
        str(source),
        "--exe-dry-run",
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "--release-exe" in output or "installer" in output.lower()
    assert "cli_entry.py" in output or "release package" in output
    assert "ModuleNotFoundError" not in output
    assert "Traceback" not in output


def test_install_defaults_to_interactive_question_answer_when_args_are_absent(
    tmp_path, monkeypatch
):
    """Regression baseline: bare installer should be usable as an interactive flow."""

    from installer import entrypoint as Install

    prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        prompt_text = prompt.lower()
        if "provider" in prompt_text:
            return "openai"
        if "base" in prompt_text:
            return "https://openai.local.test/v1"
        if "model" in prompt_text:
            return "gpt-test"
        if "api key" in prompt_text:
            return "sk-test-interactive-installer"
        if "重试安装向导" in prompt:
            raise AssertionError(f"installer unexpectedly requested retry: {prompts!r}")
        if any(
            expected in prompt
            for expected in (
                "安装/项目路径",
                "释放完整程序文件到该目录",
                "组件选择",
                "初始化 .supermedicine 配置",
                "记录创建快捷方式意向",
                "显示 PATH 手动配置提示",
                "复制 SuperMedicine.exe 到桌面",
                "开始安装",
            )
        ):
            return ""
        raise AssertionError(f"unexpected installer prompt: {prompt!r}")

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return "sk-test-interactive-installer"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(Install.getpass, "getpass", fake_getpass)

    Install.main([])

    config_file = tmp_path / ".supermedicine" / "config.yaml"
    assert config_file.exists()
    assert "sk-test-interactive-installer" in config_file.read_text(encoding="utf-8")
    assert any("provider" in prompt.lower() for prompt in prompts)
    assert any("base" in prompt.lower() for prompt in prompts)
    assert any("api key" in prompt.lower() for prompt in prompts)


def test_python_install_py_bare_interactive_flow_creates_config_without_optional_installer_package(
    tmp_path,
):
    """Regression: the exact user command `python install_entry.py` must work as a wizard."""

    _copy_install_entrypoint_without_installer_package(tmp_path)
    input_text = (
        "\n".join(
            [
                "",  # installation/project path: current directory
                "",  # full payload extraction: default no
                "",  # initialize .supermedicine: default yes
                "openai",
                "https://openai.local.test/v1",
                "gpt-test",
                "sk-test-python-install-interactive",
                "",  # shortcut preference: default no
                "",  # PATH preference: default no
                "",  # desktop Exe release: default no
                "",  # confirmation summary: default yes
            ]
        )
        + "\n"
    )

    result = _run_isolated_install(tmp_path, input_text=input_text)

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert "SuperMedicine" in output
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output
    assert "UnicodeEncodeError" not in output


# ═══ Installer Exe Release Tests ═════════════════════════════════════════════


def test_exe_desktop_release_uses_supplied_desktop_directory_and_dry_run(
    tmp_path, caplog
):
    """Regression skeleton for future unified installer / Exe desktop release.

    The contract is intentionally test-friendly: callers must be able to inject a
    temporary desktop directory and dry-run the release without touching the real
    user desktop or requiring an interactive terminal.
    """

    module = importlib.import_module("installer.exe_release")

    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    build_dir = tmp_path / "dist"
    build_dir.mkdir()
    exe_path = build_dir / "SuperMedicine.exe"
    exe_path.write_bytes(b"fake exe bytes")
    caplog.set_level(logging.INFO, logger="installer.exe_release")

    result = module.release_exe_to_desktop(
        exe_path=exe_path,
        desktop_dir=desktop_dir,
        dry_run=True,
    )

    assert not (desktop_dir / "SuperMedicine.exe").exists()
    assert result["dry_run"] is True
    assert result["desktop_dir"] == desktop_dir
    assert result["target_path"] == desktop_dir / "SuperMedicine.exe"
    assert result["status"] == "dry-run"
    assert "Exe release dry-run" in caplog.text
    assert str(desktop_dir / "SuperMedicine.exe") in caplog.text


def test_exe_desktop_release_copies_to_supplied_desktop_directory(tmp_path, caplog):
    module = importlib.import_module("installer.exe_release")
    caplog.set_level(logging.INFO, logger="installer.exe_release")
    desktop_dir = tmp_path / "Desktop"
    source = tmp_path / "dist" / "SuperMedicine.exe"
    source.parent.mkdir()
    source.write_bytes(b"fake exe bytes")

    result = module.release_exe_to_desktop(exe_path=source, desktop_dir=desktop_dir)

    target = desktop_dir / "SuperMedicine.exe"
    assert result["status"] == "copied"
    assert result["reason"] == "created"
    assert result["target_path"] == target
    assert target.read_bytes() == b"fake exe bytes"
    assert "Exe release completed" in caplog.text
    assert str(target) in caplog.text


def test_exe_desktop_release_missing_source_has_deterministic_error(tmp_path):
    module = importlib.import_module("installer.exe_release")

    with pytest.raises(FileNotFoundError, match="Exe source does not exist"):
        module.release_exe_to_desktop(
            exe_path=tmp_path / "dist" / "Missing.exe",
            desktop_dir=tmp_path / "Desktop",
        )


def test_exe_desktop_release_skips_existing_target_by_default(tmp_path, caplog):
    module = importlib.import_module("installer.exe_release")
    caplog.set_level(logging.INFO, logger="installer.exe_release")
    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"new bytes")
    target = desktop_dir / "SuperMedicine.exe"
    target.write_bytes(b"existing bytes")

    result = module.release_exe_to_desktop(exe_path=source, desktop_dir=desktop_dir)

    assert result["status"] == "skipped"
    assert result["reason"] == "target-exists"
    assert target.read_bytes() == b"existing bytes"
    assert "Exe release skipped" in caplog.text
    assert str(target) in caplog.text


def test_exe_desktop_release_overwrites_existing_target_when_requested(
    tmp_path, caplog
):
    module = importlib.import_module("installer.exe_release")
    caplog.set_level(logging.INFO, logger="installer.exe_release")
    desktop_dir = tmp_path / "Desktop"
    desktop_dir.mkdir()
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"new bytes")
    target = desktop_dir / "SuperMedicine.exe"
    target.write_bytes(b"existing bytes")

    result = module.release_exe_to_desktop(
        exe_path=source, desktop_dir=desktop_dir, overwrite=True
    )

    assert result["status"] == "copied"
    assert result["reason"] == "overwritten"
    assert target.read_bytes() == b"new bytes"
    assert "Exe release completed" in caplog.text
    assert str(target) in caplog.text


def test_exe_desktop_release_logs_copy_errors(tmp_path, caplog, monkeypatch):
    module = importlib.import_module("installer.exe_release")
    caplog.set_level(logging.ERROR, logger="installer.exe_release")
    desktop_dir = tmp_path / "Desktop"
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")

    def fail_copy2(source_path, target_path):
        raise OSError("copy failed for test")

    monkeypatch.setattr(module.shutil, "copy2", fail_copy2)

    with pytest.raises(OSError, match="copy failed for test"):
        module.release_exe_to_desktop(exe_path=source, desktop_dir=desktop_dir)

    assert "Exe release failed" in caplog.text
    assert "copy failed for test" in caplog.text
    assert str(desktop_dir / "SuperMedicine.exe") in caplog.text


@pytest.mark.parametrize(
    "bad_name",
    ["../SuperMedicine.exe", "subdir/SuperMedicine.exe", "bad:name.exe", "CON.exe"],
)
def test_exe_desktop_release_rejects_unsafe_target_filename(tmp_path, bad_name):
    module = importlib.import_module("installer.exe_release")
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")

    with pytest.raises(module.ExeReleaseError):
        module.release_exe_to_desktop(
            exe_path=source,
            desktop_dir=tmp_path / "Desktop",
            target_filename=bad_name,
        )


def test_exe_desktop_release_normalizes_target_filename_suffix(tmp_path):
    module = importlib.import_module("installer.exe_release")
    source = tmp_path / "BuildName.exe"
    source.write_bytes(b"fake exe bytes")

    result = module.release_exe_to_desktop(
        exe_path=source,
        desktop_dir=tmp_path / "Desktop",
        target_filename="SuperMedicine",
        dry_run=True,
    )

    assert result["target_filename"] == "SuperMedicine.exe"
    assert result["target_path"] == tmp_path / "Desktop" / "SuperMedicine.exe"


def test_release_payload_to_directory_copies_unified_layout(tmp_path, caplog):
    module = importlib.import_module("installer.exe_release")
    caplog.set_level(logging.INFO, logger="installer.exe_release")
    payload = _make_release_payload(tmp_path)
    target_dir = tmp_path / "Installed"

    result = module.release_payload_to_directory(
        source_root=payload, target_dir=target_dir
    )

    assert result["status"] == "copied"
    assert result["reason"] == "created"
    assert (target_dir / "install_entry.py").exists()
    assert (target_dir / "install_entry.py").read_text(encoding="utf-8") == (
        payload / "install_entry.py"
    ).read_text(encoding="utf-8")
    assert (target_dir / "installer" / "__init__.py").exists()
    assert (target_dir / "installer" / "entrypoint.py").exists()
    assert (target_dir / "installer" / "exe_release.py").exists()
    assert (target_dir / "dist" / "SuperMedicine.exe").read_bytes() == b"app exe"
    assert "Release payload extraction completed" in caplog.text


def test_release_payload_to_directory_dry_run_does_not_create_target(tmp_path):
    module = importlib.import_module("installer.exe_release")
    payload = _make_release_payload(tmp_path)

    result = module.release_payload_to_directory(
        source_root=payload,
        target_dir=tmp_path / "Installed",
        dry_run=True,
    )

    assert result["status"] == "dry-run"
    assert result["file_count"] >= 5
    assert not (tmp_path / "Installed").exists()


def test_release_gui_exe_dry_run_uses_gui_desktop_target(tmp_path, caplog):
    from installer.entrypoint import main

    gui_exe = tmp_path / "SuperMedicineGUI.exe"
    gui_exe.write_bytes(b"gui exe")
    desktop = tmp_path / "Desktop"
    caplog.set_level(logging.INFO)

    main(
        [
            "--release-gui-exe",
            str(gui_exe),
            "--desktop-dir",
            str(desktop),
            "--exe-dry-run",
            "--if-installed",
            "ignore",
        ]
    )

    assert not desktop.exists()
    assert "SuperMedicineGUI.exe" in caplog.text


def test_missing_gui_exe_never_falls_back_to_cli_exe(tmp_path, monkeypatch):
    from installer import exe_release

    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "SuperMedicine.exe").write_bytes(b"cli exe")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(exe_release, "_release_root", lambda: tmp_path)

    with pytest.raises(FileNotFoundError):
        exe_release.resolve_exe_path(Path("dist") / "SuperMedicineGUI.exe")


def test_release_payload_to_directory_rejects_incomplete_layout(tmp_path):
    module = importlib.import_module("installer.exe_release")
    payload = tmp_path / "release_payload"
    payload.mkdir()

    with pytest.raises(FileNotFoundError, match="Release payload is incomplete"):
        module.release_payload_to_directory(
            source_root=payload, target_dir=tmp_path / "Installed"
        )


def test_install_help_documents_unified_install_and_desktop_release(capsys):
    install = importlib.import_module("installer.entrypoint")

    with pytest.raises(SystemExit) as excinfo:
        install.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "--unified-install" in output
    assert "--release-exe" in output
    assert "--desktop-dir" in output
    assert "--exe-dry-run" in output
    assert "--extract-release-to" in output
    assert "统一安装" in output


def test_existing_install_detection_priority_uses_record_before_config_payload_and_desktop(
    tmp_path,
):
    install = importlib.import_module("installer.entrypoint")
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / ".supermedicine" / "install-record.json").write_text(
        "{}", encoding="utf-8"
    )
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        "project_name: supermedicine\n", encoding="utf-8"
    )
    (tmp_path / "cli_entry.py").write_text("print('payload')\n", encoding="utf-8")
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    (desktop / "SuperMedicine.exe").write_bytes(b"old exe")

    result = install.detect_existing_install(tmp_path, desktop_dir=desktop)

    assert result.installed is True
    assert result.reason == "install-record"
    assert [item.kind for item in result.evidence] == [
        "install-record",
        "config",
        "payload-collision",
        "desktop-exe-collision",
    ]


def test_scripted_existing_install_without_policy_fails_without_prompt(
    tmp_path, monkeypatch
):
    install = importlib.import_module("installer.entrypoint")
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir()
    config.write_text("project_name: supermedicine\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    def fail_input(prompt):
        raise AssertionError(f"scripted mode prompted unexpectedly: {prompt}")

    monkeypatch.setattr("builtins.input", fail_input)

    with pytest.raises(SystemExit) as excinfo:
        install.main(["--init", *_llm_args()])

    assert "--if-installed" in str(excinfo.value)


def test_scripted_uninstall_policy_requires_explicit_user_data_choice(
    tmp_path, monkeypatch
):
    install = importlib.import_module("installer.entrypoint")
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir()
    config.write_text("project_name: supermedicine\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as excinfo:
        install.main(["--init", "--if-installed", "uninstall", *_llm_args()])

    assert "--preserve-user-data" in str(excinfo.value)
    assert config.exists()


def test_update_policy_preserves_existing_config_secret_and_writes_secret_free_record(
    tmp_path, monkeypatch
):
    install = importlib.import_module("installer.entrypoint")
    secret = "sk-existing-secret-to-preserve"
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir()
    config.write_text(
        "project_name: supermedicine\nllm:\n  provider: openai\n  providers:\n    openai:\n      api_key: "
        + secret
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    install.main(["--init", "--if-installed", "update", *_llm_args()])

    config_text = config.read_text(encoding="utf-8")
    record_text = (tmp_path / ".supermedicine" / "install-record.json").read_text(
        encoding="utf-8"
    )
    assert secret in config_text
    assert secret not in record_text
    record = json.loads(record_text)
    assert record["name"] == "supermedicine"
    assert record["mode"] == "update"


def test_interactive_existing_install_update_branch_prompts_two_main_choices(
    tmp_path, monkeypatch
):
    install = importlib.import_module("installer.entrypoint")
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir()
    config.write_text("project_name: supermedicine\n", encoding="utf-8")
    prompts: list[str] = []
    answers = iter([str(tmp_path), "2", "n", "", "n", "n", "n", "n", ""])

    def fake_input(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", fake_input)

    install.main([])

    assert any("已有安装处理" in prompt for prompt in prompts)
    assert config.exists()


def test_interactive_uninstall_branch_asks_second_user_data_confirmation(
    tmp_path, monkeypatch
):
    install = importlib.import_module("installer.entrypoint")
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir()
    config.write_text("project_name: supermedicine\n", encoding="utf-8")
    prompts: list[str] = []
    answers = iter([str(tmp_path), "1", "1", "n", "", "n", "n", "n", "n", ""])

    def fake_input(prompt):
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(
        install,
        "_uninstall_existing_install",
        lambda project_dir, *, preserve_user_data: {
            "status": "removed",
            "preserve": preserve_user_data,
        },
    )

    install.main([])

    assert any("已有安装处理" in prompt for prompt in prompts)
    assert any("用户数据处理" in prompt for prompt in prompts)


def test_unified_install_dry_run_initializes_project_without_real_desktop_write(
    tmp_path, monkeypatch, caplog
):
    install = importlib.import_module("installer.entrypoint")
    source = tmp_path / "dist" / "SuperMedicine.exe"
    source.parent.mkdir()
    source.write_bytes(b"fake exe bytes")
    desktop_dir = tmp_path / "fake-desktop"
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(install.Path, "home", lambda: real_home)
    caplog.set_level(logging.INFO)

    install.main(
        [
            "--unified-install",
            "--release-exe",
            str(source),
            "--desktop-dir",
            str(desktop_dir),
            "--exe-dry-run",
            *_llm_args(),
        ]
    )

    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert not (desktop_dir / "SuperMedicine.exe").exists()
    assert not (real_home / "Desktop" / "SuperMedicine.exe").exists()
    assert "安装初始化结果" in caplog.text
    assert "桌面 Exe 释放 dry-run" in caplog.text
    assert str(desktop_dir / "SuperMedicine.exe") in caplog.text


def test_init_with_release_exe_copies_to_injected_desktop_directory(
    tmp_path, monkeypatch, caplog
):
    install = importlib.import_module("installer.entrypoint")
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")
    desktop_dir = tmp_path / "Desktop"
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO)

    install.main(
        [
            "--init",
            "--release-exe",
            str(source),
            "--desktop-dir",
            str(desktop_dir),
            *_llm_args(),
        ]
    )

    target = desktop_dir / "SuperMedicine.exe"
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert target.read_bytes() == b"fake exe bytes"
    assert "桌面 Exe 释放完成" in caplog.text
    assert str(target) in caplog.text


def test_unified_install_requires_release_exe(capsys):
    install = importlib.import_module("installer.entrypoint")

    with pytest.raises(SystemExit) as excinfo:
        install.main(["--unified-install", *_llm_args()])

    assert excinfo.value.code == 2
    assert "--unified-install requires --release-exe" in capsys.readouterr().err


def test_install_manifest_documents_exe_as_external_release_artifact():
    manifest = json.loads((REPO_ROOT / "install.json").read_text(encoding="utf-8"))
    resource_policy = manifest["packaging_resources"]

    assert resource_policy["installer_package"] == "installer"
    assert "installer/resources/*.json" in resource_policy["non_code_resource_globs"]
    assert "Real SuperMedicine.exe binaries" in resource_policy["exe_resource_strategy"]
    assert "not committed" in resource_policy["exe_resource_strategy"]
    assert "must not use a .exe suffix" in resource_policy["exe_resource_strategy"]
    assert "*.exe" in resource_policy["generated_artifacts_excluded"]


# ═══ Uninstall Tests ══════════════════════════════════════════════════════════


def test_dry_run_does_not_delete_project_owned_files(tmp_path):
    owned = tmp_path / ".supermedicine"
    owned.mkdir()
    (owned / "config.yaml").write_text(
        "project_name: supermedicine\n", encoding="utf-8"
    )

    result = uninstall(tmp_path, dry_run=True, force=True)

    assert result["status"] == "dry-run"
    assert (owned / "config.yaml").exists()
    assert any(item["path"] == ".supermedicine" for item in result["planned"])


def test_force_removes_owned_runtime_artifacts_but_not_unrecorded_platform_dirs(
    tmp_path,
):
    paths = [
        tmp_path / ".supermedicine" / "config.yaml",
        tmp_path / ".supermedicine" / "policies" / "audit.jsonl",
        tmp_path / ".supermedicine" / "checkpoints" / "task" / "status.json",
        tmp_path / ".opencode" / "plugin.json",
        tmp_path / ".claude" / "skills" / "supermedicine" / "SKILL.md",
        tmp_path / "superpowers" / "supermedicine.md",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert not (tmp_path / ".supermedicine").exists()
    assert (tmp_path / ".opencode" / "plugin.json").exists()
    assert (tmp_path / ".claude" / "skills" / "supermedicine" / "SKILL.md").exists()
    assert (tmp_path / "superpowers" / "supermedicine.md").exists()


def test_uninstall_does_not_remove_user_owned_files_or_repo_root(tmp_path):
    user_file = tmp_path / "user-notes.md"
    source_file = tmp_path / "cli_entry.py"
    user_file.write_text("keep", encoding="utf-8")
    source_file.write_text("keep", encoding="utf-8")
    (tmp_path / ".supermedicine").mkdir()

    result = uninstall(tmp_path, force=True)

    assert user_file.exists()
    assert source_file.exists()
    assert tmp_path.exists()
    assert "." not in result["removed"]


def test_recorded_and_explicit_targets_are_removed_only_inside_project(tmp_path):
    inside_recorded = tmp_path / "platform-targets" / "opencode" / "supermedicine.json"
    inside_explicit = tmp_path / "platform-targets" / "claude" / "SKILL.md"
    outside = tmp_path.parent / "outside-supermedicine-target.txt"
    for path in (inside_recorded, inside_explicit, outside):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text(
        '{"platform_target_paths":["platform-targets/opencode/supermedicine.json","../outside-supermedicine-target.txt"]}',
        encoding="utf-8",
    )

    result = uninstall(
        tmp_path, force=True, explicit_targets=["platform-targets/claude/SKILL.md"]
    )

    assert not inside_recorded.exists()
    assert not inside_explicit.exists()
    assert outside.exists()
    assert any(str(outside) in item for item in result["skipped"])
    outside.unlink()


def test_nested_platform_install_records_are_removed_but_unrecorded_home_like_dirs_survive(
    tmp_path,
):
    recorded_opencode = (
        tmp_path / ".config" / "opencode" / "supermedicine" / "plugin.json"
    )
    recorded_claude = tmp_path / ".claude" / "skills" / "supermedicine" / "SKILL.md"
    unrecorded_neighbor = tmp_path / ".claude" / "settings.json"
    for path in (recorded_opencode, recorded_claude, unrecorded_neighbor):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text(
        json.dumps(
            {
                "platforms": {
                    "opencode": {
                        "target_paths": [".config/opencode/supermedicine/plugin.json"]
                    },
                    "claude-code": {
                        "target_paths": [".claude/skills/supermedicine/SKILL.md"]
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert not recorded_opencode.exists()
    assert not recorded_claude.exists()
    assert unrecorded_neighbor.exists()


def test_invalid_install_record_is_ignored_safely(tmp_path, caplog):
    unrecorded_platform_file = tmp_path / ".opencode" / "plugin.json"
    unrecorded_platform_file.parent.mkdir()
    unrecorded_platform_file.write_text("user managed", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text("{not-json", encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert unrecorded_platform_file.exists()
    assert "Ignoring invalid install record" in caplog.text


def test_uninstall_logs_are_secret_redacted(tmp_path, caplog):
    secret = "sk-test-uninstall-secret"
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump({"llm": {"providers": {"openai": {"api_key": secret}}}}),
        encoding="utf-8",
    )
    caplog.set_level(logging.INFO, logger="Uninstall")

    uninstall(tmp_path, dry_run=True, force=True)

    assert secret not in caplog.text
    assert "api_key" not in caplog.text


def test_collect_candidates_defines_project_owned_rules(tmp_path):
    candidates, skipped = collect_removal_candidates(
        tmp_path, explicit_targets=[".supermedicine/custom-platform-copy"]
    )
    candidate_paths = {
        candidate.path.relative_to(tmp_path).as_posix() for candidate in candidates
    }

    assert ".supermedicine" in candidate_paths
    assert "workspaces" in candidate_paths
    assert ".supermedicine/custom-platform-copy" in candidate_paths
    assert skipped == []


def test_uninstall_removes_recorded_binary_shortcut_config_cache_log_temp_and_user_data_by_default(
    tmp_path,
):
    recorded_paths = {
        "binaries": ["bin/supermedicine.exe"],
        "shortcuts": ["shortcuts/SuperMedicine.lnk"],
        "config_dirs": ["config/supermedicine/settings.json"],
        "cache_dirs": ["cache/supermedicine/cache.db"],
        "log_dirs": ["logs/supermedicine/app.log"],
        "temp_dirs": ["tmp/supermedicine/session.tmp"],
        "user_data_paths": ["data/supermedicine/user.db"],
    }
    for values in recorded_paths.values():
        for relative in values:
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(recorded_paths), encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    for values in recorded_paths.values():
        for relative in values:
            assert not (tmp_path / relative).exists()


def test_uninstall_manifest_ownership_keys_cover_recorded_exe_and_shortcut_artifacts():
    manifest = json.loads(
        (
            __import__("pathlib").Path(__file__).resolve().parents[1] / "install.json"
        ).read_text(encoding="utf-8")
    )
    recorded_keys = set(manifest["uninstall"]["recorded_artifact_keys"])

    assert {"binaries", "binary_paths", "shortcuts", "shortcut_paths"}.issubset(
        recorded_keys
    )
    assert "binaries" in manifest["packaging_resources"]["source_tree_exe_policy"]
    assert "shortcut_paths" in manifest["packaging_resources"]["source_tree_exe_policy"]


def test_uninstall_can_preserve_recorded_user_data_explicitly(tmp_path):
    user_data = tmp_path / "data" / "supermedicine" / "user.db"
    generated_config = tmp_path / "config" / "supermedicine" / "settings.json"
    for path in (user_data, generated_config):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "user_data_paths": ["data/supermedicine/user.db"],
                "config_dirs": ["config/supermedicine/settings.json"],
            }
        ),
        encoding="utf-8",
    )

    result = uninstall(tmp_path, force=True, preserve_user_data=True)

    assert result["status"] == "removed"
    assert user_data.exists()
    assert not generated_config.exists()
    assert any("preserved-user-data" in item for item in result["skipped"])


def test_uninstall_preserve_user_data_keeps_supermedicine_config_when_recorded(
    tmp_path,
):
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("project_name: supermedicine\n", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.write_text(
        json.dumps({"user_data_paths": [".supermedicine"]}),
        encoding="utf-8",
    )

    result = uninstall(tmp_path, force=True, preserve_user_data=True)

    assert result["status"] == "removed"
    assert config.exists()
    assert any("preserved-user-data-parent" in item for item in result["skipped"])


def test_uninstall_reports_residuals_and_repair_suggestions_when_delete_fails(
    tmp_path, monkeypatch
):
    blocked = tmp_path / ".supermedicine" / "blocked.log"
    blocked.parent.mkdir(parents=True)
    blocked.write_text("locked", encoding="utf-8")

    def fail_delete(path):
        raise OSError("file is locked")

    monkeypatch.setattr("uninstall_entry._delete_path", fail_delete)

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed-with-residuals"
    assert result["residuals"]
    assert result["repair_suggestions"]


# ═══ Component Integration Tests ═══════════════════════════════════════════════


def test_interactive_installer_component_selection_step(tmp_path, monkeypatch, caplog):
    """Interactive installer prompts for component selection when install.json defines components."""
    import logging

    from installer import entrypoint as Install

    caplog.set_level(logging.INFO)

    # Create a minimal install.json with components in the workspace
    source_root = tmp_path / "source"
    source_root.mkdir()
    install_json = source_root / "install.json"
    install_json.write_text(
        json.dumps(
            {
                "name": "supermedicine",
                "version": "test",
                "components": {
                    "cli": {
                        "name": "cli",
                        "description": "Command-line interface",
                        "required": True,
                        "default": True,
                        "files": ["cli/"],
                        "dependencies": [],
                    },
                    "web": {
                        "name": "web",
                        "description": "Web interface",
                        "required": False,
                        "default": False,
                        "files": ["web/"],
                        "dependencies": ["cli"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    prompts: list[str] = []
    # Sequence: path, extract, components toggle (confirm default), init, llm config, shortcuts, PATH, desktop exe, confirm
    answers = iter(
        [
            str(tmp_path),  # install path
            "",  # extract release: no
            "",  # component selection: accept default (cli only)
            "",  # init config: yes
            "openai",  # provider
            "https://openai.local.test/v1",  # base url
            "gpt-test",  # model
            "sk-test-component-interactive",  # api key
            "",  # shortcut: no
            "",  # PATH: no
            "",  # desktop exe: no
            "",  # confirm: yes
        ]
    )

    def fake_input(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    def fake_getpass(prompt: str) -> str:
        prompts.append(prompt)
        return "sk-test-component-interactive"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(Install.getpass, "getpass", fake_getpass)

    # Patch the source root resolution to point to our test source
    monkeypatch.setattr(Install, "_release_entrypoint_dir", lambda: source_root)

    Install.main([])

    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    # Verify the component selection prompt appeared
    assert any("组件选择" in prompt for prompt in prompts)
    # Verify component info was displayed via logger.info (not input prompts)
    assert "cli" in caplog.text


def test_install_record_contains_installed_components_field(tmp_path, monkeypatch):
    """After component install, install-record.json includes installed_components list."""

    from installer.component_installer import (
        load_components,
        install_components,
        get_default_selection,
    )

    # Set up source with install.json and component files
    source_root = tmp_path / "source"
    source_root.mkdir()
    cli_dir = source_root / "cli"
    cli_dir.mkdir()
    (cli_dir / "main.py").write_text("# cli main\n", encoding="utf-8")
    install_json = source_root / "install.json"
    install_json.write_text(
        json.dumps(
            {
                "name": "supermedicine",
                "version": "test",
                "components": {
                    "cli": {
                        "name": "cli",
                        "description": "Command-line interface",
                        "required": True,
                        "default": True,
                        "files": ["cli/"],
                        "dependencies": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    components = load_components(install_json)
    selected = get_default_selection(components)

    # Install components to target
    install_path = tmp_path / "installed"
    result = install_components(components, selected, install_path, source_root)
    assert result["status"] == "copied"

    # Simulate what the installer does: write install record with installed_components
    from installer.entrypoint import write_install_record, _install_record_artifacts_from_results

    artifacts = _install_record_artifacts_from_results(selected_components=selected)
    write_install_record(install_path, artifacts=artifacts, mode="init")

    # Read the written record and verify installed_components is present
    record_path = install_path / ".supermedicine" / "install-record.json"
    assert record_path.exists()
    written_record = json.loads(record_path.read_text(encoding="utf-8"))
    assert "installed_components" in written_record
    assert written_record["installed_components"] == ["cli"]


def test_component_uninstall_removes_component_files(tmp_path):
    """Component-based uninstall correctly removes component files."""

    from installer.component_installer import (
        load_components,
        install_components,
    )

    # Set up source with install.json and component files
    source_root = tmp_path / "source"
    source_root.mkdir()
    cli_dir = source_root / "cli"
    cli_dir.mkdir()
    (cli_dir / "main.py").write_text("# cli main\n", encoding="utf-8")
    (cli_dir / "utils.py").write_text("# cli utils\n", encoding="utf-8")
    web_dir = source_root / "web"
    web_dir.mkdir()
    (web_dir / "index.html").write_text("<html>web</html>\n", encoding="utf-8")
    install_json = source_root / "install.json"
    install_json.write_text(
        json.dumps(
            {
                "name": "supermedicine",
                "version": "test",
                "components": {
                    "cli": {
                        "name": "cli",
                        "description": "Command-line interface",
                        "required": True,
                        "default": True,
                        "files": ["cli/"],
                        "dependencies": [],
                    },
                    "web": {
                        "name": "web",
                        "description": "Web interface",
                        "required": False,
                        "default": False,
                        "files": ["web/"],
                        "dependencies": ["cli"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    components = load_components(install_json)
    selected = ["cli", "web"]

    # Install both components
    install_path = tmp_path / "installed"
    result = install_components(components, selected, install_path, source_root)
    assert result["status"] == "copied"
    assert (install_path / "cli" / "main.py").exists()
    assert (install_path / "cli" / "utils.py").exists()
    assert (install_path / "web" / "index.html").exists()

    # Copy install.json into the installed directory for uninstall to find
    shutil.copy2(install_json, install_path / "install.json")

    # Write an install record with installed_components
    record_path = install_path / ".supermedicine" / "install-record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(
            {
                "installed_components": ["cli", "web"],
                "created_paths": [".supermedicine"],
                "config_dirs": [".supermedicine"],
                "user_data_paths": [".supermedicine"],
            }
        ),
        encoding="utf-8",
    )

    # Uninstall all components
    uninstall_result = uninstall(install_path, force=True)

    assert uninstall_result["status"] == "removed"
    # Verify component files were removed
    assert not (install_path / "cli" / "main.py").exists()
    assert not (install_path / "cli" / "utils.py").exists()
    assert not (install_path / "web" / "index.html").exists()


def test_init_flag_still_works_without_component_changes(tmp_path):
    """Original --init installation path is not affected by componentization."""

    _copy_install_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_install(
        tmp_path,
        "--init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-init-no-components",
        "--model",
        "gpt-test",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert "ModuleNotFoundError" not in output
    assert "Traceback" not in output

    # Verify config contains the provider
    config_text = (tmp_path / ".supermedicine" / "config.yaml").read_text(encoding="utf-8")
    assert "openai" in config_text


def test_unified_install_flag_still_works_without_component_changes(tmp_path, monkeypatch):
    """Original --unified-install path is not affected by componentization."""

    install = importlib.import_module("installer.entrypoint")
    source = tmp_path / "dist" / "SuperMedicine.exe"
    source.parent.mkdir()
    source.write_bytes(b"fake exe bytes")
    desktop_dir = tmp_path / "fake-desktop"
    real_home = tmp_path / "real-home"
    real_home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(install.Path, "home", lambda: real_home)

    install.main(
        [
            "--unified-install",
            "--release-exe",
            str(source),
            "--desktop-dir",
            str(desktop_dir),
            "--exe-dry-run",
            *_llm_args(),
        ]
    )

    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert not (desktop_dir / "SuperMedicine.exe").exists()

    # Verify the install record does NOT contain installed_components
    # (since no components were selected in --unified-install mode)
    record_path = tmp_path / ".supermedicine" / "install-record.json"
    assert record_path.exists()
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert "installed_components" not in record

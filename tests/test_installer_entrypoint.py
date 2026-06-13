from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER_SUBPROCESS_TIMEOUT_SECONDS = 30


def _has_exact_child_name(directory: Path, filename: str) -> bool:
    """Return whether a directory contains an entry with this exact spelling.

    Path.exists()/is_file() are not sufficient here because Windows filesystems are
    commonly case-insensitive: ``Path("install_entry.py").is_file()`` can report true
    when only ``install_entry.py`` exists with different casing.  The installer contract
    must be explicit about the entrypoint spelling so platforms can run the documented
    user command ``python install_entry.py``.
    """

    return filename in {child.name for child in directory.iterdir()}


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


def _supports_case_distinct_names(directory: Path) -> bool:
    """Return whether this filesystem location can hold exact case-only siblings."""

    upper = directory / "CaseProbe.tmp"
    lower = directory / "caseprobe.tmp"
    try:
        upper.write_text("upper", encoding="utf-8")
        lower.write_text("lower", encoding="utf-8")
        return _has_exact_child_name(directory, upper.name) and _has_exact_child_name(
            directory, lower.name
        )
    finally:
        for path in (upper, lower):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _cp1252_stdio_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    return env


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

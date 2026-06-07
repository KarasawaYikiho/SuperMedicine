from __future__ import annotations

import importlib
import json
import logging
import shutil
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


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


def _has_exact_child_name(directory: Path, filename: str) -> bool:
    return filename in {child.name for child in directory.iterdir()}


def _supports_case_distinct_names(directory: Path) -> bool:
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


def _make_release_payload(root: Path) -> Path:
    payload = root / "release_payload"
    (payload / "core").mkdir(parents=True)
    (payload / "permission").mkdir()
    (payload / "installer").mkdir()
    (payload / "dist").mkdir()
    shutil.copy2(REPO_ROOT / "Install.py", payload / "Install.py")
    if _supports_case_distinct_names(payload):
        shutil.copy2(REPO_ROOT / "install.py", payload / "install.py")
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
    (payload / "README.md").write_text("docs\n", encoding="utf-8")
    return payload


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
    assert (target_dir / "install.py").exists()
    assert (target_dir / "Install.py").exists()
    assert (target_dir / "Install.py").read_text(encoding="utf-8") == (
        payload / "Install.py"
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
    (tmp_path / "Cli.py").write_text("print('payload')\n", encoding="utf-8")
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
    answers = iter([str(tmp_path), "2", "n", "n", "n", "n", "n", ""])

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
    answers = iter([str(tmp_path), "1", "1", "n", "n", "n", "n", "n", ""])

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

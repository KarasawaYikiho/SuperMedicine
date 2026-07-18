from __future__ import annotations

from pathlib import Path


def test_secure_config_permissions_use_owner_only_posix_modes(monkeypatch, tmp_path):
    from core import secure_files

    config_path = tmp_path / ".supermedicine" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("llm: {}\n", encoding="utf-8")
    chmod_calls: list[tuple[Path, int]] = []

    monkeypatch.setattr(secure_files, "IS_POSIX", True)
    monkeypatch.setattr(
        secure_files.os,
        "chmod",
        lambda path, mode: chmod_calls.append((Path(path), mode)),
    )

    secure_files.secure_config_permissions(config_path)

    assert chmod_calls == [
        (config_path.parent, 0o700),
        (config_path, 0o600),
    ]


def test_secure_config_permissions_are_noop_off_posix(monkeypatch, tmp_path):
    from core import secure_files

    config_path = tmp_path / ".supermedicine" / "config.yaml"
    monkeypatch.setattr(secure_files, "IS_POSIX", False)
    monkeypatch.setattr(
        secure_files.os,
        "chmod",
        lambda path, mode: (_ for _ in ()).throw(AssertionError("unexpected chmod")),
    )

    secure_files.secure_config_permissions(config_path)


def test_config_center_save_applies_secure_permissions(monkeypatch, tmp_path):
    from core.config_center import ConfigCenter

    calls: list[Path] = []
    monkeypatch.setattr(
        "core.config_center.secure_config_permissions",
        lambda path: calls.append(Path(path)),
    )
    config_path = tmp_path / ".supermedicine" / "config.yaml"

    ConfigCenter(config_path).save()

    assert calls == [config_path]


def test_installer_config_write_applies_secure_permissions(monkeypatch, tmp_path):
    from installer.entrypoint import _write_config

    calls: list[Path] = []
    monkeypatch.setattr(
        "installer.entrypoint.secure_config_permissions",
        lambda path: calls.append(Path(path)),
    )
    config_path = tmp_path / ".supermedicine" / "config.yaml"
    config_path.parent.mkdir()

    _write_config(config_path, {"llm": {"api_key": "secret"}})

    assert calls == [config_path]

"""Contracts for the shared installer service used by every interaction layer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _manifest(path: Path) -> Path:
    manifest = path / "install.json"
    manifest.write_text(
        json.dumps(
            {
                "components": {
                    "core": {
                        "name": "core",
                        "description": "Core",
                        "required": True,
                        "default": True,
                        "files": ["core/"],
                        "dependencies": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return manifest


def test_install_service_owns_manifest_resolution_and_component_copy(tmp_path):
    from installer.component_installer import InstallService

    source = tmp_path / "source"
    (source / "core").mkdir(parents=True)
    (source / "core" / "runtime.py").write_text("runtime", encoding="utf-8")
    service = InstallService.from_manifest(_manifest(tmp_path), source_root=source)

    assert service.default_selection() == ["core"]
    result = service.install(service.default_selection(), tmp_path / "target")

    assert result["status"] == "copied"
    assert (tmp_path / "target" / "core" / "runtime.py").read_text() == "runtime"
    assert service.diagnostics(["core"])["file_count"] == 1


def test_installer_package_exports_shared_install_service():
    from installer import InstallService

    assert InstallService.__name__ == "InstallService"


def test_install_service_rolls_back_files_created_before_copy_failure(
    tmp_path, monkeypatch
):
    from installer.component_installer import InstallService

    source = tmp_path / "source"
    (source / "core").mkdir(parents=True)
    (source / "core" / "a.py").write_text("a", encoding="utf-8")
    (source / "core" / "b.py").write_text("b", encoding="utf-8")
    service = InstallService.from_manifest(_manifest(tmp_path), source_root=source)

    import installer.component_installer as component_installer

    real_copy = component_installer.shutil.copy2
    calls = 0

    def fail_second_copy(source_path, target_path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated copy failure")
        return real_copy(source_path, target_path)

    monkeypatch.setattr(component_installer.shutil, "copy2", fail_second_copy)

    with pytest.raises(OSError, match="simulated copy failure"):
        service.install(["core"], tmp_path / "target")

    assert not (tmp_path / "target" / "core" / "a.py").exists()


def test_cli_gui_and_uninstaller_delegate_to_shared_install_service():
    root = Path(__file__).resolve().parents[1]
    cli = (root / "installer" / "entrypoint.py").read_text(encoding="utf-8")
    gui = (root / "installer" / "gui_installer.py").read_text(encoding="utf-8")
    uninstaller = (root / "uninstall_entry.py").read_text(encoding="utf-8")

    assert "from installer.component_installer import" in cli
    assert "from installer.component_installer import" in gui
    assert "InstallService.from_manifest" in cli
    assert "InstallService.from_manifest" in gui
    assert "from installer.component_installer import load_install_manifest" in uninstaller
    assert "load_install_manifest(project_dir / INSTALL_MANIFEST)" in uninstaller


def test_gui_installer_self_test_validates_manifest_service_and_storage(capsys):
    from installer.gui_installer import main

    assert main(["--self-test"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["ok"] is True
    assert report["checks"]["manifest"] is True
    assert report["checks"]["install_service"] is True
    assert report["checks"]["components"] is True
    assert report["checks"]["persistent_path_outside_bundle"] is True


def test_gui_installer_resolves_manifest_from_pyinstaller_bundle(tmp_path, monkeypatch):
    from installer import gui_installer

    manifest = tmp_path / "install.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(gui_installer.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert gui_installer._find_install_json() == manifest

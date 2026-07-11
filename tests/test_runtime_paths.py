from __future__ import annotations

import json

from core.runtime_paths import RuntimePaths


def test_source_paths_use_source_root_and_keep_spaces(tmp_path):
    source_root = tmp_path / "source tree with spaces"

    paths = RuntimePaths.resolve(source_root=source_root, environ={})

    assert paths.project_root == source_root.resolve()
    assert paths.data_root == source_root.resolve() / ".supermedicine"
    assert paths.resource_root == source_root.resolve()
    assert paths.executable_root == source_root.resolve()


def test_explicit_project_root_overrides_environment_and_install_evidence(tmp_path):
    explicit = tmp_path / "explicit project"
    environment = tmp_path / "environment project"
    installed = tmp_path / "installed project"
    record = installed / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"install_dir": str(installed)}), encoding="utf-8")

    paths = RuntimePaths.resolve(
        explicit,
        source_root=tmp_path / "source",
        install_record=record,
        environ={"SM_PROJECT_ROOT": str(environment)},
    )

    assert paths.project_root == explicit.resolve()


def test_environment_overrides_install_record(tmp_path):
    environment = tmp_path / "environment project"
    installed = tmp_path / "installed project"
    record = installed / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text(json.dumps({"install_dir": str(installed)}), encoding="utf-8")

    paths = RuntimePaths.resolve(
        source_root=tmp_path / "source",
        install_record=record,
        environ={"SM_PROJECT_ROOT": str(environment)},
    )

    assert paths.project_root == environment.resolve()


def test_valid_install_record_precedes_config_directory(tmp_path):
    installed = tmp_path / "recorded install"
    configured = tmp_path / "configured install"
    record = tmp_path / "record location" / "install-record.json"
    record.parent.mkdir()
    record.write_text(json.dumps({"install_dir": str(installed)}), encoding="utf-8")
    config = configured / ".supermedicine" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("project_name: supermedicine\n", encoding="utf-8")

    paths = RuntimePaths.resolve(
        source_root=tmp_path / "source",
        install_record=record,
        config_path=config,
        environ={},
    )

    assert paths.project_root == installed.resolve()


def test_invalid_install_record_falls_back_to_config_directory(tmp_path):
    configured = tmp_path / "configured install"
    record = tmp_path / "invalid record.json"
    record.write_text("{}", encoding="utf-8")
    config = configured / ".supermedicine" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("project_name: supermedicine\n", encoding="utf-8")

    paths = RuntimePaths.resolve(
        source_root=tmp_path / "source",
        install_record=record,
        config_path=config,
        environ={},
    )

    assert paths.project_root == configured.resolve()


def test_frozen_resources_are_read_only_and_data_never_uses_meipass(tmp_path):
    bundle = tmp_path / "read only bundle"
    executable = tmp_path / "Program Files" / "SuperMedicineGUI.exe"
    local_app_data = tmp_path / "Local App Data"
    bundle.mkdir()
    bundle.chmod(0o555)

    paths = RuntimePaths.resolve(
        frozen=True,
        bundle_root=bundle,
        executable=executable,
        platform="win32",
        environ={"LOCALAPPDATA": str(local_app_data)},
    )

    assert paths.resource_root == bundle.resolve()
    assert paths.executable_root == executable.parent.resolve()
    assert paths.project_root == (local_app_data / "SuperMedicine").resolve()
    assert paths.data_root == paths.project_root / ".supermedicine"
    assert bundle.resolve() not in paths.data_root.parents


def test_windows_gui_default_can_be_overridden(tmp_path):
    override = tmp_path / "portable data"

    paths = RuntimePaths.resolve(
        override,
        frozen=True,
        bundle_root=tmp_path / "bundle",
        executable=tmp_path / "SuperMedicineGUI.exe",
        platform="win32",
        environ={"LOCALAPPDATA": str(tmp_path / "LocalAppData")},
    )

    assert paths.project_root == override.resolve()
    assert paths.data_root == override.resolve() / ".supermedicine"

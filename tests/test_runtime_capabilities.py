from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from core.plugin_registry import PluginRegistry
from core.kernel import Kernel
from core.runtime_capabilities import (
    RuntimeInvariantError,
    validate_required_plugins,
)


def test_required_runtime_plugin_missing_fails_closed(tmp_path):
    registry = PluginRegistry(tmp_path / "plugins")
    registry.discover()

    with pytest.raises(RuntimeInvariantError) as captured:
        validate_required_plugins(registry, tmp_path / "install.json")

    assert captured.value.code == "required_plugin_missing"
    assert captured.value.to_dict()["details"]["plugin"] == "harness-core"


def test_discovery_replaces_stale_plugins_after_manifest_is_removed(tmp_path):
    plugin_dir = tmp_path / "plugins" / "example"
    plugin_dir.mkdir(parents=True)
    manifest = plugin_dir / "plugin.yaml"
    manifest.write_text(
        "name: example\nversion: '1'\ntype: tool\nentry: main.py\n",
        encoding="utf-8",
    )
    (plugin_dir / "main.py").write_text("def execute(action, params): return {}\n")
    registry = PluginRegistry(tmp_path / "plugins")

    registry.discover()
    manifest.unlink()
    registry.discover()

    assert registry.get("example") is None
    assert registry.list_plugins() == []


def test_kernel_startup_fails_closed_when_required_plugin_is_missing(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project: test\n", encoding="utf-8")
    (tmp_path / "plugins").mkdir()

    with pytest.raises(RuntimeInvariantError) as captured:
        Kernel(config_path=config_path, plugins_dir=tmp_path / "plugins")

    assert captured.value.code == "required_plugin_missing"


def _copy_required_plugins(destination: Path) -> PluginRegistry:
    source = Path(__file__).resolve().parents[1] / "plugins"
    for name in ("harness", "rag"):
        shutil.copytree(source / name, destination / name)
    registry = PluginRegistry(destination)
    registry.discover()
    return registry


def test_duplicate_required_plugin_name_fails_with_stable_code(tmp_path):
    plugins = tmp_path / "plugins"
    registry = _copy_required_plugins(plugins)
    duplicate = plugins / "duplicate-harness"
    duplicate.mkdir()
    (duplicate / "plugin.yaml").write_text(
        "name: harness-core\nversion: '1'\ntype: harness\nentry: main.py\n",
        encoding="utf-8",
    )
    (duplicate / "main.py").write_text("def execute(*args): return {}\n", encoding="utf-8")
    registry.discover()

    with pytest.raises(RuntimeInvariantError) as captured:
        validate_required_plugins(registry)

    assert captured.value.code == "duplicate_plugin_name"


def test_required_entry_import_failure_has_stable_code(tmp_path):
    plugins = tmp_path / "plugins"
    registry = _copy_required_plugins(plugins)
    (plugins / "rag" / "main.py").write_text("def broken(:\n", encoding="utf-8")
    registry.discover()

    with pytest.raises(RuntimeInvariantError) as captured:
        validate_required_plugins(registry)

    assert captured.value.code == "required_plugin_import_error"


def test_disable_requests_are_ignored_and_reported(tmp_path):
    registry = _copy_required_plugins(tmp_path / "plugins")
    config = tmp_path / "config.yaml"
    config.write_text("harness:\n  enabled: false\nrag:\n  enabled: false\n", encoding="utf-8")

    capabilities = validate_required_plugins(registry, config)

    assert capabilities.healthy is True
    assert {item["plugin"] for item in capabilities.diagnostics if item.get("code") == "invalid_disable_request"} == {"harness", "rag"}


def test_required_manifest_must_declare_required_and_not_disableable(tmp_path):
    plugins = tmp_path / "plugins"
    registry = _copy_required_plugins(plugins)
    manifest = plugins / "rag" / "plugin.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace("required: true", "required: false"),
        encoding="utf-8",
    )
    registry.discover()

    with pytest.raises(RuntimeInvariantError) as captured:
        validate_required_plugins(registry)

    assert captured.value.code == "required_plugin_manifest_invalid"

import yaml
from core.plugin_registry import PluginRegistry
from plugins.base_plugin import BasePlugin

class TestPluginRegistry:
    def _create_plugin(self, tmp_path, name="test-plugin"):
        d = tmp_path / name; d.mkdir(parents=True)
        (d / "plugin.yaml").write_text(yaml.dump({"name": name, "version": "0.1.0", "type": "tool", "provides": ["test.action"]}))
        return d
    def test_discover(self, tmp_path):
        self._create_plugin(tmp_path, "a"); self._create_plugin(tmp_path, "b")
        assert len(PluginRegistry(tmp_path).discover()) == 2
    def test_load_meta(self, tmp_path):
        self._create_plugin(tmp_path)
        r = PluginRegistry(tmp_path); r.discover()
        m = r.get_meta("test-plugin")
        assert m is not None and m.name == "test-plugin" and m.version == "0.1.0"
    def test_get_plugin(self, tmp_path):
        self._create_plugin(tmp_path)
        r = PluginRegistry(tmp_path); r.discover()
        p = r.get("test-plugin")
        assert p is not None and isinstance(p, BasePlugin)
    def test_unknown_returns_none(self, tmp_path):
        r = PluginRegistry(tmp_path)
        assert r.get("nope") is None and r.get_meta("nope") is None

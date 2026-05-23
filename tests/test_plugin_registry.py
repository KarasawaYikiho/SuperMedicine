import yaml
from core.plugin_registry import PluginRegistry
from plugins.base_plugin import BasePlugin

class TestPluginRegistry:
    def _create_plugin(self, tmp_path, name="test-plugin"):
        d = tmp_path / name
        d.mkdir(parents=True)
        (d / "plugin.yaml").write_text(yaml.dump({"name": name, "version": "0.1.0", "type": "tool", "provides": ["test.action"]}))
        return d
    def test_discover(self, tmp_path):
        self._create_plugin(tmp_path, "a")
        self._create_plugin(tmp_path, "b")
        assert len(PluginRegistry(tmp_path).discover()) == 2
    def test_load_meta(self, tmp_path):
        self._create_plugin(tmp_path)
        r = PluginRegistry(tmp_path)
        r.discover()
        m = r.get_meta("test-plugin")
        assert m is not None and m.name == "test-plugin" and m.version == "0.1.0"
    def test_get_plugin(self, tmp_path):
        self._create_plugin(tmp_path)
        r = PluginRegistry(tmp_path)
        r.discover()
        p = r.get("test-plugin")
        assert p is not None and isinstance(p, BasePlugin)
    def test_unknown_returns_none(self, tmp_path):
        r = PluginRegistry(tmp_path)
        assert r.get("nope") is None and r.get_meta("nope") is None

    def test_python_entry_execute_success(self, tmp_path):
        d = self._create_plugin(tmp_path, "entry-plugin")
        (d / "main.py").write_text(
            "def execute(action, params):\n"
            "    return {'status': 'success', 'action': action, 'result': params}\n"
        )
        r = PluginRegistry(tmp_path)
        r.discover()
        result = r.get("entry-plugin").execute("demo.action", {"ok": True})
        assert result["status"] == "success"
        assert result["output"] == {"ok": True}
        assert result["error"] is None
        assert "contract_version" in result["metadata"]

    def test_python_entry_missing_execute_returns_plugin_error(self, tmp_path):
        d = self._create_plugin(tmp_path, "bad-entry-plugin")
        (d / "main.py").write_text("VALUE = 1\n")
        r = PluginRegistry(tmp_path)
        r.discover()
        result = r.get("bad-entry-plugin").execute("demo.action", {})
        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert result["error"]

    def test_python_entry_exception_is_structured_plugin_error(self, tmp_path):
        d = self._create_plugin(tmp_path, "faulty-entry-plugin")
        (d / "main.py").write_text(
            "def execute(action, params, context=None):\n"
            "    raise RuntimeError('boom')\n"
        )
        r = PluginRegistry(tmp_path)
        r.discover()
        result = r.get("faulty-entry-plugin").execute("demo.action", {})
        assert result["status"] == "plugin_error"
        assert result["plugin"] == "faulty-entry-plugin"
        assert result["action"] == "demo.action"
        assert result["output"] is None
        assert "boom" in result["error"]

    def test_medical_statistics_plugins_expose_prototype_boundary_contract(self):
        r = PluginRegistry("plugins")
        r.discover()
        py_result = r.get("python-stats").execute("stats.descriptive", {"data": [1, 2, 3]})
        survival_result = r.get("r-survival").execute("r.survival.km", {"times": [1, 2, 3], "events": [1, 0, 1]})
        for result in (py_result, survival_result):
            assert result["status"] == "success"
            assert result["metadata"]["audit"]["interface_only"] is True
            assert result["metadata"]["audit"]["prototype_path"] is True
            assert result["metadata"]["contract"]["stage"] == "prototype-interface-tests-only"
            assert "not clinical-grade statistics" in result["metadata"]["medical_boundary"]

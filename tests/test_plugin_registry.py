import yaml
from core.plugin_registry import PluginRegistry
from plugins.base_plugin import BasePlugin


class TestAdapterDiscoveryRegistry:
    def test_top_level_adapters_import_exposes_static_metadata_without_platform_imports(self):
        import sys

        sys.modules.pop("adapters", None)
        sys.modules.pop("adapters.standalone", None)
        sys.modules.pop("adapters.standalone.adapter", None)
        sys.modules.pop("adapters.opencode", None)
        sys.modules.pop("adapters.opencode.adapter", None)
        sys.modules.pop("adapters.claude_code", None)
        sys.modules.pop("adapters.claude_code.adapter", None)

        import adapters

        assert "adapters.standalone.adapter" not in sys.modules
        assert "adapters.opencode.adapter" not in sys.modules
        assert "adapters.claude_code.adapter" not in sys.modules

        registrations = adapters.list_adapter_registrations()
        assert {item["platform"] for item in registrations} == {"standalone", "opencode", "claude-code"}
        assert adapters.default_adapter_registration()["platform"] == "standalone"

        for registration in registrations:
            assert registration["module"].startswith("adapters.")
            assert "adapter_class" in registration

        assert "adapters.standalone" not in sys.modules
        assert "adapters.opencode" not in sys.modules
        assert "adapters.claude_code" not in sys.modules

    def test_adapter_registry_distinguishes_core_and_optional_boundaries(self):
        import adapters

        standalone = adapters.get_adapter_registration("standalone")
        opencode = adapters.get_adapter_registration("opencode")
        claude = adapters.get_adapter_registration("claude-code")

        assert standalone["core"] is True
        assert standalone["default"] is True
        assert standalone["optional"] is False
        assert opencode["optional"] is True
        assert opencode["core"] is False
        assert opencode["requires_core_runtime"] is False
        assert claude["optional"] is True
        assert claude["core"] is False
        assert claude["requires_core_runtime"] is False
        assert adapters.list_adapter_registrations(include_optional=False) == [standalone]


class TestPluginRegistry:
    def _create_plugin(self, tmp_path, name="test-plugin"):
        d = tmp_path / name
        d.mkdir(parents=True)
        (d / "plugin.yaml").write_text(yaml.dump({"name": name, "version": "0.1.0", "type": "tool", "provides": ["test.action"]}), encoding="utf-8")
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
            "    return {'status': 'success', 'action': action, 'result': params}\n",
            encoding="utf-8",
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
        (d / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
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
            "    raise RuntimeError('boom')\n",
            encoding="utf-8",
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

    def test_rag_interface_manifest_actions_execute_with_stable_shape(self, tmp_path):
        r = PluginRegistry("plugins")
        metas = r.discover()
        meta = r.get_meta("rag-interface")
        assert meta is not None
        assert meta.name in [item.name for item in metas]
        assert {item["id"] for item in meta.provides} == {"rag.query", "rag.context.store", "rag.context.retrieve"}

        result = r.get("rag-interface").execute(
            "rag.query",
            {
                "query": "hypertension cardiovascular",
                "top_k": 1,
                "storage_dir": str(tmp_path / "rag"),
                "documents": [
                    {
                        "id": "doc-1",
                        "title": "Hypertension review",
                        "source": "local-test-index",
                        "text": "hypertension diabetes cardiovascular risk",
                    }
                ],
            },
        )

        assert result["status"] == "success"
        assert result["plugin"] == "rag-interface"
        assert result["action"] == "rag.query"
        output = result["output"]
        assert output["status"] == "success"
        assert output["items"][0]["source"] == "local-test-index"
        assert output["items"][0]["title"] == "Hypertension review"
        assert "score" in output["items"][0]
        assert "snippet" in output["items"][0]
        assert output["errors"] == []
        assert "metadata" in output

    def test_rag_interface_invalid_input_is_structured_plugin_error(self):
        r = PluginRegistry("plugins")
        r.discover()

        result = r.get("rag-interface").execute("rag.query", {"query": ""})

        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid rag-interface input" in result["error"]

    def test_harness_core_manifest_actions_execute_with_stable_shape(self, tmp_path):
        checkpoint_task = tmp_path / "checkpoints" / "task-1" / "step-1"
        checkpoint_task.mkdir(parents=True)
        (checkpoint_task / "status.json").write_text('{"state": "completed"}', encoding="utf-8")

        r = PluginRegistry("plugins")
        metas = r.discover()
        meta = r.get_meta("harness-core")
        assert meta is not None
        assert meta.name in [item.name for item in metas]
        assert {item["id"] for item in meta.provides} == {
            "harness.integration.checkpoint",
            "harness.integration.checkpoint_all",
            "harness.monitor.permission_audit",
            "harness.monitor.denied_actions",
            "harness.monitor.anomaly",
            "harness.monitor.performance",
            "harness.monitor.failure_patterns",
        }

        result = r.get("harness-core").execute(
            "harness.integration.checkpoint",
            {"checkpoint_dir": str(tmp_path / "checkpoints"), "task_id": "task-1"},
        )

        assert result["status"] == "success"
        assert result["plugin"] == "harness-core"
        assert result["action"] == "harness.integration.checkpoint"
        assert result["output"]["complete"] is True
        assert result["output"]["structurally_complete"] is True
        assert result["output"]["final_state_success"] is True
        assert result["output"]["warnings"] == []
        assert result["output"]["total_steps"] == 1
        assert result["metadata"]["contract"]["actions"]

    def test_harness_core_monitor_malformed_jsonl_returns_warnings(self, tmp_path):
        audit_log = tmp_path / "audit.jsonl"
        audit_log.write_text('{"agent_id":"alpha","result":"DENIED"}\n{not-json\n', encoding="utf-8")
        r = PluginRegistry("plugins")
        r.discover()

        result = r.get("harness-core").execute(
            "harness.monitor.permission_audit",
            {"audit_log_path": str(audit_log)},
        )

        assert result["status"] == "success"
        assert result["output"]["total"] == 1
        assert result["output"]["warnings"][0]["code"] == "malformed_json"

    def test_harness_core_invalid_input_is_structured_plugin_error(self):
        r = PluginRegistry("plugins")
        r.discover()

        result = r.get("harness-core").execute("harness.integration.checkpoint", {"task_id": "task-1"})

        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid harness-core input" in result["error"]

    def test_medical_citation_manifest_actions_execute_with_stable_shape(self):
        r = PluginRegistry("plugins")
        metas = r.discover()
        meta = r.get_meta("medical-citation")
        assert meta is not None
        assert meta.name in [item.name for item in metas]
        assert {item["id"] for item in meta.provides} == {"standard.citation.ama", "standard.citation.vancouver"}

        result = r.get("medical-citation").execute(
            "standard.citation.ama",
            {
                "source_id": "src-1",
                "sources": {
                    "src-1": {
                        "reference_type": "journal",
                        "authors": ["John Smith", "Jane Doe"],
                        "title": "Cardiovascular Risk Factors",
                        "journal": "JAMA",
                        "year": 2024,
                        "volume": "331",
                        "issue": "5",
                        "pages": "401-410",
                        "doi": "10.1001/jama.2024.1234",
                    }
                },
            },
        )

        assert result["status"] == "success"
        assert result["plugin"] == "medical-citation"
        assert result["action"] == "standard.citation.ama"
        assert result["output"]["format"] == "AMA"
        assert "Smith J" in result["output"]["citation"]

    def test_medical_citation_invalid_input_is_structured_plugin_error(self):
        r = PluginRegistry("plugins")
        r.discover()

        result = r.get("medical-citation").execute("standard.citation.ama", {"source_id": "missing", "sources": {}})

        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert "Invalid medical-citation input" in result["error"]

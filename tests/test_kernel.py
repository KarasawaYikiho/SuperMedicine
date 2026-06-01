from __future__ import annotations

import shutil
import yaml
from core.llm_client import LLMClient
from core.kernel import Kernel
from permission.engine import PermissionEngine
from permission.prompt_generator import PromptGenerator

class TestKernel:
    def _create_kernel(self, tmp_path):
        (tmp_path / "config.yaml").write_text(yaml.dump({"project": "test"}), encoding="utf-8")
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        return Kernel(config_path=tmp_path / "config.yaml", plugins_dir=tmp_path / "plugins", policies_dir=tmp_path / "policies")
    def test_init(self, tmp_path):
        assert self._create_kernel(tmp_path) is not None
    def test_config(self, tmp_path):
        assert self._create_kernel(tmp_path).config.get("project") == "test"
    def test_plugin_registry(self, tmp_path):
        assert self._create_kernel(tmp_path).plugin_registry is not None
    def test_event_bus(self, tmp_path):
        assert self._create_kernel(tmp_path).event_bus is not None

    def test_kernel_permission_engine_is_runtime_gate_not_prompt_generator(self, tmp_path):
        kernel = self._create_kernel(tmp_path)

        assert isinstance(kernel.permission_engine, PermissionEngine)
        assert not isinstance(kernel.permission_engine, PromptGenerator)

    def test_llm_chat_provider_exception_returns_structured_error_and_checkpoint(self, tmp_path, monkeypatch):
        class ExplodingClient(LLMClient):
            def chat(self, messages, **kwargs):
                raise RuntimeError("provider failed api_key=sk-kernel-secret")

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(kernel.llm_manager, "create_client", lambda: ExplodingClient())
        monkeypatch.setattr(kernel.llm_manager, "get_current_provider", lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"})
        monkeypatch.setattr(kernel.llm_manager, "validate_provider", lambda name, config: None)

        result = kernel.execute_task("unmatched natural language")

        assert result["status"] == "llm_error"
        assert result["action"] == "llm.chat"
        assert result["error"]["code"] == "provider_chat_exception"
        assert "sk-kernel-secret" not in str(result)
        assert list((tmp_path / "checkpoints").rglob("status.json"))

from __future__ import annotations

import shutil
import yaml
from core.llm_client import LLMClient
from core.kernel import Kernel, SUPERMEDICINE_SYSTEM_PROMPT
from permission.engine import PermissionEngine
from permission.prompt_generator import PromptGenerator


class TestKernel:
    def _create_kernel(self, tmp_path):
        (tmp_path / "config.yaml").write_text(
            yaml.dump({"project": "test"}), encoding="utf-8"
        )
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        shutil.copyfile(
            PermissionEngine.default_policy_path(),
            tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
        )
        return Kernel(
            config_path=tmp_path / "config.yaml",
            plugins_dir=tmp_path / "plugins",
            policies_dir=tmp_path / "policies",
        )

    def test_init(self, tmp_path):
        assert self._create_kernel(tmp_path) is not None

    def test_config(self, tmp_path):
        assert self._create_kernel(tmp_path).config.get("project") == "test"

    def test_plugin_registry(self, tmp_path):
        assert self._create_kernel(tmp_path).plugin_registry is not None

    def test_event_bus(self, tmp_path):
        assert self._create_kernel(tmp_path).event_bus is not None

    def test_kernel_permission_engine_is_runtime_gate_not_prompt_generator(
        self, tmp_path
    ):
        kernel = self._create_kernel(tmp_path)

        assert isinstance(kernel.permission_engine, PermissionEngine)
        assert not isinstance(kernel.permission_engine, PromptGenerator)

    def test_llm_chat_provider_exception_returns_structured_error_and_checkpoint(
        self, tmp_path, monkeypatch
    ):
        class ExplodingClient(LLMClient):
            def chat(self, messages, **kwargs):
                raise RuntimeError("provider failed api_key=sk-kernel-secret")

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: ExplodingClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("unmatched natural language")

        assert result["status"] == "llm_error"
        assert result["action"] == "llm.chat"
        assert result["error"]["code"] == "provider_chat_exception"
        assert "sk-kernel-secret" not in str(result)
        assert list((tmp_path / "checkpoints").rglob("status.json"))

    def test_llm_chat_injects_supermedicine_system_prompt_before_user_message(
        self, tmp_path, monkeypatch
    ):
        captured = {}

        class CapturingClient(LLMClient):
            def chat(self, messages, **kwargs):
                captured["messages"] = messages
                return {
                    "content": "I am SuperMedicine, the SuperMedicine project assistant."
                }

            def complete(self, prompt, **kwargs):
                return {"content": ""}

        kernel = self._create_kernel(tmp_path)
        monkeypatch.setattr(
            kernel.llm_manager, "create_client", lambda: CapturingClient()
        )
        monkeypatch.setattr(
            kernel.llm_manager,
            "get_current_provider",
            lambda redacted=True: {"provider": "fake", "api_key": "<redacted>"},
        )
        monkeypatch.setattr(
            kernel.llm_manager, "validate_provider", lambda name, config: None
        )

        result = kernel.execute_task("你是谁？")

        assert result["status"] == "success"
        assert (
            result["output"]
            == "I am SuperMedicine, the SuperMedicine project assistant."
        )
        assert "ChatGPT" not in result["output"]
        assert captured["messages"][0]["role"] == "system"
        assert "SuperMedicine" in captured["messages"][0]["content"]
        assert "project assistant" in captured["messages"][0]["content"]
        assert (
            "prototype/interface-stage research assistance"
            in captured["messages"][0]["content"]
        )
        assert "runtime wiring" in captured["messages"][0]["content"]
        assert captured["messages"][0]["content"] == SUPERMEDICINE_SYSTEM_PROMPT
        assert captured["messages"][1] == {"role": "user", "content": "你是谁？"}

    def test_llm_chat_system_prompt_preserves_permission_generator_boundary(
        self, tmp_path
    ):
        kernel = self._create_kernel(tmp_path)
        messages = kernel._llm_chat_messages("你的职责是什么？")

        assert messages[0]["role"] == "system"
        assert (
            "advisory prompt text is not a substitute for runtime permission checks"
            in messages[0]["content"]
        )
        assert "PromptGenerator" not in messages[0]["content"]
        assert "PermissionEngine" not in messages[0]["content"]
        assert messages[1] == {"role": "user", "content": "你的职责是什么？"}

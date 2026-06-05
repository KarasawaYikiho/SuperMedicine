"""LLM 客户端测试"""

from __future__ import annotations

import json
from unittest.mock import patch

import yaml

from core.config_center import ConfigCenter
from core.llm_client import (
    LLMClient,
    TrackedLLMClient,
    create_configured_llm_client,
    create_llm_client,
)
from core.llm_providers.base import AnthropicClient, OpenAIClient
from core.llm_providers import base as provider_base
from core.llm_providers.config import LLMProviderConfig
from core.llm_providers.openrouter import OpenRouterClient


class TestOpenRouterClient:
    """测试 OpenRouter LLM 客户端"""

    def test_init_defaults(self):
        """测试默认初始化"""
        client = OpenRouterClient()
        assert client.model == "anthropic/claude-3.5-sonnet"

    def test_init_custom_model(self):
        """测试自定义模型"""
        client = OpenRouterClient(model="openai/gpt-4o")
        assert client.model == "openai/gpt-4o"

    def test_complete_without_api_key(self):
        """无 API Key 时返回错误"""
        client = OpenRouterClient(api_key="")
        result = client.complete("Hello")
        assert result["content"] == ""
        assert "error" in result

    def test_chat_mock_response(self):
        """模拟 API 响应"""
        client = OpenRouterClient(api_key="test-key")
        with patch.object(
            client,
            "chat",
            return_value={
                "content": "Hello, I am Claude.",
                "model": "anthropic/claude-3.5-sonnet",
                "usage": {"prompt_tokens": 5, "completion_tokens": 10},
            },
        ):
            result = client.chat([{"role": "user", "content": "Hi"}])
            assert result["content"] == "Hello, I am Claude."
            assert result["model"] == "anthropic/claude-3.5-sonnet"

    def test_complete_mock_response(self):
        """模拟 Complete 调用"""
        client = OpenRouterClient(api_key="test-key")
        with patch.object(
            client,
            "_openai_request",
            return_value={
                "content": "Response text",
                "model": "anthropic/claude-3.5-sonnet",
                "usage": {},
            },
        ):
            result = client.complete("Test prompt", temperature=0.5)
            assert result["content"] == "Response text"


class TestLLMFactory:
    """测试 LLM 工厂函数"""

    def test_create_openrouter(self):
        """创建 OpenRouter 客户端"""
        client = create_llm_client("openrouter", api_key="test-key", model="test-model")
        assert isinstance(client, OpenRouterClient)
        assert client.model == "test-model"

    def test_create_openai(self):
        client = create_llm_client("openai", api_key="test-key", model="gpt-test")
        assert isinstance(client, OpenAIClient)
        assert client.model == "gpt-test"

    def test_create_anthropic(self):
        client = create_llm_client("anthropic", api_key="test-key", model="claude-test")
        assert isinstance(client, AnthropicClient)
        assert client.model == "claude-test"

    def test_create_unsupported(self):
        """未配置 api_format 的自定义 Provider 默认使用 OpenAI 格式"""
        client = create_llm_client("unsupported")
        assert isinstance(client, OpenAIClient)
        assert client.config.provider == "unsupported"

    def test_create_custom_openai_format_provider_from_config(self):
        client = create_llm_client(
            "local-openai-compatible",
            config={
                "api_format": "openai",
                "base_url": "https://local-openai.test/v1",
                "api_key": "test-key",
                "model": "local-gpt",
            },
        )

        assert isinstance(client, OpenAIClient)
        assert client.model == "local-gpt"

    def test_create_custom_anthropic_format_provider_from_config(self):
        client = create_llm_client(
            "local-anthropic-compatible",
            config={
                "api_format": "anthropic",
                "base_url": "https://local-anthropic.test/v1",
                "api_key": "test-key",
                "model": "local-claude",
            },
        )

        assert isinstance(client, AnthropicClient)
        assert client.model == "local-claude"


class TestTrackedLLMClientDiagnostics:
    def test_missing_usage_emits_debug_diagnostic(self, caplog):
        class FakeClient(LLMClient):
            def chat(self, messages, **kwargs):
                return {"content": "ok", "model": "fake-model"}

            def complete(self, prompt, **kwargs):
                return {"content": "ok", "model": "fake-model"}

        class FakeTracker:
            def record(self, *args, **kwargs):
                raise AssertionError("missing usage should not be recorded")

        caplog.set_level("DEBUG", logger="core.llm_client")
        TrackedLLMClient(FakeClient(), "fake", FakeTracker()).chat(
            [{"role": "user", "content": "hi"}]
        )

        assert "LLM usage unavailable or malformed" in caplog.text


class TestUnifiedProviderConfig:
    def test_openai_missing_api_key_structured_error(self):
        client = create_llm_client(
            "openai", api_key="", base_url="https://example.test/v1"
        )
        result = client.complete("Hello")
        assert result["error"]["code"] == "missing_api_key"

    def test_openai_config_does_not_inject_real_provider_defaults(self):
        config = LLMProviderConfig.from_mapping("openai", {})

        assert config.base_url == ""
        assert config.model == ""

    def test_anthropic_missing_base_url_structured_error(self):
        client = create_llm_client("anthropic", api_key="test-key", base_url="")
        result = client.complete("Hello")
        assert result["error"]["code"] == "missing_base_url"

    def test_error_does_not_expose_api_key(self):
        secret = "sk-test-secret"
        config = LLMProviderConfig.from_mapping("openai", {"api_key": secret})
        result = config.error("request_error", f"failed with {secret}")
        assert secret not in str(result)
        assert "<redacted>" in str(result)

    def test_safe_dict_redacts_secret_headers(self):
        config = LLMProviderConfig.from_mapping(
            "openai",
            {
                "api_key": "sk-test-secret",
                "headers": {"Authorization": "Bearer sk-test-secret"},
            },
        )
        safe = config.safe_dict()
        assert safe["api_key"] == "<redacted>"
        assert safe["headers"]["Authorization"] == "<redacted>"

    def test_openai_chat_request_uses_config_without_real_network(self, monkeypatch):
        secret = "sk-test-openai-fake-key"
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "model": "gpt-fake",
                        "choices": [{"message": {"content": "local fake response"}}],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 2},
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        client = create_llm_client(
            "openai",
            api_key=secret,
            base_url="https://openai.local.test/v1",
            model="gpt-fake",
            timeout=3,
        )
        result = client.chat(
            [{"role": "user", "content": "hello"}], temperature=0.2, max_tokens=7
        )

        assert result["content"] == "local fake response"
        assert captured["url"] == "https://openai.local.test/v1/chat/completions"
        assert captured["headers"]["Authorization"] == f"Bearer {secret}"
        assert captured["payload"] == {
            "model": "gpt-fake",
            "messages": [{"role": "user", "content": "hello"}],
            "temperature": 0.2,
            "max_tokens": 7,
        }
        assert captured["timeout"] == 3

    def test_anthropic_request_uses_messages_api_without_real_network(
        self, monkeypatch
    ):
        secret = "anthropic-test-fake-key"
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return json.dumps(
                    {
                        "model": "claude-fake",
                        "content": [{"type": "text", "text": "anthropic local fake"}],
                        "usage": {"input_tokens": 1, "output_tokens": 2},
                    }
                ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

        client = create_llm_client(
            "anthropic",
            api_key=secret,
            base_url="https://anthropic.local.test/v1",
            model="claude-fake",
            timeout=4,
        )
        result = client.chat(
            [
                {"role": "system", "content": "system boundary"},
                {"role": "user", "content": "hello"},
            ],
            temperature=0.1,
            max_tokens=9,
        )

        assert result["content"] == "anthropic local fake"
        assert captured["url"] == "https://anthropic.local.test/v1/messages"
        captured_headers = {
            key.lower(): value for key, value in captured["headers"].items()
        }
        assert captured_headers["x-api-key"] == secret
        assert captured["payload"] == {
            "model": "claude-fake",
            "max_tokens": 9,
            "messages": [{"role": "user", "content": "hello"}],
            "system": "system boundary",
            "temperature": 0.1,
        }
        assert captured["timeout"] == 4

    def test_config_mapping_reads_provider_env_without_exposing_secret(
        self, monkeypatch
    ):
        secret = "sk-test-env-only-secret"
        monkeypatch.setenv("OPENAI_API_KEY", secret)

        client = create_llm_client(
            "openai",
            config={"base_url": "https://env.local.test/v1", "model": "gpt-env"},
        )

        assert isinstance(client, OpenAIClient)
        assert client.config.api_key == secret
        assert client.config.safe_dict()["api_key"] == "<redacted>"
        assert secret not in str(client.config.safe_dict())

    def test_provider_url_rejects_credentials_before_network(self, monkeypatch):
        def fail_urlopen(*args, **kwargs):
            raise AssertionError("unsafe provider URL must not reach network")

        monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)
        client = create_llm_client(
            "openai",
            api_key="sk-test-secret",
            base_url="https://user:password@example.test/v1",
            model="gpt-fake",
        )

        result = client.chat([{"role": "user", "content": "hello"}])

        assert result["error"]["code"] == "invalid_base_url"
        assert "credentials" in result["error"]["message"]
        assert "sk-test-secret" not in str(result)

    def test_provider_response_size_limit_returns_structured_error(self, monkeypatch):
        class OversizedResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, size=None):
                return b"{" + (b"a" * provider_base.MAX_PROVIDER_RESPONSE_BYTES) + b"}"

        monkeypatch.setattr(
            "urllib.request.urlopen", lambda request, timeout: OversizedResponse()
        )
        client = create_llm_client(
            "openai",
            api_key="sk-test-secret",
            base_url="https://example.test/v1",
            model="gpt-fake",
        )

        result = client.chat([{"role": "user", "content": "hello"}])

        assert result["error"]["code"] == "invalid_response"
        assert "maximum supported size" in result["error"]["message"]

    def test_configured_factory_uses_config_center_runtime_provider(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "provider": "openai",
                        "last_provider": "anthropic",
                        "providers": {
                            "openai": {
                                "api_format": "openai",
                                "base_url": "https://openai.test/v1",
                                "api_key": "sk-openai",
                                "model": "gpt-test",
                            },
                            "anthropic": {
                                "api_format": "anthropic",
                                "base_url": "https://anthropic.test/v1",
                                "api_key": "sk-anthropic",
                                "model": "claude-test",
                            },
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        client = create_configured_llm_client(ConfigCenter(config_path))

        assert isinstance(client._wrapped, AnthropicClient)
        assert client.config.provider == "anthropic"

    def test_api_key_is_redacted_across_config_validation_and_client_error_path(self):
        secret = "sk-full-redaction-secret"
        provider_config = {
            "api_format": "openai",
            "base_url": "https://redaction.local.test/v1",
            "api_key": secret,
            "model": "gpt-redaction",
            "headers": {"Authorization": f"Bearer {secret}", "X-Api-Key": secret},
        }
        config = LLMProviderConfig.from_mapping("openai", provider_config)
        client = create_llm_client("openai", config=provider_config)

        safe_config = config.safe_dict()
        error = config.error(
            "request_error",
            f"Authorization failed for Bearer {secret}; api_key={secret}",
        )
        client_error = client.config.error("request_error", f"token={secret}")

        assert safe_config["api_key"] == "<redacted>"
        assert safe_config["headers"]["Authorization"] == "<redacted>"
        assert safe_config["headers"]["X-Api-Key"] == "<redacted>"
        assert secret not in str(safe_config)
        assert secret not in str(error)
        assert secret not in str(client_error)
        assert "<redacted>" in str(error) or "[REDACTED]" in str(error)

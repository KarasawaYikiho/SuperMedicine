"""Custom provider integration tests."""
from __future__ import annotations

import yaml

from core.config_center import ConfigCenter
from core.llm_client import create_llm_client
from core.llm_manager import LLMConfigManager
from core.llm_providers.base import AnthropicClient, OpenAIClient
from core.llm_providers.config import _default_api_key_env, _infer_api_format


def _write_config(tmp_path, providers: dict, *, current: str = "", last: str = "") -> ConfigCenter:
    """Helper: write a config.yaml with given LLM providers and return ConfigCenter."""
    llm: dict = {"providers": providers}
    if current:
        llm["provider"] = current
    if last:
        llm["last_provider"] = last
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"llm": llm}, sort_keys=False),
        encoding="utf-8",
    )
    return ConfigCenter(config_path)


class TestCustomOpenAIFormatProvider:
    """Test custom provider using OpenAI API format."""

    def test_custom_openai_format_provider(self, tmp_path):
        """Create config with custom provider 'deepseek' using api_format='openai',
        verify LLMConfigManager.create_client() returns an OpenAIClient instance
        with client.config.provider == 'deepseek'."""
        cc = _write_config(
            tmp_path,
            providers={
                "deepseek": {
                    "api_format": "openai",
                    "base_url": "https://api.deepseek.com/v1",
                    "api_key": "sk-deepseek-test",
                    "model": "deepseek-chat",
                },
            },
            current="deepseek",
        )
        manager = LLMConfigManager(cc)
        client = manager.create_client()

        assert isinstance(client._wrapped, OpenAIClient)
        assert client.config.provider == "deepseek"
        assert client.config.model == "deepseek-chat"


class TestCustomAnthropicFormatProvider:
    """Test custom provider using Anthropic API format."""

    def test_custom_anthropic_format_provider(self, tmp_path):
        """Create config with custom provider 'my-claude' using api_format='anthropic',
        verify LLMConfigManager.create_client() returns an AnthropicClient instance
        with client.config.provider == 'my-claude'."""
        cc = _write_config(
            tmp_path,
            providers={
                "my-claude": {
                    "api_format": "anthropic",
                    "base_url": "https://my-claude-proxy.example.com/v1",
                    "api_key": "sk-claude-test",
                    "model": "claude-3-sonnet",
                },
            },
            current="my-claude",
        )
        manager = LLMConfigManager(cc)
        client = manager.create_client()

        assert isinstance(client._wrapped, AnthropicClient)
        assert client.config.provider == "my-claude"
        assert client.config.model == "claude-3-sonnet"


class TestProviderNameInferredFormat:
    """Test _infer_api_format function with various provider names."""

    def test_provider_name_inferred_format(self):
        """Test _infer_api_format maps provider names to the correct API format."""
        # Anthropic-family providers
        assert _infer_api_format("anthropic") == "anthropic"
        assert _infer_api_format("claude-proxy") == "anthropic"

        # OpenAI-compatible providers
        assert _infer_api_format("deepseek") == "openai"
        assert _infer_api_format("zhipu") == "openai"
        assert _infer_api_format("ollama") == "openai"
        assert _infer_api_format("my-custom-provider") == "openai"


class TestCustomProviderNoWhitelistError:
    """Verify create_llm_client accepts custom providers without whitelist errors."""

    def test_custom_provider_no_whitelist_error(self):
        """create_llm_client('deepseek', config={...}) should NOT raise ValueError."""
        client = create_llm_client(
            "deepseek",
            config={
                "api_format": "openai",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": "sk-test",
                "model": "deepseek-chat",
            },
        )
        assert isinstance(client, OpenAIClient)
        assert client.config.provider == "deepseek"


class TestEnvVarGeneratedForCustomProvider:
    """Test _default_api_key_env generates correct environment variable names."""

    def test_env_var_generated_for_custom_provider(self):
        """Test _default_api_key_env returns correct env var for known and custom providers."""
        assert _default_api_key_env("openai") == "OPENAI_API_KEY"
        assert _default_api_key_env("anthropic") == "ANTHROPIC_API_KEY"
        assert _default_api_key_env("deepseek") == "DEEPSEEK_API_KEY"

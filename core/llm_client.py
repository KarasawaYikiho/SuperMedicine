"""LLM 客户端抽象层"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from core.redaction import redact_sensitive

if False:  # pragma: no cover - typing-only without runtime import cycle
    from core.config_center import ConfigCenter


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """发送多轮对话消息

        Args:
            messages: [{"role": "system|user|assistant", "content": "..."}]
            **kwargs: 模型特定参数 (temperature, max_tokens, etc.)

        Returns:
            {"content": "...", "model": "...", "usage": {...}}
        """
        ...

    @abstractmethod
    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """单轮文本补全

        Args:
            prompt: 提示文本
            **kwargs: 模型特定参数

        Returns:
            {"content": "...", "model": "...", "usage": {...}}
        """
        ...


def create_llm_client(provider: str, **kwargs: Any) -> LLMClient:
    """工厂函数：根据 provider 名称创建 LLMClient 实例

    Args:
        provider: "openai", "anthropic", or legacy "openrouter"
        **kwargs: 传递给具体 Provider 的参数 (api_key, model, etc.)

    Returns:
        LLMClient 实例

    Raises:
        ValueError: 不支持的 provider
    """
    config = kwargs.pop("config", None)
    has_config_mapping = isinstance(config, Mapping)
    if has_config_mapping:
        merged = dict(config)
        merged.update(kwargs)
        kwargs = merged

    normalized_provider = provider.lower()
    if normalized_provider and normalized_provider not in {"openai", "anthropic", "openrouter"}:
        api_format = str(kwargs.get("api_format") or kwargs.get("format") or "").lower()
        if has_config_mapping and api_format == "anthropic":
            normalized_provider = "anthropic"
        elif has_config_mapping and api_format in {"openai", "openai_responses", "responses"}:
            normalized_provider = "openai"
        else:
            raise ValueError(f"Unsupported LLM provider: {redact_sensitive(provider)}")
    if normalized_provider == "openai":
        from core.llm_providers.base import OpenAIClient
        return OpenAIClient(**kwargs)
    if normalized_provider == "anthropic":
        from core.llm_providers.base import AnthropicClient
        return AnthropicClient(**kwargs)
    if normalized_provider == "openrouter":
        from core.llm_providers.openrouter import OpenRouterClient
        return OpenRouterClient(**kwargs)
    raise ValueError(f"Unsupported LLM provider: {redact_sensitive(provider)}")


def create_configured_llm_client(config_center: "ConfigCenter") -> LLMClient | dict[str, Any]:
    """Create an LLM client from ConfigCenter runtime provider restoration logic."""
    from core.llm_manager import LLMConfigManager

    return LLMConfigManager(config_center).create_client()

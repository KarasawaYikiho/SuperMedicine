"""LLM 客户端抽象层"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from core.redaction import redact_sensitive

if False:  # pragma: no cover - typing-only without runtime import cycle
    from core.config_center import ConfigCenter
    from core.token_tracker import TokenTracker


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


class TrackedLLMClient(LLMClient):
    """Decorator that wraps an LLMClient and records token usage after each call.

    After each ``chat()`` or ``complete()`` call the wrapper inspects the
    ``usage`` field of the response dict and forwards the token counts to a
    :class:`TokenTracker`.  Missing or malformed usage data is silently
    ignored so that tracking failures never break the caller.
    """

    def __init__(self, wrapped: LLMClient, provider: str, tracker: "TokenTracker") -> None:
        self._wrapped = wrapped
        self._provider = provider
        self._tracker = tracker

    # -- property delegation ---------------------------------------------------

    @property
    def config(self):
        """Proxy config from the wrapped client."""
        return getattr(self._wrapped, 'config', None)

    # -- delegation -----------------------------------------------------------

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        response = self._wrapped.chat(messages, **kwargs)
        self._record_usage(response)
        return response

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        response = self._wrapped.complete(prompt, **kwargs)
        self._record_usage(response)
        return response

    # -- internal -------------------------------------------------------------

    def _record_usage(self, response: dict[str, Any]) -> None:
        """Extract usage from *response* and record it via the tracker."""
        usage: Any = response.get("usage")
        if not usage or not isinstance(usage, dict):
            return

        # Support both OpenAI-style and Anthropic-style usage dicts.
        prompt_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        if prompt_tokens == 0 and completion_tokens == 0:
            return

        model = str(response.get("model") or "unknown")
        self._tracker.record(
            self._provider,
            model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


def _infer_api_format(provider: str, kwargs: dict[str, Any]) -> str:
    """Infer API format from provider name or kwargs.

    Args:
        provider: Normalized provider name
        kwargs: Merged configuration kwargs

    Returns:
        Inferred api_format string
    """
    # Explicit api_format in kwargs takes precedence
    api_format = str(kwargs.get("api_format") or kwargs.get("format") or "").lower()
    if api_format:
        return api_format

    # Infer from provider name
    provider_lower = provider.lower()
    if provider_lower == "anthropic":
        return "anthropic"
    if provider_lower == "openrouter":
        return "openrouter"
    # Default to openai format for unknown providers
    return "openai"


def create_llm_client(provider: str, **kwargs: Any) -> LLMClient:
    """工厂函数：根据 api_format 创建 LLMClient 实例

    Routes to the appropriate client based on api_format rather than provider name.
    Any provider name is accepted; the api_format field determines which client is used.

    Args:
        provider: Any provider name (e.g., "openai", "anthropic", "deepseek", etc.)
        **kwargs: 传递给具体 Provider 的参数 (api_key, model, api_format, etc.)
            - api_format: "openai", "openai_responses", "responses", "anthropic", or "openrouter"
            - If not provided, inferred from provider name

    Returns:
        LLMClient 实例

    Raises:
        ValueError: 不支持的 api_format
    """
    config = kwargs.pop("config", None)
    has_config_mapping = isinstance(config, Mapping)
    if has_config_mapping:
        merged = dict(config)
        merged.update(kwargs)
        kwargs = merged

    normalized_provider = provider.lower()
    api_format = _infer_api_format(normalized_provider, kwargs)
    kwargs.setdefault("provider", normalized_provider)

    if api_format in ("openai", "openai_responses", "responses"):
        from core.llm_providers.base import OpenAIClient
        return OpenAIClient(**kwargs)
    if api_format == "anthropic":
        from core.llm_providers.base import AnthropicClient
        return AnthropicClient(**kwargs)
    if api_format == "openrouter" or normalized_provider == "openrouter":
        from core.llm_providers.openrouter import OpenRouterClient
        return OpenRouterClient(**kwargs)
    raise ValueError(f"Unsupported api_format: {redact_sensitive(api_format)}")


def create_configured_llm_client(config_center: "ConfigCenter") -> LLMClient | dict[str, Any]:
    """Create an LLM client from ConfigCenter runtime provider restoration logic."""
    from core.llm_manager import LLMConfigManager

    return LLMConfigManager(config_center).create_client()

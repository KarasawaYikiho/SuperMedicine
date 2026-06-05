"""OpenRouter LLM Provider — 聚合多个 AI 模型的 API"""

from __future__ import annotations

from typing import Any

from core.llm_providers.base import ConfiguredLLMClient
from core.llm_providers.config import LLMProviderConfig


class OpenRouterClient(ConfiguredLLMClient):
    """OpenRouter API 客户端

    通过 OpenRouter (https://openrouter.ai) 调用 LLM。
    API 兼容 OpenAI 格式，支持多个模型。

    环境变量:
        OPENROUTER_API_KEY — API 密钥（必需）
    """

    DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

    def __init__(
        self, api_key: str | None = None, model: str | None = None, **kwargs: Any
    ):
        """初始化 OpenRouter 客户端

        Args:
            api_key: API 密钥（默认从 OPENROUTER_API_KEY 环境变量读取）
            model: 模型名称（默认 anthropic/claude-3.5-sonnet）
        """
        headers = {
            "HTTP-Referer": "https://github.com/KarasawaYikiho/SuperMedicine",
            "X-Title": "SuperMedicine",
            **kwargs.pop("headers", {}),
        }
        config = LLMProviderConfig.from_mapping(
            "openrouter",
            kwargs,
            api_key=api_key,
            model=self.DEFAULT_MODEL if model is None else model,
            headers=headers,
            api_format="openai",
        )
        super().__init__(config)

    def _request(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """Backward-compatible request hook used by existing tests/extensions."""
        return self.chat(messages, **kwargs)

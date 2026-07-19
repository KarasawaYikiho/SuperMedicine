"""LLM provider integrations."""

from __future__ import annotations

import sys

from core.llm_providers import base as _base
from core.llm_providers.base import (
    AnthropicClient,
    ConfiguredLLMClient,
    OpenAIClient,
    OpenRouterClient,
)
from core.llm_providers.config import LLMProviderConfig

sys.modules.setdefault("core.llm_providers.openrouter", _base)

__all__ = [
    "AnthropicClient",
    "ConfiguredLLMClient",
    "LLMProviderConfig",
    "OpenAIClient",
    "OpenRouterClient",
]

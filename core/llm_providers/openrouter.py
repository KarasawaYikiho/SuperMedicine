"""OpenRouter LLM Provider — 聚合多个 AI 模型的 API"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Any

from core.llm_client import LLMClient


class OpenRouterClient(LLMClient):
    """OpenRouter API 客户端

    通过 OpenRouter (https://openrouter.ai) 调用 LLM。
    API 兼容 OpenAI 格式，支持多个模型。

    环境变量:
        OPENROUTER_API_KEY — API 密钥（必需）
    """

    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

    def __init__(self, api_key: str | None = None, model: str | None = None, **kwargs: Any):
        """初始化 OpenRouter 客户端

        Args:
            api_key: API 密钥（默认从 OPENROUTER_API_KEY 环境变量读取）
            model: 模型名称（默认 anthropic/claude-3.5-sonnet）
        """
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self._model = model or self.DEFAULT_MODEL
        self._extra_headers = kwargs.pop("headers", {})

    @property
    def model(self) -> str:
        return self._model

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """发送多轮对话"""
        return self._request(messages, **kwargs)

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """单轮文本补全"""
        messages = [{"role": "user", "content": prompt}]
        return self._request(messages, **kwargs)

    def _request(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """发送 HTTP 请求到 OpenRouter API"""
        if not self._api_key:
            return {
                "content": "",
                "model": self._model,
                "error": "OPENROUTER_API_KEY not set",
                "usage": {},
            }

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/KarasawaYikiho/SuperMedicine",
            "X-Title": "SuperMedicine",
            **self._extra_headers,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(self.API_URL, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                response = json.loads(resp.read().decode("utf-8"))

            choice = response.get("choices", [{}])[0]
            return {
                "content": choice.get("message", {}).get("content", ""),
                "model": response.get("model", self._model),
                "usage": response.get("usage", {}),
            }
        except urllib.error.HTTPError as e:
            return {
                "content": "",
                "model": self._model,
                "error": f"HTTP {e.code}: {e.reason}",
                "usage": {},
            }
        except Exception as e:
            return {
                "content": "",
                "model": self._model,
                "error": str(e),
                "usage": {},
            }

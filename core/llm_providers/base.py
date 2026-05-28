"""HTTP clients for unified LLM provider configs."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Iterable

from core.llm_client import LLMClient
from core.llm_providers.config import LLMProviderConfig, sanitize_error_message


class ConfiguredLLMClient(LLMClient):
    """LLM client driven by a normalized provider configuration."""

    def __init__(self, config: LLMProviderConfig):
        self.config = config

    @property
    def model(self) -> str:
        return self.config.model

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        validation_error = self.config.validation_error()
        if validation_error:
            return validation_error

        api_format = kwargs.pop("api_format", self.config.api_format).lower()
        if api_format == "anthropic":
            return self._anthropic_request(messages, **kwargs)
        if api_format in {"openai_responses", "responses"}:
            return self._openai_responses_request(messages, **kwargs)
        return self._openai_request(messages, **kwargs)

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def _openai_request(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }
        self._copy_options(
            payload,
            kwargs,
            allowed=("temperature", "max_tokens", "top_p", "frequency_penalty", "presence_penalty", "stop"),
            defaults={"temperature": 0.7, "max_tokens": 1024},
        )
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **self.config.headers,
        }
        response = self._post_json("/chat/completions", payload, headers)
        if "error" in response:
            return response
        return self._parse_openai_chat_response(response)

    def _openai_responses_request(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "input": self._openai_responses_input(messages),
        }
        system = self._combined_system_prompt(messages)
        if system:
            payload["instructions"] = system
        self._copy_options(
            payload,
            kwargs,
            allowed=("temperature", "max_output_tokens", "top_p", "truncation"),
            defaults={"temperature": 0.7, "max_output_tokens": kwargs.get("max_tokens", 1024)},
        )
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            **self.config.headers,
        }
        response = self._post_json("/responses", payload, headers)
        if "error" in response:
            return response
        return self._parse_openai_responses_response(response)

    def _parse_openai_chat_response(self, response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices") or [{}]
        choice = choices[0] if isinstance(choices, list) and choices else {}
        message = choice.get("message", {}) if isinstance(choice, dict) else {}
        return {
            "content": self._content_to_text(message.get("content", "")),
            "model": response.get("model", self.config.model),
            "usage": response.get("usage", {}),
        }

    def _parse_openai_responses_response(self, response: dict[str, Any]) -> dict[str, Any]:
        content = response.get("output_text")
        if not content:
            parts: list[str] = []
            for item in response.get("output", []) or []:
                if not isinstance(item, dict):
                    continue
                for block in item.get("content", []) or []:
                    if isinstance(block, dict):
                        parts.append(str(block.get("text") or block.get("content") or ""))
            content = "".join(parts)
        return {
            "content": str(content or ""),
            "model": response.get("model", self.config.model),
            "usage": response.get("usage", {}),
        }

    def _anthropic_request(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "messages": self._anthropic_messages(messages),
        }
        system = self._combined_system_prompt(messages)
        if system:
            payload["system"] = system
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        for option in ("top_p", "top_k", "stop_sequences"):
            if option in kwargs and kwargs[option] is not None:
                payload[option] = kwargs[option]
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            **self.config.headers,
        }
        response = self._post_json("/messages", payload, headers)
        if "error" in response:
            return response
        content = self._content_to_text(response.get("content", []))
        return {
            "content": content,
            "model": response.get("model", self.config.model),
            "usage": response.get("usage", {}),
        }

    def _post_json(self, path: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        url = self.config.base_url.rstrip("/") + path
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return self._http_error(exc)
        except Exception as exc:
            message = sanitize_error_message(str(exc), [self.config.api_key])
            return self.config.error("request_error", message)

    def _http_error(self, exc: urllib.error.HTTPError) -> dict[str, Any]:
        details = ""
        try:
            raw = exc.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            details = self._extract_error_message(parsed)
        except Exception:
            details = ""
        reason = details or getattr(exc, "reason", "") or "HTTP error"
        message = sanitize_error_message(f"HTTP {exc.code}: {reason}", [self.config.api_key])
        return self.config.error("http_error", message)

    @staticmethod
    def _copy_options(
        payload: dict[str, Any],
        kwargs: dict[str, Any],
        *,
        allowed: Iterable[str],
        defaults: dict[str, Any] | None = None,
    ) -> None:
        for key, value in (defaults or {}).items():
            if value is not None:
                payload[key] = value
        for key in allowed:
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    parts.append(str(block.get("text") or block.get("content") or ""))
            return "".join(parts)
        return str(content or "")

    @staticmethod
    def _combined_system_prompt(messages: list[dict[str, str]]) -> str:
        return "\n\n".join(str(message.get("content", "")) for message in messages if message.get("role") == "system")

    @staticmethod
    def _anthropic_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        return [message for message in messages if message.get("role") != "system"]

    @staticmethod
    def _openai_responses_input(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        return [message for message in messages if message.get("role") != "system"]

    @staticmethod
    def _extract_error_message(parsed: Any) -> str:
        if isinstance(parsed, dict):
            error = parsed.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("error") or error.get("type") or "")
            if isinstance(error, str):
                return error
            return str(parsed.get("message") or parsed.get("detail") or "")
        return ""


class OpenAIClient(ConfiguredLLMClient):
    """OpenAI-format API client."""

    def __init__(self, **kwargs: Any):
        if "api_format" not in kwargs and "format" not in kwargs:
            kwargs["api_format"] = "openai"
        super().__init__(LLMProviderConfig.from_mapping("openai", kwargs))


class AnthropicClient(ConfiguredLLMClient):
    """Anthropic Messages API client."""

    def __init__(self, **kwargs: Any):
        if "api_format" not in kwargs and "format" not in kwargs:
            kwargs["api_format"] = "anthropic"
        super().__init__(LLMProviderConfig.from_mapping("anthropic", kwargs))

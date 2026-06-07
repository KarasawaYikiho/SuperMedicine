"""HTTP clients for unified LLM provider configs."""

from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable

from core.llm_client import LLMClient
from core.llm_providers.config import (
    LLMProviderConfig,
    sanitize_error_message,
    sanitized_headers,
)
from core.redaction import redact_sensitive


logger = logging.getLogger(__name__)

MAX_PROVIDER_RESPONSE_BYTES = 10 * 1024 * 1024


class UnsafeProviderURL(ValueError):
    """Raised when a configured provider URL is unsafe before network access."""


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
            logger.warning(
                "LLM provider configuration rejected before request: provider=%s code=%s",
                self.config.provider,
                validation_error.get("error", {}).get("code"),
            )
            return validation_error

        if not self._valid_messages(messages):
            logger.warning(
                "LLM request rejected because messages are empty or malformed: provider=%s",
                self.config.provider,
            )
            return self.config.error(
                "invalid_request",
                "LLM request requires at least one non-empty message with role and content",
            )

        api_format = kwargs.pop("api_format", self.config.api_format).lower()
        if api_format == "anthropic":
            return self._anthropic_request(messages, **kwargs)
        if api_format in {"openai_responses", "responses"}:
            return self._openai_responses_request(messages, **kwargs)
        return self._openai_request(messages, **kwargs)

    def complete(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def _openai_request(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }
        self._copy_options(
            payload,
            kwargs,
            allowed=(
                "temperature",
                "max_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
                "stop",
            ),
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

    def _openai_responses_request(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
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
            defaults={
                "temperature": 0.7,
                "max_output_tokens": kwargs.get("max_tokens", 1024),
            },
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
        content = (
            self._content_to_text(message.get("content", ""))
            if isinstance(message, dict)
            else ""
        )
        if not content:
            return self._invalid_response(
                "OpenAI chat response did not contain message.content", response
            )
        return {
            "content": content,
            "model": response.get("model", self.config.model),
            "usage": response.get("usage", {}),
        }

    def _parse_openai_responses_response(
        self, response: dict[str, Any]
    ) -> dict[str, Any]:
        content = response.get("output_text")
        if not content:
            parts: list[str] = []
            for item in response.get("output", []) or []:
                if not isinstance(item, dict):
                    continue
                for block in item.get("content", []) or []:
                    if isinstance(block, dict):
                        parts.append(
                            str(block.get("text") or block.get("content") or "")
                        )
            content = "".join(parts)
        if not content:
            return self._invalid_response(
                "OpenAI responses response did not contain output text", response
            )
        return {
            "content": str(content or ""),
            "model": response.get("model", self.config.model),
            "usage": response.get("usage", {}),
        }

    def _anthropic_request(
        self, messages: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
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
        if not content:
            return self._invalid_response(
                "Anthropic response did not contain text content", response
            )
        return {
            "content": content,
            "model": response.get("model", self.config.model),
            "usage": response.get("usage", {}),
        }

    def _post_json(
        self, path: str, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        try:
            url = self._provider_url(path)
        except UnsafeProviderURL as exc:
            message = sanitize_error_message(str(exc), [self.config.api_key])
            logger.error(
                "LLM provider URL rejected: provider=%s reason=%s",
                self.config.provider,
                message,
            )
            return self.config.error("invalid_base_url", message)
        safe_url = redact_sensitive(url)
        logger.info(
            "Sending LLM request: provider=%s format=%s model=%s url=%s timeout=%s headers=%s message_count=%s",
            self.config.provider,
            self.config.api_format,
            self.config.model,
            safe_url,
            self.config.timeout,
            sanitized_headers(headers),
            len(payload.get("messages") or payload.get("input") or []),
        )
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                raw_bytes = self._read_limited_response(resp)
                if raw_bytes is None:
                    return self.config.error(
                        "invalid_response",
                        "LLM provider response exceeded maximum supported size",
                    )
                raw = raw_bytes.decode("utf-8")
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    logger.error(
                        "LLM provider returned non-object JSON: provider=%s",
                        self.config.provider,
                    )
                    return self.config.error(
                        "invalid_response",
                        "LLM provider returned non-object JSON response",
                    )
                logger.info(
                    "LLM request completed: provider=%s model=%s",
                    self.config.provider,
                    parsed.get("model", self.config.model),
                )
                return parsed
        except urllib.error.HTTPError as exc:
            return self._http_error(exc)
        except socket.timeout as exc:
            logger.error(
                "LLM request timed out: provider=%s url=%s timeout=%s",
                self.config.provider,
                safe_url,
                self.config.timeout,
            )
            return self.config.error(
                "timeout",
                f"LLM provider request timed out after {self.config.timeout} seconds: {exc}",
            )
        except urllib.error.URLError as exc:
            reason = sanitize_error_message(
                str(getattr(exc, "reason", exc)), [self.config.api_key]
            )
            logger.error(
                "LLM network failure: provider=%s url=%s error=%s",
                self.config.provider,
                safe_url,
                reason,
            )
            return self.config.error(
                "network_error", f"LLM provider network failure: {reason}"
            )
        except json.JSONDecodeError as exc:
            logger.error(
                "LLM provider returned invalid JSON: provider=%s url=%s error=%s",
                self.config.provider,
                safe_url,
                exc,
            )
            return self.config.error(
                "invalid_response", f"LLM provider returned invalid JSON: {exc}"
            )
        except Exception as exc:
            message = sanitize_error_message(str(exc), [self.config.api_key])
            logger.error(
                "LLM request failed: provider=%s url=%s error=%s",
                self.config.provider,
                safe_url,
                message,
            )
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
        message = sanitize_error_message(
            f"HTTP {exc.code}: {reason}", [self.config.api_key]
        )
        code = "authentication_failed" if exc.code in (401, 403) else "http_error"
        logger.error(
            "LLM HTTP failure: provider=%s status=%s error=%s",
            self.config.provider,
            exc.code,
            message,
        )
        return self.config.error(code, message)

    def _provider_url(self, path: str) -> str:
        if not path.startswith("/") or any(ord(character) < 32 for character in path):
            raise UnsafeProviderURL("LLM provider request path is invalid")
        base_url = self.config.base_url.strip()
        if any(ord(character) < 32 for character in base_url):
            raise UnsafeProviderURL("LLM provider base_url contains unsafe characters")
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise UnsafeProviderURL("LLM provider base_url must use http or https")
        if not parsed.hostname:
            raise UnsafeProviderURL("LLM provider base_url must include a host")
        if parsed.username or parsed.password:
            raise UnsafeProviderURL(
                "LLM provider base_url must not include credentials"
            )
        if parsed.fragment:
            raise UnsafeProviderURL("LLM provider base_url must not include a fragment")
        return urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

    def _read_limited_response(self, response: Any) -> bytes | None:
        try:
            raw = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
        except TypeError:
            raw = response.read()
        if len(raw) > MAX_PROVIDER_RESPONSE_BYTES:
            logger.error(
                "LLM provider response exceeded size limit: provider=%s limit=%s",
                self.config.provider,
                MAX_PROVIDER_RESPONSE_BYTES,
            )
            return None
        return raw

    def _invalid_response(
        self, message: str, response: dict[str, Any]
    ) -> dict[str, Any]:
        logger.error(
            "LLM response parsing failed: provider=%s model=%s reason=%s keys=%s",
            self.config.provider,
            self.config.model,
            message,
            sorted(str(key) for key in response.keys()),
        )
        return self.config.error("invalid_response", message)

    @staticmethod
    def _valid_messages(messages: list[dict[str, str]]) -> bool:
        if not isinstance(messages, list) or not messages:
            return False
        for message in messages:
            if not isinstance(message, dict):
                return False
            if not str(message.get("role") or "").strip():
                return False
            if str(message.get("content") or "").strip():
                return True
        return False

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
        return "\n\n".join(
            str(message.get("content", ""))
            for message in messages
            if message.get("role") == "system"
        )

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
                return str(
                    error.get("message")
                    or error.get("error")
                    or error.get("type")
                    or ""
                )
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

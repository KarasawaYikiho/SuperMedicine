"""RAG 检索接口定义。

The RAG contract intentionally supports both in-process/local indexes and
external database/vector-index providers.  Implementations should keep query
results stable and expose connection/configuration failures as structured data
instead of raising opaque exceptions to callers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.redaction import redact_sensitive


@dataclass(frozen=True)
class RAGProviderConfig:
    """Configuration for local, mock, or external RAG providers.

    Secrets must be referenced by environment variable name via ``api_key_env``
    and read by the concrete provider at runtime.  They must not be hardcoded in
    source files or configuration committed to the repository.
    """

    provider_type: str = "local"
    endpoint: str | None = None
    index_name: str | None = None
    namespace: str | None = None
    api_key_env: str | None = None
    timeout_seconds: float = 10.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def resource_metadata(self) -> dict[str, Any]:
        """Return safe resource metadata without dereferencing secret values."""
        return redact_sensitive(
            {
                "provider_type": self.provider_type,
                "endpoint": self.endpoint,
                "index_name": self.index_name,
                "namespace": self.namespace,
                "api_key_env": self.api_key_env,
                "timeout_seconds": self.timeout_seconds,
                **self.metadata,
            }
        )


class RAGProviderError(Exception):
    """Base class for structured RAG provider errors."""

    code = "rag_error"

    def __init__(self, message: str, *, retryable: bool = False, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": redact_sensitive(self.message),
            "retryable": self.retryable,
            "details": redact_sensitive(self.details),
        }


class RAGConfigurationError(RAGProviderError):
    """Provider configuration is incomplete or invalid."""

    code = "configuration_error"


class RAGConnectionError(RAGProviderError):
    """Provider cannot connect to the configured service/index."""

    code = "connection_error"


class RAGQueryTimeoutError(RAGProviderError):
    """Provider query timed out."""

    code = "query_timeout"


class RAGResourceError(RAGProviderError):
    """Provider resource policy, quota, or allocation failed."""

    code = "resource_error"


def make_rag_result(
    items: list[dict[str, Any]] | None = None,
    *,
    provider: str,
    status: str = "success",
    errors: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a stable RAG query result with backward-compatible aliases.

    Canonical result items should include ``id``, ``title`` or ``source``,
    ``score``, and ``snippet`` where those fields are available.  Legacy callers
    can continue to consume ``results``, ``relevance_scores``, and
    ``source_metadata``.
    """

    normalized_items = redact_sensitive(items or [])
    safe_metadata = redact_sensitive(metadata or {})
    return {
        "status": status,
        "provider": provider,
        "items": normalized_items,
        "results": [item.get("snippet", "") for item in normalized_items],
        "relevance_scores": [item.get("score", 0.0) for item in normalized_items],
        "source_metadata": [
            {
                key: value
                for key, value in item.items()
                if key not in {"snippet", "score"}
            }
            for item in normalized_items
        ],
        "errors": redact_sensitive(errors or []),
        "metadata": safe_metadata,
    }


class RAGProvider:
    """RAG Provider 接口"""

    provider_name = "abstract"

    def connect(self) -> dict[str, Any]:
        """Connect to the backing store if needed and return status metadata."""
        return {"status": "connected", "provider": self.provider_name}

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        """检索相关文献/向量记录，返回稳定结构化结果。"""
        raise NotImplementedError

    def store_context(self, key: str, data: Any) -> None:
        """存储上下文"""
        raise NotImplementedError

    def retrieve_context(self, key: str) -> Any | None:
        """获取上下文"""
        raise NotImplementedError


class EmptyRAGProvider(RAGProvider):
    """空 RAG Provider — 内存存储上下文，无实际检索"""

    provider_name = "empty"

    def __init__(self):
        self._context: dict[str, Any] = {}

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        return make_rag_result([], provider=self.provider_name, metadata={"query": query_text, "top_k": top_k})

    def store_context(self, key: str, data: Any) -> None:
        self._context[key] = data

    def retrieve_context(self, key: str) -> Any | None:
        return self._context.get(key)


__all__ = [
    "RAGProviderConfig",
    "RAGProviderError",
    "RAGConfigurationError",
    "RAGConnectionError",
    "RAGQueryTimeoutError",
    "RAGResourceError",
    "RAGProvider",
    "EmptyRAGProvider",
    "make_rag_result",
]

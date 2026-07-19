"""Shared RAG contracts plus local and deterministic vector providers."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
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

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ):
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
    _context: dict[str, Any]

    def connect(self) -> dict[str, Any]:
        """Connect to the backing store if needed and return status metadata."""
        return {"status": "connected", "provider": self.provider_name}

    def store_context(self, key: str, data: Any) -> None:
        """Store transient context for providers without persistent context storage."""
        context = getattr(self, "_context", None)
        if context is None:
            context = self._context = {}
        context[key] = data

    def retrieve_context(self, key: str) -> Any | None:
        """Retrieve transient context for providers without persistent storage."""
        return getattr(self, "_context", {}).get(key)


class EmptyRAGProvider(RAGProvider):
    """空 RAG Provider — 内存存储上下文，无实际检索"""

    provider_name = "empty"

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        return make_rag_result(
            [],
            provider=self.provider_name,
            metadata={"query": query_text, "top_k": top_k},
        )


class LocalRAGProvider(RAGProvider):
    """基于本地文件的 RAG Provider"""

    provider_name = "local-bm25"
    _SAFE_CONTEXT_KEY = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(self, storage_dir: Path):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._documents: list[dict[str, Any]] = []
        self._context_dir = self._storage_dir / "context"
        self._context_dir.mkdir(exist_ok=True)
        self._index_file = self._storage_dir / "documents.json"
        self._load_index()

    def _load_index(self) -> None:
        if self._index_file.exists():
            with open(self._index_file, encoding="utf-8") as f:
                self._documents = json.load(f)

    def _save_index(self) -> None:
        with NamedTemporaryFile(
            "w", encoding="utf-8", dir=self._storage_dir, delete=False
        ) as temporary:
            json.dump(self._documents, temporary, ensure_ascii=False, indent=2)
            temporary.flush()
            temporary_path = Path(temporary.name)
        temporary_path.replace(self._index_file)

    def add_document(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        content_hash = sha256(text.encode("utf-8")).hexdigest()
        if any(
            document.get("content_hash") == content_hash
            or (
                "content_hash" not in document
                and document.get("text") == text
            )
            for document in self._documents
        ):
            return
        """添加文档到索引"""
        metadata = dict(metadata or {})
        document_id = str(metadata.get("document_id") or metadata.get("id") or content_hash)
        metadata.setdefault("document_id", document_id)
        metadata.setdefault("chunk_id", f"{document_id}:0")
        metadata.setdefault("source_type", "local")
        metadata.setdefault("source_path", "")
        metadata.setdefault("page", None)
        metadata.setdefault("section", "")
        metadata.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        doc = {
            "id": len(self._documents),
            "text": text,
            "metadata": metadata,
            "tokens": self._tokenize(text),
            "content_hash": content_hash,
        }
        self._documents.append(doc)
        self._save_index()

    def remove_document(self, document_id: str) -> int:
        """Remove every chunk belonging to one logical document."""
        before = len(self._documents)
        self._documents = [
            document
            for document in self._documents
            if str(document.get("metadata", {}).get("document_id")) != document_id
        ]
        removed = before - len(self._documents)
        if removed:
            self._save_index()
        return removed

    def replace_document(
        self,
        document_id: str,
        chunks: list[tuple[str, dict[str, Any]]],
    ) -> None:
        """Atomically replace all indexed chunks for a logical document."""
        original = list(self._documents)
        self._documents = [
            document
            for document in self._documents
            if str(document.get("metadata", {}).get("document_id")) != document_id
        ]
        try:
            for text, metadata in chunks:
                values = dict(metadata)
                values["document_id"] = document_id
                content_hash = sha256(text.encode("utf-8")).hexdigest()
                values.setdefault("chunk_id", f"{document_id}:{len(self._documents)}")
                values.setdefault("source_type", "local")
                values.setdefault("source_path", "")
                values.setdefault("page", None)
                values.setdefault("section", "")
                values.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                self._documents.append(
                    {
                        "id": len(self._documents),
                        "text": text,
                        "metadata": values,
                        "tokens": self._tokenize(text),
                        "content_hash": content_hash,
                    }
                )
            self._save_index()
        except Exception:
            self._documents = original
            raise

    def query(
        self, query: str, top_k: int = 5, scope: str = "literature"
    ) -> dict[str, Any]:
        """查询"""
        if not self._documents:
            return make_rag_result(
                [],
                provider=self.provider_name,
                metadata={
                    "query": query,
                    "top_k": top_k,
                    "scope": scope,
                    "resource": {"kind": "local_index"},
                },
            )

        query_tokens = self._tokenize(query)

        # BM25 lexical ranking (dependency-free).
        scores = []
        average_length = sum(len(doc["tokens"]) for doc in self._documents) / max(
            len(self._documents), 1
        )
        for doc in self._documents:
            score = self._bm25_score(query_tokens, doc["tokens"], average_length)
            scores.append((score, doc))

        # 按相似度排序
        scores.sort(key=lambda x: x[0], reverse=True)

        top_results = [item for item in scores if item[0] > 0][:top_k]

        items = []
        for score, doc in top_results:
            metadata = doc.get("metadata", {})
            items.append(
                {
                    "id": str(metadata.get("id", doc.get("id", ""))),
                    "title": metadata.get("title")
                    or metadata.get("source")
                    or f"local:{doc.get('id', '')}",
                    "source": metadata.get("source", "local"),
                    "score": round(score, 4),
                    "snippet": doc["text"],
                    "document_id": str(metadata.get("document_id", "")),
                    "chunk_id": str(metadata.get("chunk_id", "")),
                    "content_hash": str(doc.get("content_hash", "")),
                    "source_type": metadata.get("source_type", "local"),
                    "source_path": metadata.get("source_path", ""),
                    "page": metadata.get("page"),
                    "section": metadata.get("section", ""),
                    "created_at": metadata.get("created_at", ""),
                    "metadata": metadata,
                }
            )

        return make_rag_result(
            items,
            provider=self.provider_name,
            metadata={
                "query": query,
                "top_k": top_k,
                "scope": scope,
                "resource": {
                    "kind": "local_index",
                    "document_count": len(self._documents),
                },
            },
        )

    def store_context(self, key: str, value: Any) -> None:
        """存储项目上下文"""
        context_file = self._context_file_for_key(key)
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)

    def retrieve_context(self, key: str) -> Any | None:
        """检索项目上下文"""
        context_file = self._context_file_for_key(key)
        if not context_file.exists():
            return None
        with open(context_file, encoding="utf-8") as f:
            return json.load(f)

    def _context_file_for_key(self, key: str) -> Path:
        """Return a context JSON path for a restricted safe key.

        Context keys become filenames under ``self._context_dir``.  Restricting
        them to a conservative filename subset preserves existing safe keys such
        as ``project_1`` while preventing path traversal, absolute paths, drive
        prefixes, and separator tricks from escaping the context directory.
        """
        if not isinstance(key, str) or not key:
            raise ValueError("context key must be a non-empty string")
        if key in {".", ".."} or not self._SAFE_CONTEXT_KEY.fullmatch(key):
            raise ValueError(
                "context key must contain only letters, numbers, underscore, dash, or dot"
            )

        context_root = self._context_dir.resolve()
        context_file = (self._context_dir / f"{key}.json").resolve()
        if context_file.parent != context_root:
            raise ValueError(
                "context key resolves outside the local RAG context directory"
            )
        return context_file

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize Latin medical terms and CJK text without character-only noise."""
        tokens: list[str] = []
        for part in re.findall(r"[a-z0-9][a-z0-9._-]*|[\u3400-\u9fff]+", text.lower()):
            if re.fullmatch(r"[\u3400-\u9fff]+", part):
                tokens.extend(
                    part[index : index + 2]
                    for index in range(max(len(part) - 1, 1))
                )
            else:
                tokens.append(part)
        return tokens

    def _bm25_score(
        self, query_tokens: list[str], document_tokens: list[str], average_length: float
    ) -> float:
        """Return a BM25 score using corpus document frequencies."""
        if not query_tokens or not document_tokens:
            return 0.0
        frequencies = Counter(document_tokens)
        total_documents = len(self._documents)
        score = 0.0
        k1 = 1.5
        b = 0.75
        for token in set(query_tokens):
            document_frequency = sum(
                token in document.get("tokens", []) for document in self._documents
            )
            inverse_frequency = math.log(
                1 + (total_documents - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            frequency = frequencies.get(token, 0)
            denominator = frequency + k1 * (
                1 - b + b * len(document_tokens) / max(average_length, 1.0)
            )
            score += inverse_frequency * (frequency * (k1 + 1)) / denominator
        return score


class MockExternalVectorStoreProvider(RAGProvider):
    """Contract backend that behaves like an external vector index without I/O.

    This provider is intentionally deterministic and dependency-free.  It lets
    callers validate external database/vector-index configuration, connection
    state, timeout/config failures, and stable query result shape without
    requiring a live external service in development or tests.
    """

    provider_name = "mock-external-vector-store"

    def __init__(
        self, config: RAGProviderConfig, records: list[dict[str, Any]] | None = None
    ):
        self.config = config
        self._records = records or []
        self._connected = False

    def connect(self) -> dict[str, Any]:
        try:
            self._validate_config()
        except RAGConfigurationError as exc:
            return {
                "status": "error",
                "provider": self.provider_name,
                "errors": [exc.to_dict()],
                "metadata": {"resource": self.config.resource_metadata()},
            }

        if self.config.endpoint == "mock://connection-error":
            connection_error = RAGConnectionError(
                "Mock vector store connection failed.",
                retryable=True,
                details={
                    "endpoint": self.config.endpoint,
                    "timeout_seconds": self.config.timeout_seconds,
                },
            )
            return {
                "status": "error",
                "provider": self.provider_name,
                "errors": [connection_error.to_dict()],
                "metadata": {"resource": self.config.resource_metadata()},
            }

        if self.config.timeout_seconds > 120:
            resource_error = RAGResourceError(
                "Mock vector store timeout exceeds resource policy.",
                retryable=False,
                details={
                    "timeout_seconds": self.config.timeout_seconds,
                    "max_timeout_seconds": 120,
                },
            )
            return {
                "status": "error",
                "provider": self.provider_name,
                "errors": [resource_error.to_dict()],
                "metadata": {"resource": self.config.resource_metadata()},
            }

        self._connected = True
        return {
            "status": "connected",
            "provider": self.provider_name,
            "metadata": {
                "resource": self.config.resource_metadata(),
                "security": {
                    "external_resource": True,
                    "secret_source": "env" if self.config.api_key_env else "none",
                },
            },
        }

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        connection = self.connect() if not self._connected else {"status": "connected"}
        if connection.get("status") != "connected":
            raw_errors = connection.get("errors")
            errors: list[dict[str, Any]] | None = (
                raw_errors if isinstance(raw_errors, list) else None
            )
            return make_rag_result(
                [],
                provider=self.provider_name,
                status="error",
                errors=errors,
                metadata={
                    "query": query_text,
                    "top_k": top_k,
                    "resource": self.config.resource_metadata(),
                },
            )

        if self.config.timeout_seconds <= 0:
            exc = RAGQueryTimeoutError(
                "Mock vector store query timed out.",
                retryable=True,
                details={"timeout_seconds": self.config.timeout_seconds},
            )
            return make_rag_result(
                [],
                provider=self.provider_name,
                status="error",
                errors=[exc.to_dict()],
                metadata={
                    "query": query_text,
                    "top_k": top_k,
                    "resource": self.config.resource_metadata(),
                },
            )

        tokens = set(self._tokenize(query_text))
        ranked: list[dict[str, Any]] = []
        for record in self._records:
            text = str(record.get("text") or record.get("snippet") or "")
            record_tokens = set(self._tokenize(text))
            score = (
                len(tokens & record_tokens) / len(tokens | record_tokens)
                if tokens and record_tokens
                else 0.0
            )
            ranked.append(
                {
                    "id": str(record.get("id", "")),
                    "title": record.get("title")
                    or record.get("source")
                    or str(record.get("id", "")),
                    "source": record.get(
                        "source", self.config.index_name or "external-vector-index"
                    ),
                    "score": round(float(record.get("score", score)), 4),
                    "snippet": text,
                    "metadata": record.get("metadata", {}),
                }
            )

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return make_rag_result(
            ranked[:top_k],
            provider=self.provider_name,
            metadata={
                "query": query_text,
                "top_k": top_k,
                "resource": self.config.resource_metadata(),
                "security": {
                    "external_resource": True,
                    "secret_source": "env" if self.config.api_key_env else "none",
                },
            },
        )

    def _validate_config(self) -> None:
        missing = []
        if not self.config.endpoint:
            missing.append("endpoint")
        if not self.config.index_name:
            missing.append("index_name")
        if missing:
            raise RAGConfigurationError(
                "External vector store configuration is incomplete.",
                details={"missing": missing},
            )

    def _tokenize(self, text: str) -> list[str]:
        return [
            token
            for token in text.lower().replace("/", " ").replace(",", " ").split()
            if token
        ]


__all__ = [
    "RAGProviderConfig",
    "RAGProviderError",
    "RAGConfigurationError",
    "RAGConnectionError",
    "RAGQueryTimeoutError",
    "RAGResourceError",
    "RAGProvider",
    "EmptyRAGProvider",
    "LocalRAGProvider",
    "MockExternalVectorStoreProvider",
    "make_rag_result",
]

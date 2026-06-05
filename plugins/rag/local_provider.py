"""RAG 本地实现 — 基于 TF-IDF 的检索和外部向量库契约后端。"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .interface import (
    RAGConfigurationError,
    RAGConnectionError,
    RAGProvider,
    RAGProviderConfig,
    RAGQueryTimeoutError,
    RAGResourceError,
    make_rag_result,
)


class LocalRAGProvider(RAGProvider):
    """基于本地文件的 RAG Provider"""

    provider_name = "local-tfidf"
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
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(self._documents, f, ensure_ascii=False, indent=2)

    def add_document(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        """添加文档到索引"""
        doc = {
            "id": len(self._documents),
            "text": text,
            "metadata": metadata or {},
            "tokens": self._tokenize(text),
        }
        self._documents.append(doc)
        self._save_index()

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

        # 计算 TF-IDF 相似度
        scores = []
        for doc in self._documents:
            score = self._cosine_similarity(query_tokens, doc["tokens"])
            scores.append((score, doc))

        # 按相似度排序
        scores.sort(key=lambda x: x[0], reverse=True)

        top_results = scores[:top_k]

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
        """简单分词，支持中英文混合"""
        tokens: list[str] = []
        for word in text.lower().split():
            has_cjk = any(ord(c) > 0x2E80 for c in word)
            if has_cjk:
                # 包含 CJK 字符，逐字拆分
                for c in word:
                    tokens.append(c)
            else:
                tokens.append(word)
        return tokens

    def _cosine_similarity(self, tokens1: list[str], tokens2: list[str]) -> float:
        """计算余弦相似度"""
        counter1 = Counter(tokens1)
        counter2 = Counter(tokens2)

        # 所有词
        all_words = set(counter1.keys()) | set(counter2.keys())

        # 计算点积
        dot_product = sum(counter1.get(w, 0) * counter2.get(w, 0) for w in all_words)

        # 计算范数
        norm1 = math.sqrt(sum(v**2 for v in counter1.values()))
        norm2 = math.sqrt(sum(v**2 for v in counter2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot_product / (norm1 * norm2)


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
        self._context: dict[str, Any] = {}
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

    def store_context(self, key: str, data: Any) -> None:
        self._context[key] = data

    def retrieve_context(self, key: str) -> Any | None:
        return self._context.get(key)

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

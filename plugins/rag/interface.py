"""RAG 插件接口 — 空实现"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class RAGProvider(ABC):
    @abstractmethod
    def query(self, query: str, scope: str = "literature") -> dict[str, Any]: ...
    @abstractmethod
    def store_context(self, key: str, value: Any) -> None: ...
    @abstractmethod
    def retrieve_context(self, key: str) -> Any | None: ...

class EmptyRAGProvider(RAGProvider):
    def query(self, query: str, scope: str = "literature") -> dict[str, Any]:
        return {"results": [], "warning": "RAG provider not configured"}
    def store_context(self, key: str, value: Any) -> None: pass
    def retrieve_context(self, key: str) -> Any | None: return None

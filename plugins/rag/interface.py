"""RAG 检索接口定义"""
from __future__ import annotations

from typing import Any


class RAGProvider:
    """RAG Provider 接口"""

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        """检索相关文献"""
        raise NotImplementedError

    def store_context(self, key: str, data: Any) -> None:
        """存储上下文"""
        raise NotImplementedError

    def retrieve_context(self, key: str) -> Any | None:
        """获取上下文"""
        raise NotImplementedError


class EmptyRAGProvider(RAGProvider):
    """空 RAG Provider — 内存存储上下文，无实际检索"""

    def __init__(self):
        self._context: dict[str, Any] = {}

    def query(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        return []

    def store_context(self, key: str, data: Any) -> None:
        self._context[key] = data

    def retrieve_context(self, key: str) -> Any | None:
        return self._context.get(key)


from .local_provider import LocalRAGProvider

__all__ = ["RAGProvider", "EmptyRAGProvider", "LocalRAGProvider"]

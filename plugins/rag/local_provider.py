"""RAG 本地实现 — 基于 TF-IDF 的检索"""
from __future__ import annotations

import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any

from .interface import RAGProvider


class LocalRAGProvider(RAGProvider):
    """基于本地文件的 RAG Provider"""

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

    def query(self, query: str, scope: str = "literature") -> dict[str, Any]:
        """查询"""
        if not self._documents:
            return {"results": [], "relevance_scores": [], "source_metadata": []}

        query_tokens = self._tokenize(query)

        # 计算 TF-IDF 相似度
        scores = []
        for doc in self._documents:
            score = self._cosine_similarity(query_tokens, doc["tokens"])
            scores.append((score, doc))

        # 按相似度排序
        scores.sort(key=lambda x: x[0], reverse=True)

        # 返回前 5 个结果
        top_results = scores[:5]

        return {
            "results": [doc["text"] for _, doc in top_results],
            "relevance_scores": [round(score, 4) for score, _ in top_results],
            "source_metadata": [doc["metadata"] for _, doc in top_results],
        }

    def store_context(self, key: str, value: Any) -> None:
        """存储项目上下文"""
        context_file = self._context_dir / f"{key}.json"
        with open(context_file, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)

    def retrieve_context(self, key: str) -> Any | None:
        """检索项目上下文"""
        context_file = self._context_dir / f"{key}.json"
        if not context_file.exists():
            return None
        with open(context_file, encoding="utf-8") as f:
            return json.load(f)

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
        norm1 = math.sqrt(sum(v ** 2 for v in counter1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in counter2.values()))

        if norm1 == 0 or norm2 == 0:
            return 0

        return dot_product / (norm1 * norm2)

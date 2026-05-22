"""Vancouver 引用格式"""
from __future__ import annotations

from dataclasses import dataclass

from .utils import format_authors


class VancouverFormatter:
    """Vancouver（ICMJE）引用格式化器"""

    def format_journal(self, article) -> str:
        """格式化期刊文章"""
        authors = format_authors(article.authors)
        citation = f"{authors}. {article.title}. {article.journal}. {article.year};{article.volume}"
        if article.issue:
            citation += f"({article.issue})"
        if article.pages:
            citation += f":{article.pages}"
        citation += "."
        return citation

    def format_book(self, book) -> str:
        """格式化书籍"""
        authors = format_authors(book.authors)
        citation = f"{authors}. {book.title}."
        if book.edition:
            citation += f" {book.edition} ed."
        citation += f" {book.publisher}; {book.year}."
        return citation

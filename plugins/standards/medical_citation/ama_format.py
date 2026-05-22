"""AMA 引用格式"""
from __future__ import annotations

from dataclasses import dataclass

from .utils import format_authors, format_journal_base, format_book_base


@dataclass
class JournalArticle:
    """期刊文章"""
    authors: list[str]
    title: str
    journal: str
    year: int
    volume: str
    issue: str = ""
    pages: str = ""
    doi: str = ""


@dataclass
class Book:
    """书籍"""
    authors: list[str]
    title: str
    publisher: str
    year: int
    edition: str = ""


class AMAFormatter:
    """AMA（American Medical Association）引用格式化器"""

    def format_journal(self, article: JournalArticle) -> str:
        """格式化期刊文章（含 DOI）"""
        return format_journal_base(article, include_doi=True)

    def format_book(self, book: Book) -> str:
        """格式化书籍"""
        return format_book_base(book)

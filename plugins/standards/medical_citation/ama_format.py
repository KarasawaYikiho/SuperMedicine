"""AMA 引用格式"""
from __future__ import annotations

from dataclasses import dataclass

from .utils import format_authors


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
        """格式化期刊文章"""
        authors = format_authors(article.authors)
        citation = f"{authors}. {article.title}. {article.journal}. {article.year};{article.volume}"
        if article.issue:
            citation += f"({article.issue})"
        if article.pages:
            citation += f":{article.pages}"
        citation += "."
        if article.doi:
            citation += f" doi:{article.doi}"
        return citation

    def format_book(self, book: Book) -> str:
        """格式化书籍"""
        authors = format_authors(book.authors)
        citation = f"{authors}. {book.title}."
        if book.edition:
            citation += f" {book.edition} ed."
        citation += f" {book.publisher}; {book.year}."
        return citation

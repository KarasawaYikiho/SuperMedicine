"""AMA 引用格式"""
from __future__ import annotations

from .utils import Book, JournalArticle, format_book_base, format_journal_base


class AMAFormatter:
    """AMA（American Medical Association）引用格式化器"""

    def format_journal(self, article: JournalArticle) -> str:
        """格式化期刊文章（含 DOI）"""
        return format_journal_base(article, include_doi=True)

    def format_book(self, book: Book) -> str:
        """格式化书籍"""
        return format_book_base(book)

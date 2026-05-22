"""Vancouver 引用格式"""
from __future__ import annotations


from .utils import format_journal_base, format_book_base


class VancouverFormatter:
    """Vancouver（ICMJE）引用格式化器"""

    def format_journal(self, article) -> str:
        """格式化期刊文章"""
        return format_journal_base(article)

    def format_book(self, book) -> str:
        """格式化书籍"""
        return format_book_base(book)

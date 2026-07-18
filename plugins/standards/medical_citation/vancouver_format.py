"""Vancouver 引用格式"""

from __future__ import annotations


from .utils import Book, CitationFormatter, JournalArticle

__all__ = ["VancouverFormatter", "Book", "JournalArticle"]


class VancouverFormatter(CitationFormatter):
    """Vancouver（ICMJE）引用格式化器"""

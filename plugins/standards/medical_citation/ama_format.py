"""AMA 引用格式"""

from __future__ import annotations

from .utils import Book, CitationFormatter, JournalArticle

__all__ = ["AMAFormatter", "VancouverFormatter", "Book", "JournalArticle"]


class AMAFormatter(CitationFormatter):
    """AMA（American Medical Association）引用格式化器"""

    include_doi = True


class VancouverFormatter(CitationFormatter):
    """Vancouver（ICMJE）引用格式化器"""

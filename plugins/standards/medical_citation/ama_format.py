"""AMA 引用格式"""

from __future__ import annotations

from .utils import Book, CitationFormatter, JournalArticle

__all__ = ["AMAFormatter", "Book", "JournalArticle"]


class AMAFormatter(CitationFormatter):
    """AMA（American Medical Association）引用格式化器"""

    include_doi = True

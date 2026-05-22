"""Vancouver 引用格式"""
from __future__ import annotations

from dataclasses import dataclass


class VancouverFormatter:
    """Vancouver（ICMJE）引用格式化器"""

    def format_journal(self, article) -> str:
        """格式化期刊文章"""
        authors = self._format_authors_vancouver(article.authors)
        citation = f"{authors}. {article.title}. {article.journal}. {article.year};{article.volume}"
        if article.issue:
            citation += f"({article.issue})"
        if article.pages:
            citation += f":{article.pages}"
        citation += "."
        return citation

    def format_book(self, book) -> str:
        """格式化书籍"""
        authors = self._format_authors_vancouver(book.authors)
        citation = f"{authors}. {book.title}."
        if book.edition:
            citation += f" {book.edition} ed."
        citation += f" {book.publisher}; {book.year}."
        return citation

    def _format_authors_vancouver(self, authors: list[str]) -> str:
        """Vancouver 作者格式：姓 名首字母（无句点）"""
        formatted = []
        for author in authors:
            parts = author.split()
            if len(parts) >= 2:
                last = parts[-1]
                initials = "".join(p[0].upper() for p in parts[:-1])
                formatted.append(f"{last} {initials}")
            else:
                formatted.append(author)

        if len(formatted) <= 6:
            return ", ".join(formatted)
        else:
            return ", ".join(formatted[:6]) + ", et al"

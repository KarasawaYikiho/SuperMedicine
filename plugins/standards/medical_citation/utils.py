"""引用格式化工具函数"""
from __future__ import annotations


def format_authors(authors: list[str], max_authors: int = 6) -> str:
    """
    格式化作者列表

    Args:
        authors: 作者列表，每个元素为 "名 姓" 格式
        max_authors: 最大作者数量，超过则使用 "et al"

    Returns:
        格式化后的作者字符串
    """
    formatted = []
    for author in authors:
        parts = author.split()
        if len(parts) >= 2:
            last = parts[-1]
            initials = "".join(p[0].upper() for p in parts[:-1])
            formatted.append(f"{last} {initials}")
        else:
            formatted.append(author)

    if len(formatted) <= max_authors:
        return ", ".join(formatted)
    else:
        return ", ".join(formatted[:max_authors]) + ", et al"


def format_journal_base(article, include_doi: bool = False) -> str:
    """期刊文章共享格式化逻辑。

    Args:
        article: JournalArticle 对象，需有 authors, title, journal, year,
                 volume, issue, pages, doi 属性。
        include_doi: 是否在末尾附加 DOI（AMA 格式需要）。

    Returns:
        格式化后的引用字符串。
    """
    authors = format_authors(article.authors)
    citation = f"{authors}. {article.title}. {article.journal}. {article.year};{article.volume}"
    if article.issue:
        citation += f"({article.issue})"
    if article.pages:
        citation += f":{article.pages}"
    citation += "."
    if include_doi and article.doi:
        citation += f" doi:{article.doi}"
    return citation


def format_book_base(book) -> str:
    """书籍共享格式化逻辑。

    Args:
        book: Book 对象，需有 authors, title, publisher, year, edition 属性。

    Returns:
        格式化后的引用字符串。
    """
    authors = format_authors(book.authors)
    citation = f"{authors}. {book.title}."
    if book.edition:
        citation += f" {book.edition} ed."
    citation += f" {book.publisher}; {book.year}."
    return citation

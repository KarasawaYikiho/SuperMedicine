"""引用格式化工具函数"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class JournalArticle:
    """期刊文章共享引用模型。"""

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
    """书籍共享引用模型。"""

    authors: list[str]
    title: str
    publisher: str
    year: int
    edition: str = ""


@dataclass
class CitationSource:
    """医学事实可引用来源。"""

    source_id: str
    reference: JournalArticle | Book | str
    confidence: float = 1.0
    valid: bool = True
    note: str = ""


@dataclass
class CitationValidationResult:
    """引用准确性校验结果。"""

    source_id: str | None
    status: str
    message: str
    confidence: float | None = None


LOW_CONFIDENCE_THRESHOLD = 0.7


def validate_source_id(
    source_id: str | None,
    sources: dict[str, CitationSource] | None,
    *,
    confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> CitationValidationResult:
    """校验医学事实的来源 ID，避免缺失、无效或低置信来源被伪造成引用。"""
    if not source_id:
        return CitationValidationResult(
            source_id=None,
            status="error",
            message="Medical fact requires a source_id; citation was not generated.",
        )

    source = (sources or {}).get(source_id)
    if source is None:
        return CitationValidationResult(
            source_id=source_id,
            status="error",
            message=f"Unknown source_id '{source_id}'; citation was not generated.",
        )

    if not source.valid:
        return CitationValidationResult(
            source_id=source_id,
            status="error",
            message=f"Invalid source_id '{source_id}'; citation was not generated.",
            confidence=source.confidence,
        )

    if source.confidence < confidence_threshold:
        return CitationValidationResult(
            source_id=source_id,
            status="warning",
            message=f"Low-confidence source_id '{source_id}' should be reviewed before citation use.",
            confidence=source.confidence,
        )

    return CitationValidationResult(
        source_id=source_id,
        status="ok",
        message=f"Source_id '{source_id}' is available for citation.",
        confidence=source.confidence,
    )


def citation_state_from_validation(
    result: CitationValidationResult,
) -> dict[str, object]:
    """将引用校验结果转为稳定、可观察的状态字典。"""
    return {
        "source_id": result.source_id,
        "status": result.status,
        "message": result.message,
        "confidence": result.confidence,
    }


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

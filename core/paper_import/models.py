"""Data models and constants for paper import support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


SUPPORTED_PAPER_EXTENSIONS: tuple[str, ...] = (".pdf", ".tex", ".bib", ".ris", ".txt", ".md")


@dataclass(slots=True)
class PaperMetadata:
    """Metadata captured for an imported paper."""

    id: Optional[str] = None
    sha256: Optional[str] = None
    stored_path: Optional[Path] = None
    format: Optional[str] = None
    imported_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    title: str = ""
    authors: list[str] = field(default_factory=list)
    doi: Optional[str] = None
    pmid: Optional[str] = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PaperImportResult:
    """Result payload returned after a paper source is imported."""

    metadata: PaperMetadata
    source_path: Optional[Path] = None
    warnings: list[str] = field(default_factory=list)
    duplicate: bool = False
    duplicate_reason: Optional[str] = None

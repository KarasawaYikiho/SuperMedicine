"""Data models and constants for paper import support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


SUPPORTED_PAPER_EXTENSIONS: tuple[str, ...] = (
    ".pdf",
    ".tex",
    ".bib",
    ".ris",
    ".txt",
    ".md",
)


@dataclass(slots=True)
class PaperMetadata:
    """Metadata captured for an imported paper."""

    id: str | None = None
    sha256: str | None = None
    stored_path: Path | None = None
    format: str | None = None
    imported_at: datetime | None = None
    updated_at: datetime | None = None
    title: str = ""
    authors: list[str] = field(default_factory=list)
    doi: str | None = None
    pmid: str | None = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PaperImportResult:
    """Result payload returned after a paper source is imported."""

    metadata: PaperMetadata
    source_path: Path | None = None
    status: str = "imported"
    warnings: list[str] = field(default_factory=list)
    duplicate: bool = False
    duplicate_reason: str | None = None


class PaperImportError(Exception):
    """Base exception for paper import failures."""


class UnsupportedPaperFormatError(PaperImportError):
    """Raised when a paper source uses an unsupported file format."""


class MissingPaperSourceError(PaperImportError):
    """Raised when an expected paper source is missing or unavailable."""


class PaperMetadataError(PaperImportError):
    """Raised when paper metadata is invalid or cannot be represented."""

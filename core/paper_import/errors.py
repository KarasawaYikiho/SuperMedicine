"""Paper import specific exceptions."""

from __future__ import annotations


class PaperImportError(Exception):
    """Base exception for paper import failures."""


class UnsupportedPaperFormatError(PaperImportError):
    """Raised when a paper source uses an unsupported file format."""


class MissingPaperSourceError(PaperImportError):
    """Raised when an expected paper source is missing or unavailable."""


class PaperMetadataError(PaperImportError):
    """Raised when paper metadata is invalid or cannot be represented."""

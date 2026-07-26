"""Public types for paper import support."""

from __future__ import annotations

from core.paper_import.contracts import (
    MissingPaperSourceError,
    PaperImportError,
    PaperMetadataError,
    SUPPORTED_PAPER_EXTENSIONS,
    PaperImportResult,
    PaperMetadata,
    UnsupportedPaperFormatError,
)

from core.paper_import.enrichment import (
    LocalMockMetadataProvider,
    PaperEnricher,
    PaperEnrichmentResult,
    PaperMetadataProvider,
)
from core.paper_import.importer import PaperImporter

__all__ = [
    "SUPPORTED_PAPER_EXTENSIONS",
    "PaperImporter",
    "PaperEnricher",
    "PaperEnrichmentResult",
    "PaperMetadataProvider",
    "LocalMockMetadataProvider",
    "PaperImportResult",
    "PaperMetadata",
    "PaperImportError",
    "UnsupportedPaperFormatError",
    "MissingPaperSourceError",
    "PaperMetadataError",
]

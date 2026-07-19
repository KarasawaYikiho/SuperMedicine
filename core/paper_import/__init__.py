"""Public types for paper import support."""

from __future__ import annotations

import sys

from core.paper_import import contracts as _contracts
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

sys.modules.setdefault("core.paper_import.errors", _contracts)
sys.modules.setdefault("core.paper_import.models", _contracts)

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

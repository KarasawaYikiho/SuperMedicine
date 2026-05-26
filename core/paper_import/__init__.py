"""Public types for paper import support."""

from core.paper_import.errors import (
    MissingPaperSourceError,
    PaperImportError,
    PaperMetadataError,
    UnsupportedPaperFormatError,
)
from core.paper_import.enrichment import (
    LocalMockMetadataProvider,
    PaperEnricher,
    PaperEnrichmentResult,
    PaperMetadataProvider,
)
from core.paper_import.importer import PaperImporter
from core.paper_import.models import (
    SUPPORTED_PAPER_EXTENSIONS,
    PaperImportResult,
    PaperMetadata,
)

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

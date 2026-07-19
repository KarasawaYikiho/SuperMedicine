"""Copy-only, workspace-contained paper importer core."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paper_import.contracts import (
    MissingPaperSourceError,
    SUPPORTED_PAPER_EXTENSIONS,
    PaperImportResult,
    PaperMetadata,
    UnsupportedPaperFormatError,
)
from core.path_safety import _is_relative_to, validate_path_in_project_root
from core.rag_service import RAGService
from core.serialization import json_ready
from core.time_utils import utc_now_datetime
from core.workspace import WorkspaceInfo, WorkspaceManager


_EDITABLE_METADATA_FIELDS: tuple[str, ...] = (
    "title",
    "authors",
    "doi",
    "pmid",
    "notes",
    "tags",
)


@dataclass(frozen=True)
class _ImportPaths:
    stored: Path
    metadata: Path
    metadata_dir: Path
    log: Path


def _metadata_value(metadata: PaperMetadata | dict[str, Any] | None, field: str) -> Any:
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return metadata.get(field)
    return getattr(metadata, field, None)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


def _normalize_doi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized.removeprefix(prefix).strip()
    return normalized or None


def _normalize_pmid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    normalized = re.sub(r"^pmid\s*:\s*", "", normalized, flags=re.IGNORECASE).strip()
    if normalized.isdigit():
        return normalized
    digits = "".join(character for character in normalized if character.isdigit())
    return digits or None


class PaperImporter:
    """Import local paper files by copying bytes into an existing workspace."""

    def __init__(
        self, project_root: str | Path | WorkspaceManager | None = None
    ) -> None:
        if isinstance(project_root, WorkspaceManager):
            self.workspace_manager = project_root
        else:
            self.workspace_manager = WorkspaceManager(project_root)
        self.project_root = self.workspace_manager.project_root

    def import_file(
        self,
        workspace_id: str,
        source_path: str | Path,
        metadata: PaperMetadata | dict[str, Any] | None = None,
    ) -> PaperImportResult:
        """Copy *source_path* into *workspace_id* and persist metadata/log records."""

        source, extension, source_bytes, sha256 = self._read_source(source_path)
        workspace = self.workspace_manager.get_workspace(workspace_id)
        paths = self._prepare_import_paths(workspace, sha256, extension)
        now = utc_now_datetime()
        duplicate = self._duplicate_result(
            paths, source, sha256, now, metadata
        )
        if duplicate is not None:
            return duplicate
        return self._store_new_paper(
            workspace, paths, source, extension, source_bytes, sha256, now, metadata
        )

    @staticmethod
    def _read_source(source_path: str | Path) -> tuple[Path, str, bytes, str]:
        source = Path(source_path).expanduser()
        if not source.exists() or not source.is_file():
            raise MissingPaperSourceError(
                f"Paper source must exist and be a file: {source}"
            )
        extension = source.suffix.lower()
        if extension not in SUPPORTED_PAPER_EXTENSIONS:
            raise UnsupportedPaperFormatError(
                f"Unsupported paper format: {extension or '<none>'}"
            )
        source_bytes = source.read_bytes()
        return source, extension, source_bytes, hashlib.sha256(source_bytes).hexdigest()

    def _prepare_import_paths(
        self, workspace: WorkspaceInfo, sha256: str, extension: str
    ) -> _ImportPaths:
        originals = self._workspace_child(workspace, "papers", "originals")
        metadata = self._workspace_child(workspace, "papers", "metadata")
        imports = self._workspace_child(workspace, "papers", "imports")
        for directory in (originals, metadata, imports):
            directory.mkdir(parents=True, exist_ok=True)
        return _ImportPaths(
            stored=self._workspace_child(
                workspace, "papers", "originals", f"{sha256}{extension}"
            ),
            metadata=self._workspace_child(
                workspace, "papers", "metadata", f"{sha256}.json"
            ),
            metadata_dir=metadata,
            log=self._workspace_child(
                workspace, "papers", "imports", "import-log.jsonl"
            ),
        )

    def _duplicate_result(
        self,
        paths: _ImportPaths,
        source: Path,
        sha256: str,
        now: datetime,
        metadata: PaperMetadata | dict[str, Any] | None,
    ) -> PaperImportResult | None:
        duplicate = None
        if paths.metadata.exists():
            duplicate = (
                paths.metadata,
                self._load_metadata(paths.metadata),
                "sha256_already_imported",
            )
        if duplicate is None:
            duplicate = self._find_metadata_duplicate(paths.metadata_dir, metadata)
        if duplicate is None:
            return None
        metadata_path, existing, reason = duplicate
        self._log_duplicate_import(
            import_log_path=paths.log,
            imported_at=now,
            paper_id=existing.id,
            sha256=sha256,
            source_path=source,
            stored_path=existing.stored_path,
            metadata_path=metadata_path,
            duplicate_reason=reason,
        )
        return PaperImportResult(
            metadata=existing,
            source_path=source,
            duplicate=True,
            duplicate_reason=reason,
        )

    def _store_new_paper(
        self,
        workspace: WorkspaceInfo,
        paths: _ImportPaths,
        source: Path,
        extension: str,
        source_bytes: bytes,
        sha256: str,
        now: datetime,
        metadata: PaperMetadata | dict[str, Any] | None,
    ) -> PaperImportResult:
        paths.stored.write_bytes(source_bytes)
        paper = PaperMetadata(
            id=sha256,
            sha256=sha256,
            stored_path=paths.stored,
            format=extension,
            imported_at=now,
            updated_at=now,
        )
        self._apply_editable_metadata(paper, metadata)
        self._write_metadata(paths.metadata, paper)
        import_status = "imported"
        import_warnings: list[str] = []
        if extension in {".md", ".txt", ".pdf"}:
            try:
                page_texts = None
                text = source_bytes.decode("utf-8") if extension != ".pdf" else ""
                if extension == ".pdf":
                    from pypdf import PdfReader

                    reader = PdfReader(paths.stored)
                    page_texts = [
                        (page_number, page.extract_text() or "")
                        for page_number, page in enumerate(reader.pages, start=1)
                    ]
                    if not any(page_text.strip() for _, page_text in page_texts):
                        import_status = "ocr_required"
                        import_warnings.append(
                            "ocr_required: PDF contains no extractable text"
                        )
                        page_texts = None
                if import_status != "ocr_required":
                    RAGService.index_workspace_document(
                        workspace.path,
                        text=text,
                        document_id=paper.id or sha256,
                        source_path=paths.stored,
                        title=paper.title,
                        page_texts=page_texts,
                    )
            except Exception:
                import_status = "imported_with_index_error"
                import_warnings.append("rag_index_failed: retry paper indexing")
        log_record = {
            "event": "paper_imported",
            "imported_at": now,
            "paper_id": paper.id,
            "sha256": sha256,
            "source_path": source,
            "stored_path": paths.stored,
            "metadata_path": paths.metadata,
            "index_status": import_status,
        }
        with paths.log.open("a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(json_ready(log_record), ensure_ascii=False, sort_keys=True)
                + "\n"
            )
        return PaperImportResult(
            metadata=paper,
            source_path=source,
            status=import_status,
            warnings=import_warnings,
        )

    import_paper = import_file

    def list_papers(self, workspace_id: str) -> list[PaperMetadata]:
        """Return all persisted paper metadata for an existing workspace."""

        workspace = self.workspace_manager.get_workspace(workspace_id)
        metadata_dir = self._workspace_child(workspace, "papers", "metadata")
        if not metadata_dir.exists():
            return []
        return [
            self._load_metadata(path) for path in sorted(metadata_dir.glob("*.json"))
        ]

    def get_paper(self, workspace_id: str, paper_id: str) -> PaperMetadata:
        """Return one paper metadata record from an existing workspace."""

        path = self._metadata_path_for_paper(workspace_id, paper_id)
        if not path.exists() or not path.is_file():
            raise MissingPaperSourceError(f"Paper metadata not found: {paper_id}")
        return self._load_metadata(path)

    def update_paper_metadata(
        self,
        workspace_id: str,
        paper_id: str,
        metadata: PaperMetadata | dict[str, Any],
    ) -> PaperMetadata:
        """Apply editable metadata updates to one persisted paper record."""

        path = self._metadata_path_for_paper(workspace_id, paper_id)
        if not path.exists() or not path.is_file():
            raise MissingPaperSourceError(f"Paper metadata not found: {paper_id}")
        current = self._load_metadata(path)
        self._apply_editable_metadata(current, metadata)
        current.updated_at = utc_now_datetime()
        self._write_metadata(path, current)
        return current

    def save_paper_metadata(
        self, workspace_id: str, metadata: PaperMetadata
    ) -> PaperMetadata:
        """Persist a complete metadata object for an existing paper."""

        if not metadata.id:
            raise MissingPaperSourceError("Paper metadata id is required")
        path = self._metadata_path_for_paper(workspace_id, metadata.id)
        if not path.exists() or not path.is_file():
            raise MissingPaperSourceError(f"Paper metadata not found: {metadata.id}")
        metadata.updated_at = utc_now_datetime()
        self._write_metadata(path, metadata)
        return metadata

    def delete_paper(self, workspace_id: str, paper_id: str) -> dict[str, Any]:
        """Delete one imported paper and synchronously remove its RAG chunks."""
        workspace = self.workspace_manager.get_workspace(workspace_id)
        metadata_path = self._metadata_path_for_paper(workspace_id, paper_id)
        if not metadata_path.is_file():
            raise MissingPaperSourceError(f"Paper metadata not found: {paper_id}")
        metadata = self._load_metadata(metadata_path)
        removed_chunks = RAGService.remove_workspace_document(workspace.path, paper_id)
        stored_path = metadata.stored_path
        if stored_path is not None and stored_path.is_file():
            stored_path.unlink()
        metadata_path.unlink()
        return {
            "status": "deleted",
            "paper_id": paper_id,
            "rag_chunks_removed": removed_chunks,
        }

    def _metadata_path_for_paper(self, workspace_id: str, paper_id: str) -> Path:
        workspace = self.workspace_manager.get_workspace(workspace_id)
        return self._workspace_child(
            workspace, "papers", "metadata", f"{paper_id}.json"
        )

    def _workspace_child(self, workspace: WorkspaceInfo, *parts: str) -> Path:
        path = validate_path_in_project_root(
            workspace.path.joinpath(*parts), self.project_root
        )
        workspace_root = validate_path_in_project_root(
            workspace.path, self.project_root
        )
        if not _is_relative_to(path, workspace_root):
            raise MissingPaperSourceError(
                f"Import destination escapes workspace: {path}"
            )
        return path

    def _apply_editable_metadata(
        self,
        paper_metadata: PaperMetadata,
        metadata: PaperMetadata | dict[str, Any] | None,
    ) -> None:
        for field in _EDITABLE_METADATA_FIELDS:
            value = _metadata_value(metadata, field)
            if value is not None:
                setattr(paper_metadata, field, value)

    def _find_metadata_duplicate(
        self,
        metadata_dir: Path,
        metadata: PaperMetadata | dict[str, Any] | None,
    ) -> tuple[Path, PaperMetadata, str] | None:
        new_doi = _normalize_doi(_metadata_value(metadata, "doi"))
        new_pmid = _normalize_pmid(_metadata_value(metadata, "pmid"))
        if new_doi is None and new_pmid is None:
            return None

        for candidate_path in sorted(metadata_dir.glob("*.json")):
            candidate_metadata = self._load_metadata(candidate_path)
            if (
                new_doi is not None
                and _normalize_doi(candidate_metadata.doi) == new_doi
            ):
                return candidate_path, candidate_metadata, "doi_already_imported"
            if (
                new_pmid is not None
                and _normalize_pmid(candidate_metadata.pmid) == new_pmid
            ):
                return candidate_path, candidate_metadata, "pmid_already_imported"
        return None

    def _log_duplicate_import(
        self,
        *,
        import_log_path: Path,
        imported_at: datetime,
        paper_id: str | None,
        sha256: str,
        source_path: Path,
        stored_path: Path | None,
        metadata_path: Path,
        duplicate_reason: str,
    ) -> None:
        log_record = {
            "event": "paper_import_duplicate",
            "imported_at": imported_at,
            "paper_id": paper_id,
            "sha256": sha256,
            "source_path": source_path,
            "stored_path": stored_path,
            "metadata_path": metadata_path,
            "duplicate": True,
            "duplicate_reason": duplicate_reason,
        }
        with import_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(json_ready(log_record), ensure_ascii=False, sort_keys=True)
                + "\n"
            )

    def _load_metadata(self, metadata_path: Path) -> PaperMetadata:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        stored_path = data.get("stored_path")
        return PaperMetadata(
            id=data.get("id"),
            sha256=data.get("sha256"),
            stored_path=Path(stored_path) if stored_path else None,
            format=data.get("format"),
            imported_at=_parse_datetime(data.get("imported_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            title=data.get("title", ""),
            authors=list(data.get("authors") or []),
            doi=data.get("doi"),
            pmid=data.get("pmid"),
            notes=data.get("notes", ""),
            tags=list(data.get("tags") or []),
        )

    def _write_metadata(self, metadata_path: Path, metadata: PaperMetadata) -> None:
        metadata_path.write_text(
            json.dumps(
                json_ready(metadata), ensure_ascii=False, sort_keys=True, indent=2
            )
            + "\n",
            encoding="utf-8",
        )

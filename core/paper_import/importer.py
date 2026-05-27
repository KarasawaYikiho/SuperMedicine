"""Copy-only, workspace-contained paper importer core."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.paper_import.errors import MissingPaperSourceError, UnsupportedPaperFormatError
from core.paper_import.models import (
    SUPPORTED_PAPER_EXTENSIONS,
    PaperImportResult,
    PaperMetadata,
)
from core.path_safety import validate_path_in_project_root
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


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _metadata_value(metadata: PaperMetadata | dict[str, Any] | None, field: str) -> Any:
    if metadata is None:
        return None
    if isinstance(metadata, dict):
        return metadata.get(field)
    return getattr(metadata, field, None)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return _json_ready(asdict(value))
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


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

    def __init__(self, project_root: str | Path | WorkspaceManager | None = None) -> None:
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

        workspace = self.workspace_manager.get_workspace(workspace_id)
        source = Path(source_path).expanduser()
        if not source.exists() or not source.is_file():
            raise MissingPaperSourceError(f"Paper source must exist and be a file: {source}")

        extension = source.suffix.lower()
        if extension not in SUPPORTED_PAPER_EXTENSIONS:
            raise UnsupportedPaperFormatError(f"Unsupported paper format: {extension or '<none>'}")

        source_bytes = source.read_bytes()
        sha256 = hashlib.sha256(source_bytes).hexdigest()
        now = utc_now_datetime()

        originals_dir = self._workspace_child(workspace, "papers", "originals")
        metadata_dir = self._workspace_child(workspace, "papers", "metadata")
        imports_dir = self._workspace_child(workspace, "papers", "imports")
        originals_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        imports_dir.mkdir(parents=True, exist_ok=True)

        stored_path = self._workspace_child(workspace, "papers", "originals", f"{sha256}{extension}")
        metadata_path = self._workspace_child(
            workspace,
            "papers",
            "metadata",
            f"{sha256}.json",
        )
        import_log_path = self._workspace_child(
            workspace,
            "papers",
            "imports",
            "import-log.jsonl",
        )

        if metadata_path.exists():
            existing_metadata = self._load_metadata(metadata_path)
            duplicate_reason = "sha256_already_imported"
            self._log_duplicate_import(
                import_log_path=import_log_path,
                imported_at=now,
                paper_id=existing_metadata.id,
                sha256=sha256,
                source_path=source,
                stored_path=existing_metadata.stored_path,
                metadata_path=metadata_path,
                duplicate_reason=duplicate_reason,
            )
            return PaperImportResult(
                metadata=existing_metadata,
                source_path=source,
                duplicate=True,
                duplicate_reason=duplicate_reason,
            )

        metadata_duplicate = self._find_metadata_duplicate(metadata_dir, metadata)
        if metadata_duplicate is not None:
            existing_metadata_path, existing_metadata, duplicate_reason = metadata_duplicate
            self._log_duplicate_import(
                import_log_path=import_log_path,
                imported_at=now,
                paper_id=existing_metadata.id,
                sha256=sha256,
                source_path=source,
                stored_path=existing_metadata.stored_path,
                metadata_path=existing_metadata_path,
                duplicate_reason=duplicate_reason,
            )
            return PaperImportResult(
                metadata=existing_metadata,
                source_path=source,
                duplicate=True,
                duplicate_reason=duplicate_reason,
            )

        stored_path.write_bytes(source_bytes)

        paper_metadata = PaperMetadata(
            id=sha256,
            sha256=sha256,
            stored_path=stored_path,
            format=extension,
            imported_at=now,
            updated_at=now,
        )
        self._apply_editable_metadata(paper_metadata, metadata)

        metadata_path.write_text(
            json.dumps(_json_ready(paper_metadata), ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
            encoding="utf-8",
        )

        log_record = {
            "event": "paper_imported",
            "imported_at": now,
            "paper_id": paper_metadata.id,
            "sha256": sha256,
            "source_path": source,
            "stored_path": stored_path,
            "metadata_path": metadata_path,
        }
        with import_log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(_json_ready(log_record), ensure_ascii=False, sort_keys=True) + "\n")

        return PaperImportResult(metadata=paper_metadata, source_path=source)

    import_paper = import_file

    def list_papers(self, workspace_id: str) -> list[PaperMetadata]:
        """Return all persisted paper metadata for an existing workspace."""

        workspace = self.workspace_manager.get_workspace(workspace_id)
        metadata_dir = self._workspace_child(workspace, "papers", "metadata")
        if not metadata_dir.exists():
            return []
        return [self._load_metadata(path) for path in sorted(metadata_dir.glob("*.json"))]

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

    def save_paper_metadata(self, workspace_id: str, metadata: PaperMetadata) -> PaperMetadata:
        """Persist a complete metadata object for an existing paper."""

        if not metadata.id:
            raise MissingPaperSourceError("Paper metadata id is required")
        path = self._metadata_path_for_paper(workspace_id, metadata.id)
        if not path.exists() or not path.is_file():
            raise MissingPaperSourceError(f"Paper metadata not found: {metadata.id}")
        metadata.updated_at = utc_now_datetime()
        self._write_metadata(path, metadata)
        return metadata

    def _metadata_path_for_paper(self, workspace_id: str, paper_id: str) -> Path:
        workspace = self.workspace_manager.get_workspace(workspace_id)
        return self._workspace_child(workspace, "papers", "metadata", f"{paper_id}.json")

    def _workspace_child(self, workspace: WorkspaceInfo, *parts: str) -> Path:
        path = validate_path_in_project_root(workspace.path.joinpath(*parts), self.project_root)
        workspace_root = validate_path_in_project_root(workspace.path, self.project_root)
        if not _is_relative_to(path, workspace_root):
            raise MissingPaperSourceError(f"Import destination escapes workspace: {path}")
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
            if new_doi is not None and _normalize_doi(candidate_metadata.doi) == new_doi:
                return candidate_path, candidate_metadata, "doi_already_imported"
            if new_pmid is not None and _normalize_pmid(candidate_metadata.pmid) == new_pmid:
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
            log_file.write(json.dumps(_json_ready(log_record), ensure_ascii=False, sort_keys=True) + "\n")

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
            json.dumps(_json_ready(metadata), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

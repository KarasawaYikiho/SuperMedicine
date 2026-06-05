"""Experience learning storage foundation.

This module provides additive JSONL storage primitives for user-confirmed
experience summaries. It deliberately does not integrate with CLI, TUI, or RAG
actions yet.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import tempfile
import uuid
from typing import Any, Literal

from core.time_utils import utc_now
from core.workspace import WorkspaceManager


EXPERIENCE_LEARNING_ENABLED_BY_DEFAULT = True
GENERAL_EXPERIENCE_DIRNAME = "supermedicine-rag-interface"
CONFIRMED_EXPERIENCE_FILENAME = "confirmed.jsonl"

ExperienceScope = Literal["general", "workspace"]
ExportFormat = Literal["json", "md"]

_PROJECT_DETAIL_MARKERS = {
    "workspace_id",
    "project_details",
    "paper_ids",
    "paper_paths",
    "contains_project_details",
}
_RAW_CONVERSATION_MARKERS = {
    "raw_conversation",
    "raw_conversation_text",
    "conversation",
    "conversation_text",
    "messages",
    "transcript",
}


class ExperienceError(ValueError):
    """Base exception for experience storage failures."""


class ExperiencePrivacyError(ExperienceError):
    """Raised when a record violates experience privacy boundaries."""


class ExperienceValidationError(ExperienceError):
    """Raised when an experience record is not safe to persist."""


def _new_id() -> str:
    return str(uuid.uuid4())


def _contains_key(data: Any, keys: set[str]) -> bool:
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key) in keys:
                return True
            if _contains_key(value, keys):
                return True
    elif isinstance(data, (list, tuple)):
        return any(_contains_key(item, keys) for item in data)
    return False


def _contains_marker_text(data: Any, markers: set[str]) -> bool:
    if isinstance(data, dict):
        return any(_contains_marker_text(value, markers) for value in data.values())
    if isinstance(data, (list, tuple)):
        return any(_contains_marker_text(item, markers) for item in data)
    if isinstance(data, str):
        lowered = data.lower()
        return any(marker.lower() in lowered for marker in markers)
    return False


@dataclass(frozen=True)
class ExperienceClassificationSuggestion:
    """Non-persisted scope suggestion awaiting explicit user confirmation."""

    suggested_scope: ExperienceScope
    title: str
    summary: str
    tags: list[str] = field(default_factory=list)
    reason: str = ""
    confirmed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperienceRecord:
    """A persisted, user-confirmed experience summary.

    Raw conversations are never accepted or stored. ``confirmed`` must be true
    for confirmed storage APIs.
    """

    title: str
    summary: str
    scope: ExperienceScope
    tags: list[str] = field(default_factory=list)
    workspace_id: str | None = None
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    raw_conversation_stored: bool = False
    confirmed: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperienceRecord":
        _reject_raw_conversation_fields(data)
        record = cls(
            id=str(data.get("id") or _new_id()),
            scope=str(data.get("scope")),  # type: ignore[arg-type]
            workspace_id=data.get("workspace_id"),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            tags=[str(tag) for tag in data.get("tags", [])],
            created_at=str(data.get("created_at") or utc_now()),
            updated_at=str(data.get("updated_at") or utc_now()),
            raw_conversation_stored=bool(data.get("raw_conversation_stored", False)),
            confirmed=bool(data.get("confirmed", True)),
        )
        validate_confirmed_record(record)
        return record


def _reject_raw_conversation_fields(data: dict[str, Any]) -> None:
    if data.get("raw_conversation_stored") is True:
        raise ExperiencePrivacyError("Raw conversation storage is not allowed")
    if _contains_key(data, _RAW_CONVERSATION_MARKERS):
        raise ExperiencePrivacyError("Raw conversation fields are not allowed")
    if _contains_marker_text(data, _RAW_CONVERSATION_MARKERS):
        raise ExperiencePrivacyError("Raw conversation markers are not allowed")


def validate_confirmed_record(record: ExperienceRecord) -> None:
    """Validate a record before it can enter confirmed storage."""

    if record.scope not in ("general", "workspace"):
        raise ExperienceValidationError(
            "Experience scope must be 'general' or 'workspace'"
        )
    if not record.confirmed:
        raise ExperienceValidationError(
            "Only user-confirmed experiences may be persisted"
        )
    if record.raw_conversation_stored:
        raise ExperiencePrivacyError("Raw conversation storage is not allowed")
    if not record.title.strip():
        raise ExperienceValidationError("Experience title is required")
    if not record.summary.strip():
        raise ExperienceValidationError("Experience summary is required")
    if record.scope == "workspace" and not record.workspace_id:
        raise ExperienceValidationError("Workspace experiences require a workspace_id")
    if record.scope == "general" and record.workspace_id is not None:
        raise ExperiencePrivacyError(
            "General experiences must not include a workspace_id"
        )
    _reject_raw_conversation_fields(record.to_dict())


def validate_general_experience_privacy(
    record: ExperienceRecord, source: dict[str, Any] | None = None
) -> None:
    """Reject deterministic project-detail markers in the general method layer."""

    payload = record.to_dict() if source is None else dict(source)
    if payload.get("contains_project_details") is True:
        raise ExperiencePrivacyError(
            "General experiences must not contain project details"
        )
    if payload.get("workspace_id") is not None:
        raise ExperiencePrivacyError(
            "General experiences must not contain workspace_id"
        )
    for marker in ("project_details", "paper_ids", "paper_paths"):
        if _contains_key(payload, {marker}):
            raise ExperiencePrivacyError(
                f"General experiences must not contain {marker}"
            )
    if _contains_marker_text(payload, _PROJECT_DETAIL_MARKERS):
        raise ExperiencePrivacyError(
            "General experiences must not contain project detail markers"
        )


class ExperienceStore:
    """JSONL store for confirmed general and workspace experience summaries."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.workspace_manager = WorkspaceManager(project_root)
        self.project_root = self.workspace_manager.project_root

    @property
    def general_confirmed_path(self) -> Path:
        return (
            Path(tempfile.gettempdir())
            / GENERAL_EXPERIENCE_DIRNAME
            / "general-experience"
            / CONFIRMED_EXPERIENCE_FILENAME
        )

    def workspace_confirmed_path(self, workspace_id: str) -> Path:
        workspace = self.workspace_manager.get_workspace(workspace_id)
        return (
            workspace.path
            / ".supermedicine"
            / "rag"
            / "local"
            / "experience"
            / CONFIRMED_EXPERIENCE_FILENAME
        )

    def store_confirmed_experience(
        self, record: ExperienceRecord | dict[str, Any]
    ) -> ExperienceRecord:
        """Persist a confirmed record to its scope-specific storage layer."""

        source = record if isinstance(record, dict) else record.to_dict()
        _reject_raw_conversation_fields(source)
        normalized = (
            ExperienceRecord.from_dict(source) if isinstance(record, dict) else record
        )
        validate_confirmed_record(normalized)

        if normalized.scope == "general":
            validate_general_experience_privacy(normalized, source)
            return self.store_confirmed_general_experience(normalized)
        return self.store_confirmed_workspace_experience(normalized)

    def suggest_classification(
        self,
        *,
        workspace_id: str,
        title: str | None = None,
        summary: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperienceClassificationSuggestion:
        """Suggest a scope without writing anything to storage."""

        self.workspace_manager.get_workspace(workspace_id)
        payload: dict[str, Any] = {
            "title": title or "Experience",
            "summary": summary,
            "tags": list(tags or []),
            **(metadata or {}),
        }
        _reject_raw_conversation_fields(payload)
        if _contains_key(payload, _PROJECT_DETAIL_MARKERS) or _contains_marker_text(
            payload, _PROJECT_DETAIL_MARKERS
        ):
            scope: ExperienceScope = "workspace"
            reason = "Project-detail markers require workspace-local storage."
        else:
            scope = "general"
            reason = "No deterministic project-detail markers found."
        return ExperienceClassificationSuggestion(
            suggested_scope=scope,
            title=title or "Experience",
            summary=summary,
            tags=list(tags or []),
            reason=reason,
            confirmed=False,
        )

    def confirm_classification(
        self,
        *,
        workspace_id: str,
        scope: ExperienceScope,
        title: str,
        summary: str,
        tags: list[str] | None = None,
        source: dict[str, Any] | None = None,
    ) -> ExperienceRecord:
        """Persist only after the caller supplies an explicit confirmed scope."""

        self.workspace_manager.get_workspace(workspace_id)
        payload = dict(source or {})
        payload.update(
            {
                "scope": scope,
                "title": title,
                "summary": summary,
                "tags": list(tags or []),
                "confirmed": True,
            }
        )
        if scope == "workspace":
            payload["workspace_id"] = workspace_id
        else:
            payload.pop("workspace_id", None)
        return self.store_confirmed_experience(payload)

    def store_confirmed_general_experience(
        self,
        record: ExperienceRecord | None = None,
        *,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> ExperienceRecord:
        """Write a confirmed general method experience to tempdir storage."""

        normalized = record or ExperienceRecord(
            scope="general",
            title=title or "",
            summary=summary or "",
            tags=list(tags or []),
        )
        validate_confirmed_record(normalized)
        validate_general_experience_privacy(normalized)
        self._append_jsonl(self.general_confirmed_path, normalized)
        return normalized

    def store_confirmed_workspace_experience(
        self,
        record: ExperienceRecord | None = None,
        *,
        workspace_id: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> ExperienceRecord:
        """Write a confirmed workspace experience to that workspace only."""

        normalized = record or ExperienceRecord(
            scope="workspace",
            workspace_id=workspace_id,
            title=title or "",
            summary=summary or "",
            tags=list(tags or []),
        )
        validate_confirmed_record(normalized)
        path = self.workspace_confirmed_path(normalized.workspace_id or "")
        self._append_jsonl(path, normalized)
        return normalized

    def list_general_experiences(self) -> list[ExperienceRecord]:
        """List confirmed general experiences shared through the method layer."""

        return self._read_jsonl(self.general_confirmed_path)

    def list_workspace_experiences(self, workspace_id: str) -> list[ExperienceRecord]:
        """List confirmed experiences for exactly one initialized workspace."""

        return self._read_jsonl(self.workspace_confirmed_path(workspace_id))

    def list_experiences(
        self, workspace_id: str, *, include_general: bool = False
    ) -> list[ExperienceRecord]:
        """List records visible from the explicit workspace context."""

        self.workspace_manager.get_workspace(workspace_id)
        records = self.list_workspace_experiences(workspace_id)
        if include_general:
            records.extend(self.list_general_experiences())
        return records

    def get_experience(
        self,
        record_id: str,
        *,
        workspace_id: str,
        scope: ExperienceScope | None = None,
        include_general: bool = True,
    ) -> ExperienceRecord:
        """Get a visible record by id from a caller-supplied workspace context."""

        candidates: list[ExperienceRecord] = []
        if scope in (None, "workspace"):
            candidates.extend(self.list_workspace_experiences(workspace_id))
        if (scope in (None, "general")) and include_general:
            self.workspace_manager.get_workspace(workspace_id)
            candidates.extend(self.list_general_experiences())
        for record in candidates:
            if record.id == record_id:
                return record
        raise ExperienceValidationError(f"Experience record not found: {record_id}")

    def edit_experience(
        self,
        record_id: str,
        *,
        workspace_id: str,
        scope: ExperienceScope,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> ExperienceRecord:
        """Edit one record in its explicit scope while preserving privacy rules."""

        self.workspace_manager.get_workspace(workspace_id)
        path = (
            self.general_confirmed_path
            if scope == "general"
            else self.workspace_confirmed_path(workspace_id)
        )
        records = self._read_jsonl(path)
        updated: ExperienceRecord | None = None
        rewritten: list[ExperienceRecord] = []
        for record in records:
            if record.id == record_id:
                updated = ExperienceRecord(
                    id=record.id,
                    scope=record.scope,
                    workspace_id=record.workspace_id,
                    title=title if title is not None else record.title,
                    summary=summary if summary is not None else record.summary,
                    tags=list(tags) if tags is not None else list(record.tags),
                    created_at=record.created_at,
                    updated_at=utc_now(),
                    raw_conversation_stored=False,
                    confirmed=True,
                )
                validate_confirmed_record(updated)
                if updated.scope == "general":
                    validate_general_experience_privacy(updated)
                rewritten.append(updated)
            else:
                rewritten.append(record)
        if updated is None:
            raise ExperienceValidationError(f"Experience record not found: {record_id}")
        self._write_jsonl(path, rewritten)
        return updated

    def delete_experience(
        self, record_id: str, *, workspace_id: str, scope: ExperienceScope
    ) -> ExperienceRecord:
        """Delete one record from its explicit scope and return the deleted record."""

        self.workspace_manager.get_workspace(workspace_id)
        path = (
            self.general_confirmed_path
            if scope == "general"
            else self.workspace_confirmed_path(workspace_id)
        )
        records = self._read_jsonl(path)
        deleted: ExperienceRecord | None = None
        remaining: list[ExperienceRecord] = []
        for record in records:
            if record.id == record_id:
                deleted = record
            else:
                remaining.append(record)
        if deleted is None:
            raise ExperienceValidationError(f"Experience record not found: {record_id}")
        self._write_jsonl(path, remaining)
        return deleted

    def export_experiences(
        self,
        *,
        workspace_id: str,
        format: ExportFormat = "json",
        include_general: bool = False,
        path: str | Path | None = None,
    ) -> str:
        """Export records visible from one workspace as JSON or Markdown."""

        records = self.list_experiences(workspace_id, include_general=include_general)
        if format == "json":
            rendered = json.dumps(
                [record.to_dict() for record in records], ensure_ascii=False, indent=2
            )
        elif format == "md":
            rendered = self._records_to_markdown(records)
        else:
            raise ExperienceValidationError("Export format must be 'json' or 'md'")
        if path is not None:
            Path(path).write_text(rendered, encoding="utf-8")
        return rendered

    def _append_jsonl(self, path: Path, record: ExperienceRecord) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
            )
            handle.write("\n")

    def _write_jsonl(self, path: Path, records: list[ExperienceRecord]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(
                    json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
                )
                handle.write("\n")

    def _read_jsonl(self, path: Path) -> list[ExperienceRecord]:
        if not path.is_file():
            return []
        records: list[ExperienceRecord] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                loaded = json.loads(stripped)
                if not isinstance(loaded, dict):
                    raise ExperienceValidationError(
                        "Experience JSONL rows must be objects"
                    )
                records.append(ExperienceRecord.from_dict(loaded))
        return records

    def _records_to_markdown(self, records: list[ExperienceRecord]) -> str:
        lines = ["# Experience Export", ""]
        for record in records:
            lines.extend(
                [
                    f"## {record.title}",
                    "",
                    f"- id: {record.id}",
                    f"- scope: {record.scope}",
                    f"- created_at: {record.created_at}",
                    f"- updated_at: {record.updated_at}",
                    f"- tags: {', '.join(record.tags)}",
                    "",
                    record.summary,
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

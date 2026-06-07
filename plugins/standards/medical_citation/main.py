"""Executable entrypoint for the medical-citation manifest plugin."""

from __future__ import annotations

from typing import Any

from plugins.base_plugin import plugin_result
from plugins.standards.medical_citation.ama_format import AMAFormatter
from plugins.standards.medical_citation.utils import (
    Book,
    CitationSource,
    JournalArticle,
    citation_state_from_validation,
    validate_source_id,
)
from plugins.standards.medical_citation.vancouver_format import VancouverFormatter
from plugins.tools._common import required_str


PLUGIN_NAME = "medical-citation"
MEDICAL_BOUNDARY = (
    "Medical citation output is deterministic formatting of user-provided, "
    "validated source metadata only; citations are not generated when the "
    "source is missing, unknown, or invalid, and all output requires human "
    "expert review before research, regulatory, or clinical use."
)

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "standard.citation.ama": {
        "required_params": {"source_id": "str", "sources": "dict[str, source]"},
        "optional_params": {"reference_type": "journal|book"},
        "output_fields": [
            "citation",
            "format",
            "source_id",
            "validation",
            "reference_type",
        ],
    },
    "standard.citation.vancouver": {
        "required_params": {"source_id": "str", "sources": "dict[str, source]"},
        "optional_params": {"reference_type": "journal|book"},
        "output_fields": [
            "citation",
            "format",
            "source_id",
            "validation",
            "reference_type",
        ],
    },
}


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute supported medical citation formatting actions."""
    params = params or {}
    context = context or {}
    metadata = _base_metadata(context)

    if action not in ACTION_CONTRACTS:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            error=f"Unsupported medical-citation action: {action}",
            metadata=metadata,
        )

    try:
        output = _execute_citation(action, params)
    except (TypeError, ValueError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            error=f"Invalid medical-citation input: {exc}",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin=PLUGIN_NAME,
        action=action,
        output=output,
        metadata=metadata,
    )


def _execute_citation(action: str, params: dict[str, Any]) -> dict[str, Any]:
    sources = _sources_from_params(params.get("sources"))
    source_id = params.get("source_id")
    if source_id is not None and not isinstance(source_id, str):
        raise ValueError("source_id must be a string")

    validation = validate_source_id(source_id, sources)
    if validation.status == "error":
        raise ValueError(validation.message)
    if validation.source_id is None:
        raise ValueError(validation.message)

    source = sources[validation.source_id]
    reference = source.reference
    if not isinstance(reference, (JournalArticle, Book)):
        raise ValueError("source reference must be structured journal or book metadata")
    reference_type = _reference_type(reference)
    formatter = (
        AMAFormatter() if action == "standard.citation.ama" else VancouverFormatter()
    )
    citation_format = "AMA" if action == "standard.citation.ama" else "Vancouver"

    if isinstance(reference, JournalArticle):
        citation = formatter.format_journal(reference)
    elif isinstance(reference, Book):
        citation = formatter.format_book(reference)
    else:
        raise ValueError("source reference must be structured journal or book metadata")

    return {
        "status": validation.status,
        "format": citation_format,
        "source_id": validation.source_id,
        "reference_type": reference_type,
        "citation": citation,
        "validation": citation_state_from_validation(validation),
        "medical_boundary": MEDICAL_BOUNDARY,
        "not_for_clinical_advice": True,
        "requires_human_review": True,
    }


def _base_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "medical_boundary": MEDICAL_BOUNDARY,
        "not_for_clinical_advice": True,
        "requires_human_review": True,
        "resource": {"kind": "standard", "plugin": PLUGIN_NAME},
        "security": {
            "permission_entrypoint": "kernel",
            "permission_checked": bool(context),
        },
        "contract": {
            "actions": ACTION_CONTRACTS,
            "provider_contract": "medical-citation-formatters",
        },
        "audit": {
            "context_keys": sorted(context.keys()),
            "citation_fabrication": "not_generated",
        },
    }


def _sources_from_params(value: Any) -> dict[str, CitationSource]:
    if not isinstance(value, dict) or not value:
        raise ValueError("sources must be a non-empty dictionary")

    sources: dict[str, CitationSource] = {}
    for key, item in value.items():
        source_id = str(key)
        if isinstance(item, CitationSource):
            if item.source_id != source_id:
                raise ValueError("source_id must match its sources dictionary key")
            sources[source_id] = item
            continue
        if not isinstance(item, dict):
            raise ValueError(
                "sources entries must be dictionaries or CitationSource objects"
            )
        sources[source_id] = _source_from_dict(source_id, item)
    return sources


def _source_from_dict(source_id: str, item: dict[str, Any]) -> CitationSource:
    declared_id = item.get("source_id", source_id)
    if declared_id != source_id:
        raise ValueError("source_id must match its sources dictionary key")
    confidence = item.get("confidence", 1.0)
    if not isinstance(confidence, (int, float)):
        raise ValueError("source confidence must be numeric when provided")
    valid = item.get("valid", True)
    if not isinstance(valid, bool):
        raise ValueError("source valid must be boolean when provided")
    note = item.get("note", "")
    if not isinstance(note, str):
        raise ValueError("source note must be a string when provided")
    source_type = _optional_metadata_str(item.get("source_type"), "provided_source")
    location = _optional_metadata_str(item.get("location"), "")
    authority = _optional_metadata_str(item.get("authority"), "unspecified")
    verification_status = _optional_metadata_str(
        item.get("verification_status"), "provided_not_rechecked"
    )

    return CitationSource(
        source_id=source_id,
        reference=_reference_from_source_dict(item),
        confidence=float(confidence),
        valid=valid,
        note=note,
        source_type=source_type,
        location=location,
        authority=authority,
        verification_status=verification_status,
    )


def _reference_from_source_dict(item: dict[str, Any]) -> JournalArticle | Book:
    reference = item.get("reference")
    reference_type = str(item.get("reference_type") or item.get("type") or "").lower()

    if isinstance(reference, (JournalArticle, Book)):
        return reference
    if isinstance(reference, dict):
        data = reference
        reference_type = str(
            reference.get("reference_type") or reference.get("type") or reference_type
        ).lower()
    else:
        data = item

    if reference_type in {"book", "monograph"}:
        return _book_from_dict(data)
    if reference_type in {"journal", "journal_article", "article", ""}:
        return _journal_from_dict(data)
    raise ValueError("reference_type must be journal or book")


def _journal_from_dict(data: dict[str, Any]) -> JournalArticle:
    authors = _authors(data.get("authors"))
    title = required_str(data, "title")
    journal = required_str(data, "journal")
    year = _year(data.get("year"))
    volume = required_str(data, "volume")
    return JournalArticle(
        authors=authors,
        title=title,
        journal=journal,
        year=year,
        volume=volume,
        issue=_optional_str(data.get("issue")),
        pages=_optional_str(data.get("pages")),
        doi=_optional_str(data.get("doi")),
    )


def _book_from_dict(data: dict[str, Any]) -> Book:
    return Book(
        authors=_authors(data.get("authors")),
        title=required_str(data, "title"),
        publisher=required_str(data, "publisher"),
        year=_year(data.get("year")),
        edition=_optional_str(data.get("edition")),
    )


def _authors(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("authors must be a non-empty list of strings")
    authors = []
    for author in value:
        if not isinstance(author, str) or not author.strip():
            raise ValueError("authors must be a non-empty list of strings")
        authors.append(author)
    return authors


def _optional_str(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("optional citation fields must be strings when provided")
    return value


def _optional_metadata_str(value: Any, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(
            "optional source provenance fields must be strings when provided"
        )
    return value


def _year(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("year must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("year must be an integer") from exc


def _reference_type(reference: JournalArticle | Book) -> str:
    if isinstance(reference, JournalArticle):
        return "journal"
    if isinstance(reference, Book):
        return "book"
    raise ValueError("source reference must be structured journal or book metadata")

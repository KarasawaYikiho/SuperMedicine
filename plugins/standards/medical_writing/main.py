"""Executable entrypoint for the medical-writing manifest plugin."""

from __future__ import annotations

from typing import Any

from plugins.base_plugin import plugin_result
from plugins.standards.medical_citation.utils import CitationSource

from .checklist_base import HUMAN_REVIEW_MESSAGE, MedicalClaim
from .checklists import get_consort_checklist, get_strobe_checklist
from .prisma import PRISMAChecklist
from .stard import STARDChecklist


PLUGIN_NAME = "medical-writing"
MEDICAL_BOUNDARY = (
    "Medical writing output is for drafting and reporting-quality review only; "
    "it is not clinical advice and requires human expert review before research, "
    "regulatory, or clinical use."
)

ACTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "standard.consort": {
        "required_params": {"text": "str"},
        "optional_params": {
            "claims": "list[dict|MedicalClaim]",
            "sources": "dict[str, CitationSource|dict|str]",
        },
        "output_fields": [
            "standard",
            "version",
            "total_items",
            "found_items",
            "compliance_rate",
            "details",
            "human_review_message",
        ],
    },
    "standard.strobe": {
        "required_params": {"text": "str"},
        "optional_params": {
            "claims": "list[dict|MedicalClaim]",
            "sources": "dict[str, CitationSource|dict|str]",
        },
        "output_fields": [
            "standard",
            "version",
            "total_items",
            "found_items",
            "compliance_rate",
            "details",
            "human_review_message",
        ],
    },
    "standard.prisma": {
        "required_params": {"text": "str"},
        "optional_params": {
            "claims": "list[dict|MedicalClaim]",
            "sources": "dict[str, CitationSource|dict|str]",
        },
        "output_fields": [
            "standard",
            "version",
            "total_items",
            "found_items",
            "compliance_rate",
            "details",
            "human_review_message",
        ],
    },
    "standard.stard": {
        "required_params": {"text": "str"},
        "optional_params": {
            "claims": "list[dict|MedicalClaim]",
            "sources": "dict[str, CitationSource|dict|str]",
        },
        "output_fields": [
            "standard",
            "version",
            "total_items",
            "found_items",
            "compliance_rate",
            "details",
            "human_review_message",
        ],
    },
}


def execute(
    action: str,
    params: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute supported medical writing checklist actions."""
    params = params or {}
    context = context or {}
    metadata = _base_metadata(context)

    try:
        checklist = _checklist_for_action(action)
        if checklist is None:
            return plugin_result(
                status="plugin_error",
                plugin=PLUGIN_NAME,
                action=action,
                error=f"Unsupported medical-writing action: {action}",
                metadata=metadata,
            )

        text = _required_text(params)
        claims = _claims_from_params(params.get("claims"))
        sources = _sources_from_params(params.get("sources"))
        output = checklist.check(text, claims=claims, sources=sources)
        output.setdefault("human_review_message", HUMAN_REVIEW_MESSAGE)
        output.setdefault("medical_boundary", MEDICAL_BOUNDARY)
    except (TypeError, ValueError) as exc:
        return plugin_result(
            status="plugin_error",
            plugin=PLUGIN_NAME,
            action=action,
            error=f"Invalid medical-writing input: {exc}",
            metadata=metadata,
        )

    return plugin_result(
        status="success",
        plugin=PLUGIN_NAME,
        action=action,
        output=output,
        metadata=metadata,
    )


def _checklist_for_action(action: str):
    if action == "standard.consort":
        return get_consort_checklist()
    if action == "standard.strobe":
        return get_strobe_checklist()
    if action == "standard.prisma":
        return PRISMAChecklist()
    if action == "standard.stard":
        return STARDChecklist()
    return None


def _base_metadata(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "medical_boundary": MEDICAL_BOUNDARY,
        "not_for_clinical_advice": True,
        "requires_human_review": True,
        "human_review_message": HUMAN_REVIEW_MESSAGE,
        "resource": {"kind": "standard", "plugin": PLUGIN_NAME},
        "security": {
            "permission_entrypoint": "kernel",
            "permission_checked": bool(context),
        },
        "contract": {
            "actions": ACTION_CONTRACTS,
            "provider_contract": "medical-writing-checklist",
        },
        "audit": {
            "context_keys": sorted(context.keys()),
            "citation_fabrication": "not_generated",
        },
    }


def _required_text(params: dict[str, Any]) -> str:
    text = params.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    return text


def _claims_from_params(value: Any) -> list[MedicalClaim] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("claims must be a list when provided")

    claims: list[MedicalClaim] = []
    for item in value:
        if isinstance(item, MedicalClaim):
            claims.append(item)
            continue
        if not isinstance(item, dict):
            raise ValueError(
                "claims entries must be dictionaries or MedicalClaim objects"
            )
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("claim text must be a non-empty string")
        claim_type = item.get("claim_type", "fact")
        if not isinstance(claim_type, str) or not claim_type.strip():
            raise ValueError("claim_type must be a non-empty string when provided")
        source_id = item.get("source_id")
        if source_id is not None and not isinstance(source_id, str):
            raise ValueError("claim source_id must be a string when provided")
        confidence = item.get("confidence")
        if confidence is not None and not isinstance(confidence, (int, float)):
            raise ValueError("claim confidence must be numeric when provided")
        claims.append(
            MedicalClaim(
                text=text,
                claim_type=claim_type,
                source_id=source_id,
                confidence=confidence,
            )
        )
    return claims


def _sources_from_params(value: Any) -> dict[str, CitationSource] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("sources must be a dictionary when provided")

    sources: dict[str, CitationSource] = {}
    for key, item in value.items():
        source_id = str(key)
        if isinstance(item, CitationSource):
            sources[source_id] = item
            continue
        if isinstance(item, str):
            sources[source_id] = CitationSource(source_id=source_id, reference=item)
            continue
        if not isinstance(item, dict):
            raise ValueError(
                "sources entries must be dictionaries, strings, or CitationSource objects"
            )
        declared_id = item.get("source_id", source_id)
        if declared_id != source_id:
            raise ValueError("source_id must match its sources dictionary key")
        reference = item.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("source reference must be a non-empty string")
        confidence = item.get("confidence", 1.0)
        if not isinstance(confidence, (int, float)):
            raise ValueError("source confidence must be numeric when provided")
        valid = item.get("valid", True)
        if not isinstance(valid, bool):
            raise ValueError("source valid must be boolean when provided")
        note = item.get("note", "")
        if not isinstance(note, str):
            raise ValueError("source note must be a string when provided")
        sources[source_id] = CitationSource(
            source_id=source_id,
            reference=reference,
            confidence=float(confidence),
            valid=valid,
            note=note,
        )
    return sources

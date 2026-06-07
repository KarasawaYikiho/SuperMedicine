"""规范检查清单基类"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from plugins.standards.medical_citation.utils import (
    CitationSource,
    citation_provenance_from_source,
    citation_state_from_validation,
    validate_source_id,
)


HUMAN_REVIEW_MESSAGE = (
    "Human review required: medical writing output is for drafting and quality "
    "review only, not clinical advice or a substitute for professional judgment."
)
MEDICAL_FACT_KEYWORDS = (
    "治疗",
    "诊断",
    "风险",
    "死亡",
    "有效",
    "敏感度",
    "特异度",
    "adverse",
    "diagnosis",
    "treatment",
    "mortality",
    "risk",
    "effective",
    "sensitivity",
    "specificity",
)


@dataclass
class ChecklistItemBase:
    """检查条目基类"""

    id: int | str
    section: str
    item: str
    description: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class MedicalClaim:
    """医学写作输出中的单条声明。"""

    text: str
    claim_type: str = "fact"
    source_id: str | None = None
    confidence: float | None = None
    claim_id: str | None = None
    location: str = ""
    verification_status: str = "not_checked"
    suggested_fix: str = ""


def _infer_claim_type(sentence: str) -> str:
    sentence_lower = sentence.lower()
    if any(
        term in sentence_lower for term in ("局限", "limitation", "limited", "不足")
    ):
        return "limitation"
    if any(
        term in sentence_lower
        for term in ("建议", "应考虑", "suggest", "recommend", "may consider")
    ):
        return "suggestion"
    if any(
        term in sentence_lower
        for term in ("可能", "提示", "推测", "inference", "may", "might", "suggests")
    ):
        return "inference"
    return "fact"


def _split_claim_sentences(text: str) -> list[str]:
    separators = "。；;\n"
    normalized = text
    for separator in separators:
        normalized = normalized.replace(separator, "|")
    return [part.strip() for part in normalized.split("|") if part.strip()]


def annotate_medical_claims(
    claims: list[MedicalClaim] | None = None, text: str = ""
) -> list[dict[str, Any]]:
    """标注医学写作声明的 fact/inference/suggestion/limitation 类型。"""
    if claims is None:
        claims = [
            MedicalClaim(text=sentence, claim_type=_infer_claim_type(sentence))
            for sentence in _split_claim_sentences(text)
        ]

    annotations: list[dict[str, Any]] = []
    for index, claim in enumerate(claims, start=1):
        annotations.append(
            {
                "claim_id": claim.claim_id or f"C{index:03d}",
                "text": claim.text,
                "claim_type": claim.claim_type,
                "source_id": claim.source_id,
                "confidence": claim.confidence,
                "location": claim.location,
                "verification_status": claim.verification_status,
                "suggested_fix": claim.suggested_fix,
            }
        )
    return annotations


def _citation_issue_type(validation_status: str, source_id: object) -> str | None:
    if validation_status == "ok":
        return None
    if validation_status == "warning":
        return "low_confidence_source"
    if not source_id:
        return "missing_source_id"
    return "source_unavailable_or_invalid"


def _claim_audit_summary(annotations: list[dict[str, Any]]) -> dict[str, Any]:
    required = [
        annotation for annotation in annotations if annotation["requires_citation"]
    ]
    blocked = [
        annotation
        for annotation in required
        if annotation.get("citation_status") == "error"
    ]
    needs_review = [
        annotation
        for annotation in required
        if annotation.get("citation_status") == "warning"
    ]
    linked = [
        annotation
        for annotation in required
        if annotation.get("citation_status") == "ok"
    ]
    return {
        "audit_mode": "provided_sources_only",
        "network_lookup_performed": False,
        "total_claims": len(annotations),
        "citation_required_claims": len(required),
        "linked_claims": len(linked),
        "needs_human_review_claims": len(needs_review),
        "blocked_claims": len(blocked),
        "gate_status": "blocked"
        if blocked
        else "review_required"
        if needs_review
        else "pass",
    }


def enforce_medical_accuracy(
    claims: list[MedicalClaim] | None = None,
    sources: dict[str, CitationSource] | None = None,
    *,
    text: str = "",
) -> dict[str, Any]:
    """对需引用医学事实施加来源 ID 与置信度约束。"""
    if claims is None:
        claims = [
            MedicalClaim(text=sentence, claim_type=_infer_claim_type(sentence))
            for sentence in _split_claim_sentences(text)
        ]

    annotations = annotate_medical_claims(claims)
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    source_states: list[dict[str, object]] = []

    for annotation in annotations:
        claim_text = str(annotation["text"])
        claim_type = str(annotation["claim_type"])
        requires_citation = claim_type == "fact" and any(
            keyword in claim_text.lower() for keyword in MEDICAL_FACT_KEYWORDS
        )
        annotation["requires_citation"] = requires_citation

        if not requires_citation:
            continue

        validation = validate_source_id(annotation.get("source_id"), sources)
        state = citation_state_from_validation(validation)
        source_states.append(state)
        annotation["citation_status"] = validation.status
        annotation["citation_issue_type"] = _citation_issue_type(
            validation.status, annotation.get("source_id")
        )
        annotation["source_provenance"] = citation_provenance_from_source(
            (sources or {}).get(str(annotation.get("source_id")))
            if annotation.get("source_id")
            else None
        )

        issue = {
            "claim_id": annotation["claim_id"],
            "claim": claim_text,
            "citation_issue_type": annotation["citation_issue_type"],
            **state,
        }
        if validation.status == "error":
            errors.append(issue)
        elif validation.status == "warning":
            warnings.append(issue)

    return {
        "claim_annotations": annotations,
        "citation_warnings": warnings,
        "citation_errors": errors,
        "source_states": source_states,
        "claim_audit_summary": _claim_audit_summary(annotations),
        "human_review_message": HUMAN_REVIEW_MESSAGE,
    }


class ChecklistBase:
    """规范检查清单基类"""

    def __init__(self, name: str, version: str, items: list[ChecklistItemBase]):
        self.name = name
        self.version = version
        self.items = items

    def check(
        self,
        text: str,
        claims: list[MedicalClaim] | None = None,
        sources: dict[str, CitationSource] | None = None,
    ) -> dict[str, Any]:
        """检查文本是否符合规范"""
        results: list[dict[str, Any]] = []
        text_lower = text.lower()

        for item in self.items:
            found = any(kw.lower() in text_lower for kw in item.keywords)
            results.append(
                {
                    "item_id": item.id,
                    "section": item.section,
                    "item": item.item,
                    "found": found,
                }
            )

        total = len(results)
        found_items = sum(1 for r in results if r["found"])

        result = {
            "standard": self.name,
            "version": self.version,
            "total_items": total,
            "found_items": found_items,
            "compliance_rate": round(found_items / total * 100, 1) if total > 0 else 0,
            "details": results,
        }
        result.update(enforce_medical_accuracy(claims, sources, text=text))
        return result

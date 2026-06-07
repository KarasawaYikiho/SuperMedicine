from __future__ import annotations

from plugins.standards.medical_writing.checklists import (
    get_consort_checklist,
    get_strobe_checklist,
)
from plugins.standards.medical_writing.checklist_base import MedicalClaim
from plugins.standards.medical_writing.main import execute
from plugins.standards.medical_citation.utils import CitationSource, JournalArticle


class TestConsortChecklist:
    def test_checklist_loaded(self):
        checklist = get_consort_checklist()
        assert checklist.name == "CONSORT"
        assert len(checklist.items) > 0

    def test_check_with_consort_text(self):
        checklist = get_consort_checklist()
        text = "本研究是一项随机对照试验，采用结构化摘要，描述了科学背景和目的"
        result = checklist.check(text)
        assert result["standard"] == "CONSORT"
        assert result["total_items"] > 0
        assert result["found_items"] > 0

    def test_check_empty_text(self):
        checklist = get_consort_checklist()
        result = checklist.check("")
        assert result["found_items"] == 0

    def test_medical_claims_are_classified_and_review_message_present(self):
        checklist = get_consort_checklist()
        claims = [
            MedicalClaim("治疗有效", "fact", "src-1"),
            MedicalClaim("结果可能提示获益", "inference"),
            MedicalClaim("建议进行人工复核", "suggestion"),
            MedicalClaim("局限性包括样本量较小", "limitation"),
        ]
        sources = {
            "src-1": CitationSource(
                "src-1",
                JournalArticle(["John Smith"], "Trial", "JAMA", 2024, "331"),
            )
        }

        result = checklist.check("随机对照试验", claims=claims, sources=sources)

        claim_types = {claim["claim_type"] for claim in result["claim_annotations"]}
        assert {"fact", "inference", "suggestion", "limitation"}.issubset(claim_types)
        assert result["citation_errors"] == []
        assert "not clinical advice" in result["human_review_message"]

    def test_missing_citation_for_medical_fact_returns_error_without_fabrication(self):
        checklist = get_consort_checklist()
        claims = [MedicalClaim("该治疗有效并降低死亡风险", "fact")]

        result = checklist.check("随机对照试验", claims=claims, sources={})

        assert result["citation_errors"][0]["status"] == "error"
        assert result["source_states"][0]["source_id"] is None
        assert "not generated" in result["citation_errors"][0]["message"]

    def test_invalid_source_returns_error(self):
        checklist = get_consort_checklist()
        claims = [MedicalClaim("诊断特异度为90%", "fact", "bad-src")]
        sources = {
            "bad-src": CitationSource("bad-src", "Retracted record", valid=False)
        }

        result = checklist.check("随机对照试验", claims=claims, sources=sources)

        assert result["citation_errors"][0]["source_id"] == "bad-src"
        assert result["citation_errors"][0]["status"] == "error"

    def test_low_confidence_source_returns_observable_warning(self):
        checklist = get_consort_checklist()
        claims = [MedicalClaim("治疗有效", "fact", "low-src")]
        sources = {
            "low-src": CitationSource("low-src", "Unverified source", confidence=0.4)
        }

        result = checklist.check("随机对照试验", claims=claims, sources=sources)

        assert result["citation_warnings"][0]["source_id"] == "low-src"
        assert result["source_states"][0]["confidence"] == 0.4

    def test_claim_ledger_provenance_and_audit_summary_are_reported(self):
        checklist = get_consort_checklist()
        claims = [
            MedicalClaim(
                text="该治疗有效并降低死亡风险",
                claim_type="fact",
                source_id="src-1",
                claim_id="claim-treatment-1",
                location="discussion paragraph 2",
                verification_status="human_checked",
                suggested_fix="",
            )
        ]
        sources = {
            "src-1": CitationSource(
                source_id="src-1",
                reference="User supplied trial summary",
                source_type="uploaded_document",
                location="source.pdf p. 4",
                authority="peer_reviewed_article",
                verification_status="provided_by_user",
            )
        }

        result = checklist.check("随机对照试验", claims=claims, sources=sources)

        annotation = result["claim_annotations"][0]
        assert annotation["claim_id"] == "claim-treatment-1"
        assert annotation["location"] == "discussion paragraph 2"
        assert annotation["verification_status"] == "human_checked"
        assert annotation["suggested_fix"] == ""
        assert annotation["source_provenance"] == {
            "source_id": "src-1",
            "source_type": "uploaded_document",
            "location": "source.pdf p. 4",
            "authority": "peer_reviewed_article",
            "verification_status": "provided_by_user",
            "confidence": 1.0,
            "valid": True,
        }
        assert result["claim_audit_summary"] == {
            "audit_mode": "provided_sources_only",
            "network_lookup_performed": False,
            "total_claims": 1,
            "citation_required_claims": 1,
            "linked_claims": 1,
            "needs_human_review_claims": 0,
            "blocked_claims": 0,
            "gate_status": "pass",
        }

    def test_claim_audit_summary_blocks_missing_required_source(self):
        checklist = get_consort_checklist()
        claims = [
            MedicalClaim(
                text="该治疗有效并降低死亡风险",
                claim_type="fact",
                claim_id="claim-without-source",
                location="abstract",
                suggested_fix="Add a supported source before export.",
            )
        ]

        result = checklist.check("随机对照试验", claims=claims, sources={})

        assert result["claim_annotations"][0]["claim_id"] == "claim-without-source"
        assert result["claim_annotations"][0]["location"] == "abstract"
        assert (
            result["claim_annotations"][0]["suggested_fix"]
            == "Add a supported source before export."
        )
        assert result["claim_annotations"][0]["source_provenance"]["valid"] is False
        assert (
            result["citation_errors"][0]["citation_issue_type"] == "missing_source_id"
        )
        assert result["claim_audit_summary"]["network_lookup_performed"] is False
        assert result["claim_audit_summary"]["gate_status"] == "blocked"


class TestStrobeChecklist:
    def test_checklist_loaded(self):
        checklist = get_strobe_checklist()
        assert checklist.name == "STROBE"
        assert len(checklist.items) > 0

    def test_check_with_strobe_text(self):
        checklist = get_strobe_checklist()
        text = "这是一项队列研究，描述了研究设计和参与者选择标准"
        result = checklist.check(text)
        assert result["standard"] == "STROBE"
        assert result["total_items"] > 0


class TestMedicalWritingPluginSafetyMetadata:
    def test_execute_includes_machine_readable_review_and_advice_boundaries(self):
        result = execute("standard.consort", {"text": "随机对照试验采用结构化摘要"})

        assert result["status"] == "success"
        assert result["metadata"]["requires_human_review"] is True
        assert result["metadata"]["not_for_clinical_advice"] is True
        assert result["output"]["human_review_message"]

    def test_execute_accepts_optional_claim_audit_fields(self):
        result = execute(
            "standard.consort",
            {
                "text": "随机对照试验采用结构化摘要",
                "claims": [
                    {
                        "text": "该治疗有效",
                        "claim_type": "fact",
                        "source_id": "src-1",
                        "claim_id": "C-TREATMENT",
                        "location": "results",
                        "verification_status": "provided_not_rechecked",
                        "suggested_fix": "",
                    }
                ],
                "sources": {
                    "src-1": {
                        "reference": "Provided manuscript source",
                        "source_type": "doc_only",
                        "location": "appendix table 1",
                        "authority": "user_provided_document",
                        "verification_status": "provided_not_rechecked",
                    }
                },
            },
        )

        assert result["status"] == "success"
        annotation = result["output"]["claim_annotations"][0]
        assert annotation["claim_id"] == "C-TREATMENT"
        assert annotation["source_provenance"]["source_type"] == "doc_only"
        assert result["output"]["claim_audit_summary"]["gate_status"] == "pass"

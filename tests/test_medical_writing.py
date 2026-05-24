from plugins.standards.medical_writing.checklists import get_consort_checklist, get_strobe_checklist
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
        sources = {"bad-src": CitationSource("bad-src", "Retracted record", valid=False)}

        result = checklist.check("随机对照试验", claims=claims, sources=sources)

        assert result["citation_errors"][0]["source_id"] == "bad-src"
        assert result["citation_errors"][0]["status"] == "error"

    def test_low_confidence_source_returns_observable_warning(self):
        checklist = get_consort_checklist()
        claims = [MedicalClaim("治疗有效", "fact", "low-src")]
        sources = {"low-src": CitationSource("low-src", "Unverified source", confidence=0.4)}

        result = checklist.check("随机对照试验", claims=claims, sources=sources)

        assert result["citation_warnings"][0]["source_id"] == "low-src"
        assert result["source_states"][0]["confidence"] == 0.4


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

from __future__ import annotations

from plugins.standards.medical_citation.ama_format import (
    AMAFormatter,
    JournalArticle,
    Book,
)
from plugins.standards.medical_citation.main import execute
from plugins.standards.medical_citation.vancouver_format import VancouverFormatter
from plugins.standards.medical_citation.utils import (
    CitationSource,
    citation_provenance_from_source,
    validate_source_id,
)


class TestAMAFormatter:
    def test_journal_article(self):
        formatter = AMAFormatter()
        article = JournalArticle(
            authors=["John Smith", "Jane Doe"],
            title="Cardiovascular Risk Factors",
            journal="JAMA",
            year=2024,
            volume="331",
            issue="5",
            pages="401-410",
            doi="10.1001/jama.2024.1234",
        )
        result = formatter.format_journal(article)
        assert "Smith J" in result
        assert "Doe J" in result
        assert "JAMA" in result
        assert "2024" in result

    def test_book(self):
        formatter = AMAFormatter()
        book = Book(
            authors=["Robert Jones"],
            title="Medical Statistics",
            publisher="Springer",
            year=2023,
            edition="3rd",
        )
        result = formatter.format_book(book)
        assert "Jones R" in result
        assert "Medical Statistics" in result


class TestVancouverFormatter:
    def test_journal_article(self):
        formatter = VancouverFormatter()
        article = JournalArticle(
            authors=["John Smith", "Jane Doe"],
            title="Cardiovascular Risk Factors",
            journal="JAMA",
            year=2024,
            volume="331",
            issue="5",
            pages="401-410",
        )
        result = formatter.format_journal(article)
        assert "Smith J" in result
        assert "JAMA" in result


class TestCitationAccuracy:
    def test_ama_and_vancouver_snapshots_keep_only_declared_doi_difference(self):
        article = JournalArticle(
            authors=["John Smith", "Jane Doe"],
            title="Cardiovascular Risk Factors",
            journal="JAMA",
            year=2024,
            volume="331",
            issue="5",
            pages="401-410",
            doi="10.1001/jama.2024.1234",
        )

        assert VancouverFormatter().format_journal(article) == (
            "Smith J, Doe J. Cardiovascular Risk Factors. JAMA. 2024;331(5):401-410."
        )
        assert AMAFormatter().format_journal(article) == (
            "Smith J, Doe J. Cardiovascular Risk Factors. JAMA. 2024;331(5):401-410. "
            "doi:10.1001/jama.2024.1234"
        )

    def test_formatter_models_are_shared(self):
        article = JournalArticle(
            authors=["John Smith"],
            title="Cardiovascular Risk Factors",
            journal="JAMA",
            year=2024,
            volume="331",
        )

        assert AMAFormatter().format_journal(article)
        assert VancouverFormatter().format_journal(article)

    def test_missing_source_id_is_error_and_does_not_generate_citation(self):
        result = validate_source_id(None, {})

        assert result.status == "error"
        assert result.source_id is None
        assert "not generated" in result.message

    def test_unknown_source_id_is_error(self):
        result = validate_source_id("unknown", {})

        assert result.status == "error"
        assert "Unknown source_id" in result.message

    def test_low_confidence_source_is_warning(self):
        sources = {"src-1": CitationSource("src-1", "Reference", confidence=0.5)}

        result = validate_source_id("src-1", sources)

        assert result.status == "warning"
        assert result.confidence == 0.5

    def test_citation_source_provenance_defaults_are_stable(self):
        source = CitationSource("src-1", "Reference")

        provenance = citation_provenance_from_source(source)

        assert provenance == {
            "source_id": "src-1",
            "source_type": "provided_source",
            "location": "",
            "authority": "unspecified",
            "verification_status": "provided_not_rechecked",
            "confidence": 1.0,
            "valid": True,
        }

    def test_citation_source_provenance_uses_supplied_metadata(self):
        source = CitationSource(
            source_id="src-1",
            reference="Reference",
            confidence=0.8,
            valid=True,
            source_type="uploaded_pdf",
            location="p. 12",
            authority="systematic_review",
            verification_status="human_checked",
        )

        provenance = citation_provenance_from_source(source)

        assert provenance["source_id"] == "src-1"
        assert provenance["source_type"] == "uploaded_pdf"
        assert provenance["location"] == "p. 12"
        assert provenance["authority"] == "systematic_review"
        assert provenance["verification_status"] == "human_checked"
        assert provenance["confidence"] == 0.8
        assert provenance["valid"] is True

    def test_missing_source_provenance_is_explicitly_unavailable(self):
        provenance = citation_provenance_from_source(None)

        assert provenance["source_id"] is None
        assert provenance["verification_status"] == "source_not_available"
        assert provenance["valid"] is False


class TestMedicalCitationPluginEntry:
    def test_ama_action_formats_valid_structured_source(self):
        result = execute(
            "standard.citation.ama",
            {
                "source_id": "src-1",
                "sources": {
                    "src-1": {
                        "reference_type": "journal",
                        "authors": ["John Smith", "Jane Doe"],
                        "title": "Cardiovascular Risk Factors",
                        "journal": "JAMA",
                        "year": 2024,
                        "volume": "331",
                        "issue": "5",
                        "pages": "401-410",
                        "doi": "10.1001/jama.2024.1234",
                    }
                },
            },
        )

        assert result["status"] == "success"
        assert result["plugin"] == "medical-citation"
        assert result["action"] == "standard.citation.ama"
        assert result["metadata"]["requires_human_review"] is True
        assert result["metadata"]["not_for_clinical_advice"] is True
        assert result["output"]["requires_human_review"] is True
        assert result["output"]["not_for_clinical_advice"] is True
        assert "Smith J" in result["output"]["citation"]
        assert "doi:10.1001/jama.2024.1234" in result["output"]["citation"]

    def test_missing_source_returns_structured_plugin_error_without_citation(self):
        result = execute("standard.citation.ama", {"sources": {}})

        assert result["status"] == "plugin_error"
        assert result["output"] is None
        assert (
            "citation was not generated" in result["error"]
            or "sources must be" in result["error"]
        )

    def test_skill_doc_formatter_example_uses_journal_article_model(self):
        doc_path = (
            __import__("pathlib").Path(__file__).parent.parent
            / "adapters"
            / "opencode"
            / "skills"
            / "medical-citation.md"
        )
        content = doc_path.read_text(encoding="utf-8")

        assert "JournalArticle" in content
        assert "formatter.format_journal(JournalArticle(" in content
        assert 'volume="331"' in content
        assert "source_id" in content

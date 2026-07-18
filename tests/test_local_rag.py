from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from permission.engine import PermissionEngine
from core.config_center import ConfigCenter
from core.rag_service import RAGService
from plugins.rag.interface import RAGProviderConfig
from plugins.rag.local_provider import LocalRAGProvider, MockExternalVectorStoreProvider
from plugins.rag import main as rag_main
from plugins.rag.pubmed_provider import PubmedRAGProvider


def _pubmed_engine_for(agent_id: str, allowed: bool) -> PermissionEngine:
    policy_dir = Path(tempfile.mkdtemp()) / "policies"
    policy_dir.mkdir()
    permissions = {
        "allowed": [
            {
                "action": "rag.external.query",
                "scope": "https://eutils.ncbi.nlm.nih.gov/*",
            }
        ]
        if allowed
        else [],
        "denied": [] if allowed else [{"action": "rag.external.query", "scope": "*"}],
        "hard_limits": {"network_access": True, "external_api": True},
    }
    (policy_dir / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
        yaml.dump(
            {
                "agent_id": agent_id,
                "role": "rag-test",
                "permissions": permissions,
            }
        ),
        encoding="utf-8",
    )
    return PermissionEngine(policy_dir, policy_dir / "audit.jsonl")


class TestLocalRAGProvider:
    def test_query_without_explicit_documents_returns_an_empty_local_index(self, tmp_path):
        result = rag_main.execute(
            "rag.query",
            {"query": "hypertension", "storage_dir": str(tmp_path / "rag")},
            {"agent_id": "alpha", "permission_checked": True},
        )

        assert result["status"] == "success"
        assert result["output"]["items"] == []

    def test_add_and_query(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        provider.add_document("心血管疾病的危险因素包括高血压和糖尿病")
        provider.add_document("肿瘤免疫治疗是近年来的研究热点")
        provider.add_document("心血管疾病的预防措施包括健康饮食和运动")

        result = provider.query("心血管疾病")
        assert len(result["results"]) > 0
        assert result["relevance_scores"][0] > 0
        assert result["items"][0]["id"] is not None
        assert "score" in result["items"][0]
        assert "snippet" in result["items"][0]

    def test_readding_identical_document_does_not_grow_the_index(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)

        provider.add_document("hypertension evidence", {"source": "fixture"})
        provider.add_document("hypertension evidence", {"source": "fixture"})

        assert len(json.loads((tmp_path / "documents.json").read_text("utf-8"))) == 1

    def test_query_excludes_zero_score_documents(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        provider.add_document("hypertension evidence")
        provider.add_document("oncology immunotherapy")

        result = provider.query("hypertension")

        assert [item["snippet"] for item in result["items"]] == [
            "hypertension evidence"
        ]

    def test_tokenizer_uses_cjk_bigrams_and_preserves_medical_abbreviations(self, tmp_path):
        tokens = LocalRAGProvider(tmp_path)._tokenize("高血压与ACEI治疗 2024")

        assert "高血" in tokens
        assert "血压" in tokens
        assert "acei" in tokens
        assert "2024" in tokens

    def test_index_records_and_results_preserve_traceable_source_fields(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        provider.add_document(
            "ACEI evidence for hypertension",
            {
                "document_id": "paper-1",
                "chunk_id": "paper-1:7",
                "source_type": "paper",
                "source_path": "paper.pdf",
                "page": 7,
                "section": "Results",
            },
        )

        item = provider.query("ACEI hypertension")["items"][0]

        assert item["document_id"] == "paper-1"
        assert item["chunk_id"] == "paper-1:7"
        assert item["source_path"] == "paper.pdf"
        assert item["page"] == 7
        assert item["content_hash"]
        assert item["created_at"]

    def test_replace_and_remove_document_chunks_are_idempotent(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        provider.add_document("old hypertension text", {"document_id": "paper-1"})
        provider.replace_document(
            "paper-1",
            [("new oncology text", {"chunk_id": "paper-1:1"})],
        )

        assert provider.query("old hypertension")["items"] == []
        assert provider.query("new oncology")["items"][0]["document_id"] == "paper-1"
        assert provider.remove_document("paper-1") == 1
        assert provider.remove_document("paper-1") == 0

    def test_empty_query(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        result = provider.query("test")
        assert result["results"] == []

    def test_context_store_retrieve(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        provider.store_context("project_1", {"name": "test", "data": [1, 2, 3]})
        result = provider.retrieve_context("project_1")
        assert result is not None
        assert result["name"] == "test"

    def test_context_key_rejects_path_traversal(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)

        for key in (
            "../escape",
            "..\\escape",
            "/tmp/escape",
            "C:\\escape",
            "nested/key",
        ):
            try:
                provider.store_context(key, {"blocked": True})
                assert False, f"unsafe key should be rejected: {key}"
            except ValueError:
                pass

        assert not (tmp_path / "escape.json").exists()

    def test_context_key_retrieve_rejects_path_traversal(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)

        try:
            provider.retrieve_context("../escape")
            assert False, "unsafe key should be rejected"
        except ValueError:
            pass

    def test_context_not_found(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        assert provider.retrieve_context("nonexistent") is None


def test_rag_service_truncates_sources_to_configured_context_budget(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "rag:\n  top_k: 5\n  min_score: 0\n  max_context_chars: 40\n",
        encoding="utf-8",
    )
    provider = LocalRAGProvider(tmp_path / ".supermedicine" / "rag" / "local")
    provider.add_document("hypertension " + "evidence " * 20)

    context = RAGService(ConfigCenter(config_path), config_path).retrieve(
        "hypertension evidence"
    )

    assert sum(len(item["snippet"]) for item in context.sources) <= 40


def test_medical_writing_and_citation_are_classified_as_knowledge_generation():
    assert RAGService.classify_task("CONSORT", "medical-writing", "standard.consort") == "knowledge_generation"
    assert RAGService.classify_task("AMA", "medical-citation", "standard.citation.ama") == "knowledge_generation"


def test_pubmed_denial_uses_local_results_as_degraded_without_http(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("rag:\n  provider: hybrid\n  min_score: 0\n", encoding="utf-8")
    LocalRAGProvider(tmp_path / ".supermedicine" / "rag" / "local").add_document(
        "local hypertension evidence", {"source": "local-paper"}
    )
    monkeypatch.setattr(
        PubmedRAGProvider,
        "_search",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("HTTP path must not run after permission denial")
        ),
    )

    context = RAGService(
        ConfigCenter(config_path),
        config_path,
        permission_engine=_pubmed_engine_for("alpha", False),
    ).retrieve("hypertension")

    assert context.status == "degraded"
    assert context.sources[0]["source"] == "local-paper"
    assert context.errors[0]["code"] == "permission_denied"


class TestPubmedRAGProvider:
    """测试 PubMed RAG Provider"""

    def test_query_empty_result_on_failure(self):
        """API 失败时返回空结果"""
        provider = PubmedRAGProvider(
            permission_engine=_pubmed_engine_for("alpha", True), agent_id="alpha"
        )
        with patch.object(provider, "_search", side_effect=Exception("network error")):
            result = provider.query("test query")
            assert result["results"] == []
            assert result["relevance_scores"] == []
            assert result["source_metadata"] == []
            assert result["status"] == "error"
            assert result["errors"][0]["code"] == "connection_error"

    def test_query_with_mock_results(self):
        """模拟 API 返回结果"""
        provider = PubmedRAGProvider(
            permission_engine=_pubmed_engine_for("alpha", True), agent_id="alpha"
        )

        # Mock _search 返回一些 PMIDs
        mock_ids = ["12345", "67890"]

        # Mock _fetch 返回文章数据
        mock_articles = [
            {
                "pmid": "12345",
                "title": "Test Article 1",
                "authors": "Smith J, Doe J",
                "journal": "J Test Med",
                "year": "2024",
                "doi": "10.1234/test.1",
                "abstract": "This is a test abstract for article 1.",
            },
            {
                "pmid": "67890",
                "title": "Test Article 2",
                "authors": "Brown K",
                "journal": "Test Journal",
                "year": "2023",
                "doi": "10.1234/test.2",
                "abstract": "This is a test abstract for article 2.",
            },
        ]

        with patch.object(provider, "_search", return_value=mock_ids):
            with patch.object(provider, "_fetch", return_value=mock_articles):
                result = provider.query("test query")

        assert len(result["results"]) == 2
        assert result["results"][0] == "This is a test abstract for article 1."
        assert result["results"][1] == "This is a test abstract for article 2."
        assert len(result["source_metadata"]) == 2
        assert result["source_metadata"][0]["pmid"] == "12345"
        assert result["source_metadata"][0]["title"] == "Test Article 1"
        assert result["relevance_scores"][0] == 1.0
        assert result["relevance_scores"][1] == 0.95
        assert result["items"][0]["id"] == "12345"
        assert result["items"][0]["source"] == "PubMed"

    def test_context_store_retrieve(self):
        """验证上下文存取"""
        provider = PubmedRAGProvider()
        provider.store_context("key1", {"data": 123})
        assert provider.retrieve_context("key1") == {"data": 123}
        assert provider.retrieve_context("nonexistent") is None

    def test_empty_search(self):
        """空搜索结果"""
        provider = PubmedRAGProvider(
            permission_engine=_pubmed_engine_for("alpha", True), agent_id="alpha"
        )
        with patch.object(provider, "_search", return_value=[]):
            result = provider.query("no results query")
            assert result["results"] == []
            assert result["source_metadata"] == []

    def test_pubmed_external_query_permission_denied_before_http(self, tmp_path):
        """PubMed external HTTP access is policy-gated when an engine is supplied."""
        policies = tmp_path / "policies"
        policies.mkdir()
        (policies / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
            yaml.dump(
                {
                    "agent_id": "alpha",
                    "role": "restricted",
                    "permissions": {
                        "allowed": [],
                        "denied": [{"action": "rag.external.query", "scope": "*"}],
                    },
                }
            ),
            encoding="utf-8",
        )
        engine = PermissionEngine(policies, tmp_path / "audit.jsonl")
        provider = PubmedRAGProvider(permission_engine=engine, agent_id="alpha")

        with patch.object(
            provider, "_search", side_effect=AssertionError("HTTP path should not run")
        ):
            result = provider.query("blocked")

        assert result["status"] == "denied"
        assert result["errors"][0]["code"] == "permission_denied"
        assert result["metadata"]["security"]["permission_checked"] is True

    def test_pubmed_external_query_requires_permission_engine_before_http(self):
        provider = PubmedRAGProvider()

        with patch.object(
            provider, "_search", side_effect=AssertionError("HTTP path should not run")
        ):
            result = provider.query("blocked")

        assert result["status"] == "denied"
        assert result["errors"][0]["code"] == "permission_engine_required"

    def test_pubmed_external_query_requires_agent_identity_before_http(self):
        provider = PubmedRAGProvider(
            permission_engine=_pubmed_engine_for("alpha", True)
        )

        with patch.object(
            provider, "_search", side_effect=AssertionError("HTTP path should not run")
        ):
            result = provider.query("blocked")

        assert result["status"] == "denied"
        assert result["errors"][0]["code"] == "agent_identity_required"
        assert result["metadata"]["security"]["permission_checked"] is False

    def test_pubmed_url_validation_rejects_non_ncbi_endpoint(self):
        provider = PubmedRAGProvider(
            permission_engine=_pubmed_engine_for("alpha", True), agent_id="alpha"
        )

        with pytest.raises(OSError, match="outside the configured HTTPS endpoint"):
            provider._validate_pubmed_url("http://169.254.169.254/latest/meta-data")

    def test_pubmed_response_size_is_bounded(self):
        provider = PubmedRAGProvider(
            permission_engine=_pubmed_engine_for("alpha", True), agent_id="alpha"
        )

        class OversizedResponse:
            def read(self, size=None):
                return b"x" * (provider.MAX_RESPONSE_BYTES + 1)

        with pytest.raises(OSError, match="exceeded maximum supported size"):
            provider._read_limited_response(OversizedResponse())


class TestMockExternalVectorStoreProvider:
    """External vector-store contract backend tests."""

    def test_configured_backend_connects_and_queries_stable_shape(self):
        config = RAGProviderConfig(
            provider_type="external_vector",
            endpoint="mock://vector-store",
            index_name="medical-literature",
            namespace="tests",
            api_key_env="SM_RAG_API_KEY",
        )
        provider = MockExternalVectorStoreProvider(
            config,
            records=[
                {
                    "id": "doc-1",
                    "title": "Hypertension review",
                    "source": "mock-index",
                    "text": "hypertension diabetes cardiovascular risk",
                    "metadata": {"year": 2024},
                },
                {
                    "id": "doc-2",
                    "title": "Oncology review",
                    "source": "mock-index",
                    "text": "immunotherapy oncology cancer",
                },
            ],
        )

        connection = provider.connect()
        assert connection["status"] == "connected"
        result = provider.query("hypertension cardiovascular", top_k=1)

        assert result["status"] == "success"
        assert result["provider"] == "mock-external-vector-store"
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == "doc-1"
        assert result["items"][0]["title"] == "Hypertension review"
        assert result["items"][0]["score"] > 0
        assert (
            result["items"][0]["snippet"] == "hypertension diabetes cardiovascular risk"
        )
        assert result["results"] == ["hypertension diabetes cardiovascular risk"]

    def test_missing_config_is_structured_error(self):
        provider = MockExternalVectorStoreProvider(
            RAGProviderConfig(provider_type="external_vector")
        )

        result = provider.query("anything")

        assert result["status"] == "error"
        assert result["items"] == []
        assert result["errors"][0]["code"] == "configuration_error"
        assert "endpoint" in result["errors"][0]["details"]["missing"]
        assert "index_name" in result["errors"][0]["details"]["missing"]

    def test_connection_failure_is_structured_error(self):
        provider = MockExternalVectorStoreProvider(
            RAGProviderConfig(endpoint="mock://connection-error", index_name="idx")
        )

        result = provider.query("anything")

        assert result["status"] == "error"
        assert result["errors"][0]["code"] == "connection_error"
        assert result["errors"][0]["retryable"] is True

    def test_timeout_and_empty_results_are_observable(self):
        timeout_provider = MockExternalVectorStoreProvider(
            RAGProviderConfig(
                endpoint="mock://vector-store", index_name="idx", timeout_seconds=0
            ),
            records=[{"id": "doc-1", "text": "content"}],
        )
        timeout_result = timeout_provider.query("content")
        assert timeout_result["status"] == "error"
        assert timeout_result["errors"][0]["code"] == "query_timeout"

        empty_provider = MockExternalVectorStoreProvider(
            RAGProviderConfig(endpoint="mock://vector-store", index_name="idx")
        )
        empty_result = empty_provider.query("content")
        assert empty_result["status"] == "success"
        assert empty_result["items"] == []
        assert empty_result["errors"] == []

    def test_resource_error_for_excessive_timeout(self):
        provider = MockExternalVectorStoreProvider(
            RAGProviderConfig(
                endpoint="mock://vector-store", index_name="idx", timeout_seconds=121
            )
        )

        result = provider.query("content")

        assert result["status"] == "error"
        assert result["errors"][0]["code"] == "resource_error"
        assert result["errors"][0]["details"]["max_timeout_seconds"] == 120

    def test_rag_payloads_redact_raw_secret_values(self):
        sensitive_key = "api" + "_" + "key"
        token_key = "tok" + "en"
        password_key = "pass" + "word"
        raw_value = "redaction" + "-" + "payload"
        nested_value = "nested" + "-" + "payload"
        record_value = "record" + "-" + "payload"
        provider = MockExternalVectorStoreProvider(
            RAGProviderConfig(
                endpoint="mock://vector-store",
                index_name="idx",
                api_key_env="SM_RAG_API_KEY",
                metadata={
                    sensitive_key: raw_value,
                    "nested": {token_key: nested_value},
                },
            ),
            records=[
                {
                    "id": "doc-1",
                    "text": f"{sensitive_key}={record_value} content",
                    "metadata": {password_key: raw_value},
                }
            ],
        )

        result = provider.query("content")
        serialized = json.dumps(result, ensure_ascii=False)

        assert raw_value not in serialized
        assert nested_value not in serialized
        assert record_value not in serialized
        assert "SM_RAG_API_KEY" in serialized
        assert "[REDACTED]" in serialized

    def test_skill_doc_does_not_instantiate_abstract_provider(self):
        doc_path = (
            __import__("pathlib").Path(__file__).parent.parent
            / "adapters"
            / "opencode"
            / "skills"
            / "rag-query.md"
        )
        content = doc_path.read_text(encoding="utf-8")

        assert "RAGProvider()" not in content
        assert "from plugins.rag.main import execute" in content
        assert "MockExternalVectorStoreProvider" in content
        assert "RAGProviderConfig" in content

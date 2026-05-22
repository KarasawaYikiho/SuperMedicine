import pytest
from plugins.rag.local_provider import LocalRAGProvider


class TestLocalRAGProvider:
    def test_add_and_query(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        provider.add_document("心血管疾病的危险因素包括高血压和糖尿病")
        provider.add_document("肿瘤免疫治疗是近年来的研究热点")
        provider.add_document("心血管疾病的预防措施包括健康饮食和运动")

        result = provider.query("心血管疾病")
        assert len(result["results"]) > 0
        assert result["relevance_scores"][0] > 0

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

    def test_context_not_found(self, tmp_path):
        provider = LocalRAGProvider(tmp_path)
        assert provider.retrieve_context("nonexistent") is None

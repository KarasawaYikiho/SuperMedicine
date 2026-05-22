from unittest.mock import patch, MagicMock

from plugins.rag.local_provider import LocalRAGProvider
from plugins.rag.pubmed_provider import PubmedRAGProvider


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


class TestPubmedRAGProvider:
    """测试 PubMed RAG Provider"""

    def test_query_empty_result_on_failure(self):
        """API 失败时返回空结果"""
        provider = PubmedRAGProvider()
        with patch.object(provider, '_search', side_effect=Exception("network error")):
            result = provider.query("test query")
            assert result["results"] == []
            assert result["relevance_scores"] == []
            assert result["source_metadata"] == []

    def test_query_with_mock_results(self):
        """模拟 API 返回结果"""
        provider = PubmedRAGProvider()

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

        with patch.object(provider, '_search', return_value=mock_ids):
            with patch.object(provider, '_fetch', return_value=mock_articles):
                result = provider.query("test query")

        assert len(result["results"]) == 2
        assert result["results"][0] == "This is a test abstract for article 1."
        assert result["results"][1] == "This is a test abstract for article 2."
        assert len(result["source_metadata"]) == 2
        assert result["source_metadata"][0]["pmid"] == "12345"
        assert result["source_metadata"][0]["title"] == "Test Article 1"
        assert result["relevance_scores"][0] == 1.0
        assert result["relevance_scores"][1] == 0.95

    def test_context_store_retrieve(self):
        """验证上下文存取"""
        provider = PubmedRAGProvider()
        provider.store_context("key1", {"data": 123})
        assert provider.retrieve_context("key1") == {"data": 123}
        assert provider.retrieve_context("nonexistent") is None

    def test_empty_search(self):
        """空搜索结果"""
        provider = PubmedRAGProvider()
        with patch.object(provider, '_search', return_value=[]):
            result = provider.query("no results query")
            assert result["results"] == []
            assert result["source_metadata"] == []

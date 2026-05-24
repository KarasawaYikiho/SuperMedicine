"""PubMed Entrez API Provider — 免费医学文献检索"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from permission.engine import PermissionEngine
from permission.policy import PermissionResult

from .interface import RAGConnectionError, RAGProvider, RAGQueryTimeoutError, make_rag_result


class PubmedRAGProvider(RAGProvider):
    """PubMed Entrez API Provider

    使用 NCBI E-utilities API 进行医学文献检索，免费无需认证。
    API 基础地址: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    provider_name = "pubmed"

    def __init__(
        self,
        email: str = "supermedicine@example.com",
        tool: str = "supermedicine",
        timeout_seconds: float = 10.0,
        permission_engine: PermissionEngine | None = None,
        agent_id: str | None = None,
    ):
        self._email = email
        self._tool = tool
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), 120.0))
        self._permission_engine = permission_engine
        self._agent_id = agent_id
        self._context: dict[str, Any] = {}

    def connect(self) -> dict[str, Any]:
        return {
            "status": "configured",
            "provider": self.provider_name,
            "metadata": {
                "resource": {"kind": "external_api", "endpoint": self.BASE_URL, "timeout_seconds": self._timeout_seconds},
                "security": {"external_resource": True, "authentication": "none"},
            },
        }

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        """检索 PubMed 文献

        Args:
            query_text: 医学查询文本（支持 PubMed 查询语法）
            top_k: 返回结果数量上限

        Returns:
            {"results": [...], "relevance_scores": [...], "source_metadata": [...]}
        """
        denied = self._permission_denied()
        if denied is not None:
            return denied

        try:
            # Step 1: Esearch — 获取匹配的 PubMed IDs
            ids = self._search(query_text, top_k)
            if not ids:
                return make_rag_result([], provider=self.provider_name, metadata={"query": query_text, "top_k": top_k, **self.connect()["metadata"]})

            # Step 2: Efetch — 获取摘要和元数据
            articles = self._fetch(ids)

            items = []
            for i, article in enumerate(articles):
                metadata = {
                    "pmid": article.get("pmid", ""),
                    "title": article.get("title", ""),
                    "authors": article.get("authors", ""),
                    "journal": article.get("journal", ""),
                    "year": article.get("year", ""),
                    "doi": article.get("doi", ""),
                }
                items.append(
                    {
                        "id": article.get("pmid", ""),
                        "title": article.get("title", ""),
                        "source": "PubMed",
                        "score": round(1.0 - i * 0.05, 4),
                        "snippet": article.get("abstract", ""),
                        **metadata,
                        "metadata": metadata,
                    }
                )

            return make_rag_result(items, provider=self.provider_name, metadata={"query": query_text, "top_k": top_k, **self.connect()["metadata"]})
        except TimeoutError as exc:
            timeout_error = RAGQueryTimeoutError("PubMed query timed out.", retryable=True, details={"cause": str(exc)})
            return make_rag_result([], provider=self.provider_name, status="error", errors=[timeout_error.to_dict()], metadata={"query": query_text, "top_k": top_k, **self.connect()["metadata"]})
        except (urllib.error.URLError, OSError) as exc:
            connection_error = RAGConnectionError("PubMed connection failed.", retryable=True, details={"cause": str(exc)})
            return make_rag_result([], provider=self.provider_name, status="error", errors=[connection_error.to_dict()], metadata={"query": query_text, "top_k": top_k, **self.connect()["metadata"]})
        except Exception as exc:
            provider_error = RAGConnectionError("PubMed provider failed.", retryable=True, details={"cause": str(exc)})
            return make_rag_result([], provider=self.provider_name, status="error", errors=[provider_error.to_dict()], metadata={"query": query_text, "top_k": top_k, **self.connect()["metadata"]})

    def _search(self, query: str, max_results: int) -> list[str]:
        """Esearch: 检索 PubMed IDs"""
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": str(max_results),
            "retmode": "json",
            "sort": "relevance",
            "email": self._email,
            "tool": self._tool,
        }
        url = f"{self.BASE_URL}/esearch.fcgi?{urllib.parse.urlencode(params)}"
        data = self._get_json(url)
        return data.get("esearchresult", {}).get("idlist", [])

    def _fetch(self, ids: list[str]) -> list[dict[str, Any]]:
        """Efetch: 获取文献摘要和元数据"""
        params = {
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self._email,
            "tool": self._tool,
        }
        url = f"{self.BASE_URL}/efetch.fcgi?{urllib.parse.urlencode(params)}"
        xml_text = self._get_text(url)
        return self._parse_articles(xml_text)

    def _parse_articles(self, xml_text: str) -> list[dict[str, Any]]:
        """解析 PubMed XML 响应"""
        articles = []
        try:
            root = ET.fromstring(xml_text)
            for article_elem in root.findall(".//PubmedArticle"):
                article = self._parse_article(article_elem)
                if article:
                    articles.append(article)
        except ET.ParseError:
            pass
        return articles

    def _parse_article(self, elem) -> dict[str, Any] | None:
        """解析单个 PubmedArticle 元素"""
        try:
            medline = elem.find(".//MedlineCitation")
            if medline is None:
                return None

            pmid = medline.findtext("PMID", "")

            article_elem = medline.find("Article")
            if article_elem is None:
                return None

            title = article_elem.findtext("ArticleTitle", "")

            # 作者列表
            authors = []
            author_list = article_elem.find("AuthorList")
            if author_list is not None:
                for author in author_list.findall("Author"):
                    last = author.findtext("LastName", "")
                    fore = author.findtext("ForeName", "")
                    if last:
                        authors.append(f"{last} {fore}" if fore else last)

            # 期刊信息
            journal_elem = article_elem.find("Journal")
            journal_name = ""
            year = ""
            if journal_elem is not None:
                journal_name = journal_elem.findtext("Title", "")
                pub_date = journal_elem.find("JournalIssue/PubDate")
                if pub_date is not None:
                    year = pub_date.findtext("Year", "")

            # 摘要
            abstract_elem = article_elem.find("Abstract")
            abstract = ""
            if abstract_elem is not None:
                parts = []
                for at in abstract_elem.findall("AbstractText"):
                    label = at.get("Label", "")
                    text = at.text or ""
                    parts.append(f"{label}: {text}" if label else text)
                abstract = " ".join(parts)

            # DOI
            doi = ""
            for eid in article_elem.findall(".//ELocationID"):
                if eid.get("EIdType") == "doi":
                    doi = eid.text or ""

            return {
                "pmid": pmid,
                "title": title,
                "authors": ", ".join(authors[:5]),
                "journal": journal_name,
                "year": year,
                "doi": doi,
                "abstract": abstract,
            }
        except Exception:
            return None

    def _get_json(self, url: str) -> dict[str, Any]:
        """HTTP GET 并解析 JSON"""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_text(self, url: str) -> str:
        """HTTP GET 返回文本"""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=self._timeout_seconds) as resp:
            return resp.read().decode("utf-8")

    def _permission_denied(self) -> dict[str, Any] | None:
        """Check optional policy gate before PubMed external HTTP access."""
        if self._permission_engine is None:
            return make_rag_result(
                [],
                provider=self.provider_name,
                status="denied",
                errors=[
                    {
                        "code": "permission_engine_required",
                        "message": "PubMed external HTTP access requires an explicit permission engine and policy context.",
                        "retryable": False,
                        "details": {"action": "rag.external.query", "resource": "https://eutils.ncbi.nlm.nih.gov/*"},
                    }
                ],
                metadata={
                    "resource": {"kind": "external_api", "endpoint": self.BASE_URL, "timeout_seconds": self._timeout_seconds},
                    "security": {"external_resource": True, "permission": "denied", "permission_checked": False},
                },
            )

        if not isinstance(self._agent_id, str) or not self._agent_id.strip():
            return make_rag_result(
                [],
                provider=self.provider_name,
                status="denied",
                errors=[
                    {
                        "code": "agent_identity_required",
                        "message": "PubMed external HTTP access requires an explicit agent identity for permission checks.",
                        "retryable": False,
                        "details": {"action": "rag.external.query", "resource": "https://eutils.ncbi.nlm.nih.gov/*"},
                    }
                ],
                metadata={
                    "resource": {"kind": "external_api", "endpoint": self.BASE_URL, "timeout_seconds": self._timeout_seconds},
                    "security": {"external_resource": True, "permission": "denied", "permission_checked": False},
                },
            )

        resource = "https://eutils.ncbi.nlm.nih.gov/*"
        result = self._permission_engine.check(
            self._agent_id.strip(),
            "rag.external.query",
            resource,
            context={
                "action": "rag.external.query",
                "resource": {"kind": "external_api", "provider": self.provider_name, "endpoint": self.BASE_URL},
                "provider": self.provider_name,
                "requires_network": True,
                "requires_external_api": True,
                "timeout_seconds": self._timeout_seconds,
            },
        )
        if result == PermissionResult.ALLOWED:
            return None

        return make_rag_result(
            [],
            provider=self.provider_name,
            status="denied",
            errors=[
                {
                    "code": "permission_denied",
                    "message": "PubMed external HTTP access denied by permission policy.",
                    "retryable": False,
                    "details": {"action": "rag.external.query", "resource": resource},
                }
            ],
            metadata={
                "resource": {"kind": "external_api", "endpoint": self.BASE_URL, "timeout_seconds": self._timeout_seconds},
                "security": {"external_resource": True, "permission": "denied", "permission_checked": True},
            },
        )

    def store_context(self, key: str, data: Any) -> None:
        self._context[key] = data

    def retrieve_context(self, key: str) -> Any | None:
        return self._context.get(key)

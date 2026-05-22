"""PubMed Entrez API Provider — 免费医学文献检索"""
from __future__ import annotations

import json
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Any

from .interface import RAGProvider


class PubmedRAGProvider(RAGProvider):
    """PubMed Entrez API Provider

    使用 NCBI E-utilities API 进行医学文献检索，免费无需认证。
    API 基础地址: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, email: str = "supermedicine@example.com", tool: str = "supermedicine"):
        self._email = email
        self._tool = tool
        self._context: dict[str, Any] = {}

    def query(self, query_text: str, top_k: int = 5) -> dict[str, Any]:
        """检索 PubMed 文献

        Args:
            query_text: 医学查询文本（支持 PubMed 查询语法）
            top_k: 返回结果数量上限

        Returns:
            {"results": [...], "relevance_scores": [...], "source_metadata": [...]}
        """
        try:
            # Step 1: esearch — 获取匹配的 PubMed IDs
            ids = self._search(query_text, top_k)
            if not ids:
                return {"results": [], "relevance_scores": [], "source_metadata": []}

            # Step 2: efetch — 获取摘要和元数据
            articles = self._fetch(ids)

            results = []
            scores = []
            metadata = []
            for i, article in enumerate(articles):
                results.append(article.get("abstract", ""))
                scores.append(1.0 - i * 0.05)  # 按返回顺序递减
                metadata.append({
                    "pmid": article.get("pmid", ""),
                    "title": article.get("title", ""),
                    "authors": article.get("authors", ""),
                    "journal": article.get("journal", ""),
                    "year": article.get("year", ""),
                    "doi": article.get("doi", ""),
                })

            return {
                "results": results,
                "relevance_scores": scores,
                "source_metadata": metadata,
            }
        except Exception:
            # API 调用失败时返回空结果
            return {"results": [], "relevance_scores": [], "source_metadata": []}

    def _search(self, query: str, max_results: int) -> list[str]:
        """esearch: 检索 PubMed IDs"""
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
        """efetch: 获取文献摘要和元数据"""
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_text(self, url: str) -> str:
        """HTTP GET 返回文本"""
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")

    def store_context(self, key: str, data: Any) -> None:
        self._context[key] = data

    def retrieve_context(self, key: str) -> Any | None:
        return self._context.get(key)

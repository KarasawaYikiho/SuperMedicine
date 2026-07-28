"""Internet paper discovery with normalized Crossref and PubMed records."""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from typing import Any, Callable

from core import PUBLIC_VERSION

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_QUERY_LENGTH = 500
MAX_EXTERNAL_ID_LENGTH = 256
MAX_RESULTS = 50


class OnlinePaperError(RuntimeError):
    """Raised when an online literature provider cannot complete a request."""


@dataclass(frozen=True, slots=True)
class OnlinePaper:
    source: str
    external_id: str
    title: str
    authors: tuple[str, ...] = ()
    abstract: str = ""
    doi: str | None = None
    pmid: str | None = None
    journal: str = ""
    published: str = ""
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["authors"] = list(self.authors)
        return data


JsonGetter = Callable[[str], dict[str, Any]]
TextGetter = Callable[[str], str]


def _default_text_getter(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/xml;q=0.9",
            "User-Agent": f"SuperMedicine/{PUBLIC_VERSION} literature-search",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            declared_length = response.headers.get("Content-Length")
            if declared_length and int(declared_length) > MAX_RESPONSE_BYTES:
                raise OnlinePaperError("Online paper response exceeds the size limit")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise OnlinePaperError("Online paper response exceeds the size limit")
            return payload.decode("utf-8", errors="replace")
    except OnlinePaperError:
        raise
    except Exception as exc:
        raise OnlinePaperError("在线论文服务暂时不可用，请稍后重试。") from exc


def _default_json_getter(url: str) -> dict[str, Any]:
    try:
        payload = json.loads(_default_text_getter(url))
    except json.JSONDecodeError as exc:
        raise OnlinePaperError("在线论文服务返回了无法解析的数据。") from exc
    if not isinstance(payload, dict):
        raise OnlinePaperError("在线论文服务返回了无效的数据。")
    return payload


def _clean_markup(value: Any) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def _crossref_record(item: dict[str, Any]) -> OnlinePaper:
    title_values = item.get("title")
    title = (
        _clean_markup(title_values[0])
        if isinstance(title_values, list) and title_values
        else _clean_markup(title_values)
    )
    authors = []
    for author in item.get("author", []) if isinstance(item.get("author"), list) else []:
        if not isinstance(author, dict):
            continue
        name = " ".join(
            part for part in (str(author.get("given") or ""), str(author.get("family") or "")) if part
        ).strip()
        if name:
            authors.append(name)
    doi = str(item.get("DOI") or "").strip() or None
    containers = item.get("container-title")
    journal = (
        _clean_markup(containers[0])
        if isinstance(containers, list) and containers
        else _clean_markup(containers)
    )
    published = ""
    date_parts = (item.get("published-print") or item.get("published-online") or {}).get(
        "date-parts", []
    )
    if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
        published = "-".join(str(part) for part in date_parts[0])
    return OnlinePaper(
        source="crossref",
        external_id=doi or str(item.get("URL") or title),
        title=title or "未命名论文",
        authors=tuple(authors),
        abstract=_clean_markup(item.get("abstract")),
        doi=doi,
        journal=journal,
        published=published,
        url=str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
    )


class OnlinePaperClient:
    """Small dependency-free client for user-triggered literature discovery."""

    def __init__(
        self,
        *,
        json_getter: JsonGetter = _default_json_getter,
        text_getter: TextGetter = _default_text_getter,
    ) -> None:
        self._json = json_getter
        self._text = text_getter

    def search(self, query: str, *, source: str = "pubmed", limit: int = 10) -> list[OnlinePaper]:
        query = query.strip()
        if not query:
            raise ValueError("Paper search query is required")
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Paper search query exceeds {MAX_QUERY_LENGTH} characters")
        try:
            limit = int(limit)
        except (TypeError, ValueError) as exc:
            raise ValueError("Paper result limit must be an integer") from exc
        if not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"Paper result limit must be between 1 and {MAX_RESULTS}")
        normalized = self._source(source)
        if normalized == "crossref":
            return self._search_crossref(query, limit)
        if normalized == "pubmed":
            return self._search_pubmed(query, limit)
        raise AssertionError("unreachable")

    def get(self, source: str, external_id: str) -> OnlinePaper:
        normalized = self._source(source)
        identifier = external_id.strip()
        if not identifier:
            raise ValueError("Paper identifier is required")
        if len(identifier) > MAX_EXTERNAL_ID_LENGTH or any(
            ord(character) < 32 for character in identifier
        ):
            raise ValueError("Paper identifier is invalid")
        if normalized == "crossref":
            if not re.fullmatch(r"10\.\d{4,9}/\S+", identifier):
                raise ValueError("Crossref identifier must be a DOI")
            url = "https://api.crossref.org/works/" + urllib.parse.quote(identifier, safe="")
            message = self._json(url).get("message")
            if not isinstance(message, dict):
                raise OnlinePaperError("Crossref 未返回该论文。")
            return _crossref_record(message)
        if normalized == "pubmed":
            return self._fetch_pubmed(identifier)
        raise AssertionError("unreachable")

    @staticmethod
    def _source(source: str) -> str:
        normalized = str(source).strip().lower()
        if normalized not in {"pubmed", "crossref"}:
            raise ValueError("Paper source must be pubmed or crossref")
        return normalized

    def _search_crossref(self, query: str, limit: int) -> list[OnlinePaper]:
        params = urllib.parse.urlencode({"query.bibliographic": query, "rows": limit})
        payload = self._json(f"https://api.crossref.org/works?{params}")
        message = payload.get("message")
        items = message.get("items", []) if isinstance(message, dict) else []
        return [
            _crossref_record(item)
            for item in items[:limit]
            if isinstance(item, dict)
        ]

    def _search_pubmed(self, query: str, limit: int) -> list[OnlinePaper]:
        params = urllib.parse.urlencode(
            {"db": "pubmed", "term": query, "retmode": "json", "retmax": limit}
        )
        search = self._json(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + params
        )
        result = search.get("esearchresult")
        ids = result.get("idlist", []) if isinstance(result, dict) else []
        safe_ids = [
            str(item)
            for item in ids
            if str(item).isdigit() and len(str(item)) <= 12
        ][:limit]
        if not safe_ids:
            return []
        summary_params = urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(safe_ids), "retmode": "json"}
        )
        summary = self._json(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?"
            + summary_params
        ).get("result", {})
        records = []
        for pmid in safe_ids:
            item = summary.get(pmid) if isinstance(summary, dict) else None
            if not isinstance(item, dict):
                continue
            authors = tuple(
                str(author.get("name") or "")
                for author in item.get("authors", [])
                if isinstance(author, dict) and author.get("name")
            )
            doi = None
            for article_id in item.get("articleids", []):
                if isinstance(article_id, dict) and article_id.get("idtype") == "doi":
                    doi = str(article_id.get("value") or "") or None
                    break
            records.append(
                OnlinePaper(
                    source="pubmed",
                    external_id=pmid,
                    title=_clean_markup(item.get("title")) or "未命名论文",
                    authors=authors,
                    doi=doi,
                    pmid=pmid,
                    journal=_clean_markup(item.get("fulljournalname") or item.get("source")),
                    published=str(item.get("pubdate") or ""),
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
        return records

    def _fetch_pubmed(self, pmid: str) -> OnlinePaper:
        if not pmid.isdigit():
            raise ValueError("PubMed identifier must be a numeric PMID")
        params = urllib.parse.urlencode(
            {"db": "pubmed", "id": pmid, "retmode": "xml"}
        )
        raw = self._text(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + params
        )
        try:
            article = ET.fromstring(raw).find(".//PubmedArticle")
        except ET.ParseError as exc:
            raise OnlinePaperError("PubMed 返回了无法解析的数据。") from exc
        if article is None:
            raise OnlinePaperError("PubMed 未返回该论文。")
        title = _clean_markup("".join(article.findtext(".//ArticleTitle") or ""))
        authors = []
        for author in article.findall(".//Author"):
            name = " ".join(
                part
                for part in (
                    author.findtext("ForeName") or "",
                    author.findtext("LastName") or "",
                )
                if part
            )
            if name:
                authors.append(name)
        abstracts = [
            _clean_markup("".join(node.itertext()))
            for node in article.findall(".//Abstract/AbstractText")
        ]
        doi = None
        for node in article.findall(".//ArticleId"):
            if node.attrib.get("IdType") == "doi" and node.text:
                doi = node.text.strip()
                break
        return OnlinePaper(
            source="pubmed",
            external_id=pmid,
            title=title or "未命名论文",
            authors=tuple(authors),
            abstract="\n\n".join(part for part in abstracts if part),
            doi=doi,
            pmid=pmid,
            journal=_clean_markup(article.findtext(".//Journal/Title")),
            published=_clean_markup(article.findtext(".//PubDate/Year")),
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        )


__all__ = ["OnlinePaper", "OnlinePaperClient", "OnlinePaperError"]

"""Local-first retrieval orchestration for generation paths."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.config_center import ConfigCenter
from core.path_safety import validate_path_in_project_root
from core.runtime_capabilities import RuntimeInvariantError
from permission.engine import PermissionEngine
from plugins.rag.providers import LocalRAGProvider
from plugins.rag.pubmed_provider import PubmedRAGProvider


@dataclass(frozen=True)
class RAGContext:
    status: str
    sources: tuple[dict[str, Any], ...]
    errors: tuple[dict[str, Any], ...] = ()

    def as_prompt_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "sources": list(self.sources),
            "errors": list(self.errors),
        }

    def as_metadata(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "status": self.status,
            "errors": list(self.errors),
        }


class RAGService:
    """Retrieves local evidence without silently falling back to demo content."""

    def __init__(
        self,
        config: ConfigCenter,
        config_path: Path,
        *,
        permission_engine: PermissionEngine | None = None,
        agent_id: str = "alpha",
    ) -> None:
        self._config = config
        self._config_path = Path(config_path)
        self._permission_engine = permission_engine
        self._agent_id = agent_id
        self._default_storage_dir = self._storage_dir()
        try:
            LocalRAGProvider(self._default_storage_dir)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise RuntimeInvariantError(
                "rag_index_corrupt",
                "Local RAG index is unavailable; runtime startup was blocked.",
                {"reason": type(exc).__name__},
            ) from exc
        try:
            with NamedTemporaryFile(dir=self._default_storage_dir):
                pass
        except OSError as exc:
            raise RuntimeInvariantError(
                "rag_storage_unavailable",
                "Local RAG storage is not writable; runtime startup was blocked.",
                {"reason": type(exc).__name__},
            ) from exc

    def _storage_dir(self, workspace_path: Path | None = None) -> Path:
        project_root = (
            self._config_path.parent.parent
            if self._config_path.parent.name == ".supermedicine"
            else self._config_path.parent
        )
        storage_root = project_root
        if workspace_path is not None:
            storage_root = validate_path_in_project_root(Path(workspace_path), project_root)
        return storage_root / ".supermedicine" / "rag" / "local"

    @staticmethod
    def classify_task(
        task: str, plugin: str | None = None, action: str | None = None
    ) -> str:
        """Classify execution without depending on retrieval keywords."""
        del task
        if action in {"status", "diagnose"} or (action or "").startswith("harness."):
            return "control"
        if plugin in {"medical-writing", "medical-citation"}:
            return "knowledge_generation"
        if plugin is not None:
            return "deterministic_plugin"
        return "knowledge_generation"

    def retrieve(self, query: str, workspace_path: Path | None = None) -> RAGContext:
        settings = self._config.get_rag_config()
        try:
            provider = LocalRAGProvider(self._storage_dir(workspace_path))
            response = provider.query(query, top_k=int(settings["top_k"]))
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            raise RuntimeInvariantError(
                "rag_index_corrupt",
                "Local RAG index is unavailable; generation was blocked.",
                {"reason": type(exc).__name__},
            ) from exc
        minimum = float(settings["min_score"])
        candidates = [
            item
            for item in response.get("items", [])
            if isinstance(item, dict) and float(item.get("score", 0.0)) >= minimum
        ]
        errors: list[dict[str, Any]] = []
        status = "used" if candidates else "empty"
        if str(settings.get("provider", "local")).lower() in {"hybrid", "pubmed"}:
            external = PubmedRAGProvider(
                permission_engine=self._permission_engine,
                agent_id=self._agent_id,
            ).query(query, top_k=int(settings["top_k"]))
            external_items = external.get("items", [])
            if external.get("status") == "success" and isinstance(external_items, list):
                candidates.extend(
                    item for item in external_items if isinstance(item, dict)
                )
                if external_items:
                    status = "used"
            else:
                status = "degraded"
                raw_errors = external.get("errors", [])
                if isinstance(raw_errors, list):
                    errors.extend(item for item in raw_errors if isinstance(item, dict))
        deduplicated: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for candidate in candidates:
            identity = (
                str(candidate.get("source", "")),
                str(candidate.get("id", "")),
                str(candidate.get("content_hash", "")),
            )
            if identity in seen:
                continue
            seen.add(identity)
            deduplicated.append(candidate)
        remaining = max(0, int(settings["max_context_chars"]))
        bounded_sources: list[dict[str, Any]] = []
        for candidate in deduplicated:
            if remaining <= 0:
                break
            source = dict(candidate)
            snippet = str(source.get("snippet", ""))[:remaining]
            source["snippet"] = snippet
            remaining -= len(snippet)
            bounded_sources.append(source)
        sources = tuple(bounded_sources)
        if status != "degraded":
            status = "used" if sources else "empty"
        return RAGContext(status, sources, tuple(errors))

    @staticmethod
    def index_workspace_document(
        workspace_path: Path,
        *,
        text: str,
        document_id: str,
        source_path: Path,
        title: str = "",
        page_texts: list[tuple[int, str]] | None = None,
    ) -> None:
        """Replace an extracted document with traceable, bounded chunks."""
        provider = LocalRAGProvider(
            Path(workspace_path) / ".supermedicine" / "rag" / "local"
        )
        chunks: list[tuple[str, dict[str, Any]]] = []
        inputs: list[tuple[int | None, str]] = (
            list(page_texts) if page_texts else [(None, text)]
        )
        chunk_size = 1200
        overlap = 150
        for page, page_text in inputs:
            cleaned = page_text.strip()
            if not cleaned:
                continue
            start = 0
            while start < len(cleaned):
                chunk_text = cleaned[start : start + chunk_size]
                chunk_number = len(chunks)
                chunks.append(
                    (
                        chunk_text,
                        {
                            "chunk_id": f"{document_id}:{chunk_number}",
                            "title": title or source_path.name,
                            "source": "paper_import",
                            "source_path": source_path.name,
                            "source_type": "paper",
                            "page": page,
                            "section": "",
                        },
                    )
                )
                if start + chunk_size >= len(cleaned):
                    break
                start += chunk_size - overlap
        provider.replace_document(document_id, chunks)

    @staticmethod
    def remove_workspace_document(workspace_path: Path, document_id: str) -> int:
        """Remove all RAG chunks associated with one imported paper."""
        return LocalRAGProvider(
            Path(workspace_path) / ".supermedicine" / "rag" / "local"
        ).remove_document(document_id)

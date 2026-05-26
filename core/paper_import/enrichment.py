"""Permission-aware metadata enrichment for imported papers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from core.paper_import.models import PaperMetadata
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from permission.policy import PermissionResult


PAPER_ENRICH_ACTION = "paper.enrich"
PAPER_ENRICH_AGENT_ID = "delta"


class PaperMetadataProvider(Protocol):
    """Fetch supplemental paper metadata after permission approval."""

    name: str

    resource: str

    requires_network: bool
    requires_external_api: bool

    def fetch(self, metadata: PaperMetadata) -> dict[str, Any]:
        """Return metadata fields to merge into an existing paper record."""


@dataclass(slots=True)
class LocalMockMetadataProvider:
    """Deterministic local provider for tests and offline enrichment demos."""

    name: str = "local_mock"
    resource: str = "mock://paper-metadata"
    requires_network: bool = True
    requires_external_api: bool = True
    fixtures: dict[str, dict[str, Any]] = field(default_factory=dict)

    def fetch(self, metadata: PaperMetadata) -> dict[str, Any]:
        key = metadata.doi or metadata.pmid or metadata.id or ""
        if key in self.fixtures:
            return dict(self.fixtures[key])
        title = metadata.title or (f"Enriched paper {key}" if key else "Enriched paper")
        return {
            "title": title,
            "doi": metadata.doi,
            "pmid": metadata.pmid,
            "tags": sorted(set([*metadata.tags, "enriched"])),
        }


@dataclass(slots=True)
class PaperEnrichmentResult:
    """Outcome of an attempted metadata enrichment."""

    metadata: PaperMetadata
    status: str
    warning: str | None = None
    applied_fields: list[str] = field(default_factory=list)


class PaperEnricher:
    """Gate provider calls behind explicit confirmation and PermissionEngine."""

    def __init__(
        self,
        permission_engine: PermissionEngine,
        audit_logger: AuditLogger,
        provider: PaperMetadataProvider | None = None,
        agent_id: str = PAPER_ENRICH_AGENT_ID,
    ) -> None:
        self.permission_engine = permission_engine
        self.audit_logger = audit_logger
        self.provider = provider or LocalMockMetadataProvider()
        self.agent_id = agent_id

    def enrich(self, metadata: PaperMetadata, *, confirmed: bool) -> PaperEnrichmentResult:
        resource = self.provider.resource
        paper_id = metadata.id or "<unknown>"
        if not confirmed:
            self.audit_logger.log(
                agent_id=self.agent_id,
                action=PAPER_ENRICH_ACTION,
                resource=resource,
                result="skipped",
                reason="missing_explicit_confirmation",
            )
            return PaperEnrichmentResult(
                metadata=metadata,
                status="skipped",
                warning="enrichment skipped: --confirm-enrich is required",
            )

        self.audit_logger.log(
            agent_id=self.agent_id,
            action=PAPER_ENRICH_ACTION,
            resource=resource,
            result="requested",
            reason=f"paper_id:{paper_id}",
        )
        decision = self.permission_engine.check(
            self.agent_id,
            PAPER_ENRICH_ACTION,
            resource,
            context={
                "paper_id": paper_id,
                "provider": self.provider.name,
                "requires_network": self.provider.requires_network,
                "requires_external_api": self.provider.requires_external_api,
            },
        )
        if decision != PermissionResult.ALLOWED:
            self.audit_logger.log(
                agent_id=self.agent_id,
                action=PAPER_ENRICH_ACTION,
                resource=resource,
                result="denied",
                reason="permission_denied",
            )
            return PaperEnrichmentResult(
                metadata=metadata,
                status="denied",
                warning="enrichment denied by permission policy",
            )

        self.audit_logger.log(
            agent_id=self.agent_id,
            action=PAPER_ENRICH_ACTION,
            resource=resource,
            result="allowed",
            reason="permission_allowed",
        )
        try:
            fetched = self.provider.fetch(metadata)
        except Exception as exc:  # Provider failures must not corrupt imports.
            self.audit_logger.log(
                agent_id=self.agent_id,
                action=PAPER_ENRICH_ACTION,
                resource=resource,
                result="skipped",
                reason=f"provider_unavailable:{type(exc).__name__}",
            )
            return PaperEnrichmentResult(
                metadata=metadata,
                status="skipped",
                warning=f"enrichment skipped: provider unavailable ({type(exc).__name__})",
            )

        applied = _apply_provider_fields(metadata, fetched)
        self.audit_logger.log(
            agent_id=self.agent_id,
            action=PAPER_ENRICH_ACTION,
            resource=resource,
            result="enriched",
            reason=",".join(applied) if applied else "no_fields_applied",
        )
        return PaperEnrichmentResult(metadata=metadata, status="enriched", applied_fields=applied)


def _apply_provider_fields(metadata: PaperMetadata, fetched: dict[str, Any]) -> list[str]:
    applied: list[str] = []
    for field_name in ("title", "authors", "doi", "pmid", "notes", "tags"):
        if field_name not in fetched or fetched[field_name] is None:
            continue
        value = fetched[field_name]
        if field_name in {"authors", "tags"}:
            value = list(value or [])
        setattr(metadata, field_name, value)
        applied.append(field_name)
    return applied

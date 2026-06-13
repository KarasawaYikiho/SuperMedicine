"""Safe self-evolution artifact generation service.

The service in this module is deliberately conservative.  It converts a user
intent and optional confirmed experience records into a deterministic preview,
then writes only whitelisted Markdown/Python/R generated artifacts after an
explicit confirmation flag and the existing permission/audit path approve the
operation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Literal, Sequence

from core.experience import ExperienceRecord, ExperienceStore
from core.log_report import LogReportStore
from core.log_report_models import TUI_LOG_SESSION_ID
from core.operation_guard import authorize_dangerous_operation
from core.path_safety import (
    DangerousOverwriteError,
    PathSafetyError,
    reject_sensitive_content,
    resolve_project_root,
    validate_path_in_project_root,
    validate_sandbox_write_path,
)
from core.redaction import redact_sensitive
from core.serialization import json_ready
from core.time_utils import utc_now
from permission.access_mode import AccessModePolicy, FileAccessOperation
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from permission.policy import ensure_default_policy


ArtifactType = Literal["markdown", "python_tool", "r_tool"]
AccessModeName = Literal["sandbox", "conservative", "full"]

ARTIFACT_TYPE_WHITELIST: tuple[ArtifactType, ...] = (
    "markdown",
    "python_tool",
    "r_tool",
)
SELF_EVOLUTION_ACTION = "self_evolution.generate"
ALLOWED_MARKDOWN_EXTENSIONS = (".md",)
ALLOWED_TOOL_EXTENSIONS = (".py", ".r", ".R", ".md", ".txt")
SELF_EVOLUTION_WRITABLE_ROOTS = ("self_evolution", "generated", "tools/generated")
PROHIBITED_DOC_PARTS = {"docs", "Docs"}
PROHIBITED_DOC_FILENAMES = {"REQUIREMENTS_TRACEABILITY.md"}
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class SelfEvolutionError(ValueError):
    """Base exception for self-evolution service failures."""


class SelfEvolutionValidationError(SelfEvolutionError):
    """Raised when a self-evolution request is invalid."""


class SelfEvolutionPermissionError(SelfEvolutionError):
    """Raised when permissions block confirmed generation."""


@dataclass(frozen=True)
class GeneratedArtifact:
    """One file proposed or written by the self-evolution service."""

    path: Path
    artifact_type: ArtifactType
    content: str
    description: str
    exists: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return json_ready(data)


@dataclass(frozen=True)
class SelfEvolutionRequest:
    """Normalized self-evolution generation request."""

    user_intent: str
    artifact_type: ArtifactType
    output_path: str | Path
    access_mode: AccessModeName = "sandbox"
    experience_source: Any | None = None
    workspace_id: str | None = None
    confirmed: bool = False
    overwrite: bool = False
    agent_id: str = "delta"
    full_access_confirmed: bool = False
    risk_notice_acknowledged: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SelfEvolutionResult:
    """Structured preview/write result returned to callers."""

    status: str
    mode: str
    artifact_type: str
    plan: dict[str, Any]
    artifacts: list[dict[str, Any]]
    message: str
    errors: list[str] = field(default_factory=list)
    audit_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return json_ready(redact_sensitive(asdict(self)))


class SelfEvolutionService:
    """Generate whitelisted self-evolution previews and confirmed artifacts."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = resolve_project_root(project_root)
        self.experience_store = ExperienceStore(self.project_root)

    def generate(
        self,
        *,
        user_intent: str,
        artifact_type: str,
        output_path: str | Path,
        access_mode: str = "sandbox",
        experience_source: Any | None = None,
        workspace_id: str | None = None,
        confirmed: bool = False,
        overwrite: bool = False,
        permission_engine: PermissionEngine | None = None,
        audit_logger: AuditLogger | None = None,
        agent_id: str = "delta",
        full_access_confirmed: bool = False,
        risk_notice_acknowledged: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return a preview, or write generated files only when confirmed.

        Failures are returned as structured dictionaries instead of leaking raw
        exceptions to user-facing callers.
        """

        try:
            request = self._normalize_request(
                user_intent=user_intent,
                artifact_type=artifact_type,
                output_path=output_path,
                access_mode=access_mode,
                experience_source=experience_source,
                workspace_id=workspace_id,
                confirmed=confirmed,
                overwrite=overwrite,
                agent_id=agent_id,
                full_access_confirmed=full_access_confirmed,
                risk_notice_acknowledged=risk_notice_acknowledged,
                metadata=metadata or {},
            )
            artifacts = self._build_artifacts(request)
            plan = self._build_plan(request, artifacts)
            if not request.confirmed:
                self._record_event(
                    audit_logger,
                    request,
                    plan=plan,
                    result="PREVIEW",
                    reason="preview_only_no_files_written",
                    decision="preview",
                    severity="Info",
                )
                return SelfEvolutionResult(
                    status="preview",
                    mode="preview",
                    artifact_type=request.artifact_type,
                    plan=plan,
                    artifacts=[artifact.to_dict() for artifact in artifacts],
                    message="Preview generated; no files were written because confirmed is false.",
                ).to_dict()

            audit_records = self._authorize_artifacts(
                request, artifacts, permission_engine, audit_logger
            )
            written = self._write_artifacts(artifacts)
            success_plan = {**plan, "written_files": [str(path) for path in written]}
            self._record_event(
                audit_logger,
                request,
                plan=success_plan,
                result="ALLOWED",
                reason="confirmed_artifacts_written",
                decision="confirm",
                severity="Success",
            )
            return SelfEvolutionResult(
                status="success",
                mode="confirmed",
                artifact_type=request.artifact_type,
                plan=success_plan,
                artifacts=[artifact.to_dict() for artifact in artifacts],
                message="Confirmed self-evolution artifacts were written.",
                audit_records=audit_records,
            ).to_dict()
        except Exception as exc:  # intentionally returns clear failure objects
            self._audit_failure(
                audit_logger,
                agent_id,
                artifact_type,
                output_path,
                exc,
                access_mode=access_mode,
                confirmed=confirmed,
            )
            return SelfEvolutionResult(
                status="failed",
                mode="confirmed" if confirmed else "preview",
                artifact_type=str(artifact_type),
                plan={},
                artifacts=[],
                message="Self-evolution request failed.",
                errors=[str(redact_sensitive(str(exc)))],
            ).to_dict()

    def preview(self, **kwargs: Any) -> dict[str, Any]:
        """Convenience wrapper that never writes files."""

        kwargs["confirmed"] = False
        return self.generate(**kwargs)

    def confirm(self, **kwargs: Any) -> dict[str, Any]:
        """Convenience wrapper for explicit confirmed generation."""

        kwargs["confirmed"] = True
        return self.generate(**kwargs)

    def _normalize_request(self, **kwargs: Any) -> SelfEvolutionRequest:
        intent = str(kwargs["user_intent"]).strip()
        if not intent:
            raise SelfEvolutionValidationError("User intent is required")
        reject_sensitive_content(intent)

        artifact_type = str(kwargs["artifact_type"]).strip().lower()
        if artifact_type not in ARTIFACT_TYPE_WHITELIST:
            raise SelfEvolutionValidationError(
                "Artifact type must be one of: " + ", ".join(ARTIFACT_TYPE_WHITELIST)
            )
        access_mode = str(kwargs["access_mode"]).strip().lower()
        if access_mode not in {"sandbox", "conservative", "full"}:
            raise SelfEvolutionValidationError(
                "Access mode must be one of: sandbox, conservative, full"
            )
        if not str(kwargs["output_path"]).strip():
            raise SelfEvolutionValidationError("Output path is required")
        return SelfEvolutionRequest(
            user_intent=intent,
            artifact_type=artifact_type,  # type: ignore[arg-type]
            output_path=kwargs["output_path"],
            access_mode=access_mode,  # type: ignore[arg-type]
            experience_source=kwargs.get("experience_source"),
            workspace_id=kwargs.get("workspace_id"),
            confirmed=bool(kwargs.get("confirmed", False)),
            overwrite=bool(kwargs.get("overwrite", False)),
            agent_id=str(kwargs.get("agent_id") or "delta"),
            full_access_confirmed=bool(kwargs.get("full_access_confirmed", False)),
            risk_notice_acknowledged=bool(
                kwargs.get("risk_notice_acknowledged", False)
            ),
            metadata=dict(kwargs.get("metadata") or {}),
        )

    def _build_artifacts(
        self, request: SelfEvolutionRequest
    ) -> list[GeneratedArtifact]:
        experience_records = self._resolve_experience_records(
            request.experience_source, request.workspace_id
        )
        if request.artifact_type == "markdown":
            path = self._resolve_output_file(
                request.output_path,
                request,
                allowed_extensions=ALLOWED_MARKDOWN_EXTENSIONS,
                default_filename="self-evolution.md",
            )
            return self._finalize_artifacts(
                [
                    GeneratedArtifact(
                        path=path,
                        artifact_type=request.artifact_type,
                        content=self._render_markdown(request, experience_records),
                        description="Markdown self-evolution plan/preview artifact",
                        exists=path.exists(),
                    )
                ]
            )

        extension = ".py" if request.artifact_type == "python_tool" else ".R"
        filename = f"{self._slug_from_intent(request.user_intent)}{extension}"
        path = self._resolve_output_file(
            request.output_path,
            request,
            allowed_extensions=ALLOWED_TOOL_EXTENSIONS,
            default_filename=filename,
        )
        content = (
            self._render_python_tool(request, experience_records)
            if request.artifact_type == "python_tool"
            else self._render_r_tool(request, experience_records)
        )
        readme = path.with_name(f"{path.stem}-README.md")
        readme = self._validate_candidate_path(
            readme,
            request,
            allowed_extensions=ALLOWED_TOOL_EXTENSIONS,
        )
        return self._finalize_artifacts(
            [
                GeneratedArtifact(
                    path=path,
                    artifact_type=request.artifact_type,
                    content=content,
                    description="Generated guarded workspace tool runner",
                    exists=path.exists(),
                ),
                GeneratedArtifact(
                    path=readme,
                    artifact_type=request.artifact_type,
                    content=self._render_tool_readme(
                        request, experience_records, path.name
                    ),
                    description="Generated tool companion Markdown metadata",
                    exists=readme.exists(),
                ),
            ]
        )

    def _finalize_artifacts(
        self, artifacts: list[GeneratedArtifact]
    ) -> list[GeneratedArtifact]:
        for artifact in artifacts:
            reject_sensitive_content(artifact.content)
        return artifacts

    def _resolve_output_file(
        self,
        output_path: str | Path,
        request: SelfEvolutionRequest,
        *,
        allowed_extensions: Sequence[str],
        default_filename: str,
    ) -> Path:
        candidate = Path(output_path)
        if candidate.suffix == "":
            candidate = candidate / default_filename
        return self._validate_candidate_path(
            candidate,
            request,
            allowed_extensions=allowed_extensions,
        )

    def _validate_candidate_path(
        self,
        candidate: str | Path,
        request: SelfEvolutionRequest,
        *,
        allowed_extensions: Sequence[str],
    ) -> Path:
        if request.access_mode == "sandbox":
            resolved = validate_sandbox_write_path(
                candidate,
                self.project_root,
                writable_roots=SELF_EVOLUTION_WRITABLE_ROOTS,
                allowed_extensions=allowed_extensions,
                allow_overwrite=request.overwrite,
            )
        elif request.access_mode == "conservative":
            resolved = validate_path_in_project_root(candidate, self.project_root)
            self._validate_extension_and_overwrite(
                resolved, allowed_extensions, allow_overwrite=request.overwrite
            )
        else:
            path = Path(candidate).expanduser()
            if not path.is_absolute():
                path = self.project_root / path
            resolved = path.resolve()
            self._validate_extension_and_overwrite(
                resolved, allowed_extensions, allow_overwrite=request.overwrite
            )
        self._reject_prohibited_engineering_docs(resolved)
        return resolved

    def _validate_extension_and_overwrite(
        self,
        path: Path,
        allowed_extensions: Sequence[str],
        *,
        allow_overwrite: bool,
    ) -> None:
        normalized_extensions = {
            extension.lower()
            if str(extension).startswith(".")
            else f".{str(extension).lower()}"
            for extension in allowed_extensions
        }
        if path.suffix.lower() not in normalized_extensions:
            raise SelfEvolutionValidationError(
                f"Self-evolution output file type is not allowed: {path.suffix}"
            )
        if path.exists() and not allow_overwrite:
            raise DangerousOverwriteError(
                f"Self-evolution write would overwrite an existing file: {path}"
            )

    def _authorize_artifacts(
        self,
        request: SelfEvolutionRequest,
        artifacts: list[GeneratedArtifact],
        permission_engine: PermissionEngine | None,
        audit_logger: AuditLogger | None,
    ) -> list[dict[str, Any]]:
        policies_dir = self.project_root / ".supermedicine" / "policies"
        audit_log = policies_dir / "audit.jsonl"
        if permission_engine is None:
            ensure_default_policy(self.project_root)
        engine = permission_engine or PermissionEngine(policies_dir, audit_log)
        audit = audit_logger or AuditLogger(audit_log)
        access_policy = self._access_policy(request)
        audit_records: list[dict[str, Any]] = []
        for artifact in artifacts:
            reject_sensitive_content(artifact.content)
            authorization = authorize_dangerous_operation(
                permission_engine=engine,
                agent_id=request.agent_id,
                action=SELF_EVOLUTION_ACTION,
                path=artifact.path,
                project_root=self.project_root,
                context={
                    "artifact_type": request.artifact_type,
                    "workspace_id": request.workspace_id,
                    "confirmed": request.confirmed,
                    "preview": False,
                    "max_files_per_session": len(artifacts),
                },
                audit_logger=audit,
                access_policy=access_policy,
                file_operation=FileAccessOperation.WRITE,
                operation="self_evolution_generate",
                content=artifact.content,
                allow_overwrite=request.overwrite,
                explicit_authorization=request.full_access_confirmed,
                risk_notice_acknowledged=request.risk_notice_acknowledged,
            )
            audit_records.append(authorization.audit_record.to_context())
        return audit_records

    def _write_artifacts(self, artifacts: list[GeneratedArtifact]) -> list[Path]:
        written: list[Path] = []
        for artifact in artifacts:
            if artifact.path.exists() and artifact.exists is False:
                raise DangerousOverwriteError(
                    f"Sandbox write would overwrite an existing file: {artifact.path}"
                )
            artifact.path.parent.mkdir(parents=True, exist_ok=True)
            artifact.path.write_text(artifact.content, encoding="utf-8", newline="\n")
            written.append(artifact.path)
        return written

    def _access_policy(self, request: SelfEvolutionRequest) -> AccessModePolicy:
        extensions = (
            ALLOWED_MARKDOWN_EXTENSIONS
            if request.artifact_type == "markdown"
            else ALLOWED_TOOL_EXTENSIONS
        )
        if request.access_mode == "sandbox":
            return AccessModePolicy.sandbox(
                self.project_root,
                sandbox_writable_roots=SELF_EVOLUTION_WRITABLE_ROOTS,
                sandbox_allowed_extensions=extensions,
            )
        if request.access_mode == "full":
            if not request.risk_notice_acknowledged:
                raise SelfEvolutionPermissionError(
                    "Full access self-evolution writes require risk notice acknowledgement"
                )
            return AccessModePolicy.full(
                self.project_root,
                explicit_confirmation=request.full_access_confirmed,
            )
        return AccessModePolicy.conservative(self.project_root)

    def _resolve_experience_records(
        self, source: Any | None, workspace_id: str | None
    ) -> list[ExperienceRecord]:
        if source is None:
            return []
        if isinstance(source, ExperienceRecord):
            return [source]
        if isinstance(source, dict):
            return [ExperienceRecord.from_dict(source)]
        if isinstance(source, str):
            if not workspace_id:
                raise SelfEvolutionValidationError(
                    "workspace_id is required when experience_source is a record id"
                )
            return [
                self.experience_store.get_experience(source, workspace_id=workspace_id)
            ]
        if isinstance(source, Sequence) and not isinstance(source, (bytes, bytearray)):
            records: list[ExperienceRecord] = []
            for item in source:
                records.extend(self._resolve_experience_records(item, workspace_id))
            return records
        raise SelfEvolutionValidationError("Unsupported experience source")

    def _build_plan(
        self, request: SelfEvolutionRequest, artifacts: list[GeneratedArtifact]
    ) -> dict[str, Any]:
        conflicts = [str(artifact.path) for artifact in artifacts if artifact.exists]
        return {
            "intent": request.user_intent,
            "artifact_type": request.artifact_type,
            "access_mode": request.access_mode,
            "target": str(
                artifacts[0].path if len(artifacts) == 1 else artifacts[0].path.parent
            ),
            "files": [
                {
                    "path": str(artifact.path),
                    "description": artifact.description,
                    "bytes": len(artifact.content.encode("utf-8")),
                    "exists": artifact.exists,
                }
                for artifact in artifacts
            ],
            "conflicts": conflicts,
            "will_write": request.confirmed,
            "requires_confirmation": not request.confirmed,
            "created_at": utc_now(),
        }

    def _render_markdown(
        self, request: SelfEvolutionRequest, experiences: list[ExperienceRecord]
    ) -> str:
        lines = [
            "# Self-Evolution Plan",
            "",
            "## User Intent",
            request.user_intent,
            "",
            "## Generated Preview",
            "- Artifact type: markdown",
            f"- Access mode: {request.access_mode}",
            "- Safety: preview before write; confirmed writes only under approved generated roots.",
            "",
            "## Suggested Steps",
            "1. Restate the intended workflow improvement.",
            "2. Apply reusable confirmed experience guidance when available.",
            "3. Keep generated artifacts small, reviewable, and non-executable by default.",
            "4. Hand off verification to the caller/tester before adoption.",
        ]
        lines.extend(self._experience_markdown(experiences))
        return "\n".join(lines).rstrip() + "\n"

    def _render_tool_readme(
        self,
        request: SelfEvolutionRequest,
        experiences: list[ExperienceRecord],
        runner_name: str,
    ) -> str:
        lines = [
            "# Generated Self-Evolution Tool",
            "",
            f"- Runner: `{runner_name}`",
            f"- Artifact type: `{request.artifact_type}`",
            f"- Access mode used for generation: `{request.access_mode}`",
            "",
            "## Intent",
            request.user_intent,
            "",
            "## Safety Notes",
            "- Generated under approved self-evolution/tool generated roots only.",
            "- Runner performs argument parsing and path validation only; callers remain responsible for permission-gated execution.",
            "- No secrets or raw conversations are embedded.",
        ]
        lines.extend(self._experience_markdown(experiences))
        return "\n".join(lines).rstrip() + "\n"

    def _render_python_tool(
        self, request: SelfEvolutionRequest, experiences: list[ExperienceRecord]
    ) -> str:
        experience_notes = self._experience_notes(experiences)
        return (
            "#!/usr/bin/env python\n"
            '"""Generated SuperMedicine self-evolution helper tool."""\n\n'
            "from __future__ import annotations\n\n"
            "import argparse\n"
            "from pathlib import Path\n\n"
            "from core.path_safety import validate_sandbox_write_path\n\n"
            f"INTENT = {request.user_intent!r}\n"
            f"EXPERIENCE_NOTES = {experience_notes!r}\n\n"
            "def write_safe_output(output_path: str) -> None:\n"
            "    target = validate_sandbox_write_path(\n"
            "        output_path,\n"
            "        Path.cwd(),\n"
            "        writable_roots=('self_evolution', 'generated', 'tools/generated'),\n"
            "        allowed_extensions=('.md', '.txt'),\n"
            "        allow_overwrite=False,\n"
            "    )\n"
            "    target.parent.mkdir(parents=True, exist_ok=True)\n"
            "    target.write_text('Self-evolution helper prepared.\\n', encoding='utf-8')\n\n"
            "def main() -> int:\n"
            "    parser = argparse.ArgumentParser(description=INTENT)\n"
            "    parser.add_argument('--input', default='')\n"
            "    parser.add_argument('--output', default='')\n"
            "    parser.add_argument('--check-deps', action='store_true')\n"
            "    args = parser.parse_args()\n"
            "    if args.check_deps:\n"
            "        print('No optional dependencies declared for this generated helper.')\n"
            "        return 0\n"
            "    if args.output:\n"
            "        write_safe_output(args.output)\n"
            "    print(INTENT)\n"
            "    for note in EXPERIENCE_NOTES:\n"
            "        print(f'- {note}')\n"
            "    return 0\n\n"
            "if __name__ == '__main__':\n"
            "    raise SystemExit(main())\n"
        )

    def _render_r_tool(
        self, request: SelfEvolutionRequest, experiences: list[ExperienceRecord]
    ) -> str:
        notes = self._experience_notes(experiences)
        escaped_notes = ", ".join(repr(note) for note in notes)
        return (
            "#!/usr/bin/env Rscript\n"
            "# Generated SuperMedicine self-evolution helper tool.\n"
            f"intent <- {request.user_intent!r}\n"
            f"experience_notes <- c({escaped_notes})\n"
            "args <- commandArgs(trailingOnly = TRUE)\n"
            "if ('--check-deps' %in% args) {\n"
            "  cat('No optional dependencies declared for this generated helper.\\n')\n"
            "  quit(status = 0)\n"
            "}\n"
            "cat(intent, '\\n')\n"
            "if (length(experience_notes) > 0) {\n"
            "  for (note in experience_notes) cat('- ', note, '\\n', sep = '')\n"
            "}\n"
        )

    def _experience_markdown(self, experiences: list[ExperienceRecord]) -> list[str]:
        if not experiences:
            return [
                "",
                "## Experience Source",
                "No confirmed experience source supplied.",
            ]
        lines = ["", "## Experience Source"]
        for record in experiences:
            lines.extend(
                [
                    f"### {record.title}",
                    f"- id: {record.id}",
                    f"- scope: {record.scope}",
                    f"- tags: {', '.join(record.tags)}",
                    "",
                    record.summary,
                    "",
                ]
            )
        return lines

    def _experience_notes(self, experiences: list[ExperienceRecord]) -> list[str]:
        return [f"{record.title}: {record.summary}" for record in experiences]

    def _slug_from_intent(self, intent: str) -> str:
        slug = _SLUG_RE.sub("-", intent.lower()).strip("-")[:48].strip("-")
        return slug or "self-evolution-tool"

    def _reject_prohibited_engineering_docs(self, path: Path) -> None:
        if path.name.lower() in {name.lower() for name in PROHIBITED_DOC_FILENAMES}:
            raise SelfEvolutionValidationError(
                "Prohibited engineering traceability documents cannot be generated"
            )
        prohibited_doc_parts = {part.lower() for part in PROHIBITED_DOC_PARTS}
        if any(part.lower() in prohibited_doc_parts for part in path.parts):
            raise SelfEvolutionValidationError(
                "Docs/docs engineering document paths are not allowed for self-evolution output"
            )

    def _record_event(
        self,
        audit_logger: AuditLogger | None,
        request: SelfEvolutionRequest,
        *,
        plan: dict[str, Any],
        result: str,
        reason: str,
        decision: str,
        severity: str,
    ) -> None:
        target = str(plan.get("target") or request.output_path)
        event = self._event_payload(
            request_summary=self._request_summary(request.user_intent),
            access_mode=request.access_mode,
            target_path=target,
            artifact_type=request.artifact_type,
            decision=decision,
            result=result,
            reason=reason,
            confirmed=request.confirmed,
            workspace_id=request.workspace_id,
        )
        self._write_audit_event(
            audit_logger, request.agent_id, target, result, reason, event
        )
        self._write_log_event(event, severity=severity)

    def _audit_failure(
        self,
        audit_logger: AuditLogger | None,
        agent_id: str,
        artifact_type: str,
        output_path: str | Path,
        exc: Exception,
        *,
        access_mode: str,
        confirmed: bool,
    ) -> None:
        result = (
            "DENIED"
            if isinstance(
                exc, (SelfEvolutionPermissionError, PathSafetyError, PermissionError)
            )
            else "FAILED"
        )
        reason = str(exc)
        event = self._event_payload(
            request_summary="",
            access_mode=access_mode,
            target_path=str(output_path),
            artifact_type=str(artifact_type),
            decision="confirm" if confirmed else "preview",
            result=result,
            reason=reason,
            confirmed=confirmed,
            workspace_id=None,
        )
        self._write_audit_event(
            audit_logger, agent_id, str(output_path), result, reason, event
        )
        self._write_log_event(event, severity="Error")

    def _write_audit_event(
        self,
        audit_logger: AuditLogger | None,
        agent_id: str,
        resource: str,
        result: str,
        reason: str,
        context: dict[str, Any],
    ) -> None:
        try:
            audit = audit_logger or AuditLogger.for_project(self.project_root)
            audit.log(
                agent_id=agent_id,
                action=SELF_EVOLUTION_ACTION,
                resource=resource,
                result=result,
                reason=reason,
                context=context,
            )
        except Exception:
            return

    def _write_log_event(self, event: dict[str, Any], *, severity: str) -> None:
        try:
            LogReportStore(self.project_root).append(
                json.dumps(event, ensure_ascii=False, sort_keys=True),
                session_id=TUI_LOG_SESSION_ID,
                severity=severity,
            )
        except Exception:
            return

    @staticmethod
    def _request_summary(intent: str) -> str:
        summary = " ".join(str(intent or "").split())
        if len(summary) > 160:
            return f"{summary[:159].rstrip()}…"
        return summary

    @staticmethod
    def _event_payload(
        *,
        request_summary: str,
        access_mode: str,
        target_path: str,
        artifact_type: str,
        decision: str,
        result: str,
        reason: str,
        confirmed: bool,
        workspace_id: str | None,
    ) -> dict[str, Any]:
        return {
            "event": "self_evolution.audit",
            "action": SELF_EVOLUTION_ACTION,
            "request_summary": request_summary,
            "access_mode": access_mode,
            "target_path": target_path,
            "artifact_type": artifact_type,
            "decision": decision,
            "confirmed": confirmed,
            "result": result,
            "rejection_reason": reason if result in {"DENIED", "FAILED"} else "",
            "reason": reason,
            "workspace_id": workspace_id,
        }


def build_self_evolution_preview(**kwargs: Any) -> dict[str, Any]:
    """Module-level helper for callers that only need preview behavior."""

    project_root = kwargs.pop("project_root", None)
    return SelfEvolutionService(project_root).preview(**kwargs)


__all__ = [
    "ARTIFACT_TYPE_WHITELIST",
    "SELF_EVOLUTION_ACTION",
    "SelfEvolutionError",
    "SelfEvolutionRequest",
    "SelfEvolutionResult",
    "SelfEvolutionService",
    "SelfEvolutionPermissionError",
    "SelfEvolutionValidationError",
    "build_self_evolution_preview",
]

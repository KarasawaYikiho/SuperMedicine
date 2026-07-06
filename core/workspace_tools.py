"""Workspace-local modular Python/R research tool support.

Tools are stored under explicit workspaces as::

    workspaces/<id>/tools/python/<tool-id>/...
    workspaces/<id>/tools/r/<tool-id>/...

This module intentionally prepares guarded invocations instead of executing
untrusted workspace scripts directly.  PermissionEngine approval and audit
logging are still required for dry-run and prepared invocation paths.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
from typing import Any, Sequence

import yaml

from core.operation_guard import authorize_dangerous_operation
from core.path_safety import validate_path_in_project_root
from core.workspace import WorkspaceManager
from core.workspace_tool_models import (
    InvalidToolId,
    MANIFEST_FILE,
    SUPPORTED_LANGUAGES,
    TOOLS_DIR,
    ToolCandidateError,
    ToolImportCandidate,
    ToolInvocationPlan,
    ToolLanguage,
    ToolManifest,
    ToolManifestError,
    ToolNotFoundError,
    WorkspaceToolError,
    _load_candidate_metadata,
    _safe_load_manifest,
    validate_language,
    validate_tool_id,
)
from core.workspace_tool_spec import TOOL_AUTHORING_SPEC, build_tool_authoring_llm_context  # noqa: F401
from core.workspace_tool_templates import BUILTIN_TEMPLATES
from permission.audit import AuditLogger
from permission.engine import PermissionEngine


def _slug_from_name(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return validate_tool_id(slug or "tool")


class WorkspaceToolService:
    """Manage modular tools inside explicit workspace directories."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = self._resolve_service_project_root(project_root)
        self.workspace_manager = WorkspaceManager(self.project_root)

    @classmethod
    def _resolve_service_project_root(cls, project_root: str | Path | None) -> Path:
        """Resolve the repository root used for global tool discovery.

        Tool scanning is intentionally project-global: selecting a workspace or
        launching from a nested/workspace directory must not make
        ``plugins/tools`` disappear.  Explicit non-workspace roots stay scoped
        to the caller-provided directory so isolated tests and temporary
        projects do not accidentally scan the checkout containing this module.
        """

        start = Path.cwd() if project_root is None else Path(project_root)
        resolved = start.expanduser().resolve()

        if (resolved / "plugins" / TOOLS_DIR).is_dir():
            return resolved

        should_walk_up = project_root is None or "workspaces" in resolved.parts
        if not should_walk_up:
            return resolved

        for candidate in (resolved, *resolved.parents):
            if (candidate / "plugins" / TOOLS_DIR).is_dir():
                return candidate
        return resolved

    def tool_source_root(self) -> Path:
        """Return the project directory scanned for importable Python/R tools."""

        return validate_path_in_project_root(
            self.project_root / "plugins" / TOOLS_DIR, self.project_root
        )

    def initialize_tools(self, workspace_id: str) -> dict[str, Any]:
        info = self.workspace_manager.initialize_workspace(workspace_id)
        paths = []
        for language in SUPPORTED_LANGUAGES:
            path = self.tools_language_path(info.id, language)
            path.mkdir(parents=True, exist_ok=True)
            paths.append(str(path))
        return {"workspace_id": info.id, "paths": paths, "status": "initialized"}

    def workspace_path(self, workspace_id: str) -> Path:
        return self.workspace_manager.get_workspace(workspace_id).path

    def tools_language_path(self, workspace_id: str, language: str) -> Path:
        lang = validate_language(language)
        workspace = self.workspace_path(workspace_id)
        return validate_path_in_project_root(
            workspace / TOOLS_DIR / lang, self.project_root
        )

    def tool_path(self, workspace_id: str, language: str, tool_id: str) -> Path:
        path = validate_path_in_project_root(
            self.tools_language_path(workspace_id, language)
            / validate_tool_id(tool_id),
            self.project_root,
        )
        language_root = self.tools_language_path(workspace_id, language)
        path.relative_to(language_root)
        return path

    def resolve_within_tool(
        self, workspace_id: str, language: str, tool_id: str, relative_path: str | Path
    ) -> Path:
        root = self.tool_path(workspace_id, language, tool_id)
        candidate = validate_path_in_project_root(
            root / relative_path, self.project_root
        )
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise WorkspaceToolError(
                f"Path resolves outside tool folder: {relative_path}"
            ) from exc
        return candidate

    def resolve_within_workspace(
        self, workspace_id: str, path: str | Path | None
    ) -> Path | None:
        if path is None:
            return None
        workspace = self.workspace_path(workspace_id)
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = workspace / candidate
        resolved = validate_path_in_project_root(candidate, self.project_root)
        try:
            resolved.relative_to(workspace)
        except ValueError as exc:
            raise WorkspaceToolError(
                f"Path resolves outside workspace: {path}"
            ) from exc
        return resolved

    def add_builtin_tool(
        self, workspace_id: str, language: str, tool_id: str, *, overwrite: bool = False
    ) -> dict[str, Any]:
        lang = validate_language(language)
        slug = validate_tool_id(tool_id)
        key = (lang, slug)
        if key not in BUILTIN_TEMPLATES:
            raise ToolNotFoundError(f"Unknown built-in tool template: {lang}/{slug}")
        destination = self.tool_path(workspace_id, lang, slug)
        if destination.exists() and any(destination.iterdir()) and not overwrite:
            manifest = self.load_manifest(workspace_id, lang, slug)
            return {
                "status": "exists",
                "tool": manifest.to_dict(),
                "path": str(destination),
            }
        if destination.exists() and overwrite:
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
        for filename, content in BUILTIN_TEMPLATES[key].items():
            target = self.resolve_within_tool(workspace_id, lang, slug, filename)
            target.write_text(content, encoding="utf-8")
        manifest = self.load_manifest(workspace_id, lang, slug)
        return {"status": "added", "tool": manifest.to_dict(), "path": str(destination)}

    def scan_import_candidates(
        self, language: str | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        """Scan Python/R source tool directories and return user-selectable candidates.

        Scans the ``plugins/tools`` directory under the project root for tool
        candidates.  This operation does **not** require a workspace to be
        selected so that tools are discoverable globally.
        """

        languages = (
            [validate_language(language)] if language else list(SUPPORTED_LANGUAGES)
        )
        result: dict[str, list[dict[str, Any]]] = {lang: [] for lang in languages}
        root = self.tool_source_root()
        if not root.is_dir():
            return result

        candidates: list[ToolImportCandidate] = []
        for entry in sorted(root.iterdir(), key=lambda item: item.name):
            if not entry.is_dir() or entry.name == "__pycache__":
                continue
            try:
                candidate = self._candidate_from_source(entry)
            except Exception as exc:
                # Never let a single malformed tool directory abort the
                # entire scan – record a synthetic invalid candidate so the
                # user can see which tool failed and why.
                candidate = ToolImportCandidate(
                    index=0,
                    id=entry.name,
                    language="python",
                    name=entry.name,
                    description="Scan failed",
                    source_path=entry,
                    entrypoint=None,
                    version="0.0.0",
                    dependencies=[],
                    inputs=[],
                    outputs=[],
                    status="invalid",
                    warnings=[f"scan error: {exc}"],
                )
            if candidate and candidate.language in languages:
                candidates.append(candidate)

        for index, candidate in enumerate(candidates, start=1):
            indexed = ToolImportCandidate(
                index=index,
                id=candidate.id,
                language=candidate.language,
                name=candidate.name,
                description=candidate.description,
                source_path=candidate.source_path,
                entrypoint=candidate.entrypoint,
                version=candidate.version,
                dependencies=candidate.dependencies,
                inputs=candidate.inputs,
                outputs=candidate.outputs,
                status=candidate.status,
                warnings=candidate.warnings,
            )
            result[indexed.language].append(indexed.to_dict())
        return result

    def import_scanned_tools(
        self,
        workspace_id: str,
        selections: Sequence[str | int],
        *,
        language: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Import one or more scanned candidates by list index or displayed slug."""

        self.initialize_tools(workspace_id)
        if not selections:
            raise ToolCandidateError(
                "Select one or more tools from the scanned candidate list; tool ID entry is not required."
            )
        grouped = self.scan_import_candidates(language)
        candidates = [item for items in grouped.values() for item in items]
        if not candidates:
            return {
                "status": "no_candidates",
                "message": "No Python/R tool directories were found to import.",
                "candidates": grouped,
                "imported": [],
                "errors": [],
            }
        selected = self._resolve_candidate_selections(candidates, selections)
        imported: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for item in selected:
            try:
                candidate = self._candidate_from_source(Path(item["source_path"]))
                if candidate is None or not candidate.importable:
                    reason = "; ".join(item.get("warnings") or []) or item.get(
                        "status", "invalid"
                    )
                    raise ToolCandidateError(
                        f"Tool candidate is not importable: {reason}"
                    )
                imported.append(
                    self._import_candidate(workspace_id, candidate, overwrite=overwrite)
                )
            except WorkspaceToolError as exc:
                errors.append(
                    {
                        "id": item.get("id"),
                        "language": item.get("language"),
                        "error": str(exc),
                    }
                )
        return {
            "status": "imported"
            if imported and not errors
            else "partial"
            if imported
            else "failed",
            "imported": imported,
            "errors": errors,
            "candidates": grouped,
        }

    def load_manifest(
        self, workspace_id: str, language: str, tool_id: str
    ) -> ToolManifest:
        lang = validate_language(language)
        slug = validate_tool_id(tool_id)
        manifest_path = self.resolve_within_tool(
            workspace_id, lang, slug, MANIFEST_FILE
        )
        if not manifest_path.is_file():
            raise ToolManifestError(f"Tool manifest not found: {manifest_path}")
        data = _safe_load_manifest(manifest_path)
        manifest = ToolManifest.from_dict(
            data, expected_id=slug, expected_language=lang
        )
        entrypoint = self.resolve_within_tool(
            workspace_id, lang, slug, manifest.entrypoint
        )
        if not entrypoint.is_file():
            raise ToolManifestError(f"Tool entrypoint not found: {entrypoint}")
        return manifest

    def _candidate_from_source(self, source_path: Path) -> ToolImportCandidate | None:
        source_path = validate_path_in_project_root(source_path, self.project_root)
        plugin_manifest = source_path / "plugin.yaml"
        workspace_manifest = source_path / MANIFEST_FILE
        data: dict[str, Any] = {}
        warnings: list[str] = []
        used_plugin_fallback = False
        if workspace_manifest.is_file():
            data = _load_candidate_metadata(workspace_manifest, warnings)
        elif plugin_manifest.is_file():
            data = _load_candidate_metadata(plugin_manifest, warnings)
            used_plugin_fallback = True
            warnings.append("workspace tool.yaml missing; displaying plugin metadata")
        else:
            warnings.append("metadata missing; displaying directory name only")

        if not isinstance(data, dict):
            data = {}
            warnings.append("metadata is not a mapping")

        raw_name = str(data.get("name") or source_path.name)
        try:
            tool_id = _slug_from_name(
                str(data.get("id") or raw_name or source_path.name)
            )
        except InvalidToolId:
            tool_id = _slug_from_name(source_path.name)
            warnings.append("metadata id is invalid; using directory slug")

        language_value = str(data.get("language") or "").lower()
        if language_value in SUPPORTED_LANGUAGES:
            # Language is explicitly provided and valid �?respect it
            pass
        elif language_value:
            # Language is set but not a recognized value �?fall back to directory inference
            inferred = "r" if source_path.name.lower().startswith("r_") else "python"
            language_value = inferred
            warnings.append(f"metadata language unsupported; inferred {inferred}")
        else:
            # Language is missing entirely �?infer from directory name prefix
            inferred = "r" if source_path.name.lower().startswith("r_") else "python"
            language_value = inferred
            warnings.append(f"metadata language missing; inferred {inferred}")
        lang = validate_language(language_value)

        entrypoint = str(data.get("entrypoint") or data.get("entry") or "")
        if not entrypoint:
            fallback_names = (
                ("runner.R", "main.R", "main.py")
                if lang == "r"
                else ("main.py", "runner.py")
            )
            entrypoint = next(
                (name for name in fallback_names if (source_path / name).is_file()),
                fallback_names[0],
            )
            warnings.append("entrypoint missing; using fallback")
        status = "ready"
        try:
            if Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts:
                raise ToolManifestError("entrypoint must stay inside source folder")
            entrypoint_path = validate_path_in_project_root(
                source_path / entrypoint, self.project_root
            )
            entrypoint_path.relative_to(source_path)
            if not entrypoint_path.is_file():
                raise ToolManifestError(f"entrypoint not found: {entrypoint}")
            if not used_plugin_fallback:
                if lang == "python" and entrypoint_path.suffix != ".py":
                    raise ToolManifestError("python tool entrypoint must be a .py file")
                if lang == "r" and entrypoint_path.suffix.lower() != ".r":
                    raise ToolManifestError("r tool entrypoint must be an .R file")
        except (ValueError, WorkspaceToolError) as exc:
            status = "invalid"
            warnings.append(str(exc))

        dependencies = data.get("dependencies", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            dependencies = []
            warnings.append("dependencies metadata invalid; using empty list")
        inputs = data.get("inputs", [])
        outputs = data.get("outputs", [])
        if not isinstance(inputs, list) or not all(
            isinstance(item, dict) for item in inputs
        ):
            inputs = []
            warnings.append("inputs metadata invalid; using empty list")
        if not isinstance(outputs, list) or not all(
            isinstance(item, dict) for item in outputs
        ):
            outputs = []
            warnings.append("outputs metadata invalid; using empty list")

        return ToolImportCandidate(
            index=0,
            id=tool_id,
            language=lang,
            name=raw_name,
            description=str(
                data.get("description") or "No description metadata provided"
            ),
            source_path=source_path,
            entrypoint=entrypoint if status == "ready" else None,
            version=str(data.get("version") or "0.0.0"),
            dependencies=list(dependencies),
            inputs=list(inputs),
            outputs=list(outputs),
            status=status,
            warnings=warnings,
        )

    def _resolve_candidate_selections(
        self, candidates: list[dict[str, Any]], selections: Sequence[str | int]
    ) -> list[dict[str, Any]]:
        if not selections:
            raise ToolCandidateError(
                "Select one or more tools from the scanned candidate list; tool ID entry is not required."
            )
        by_index = {str(item["index"]): item for item in candidates}
        by_slug = {f"{item['language']}/{item['id']}": item for item in candidates}
        by_slug.update({str(item["id"]): item for item in candidates})
        selected: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for selection in selections:
            key = str(selection).strip()
            item = by_index.get(key) or by_slug.get(key)
            if item is None:
                raise ToolCandidateError(f"Unknown scanned tool selection: {selection}")
            identity = (str(item["language"]), str(item["id"]))
            if identity not in seen:
                selected.append(item)
                seen.add(identity)
        return selected

    def _import_candidate(
        self, workspace_id: str, candidate: ToolImportCandidate, *, overwrite: bool
    ) -> dict[str, Any]:
        manifest = candidate.to_manifest()
        destination = self.tool_path(workspace_id, manifest.language, manifest.id)
        if destination.exists() and any(destination.iterdir()) and not overwrite:
            existing = self.load_manifest(workspace_id, manifest.language, manifest.id)
            return {
                "status": "exists",
                "tool": existing.to_dict(),
                "path": str(destination),
            }
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            candidate.source_path,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (destination / MANIFEST_FILE).write_text(
            yaml.safe_dump(manifest.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        loaded = self.load_manifest(workspace_id, manifest.language, manifest.id)
        return {
            "status": "imported",
            "tool": loaded.to_dict(),
            "path": str(destination),
        }

    def list_tools(
        self, workspace_id: str, language: str | None = None
    ) -> dict[str, list[dict[str, Any]]]:
        self.initialize_tools(workspace_id)
        languages = (
            [validate_language(language)] if language else list(SUPPORTED_LANGUAGES)
        )
        result: dict[str, list[dict[str, Any]]] = {lang: [] for lang in languages}
        for lang in languages:
            root = self.tools_language_path(workspace_id, lang)
            for entry in (
                sorted(root.iterdir(), key=lambda item: item.name)
                if root.exists()
                else []
            ):
                if not entry.is_dir():
                    continue
                try:
                    manifest = self.load_manifest(workspace_id, lang, entry.name)
                except WorkspaceToolError:
                    continue
                item = manifest.to_dict()
                item["path"] = str(entry)
                result[lang].append(item)
        return result

    def show_tool(
        self, workspace_id: str, language: str, tool_id: str
    ) -> dict[str, Any]:
        manifest = self.load_manifest(workspace_id, language, tool_id)
        tool_path = self.tool_path(workspace_id, language, tool_id)
        data = manifest.to_dict()
        data["path"] = str(tool_path)
        data["entrypoint_path"] = str(
            self.resolve_within_tool(
                workspace_id, language, tool_id, manifest.entrypoint
            )
        )
        return data

    def prepare_invocation(
        self,
        workspace_id: str,
        language: str,
        tool_id: str,
        *,
        dry_run: bool = False,
        input_path: str | Path | None = None,
        output_path: str | Path | None = None,
        permission_engine: PermissionEngine | None = None,
        audit_logger: AuditLogger | None = None,
        agent_id: str = "delta",
    ) -> ToolInvocationPlan:
        lang = validate_language(language)
        slug = validate_tool_id(tool_id)
        manifest = self.load_manifest(workspace_id, lang, slug)
        entrypoint = self.resolve_within_tool(
            workspace_id, lang, slug, manifest.entrypoint
        )
        resolved_input = self.resolve_within_workspace(workspace_id, input_path)
        resolved_output = self.resolve_within_workspace(workspace_id, output_path)
        command = self._command_for_manifest(
            manifest, entrypoint, resolved_input, resolved_output
        )

        policies_dir = self.project_root / ".supermedicine" / "policies"
        audit_log = policies_dir / "audit.jsonl"
        engine = permission_engine or PermissionEngine(policies_dir, audit_log)
        audit = audit_logger or AuditLogger(audit_log)
        authorize_dangerous_operation(
            permission_engine=engine,
            agent_id=agent_id,
            action="tool.run",
            path=entrypoint,
            project_root=self.project_root,
            context={
                "workspace_id": workspace_id,
                "language": lang,
                "tool_id": slug,
                "dry_run": dry_run,
            },
            audit_logger=audit,
            operation="workspace_tool_run",
        )

        return ToolInvocationPlan(
            workspace_id=workspace_id,
            language=lang,
            tool_id=slug,
            tool_path=self.tool_path(workspace_id, lang, slug),
            entrypoint=entrypoint,
            command=command,
            dry_run=dry_run,
            input_path=resolved_input,
            output_path=resolved_output,
            dependencies=manifest.dependencies,
            missing_runtime=self._missing_runtime(lang),
            missing_optional_dependencies=list(manifest.dependencies),
        )

    def _command_for_manifest(
        self,
        manifest: ToolManifest,
        entrypoint: Path,
        input_path: Path | None,
        output_path: Path | None,
    ) -> list[str]:
        if manifest.language == "python":
            command = ["python", str(entrypoint)]
        else:
            command = ["Rscript", str(entrypoint)]
        if input_path is not None:
            command.extend(["--input", str(input_path)])
        if output_path is not None:
            command.extend(["--output", str(output_path)])
        command.extend(["--tool-kind", manifest.id])
        return command

    @staticmethod
    def _missing_runtime(language: ToolLanguage) -> str | None:
        executable = "python" if language == "python" else "Rscript"
        return None if shutil.which(executable) else executable

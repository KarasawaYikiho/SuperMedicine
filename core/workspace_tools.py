"""Workspace-local modular Python/R research tool support.

Tools are stored under explicit workspaces as::

    workspaces/<id>/tools/python/<tool-id>/...
    workspaces/<id>/tools/r/<tool-id>/...

This module intentionally prepares guarded invocations instead of executing
untrusted workspace scripts directly.  PermissionEngine approval and audit
logging are still required for dry-run and prepared invocation paths.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
from typing import Any, Literal

import yaml

from core.operation_guard import authorize_dangerous_operation
from core.path_safety import validate_path_in_project_root
from core.workspace import WorkspaceManager
from permission.audit import AuditLogger
from permission.engine import PermissionEngine


ToolLanguage = Literal["python", "r"]

TOOLS_DIR = "tools"
MANIFEST_FILE = "tool.yaml"
SUPPORTED_LANGUAGES: tuple[ToolLanguage, ...] = ("python", "r")
BUILTIN_TOOLS: tuple[str, ...] = ("heatmap", "umap")

_TOOL_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")


class WorkspaceToolError(ValueError):
    """Base exception for workspace tool failures."""


class InvalidToolId(WorkspaceToolError):
    """Raised when a tool id is not a safe slug."""


class InvalidToolLanguage(WorkspaceToolError):
    """Raised when a language is not supported."""


class ToolNotFoundError(WorkspaceToolError):
    """Raised when a selected workspace tool does not exist."""


class ToolManifestError(WorkspaceToolError):
    """Raised when a manifest is missing or invalid."""


def validate_tool_id(tool_id: str) -> str:
    """Validate and return a safe lower-case tool slug."""

    if not isinstance(tool_id, str) or not _TOOL_ID_RE.fullmatch(tool_id):
        raise InvalidToolId("Tool id must be a lowercase slug using letters, digits, and hyphens")
    return tool_id


def validate_language(language: str) -> ToolLanguage:
    """Validate a workspace tool language."""

    if language not in SUPPORTED_LANGUAGES:
        raise InvalidToolLanguage("Tool language must be one of: python, r")
    return language  # type: ignore[return-value]


@dataclass(frozen=True)
class ToolManifest:
    id: str
    language: ToolLanguage
    name: str
    description: str
    entrypoint: str
    dependencies: list[str]
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    version: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, expected_id: str | None = None, expected_language: str | None = None) -> "ToolManifest":
        if not isinstance(data, dict):
            raise ToolManifestError("Tool manifest must be a mapping")

        required = ("id", "language", "name", "description", "entrypoint", "dependencies", "inputs", "outputs", "version")
        missing = [field for field in required if field not in data]
        if missing:
            raise ToolManifestError(f"Tool manifest missing required fields: {', '.join(missing)}")

        tool_id = validate_tool_id(str(data["id"]))
        language = validate_language(str(data["language"]))
        if expected_id is not None and tool_id != validate_tool_id(expected_id):
            raise ToolManifestError(f"Tool manifest id mismatch: expected {expected_id}, found {tool_id}")
        if expected_language is not None and language != validate_language(expected_language):
            raise ToolManifestError(f"Tool manifest language mismatch: expected {expected_language}, found {language}")

        dependencies = data["dependencies"]
        inputs = data["inputs"]
        outputs = data["outputs"]
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            raise ToolManifestError("Tool manifest dependencies must be a list of strings")
        if not isinstance(inputs, list) or not all(isinstance(item, dict) for item in inputs):
            raise ToolManifestError("Tool manifest inputs must be a list of mappings")
        if not isinstance(outputs, list) or not all(isinstance(item, dict) for item in outputs):
            raise ToolManifestError("Tool manifest outputs must be a list of mappings")

        entrypoint = str(data["entrypoint"])
        if Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts:
            raise ToolManifestError("Tool manifest entrypoint must be a relative path inside the tool folder")

        return cls(
            id=tool_id,
            language=language,
            name=str(data["name"]),
            description=str(data["description"]),
            entrypoint=entrypoint,
            dependencies=list(dependencies),
            inputs=list(inputs),
            outputs=list(outputs),
            version=str(data["version"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "language": self.language,
            "name": self.name,
            "description": self.description,
            "entrypoint": self.entrypoint,
            "dependencies": list(self.dependencies),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "version": self.version,
        }


@dataclass(frozen=True)
class ToolInvocationPlan:
    workspace_id: str
    language: ToolLanguage
    tool_id: str
    tool_path: Path
    entrypoint: Path
    command: list[str]
    dry_run: bool
    input_path: Path | None
    output_path: Path | None
    dependencies: list[str]
    missing_runtime: str | None = None
    missing_optional_dependencies: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "language": self.language,
            "tool_id": self.tool_id,
            "tool_path": str(self.tool_path),
            "entrypoint": str(self.entrypoint),
            "command": list(self.command),
            "dry_run": self.dry_run,
            "input_path": str(self.input_path) if self.input_path else None,
            "output_path": str(self.output_path) if self.output_path else None,
            "dependencies": list(self.dependencies),
            "missing_runtime": self.missing_runtime,
            "missing_optional_dependencies": list(self.missing_optional_dependencies or []),
            "status": "prepared" if self.dry_run else "not_executed",
            "message": "Command prepared only; workspace tool scripts are not executed by this safe foundation.",
        }


def _manifest_text(tool_id: str, language: ToolLanguage, name: str, description: str, entrypoint: str, dependencies: list[str]) -> str:
    return yaml.safe_dump(
        {
            "id": tool_id,
            "language": language,
            "name": name,
            "description": description,
            "entrypoint": entrypoint,
            "dependencies": dependencies,
            "inputs": [{"name": "input", "description": "Input matrix/table path", "required": False}],
            "outputs": [{"name": "output", "description": "Output artifact path", "required": False}],
            "version": "1.0.0",
        },
        sort_keys=False,
        allow_unicode=True,
    )


PYTHON_RUNNER = '''#!/usr/bin/env python3
"""Workspace-local optional Python visualization runner."""
from __future__ import annotations

import argparse
import importlib.util
import sys


def missing(packages: list[str]) -> list[str]:
    return [package for package in packages if importlib.util.find_spec(package) is None]


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional SuperMedicine Python workspace tool")
    parser.add_argument("--input", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--check-deps", action="store_true")
    parser.add_argument("--tool-kind", default="visualization")
    args = parser.parse_args()
    required = ["pandas", "matplotlib", "seaborn"]
    if args.tool_kind == "umap":
        required.append("umap")
    unavailable = missing(required)
    if unavailable:
        print("Missing optional Python dependencies: " + ", ".join(unavailable))
        print("Install them in your workspace environment before running this tool.")
        return 2
    if args.check_deps:
        print("All optional Python dependencies are available.")
        return 0
    print("Dependencies are available; implement project-specific data loading before execution.")
    print(f"input={args.input!r} output={args.output!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

R_RUNNER = '''#!/usr/bin/env Rscript
args <- commandArgs(trailingOnly = TRUE)
tool_kind <- "visualization"
if ("--tool-kind" %in% args) {
  idx <- match("--tool-kind", args)
  if (!is.na(idx) && length(args) >= idx + 1) tool_kind <- args[[idx + 1]]
}
required <- c("ggplot2", "readr")
if (tool_kind == "heatmap") required <- c(required, "pheatmap")
if (tool_kind == "umap") required <- c(required, "umap")
missing <- required[!vapply(required, requireNamespace, quietly = TRUE, FUN.VALUE = logical(1))]
if (length(missing) > 0) {
  cat("Missing optional R dependencies:", paste(missing, collapse = ", "), "\n")
  cat("Install them in your workspace R library before running this tool.\n")
  quit(status = 2)
}
cat("All optional R dependencies are available. Add project-specific data loading before execution.\n")
'''


BUILTIN_TEMPLATES: dict[tuple[ToolLanguage, str], dict[str, str]] = {
    ("python", "heatmap"): {
        MANIFEST_FILE: _manifest_text("heatmap", "python", "Python heatmap", "Optional Python heatmap template", "runner.py", ["pandas", "matplotlib", "seaborn"]),
        "README.md": "# Python heatmap\n\nWorkspace-local heatmap scaffold. Optional dependencies are reported by `runner.py`.\n",
        "runner.py": PYTHON_RUNNER.replace('--tool-kind", default="visualization"', '--tool-kind", default="heatmap"'),
    },
    ("python", "umap"): {
        MANIFEST_FILE: _manifest_text("umap", "python", "Python UMAP", "Optional Python UMAP template", "runner.py", ["pandas", "matplotlib", "umap-learn"]),
        "README.md": "# Python UMAP\n\nWorkspace-local UMAP scaffold. Optional dependencies are reported by `runner.py`.\n",
        "runner.py": PYTHON_RUNNER.replace('--tool-kind", default="visualization"', '--tool-kind", default="umap"'),
    },
    ("r", "heatmap"): {
        MANIFEST_FILE: _manifest_text("heatmap", "r", "R heatmap", "Optional R heatmap template", "runner.R", ["ggplot2", "readr", "pheatmap"]),
        "README.md": "# R heatmap\n\nWorkspace-local R heatmap scaffold. Optional dependencies are reported by `runner.R`.\n",
        "runner.R": R_RUNNER.replace('tool_kind <- "visualization"', 'tool_kind <- "heatmap"'),
    },
    ("r", "umap"): {
        MANIFEST_FILE: _manifest_text("umap", "r", "R UMAP", "Optional R UMAP template", "runner.R", ["ggplot2", "readr", "umap"]),
        "README.md": "# R UMAP\n\nWorkspace-local R UMAP scaffold. Optional dependencies are reported by `runner.R`.\n",
        "runner.R": R_RUNNER.replace('tool_kind <- "visualization"', 'tool_kind <- "umap"'),
    },
}


class WorkspaceToolService:
    """Manage modular tools inside explicit workspace directories."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path.cwd().resolve() if project_root is None else Path(project_root).resolve()
        self.workspace_manager = WorkspaceManager(self.project_root)

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
        return validate_path_in_project_root(workspace / TOOLS_DIR / lang, self.project_root)

    def tool_path(self, workspace_id: str, language: str, tool_id: str) -> Path:
        path = validate_path_in_project_root(self.tools_language_path(workspace_id, language) / validate_tool_id(tool_id), self.project_root)
        language_root = self.tools_language_path(workspace_id, language)
        path.relative_to(language_root)
        return path

    def resolve_within_tool(self, workspace_id: str, language: str, tool_id: str, relative_path: str | Path) -> Path:
        root = self.tool_path(workspace_id, language, tool_id)
        candidate = validate_path_in_project_root(root / relative_path, self.project_root)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise WorkspaceToolError(f"Path resolves outside tool folder: {relative_path}") from exc
        return candidate

    def resolve_within_workspace(self, workspace_id: str, path: str | Path | None) -> Path | None:
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
            raise WorkspaceToolError(f"Path resolves outside workspace: {path}") from exc
        return resolved

    def add_builtin_tool(self, workspace_id: str, language: str, tool_id: str, *, overwrite: bool = False) -> dict[str, Any]:
        lang = validate_language(language)
        slug = validate_tool_id(tool_id)
        key = (lang, slug)
        if key not in BUILTIN_TEMPLATES:
            raise ToolNotFoundError(f"Unknown built-in tool template: {lang}/{slug}")
        destination = self.tool_path(workspace_id, lang, slug)
        if destination.exists() and any(destination.iterdir()) and not overwrite:
            manifest = self.load_manifest(workspace_id, lang, slug)
            return {"status": "exists", "tool": manifest.to_dict(), "path": str(destination)}
        if destination.exists() and overwrite:
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
        for filename, content in BUILTIN_TEMPLATES[key].items():
            target = self.resolve_within_tool(workspace_id, lang, slug, filename)
            target.write_text(content, encoding="utf-8")
        manifest = self.load_manifest(workspace_id, lang, slug)
        return {"status": "added", "tool": manifest.to_dict(), "path": str(destination)}

    def load_manifest(self, workspace_id: str, language: str, tool_id: str) -> ToolManifest:
        lang = validate_language(language)
        slug = validate_tool_id(tool_id)
        manifest_path = self.resolve_within_tool(workspace_id, lang, slug, MANIFEST_FILE)
        if not manifest_path.is_file():
            raise ToolManifestError(f"Tool manifest not found: {manifest_path}")
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        manifest = ToolManifest.from_dict(data, expected_id=slug, expected_language=lang)
        entrypoint = self.resolve_within_tool(workspace_id, lang, slug, manifest.entrypoint)
        if not entrypoint.is_file():
            raise ToolManifestError(f"Tool entrypoint not found: {entrypoint}")
        return manifest

    def list_tools(self, workspace_id: str, language: str | None = None) -> dict[str, list[dict[str, Any]]]:
        self.initialize_tools(workspace_id)
        languages = [validate_language(language)] if language else list(SUPPORTED_LANGUAGES)
        result: dict[str, list[dict[str, Any]]] = {lang: [] for lang in languages}
        for lang in languages:
            root = self.tools_language_path(workspace_id, lang)
            for entry in sorted(root.iterdir(), key=lambda item: item.name) if root.exists() else []:
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

    def show_tool(self, workspace_id: str, language: str, tool_id: str) -> dict[str, Any]:
        manifest = self.load_manifest(workspace_id, language, tool_id)
        tool_path = self.tool_path(workspace_id, language, tool_id)
        data = manifest.to_dict()
        data["path"] = str(tool_path)
        data["entrypoint_path"] = str(self.resolve_within_tool(workspace_id, language, tool_id, manifest.entrypoint))
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
        entrypoint = self.resolve_within_tool(workspace_id, lang, slug, manifest.entrypoint)
        resolved_input = self.resolve_within_workspace(workspace_id, input_path)
        resolved_output = self.resolve_within_workspace(workspace_id, output_path)
        command = self._command_for_manifest(manifest, entrypoint, resolved_input, resolved_output)

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
            context={"workspace_id": workspace_id, "language": lang, "tool_id": slug, "dry_run": dry_run},
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

    def _command_for_manifest(self, manifest: ToolManifest, entrypoint: Path, input_path: Path | None, output_path: Path | None) -> list[str]:
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

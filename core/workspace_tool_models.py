"""Workspace tool data models, exceptions, constants, and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Literal

import yaml


ToolLanguage = Literal["python", "r"]

TOOLS_DIR = "tools"
MANIFEST_FILE = "tool.yaml"
SUPPORTED_LANGUAGES: tuple[ToolLanguage, ...] = ("python", "r")
BUILTIN_TOOLS: tuple[str, ...] = ("heatmap", "umap")
TOOL_SOURCE_ROOT = "plugins/tools"
PYTHON_TOOL_STORAGE = "workspaces/<workspace-id>/tools/python/<tool-id>/"
R_TOOL_STORAGE = "workspaces/<workspace-id>/tools/r/<tool-id>/"

_TOOL_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
MAX_TOOL_MANIFEST_BYTES = 256 * 1024


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


class ToolCandidateError(WorkspaceToolError):
    """Raised when an import candidate cannot become a workspace tool."""


def _read_limited_text(path: Path, *, max_bytes: int = MAX_TOOL_MANIFEST_BYTES) -> str:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ToolManifestError(f"Tool manifest is too large: {path}")
    return raw.decode("utf-8")


def _safe_load_manifest(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(_read_limited_text(path)) or {}
    if not isinstance(data, dict):
        raise ToolManifestError("Tool manifest must be a mapping")
    return data


def _load_candidate_metadata(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        return _safe_load_manifest(path)
    except (ToolManifestError, yaml.YAMLError) as exc:
        warnings.append(str(exc))
        return {}


def validate_tool_id(tool_id: str) -> str:
    """Validate and return a safe lower-case tool slug."""

    if not isinstance(tool_id, str) or not _TOOL_ID_RE.fullmatch(tool_id):
        raise InvalidToolId(
            "Tool id must be a lowercase slug using letters, digits, and hyphens"
        )
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
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        expected_id: str | None = None,
        expected_language: str | None = None,
    ) -> "ToolManifest":
        if not isinstance(data, dict):
            raise ToolManifestError("Tool manifest must be a mapping")

        required = (
            "id",
            "language",
            "name",
            "description",
            "entrypoint",
            "dependencies",
            "inputs",
            "outputs",
            "version",
        )
        missing = [field for field in required if field not in data]
        if missing:
            raise ToolManifestError(
                f"Tool manifest missing required fields: {', '.join(missing)}"
            )

        tool_id = validate_tool_id(str(data["id"]))
        language = validate_language(str(data["language"]))
        if expected_id is not None and tool_id != validate_tool_id(expected_id):
            raise ToolManifestError(
                f"Tool manifest id mismatch: expected {expected_id}, found {tool_id}"
            )
        if expected_language is not None and language != validate_language(
            expected_language
        ):
            raise ToolManifestError(
                f"Tool manifest language mismatch: expected {expected_language}, found {language}"
            )

        dependencies = data["dependencies"]
        inputs = data["inputs"]
        outputs = data["outputs"]
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise ToolManifestError(
                "Tool manifest dependencies must be a list of strings"
            )
        if not isinstance(inputs, list) or not all(
            isinstance(item, dict) for item in inputs
        ):
            raise ToolManifestError("Tool manifest inputs must be a list of mappings")
        if not isinstance(outputs, list) or not all(
            isinstance(item, dict) for item in outputs
        ):
            raise ToolManifestError("Tool manifest outputs must be a list of mappings")

        entrypoint = str(data["entrypoint"])
        if Path(entrypoint).is_absolute() or ".." in Path(entrypoint).parts:
            raise ToolManifestError(
                "Tool manifest entrypoint must be a relative path inside the tool folder"
            )

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
            "missing_optional_dependencies": list(
                self.missing_optional_dependencies or []
            ),
            "status": "prepared" if self.dry_run else "not_executed",
            "message": "Command prepared only; workspace tool scripts are not executed by this safe foundation.",
        }


@dataclass(frozen=True)
class ToolImportCandidate:
    """A Python/R tool discovered from the project tool source directory."""

    index: int
    id: str
    language: ToolLanguage
    name: str
    description: str
    source_path: Path
    entrypoint: str | None
    version: str
    dependencies: list[str]
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]
    status: str
    warnings: list[str]

    @property
    def importable(self) -> bool:
        return self.status == "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "id": self.id,
            "language": self.language,
            "name": self.name,
            "description": self.description,
            "source_path": str(self.source_path),
            "entrypoint": self.entrypoint,
            "version": self.version,
            "dependencies": list(self.dependencies),
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "status": self.status,
            "warnings": list(self.warnings),
            "importable": self.importable,
        }

    def to_manifest(self) -> ToolManifest:
        if not self.importable or not self.entrypoint:
            raise ToolCandidateError(
                f"Tool candidate is not importable: {self.language}/{self.id}"
            )
        return ToolManifest(
            id=self.id,
            language=self.language,
            name=self.name,
            description=self.description,
            entrypoint=self.entrypoint,
            dependencies=list(self.dependencies),
            inputs=list(self.inputs),
            outputs=list(self.outputs),
            version=self.version,
        )

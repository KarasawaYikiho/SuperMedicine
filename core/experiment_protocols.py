"""Experiment protocol discovery and configuration loading.

Experiment protocols are stored as configuration files under the plugin tree in
``plugins/experiments``. The loader discovers all YAML/JSON files in that single
directory, validates them, and exposes protocols by ID or alias.
"""

from __future__ import annotations

import json
import re
from hashlib import sha1
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


EXPERIMENT_CONFIG_DIRNAME = "experiments"
EXPERIMENT_CONFIG_EXTENSIONS = {".json", ".yaml", ".yml"}
EXPERIMENT_CONFIG_AUTHORING_RULES = """Experiment configuration authoring rules:
- Save experiment protocol files only under plugins/experiments/ using .yaml, .yml, or .json.
- Required root fields: protocol_id, title, description, steps. Optional root fields: version, metadata.
- protocol_id must be unique across all experiment configs and use lowercase letters, numbers, underscores, or hyphens.
- metadata.aliases, when present, must be a list and every alias must avoid conflicts with existing IDs/aliases.
- steps must be a non-empty list. Each step requires unique step_id and title; instructions should describe safe research workflow guidance.
- input_fields entries may include name, label, field_type, required, help_text. Field names should be machine-readable.
- calculation_requests entries may include request_id, kind, description, parameters, plugin_name, action. Existing WB plugin compatibility is preserved by explicit experiment-wb requests or legacy WB mappings.
- expected_outputs should list machine-readable output keys for each step.
- Never overwrite an existing file or duplicate an existing protocol ID/alias unless the caller explicitly confirms overwrite.
- Reject invalid formats, unsafe names, unwritable directories, and naming conflicts with a clear error.
"""

_SAFE_PROTOCOL_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class ExperimentProtocolConfigError(ValueError):
    """Raised when experiment protocol configuration cannot be loaded."""


class ExperimentProtocolAuthoringError(ValueError):
    """Raised when an experiment protocol cannot be authored or saved safely."""


def default_experiment_config_dir() -> Path:
    """Return the repository plugin experiment configuration directory."""

    return Path(__file__).resolve().parents[1] / "plugins" / EXPERIMENT_CONFIG_DIRNAME


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "_", value.strip().lower()).strip("_-")
    if len(slug) < 2:
        slug = f"{slug or 'experiment'}_{sha1(value.encode('utf-8')).hexdigest()[:8]}"
    return slug[:64]


def _assert_safe_protocol_id(protocol_id: str) -> None:
    if not _SAFE_PROTOCOL_ID.match(protocol_id):
        raise ExperimentProtocolAuthoringError(
            "experiment protocol_id must be 2-64 chars of lowercase letters, numbers, underscores, or hyphens"
        )


def _ensure_writable_config_dir(config_dir: Path) -> None:
    if config_dir.exists() and not config_dir.is_dir():
        raise ExperimentProtocolAuthoringError(
            f"experiment config path is not a directory: {config_dir}"
        )
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise ExperimentProtocolAuthoringError(
            f"experiment config directory is not writable: {config_dir}: {exc}"
        ) from exc


@dataclass(frozen=True)
class ExperimentInputField:
    """A user-provided value requested by a protocol step."""

    name: str
    label: str
    field_type: str = "text"
    required: bool = False
    help_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "field_type": self.field_type,
            "required": self.required,
            "help_text": self.help_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentInputField":
        return cls(
            name=str(data["name"]),
            label=str(data.get("label", data["name"])),
            field_type=str(data.get("field_type", "text")),
            required=bool(data.get("required", False)),
            help_text=str(data.get("help_text", "")),
        )


@dataclass(frozen=True)
class CalculationRequest:
    """A deferred calculation descriptor for a later plugin or service."""

    request_id: str
    kind: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    plugin_name: str | None = None
    action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "request_id": self.request_id,
            "kind": self.kind,
            "description": self.description,
            "parameters": dict(self.parameters),
        }
        if self.plugin_name:
            data["plugin_name"] = self.plugin_name
        if self.action:
            data["action"] = self.action
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalculationRequest":
        return cls(
            request_id=str(data["request_id"]),
            kind=str(data["kind"]),
            description=str(data.get("description", "")),
            parameters=dict(data.get("parameters", {})),
            plugin_name=str(data["plugin_name"]) if data.get("plugin_name") else None,
            action=str(data["action"]) if data.get("action") else None,
        )


@dataclass(frozen=True)
class ExperimentStep:
    """One step in an experiment protocol."""

    step_id: str
    title: str
    instructions: str
    input_fields: tuple[ExperimentInputField, ...] = ()
    calculation_requests: tuple[CalculationRequest, ...] = ()
    expected_outputs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "instructions": self.instructions,
            "input_fields": [field.to_dict() for field in self.input_fields],
            "calculation_requests": [
                request.to_dict() for request in self.calculation_requests
            ],
            "expected_outputs": list(self.expected_outputs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentStep":
        return cls(
            step_id=str(data["step_id"]),
            title=str(data["title"]),
            instructions=str(data.get("instructions", "")),
            input_fields=tuple(
                ExperimentInputField.from_dict(item)
                for item in data.get("input_fields", [])
            ),
            calculation_requests=tuple(
                CalculationRequest.from_dict(item)
                for item in data.get("calculation_requests", [])
            ),
            expected_outputs=tuple(
                str(item) for item in data.get("expected_outputs", [])
            ),
        )


@dataclass(frozen=True)
class ExperimentProtocol:
    """A reusable experiment workflow definition."""

    protocol_id: str
    title: str
    description: str
    steps: tuple[ExperimentStep, ...]
    version: str = "1.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("experiment protocol must contain at least one step")
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("experiment protocol step IDs must be unique")

    def get_step(self, step_id: str) -> ExperimentStep:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(f"unknown experiment step: {step_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "metadata": dict(self.metadata),
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentProtocol":
        return cls(
            protocol_id=str(data["protocol_id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            version=str(data.get("version", "1.0")),
            metadata=dict(data.get("metadata", {})),
            steps=tuple(ExperimentStep.from_dict(item) for item in data["steps"]),
        )


def _load_config_file(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = json.loads(raw) if path.suffix.lower() == ".json" else yaml.safe_load(raw)
    except Exception as exc:
        raise ExperimentProtocolConfigError(
            f"experiment config format error in {path}: {exc}"
        ) from exc
    if not isinstance(loaded, dict):
        raise ExperimentProtocolConfigError(
            f"experiment config format error in {path}: root must be an object"
        )
    return loaded


def _config_paths(config_dir: Path) -> list[Path]:
    if not config_dir.exists():
        raise ExperimentProtocolConfigError(
            f"experiment config directory missing: {config_dir}"
        )
    if not config_dir.is_dir():
        raise ExperimentProtocolConfigError(
            f"experiment config path is not a directory: {config_dir}"
        )
    paths = sorted(
        path
        for path in config_dir.iterdir()
        if path.is_file() and path.suffix.lower() in EXPERIMENT_CONFIG_EXTENSIONS
    )
    if not paths:
        raise ExperimentProtocolConfigError(
            f"experiment config directory is empty: {config_dir}"
        )
    return paths


def load_protocols(
    config_dir: str | Path | None = None,
) -> tuple[dict[str, ExperimentProtocol], dict[str, Path]]:
    """Load experiment protocols from the unified plugin experiment directory."""

    directory = Path(config_dir) if config_dir is not None else default_experiment_config_dir()
    protocols_by_name: dict[str, ExperimentProtocol] = {}
    sources_by_name: dict[str, Path] = {}
    normalized_names: dict[str, str] = {}
    canonical_titles: dict[str, Path] = {}
    canonical_ids: dict[str, Path] = {}

    for path in _config_paths(directory):
        data = _load_config_file(path)
        try:
            protocol = ExperimentProtocol.from_dict(data)
        except Exception as exc:
            raise ExperimentProtocolConfigError(
                f"experiment config format error in {path}: {exc}"
            ) from exc

        normalized_id = protocol.protocol_id.casefold()
        if normalized_id in canonical_ids:
            raise ExperimentProtocolConfigError(
                "duplicate experiment protocol id "
                f"'{protocol.protocol_id}' in {path} and {canonical_ids[normalized_id]}"
            )
        canonical_ids[normalized_id] = path

        normalized_title = protocol.title.casefold()
        if normalized_title in canonical_titles:
            raise ExperimentProtocolConfigError(
                "duplicate experiment protocol name "
                f"'{protocol.title}' in {path} and {canonical_titles[normalized_title]}"
            )
        canonical_titles[normalized_title] = path

        names = [protocol.protocol_id]
        aliases = protocol.metadata.get("aliases", [])
        if not isinstance(aliases, list):
            raise ExperimentProtocolConfigError(
                f"experiment config format error in {path}: metadata.aliases must be a list"
            )
        names.extend(str(alias) for alias in aliases)
        for name in names:
            key = str(name)
            normalized = key.casefold()
            if normalized in normalized_names:
                previous_key = normalized_names[normalized]
                previous = sources_by_name[previous_key]
                raise ExperimentProtocolConfigError(
                    f"duplicate experiment protocol name '{key}' in {path} and {previous}"
                )
            protocols_by_name[key] = protocol
            sources_by_name[key] = path
            normalized_names[normalized] = key

    return protocols_by_name, sources_by_name


def validate_experiment_config(data: dict[str, Any]) -> ExperimentProtocol:
    """Validate a candidate experiment config and return its normalized protocol."""

    if not isinstance(data, dict):
        raise ExperimentProtocolAuthoringError("experiment config root must be an object")
    try:
        protocol = ExperimentProtocol.from_dict(data)
    except Exception as exc:
        raise ExperimentProtocolAuthoringError(
            f"experiment config format error: {exc}"
        ) from exc
    _assert_safe_protocol_id(protocol.protocol_id)
    for step in protocol.steps:
        _assert_safe_protocol_id(step.step_id)
        for input_field in step.input_fields:
            if not input_field.name:
                raise ExperimentProtocolAuthoringError(
                    f"step {step.step_id} contains an empty input field name"
                )
        for request in step.calculation_requests:
            if not request.request_id or not request.kind:
                raise ExperimentProtocolAuthoringError(
                    f"step {step.step_id} contains an invalid calculation request"
                )
    aliases = protocol.metadata.get("aliases", [])
    if aliases is not None and not isinstance(aliases, list):
        raise ExperimentProtocolAuthoringError("metadata.aliases must be a list")
    return protocol


def summarize_experiment_protocol(protocol: ExperimentProtocol) -> dict[str, Any]:
    """Return an LLM-safe summary of an experiment protocol."""

    return {
        "protocol_id": protocol.protocol_id,
        "title": protocol.title,
        "description": protocol.description,
        "version": protocol.version,
        "metadata": dict(protocol.metadata),
        "step_count": len(protocol.steps),
        "steps": [
            {
                "step_id": step.step_id,
                "title": step.title,
                "instructions": step.instructions,
                "input_fields": [field.to_dict() for field in step.input_fields],
                "calculation_requests": [
                    request.to_dict() for request in step.calculation_requests
                ],
                "expected_outputs": list(step.expected_outputs),
            }
            for step in protocol.steps
        ],
    }


def build_experiment_llm_context(protocol_id: str | None = None) -> dict[str, Any]:
    """Build the secret-free experiment configuration context for LLM prompts."""

    protocols = list_protocols()
    selected = None
    if protocol_id:
        selected = get_protocol(protocol_id)
    elif protocols:
        selected = next(
            (protocol for protocol in protocols if protocol.protocol_id == "western_blot_basic"),
            protocols[0],
        )
    return {
        "config_directory": str(default_experiment_config_dir()),
        "authoring_rules": EXPERIMENT_CONFIG_AUTHORING_RULES.strip(),
        "available_protocols": [
            {
                "protocol_id": protocol.protocol_id,
                "title": protocol.title,
                "aliases": protocol.metadata.get("aliases", []),
                "step_count": len(protocol.steps),
            }
            for protocol in protocols
        ],
        "selected_protocol": summarize_experiment_protocol(selected) if selected else None,
    }


def draft_experiment_config_from_instruction(instruction: str) -> dict[str, Any]:
    """Create a conservative valid experiment config draft from a user instruction."""

    text = instruction.strip()
    if not text:
        raise ExperimentProtocolAuthoringError("experiment instruction cannot be empty")
    title = text.splitlines()[0].strip()[:80] or "新增实验配置"
    protocol_id = _safe_slug(title)
    return {
        "protocol_id": protocol_id,
        "title": title,
        "description": text,
        "version": "1.0",
        "metadata": {
            "source": "llm_draft",
            "aliases": [],
        },
        "steps": [
            {
                "step_id": "plan",
                "title": "实验规划",
                "instructions": "确认实验目的、样本/材料、关键限制、参数范围和人工审核要求。",
                "input_fields": [
                    {
                        "name": "objective",
                        "label": "实验目的",
                        "required": True,
                        "help_text": "研究目的或待验证问题。",
                    },
                    {
                        "name": "constraints",
                        "label": "限制条件",
                        "required": False,
                        "help_text": "伦理、安全、样本量、设备或试剂限制。",
                    },
                ],
                "expected_outputs": ["experiment_plan"],
            },
            {
                "step_id": "execute",
                "title": "执行记录",
                "instructions": "按确认后的方案记录实验步骤、关键参数、偏差和观察结果。",
                "input_fields": [
                    {
                        "name": "parameters",
                        "label": "关键参数",
                        "field_type": "json",
                        "required": True,
                        "help_text": "温度、时间、浓度、批次等可修改参数。",
                    },
                    {
                        "name": "observations",
                        "label": "观察记录",
                        "required": False,
                    },
                ],
                "expected_outputs": ["execution_record"],
            },
            {
                "step_id": "review",
                "title": "结果复核",
                "instructions": "汇总输出、异常、可重复性信息，并标记需要专家复核的事项。",
                "input_fields": [
                    {"name": "results", "label": "结果摘要", "required": True},
                    {"name": "review_notes", "label": "复核备注", "required": False},
                ],
                "expected_outputs": ["review_record"],
            },
        ],
    }


def save_experiment_config(
    data: dict[str, Any],
    *,
    config_dir: str | Path | None = None,
    filename: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Validate and write an experiment config into the unified directory safely."""

    protocol = validate_experiment_config(data)
    directory = Path(config_dir) if config_dir is not None else default_experiment_config_dir()
    _ensure_writable_config_dir(directory)
    safe_name = filename or f"{protocol.protocol_id}.yaml"
    target = directory / safe_name
    if target.name != safe_name or target.suffix.lower() not in EXPERIMENT_CONFIG_EXTENSIONS:
        raise ExperimentProtocolAuthoringError(
            "experiment config filename must be a safe .yaml, .yml, or .json basename"
        )
    if target.exists() and not overwrite:
        raise ExperimentProtocolAuthoringError(
            f"experiment config already exists: {target}; pass overwrite=True only after explicit confirmation"
        )
    try:
        existing, sources = load_protocols(directory)
    except ExperimentProtocolConfigError:
        existing, sources = {}, {}
    candidate_names = [protocol.protocol_id] + [
        str(alias) for alias in protocol.metadata.get("aliases", [])
    ]
    for name in candidate_names:
        for existing_name, existing_protocol in existing.items():
            source = sources.get(existing_name)
            same_target = source is not None and source.resolve() == target.resolve()
            if same_target and overwrite:
                continue
            if name.casefold() == existing_name.casefold() or name.casefold() == existing_protocol.protocol_id.casefold():
                raise ExperimentProtocolAuthoringError(
                    f"experiment protocol name conflict: {name} already exists in {source}"
                )
            if protocol.title.casefold() == existing_protocol.title.casefold():
                raise ExperimentProtocolAuthoringError(
                    f"experiment protocol title conflict: {protocol.title} already exists in {source}"
                )
    payload = protocol.to_dict()
    try:
        if target.suffix.lower() == ".json":
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            target.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception as exc:
        raise ExperimentProtocolAuthoringError(
            f"could not write experiment config {target}: {exc}"
        ) from exc
    return {
        "ok": True,
        "path": str(target),
        "protocol": summarize_experiment_protocol(protocol),
        "discoverable": protocol.protocol_id in load_protocols(directory)[0],
    }


def create_experiment_config_from_instruction(
    instruction: str,
    *,
    config_dir: str | Path | None = None,
    filename: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Draft, validate, and save an experiment config from natural language."""

    return save_experiment_config(
        draft_experiment_config_from_instruction(instruction),
        config_dir=config_dir,
        filename=filename,
        overwrite=overwrite,
    )


def get_protocol(protocol_id: str) -> ExperimentProtocol:
    """Return a configured protocol by ID or alias."""

    protocols, _sources = load_protocols()
    try:
        return protocols[protocol_id]
    except KeyError as exc:
        normalized = protocol_id.casefold()
        for name, protocol in protocols.items():
            if name.casefold() == normalized:
                return protocol
        raise KeyError(f"unknown experiment protocol: {protocol_id}") from exc


def list_protocols() -> list[ExperimentProtocol]:
    """Return unique configured protocols."""

    protocols_by_name, _sources = load_protocols()
    protocols: dict[str, ExperimentProtocol] = {}
    for protocol in protocols_by_name.values():
        protocols[protocol.protocol_id] = protocol
    return sorted(protocols.values(), key=lambda protocol: protocol.title)

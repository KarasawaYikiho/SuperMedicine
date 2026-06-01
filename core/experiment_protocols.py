"""Built-in experiment protocol definitions.

This module intentionally contains protocol structure only. Step-specific
calculation requests are represented as generic descriptors so later plugins can
perform reagent math or external assistance without hard-coding that logic into
the core state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "kind": self.kind,
            "description": self.description,
            "parameters": dict(self.parameters),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalculationRequest":
        return cls(
            request_id=str(data["request_id"]),
            kind=str(data["kind"]),
            description=str(data.get("description", "")),
            parameters=dict(data.get("parameters", {})),
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
            expected_outputs=tuple(str(item) for item in data.get("expected_outputs", [])),
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


WB_PROTOCOL = ExperimentProtocol(
    protocol_id="western_blot_basic",
    title="Western Blot 基础流程",
    description="Western Blot 实验指导骨架，用于逐步记录样本、转膜、封闭、孵育、显影与分析信息。",
    metadata={"category": "WB", "built_in": True},
    steps=(
        ExperimentStep(
            step_id="sample_preparation",
            title="样本准备",
            instructions="记录样本来源、目标蛋白和上样相关信息。",
            input_fields=(
                ExperimentInputField("sample_id", "样本编号", required=True),
                ExperimentInputField("target_protein", "目标蛋白", required=True),
                ExperimentInputField("notes", "样本备注"),
            ),
            calculation_requests=(
                CalculationRequest(
                    request_id="protein_loading_normalization",
                    kind="normalization",
                    description="预留蛋白上样量归一化计算请求。",
                ),
            ),
            expected_outputs=("sample_record",),
        ),
        ExperimentStep(
            step_id="gel_electrophoresis",
            title="凝胶电泳",
            instructions="记录凝胶类型、电泳条件和观察到的迁移情况。",
            input_fields=(
                ExperimentInputField("gel_percentage", "凝胶浓度"),
                ExperimentInputField("run_condition", "电泳条件"),
            ),
            expected_outputs=("electrophoresis_record",),
        ),
        ExperimentStep(
            step_id="transfer",
            title="转膜",
            instructions="记录膜类型、转膜条件以及转膜质量观察。",
            input_fields=(
                ExperimentInputField("membrane_type", "膜类型"),
                ExperimentInputField("transfer_condition", "转膜条件"),
            ),
            expected_outputs=("transfer_record",),
        ),
        ExperimentStep(
            step_id="blocking_and_antibody",
            title="封闭与抗体孵育",
            instructions="记录封闭条件、一抗/二抗信息和孵育条件。",
            input_fields=(
                ExperimentInputField("blocking_buffer", "封闭液"),
                ExperimentInputField("primary_antibody", "一抗信息", required=True),
                ExperimentInputField("secondary_antibody", "二抗信息"),
            ),
            calculation_requests=(
                CalculationRequest(
                    request_id="antibody_dilution",
                    kind="dilution",
                    description="预留抗体稀释计算请求。",
                ),
            ),
            expected_outputs=("antibody_incubation_record",),
        ),
        ExperimentStep(
            step_id="detection_and_analysis",
            title="显影与分析",
            instructions="记录显影方式、图像文件、条带观察和定量分析输出。",
            input_fields=(
                ExperimentInputField("detection_method", "显影方式"),
                ExperimentInputField("image_reference", "图像或文件引用"),
                ExperimentInputField("analysis_notes", "分析备注"),
            ),
            calculation_requests=(
                CalculationRequest(
                    request_id="band_intensity_analysis",
                    kind="analysis",
                    description="预留条带灰度/强度分析请求。",
                ),
            ),
            expected_outputs=("analysis_record",),
        ),
    ),
)

BUILT_IN_PROTOCOLS: dict[str, ExperimentProtocol] = {
    WB_PROTOCOL.protocol_id: WB_PROTOCOL,
    "wb": WB_PROTOCOL,
}


def get_protocol(protocol_id: str) -> ExperimentProtocol:
    """Return a built-in protocol by ID or alias."""

    try:
        return BUILT_IN_PROTOCOLS[protocol_id]
    except KeyError as exc:
        raise KeyError(f"unknown experiment protocol: {protocol_id}") from exc


def list_protocols() -> list[ExperimentProtocol]:
    """Return unique built-in protocols."""

    protocols: dict[str, ExperimentProtocol] = {}
    for protocol in BUILT_IN_PROTOCOLS.values():
        protocols[protocol.protocol_id] = protocol
    return list(protocols.values())

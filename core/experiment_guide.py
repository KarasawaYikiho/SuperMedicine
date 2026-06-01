"""Core experiment guide state machine.

The guide is a standalone, UI-free service for progressing through experiment
protocols and recording per-step inputs, calculation requests, calculation
results, outputs, progress, completion, and error state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4

from core.experiment_protocols import ExperimentProtocol, get_protocol
from core.redaction import redact_sensitive


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ExperimentStatus(str, Enum):
    """Lifecycle states for an experiment guide session."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class ExperimentGuideError(ValueError):
    """Raised when a session cannot accept a requested state transition."""


MEDICAL_BOUNDARY = (
    "Current-stage SuperMedicine output: not production/clinical medical advice; "
    "requires expert review before any research, regulatory, or clinical use."
)


def _compact_summary(value: Any, *, max_text: int = 500) -> Any:
    """Return a redacted, bounded summary suitable for audit log messages."""

    safe_value = redact_sensitive(value)
    if isinstance(safe_value, dict):
        return {str(key): _compact_summary(item, max_text=max_text) for key, item in safe_value.items()}
    if isinstance(safe_value, list):
        summarized = [_compact_summary(item, max_text=max_text) for item in safe_value[:10]]
        if len(safe_value) > 10:
            summarized.append({"truncated_items": len(safe_value) - 10})
        return summarized
    if isinstance(safe_value, str) and len(safe_value) > max_text:
        return f"{safe_value[:max_text]}...<truncated>"
    return safe_value


def build_experiment_log_event(
    event_type: str,
    session: "ExperimentSession",
    *,
    step_id: str | None = None,
    user_input: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    plugin_request: dict[str, Any] | None = None,
    kernel_result: dict[str, Any] | None = None,
    record: dict[str, Any] | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Build a structured, secret-redacted experiment audit event."""

    next_step = session.current_step
    event: dict[str, Any] = {
        "event_type": event_type,
        "session_id": session.session_id,
        "protocol_id": session.protocol.protocol_id,
        "status": session.status.value if hasattr(session.status, "value") else str(session.status),
        "progress": session.progress,
        "medical_boundary": MEDICAL_BOUNDARY,
    }
    if message:
        event["message"] = message
    if step_id:
        event["step_id"] = step_id
    if user_input is not None:
        event["user_input"] = _compact_summary(user_input)
    if outputs is not None:
        event["outputs"] = _compact_summary(outputs)
    if record is not None:
        event["record"] = _compact_summary(record)
    if plugin_request is not None:
        event["request_id"] = plugin_request.get("request_id")
        event["plugin"] = plugin_request.get("plugin_name")
        event["action"] = plugin_request.get("action")
        event["plugin_request"] = _compact_summary(
            {
                "request_id": plugin_request.get("request_id"),
                "plugin_name": plugin_request.get("plugin_name"),
                "action": plugin_request.get("action"),
                "kind": plugin_request.get("kind"),
                "metadata": plugin_request.get("metadata", {}),
            }
        )
    if kernel_result is not None:
        event["plugin_result_summary"] = _compact_summary(
            {
                "status": kernel_result.get("status"),
                "plugin": kernel_result.get("plugin"),
                "action": kernel_result.get("action"),
                "output": kernel_result.get("output"),
                "error": kernel_result.get("error"),
                "metadata": kernel_result.get("metadata", {}),
            }
        )
        event.setdefault("plugin", kernel_result.get("plugin"))
        event.setdefault("action", kernel_result.get("action"))
    if next_step is None:
        event["completion"] = {"completed": session.is_completed, "completed_at": session.updated_at}
    else:
        event["next_step"] = _compact_summary(
            {
                "step_id": next_step.step_id,
                "title": next_step.title,
                "instructions": next_step.instructions,
            }
        )
    return redact_sensitive(event)


def append_experiment_log_event(
    store: Any,
    event_type: str,
    session: "ExperimentSession",
    **kwargs: Any,
) -> dict[str, Any]:
    """Append one structured experiment event to the session-scoped log report."""

    event = build_experiment_log_event(event_type, session, **kwargs)
    return store.append(
        json.dumps(event, ensure_ascii=False, sort_keys=True),
        session_id=session.session_id,
    )


class KernelExecutor(Protocol):
    """Minimal Kernel execution surface used by the experiment guide."""

    def execute_task(
        self,
        task: str,
        plugin_name: str | None = None,
        action: str | None = None,
        params: dict[str, Any] | None = None,
        agent_id: str = "alpha",
    ) -> dict[str, Any]:
        ...


EXPERIMENT_WB_ACTIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("sample_preparation", "normalization"): (
        "experiment-wb",
        "experiment.wb.normalize_loading",
    ),
    ("blocking_and_antibody", "dilution"): (
        "experiment-wb",
        "experiment.wb.antibody_dilution",
    ),
}


@dataclass
class CalculationResult:
    """A calculation result supplied by a later plugin or external caller."""

    request_id: str
    status: str
    value: Any = None
    unit: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "status": self.status,
            "value": self.value,
            "unit": self.unit,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalculationResult":
        return cls(
            request_id=str(data["request_id"]),
            status=str(data.get("status", "completed")),
            value=data.get("value"),
            unit=data.get("unit"),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class StepRecord:
    """Data recorded for one protocol step."""

    step_id: str
    user_input: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    calculation_results: list[CalculationResult] = field(default_factory=list)
    completed: bool = False
    submitted_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "user_input": dict(self.user_input),
            "outputs": dict(self.outputs),
            "calculation_results": [result.to_dict() for result in self.calculation_results],
            "completed": self.completed,
            "submitted_at": self.submitted_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepRecord":
        return cls(
            step_id=str(data["step_id"]),
            user_input=dict(data.get("user_input", {})),
            outputs=dict(data.get("outputs", {})),
            calculation_results=[
                CalculationResult.from_dict(item)
                for item in data.get("calculation_results", [])
            ],
            completed=bool(data.get("completed", False)),
            submitted_at=data.get("submitted_at"),
        )


@dataclass
class ExperimentSession:
    """A resumable state-machine instance for one protocol run."""

    session_id: str
    protocol: ExperimentProtocol
    current_step_index: int = 0
    status: ExperimentStatus = ExperimentStatus.IN_PROGRESS
    records: dict[str, StepRecord] = field(default_factory=dict)
    error: str | None = None
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        protocol: ExperimentProtocol | str = "wb",
        *,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ExperimentSession":
        selected_protocol = get_protocol(protocol) if isinstance(protocol, str) else protocol
        return cls(
            session_id=session_id or f"experiment-{uuid4().hex}",
            protocol=selected_protocol,
            metadata=dict(metadata or {}),
        )

    @property
    def current_step(self):
        if self.status == ExperimentStatus.COMPLETED:
            return None
        return self.protocol.steps[self.current_step_index]

    @property
    def progress(self) -> dict[str, int]:
        total_steps = len(self.protocol.steps)
        completed_steps = sum(1 for record in self.records.values() if record.completed)
        return {
            "current_step_index": self.current_step_index,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
        }

    @property
    def is_completed(self) -> bool:
        return self.status == ExperimentStatus.COMPLETED

    def submit_step(
        self,
        step_id: str,
        user_input: dict[str, Any] | None = None,
        *,
        outputs: dict[str, Any] | None = None,
        calculation_results: list[CalculationResult | dict[str, Any]] | None = None,
        advance: bool = True,
    ) -> StepRecord:
        """Record data for the current step and optionally advance state."""

        if self.status == ExperimentStatus.COMPLETED:
            self._fail("cannot submit data to a completed experiment")
        if self.status == ExperimentStatus.ERROR:
            raise ExperimentGuideError(self.error or "experiment is in error state")

        current_step = self.current_step
        if current_step is None or step_id != current_step.step_id:
            self._fail(f"expected step {current_step.step_id if current_step else None}, got {step_id}")

        provided_input = dict(user_input or {})
        missing = [
            input_field.name
            for input_field in current_step.input_fields
            if input_field.required and input_field.name not in provided_input
        ]
        if missing:
            self._fail(f"missing required input fields: {', '.join(missing)}")

        normalized_results = [
            result if isinstance(result, CalculationResult) else CalculationResult.from_dict(result)
            for result in calculation_results or []
        ]
        record = StepRecord(
            step_id=step_id,
            user_input=provided_input,
            outputs=dict(outputs or {}),
            calculation_results=normalized_results,
            completed=True,
            submitted_at=_utc_now(),
        )
        self.records[step_id] = record
        self.error = None
        if advance:
            self.advance()
        else:
            self.updated_at = _utc_now()
        return record

    def build_plugin_requests(
        self,
        step_id: str,
        *,
        calculation_params: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Create serializable plugin requests for the current step."""

        if self.status == ExperimentStatus.COMPLETED:
            self._fail("cannot build plugin requests for a completed experiment")
        if self.status == ExperimentStatus.ERROR:
            raise ExperimentGuideError(self.error or "experiment is in error state")

        current_step = self.current_step
        if current_step is None or step_id != current_step.step_id:
            self._fail(f"expected step {current_step.step_id if current_step else None}, got {step_id}")

        params_by_request = calculation_params or {}
        requests: list[dict[str, Any]] = []
        for calculation_request in current_step.calculation_requests:
            plugin_action = EXPERIMENT_WB_ACTIONS.get((current_step.step_id, calculation_request.kind))
            if plugin_action is None:
                continue
            plugin_name, action = plugin_action
            params = dict(calculation_request.parameters)
            params.update(params_by_request.get(calculation_request.request_id, {}))
            requests.append(
                {
                    "request_id": calculation_request.request_id,
                    "kind": calculation_request.kind,
                    "description": calculation_request.description,
                    "plugin_name": plugin_name,
                    "action": action,
                    "params": params,
                    "task": f"experiment calculation {self.session_id} {current_step.step_id} {calculation_request.request_id}",
                    "metadata": {
                        "session_id": self.session_id,
                        "protocol_id": self.protocol.protocol_id,
                        "step_id": current_step.step_id,
                    },
                }
            )
        return requests

    def apply_plugin_result(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
        kernel_result: dict[str, Any],
        *,
        outputs: dict[str, Any] | None = None,
        request_id: str | None = None,
        advance: bool = True,
    ) -> StepRecord:
        """Record a Kernel-routed plugin result for a guide step."""

        status = str(kernel_result.get("status", "plugin_error"))
        calculation = CalculationResult(
            request_id=request_id or str(kernel_result.get("action") or "plugin_result"),
            status="completed" if status == "success" else status,
            value=kernel_result.get("output") if status == "success" else None,
            metadata={
                "kernel_status": status,
                "plugin": kernel_result.get("plugin"),
                "action": kernel_result.get("action"),
                "error": kernel_result.get("error"),
                "metadata": kernel_result.get("metadata", {}),
            },
        )
        if status != "success":
            self._fail(str(kernel_result.get("error") or f"plugin calculation failed: {status}"))
        return self.submit_step(
            step_id,
            user_input,
            outputs=outputs,
            calculation_results=[calculation],
            advance=advance,
        )

    def advance(self) -> None:
        """Move from the current completed step to the next step or finish."""

        if self.status == ExperimentStatus.COMPLETED:
            return
        if self.status == ExperimentStatus.ERROR:
            raise ExperimentGuideError(self.error or "experiment is in error state")
        current_step = self.protocol.steps[self.current_step_index]
        if not self.records.get(current_step.step_id, StepRecord(current_step.step_id)).completed:
            self._fail(f"cannot advance before completing step {current_step.step_id}")
        if self.current_step_index >= len(self.protocol.steps) - 1:
            self.status = ExperimentStatus.COMPLETED
        else:
            self.current_step_index += 1
        self.updated_at = _utc_now()

    def recover(self) -> None:
        """Leave error state and resume from the current step."""

        if self.status == ExperimentStatus.ERROR:
            self.status = ExperimentStatus.IN_PROGRESS
            self.error = None
            self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "protocol": self.protocol.to_dict(),
            "current_step_index": self.current_step_index,
            "status": self.status.value,
            "records": {key: value.to_dict() for key, value in self.records.items()},
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
            "progress": self.progress,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentSession":
        protocol = ExperimentProtocol.from_dict(data["protocol"])
        session = cls(
            session_id=str(data["session_id"]),
            protocol=protocol,
            current_step_index=int(data.get("current_step_index", 0)),
            status=ExperimentStatus(data.get("status", ExperimentStatus.IN_PROGRESS.value)),
            records={
                str(key): StepRecord.from_dict(value)
                for key, value in data.get("records", {}).items()
            },
            error=data.get("error"),
            created_at=str(data.get("created_at", _utc_now())),
            updated_at=str(data.get("updated_at", _utc_now())),
            metadata=dict(data.get("metadata", {})),
        )
        if not 0 <= session.current_step_index < len(session.protocol.steps):
            raise ExperimentGuideError("saved experiment session has invalid step index")
        return session

    def _fail(self, message: str) -> None:
        self.status = ExperimentStatus.ERROR
        self.error = message
        self.updated_at = _utc_now()
        raise ExperimentGuideError(message)


class ExperimentGuide:
    """Small facade for creating and restoring experiment sessions."""

    def create_session(
        self,
        protocol_id: str = "wb",
        *,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExperimentSession:
        return ExperimentSession.create(
            protocol_id,
            session_id=session_id,
            metadata=metadata,
        )

    def restore_session(self, data: dict[str, Any]) -> ExperimentSession:
        return ExperimentSession.from_dict(data)

    def execute_step_calculation(
        self,
        kernel: KernelExecutor,
        session: ExperimentSession,
        step_id: str,
        user_input: dict[str, Any] | None = None,
        *,
        calculation_params: dict[str, dict[str, Any]] | None = None,
        outputs: dict[str, Any] | None = None,
        agent_id: str = "alpha",
        advance: bool = True,
    ) -> dict[str, Any]:
        """Execute an experiment calculation via Kernel's permission path."""

        plugin_requests = session.build_plugin_requests(
            step_id,
            calculation_params=calculation_params,
        )
        if not plugin_requests:
            record = session.submit_step(
                step_id,
                user_input,
                outputs=outputs,
                calculation_results=[],
                advance=advance,
            )
            return self._guidance_response(
                session,
                record=record,
                plugin_request=None,
                kernel_result=None,
            )

        plugin_request = plugin_requests[0]
        kernel_result = kernel.execute_task(
            plugin_request["task"],
            plugin_name=plugin_request["plugin_name"],
            action=plugin_request["action"],
            params=plugin_request["params"],
            agent_id=agent_id,
        )
        if kernel_result.get("status") != "success":
            return self._guidance_response(
                session,
                record=None,
                plugin_request=plugin_request,
                kernel_result=kernel_result,
            )

        record = session.apply_plugin_result(
            step_id,
            user_input,
            kernel_result,
            outputs=outputs,
            request_id=str(plugin_request["request_id"]),
            advance=advance,
        )
        return self._guidance_response(
            session,
            record=record,
            plugin_request=plugin_request,
            kernel_result=kernel_result,
        )

    def _guidance_response(
        self,
        session: ExperimentSession,
        *,
        record: StepRecord | None,
        plugin_request: dict[str, Any] | None,
        kernel_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        next_step = session.current_step
        status = kernel_result.get("status") if kernel_result else "success"
        return {
            "status": status,
            "session": session.to_dict(),
            "record": record.to_dict() if record else None,
            "plugin_request": plugin_request,
            "kernel_result": kernel_result,
            "next_step": next_step.to_dict() if next_step else None,
            "progress": session.progress,
            "medical_boundary": MEDICAL_BOUNDARY,
        }

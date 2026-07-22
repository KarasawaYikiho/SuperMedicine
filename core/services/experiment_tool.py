"""Experiment and workspace-tool application service."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any, Callable, Sequence, cast

from core.config_center import ConfigCenter
from core.experiment_guide import (
    CalculationResult,
    ExperimentGuide,
    ExperimentGuideError,
    ExperimentSession,
    MEDICAL_BOUNDARY,
    append_experiment_log_event,
)
from core.experiment_protocols import (
    ExperimentProtocolAuthoringError,
    ExperimentProtocolConfigError,
    build_experiment_llm_context,
    create_experiment_config_from_instruction,
    list_protocols,
    save_experiment_config,
)
from core.kernel import Kernel
from core.log_report import LogReportStore
from core.redaction import redact_sensitive
from core.serialization import json_ready
from core.workspace import InvalidWorkspaceId, WorkspaceError, WorkspaceNotFoundError
from core.workspace_tool_models import (
    InvalidToolId,
    InvalidToolLanguage,
    ToolCandidateError,
    ToolManifestError,
    ToolNotFoundError,
    WorkspaceToolError,
)
from core.workspace_tools import WorkspaceToolService
from permission.policy import ensure_default_policy
from plugins.tools.experiment_wb import main as wb_plugin

from . import result as _result
from .result import ServiceResult


class ExperimentToolService:
    """Own experiment and workspace-tool use cases used by all interfaces."""

    require_data = staticmethod(
        partial(
            _result._require_data,
            "Experiment/tool service failed",
            {"workspace_not_found": WorkspaceNotFoundError},
        )
    )
    _meta = staticmethod(partial(_result._service_meta, "experiment_tool"))

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.tools = WorkspaceToolService(project_root)
        self.project_root = self.tools.project_root

    def start_experiment(
        self,
        protocol: str,
        *,
        session_id: str | None = None,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            session = ExperimentGuide().create_session(protocol, session_id=session_id)
            self._select_protocol(session.protocol.protocol_id)
            path = self._session_path(session.session_id)
            self._save_session(path, session.to_dict())
            append_experiment_log_event(
                LogReportStore(self.project_root),
                "experiment_started",
                session,
                message="experiment guide session started",
            )
            return self._experiment_payload(session, path)

        return self._experiment_call("start_experiment", request_id, action)

    def list_experiments(
        self, *, request_id: str | None = None
    ) -> ServiceResult[list[dict[str, Any]]]:
        return self._experiment_call(
            "list_experiments",
            request_id,
            lambda: [
                {
                    "protocol_id": protocol.protocol_id,
                    "title": protocol.title,
                    "description": protocol.description,
                    "version": protocol.version,
                    "metadata": protocol.metadata,
                    "step_count": len(protocol.steps),
                }
                for protocol in list_protocols()
            ],
        )

    def experiment_context(
        self,
        protocol: str | None = None,
        *,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            result = build_experiment_llm_context(protocol)
            selected = result.get("selected_protocol")
            if protocol and isinstance(selected, dict) and selected.get("protocol_id"):
                protocol_id = str(selected["protocol_id"])
                self._select_protocol(protocol_id)
                result["runtime_sync"] = {
                    "selected_experiment_protocol": protocol_id,
                    "message": "实验配置选择已同步到统一配置；后续 LLM 上下文会读取该协议。",
                }
            return result

        return self._experiment_call("experiment_context", request_id, action)

    def add_experiment_config(
        self,
        *,
        instruction: str | None = None,
        config: dict[str, Any] | None = None,
        filename: str | None = None,
        overwrite: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            if bool(instruction and instruction.strip()) == (config is not None):
                raise ValueError("provide exactly one of instruction or config")
            result = (
                save_experiment_config(
                    config or {}, filename=filename, overwrite=overwrite
                )
                if config is not None
                else create_experiment_config_from_instruction(
                    instruction or "", filename=filename, overwrite=overwrite
                )
            )
            protocol = result.get("protocol")
            if isinstance(protocol, dict) and protocol.get("protocol_id"):
                protocol_id = str(protocol["protocol_id"])
                self._select_protocol(protocol_id)
                result["runtime_sync"] = {
                    "selected_experiment_protocol": protocol_id,
                    "message": "新增实验配置已同步为后续 LLM 上下文的当前实验。",
                }
            return result

        return self._experiment_call("add_experiment_config", request_id, action)

    def show_experiment(
        self, session_file: str | Path, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        path = Path(session_file)
        return self._experiment_call(
            "show_experiment",
            request_id,
            lambda: self._experiment_payload(
                ExperimentGuide().restore_session(self._load_session(path)), path
            ),
            session_file=str(path),
        )

    def submit_experiment(
        self,
        session_file: str | Path,
        step_id: str,
        input_data: str | dict[str, Any],
        *,
        calculate: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        path = Path(session_file)
        return self._experiment_call(
            "submit_experiment",
            request_id,
            lambda: self._submit_experiment(path, step_id, input_data, calculate),
            session_file=str(path),
            step_id=step_id,
        )

    def experiment_protocols(self) -> ServiceResult[list[Any]]:
        return self._experiment_call(
            "experiment_protocols", None, lambda: ExperimentGuide().list_protocols()
        )

    def create_live_session(
        self,
        protocol: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceResult[ExperimentSession]:
        return self._experiment_call(
            "create_live_session",
            None,
            lambda: ExperimentGuide().create_session(protocol, metadata=metadata),
        )

    def select_experiment_protocol(
        self, protocol_id: str
    ) -> ServiceResult[dict[str, str]]:
        def action() -> dict[str, str]:
            self._select_protocol(protocol_id)
            return {"selected_experiment_protocol": protocol_id}

        return self._experiment_call("select_experiment_protocol", None, action)

    def selected_experiment_protocol(self) -> ServiceResult[str]:
        return self._experiment_call(
            "selected_experiment_protocol",
            None,
            lambda: ConfigCenter(
                self.project_root / ".supermedicine" / "config.yaml"
            ).get_selected_experiment_protocol(),
        )

    def calculate_live_step(
        self, session: ExperimentSession, user_input: dict[str, Any]
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            step = session.current_step
            if step is None:
                raise ExperimentGuideError("experiment is already completed")
            requests = session.build_plugin_requests(step.step_id)
            if not requests:
                return {"status": "no_calculation"}
            ensure_default_policy(self.project_root)
            kernel = Kernel(
                config_path=self.project_root / ".supermedicine" / "config.yaml",
                policies_dir=self.project_root / ".supermedicine" / "policies",
            )
            params = self._calculation_params(requests[0], user_input)
            calculation = ExperimentGuide().execute_step_calculation(
                kernel,
                session,
                step.step_id,
                user_input=user_input,
                calculation_params=params,
                advance=False,
            )
            append_experiment_log_event(
                LogReportStore(self.project_root),
                "plugin_result",
                session,
                step_id=step.step_id,
                user_input=user_input,
                plugin_request=calculation.get("plugin_request") or requests[0],
                kernel_result=calculation.get("kernel_result") or {},
            )
            return calculation

        return self._experiment_call("calculate_live_step", None, action)

    def submit_live_step(
        self,
        session: ExperimentSession,
        user_input: dict[str, Any],
        outputs: dict[str, Any],
    ) -> ServiceResult[dict[str, Any]]:
        step = session.current_step
        if step is None:
            return ServiceResult.failure(
                "experiment_error",
                "experiment is already completed",
                meta=self._meta("submit_live_step"),
            )
        try:
            record = session.submit_step(
                step.step_id, user_input, outputs=outputs, advance=True
            )
            self._log_experiment_submission(
                session, step.step_id, user_input, outputs, record.to_dict()
            )
            return ServiceResult.success(
                record.to_dict(), meta=self._meta("submit_live_step")
            )
        except Exception as exc:
            session.recover()
            return self._experiment_failure(exc, "submit_live_step", None, {})

    def append_live_event(
        self, event_type: str, session: ExperimentSession, **kwargs: Any
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            return append_experiment_log_event(
                LogReportStore(self.project_root), event_type, session, **kwargs
            )

        return self._experiment_call("append_live_event", None, action)

    def save_live_log(
        self, session: ExperimentSession, last_calculation: Any
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            payload = redact_sensitive(
                {
                    "session_id": session.session_id,
                    "event": "experiment_log_saved",
                    "session": {
                        "protocol_id": session.protocol.protocol_id,
                        "status": session.status.value,
                        "progress": session.progress,
                        "current_step": session.current_step.step_id
                        if session.current_step
                        else None,
                    },
                    "last_calculation": self._compact_log(last_calculation),
                    "medical_boundary": MEDICAL_BOUNDARY,
                }
            )
            return LogReportStore(self.project_root).append(
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                session_id=session.session_id,
            )

        return self._experiment_call("save_live_log", None, action)

    def initialize_tools(
        self, workspace_id: str, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, Any]]:
        return self._tool_call(
            "initialize_tools",
            request_id,
            lambda: self.tools.initialize_tools(workspace_id),
            workspace_id=workspace_id,
        )

    def list_tools(
        self,
        workspace_id: str,
        *,
        language: str | None = None,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, list[dict[str, Any]]]]:
        return self._tool_call(
            "list_tools",
            request_id,
            lambda: self.tools.list_tools(workspace_id, language=language),
            workspace_id=workspace_id,
        )

    def scan_tools(
        self, language: str | None = None, *, request_id: str | None = None
    ) -> ServiceResult[dict[str, list[dict[str, Any]]]]:
        return self._tool_call(
            "scan_tools",
            request_id,
            lambda: self.tools.scan_import_candidates(language),
        )

    def import_tools(
        self,
        workspace_id: str,
        selections: Sequence[str | int] | None,
        *,
        language: str | None = None,
        overwrite: bool = False,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        def action() -> dict[str, Any]:
            if not selections:
                return {
                    "status": "select_required",
                    "message": "Select tools from this scanned list with --select; no tool ID knowledge is required.",
                    "candidates": self.tools.scan_import_candidates(language),
                }
            result = self.tools.import_scanned_tools(
                workspace_id,
                selections,
                language=language,
                overwrite=overwrite,
            )
            imported_raw = result.get("imported")
            imported = (
                [cast(dict[str, Any], item) for item in imported_raw if isinstance(item, dict)]
                if isinstance(imported_raw, list)
                else []
            )
            if imported:
                self._record_tool_import(workspace_id, imported)
            return result

        return self._tool_call(
            "import_tools",
            request_id,
            action,
            workspace_id=workspace_id,
        )

    def show_tool(
        self,
        workspace_id: str,
        language: str,
        tool_id: str,
        *,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._tool_call(
            "show_tool",
            request_id,
            lambda: self.tools.show_tool(workspace_id, language, tool_id),
            workspace_id=workspace_id,
            tool_id=tool_id,
        )

    def prepare_tool(
        self,
        workspace_id: str,
        language: str,
        tool_id: str,
        *,
        dry_run: bool = False,
        input_path: str | None = None,
        output_path: str | None = None,
        request_id: str | None = None,
    ) -> ServiceResult[dict[str, Any]]:
        return self._tool_call(
            "prepare_tool",
            request_id,
            lambda: self.tools.prepare_invocation(
                workspace_id,
                language,
                tool_id,
                dry_run=dry_run,
                input_path=input_path,
                output_path=output_path,
            ).to_dict(),
            workspace_id=workspace_id,
            tool_id=tool_id,
        )

    def _submit_experiment(
        self,
        path: Path,
        step_id: str,
        input_data: str | dict[str, Any],
        calculate: bool,
    ) -> dict[str, Any]:
        guide = ExperimentGuide()
        session = guide.restore_session(self._load_session(path))
        payload = self.parse_input(input_data)
        user_input = self._mapping(payload.get("user_input", payload), "user_input")
        outputs = self._mapping(payload.get("outputs", {}), "outputs")
        params = self._mapping(
            payload.get("calculation_params", {}), "calculation_params"
        )
        calculation_results: list[CalculationResult | dict[str, Any]] = []
        plugin_request = None
        kernel_result = None
        if calculate:
            plugin_request, kernel_result = self._calculate_experiment(
                session, step_id, params
            )
            calculation_results.append(
                {
                    "request_id": str(plugin_request["request_id"]),
                    "status": "completed",
                    "value": kernel_result.get("output"),
                    "metadata": {
                        "plugin": kernel_result.get("plugin"),
                        "action": kernel_result.get("action"),
                        "metadata": kernel_result.get("metadata", {}),
                    },
                }
            )
        record = session.submit_step(
            step_id,
            user_input,
            outputs=outputs,
            calculation_results=calculation_results,
        )
        self._save_session(path, session.to_dict())
        self._log_experiment_submission(
            session, step_id, user_input, outputs, record.to_dict()
        )
        return self._experiment_payload(
            session,
            path,
            record=record.to_dict(),
            plugin_request=plugin_request,
            kernel_result=kernel_result,
        )

    def _calculate_experiment(
        self,
        session: ExperimentSession,
        step_id: str,
        calculation_params: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        requests = session.build_plugin_requests(
            step_id, calculation_params=calculation_params
        )
        if not requests:
            if session.protocol.protocol_id == "western_blot_basic":
                raise ValueError(
                    f"step {step_id} has no supported WB calculation request"
                )
            raise ValueError(
                f"step {step_id} has no supported experiment calculation request"
            )
        request = requests[0]
        if request.get("plugin_name") != "experiment-wb":
            raise ValueError(
                "CLI --calculate currently supports experiment-wb plugin requests only; "
                f"got {request.get('plugin_name')}"
            )
        result = wb_plugin.execute(
            request["action"], request["params"], request["metadata"]
        )
        if result.get("status") != "success":
            raise ValueError(str(result.get("error") or "WB calculation failed"))
        append_experiment_log_event(
            LogReportStore(self.project_root),
            "plugin_result",
            session,
            step_id=step_id,
            plugin_request=request,
            kernel_result=result,
        )
        return request, result

    def _log_experiment_submission(
        self,
        session: ExperimentSession,
        step_id: str,
        user_input: dict[str, Any],
        outputs: dict[str, Any],
        record: dict[str, Any],
    ) -> None:
        store = LogReportStore(self.project_root)
        append_experiment_log_event(
            store,
            "step_input_submitted",
            session,
            step_id=step_id,
            user_input=user_input,
            outputs=outputs,
            record=record,
        )
        append_experiment_log_event(
            store,
            "experiment_completed" if session.is_completed else "step_guidance",
            session,
            step_id=step_id,
            record=record,
        )

    @staticmethod
    def _calculation_params(
        request: dict[str, Any], user_input: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        request_id = str(request.get("request_id") or "")
        params = user_input.get("calculation_params")
        if isinstance(params, dict):
            nested = params.get(request_id)
            return {request_id: nested if isinstance(nested, dict) else params}
        if request.get("action") == "experiment.wb.normalize_loading":
            return {
                request_id: {
                    "samples": [
                        {
                            "name": str(user_input.get("sample_id") or "sample-1"),
                            "concentration": user_input.get(
                                "concentration",
                                user_input.get("sample_concentration", 1.0),
                            ),
                        }
                    ],
                    "target_protein_amount": user_input.get(
                        "target_protein_amount", 10.0
                    ),
                    "final_well_volume": user_input.get("final_well_volume", 20.0),
                }
            }
        if request.get("action") == "experiment.wb.antibody_dilution":
            return {
                request_id: {
                    "total_volume": user_input.get("total_volume", 1000.0),
                    "dilution_ratio": user_input.get("dilution_ratio", "1:1000"),
                }
            }
        return {}

    @staticmethod
    def _compact_log(value: Any, max_text: int = 1000) -> Any:
        redacted = redact_sensitive(value)
        text = json.dumps(redacted, ensure_ascii=False, sort_keys=True, default=str)
        if len(text) <= max_text:
            return redacted
        return {"truncated": True, "preview": text[:max_text]}

    def _experiment_call(
        self,
        operation: str,
        request_id: str | None,
        action: Callable[[], Any],
        **details: str,
    ) -> ServiceResult[Any]:
        try:
            return ServiceResult.success(
                action(), request_id=request_id, meta=self._meta(operation)
            )
        except (
            FileNotFoundError,
            ExperimentGuideError,
            ExperimentProtocolConfigError,
            ExperimentProtocolAuthoringError,
            ValueError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            return self._experiment_failure(exc, operation, request_id, details)
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                _result._safe_internal_message(exc, "Experiment/tool service failed"),
                request_id=request_id,
                details=details,
                meta=self._meta(operation),
            )

    def _experiment_failure(
        self,
        exc: Exception,
        operation: str,
        request_id: str | None,
        details: dict[str, str],
    ) -> ServiceResult[Any]:
        code = (
            "experiment_session_not_found"
            if isinstance(exc, FileNotFoundError)
            else "experiment_error"
        )
        return ServiceResult.failure(
            code,
            str(exc),
            request_id=request_id,
            details=details,
            meta=self._meta(operation),
        )

    def _select_protocol(self, protocol_id: str) -> None:
        ConfigCenter(
            self.project_root / ".supermedicine" / "config.yaml"
        ).set_selected_experiment_protocol(protocol_id, save=True)

    def _session_path(self, session_id: str) -> Path:
        return self.project_root / ".supermedicine" / "experiments" / f"{session_id}.json"

    @staticmethod
    def _load_session(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("experiment session file must contain a JSON object")
        return data

    @staticmethod
    def _save_session(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                json_ready(redact_sensitive(data)), ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )

    @staticmethod
    def parse_input(value: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"--input-json must be valid JSON: {exc.msg}"
            ) from exc
        if not isinstance(parsed, dict):
            raise ValueError("--input-json must be a JSON object")
        return parsed

    @staticmethod
    def _mapping(value: object, name: str) -> dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError(f"{name} must be a JSON object")
        return value

    @staticmethod
    def _experiment_payload(
        session: ExperimentSession,
        path: Path,
        *,
        record: dict[str, Any] | None = None,
        plugin_request: dict[str, Any] | None = None,
        kernel_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        current = session.current_step
        return {
            "status": session.status.value,
            "session_file": str(path),
            "session": session.to_dict(),
            "current_step": current.to_dict() if current else None,
            "record": record,
            "plugin_request": plugin_request,
            "kernel_result": kernel_result,
            "progress": session.progress,
            "medical_boundary": MEDICAL_BOUNDARY,
        }

    def _record_tool_import(
        self, workspace_id: str, imported: list[dict[str, Any]]
    ) -> None:
        config = ConfigCenter(self.project_root / ".supermedicine" / "config.yaml")
        config.set_runtime_state_value("last_workspace_id", workspace_id)
        config.record_tool_import_state(
            workspace_id=workspace_id, imported=imported, save=True
        )

    def _tool_call(
        self,
        operation: str,
        request_id: str | None,
        action: Callable[[], Any],
        **details: str,
    ) -> ServiceResult[Any]:
        try:
            return ServiceResult.success(
                action(), request_id=request_id, meta=self._meta(operation)
            )
        except (WorkspaceToolError, WorkspaceError, OSError) as exc:
            return ServiceResult.failure(
                self._tool_error_code(exc),
                str(exc),
                request_id=request_id,
                details=details,
                meta=self._meta(operation),
            )
        except Exception as exc:
            return ServiceResult.failure(
                "internal_error",
                _result._safe_internal_message(exc, "Experiment/tool service failed"),
                request_id=request_id,
                details=details,
                meta=self._meta(operation),
            )

    @staticmethod
    def _tool_error_code(exc: Exception) -> str:
        if isinstance(exc, InvalidToolLanguage):
            return "invalid_tool_language"
        if isinstance(exc, InvalidToolId):
            return "invalid_tool_id"
        if isinstance(exc, ToolNotFoundError):
            return "tool_not_found"
        if isinstance(exc, ToolManifestError):
            return "invalid_tool_manifest"
        if isinstance(exc, ToolCandidateError):
            return "invalid_tool_candidate"
        if isinstance(exc, WorkspaceNotFoundError):
            return "workspace_not_found"
        if isinstance(exc, InvalidWorkspaceId):
            return "invalid_workspace_id"
        return "tool_error"

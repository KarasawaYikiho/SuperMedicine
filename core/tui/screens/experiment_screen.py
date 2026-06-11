"""Experiment guide view for SuperMedicine TUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.config_center import ConfigCenter
from core.experiment_guide import (
    ExperimentGuide,
    ExperimentGuideError,
    ExperimentSession,
    MEDICAL_BOUNDARY,
    append_experiment_log_event,
)
from core.kernel import Kernel
from core.log_report import LogReportStore
from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t
from permission.policy import ensure_default_policy


class ExperimentGuideView(Vertical):
    """Minimal standalone experiment guide page."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._guide = ExperimentGuide()
        self._protocols = self._guide.list_protocols()
        if not self._protocols:
            raise ValueError("no experiment protocols are configured")
        self._config = ConfigCenter(
            self._project_root / ".supermedicine" / "config.yaml"
        )
        selected_protocol = self._config.get_selected_experiment_protocol() or "wb"
        self._sessions_by_protocol: dict[str, ExperimentSession] = {}
        try:
            self._session: ExperimentSession = self._guide.create_session(
                selected_protocol, metadata={"source": "tui"}
            )
        except Exception:
            self._session = self._guide.create_session(
                self._protocols[0].protocol_id, metadata={"source": "tui"}
            )
        self._sync_selected_protocol()
        self._sessions_by_protocol[self._session.protocol.protocol_id] = self._session
        self._last_calculation: dict[str, Any] | None = None
        self._started_logged = False

    def compose(self) -> ComposeResult:
        yield Static(t("experiment_title"), classes="section-title")
        yield Static(t("experiment_boundary"), id="experiment-boundary")
        yield Static(
            t("experiment_action_hint"), id="experiment-action-hint", classes="hint"
        )
        protocol_table: DataTable = DataTable(id="experiment-protocol-table", cursor_type="row")
        protocol_table.styles.max_height = 12
        yield protocol_table
        yield Button(
            "切换到下一个实验配置", id="experiment-switch", classes="btn btn-secondary"
        )
        yield Static("", id="experiment-session")
        yield Static("", id="experiment-step")
        yield Static("", id="experiment-instructions")
        input_table: DataTable = DataTable(id="experiment-input-table", cursor_type="row")
        input_table.styles.max_height = 8
        yield input_table
        data_input = TextArea.code_editor("", language="json", id="experiment-data-input")
        data_input.styles.max_height = 10
        yield data_input
        yield Input(
            placeholder=t("experiment_output_data"), id="experiment-output-input"
        )
        with Horizontal(classes="form-row"):
            yield Button(
                t("experiment_calculate_step"),
                id="experiment-calculate",
                classes="btn btn-secondary",
            )
            yield Button(
                t("experiment_submit_step"),
                id="experiment-submit",
                classes="btn btn-primary",
            )
            yield Button(
                t("experiment_save_log"),
                id="experiment-save-log",
                classes="btn btn-secondary",
            )
        yield Static("", id="experiment-reagent-result")
        yield Static("", id="experiment-status")

    def on_mount(self) -> None:
        self.refresh_session_view(t("experiment_session_created"))

    def on_show(self) -> None:
        if not self._started_logged:
            self._append_log_event(
                "experiment_started", message="experiment guide session started"
            )
            self._started_logged = True

    def refresh_session_view(self, status_message: str | None = None) -> None:
        self._refresh_protocol_table()
        self.query_one("#experiment-session", Static).update(self._session_summary())
        current_step = self._session.current_step
        table = self.query_one("#experiment-input-table", DataTable)
        table.clear(columns=True)
        table.add_columns("字段", "标签", "必填", "说明")
        if current_step is None:
            self.query_one("#experiment-step", Static).update(t("experiment_completed"))
            self.query_one("#experiment-instructions", Static).update(MEDICAL_BOUNDARY)
        else:
            self.query_one("#experiment-step", Static).update(
                f"{t('experiment_current_step')}：{current_step.title} ({current_step.step_id})"
            )
            self.query_one("#experiment-instructions", Static).update(
                f"{t('experiment_step_instructions')}：{current_step.instructions}"
            )
            for field in current_step.input_fields:
                table.add_row(
                    field.name,
                    field.label,
                    t("yes") if field.required else t("no"),
                    field.help_text,
                )
        if status_message:
            self._set_status(status_message)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "experiment-calculate":
            self._calculate_current_step()
        elif event.button.id == "experiment-submit":
            self._submit_current_step()
        elif event.button.id == "experiment-save-log":
            self._save_log()
        elif event.button.id == "experiment-switch":
            self._switch_to_next_protocol()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle double-click or Enter on a table row to paste field name."""
        if event.data_table.id == "experiment-input-table":
            self._paste_field_name(event.row_key)

    def _paste_field_name(self, row_key: object) -> None:
        """Append field_name= to the data input TextArea."""
        table = self.query_one("#experiment-input-table", DataTable)
        try:
            row = table.get_row_at(int(str(row_key)))
        except (ValueError, IndexError):
            return
        field_name = str(row[0]) if row else ""
        if not field_name:
            return
        textarea = self.query_one("#experiment-data-input", TextArea)
        current = textarea.text
        if current and not current.endswith("\n"):
            current += "\n"
        textarea.load_text(current + field_name + "=")

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "experiment-output-input":
            self._submit_current_step()

    def _refresh_protocol_table(self) -> None:
        table = self.query_one("#experiment-protocol-table", DataTable)
        table.clear(columns=True)
        table.add_columns("当前", "实验 ID", "实验名称", "步骤数")
        current_protocol_id = self._session.protocol.protocol_id
        for protocol in self._protocols:
            table.add_row(
                "*" if protocol.protocol_id == current_protocol_id else "",
                protocol.protocol_id,
                protocol.title,
                str(len(protocol.steps)),
                key=protocol.protocol_id,
            )

    def _switch_to_next_protocol(self) -> None:
        current_protocol_id = self._session.protocol.protocol_id
        protocol_ids = [protocol.protocol_id for protocol in self._protocols]
        current_index = protocol_ids.index(current_protocol_id)
        next_protocol = self._protocols[(current_index + 1) % len(self._protocols)]
        next_session = self._sessions_by_protocol.get(next_protocol.protocol_id)
        if next_session is None:
            next_session = self._guide.create_session(
                next_protocol.protocol_id,
                metadata={"source": "tui"},
            )
            self._sessions_by_protocol[next_protocol.protocol_id] = next_session
            self._session = next_session
            self._append_log_event(
                "experiment_started",
                message="experiment guide session started after protocol switch",
            )
        else:
            self._session = next_session
        self._last_calculation = None
        self.query_one("#experiment-data-input", TextArea).load_text("")
        self.query_one("#experiment-output-input", Input).value = ""
        self.query_one("#experiment-reagent-result", Static).update("")
        self.refresh_session_view(f"已切换实验配置：{next_protocol.title}")
        self._sync_selected_protocol()

    def _sync_selected_protocol(self) -> None:
        """Persist selected experiment protocol so LLM context follows TUI state."""

        try:
            self._config.set_selected_experiment_protocol(
                self._session.protocol.protocol_id,
                save=True,
            )
        except Exception as exc:
            try:
                self._set_status(f"实验配置同步失败：{redact_sensitive(str(exc))}")
            except Exception:
                pass

    def _calculate_current_step(self) -> None:
        current_step = self._session.current_step
        if current_step is None:
            self._set_status(t("experiment_completed"))
            return
        try:
            user_input = self._parse_user_data()
            requests = self._session.build_plugin_requests(current_step.step_id)
            if not requests:
                self._last_calculation = None
                self.query_one("#experiment-reagent-result", Static).update(
                    t("experiment_no_calculation")
                )
                self._set_status(t("experiment_no_calculation"))
                return
            ensure_default_policy(self._project_root)
            kernel = Kernel(
                config_path=self._project_root / ".supermedicine" / "config.yaml",
                policies_dir=self._project_root / ".supermedicine" / "policies",
            )
            calculation_params = self._calculation_params_for_request(
                requests[0], user_input
            )
            rendered_request = dict(requests[0])
            rendered_request["params"] = {
                **dict(rendered_request.get("params", {})),
                **calculation_params.get(
                    str(rendered_request.get("request_id") or ""), {}
                ),
            }
            calculation = self._guide.execute_step_calculation(
                kernel,
                self._session,
                current_step.step_id,
                user_input=user_input,
                calculation_params=calculation_params,
                advance=False,
            )
            self._last_calculation = calculation
            kernel_result = calculation.get("kernel_result") or {}
            self._append_log_event(
                "plugin_result",
                step_id=current_step.step_id,
                user_input=user_input,
                plugin_request=calculation.get("plugin_request") or rendered_request,
                kernel_result=kernel_result,
            )
            if calculation.get("status") != "success":
                self.query_one("#experiment-reagent-result", Static).update(
                    f"{t('error')}：\n{json.dumps(redact_sensitive(calculation), ensure_ascii=False, indent=2)}"
                )
                self._set_status(
                    f"{t('error')}: {redact_sensitive(kernel_result.get('error') or calculation.get('status'))}"
                )
                return
            self.query_one("#experiment-reagent-result", Static).update(
                f"{t('experiment_reagent_result')}：\n{json.dumps(redact_sensitive(self._last_calculation), ensure_ascii=False, indent=2)}"
            )
            self._set_status(t("experiment_reagent_result"))
        except Exception as exc:
            self._set_error(exc)

    def _submit_current_step(self) -> None:
        current_step = self._session.current_step
        if current_step is None:
            self._set_status(t("experiment_completed"))
            return
        try:
            user_input = self._parse_user_data()
            outputs = self._parse_outputs()
            record = self._session.submit_step(
                current_step.step_id, user_input, outputs=outputs, advance=True
            )
            self._append_log_event(
                "step_input_submitted",
                step_id=current_step.step_id,
                user_input=user_input,
                outputs=outputs,
                record=record.to_dict(),
            )
            self._append_log_event(
                "experiment_completed"
                if self._session.is_completed
                else "step_guidance",
                step_id=current_step.step_id,
                record=record.to_dict(),
            )
            self.refresh_session_view(
                t("experiment_completed")
                if self._session.is_completed
                else t("experiment_step_saved")
            )
        except ExperimentGuideError as exc:
            self._session.recover()
            self._set_error(exc)
        except Exception as exc:
            self._set_error(exc)

    def _append_log_event(self, event_type: str, **kwargs: Any) -> None:
        append_experiment_log_event(
            LogReportStore(self._project_root),
            event_type,
            self._session,
            **kwargs,
        )

    def _save_log(self) -> None:
        payload = redact_sensitive(
            {
                "session_id": self._session.session_id,
                "event": "experiment_log_saved",
                "session": {
                    "protocol_id": self._session.protocol.protocol_id,
                    "status": self._session.status.value,
                    "progress": self._session.progress,
                    "current_step": self._session.current_step.step_id
                    if self._session.current_step
                    else None,
                },
                "last_calculation": self._compact_log_value(self._last_calculation),
                "medical_boundary": MEDICAL_BOUNDARY,
            }
        )
        try:
            result = LogReportStore(self._project_root).append(
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                session_id=self._session.session_id,
            )
            self._set_status(f"{t('experiment_log_saved')}: {result.get('file')}")
        except Exception as exc:
            self._set_error(exc)

    def _compact_log_value(self, value: Any, *, max_text: int = 1000) -> Any:
        redacted = redact_sensitive(value)
        text = json.dumps(redacted, ensure_ascii=False, sort_keys=True, default=str)
        if len(text) <= max_text:
            return redacted
        return {"truncated": True, "preview": text[:max_text]}

    def _parse_user_data(self) -> dict[str, Any]:
        raw = self.query_one("#experiment-data-input", TextArea).text.strip()
        data = self._parse_mapping(raw)
        current_step = self._session.current_step
        if current_step is not None:
            missing = [
                field.label
                for field in current_step.input_fields
                if field.required and field.name not in data
            ]
            if missing:
                raise ValueError(
                    f"{t('experiment_missing_required')}: {', '.join(missing)}"
                )
        return data

    def _parse_outputs(self) -> dict[str, Any]:
        raw = self.query_one("#experiment-output-input", Input).value.strip()
        if not raw:
            return {}
        return {"note": raw}

    def _calculation_params_for_request(
        self, request: dict[str, Any], user_input: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        request_id = str(request.get("request_id") or "")
        params = user_input.get("calculation_params")
        if isinstance(params, dict):
            nested = params.get(request_id)
            if isinstance(nested, dict):
                return {request_id: nested}
            return {request_id: params}
        if request.get("action") == "experiment.wb.normalize_loading":
            sample_name = str(user_input.get("sample_id") or "sample-1")
            raw_concentration = user_input.get(
                "concentration", user_input.get("sample_concentration", 1.0)
            )
            raw_target = user_input.get("target_protein_amount", 10.0)
            raw_final = user_input.get("final_well_volume", 20.0)
            return {
                request_id: {
                    "samples": [
                        {"name": sample_name, "concentration": raw_concentration}
                    ],
                    "target_protein_amount": raw_target,
                    "final_well_volume": raw_final,
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

    def _parse_mapping(self, raw: str) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
            for line in raw.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped and ":" not in stripped:
                    continue  # skip unparseable lines silently
                if "=" in stripped:
                    key, value = stripped.split("=", 1)
                else:
                    key, value = stripped.split(":", 1)
                parsed[key.strip()] = value.strip()
        if not isinstance(parsed, dict):
            raise ValueError(t("experiment_parse_error"))
        return parsed

    def _session_summary(self) -> str:
        progress = self._session.progress
        return (
            f"{t('experiment_session')}：{self._session.session_id} · "
            f"{t('experiment_protocol')}：{self._session.protocol.title} · "
            f"{progress['completed_steps']}/{progress['total_steps']}"
        )

    def _set_status(self, message: str) -> None:
        status = self.query_one("#experiment-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        message = (
            f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}"
        )
        self._set_status(message)
        self.app.notify(message, severity="error")


ExperimentScreen = ExperimentGuideView

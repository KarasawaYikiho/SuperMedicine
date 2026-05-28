"""Experience management view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


class ExperienceView(Vertical):
    """View for managing experience records."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("experience_title"), classes="section-title")
        yield Select(
            [],
            prompt=t("paper_select_workspace"),
            id="exp-workspace-select",
        )
        yield DataTable(id="exp-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Input(placeholder=t("experience_title_label"), id="exp-title-input")
            yield Input(placeholder=t("experience_summary_label"), id="exp-summary-input")
        with Horizontal(classes="form-row"):
            yield Input(placeholder=t("experience_tags_label"), id="exp-tags-input")
            yield Select(
                [
                    (t("experience_scope_workspace"), "workspace"),
                    (t("experience_scope_general"), "general"),
                ],
                value="workspace",
                id="exp-scope-select",
            )
        with Horizontal(classes="form-row"):
            yield Button(t("experience_suggest"), id="exp-suggest", classes="btn btn-secondary")
            yield Button(t("confirm"), id="exp-confirm", classes="btn btn-primary")
            yield Button(t("experience_export"), id="exp-export", classes="btn btn-secondary")
            yield Button(t("refresh"), id="exp-refresh", classes="btn btn-secondary")
            yield Button(t("delete"), id="exp-delete", classes="btn btn-danger")
        yield Static("", id="exp-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def _get_experience_controller(self):
        from core.tui.screens.experience import ExperienceScreenController

        return ExperienceScreenController(project_root=self._project_root)

    def _get_workspace_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        return WorkspaceScreenController(project_root=self._project_root)

    def _load_workspaces(self) -> None:
        select_widget = self.query_one("#exp-workspace-select", Select)
        controller = self._get_workspace_controller()
        try:
            workspaces = controller.list_workspaces()
            options = [(ws["label"], ws["id"]) for ws in workspaces]
            select_widget.set_options(options)
        except Exception as e:
            self._set_error(e)

    def _get_selected_workspace(self) -> str | None:
        select_widget = self.query_one("#exp-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _load_experiences(self) -> None:
        workspace_id = self._get_selected_workspace()
        table = self.query_one("#exp-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "ID",
            t("experience_title_label"),
            t("experience_summary_label"),
            t("experience_scope_label"),
            t("experience_tags_label"),
        )
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        controller = self._get_experience_controller()
        try:
            records = controller.list_experiences(workspace_id, include_general=True)
            if not records:
                self._set_status(t("experience_no_records"))
                return
            for record in records:
                tags = ", ".join(record.get("tags", []))
                table.add_row(
                    record.get("id", ""),
                    record.get("title", ""),
                    record.get("summary", "")[:50],
                    record.get("scope", ""),
                    tags,
                    key=record.get("id", ""),
                )
            self._set_status(f"{t('experience_list')}: {len(records)}")
        except Exception as e:
            self._set_error(e)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#exp-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        self._set_status(f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "exp-workspace-select":
            self._load_experiences()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exp-suggest":
            self._suggest_classification()
        elif event.button.id == "exp-confirm":
            self._confirm_experience()
        elif event.button.id == "exp-delete":
            self._delete_experience()
        elif event.button.id == "exp-export":
            self._export_experiences()
        elif event.button.id == "exp-refresh":
            self._load_experiences()

    def _suggest_classification(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        title_input = self.query_one("#exp-title-input", Input)
        summary_input = self.query_one("#exp-summary-input", Input)
        tags_input = self.query_one("#exp-tags-input", Input)

        title = title_input.value.strip()
        summary = summary_input.value.strip()
        if not summary:
            self._set_status(f"{t('error')}: {t('experience_summary_label')}")
            return

        tags = (
            [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]
            if tags_input.value.strip()
            else None
        )

        controller = self._get_experience_controller()
        try:
            result = controller.suggest_classification(
                workspace_id,
                summary=summary,
                title=title or None,
                tags=tags,
            )
            self._set_status(result.get("message", t("experience_suggested")))
        except Exception as e:
            self._set_error(e)

    def _confirm_experience(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        title_input = self.query_one("#exp-title-input", Input)
        summary_input = self.query_one("#exp-summary-input", Input)
        tags_input = self.query_one("#exp-tags-input", Input)
        scope_select = self.query_one("#exp-scope-select", Select)

        title = title_input.value.strip()
        summary = summary_input.value.strip()
        if not title or not summary:
            self._set_status(f"{t('error')}: {t('experience_title_label')}, {t('experience_summary_label')}")
            return

        tags = (
            [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]
            if tags_input.value.strip()
            else None
        )
        scope = str(scope_select.value) if scope_select.value != Select.BLANK else "workspace"

        controller = self._get_experience_controller()
        try:
            result = controller.confirm_suggestion(
                workspace_id,
                scope=scope,  # type: ignore[arg-type]
                title=title,
                summary=summary,
                tags=tags,
                confirm=True,
            )
            self._set_status(result.get("message", t("experience_confirmed")))
            self._load_experiences()
        except Exception as e:
            self._set_error(e)

    def _delete_experience(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        table = self.query_one("#exp-table", DataTable)
        if table.cursor_row is None:
            self._set_status(t("no_selection"))
            return

        row_data = table.get_row_at(table.cursor_row)
        record_id = str(row_data[0])
        confirmation = self.query_one("#exp-title-input", Input).value.strip()
        if confirmation != record_id:
            self._set_status(t("experience_delete_requires_confirm"))
            return

        controller = self._get_experience_controller()
        try:
            result = controller.delete_experience(
                record_id,
                workspace_id=workspace_id,
                scope="workspace",  # type: ignore[arg-type]
                confirm=record_id,
            )
            self._set_status(result.get("message", t("experience_deleted")))
            self._load_experiences()
        except Exception as e:
            self._set_error(e)

    def _export_experiences(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        controller = self._get_experience_controller()
        try:
            result = controller.export_experiences(workspace_id=workspace_id, format="json", include_general=True)
            self._set_status(result.get("message", ""))
        except Exception as e:
            self._set_error(e)


# Backward-compatible alias
ExperienceScreen = ExperienceView


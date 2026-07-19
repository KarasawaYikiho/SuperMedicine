"""Converged TUI views for the research domain."""
# ruff: noqa: E402,F401,F811

from __future__ import annotations

# --- migrated from papers.py ---
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.services import PaperRAGService


@dataclass(slots=True)
class PaperScreenController:
    """Controller for paper import/list/show/edit/enrich TUI actions."""

    project_root: Path | str | None = None

    @property
    def service(self) -> PaperRAGService:
        return PaperRAGService(self.project_root)

    @property
    def root(self) -> Path:
        return self.service.project_root

    def import_paper(
        self,
        workspace_id: str,
        source_path: str | Path,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Copy-only import into the explicit workspace."""

        result = self.service.import_paper(
            workspace_id, source_path, metadata or {}
        )
        data = self.service.require_data(result)
        return self._import_payload(data, message="论文已复制导入工作区")

    def list_papers(self, workspace_id: str) -> list[dict[str, Any]]:
        result = self.service.list_papers(workspace_id)
        return [
            self._metadata_payload(paper)
            for paper in self.service.require_data(result)
        ]

    def show_paper(self, workspace_id: str, paper_id: str) -> dict[str, Any]:
        result = self.service.show_paper(workspace_id, paper_id)
        return self._metadata_payload(
            self.service.require_data(result), message="论文详情"
        )

    def edit_metadata(
        self, workspace_id: str, paper_id: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Edit only importer-supported metadata fields."""

        result = self.service.edit_metadata(workspace_id, paper_id, metadata)
        return self._metadata_payload(
            self.service.require_data(result), message="论文元数据已更新"
        )

    def enrich_metadata(
        self, workspace_id: str, paper_id: str, *, confirm: bool
    ) -> dict[str, Any]:
        """Run explicit enrichment confirmation flow; never performs silent online enrichment."""

        result = self.service.enrich_metadata(
            workspace_id, paper_id, confirm=confirm
        )
        payload = dict(self.service.require_data(result))
        payload["message"] = (
            "论文在线补全已完成"
            if payload["status"] == "enriched"
            else "论文在线补全未执行"
        )
        payload["metadata"] = self._metadata_payload(payload["metadata"])
        return payload

    def _import_payload(
        self, result: dict[str, Any], *, message: str
    ) -> dict[str, Any]:
        payload = dict(result)
        payload["message"] = message
        payload["metadata"] = self._metadata_payload(payload["metadata"])
        return payload

    def _metadata_payload(
        self, metadata: dict[str, Any], message: str | None = None
    ) -> dict[str, Any]:
        payload = dict(metadata)
        payload["label"] = (
            f"论文：{payload.get('title') or payload.get('id') or '未命名'}"
        )
        if message is not None:
            payload["message"] = message
        return payload


# --- migrated from paper_screen.py ---
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style
from core.tui.i18n import t


class PaperView(Vertical):
    """View for managing papers."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("paper_title"), classes="section-title")
        yield Static(t("paper_action_hint"), id="paper-action-hint", classes="hint")
        yield Select(
            [],
            prompt=t("paper_select_workspace"),
            id="paper-workspace-select",
        )
        yield DataTable(id="paper-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Input(placeholder=t("paper_file_path"), id="paper-path-input")
            yield Input(placeholder=t("paper_title_label"), id="paper-title-input")
        with Horizontal(classes="form-row"):
            yield Input(placeholder=t("paper_doi_label"), id="paper-doi-input")
            yield Input(placeholder=t("paper_pmid_label"), id="paper-pmid-input")
        with Horizontal(classes="form-row"):
            yield Input(placeholder=t("paper_notes_label"), id="paper-notes-input")
            yield Input(placeholder=t("paper_tags_label"), id="paper-tags-input")
        with Horizontal(classes="form-row"):
            yield Button(
                t("paper_import"), id="paper-import", classes="btn btn-primary"
            )
            yield Button(t("refresh"), id="paper-refresh", classes="btn btn-secondary")
            yield Button(
                t("paper_enrich"), id="paper-enrich", classes="btn btn-secondary"
            )
        yield Static("", id="paper-status")

    def on_mount(self) -> None:
        self._load_workspaces()

    def _get_paper_controller(self):
        from core.tui.screens.papers import PaperScreenController

        return PaperScreenController(project_root=self._project_root)

    def _get_workspace_controller(self):
        from core.tui.screens.workspaces import WorkspaceScreenController

        return WorkspaceScreenController(project_root=self._project_root)

    def _load_workspaces(self) -> None:
        select_widget = self.query_one("#paper-workspace-select", Select)
        controller = self._get_workspace_controller()
        try:
            workspaces = controller.list_workspaces()
            options = [(ws["label"], ws["id"]) for ws in workspaces]
            select_widget.set_options(options)
            if not options:
                self._set_status(t("workspace_no_workspaces"))
        except Exception as e:
            self._set_error(e)

    def _get_selected_workspace(self) -> str | None:
        select_widget = self.query_one("#paper-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _load_papers(self, *, refreshed: bool = False) -> None:
        workspace_id = self._get_selected_workspace()
        table = self.query_one("#paper-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            "ID",
            t("paper_title_label"),
            t("paper_authors"),
            t("paper_format"),
            t("paper_imported_at"),
        )
        if not workspace_id:
            self._set_status(
                f"{t('paper_refreshed')}：{t('paper_select_workspace')}"
                if refreshed
                else t("paper_select_workspace")
            )
            return

        controller = self._get_paper_controller()
        try:
            papers = controller.list_papers(workspace_id)
            if not papers:
                self._set_status(
                    f"{t('paper_refreshed')}：{t('paper_no_papers')}"
                    if refreshed
                    else t("paper_no_papers")
                )
                return
            for paper in papers:
                authors = ", ".join(paper.get("authors", []))
                table.add_row(
                    paper.get("id", ""),
                    paper.get("title", ""),
                    authors,
                    paper.get("format", ""),
                    paper.get("imported_at", ""),
                    key=paper.get("id", ""),
                )
            self._set_status(
                f"{t('paper_refreshed')}: {len(papers)}"
                if refreshed
                else f"{t('paper_list')}: {len(papers)}"
            )
        except Exception as e:
            self._set_error(e)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#paper-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        message = (
            f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}"
        )
        self._set_status(message)
        self.app.notify(message, severity="error")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "paper-workspace-select":
            self._load_papers()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "paper-import":
            self._import_paper()
        elif event.button.id == "paper-enrich":
            self._enrich_paper()
        elif event.button.id == "paper-refresh":
            self._load_papers(refreshed=True)

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "paper-path-input":
            self._import_paper()

    def _import_paper(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        path_input = self.query_one("#paper-path-input", Input)
        title_input = self.query_one("#paper-title-input", Input)
        doi_input = self.query_one("#paper-doi-input", Input)
        pmid_input = self.query_one("#paper-pmid-input", Input)
        notes_input = self.query_one("#paper-notes-input", Input)
        tags_input = self.query_one("#paper-tags-input", Input)

        source_path = path_input.value.strip()
        if not source_path:
            self._set_status(f"{t('error')}: {t('paper_file_path')}")
            return

        metadata: dict = {}
        if title_input.value.strip():
            metadata["title"] = title_input.value.strip()
        if doi_input.value.strip():
            metadata["doi"] = doi_input.value.strip()
        if pmid_input.value.strip():
            metadata["pmid"] = pmid_input.value.strip()
        if notes_input.value.strip():
            metadata["notes"] = notes_input.value.strip()
        if tags_input.value.strip():
            metadata["tags"] = [
                tag.strip() for tag in tags_input.value.split(",") if tag.strip()
            ]

        controller = self._get_paper_controller()
        try:
            result = controller.import_paper(
                workspace_id, source_path, metadata=metadata
            )
            self._set_status(result.get("message", t("paper_imported")))
            self.app.notify(result.get("message", t("paper_imported")))
            self._load_papers()
            self._set_status(result.get("message", t("paper_imported")))
        except Exception as e:
            self._set_error(e)

    def _enrich_paper(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        table = self.query_one("#paper-table", DataTable)
        if table.row_count == 0:
            self._set_status(f"{t('error')}: {t('paper_no_papers')}，无法执行该操作")
            return
        if (
            table.cursor_row is None
            or table.cursor_row < 0
            or table.cursor_row >= table.row_count
        ):
            self._set_status(f"{t('error')}: 未选择任何论文，无法执行该操作")
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        confirmation = self.query_one("#paper-doi-input", Input).value.strip()
        if confirmation != str(row_key):
            self._set_status(t("paper_enrich_confirm"))
            return
        controller = self._get_paper_controller()
        try:
            result = controller.enrich_metadata(workspace_id, row_key, confirm=True)
            self._set_status(result.get("message", ""))
            self.app.notify(result.get("message", t("paper_enrich")))
            self._load_papers()
            self._set_status(result.get("message", ""))
        except Exception as e:
            self._set_error(e)


# Backward-compatible alias
PaperScreen = PaperView


# --- migrated from experience.py ---
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.experience import ExperienceScope, ExportFormat
from core.services import ExperienceEvolutionService


@dataclass(slots=True)
class ExperienceScreenController:
    """Controller for suggestion, confirmation, listing, editing, deletion, export."""

    project_root: Path | str | None = None

    @property
    def service(self) -> ExperienceEvolutionService:
        return ExperienceEvolutionService(self.project_root)

    def suggest_classification(
        self,
        workspace_id: str,
        *,
        summary: str,
        title: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.service.suggest_experience(
            workspace_id,
            summary,
            title=title,
            tags=tags,
            metadata=metadata,
        )
        payload = dict(self.service.require_data(result))
        payload["label"] = "经验分类建议"
        payload["message"] = "请确认后再写入经验库"
        return payload

    def confirm_suggestion(
        self,
        workspace_id: str,
        *,
        scope: ExperienceScope,
        title: str,
        summary: str,
        tags: list[str] | None = None,
        confirm: bool,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not confirm:
            raise ValueError("写入经验前需要用户最终确认")
        result = self.service.add_experience(
            workspace_id,
            scope,
            title,
            summary,
            tags=tags,
            confirm=confirm,
            source=source,
        )
        payload = dict(self.service.require_data(result))
        payload["label"] = f"经验：{payload['title']}"
        payload["message"] = "经验已确认写入"
        return payload

    def list_experiences(
        self, workspace_id: str, *, include_general: bool = False
    ) -> list[dict[str, Any]]:
        result = self.service.list_experiences(
            workspace_id, include_general=include_general
        )
        return [self._record_payload(record) for record in self.service.require_data(result)]

    def edit_experience(
        self,
        record_id: str,
        *,
        workspace_id: str,
        scope: ExperienceScope,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        result = self.service.edit_experience(
            record_id,
            workspace_id,
            scope,
            title=title,
            summary=summary,
            tags=tags,
        )
        return self._record_payload(
            self.service.require_data(result), message="经验已更新"
        )

    def delete_experience(
        self, record_id: str, *, workspace_id: str, scope: ExperienceScope, confirm: str
    ) -> dict[str, Any]:
        if confirm != record_id:
            raise ValueError("删除经验需要输入完全一致的经验 ID 作为确认")
        result = self.service.delete_experience(
            record_id, workspace_id, scope, confirm=confirm
        )
        payload = dict(self.service.require_data(result))
        payload["message"] = "经验已删除"
        return payload

    def export_experiences(
        self,
        *,
        workspace_id: str,
        format: ExportFormat = "json",
        include_general: bool = False,
        path: str | Path | None = None,
    ) -> dict[str, Any]:
        result = self.service.export_experiences(
            workspace_id,
            format,
            include_general=include_general,
            path=path,
        )
        rendered = self.service.require_data(result)
        return {"format": format, "content": rendered, "message": "经验已导出"}

    def _record_payload(
        self, record: dict[str, Any], message: str | None = None
    ) -> dict[str, Any]:
        payload = dict(record)
        payload["label"] = f"经验：{payload['title']}"
        if message is not None:
            payload["message"] = message
        return payload


# --- migrated from experience_screen.py ---
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
        yield Static(t("experience_action_hint"), id="exp-action-hint", classes="hint")
        yield Select(
            [],
            prompt=t("paper_select_workspace"),
            id="exp-workspace-select",
        )
        yield DataTable(id="exp-table", cursor_type="row")
        with Horizontal(classes="form-row"):
            yield Input(placeholder=t("experience_title_label"), id="exp-title-input")
            yield Input(
                placeholder=t("experience_summary_label"), id="exp-summary-input"
            )
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
            yield Button(
                t("experience_suggest"), id="exp-suggest", classes="btn btn-secondary"
            )
            yield Button(t("confirm"), id="exp-confirm", classes="btn btn-primary")
            yield Button(
                t("experience_export"), id="exp-export", classes="btn btn-secondary"
            )
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
            if not options:
                self._set_status(t("workspace_no_workspaces"))
        except Exception as e:
            self._set_error(e)

    def _get_selected_workspace(self) -> str | None:
        select_widget = self.query_one("#exp-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _load_experiences(self, *, refreshed: bool = False) -> None:
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
            self._set_status(
                f"{t('experience_refreshed')}：{t('paper_select_workspace')}"
                if refreshed
                else t("paper_select_workspace")
            )
            return

        controller = self._get_experience_controller()
        try:
            records = controller.list_experiences(workspace_id, include_general=True)
            if not records:
                self._set_status(
                    f"{t('experience_refreshed')}：{t('experience_no_records')}"
                    if refreshed
                    else t("experience_no_records")
                )
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
            self._set_status(
                f"{t('experience_refreshed')}: {len(records)}"
                if refreshed
                else f"{t('experience_list')}: {len(records)}"
            )
        except Exception as e:
            self._set_error(e)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#exp-status", Static)
        safe_message = str(redact_sensitive(message))
        status.update(safe_message)
        apply_status_style(status, safe_message)

    def _set_error(self, error: Exception) -> None:
        message = (
            f"{t('error')}: {redact_sensitive(str(error)) or t('safe_error_hint')}"
        )
        self._set_status(message)
        self.app.notify(message, severity="error")

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
            self._load_experiences(refreshed=True)

    def handle_input_submit(self, input_id: str, value: str) -> None:
        if input_id == "exp-summary-input":
            self._suggest_classification()
        elif input_id == "exp-title-input":
            self._confirm_experience()

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
            self.app.notify(result.get("message", t("experience_suggested")))
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
            self._set_status(
                f"{t('error')}: {t('experience_title_label')}, {t('experience_summary_label')}"
            )
            return

        tags = (
            [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]
            if tags_input.value.strip()
            else None
        )
        scope = (
            str(scope_select.value)
            if scope_select.value != Select.BLANK
            else "workspace"
        )

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
            self.app.notify(result.get("message", t("experience_confirmed")))
            self._load_experiences()
            self._set_status(result.get("message", t("experience_confirmed")))
        except Exception as e:
            self._set_error(e)

    def _delete_experience(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        table = self.query_one("#exp-table", DataTable)
        if table.row_count == 0:
            self._set_status(
                f"{t('error')}: {t('experience_no_records')}，无法执行该操作"
            )
            return
        if (
            table.cursor_row is None
            or table.cursor_row < 0
            or table.cursor_row >= table.row_count
        ):
            self._set_status(f"{t('error')}: {t('no_selection')}，无法执行该操作")
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
            self.app.notify(result.get("message", t("experience_deleted")))
            self._load_experiences()
            self._set_status(result.get("message", t("experience_deleted")))
        except Exception as e:
            self._set_error(e)

    def _export_experiences(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        controller = self._get_experience_controller()
        try:
            result = controller.export_experiences(
                workspace_id=workspace_id, format="json", include_general=True
            )
            self._set_status(result.get("message", ""))
            self.app.notify(result.get("message", t("experience_export")))
        except Exception as e:
            self._set_error(e)


# Backward-compatible alias
ExperienceScreen = ExperienceView


# --- migrated from experiment_screen.py ---
import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static, TextArea

from core.experiment_guide import (
    ExperimentSession,
    MEDICAL_BOUNDARY,
)
from core.redaction import redact_sensitive
from core.services import ExperimentToolService
from core.tui.app import apply_status_style
from core.tui.i18n import t


class ExperimentGuideView(Vertical):
    """Minimal standalone experiment guide page."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()
        self._service = ExperimentToolService(self._project_root)
        self._protocols = self._service.require_data(
            self._service.experiment_protocols()
        )
        if not self._protocols:
            raise ValueError("no experiment protocols are configured")
        selected_protocol = self._service.require_data(
            self._service.selected_experiment_protocol()
        )
        selected_protocol = selected_protocol or "wb"
        self._sessions_by_protocol: dict[str, ExperimentSession] = {}
        try:
            self._session: ExperimentSession = self._service.require_data(
                self._service.create_live_session(
                    selected_protocol, metadata={"source": "tui"}
                )
            )
        except Exception:
            self._session = self._service.require_data(
                self._service.create_live_session(
                    self._protocols[0].protocol_id, metadata={"source": "tui"}
                )
            )
        self._sync_selected_protocol()
        self._sessions_by_protocol[self._session.protocol.protocol_id] = self._session
        self._last_calculation: dict[str, Any] | None = None
        self._started_logged = False
        self._selected_field_key: object | None = None
        self._last_activated_field_key: object | None = None

    def compose(self) -> ComposeResult:
        yield Static(t("experiment_title"), classes="section-title")
        yield Static(t("experiment_boundary"), id="experiment-boundary")
        yield Static(
            t("experiment_action_hint"), id="experiment-action-hint", classes="hint"
        )
        protocol_table: DataTable = DataTable(id="experiment-protocol-table", cursor_type="row")
        protocol_table.styles.height = "auto"
        protocol_table.styles.max_height = 12
        yield protocol_table
        yield Button(
            "切换到下一个实验配置", id="experiment-switch", classes="btn btn-secondary"
        )
        yield Static("", id="experiment-session")
        yield Static("", id="experiment-step")
        yield Static("", id="experiment-instructions")
        input_table: DataTable = DataTable(id="experiment-input-table", cursor_type="row")
        input_table.styles.height = "auto"
        input_table.styles.max_height = 8
        yield input_table
        yield Button(
            "粘贴选中字段到输入框",
            id="experiment-paste-field",
            classes="btn btn-secondary",
        )
        data_input = TextArea.code_editor("", language="json", id="experiment-data-input")
        data_input.styles.height = "auto"
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
        self._selected_field_key = None
        self._last_activated_field_key = None
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
                    key=field.name,
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
        elif event.button.id == "experiment-paste-field":
            self._paste_selected_field()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Track field selection without treating selection changes as paste actions."""
        if event.data_table.id != "experiment-input-table":
            return
        if event.row_key != self._selected_field_key:
            self._selected_field_key = event.row_key
            self._last_activated_field_key = None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle repeated activation of the currently selected field.

        Row selection/highlighting is tracked separately from activation so
        changing fields can never paste a stale, previously selected row.  The
        first activation of the selected row arms paste; the next activation of
        that same still-selected row pastes exactly the current field once.
        """
        if event.data_table.id != "experiment-input-table":
            return
        if event.row_key != self._selected_field_key:
            self._selected_field_key = event.row_key
            self._last_activated_field_key = None
            return
        if event.row_key == self._last_activated_field_key:
            self._paste_field_name(event.row_key)
            self._last_activated_field_key = None
        else:
            self._last_activated_field_key = event.row_key

    def _paste_selected_field(self) -> None:
        """Paste the currently highlighted field name into the data input TextArea."""
        table = self.query_one("#experiment-input-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)
            field_name = str(row_key[0]) if row_key else ""
            if field_name:
                textarea = self.query_one("#experiment-data-input", TextArea)
                current = textarea.text
                if current and not current.endswith("\n"):
                    current += "\n"
                textarea.load_text(current + field_name + "=")

    def _paste_field_name(self, row_key: object) -> None:
        """Append field_name= to the data input TextArea."""
        field_name = str(getattr(row_key, "value", row_key))
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
            next_session = self._service.require_data(
                self._service.create_live_session(
                    next_protocol.protocol_id,
                    metadata={"source": "tui"},
                )
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
            self._service.require_data(
                self._service.select_experiment_protocol(
                    self._session.protocol.protocol_id
                )
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
            calculation = self._service.require_data(
                self._service.calculate_live_step(self._session, user_input)
            )
            if calculation.get("status") == "no_calculation":
                self._last_calculation = None
                self.query_one("#experiment-reagent-result", Static).update(
                    t("experiment_no_calculation")
                )
                self._set_status(t("experiment_no_calculation"))
                return
            self._last_calculation = calculation
            kernel_result = calculation.get("kernel_result") or {}
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
            self._service.require_data(
                self._service.submit_live_step(
                    self._session, user_input, outputs
                )
            )
            self.refresh_session_view(
                t("experiment_completed")
                if self._session.is_completed
                else t("experiment_step_saved")
            )
        except Exception as exc:
            self._set_error(exc)

    def _append_log_event(self, event_type: str, **kwargs: Any) -> None:
        self._service.require_data(
            self._service.append_live_event(
                event_type, self._session, **kwargs
            )
        )

    def _save_log(self) -> None:
        try:
            result = self._service.require_data(
                self._service.save_live_log(
                    self._session, self._last_calculation
                )
            )
            self._set_status(f"{t('experiment_log_saved')}: {result.get('file')}")
        except Exception as exc:
            self._set_error(exc)

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

"""Paper management view for SuperMedicine TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static

from core.tui.i18n import t


class PaperView(Vertical):
    """View for managing papers."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static(t("paper_title"), classes="section-title")
        yield Select(
            [],
            prompt=t("paper_select_workspace"),
            id="paper-workspace-select",
        )
        yield DataTable(id="paper-table", cursor_type="row")
        with Horizontal():
            yield Input(placeholder=t("paper_file_path"), id="paper-path-input")
            yield Input(placeholder=t("paper_title_label"), id="paper-title-input")
        with Horizontal():
            yield Input(placeholder=t("paper_doi_label"), id="paper-doi-input")
            yield Input(placeholder=t("paper_pmid_label"), id="paper-pmid-input")
        with Horizontal():
            yield Input(placeholder=t("paper_notes_label"), id="paper-notes-input")
            yield Input(placeholder=t("paper_tags_label"), id="paper-tags-input")
        with Horizontal():
            yield Button(t("paper_import"), id="paper-import", classes="btn btn-primary")
            yield Button(t("paper_enrich"), id="paper-enrich", classes="btn btn-secondary")
            yield Button(t("refresh"), id="paper-refresh", classes="btn btn-secondary")
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
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _get_selected_workspace(self) -> str | None:
        select_widget = self.query_one("#paper-workspace-select", Select)
        value = select_widget.value
        if value is None or value == Select.BLANK:
            return None
        return str(value)

    def _load_papers(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        table = self.query_one("#paper-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", t("paper_title_label"), t("paper_authors"), t("paper_format"), t("paper_imported_at"))

        controller = self._get_paper_controller()
        try:
            papers = controller.list_papers(workspace_id)
            if not papers:
                self._set_status(t("paper_no_papers"))
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
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#paper-status", Static)
        status.update(message)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "paper-workspace-select":
            self._load_papers()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "paper-import":
            self._import_paper()
        elif event.button.id == "paper-enrich":
            self._enrich_paper()
        elif event.button.id == "paper-refresh":
            self._load_papers()

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
            metadata["tags"] = [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]

        controller = self._get_paper_controller()
        try:
            result = controller.import_paper(workspace_id, source_path, metadata=metadata)
            self._set_status(result.get("message", t("paper_imported")))
            self._load_papers()
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")

    def _enrich_paper(self) -> None:
        workspace_id = self._get_selected_workspace()
        if not workspace_id:
            self._set_status(t("paper_select_workspace"))
            return

        table = self.query_one("#paper-table", DataTable)
        if table.cursor_row is None:
            self._set_status(t("no_selection"))
            return

        row_key = table.get_row_at(table.cursor_row)[0]
        controller = self._get_paper_controller()
        try:
            result = controller.enrich_metadata(workspace_id, row_key, confirm=True)
            self._set_status(result.get("message", ""))
            self._load_papers()
        except Exception as e:
            self._set_status(f"{t('error')}: {e}")


# Backward-compatible alias
PaperScreen = PaperView


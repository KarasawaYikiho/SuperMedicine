"""Diagnose view for SuperMedicine TUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style


class DiagnoseView(Vertical):
    """TUI surface aligned with the GUI/CLI diagnose feature."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static("诊断", classes="section-title")
        yield Static("输出可安全分享的配置、LLM、审计和日志诊断摘要。", classes="hint")
        with Horizontal(classes="form-row"):
            yield Button("运行全部", id="diagnose-refresh", classes="btn btn-primary")
            yield Button("配置", id="diagnose-config", classes="btn btn-secondary")
            yield Button("LLM", id="diagnose-llm", classes="btn btn-secondary")
            yield Button("安装", id="diagnose-install", classes="btn btn-secondary")
        yield Static("", id="diagnose-status")
        yield Static("点击诊断按钮以运行诊断。", id="diagnose-output")

    def on_mount(self) -> None:
        self.refresh_view_data()

    def refresh_view_data(self) -> None:
        self._run_diagnose("all")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "diagnose-refresh":
            self._run_diagnose("all")
        elif event.button.id == "diagnose-config":
            self._run_diagnose("config")
        elif event.button.id == "diagnose-llm":
            self._run_diagnose("llm")
        elif event.button.id == "diagnose-install":
            self._run_diagnose("install")

    def _run_diagnose(self, section: str) -> None:
        try:
            from cli_entry import CLI

            result = CLI().diagnose()
            if section == "config":
                result = result.get("config", {})
            elif section == "llm":
                result = result.get("llm", {})
            elif section == "install":
                result = {
                    "audit": result.get("audit", {}),
                    "log_storage": result.get("log_storage", {}),
                }
            text = json.dumps(result, ensure_ascii=False, indent=2)
            self.query_one("#diagnose-output", Static).update(str(redact_sensitive(text)))
            self._set_status("诊断完成")
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#diagnose-status", Static)
        status.update(str(redact_sensitive(message)))
        apply_status_style(status, str(message))


DiagnoseScreen = DiagnoseView

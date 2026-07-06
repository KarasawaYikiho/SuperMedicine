"""Self-evolution view for SuperMedicine TUI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Select, Static, TextArea

from core.redaction import redact_sensitive
from core.tui.app import apply_status_style


class SelfEvolutionView(Vertical):
    """TUI surface aligned with the GUI self-evolution feature."""

    def __init__(self, project_root: Path | str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._project_root = Path(project_root) if project_root else Path.cwd()

    def compose(self) -> ComposeResult:
        yield Static("自进化", classes="section-title")
        yield Static("生成代码、配置、文档或测试制品预览；写入仍受权限策略保护。", classes="hint")
        yield TextArea("", id="self-evolution-instruction")
        yield Select(
            [("代码", "code"), ("配置", "config"), ("文档", "documentation"), ("测试", "test")],
            value="code",
            id="self-evolution-type",
        )
        yield Input(placeholder="输出路径", id="self-evolution-output")
        with Horizontal(classes="form-row"):
            yield Button("生成制品", id="self-evolution-generate", classes="btn btn-primary")
            yield Button("刷新", id="self-evolution-refresh", classes="btn btn-secondary")
        yield DataTable(id="self-evolution-table", cursor_type="row")
        yield Static("", id="self-evolution-status")

    def on_mount(self) -> None:
        self.refresh_view_data()

    def refresh_view_data(self) -> None:
        table = self.query_one("#self-evolution-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "类型", "指令", "状态")
        artifacts_dir = self._project_root / "self_evolution"
        if not artifacts_dir.exists():
            self._set_status("暂无自进化制品")
            return
        count = 0
        for path in artifacts_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            table.add_row(
                path.stem,
                str(data.get("type", "-")),
                str(data.get("instruction", "-"))[:80],
                str(data.get("status", "pending")),
                key=path.stem,
            )
            count += 1
        self._set_status(f"自进化制品：{count}" if count else "暂无自进化制品")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "self-evolution-refresh":
            self.refresh_view_data()
        elif event.button.id == "self-evolution-generate":
            self._generate_artifact()

    def _generate_artifact(self) -> None:
        instruction = self.query_one("#self-evolution-instruction", TextArea).text.strip()
        output = self.query_one("#self-evolution-output", Input).value.strip()
        artifact_type = self.query_one("#self-evolution-type", Select).value
        if not instruction or not output:
            self._set_status("请填写指令和输出路径")
            return
        try:
            from cli_entry import CLI

            result = CLI().self_evolve(
                instruction=instruction,
                artifact_type=str(artifact_type or "code"),
                output=output,
                preview=True,
            )
            self._set_status(str(redact_sensitive(result.get("message") or result.get("status") or "制品已生成")))
            self.refresh_view_data()
        except Exception as exc:
            self._set_status(f"错误：{redact_sensitive(str(exc))}")

    def _set_status(self, message: str) -> None:
        status = self.query_one("#self-evolution-status", Static)
        status.update(str(redact_sensitive(message)))
        apply_status_style(status, str(message))


SelfEvolutionScreen = SelfEvolutionView

"""Python launcher contracts for the OpenTUI-only terminal interface."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from core.tui.app import TUIStatus, launch_tui, main
from core.tui.opentui_runtime import OpenTUIRuntimeError


def test_dry_run_reports_the_pinned_opentui_runtime(tmp_path, capsys):
    status = launch_tui(dry_run=True, project_root=tmp_path)

    assert status == TUIStatus(
        title=status.title,
        message=status.message,
        labels=status.labels,
        interactive=False,
    )
    assert status.runtime_name == "@opentui/core"
    assert status.runtime_version == "0.4.3"
    assert status.title in capsys.readouterr().out


def test_interactive_launch_delegates_terminal_ownership_to_opentui(
    tmp_path, monkeypatch, capsys
):
    launched: list[Path] = []
    monkeypatch.setattr(
        "core.log_report_handler.configure_tui_log_storage", lambda root: None
    )
    monkeypatch.setattr(
        "core.tui.app.launch_opentui_runtime",
        lambda *, project_root: launched.append(project_root) or 0,
    )

    status = launch_tui(project_root=tmp_path)

    assert status.interactive is True
    assert launched == [tmp_path.resolve()]
    assert capsys.readouterr().out == ""


def test_missing_opentui_runtime_returns_actionable_noninteractive_status(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "core.log_report_handler.configure_tui_log_storage", lambda root: None
    )

    def fail(**_kwargs):
        raise OpenTUIRuntimeError("Install Bun and retry")

    monkeypatch.setattr("core.tui.app.launch_opentui_runtime", fail)

    status = launch_tui(project_root=tmp_path)

    assert status.interactive is False
    assert status.message == "Install Bun and retry"


def test_tui_main_accepts_dry_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    assert main(["--dry-run"]).interactive is False


@pytest.mark.parametrize(
    ("module_name", "symbol"),
    [
        ("core.tui.screens.chat_view", "ChatView"),
        ("core.tui.screens.workspace_screen", "WorkspaceView"),
        ("core.tui.screens.paper_screen", "PaperView"),
        ("core.tui.screens.permission_screen", "PermissionView"),
        ("core.tui.prompt_input", "PromptInput"),
        ("core.tui.stream_capture", "_capture_current_thread_tui_streams"),
    ],
)
def test_historical_tui_modules_resolve_to_explicit_opentui_aliases(
    module_name, symbol
):
    module = importlib.import_module(module_name)

    assert hasattr(module, symbol)
    assert module.OPENTUI_REPLACEMENT == "core.tui.app.launch_tui"

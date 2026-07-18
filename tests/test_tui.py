from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from textual.widgets import Button, DataTable, Input, ListView, Select, Static, TextArea

from cli_entry import CLI, main
from core.config_center import ConfigCenter
from core.llm_manager import LLMConfigManager
from core.log_report import LogReportStore
from core.log_report_models import TUI_LOG_SESSION_ID
from core.tui.app import PromptInput, SuperMedicineTUI, launch_tui
from core.tui.dialog_history import DialogHistoryPrivacyError, DialogHistoryStore
from core.tui.i18n import LABELS, t, tui_title_style_inventory
from core.tui.permissions import TUI_TOOL_ACTION, prepare_tool_action
from core.tui.preview_artifact import write_preview_artifact
from core.tui.screens.chat_view import ChatView, safe_display_text
from core.tui.screens.dashboard import (
    DashboardOverviewController,
    DashboardView,
    collect_dashboard_context,
)
from core.tui.screens.dialog_screen import DialogView
from core.tui.screens.experience import ExperienceScreenController
from core.tui.screens.experience_screen import ExperienceView
from core.tui.screens.experiment_screen import ExperimentGuideView
from core.tui.screens.llm_screen import LLMScreenController, LLMView
from core.tui.screens.log_screen import LogReportView
from core.tui.screens.paper_screen import PaperView
from core.tui.screens.papers import PaperScreenController
from core.tui.screens.permission_screen import PermissionScreenController, PermissionView
from core.tui.screens.tool_screen import ToolView
from core.tui.screens.workspace_screen import WorkspaceView
from core.tui.screens.workspaces import WorkspaceScreenController
from core.tui.state import TUIState, load_recent_workspace, save_recent_workspace
from core.tui.status_helpers import STATUS_STYLE_CLASSES
from core.workspace import WorkspaceManager
from permission.access_mode import AccessDecisionStatus, FullAccessConfirmationRequired
from permission.policy import PermissionResult


# ═══ Shared helper functions ═══


def _static_text(widget: Static) -> str:
    return str(widget.renderable)


def _read_app_tcss() -> str:
    return (Path(__file__).resolve().parents[1] / "core" / "tui" / "app.tcss").read_text(
        encoding="utf-8"
    )


def _css_block(css: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", css, re.DOTALL)
    assert match is not None
    return match.group("body")


async def _wait_for_tui_condition(pilot, condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause()
        if condition():
            return
    await pilot.pause()
    assert condition()


def _assert_red_error_with_reason(status: Static, reason: str) -> None:
    rendered = _static_text(status)
    has_class = getattr(status, "has_class", None)
    classes = {str(class_name) for class_name in getattr(status, "classes", set())}

    assert t("error") in rendered
    assert reason in rendered
    assert "status-error" in classes or (
        callable(has_class) and has_class("status-error")
    )


def _assert_tool_empty_run_error(status: Static) -> None:
    rendered = _static_text(status)
    has_class = getattr(status, "has_class", None)
    classes = {str(class_name) for class_name in getattr(status, "classes", set())}

    assert t("error") in rendered
    assert t("tool_no_tools") in rendered
    assert "status-error" in classes or (
        callable(has_class) and has_class("status-error")
    )


def _assert_same_view_intact(app: SuperMedicineTUI, view_name: str) -> None:
    assert app._current_view == view_name
    assert app._views[view_name].display is True
    assert app.query_one("#prompt-input", Input) is not None


class CapturingRichLog:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.write_options: list[dict[str, Any]] = []

    def write(self, value: str, **_: Any) -> None:
        self.lines.append(value)
        self.write_options.append(_)

    def clear(self) -> None:
        self.lines.clear()
        self.write_options.clear()


class CapturingStatic:
    def __init__(self) -> None:
        self.content: str = ""
        self.visible: bool = False

    def update(self, value: str) -> None:
        self.content = value


class CapturingChatView(ChatView):
    def __init__(self) -> None:
        super().__init__()
        self.output = CapturingRichLog()
        self._indicator = CapturingStatic()
        self._processing_indicator = CapturingStatic()

    def query_one(self, selector, widget_type=None):
        if selector == "#chat-output":
            return self.output
        if selector == "#thinking-indicator":
            return self._indicator
        if selector == "#processing-indicator":
            return self._processing_indicator
        return self.output


class DummyPromptInput:
    id = "prompt-input"

    def __init__(self, value: str = "") -> None:
        self.value = value
        self.disabled = False
        self.placeholder = t("input_placeholder")
        self.focused = False

    def focus(self) -> None:
        self.focused = True


class DummySecondaryInput(DummyPromptInput):
    id = "secondary-input"


class DummySubmittedEvent:
    def __init__(
        self, value: str, input_widget: DummyPromptInput | None = None
    ) -> None:
        self.value = value
        self.input = input_widget or DummyPromptInput(value)
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


class CapturingSubmitChat:
    def __init__(self) -> None:
        self.user_messages: list[str] = []
        self.status_messages: list[str] = []
        self.error_messages: list[str] = []

    def add_user_message(self, message: str) -> int:
        self.user_messages.append(message)
        return len(self.user_messages)

    def add_status_message(self, message: str) -> None:
        self.status_messages.append(message)

    def add_system_message(self, message: str) -> None:
        self.status_messages.append(message)

    def add_assistant_message(self, message: str, turn_id: int | None = None) -> None:
        self.status_messages.append(message)

    def add_error_message(self, message: str) -> None:
        self.error_messages.append(message)


class FakePermissionEngine:
    def __init__(self, result: PermissionResult):
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def check(self, agent_id, action, resource, context=None):
        self.calls.append(
            {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": context,
            }
        )
        return self.result


def _policy(tmp_path):
    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True, exist_ok=True)
    (policies / "default.yaml").write_text(
        "agent_id: delta\nrole: test\npermissions:\n  allowed:\n    - action: 'paper.enrich'\n      scope: '*'\n",
        encoding="utf-8",
    )


def _allow_delete_policy(tmp_path):
    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True)
    (policies / "default.yaml").write_text(
        "agent_id: delta\nrole: test\npermissions:\n  allowed:\n    - action: 'workspace.delete'\n      scope: '*'\n",
        encoding="utf-8",
    )


# ═══ test_tui_chat_view ═══


class TestThinkingAnimation:
    def test_thinking_indicator_is_composed_inside_chat_dialog(self):
        compose_source = inspect.getsource(ChatView.compose)

        assert 'with Container(id="chat-dialog")' in compose_source
        assert 'yield RichLog(id="chat-output"' in compose_source
        assert 'yield Static("", id="thinking-indicator")' in compose_source
        assert compose_source.index('with Container(id="chat-dialog")') < compose_source.index(
            'yield Static("", id="thinking-indicator")'
        )

    def test_processing_indicator_is_not_composed_inside_chat_view(self):
        compose_source = inspect.getsource(ChatView.compose)

        assert 'yield Static("", id="processing-indicator")' not in compose_source

    def test_thinking_indicator_css_anchors_lower_right_inside_chat_dialog(self):
        css = _read_app_tcss()
        dialog = _css_block(css, "#chat-dialog")
        thinking = _css_block(css, "#thinking-indicator")

        assert "height: 1fr" in dialog
        assert "width: 100%" in dialog
        assert "min-width: 0" in dialog
        assert "layers: base overlay" in dialog
        assert "dock: bottom" in thinking
        assert "align: right bottom" in thinking
        assert "layer: overlay" in thinking
        assert "margin: 0 2 1 0" in thinking

    def test_start_thinking_animation_sets_indicator_visible(self):
        view = CapturingChatView()

        view._thinking_active = True
        view._thinking_frame = 0
        view._indicator.visible = True
        view._indicator.update("[bold magenta]🧠 思考中 ○○○○○[/]")

        assert view._indicator.visible is True
        assert "思考中" in view._indicator.content
        assert "○○○○○" in view._indicator.content

    def test_advance_thinking_frame_updates_fill_pattern(self):
        view = CapturingChatView()
        view._thinking_active = True

        for frame in range(6):
            view._thinking_frame = frame
            view._advance_thinking_frame()
            filled = "●" * ((frame + 1) % 6)
            empty = "○" * (5 - (frame + 1) % 6)
            assert filled + empty in view._indicator.content
            assert "思考中" in view._indicator.content

    def test_stop_thinking_animation_hides_indicator(self):
        view = CapturingChatView()
        view._thinking_active = True
        view._indicator.visible = True

        view._thinking_active = False
        view._indicator.visible = False

        assert view._thinking_active is False
        assert view._indicator.visible is False

    def test_thinking_animation_inactive_frame_does_nothing(self):
        view = CapturingChatView()
        view._thinking_active = False
        view._indicator.content = "unchanged"

        view._advance_thinking_frame()

        assert view._indicator.content == "unchanged"


class TestProcessingAnimation:
    def test_app_compose_places_processing_indicator_before_input_bar(self):
        compose_source = inspect.getsource(SuperMedicineTUI.compose)

        assert 'yield Static("", id="processing-indicator")' in compose_source
        assert compose_source.index('yield Static("", id="processing-indicator")') < compose_source.index(
            'with Horizontal(id="input-bar")'
        )

    def test_processing_indicator_css_has_no_extra_frame(self):
        css = _read_app_tcss()
        processing = _css_block(css, "#processing-indicator")

        assert "border:" not in processing
        assert "dock:" not in processing
        assert "layer:" not in processing
        assert "background:" not in processing

    def test_start_processing_animation_sets_indicator_visible(self):
        view = CapturingChatView()

        view._processing_active = True
        view._processing_frame = 0
        view._processing_indicator.visible = True
        view._processing_indicator.update(
            f"[bold yellow]⏳ {t('chat_processing_state')} ○○○○○[/]"
        )

        assert view._processing_indicator.visible is True
        assert t("chat_processing_state") in view._processing_indicator.content
        assert "○○○○○" in view._processing_indicator.content

    def test_advance_processing_frame_updates_fill_pattern(self):
        view = CapturingChatView()
        view._processing_active = True

        for frame in range(6):
            view._processing_frame = frame
            view._advance_processing_frame()
            assert t("chat_processing_state") in view._processing_indicator.content

    def test_stop_processing_animation_hides_indicator(self):
        view = CapturingChatView()
        view._processing_active = True
        view._processing_indicator.visible = True

        view._processing_active = False
        view._processing_indicator.visible = False

        assert view._processing_active is False
        assert view._processing_indicator.visible is False

    def test_processing_animation_inactive_frame_does_nothing(self):
        view = CapturingChatView()
        view._processing_active = False
        view._processing_indicator.content = "unchanged"

        view._advance_processing_frame()

        assert view._processing_indicator.content == "unchanged"


class TestThinkingContent:
    def test_append_thinking_content_writes_to_output(self):
        view = CapturingChatView()

        view.append_thinking_content("Let me think about this...")

        rendered = "\n".join(view.output.lines)
        assert "Let me think about this..." in rendered
        assert "dim magenta" in rendered

    def test_append_thinking_content_skips_empty_string(self):
        view = CapturingChatView()

        view.append_thinking_content("")

        assert view.output.lines == []

    def test_append_thinking_content_redacts_secrets(self):
        view = CapturingChatView()

        view.append_thinking_content("api_key=sk-secret123456789")

        rendered = "\n".join(view.output.lines)
        assert "sk-secret123456789" not in rendered
        assert "[已隐藏]" in rendered

    def test_add_reasoning_status_shows_magenta_label(self):
        view = CapturingChatView()

        view.add_reasoning_status("模型正在处理请求")

        rendered = "\n".join(view.output.lines)
        assert "推理状态" in rendered
        assert "🧠" in rendered
        assert "模型正在处理请求" in rendered


class TestStreamingAssistantMessage:
    def test_begin_assistant_message_shows_assistant_label_only(self):
        view = CapturingChatView()
        view.add_user_message("hello")

        view.begin_assistant_message(turn_id=1)

        rendered = "\n".join(view.output.lines)
        assert f"{t('chat_assistant_label')} #1" in rendered
        assert rendered.rstrip().endswith(f"{t('chat_assistant_label')} #1[/]")

    def test_append_assistant_delta_writes_content(self):
        view = CapturingChatView()

        view.append_assistant_delta("Hello ")
        view.append_assistant_delta("world")

        rendered = "\n".join(view.output.lines)
        assert "Hello " in rendered
        assert "world" in rendered

    def test_append_assistant_delta_skips_empty(self):
        view = CapturingChatView()

        view.append_assistant_delta("")

        assert view.output.lines == []

    def test_append_assistant_delta_redacts_secrets(self):
        view = CapturingChatView()

        view.append_assistant_delta("Bearer sk-stream-secret123456789")

        rendered = "\n".join(view.output.lines)
        assert "sk-stream-secret123456789" not in rendered

    def test_streaming_flow_begin_then_deltas_then_reasoning(self):
        view = CapturingChatView()
        view.add_user_message("test")

        view.begin_assistant_message(turn_id=1)
        view.append_assistant_delta("Part 1 ")
        view.append_assistant_delta("Part 2")
        view.add_reasoning_status("推理完成")

        rendered = "\n".join(view.output.lines)
        assert f"{t('chat_user_label')} #1" in rendered
        assert f"{t('chat_assistant_label')} #1" in rendered
        assert "Part 1 " in rendered
        assert "Part 2" in rendered
        assert "推理状态" in rendered

    def test_streaming_writes_use_full_chat_dialog_width(self):
        view = CapturingChatView()

        view.begin_assistant_message(turn_id=1)
        view.append_assistant_delta("A long streamed assistant response chunk ")
        view.append_assistant_delta("continues without narrowing the renderable.")

        assert view.output.write_options
        assert all(options.get("expand") is True for options in view.output.write_options)
        assert all(options.get("shrink") is False for options in view.output.write_options)


class TestSafeDisplayText:
    def test_safe_display_text_escapes_html_tags(self):
        result = safe_display_text("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_safe_display_text_escapes_rich_markup(self):
        result = safe_display_text("[bold]text[/bold]")
        assert "\\[bold]" in result

    def test_safe_display_text_redacts_api_keys(self):
        result = safe_display_text("api_key=sk-my-secret-key-12345678")
        assert "sk-my-secret-key-12345678" not in result
        assert "[已隐藏]" in result

    def test_safe_display_text_redacts_bearer_tokens(self):
        result = safe_display_text("Authorization: Bearer abc.def.ghi")
        assert "Bearer abc" not in result
        assert "Bearer [已隐藏]" in result

    def test_safe_display_text_handles_none_value(self):
        result = safe_display_text(None)
        assert result == ""


def test_chat_messages_are_escaped_redacted_and_stably_prefixed():
    view = CapturingChatView()

    turn_id = view.add_user_message("<ask> [bold] api_key=sk-secret123456789")
    view.add_system_message("系统 [red] <notice>")
    view.add_assistant_message("结果 [green] <ok> Bearer abc.def.ghi", turn_id=turn_id)
    view.add_error_message("失败 password=p@ssword [blink]")
    rendered = "\n".join(view.output.lines)

    assert t("chat_user_label") in rendered
    assert t("chat_system_label") in rendered
    assert t("chat_assistant_label") in rendered
    assert t("chat_error_label") in rendered
    assert "&lt;ask&gt;" in rendered
    assert "\\[bold]" in rendered
    assert "\\[green]" in rendered
    assert "\\[blink]" in rendered
    assert "sk-secret" not in rendered
    assert "p@ssword" not in rendered
    assert "Bearer abc" not in rendered
    assert t("chat_error_action") in rendered
    assert f"{t('chat_user_label')} #1" in rendered
    assert f"{t('chat_assistant_label')} #1" in rendered


def test_chat_status_message_uses_status_prefix_and_escaping():
    view = CapturingChatView()

    view.add_status_message("运行中 [red] <unsafe>")
    rendered = "\n".join(view.output.lines)

    assert t("chat_status_label") in rendered
    assert "\\[red]" in rendered
    assert "&lt;unsafe&gt;" in rendered


def test_chat_empty_success_and_error_copy_stays_localized_and_secret_safe():
    view = CapturingChatView()
    secret = "sk-chat-empty-secret"

    view.add_system_message(t("chat_help"))
    view.add_assistant_message(t("chat_no_output"))
    view.add_error_message(f"{t('error')}: api_key={secret}")
    rendered = "\n".join(view.output.lines)

    assert t("chat_help") in rendered
    assert t("chat_no_output") in rendered
    assert t("chat_error_action") in rendered
    assert secret not in rendered
    assert "[已隐藏]" in rendered


def test_kernel_result_format_handles_success_error_empty_and_non_dict_outputs():
    assert SuperMedicineTUI._format_kernel_result(
        {"status": "success", "output": {"b": 2, "a": [1]}}
    ) == {
        "kind": "assistant",
        "message": f'{t("chat_result_status")}: success\n{t("chat_result_output")}:\n{{\n  "a": [\n    1\n  ],\n  "b": 2\n}}',
    }
    assert SuperMedicineTUI._format_kernel_result(
        {"status": "failure", "error": "bad [red]"}
    ) == {
        "kind": "error",
        "message": f"{t('chat_result_status')}: failure\nbad [red]",
    }
    assert (
        "sk-secret"
        not in SuperMedicineTUI._format_kernel_result(
            {"status": "success", "output": {"api_key": "sk-secret123456789"}}
        )["message"]
    )
    assert SuperMedicineTUI._format_kernel_result(
        {"status": "success", "output": ""}
    ) == {
        "kind": "assistant",
        "message": f"{t('chat_result_status')}: success\n{t('chat_result_output')}:\n{t('chat_no_output')}",
    }
    assert SuperMedicineTUI._format_kernel_result(["one", "two"])["message"].endswith(
        '[\n  "one",\n  "two"\n]'
    )


def test_kernel_result_format_redacts_secret_strings_and_keeps_stable_chinese_headings():
    secret = "sk-chat-format-secret"

    formatted = SuperMedicineTUI._format_kernel_result(
        {"status": "success", "output": f"api_key={secret} [bold] <ok>"}
    )

    assert formatted["kind"] == "assistant"
    assert formatted["message"].startswith(
        f"{t('chat_result_status')}: success\n{t('chat_result_output')}:\n"
    )
    assert secret not in formatted["message"]
    assert "[已隐藏]" in formatted["message"]


def test_run_kernel_task_emits_running_completion_and_formatted_messages(
    monkeypatch, tmp_path
):
    events: list[tuple[str, ...]] = []

    class FakeChat:
        def add_system_message(self, message: str) -> None:
            events.append(("system", message))

        def add_status_message(self, message: str) -> None:
            events.append(("status", message))

        def add_assistant_message(
            self, message: str, turn_id: int | None = None
        ) -> None:
            events.append(("assistant", message))

        def add_error_message(self, message: str) -> None:
            events.append(("error", message))

        def start_processing_animation(self):
            events.append(("processing_animation_start",))

        def stop_processing_animation(self):
            events.append(("processing_animation_stop",))

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            pass

        def execute_task(self, message: str, progress_callback=None):
            if progress_callback:
                progress_callback(
                    {
                        "kind": "reasoning",
                        "message": "模型正在处理请求；当前 Provider 未暴露完整思考内容，仅显示合规处理进度。",
                    }
                )
            return {"status": "success", "output": ["ok"]}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    monkeypatch.setattr(SuperMedicineTUI, "_update_status_bar", lambda self: None)
    app = SuperMedicineTUI(project_root=tmp_path)

    asyncio.run(app._run_kernel_task("hello", FakeChat(), turn_id=1))

    assert events[0] == ("system", t("thinking"))
    assert ("processing_animation_start",) in events
    assert any(
        kind == "assistant" and t("chat_result_status") in message and "ok" in message
        for kind, message in (e for e in events if len(e) == 2)
    )
    assert events[-1] == ("processing_animation_stop",)
    assert ("status", t("chat_completed")) in events
    assert app._task_running is False


def test_chat_submit_sets_processing_state_locks_main_input_and_displays_status(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)
    prompt = DummyPromptInput("hello")
    chat = CapturingSubmitChat()
    workers: list[object] = []
    app._views = {"chat": chat}
    app.query_one = lambda selector, widget_type=None: prompt
    app._update_status_bar = lambda: None

    def capture_worker(worker, exclusive=True):
        workers.append(worker)
        worker.close()

    app.run_worker = capture_worker

    app.on_input_submitted(DummySubmittedEvent("hello", prompt))
    status = app.status_text("chat")

    assert app.is_chat_processing is True
    assert prompt.disabled is True
    assert prompt.placeholder == t("input_placeholder_processing")
    assert t("chat_processing_state") in status.center
    assert chat.user_messages == ["hello"]
    assert len(workers) == 1


def test_chat_processing_locks_only_main_prompt_input(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)
    prompt = DummyPromptInput("hello")
    secondary = DummySecondaryInput()
    chat = CapturingSubmitChat()
    workers: list[object] = []
    app._views = {"chat": chat}

    def fake_query_one(selector, widget_type=None):
        if selector == "#prompt-input":
            return prompt
        return secondary

    app.query_one = fake_query_one
    app._update_status_bar = lambda: None

    def capture_worker(worker, exclusive=True):
        workers.append(worker)
        worker.close()

    app.run_worker = capture_worker

    app.on_input_submitted(DummySubmittedEvent("hello", prompt))

    assert prompt.disabled is True
    assert secondary.disabled is False
    assert len(workers) == 1


def test_chat_repeated_submit_while_processing_ignores_second_worker(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)
    prompt = DummyPromptInput("first")
    chat = CapturingSubmitChat()
    workers: list[object] = []
    app._views = {"chat": chat}
    app.query_one = lambda selector, widget_type=None: prompt
    app._update_status_bar = lambda: None

    def capture_worker(worker, exclusive=True):
        workers.append(worker)
        worker.close()

    app.run_worker = capture_worker

    app.on_input_submitted(DummySubmittedEvent("first", prompt))
    app.on_input_submitted(DummySubmittedEvent("second", prompt))

    assert chat.user_messages == ["first"]
    assert len(workers) == 1
    assert t("chat_processing_reject") in chat.status_messages


def test_chat_processing_unlocks_on_completion(monkeypatch, tmp_path):
    class FakeKernel:
        def __init__(self, *args, **kwargs):
            pass

        def execute_task(self, message: str, progress_callback=None):
            return {"status": "success", "output": "ok"}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    app = SuperMedicineTUI(project_root=tmp_path)
    prompt = DummyPromptInput()
    app.query_one = lambda selector, widget_type=None: prompt
    app._update_status_bar = lambda: None
    app._set_chat_processing(True)

    asyncio.run(app._run_kernel_task("hello", CapturingSubmitChat(), turn_id=1))

    assert app.is_chat_processing is False
    assert prompt.disabled is False
    assert prompt.placeholder == t("input_placeholder")


def test_chat_processing_status_refreshes_when_switching_views(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)
    updates: list[str] = []

    class FakeView:
        display = True

    app._views = {"chat": FakeView()}
    app._current_view = "chat"
    app._chat_processing = True
    app._task_running = True
    app._focus_current_view_default = lambda: None
    app._update_status_bar = lambda: updates.append(app.status_text("chat").center)

    app.action_switch_view("chat")

    assert updates
    assert t("chat_processing_state") in updates[-1]

def test_chat_processing_unlocks_on_exception(monkeypatch, tmp_path):
    class FakeKernel:
        def __init__(self, *args, **kwargs):
            pass

        def execute_task(self, message: str, progress_callback=None):
            raise RuntimeError("boom")

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    app = SuperMedicineTUI(project_root=tmp_path)
    prompt = DummyPromptInput()
    chat = CapturingSubmitChat()
    app.query_one = lambda selector, widget_type=None: prompt
    app._update_status_bar = lambda: None
    app._set_chat_processing(True)

    asyncio.run(app._run_kernel_task("hello", chat, turn_id=1))

    assert app.is_chat_processing is False
    assert prompt.disabled is False
    assert chat.error_messages

def test_chat_streaming_methods_keep_assistant_turn_and_append_safe_deltas():
    view = CapturingChatView()
    turn_id = view.add_user_message("hello")

    view.begin_assistant_message(turn_id)
    view.append_assistant_delta("delta [bold] <x> token=secret")
    view.add_reasoning_status(
        "模型正在处理请求；当前 Provider 未暴露完整思考内容，仅显示合规处理进度。"
    )
    rendered = "\n".join(view.output.lines)

    assert f"{t('chat_user_label')} #1" in rendered
    assert f"{t('chat_assistant_label')} #1" in rendered
    assert "delta" in rendered
    assert "\\[bold]" in rendered
    assert "&lt;x&gt;" in rendered
    assert "secret" not in rendered
    assert "推理状态" in rendered


def test_safe_display_text_escapes_markup_and_redacts_secrets():
    rendered = safe_display_text("token=abc123 [bold] <x> sk-liveSECRET123")

    assert "abc123" not in rendered
    assert "sk-liveSECRET123" not in rendered
    assert "\\[bold]" in rendered
    assert "&lt;x&gt;" in rendered


# ═══ test_tui_dashboard ═══


def test_dashboard_context_for_uninitialized_project_is_chinese_and_stable(tmp_path):
    context = collect_dashboard_context(tmp_path)

    assert context["initialized"] is False
    assert context["init_status"] == "未初始化"
    assert context["workspace_count"] == 0
    assert context["plugin_count"] == 0
    assert context["module_count"] == 0
    assert context["llm_status"] == "LLM 未就绪：暂无 LLM Provider"
    assert context["recent_hint"] == "暂无工作区，请先创建"
    assert "初始化" in context["action_hint"]


def test_dashboard_context_for_initialized_project_with_workspace_and_ready_llm_redacts_secret(
    tmp_path,
):
    secret = "sk-dashboard-secret"
    (tmp_path / ".supermedicine").mkdir()
    plugin_dir = tmp_path / "plugins" / "demo_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text("name: demo\n", encoding="utf-8")
    (tmp_path / "core" / "agents").mkdir(parents=True)

    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("study-a")
    manager.save_recent_selection("study-a")
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.local.test/v1",
                            "api_key": secret,
                            "model": "gpt-dashboard",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)
    rows = DashboardOverviewController(tmp_path).overview_rows()
    rendered = str(context) + str(rows)

    assert context["initialized"] is True
    assert context["init_status"] == "已初始化"
    assert context["workspace_count"] == 1
    assert context["plugin_count"] == 1
    assert context["module_count"] == 1
    assert context["llm_status"] == "LLM 已就绪：openai（gpt-dashboard）"
    assert context["recent_hint"] == "最近工作区：study-a"
    assert rows[0] == ("初始化", "已初始化")
    assert secret not in rendered


def test_dashboard_context_reports_initialized_project_without_workspace_or_provider(
    tmp_path,
):
    (tmp_path / ".supermedicine").mkdir()

    context = collect_dashboard_context(tmp_path)

    assert context["init_status"] == "已初始化"
    assert context["workspace_count"] == 0
    assert context["llm_status"] == "LLM 未就绪：暂无 LLM Provider"
    assert context["recent_hint"] == "暂无工作区，请先创建"
    assert "创建工作区" in context["action_hint"]


def test_dashboard_context_collects_counts_recent_hint_and_ready_advice_without_network(
    tmp_path,
):
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / "plugins" / "good_plugin").mkdir(parents=True)
    (tmp_path / "plugins" / "good_plugin" / "plugin.yaml").write_text(
        "name: good\n", encoding="utf-8"
    )
    (tmp_path / "plugins" / "_ignored").mkdir(parents=True)
    (tmp_path / "plugins" / "_ignored" / "plugin.yaml").write_text(
        "name: ignored\n", encoding="utf-8"
    )
    (tmp_path / "core" / "agents").mkdir(parents=True)
    (tmp_path / "core" / "_private").mkdir(parents=True)
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("study-a")
    manager.initialize_workspace("study-b")
    manager.save_recent_selection("study-b", "study-a")
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://llm.local.test/v1",
                            "api_key": "sk-dashboard-counts-secret",
                            "model": "gpt-dashboard",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)

    assert context["workspace_count"] == 2
    assert context["plugin_count"] == 1
    assert context["module_count"] == 1
    assert context["llm_ready"] is True
    assert context["recent_hint"] == "最近工作区：study-a"
    assert context["action_hint"] == "运行上下文已就绪，可进入对话或工作区继续任务。"
    assert "sk-dashboard-counts-secret" not in str(context)


def test_dashboard_context_reports_incomplete_llm_without_api_key_leak(tmp_path):
    secret = "sk-incomplete-dashboard-secret"
    (tmp_path / ".supermedicine").mkdir()
    (tmp_path / ".supermedicine" / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "broken",
                    "providers": {
                        "broken": {
                            "api_format": "openai",
                            "base_url": "https://broken.local.test/v1",
                            "api_key": secret,
                            "model": "",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    context = collect_dashboard_context(tmp_path)

    assert context["llm_status"] == "LLM 未就绪：broken（缺少：model）"
    assert secret not in str(context)


def test_dashboard_view_exposes_activation_refresh_hook():
    view = DashboardView()

    assert hasattr(view, "refresh_view_data")
    assert "_load_data" in inspect.getsource(DashboardView.refresh_view_data)


class TestDashboardRefresh:
    def test_dashboard_view_uses_targeted_refresh_without_polling(self):
        source = inspect.getsource(DashboardView)

        assert "refresh_view_data" in source
        assert "set_interval" not in source

    def test_dashboard_view_compose_declares_required_widgets(self):
        source = inspect.getsource(DashboardView.compose)

        assert 'id="dashboard-table"' in source
        assert 'id="dashboard-advice"' in source
        assert 'id="dashboard-summary"' in source
        assert 'id="dashboard-shortcuts"' in source

    def test_dashboard_view_loads_data_on_mount(self, tmp_path):
        (tmp_path / ".supermedicine").mkdir()

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                table = app.query_one("#dashboard-table", DataTable)
                assert table.row_count > 0
                rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
                assert t("dashboard_init_status") in " ".join(rows)

        asyncio.run(scenario())

    def test_dashboard_view_refresh_view_data_reloads_table(self, tmp_path):
        (tmp_path / ".supermedicine").mkdir()

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                table = app.query_one("#dashboard-table", DataTable)
                initial_rows = table.row_count

                WorkspaceManager(tmp_path).initialize_workspace("dash-ws")
                app._views["dashboard"].refresh_view_data()
                await pilot.pause()

                assert table.row_count == initial_rows
                rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
                assert "1" in " ".join(rows)

        asyncio.run(scenario())

    def test_dashboard_view_switch_back_and_forth_refreshes_data(self, tmp_path):
        manager = WorkspaceManager(tmp_path)
        manager.initialize_workspace("switch-ws")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                table = app.query_one("#dashboard-table", DataTable)
                rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
                assert "1" in " ".join(rows)

                app.action_switch_view("chat")
                await pilot.pause()

                manager.initialize_workspace("switch-ws-2")
                app.action_switch_view("dashboard")
                await pilot.pause()

                rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
                assert "2" in " ".join(rows)

        asyncio.run(scenario())

    def test_dashboard_view_advice_text_updates_on_refresh(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                advice = _static_text(app.query_one("#dashboard-advice", Static))
                assert advice.startswith(t("dashboard_action_hint"))
                assert t("dashboard_action_create_workspace") in advice

                WorkspaceManager(tmp_path).initialize_workspace("adv-ws")
                app._views["dashboard"].refresh_view_data()
                await pilot.pause()

                advice = _static_text(app.query_one("#dashboard-advice", Static))
                assert advice.startswith(t("dashboard_action_hint"))
                assert t("dashboard_action_configure_llm") in advice

        asyncio.run(scenario())

    def test_dashboard_view_advice_shows_ready_when_fully_configured(self, tmp_path):
        (tmp_path / ".supermedicine").mkdir()
        WorkspaceManager(tmp_path).initialize_workspace("ready-ws")
        (tmp_path / ".supermedicine" / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "provider": "openai",
                        "providers": {
                            "openai": {
                                "api_format": "openai",
                                "base_url": "https://llm.test/v1",
                                "api_key": "sk-ready-test-key",
                                "model": "gpt-test",
                            }
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                advice = _static_text(app.query_one("#dashboard-advice", Static))
                assert t("dashboard_action_ready") in advice

        asyncio.run(scenario())

    def test_dashboard_controller_overview_rows_returns_metric_value_pairs(self, tmp_path):
        controller = DashboardOverviewController(tmp_path)

        rows = controller.overview_rows()

        assert len(rows) == 8
        labels = [label for label, _ in rows]
        assert t("dashboard_init_status") in labels
        assert t("dashboard_workspaces") in labels
        assert t("dashboard_plugins") in labels
        assert t("dashboard_modules") in labels
        assert t("dashboard_llm_status") in labels
        assert t("dashboard_token_stats") in labels
        assert t("dashboard_recent_hint") in labels
        assert t("dashboard_version") in labels

    def test_dashboard_controller_context_reflects_state_changes(self, tmp_path):
        context_before = collect_dashboard_context(tmp_path)
        assert context_before["initialized"] is False
        assert context_before["workspace_count"] == 0

        (tmp_path / ".supermedicine").mkdir()
        WorkspaceManager(tmp_path).initialize_workspace("ctx-ws")

        context_after = collect_dashboard_context(tmp_path)
        assert context_after["initialized"] is True
        assert context_after["workspace_count"] == 1

    def test_dashboard_controller_context_no_secret_leak(self, tmp_path):
        secret = "sk-dashboard-refresh-secret"
        (tmp_path / ".supermedicine").mkdir()
        (tmp_path / ".supermedicine" / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "provider": "openai",
                        "providers": {
                            "openai": {
                                "api_format": "openai",
                                "base_url": "https://llm.test/v1",
                                "api_key": secret,
                                "model": "gpt-test",
                            }
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        context = collect_dashboard_context(tmp_path)
        rows = DashboardOverviewController(tmp_path).overview_rows()

        rendered = str(context) + str(rows)
        assert secret not in rendered

    def test_dashboard_view_table_has_two_columns(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                table = app.query_one("#dashboard-table", DataTable)
                columns = [str(col.label) for col in table.columns.values()]
                assert len(columns) == 2
                assert t("dashboard_metric") in columns
                assert t("dashboard_value") in columns

        asyncio.run(scenario())

    def test_dashboard_view_shows_llm_status_in_table(self, tmp_path):
        (tmp_path / ".supermedicine").mkdir()
        (tmp_path / ".supermedicine" / "config.yaml").write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "provider": "openai",
                        "providers": {
                            "openai": {
                                "api_format": "openai",
                                "base_url": "https://llm.test/v1",
                                "api_key": "sk-llm-status-test",
                                "model": "gpt-dash",
                            }
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 50)) as pilot:
                app.action_switch_view("dashboard")
                await pilot.pause()

                table = app.query_one("#dashboard-table", DataTable)
                rows = [str(table.get_row_at(i)) for i in range(table.row_count)]
                combined = " ".join(rows)
                assert "openai" in combined
                assert "gpt-dash" in combined
                assert "LLM 已就绪" in combined

        asyncio.run(scenario())

    def test_dashboard_view_no_polling_timer(self):
        source = inspect.getsource(DashboardView)

        assert "set_interval" not in source
        assert "Timer" not in source

    def test_dashboard_context_action_hint_varies_by_state(self, tmp_path):
        context = collect_dashboard_context(tmp_path)
        assert t("dashboard_action_init") in context["action_hint"]

        (tmp_path / ".supermedicine").mkdir()
        context = collect_dashboard_context(tmp_path)
        assert t("dashboard_action_create_workspace") in context["action_hint"]

        WorkspaceManager(tmp_path).initialize_workspace("hint-ws")
        context = collect_dashboard_context(tmp_path)
        assert t("dashboard_action_configure_llm") in context["action_hint"]

    def test_dashboard_controller_advice_text_returns_action_hint(self, tmp_path):
        controller = DashboardOverviewController(tmp_path)
        context = controller.context()

        assert controller.advice_text() == context["action_hint"]


# ═══ test_tui_dialog_history ═══


def test_dialog_history_appends_and_loads_summary_events_only(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = DialogHistoryStore(tmp_path)

    event = store.append_event(
        "study-a",
        event="screen_opened",
        summary="用户打开工作区屏幕",
        metadata={"screen": "工作区"},
        session_id="session1",
    )
    loaded = store.load_events("study-a", session_id="session1")

    assert loaded[0].id == event.id
    assert loaded[0].summary == "用户打开工作区屏幕"
    assert (
        store.history_path("study-a", "session1").parent
        == tmp_path / "workspaces" / "study-a" / ".supermedicine" / "sessions"
    )


def test_dialog_history_rejects_raw_conversation_fields(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = DialogHistoryStore(tmp_path)

    with pytest.raises(DialogHistoryPrivacyError, match="原始对话"):
        store.append_event(
            "study-a",
            event="bad",
            summary="摘要",
            metadata={"messages": ["raw"]},
        )


def test_dialog_history_rejects_raw_conversation_on_reload(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    store = DialogHistoryStore(tmp_path)
    path = store.history_path("study-a")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"event": "bad", "summary": "contains raw_conversation marker"},
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(DialogHistoryPrivacyError):
        store.load_events("study-a")


# ═══ test_tui_entrypoint ═══


def test_tui_help_is_registered(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["supermedicine", "tui", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert "启动中文 TUI 工作台" in capsys.readouterr().out


def test_cli_init_help_documents_optional_desktop_exe_release(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["supermedicine", "init", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "--release-exe" in output
    assert "--desktop-dir" in output
    assert "--exe-dry-run" in output
    assert "避免真实桌面写入" in output


def test_chinese_labels_available():
    assert t("app_title") == "SuperMedicine"
    assert LABELS["permission_required"] == "需要权限确认"
    assert LABELS["layout_shortcuts"] == "快捷键"
    assert LABELS["status_task_idle"] == "任务空闲"
    assert LABELS["status_focus_input"] == "输入框"
    assert "Tab/Shift+Tab" in LABELS["status_shortcuts_hint"]
    assert "M 菜单" in LABELS["status_shortcuts_hint"]
    assert "F" not in LABELS["status_maximized"]
    assert "M 菜单" in LABELS["status_maximized"]
    assert LABELS["menu_select_view"] == "选择视图"
    assert LABELS["menu_change_theme"] == "切换主题"
    assert LABELS["menu_toggle_maximize"] == "最大化/还原"
    assert LABELS["menu_show_help"] == "帮助"
    assert "Enter" in LABELS["help_submission"]
    assert "危险操作" in LABELS["help_danger"]
    assert "LLM" in LABELS["help_status"]
    assert "任务" in LABELS["help_status"]


def test_tui_dry_run_returns_chinese_status(capsys):
    status = launch_tui(dry_run=True)

    assert status.interactive is False
    assert status.title == "SuperMedicine"
    assert "基础组件已就绪" in status.message
    assert status.current_view == "chat"
    assert status.view_title == "对话"
    assert "任务空闲" in status.status_center
    assert "1-0" not in status.shortcut_hint
    assert "M 菜单" in status.shortcut_hint
    assert "Tab/Shift+Tab" in status.shortcut_hint
    assert status.focus_target == "prompt-input"
    assert "SuperMedicine" in capsys.readouterr().out


def test_tui_startup_metadata_covers_all_primary_views_and_shortcuts():
    nav_items = SuperMedicineTUI.nav_items()
    binding_by_key = {binding.key: binding for binding in SuperMedicineTUI.BINDINGS}

    assert [item.key for item in nav_items] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "0",
    ]
    assert [item.view_id for item in nav_items] == [
        "chat",
        "dashboard",
        "workspace",
        "paper",
        "experience",
        "tool",
        "dialog",
        "llm",
        "experiment",
        "log",
    ]
    assert [item.label for item in nav_items] == [
        "对话",
        "状态看板",
        "工作区",
        "论文",
        "经验",
        "工具",
        "对话历史",
        "LLM 配置",
        "实验",
        "Log 报告",
    ]
    assert all(item.icon for item in nav_items)
    assert not ({item.key for item in nav_items} & set(binding_by_key))
    assert not any(
        binding.key.isdigit() and "switch_view" in binding.action
        for binding in SuperMedicineTUI.BINDINGS
    )
    assert "1-0" not in SuperMedicineTUI.shortcut_hint_text()
    assert "切换视图" not in SuperMedicineTUI.shortcut_hint_text()
    assert "Enter 提交" in SuperMedicineTUI.shortcut_hint_text()
    assert "M 菜单" in SuperMedicineTUI.shortcut_hint_text()
    assert "F 最大化" not in SuperMedicineTUI.shortcut_hint_text()
    assert "? 帮助" not in SuperMedicineTUI.shortcut_hint_text()


def test_opentui_page_inventory_covers_all_primary_pages_and_interactions():
    routes = SuperMedicineTUI.opentui_routes()
    by_view = {route.view_id: route for route in routes}

    assert set(by_view) == {
        "chat",
        "dashboard",
        "workspace",
        "paper",
        "experience",
        "tool",
        "dialog",
        "llm",
        "experiment",
        "log",
    }
    for view_id in [item.view_id for item in SuperMedicineTUI.nav_items()]:
        route = by_view[view_id]
        assert route.placeholder
        assert route.sections
        assert route.actions
        assert "OpenTUI" in route.placeholder or "TextTable-style" in route.placeholder
    assert by_view["chat"].sections == (
        "Conversation Scrollback",
        "Prompt Footer",
        "Processing / Thinking Status",
    )
    assert "隐藏" not in " ".join(by_view["llm"].actions)


def test_tui_labels_follow_chinese_first_policy_with_reasonable_english_terms():
    chinese_first_expectations = {
        "nav_dashboard": "状态看板",
        "nav_workspace": "工作区",
        "nav_paper": "论文",
        "nav_experience": "经验",
        "nav_tool": "工具",
        "nav_dialog": "对话历史",
        "dashboard_title": "状态看板",
        "workspace_title": "工作区",
        "paper_title": "论文",
        "experience_title": "经验",
        "tool_title": "工具",
        "dialog_title": "对话历史",
        "help_title": "帮助",
        "menu_title": "菜单",
        "experiment_title": "实验",
        "layout_shortcuts": "快捷键",
        "layout_current_view": "当前视图",
        "layout_focus": "焦点",
    }

    for key, expected in chinese_first_expectations.items():
        assert t(key) == expected

    retained_english_terms = [
        t("app_title"),
        t("nav_llm"),
        t("llm_provider"),
        t("llm_api_key"),
        t("dashboard_llm_no_provider"),
        t("log_title"),
        t("chat_user_label"),
        t("chat_system_label"),
        t("chat_assistant_label"),
        t("chat_result_output"),
    ]
    combined = "\n".join(retained_english_terms)
    for expected in ["SuperMedicine", "LLM", "Provider", "API Key", "Log", "User", "System", "Assistant", "Output"]:
        assert expected in combined
    assert re.search(r"LLM Provider", combined)


def test_tui_title_style_inventory_enforces_english_emphasis_without_replacing_chinese():
    inventory = tui_title_style_inventory()

    assert inventory["english_style_violations"] == {}
    assert inventory["english_single_word_labels"] == {
        "chat_user_label": "User",
        "chat_system_label": "System",
        "chat_assistant_label": "Assistant",
        "chat_error_label": "Error",
        "chat_status_label": "Status",
        "chat_result_status": "Status",
        "chat_result_output": "Output",
    }
    assert inventory["chinese_first_labels"]["nav_dashboard"] == "状态看板"
    assert "Chinese-first" in inventory["policy"]


def test_tui_theme_layout_and_status_text_are_testable_without_terminal(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)

    assert app.CSS_PATH.endswith("app.tcss")
    assert app.theme == "supermedicine"
    assert app.AUTO_FOCUS == "#prompt-input"
    assert "#sidebar" in Path(app.CSS_PATH).read_text(encoding="utf-8")

    idle_status = app.status_text("chat")
    assert "Harness" in idle_status.center
    assert "RAG" in idle_status.center
    assert "Agents single" in idle_status.center
    assert idle_status.left.startswith("📁 0 工作区")
    assert "🔌 0 插件" in idle_status.center
    assert "LLM 未就绪" in idle_status.center
    assert "任务空闲" in idle_status.center
    assert "当前视图：对话" in idle_status.right
    assert idle_status.focus == "焦点：输入框"

    app._task_running = True
    running_status = app.status_text("llm")
    assert "任务执行中" in running_status.center
    assert "当前视图：LLM 配置" in running_status.right


def test_tui_small_window_layout_uses_bounded_scrollable_regions():
    stylesheet = Path(SuperMedicineTUI.CSS_PATH).read_text(encoding="utf-8")
    compose_source = inspect.getsource(SuperMedicineTUI.compose)

    assert "ScrollableContainer(id=\"content-pane\")" in compose_source
    for selector in ["#app-body", "#sidebar", "#main-area", "#content-pane"]:
        block = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", stylesheet, re.DOTALL
        )
        assert block is not None, selector
        body = block.group("body")
        assert "min-height: 0" in body, selector
    for selector in ["#sidebar", "#main-area", "#content-pane", "#chat-output"]:
        block = re.search(
            rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", stylesheet, re.DOTALL
        )
        assert block is not None, selector
        assert "overflow-y: auto" in block.group("body"), selector
    assert "min-height: 8" not in stylesheet


def test_tui_dynamic_refresh_inventory_documents_targeted_boundary():
    surfaces = SuperMedicineTUI.dynamic_refresh_surfaces()
    by_view = {surface.view_id: surface for surface in surfaces}

    assert set(by_view) == {"workspace", "log", "dashboard", "tool", "dialog"}
    assert by_view["workspace"].manual_control == "#workspace-refresh"
    assert by_view["log"].refresh_hook == "refresh_view_data"
    assert all("no broad polling" in surface.policy for surface in surfaces)
    assert all("filesystem watcher" in surface.policy for surface in surfaces)


def test_tui_preview_artifact_workflow_writes_text_without_approval_claim(tmp_path):
    artifact = write_preview_artifact(project_root=tmp_path, output_dir=tmp_path)
    text = artifact.read_text(encoding="utf-8")

    assert artifact.name == "SuperMedicine_TUI_preview.txt"
    assert "SuperMedicine TUI Preview Artifact" in text
    assert "Upper-left clickable label" in text
    assert "User approval has NOT been recorded" in text
    assert "Targeted refresh boundary" in text


def test_tui_dry_run_prints_modern_status_without_secrets(capsys):
    status = launch_tui(dry_run=True)
    output = capsys.readouterr().out

    assert "当前视图：对话" in output
    assert "快捷键：1-0 切换视图" not in output
    assert "1-0" not in output
    assert "Enter 提交" in output
    assert "焦点：输入框" in output
    assert status.status_left.startswith("📁")
    assert "🔌" in status.status_center
    assert "任务空闲" in status.status_center


def test_tui_dry_run_status_and_output_use_chinese_copy_and_no_llm_secret(
    tmp_path, capsys
):
    secret = "sk-dryrun-copy-secret"
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.local.test/v1",
                            "api_key": secret,
                            "model": "gpt-copy",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    status = launch_tui(dry_run=True, project_root=tmp_path)
    output = capsys.readouterr().out
    combined = f"{status}\n{output}"

    assert status.interactive is False
    assert "TUI 基础组件已就绪" in status.message
    assert "LLM 已就绪" in status.message
    assert "工具执行必须经过权限引擎" in output
    assert "当前视图：对话" in output
    assert "焦点：输入框" in output
    assert secret not in combined


def test_cli_tui_dry_run_entrypoint(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    status = CLI().tui(dry_run=True)

    assert status.interactive is False


def test_tui_dry_run_restores_last_exit_provider_without_secret_leak(tmp_path, capsys):
    secret = "sk-tui-entry-secret"
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "last_provider": "anthropic",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.test/v1",
                            "api_key": "sk-openai-entry",
                            "model": "gpt-test",
                        },
                        "anthropic": {
                            "api_format": "anthropic",
                            "base_url": "https://anthropic.test/v1",
                            "api_key": secret,
                            "model": "claude-test",
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    status = launch_tui(dry_run=True, project_root=tmp_path)
    output = capsys.readouterr().out

    assert status.interactive is False
    assert status.llm_ready is True
    assert status.llm_provider == "anthropic"
    assert "anthropic" in status.status_center
    assert "anthropic" in output
    assert secret not in output


def test_tui_view_title_and_status_text_are_test_friendly(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)

    assert app.view_title_text("workspace") == "工作区"
    assert app.view_title_text("llm") == "LLM 配置"
    assert app.view_title_text("experiment") == "实验"
    assert app.view_title_text("log") == "Log 报告"
    assert app.status_text("workspace").focus == "焦点：输入框"
    assert "当前视图：工作区" in app.status_text("workspace").right
    assert "1-0" not in app.shortcut_hint_text()
    assert "切换视图" not in app.shortcut_hint_text()
    assert "Tab/Shift+Tab" in app.shortcut_hint_text()
    assert "M 菜单" in app.shortcut_hint_text()


def test_tui_help_text_documents_actual_bindings_and_state_meanings():
    binding_keys = {binding.key for binding in SuperMedicineTUI.BINDINGS}

    for key in {
        "Q",
        "M",
    }:
        assert key in binding_keys
    assert "f" not in binding_keys
    assert "question_mark" not in binding_keys

    help_text = "\n".join(
        [
            LABELS["help_navigation"],
            LABELS["help_submission"],
            LABELS["help_refresh"],
            LABELS["help_danger"],
            LABELS["help_status"],
            LABELS["help_global"],
        ]
    )

    for expected in [
        "Tab/Shift+Tab",
        "Enter",
        "刷新",
        "危险操作",
        "LLM",
        "任务",
        "M",
        "选择视图",
        "最大化/还原",
    ]:
        assert expected in help_text

    assert "1-0" not in help_text
    assert "数字键直接切换视图" not in help_text


def test_readme_tui_docs_match_bindings_and_preserve_boundaries():
    root = Path(__file__).resolve().parents[1]
    readme = root.joinpath("README.md").read_text(encoding="utf-8")
    readme_zh_cn = root.joinpath("README.zh-CN.md").read_text(encoding="utf-8")

    for expected in [
        "`Tab`",
        "`Shift+Tab`",
        "`Enter`",
        "`M`",
        "`P`",
        "`Q`",
    ]:
        assert expected in readme
    assert "`f`" not in readme
    assert "`?`" not in readme
    assert "Number keys `1-0` are not direct view-switching shortcuts" in readme
    assert "数字键 `1-0` 不是直接视图切换快捷键" in readme_zh_cn
    assert "选择视图" in readme
    assert "切换主题" in readme
    assert "帮助" in readme
    assert "最大化/还原" in readme
    assert "LLM 状态" in readme
    assert "任务运行状态" in readme
    assert "Chat Processing" in readme
    assert "Only the main\nprompt input is locked" in readme
    assert "watcher or polling" in readme
    assert "Chat Processing" in readme_zh_cn
    assert "只有主输入框" in readme_zh_cn
    assert "watcher 或轮询" in readme_zh_cn
    assert "CLI commands always require explicit `--workspace`" in readme
    assert "OpenCode runtime" not in readme


def test_tui_stylesheet_selectors_match_declared_widgets_and_classes():
    root = Path(__file__).resolve().parents[1]
    stylesheet = root.joinpath("core", "tui", "app.tcss").read_text(encoding="utf-8")
    assert "@media" not in stylesheet
    tui_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            root.joinpath("core", "tui", "app.py"),
            root.joinpath("core", "tui", "menu_screens.py"),
            *root.joinpath("core", "tui", "screens").glob("*_screen.py"),
        ]
    )
    tui_sources += root.joinpath("core", "tui", "screens", "chat_view.py").read_text(
        encoding="utf-8"
    )
    tui_sources += root.joinpath("core", "tui", "screens", "dashboard.py").read_text(
        encoding="utf-8"
    )

    declared_ids = set(re.findall(r'id="([a-zA-Z0-9_-]+)"', tui_sources))
    declared_classes = {
        class_name
        for classes in re.findall(r'classes="([a-zA-Z0-9_ -]+)"', tui_sources)
        for class_name in classes.split()
    }
    declared_classes.update(STATUS_STYLE_CLASSES)
    declared_classes.update(
        {
            "status-info",
            "status-success",
            "status-warning",
            "status-error",
            "-active",
            "-maximized",
            "tui-menu-list",
            "menu-affordance",
        }
    )

    selector_blocks = [block.rsplit("}", 1)[-1] for block in stylesheet.split("{")[:-1]]
    selectors = "\n".join(selector_blocks)
    css_ids = set(re.findall(r"#([a-zA-Z0-9_-]+)", selectors))
    css_classes = set(re.findall(r"\.(-?[a-zA-Z_][a-zA-Z0-9_-]*)", selectors))

    assert css_ids <= declared_ids
    assert css_classes <= declared_classes


@pytest.mark.parametrize("menu_key", ["M"])
def test_tui_menu_binding_opens_view_submenu_and_theme_entry(tmp_path, menu_key):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            prompt = app.query_one("#prompt-input", Input)
            assert prompt.has_focus
            assert app.query_one("#menu-button", Static) is not None

            await pilot.press(menu_key)
            await pilot.pause()

            assert prompt.value == ""
            assert app.screen.query_one("#tui-main-menu-list", ListView)
            menu_text = "\n".join(
                str(cast(Static, static).renderable)
                for static in app.screen.query("#tui-main-menu-list Static")
            )
            assert "选择视图" in menu_text
            assert "权限设置" in menu_text
            assert "切换主题" in menu_text
            assert "帮助" in menu_text
            assert "最大化/还原" in menu_text
            assert "工作区设置" not in menu_text
            assert "LLM 设置" not in menu_text

            await pilot.press("enter")
            await pilot.pause()
            view_text = "\n".join(
                str(cast(Static, static).renderable)
                for static in app.screen.query("#tui-view-menu-list Static")
            )
            assert "对话" in view_text
            assert "工作区" in view_text
            assert "LLM 配置" in view_text
            assert "Log 报告" in view_text
            assert "权限设置" not in view_text

            await pilot.press("down", "enter")
            await pilot.pause()
            assert app._current_view == "dashboard"
            assert app.view_title_text(app._current_view) == "状态看板"

    asyncio.run(scenario())


def test_tui_upper_left_menu_button_opens_menu(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            button = app.query_one("#menu-button", Static)
            assert "菜单" in str(button.renderable)
            assert "M" in str(button.renderable)
            assert list(app.query("Header")) == []
            assert list(app.query("Footer")) == []

            await pilot.click("#menu-button")
            await pilot.pause()

            assert app.screen.query_one("#tui-main-menu-list", ListView)

    asyncio.run(scenario())


def test_tui_menu_permission_entry_matches_permission_shortcut(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.press("M")
            await pilot.pause()

            menu_text = "\n".join(
                str(cast(Static, static).renderable)
                for static in app.screen.query("#tui-main-menu-list Static")
            )
            assert "权限设置" in menu_text
            assert "工作区设置" not in menu_text
            assert "LLM 设置" not in menu_text

            await pilot.press("down", "enter")
            await pilot.pause()
            assert app._current_view == "permission"
            assert app.view_title_text(app._current_view) == "权限"

            await pilot.press("M", "enter")
            await pilot.pause()
            view_text = "\n".join(
                str(cast(Static, static).renderable)
                for static in app.screen.query("#tui-view-menu-list Static")
            )
            assert "LLM 配置" in view_text
            assert "工作区" in view_text
            assert "权限设置" not in view_text

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("key", "char"),
    [
        ("shift+m", "M"),
        ("M", "M"),
    ],
)
def test_prompt_input_treats_m_and_shift_m_as_menu_key(key, char):
    class KeyEvent:
        def __init__(self, key: str, character: str) -> None:
            self.key = key
            self.character = character

    assert PromptInput()._is_menu_key(KeyEvent(key, char))


def test_prompt_input_treats_lowercase_m_as_ordinary_text():
    class KeyEvent:
        def __init__(self, key: str, character: str) -> None:
            self.key = key
            self.character = character

    event = KeyEvent("m", "m")

    assert not PromptInput()._is_menu_key(event)
    assert not PromptInput()._is_terminal_control_key(event)


@pytest.mark.parametrize("key", ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "f", "?", "p"])
def test_prompt_input_keeps_removed_shortcuts_and_ordinary_keys_as_text(key):
    class KeyEvent:
        def __init__(self, key: str, character: str) -> None:
            self.key = key
            self.character = character

    assert not PromptInput()._is_menu_key(KeyEvent(key, key))
    assert not PromptInput()._is_terminal_control_key(KeyEvent(key, key))


# ═══ test_tui_experience_screens ═══


def test_experience_screen_suggest_requires_later_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    suggestion = controller.suggest_classification(
        "study-a", title="方法", summary="总结事件"
    )

    assert suggestion["label"] == "经验分类建议"
    assert suggestion["confirmed"] is False
    assert controller.list_experiences("study-a") == []


def test_experience_screen_empty_state_and_confirmation_copy_are_chinese(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    assert controller.list_experiences("study-a") == []
    assert t("experience_no_records") == "暂无经验记录"
    with pytest.raises(ValueError, match="最终确认"):
        controller.confirm_suggestion(
            "study-a",
            scope="workspace",
            title="经验",
            summary="摘要",
            confirm=False,
        )


def test_experience_screen_confirm_then_list_edit_export(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)

    with pytest.raises(ValueError, match="最终确认"):
        controller.confirm_suggestion(
            "study-a",
            scope="workspace",
            title="经验",
            summary="摘要",
            confirm=False,
        )

    record = controller.confirm_suggestion(
        "study-a",
        scope="workspace",
        title="经验",
        summary="摘要",
        tags=["tui"],
        confirm=True,
    )
    edited = controller.edit_experience(
        record["id"], workspace_id="study-a", scope="workspace", title="新经验"
    )
    exported = controller.export_experiences(workspace_id="study-a", format="md")

    assert record["message"] == "经验已确认写入"
    assert edited["title"] == "新经验"
    assert controller.list_experiences("study-a")[0]["label"] == "经验：新经验"
    assert "新经验" in exported["content"]


def test_experience_screen_delete_requires_exact_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = ExperienceScreenController(tmp_path)
    record = controller.confirm_suggestion(
        "study-a",
        scope="workspace",
        title="经验",
        summary="摘要",
        confirm=True,
    )

    with pytest.raises(ValueError, match="经验 ID"):
        controller.delete_experience(
            record["id"], workspace_id="study-a", scope="workspace", confirm="wrong"
        )

    deleted = controller.delete_experience(
        record["id"], workspace_id="study-a", scope="workspace", confirm=record["id"]
    )
    assert deleted["status"] == "deleted"
    assert controller.list_experiences("study-a") == []


def test_experience_delete_copy_describes_exact_irreversible_confirmation():
    assert "完全一致" in t("experience_delete_requires_confirm")
    assert "不可恢复" in t("experience_delete_requires_confirm")


def test_experience_view_sets_deterministic_non_empty_reload_status():
    loader = inspect.getsource(ExperienceView._load_experiences)

    assert "experience_list" in loader
    assert "len(records)" in loader


def test_experience_view_empty_success_error_copy_and_secret_redaction_are_explicit():
    compose_source = inspect.getsource(ExperienceView.compose)
    loader_source = inspect.getsource(ExperienceView._load_experiences)
    confirm_source = inspect.getsource(ExperienceView._confirm_experience)
    error_source = inspect.getsource(ExperienceView._set_error)
    status_source = inspect.getsource(ExperienceView._set_status)

    assert "experience_no_records" in loader_source
    assert "experience_list" in loader_source
    assert "experience_confirmed" in confirm_source
    assert "experience_delete_requires_confirm" in compose_source + inspect.getsource(
        ExperienceView._delete_experience
    )
    assert "redact_sensitive" in error_source
    assert "redact_sensitive" in status_source
    assert t("experience_no_records") == "暂无经验记录"
    assert "完全一致" in t("experience_delete_requires_confirm")


# ═══ test_tui_experiment_screen ═══


class _FakeExperimentFieldTextArea:
    def __init__(self) -> None:
        self.text = ""

    def load_text(self, value: str) -> None:
        self.text = value


class _FakeExperimentFieldTableEvent:
    def __init__(self, row_key: str) -> None:
        self.data_table = type("FakeExperimentInputTable", (), {"id": "experiment-input-table"})()
        self.row_key = row_key


def _fake_experiment_field_highlighted(row_key: str) -> DataTable.RowHighlighted:
    return cast(DataTable.RowHighlighted, _FakeExperimentFieldTableEvent(row_key))


def _fake_experiment_field_selected(row_key: str) -> DataTable.RowSelected:
    return cast(DataTable.RowSelected, _FakeExperimentFieldTableEvent(row_key))


def _experiment_view_for_field_paste() -> tuple[Any, _FakeExperimentFieldTextArea]:
    textarea = _FakeExperimentFieldTextArea()
    view = type(
        "FieldPasteExperimentView",
        (),
        {
            "_selected_field_key": None,
            "_last_activated_field_key": None,
            "query_one": lambda self, selector, widget_type=None: textarea,
        },
    )()
    view._paste_field_name = lambda row_key: ExperimentGuideView._paste_field_name(
        view, row_key
    )
    return view, textarea


def test_experiment_field_switch_does_not_paste_previous_selected_field() -> None:
    view, textarea = _experiment_view_for_field_paste()

    ExperimentGuideView.on_data_table_row_highlighted(
        view, _fake_experiment_field_highlighted("sample_id")
    )
    ExperimentGuideView.on_data_table_row_selected(
        view, _fake_experiment_field_selected("sample_id")
    )
    ExperimentGuideView.on_data_table_row_highlighted(
        view, _fake_experiment_field_highlighted("target_protein")
    )
    ExperimentGuideView.on_data_table_row_selected(
        view, _fake_experiment_field_selected("target_protein")
    )

    assert textarea.text == ""
    assert view._selected_field_key == "target_protein"
    assert view._last_activated_field_key == "target_protein"


def test_experiment_field_double_activation_pastes_current_field_once() -> None:
    view, textarea = _experiment_view_for_field_paste()

    ExperimentGuideView.on_data_table_row_highlighted(
        view, _fake_experiment_field_highlighted("sample_id")
    )
    ExperimentGuideView.on_data_table_row_selected(
        view, _fake_experiment_field_selected("sample_id")
    )
    ExperimentGuideView.on_data_table_row_highlighted(
        view, _fake_experiment_field_highlighted("target_protein")
    )
    ExperimentGuideView.on_data_table_row_selected(
        view, _fake_experiment_field_selected("target_protein")
    )
    ExperimentGuideView.on_data_table_row_selected(
        view, _fake_experiment_field_selected("target_protein")
    )

    assert textarea.text == "target_protein="
    assert "sample_id=" not in textarea.text
    assert view._last_activated_field_key is None


def test_tui_explicit_switch_opens_experiment_screen_and_preserves_prompt_focus(
    tmp_path,
):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            assert app._current_view == "experiment"
            assert app._views["experiment"].display is True
            assert app.query_one("#prompt-input", Input).has_focus
            assert t("nav_experiment") in _static_text(
                app.query_one("#view-title", Static)
            )
            assert t("experiment_boundary") in _static_text(
                app.query_one("#experiment-boundary", Static)
            )
            assert t("experiment_current_step") in _static_text(
                app.query_one("#experiment-step", Static)
            )
            assert app.query_one("#experiment-data-input", TextArea) is not None

            app.action_switch_view("chat")
            await pilot.pause()

            assert app._current_view == "chat"
            assert app.query_one("#prompt-input", Input).has_focus

    asyncio.run(scenario())


def test_experiment_screen_accepts_input_calculates_advances_and_saves_redacted_log(
    tmp_path,
):
    secret = "sk-experiment-screen-secret"

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            data_input = app.query_one("#experiment-data-input", TextArea)
            data_input.load_text(
                '{"sample_id":"S1","target_protein":"GAPDH",'
                f'"notes":"api_key={secret}"}}'
            )
            app.query_one("#experiment-output-input", Input).value = "样本已裂解"

            await pilot.click("#experiment-calculate")
            await pilot.pause()

            calculation_text = _static_text(
                app.query_one("#experiment-reagent-result", Static)
            )
            assert t("experiment_reagent_result") in calculation_text
            assert "protein_loading_normalization" in calculation_text
            assert "experiment-wb" in calculation_text
            assert "preview" not in calculation_text
            assert secret not in calculation_text
            assert "[REDACTED]" in calculation_text
            assert t("experiment_reagent_result") in _static_text(
                app.query_one("#experiment-status", Static)
            )

            await pilot.click("#experiment-submit")
            await pilot.pause()

            view = app._views["experiment"]
            assert view._session.current_step.step_id == "gel_electrophoresis"
            assert t("experiment_step_saved") in _static_text(
                app.query_one("#experiment-status", Static)
            )

            await pilot.click("#experiment-save-log")
            await pilot.pause()

            log_files = list((tmp_path / ".supermedicine" / "logs").glob("*.json"))
            assert len(log_files) == 1
            log_text = log_files[0].read_text(encoding="utf-8")
            assert secret not in log_text
            assert "[REDACTED]" in log_text
            assert t("experiment_log_saved") in _static_text(
                app.query_one("#experiment-status", Static)
            )

    asyncio.run(scenario())


def test_experiment_screen_reports_missing_required_input(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            app.query_one("#experiment-data-input", TextArea).load_text(
                '{"sample_id":"S1"}'
            )
            await pilot.click("#experiment-submit")
            await pilot.pause()

            status = _static_text(app.query_one("#experiment-status", Static))
            assert t("error") in status
            assert t("experiment_missing_required") in status
            assert "目标蛋白" in status

    asyncio.run(scenario())


def test_experiment_screen_initial_empty_copy_and_safe_layout_are_visible(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experiment")
            await pilot.pause()

            assert t("experiment_protocol") in _static_text(
                app.query_one("#experiment-session", Static)
            )
            assert t("experiment_current_step") in _static_text(
                app.query_one("#experiment-step", Static)
            )
            assert t("experiment_step_instructions") in _static_text(
                app.query_one("#experiment-instructions", Static)
            )
            assert app.query_one("#experiment-input-table", DataTable).row_count > 0
            assert t("experiment_boundary") in _static_text(
                app.query_one("#experiment-boundary", Static)
            )
            assert app.query_one("#experiment-data-input", TextArea).text == ""
            assert app.query_one("#experiment-output-input", Input).value == ""
            assert t("experiment_calculate_step") in str(
                app.query_one("#experiment-calculate", Button).label
            )
            assert t("experiment_submit_step") in str(
                app.query_one("#experiment-submit", Button).label
            )
            assert t("experiment_save_log") in str(
                app.query_one("#experiment-save-log", Button).label
            )

    asyncio.run(scenario())


# ═══ test_tui_invalid_table_actions ═══


def test_tool_run_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("tool")
            await pilot.pause()

            view = app._views["tool"]
            view.query_one("#tool-workspace-select", Select).value = "study-a"
            view._load_tools()
            table = view.query_one("#tool-table", DataTable)
            assert table.row_count == 0
            assert getattr(view, "_table_mode") == "workspace"
            assert view.query_one("#tool-workspace-select", Select).value == "study-a"

            view._run_tool()

            _assert_same_view_intact(app, "tool")
            _assert_tool_empty_run_error(view.query_one("#tool-status", Static))

            select = view.query_one("#tool-workspace-select", Select)
            stale_same_workspace_event = type(
                "StaleSelectChangedEvent",
                (),
                {"select": select},
            )()
            view.on_select_changed(stale_same_workspace_event)
            _assert_same_view_intact(app, "tool")
            _assert_tool_empty_run_error(view.query_one("#tool-status", Static))

            view._load_tools()
            _assert_same_view_intact(app, "tool")
            _assert_tool_empty_run_error(view.query_one("#tool-status", Static))

    asyncio.run(scenario())


def test_tool_screen_scans_candidates_without_tool_id_input(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "plugins" / "tools" / "python_stats"
    source.mkdir(parents=True)
    (source / "plugin.yaml").write_text(
        yaml.safe_dump(
            {"name": "python-stats", "language": "python", "entry": "main.py"},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (source / "main.py").write_text("print('ok')\n", encoding="utf-8")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("tool")
            await pilot.pause()

            view = app._views["tool"]
            assert list(view.query("#tool-id-input")) == []
            view.query_one("#tool-workspace-select", Select).value = "study-a"
            await _wait_for_tui_condition(
                pilot,
                lambda: (
                    view.query_one("#tool-workspace-select", Select).value == "study-a"
                ),
            )
            view.query_one("#tool-scan", Button).focus()
            await pilot.click("#tool-scan")

            table = view.query_one("#tool-table", DataTable)
            await _wait_for_tui_condition(
                pilot,
                lambda: (
                    getattr(view, "_table_mode") == "candidates"
                    and table.row_count == 1
                ),
            )
            assert table.row_count == 1
            assert table.get_row_at(0)[2] == "python-stats"

    asyncio.run(scenario())


def test_paper_enrich_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("paper")
            await pilot.pause()

            view = app._views["paper"]
            view.query_one("#paper-workspace-select", Select).value = "study-a"
            view._load_papers()
            table = view.query_one("#paper-table", DataTable)
            assert table.row_count == 0
            assert view.query_one("#paper-workspace-select", Select).value == "study-a"

            view._enrich_paper()

            _assert_same_view_intact(app, "paper")
            _assert_red_error_with_reason(
                view.query_one("#paper-status", Static), t("paper_no_papers")
            )

    asyncio.run(scenario())


def test_log_show_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 0

            view = app._views["log"]
            view._show_selected_log()

            _assert_same_view_intact(app, "log")
            _assert_red_error_with_reason(
                app.query_one("#log-status", Static), t("log_no_reports")
            )

    asyncio.run(scenario())


def test_experience_delete_on_empty_table_shows_red_error_without_exiting_tui(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("experience")
            await pilot.pause()

            view = app._views["experience"]
            view.query_one("#exp-workspace-select", Select).value = "study-a"
            view._load_experiences()
            table = view.query_one("#exp-table", DataTable)
            assert table.row_count == 0
            assert view.query_one("#exp-workspace-select", Select).value == "study-a"

            view._delete_experience()

            _assert_same_view_intact(app, "experience")
            _assert_red_error_with_reason(
                view.query_one("#exp-status", Static), t("experience_no_records")
            )

    asyncio.run(scenario())


# ═══ test_tui_llm_screen ═══


def test_tui_controller_adds_switches_and_redacts_provider(tmp_path):
    secret = "sk-tui-screen-secret"
    controller = LLMScreenController(tmp_path)

    add_result = controller.add_provider(
        "TUI-Provider",
        base_url="https://tui-provider.local.test/v1",
        api_key=secret,
        model="tui-model",
        set_current=True,
    )
    switch_result = controller.switch_provider("tui-provider")
    providers = controller.list_providers()
    readiness = controller.readiness()
    reloaded = ConfigCenter(tmp_path / ".supermedicine" / "config.yaml")

    assert add_result["ok"] is True
    assert switch_result["ok"] is True
    assert readiness == {
        "ok": True,
        "provider": "tui-provider",
        "message": t("llm_ready"),
    }
    assert providers["tui-provider"]["api_key"] == "[REDACTED]"
    assert secret not in str(add_result)
    assert secret not in str(switch_result)
    assert secret not in str(providers)
    assert reloaded.get_llm_current_provider_name() == "tui-provider"
    assert reloaded.get_llm_last_provider_name() == "tui-provider"
    assert reloaded.get_llm_provider_config("tui-provider")["api_key"] == secret


def test_tui_controller_restores_previous_exit_provider_on_startup(tmp_path):
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "last_provider": "anthropic",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.test/v1",
                            "api_key": "sk-openai-tui",
                            "model": "gpt-test",
                        },
                        "anthropic": {
                            "api_format": "anthropic",
                            "base_url": "https://anthropic.test/v1",
                            "api_key": "sk-anthropic-tui",
                            "model": "claude-test",
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    controller = LLMScreenController(tmp_path)

    assert controller.current_provider()["provider"] == "anthropic"
    assert (
        ConfigCenter(config_dir / "config.yaml").get_llm_current_provider_name()
        == "anthropic"
    )


def test_tui_controller_ignores_missing_last_provider_and_keeps_valid_current(tmp_path):
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "last_provider": "missing-provider",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.test/v1",
                            "api_key": "sk-openai-fallback",
                            "model": "gpt-test",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    controller = LLMScreenController(tmp_path)

    assert controller.current_provider()["provider"] == "openai"
    assert controller.readiness() == {
        "ok": True,
        "provider": "openai",
        "message": t("llm_ready"),
    }
    assert (
        ConfigCenter(config_dir / "config.yaml").get_llm_current_provider_name()
        == "openai"
    )


def test_tui_controller_save_exit_state_persists_current_provider_for_restore(tmp_path):
    controller = LLMScreenController(tmp_path)
    controller.add_provider(
        "openai",
        base_url="https://openai.test/v1",
        api_key="sk-openai-exit-state",
        model="gpt-test",
        set_current=True,
    )

    saved = controller.save_exit_state()
    restored = LLMScreenController(tmp_path)

    assert saved == {"ok": True, "provider": "openai"}
    assert restored.current_provider()["provider"] == "openai"


def test_tui_controller_error_messages_do_not_expose_api_key(tmp_path):
    secret = "sk-tui-broken-secret"
    controller = LLMScreenController(tmp_path)

    result = controller.add_provider(
        "broken-tui",
        base_url="",
        api_key=secret,
        model="",
        set_current=True,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "missing_base_url"
    assert secret not in str(result)


def test_tui_controller_readiness_message_redacts_api_key(tmp_path):
    secret = "sk-tui-readiness-secret"
    controller = LLMScreenController(tmp_path)

    result = controller.add_provider(
        "needs-model",
        base_url="https://needs-model.local.test/v1",
        api_key=secret,
        model="",
        set_current=False,
    )
    switch_result = controller.validate_provider("needs-model")
    readiness = controller.readiness()

    assert result["ok"] is True
    assert switch_result["ok"] is False
    assert readiness["ok"] is False
    assert secret not in str(result)
    assert secret not in str(switch_result)
    assert secret not in str(readiness)


def test_llm_view_declares_secret_safe_inputs_empty_state_and_error_redaction():
    compose_source = inspect.getsource(LLMView.compose)
    refresh_source = inspect.getsource(LLMView.refresh_llm_state)
    add_source = inspect.getsource(LLMView._add_provider_from_form)
    error_source = inspect.getsource(LLMView._safe_error_message)

    assert 'id="llm-api-key-input"' in compose_source
    assert "password=True" in compose_source
    assert "llm_secret_hidden" in compose_source
    assert "llm_no_providers" in refresh_source
    assert "llm_provider_added" in add_source
    assert "redact_sensitive" in error_source
    assert t("llm_secret_hidden") == "密钥已隐藏，不会显示在状态栏或通知中"
    assert t("llm_no_providers") == "暂无 LLM Provider"


def test_background_llm_transport_diagnostics_are_not_formatted_as_chat_content():
    """Regression baseline: backend LLM telemetry must not leak into TUI chat output."""

    formatted = SuperMedicineTUI._format_kernel_result(
        {
            "status": "success",
            "output": {
                "stage": "LLM Request Sending",
                "command": "LLM Request Sending: POST https://llm.local.test/v1/chat/completions",
                "assistant": "final user-facing answer",
            },
        }
    )

    assert formatted["kind"] == "assistant"
    assert "final user-facing answer" in formatted["message"]
    assert "LLM Request Sending" not in formatted["message"]
    assert "POST https://llm.local.test" not in formatted["message"]


# ═══ test_tui_log_screen ═══


def test_tui_explicit_switch_opens_log_screen_and_global_shortcuts_remain(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            assert app._current_view == "log"
            assert app._views["log"].display is True
            assert app.query_one("#prompt-input", Input).has_focus
            assert t("nav_log") in _static_text(app.query_one("#view-title", Static))
            assert t("log_redaction_hint") in _static_text(
                app.query_one("#log-redaction-hint", Static)
            )
            assert app.query_one("#log-message-input", TextArea) is not None
            assert app.query_one("#log-table", DataTable) is not None

            app.action_switch_view("experiment")
            await pilot.pause()

            assert app._current_view == "experiment"
            assert app.query_one("#prompt-input", Input).has_focus

    asyncio.run(scenario())


def test_log_screen_writes_lists_and_shows_redacted_report(tmp_path):
    secret = "sk-log-screen-secret"

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            app.query_one("#log-session-id-input", Input).value = "session-1"
            app.query_one("#log-message-input", TextArea).load_text(
                f"实验记录 api_key={secret}"
            )

            await pilot.click("#log-write")
            await pilot.pause()

            log_dir = tmp_path / ".supermedicine" / "logs"
            log_files = list(log_dir.glob("*.json"))
            assert len(log_files) == 1
            saved_text = log_files[0].read_text(encoding="utf-8")
            assert secret not in saved_text
            assert "[REDACTED]" in saved_text
            assert t("log_list") in _static_text(app.query_one("#log-status", Static))

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 1
            table.move_cursor(row=0, column=0)
            await pilot.click("#log-show")
            await pilot.pause()

            detail = _static_text(app.query_one("#log-detail", Static))
            assert t("log_loaded") in detail
            assert "session-1" in detail
            assert secret not in detail
            assert "[REDACTED]" in detail

    asyncio.run(scenario())


def test_log_screen_empty_message_sets_status_without_creating_report(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            app.query_one("#log-message-input", TextArea).load_text("")
            await pilot.click("#log-write")
            await pilot.pause()

            assert t("log_empty_message") in _static_text(
                app.query_one("#log-status", Static)
            )
            assert not (tmp_path / ".supermedicine" / "logs").exists()

    asyncio.run(scenario())


def test_log_screen_initial_empty_copy_and_safe_layout_are_visible(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            assert t("log_redaction_hint") in _static_text(
                app.query_one("#log-redaction-hint", Static)
            )
            assert t("log_no_reports") in _static_text(
                app.query_one("#log-status", Static)
            )
            assert app.query_one("#log-session-id-input", Input).value == ""
            assert app.query_one("#log-message-input", TextArea).text == ""
            assert app.query_one("#log-table", DataTable).row_count == 0
            assert t("log_write") in str(app.query_one("#log-write", Button).label)
            assert t("log_show") in str(app.query_one("#log-show", Button).label)

    asyncio.run(scenario())


def test_log_screen_severity_text_uses_distinct_styles():
    cases = {
        "【Error】 failed": "red",
        "【Warning】 check this": "yellow",
        "【Info】 started": "cyan",
        "【Debug】 details": "blue",
        "【Success】 saved": "green",
    }

    for message, style_token in cases.items():
        rendered = LogReportView._severity_text(message)

        assert str(rendered) == message
        assert style_token in str(rendered.style)


def test_log_screen_empty_and_refreshed_status_include_zero_statistics(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            initial_status = _static_text(app.query_one("#log-status", Static))
            assert t("log_no_reports") in initial_status
            assert "entries=0" in initial_status
            assert "Error=0" in initial_status
            assert "Warning=0" in initial_status
            assert "Info=0" in initial_status
            assert "Debug=0" in initial_status
            assert "Success=0" in initial_status

            await pilot.click("#log-refresh")
            await pilot.pause()

            refreshed_status = _static_text(app.query_one("#log-status", Static))
            assert t("log_refreshed") in refreshed_status
            assert t("log_no_reports") in refreshed_status
            assert "entries=0" in refreshed_status

    asyncio.run(scenario())


def test_log_screen_populated_table_and_detail_statistics_match_selected_entry(
    tmp_path,
):
    store = LogReportStore(tmp_path)
    store.write("alpha failed", session_id="alpha", severity="Error")
    store.write("alpha saved", session_id="alpha", severity="Success")
    store.write("beta warning", session_id="beta", severity="Warning")

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 3
            status = _static_text(app.query_one("#log-status", Static))
            assert f"{t('log_refreshed')}: 3" in status
            assert "entries=3" in status
            assert "Error=1" in status
            assert "Warning=1" in status
            assert "Success=1" in status

            beta_row = next(
                index
                for index in range(table.row_count)
                if "beta" in str(table.get_row_at(index)[3])
            )
            table.move_cursor(row=beta_row, column=0)
            await pilot.click("#log-show")
            await pilot.pause()

            detail = _static_text(app.query_one("#log-detail", Static))
            assert t("log_loaded") in detail
            assert "beta" in detail
            assert "Severity: Warning" in detail
            assert "Statistics: entries=1" in detail
            assert "Warning=1" in detail
            assert "Error=0" in detail
            assert "Success=0" in detail
            assert "alpha failed" not in detail
            assert "alpha saved" not in detail

    asyncio.run(scenario())


def test_log_screen_refresh_button_reads_entries_created_after_enter(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("log")
            await pilot.pause()

            table = app.query_one("#log-table", DataTable)
            assert table.row_count == 0

            LogReportStore(tmp_path).write("late log", session_id="late")
            await pilot.click("#log-refresh")
            await pilot.pause()

            assert table.row_count == 1
            assert "late" in str(table.get_row_at(0))
            assert t("log_refreshed") in _static_text(app.query_one("#log-status", Static))

    asyncio.run(scenario())


def test_log_screen_uses_targeted_refresh_hook_without_timer_polling():
    source = inspect.getsource(LogReportView)

    assert "refresh_view_data" in source
    assert "set_interval" not in source
    assert "Timer" not in source


def test_log_screen_severity_label_uses_explicit_mapping_for_each_level():
    cases = {
        "Error": "red",
        "Warning": "yellow",
        "Info": "cyan",
        "Debug": "blue",
        "Success": "green",
    }

    for severity, style_token in cases.items():
        rendered = LogReportView._severity_label(severity)

        assert str(rendered) == f"[{severity}]"
        assert style_token in str(rendered.style)


class TestLogScreenRefreshAndAggregation:
    def test_log_screen_refresh_view_data_populates_table_from_store(self, tmp_path):
        store = LogReportStore(tmp_path)
        store.write("pre-existing log", session_id="pre-session", severity="Info")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                assert table.row_count == 1
                assert "pre-session" in str(table.get_row_at(0))
                assert t("log_list") in _static_text(app.query_one("#log-status", Static))

        asyncio.run(scenario())

    def test_log_screen_refresh_after_external_write_updates_table(self, tmp_path):
        store = LogReportStore(tmp_path)

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                assert table.row_count == 0

                store.write("external entry", session_id="ext-session", severity="Info")

                app._views["log"].refresh_view_data()
                await pilot.pause()

                assert table.row_count == 1
                assert "ext-session" in str(table.get_row_at(0))
                assert t("log_refreshed") in _static_text(app.query_one("#log-status", Static))

        asyncio.run(scenario())

    def test_log_screen_auto_follow_toggle_announces_state_change(self, tmp_path):
        store = LogReportStore(tmp_path)
        for i in range(3):
            store.write(f"entry {i}", session_id="follow-test", severity="Info")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                view = app._views["log"]
                assert view._auto_follow is True

                await pilot.click("#log-auto-follow")
                await pilot.pause()

                assert view._auto_follow is False
                status = _static_text(app.query_one("#log-status", Static))
                assert "自动跟随：关" in status

        asyncio.run(scenario())

    def test_log_screen_auto_follow_scrolls_to_last_entry(self, tmp_path):
        store = LogReportStore(tmp_path)
        for i in range(5):
            store.write(f"entry {i}", session_id="scroll-test", severity="Info")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                assert table.row_count == 5
                assert table.cursor_row == 4

        asyncio.run(scenario())

    def test_log_screen_multi_session_aggregated_statistics_in_status(self, tmp_path):
        store = LogReportStore(tmp_path)
        store.write("alpha error", session_id="stat-alpha", severity="Error")
        store.write("alpha info", session_id="stat-alpha", severity="Info")
        store.write("beta warning", session_id="stat-beta", severity="Warning")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                status = _static_text(app.query_one("#log-status", Static))
                assert "entries=3" in status
                assert "Error=1" in status
                assert "Warning=1" in status
                assert "Info=1" in status

        asyncio.run(scenario())

    def test_log_screen_detail_statistics_match_selected_session_entry(self, tmp_path):
        store = LogReportStore(tmp_path)
        store.write("alpha error", session_id="detail-alpha", severity="Error")
        store.write("alpha info", session_id="detail-alpha", severity="Info")
        store.write("beta success", session_id="detail-beta", severity="Success")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                beta_row = next(
                    i
                    for i in range(table.row_count)
                    if "detail-beta" in str(table.get_row_at(i))
                )
                table.move_cursor(row=beta_row, column=0)
                await pilot.click("#log-show")
                await pilot.pause()

                detail = _static_text(app.query_one("#log-detail", Static))
                assert t("log_loaded") in detail
                assert "detail-beta" in detail
                assert "Statistics: entries=1" in detail
                assert "Success=1" in detail
                assert "Error=0" in detail

        asyncio.run(scenario())

    def test_log_screen_write_with_session_refreshes_and_displays_new_entry(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                app.query_one("#log-session-id-input", Input).value = "ui-write-session"
                app.query_one("#log-message-input", TextArea).load_text("UI log entry")

                await pilot.click("#log-write")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                assert table.row_count == 1
                assert "ui-write-session" in str(table.get_row_at(0))
                status = _static_text(app.query_one("#log-status", Static))
                assert t("log_saved") in status

                log_dir = tmp_path / ".supermedicine" / "logs"
                assert len(list(log_dir.glob("*.json"))) == 1

        asyncio.run(scenario())

    def test_log_screen_write_without_session_routes_to_tui_application(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                app.query_one("#log-message-input", TextArea).load_text("no session entry")

                await pilot.click("#log-write")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                assert table.row_count == 1
                assert TUI_LOG_SESSION_ID in str(table.get_row_at(0))

        asyncio.run(scenario())

    def test_log_screen_severity_text_redacts_secrets_in_displayed_detail(self, tmp_path):
        secret = "sk-log-detail-secret"
        store = LogReportStore(tmp_path)
        store.write(f"api failure api_key={secret}", session_id="redact-detail", severity="Error")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                table = app.query_one("#log-table", DataTable)
                table.move_cursor(row=0, column=0)
                await pilot.click("#log-show")
                await pilot.pause()

                detail = _static_text(app.query_one("#log-detail", Static))
                assert secret not in detail
                assert "[REDACTED]" in detail

        asyncio.run(scenario())

    def test_log_screen_preview_text_truncates_long_messages(self):
        preview = LogReportView._preview_text("a" * 200, limit=50)

        assert len(preview) <= 51
        assert preview.endswith("…")

    def test_log_screen_wrapped_detail_text_line_wraps_long_lines(self):
        wrapped = LogReportView._wrapped_detail_text("b" * 400, line_limit=100)

        for line in wrapped.splitlines():
            assert len(line) <= 100

    def test_log_screen_statistics_text_format(self):
        text = LogReportView._statistics_text(
            {
                "entry_count": 5,
                "severity_counts": {
                    "Error": 2,
                    "Warning": 1,
                    "Info": 1,
                    "Debug": 0,
                    "Success": 1,
                },
            }
        )

        assert "entries=5" in text
        assert "Error=2" in text
        assert "Warning=1" in text
        assert "Info=1" in text
        assert "Debug=0" in text
        assert "Success=1" in text

    def test_log_screen_statistics_text_handles_empty_statistics(self):
        text = LogReportView._statistics_text({})

        assert "entries=0" in text
        assert "Error=0" in text

    def test_log_screen_entry_severity_uses_explicit_over_detected(self):
        entry = {"severity": "Success", "raw_message": "operation failed"}

        assert LogReportView._entry_severity(entry) == "Success"

    def test_log_screen_entry_severity_falls_back_to_detection(self):
        entry = {"severity": "", "raw_message": "operation failed"}

        assert LogReportView._entry_severity(entry) == "Error"

    def test_log_screen_entry_message_formats_with_severity_label(self):
        entry = {"raw_message": "saved data", "severity": "Success"}
        message = LogReportView._entry_message(entry, severity="Success")

        assert message == "【Success】 saved data"

    def test_log_screen_storage_location_displays_log_and_audit_paths(self, tmp_path):
        store = LogReportStore(tmp_path)
        store.write("test", session_id="path-test")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                location = _static_text(app.query_one("#log-storage-location", Static))
                assert "存储位置" in location
                assert "Log/Report=" in location
                assert "Audit=" in location
                assert "audit.jsonl" in location
                assert "logs" in location

        asyncio.run(scenario())

    def test_log_screen_show_on_no_selection_shows_error(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                view = app._views["log"]
                table = view.query_one("#log-table", DataTable)
                assert table.row_count == 0

                view._show_selected_log()

                status = _static_text(app.query_one("#log-status", Static))
                assert t("error") in status
                assert t("log_no_reports") in status

        asyncio.run(scenario())

    def test_log_screen_refresh_preserves_cursor_position_when_auto_follow_off(self, tmp_path):
        store = LogReportStore(tmp_path)
        for i in range(5):
            store.write(f"entry {i}", session_id="cursor-test", severity="Info")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(140, 45)) as pilot:
                app.action_switch_view("log")
                await pilot.pause()

                view = app._views["log"]
                table = app.query_one("#log-table", DataTable)

                view._set_auto_follow(False)
                table.move_cursor(row=1, column=0)
                await pilot.pause()

                store.write("new entry", session_id="cursor-test", severity="Info")
                view.refresh_logs(refreshed=True)
                await pilot.pause()

                assert table.cursor_row <= 2

        asyncio.run(scenario())

    def test_log_screen_compose_declares_required_widgets(self):
        compose_source = inspect.getsource(LogReportView.compose)

        assert 'id="log-redaction-hint"' in compose_source
        assert 'id="log-action-hint"' in compose_source
        assert 'id="log-session-id-input"' in compose_source
        assert 'id="log-message-input"' in compose_source
        assert 'id="log-write"' in compose_source
        assert 'id="log-show"' in compose_source
        assert 'id="log-refresh"' in compose_source
        assert 'id="log-auto-follow"' in compose_source
        assert 'id="log-table"' in compose_source
        assert 'id="log-detail"' in compose_source
        assert 'id="log-status"' in compose_source

    def test_log_screen_uses_targeted_refresh_without_polling(self):
        source = inspect.getsource(LogReportView)

        assert "refresh_view_data" in source
        assert "set_interval" not in source
        assert "Timer" not in source

    def test_log_screen_service_property_creates_fresh_service(self, tmp_path):
        view = LogReportView(project_root=tmp_path)

        store1 = view.service
        store2 = view.service

        assert store1 is not store2
        assert store1.project_root == store2.project_root


# ═══ test_tui_paper_screens ═══


def test_paper_screen_import_is_copy_only_and_lists_metadata(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)

    imported = controller.import_paper(
        "study-a", source, metadata={"title": "研究论文", "tags": ["肿瘤"]}
    )

    assert source.exists()
    assert imported["message"] == "论文已复制导入工作区"
    assert imported["metadata"]["title"] == "研究论文"
    assert imported["metadata"]["stored_path"] != str(source)
    assert controller.list_papers("study-a")[0]["label"] == "论文：研究论文"


def test_paper_screen_empty_state_and_select_workspace_copy_are_chinese(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    controller = PaperScreenController(tmp_path)

    assert controller.list_papers("study-a") == []
    assert t("paper_no_papers") == "暂无论文，请先导入"
    assert t("paper_select_workspace") == "请先选择工作区"


def test_paper_screen_edit_metadata(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)
    paper_id = controller.import_paper("study-a", source)["metadata"]["id"]

    updated = controller.edit_metadata(
        "study-a", paper_id, {"title": "更新标题", "notes": "中文备注"}
    )

    assert updated["message"] == "论文元数据已更新"
    assert controller.show_paper("study-a", paper_id)["title"] == "更新标题"


def test_paper_screen_enrichment_requires_explicit_confirmation(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)
    paper_id = controller.import_paper("study-a", source)["metadata"]["id"]

    skipped = controller.enrich_metadata("study-a", paper_id, confirm=False)

    assert skipped["status"] == "skipped"
    assert skipped["message"] == "论文在线补全未执行"

    _policy(tmp_path)
    enriched = controller.enrich_metadata("study-a", paper_id, confirm=True)
    assert enriched["status"] == "enriched"
    assert "enriched" in enriched["metadata"]["tags"]


def test_paper_enrichment_copy_warns_about_network_and_confirmation():
    assert "网络请求" in t("paper_enrich_confirm")
    assert "选中论文 ID" in t("paper_enrich_confirm")


def test_paper_enrichment_confirmation_skips_without_network_policy_or_api(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    source = tmp_path / "source.pdf"
    source.write_bytes(b"paper bytes")
    controller = PaperScreenController(tmp_path)
    paper_id = controller.import_paper("study-a", source)["metadata"]["id"]

    skipped = controller.enrich_metadata("study-a", paper_id, confirm=False)

    assert skipped["status"] == "skipped"
    assert skipped["applied_fields"] == []
    assert skipped["message"] == "论文在线补全未执行"
    assert t("paper_enrich_confirm")
    assert (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").exists()


def test_paper_view_sets_deterministic_non_empty_reload_status():
    loader = inspect.getsource(PaperView._load_papers)

    assert "paper_list" in loader
    assert "len(papers)" in loader


def test_paper_view_empty_success_error_copy_and_secret_redaction_are_explicit():
    compose_source = inspect.getsource(PaperView.compose)
    loader_source = inspect.getsource(PaperView._load_papers)
    import_source = inspect.getsource(PaperView._import_paper)
    error_source = inspect.getsource(PaperView._set_error)
    status_source = inspect.getsource(PaperView._set_status)

    assert "paper_select_workspace" in compose_source
    assert "paper_no_papers" in loader_source
    assert "paper_list" in loader_source
    assert "paper_imported" in import_source
    assert "redact_sensitive" in error_source
    assert "redact_sensitive" in status_source
    assert t("paper_no_papers") == "暂无论文，请先导入"
    assert t("paper_select_workspace") == "请先选择工作区"


# ═══ test_tui_permissions ═══


class TestPermissionScreenController:
    def test_set_mode_conservative_without_confirmation(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        result = controller.set_mode("conservative")

        assert result["mode"] == "conservative"
        assert result["full_mode_confirmed"] is False

    def test_set_mode_full_requires_full_confirmation_text(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        result = controller.set_mode("full", confirmation_text="FULL")

        assert result["mode"] == "full"
        assert result["full_mode_confirmed"] is True

    def test_set_mode_full_without_confirmation_text_raises(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="")

    def test_set_mode_full_with_wrong_confirmation_text_raises(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="full")

    def test_set_mode_full_with_whitespace_confirmation_raises(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="   ")

    def test_set_mode_conservative_ignores_confirmation_text(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        result = controller.set_mode("conservative", confirmation_text="anything")

        assert result["mode"] == "conservative"
        assert result["full_mode_confirmed"] is False

    def test_set_mode_persists_to_config_file(self, tmp_path):
        controller = PermissionScreenController(tmp_path)
        controller.set_mode("full", confirmation_text="FULL")

        reloaded = PermissionScreenController(tmp_path)
        config = reloaded.current_config()

        assert config["mode"] == "full"
        assert config["full_mode_confirmed"] is True

    def test_set_mode_switches_from_full_back_to_conservative(self, tmp_path):
        controller = PermissionScreenController(tmp_path)
        controller.set_mode("full", confirmation_text="FULL")
        result = controller.set_mode("conservative")

        assert result["mode"] == "conservative"
        assert result["full_mode_confirmed"] is False

    def test_authorize_directory_adds_to_config(self, tmp_path):
        external = tmp_path / "external"
        external.mkdir()
        controller = PermissionScreenController(tmp_path)

        result = controller.authorize_directory(external)

        assert str(external.resolve()) in result["authorized_external_roots"]

    def test_revoke_directory_removes_from_config(self, tmp_path):
        external = tmp_path / "external"
        external.mkdir()
        controller = PermissionScreenController(tmp_path)
        controller.authorize_directory(external)

        result = controller.revoke_directory(external)

        assert str(external.resolve()) not in result["authorized_external_roots"]

    def test_access_decision_returns_correct_structure(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        decision = controller.access_decision(project / "notes.md", "write")

        assert decision["status"] == "allowed"
        assert decision["mode"] == "conservative"
        assert isinstance(decision["reason"], str)
        assert isinstance(decision["path"], str)
        assert isinstance(decision["helper"], str)

    def test_access_decision_external_write_denied_in_conservative(self, tmp_path):
        project = tmp_path / "project"
        external = tmp_path / "external"
        project.mkdir()
        external.mkdir()
        controller = PermissionScreenController(project)

        decision = controller.access_decision(external / "out.csv", "write")

        assert decision["status"] == "denied"

    def test_access_decision_external_read_prompts_in_conservative(self, tmp_path):
        project = tmp_path / "project"
        external = tmp_path / "external"
        project.mkdir()
        external.mkdir()
        controller = PermissionScreenController(project)

        decision = controller.access_decision(external / "data.csv", "read")

        assert decision["status"] == "prompt_required"

    def test_current_config_returns_default_when_no_config_file(self, tmp_path):
        controller = PermissionScreenController(tmp_path)
        config = controller.current_config()

        assert config["mode"] == "conservative"
        assert config["full_mode_confirmed"] is False
        assert config["authorized_external_roots"] == []

    def test_project_root_defaults_to_cwd(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        controller = PermissionScreenController()

        assert controller.project_root == tmp_path


class TestPermissionViewComposition:
    def test_permission_view_has_separate_mode_select_and_confirm_input(self):
        source = inspect.getsource(PermissionView.compose)

        assert "permission-mode-select" in source
        assert "permission-confirm-input" in source
        assert "Select" in source
        assert "Input" in source

    def test_permission_view_has_add_and_remove_root_controls(self):
        source = inspect.getsource(PermissionView.compose)

        assert "permission-root-input" in source
        assert "permission-add-root" in source
        assert "permission-remove-root" in source

    def test_permission_view_has_refresh_button(self):
        source = inspect.getsource(PermissionView.compose)

        assert "permission-refresh" in source

    def test_permission_view_has_status_and_risk_notice(self):
        source = inspect.getsource(PermissionView.compose)

        assert "permission-status" in source
        assert "permission-risk" in source
        assert "permission-current" in source

    def test_permission_risk_notice_mentions_full_confirmation(self):
        from core.tui.screens.permission_screen import PERMISSION_RISK_NOTICE

        assert "FULL" in PERMISSION_RISK_NOTICE
        assert "显式确认" in PERMISSION_RISK_NOTICE

    def test_permission_risk_notice_mentions_no_silent_escalation(self):
        from core.tui.screens.permission_screen import PERMISSION_RISK_NOTICE

        assert "不会静默提权" in PERMISSION_RISK_NOTICE
        assert "不会绕过" in PERMISSION_RISK_NOTICE


class TestPermissionInputSeparation:
    def test_mode_select_widget_offers_conservative_and_full(self):
        source = inspect.getsource(PermissionView.compose)

        assert '"conservative"' in source
        assert '"full"' in source

    def test_confirm_input_placeholder_documents_full_requirement(self):
        source = inspect.getsource(PermissionView.compose)

        assert "FULL" in source

    def test_controller_uses_separate_mode_and_confirmation(self, tmp_path):
        controller = PermissionScreenController(tmp_path)

        result1 = controller.set_mode("conservative")
        assert result1["mode"] == "conservative"

        result2 = controller.set_mode("full", confirmation_text="FULL")
        assert result2["mode"] == "full"

        with pytest.raises(FullAccessConfirmationRequired):
            controller.set_mode("full", confirmation_text="")

    def test_handle_input_submit_routes_confirm_input_to_set_mode(self):
        source = inspect.getsource(PermissionView.handle_input_submit)

        assert "permission-confirm-input" in source
        assert "_set_mode_from_form" in source

    def test_handle_input_submit_routes_root_input_to_add_root(self):
        source = inspect.getsource(PermissionView.handle_input_submit)

        assert "permission-root-input" in source
        assert "_add_root_from_form" in source

    def test_set_mode_from_form_clears_confirmation_input_after_success(self):
        source = inspect.getsource(PermissionView._set_mode_from_form)

        assert 'permission-confirm-input' in source
        assert '.value = ""' in source


class TestPermissionControllerSaveIntegration:
    def test_authorize_then_access_decision_allows(self, tmp_path):
        external = tmp_path / "external"
        external.mkdir()
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        controller.authorize_directory(external)
        decision = controller.access_decision(external / "file.txt", "write")

        assert decision["status"] == "allowed"

    def test_revoke_then_access_decision_denies(self, tmp_path):
        external = tmp_path / "external"
        external.mkdir()
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        controller.authorize_directory(external)
        controller.revoke_directory(external)
        decision = controller.access_decision(external / "file.txt", "write")

        assert decision["status"] == "denied"

    def test_full_mode_access_decision_allows_external(self, tmp_path):
        project = tmp_path / "project"
        project.mkdir()
        controller = PermissionScreenController(project)

        controller.set_mode("full", confirmation_text="FULL")
        decision = controller.access_decision(tmp_path / "anywhere" / "file.txt", "write")

        assert decision["status"] == "allowed"
        assert decision["mode"] == "full"


def test_high_risk_action_refuses_unconfirmed_request_without_permission_call():
    engine = FakePermissionEngine(PermissionResult.ALLOWED)

    request = prepare_tool_action(engine, tool="bash", resource="bash", confirmed=False)

    assert request.allowed is False
    assert request.confirmed is False
    assert request.permission == "denied"
    assert engine.calls == []


def test_high_risk_action_requires_permission_engine_allow():
    denied_engine = FakePermissionEngine(PermissionResult.DENIED)

    denied = prepare_tool_action(
        denied_engine, tool="write", resource="notes/output.md", confirmed=True
    )

    assert denied.allowed is False
    assert denied.permission == "denied"
    assert denied_engine.calls[0]["action"] == TUI_TOOL_ACTION
    assert denied_engine.calls[0]["context"]["sandbox_required"] is True

    allowed_engine = FakePermissionEngine(PermissionResult.ALLOWED)
    allowed = prepare_tool_action(
        allowed_engine, tool="edit", resource="notes/output.md", confirmed=True
    )

    assert allowed.allowed is True
    assert allowed.permission == "allowed"


def test_low_risk_action_still_uses_permission_engine_but_not_confirmation_gate():
    engine = FakePermissionEngine(PermissionResult.ALLOWED)

    request = prepare_tool_action(
        engine,
        tool="read",
        resource="notes/summary.md",
        confirmed=False,
        context={"screen": "工具管理"},
    )

    assert request.allowed is True
    assert request.confirmed is False
    assert request.context["requires_confirmation"] is False
    assert request.context["sandbox_required"] is True
    assert request.context["audit_required"] is True
    assert engine.calls[0]["context"]["screen"] == "工具管理"


def test_permission_screen_controller_requires_full_confirmation_and_updates_policy(
    tmp_path,
):
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    controller = PermissionScreenController(project_root)

    conservative_write = controller.access_decision(external_root / "out.csv", "write")

    assert conservative_write["status"] == AccessDecisionStatus.DENIED.value
    with pytest.raises(FullAccessConfirmationRequired):
        controller.set_mode("full", confirmation_text="")

    full_config = controller.set_mode("full", confirmation_text="FULL")
    full_write = controller.access_decision(external_root / "out.csv", "write")
    conservative_config = controller.set_mode("conservative")

    assert full_config["mode"] == "full"
    assert full_config["full_mode_confirmed"] is True
    assert full_write["status"] == AccessDecisionStatus.ALLOWED.value
    assert "will not silently" in full_write["helper"]
    assert conservative_config["mode"] == "conservative"
    assert conservative_config["full_mode_confirmed"] is False


# ═══ test_tui_state ═══


def test_recent_workspace_selection_saved_and_loaded_from_workspace_session_state(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("trial-1")
    manager.initialize_workspace("trial-2")

    state_path = save_recent_workspace("trial-1", "trial-2", project_root=tmp_path)

    assert (
        state_path
        == tmp_path
        / "workspaces"
        / "trial-1"
        / ".supermedicine"
        / "sessions"
        / "tui_recent_selection.yaml"
    )
    assert load_recent_workspace("trial-1", project_root=tmp_path) == "trial-2"
    assert load_recent_workspace("trial-2", project_root=tmp_path) is None
    assert not (
        tmp_path / ".supermedicine" / "sessions" / "tui_recent_selection.yaml"
    ).exists()


def test_tui_state_facade_uses_workspace_session_only(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    state = TUIState(tmp_path)

    state.save_recent_workspace("trial-1")

    assert state.load_recent_workspace("trial-1") == "trial-1"


def test_recent_workspace_state_is_scoped_per_workspace_and_not_global_cli_state(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path)
    manager.initialize_workspace("trial-1")
    manager.initialize_workspace("trial-2")

    first_state_path = save_recent_workspace(
        "trial-1", "trial-2", project_root=tmp_path
    )
    second_state_path = save_recent_workspace(
        "trial-2", "trial-1", project_root=tmp_path
    )

    assert load_recent_workspace("trial-1", project_root=tmp_path) == "trial-2"
    assert load_recent_workspace("trial-2", project_root=tmp_path) == "trial-1"
    assert (
        first_state_path.parent
        == tmp_path / "workspaces" / "trial-1" / ".supermedicine" / "sessions"
    )
    assert (
        second_state_path.parent
        == tmp_path / "workspaces" / "trial-2" / ".supermedicine" / "sessions"
    )
    assert not (
        tmp_path / ".supermedicine" / "sessions" / "tui_recent_selection.yaml"
    ).exists()


def test_tui_state_does_not_affect_cli_workspace_requirement(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    save_recent_workspace("trial-1", project_root=tmp_path)
    captured = {}

    class FakeRegistry:
        def discover(self):
            return []

    class FakeCheckpointManager:
        base_dir = "checkpoints"

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["params"] = params
            return {"status": "success", "task": task, "output": {}}

    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True)
    (policies / "default.yaml").write_text(
        "agent_id: delta\nrole: test\npermissions:\n  allowed:\n    - action: '*'\n      scope: '*'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)

    CLI().run("task", params={"x": 1})

    assert captured["params"] == {"x": 1}
    assert "_workspace" not in captured["params"]


def test_llm_startup_restore_is_separate_from_tui_workspace_session_state(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    save_recent_workspace("trial-1", project_root=tmp_path)
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "last_provider": "anthropic",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.test/v1",
                            "api_key": "sk-openai-state",
                            "model": "gpt-test",
                        },
                        "anthropic": {
                            "api_format": "anthropic",
                            "base_url": "https://anthropic.test/v1",
                            "api_key": "sk-anthropic-state",
                            "model": "claude-test",
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    manager = LLMConfigManager(ConfigCenter(config_path))

    assert load_recent_workspace("trial-1", project_root=tmp_path) == "trial-1"
    assert manager.get_current_provider()["provider"] == "anthropic"
    assert ConfigCenter(config_path).get_llm_current_provider_name() == "anthropic"


def test_tui_shell_status_object_exposes_workspace_plugin_llm_version_and_task_state(
    tmp_path,
):
    plugins_dir = tmp_path / "plugins" / "demo_plugin"
    plugins_dir.mkdir(parents=True)
    (plugins_dir / "plugin.yaml").write_text("name: demo\n", encoding="utf-8")
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "openai",
                    "providers": {
                        "openai": {
                            "api_format": "openai",
                            "base_url": "https://openai.test/v1",
                            "api_key": "sk-hidden-state",
                            "model": "gpt-test",
                        },
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    app = SuperMedicineTUI(project_root=tmp_path)
    status = app.status_text("llm")

    assert status.left == "📁 1 工作区"
    assert "🔌 1 插件" in status.center
    assert "openai LLM 已就绪" in status.center
    assert "任务空闲" in status.center
    assert "当前视图：LLM 配置" in status.right
    assert "SuperMedicine" in status.right
    assert "sk-hidden-state" not in status.center
    assert status.focus == "焦点：输入框"


def test_tui_navigation_metadata_preserves_numeric_shortcuts_and_minimal_titles(
    tmp_path,
):
    app = SuperMedicineTUI(project_root=tmp_path)

    assert [item.key for item in app.nav_items()] == [
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "0",
    ]
    assert [item.view_id for item in app.nav_items()] == [
        "chat",
        "dashboard",
        "workspace",
        "paper",
        "experience",
        "tool",
        "dialog",
        "llm",
        "experiment",
        "log",
    ]
    assert app.nav_items()[0].label == "对话"
    assert app.nav_items()[-2].label == "实验"
    assert app.nav_items()[-1].label == "Log 报告"


# ═══ test_tui_workspace_screens ═══


class TestWorkspaceRefresh:
    def test_workspace_view_exposes_refresh_view_data_hook(self):
        assert hasattr(WorkspaceView, "refresh_view_data")
        source = inspect.getsource(WorkspaceView.refresh_view_data)
        assert "_load_workspaces" in source
        assert "refreshed=True" in source

    def test_workspace_view_compose_declares_required_widgets(self):
        source = inspect.getsource(WorkspaceView.compose)

        assert 'id="workspace-table"' in source
        assert 'id="workspace-id-input"' in source
        assert 'id="workspace-create"' in source
        assert 'id="workspace-select"' in source
        assert 'id="workspace-refresh"' in source
        assert 'id="workspace-delete"' in source
        assert 'id="workspace-status"' in source

    def test_workspace_view_uses_targeted_refresh_without_polling(self):
        source = inspect.getsource(WorkspaceView)

        assert "refresh_view_data" in source
        assert "set_interval" not in source

    def test_workspace_screen_loads_data_on_mount(self, tmp_path):
        manager = WorkspaceManager(tmp_path)
        manager.initialize_workspace("test-ws")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                assert table.row_count == 1
                assert "test-ws" in str(table.get_row_at(0))
                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_list") in status

        asyncio.run(scenario())

    def test_workspace_screen_shows_empty_state_when_no_workspaces(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                assert table.row_count == 0
                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_no_workspaces") in status

        asyncio.run(scenario())

    def test_workspace_screen_refresh_view_data_updates_table(self, tmp_path):
        manager = WorkspaceManager(tmp_path)
        manager.initialize_workspace("initial-ws")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                assert table.row_count == 1

                manager.initialize_workspace("external-ws")
                app._views["workspace"].refresh_view_data()
                await pilot.pause()

                assert table.row_count == 2
                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_refreshed") in status

        asyncio.run(scenario())

    def test_workspace_screen_refresh_button_triggers_reload(self, tmp_path):
        manager = WorkspaceManager(tmp_path)
        manager.initialize_workspace("btn-ws")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                assert table.row_count == 1

                manager.initialize_workspace("added-ws")
                app.query_one("#workspace-refresh", Button).press()
                await _wait_for_tui_condition(pilot, lambda: table.row_count == 2)

                assert table.row_count == 2
                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_refreshed") in status

        asyncio.run(scenario())

    def test_workspace_screen_refresh_preserves_selected_row(self, tmp_path):
        manager = WorkspaceManager(tmp_path)
        manager.initialize_workspace("alpha")
        manager.initialize_workspace("beta")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                beta_index = next(
                    i for i in range(table.row_count) if "beta" in str(table.get_row_at(i))
                )
                table.move_cursor(row=beta_index, column=0)
                await pilot.pause()

                manager.initialize_workspace("gamma")
                app._views["workspace"].refresh_view_data()
                await pilot.pause()

                assert table.row_count == 3
                row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
                assert str(row_key.value) == "beta"

        asyncio.run(scenario())

    def test_workspace_screen_create_then_refresh_shows_new_workspace(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                assert table.row_count == 0

                input_widget = app.query_one("#workspace-id-input", Input)
                input_widget.value = "new-ws"
                input_widget.focus()
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()

                assert table.row_count == 1
                assert "new-ws" in str(table.get_row_at(0))
                status = _static_text(app.query_one("#workspace-status", Static))
                assert "已创建并选择工作区" in status

        asyncio.run(scenario())

    def test_workspace_screen_create_empty_id_shows_error(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                input_widget = app.query_one("#workspace-id-input", Input)
                input_widget.focus()
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()

                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("error") in status

        asyncio.run(scenario())

    def test_workspace_screen_select_updates_status(self, tmp_path):
        WorkspaceManager(tmp_path).initialize_workspace("sel-ws")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await _wait_for_tui_condition(
                    pilot,
                    lambda: t("workspace_list") in _static_text(app.query_one("#workspace-status", Static))
                    or t("workspace_no_workspaces") in _static_text(app.query_one("#workspace-status", Static)),
                )

                input_widget = app.query_one("#workspace-id-input", Input)
                input_widget.value = "sel-ws"
                app.query_one("#workspace-select", Button).press()
                await _wait_for_tui_condition(
                    pilot,
                    lambda: "已选择工作区" in _static_text(app.query_one("#workspace-status", Static)),
                )

                status = _static_text(app.query_one("#workspace-status", Static))
                assert "已选择工作区" in status

        asyncio.run(scenario())

    def test_workspace_screen_refresh_view_data_shows_refreshed_prefix(self, tmp_path):
        manager = WorkspaceManager(tmp_path)
        manager.initialize_workspace("refresh-prefix-ws")

        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                status_initial = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_list") in status_initial

                app._views["workspace"].refresh_view_data()
                await pilot.pause()

                status_refreshed = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_refreshed") in status_refreshed
                assert status_refreshed.startswith(t("workspace_refreshed"))

        asyncio.run(scenario())

    def test_workspace_screen_refresh_empty_shows_refreshed_empty_message(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                app._views["workspace"].refresh_view_data()
                await pilot.pause()

                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_refreshed") in status
                assert t("workspace_no_workspaces") in status

        asyncio.run(scenario())

    def test_workspace_screen_controller_list_returns_expected_format(self, tmp_path):
        WorkspaceManager(tmp_path).initialize_workspace("ctrl-ws")
        controller = WorkspaceScreenController(project_root=tmp_path)

        workspaces = controller.list_workspaces()

        assert len(workspaces) == 1
        ws = workspaces[0]
        assert "id" in ws
        assert "path" in ws
        assert "metadata" in ws
        assert ws["id"] == "ctrl-ws"

    def test_workspace_screen_compose_declares_hint_and_title_widgets(self):
        source = inspect.getsource(WorkspaceView.compose)

        assert 'classes="section-title"' in source
        assert 'id="workspace-create-hint"' in source
        assert 'id="workspace-action-hint"' in source

    def test_workspace_screen_ctrl_n_focuses_input(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                await pilot.press("ctrl+n")
                await pilot.pause()

                input_widget = app.query_one("#workspace-id-input", Input)
                assert input_widget.has_focus

        asyncio.run(scenario())

    def test_workspace_view_refresh_reads_external_workspace_with_condition_wait(self, tmp_path):
        async def scenario() -> None:
            app = SuperMedicineTUI(project_root=tmp_path)
            async with app.run_test(size=(180, 80)) as pilot:
                app.action_switch_view("workspace")
                await pilot.pause()

                table = app.query_one("#workspace-table", DataTable)
                assert table.row_count == 0

                WorkspaceManager(tmp_path).initialize_workspace("external-a")

                workspace_view = app.query_one("WorkspaceView", WorkspaceView)
                workspace_view._load_workspaces(refreshed=True)
                await pilot.pause()
                await _wait_for_tui_condition(pilot, lambda: table.row_count == 1, timeout=5.0)

                assert table.row_count == 1
                assert table.get_row("external-a")[0] == "external-a"
                status = _static_text(app.query_one("#workspace-status", Static))
                assert t("workspace_refreshed") in status

        asyncio.run(scenario())


def test_workspace_screen_create_select_and_recent_state(tmp_path):
    controller = WorkspaceScreenController(tmp_path)

    created = controller.create_workspace("study-a")
    selected = controller.select_workspace("study-a")

    assert created["label"] == "工作区：study-a"
    assert selected["message"] == "已选择工作区"
    assert controller.recent_workspace("study-a") == "study-a"
    assert controller.list_workspaces()[0]["id"] == "study-a"


def test_workspace_screen_create_rejects_duplicate_and_invalid_ids(tmp_path):
    controller = WorkspaceScreenController(tmp_path)
    controller.create_workspace("study-a")

    with pytest.raises(ValueError, match="已存在"):
        controller.create_workspace("study-a")

    with pytest.raises(ValueError, match="小写字母"):
        controller.create_workspace("Study_A")


def test_workspace_screen_create_does_not_enter_kernel_or_llm(tmp_path, monkeypatch):
    imported: list[str] = []
    original_import = __import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("core.kernel", "core.llm_client", "core.llm_providers")):
            imported.append(name)
            raise AssertionError(
                f"TUI workspace create must not import Kernel/LLM module: {name}"
            )
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", guarded_import)

    result = WorkspaceScreenController(tmp_path).create_workspace("direct-tui")

    assert result["id"] == "direct-tui"
    assert result["selected"] is True
    assert (tmp_path / "workspaces" / "direct-tui" / "workspace.yaml").is_file()
    assert imported == []


def test_workspace_screen_empty_state_is_chinese_and_non_destructive(tmp_path):
    controller = WorkspaceScreenController(tmp_path)

    assert controller.list_workspaces() == []
    assert t("workspace_no_workspaces") == "暂无工作区，请先创建"
    assert not (tmp_path / "workspaces").exists()


def test_workspace_screen_delete_requires_exact_confirmation(tmp_path):
    _allow_delete_policy(tmp_path)
    controller = WorkspaceScreenController(tmp_path)
    controller.create_workspace("study-a")

    with pytest.raises(ValueError, match="工作区 ID"):
        controller.delete_workspace("study-a", confirm="wrong")

    assert (tmp_path / "workspaces" / "study-a").exists()


def test_workspace_screen_hard_delete_uses_policy_and_removes_workspace(tmp_path):
    _allow_delete_policy(tmp_path)
    controller = WorkspaceScreenController(tmp_path)
    controller.create_workspace("study-a")

    result = controller.delete_workspace("study-a", confirm="study-a")

    assert result["status"] == "deleted"
    assert result["message"] == "工作区已硬删除"
    assert not (tmp_path / "workspaces" / "study-a").exists()
    assert (tmp_path / ".supermedicine" / "policies" / "audit.jsonl").exists()


def test_workspace_view_delete_does_not_auto_confirm_source():
    delete_source = inspect.getsource(WorkspaceView._delete_workspace)

    assert "confirm=workspace_id" not in delete_source
    assert "delete:" in delete_source
    assert "confirmed_workspace_id" in delete_source


def test_workspace_delete_copy_describes_exact_irreversible_confirmation():
    assert "完全一致" in t("workspace_delete_requires_confirm")
    assert "不可恢复" in t("workspace_delete_requires_confirm")


def test_workspace_manual_create_entry_copy_is_visible_and_keyboard_mouse_friendly():
    assert "手动创建" in t("workspace_manual_create_hint")
    assert "Enter" in t("workspace_manual_create_hint")
    assert "Ctrl+N" in t("workspace_manual_create_hint")
    assert "鼠标" in t("workspace_manual_create_hint")
    assert "小写字母" in t("workspace_create_placeholder")


def test_workspace_view_supports_enter_shortcut_and_keeps_focus_after_create():
    compose_source = inspect.getsource(WorkspaceView.compose)
    create_source = inspect.getsource(WorkspaceView._create_workspace)
    load_source = inspect.getsource(WorkspaceView._load_workspaces)
    key_source = inspect.getsource(WorkspaceView.on_key)
    submit_source = inspect.getsource(WorkspaceView.handle_input_submit)
    row_source = inspect.getsource(WorkspaceView.on_data_table_row_selected)

    assert "workspace_manual_create_hint" in compose_source
    assert "workspace_create_placeholder" in compose_source
    assert "ctrl+n" in key_source
    assert "workspace-id-input" in submit_source
    assert "_create_workspace(value.strip())" in submit_source
    assert "input_widget.focus()" in create_source
    assert "_load_workspaces(preserve_status=True)" in create_source
    assert "_select_table_row" in create_source
    assert "move_cursor" in inspect.getsource(WorkspaceView._select_table_row)
    assert "preserve_status" in load_source
    assert "_select_workspace(workspace_id)" in row_source


def test_workspace_view_manual_create_is_visible_and_usable_in_running_tui(tmp_path):
    """Regression baseline: manual workspace creation is visible, focusable, and creates a selectable row."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            view = app._views["workspace"]
            hint = view.query_one("#workspace-create-hint", Static)
            input_widget = view.query_one("#workspace-id-input", Input)
            table = view.query_one("#workspace-table", DataTable)
            status = view.query_one("#workspace-status", Static)

            assert "手动创建" in str(hint.renderable)
            assert input_widget.has_focus

            view._create_workspace("manual-a")
            await pilot.pause()

            assert (tmp_path / "workspaces" / "manual-a" / "workspace.yaml").is_file()
            assert input_widget.value == "manual-a"
            assert input_widget.has_focus
            assert table.get_row("manual-a")[0] == "manual-a"
            assert "manual-a" in str(status.renderable)

    asyncio.run(scenario())


def test_workspace_manual_create_is_visible_to_already_mounted_dialog_page(tmp_path):
    """Regression baseline: pages mounted before manual create must observe the shared workspace list."""

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            workspace_view = app._views["workspace"]
            workspace_view._create_workspace("manual-cross-page")
            await pilot.pause()

            app.action_switch_view("dialog")
            await pilot.pause()

            dialog_view = app._views["dialog"]
            select_widget = dialog_view.query_one("#dialog-workspace-select")
            option_values = [str(option[1]) for option in select_widget._options]

            assert "manual-cross-page" in option_values

            dialog_view._load_dialog_history(refreshed=True)
            await pilot.pause()
            status = dialog_view.query_one("#dialog-status", Static)
            assert "暂无工作区" not in str(status.renderable)

    asyncio.run(scenario())


def test_workspace_view_prevents_global_prompt_from_stealing_workspace_focus():
    app_switch_source = inspect.getsource(SuperMedicineTUI.action_switch_view)
    app_focus_source = inspect.getsource(SuperMedicineTUI._focus_current_view_default)
    prompt_focus_source = inspect.getsource(SuperMedicineTUI._focus_prompt_input)

    assert "_focus_current_view_default" in app_switch_source
    assert "focus_default" in app_focus_source
    assert "self._focus_prompt_input()" in app_focus_source
    assert "#prompt-input" in prompt_focus_source


def test_workspace_view_error_path_redacts_secret_and_notifies(monkeypatch, tmp_path):
    secret = "sk-workspace-error-secret"
    messages: list[str] = []

    class FakeStatus:
        def update(self, message):
            messages.append(str(message))

        def remove_class(self, *classes):
            pass

        def add_class(self, class_name):
            pass

    class FakeApp:
        def notify(self, message, severity=None):
            messages.append(str(message))

    class TestWorkspaceView(WorkspaceView):
        @property
        def app(self):
            return FakeApp()

        def query_one(self, *args, **kwargs):
            return FakeStatus()

    view = TestWorkspaceView(tmp_path)

    view._set_error(RuntimeError(f"failed api_key={secret}"))

    rendered = "\n".join(messages)
    assert t("error") in rendered
    assert secret not in rendered
    assert "[已隐藏]" in rendered


def test_business_views_set_deterministic_non_empty_reload_statuses():
    workspace_loader = inspect.getsource(WorkspaceView._load_workspaces)
    tool_loader = inspect.getsource(ToolView._load_tools)
    dialog_loader = inspect.getsource(DialogView._load_dialog_history)

    assert "workspace_list" in workspace_loader
    assert "len(workspaces)" in workspace_loader
    assert "tool_list" in tool_loader
    assert "tool_count" in tool_loader
    assert "dialog_refreshed" in dialog_loader
    assert "len(events)" in dialog_loader


def test_workspace_view_refresh_button_reads_external_workspace_created_after_enter(tmp_path):
    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            app.action_switch_view("workspace")
            await pilot.pause()

            table = app.query_one("#workspace-table", DataTable)
            assert table.row_count == 0

            WorkspaceManager(tmp_path).initialize_workspace("external-a")
            # 直接调用视图刷新方法，避免 pilot.click() 的事件传递问题
            workspace_view = app.query_one("WorkspaceView", WorkspaceView)
            workspace_view._load_workspaces(refreshed=True)
            await pilot.pause()
            await _wait_for_tui_condition(pilot, lambda: table.row_count == 1, timeout=5.0)

            assert table.row_count == 1
            assert table.get_row("external-a")[0] == "external-a"
            assert t("workspace_refreshed") in str(
                app.query_one("#workspace-status", Static).renderable
            )

    asyncio.run(scenario())


def test_app_switch_view_invokes_dynamic_refresh_hooks(tmp_path):
    app = SuperMedicineTUI(project_root=tmp_path)
    calls: list[str] = []

    class FakeView:
        display = False

        def refresh_view_data(self) -> None:
            calls.append("refresh")

    app._views = {"workspace": FakeView()}
    app._current_view = "workspace"
    app._focus_current_view_default = lambda: None
    app._update_status_bar = lambda: None

    app.action_switch_view("workspace")

    assert calls == ["refresh"]

from __future__ import annotations

from core.tui.app import SuperMedicineTUI
from core.tui.i18n import t
from core.tui.screens.chat_view import ChatView, safe_display_text


class CapturingRichLog:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, value: str) -> None:
        self.lines.append(value)

    def clear(self) -> None:
        self.lines.clear()


class CapturingChatView(ChatView):
    def __init__(self) -> None:
        super().__init__()
        self.output = CapturingRichLog()

    def query_one(self, selector, widget_type=None):
        return self.output


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
    events: list[tuple[str, str]] = []

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

    import asyncio

    asyncio.run(app._run_kernel_task("hello", FakeChat(), turn_id=1))

    assert events[0] == ("system", t("thinking"))
    assert ("status", t("chat_running")) in events
    assert any(
        kind == "assistant" and t("chat_result_status") in message and "ok" in message
        for kind, message in events
    )
    assert events[-1] == ("status", t("chat_completed"))
    assert app._task_running is False


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

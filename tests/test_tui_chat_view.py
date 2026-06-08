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

    import asyncio

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

    import asyncio

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

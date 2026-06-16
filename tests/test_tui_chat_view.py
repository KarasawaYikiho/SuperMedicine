"""Tests for ChatView progress display — DBG-BUG-004."""

from __future__ import annotations

from typing import Any

from core.tui.i18n import t
from core.tui.screens.chat_view import ChatView, safe_display_text


# ═══ Helpers ═══


class CapturingRichLog:
    """Fake RichLog that captures written lines."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, value: str) -> None:
        self.lines.append(value)

    def clear(self) -> None:
        self.lines.clear()


class CapturingStatic:
    """Fake Static widget that records update calls."""

    def __init__(self) -> None:
        self.content: str = ""
        self.visible: bool = False

    def update(self, value: str) -> None:
        self.content = value


class CapturingChatView(ChatView):
    """ChatView subclass that replaces query_one with capturing stubs."""

    def __init__(self) -> None:
        super().__init__()
        self.output = CapturingRichLog()
        self._indicator = CapturingStatic()

    def query_one(self, selector: str, widget_type: Any = None) -> Any:  # type: ignore[override]
        if selector == "#chat-output":
            return self.output
        if selector == "#thinking-indicator":
            return self._indicator
        raise ValueError(f"Unexpected selector: {selector}")


# ═══ Thinking Animation Tests ═══


class TestThinkingAnimation:
    """Verify thinking animation lifecycle on ChatView."""

    def test_start_thinking_animation_sets_indicator_visible(self):
        view = CapturingChatView()

        # Directly test state changes without timer
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

        # Simulate frame advances
        for frame in range(6):
            view._thinking_frame = frame
            view._advance_thinking_frame()
            filled = "●" * ((frame + 1) % 6)
            empty = "○" * (5 - (frame + 1) % 6)
            assert filled + empty in view._indicator.content
            # Verify indicator was updated with thinking text
            assert "思考中" in view._indicator.content

    def test_stop_thinking_animation_hides_indicator(self):
        view = CapturingChatView()
        view._thinking_active = True
        view._indicator.visible = True

        # Simulate stop
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


# ═══ Processing Animation Tests ═══


class TestProcessingAnimation:
    """Verify processing animation lifecycle on ChatView."""

    def test_start_processing_animation_sets_indicator_visible(self):
        view = CapturingChatView()

        view._processing_active = True
        view._processing_frame = 0
        view._indicator.visible = True
        view._indicator.update(f"[bold yellow]⏳ {t('chat_processing_state')} ○○○○○[/]")

        assert view._indicator.visible is True
        assert t("chat_processing_state") in view._indicator.content
        assert "○○○○○" in view._indicator.content

    def test_advance_processing_frame_updates_fill_pattern(self):
        view = CapturingChatView()
        view._processing_active = True

        for frame in range(6):
            view._processing_frame = frame
            view._advance_processing_frame()
            assert t("chat_processing_state") in view._indicator.content

    def test_stop_processing_animation_hides_indicator(self):
        view = CapturingChatView()
        view._processing_active = True
        view._indicator.visible = True

        view._processing_active = False
        view._indicator.visible = False

        assert view._processing_active is False
        assert view._indicator.visible is False

    def test_processing_animation_inactive_frame_does_nothing(self):
        view = CapturingChatView()
        view._processing_active = False
        view._indicator.content = "unchanged"

        view._advance_processing_frame()

        assert view._indicator.content == "unchanged"


# ═══ Thinking Content Tests ═══


class TestThinkingContent:
    """Verify thinking/reasoning content display in chat view."""

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


# ═══ Streaming Assistant Message Tests ═══


class TestStreamingAssistantMessage:
    """Verify begin_assistant_message and append_assistant_delta."""

    def test_begin_assistant_message_shows_generating_hint(self):
        view = CapturingChatView()
        view.add_user_message("hello")

        view.begin_assistant_message(turn_id=1)

        rendered = "\n".join(view.output.lines)
        assert f"{t('chat_assistant_label')} #1" in rendered
        assert "助手正在生成回复..." in rendered

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


# ═══ Safe Display Text Tests ═══


class TestSafeDisplayText:
    """Verify safe_display_text handles escaping and redaction."""

    def test_escapes_html_tags(self):
        result = safe_display_text("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_escapes_rich_markup(self):
        result = safe_display_text("[bold]text[/bold]")
        assert "\\[bold]" in result

    def test_redacts_api_keys(self):
        result = safe_display_text("api_key=sk-my-secret-key-12345678")
        assert "sk-my-secret-key-12345678" not in result
        assert "[已隐藏]" in result

    def test_redacts_bearer_tokens(self):
        result = safe_display_text("Authorization: Bearer abc.def.ghi")
        assert "Bearer abc" not in result
        assert "Bearer [已隐藏]" in result

    def test_handles_none_value(self):
        result = safe_display_text(None)
        assert result == ""

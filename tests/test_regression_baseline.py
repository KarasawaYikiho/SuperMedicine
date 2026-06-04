from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
import yaml
from textual import events

from installer.entrypoint import init_config
from Uninstall import uninstall
from core.config_center import ConfigCenter
from core.llm_client import create_configured_llm_client
from core.tui.app import PromptInput, SuperMedicineTUI, launch_tui


def test_llm_client_must_really_call_configured_provider_or_return_explicit_failure(tmp_path, monkeypatch):
    """Regression baseline: configured LLM calls may not be faked as success."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "baseline-openai",
                    "providers": {
                        "baseline-openai": {
                            "api_format": "openai",
                            "base_url": "https://llm-baseline.local.test/v1",
                            "api_key": "sk-baseline-llm-secret",
                            "model": "baseline-model",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "model": "baseline-model",
                    "choices": [{"message": {"content": "provider response"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3},
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    client = create_configured_llm_client(ConfigCenter(config_path))
    result = client.chat([{"role": "user", "content": "baseline prompt"}], max_tokens=5)

    assert captured["url"] == "https://llm-baseline.local.test/v1/chat/completions"
    assert captured["payload"] == {
        "model": "baseline-model",
        "messages": [{"role": "user", "content": "baseline prompt"}],
        "temperature": 0.7,
        "max_tokens": 5,
    }
    assert result["content"] == "provider response"
    assert result["model"] == "baseline-model"


def test_llm_client_missing_configuration_is_explicit_failure_not_success(tmp_path):
    """Regression baseline: no configured provider must be an actionable failure."""

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"project": "no-llm"}), encoding="utf-8")

    result = create_configured_llm_client(ConfigCenter(config_path))

    assert result["ok"] is False
    assert result["error"]["code"] == "missing_provider"
    assert "Install.py --init" in result["error"]["message"]


def test_tui_visible_logging_does_not_show_llm_client_creation_noise(tmp_path, caplog):
    """Regression baseline: ordinary TUI-facing INFO logs must not expose internal LLM creation chatter."""

    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    config_path = config_dir / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "baseline-openai",
                    "providers": {
                        "baseline-openai": {
                            "api_format": "openai",
                            "base_url": "https://llm-baseline.local.test/v1",
                            "api_key": "sk-baseline-llm-secret",
                            "model": "baseline-model",
                        }
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    forbidden_fragments = (
        "LLM Manager_create_client",
        "LLM manager create_client",
        "Creating LLM client",
    )

    caplog.set_level("INFO", logger="core.llm_manager")
    caplog.set_level("INFO", logger="core.llm_client")
    create_configured_llm_client(ConfigCenter(config_path))

    assert not any(fragment in caplog.text for fragment in forbidden_fragments)

    caplog.clear()
    caplog.set_level("DEBUG", logger="core.llm_manager")
    caplog.set_level("DEBUG", logger="core.llm_client")
    create_configured_llm_client(ConfigCenter(config_path))

    assert "LLM manager create_client" in caplog.text
    assert "Creating LLM client" in caplog.text
    assert "sk-baseline-llm-secret" not in caplog.text


def test_tui_input_submission_clears_input_without_raw_terminal_echo_or_screen_clear(tmp_path, capsys, monkeypatch):
    """Regression baseline: submitted input stays inside TUI state and is not echoed to the raw terminal."""

    processed: list[str] = []
    rendered_user_messages: list[str] = []

    class FakeInput:
        value = "sensitive prompt that must not leak"

    class FakeEvent:
        input = FakeInput()
        value = FakeInput.value
        stopped = False

        @classmethod
        def stop(cls):
            cls.stopped = True

    class FakeChat:
        def add_user_message(self, message: str) -> None:
            rendered_user_messages.append(message)

    def fake_process_message(self, message: str) -> None:
        processed.append(message)

    forbidden_terminal_calls: list[tuple[object, ...]] = []

    def fake_print(*args, **kwargs):
        forbidden_terminal_calls.append(args)

    monkeypatch.setattr(SuperMedicineTUI, "_process_message", fake_process_message)
    monkeypatch.setattr("builtins.print", fake_print)

    app = SuperMedicineTUI(project_root=tmp_path)
    app._views = {"chat": FakeChat()}

    app.on_input_submitted(FakeEvent())

    assert FakeEvent.input.value == ""
    assert processed == ["sensitive prompt that must not leak"]
    assert rendered_user_messages == ["sensitive prompt that must not leak"]
    assert FakeEvent.stopped is True
    assert forbidden_terminal_calls == []
    assert "sensitive prompt that must not leak" not in capsys.readouterr().out


def test_tui_interactive_launch_does_not_print_status_before_alternate_screen(tmp_path, capsys, monkeypatch):
    """Regression baseline: interactive launch lets Textual own terminal output and input mode."""

    run_kwargs: dict[str, object] = {}

    def fake_run(self, **kwargs):
        run_kwargs.update(kwargs)

    monkeypatch.setattr(SuperMedicineTUI, "run", fake_run)

    status = launch_tui(dry_run=False, project_root=tmp_path)

    assert status.interactive is True
    assert run_kwargs == {"mouse": True}
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    ("shortcut", "expected_view"),
    [
        ("1", "chat"),
        ("2", "dashboard"),
        ("3", "workspace"),
        ("4", "paper"),
        ("5", "experience"),
        ("6", "tool"),
        ("7", "dialog"),
        ("8", "llm"),
        ("9", "experiment"),
        ("0", "log"),
    ],
)
def test_tui_prompt_starts_clean_and_numeric_shortcuts_do_not_enter_prompt(tmp_path, shortcut, expected_view):
    """Regression baseline: startup focus/nav keys must not seed prompt text with shortcut digits."""

    import asyncio

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            prompt = app.query_one("#prompt-input", PromptInput)
            assert prompt.value == ""

            await pilot.press(shortcut)
            await pilot.pause()

            assert app._current_view == expected_view
            assert prompt.value == ""
            if expected_view == "workspace":
                assert not prompt.has_focus
            else:
                assert prompt.has_focus

    asyncio.run(scenario())


def test_tui_prompt_filters_terminal_control_sequences_but_preserves_pasted_digits():
    """Regression baseline: mouse/CSI bytes are not prompt text; pasted numeric text is."""

    prompt = PromptInput()

    assert prompt._clean_terminal_control_text("\x1b[<0;12;34M") == ""
    assert prompt._clean_terminal_control_text("[<0;12;34M") == ""
    assert prompt._clean_terminal_control_text("\x1b[200~abc123\x1b[201~") == "abc123"
    assert prompt._clean_terminal_control_text("ordinary 123 text") == "ordinary 123 text"


def test_tui_prompt_swallow_digits_while_terminal_sequence_is_incomplete():
    """Regression baseline: raw mouse sequence digits must not trigger view navigation."""

    import asyncio

    async def scenario() -> None:
        app = SuperMedicineTUI()
        async with app.run_test(size=(140, 45)):
            prompt = app.query_one("#prompt-input", PromptInput)
            prompt.value = "[<"

            class FakeKey:
                key = "7"
                character = "7"
                stopped = False
                prevented = False

                def stop(self) -> None:
                    self.stopped = True

                def prevent_default(self) -> None:
                    self.prevented = True

            event = FakeKey()
            prompt.on_key(cast(events.Key, event))

            assert event.stopped is True
            assert event.prevented is True
            assert prompt.value == ""

    asyncio.run(scenario())


def test_tui_prompt_key_filter_uses_textual_character_attribute_shape():
    """Regression baseline: Textual Key events expose character, not char."""

    prompt = PromptInput()

    class EscapeKey:
        key = "escape"
        character = None

    class DigitKey:
        key = "7"
        character = "7"

    assert prompt._is_terminal_control_key(cast(events.Key, EscapeKey())) is True
    assert prompt._is_terminal_control_key(cast(events.Key, DigitKey())) is False


def test_tui_status_bar_skips_unchanged_widget_updates(tmp_path):
    """Regression baseline: repeated refresh requests should not repaint unchanged status widgets."""

    app = SuperMedicineTUI(project_root=tmp_path)
    updates: list[tuple[str, str]] = []

    class FakeStatus:
        def __init__(self, name: str) -> None:
            self.name = name

        def update(self, value: str) -> None:
            updates.append((self.name, value))

    widgets = {
        "#status-left": FakeStatus("left"),
        "#status-center": FakeStatus("center"),
        "#status-right": FakeStatus("right"),
    }

    def fake_query_one(selector, widget_type=None):
        return widgets[selector]

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(app, "query_one", fake_query_one)
        monkeypatch.setattr(app, "_status_clock_text", lambda: "12:00 UTC")
        app._update_status_bar()
        app._update_status_bar()
    finally:
        monkeypatch.undo()

    assert [name for name, _ in updates] == ["left", "center", "right"]


def test_tui_sources_do_not_use_terminal_clear_sequences_that_cause_flicker():
    """Regression baseline: TUI code should not manually clear the raw terminal."""

    root = Path(__file__).resolve().parents[1]
    tui_sources = [root / "core" / "tui" / "app.py", *sorted((root / "core" / "tui" / "screens").glob("*.py"))]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in tui_sources)

    forbidden_fragments = [
        "os.system('clear'",
        'os.system("clear"',
        "os.system('cls'",
        'os.system("cls"',
        "\\x1b[2J",
        "\\033[2J",
    ]
    assert not any(fragment in combined for fragment in forbidden_fragments)


def test_experiment_and_log_tui_views_are_additive_to_existing_navigation():
    """Regression baseline: new TUI entries must not replace existing core views."""

    nav_keys = {item.key for item in SuperMedicineTUI.NAV_ITEMS}
    nav_views = {item.view_id for item in SuperMedicineTUI.NAV_ITEMS}
    nav_by_key = {item.key: item for item in SuperMedicineTUI.NAV_ITEMS}
    binding_keys = {binding.key for binding in SuperMedicineTUI.BINDINGS}

    assert {"1", "2", "3", "4", "5", "6", "7", "8"}.issubset(nav_keys)
    assert {"chat", "dashboard", "workspace", "tool", "llm", "paper", "experience", "dialog"}.issubset(nav_views)
    assert nav_by_key["9"].view_id == "experiment"
    assert nav_by_key["9"].label == "实验指导器"
    assert nav_by_key["0"].view_id == "log"
    assert nav_by_key["0"].label == "Log 报告"
    assert {"9", "0"}.issubset(binding_keys)


def test_install_requires_llm_and_does_not_leave_partial_install_artifacts(tmp_path):
    """Regression baseline: first install must force complete LLM import/configuration."""

    with pytest.raises(ValueError, match="provider, base_url, api_key, model"):
        init_config(tmp_path)

    assert not (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert not (tmp_path / ".supermedicine" / "agents").exists()
    assert not (tmp_path / ".supermedicine" / "plugins").exists()


def test_uninstall_removes_installed_artifacts_and_recorded_config_residue(tmp_path):
    """Regression baseline: uninstall cleans project-owned install products and recorded residues."""

    created_paths = [
        ".supermedicine/config.yaml",
        ".supermedicine/agents/agent.md",
        ".supermedicine/plugins/plugin.yaml",
        "workspaces/demo/state.json",
        "platform-targets/opencode/supermedicine.json",
    ]
    for relative in created_paths:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    (tmp_path / ".supermedicine" / "install-record.json").write_text(
        json.dumps({"created_paths": created_paths, "platform_target_paths": ["platform-targets/opencode/supermedicine.json"]}),
        encoding="utf-8",
    )
    user_file = tmp_path / "user-notes.md"
    user_file.write_text("keep", encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert not (tmp_path / ".supermedicine").exists()
    assert not (tmp_path / "workspaces").exists()
    assert not (tmp_path / "platform-targets" / "opencode" / "supermedicine.json").exists()
    assert user_file.exists()

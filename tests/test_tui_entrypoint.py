from __future__ import annotations

import pytest
import yaml
import re
from pathlib import Path
from typing import cast

from textual.widgets import Input, ListView, Static

from cli_entry import CLI, main
from core.tui.app import PromptInput, SuperMedicineTUI, launch_tui
from core.tui.status_helpers import STATUS_STYLE_CLASSES
from core.tui.i18n import LABELS, t, tui_title_style_inventory
from core.tui.preview_artifact import write_preview_artifact


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
    import asyncio

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
            assert "切换主题" in menu_text
            assert "帮助" in menu_text
            assert "最大化/还原" in menu_text

            await pilot.press("enter")
            await pilot.pause()
            view_text = "\n".join(
                str(cast(Static, static).renderable)
                for static in app.screen.query("#tui-view-menu-list Static")
            )
            assert "对话" in view_text
            assert "Log 报告" in view_text

            await pilot.press("down", "enter")
            await pilot.pause()
            assert app._current_view == "dashboard"
            assert app.view_title_text(app._current_view) == "状态看板"

    asyncio.run(scenario())


def test_tui_upper_left_menu_button_opens_menu(tmp_path):
    import asyncio

    async def scenario() -> None:
        app = SuperMedicineTUI(project_root=tmp_path)
        async with app.run_test(size=(140, 45)) as pilot:
            button = app.query_one("#menu-button", Static)
            assert "菜单" in str(button.renderable)
            assert "M" in str(button.renderable)

            await pilot.click("#menu-button")
            await pilot.pause()

            assert app.screen.query_one("#tui-main-menu-list", ListView)

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

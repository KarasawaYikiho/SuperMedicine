from __future__ import annotations

import pytest
import yaml
import re
from pathlib import Path

from Cli import CLI, main
from core.tui.app import STATUS_STYLE_CLASSES, SuperMedicineTUI, launch_tui
from core.tui.i18n import LABELS, t


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
    assert t("app_title") == "SuperMedicine 终端工作台"
    assert LABELS["permission_required"] == "需要权限确认"
    assert LABELS["layout_shortcuts"] == "快捷键"
    assert LABELS["status_task_idle"] == "任务空闲"
    assert LABELS["status_focus_input"] == "输入栏"
    assert "Tab/Shift+Tab" in LABELS["status_shortcuts_hint"]
    assert "Enter" in LABELS["help_submission"]
    assert "危险操作" in LABELS["help_danger"]
    assert "LLM" in LABELS["help_status"]
    assert "任务" in LABELS["help_status"]


def test_tui_dry_run_returns_chinese_status(capsys):
    status = launch_tui(dry_run=True)

    assert status.interactive is False
    assert status.title == "SuperMedicine 终端工作台"
    assert "基础组件已就绪" in status.message
    assert status.current_view == "chat"
    assert status.view_title == "对话"
    assert "任务空闲" in status.status_center
    assert "1-0 切换视图" in status.shortcut_hint
    assert "Tab/Shift+Tab" in status.shortcut_hint
    assert status.focus_target == "prompt-input"
    assert "SuperMedicine 终端工作台" in capsys.readouterr().out


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
        "仪表盘",
        "工作区管理",
        "论文管理",
        "经验学习",
        "工具管理",
        "对话历史",
        "LLM 管理",
        "实验指导器",
        "Log 报告",
    ]
    assert all(item.icon for item in nav_items)
    assert {item.key for item in nav_items} <= set(binding_by_key)
    assert all("switch_view" in binding_by_key[item.key].action for item in nav_items)
    assert "1-0 切换视图" in SuperMedicineTUI.shortcut_hint_text()
    assert "Enter 提交" in SuperMedicineTUI.shortcut_hint_text()
    assert "? 帮助" in SuperMedicineTUI.shortcut_hint_text()


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
    assert idle_status.focus == "焦点：输入栏"

    app._task_running = True
    running_status = app.status_text("llm")
    assert "任务执行中" in running_status.center
    assert "当前视图：LLM 管理" in running_status.right


def test_tui_dry_run_prints_modern_status_without_secrets(capsys):
    status = launch_tui(dry_run=True)
    output = capsys.readouterr().out

    assert "当前视图：对话" in output
    assert "快捷键：1-0 切换视图" in output
    assert "Enter 提交" in output
    assert "焦点：输入栏" in output
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
    assert "焦点：输入栏" in output
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

    assert app.view_title_text("workspace") == "工作区管理"
    assert app.view_title_text("llm") == "LLM 管理"
    assert app.view_title_text("experiment") == "实验指导器"
    assert app.view_title_text("log") == "Log 报告"
    assert app.status_text("workspace").focus == "焦点：输入栏"
    assert "当前视图：工作区管理" in app.status_text("workspace").right
    assert "1-0 切换视图" in app.shortcut_hint_text()
    assert "Tab/Shift+Tab" in app.shortcut_hint_text()


def test_tui_help_text_documents_actual_bindings_and_state_meanings():
    binding_keys = {binding.key for binding in SuperMedicineTUI.BINDINGS}

    for key in {
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
        "q",
        "f",
        "question_mark",
    }:
        assert key in binding_keys

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
        "1-0",
        "Tab/Shift+Tab",
        "Enter",
        "刷新",
        "危险操作",
        "LLM",
        "任务",
        "Q",
        "F",
        "?",
    ]:
        assert expected in help_text


def test_readme_tui_docs_match_bindings_and_preserve_boundaries():
    readme = (
        Path(__file__)
        .resolve()
        .parents[1]
        .joinpath("README.md")
        .read_text(encoding="utf-8")
    )

    for expected in [
        "`1`",
        "`2`",
        "`3`",
        "`4`",
        "`5`",
        "`6`",
        "`7`",
        "`8`",
        "`Tab`",
        "`Shift+Tab`",
        "`Enter`",
        "`f`",
        "`?`",
        "`q`",
    ]:
        assert expected in readme
    assert "LLM 状态" in readme
    assert "任务运行状态" in readme
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
        }
    )

    selector_blocks = [block.rsplit("}", 1)[-1] for block in stylesheet.split("{")[:-1]]
    selectors = "\n".join(selector_blocks)
    css_ids = set(re.findall(r"#([a-zA-Z0-9_-]+)", selectors))
    css_classes = set(re.findall(r"\.(-?[a-zA-Z_][a-zA-Z0-9_-]*)", selectors))

    assert css_ids <= declared_ids
    assert css_classes <= declared_classes

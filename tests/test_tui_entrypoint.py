from __future__ import annotations

import pytest

from Cli import CLI, main
from core.tui.app import launch_tui
from core.tui.i18n import LABELS, t


def test_tui_help_is_registered(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["supermedicine", "tui", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 0
    assert "启动中文 TUI 工作台" in capsys.readouterr().out


def test_chinese_labels_available():
    assert t("app_title") == "SuperMedicine 终端工作台"
    assert LABELS["permission_required"] == "需要权限确认"


def test_tui_dry_run_returns_chinese_status(capsys):
    status = launch_tui(dry_run=True)

    assert status.interactive is False
    assert status.title == "SuperMedicine 终端工作台"
    assert "基础组件已就绪" in status.message
    assert "SuperMedicine 终端工作台" in capsys.readouterr().out


def test_cli_tui_dry_run_entrypoint(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    status = CLI().tui(dry_run=True)

    assert status.interactive is False

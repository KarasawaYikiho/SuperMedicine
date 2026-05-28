from __future__ import annotations

import pytest
import yaml

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
                        "openai": {"api_format": "openai", "base_url": "https://openai.test/v1", "api_key": "sk-openai-entry", "model": "gpt-test"},
                        "anthropic": {"api_format": "anthropic", "base_url": "https://anthropic.test/v1", "api_key": secret, "model": "claude-test"},
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
    assert "anthropic" in output
    assert secret not in output

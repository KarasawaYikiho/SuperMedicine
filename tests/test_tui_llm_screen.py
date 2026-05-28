from __future__ import annotations

import yaml

from core.config_center import ConfigCenter
from core.tui.i18n import t
from core.tui.screens.llm_screen import LLMScreenController


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
    assert readiness == {"ok": True, "provider": "tui-provider", "message": t("llm_ready")}
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
                        "openai": {"api_format": "openai", "base_url": "https://openai.test/v1", "api_key": "sk-openai-tui", "model": "gpt-test"},
                        "anthropic": {"api_format": "anthropic", "base_url": "https://anthropic.test/v1", "api_key": "sk-anthropic-tui", "model": "claude-test"},
                    },
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    controller = LLMScreenController(tmp_path)

    assert controller.current_provider()["provider"] == "anthropic"
    assert ConfigCenter(config_dir / "config.yaml").get_llm_current_provider_name() == "anthropic"


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

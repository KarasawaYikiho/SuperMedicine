from __future__ import annotations

import inspect

import yaml

from core.config_center import ConfigCenter
from core.tui.i18n import t
from core.tui.screens.llm_screen import LLMView, LLMScreenController


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
    assert controller.readiness() == {"ok": True, "provider": "openai", "message": t("llm_ready")}
    assert ConfigCenter(config_dir / "config.yaml").get_llm_current_provider_name() == "openai"


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
    switch_result = controller.manager.switch_provider("needs-model", save=False)
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

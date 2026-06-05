from __future__ import annotations

import shutil

import yaml

from core.config_center import ConfigCenter
from core.kernel import Kernel
from core.llm_client import LLMClient
from core.llm_manager import LLMConfigManager
from permission.engine import PermissionEngine


def _write_config(path, *, provider="openai", last_provider=None):
    llm = {
        "provider": provider,
        "providers": {
            "openai": {
                "api_format": "openai",
                "base_url": "https://openai.test/v1",
                "api_key": "sk-openai-secret",
                "model": "gpt-test",
            },
            "anthropic": {
                "api_format": "anthropic",
                "base_url": "https://anthropic.test/v1",
                "api_key": "sk-anthropic-secret",
                "model": "claude-test",
            },
        },
    }
    if last_provider is not None:
        llm["last_provider"] = last_provider
    path.write_text(yaml.safe_dump({"llm": llm}, sort_keys=False), encoding="utf-8")


def test_manager_adds_lists_and_redacts_providers(tmp_path):
    config_path = tmp_path / "config.yaml"
    manager = LLMConfigManager(ConfigCenter(config_path), restore_on_startup=False)

    result = manager.add_provider(
        "openai",
        {
            "base_url": "https://openai.test/v1",
            "api_key": "sk-new-secret",
            "model": "gpt-test",
        },
        set_current=True,
    )

    assert result["ok"] is True
    providers = manager.list_providers()
    assert providers["openai"]["api_key"] == "[REDACTED]"
    assert "sk-new-secret" not in str(providers)
    assert ConfigCenter(config_path).get_llm_current_provider_name() == "openai"


def test_cli_add_switch_and_list_are_secret_safe_and_persist_current(
    tmp_path, monkeypatch, caplog
):
    from Cli import CLI

    secret = "sk-cli-manager-secret"
    monkeypatch.chdir(tmp_path)
    caplog.set_level("INFO", logger="Cli")

    add_result = CLI().llm_add(
        "cli-provider",
        base_url="https://cli-provider.local.test/v1",
        api_key=secret,
        model="cli-model",
        headers={"Authorization": f"Bearer {secret}", "X-Trace": "safe"},
        set_current=True,
    )
    switch_result = CLI().llm_switch("cli-provider")
    list_result = CLI().llm_list()
    reloaded = ConfigCenter(tmp_path / ".supermedicine" / "config.yaml")

    assert add_result["ok"] is True
    assert switch_result["ok"] is True
    assert list_result["current_provider"] == "cli-provider"
    assert list_result["last_provider"] == "cli-provider"
    assert list_result["providers"]["cli-provider"]["api_key"] == "[REDACTED]"
    assert (
        list_result["providers"]["cli-provider"]["headers"]["Authorization"]
        == "<redacted>"
    )
    assert reloaded.get_llm_current_provider_name() == "cli-provider"
    assert reloaded.get_llm_last_provider_name() == "cli-provider"
    assert reloaded.get_llm_provider_config("cli-provider")["api_key"] == secret
    assert secret not in str(add_result)
    assert secret not in str(switch_result)
    assert secret not in str(list_result)
    assert secret not in caplog.text


def test_switch_provider_persists_current_and_last_provider(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, provider="openai")
    manager = LLMConfigManager(ConfigCenter(config_path))

    result = manager.switch_provider("anthropic")

    assert result["ok"] is True
    reloaded = ConfigCenter(config_path)
    assert reloaded.get_llm_current_provider_name() == "anthropic"
    assert reloaded.get_llm_last_provider_name() == "anthropic"


def test_startup_restores_last_provider_before_install_default(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, provider="openai", last_provider="anthropic")

    manager = LLMConfigManager(ConfigCenter(config_path))

    assert manager.get_current_provider()["provider"] == "anthropic"


def test_startup_uses_install_default_when_no_last_provider(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, provider="openai")

    manager = LLMConfigManager(ConfigCenter(config_path))

    assert manager.get_current_provider()["provider"] == "openai"


def test_kernel_exposes_manager_and_restores_last_provider(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, provider="openai", last_provider="anthropic")
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()
    shutil.copyfile(
        PermissionEngine.default_policy_path(),
        policies_dir / PermissionEngine.DEFAULT_POLICY_FILENAME,
    )

    kernel = Kernel(
        config_path=config_path,
        plugins_dir=tmp_path / "plugins",
        policies_dir=policies_dir,
    )

    assert kernel.llm_manager.get_current_provider()["provider"] == "anthropic"


def test_incomplete_provider_returns_structured_secret_safe_error(tmp_path):
    config_path = tmp_path / "config.yaml"
    secret = "sk-should-not-leak"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "broken",
                    "providers": {
                        "broken": {"base_url": "", "api_key": secret, "model": ""},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    manager = LLMConfigManager(ConfigCenter(config_path))

    result = manager.switch_provider("broken")

    assert result["ok"] is False
    assert result["error"]["code"] == "missing_base_url"
    assert set(result["error"]["details"]["missing"]) == {"base_url", "model"}
    assert secret not in str(result)


def test_list_style_providers_survive_startup_and_can_switch_and_create_client(
    tmp_path,
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "local-openai",
                    "last_provider": "local-anthropic",
                    "providers": [
                        {
                            "provider": "local-openai",
                            "api_format": "openai",
                            "base_url": "https://local-openai.test/v1",
                            "api_key": "sk-local-openai-secret",
                            "model": "local-gpt",
                        },
                        {
                            "provider": "local-anthropic",
                            "api_format": "anthropic",
                            "base_url": "https://local-anthropic.test/v1",
                            "api_key": "sk-local-anthropic-secret",
                            "model": "local-claude",
                        },
                    ],
                }
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    manager = LLMConfigManager(ConfigCenter(config_path))

    providers = manager.list_providers()
    assert sorted(providers) == ["local-anthropic", "local-openai"]
    assert providers["local-openai"]["api_key"] == "[REDACTED]"
    assert "sk-local-openai-secret" not in str(providers)
    assert manager.get_current_provider()["provider"] == "local-anthropic"

    switch_result = manager.switch_provider("local-openai")
    client = manager.create_client()

    assert switch_result["ok"] is True
    assert isinstance(client, LLMClient)
    reloaded = ConfigCenter(config_path)
    assert sorted(reloaded.get_llm_providers()) == ["local-anthropic", "local-openai"]
    assert reloaded.get_llm_current_provider_name() == "local-openai"


def test_create_client_uses_restored_last_provider_not_install_default(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, provider="openai", last_provider="anthropic")

    client = LLMConfigManager(ConfigCenter(config_path)).create_client()

    assert isinstance(client, LLMClient)
    assert client.config.provider == "anthropic"
    assert client.config.model == "claude-test"


def test_create_client_after_switch_uses_new_current_provider(tmp_path):
    config_path = tmp_path / "config.yaml"
    _write_config(config_path, provider="openai", last_provider="anthropic")
    manager = LLMConfigManager(ConfigCenter(config_path))

    manager.switch_provider("openai")
    client = manager.create_client()

    assert isinstance(client, LLMClient)
    assert client.config.provider == "openai"
    assert client.config.model == "gpt-test"


def test_create_client_without_llm_config_returns_actionable_secret_safe_error(
    tmp_path,
):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump({"project": "missing-llm"}), encoding="utf-8")

    result = LLMConfigManager(ConfigCenter(config_path)).create_client()

    assert result["ok"] is False
    assert result["error"]["code"] == "missing_provider"
    assert "Install.py --init" in result["error"]["message"]
    assert ".supermedicine/config.yaml" in result["error"]["message"]
    assert "supermedicine llm add/switch" in result["error"]["message"]
    assert "TUI" in result["error"]["message"]
    assert "sk-" not in str(result).lower()

from __future__ import annotations


from core.config_center import ConfigCenter, DEFAULT_EXPERIMENT_GUIDE_CONFIG, DEFAULT_LOG_REPORT_CONFIG


class TestConfigCenter:
    """测试 ConfigCenter"""

    def test_get_set(self, tmp_path):
        """验证 set/get 读写正确"""
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)
        cc.set("key1", "value1")
        assert cc.get("key1") == "value1"
        assert cc.get("nonexistent") is None
        assert cc.get("nonexistent", "default") == "default"

    def test_experiment_guide_and_log_report_defaults_when_config_missing(self, tmp_path):
        """验证缺失用户配置时返回完整安全默认值。"""
        cc = ConfigCenter(tmp_path / "config.yaml")

        assert cc.get_experiment_guide_config() == DEFAULT_EXPERIMENT_GUIDE_CONFIG
        assert cc.get_log_report_config() == DEFAULT_LOG_REPORT_CONFIG

    def test_default_sections_merge_user_config_with_safe_defaults(self, tmp_path):
        """验证用户配置与默认值兼容合并。"""
        import yaml

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "experiment_guide": {"enabled": False},
                    "log_report": {"max_message_length": 123},
                }
            ),
            encoding="utf-8",
        )

        cc = ConfigCenter(config_path)

        experiment_guide = cc.get_experiment_guide_config()
        log_report = cc.get_log_report_config()
        assert experiment_guide["enabled"] is False
        assert experiment_guide["max_steps"] == DEFAULT_EXPERIMENT_GUIDE_CONFIG["max_steps"]
        assert log_report["max_message_length"] == 123
        assert log_report["max_records_per_session"] == DEFAULT_LOG_REPORT_CONFIG["max_records_per_session"]

    def test_save_and_reload(self, tmp_path):
        """验证 save() 持久化后重新加载正确"""
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)
        cc.set("project", "supermedicine")
        cc.set("version", "0.1.0")
        cc.save()

        # 重新加载
        cc2 = ConfigCenter(config_path)
        assert cc2.get("project") == "supermedicine"
        assert cc2.get("version") == "0.1.0"

    def test_env_override(self, tmp_path, monkeypatch):
        """验证 SM_* 环境变量覆盖"""
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)
        cc.set("test_key", "from_file")
        cc.save()

        # 设置环境变量
        monkeypatch.setenv("SM_TEST_KEY", "from_env")
        assert cc.get("test_key") == "from_env"

        # Save 不应包含环境变量值
        cc.save()
        cc3 = ConfigCenter(config_path)
        monkeypatch.delenv("SM_TEST_KEY", raising=False)
        assert cc3.get("test_key") == "from_file"

    def test_init_with_existing_file(self, tmp_path):
        """验证从已有文件加载"""
        import yaml
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({"app": "supermedicine", "debug": True}), encoding="utf-8")
        cc = ConfigCenter(config_path)
        assert cc.get("app") == "supermedicine"
        assert cc.get("debug") is True

    def test_get_llm_provider_config(self, tmp_path):
        """验证 LLM Provider 配置可按 provider 加载"""
        import yaml
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({
            "llm": {
                "provider": "anthropic",
                "providers": {
                    "openai": {
                        "api_format": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "api_key_env": "OPENAI_API_KEY",
                        "model": "gpt-test",
                    },
                    "anthropic": {
                        "api_format": "anthropic",
                        "base_url": "https://api.anthropic.com/v1",
                        "api_key_env": "ANTHROPIC_API_KEY",
                        "model": "claude-test",
                    },
                },
            }
        }), encoding="utf-8")
        cc = ConfigCenter(config_path)

        default_config = cc.get_llm_provider_config()
        openai_config = cc.get_llm_provider_config("openai")

        assert default_config["provider"] == "anthropic"
        assert default_config["api_format"] == "anthropic"
        assert openai_config["provider"] == "openai"
        assert openai_config["api_format"] == "openai"

    def test_get_llm_provider_config_has_no_implicit_openai_default(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump({"llm": {"provider": "", "providers": {}}}), encoding="utf-8")

        cc = ConfigCenter(config_path)

        assert cc.get_llm_provider_config() == {"provider": ""}

    def test_llm_provider_helpers_persist_multiple_providers_and_last_provider(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)

        cc.set_llm_provider_config("openai", {"base_url": "https://openai.test/v1", "api_key": "sk-openai", "model": "gpt-test"})
        cc.set_llm_provider_config("anthropic", {"base_url": "https://anthropic.test/v1", "api_key": "sk-anthropic", "model": "claude-test"})
        cc.set_llm_current_provider("openai")
        cc.set_llm_last_provider("anthropic")
        cc.save()

        reloaded = ConfigCenter(config_path)

        assert sorted(reloaded.get_llm_providers()) == ["anthropic", "openai"]
        assert reloaded.get_llm_current_provider_name() == "openai"
        assert reloaded.get_llm_last_provider_name() == "anthropic"
        assert "sk-openai" not in str(reloaded.get_llm_providers(redacted=True))

    def test_ensure_llm_config_preserves_list_style_providers(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.safe_dump({
            "llm": {
                "provider": "local-openai",
                "providers": [
                    {
                        "provider": "local-openai",
                        "api_format": "openai",
                        "base_url": "https://local-openai.test/v1",
                        "api_key": "sk-local-openai",
                        "model": "local-gpt",
                    },
                    {
                        "name": "local-anthropic",
                        "api_format": "anthropic",
                        "base_url": "https://local-anthropic.test/v1",
                        "api_key": "sk-local-anthropic",
                        "model": "local-claude",
                    },
                ],
            }
        }), encoding="utf-8")
        cc = ConfigCenter(config_path)

        llm_config = cc.ensure_llm_config()

        assert sorted(llm_config["providers"]) == ["local-anthropic", "local-openai"]
        assert cc.get_llm_provider_config("local-openai")["model"] == "local-gpt"
        assert cc.get_llm_provider_config("local-anthropic")["api_format"] == "anthropic"

    def test_manual_file_provider_addition_and_switch_is_normalized_and_secret_safe(self, tmp_path):
        import yaml
        config_path = tmp_path / "config.yaml"
        secret = "sk-file-added-secret"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "llm": {
                        "provider": "file-added",
                        "providers": {
                            "file-added": {
                                "api_format": "openai",
                                "base_url": "https://file-added.local.test/v1",
                                "api_key": secret,
                                "model": "file-added-model",
                                "headers": {"Authorization": f"Bearer {secret}", "X-Trace": "safe"},
                            }
                        },
                    }
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

        cc = ConfigCenter(config_path)
        provider = cc.get_llm_provider_config()
        redacted = cc.get_llm_provider_config(redacted=True)

        assert provider["provider"] == "file-added"
        assert provider["api_key"] == secret
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["headers"]["Authorization"] == "<redacted>"
        assert redacted["headers"]["X-Trace"] == "safe"
        assert secret not in str(redacted)

    def test_safe_all_redacts_query_params_authorization_and_passwd(self, tmp_path, monkeypatch):
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)
        secret = "sk-safe-all-secret"
        cc.set("callback", f"https://example.test/cb?api_key={secret}&ok=1")
        cc.set("database", {"passwd": secret, "url": f"postgres://u:password={secret}@db"})
        monkeypatch.setenv("SM_AUTHORIZATION", f"Bearer {secret}")

        safe = cc.safe_all()

        assert secret not in str(safe)
        assert "[REDACTED]" in str(safe)

    def test_diagnostics_reports_config_load_state_env_precedence_and_redacts(self, tmp_path, monkeypatch):
        config_path = tmp_path / "config.yaml"
        secret = "diagnostics-env-api-key-value-not-real"
        config_path.write_text(f"callback: https://example.test/cb?api_key={secret}\n", encoding="utf-8")
        monkeypatch.setenv("SM_LLM_API_KEY", secret)

        diagnostics = ConfigCenter(config_path).diagnostics()

        assert diagnostics["config_path"] == str(config_path)
        assert diagnostics["exists"] is True
        assert diagnostics["load_error"] == ""
        assert "SM_LLM_API_KEY" in diagnostics["env_override_keys"]
        assert diagnostics["precedence"] == ["SM_* environment variables", "config file", "code defaults"]
        assert secret not in str(diagnostics)
        assert diagnostics["config"]["llm-api-key"] == "[REDACTED]"
        assert "[REDACTED]" in str(diagnostics)

    def test_diagnose_llm_config_reports_missing_fields_and_redacts_provider(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        secret = "sk-llm-diagnostic-secret"
        config_path.write_text(
            "\n".join(
                [
                    "llm:",
                    "  provider: openai",
                    "  providers:",
                    "    openai:",
                    "      api_key: " + secret,
                ]
            ),
            encoding="utf-8",
        )

        diagnostic = ConfigCenter(config_path).diagnose_llm_config()

        assert diagnostic["ok"] is False
        assert diagnostic["stage"] == "config.llm"
        assert diagnostic["config_path"] == str(config_path)
        assert diagnostic["provider"] == "openai"
        assert "base_url" in diagnostic["missing"]
        assert "model" in diagnostic["missing"]
        assert diagnostic["hints"]["api_key"].startswith("Set providers.<provider>.api_key")
        assert secret not in str(diagnostic)
        assert diagnostic["providers"]["openai"]["api_key"] == "[REDACTED]"

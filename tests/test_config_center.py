from __future__ import annotations

import pytest

from core.config_center import (
    ConfigCenter,
    DEFAULT_EXPERIMENT_GUIDE_CONFIG,
    DEFAULT_LOG_REPORT_CONFIG,
)
from permission.access_mode import AccessDecisionStatus, FullAccessConfirmationRequired


class TestConfigCenter:
    def test_rag_config_has_required_local_first_defaults(self, tmp_path):
        config = ConfigCenter(tmp_path / "config.yaml")

        rag = config.get_rag_config()

        assert rag["provider"] == "local"
        assert rag["top_k"] == 6
        assert "enabled" not in rag

    def test_agents_config_defaults_to_single_with_bounded_execution(self, tmp_path):
        config = ConfigCenter(tmp_path / "config.yaml")

        assert config.get_agents_config() == {
            "mode": "single",
            "max_steps": 4,
            "max_retries": 1,
        }

    def test_agents_config_rejects_unknown_mode(self, tmp_path):
        config = ConfigCenter(tmp_path / "config.yaml")
        config.set("agents", {"mode": "swarm"})

        with pytest.raises(ValueError, match="agents.mode"):
            config.get_agents_config()

    """测试 ConfigCenter"""

    def test_get_set(self, tmp_path):
        """验证 set/get 读写正确"""
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)
        cc.set("key1", "value1")
        assert cc.get("key1") == "value1"
        assert cc.get("nonexistent") is None
        assert cc.get("nonexistent", "default") == "default"

    def test_experiment_guide_and_log_report_defaults_when_config_missing(
        self, tmp_path
    ):
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
        assert (
            experiment_guide["max_steps"]
            == DEFAULT_EXPERIMENT_GUIDE_CONFIG["max_steps"]
        )
        assert log_report["max_message_length"] == 123
        assert (
            log_report["max_records_per_session"]
            == DEFAULT_LOG_REPORT_CONFIG["max_records_per_session"]
        )

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
        config_path.write_text(
            yaml.dump({"app": "supermedicine", "debug": True}), encoding="utf-8"
        )
        cc = ConfigCenter(config_path)
        assert cc.get("app") == "supermedicine"
        assert cc.get("debug") is True

    def test_get_llm_provider_config(self, tmp_path):
        """验证 LLM Provider 配置可按 provider 加载"""
        import yaml

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            yaml.dump(
                {
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
                }
            ),
            encoding="utf-8",
        )
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
        config_path.write_text(
            yaml.dump({"llm": {"provider": "", "providers": {}}}), encoding="utf-8"
        )

        cc = ConfigCenter(config_path)

        assert cc.get_llm_provider_config() == {"provider": ""}

    def test_llm_provider_helpers_persist_multiple_providers_and_last_provider(
        self, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)

        cc.set_llm_provider_config(
            "openai",
            {
                "base_url": "https://openai.test/v1",
                "api_key": "sk-openai",
                "model": "gpt-test",
            },
        )
        cc.set_llm_provider_config(
            "anthropic",
            {
                "base_url": "https://anthropic.test/v1",
                "api_key": "sk-anthropic",
                "model": "claude-test",
            },
        )
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
        config_path.write_text(
            yaml.safe_dump(
                {
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
                }
            ),
            encoding="utf-8",
        )
        cc = ConfigCenter(config_path)

        llm_config = cc.ensure_llm_config()

        assert sorted(llm_config["providers"]) == ["local-anthropic", "local-openai"]
        assert cc.get_llm_provider_config("local-openai")["model"] == "local-gpt"
        assert (
            cc.get_llm_provider_config("local-anthropic")["api_format"] == "anthropic"
        )

    def test_manual_file_provider_addition_and_switch_is_normalized_and_secret_safe(
        self, tmp_path
    ):
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
                                "headers": {
                                    "Authorization": f"Bearer {secret}",
                                    "X-Trace": "safe",
                                },
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

    def test_safe_all_redacts_query_params_authorization_and_passwd(
        self, tmp_path, monkeypatch
    ):
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)
        secret = "sk-safe-all-secret"
        cc.set("callback", f"https://example.test/cb?api_key={secret}&ok=1")
        cc.set(
            "database", {"passwd": secret, "url": f"postgres://u:password={secret}@db"}
        )
        monkeypatch.setenv("SM_AUTHORIZATION", f"Bearer {secret}")

        safe = cc.safe_all()

        assert secret not in str(safe)
        assert "[REDACTED]" in str(safe)

    def test_diagnostics_reports_config_load_state_env_precedence_and_redacts(
        self, tmp_path, monkeypatch
    ):
        config_path = tmp_path / "config.yaml"
        secret = "diagnostics-env-api-key-value-not-real"
        config_path.write_text(
            f"callback: https://example.test/cb?api_key={secret}\n", encoding="utf-8"
        )
        monkeypatch.setenv("SM_LLM_API_KEY", secret)

        diagnostics = ConfigCenter(config_path).diagnostics()

        assert diagnostics["config_path"] == str(config_path)
        assert diagnostics["exists"] is True
        assert diagnostics["load_error"] == ""
        assert "SM_LLM_API_KEY" in diagnostics["env_override_keys"]
        assert diagnostics["precedence"] == [
            "SM_* environment variables",
            "config file",
            "code defaults",
        ]
        assert secret not in str(diagnostics)
        assert diagnostics["config"]["llm-api-key"] == "[REDACTED]"
        assert "[REDACTED]" in str(diagnostics)

    def test_diagnose_llm_config_reports_missing_fields_and_redacts_provider(
        self, tmp_path
    ):
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
        assert diagnostic["hints"]["api_key"].startswith(
            "Set providers.<provider>.api_key"
        )
        assert secret not in str(diagnostic)
        assert diagnostic["providers"]["openai"]["api_key"] == "[REDACTED]"

    def test_file_access_policy_switches_runtime_without_restart_and_requires_full_confirmation(
        self, tmp_path
    ):
        config_path = tmp_path / "config.yaml"
        project_root = tmp_path / "project"
        external_root = tmp_path / "external"
        project_root.mkdir()
        external_root.mkdir()
        cc = ConfigCenter(config_path)

        conservative = cc.get_file_access_policy(project_root)
        project_decision = conservative.decide(project_root / "notes.md", "write")
        external_read = conservative.decide(external_root / "data.csv", "read")
        external_write = conservative.decide(external_root / "out.csv", "write")

        assert project_decision.status == AccessDecisionStatus.ALLOWED
        assert external_read.status == AccessDecisionStatus.PROMPT_REQUIRED
        assert external_write.status == AccessDecisionStatus.DENIED
        with pytest.raises(FullAccessConfirmationRequired):
            cc.set_file_access_mode("full")

        cc.authorize_external_file_access_directory(external_root)
        authorized = cc.get_file_access_policy(project_root).decide(
            external_root / "out.csv", "write"
        )
        cc.set_file_access_mode("full", explicit_confirmation=True)
        full = cc.get_file_access_policy(project_root).decide(
            tmp_path / "elsewhere" / "system.txt", "delete"
        )

        assert authorized.status == AccessDecisionStatus.ALLOWED
        assert authorized.reason == "external_directory_explicitly_authorized"
        assert full.status == AccessDecisionStatus.ALLOWED
        assert "administrator" in full.helper.lower()
        assert "will not silently" in full.helper

    def test_file_access_authorized_roots_normalize_quoted_absolute_and_relative_paths(
        self, tmp_path, monkeypatch
    ):
        config_path = tmp_path / "config.yaml"
        project_root = tmp_path / "project"
        external_root = tmp_path / "external quoted"
        project_root.mkdir()
        external_root.mkdir()
        monkeypatch.chdir(tmp_path)
        cc = ConfigCenter(config_path)

        absolute_quoted = f'"{external_root}"'
        relative_quoted = "'external quoted'"

        config = cc.authorize_external_file_access_directory(absolute_quoted)
        policy = cc.get_file_access_policy(project_root)
        authorized = policy.decide(external_root / "out.csv", "write")

        assert config["authorized_external_roots"] == [str(external_root.resolve())]
        assert authorized.status == AccessDecisionStatus.ALLOWED
        assert authorized.reason == "external_directory_explicitly_authorized"

        cc.authorize_external_file_access_directory(relative_quoted)
        assert cc.get_file_access_config()["authorized_external_roots"] == [
            str(external_root.resolve())
        ]

        revoked = cc.revoke_external_file_access_directory(relative_quoted)

        assert revoked["authorized_external_roots"] == []


# ═══ Path Normalization Tests ═══


class TestNormalizeUserDirectoryPath:
    """Test _normalize_user_directory_path handles diverse user inputs."""

    def test_plain_absolute_path(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "data"
        target.mkdir()

        result = _normalize_user_directory_path(str(target))

        assert result == target.resolve()

    def test_double_quoted_absolute_path(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "quoted dir"
        target.mkdir()
        quoted = f'"{target}"'

        result = _normalize_user_directory_path(quoted)

        assert result == target.resolve()

    def test_single_quoted_absolute_path(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "single quoted"
        target.mkdir()
        quoted = f"'{target}'"

        result = _normalize_user_directory_path(quoted)

        assert result == target.resolve()

    def test_relative_path_resolves_from_cwd(self, tmp_path, monkeypatch):
        from core.config_center import _normalize_user_directory_path

        monkeypatch.chdir(tmp_path)
        (tmp_path / "relative").mkdir()

        result = _normalize_user_directory_path("relative")

        assert result == (tmp_path / "relative").resolve()

    def test_relative_quoted_path_resolves_from_cwd(self, tmp_path, monkeypatch):
        from core.config_center import _normalize_user_directory_path

        monkeypatch.chdir(tmp_path)
        (tmp_path / "rel quoted").mkdir()

        result = _normalize_user_directory_path("'rel quoted'")

        assert result == (tmp_path / "rel quoted").resolve()

    def test_path_object_passes_through(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "pathobj"
        target.mkdir()

        result = _normalize_user_directory_path(target)

        assert result == target.expanduser().resolve()

    def test_empty_string_resolves_to_cwd(self, tmp_path, monkeypatch):
        from core.config_center import _normalize_user_directory_path

        monkeypatch.chdir(tmp_path)

        result = _normalize_user_directory_path("")

        assert result == tmp_path.resolve()

    def test_whitespace_stripped(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "spaced"
        target.mkdir()
        padded = f"  {target}  "

        result = _normalize_user_directory_path(padded)

        assert result == target.resolve()

    def test_path_with_spaces_unquoted(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "my data"
        target.mkdir()

        result = _normalize_user_directory_path(str(target))

        assert result == target.resolve()

    def test_path_with_special_chars(self, tmp_path):
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "data-v2.0"
        target.mkdir()

        result = _normalize_user_directory_path(str(target))

        assert result == target.resolve()

    def test_shlex_quoted_path_with_spaces(self, tmp_path):
        """shlex-split handles quoted paths with spaces correctly."""
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "program files"
        target.mkdir()
        # shlex with posix=False preserves the quotes on Windows
        quoted = f'"{target}"'

        result = _normalize_user_directory_path(quoted)

        assert result == target.resolve()

    def test_normalized_path_deduplicates_different_representations(self, tmp_path):
        """Different quoting styles for the same path normalize to identical results."""
        from core.config_center import _normalize_user_directory_path

        target = tmp_path / "shared"
        target.mkdir()
        plain = str(target)
        double_quoted = f'"{target}"'
        single_quoted = f"'{target}'"

        results = {
            _normalize_user_directory_path(plain),
            _normalize_user_directory_path(double_quoted),
            _normalize_user_directory_path(single_quoted),
        }

        assert len(results) == 1

    def test_nonexistent_path_resolves_without_error(self, tmp_path):
        """Normalization resolves even nonexistent paths (no existence check)."""
        from core.config_center import _normalize_user_directory_path

        nonexistent = tmp_path / "does_not_exist_yet"

        result = _normalize_user_directory_path(str(nonexistent))

        assert result == nonexistent.resolve()


class TestAuthorizeExternalRootPathNormalization:
    """Test that authorize/revoke normalizes paths for consistent deduplication."""

    def test_quoted_and_unquoted_same_directory_dedup(self, tmp_path):
        """Quoted and unquoted versions of the same directory are deduplicated."""
        external = tmp_path / "shared data"
        external.mkdir()
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)

        cc.authorize_external_file_access_directory(str(external))
        cc.authorize_external_file_access_directory(f'"{external}"')

        roots = cc.get_file_access_config()["authorized_external_roots"]
        assert len(roots) == 1
        assert roots[0] == str(external.resolve())

    def test_relative_and_absolute_same_directory_dedup(self, tmp_path, monkeypatch):
        """Relative and absolute paths to the same directory are deduplicated."""
        external = tmp_path / "relative_test"
        external.mkdir()
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)

        cc.authorize_external_file_access_directory(str(external.resolve()))
        cc.authorize_external_file_access_directory("relative_test")

        roots = cc.get_file_access_config()["authorized_external_roots"]
        assert len(roots) == 1

    def test_revoke_by_any_normalized_form_removes_directory(self, tmp_path):
        """Revoking by any valid normalized path form removes the directory."""
        external = tmp_path / "revoke test"
        external.mkdir()
        config_path = tmp_path / "config.yaml"
        cc = ConfigCenter(config_path)

        cc.authorize_external_file_access_directory(str(external))
        assert len(cc.get_file_access_config()["authorized_external_roots"]) == 1

        cc.revoke_external_file_access_directory(f'"{external}"')

        assert cc.get_file_access_config()["authorized_external_roots"] == []

from __future__ import annotations


from core.config_center import ConfigCenter


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

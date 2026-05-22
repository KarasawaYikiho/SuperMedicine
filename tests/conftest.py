"""共享 pytest fixtures"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def sample_config_yaml(tmp_path) -> Path:
    """创建含基本配置的 config.yaml，返回文件路径"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"project": "test", "debug": True}), encoding="utf-8")
    return config_path


@pytest.fixture
def sample_policy_dir(tmp_path) -> Path:
    """创建含默认策略文件的 policies 目录，返回目录路径"""
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    policy_data = {
        "agent_id": "test_agent",
        "role": "tester",
        "security_level": "standard",
        "permissions": {
            "allowed": [
                {"action": "read", "scope": "*"},
                {"action": "execute", "scope": "*"},
            ],
            "denied": [
                {"action": "write", "scope": "*"},
            ],
            "hard_limits": {
                "max_files_per_session": 10,
                "max_tool_calls_per_minute": 5,
            },
        },
    }
    (policy_dir / "test.yaml").write_text(yaml.dump(policy_data), encoding="utf-8")
    return policy_dir


@pytest.fixture
def sample_plugin_dir(tmp_path) -> Path:
    """创建含 plugin.yaml 的插件目录，返回目录路径"""
    plugin_dir = tmp_path / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True)
    plugin_yaml = {
        "name": "test-plugin",
        "version": "0.1.0",
        "type": "tool",
        "provides": ["test.action"],
    }
    (plugin_dir / "plugin.yaml").write_text(yaml.dump(plugin_yaml), encoding="utf-8")
    return plugin_dir.parent


@pytest.fixture
def empty_audit_log(tmp_path) -> Path:
    """返回空 audit log 文件路径"""
    log_path = tmp_path / "audit.jsonl"
    log_path.write_text("", encoding="utf-8")
    return log_path

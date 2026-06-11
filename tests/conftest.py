"""共享 Pytest Fixtures"""

from __future__ import annotations

from pathlib import Path
import urllib.request

import pytest
import yaml


@pytest.fixture(autouse=True)
def block_real_network(monkeypatch):
    """Prevent accidental real HTTP access from tests.

    Individual tests that intentionally exercise HTTP request construction must
    monkeypatch ``urllib.request.urlopen`` with a local fake response.
    """

    def _blocked_urlopen(*args, **kwargs):
        raise AssertionError("Real network access is forbidden in tests")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen)


@pytest.fixture
def sample_config_yaml(tmp_path) -> Path:
    """创建含基本配置的 Config.YAML，返回文件路径"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.dump({"project": "test", "debug": True}), encoding="utf-8"
    )
    return config_path


@pytest.fixture
def sample_policy_dir(tmp_path) -> Path:
    """创建含默认策略文件的 Policies 目录，返回目录路径"""
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
    """创建含 Plugin.YAML 的插件目录，返回目录路径"""
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
    """返回空 Audit Log 文件路径"""
    log_path = tmp_path / "audit.jsonl"
    log_path.write_text("", encoding="utf-8")
    return log_path


@pytest.fixture
def database(tmp_path):
    """Provide an in-memory-like SQLite database for testing.

    Uses a temporary file-based database so that the full Database lifecycle
    (connect / disconnect / context manager) can be exercised without
    polluting the real ``.supermedicine`` directory.
    """
    from core.database.database import Database

    db_path = tmp_path / "test.db"
    db = Database(db_path=db_path)
    db.connect()
    yield db
    db.disconnect()


@pytest.fixture
def kernel(tmp_path):
    """Provide a fully initialised Kernel instance with temp directories."""
    import shutil
    import yaml

    from core.kernel import Kernel
    from permission.engine import PermissionEngine

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"project": "test"}), encoding="utf-8")
    (tmp_path / "plugins").mkdir()
    (tmp_path / "policies").mkdir()
    shutil.copyfile(
        PermissionEngine.default_policy_path(),
        tmp_path / "policies" / PermissionEngine.DEFAULT_POLICY_FILENAME,
    )
    return Kernel(
        config_path=config_path,
        plugins_dir=tmp_path / "plugins",
        policies_dir=tmp_path / "policies",
    )


@pytest.fixture
def tmp_workspace(tmp_path) -> Path:
    """Create a temporary workspace directory with basic structure.

    Returns the workspace root path.  Useful for tests that need a
    writable workspace without touching the real project tree.
    """
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "data").mkdir()
    (ws / "output").mkdir()
    return ws

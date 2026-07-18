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
        plugins_dir="plugins",
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


def _has_exact_child_name(directory: Path, filename: str) -> bool:
    """Return whether a directory contains an entry with this exact spelling.

    Path.exists()/is_file() are not sufficient here because Windows filesystems are
    commonly case-insensitive: ``Path("install_entry.py").is_file()`` can report true
    when only ``install_entry.py`` exists with different casing.
    """
    return filename in {child.name for child in directory.iterdir()}


def _supports_case_distinct_names(directory: Path) -> bool:
    """Return whether this filesystem location can hold exact case-only siblings."""
    upper = directory / "CaseProbe.tmp"
    lower = directory / "caseprobe.tmp"
    try:
        upper.write_text("upper", encoding="utf-8")
        lower.write_text("lower", encoding="utf-8")
        return _has_exact_child_name(directory, upper.name) and _has_exact_child_name(
            directory, lower.name
        )
    finally:
        for path in (upper, lower):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _cp1252_stdio_env() -> dict[str, str]:
    """Return environment dict forcing cp1252 stdio encoding."""
    import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    return env


@pytest.fixture
def read_pyproject() -> dict:
    """Read and return pyproject.toml as a dict."""
    import re
    try:
        import tomllib
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]

    path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    if tomllib is not None:
        with path.open("rb") as f:
            return tomllib.load(f)
    text = path.read_text(encoding="utf-8")
    result: dict = {"project": {}, "tool": {"setuptools": {"package-data": {}}}}
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if version_match:
        result["project"]["version"] = version_match.group(1)
    optional_dependencies_match = re.search(
        r"^\[project\.optional-dependencies\]\s*$(.*?)(?=^\[|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if optional_dependencies_match:
        dev_match = re.search(
            r"^dev\s*=\s*\[(.*?)\]",
            optional_dependencies_match.group(1),
            re.MULTILINE | re.DOTALL,
        )
        if dev_match:
            result["project"].setdefault("optional-dependencies", {})["dev"] = (
                re.findall(r'"([^"]+)"', dev_match.group(1))
            )
    current_package_data_key = None
    for line in text.splitlines():
        package_data_match = re.match(r"^(core|installer)\s*=\s*\[", line)
        if package_data_match:
            current_package_data_key = package_data_match.group(1)
            entries = re.findall(r'"([^"]+)"', line)
            result["tool"]["setuptools"]["package-data"][current_package_data_key] = entries
        elif current_package_data_key and line.strip().startswith("]"):
            current_package_data_key = None
    return result


@pytest.fixture
def tracked_files() -> list[str]:
    """Return paths currently present in the Git index."""
    import subprocess
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]

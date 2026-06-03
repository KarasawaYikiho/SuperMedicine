from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _cp1252_stdio_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    return env


def _write_minimal_import_stubs(workspace: Path) -> None:
    """Provide non-installer imports so tests isolate optional installer import behavior."""

    core_llm_dir = workspace / "core" / "llm_providers"
    core_llm_dir.mkdir(parents=True)
    (workspace / "core" / "__init__.py").write_text("", encoding="utf-8")
    (core_llm_dir / "__init__.py").write_text("", encoding="utf-8")
    (core_llm_dir / "config.py").write_text(
        textwrap.dedent(
            """
            class LLMProviderConfig:
                def __init__(self, base_url='https://example.test/v1'):
                    self.base_url = base_url

                @classmethod
                def from_mapping(cls, provider, mapping):
                    return cls(mapping.get('base_url', 'https://example.test/v1'))

                def missing_fields(self):
                    return []
            """
        ),
        encoding="utf-8",
    )
    (workspace / "core" / "redaction.py").write_text(
        "def redact_sensitive(value):\n    return value\n",
        encoding="utf-8",
    )
    (workspace / "core" / "serialization.py").write_text(
        "def json_ready(value):\n    return value\n",
        encoding="utf-8",
    )

    permission_dir = workspace / "permission"
    permission_dir.mkdir()
    (permission_dir / "__init__.py").write_text("", encoding="utf-8")
    (permission_dir / "policy.py").write_text(
        "def ensure_default_policy(project_dir, repo_root):\n    return None\n",
        encoding="utf-8",
    )


def _copy_install_entrypoint_without_installer_package(workspace: Path) -> Path:
    install_path = workspace / "Install.py"
    install_path.write_text((REPO_ROOT / "Install.py").read_text(encoding="utf-8"), encoding="utf-8")
    _write_minimal_import_stubs(workspace)
    assert not (workspace / "installer").exists()
    return install_path


def _copy_cli_entrypoint_without_installer_package(workspace: Path) -> Path:
    cli_path = workspace / "Cli.py"
    cli_path.write_text((REPO_ROOT / "Cli.py").read_text(encoding="utf-8"), encoding="utf-8")
    (workspace / "Install.py").write_text((REPO_ROOT / "Install.py").read_text(encoding="utf-8"), encoding="utf-8")
    _write_minimal_import_stubs(workspace)
    assert not (workspace / "installer").exists()
    return cli_path


def _run_isolated_install(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "Install.py", *args],
        cwd=workspace,
        env=_cp1252_stdio_env(),
        text=True,
        encoding="cp1252",
        capture_output=True,
        check=False,
    )


def _run_isolated_cli(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "Cli.py", *args],
        cwd=workspace,
        env=_cp1252_stdio_env(),
        text=True,
        encoding="cp1252",
        capture_output=True,
        check=False,
    )


def test_install_help_works_when_optional_installer_package_is_absent(tmp_path):
    """Regression: isolated --help must survive strict Windows cp1252 stdio."""

    _copy_install_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_install(tmp_path, "--help")

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "--release-exe" in output
    assert "usage:" in output.lower()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output
    assert "UnicodeEncodeError" not in output


def test_init_entry_path_does_not_require_optional_exe_release_module(tmp_path):
    """Core install/init should remain usable even without optional Exe release code."""

    _copy_install_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_install(
        tmp_path,
        "--init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-installer-entrypoint",
        "--model",
        "gpt-test",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output


def test_release_exe_missing_optional_module_reports_actionable_error(tmp_path):
    """Explicit --release-exe may require installer code, but the error must be user-facing."""

    _copy_install_entrypoint_without_installer_package(tmp_path)
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")

    result = _run_isolated_install(tmp_path, "--release-exe", str(source), "--exe-dry-run")

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "--release-exe" in output or "installer" in output.lower()
    assert "Install.py" in output or "pip install" in output or "release package" in output
    assert "ModuleNotFoundError" not in output
    assert "Traceback" not in output


def test_cli_help_works_when_optional_installer_package_is_absent(tmp_path):
    """Regression: isolated CLI help must survive strict Windows cp1252 stdio."""

    _copy_cli_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_cli(tmp_path, "init", "--help")

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert "--release-exe" in output
    assert "usage:" in output.lower()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output
    assert "UnicodeEncodeError" not in output


def test_cli_init_without_release_exe_does_not_require_optional_installer_package(tmp_path):
    """Core CLI init should remain usable without optional Exe release code."""

    _copy_cli_entrypoint_without_installer_package(tmp_path)

    result = _run_isolated_cli(
        tmp_path,
        "init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-cli-entrypoint",
        "--model",
        "gpt-test",
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0
    assert (tmp_path / ".supermedicine" / "config.yaml").exists()
    assert "ModuleNotFoundError" not in output
    assert "No module named 'installer'" not in output


def test_cli_release_exe_missing_optional_module_reports_actionable_error(tmp_path):
    """Explicit CLI --release-exe should produce a user-facing missing-package error."""

    _copy_cli_entrypoint_without_installer_package(tmp_path)
    source = tmp_path / "SuperMedicine.exe"
    source.write_bytes(b"fake exe bytes")

    result = _run_isolated_cli(
        tmp_path,
        "init",
        "--provider",
        "openai",
        "--base-url",
        "https://openai.local.test/v1",
        "--api-key",
        "sk-test-cli-release-exe",
        "--model",
        "gpt-test",
        "--release-exe",
        str(source),
        "--exe-dry-run",
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "--release-exe" in output or "installer" in output.lower()
    assert "Cli.py" in output or "release package" in output
    assert "ModuleNotFoundError" not in output
    assert "Traceback" not in output

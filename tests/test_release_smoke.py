from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR_NAME = "SuperMedicine Beta0.4.1"
CRITICAL_RELEASE_PATHS = (
    "Install.py",
    "core",
    "core/__init__.py",
    "permission",
    "permission/__init__.py",
    "installer",
    "installer/__init__.py",
    "installer/exe_release.py",
)
CRITICAL_IMPORTS = (
    "core",
    "permission",
    "installer",
    "installer.exe_release",
)


def _cp1252_stdio_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    return env


def _copy_release_tree(tmp_path: Path) -> Path:
    """Build a representative extracted release directory in a temp workspace."""

    release_dir = tmp_path / RELEASE_DIR_NAME
    release_dir.mkdir()
    shutil.copy2(REPO_ROOT / "Install.py", release_dir / "Install.py")

    for package_name in ("core", "permission", "installer"):
        shutil.copytree(
            REPO_ROOT / package_name,
            release_dir / package_name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    return release_dir


def _run_release_python(
    release_dir: Path,
    *args: str,
    env: dict[str, str] | None = None,
    encoding: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=release_dir,
        env=env,
        text=True,
        encoding=encoding,
        capture_output=True,
        check=False,
    )


def test_extracted_release_directory_installer_entrypoint_smoke(tmp_path):
    release_dir = _copy_release_tree(tmp_path)

    for relative_path in CRITICAL_RELEASE_PATHS:
        assert (release_dir / relative_path).exists(), (
            f"Release layout missing required package/file: {relative_path}"
        )

    import_result = _run_release_python(
        release_dir,
        "-c",
        "import core, permission, installer, installer.exe_release",
    )
    import_output = import_result.stdout + import_result.stderr
    assert import_result.returncode == 0, (
        "Extracted release critical packages/files must be importable: "
        f"{', '.join(CRITICAL_IMPORTS)}\n{import_output}"
    )

    help_result = _run_release_python(
        release_dir,
        "Install.py",
        "--help",
        env=_cp1252_stdio_env(),
        encoding="cp1252",
    )
    help_output = help_result.stdout + help_result.stderr
    assert help_result.returncode == 0, help_output
    assert "usage:" in help_output.lower()
    assert "--release-exe" in help_output
    assert "UnicodeEncodeError" not in help_output

    fake_exe = release_dir / "SuperMedicine.exe"
    fake_exe.write_bytes(b"fake exe bytes for release smoke dry-run")
    dry_run_result = _run_release_python(
        release_dir,
        "Install.py",
        "--release-exe",
        str(fake_exe),
        "--desktop-dir",
        str(tmp_path / "Desktop"),
        "--exe-dry-run",
    )
    dry_run_output = dry_run_result.stdout + dry_run_result.stderr
    assert dry_run_result.returncode == 0, dry_run_output
    assert "dry-run" in dry_run_output.lower()
    assert not (tmp_path / "Desktop").exists()

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
    "dist/SuperMedicine.exe",
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
INSTALLER_EXE_RELEASE_PATHS = (
    "dist/SuperMedicine.exe",
    "SuperMedicine.exe",
)
INSTALLER_EXE_NAME = "SuperMedicineInstaller.exe"
CANONICAL_LOWERCASE_INSTALL = "install.py"


def _cp1252_stdio_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    return env


# Step-2 CI investigation note:
# ``Install.py`` delegates to ``installer.entrypoint.main()``, which calls
# ``_configure_stdio_errors()`` and reconfigures stdout/stderr with
# ``errors="backslashreplace"``.  When release-smoke subprocesses run with
# ``PYTHONIOENCODING=cp1252`` and parent decoding also uses cp1252, user-facing
# Chinese log text may be emitted as escaped ``\u....`` sequences instead of
# literal readable Chinese.  The dry-run assertion near the payload extraction
# smoke must therefore accept either the readable signal
# ``程序文件释放 dry-run`` or its escaped representation; otherwise the failure
# is an assertion/encoding mismatch, not a release-copy behavior failure.
# Related production/release files for any later fix decision are
# ``Install.py``/``install.py``, ``installer/entrypoint.py``,
# ``installer/exe_release.py``, ``.github/workflows/ci.yml``, ``setup.py``, and
# ``pyproject.toml``.
PAYLOAD_DRY_RUN_SIGNAL = "程序文件释放 dry-run"
PAYLOAD_DRY_RUN_ESCAPED_SIGNAL = PAYLOAD_DRY_RUN_SIGNAL.encode(
    "cp1252",
    errors="backslashreplace",
).decode("cp1252")
PAYLOAD_DRY_RUN_SIGNALS = (
    PAYLOAD_DRY_RUN_SIGNAL,
    PAYLOAD_DRY_RUN_ESCAPED_SIGNAL,
)


def _has_exact_child_name(directory: Path, filename: str) -> bool:
    return filename in {child.name for child in directory.iterdir()}


def _supports_case_distinct_names(directory: Path) -> bool:
    upper = directory / "CaseProbe.tmp"
    lower = directory / "caseprobe.tmp"
    try:
        upper.write_text("upper", encoding="utf-8")
        lower.write_text("lower", encoding="utf-8")
        return _has_exact_child_name(directory, upper.name) and _has_exact_child_name(directory, lower.name)
    finally:
        for path in (upper, lower):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _copy_release_tree(tmp_path: Path) -> Path:
    """Build a representative extracted release directory in a temp workspace."""

    release_dir = tmp_path / RELEASE_DIR_NAME
    release_dir.mkdir()
    shutil.copy2(REPO_ROOT / "Install.py", release_dir / "Install.py")
    lowercase_source = _read_git_index_file("install.py")
    if lowercase_source is not None and _supports_case_distinct_names(release_dir):
        (release_dir / "install.py").write_text(lowercase_source, encoding="utf-8")

    for package_name in ("core", "permission", "installer"):
        shutil.copytree(
            REPO_ROOT / package_name,
            release_dir / package_name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    release_dist_exe = release_dir / "dist" / "SuperMedicine.exe"
    release_dist_exe.parent.mkdir()
    release_dist_exe.write_bytes(b"fake dist exe bytes for payload smoke dry-run")

    return release_dir


def _read_git_index_file(path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f":{path}"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


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
    if _supports_case_distinct_names(release_dir):
        assert _has_exact_child_name(release_dir, CANONICAL_LOWERCASE_INSTALL)
    else:
        assert _read_git_index_file(CANONICAL_LOWERCASE_INSTALL) is not None, (
            "Release smoke cannot materialize case-only install.py/Install.py siblings on this filesystem, "
            "so exact lowercase install.py must remain verified through the git index and CI Zip contract."
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

    payload_dry_run_result = _run_release_python(
        release_dir,
        "Install.py",
        "--extract-release-to",
        str(tmp_path / "Installed"),
        "--release-payload-root",
        str(release_dir),
        "--exe-dry-run",
    )
    payload_output = payload_dry_run_result.stdout + payload_dry_run_result.stderr
    assert payload_dry_run_result.returncode == 0, payload_output
    assert any(signal in payload_output for signal in PAYLOAD_DRY_RUN_SIGNALS), payload_output
    assert not (tmp_path / "Installed").exists()


def test_ci_release_artifacts_include_installer_usable_exe_or_dist_path():
    """Regression baseline: published CI artifacts must contain an Exe path Install.py can release."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    # Step-2 CI investigation note:
    # These workflow assertions map the release-smoke failures to the concrete
    # CI artifact contract: ``.github/workflows/ci.yml`` must publish an app Exe
    # path usable by ``Install.py --release-exe`` and must stage the standalone
    # installer payload with both case-only wrappers.  If these fail, inspect the
    # workflow packaging scripts together with ``installer/exe_release.py``'s
    # payload requirements and the wrapper preservation logic in ``setup.py`` /
    # package metadata in ``pyproject.toml`` before changing production code.

    assert any(path in workflow for path in INSTALLER_EXE_RELEASE_PATHS), (
        "CI/release workflow must publish either dist/SuperMedicine.exe or "
        "SuperMedicine.exe so Install.py --release-exe has a documented, packaged source path."
    )
    assert "actions/upload-artifact" in workflow
    assert any(f"--release-exe {path}" in workflow or f"--release-exe {path!r}" in workflow for path in INSTALLER_EXE_RELEASE_PATHS)


def test_ci_release_artifacts_include_standalone_installer_exe_and_shared_payload():
    """Published CI artifacts must include the installer Exe next to the app Exe."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "--name SuperMedicineInstaller" in workflow
    assert f"dist/{INSTALLER_EXE_NAME}" in workflow
    assert f"stage / \"{INSTALLER_EXE_NAME}\"" in workflow
    assert "release_payload" in workflow
    assert "--extract-release-to" in workflow
    assert "dist/SuperMedicine.exe" in workflow
    assert "python -m pip install build pyinstaller" in workflow
    assert "./dist/SuperMedicineInstaller.exe --help" in workflow
    assert "./dist/SuperMedicineInstaller.exe --extract-release-to" in workflow
    assert '["git", "show", ":install.py"]' in workflow
    assert "archive.writestr(lowercase_entry" in workflow
    assert "git archive HEAD" not in workflow


def test_release_docs_describe_ci_artifact_layout_and_install_py_roles():
    """Docs must keep the user/automation release layout contract visible."""

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    install = (REPO_ROOT / "INSTALL.md").read_text(encoding="utf-8")
    combined = readme + "\n" + install

    assert "SuperMedicineInstaller.exe" in combined
    assert "dist/SuperMedicine.exe" in combined
    assert "python Install.py" in combined
    assert "--extract-release-to" in combined
    assert "--release-exe" in combined
    assert "--exe-dry-run" in combined
    assert "ModuleNotFoundError: No module named 'installer'" in combined
    assert "Exe source does not exist" in combined
    assert "Ordinary users" in combined
    assert "python install.py" in combined
    assert "with no flags" in combined
    assert "Advanced automation / CI" in combined
    assert "staged release payload" in combined
    assert "--release-payload-root . " not in combined
    assert "--release-payload-root .\\" not in combined
    assert "What the interactive questions mean" in install
    assert "Source `python install.py` usually defaults to no" in install
    assert "`SuperMedicineInstaller.exe` defaults to yes" in install

from __future__ import annotations

import os
import re
import shutil
import shlex
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
PYINSTALLER_STANDALONE_SPEC_PATH = ".pyinstaller-installer-spec"
RUNTIME_DEPENDENCY_INSTALL_RE = re.compile(
    r"^\s*python\s+-m\s+pip\s+install\b[^\n]*(?:"
    r"-e\s+['\"]?\.(?:\[[^\]\n]+\])?['\"]?|"
    r"['\"]?\.(?:\[[^\]\n]+\])?['\"]?|"
    r"-r\s+requirements\.txt\b|"
    r"\bPyYAML\b|\bpyyaml\b"
    r")",
    re.MULTILINE,
)


def _extract_bash_pyinstaller_command(workflow: str, exe_name: str) -> list[str]:
    for line in workflow.splitlines():
        command = line.strip()
        if (
            command.startswith("python -m PyInstaller")
            and f"--name {exe_name}" in command
        ):
            return shlex.split(command, posix=True)
    raise AssertionError(
        f"Could not find PyInstaller command for --name {exe_name} in CI workflow"
    )


def _token_value(tokens: list[str], option: str) -> str | None:
    try:
        option_index = tokens.index(option)
    except ValueError:
        return None
    try:
        return tokens[option_index + 1]
    except IndexError as exc:
        raise AssertionError(
            f"CI PyInstaller command has {option} without a following value"
        ) from exc


def _looks_absolute_or_resolved_for_ci_shell(source: str) -> bool:
    return (
        source.startswith(("/", "$", "${"))
        or re.match(r"^[A-Za-z]:[\\/]", source) is not None
        or "resolve" in source.lower()
        or "realpath" in source.lower()
        or "pwd" in source.lower()
    )


def _relative_source_is_staged_under_specpath(source: str, specpath: str) -> bool:
    normalized_source = source.replace("\\", "/").lstrip("./")
    normalized_specpath = specpath.replace("\\", "/").lstrip("./")
    return normalized_source == normalized_specpath or normalized_source.startswith(
        f"{normalized_specpath}/"
    )


PACKAGING_TOOLING_WITH_RUNTIME_INSTALL_RE = re.compile(
    r"^\s*python\s+-m\s+pip\s+install\b"
    r"(?=[^\n]*\bbuild\b)"
    r"(?=[^\n]*\bpyinstaller\b)"
    r"[^\n]*(?:"
    r"-e\s+['\"]?\.(?:\[[^\]\n]+\])?['\"]?|"
    r"['\"]?\.(?:\[[^\]\n]+\])?['\"]?|"
    r"-r\s+requirements\.txt\b|"
    r"\bPyYAML\b|\bpyyaml\b"
    r")",
    re.IGNORECASE | re.MULTILINE,
)


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
        return _has_exact_child_name(directory, upper.name) and _has_exact_child_name(
            directory, lower.name
        )
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
    assert any(signal in payload_output for signal in PAYLOAD_DRY_RUN_SIGNALS), (
        payload_output
    )
    assert not (tmp_path / "Installed").exists()


def test_ci_release_artifacts_include_installer_usable_exe_or_dist_path():
    """Regression baseline: published CI artifacts must contain an Exe path Install.py can release."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

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
    assert any(
        f"--release-exe {path}" in workflow or f"--release-exe {path!r}" in workflow
        for path in INSTALLER_EXE_RELEASE_PATHS
    )


def test_ci_release_artifacts_include_standalone_installer_exe_and_shared_payload():
    """Published CI artifacts must include the installer Exe next to the app Exe."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "--name SuperMedicineInstaller" in workflow
    assert f"dist/{INSTALLER_EXE_NAME}" in workflow
    assert f'stage / "{INSTALLER_EXE_NAME}"' in workflow
    assert "release_payload" in workflow
    assert "--extract-release-to" in workflow
    assert "dist/SuperMedicine.exe" in workflow
    assert PACKAGING_TOOLING_WITH_RUNTIME_INSTALL_RE.search(workflow), (
        "CI packaging smoke must install build tooling (build, pyinstaller) together with "
        "runtime/project dependencies before installer entrypoint smoke commands."
    )
    assert "./dist/SuperMedicineInstaller.exe --help" in workflow
    assert "./dist/SuperMedicineInstaller.exe --extract-release-to" in workflow
    assert '["git", "show", ":install.py"]' in workflow
    assert "archive.writestr(lowercase_entry" in workflow
    assert "git archive HEAD" not in workflow


def test_ci_standalone_installer_pyinstaller_payload_path_matches_specpath_contract():
    """Regression: --specpath must not make PyInstaller look for a missing release_payload."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    command_tokens = _extract_bash_pyinstaller_command(
        workflow, INSTALLER_EXE_NAME.removesuffix(".exe")
    )
    specpath = _token_value(command_tokens, "--specpath")
    add_data = _token_value(command_tokens, "--add-data")

    assert specpath == PYINSTALLER_STANDALONE_SPEC_PATH, (
        "This regression test models the logged standalone-installer failure where CI used "
        f"--specpath {PYINSTALLER_STANDALONE_SPEC_PATH}. If the spec path changes, update the "
        "payload-path contract assertion to keep PyInstaller data-source resolution explicit."
    )
    assert add_data is not None and ";release_payload" in add_data

    add_data_source, add_data_dest = add_data.split(";", 1)
    assert add_data_dest == "release_payload"
    assert 'payload = root / ".installer-payload-stage" / "release_payload"' in workflow
    assert _looks_absolute_or_resolved_for_ci_shell(
        add_data_source
    ) or _relative_source_is_staged_under_specpath(add_data_source, specpath), (
        "CI currently stages release_payload at repo-root .installer-payload-stage/release_payload "
        "but invokes PyInstaller with --specpath .pyinstaller-installer-spec and a relative "
        f"--add-data source {add_data_source!r}. PyInstaller resolves that relative source under "
        ".pyinstaller-installer-spec, yielding the logged missing path "
        ".pyinstaller-installer-spec/.installer-payload-stage/release_payload. Use an absolute/resolved "
        "payload source, or stage the payload below the specpath-resolved location, so "
        "SuperMedicineInstaller.exe can bundle release_payload without running PyInstaller in this test."
    )


def test_ci_packaging_smoke_installs_runtime_dependencies_before_installer_entrypoints():
    """Packaging smoke must install runtime deps, including PyYAML, before installer entrypoints."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    packaging_job = workflow[workflow.index("  packaging-smoke:") :]
    installer_smoke_markers = (
        "python Install.py --release-exe",
        "python Install.py --extract-release-to",
        "./dist/SuperMedicineInstaller.exe --help",
        "./dist/SuperMedicineInstaller.exe --extract-release-to",
    )
    first_installer_smoke_index = min(
        packaging_job.index(marker) for marker in installer_smoke_markers
    )
    before_installer_smokes = packaging_job[:first_installer_smoke_index]

    assert RUNTIME_DEPENDENCY_INSTALL_RE.search(before_installer_smokes), (
        "The packaging-smoke job invokes Install.py/SuperMedicineInstaller.exe entrypoints that import "
        "runtime modules such as yaml from PyYAML. Install the project/runtime dependencies "
        "(for example `python -m pip install -e .`, `python -m pip install -r requirements.txt`, "
        "or an explicit PyYAML install) before those smoke commands; tool-only installs like "
        "`python -m pip install build pyinstaller` are not sufficient."
    )


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

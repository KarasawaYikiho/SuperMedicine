from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from tests.conftest import _cp1252_stdio_env


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR_NAME = "SuperMedicine Beta0.4.2"
CRITICAL_RELEASE_PATHS = (
    "install_entry.py",
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
RUNTIME_DEPENDENCY_INSTALL_RE = re.compile(
    r"^\s*python\s+-m\s+pip\s+install\b[^\n]*(?:"
    r"-e\s+['\"]?\.(?:\[[^\]\n]+\])?['\"]?|"
    r"['\"]?\.(?:\[[^\]\n]+\])?['\"]?|"
    r"-r\s+requirements\.txt\b|"
    r"\bPyYAML\b|\bpyyaml\b"
    r")",
    re.MULTILINE,
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

RELEASE_LABEL = "Beta0.4.2"
PACKAGE_VERSION = "0.4.2b0"
CRITICAL_RELEASE_FILES = {
    "cli_entry.py",
    "install_entry.py",
    "install_entry.py",
    "uninstall_entry.py",
    "pyproject.toml",
    "requirements.txt",
    "install.json",
    "README.md",
    "CHANGELOG.md",
    "docs/guides/INSTALL.md",
}
CRITICAL_RELEASE_DIRS = {
    "core",
    "permission",
    "agents",
    "plugins",
    "adapters",
    "installer",
}
HIGH_RISK_MODULES = {
    "installer/entrypoint.py",
    "installer/exe_release.py",
    "permission/audit.py",
    "permission/engine.py",
    "permission/policy.py",
    "core/path_safety.py",
    "core/operation_guard.py",
    "core/redaction.py",
    "core/config_center.py",
    "core/llm_providers/config.py",
    "adapters/opencode/adapter.py",
    "adapters/opencode/plugin.json",
}


# ═══ Release Smoke Helper Functions ═══


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


def _copy_release_tree(tmp_path: Path) -> Path:
    """Build a representative extracted release directory in a temp workspace."""

    release_dir = tmp_path / RELEASE_DIR_NAME
    release_dir.mkdir()
    shutil.copy2(REPO_ROOT / "install_entry.py", release_dir / "install_entry.py")

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


# ═══ Release Smoke Tests ═══


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
        "install_entry.py",
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
        "install_entry.py",
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
        "install_entry.py",
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
    build_installer_payload = (REPO_ROOT / "scripts" / "ci" / "build_installer_payload.py").read_text(
        encoding="utf-8"
    )
    build_release_zip = (REPO_ROOT / "scripts" / "ci" / "build_release_zip.py").read_text(
        encoding="utf-8"
    )

    # CI must invoke both build scripts
    assert "build_installer_payload.py" in workflow
    assert "build_release_zip.py" in workflow

    # Installer payload must stage release_payload
    assert "release_payload" in build_installer_payload
    assert '".installer-payload-stage"' in build_installer_payload

    # Release zip must include the standalone installer and app exe
    assert f"dist/{INSTALLER_EXE_NAME}" in build_release_zip
    assert INSTALLER_EXE_NAME in build_release_zip
    assert "dist/SuperMedicine.exe" in build_release_zip

    # CI workflow must reference the app exe
    assert "dist/SuperMedicine.exe" in workflow

    # Packaging must install runtime deps
    assert PACKAGING_TOOLING_WITH_RUNTIME_INSTALL_RE.search(workflow), (
        "CI packaging smoke must install build tooling (build, pyinstaller) together with "
        "runtime/project dependencies before installer entrypoint smoke commands."
    )

    # Release zip must handle install_entry.py correctly
    assert '["git", "show", ":install_entry.py"]' in build_release_zip
    assert "archive.writestr(lowercase_entry" in build_release_zip

    # No git archive HEAD
    assert "git archive HEAD" not in workflow


def test_ci_standalone_installer_pyinstaller_payload_path_matches_specpath_contract():
    """Regression: --specpath must not make PyInstaller look for a missing release_payload."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    build_installer_payload = (REPO_ROOT / "scripts" / "ci" / "build_installer_payload.py").read_text(
        encoding="utf-8"
    )

    # CI must call the installer payload build script
    assert "build_installer_payload.py" in workflow

    # If a PyInstaller command for the standalone installer exists in the
    # workflow or the build script, verify the --specpath contract.
    for source in (workflow, build_installer_payload):
        try:
            command_tokens = _extract_bash_pyinstaller_command(
                source, INSTALLER_EXE_NAME.removesuffix(".exe")
            )
        except AssertionError:
            continue
        specpath = _token_value(command_tokens, "--specpath")
        add_data = _token_value(command_tokens, "--add-data")

        assert specpath is None, (
            "CI must not use --specpath for the standalone installer build. "
            "PyInstaller resolves --add-data relative paths based on specpath directory, "
            "not the current working directory. Removing --specpath ensures data files "
            "are found correctly in CI environments."
        )
        assert add_data is not None and ";release_payload" in add_data

        add_data_source, add_data_dest = add_data.split(";", 1)
        assert add_data_dest == "release_payload"

    # Verify the payload staging contract in the build script
    assert '".installer-payload-stage"' in build_installer_payload
    assert '"release_payload"' in build_installer_payload


def test_ci_packaging_smoke_installs_runtime_dependencies_before_installer_entrypoints():
    """Packaging smoke must install runtime deps, including PyYAML, before installer entrypoints."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    packaging_job = workflow[workflow.index("  packaging-smoke:") :]

    # Use the installer payload build invocation as a key marker, together
    # with any installer smoke markers still present in the workflow.
    installer_smoke_markers = ["python scripts/ci/build_installer_payload.py"]
    for marker in (
        "python install_entry.py --release-exe",
        "python install_entry.py --extract-release-to",
        "./dist/SuperMedicineInstaller.exe --help",
        "./dist/SuperMedicineInstaller.exe --extract-release-to",
    ):
        if marker in packaging_job:
            installer_smoke_markers.append(marker)

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
    install = (REPO_ROOT / "docs" / "guides" / "INSTALL.md").read_text(encoding="utf-8")
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


# ═══ Beta0.4.2 Release Validation ═══


def test_beta042_version_contract_is_single_source_consistent_across_release_surfaces(read_pyproject):
    """Beta0.4.2 display labels and 0.4.2b0 package metadata must not drift."""

    pyproject = read_pyproject
    install_manifest = json.loads(
        (REPO_ROOT / "install.json").read_text(encoding="utf-8")
    )
    opencode_plugin = json.loads(
        (REPO_ROOT / "adapters" / "opencode" / "plugin.json").read_text(
            encoding="utf-8"
        )
    )
    build_release_zip = (REPO_ROOT / "scripts" / "ci" / "build_release_zip.py").read_text(
        encoding="utf-8"
    )
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    plan = (REPO_ROOT / "docs" / "archive" / "Beta0.4.2ShortTermPlan.md").read_text(
        encoding="utf-8"
    )

    assert pyproject["project"]["version"] == PACKAGE_VERSION
    assert install_manifest["version"] == RELEASE_LABEL
    assert opencode_plugin["version"] == PACKAGE_VERSION
    assert f"## [{RELEASE_LABEL}]" in changelog
    assert RELEASE_LABEL in readme
    assert RELEASE_LABEL in plan
    assert PACKAGE_VERSION in plan
    assert 'release_label = f"Beta{release_version}"' in build_release_zip
    assert 'archive_name = f"SuperMedicine {release_label}.zip"' in build_release_zip


def test_release_packaging_contract_includes_critical_modules_and_high_risk_surfaces(tracked_files):
    """Step 2/3 high-risk modules must be either packaged or intentionally tracked."""

    tracked = tracked_files
    packaging_common = (REPO_ROOT / "scripts" / "ci" / "_packaging_common.py").read_text(
        encoding="utf-8"
    )

    for relative_path in CRITICAL_RELEASE_FILES:
        assert relative_path in tracked, relative_path
        assert f'"{relative_path}"' in packaging_common, relative_path

    expected_include_dirs = 'INCLUDE_DIRS = ["core", "permission", "agents", "plugins", "adapters", "installer"]'
    assert expected_include_dirs in packaging_common
    for directory in CRITICAL_RELEASE_DIRS:
        assert any(
            path == directory or path.startswith(f"{directory}/") for path in tracked
        )

    for relative_path in HIGH_RISK_MODULES:
        assert relative_path in tracked, relative_path
        if relative_path.endswith(".py"):
            assert (REPO_ROOT / relative_path).read_text(encoding="utf-8").strip()


def test_release_verification_scripts_use_runner_temp_for_pytest_temp_exhaustion_risk():
    """Regression guard for the Step 3/4 environment-only temp filesystem blocker."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    pytest_invocations = re.findall(r"python -m pytest[^\n]+", workflow)

    assert pytest_invocations, "CI must keep explicit pytest release gates"
    assert "Join-Path $env:RUNNER_TEMP" in workflow
    for invocation in pytest_invocations:
        assert "--basetemp $pytestTemp" in invocation
        assert "-p no:cacheprovider" in invocation


def test_beta042_short_term_plan_records_deferred_gaps_with_tracking_owner():
    """Short-term release scope must document unresolved broad gaps rather than hide them."""

    plan = (REPO_ROOT / "docs" / "archive" / "Beta0.4.2ShortTermPlan.md").read_text(
        encoding="utf-8"
    )

    required_markers = [
        "## Step 5 minimal validation coverage and deferred gaps",
        "Covered before Beta0.4.2 release gate",
        "Deferred beyond Beta0.4.2 short-term release",
        "延期原因",
        "后续追踪方式",
        "manual release proofreading checklist",
        "full cross-platform frozen-executable matrix",
    ]
    normalized_plan = plan.lower()
    for marker in required_markers:
        assert marker.lower() in normalized_plan

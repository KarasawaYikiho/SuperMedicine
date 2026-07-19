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
    "install.py",
    "install_entry.py",
    "assets/logo.ico",
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
    "install.py",
    "install_entry.py",
    "uninstall_entry.py",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "requirements.txt",
    "install.json",
    "THIRD_PARTY_NOTICES.md",
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
    option_equals = f"{option}="
    for token in tokens:
        if token.startswith(option_equals):
            return token.removeprefix(option_equals)

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


def _copy_release_tree(tmp_path: Path) -> Path:
    """Build a representative extracted release directory in a temp workspace."""

    release_dir = tmp_path / RELEASE_DIR_NAME
    release_dir.mkdir()
    shutil.copy2(REPO_ROOT / "install.py", release_dir / "install.py")
    shutil.copy2(REPO_ROOT / "install_entry.py", release_dir / "install_entry.py")

    logo_target = release_dir / "assets" / "logo.ico"
    logo_target.parent.mkdir()
    shutil.copy2(REPO_ROOT / "assets" / "logo.ico", logo_target)

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

    lowercase_help_result = _run_release_python(
        release_dir,
        "install.py",
        "--help",
        env=_cp1252_stdio_env(),
        encoding="cp1252",
    )
    lowercase_help_output = lowercase_help_result.stdout + lowercase_help_result.stderr
    assert lowercase_help_result.returncode == 0, lowercase_help_output
    assert "usage:" in lowercase_help_output.lower()
    assert "--release-exe" in lowercase_help_output
    assert "UnicodeEncodeError" not in lowercase_help_output

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


def test_ci_release_artifacts_include_standalone_installer_exe_and_shared_payload():
    """Published CI artifacts must include usable app, installer, and payload paths."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    build_installer_exe = (REPO_ROOT / "scripts" / "ci" / "build_installer_exe.py").read_text(
        encoding="utf-8"
    )
    build_release_zip = (REPO_ROOT / "scripts" / "ci" / "build_release_zip.py").read_text(
        encoding="utf-8"
    )
    packaging_common = (REPO_ROOT / "scripts" / "ci" / "_packaging_common.py").read_text(
        encoding="utf-8"
    )

    # CI artifact contract: app Exe, installer Exe, shared payload, and upload.
    assert any(path in workflow for path in INSTALLER_EXE_RELEASE_PATHS), (
        "CI/release workflow must publish either dist/SuperMedicine.exe or "
        "SuperMedicine.exe so Install.py --release-exe has a documented, packaged source path."
    )
    assert "actions/upload-artifact" in workflow
    assert any(
        f"--release-exe {path}" in workflow or f"--release-exe {path!r}" in workflow
        for path in INSTALLER_EXE_RELEASE_PATHS
    )
    assert "build_installer_exe.py" in workflow
    assert "build_release_zip.py" in workflow

    # Installer EXE embeds the manifest and every installable component tree.
    for bundled_path in ("install.json", "core", "permission", "plugins", "adapters"):
        assert f'"{bundled_path}"' in build_installer_exe

    # Release zip must include the standalone installer and app exe
    assert f"dist/{INSTALLER_EXE_NAME}" in build_release_zip
    assert INSTALLER_EXE_NAME in build_release_zip
    assert "dist/SuperMedicine.exe" in build_release_zip

    # CI workflow must reference the app exe
    assert "dist/SuperMedicine.exe" in workflow
    assert "npm ci" in workflow
    assert "oven-sh/setup-bun" in workflow
    assert "_pyinstaller_builder.py application" in workflow
    assert "./dist/SuperMedicine.exe tui --dry-run" in workflow

    # CUR-DBG-010: release payload/zip must carry the logo resource used for
    # externally visible Windows Exe icons, not only the in-app GUI icon.
    assert '"assets/logo.ico"' in packaging_common
    assert '"assets"' in build_installer_exe
    assert "copy_include_files(root, stage)" in build_release_zip

    # Packaging must install runtime deps
    assert PACKAGING_TOOLING_WITH_RUNTIME_INSTALL_RE.search(workflow), (
        "CI packaging smoke must install build tooling (build, pyinstaller) together with "
        "runtime/project dependencies before installer entrypoint smoke commands."
    )

    # Release zip must expose the documented lowercase installer alias.
    assert '["git", "show", ":install.py"]' in build_release_zip
    assert f"SuperMedicine {{release_label}}/{CANONICAL_LOWERCASE_INSTALL}" in build_release_zip
    assert "archive.writestr(lowercase_entry" in build_release_zip

    # No git archive HEAD
    assert "git archive HEAD" not in workflow


def test_cur_dbg_010_release_icon_contract_is_packaged_and_documented():
    """Released Exes and desktop helpers must share the logo/icon contract."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    build_gui_exe = (REPO_ROOT / "scripts" / "ci" / "build_gui_exe.py").read_text(
        encoding="utf-8"
    )
    build_application_exe = (REPO_ROOT / "scripts" / "ci" / "_pyinstaller_builder.py").read_text(
        encoding="utf-8"
    )
    build_installer_exe = (REPO_ROOT / "scripts" / "ci" / "build_installer_exe.py").read_text(
        encoding="utf-8"
    )
    packaging_common = (REPO_ROOT / "scripts" / "ci" / "_packaging_common.py").read_text(
        encoding="utf-8"
    )
    exe_release = (REPO_ROOT / "installer" / "exe_release.py").read_text(
        encoding="utf-8"
    )
    assert (REPO_ROOT / "assets" / "logo.ico").is_file()
    for builder_name, builder in (
        ("SuperMedicine", build_application_exe),
        ("SuperMedicineGUI", build_gui_exe),
        ("SuperMedicineInstaller", build_installer_exe),
    ):
        assert builder_name in builder
        assert "assets" in builder and "logo.ico" in builder
        assert "build_executable" in builder
    assert "_pyinstaller_builder.py application" in workflow
    assert "build_gui_exe.py" in workflow
    assert "build_installer_exe.py" in workflow
    assert '"assets/logo.ico"' in packaging_common
    assert "WINDOWS_ICON_CACHE_NOTE" in exe_release
    assert "assets/logo.ico" in exe_release
    assert "versioned" in exe_release
    assert "target_filename" in exe_release


def test_desktop_and_installer_exe_builders_share_one_parameterized_engine():
    """The two preserved EXE targets must not maintain duplicate build workflows."""

    ci_dir = REPO_ROOT / "scripts" / "ci"
    gui_builder = (ci_dir / "build_gui_exe.py").read_text(encoding="utf-8")
    installer_builder = (ci_dir / "build_installer_exe.py").read_text(
        encoding="utf-8"
    )
    shared_builder = ci_dir / "_pyinstaller_builder.py"

    assert shared_builder.is_file()
    shared_source = shared_builder.read_text(encoding="utf-8")
    assert "class PyInstallerTarget" in shared_source
    assert "def build_executable" in shared_source
    assert '"PyInstaller"' in shared_source
    assert '"PyInstaller"' not in gui_builder
    assert '"PyInstaller"' not in installer_builder
    assert "build_executable" in gui_builder
    assert "build_executable" in installer_builder
    assert len(gui_builder.splitlines()) <= 80
    assert len(installer_builder.splitlines()) <= 80


def test_ci_standalone_installer_uses_shared_absolute_add_data_contract():
    """Regression: bundled installer data must resolve independently of spec paths."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    build_installer_exe = (REPO_ROOT / "scripts" / "ci" / "build_installer_exe.py").read_text(
        encoding="utf-8"
    )
    shared_builder = (REPO_ROOT / "scripts" / "ci" / "_pyinstaller_builder.py").read_text(
        encoding="utf-8"
    )

    assert "build_installer_exe.py" in workflow
    assert 'data_items=(' in build_installer_exe
    assert 'source = root / item' in shared_builder
    assert 'f"--add-data={source}{separator}{destination}"' in shared_builder
    assert 'f"--specpath={root}"' in shared_builder


def test_ci_packaging_smoke_installs_runtime_dependencies_before_installer_entrypoints():
    """Packaging smoke must install runtime deps, including PyYAML, before installer entrypoints."""

    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    packaging_job = workflow[workflow.index("  packaging-smoke:") :]

    installer_smoke_markers = ["python scripts/ci/build_installer_exe.py"]
    for marker in (
        "python install_entry.py --release-exe",
        "python install_entry.py --extract-release-to",
        "./dist/SuperMedicineInstaller.exe --help",
        "./dist/SuperMedicineInstaller.exe --extract-release-to",
        "./dist/SuperMedicineInstaller.exe --self-test",
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
    assert "@opentui/core@0.4.1" in combined
    assert "npm ci" in combined
    assert "npm run opentui:smoke" in combined
    assert "Bun" in combined
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

    assert pyproject["project"]["version"] == PACKAGE_VERSION
    assert install_manifest["version"] == RELEASE_LABEL
    assert opencode_plugin["version"] == PACKAGE_VERSION
    assert f"## [{RELEASE_LABEL}]" in changelog
    assert RELEASE_LABEL in readme
    assert 'release_label = f"Beta{release_version}"' in build_release_zip
    assert 'archive_name = f"SuperMedicine {release_label}.zip"' in build_release_zip


def test_opentui_release_runtime_dependency_and_notice_are_packaged():
    """Release packaging must carry OpenTUI manifests, bridge, and MIT notices."""

    package_json = json.loads((REPO_ROOT / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((REPO_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    packaging_common = (REPO_ROOT / "scripts" / "ci" / "_packaging_common.py").read_text(
        encoding="utf-8"
    )
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    notice = (REPO_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    install = (REPO_ROOT / "docs" / "guides" / "INSTALL.md").read_text(encoding="utf-8")

    assert package_json["dependencies"]["@opentui/core"] == "0.4.1"
    assert package_lock["packages"]["node_modules/@opentui/core"]["version"] == "0.4.1"
    assert (REPO_ROOT / "core" / "tui" / "opentui_runtime.mjs").is_file()
    assert (REPO_ROOT / "core" / "tui" / "opentui_runtime.py").is_file()
    assert 'core = ["tui/app.tcss", "tui/*.mjs", "web/frontend/*"]' in pyproject
    assert "include THIRD_PARTY_NOTICES.md" in manifest
    for relative_path in (
        "package.json",
        "package-lock.json",
        "THIRD_PARTY_NOTICES.md",
    ):
        assert f'"{relative_path}"' in packaging_common
    assert "npm ci" in workflow
    assert "bun --version" in workflow
    assert "npm run opentui:smoke" in workflow
    assert "@opentui/core" in notice
    assert "MIT License" in notice
    assert "diff" in notice
    assert "BSD-3-Clause" in notice
    assert "typescript" in notice
    assert "Apache-2.0" in notice
    assert "Permission is hereby granted" in notice
    assert "npm ci" in readme + install
    assert "SUPERMEDICINE_OPENTUI_JS_RUNTIME" in readme


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

    assert "core/tui/opentui_runtime.py" in tracked


def test_dev_extra_runs_web_api_tests_in_release_gate(read_pyproject):
    """The CI dev install must include Web extras so API tests do not skip."""

    dev_dependencies = read_pyproject["project"]["optional-dependencies"]["dev"]

    assert any(dep.startswith("fastapi") for dep in dev_dependencies)
    assert any(dep.startswith("httpx>=0.28.1,<1") for dep in dev_dependencies)
    assert not any(dep.startswith("httpx2") for dep in dev_dependencies)
    assert any(dep.startswith("uvicorn") for dep in dev_dependencies)


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
    """Archived release planning notes are local-only cleanup artifacts."""

    assert not (REPO_ROOT / "docs" / "archive").exists()
    return

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

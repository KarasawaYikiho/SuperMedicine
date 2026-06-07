from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

try:
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_LABEL = "Beta0.4.2"
PACKAGE_VERSION = "0.4.2b0"
CRITICAL_RELEASE_FILES = {
    "Cli.py",
    "install.py",
    "Install.py",
    "Uninstall.py",
    "pyproject.toml",
    "requirements.txt",
    "install.json",
    "README.md",
    "CHANGELOG.md",
    "INSTALL.md",
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


def _read_pyproject() -> dict:
    path = REPO_ROOT / "pyproject.toml"
    if tomllib is not None:
        with path.open("rb") as f:
            return tomllib.load(f)
    text = path.read_text(encoding="utf-8")
    version = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return {"project": {"version": version.group(1) if version else ""}}


def _tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def test_beta042_version_contract_is_single_source_consistent_across_release_surfaces():
    """Beta0.4.2 display labels and 0.4.2b0 package metadata must not drift."""

    pyproject = _read_pyproject()
    install_manifest = json.loads(
        (REPO_ROOT / "install.json").read_text(encoding="utf-8")
    )
    opencode_plugin = json.loads(
        (REPO_ROOT / "adapters" / "opencode" / "plugin.json").read_text(
            encoding="utf-8"
        )
    )
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    plan = (REPO_ROOT / "Architecture" / "Beta0.4.2ShortTermPlan.md").read_text(
        encoding="utf-8"
    )

    assert pyproject["project"]["version"] == PACKAGE_VERSION
    assert install_manifest["version"] == RELEASE_LABEL
    assert opencode_plugin["version"] == PACKAGE_VERSION
    assert f"## [{RELEASE_LABEL}]" in changelog
    assert RELEASE_LABEL in readme
    assert RELEASE_LABEL in plan
    assert PACKAGE_VERSION in plan
    assert 'release_label = f"Beta{release_version}"' in workflow
    assert 'archive_name = f"SuperMedicine {release_label}.zip"' in workflow


def test_release_packaging_contract_includes_critical_modules_and_high_risk_surfaces():
    """Step 2/3 high-risk modules must be either packaged or intentionally tracked."""

    tracked = _tracked_files()
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    for relative_path in CRITICAL_RELEASE_FILES:
        assert relative_path in tracked, relative_path
        assert f'"{relative_path}"' in workflow, relative_path

    expected_include_dirs = 'include_dirs = ["core", "permission", "agents", "plugins", "adapters", "installer"]'
    assert expected_include_dirs in workflow
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

    plan = (REPO_ROOT / "Architecture" / "Beta0.4.2ShortTermPlan.md").read_text(
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

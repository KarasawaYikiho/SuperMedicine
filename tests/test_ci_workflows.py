from __future__ import annotations

from tests.ci_workflow_contract import (
    combined_workflow_source,
    jobs_with_write_permission,
    load_workflow,
    workflow_sources,
)


def test_workflows_are_valid_yaml_with_read_only_defaults() -> None:
    sources = workflow_sources()
    assert sources
    for name in sources:
        workflow = load_workflow(name)
        assert workflow["name"]
        assert workflow["jobs"]
        assert workflow.get("permissions", {}).get("contents") == "read"


def test_only_the_release_publication_job_can_write_repository_contents() -> None:
    assert jobs_with_write_permission() <= {
        ("ci.yml", "publish-release"),
        ("release.yml", "publish-release"),
    }


def test_workflow_set_preserves_runtime_and_packaging_commands() -> None:
    source = combined_workflow_source()
    for command in (
        "python -m pytest",
        "python -m ruff",
        "python -m mypy",
        "python -m build --wheel",
        "smoke_wheel_install.py",
        "npm ci",
        "oven-sh/setup-bun",
        "npm run opentui:smoke",
        "_pyinstaller_builder.py application",
        "build_gui_exe.py",
        "build_installer_exe.py",
        "build_release_zip.py",
        "actions/upload-artifact",
    ):
        assert command in source


def test_publication_consumes_packaged_artifacts_and_refuses_overwrite() -> None:
    source = combined_workflow_source()
    assert "actions/download-artifact" in source
    assert "gh release view" in source
    assert "gh release create" in source
    assert "gh release upload" in source

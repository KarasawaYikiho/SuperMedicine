from __future__ import annotations

from tests.ci_workflow_contract import (
    REPOSITORY_ROOT,
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
    assert jobs_with_write_permission() == {("release.yml", "publish-release")}


def test_workflow_set_has_stable_triggers_concurrency_and_timeouts() -> None:
    assert set(workflow_sources()) == {
        "_reusable-python.yml",
        "_reusable-windows-package.yml",
        "ci.yml",
        "nightly.yml",
        "opentui.yml",
        "package-smoke.yml",
        "release.yml",
    }
    ci = load_workflow("ci.yml")
    release = load_workflow("release.yml")
    assert set(ci["on"]) == {"pull_request", "push", "workflow_dispatch"}
    assert "tags" not in ci["on"]["push"]
    assert set(release["on"]) == {"push", "workflow_dispatch", "workflow_run"}
    assert release["on"]["push"]["tags"] == ["Beta*"]
    assert release["on"]["workflow_run"] == {
        "workflows": ["CI"],
        "types": ["completed"],
        "branches": ["master"],
    }

    for name in ("ci.yml", "nightly.yml", "opentui.yml", "package-smoke.yml", "release.yml"):
        assert "concurrency" in load_workflow(name)
    for name in workflow_sources():
        for job_name, definition in load_workflow(name)["jobs"].items():
            assert "uses" in definition or "timeout-minutes" in definition, (
                name,
                job_name,
            )


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


def test_publication_consumes_packaged_artifacts_and_refreshes_same_version() -> None:
    source = combined_workflow_source()
    assert "actions/download-artifact" in source
    assert "scripts/ci/validate_release_tag.py" in source
    assert "scripts/ci/verify_release_artifacts.py" in source
    assert "scripts/ci/publish_release.py" in source

    validator = (
        REPOSITORY_ROOT / "scripts" / "ci" / "validate_release_tag.py"
    ).read_text(encoding="utf-8")
    publisher = (
        REPOSITORY_ROOT / "scripts" / "ci" / "publish_release.py"
    ).read_text(encoding="utf-8")
    assert '"git", "rev-parse", "HEAD"' in validator
    assert "refusing to overwrite" not in validator
    assert '"release", "view"' in publisher
    assert '"create",' in publisher
    assert '"release", "upload"' in publisher
    assert "--clobber" in publisher
    assert "--draft" in publisher
    assert '"release", "edit"' in publisher
    assert "refusing to overwrite" not in publisher
    assert "git tag --force" in source
    assert "git push origin" in source


def test_release_builds_the_exact_successful_ci_source_commit() -> None:
    source = workflow_sources()["release.yml"]
    reusable = load_workflow("_reusable-windows-package.yml")

    assert "github.event.workflow_run.head_sha || github.sha" in source
    assert "github.event.workflow_run.conclusion == 'success'" in source
    assert "github.event.workflow_run.event == 'push'" in source
    assert "github.event.workflow_run.head_repository.full_name == github.repository" in source
    assert reusable["on"]["workflow_call"]["inputs"]["source-sha"]["default"] == ""
    assert (
        reusable["jobs"]["packaging-smoke"]["steps"][0]["with"]["ref"]
        == "${{ inputs.source-sha || github.sha }}"
    )


def test_release_jobs_form_a_validate_build_verify_publish_chain() -> None:
    release = load_workflow("release.yml")
    jobs = release["jobs"]
    assert jobs["release-tests"]["needs"] == ["validate-tag"]
    assert set(jobs["build-windows-artifacts"]["needs"]) == {
        "validate-tag",
        "release-tests",
    }
    assert set(jobs["verify-artifacts"]["needs"]) == {
        "validate-tag",
        "build-windows-artifacts",
    }
    assert set(jobs["publish-release"]["needs"]) == {
        "validate-tag",
        "verify-artifacts",
    }

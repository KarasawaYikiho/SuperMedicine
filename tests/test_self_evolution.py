from __future__ import annotations

from pathlib import Path
from typing import Any

from core.experience import ExperienceStore
from core.self_evolution import SelfEvolutionService
from core.workspace import WorkspaceManager
from permission.policy import PermissionResult


class RecordingPermissionEngine:
    def __init__(self, result: PermissionResult):
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def check(self, agent_id, action, resource, context=None):
        self.calls.append(
            {
                "agent_id": agent_id,
                "action": action,
                "resource": resource,
                "context": context,
            }
        )
        return self.result


def _service(tmp_path: Path) -> SelfEvolutionService:
    return SelfEvolutionService(tmp_path)


def test_preview_markdown_returns_plan_without_writing(tmp_path):
    target = tmp_path / "generated" / "plan.md"

    result = _service(tmp_path).preview(
        user_intent="Create a reusable verification checklist",
        artifact_type="markdown",
        output_path="generated/plan.md",
    )

    assert result["status"] == "preview"
    assert result["plan"]["will_write"] is False
    assert result["artifacts"][0]["path"] == str(target.resolve())
    assert not target.exists()


def test_confirmed_markdown_writes_allowed_file_and_bootstraps_policy(tmp_path):
    target = tmp_path / "generated" / "plan.md"

    result = _service(tmp_path).confirm(
        user_intent="Create a reusable verification checklist",
        artifact_type="markdown",
        output_path="generated/plan.md",
    )

    assert result["status"] == "success"
    assert target.is_file()
    assert "Self-Evolution Plan" in target.read_text(encoding="utf-8")
    assert (tmp_path / ".supermedicine" / "policies" / "default.yaml").is_file()


def test_python_tool_preview_and_confirmed_creation_use_safe_output_validation(
    tmp_path,
):
    target = tmp_path / "tools" / "generated" / "helper.py"

    preview = _service(tmp_path).preview(
        user_intent="Create a helper tool",
        artifact_type="python_tool",
        output_path="tools/generated/helper.py",
    )

    assert preview["status"] == "preview"
    assert not target.exists()

    confirmed = _service(tmp_path).confirm(
        user_intent="Create a helper tool",
        artifact_type="python_tool",
        output_path="tools/generated/helper.py",
    )

    assert confirmed["status"] == "success"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "validate_sandbox_write_path" in content
    assert "Path(args.output).write_text" not in content
    assert "write_safe_output(args.output)" in content
    assert (tmp_path / "tools" / "generated" / "helper-README.md").is_file()


def test_experience_source_is_included_in_generated_artifact(tmp_path):
    WorkspaceManager(tmp_path).initialize_workspace("study-a")
    record = ExperienceStore(tmp_path).store_confirmed_workspace_experience(
        workspace_id="study-a",
        title="Reuse explicit handoff",
        summary="Implementation and verification responsibilities stay separate.",
        tags=["workflow"],
    )

    result = _service(tmp_path).preview(
        user_intent="Use prior workflow lessons",
        artifact_type="markdown",
        output_path="generated/experience.md",
        workspace_id="study-a",
        experience_source=record.id,
    )

    artifact = result["artifacts"][0]
    assert result["status"] == "preview"
    assert "Reuse explicit handoff" in artifact["content"]
    assert "Implementation and verification" in artifact["content"]


def test_illegal_paths_and_extensions_are_rejected(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside" / "plan.md"
    outside.parent.mkdir()

    path_result = _service(tmp_path).preview(
        user_intent="Create plan",
        artifact_type="markdown",
        output_path=outside,
    )
    extension_result = _service(tmp_path).preview(
        user_intent="Create plan",
        artifact_type="markdown",
        output_path="generated/plan.yaml",
    )
    docs_result = _service(tmp_path).preview(
        user_intent="Create plan",
        artifact_type="markdown",
        output_path="generated/docs/REQUIREMENTS_TRACEABILITY.md",
    )

    assert path_result["status"] == "failed"
    assert extension_result["status"] == "failed"
    assert docs_result["status"] == "failed"


def test_overwrite_conflict_is_rejected_without_overwrite_flag(tmp_path):
    target = tmp_path / "generated" / "plan.md"
    target.parent.mkdir()
    target.write_text("existing", encoding="utf-8")

    result = _service(tmp_path).confirm(
        user_intent="Create replacement plan",
        artifact_type="markdown",
        output_path="generated/plan.md",
    )

    assert result["status"] == "failed"
    assert "overwrite" in result["errors"][0].lower()
    assert target.read_text(encoding="utf-8") == "existing"


def test_insufficient_permission_returns_clear_failure(tmp_path):
    engine = RecordingPermissionEngine(PermissionResult.DENIED)
    target = tmp_path / "generated" / "plan.md"

    result = _service(tmp_path).confirm(
        user_intent="Create plan",
        artifact_type="markdown",
        output_path="generated/plan.md",
        permission_engine=engine,
    )

    assert result["status"] == "failed"
    assert "denied" in result["errors"][0].lower()
    assert engine.calls
    assert not target.exists()


def test_full_access_confirmed_write_requires_risk_acknowledgement(tmp_path):
    target = tmp_path / "generated" / "full.md"

    result = _service(tmp_path).confirm(
        user_intent="Create full access plan",
        artifact_type="markdown",
        output_path="generated/full.md",
        access_mode="full",
        full_access_confirmed=True,
        risk_notice_acknowledged=False,
    )

    assert result["status"] == "failed"
    assert "risk notice" in result["errors"][0].lower()
    assert not target.exists()


def test_sensitive_content_is_rejected_before_preview_artifact_is_returned(tmp_path):
    token_secret = _service(tmp_path).preview(
        user_intent="token sk-test",
        artifact_type="markdown",
        output_path="generated/secret.md",
    )
    sk_secret = _service(tmp_path).preview(
        user_intent="Use sk-abcdef credential",
        artifact_type="markdown",
        output_path="generated/secret-2.md",
    )

    assert token_secret["status"] == "failed"
    assert token_secret["artifacts"] == []
    assert "sensitive" in token_secret["errors"][0].lower()
    assert sk_secret["status"] == "failed"
    assert sk_secret["artifacts"] == []
    assert not (tmp_path / "generated" / "secret.md").exists()


def test_empty_input_and_unknown_artifact_type_fail_clearly(tmp_path):
    empty = _service(tmp_path).preview(
        user_intent="  ",
        artifact_type="markdown",
        output_path="generated/plan.md",
    )
    unknown = _service(tmp_path).preview(
        user_intent="Create plan",
        artifact_type="binary",
        output_path="generated/plan.bin",
    )

    assert empty["status"] == "failed"
    assert "intent" in empty["errors"][0].lower()
    assert unknown["status"] == "failed"
    assert "artifact type" in unknown["errors"][0].lower()

from __future__ import annotations

import pytest

from cli_entry import CLI
from core.config_center import ConfigCenter
from permission.access_mode import (
    AccessDecisionStatus,
    AccessMode,
    AccessModePolicy,
    FullAccessConfirmationRequired,
)


def test_cli_permission_mode_requires_confirmation_and_persists_runtime_policy(
    tmp_path, monkeypatch
):
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    monkeypatch.chdir(project_root)
    cli = CLI()

    status = cli.permission_status()
    with pytest.raises(FullAccessConfirmationRequired):
        cli.permission_set_mode("full", confirm_full=False, interactive=False)

    full = cli.permission_set_mode("full", confirm_full=True, interactive=False)
    full_policy = ConfigCenter(
        project_root / ".supermedicine" / "config.yaml"
    ).get_file_access_policy(project_root)
    full_decision = full_policy.decide(external_root / "out.csv", "write")
    conservative = cli.permission_set_mode(
        "conservative", confirm_full=False, interactive=False
    )

    assert status["mode"] == "conservative"
    assert full["mode"] == "full"
    assert full["full_mode_confirmed"] is True
    assert full_decision.status == AccessDecisionStatus.ALLOWED
    assert conservative["mode"] == "conservative"
    assert conservative["full_mode_confirmed"] is False


def test_cli_permission_authorize_and_revoke_external_directory_updates_policy(
    tmp_path, monkeypatch
):
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    monkeypatch.chdir(project_root)
    cli = CLI()

    authorized = cli.permission_authorize(external_root)
    allowed = (
        ConfigCenter(project_root / ".supermedicine" / "config.yaml")
        .get_file_access_policy(project_root)
        .decide(external_root / "out.csv", "write")
    )
    revoked = cli.permission_revoke(external_root)
    denied = (
        ConfigCenter(project_root / ".supermedicine" / "config.yaml")
        .get_file_access_policy(project_root)
        .decide(external_root / "out.csv", "write")
    )

    assert str(external_root.resolve()) in authorized["authorized_external_roots"]
    assert allowed.status == AccessDecisionStatus.ALLOWED
    assert str(external_root.resolve()) not in revoked["authorized_external_roots"]
    assert denied.status == AccessDecisionStatus.DENIED


def test_sandbox_mode_limits_writes_to_generated_safe_file_types(tmp_path):
    policy = AccessModePolicy.sandbox(tmp_path)

    allowed = policy.decide(tmp_path / "generated" / "tool.py", "write")
    wrong_scope = policy.decide(tmp_path / "src" / "tool.py", "write")
    wrong_type = policy.decide(tmp_path / "generated" / "policy.yaml", "write")
    delete_denied = policy.decide(tmp_path / "generated" / "tool.py", "delete")

    assert policy.mode == AccessMode.SANDBOX
    assert allowed.status == AccessDecisionStatus.ALLOWED
    assert wrong_scope.status == AccessDecisionStatus.DENIED
    assert wrong_scope.reason == "sandbox_write_scope_not_allowed"
    assert wrong_type.status == AccessDecisionStatus.DENIED
    assert wrong_type.reason == "sandbox_file_type_not_allowed"
    assert delete_denied.status == AccessDecisionStatus.DENIED


def test_sandbox_mode_rejects_external_paths_even_when_alias_used(tmp_path):
    project_root = tmp_path / "project"
    external_root = tmp_path / "external"
    project_root.mkdir()
    external_root.mkdir()
    policy = AccessModePolicy(project_root, mode="safe")

    decision = policy.decide(external_root / "generated" / "tool.py", "write")

    assert policy.mode == AccessMode.SANDBOX
    assert decision.status == AccessDecisionStatus.DENIED
    assert decision.reason == "sandbox_path_must_remain_inside_project_root"

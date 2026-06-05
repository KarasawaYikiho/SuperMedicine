from __future__ import annotations

import pytest

from Cli import CLI
from core.config_center import ConfigCenter
from permission.access_mode import AccessDecisionStatus, FullAccessConfirmationRequired


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
    allowed = ConfigCenter(
        project_root / ".supermedicine" / "config.yaml"
    ).get_file_access_policy(project_root).decide(external_root / "out.csv", "write")
    revoked = cli.permission_revoke(external_root)
    denied = ConfigCenter(
        project_root / ".supermedicine" / "config.yaml"
    ).get_file_access_policy(project_root).decide(external_root / "out.csv", "write")

    assert str(external_root.resolve()) in authorized["authorized_external_roots"]
    assert allowed.status == AccessDecisionStatus.ALLOWED
    assert str(external_root.resolve()) not in revoked["authorized_external_roots"]
    assert denied.status == AccessDecisionStatus.DENIED

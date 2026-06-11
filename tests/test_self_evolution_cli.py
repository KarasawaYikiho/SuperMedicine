from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli_entry import main


def _cli_json(capsys) -> dict:
    captured = capsys.readouterr()
    text = captured.err or captured.out
    return json.loads(text)


def test_self_evolve_preview_does_not_write_and_reports_files(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "generated" / "preview.md"

    main(
        [
            "self-evolve",
            "--instruction",
            "Create a preview checklist",
            "--target-type",
            "markdown",
            "--output",
            "generated/preview.md",
        ]
    )

    result = _cli_json(capsys)
    assert result["status"] == "preview"
    assert result["preview"] is True
    assert result["permission_mode"] == "sandbox"
    assert result["target_path"] == str(target.resolve())
    assert result["files_to_create_or_modify"][0]["operation"] == "create"
    assert not target.exists()


def test_self_evolve_confirmed_write_creates_allowed_file_and_reports_audit(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "generated" / "confirmed.md"

    main(
        [
            "self-evolve",
            "--instruction",
            "Create a confirmed checklist",
            "--target-type",
            "markdown",
            "--output",
            "generated/confirmed.md",
            "--no-preview",
            "--confirm-write",
        ]
    )

    result = _cli_json(capsys)
    assert result["status"] == "success"
    assert result["preview"] is False
    assert result["confirm_write"] is True
    assert target.is_file()
    assert Path(result["audit_log"]["path"]).parts[-3:] == (
        ".supermedicine",
        "policies",
        "audit.jsonl",
    )
    assert result["audit_log"]["available"] is True


def test_self_evolve_sandbox_rejects_out_of_scope_path(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside" / "blocked.md"

    main(
        [
            "self-evolve",
            "--instruction",
            "Create blocked output",
            "--target-type",
            "markdown",
            "--output",
            str(outside),
        ]
    )

    result = _cli_json(capsys)
    assert result["status"] == "failed"
    assert result["failure_reason"]
    assert "outside" in result["failure_reason"].lower()
    assert result["files_to_create_or_modify"] == []
    assert not outside.exists()


def test_self_evolve_full_access_notice_is_visible_and_requires_confirmation_flags(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)

    main(
        [
            "self-evolve",
            "--instruction",
            "Create full access output",
            "--target-type",
            "markdown",
            "--output",
            "generated/full.md",
            "--access-mode",
            "full",
            "--no-preview",
            "--confirm-write",
        ]
    )

    result = _cli_json(capsys)
    assert result["status"] == "failed"
    assert result["full_access_notice"]["full_access_requested"] is True
    assert result["full_access_notice"]["explicit_full_access_confirmed"] is False
    assert result["full_access_notice"]["risk_notice_acknowledged"] is False
    assert (
        "current user/process permissions" in result["full_access_notice"]["semantics"]
    )
    assert "[REDACTED]" not in json.dumps(result["full_access_notice"])
    assert any("--confirm-full-access" in step for step in result["next_steps"])


def test_self_evolve_full_access_confirmation_flags_are_reported(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)

    main(
        [
            "self-evolve",
            "--instruction",
            "Create full access output with explicit approval",
            "--target-type",
            "markdown",
            "--output",
            "generated/full-confirmed.md",
            "--access-mode",
            "full",
            "--no-preview",
            "--confirm-write",
            "--confirm-full-access",
            "--acknowledge-risk",
        ]
    )

    result = _cli_json(capsys)
    assert result["full_access_notice"]["full_access_requested"] is True
    assert result["full_access_notice"]["explicit_full_access_confirmed"] is True
    assert result["full_access_notice"]["risk_notice_acknowledged"] is True
    assert Path(result["audit_log"]["path"]).name == "audit.jsonl"


def test_self_evolve_full_access_requires_risk_acknowledgement(
    monkeypatch, tmp_path, capsys
):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "generated" / "full-no-risk.md"

    main(
        [
            "self-evolve",
            "--instruction",
            "Create full access output without risk acknowledgement",
            "--target-type",
            "markdown",
            "--output",
            "generated/full-no-risk.md",
            "--access-mode",
            "full",
            "--no-preview",
            "--confirm-write",
            "--confirm-full-access",
        ]
    )

    result = _cli_json(capsys)
    assert result["status"] == "failed"
    assert result["full_access_notice"]["explicit_full_access_confirmed"] is True
    assert result["full_access_notice"]["risk_notice_acknowledged"] is False
    assert "risk notice" in result["failure_reason"].lower()
    assert not target.exists()


def test_self_evolve_help_does_not_regress_existing_commands(capsys):
    with pytest.raises(SystemExit) as top_level:
        main(["--help"])
    assert top_level.value.code == 0
    top_help = capsys.readouterr().out
    for command in ("init", "status", "test", "run", "sandbox", "self-evolve"):
        assert command in top_help

    with pytest.raises(SystemExit) as sandbox_help_exit:
        main(["sandbox", "--help"])
    assert sandbox_help_exit.value.code == 0
    sandbox_help = capsys.readouterr().out
    normalized_sandbox_help = " ".join(sandbox_help.replace("-\n", "-").split())
    assert "permission mode sandbox" in normalized_sandbox_help
    assert "self-evolve --access-mode sandbox" in normalized_sandbox_help

    with pytest.raises(SystemExit) as run_help:
        main(["run", "--help"])
    assert run_help.value.code == 0
    run_output = capsys.readouterr().out
    for flag in ("--verbose", "--plugin", "--action", "--params-json", "--workspace"):
        assert flag in run_output

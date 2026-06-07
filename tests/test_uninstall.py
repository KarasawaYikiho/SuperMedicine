from __future__ import annotations

import json
import logging

import yaml

from Uninstall import collect_removal_candidates, uninstall


def test_dry_run_does_not_delete_project_owned_files(tmp_path):
    owned = tmp_path / ".supermedicine"
    owned.mkdir()
    (owned / "config.yaml").write_text(
        "project_name: supermedicine\n", encoding="utf-8"
    )

    result = uninstall(tmp_path, dry_run=True, force=True)

    assert result["status"] == "dry-run"
    assert (owned / "config.yaml").exists()
    assert any(item["path"] == ".supermedicine" for item in result["planned"])


def test_force_removes_owned_runtime_artifacts_but_not_unrecorded_platform_dirs(
    tmp_path,
):
    paths = [
        tmp_path / ".supermedicine" / "config.yaml",
        tmp_path / ".supermedicine" / "policies" / "audit.jsonl",
        tmp_path / ".supermedicine" / "checkpoints" / "task" / "status.json",
        tmp_path / ".opencode" / "plugin.json",
        tmp_path / ".claude" / "skills" / "supermedicine" / "SKILL.md",
        tmp_path / "superpowers" / "supermedicine.md",
    ]
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert not (tmp_path / ".supermedicine").exists()
    assert (tmp_path / ".opencode" / "plugin.json").exists()
    assert (tmp_path / ".claude" / "skills" / "supermedicine" / "SKILL.md").exists()
    assert (tmp_path / "superpowers" / "supermedicine.md").exists()


def test_uninstall_does_not_remove_user_owned_files_or_repo_root(tmp_path):
    user_file = tmp_path / "user-notes.md"
    source_file = tmp_path / "Cli.py"
    user_file.write_text("keep", encoding="utf-8")
    source_file.write_text("keep", encoding="utf-8")
    (tmp_path / ".supermedicine").mkdir()

    result = uninstall(tmp_path, force=True)

    assert user_file.exists()
    assert source_file.exists()
    assert tmp_path.exists()
    assert "." not in result["removed"]


def test_recorded_and_explicit_targets_are_removed_only_inside_project(tmp_path):
    inside_recorded = tmp_path / "platform-targets" / "opencode" / "supermedicine.json"
    inside_explicit = tmp_path / "platform-targets" / "claude" / "SKILL.md"
    outside = tmp_path.parent / "outside-supermedicine-target.txt"
    for path in (inside_recorded, inside_explicit, outside):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text(
        '{"platform_target_paths":["platform-targets/opencode/supermedicine.json","../outside-supermedicine-target.txt"]}',
        encoding="utf-8",
    )

    result = uninstall(
        tmp_path, force=True, explicit_targets=["platform-targets/claude/SKILL.md"]
    )

    assert not inside_recorded.exists()
    assert not inside_explicit.exists()
    assert outside.exists()
    assert any(str(outside) in item for item in result["skipped"])
    outside.unlink()


def test_nested_platform_install_records_are_removed_but_unrecorded_home_like_dirs_survive(
    tmp_path,
):
    recorded_opencode = (
        tmp_path / ".config" / "opencode" / "supermedicine" / "plugin.json"
    )
    recorded_claude = tmp_path / ".claude" / "skills" / "supermedicine" / "SKILL.md"
    unrecorded_neighbor = tmp_path / ".claude" / "settings.json"
    for path in (recorded_opencode, recorded_claude, unrecorded_neighbor):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text(
        json.dumps(
            {
                "platforms": {
                    "opencode": {
                        "target_paths": [".config/opencode/supermedicine/plugin.json"]
                    },
                    "claude-code": {
                        "target_paths": [".claude/skills/supermedicine/SKILL.md"]
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert not recorded_opencode.exists()
    assert not recorded_claude.exists()
    assert unrecorded_neighbor.exists()


def test_invalid_install_record_is_ignored_safely(tmp_path, caplog):
    unrecorded_platform_file = tmp_path / ".opencode" / "plugin.json"
    unrecorded_platform_file.parent.mkdir()
    unrecorded_platform_file.write_text("user managed", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True)
    record.write_text("{not-json", encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    assert unrecorded_platform_file.exists()
    assert "Ignoring invalid install record" in caplog.text


def test_uninstall_logs_are_secret_redacted(tmp_path, caplog):
    secret = "sk-test-uninstall-secret"
    config_dir = tmp_path / ".supermedicine"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        yaml.safe_dump({"llm": {"providers": {"openai": {"api_key": secret}}}}),
        encoding="utf-8",
    )
    caplog.set_level(logging.INFO, logger="Uninstall")

    uninstall(tmp_path, dry_run=True, force=True)

    assert secret not in caplog.text
    assert "api_key" not in caplog.text


def test_collect_candidates_defines_project_owned_rules(tmp_path):
    candidates, skipped = collect_removal_candidates(
        tmp_path, explicit_targets=[".supermedicine/custom-platform-copy"]
    )
    candidate_paths = {
        candidate.path.relative_to(tmp_path).as_posix() for candidate in candidates
    }

    assert ".supermedicine" in candidate_paths
    assert "workspaces" in candidate_paths
    assert ".supermedicine/custom-platform-copy" in candidate_paths
    assert skipped == []


def test_uninstall_removes_recorded_binary_shortcut_config_cache_log_temp_and_user_data_by_default(
    tmp_path,
):
    recorded_paths = {
        "binaries": ["bin/supermedicine.exe"],
        "shortcuts": ["shortcuts/SuperMedicine.lnk"],
        "config_dirs": ["config/supermedicine/settings.json"],
        "cache_dirs": ["cache/supermedicine/cache.db"],
        "log_dirs": ["logs/supermedicine/app.log"],
        "temp_dirs": ["tmp/supermedicine/session.tmp"],
        "user_data_paths": ["data/supermedicine/user.db"],
    }
    for values in recorded_paths.values():
        for relative in values:
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(recorded_paths), encoding="utf-8")

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed"
    for values in recorded_paths.values():
        for relative in values:
            assert not (tmp_path / relative).exists()


def test_uninstall_manifest_ownership_keys_cover_recorded_exe_and_shortcut_artifacts():
    manifest = json.loads(
        (
            __import__("pathlib").Path(__file__).resolve().parents[1] / "install.json"
        ).read_text(encoding="utf-8")
    )
    recorded_keys = set(manifest["uninstall"]["recorded_artifact_keys"])

    assert {"binaries", "binary_paths", "shortcuts", "shortcut_paths"}.issubset(
        recorded_keys
    )
    assert "binaries" in manifest["packaging_resources"]["source_tree_exe_policy"]
    assert "shortcut_paths" in manifest["packaging_resources"]["source_tree_exe_policy"]


def test_uninstall_can_preserve_recorded_user_data_explicitly(tmp_path):
    user_data = tmp_path / "data" / "supermedicine" / "user.db"
    generated_config = tmp_path / "config" / "supermedicine" / "settings.json"
    for path in (user_data, generated_config):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "user_data_paths": ["data/supermedicine/user.db"],
                "config_dirs": ["config/supermedicine/settings.json"],
            }
        ),
        encoding="utf-8",
    )

    result = uninstall(tmp_path, force=True, preserve_user_data=True)

    assert result["status"] == "removed"
    assert user_data.exists()
    assert not generated_config.exists()
    assert any("preserved-user-data" in item for item in result["skipped"])


def test_uninstall_preserve_user_data_keeps_supermedicine_config_when_recorded(tmp_path):
    config = tmp_path / ".supermedicine" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text("project_name: supermedicine\n", encoding="utf-8")
    record = tmp_path / ".supermedicine" / "install-record.json"
    record.write_text(
        json.dumps({"user_data_paths": [".supermedicine"]}),
        encoding="utf-8",
    )

    result = uninstall(tmp_path, force=True, preserve_user_data=True)

    assert result["status"] == "removed"
    assert config.exists()
    assert any("preserved-user-data-parent" in item for item in result["skipped"])


def test_uninstall_reports_residuals_and_repair_suggestions_when_delete_fails(
    tmp_path, monkeypatch
):
    blocked = tmp_path / ".supermedicine" / "blocked.log"
    blocked.parent.mkdir(parents=True)
    blocked.write_text("locked", encoding="utf-8")

    def fail_delete(path):
        raise OSError("file is locked")

    monkeypatch.setattr("Uninstall._delete_path", fail_delete)

    result = uninstall(tmp_path, force=True)

    assert result["status"] == "removed-with-residuals"
    assert result["residuals"]
    assert result["repair_suggestions"]

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from Cli import CLI, main
from core.paper_import.enrichment import PaperEnricher
from core.paper_import.importer import PaperImporter
from core.workspace import WorkspaceManager
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from permission.policy import ensure_default_policy


REPO_ROOT = Path(__file__).resolve().parents[1]


def _copy_default_policy(project_dir: Path) -> None:
    ensure_default_policy(project_dir, source_root=REPO_ROOT)


def _write_delta_policy(project_dir: Path, *, allowed: list[dict], denied: list[dict] | None = None) -> None:
    policies = project_dir / ".supermedicine" / "policies"
    policies.mkdir(parents=True, exist_ok=True)
    (policies / PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
        yaml.safe_dump(
            {
                "agent_id": "delta",
                "role": "paper-cli-tests",
                "permissions": {
                    "allowed": allowed,
                    "denied": denied or [],
                    "hard_limits": {"network_access": True, "external_api": True},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _audit_entries(project_dir: Path) -> list[dict]:
    audit_log = project_dir / ".supermedicine" / "policies" / "audit.jsonl"
    if not audit_log.exists():
        return []
    return [json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()]


class CountingProvider:
    name = "counting-provider"
    resource = "mock://counting-provider"
    requires_network = True
    requires_external_api = True

    def __init__(self, payload: dict | None = None) -> None:
        self.calls = 0
        self.payload = payload or {}

    def fetch(self, metadata):
        self.calls += 1
        return dict(self.payload)


def test_paper_import_cli_requires_explicit_workspace(monkeypatch):
    monkeypatch.setattr("sys.argv", ["supermedicine", "paper", "import", "paper.md"])

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 2


def test_paper_import_cli_copies_file_and_writes_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("paper-study")
    source = tmp_path / "source.md"
    source_content = "# CLI import\n\nUTF-8 note: Δ response.\n"
    source.write_text(source_content, encoding="utf-8")

    result = CLI().paper_import(
        "paper-study",
        source,
        metadata={
            "title": "CLI Paper",
            "doi": "10.1234/cli.paper",
            "pmid": "12345678",
            "notes": "curated note",
            "tags": ["cli", "paper"],
        },
    )

    expected_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    workspace = tmp_path / "workspaces" / "paper-study"
    expected_copy = workspace / "papers" / "originals" / f"{expected_sha256}.md"
    metadata_path = workspace / "papers" / "metadata" / f"{expected_sha256}.json"
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result["metadata"]["id"] == expected_sha256
    assert expected_copy.read_text(encoding="utf-8") == source_content
    assert saved_metadata["title"] == "CLI Paper"
    assert saved_metadata["doi"] == "10.1234/cli.paper"
    assert saved_metadata["pmid"] == "12345678"
    assert saved_metadata["notes"] == "curated note"
    assert saved_metadata["tags"] == ["cli", "paper"]
    assert source.read_text(encoding="utf-8") == source_content


def test_paper_list_show_edit_use_explicit_workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("paper-study")
    source = tmp_path / "source.md"
    source.write_text("# Editable paper\n", encoding="utf-8")

    imported = CLI().paper_import("paper-study", source, metadata={"title": "Original", "tags": ["draft"]})
    paper_id = imported["metadata"]["id"]

    listed = CLI().paper_list("paper-study")
    shown = CLI().paper_show("paper-study", paper_id)
    edited = CLI().paper_edit(
        "paper-study",
        paper_id,
        {"title": "Edited", "doi": "10.1234/edited", "notes": "updated", "tags": ["edited"]},
    )

    assert [paper["id"] for paper in listed] == [paper_id]
    assert shown["id"] == paper_id
    assert shown["title"] == "Original"
    assert edited["id"] == paper_id
    assert edited["title"] == "Edited"
    assert edited["doi"] == "10.1234/edited"
    assert edited["notes"] == "updated"
    assert edited["tags"] == ["edited"]


def test_enrichment_does_not_call_provider_without_confirm_and_audits_skip(tmp_path):
    _copy_default_policy(tmp_path)
    provider = CountingProvider({"title": "Should not be used"})
    source = tmp_path / "paper.md"
    source.write_text("# Skip enrichment\n", encoding="utf-8")
    metadata = PaperImporter(WorkspaceManager(tmp_path)).import_paper(
        WorkspaceManager(tmp_path).initialize_workspace("paper-study").id,
        source,
        metadata={"title": "Original"},
    ).metadata

    result = PaperEnricher(
        PermissionEngine(tmp_path / ".supermedicine" / "policies", tmp_path / ".supermedicine" / "policies" / "audit.jsonl"),
        AuditLogger(tmp_path / ".supermedicine" / "policies" / "audit.jsonl"),
        provider=provider,
    ).enrich(metadata, confirmed=False)

    assert result.status == "skipped"
    assert provider.calls == 0
    assert metadata.title == "Original"
    entries = _audit_entries(tmp_path)
    assert entries[-1]["action"] == "paper.enrich"
    assert entries[-1]["result"] == "skipped"
    assert entries[-1]["reason"] == "missing_explicit_confirmation"


def test_enrichment_permission_deny_prevents_provider_call_and_audits_denial(tmp_path):
    _write_delta_policy(
        tmp_path,
        allowed=[],
        denied=[{"action": "paper.enrich", "scope": "*"}],
    )
    workspace = WorkspaceManager(tmp_path).initialize_workspace("paper-study")
    source = tmp_path / "paper.md"
    source.write_text("# Denied enrichment\n", encoding="utf-8")
    metadata = PaperImporter(tmp_path).import_paper(workspace.id, source, metadata={"title": "Original"}).metadata
    provider = CountingProvider({"title": "Should not be used"})

    result = PaperEnricher(
        PermissionEngine(tmp_path / ".supermedicine" / "policies", tmp_path / ".supermedicine" / "policies" / "audit.jsonl"),
        AuditLogger(tmp_path / ".supermedicine" / "policies" / "audit.jsonl"),
        provider=provider,
    ).enrich(metadata, confirmed=True)

    assert result.status == "denied"
    assert provider.calls == 0
    assert metadata.title == "Original"
    entries = _audit_entries(tmp_path)
    assert any(entry["action"] == "paper.enrich" and entry["result"] == "denied" for entry in entries)


def test_cli_enrichment_allow_uses_mocked_provider_and_updates_metadata(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    workspace = WorkspaceManager(tmp_path).initialize_workspace("paper-study")
    source = tmp_path / "paper.md"
    source.write_text("# Enrich me\n", encoding="utf-8")
    imported = CLI().paper_import(workspace.id, source, metadata={"title": "Original", "tags": ["seed"]})
    paper_id = imported["metadata"]["id"]
    provider = CountingProvider(
        {
            "title": "Enriched Title",
            "authors": ["Ada Lovelace"],
            "doi": "10.1234/enriched",
            "tags": ["seed", "enriched"],
        }
    )
    monkeypatch.setattr("core.paper_import.enrichment.LocalMockMetadataProvider", lambda: provider)

    result = CLI().paper_enrich(workspace.id, paper_id, confirm_enrich=True)
    saved_metadata = json.loads((workspace.path / "papers" / "metadata" / f"{paper_id}.json").read_text(encoding="utf-8"))

    assert provider.calls == 1
    assert result["status"] == "enriched"
    assert result["metadata"]["title"] == "Enriched Title"
    assert saved_metadata["title"] == "Enriched Title"
    assert saved_metadata["authors"] == ["Ada Lovelace"]
    assert saved_metadata["doi"] == "10.1234/enriched"
    assert saved_metadata["tags"] == ["seed", "enriched"]


def test_denied_enrichment_does_not_corrupt_import(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_delta_policy(
        tmp_path,
        allowed=[],
        denied=[{"action": "paper.enrich", "scope": "*"}],
    )
    WorkspaceManager(tmp_path).initialize_workspace("paper-study")
    source = tmp_path / "paper.md"
    source_content = "# Import survives denied enrichment\n"
    source.write_text(source_content, encoding="utf-8")
    provider = CountingProvider({"title": "Should not be used"})
    monkeypatch.setattr("core.paper_import.enrichment.LocalMockMetadataProvider", lambda: provider)

    result = CLI().paper_import(
        "paper-study",
        source,
        metadata={"title": "Original", "notes": "keep", "tags": ["safe"]},
        enrich=True,
        confirm_enrich=True,
    )

    paper_id = result["metadata"]["id"]
    workspace = tmp_path / "workspaces" / "paper-study"
    metadata_path = workspace / "papers" / "metadata" / f"{paper_id}.json"
    stored_path = workspace / "papers" / "originals" / f"{paper_id}.md"
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert provider.calls == 0
    assert result["warnings"] == ["enrichment denied by permission policy"]
    assert stored_path.read_text(encoding="utf-8") == source_content
    assert saved_metadata["title"] == "Original"
    assert saved_metadata["notes"] == "keep"
    assert saved_metadata["tags"] == ["safe"]


def test_old_cli_commands_and_run_flags_still_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    WorkspaceManager(tmp_path).initialize_workspace("trial-1")
    captured = {}

    class FakeRegistry:
        def discover(self):
            return []

    class FakeCheckpointManager:
        base_dir = "checkpoints"

    class FakeKernel:
        def __init__(self, *args, **kwargs):
            self._config_path = kwargs["config_path"]
            self._plugins_dir = kwargs["plugins_dir"]
            self._policies_dir = kwargs["policies_dir"]
            self.plugin_registry = FakeRegistry()
            self.checkpoint_manager = FakeCheckpointManager()

        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["task"] = task
            captured["plugin"] = plugin_name
            captured["action"] = action
            captured["params"] = params
            return {"status": "success", "task": task, "plugin": plugin_name, "action": action}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    monkeypatch.setattr(
        "sys.argv",
        [
            "supermedicine",
            "run",
            "legacy task",
            "--verbose",
            "--plugin",
            "p",
            "--action",
            "a",
            "--params-json",
            '{"source_id":"src-1"}',
            "--workspace",
            "trial-1",
        ],
    )

    main()

    assert captured["task"] == "legacy task"
    assert captured["plugin"] == "p"
    assert captured["action"] == "a"
    assert captured["params"]["source_id"] == "src-1"
    assert captured["params"]["_workspace"]["id"] == "trial-1"

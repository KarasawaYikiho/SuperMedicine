from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
import yaml

from cli_entry import CLI, main
from core.paper_import import PaperImporter
from core.paper_import.online import (
    MAX_RESPONSE_BYTES,
    OnlinePaper,
    OnlinePaperClient,
    OnlinePaperError,
)
from core.paper_import.enrichment import PaperEnricher
from core.paper_import.contracts import (
    MissingPaperSourceError,
    UnsupportedPaperFormatError,
)
from core.workspace import WorkspaceManager
from core.workspace import WorkspaceNotFoundError
from permission.audit import AuditLogger
from permission.engine import PermissionEngine
from plugins.rag.providers import LocalRAGProvider
from core.services.rag import RAGService
from core.services.research import PaperRAGService
from tests import KernelDouble, copy_default_policy as _copy_default_policy


SUPPORTED_EXTENSIONS = (".pdf", ".tex", ".bib", ".ris", ".txt", ".md")


def _write_delta_policy(
    project_dir: Path, *, allowed: list[dict], denied: list[dict] | None = None
) -> None:
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
    return [
        json.loads(line) for line in audit_log.read_text(encoding="utf-8").splitlines()
    ]


def _source_bytes(extension: str) -> bytes:
    if extension == ".pdf":
        return b"%PDF-1.7\nfocused paper import fixture\n%%EOF\n"
    return f"Focused paper import fixture for {extension}\n".encode("utf-8")


def _paper_storage_state(workspace_path):
    papers_dir = workspace_path / "papers"
    if not papers_dir.exists():
        return {}
    return {
        path.relative_to(papers_dir).as_posix(): path.read_bytes()
        for path in sorted(papers_dir.rglob("*"))
        if path.is_file()
    }


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


# ═══ Paper CLI Tests ═══


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

    imported = CLI().paper_import(
        "paper-study", source, metadata={"title": "Original", "tags": ["draft"]}
    )
    paper_id = imported["metadata"]["id"]

    listed = CLI().paper_list("paper-study")
    shown = CLI().paper_show("paper-study", paper_id)
    edited = CLI().paper_edit(
        "paper-study",
        paper_id,
        {
            "title": "Edited",
            "doi": "10.1234/edited",
            "notes": "updated",
            "tags": ["edited"],
        },
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
    metadata = (
        PaperImporter(WorkspaceManager(tmp_path))
        .import_paper(
            WorkspaceManager(tmp_path).initialize_workspace("paper-study").id,
            source,
            metadata={"title": "Original"},
        )
        .metadata
    )

    result = PaperEnricher(
        PermissionEngine(
            tmp_path / ".supermedicine" / "policies",
            tmp_path / ".supermedicine" / "policies" / "audit.jsonl",
        ),
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
    metadata = (
        PaperImporter(tmp_path)
        .import_paper(workspace.id, source, metadata={"title": "Original"})
        .metadata
    )
    provider = CountingProvider({"title": "Should not be used"})

    result = PaperEnricher(
        PermissionEngine(
            tmp_path / ".supermedicine" / "policies",
            tmp_path / ".supermedicine" / "policies" / "audit.jsonl",
        ),
        AuditLogger(tmp_path / ".supermedicine" / "policies" / "audit.jsonl"),
        provider=provider,
    ).enrich(metadata, confirmed=True)

    assert result.status == "denied"
    assert provider.calls == 0
    assert metadata.title == "Original"
    entries = _audit_entries(tmp_path)
    assert any(
        entry["action"] == "paper.enrich" and entry["result"] == "denied"
        for entry in entries
    )


def test_cli_enrichment_allow_uses_mocked_provider_and_updates_metadata(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _copy_default_policy(tmp_path)
    workspace = WorkspaceManager(tmp_path).initialize_workspace("paper-study")
    source = tmp_path / "paper.md"
    source.write_text("# Enrich me\n", encoding="utf-8")
    imported = CLI().paper_import(
        workspace.id, source, metadata={"title": "Original", "tags": ["seed"]}
    )
    paper_id = imported["metadata"]["id"]
    provider = CountingProvider(
        {
            "title": "Enriched Title",
            "authors": ["Ada Lovelace"],
            "doi": "10.1234/enriched",
            "tags": ["seed", "enriched"],
        }
    )
    monkeypatch.setattr(
        "core.paper_import.enrichment.LocalMockMetadataProvider", lambda: provider
    )

    result = CLI().paper_enrich(workspace.id, paper_id, confirm_enrich=True)
    saved_metadata = json.loads(
        (workspace.path / "papers" / "metadata" / f"{paper_id}.json").read_text(
            encoding="utf-8"
        )
    )

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
    monkeypatch.setattr(
        "core.paper_import.enrichment.LocalMockMetadataProvider", lambda: provider
    )

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

    class FakeKernel(KernelDouble):
        def execute_task(self, task, plugin_name=None, action=None, params=None):
            captured["task"] = task
            captured["plugin"] = plugin_name
            captured["action"] = action
            captured["params"] = params
            return {
                "status": "success",
                "task": task,
                "plugin": plugin_name,
                "action": action,
            }

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


# ═══ Paper Import Core Tests ═══


@pytest.mark.parametrize("extension", SUPPORTED_EXTENSIONS)
def test_import_supports_expected_extensions_and_preserves_source(tmp_path, extension):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("paper-study")
    source = tmp_path / f"source{extension}"
    source_content = _source_bytes(extension)
    source.write_bytes(source_content)

    result = PaperImporter(manager).import_paper(workspace.id, source)

    expected_sha256 = hashlib.sha256(source_content).hexdigest()
    expected_copy = (
        workspace.path / "papers" / "originals" / f"{expected_sha256}{extension}"
    )
    assert result.metadata.sha256 == expected_sha256
    assert result.metadata.format == extension
    assert result.metadata.stored_path == expected_copy
    assert expected_copy.read_bytes() == source_content
    assert source.read_bytes() == source_content


def test_import_writes_metadata_json_and_import_log_jsonl(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("metadata-study")
    source = tmp_path / "paper.md"
    source_content = "# Importable paper\n\nSource remains unchanged.\n"
    source.write_text(source_content, encoding="utf-8")
    editable_fields = {
        "title": "Focused Import Study",
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "doi": "10.1234/supermedicine.2026.001",
        "pmid": "12345678",
        "notes": "Clinician-curated note with UTF-8: Δ response.",
        "tags": ["import", "paper", "focused-tests"],
    }

    result = PaperImporter(manager).import_paper(
        workspace.id,
        source,
        metadata=editable_fields,
    )

    metadata_path = (
        workspace.path / "papers" / "metadata" / f"{result.metadata.id}.json"
    )
    import_log_path = workspace.path / "papers" / "imports" / "import-log.jsonl"
    expected_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    expected_copy = workspace.path / "papers" / "originals" / f"{expected_sha256}.md"

    assert metadata_path.is_file()
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert saved_metadata["id"] == result.metadata.id
    assert saved_metadata["sha256"] == expected_sha256
    assert saved_metadata["format"] == ".md"
    assert saved_metadata["stored_path"] == str(expected_copy)
    for field, value in editable_fields.items():
        assert saved_metadata[field] == value

    assert import_log_path.is_file()
    log_lines = import_log_path.read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 1
    log_record = json.loads(log_lines[0])
    assert log_record["paper_id"] == result.metadata.id
    assert log_record["sha256"] == expected_sha256
    assert log_record["source_path"] == str(source)
    assert log_record["stored_path"] == str(expected_copy)
    assert log_record["metadata_path"] == str(metadata_path)

    assert source.read_text(encoding="utf-8") == source_content


def test_import_duplicate_sha256_reuses_existing_original_metadata_and_logs_attempt(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("duplicate-study")
    source = tmp_path / "paper.md"
    source_content = "# Duplicate paper\n\nSame content should be stored once.\n"
    source.write_text(source_content, encoding="utf-8")

    importer = PaperImporter(manager)
    first_result = importer.import_paper(
        workspace.id,
        source,
        metadata={"title": "Original curated title", "notes": "Keep this note."},
    )
    metadata_path = (
        workspace.path / "papers" / "metadata" / f"{first_result.metadata.id}.json"
    )
    stored_path = (
        workspace.path / "papers" / "originals" / f"{first_result.metadata.sha256}.md"
    )
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    saved_metadata["title"] = "User edited title"
    saved_metadata["notes"] = "User edited notes should survive duplicate imports."
    metadata_path.write_text(
        json.dumps(saved_metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    second_result = importer.import_paper(
        workspace.id,
        source,
        metadata={"title": "Duplicate supplied title", "notes": "Do not overwrite."},
    )

    metadata_files = list((workspace.path / "papers" / "metadata").glob("*.json"))
    original_files = list((workspace.path / "papers" / "originals").glob("*"))
    preserved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    log_lines = (
        (workspace.path / "papers" / "imports" / "import-log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    duplicate_log_record = json.loads(log_lines[-1])

    assert first_result.duplicate is False
    assert first_result.duplicate_reason is None
    assert second_result.duplicate is True
    assert second_result.duplicate_reason == "sha256_already_imported"
    assert second_result.metadata.id == first_result.metadata.id
    assert second_result.metadata.sha256 == first_result.metadata.sha256
    assert second_result.metadata.title == "User edited title"
    assert (
        second_result.metadata.notes
        == "User edited notes should survive duplicate imports."
    )
    assert metadata_files == [metadata_path]
    assert original_files == [stored_path]
    assert preserved_metadata["title"] == "User edited title"
    assert (
        preserved_metadata["notes"]
        == "User edited notes should survive duplicate imports."
    )
    assert len(log_lines) == 2
    assert duplicate_log_record["paper_id"] == first_result.metadata.id
    assert duplicate_log_record["sha256"] == first_result.metadata.sha256
    assert duplicate_log_record["duplicate"] is True
    assert duplicate_log_record["duplicate_reason"] == "sha256_already_imported"


@pytest.mark.parametrize(
    (
        "workspace_id",
        "first_title",
        "second_title",
        "first_metadata",
        "second_metadata",
        "expected_reason",
    ),
    [
        (
            "doi-duplicate-study",
            "Original DOI title",
            "Duplicate DOI title",
            {"doi": "  https://doi.org/10.1234/SuperMedicine.DOI  "},
            {"doi": "10.1234/supermedicine.doi"},
            "doi_already_imported",
        ),
        (
            "pmid-duplicate-study",
            "Original PMID title",
            "Duplicate PMID title",
            {"pmid": " PMID: 12345678 "},
            {"pmid": "12345678"},
            "pmid_already_imported",
        ),
    ],
)
def test_import_duplicate_external_ids_reuse_existing_metadata_without_new_original(
    tmp_path,
    workspace_id,
    first_title,
    second_title,
    first_metadata,
    second_metadata,
    expected_reason,
):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace(workspace_id)
    first_source = tmp_path / "first.md"
    second_source = tmp_path / "second.md"
    first_source.write_text("# First paper\n\nOriginal source bytes.\n", encoding="utf-8")
    second_source.write_text("# Second paper\n\nDifferent source bytes.\n", encoding="utf-8")

    importer = PaperImporter(manager)
    first_result = importer.import_paper(
        workspace.id,
        first_source,
        metadata={"title": first_title, **first_metadata},
    )
    metadata_path = (
        workspace.path / "papers" / "metadata" / f"{first_result.metadata.id}.json"
    )
    stored_path = (
        workspace.path / "papers" / "originals" / f"{first_result.metadata.sha256}.md"
    )

    second_result = importer.import_paper(
        workspace.id,
        second_source,
        metadata={"title": second_title, **second_metadata},
    )

    metadata_files = list((workspace.path / "papers" / "metadata").glob("*.json"))
    original_files = list((workspace.path / "papers" / "originals").glob("*"))
    log_lines = (
        (workspace.path / "papers" / "imports" / "import-log.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    duplicate_log_record = json.loads(log_lines[-1])

    assert second_result.duplicate is True
    assert second_result.duplicate_reason == expected_reason
    assert second_result.metadata.id == first_result.metadata.id
    assert second_result.metadata.title == first_title
    assert metadata_files == [metadata_path]
    assert original_files == [stored_path]
    assert len(log_lines) == 2
    assert duplicate_log_record["paper_id"] == first_result.metadata.id
    assert duplicate_log_record["duplicate"] is True
    assert duplicate_log_record["duplicate_reason"] == expected_reason


def test_import_rejects_unsupported_extension_without_partial_writes(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("unsupported-extension-study")
    source = tmp_path / "paper.docx"
    source.write_bytes(b"unsupported paper source bytes")
    before_state = _paper_storage_state(workspace.path)

    with pytest.raises(UnsupportedPaperFormatError):
        PaperImporter(manager).import_paper(workspace.id, source)

    assert _paper_storage_state(workspace.path) == before_state
    assert not any((workspace.path / "papers" / "originals").iterdir())
    assert not any((workspace.path / "papers" / "metadata").iterdir())
    assert not any((workspace.path / "papers" / "imports").iterdir())


def test_import_rejects_missing_source_without_partial_writes(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("missing-source-study")
    source = tmp_path / "missing.md"
    before_state = _paper_storage_state(workspace.path)

    with pytest.raises(MissingPaperSourceError):
        PaperImporter(manager).import_paper(workspace.id, source)

    assert _paper_storage_state(workspace.path) == before_state
    assert not any((workspace.path / "papers" / "originals").iterdir())
    assert not any((workspace.path / "papers" / "metadata").iterdir())
    assert not any((workspace.path / "papers" / "imports").iterdir())


def test_import_propagates_missing_workspace_without_creating_workspace_or_partial_writes(
    tmp_path,
):
    manager = WorkspaceManager(tmp_path)
    source = tmp_path / "paper.md"
    source.write_text(
        "# Existing source\n\nDo not create a workspace implicitly.\n", encoding="utf-8"
    )
    missing_workspace_path = manager.workspace_path("missing-workspace-study")

    with pytest.raises(WorkspaceNotFoundError):
        PaperImporter(manager).import_paper("missing-workspace-study", source)

    assert not missing_workspace_path.exists()


def test_markdown_import_is_added_to_the_workspace_local_rag_index(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("rag-paper-study")
    source = tmp_path / "evidence.md"
    source.write_text("# Hypertension evidence\nLifestyle treatment is supported.", encoding="utf-8")

    PaperImporter(manager).import_paper(workspace.id, source)

    result = LocalRAGProvider(
        workspace.path / ".supermedicine" / "rag" / "local"
    ).query("hypertension")
    assert result["items"][0]["source"] == "paper_import"


def test_pdf_import_indexes_extractable_text_with_page_number(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("pdf-rag-study")
    source = tmp_path / "evidence.pdf"
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 12 Tf 72 720 Td (Hypertension ACEI evidence from a PDF page) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    with source.open("wb") as output:
        writer.write(output)

    result = PaperImporter(manager).import_paper(workspace.id, source)
    items = LocalRAGProvider(
        workspace.path / ".supermedicine" / "rag" / "local"
    ).query("hypertension ACEI")["items"]

    assert result.status == "imported"
    assert items[0]["page"] == 1
    assert items[0]["document_id"] == result.metadata.id


def test_blank_pdf_import_reports_ocr_required_without_claiming_indexed(tmp_path):
    from pypdf import PdfWriter

    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("ocr-study")
    source = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with source.open("wb") as output:
        writer.write(output)

    result = PaperImporter(manager).import_paper(workspace.id, source)

    assert result.status == "ocr_required"
    assert result.warnings == ["ocr_required: PDF contains no extractable text"]
    index_file = workspace.path / ".supermedicine" / "rag" / "local" / "documents.json"
    assert not index_file.exists()


def test_paper_delete_removes_original_metadata_and_rag_chunks(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("delete-rag-paper")
    source = tmp_path / "evidence.md"
    source.write_text("Unique thrombolysis evidence", encoding="utf-8")
    importer = PaperImporter(manager)
    imported = importer.import_paper(workspace.id, source)

    deleted = importer.delete_paper(workspace.id, imported.metadata.id)

    assert deleted["status"] == "deleted"
    assert not imported.metadata.stored_path.exists()
    assert LocalRAGProvider(
        workspace.path / ".supermedicine" / "rag" / "local"
    ).query("thrombolysis")["items"] == []


def test_import_preserves_copied_paper_and_reports_retryable_index_failure(
    tmp_path, monkeypatch
):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("rag-index-failure-study")
    source = tmp_path / "evidence.md"
    source.write_text("# Evidence\nImport must survive index failure.", encoding="utf-8")

    def fail_index(*args, **kwargs):
        raise OSError("index unavailable")

    monkeypatch.setattr(RAGService, "index_workspace_document", fail_index)

    result = PaperImporter(manager).import_paper(workspace.id, source)

    assert result.status == "imported_with_index_error"
    assert result.metadata.stored_path.is_file()
    assert result.warnings == ["rag_index_failed: retry paper indexing"]


def test_online_crossref_search_normalizes_results_without_optional_dependencies():
    def get_json(url: str) -> dict:
        assert "api.crossref.org/works?" in url
        return {
            "message": {
                "items": [
                    {
                        "DOI": "10.1000/example",
                        "title": ["Evidence review"],
                        "author": [{"given": "Ada", "family": "Lovelace"}],
                        "container-title": ["Medical Journal"],
                        "published-online": {"date-parts": [[2026, 7, 1]]},
                        "URL": "https://doi.org/10.1000/example",
                    }
                ]
            }
        }

    results = OnlinePaperClient(json_getter=get_json).search(
        "evidence review", source="crossref"
    )

    assert [item.external_id for item in results] == ["10.1000/example"]
    assert results[0].authors == ("Ada Lovelace",)
    assert results[0].published == "2026-7-1"


def test_online_pubmed_search_and_fetch_are_normalized():
    def get_json(url: str) -> dict:
        if "esearch.fcgi" in url:
            return {"esearchresult": {"idlist": ["123", "not-an-id", "456"]}}
        assert "esummary.fcgi" in url
        return {
            "result": {
                "123": {
                    "title": "Evidence A",
                    "authors": [{"name": "Author One"}],
                    "articleids": [{"idtype": "doi", "value": "10.1000/a"}],
                    "source": "Journal A",
                    "pubdate": "2026",
                },
                "456": {"title": "Evidence B"},
            }
        }

    xml = """
    <PubmedArticleSet><PubmedArticle><MedlineCitation><Article>
      <ArticleTitle>Evidence A</ArticleTitle>
      <Abstract><AbstractText>Bounded abstract.</AbstractText></Abstract>
      <AuthorList><Author><ForeName>Author</ForeName><LastName>One</LastName></Author></AuthorList>
      <Journal><Title>Journal A</Title></Journal>
    </Article></MedlineCitation><PubmedData><ArticleIdList>
      <ArticleId IdType="doi">10.1000/a</ArticleId>
    </ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>
    """
    client = OnlinePaperClient(json_getter=get_json, text_getter=lambda _url: xml)

    results = client.search("evidence", source="pubmed", limit=2)
    fetched = client.get("pubmed", "123")

    assert [record.external_id for record in results] == ["123", "456"]
    assert results[0].doi == "10.1000/a"
    assert fetched.abstract == "Bounded abstract."
    assert fetched.authors == ("Author One",)


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda client: client.search("", source="pubmed"), "query"),
        (lambda client: client.search("x", source="unknown"), "source"),
        (lambda client: client.search("x", limit=0), "limit"),
        (lambda client: client.get("pubmed", "not-numeric"), "PMID"),
        (lambda client: client.get("crossref", "not-a-doi"), "DOI"),
    ],
)
def test_online_paper_inputs_are_bounded(operation, message):
    with pytest.raises(ValueError, match=message):
        operation(OnlinePaperClient())


def test_online_paper_rejects_invalid_json_xml_and_oversized_response(monkeypatch):
    import core.paper_import.online as online

    with pytest.raises(OnlinePaperError):
        OnlinePaperClient(json_getter=lambda _url: {"message": []}).get(
            "crossref", "10.1000/example"
        )
    with pytest.raises(OnlinePaperError):
        OnlinePaperClient(text_getter=lambda _url: "<broken").get("pubmed", "123")

    class Response:
        headers = {"Content-Length": str(MAX_RESPONSE_BYTES + 1)}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self, _amount):
            return b""

    captured = {}

    def urlopen(request, timeout):
        captured["user_agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setattr(online.urllib.request, "urlopen", urlopen)
    with pytest.raises(OnlinePaperError, match="size limit"):
        online._default_text_getter("https://example.invalid")
    assert captured["user_agent"].startswith("SuperMedicine/")
    assert captured["timeout"] == 20


def test_online_paper_import_creates_workspace_record_and_rag_chunks(tmp_path):
    class StubOnlineClient(OnlinePaperClient):
        def get(self, source: str, external_id: str) -> OnlinePaper:
            assert (source, external_id) == ("pubmed", "12345678")
            return OnlinePaper(
                source="pubmed",
                external_id=external_id,
                title="Hypertension evidence",
                authors=("Researcher One",),
                abstract="ACE inhibitor evidence for hypertension.",
                pmid=external_id,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{external_id}/",
            )

    workspace = WorkspaceManager(tmp_path).initialize_workspace("online-paper")
    service = PaperRAGService(tmp_path, online_client=StubOnlineClient())

    result = service.import_online(workspace.id, "pubmed", "12345678")

    assert result.ok is True
    assert result.data["online_source"]["pmid"] == "12345678"
    assert service.list_papers(workspace.id).data[0]["title"] == "Hypertension evidence"
    items = LocalRAGProvider(
        workspace.path / ".supermedicine" / "rag" / "local"
    ).query("ACE inhibitor")["items"]
    assert items[0]["document_id"] == result.data["metadata"]["id"]


def test_online_import_cache_uses_hash_and_cleans_failed_import(tmp_path, monkeypatch):
    class StubOnlineClient(OnlinePaperClient):
        def __init__(self, external_id: str):
            self.external_id = external_id

        def get(self, source: str, external_id: str) -> OnlinePaper:
            return OnlinePaper(
                source=source,
                external_id=self.external_id,
                title="Evidence",
            )

    workspace = WorkspaceManager(tmp_path).initialize_workspace("cache-test")
    first = PaperRAGService(
        tmp_path, online_client=StubOnlineClient("10.1000/a:b")
    )
    second = PaperRAGService(
        tmp_path, online_client=StubOnlineClient("10.1000/a?b")
    )

    assert first.import_online(workspace.id, "crossref", "10.1000/a:b").ok
    assert second.import_online(workspace.id, "crossref", "10.1000/a?b").ok

    config_cache = Path(os.environ["SM_CONFIG"]).parent / "paper-import-cache"
    assert len(list(config_cache.glob("crossref-*.md"))) == 2

    failing = PaperRAGService(
        tmp_path, online_client=StubOnlineClient("10.1000/failure")
    )
    monkeypatch.setattr(
        failing.importer,
        "import_file",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("import failed")),
    )
    assert failing.import_online(
        workspace.id, "crossref", "10.1000/failure"
    ).ok is False
    assert not list(config_cache.glob("*.tmp"))
    assert len(list(config_cache.glob("crossref-*.md"))) == 2

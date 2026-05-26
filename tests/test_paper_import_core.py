from __future__ import annotations

import hashlib
import json

import pytest

from core.paper_import import PaperImporter
from core.paper_import.errors import MissingPaperSourceError, UnsupportedPaperFormatError
from core.workspace import WorkspaceManager
from core.workspace import WorkspaceNotFoundError


SUPPORTED_EXTENSIONS = (".pdf", ".tex", ".bib", ".ris", ".txt", ".md")


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


@pytest.mark.parametrize("extension", SUPPORTED_EXTENSIONS)
def test_import_supports_expected_extensions_and_preserves_source(tmp_path, extension):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("paper-study")
    source = tmp_path / f"source{extension}"
    source_content = _source_bytes(extension)
    source.write_bytes(source_content)

    result = PaperImporter(manager).import_paper(workspace.id, source)

    expected_sha256 = hashlib.sha256(source_content).hexdigest()
    expected_copy = workspace.path / "papers" / "originals" / f"{expected_sha256}{extension}"
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

    metadata_path = workspace.path / "papers" / "metadata" / f"{result.metadata.id}.json"
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


def test_import_duplicate_sha256_reuses_existing_original_metadata_and_logs_attempt(tmp_path):
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
    metadata_path = workspace.path / "papers" / "metadata" / f"{first_result.metadata.id}.json"
    stored_path = workspace.path / "papers" / "originals" / f"{first_result.metadata.sha256}.md"
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    saved_metadata["title"] = "User edited title"
    saved_metadata["notes"] = "User edited notes should survive duplicate imports."
    metadata_path.write_text(json.dumps(saved_metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    second_result = importer.import_paper(
        workspace.id,
        source,
        metadata={"title": "Duplicate supplied title", "notes": "Do not overwrite."},
    )

    metadata_files = list((workspace.path / "papers" / "metadata").glob("*.json"))
    original_files = list((workspace.path / "papers" / "originals").glob("*"))
    preserved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    log_lines = (workspace.path / "papers" / "imports" / "import-log.jsonl").read_text(encoding="utf-8").splitlines()
    duplicate_log_record = json.loads(log_lines[-1])

    assert first_result.duplicate is False
    assert first_result.duplicate_reason is None
    assert second_result.duplicate is True
    assert second_result.duplicate_reason == "sha256_already_imported"
    assert second_result.metadata.id == first_result.metadata.id
    assert second_result.metadata.sha256 == first_result.metadata.sha256
    assert second_result.metadata.title == "User edited title"
    assert second_result.metadata.notes == "User edited notes should survive duplicate imports."
    assert metadata_files == [metadata_path]
    assert original_files == [stored_path]
    assert preserved_metadata["title"] == "User edited title"
    assert preserved_metadata["notes"] == "User edited notes should survive duplicate imports."
    assert len(log_lines) == 2
    assert duplicate_log_record["paper_id"] == first_result.metadata.id
    assert duplicate_log_record["sha256"] == first_result.metadata.sha256
    assert duplicate_log_record["duplicate"] is True
    assert duplicate_log_record["duplicate_reason"] == "sha256_already_imported"


def test_import_duplicate_doi_reuses_existing_metadata_without_copying_new_original(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("doi-duplicate-study")
    first_source = tmp_path / "first.md"
    second_source = tmp_path / "second.md"
    first_source.write_text("# First DOI paper\n\nOriginal source bytes.\n", encoding="utf-8")
    second_source.write_text("# Second DOI paper\n\nDifferent source bytes.\n", encoding="utf-8")

    importer = PaperImporter(manager)
    first_result = importer.import_paper(
        workspace.id,
        first_source,
        metadata={"title": "Original DOI title", "doi": "  https://doi.org/10.1234/SuperMedicine.DOI  "},
    )
    metadata_path = workspace.path / "papers" / "metadata" / f"{first_result.metadata.id}.json"
    stored_path = workspace.path / "papers" / "originals" / f"{first_result.metadata.sha256}.md"

    second_result = importer.import_paper(
        workspace.id,
        second_source,
        metadata={"title": "Duplicate DOI title", "doi": "10.1234/supermedicine.doi"},
    )

    metadata_files = list((workspace.path / "papers" / "metadata").glob("*.json"))
    original_files = list((workspace.path / "papers" / "originals").glob("*"))
    log_lines = (workspace.path / "papers" / "imports" / "import-log.jsonl").read_text(encoding="utf-8").splitlines()
    duplicate_log_record = json.loads(log_lines[-1])

    assert second_result.duplicate is True
    assert second_result.duplicate_reason == "doi_already_imported"
    assert second_result.metadata.id == first_result.metadata.id
    assert second_result.metadata.title == "Original DOI title"
    assert metadata_files == [metadata_path]
    assert original_files == [stored_path]
    assert len(log_lines) == 2
    assert duplicate_log_record["paper_id"] == first_result.metadata.id
    assert duplicate_log_record["duplicate"] is True
    assert duplicate_log_record["duplicate_reason"] == "doi_already_imported"


def test_import_duplicate_pmid_reuses_existing_metadata_without_copying_new_original(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.initialize_workspace("pmid-duplicate-study")
    first_source = tmp_path / "first.md"
    second_source = tmp_path / "second.md"
    first_source.write_text("# First PMID paper\n\nOriginal source bytes.\n", encoding="utf-8")
    second_source.write_text("# Second PMID paper\n\nDifferent source bytes.\n", encoding="utf-8")

    importer = PaperImporter(manager)
    first_result = importer.import_paper(
        workspace.id,
        first_source,
        metadata={"title": "Original PMID title", "pmid": " PMID: 12345678 "},
    )
    metadata_path = workspace.path / "papers" / "metadata" / f"{first_result.metadata.id}.json"
    stored_path = workspace.path / "papers" / "originals" / f"{first_result.metadata.sha256}.md"

    second_result = importer.import_paper(
        workspace.id,
        second_source,
        metadata={"title": "Duplicate PMID title", "pmid": "12345678"},
    )

    metadata_files = list((workspace.path / "papers" / "metadata").glob("*.json"))
    original_files = list((workspace.path / "papers" / "originals").glob("*"))
    log_lines = (workspace.path / "papers" / "imports" / "import-log.jsonl").read_text(encoding="utf-8").splitlines()
    duplicate_log_record = json.loads(log_lines[-1])

    assert second_result.duplicate is True
    assert second_result.duplicate_reason == "pmid_already_imported"
    assert second_result.metadata.id == first_result.metadata.id
    assert second_result.metadata.title == "Original PMID title"
    assert metadata_files == [metadata_path]
    assert original_files == [stored_path]
    assert len(log_lines) == 2
    assert duplicate_log_record["paper_id"] == first_result.metadata.id
    assert duplicate_log_record["duplicate"] is True
    assert duplicate_log_record["duplicate_reason"] == "pmid_already_imported"


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


def test_import_propagates_missing_workspace_without_creating_workspace_or_partial_writes(tmp_path):
    manager = WorkspaceManager(tmp_path)
    source = tmp_path / "paper.md"
    source.write_text("# Existing source\n\nDo not create a workspace implicitly.\n", encoding="utf-8")
    missing_workspace_path = manager.workspace_path("missing-workspace-study")

    with pytest.raises(WorkspaceNotFoundError):
        PaperImporter(manager).import_paper("missing-workspace-study", source)

    assert not missing_workspace_path.exists()

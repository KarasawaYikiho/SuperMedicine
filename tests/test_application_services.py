from __future__ import annotations

import json

import yaml


def test_service_result_success_has_stable_transport_shape():
    from core.services import ServiceResult

    result = ServiceResult.success(
        {"id": "trial-1"},
        request_id="request-1",
        meta={"service": "workspace"},
    )

    assert result.to_dict() == {
        "ok": True,
        "data": {"id": "trial-1"},
        "error": None,
        "request_id": "request-1",
        "meta": {"service": "workspace"},
    }


def test_service_result_failure_uses_stable_error_code():
    from core.services import ServiceResult

    result = ServiceResult.failure(
        "workspace_not_found",
        "Workspace does not exist",
        request_id="request-2",
        details={"workspace_id": "missing"},
    )

    assert result.ok is False
    assert result.to_dict() == {
        "ok": False,
        "data": None,
        "error": {
            "code": "workspace_not_found",
            "message": "Workspace does not exist",
            "details": {"workspace_id": "missing"},
        },
        "request_id": "request-2",
        "meta": {},
    }


def test_workspace_service_owns_create_list_and_show(tmp_path):
    from core.services import WorkspaceService

    service = WorkspaceService(tmp_path)

    created = service.create("trial-1", name="Trial One", request_id="create-1")
    listed = service.list(request_id="list-1")
    shown = service.show("trial-1", request_id="show-1")

    assert created.ok is True
    assert created.data["name"] == "Trial One"
    assert listed.data == [shown.data]
    assert shown.data["metadata"]["display_name"] == "Trial One"
    assert created.meta == {"service": "workspace", "operation": "create"}


def test_workspace_service_delete_confirmation_failure_is_stable_and_audited(
    tmp_path,
):
    from core.services import WorkspaceService
    from permission.engine import PermissionEngine

    policies = tmp_path / ".supermedicine" / "policies"
    policies.mkdir(parents=True)
    policies.joinpath(PermissionEngine.DEFAULT_POLICY_FILENAME).write_text(
        yaml.safe_dump(
            {
                "agent_id": "delta",
                "role": "default",
                "permissions": {"allowed": [], "denied": []},
            }
        ),
        encoding="utf-8",
    )
    service = WorkspaceService(tmp_path)
    service.create("trial-1")

    result = service.delete("trial-1", confirm="wrong", request_id="delete-1")

    assert result.ok is False
    assert result.error.code == "confirmation_mismatch"
    audit_path = policies / "audit.jsonl"
    entry = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["action"] == "workspace.delete"
    assert entry["result"] == "cancelled"


def test_llm_service_add_list_switch_share_one_result_contract(tmp_path):
    from core.services import LLMService

    service = LLMService(tmp_path)
    added = service.add_provider(
        "openai",
        {
            "base_url": "https://openai.test/v1",
            "api_key": "sk-service-secret",
            "model": "gpt-test",
        },
        set_current=True,
        request_id="llm-add-1",
    )
    listed = service.list_providers(request_id="llm-list-1")
    switched = service.switch_provider("openai", request_id="llm-switch-1")

    assert added.ok is True
    assert switched.ok is True
    assert listed.data["current_provider"] == "openai"
    assert listed.data["providers"]["openai"]["api_key"] == "[REDACTED]"
    assert "sk-service-secret" not in str(added.to_dict())
    assert listed.meta == {"service": "llm", "operation": "list_providers"}


def test_llm_service_failure_preserves_manager_error_code(tmp_path):
    from core.services import LLMService

    result = LLMService(tmp_path).switch_provider("missing")

    assert result.ok is False
    assert result.error.code == "provider_not_found"
    assert result.to_dict()["error"]["details"]["provider"] == "missing"


def test_paper_rag_service_owns_import_list_show_and_edit(tmp_path):
    from core.services import PaperRAGService, WorkspaceService

    WorkspaceService(tmp_path).create("paper-study")
    source = tmp_path / "source.md"
    source.write_text("# Service paper\n", encoding="utf-8")
    service = PaperRAGService(tmp_path)

    imported = service.import_paper(
        "paper-study",
        source,
        metadata={"title": "Original", "tags": ["draft"]},
        request_id="paper-import-1",
    )
    paper_id = imported.data["metadata"]["id"]
    listed = service.list_papers("paper-study")
    shown = service.show_paper("paper-study", paper_id)
    edited = service.edit_metadata(
        "paper-study", paper_id, {"title": "Edited", "tags": ["ready"]}
    )

    assert imported.ok is True
    assert listed.data == [shown.data]
    assert shown.data["title"] == "Original"
    assert edited.data["title"] == "Edited"
    assert edited.data["tags"] == ["ready"]
    assert imported.meta == {"service": "paper_rag", "operation": "import_paper"}


def test_paper_rag_service_missing_paper_has_stable_error(tmp_path):
    from core.services import PaperRAGService, WorkspaceService

    WorkspaceService(tmp_path).create("paper-study")

    result = PaperRAGService(tmp_path).show_paper(
        "paper-study", "missing", request_id="paper-show-1"
    )

    assert result.ok is False
    assert result.error.code == "paper_not_found"
    assert result.request_id == "paper-show-1"
    assert result.error.details == {
        "workspace_id": "paper-study",
        "paper_id": "missing",
    }


def test_paper_rag_service_enrichment_requires_confirmation(tmp_path):
    from core.services import PaperRAGService, WorkspaceService

    WorkspaceService(tmp_path).create("paper-study")
    source = tmp_path / "source.md"
    source.write_text("# Service paper\n", encoding="utf-8")
    service = PaperRAGService(tmp_path)
    imported = service.import_paper("paper-study", source)
    paper_id = imported.data["metadata"]["id"]

    result = service.enrich_metadata("paper-study", paper_id, confirm=False)

    assert result.ok is True
    assert result.data["status"] == "skipped"
    assert result.data["applied_fields"] == []
    assert result.data["metadata"]["id"] == paper_id

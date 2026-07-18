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

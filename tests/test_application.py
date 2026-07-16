from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from cli_entry import CLI
from core.application import AppError, ApplicationFacade, AppResult
from core.runtime_paths import RuntimePaths
from core.web.server import create_app


def _paths(tmp_path) -> RuntimePaths:
    return RuntimePaths.resolve(project_root=tmp_path, source_root=tmp_path)


def test_result_contract_is_frozen_and_slotted() -> None:
    error = AppError(code="not_found", message="missing")
    result = AppResult(ok=False, error=error)

    assert result == AppResult(ok=False, error=error)
    assert not hasattr(result, "__dict__")
    assert not hasattr(error, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.ok = True  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        error.code = "internal_error"  # type: ignore[misc]


def test_facade_requires_explicit_runtime_paths() -> None:
    with pytest.raises(TypeError):
        ApplicationFacade()  # type: ignore[call-arg]


def test_cli_facade_and_web_endpoint_share_core_workspace_data(tmp_path) -> None:
    paths = _paths(tmp_path)
    cli = CLI(paths=paths)
    client = TestClient(create_app(paths=paths))

    created = cli.application.create_workspace("shared-root", name="Shared Root")
    cli_result = cli.application.list_workspaces()
    web_response = client.get("/api/v1/workspaces")

    assert created.ok is True
    assert web_response.status_code == 200
    assert cli_result.data == web_response.json() == [created.data]


def test_web_workspace_endpoint_consumes_injected_application_directly(
    tmp_path, monkeypatch
) -> None:
    expected = [{"id": "from-injected-facade"}]

    class StubApplication:
        def list_workspaces(self) -> AppResult:
            return AppResult(ok=True, data=expected)

    def fail_if_cli_is_constructed() -> None:
        raise AssertionError("workspace HTTP endpoint must not route through CLI")

    monkeypatch.setattr("cli_entry.CLI", fail_if_cli_is_constructed)
    client = TestClient(
        create_app(paths=_paths(tmp_path), application=StubApplication())
    )

    response = client.get("/api/v1/workspaces")

    assert response.status_code == 200
    assert response.json() == expected


@pytest.mark.parametrize(
    ("operation", "expected_code"),
    [
        (lambda app: app.get_workspace("missing"), "not_found"),
        (lambda app: app.get_workspace("INVALID/ID"), "validation_error"),
    ],
)
def test_workspace_failures_have_stable_error_codes(
    tmp_path, operation, expected_code
) -> None:
    result = operation(ApplicationFacade(_paths(tmp_path)))

    assert result.ok is False
    assert result.data is None
    assert result.error is not None
    assert result.error.code == expected_code


def test_error_messages_and_details_are_redacted(tmp_path) -> None:
    secret = "sk-application-secret-value"
    result = ApplicationFacade(_paths(tmp_path)).get_workspace(secret)

    assert result.error is not None
    rendered = f"{result.error.message} {result.error.details}"
    assert secret not in rendered
    assert "[REDACTED]" in rendered


def test_workspace_delete_preserves_exact_confirmation(tmp_path) -> None:
    app = ApplicationFacade(_paths(tmp_path))
    assert app.create_workspace("keep-me").ok is True

    denied = app.delete_workspace("keep-me", confirm="wrong")

    assert denied.ok is False
    assert denied.error is not None
    assert denied.error.code == "validation_error"
    assert app.get_workspace("keep-me").ok is True


def test_workspace_permission_failure_has_stable_error_code(tmp_path) -> None:
    paths = _paths(tmp_path)
    policies = paths.data_root / "policies"
    policies.mkdir(parents=True)
    (policies / "default.yaml").write_text(
        yaml.safe_dump(
            {
                "agent_id": "delta",
                "role": "restricted",
                "permissions": {
                    "allowed": [],
                    "denied": [{"action": "workspace.delete", "scope": "*"}],
                },
            }
        ),
        encoding="utf-8",
    )
    app = ApplicationFacade(paths)
    assert app.create_workspace("keep-me").ok is True

    denied = app.delete_workspace("keep-me", confirm="keep-me")

    assert denied.error is not None
    assert denied.error.code == "permission_denied"
    assert app.get_workspace("keep-me").ok is True


def test_web_workspace_delete_requires_caller_confirmation(tmp_path) -> None:
    paths = _paths(tmp_path)
    app = ApplicationFacade(paths)
    client = TestClient(create_app(paths=paths, application=app))
    assert app.create_workspace("keep-me").ok is True

    missing_body = client.delete("/api/v1/workspaces/keep-me")
    missing = client.request("DELETE", "/api/v1/workspaces/keep-me", json={})
    wrong = client.request(
        "DELETE", "/api/v1/workspaces/keep-me", json={"confirm": "wrong"}
    )

    assert missing_body.status_code == 422
    assert missing.status_code == 422
    assert wrong.status_code == 422
    assert missing_body.json()["error"]["code"] == "validation_error"
    assert missing.json()["error"]["code"] == "validation_error"
    assert wrong.json()["error"]["code"] == "validation_error"
    assert app.get_workspace("keep-me").ok is True


def test_web_workspace_delete_caller_sends_exact_confirmation() -> None:
    source = (
        Path(__file__).parent.parent / "core" / "web" / "frontend" / "app.js"
    ).read_text(encoding="utf-8")

    assert (
        'apiCall("DELETE", "/api/v1/workspaces/" + encodeURIComponent(id), '
        "{ confirm: id })"
    ) in source


def test_web_workspace_delete_accepts_exact_caller_confirmation(tmp_path) -> None:
    paths = _paths(tmp_path)
    source_policy = Path(__file__).parent.parent / "permission" / "default_policy.yaml"
    policies = paths.data_root / "policies"
    policies.mkdir(parents=True)
    (policies / "default.yaml").write_text(
        source_policy.read_text(encoding="utf-8"), encoding="utf-8"
    )
    app = ApplicationFacade(paths)
    client = TestClient(create_app(paths=paths, application=app))
    assert app.create_workspace("delete-me").ok is True

    response = client.request(
        "DELETE",
        "/api/v1/workspaces/delete-me",
        json={"confirm": "delete-me"},
    )

    assert response.json()["status"] == "deleted"
    missing = app.get_workspace("delete-me")
    assert missing.error is not None
    assert missing.error.code == "not_found"

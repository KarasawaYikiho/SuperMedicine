from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

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


def test_facade_requires_explicit_runtime_paths() -> None:
    with pytest.raises(TypeError):
        ApplicationFacade()  # type: ignore[call-arg]


def test_cli_and_web_facades_share_core_workspace_data(tmp_path) -> None:
    paths = _paths(tmp_path)
    cli = CLI(paths=paths)
    web = create_app(paths=paths)

    created = cli.application.create_workspace("shared-root", name="Shared Root")
    cli_result = cli.application.list_workspaces()
    web_result = web.state.application.list_workspaces()

    assert created.ok is True
    assert cli_result == web_result
    assert cli_result.data == [created.data]


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

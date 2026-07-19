"""Security contract tests for remote Web exposure."""

from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


TOKEN = "test-token-with-at-least-thirty-two-bytes"


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", True),
        ("127.10.20.30", True),
        ("::1", True),
        ("localhost", True),
        ("0.0.0.0", False),
        ("::", False),
        ("192.168.1.20", False),
        ("example.test", False),
    ],
)
def test_loopback_host_classification(host, expected):
    from core.web.security import is_loopback_host

    assert is_loopback_host(host) is expected


def test_remote_host_requires_token_file():
    from core.web.security import load_remote_auth_token

    with pytest.raises(ValueError, match="requires --auth-token-file"):
        load_remote_auth_token("0.0.0.0", None)


def test_token_file_must_be_readable_and_high_entropy(tmp_path):
    from core.web.security import load_remote_auth_token

    with pytest.raises(ValueError, match="Unable to read"):
        load_remote_auth_token("0.0.0.0", tmp_path / "missing-token")

    short = tmp_path / "short-token"
    short.write_text("too-short", encoding="utf-8")
    with pytest.raises(ValueError, match="at least 32"):
        load_remote_auth_token("0.0.0.0", short)


def test_loopback_without_token_keeps_local_api_available():
    from core.web.server import create_app

    response = TestClient(create_app()).get("/api/v1/self-evolution")

    assert response.status_code == 200


def test_remote_api_requires_bearer_token():
    from core.web.server import create_app

    client = TestClient(create_app(auth_token=TOKEN))

    missing = client.get("/api/v1/self-evolution")
    incorrect = client.get(
        "/api/v1/self-evolution", headers={"Authorization": "Bearer wrong-token"}
    )
    correct = client.get(
        "/api/v1/self-evolution", headers={"Authorization": f"Bearer {TOKEN}"}
    )

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.json()["error"]["code"] == "authentication_required"
    assert incorrect.status_code == 403
    assert incorrect.json()["error"]["code"] == "invalid_authentication"
    assert correct.status_code == 200


def test_bearer_verification_rejects_non_ascii_input_without_error():
    from core.web.security import verify_bearer_header

    assert verify_bearer_header("Bearer 错误令牌", TOKEN) is False


def test_remote_auth_protects_api_root_path():
    from core.web.server import create_app

    response = TestClient(create_app(auth_token=TOKEN)).get("/api/v1")

    assert response.status_code == 401


def test_remote_auth_does_not_block_index():
    from core.web.server import create_app

    response = TestClient(create_app(auth_token=TOKEN)).get("/")

    assert response.status_code == 200


def test_remote_websocket_rejects_chat_before_authentication(monkeypatch):
    from core.web.server import create_app

    executions = []

    class FakeConfig:
        def set_runtime_state_value(self, *args, **kwargs):
            return None

    class FakeKernel:
        def __init__(self, **kwargs):
            self._config = FakeConfig()

        def execute_task(self, message, **kwargs):
            executions.append(message)
            return {"output": message}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    client = TestClient(create_app(auth_token=TOKEN))

    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"message": "must not run"})
        response = websocket.receive_json()

    assert response == {
        "type": "error",
        "code": "authentication_required",
        "content": "WebSocket authentication is required",
    }
    assert executions == []


def test_remote_websocket_authenticates_before_chat(monkeypatch):
    from core.web.server import create_app

    executions = []

    class FakeConfig:
        def set_runtime_state_value(self, *args, **kwargs):
            return None

    class FakeKernel:
        def __init__(self, **kwargs):
            self._config = FakeConfig()

        def execute_task(self, message, **kwargs):
            executions.append(message)
            return {"output": message}

    monkeypatch.setattr("core.kernel.Kernel", FakeKernel)
    client = TestClient(create_app(auth_token=TOKEN))

    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "auth", "token": TOKEN})
        authenticated = websocket.receive_json()
        websocket.send_json({"message": "safe to run"})
        result = websocket.receive_json()

    assert authenticated == {"type": "auth_ok"}
    assert result == {"type": "result", "data": {"output": "safe to run"}}
    assert executions == ["safe to run"]


def test_frontend_uses_session_only_bearer_authentication():
    root = Path(__file__).resolve().parents[1]
    app_js = (root / "core/web/frontend/app.js").read_text(encoding="utf-8")
    index_html = (root / "core/web/frontend/index.html").read_text(encoding="utf-8")
    style_css = (root / "core/web/frontend/style.css").read_text(encoding="utf-8")

    assert 'id="web-auth-token"' in index_html
    assert 'id="web-auth-save"' in index_html
    assert 'sessionStorage.getItem("supermedicine.webAuthToken")' in app_js
    assert 'sessionStorage.setItem("supermedicine.webAuthToken"' in app_js
    assert "localStorage" not in app_js
    assert 'opts.headers.Authorization = "Bearer " + webAuthToken' in app_js
    assert 'type: "auth", token: webAuthToken' in app_js
    assert "token=" not in app_js
    assert "#web-auth-controls" in style_css
    assert "#web-auth-token" in style_css


@pytest.mark.parametrize(
    ("method", "url", "body", "code"),
    [
        ("post", "/api/v1/chat", {}, "message_required"),
        ("post", "/api/v1/workspaces", {}, "workspace_id_required"),
        ("post", "/api/v1/workspaces/ws/papers", {}, "source_path_required"),
        (
            "post",
            "/api/v1/workspaces/ws/experiences",
            {},
            "experience_fields_required",
        ),
        (
            "delete",
            "/api/v1/workspaces/ws/experiences/experience",
            {},
            "experience_scope_required",
        ),
        ("post", "/api/v1/llm/providers", {}, "provider_required"),
        ("post", "/api/v1/llm/switch", {}, "provider_required"),
        ("post", "/api/v1/permissions/mode", {}, "permission_mode_required"),
        ("post", "/api/v1/permissions/authorize", {}, "path_required"),
        ("post", "/api/v1/logs", {}, "message_required"),
        ("post", "/api/v1/experiments", {}, "protocol_required"),
        (
            "post",
            "/api/v1/experiments/session.json/submit",
            {},
            "experiment_step_input_required",
        ),
    ],
)
def test_api_validation_failures_use_http_400(method, url, body, code):
    from core.web.server import create_app

    response = TestClient(create_app()).request(method.upper(), url, json=body)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == code


def test_unexpected_api_failure_is_redacted(monkeypatch):
    from core.web.server import create_app

    secret = "must-not-leak-in-http-response"
    monkeypatch.setattr(
        "core.services.workspace.WorkspaceManager.list_workspaces",
        lambda self: (_ for _ in ()).throw(RuntimeError(secret)),
    )

    response = TestClient(create_app()).get("/api/v1/workspaces")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert secret not in response.text


def test_web_routes_have_no_legacy_http_200_error_returns():
    server = Path(__file__).resolve().parents[1].joinpath(
        "core", "web", "server.py"
    ).read_text(encoding="utf-8")

    assert 'return {"error":' not in server


def test_request_validation_error_uses_shared_envelope():
    from core.web.server import create_app

    response = TestClient(create_app()).post("/api/v1/chat")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_failed"
    assert response.json()["request_id"]


def test_unknown_api_route_uses_shared_envelope():
    from core.web.server import create_app

    response = TestClient(create_app()).get("/api/v1/not-a-real-route")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"


def test_cli_web_passes_token_file_to_server(monkeypatch, tmp_path):
    from cli_entry import CLI

    token_file = tmp_path / "token"
    captured = {}

    def fake_start_server(host, port, *, reload, auth_token_file):
        captured.update(
            host=host,
            port=port,
            reload=reload,
            auth_token_file=auth_token_file,
        )

    monkeypatch.setattr("core.web.server.start_server", fake_start_server)

    CLI().web(
        host="0.0.0.0",
        port=8123,
        reload=False,
        auth_token_file=token_file,
    )

    assert captured == {
        "host": "0.0.0.0",
        "port": 8123,
        "reload": False,
        "auth_token_file": token_file,
    }


def test_web_parser_passes_auth_token_file(monkeypatch):
    from cli.parser import main

    captured = {}
    token_file = Path("remote-web.token")

    def fake_web(self, *, host, port, reload, auth_token_file):
        captured.update(
            host=host,
            port=port,
            reload=reload,
            auth_token_file=auth_token_file,
        )

    monkeypatch.setattr("cli_entry.CLI.web", fake_web)

    main(
        [
            "web",
            "--host",
            "0.0.0.0",
            "--port",
            "8123",
            "--auth-token-file",
            str(token_file),
        ]
    )

    assert captured == {
        "host": "0.0.0.0",
        "port": 8123,
        "reload": False,
        "auth_token_file": token_file,
    }

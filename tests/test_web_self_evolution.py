"""Tests for Self Evolution API endpoints."""
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client():
    """Create test client."""
    from core.web.server import create_app
    app = create_app()
    return TestClient(app)


def test_self_evolution_list(client):
    """Test GET /api/v1/self-evolution returns a list."""
    response = client.get("/api/v1/self-evolution")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_self_evolution_generate_missing_params(client):
    """Test POST /api/v1/self-evolution/generate with missing params returns error."""
    response = client.post("/api/v1/self-evolution/generate", json={})
    assert response.status_code == 400
    data = response.json()
    assert data.get("status") == "error"


def test_self_evolution_generate_with_params(client):
    """Test POST /api/v1/self-evolution/generate with valid params."""
    response = client.post("/api/v1/self-evolution/generate", json={
        "instruction": "test instruction",
        "type": "code",
        "output": "/tmp/test_output.py",
    })
    assert response.status_code == 200
    # Should return a result (may be error if self_evolve not fully implemented)


def test_self_evolution_get_not_found(client):
    """Test GET /api/v1/self-evolution/{id} with invalid ID returns error."""
    response = client.get("/api/v1/self-evolution/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data.get("status") == "error"


def test_self_evolution_delete_not_found(client):
    """Test DELETE /api/v1/self-evolution/{id} with invalid ID returns error."""
    response = client.delete("/api/v1/self-evolution/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data.get("status") == "error"


def test_diagnose_all(client):
    """Test GET /api/v1/diagnose returns all diagnostics."""
    response = client.get("/api/v1/diagnose")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "config" in data or "error" in data


def test_status_reports_shared_required_runtime_health(client):
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    runtime = response.json()["required_runtime"]
    assert runtime["harness"]["required"] is True
    assert runtime["rag"]["disable_supported"] is False
    assert runtime["agents"]["multi_available"] is True


def test_diagnose_config(client):
    """Test GET /api/v1/diagnose/config returns config diagnostics."""
    response = client.get("/api/v1/diagnose/config")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_diagnose_llm(client):
    """Test GET /api/v1/diagnose/llm returns LLM diagnostics."""
    response = client.get("/api/v1/diagnose/llm")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_diagnose_install(client):
    """Test GET /api/v1/diagnose/install returns install diagnostics."""
    response = client.get("/api/v1/diagnose/install")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "audit" in data or "error" in data


def test_chat_missing_message_returns_http_client_error(client):
    response = client.post("/api/v1/chat", json={})

    assert response.status_code == 400
    assert response.json() == {"error": "No message provided", "status": "error"}


def test_unexpected_api_failure_returns_http_server_error(monkeypatch):
    class ExplodingCLI:
        def workspace_list(self):
            raise RuntimeError("workspace backend failed")

    monkeypatch.setattr("cli_entry.CLI", ExplodingCLI)
    from core.web.server import create_app

    response = TestClient(create_app()).get("/api/v1/workspaces")

    assert response.status_code == 500
    assert response.json() == {
        "error": "workspace backend failed",
        "status": "error",
    }


def test_paper_enrich_requires_explicit_confirmation(monkeypatch):
    """Web paper enrichment should preserve the CLI explicit-confirm boundary."""

    captured: dict[str, object] = {}

    class FakeCLI:
        def paper_enrich(self, workspace_id, paper_id, *, confirm_enrich):
            captured["workspace_id"] = workspace_id
            captured["paper_id"] = paper_id
            captured["confirm_enrich"] = confirm_enrich
            return {"status": "ok"}

    monkeypatch.setattr("cli_entry.CLI", FakeCLI)
    from core.web.server import create_app

    test_client = TestClient(create_app())

    response = test_client.post("/api/v1/workspaces/ws/papers/paper/enrich", json={})

    assert response.status_code == 200
    assert captured == {
        "workspace_id": "ws",
        "paper_id": "paper",
        "confirm_enrich": False,
    }


def test_frontend_inline_handlers_escape_javascript_string_arguments():
    """Inline onclick handlers must not be broken by IDs containing quotes."""

    app_js = Path(__file__).resolve().parents[1].joinpath(
        "core", "web", "frontend", "app.js"
    ).read_text(encoding="utf-8")

    assert "function escapeJsString" in app_js
    assert "onclick=\\\"deleteWorkspace('\" + escapeHtml" not in app_js
    assert "onclick=\\\"showLLM('\" + escapeHtml" not in app_js
    assert "onclick=\\\"viewArtifact('\" + escapeHtml" not in app_js
    assert "onclick=\\\"deleteArtifact('\" + escapeHtml" not in app_js

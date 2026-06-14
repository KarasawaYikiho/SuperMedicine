"""Tests for Diagnose API endpoints."""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from core.web.server import create_app
    app = create_app()
    return TestClient(app)


def test_diagnose_all(client):
    """Test GET /api/v1/diagnose returns all diagnostics."""
    response = client.get("/api/v1/diagnose")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    # Should contain config, llm, audit, log_storage keys
    assert "config" in data or "error" in data


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
    # Should contain audit and log_storage keys
    assert "audit" in data or "error" in data

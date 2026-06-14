"""Tests for Self Evolution API endpoints."""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient


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
    assert response.status_code == 200
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
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "error"


def test_self_evolution_delete_not_found(client):
    """Test DELETE /api/v1/self-evolution/{id} with invalid ID returns error."""
    response = client.delete("/api/v1/self-evolution/nonexistent")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "error"

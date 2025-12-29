"""Integration tests for webhook endpoint."""

import pytest
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from src.ingest_llm_as.routers.webhook import router, linear_circuit_breaker
from fastapi import FastAPI


@pytest.fixture
def app():
    """Create test app with webhook router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    """Reset circuit breaker before each test."""
    linear_circuit_breaker.record_success()
    yield


def generate_signature(payload: bytes, secret: str) -> str:
    """Generate HMAC-SHA256 signature for payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()


def test_webhook_health_endpoint(client):
    """Test webhook health endpoint."""
    response = client.get("/webhook/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "linear_circuit_breaker" in data
    assert "state" in data["linear_circuit_breaker"]


def test_webhook_linear_missing_signature(client, monkeypatch):
    """Test webhook without signature when secret is configured."""
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "test-secret")
    
    payload = {
        "action": "create",
        "data": {"id": "TEST-001"}
    }
    
    response = client.post(
        "/webhook/linear",
        json=payload
    )
    
    assert response.status_code == 401
    assert "Missing Linear-Signature" in response.json()["detail"]


def test_webhook_linear_invalid_signature(client, monkeypatch):
    """Test webhook with invalid signature."""
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "test-secret")
    
    payload = {
        "action": "create",
        "data": {"id": "TEST-001"}
    }
    
    response = client.post(
        "/webhook/linear",
        json=payload,
        headers={"Linear-Signature": "invalid-signature"}
    )
    
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


def test_webhook_linear_valid_signature_success(client, monkeypatch):
    """Test webhook with valid signature."""
    monkeypatch.setenv("LINEAR_WEBHOOK_SECRET", "test-secret")
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    
    payload = {
        "action": "create",
        "data": {"id": "TEST-001"}
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_signature(payload_bytes, "test-secret")
    
    response = client.post(
        "/webhook/linear",
        content=payload_bytes,
        headers={
            "Linear-Signature": signature,
            "Content-Type": "application/json"
        }
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "processed"
    assert data["issue_id"] == "TEST-001"
    assert "correlation_id" in data


def test_webhook_linear_no_signature_when_not_configured(client, monkeypatch):
    """Test webhook works without signature when secret not configured."""
    monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    
    payload = {
        "action": "create",
        "data": {"id": "TEST-002"}
    }
    
    response = client.post(
        "/webhook/linear",
        json=payload
    )
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "processed"
    assert data["issue_id"] == "TEST-002"


def test_webhook_linear_invalid_json(client, monkeypatch):
    """Test webhook with invalid JSON."""
    monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)
    
    response = client.post(
        "/webhook/linear",
        content=b"not-valid-json",
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


def test_webhook_linear_invalid_payload(client, monkeypatch):
    """Test webhook with invalid payload structure."""
    monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)
    
    payload = {
        "action": "create"
        # Missing "data" field
    }
    
    response = client.post(
        "/webhook/linear",
        json=payload
    )
    
    assert response.status_code == 500
    assert "Processing failed" in response.json()["detail"]


def test_webhook_linear_circuit_breaker_opens(client, monkeypatch):
    """Test circuit breaker opens after failures."""
    monkeypatch.delenv("LINEAR_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("POSTGRES_DSN", raising=False)
    monkeypatch.setenv("CIRCUIT_BREAKER_THRESHOLD", "2")
    
    # Create new circuit breaker with lower threshold
    from src.ingest_llm_as.core.circuit_breaker import CircuitBreaker
    test_cb = CircuitBreaker(failure_threshold=2, recovery_timeout=300, name="test")
    
    # Monkey patch the circuit breaker
    import src.ingest_llm_as.routers.webhook as webhook_module
    original_cb = webhook_module.linear_circuit_breaker
    webhook_module.linear_circuit_breaker = test_cb
    
    try:
        # Trigger failures
        invalid_payload = {"action": "create"}  # Missing data
        
        for _ in range(2):
            response = client.post("/webhook/linear", json=invalid_payload)
            assert response.status_code == 500
        
        # Circuit should be open now
        valid_payload = {
            "action": "create",
            "data": {"id": "TEST-003"}
        }
        response = client.post("/webhook/linear", json=valid_payload)
        assert response.status_code == 503
        assert "Circuit breaker open" in response.json()["detail"]
        
    finally:
        # Restore original circuit breaker
        webhook_module.linear_circuit_breaker = original_cb

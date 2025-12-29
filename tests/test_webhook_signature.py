"""Unit tests for webhook signature verification."""

import pytest
from src.ingest_llm_as.core.webhook_signature import verify_signature


def test_verify_signature_valid():
    """Test signature verification with valid signature."""
    payload = b'{"action": "create", "data": {"id": "TEST-001"}}'
    secret = "test-secret-key"
    
    # Generate expected signature manually
    import hmac
    import hashlib
    expected_sig = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    assert verify_signature(payload, expected_sig, secret) is True


def test_verify_signature_invalid():
    """Test signature verification with invalid signature."""
    payload = b'{"action": "create", "data": {"id": "TEST-001"}}'
    secret = "test-secret-key"
    wrong_signature = "invalid-signature-1234567890"
    
    assert verify_signature(payload, wrong_signature, secret) is False


def test_verify_signature_missing_signature():
    """Test signature verification with missing signature."""
    payload = b'{"action": "create"}'
    secret = "test-secret"
    
    assert verify_signature(payload, "", secret) is False
    assert verify_signature(payload, None, secret) is False


def test_verify_signature_missing_secret():
    """Test signature verification with missing secret."""
    payload = b'{"action": "create"}'
    signature = "some-signature"
    
    assert verify_signature(payload, signature, "") is False
    assert verify_signature(payload, signature, None) is False


def test_verify_signature_wrong_secret():
    """Test signature verification with wrong secret."""
    payload = b'{"action": "create", "data": {"id": "TEST-001"}}'
    secret = "correct-secret"
    wrong_secret = "wrong-secret"
    
    # Generate signature with correct secret
    import hmac
    import hashlib
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Verify with wrong secret should fail
    assert verify_signature(payload, signature, wrong_secret) is False


def test_verify_signature_modified_payload():
    """Test signature verification fails with modified payload."""
    original_payload = b'{"action": "create", "data": {"id": "TEST-001"}}'
    modified_payload = b'{"action": "create", "data": {"id": "TEST-002"}}'
    secret = "test-secret"
    
    # Generate signature for original payload
    import hmac
    import hashlib
    signature = hmac.new(
        secret.encode('utf-8'),
        original_payload,
        hashlib.sha256
    ).hexdigest()
    
    # Verify with modified payload should fail
    assert verify_signature(modified_payload, signature, secret) is False


def test_verify_signature_empty_payload():
    """Test signature verification with empty payload."""
    payload = b''
    secret = "test-secret"
    
    import hmac
    import hashlib
    signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Empty payload should still verify correctly
    assert verify_signature(payload, signature, secret) is True

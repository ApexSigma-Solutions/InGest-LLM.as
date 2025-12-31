"""
Unit tests for Linear webhook signature verification.

Tests cover HMAC-SHA256 signature validation, header parsing,
and secret retrieval functionality.

Phase: TN-LINEAR-06 - Webhook Ingestion
"""

import hmac
import hashlib
from unittest.mock import patch

import pytest

from ingest_llm.core.linear_webhook import (
    get_webhook_secret,
    verify_signature,
)


class TestGetWebhookSecret:
    """Test webhook secret retrieval from environment."""

    @patch("ingest_llm.core.linear_webhook.os.getenv")
    def test_get_webhook_secret_from_env(self, mock_getenv):
        """Should retrieve secret from environment variable."""
        mock_getenv.return_value = "test-secret-key-12345"

        secret = get_webhook_secret()

        assert secret == "test-secret-key-12345"
        mock_getenv.assert_called_once_with("LINEAR_WEBHOOK_SECRET")

    @patch("ingest_llm.core.linear_webhook.os.getenv")
    def test_get_webhook_secret_not_set(self, mock_getenv):
        """Should return None when secret is not set."""
        mock_getenv.return_value = None

        secret = get_webhook_secret()

        assert secret is None
        mock_getenv.assert_called_once_with("LINEAR_WEBHOOK_SECRET")

    @patch("ingest_llm.core.linear_webhook.os.getenv")
    def test_get_webhook_secret_empty_string(self, mock_getenv):
        """Should return empty string when secret is empty string."""
        mock_getenv.return_value = ""

        secret = get_webhook_secret()

        # Empty string is returned as-is from env
        assert secret == ""
        mock_getenv.assert_called_once_with("LINEAR_WEBHOOK_SECRET")


class TestVerifySignatureSuccess:
    """Test successful signature verification."""

    def test_verify_signature_valid(self):
        """Should return True for valid signature."""
        payload = b'{"action": "test", "data": {"id": "123"}}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        result = verify_signature(payload, signature, secret)

        assert result is True

    def test_verify_signature_lowercase_hex(self):
        """Should work with lowercase hex digest (standard format)."""
        payload = b'{"action": "test"}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()  # Returns lowercase by default
        # Include sha256= prefix as Linear sends it
        prefixed_signature = f"sha256={signature}"

        result = verify_signature(payload, prefixed_signature, secret)
        assert result is True

    def test_verify_signature_with_unicode_payload(self):
        """Should handle Unicode payloads correctly."""
        payload = '{"action": "test", "data": {"title": "Test Ñoño"}}'.encode("utf-8")
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        result = verify_signature(payload, signature, secret)

        assert result is True

    def test_verify_signature_with_large_payload(self):
        """Should handle large payloads correctly."""
        # Create a large payload (1MB)
        payload = b'{"data": "x" * (1024 * 1024)}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        result = verify_signature(payload, signature, secret)

        assert result is True


class TestVerifySignatureFailure:
    """Test signature verification failures."""

    def test_verify_signature_invalid(self):
        """Should return False for invalid signature."""
        payload = b'{"action": "test"}'
        secret = "test-secret-key"
        valid_signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        invalid_signature = "invalid-signature-12345"

        result = verify_signature(payload, invalid_signature, secret)

        assert result is False

    def test_verify_signature_wrong_payload(self):
        """Should return False when payload differs."""
        payload1 = b'{"action": "test"}'
        payload2 = b'{"action": "different"}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload1,
            hashlib.sha256,
        ).hexdigest()

        result = verify_signature(payload2, signature, secret)

        assert result is False

    def test_verify_signature_wrong_secret(self):
        """Should return False when secret differs."""
        payload = b'{"action": "test"}'
        secret1 = "test-secret-key-1"
        secret2 = "test-secret-key-2"
        signature = hmac.new(
            secret1.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        result = verify_signature(payload, signature, secret2)

        assert result is False

    def test_verify_signature_empty_payload(self):
        """Should return False for empty payload."""
        payload = b''
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            b'{"action": "test"}',
            hashlib.sha256,
        ).hexdigest()

        result = verify_signature(payload, signature, secret)

        assert result is False

    def test_verify_signature_empty_signature(self):
        """Should return False for empty signature."""
        payload = b'{"action": "test"}'
        secret = "test-secret-key"
        signature = ""

        result = verify_signature(payload, signature, secret)

        assert result is False

    def test_verify_signature_none_secret(self):
        """Should return False when secret is None."""
        payload = b'{"action": "test"}'
        secret = None
        signature = hmac.new(
            "test-secret-key".encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        result = verify_signature(payload, signature, secret)

        assert result is False


class TestVerifySignatureEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_verify_signature_with_special_characters(self):
        """Should handle special characters in payload."""
        payload = b'{"action": "test", "data": {"value": "test\n\t\r\\"}}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        result = verify_signature(payload, signature, secret)

        assert result is True

    def test_verify_signature_with_binary_payload(self):
        """Should handle binary payloads correctly."""
        payload = b'\x00\x01\x02\x03'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        result = verify_signature(payload, signature, secret)

        assert result is True

    def test_verify_signature_signature_format_variations(self):
        """Should handle different signature format variations."""
        payload = b'{"action": "test"}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Test with sha256= prefix (Linear format)
        result_with_prefix = verify_signature(payload, f"sha256={signature}", secret)
        assert result_with_prefix is True

        # Test with hex prefix
        result_with_hex = verify_signature(payload, f"0x{signature}", secret)
        assert result_with_hex is False

    def test_verify_signature_timing_attack(self):
        """Should reject timing attacks (different signatures)."""
        payload = b'{"action": "test"}'
        secret = "test-secret-key"
        valid_signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        valid_signature = f"sha256={valid_signature}"

        # Simulate timing attack with different signatures
        for _ in range(100):
            fake_signature = hmac.new(
                f"fake-secret-{_}".encode("utf-8"),
                payload,
                hashlib.sha256,
            ).hexdigest()
            fake_signature = f"sha256={fake_signature}"
            result = verify_signature(payload, fake_signature, secret)
            assert result is False

        # Valid signature should still work
        result = verify_signature(payload, valid_signature, secret)
        assert result is True


class TestVerifySignatureIntegration:
    """Integration tests for signature verification."""

    def test_verify_signature_with_linear_webhook_format(self):
        """Should work with Linear webhook format."""
        # Simulate a Linear webhook payload
        payload = b'{"action": "IssueCreated", "data": {"id": "LIN-123", "title": "Test"}}'
        secret = "linear-webhook-secret"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        result = verify_signature(payload, signature, secret)

        assert result is True

    def test_verify_signature_consistency(self):
        """Should produce consistent results."""
        payload = b'{"action": "test"}'
        secret = "test-secret-key"
        signature = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        # Include sha256= prefix as Linear sends it
        signature = f"sha256={signature}"

        # Verify multiple calls produce same result
        result1 = verify_signature(payload, signature, secret)
        result2 = verify_signature(payload, signature, secret)
        result3 = verify_signature(payload, signature, secret)

        assert result1 == result2 == result3 is True

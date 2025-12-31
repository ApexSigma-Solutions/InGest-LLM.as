"""
Linear Webhook Signature Verification

Validates Linear webhook payloads using HMAC-SHA256 signatures.
Phase: TN-LINEAR-06 - Webhook Ingestion Pipeline
"""
import hashlib
import hmac
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """
    Verify Linear webhook signature using HMAC-SHA256.

    Computes HMAC-SHA256 hash of payload using shared secret and
    compares with provided signature. Linear sends signature in
    'Linear-Signature' header.

    Args:
        payload: Raw request body bytes
        signature: Signature from 'Linear-Signature' header
        secret: Shared secret for webhook verification

    Returns:
        bool: True if signature is valid, False otherwise

    Raises:
        ValueError: If signature format is invalid
    """
    if not signature:
        logger.warning("Missing Linear-Signature header")
        return False

    if not secret:
        logger.error("LINEAR_WEBHOOK_SECRET not configured")
        return False

    try:
        # Linear signature format: sha256=<hex_digest>
        if not signature.startswith("sha256="):
            logger.warning("Invalid signature format: %s", signature)
            return False

        expected_signature = signature[7:]  # Remove 'sha256=' prefix

        # Compute HMAC-SHA256
        computed_hash = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        is_valid = hmac.compare_digest(computed_hash, expected_signature)

        if is_valid:
            logger.info("Webhook signature verified successfully")
        else:
            logger.warning(
                "Webhook signature verification failed",
                extra={
                    "expected": expected_signature[:8] + "...",
                    "computed": computed_hash[:8] + "...",
                },
            )

        return is_valid

    except Exception as e:
        logger.error(
            "Error verifying webhook signature",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        return False


def get_webhook_secret() -> Optional[str]:
    """
    Retrieve Linear webhook secret from environment.

    Returns:
        Optional[str]: Secret value or None if not configured
    """
    secret = os.getenv("LINEAR_WEBHOOK_SECRET")
    if not secret:
        logger.warning("LINEAR_WEBHOOK_SECRET environment variable not set")
    return secret

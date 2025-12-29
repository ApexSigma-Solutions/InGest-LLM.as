"""Linear webhook signature verification."""

import hmac
import hashlib
import os
from typing import Optional


def get_webhook_secret() -> Optional[str]:
    """
    Get Linear webhook secret from environment.
    
    Returns:
        Webhook secret or None if not configured
    """
    return os.getenv("LINEAR_WEBHOOK_SECRET")


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Linear webhook signature using HMAC-SHA256.
    
    Args:
        payload: Raw request body bytes
        signature: Signature from Linear-Signature header
        secret: Webhook secret for verification
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not secret:
        return False
    
    try:
        # Compute expected signature
        expected = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False

# Implements: adr/ADR-022-payment-processing-razorpay-india.md §Amendment 1.2
# constitutional_basis: C-059 (Implementation Traceability), ADR-014 (secret management)
"""Razorpay HTTP client — all configuration from env vars (FA-029)."""
from __future__ import annotations

import hashlib
import hmac
import logging
from base64 import b64encode

import httpx

from config import Settings

logger = logging.getLogger(__name__)

_RAZORPAY_BASE = "https://api.razorpay.com/v1"

# Bundle tier → Razorpay plan_id env var lookup
_PLAN_ENV_KEYS: dict[str, str] = {
    "STARTER": "RAZORPAY_PLAN_ID_STARTER",
    "RUNNER":  "RAZORPAY_PLAN_ID_RUNNER",
    "WINNER":  "RAZORPAY_PLAN_ID_WINNER",
}


class RazorpayClient:
    """Thin async wrapper around Razorpay Orders API.

    Never logs key_id or key_secret values (ADR-014).
    All credentials come from Settings (pydantic-settings / env vars).
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings: Settings = settings or Settings()

    def _auth_header(self) -> str:
        creds = f"{self._settings.RAZORPAY_KEY_ID}:{self._settings.RAZORPAY_KEY_SECRET}"
        return "Basic " + b64encode(creds.encode()).decode()

    async def create_order(
        self,
        amount_paise: int,
        notes: dict[str, str],
    ) -> dict:
        """Create a Razorpay order. Returns the full order object."""
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "notes": notes,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{_RAZORPAY_BASE}/orders",
                json=payload,
                headers={"Authorization": self._auth_header()},
            )
        resp.raise_for_status()
        logger.info("Razorpay order created: order_id=%s amount=%d", resp.json().get("id"), amount_paise)
        return resp.json()

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify Razorpay webhook signature (HMAC-SHA256 of raw body)."""
        secret = self._settings.RAZORPAY_WEBHOOK_SECRET.encode()
        expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify payment capture signature: HMAC of 'order_id|payment_id'."""
        secret = self._settings.RAZORPAY_KEY_SECRET.encode()
        payload = f"{order_id}|{payment_id}".encode()
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

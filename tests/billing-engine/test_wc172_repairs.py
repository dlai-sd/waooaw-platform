# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md (Demo defect repairs)
# Constitutional basis: C-007, C-059
"""Razorpay rate-limit retry and the wallet queries that must use columns that exist."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))

from meter import service as meter_service
from payment import razorpay_client
from payment.razorpay_client import RazorpayClient
from reconciliation import service as reconciliation_service

SETTINGS = SimpleNamespace(RAZORPAY_KEY_ID="rzp_test_x", RAZORPAY_KEY_SECRET="secret")


def _response(status: int, body: dict | None = None, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status, json=body or {}, headers=headers, request=httpx.Request("GET", "https://x"))


def _fake_get(monkeypatch: pytest.MonkeyPatch, replies: list[httpx.Response]) -> list[float]:
    waits: list[float] = []

    async def get(self: httpx.AsyncClient, *_args: object, **_kwargs: object) -> httpx.Response:
        return replies.pop(0)

    async def sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    monkeypatch.setattr(razorpay_client.asyncio, "sleep", sleep)
    return waits


@pytest.mark.asyncio
async def test_a_rate_limited_listing_waits_and_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    waits = _fake_get(
        monkeypatch,
        [_response(429, headers={"Retry-After": "3"}), _response(429), _response(200, {"items": [{"id": "pay_1"}]})],
    )
    items = await RazorpayClient(settings=SETTINGS).list_collection("payments", 0, 10)
    assert items == [{"id": "pay_1"}]
    assert waits == [3.0, 2.0]


@pytest.mark.asyncio
async def test_a_listing_that_stays_rate_limited_fails_after_the_attempt_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    waits = _fake_get(monkeypatch, [_response(429) for _ in range(razorpay_client._RATE_LIMIT_ATTEMPTS)])
    with pytest.raises(httpx.HTTPStatusError):
        await RazorpayClient(settings=SETTINGS).list_collection("refunds", 0, 10)
    assert len(waits) == razorpay_client._RATE_LIMIT_ATTEMPTS - 1


@pytest.mark.asyncio
async def test_other_provider_errors_are_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    waits = _fake_get(monkeypatch, [_response(500)])
    with pytest.raises(httpx.HTTPStatusError):
        await RazorpayClient(settings=SETTINGS).list_collection("payments", 0, 10)
    assert waits == []


def test_retry_wait_is_capped() -> None:
    assert razorpay_client._rate_limit_wait_seconds(_response(429, headers={"Retry-After": "600"}), 0) == 30.0


@pytest.mark.parametrize("module", [meter_service, reconciliation_service])
def test_wallet_queries_use_only_columns_that_exist(module: object) -> None:
    # wallet_buckets has no customer_id and no is_active column: a bucket's customer is its wallet's organisation.
    source = Path(module.__file__).read_text()  # type: ignore[attr-defined]
    assert "wb.customer_id" not in source
    assert "wb.is_active" not in source
    for match in re.finditer(r"(FROM|JOIN)\s+wallet_buckets", source):
        assert "customer_wallets" in source[match.start() : match.start() + 250]

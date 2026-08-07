# Implements: architecture/reference/billing/wbe-component-spec.md §4
# constitutional_basis: C-091 (Universal Prepaid Gate), C-004 (Billing Halt),
#                       C-059 (Implementation Traceability), C-023 (Evidence First)
"""CCT suite for WBE-S8 (WC-043): CCT-PREPAID-01 and CCT-SELFAUDIT-01 (full)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from main import app
from wallet.models import BucketNotFoundError, BucketReservation, InsufficientBalanceError
from wallet.router import _get_wallet_service, IReserveService
from reconciliation.service import (
    FounderActionGenerator,
    ReconciliationService,
    SelfAuditResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_reservation(
    customer_id: uuid.UUID,
    thread_type: str = "llm_mid",
    amount_paise: int = 1,
) -> BucketReservation:
    return BucketReservation(
        reservation_id=uuid.uuid4(),
        bucket_id=uuid.uuid4(),
        customer_id=customer_id,
        thread_type=thread_type,
        reserved_paise=amount_paise,
        idempotency_key=uuid.uuid4(),
        created_at=datetime.now(tz=timezone.utc),
    )


def _reserve_body(thread_type: str = "llm_mid", amount: int = 1) -> dict:
    return {
        "thread_type": thread_type,
        "amount": amount,
        "idempotency_key": str(uuid.uuid4()),
    }


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CCT-PREPAID-01 — Universal Prepaid Gate
# ---------------------------------------------------------------------------


class TestCCT_PREPAID_01:
    """CCT-PREPAID-01: AI Runtime cannot dispatch LLM call when bucket is empty."""

    @pytest.mark.asyncio
    async def test_empty_bucket_returns_402_bucket_empty(self) -> None:
        """POST /buckets/{id}/reserve → 402 BUCKET_EMPTY when balance = 0."""
        customer_id = uuid.uuid4()

        class _EmptySvc(IReserveService):
            async def reserve(self, customer_id, thread_type, amount_paise, idempotency_key):
                raise InsufficientBalanceError("Insufficient balance: available=0 requested=1")

        app.dependency_overrides[_get_wallet_service] = lambda: _EmptySvc()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await c.post(
                    f"/buckets/{customer_id}/reserve",
                    json=_reserve_body(),
                )
        finally:
            _clear_overrides()

        assert resp.status_code == 402
        assert resp.json()["detail"]["code"] == "BUCKET_EMPTY"

    @pytest.mark.asyncio
    async def test_billing_halted_returns_503(self) -> None:
        """POST /buckets/{id}/reserve → 503 BILLING_INTEGRITY_HALT when audit halted billing."""
        customer_id = uuid.uuid4()

        class _HaltedSvc(IReserveService):
            async def reserve(self, customer_id, thread_type, amount_paise, idempotency_key):
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "BILLING_INTEGRITY_HALT",
                        "message": "Billing suspended pending reconciliation audit",
                    },
                )

        app.dependency_overrides[_get_wallet_service] = lambda: _HaltedSvc()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await c.post(
                    f"/buckets/{customer_id}/reserve",
                    json=_reserve_body(),
                )
        finally:
            _clear_overrides()

        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "BILLING_INTEGRITY_HALT"

    @pytest.mark.asyncio
    async def test_bucket_not_found_returns_404(self) -> None:
        """POST /buckets/{id}/reserve → 404 BUCKET_NOT_FOUND when no bucket exists."""
        customer_id = uuid.uuid4()

        class _NoSvc(IReserveService):
            async def reserve(self, customer_id, thread_type, amount_paise, idempotency_key):
                raise BucketNotFoundError("Bucket not found")

        app.dependency_overrides[_get_wallet_service] = lambda: _NoSvc()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await c.post(
                    f"/buckets/{customer_id}/reserve",
                    json=_reserve_body(),
                )
        finally:
            _clear_overrides()

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "BUCKET_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_successful_reserve_returns_200_with_reservation(self) -> None:
        """POST /buckets/{id}/reserve → 200 with reservation when balance sufficient."""
        customer_id = uuid.uuid4()
        expected = _make_reservation(customer_id)

        class _OkSvc(IReserveService):
            async def reserve(self, customer_id, thread_type, amount_paise, idempotency_key):
                return expected

        app.dependency_overrides[_get_wallet_service] = lambda: _OkSvc()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await c.post(
                    f"/buckets/{customer_id}/reserve",
                    json=_reserve_body(),
                )
        finally:
            _clear_overrides()

        assert resp.status_code == 200
        body = resp.json()
        assert body["reservation_id"] == str(expected.reservation_id)
        assert body["reserved_paise"] == expected.reserved_paise


# ---------------------------------------------------------------------------
# CCT-SELFAUDIT-01 — Balance Reconciliation Integrity (service-level full test)
# ---------------------------------------------------------------------------


class TestCCT_SELFAUDIT_01:
    """CCT-SELFAUDIT-01: discrepancy > 1 paise halts billing + fires Founder Action."""

    @pytest.mark.asyncio
    async def test_self_audit_detects_discrepancy_halts_billing(self) -> None:
        """run_self_audit detects bucket balance ≠ ledger sum → billing halted + FA created."""
        # --- Setup: fake Redis ---
        fake_redis = fakeredis.FakeAsyncRedis(decode_responses=False)

        # --- Setup: session mock ---
        mock_session = AsyncMock()

        # Bucket row: balance_paise=1005, but computed = 1000 - 0 = 1000 → discrepancy=5
        bucket_row = MagicMock()
        bucket_row.__getitem__ = MagicMock(side_effect=lambda i: [
            "bucket-001", 1005, "ec-001", "llm_mid"
        ][i])
        # index access: [0]=bucket_id, [1]=balance_paise, [2]=ec_id, [3]=thread_type
        bucket_row.__iter__ = MagicMock(return_value=iter(["bucket-001", 1005, "ec-001", "llm_mid"]))

        # DB execute sequence:
        # 1st call → wallet_buckets SELECT (fetchall returns one row)
        # 2nd call → topup_orders SUM (scalar=1000)
        # 3rd call → bucket_reservations SUM (scalar=0)
        # 4th call → audit_evidence_log INSERT
        bucket_result = MagicMock()
        bucket_result.fetchall.return_value = [
            (str(uuid.uuid4()), 1005, str(uuid.uuid4()), "llm_mid")
        ]

        topup_result = MagicMock()
        topup_result.scalar.return_value = 1000

        consumed_result = MagicMock()
        consumed_result.scalar.return_value = 0

        mock_session.execute = AsyncMock(
            side_effect=[bucket_result, topup_result, consumed_result, AsyncMock()]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_session)

        # Founder action generator
        mock_fag = MagicMock(spec=FounderActionGenerator)
        mock_fag.maybe_create = AsyncMock(return_value=True)

        svc = ReconciliationService(
            session_factory=mock_session_factory,
            redis_client=fake_redis,
            founder_action_generator=mock_fag,
        )

        result: SelfAuditResult = await svc.run_self_audit()

        assert result.billing_halted is True, "Expected billing_halted=True on discrepancy"
        assert result.founder_action_created is True, "Expected founder_action_created=True"
        assert result.discrepancy_paise == 5, "Expected discrepancy_paise=5"

        # Redis halt flag must be set
        halted = await fake_redis.get("wbe:billing_halted")
        assert halted is not None, "wbe:billing_halted must be set in Redis"

        # Founder action must have been called with correct type
        mock_fag.maybe_create.assert_awaited_once()
        call_kwargs = mock_fag.maybe_create.call_args.kwargs
        assert call_kwargs["action_type"] == "BILLING_INTEGRITY_HALT"
        assert call_kwargs["payload"]["discrepancy_paise"] == 5

        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_self_audit_clean_state_does_not_halt(self) -> None:
        """run_self_audit with matching balances → no halt, no Founder Action."""
        fake_redis = fakeredis.FakeAsyncRedis(decode_responses=False)

        mock_session = AsyncMock()

        bucket_result = MagicMock()
        bucket_result.fetchall.return_value = [
            (str(uuid.uuid4()), 1000, str(uuid.uuid4()), "llm_mid")
        ]

        topup_result = MagicMock()
        topup_result.scalar.return_value = 1000

        consumed_result = MagicMock()
        consumed_result.scalar.return_value = 0

        mock_session.execute = AsyncMock(
            side_effect=[bucket_result, topup_result, consumed_result, AsyncMock()]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_factory = MagicMock(return_value=mock_session)

        mock_fag = MagicMock(spec=FounderActionGenerator)
        mock_fag.maybe_create = AsyncMock(return_value=False)

        svc = ReconciliationService(
            session_factory=mock_session_factory,
            redis_client=fake_redis,
            founder_action_generator=mock_fag,
        )

        result: SelfAuditResult = await svc.run_self_audit()

        assert result.billing_halted is False
        assert result.founder_action_created is False
        assert result.discrepancy_paise == 0

        halted = await fake_redis.get("wbe:billing_halted")
        assert halted is None

        mock_fag.maybe_create.assert_not_awaited()
        await fake_redis.aclose()

    @pytest.mark.asyncio
    async def test_self_audit_reserve_blocked_when_halted(self) -> None:
        """After billing halt, reserve endpoint returns 503 BILLING_INTEGRITY_HALT."""
        customer_id = uuid.uuid4()

        class _HaltedSvc(IReserveService):
            async def reserve(self, customer_id, thread_type, amount_paise, idempotency_key):
                raise HTTPException(
                    status_code=503,
                    detail={
                        "code": "BILLING_INTEGRITY_HALT",
                        "message": "Billing suspended pending reconciliation audit",
                    },
                )

        app.dependency_overrides[_get_wallet_service] = lambda: _HaltedSvc()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as c:
                resp = await c.post(
                    f"/buckets/{customer_id}/reserve",
                    json=_reserve_body(),
                )
        finally:
            _clear_overrides()

        assert resp.status_code == 503
        assert "BILLING_INTEGRITY_HALT" in resp.json()["detail"]["code"]

# Implements: work-contracts/WC-030-*.md §WC030-03:router-tests
# constitutional_basis: C-059 (Implementation Traceability), C-003 (Ops Auth),
#                       C-004 (Billing Halt Enforcement)
from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import AsyncIterator
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from reconciliation.router import _get_redis, _get_service, _require_ops_auth
from reconciliation.service import (
    CustomerMarginRow,
    DailyAuditResult,
    ReconciliationService,
    SelfAuditResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_self_audit_result(
    discrepancy_paise: int = 0,
    billing_halted: bool = False,
    founder_action_created: bool = False,
    buckets_audited: int = 3,
) -> SelfAuditResult:
    return SelfAuditResult(
        discrepancy_paise=discrepancy_paise,
        billing_halted=billing_halted,
        founder_action_created=founder_action_created,
        buckets_audited=buckets_audited,
        evidence_id=uuid.uuid4(),
        audited_at=datetime.now(tz=timezone.utc),
    )


def _make_daily_audit_result(
    unlinked: list[uuid.UUID] | None = None,
) -> DailyAuditResult:
    return DailyAuditResult(
        audit_date=datetime.now(tz=timezone.utc).date(),
        total_consumed_reservations=2,
        unlinked_reservations=unlinked or [],
        evidence_id=uuid.uuid4(),
        audited_at=datetime.now(tz=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[fakeredis.FakeAsyncRedis]:
    """Isolated async fake Redis instance with decode_responses for each test."""
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture()
def mock_service() -> MagicMock:
    """Mock ReconciliationService with sensible defaults."""
    svc = MagicMock(spec=ReconciliationService)
    svc.run_self_audit = AsyncMock(return_value=_make_self_audit_result())
    svc.run_daily_audit = AsyncMock(return_value=_make_daily_audit_result())
    svc.generate_margin_report = AsyncMock(return_value=[])
    svc.clear_halt = AsyncMock(return_value=None)
    return svc


@pytest.fixture()
def ops_token_override():
    """
    FastAPI dependency override that bypasses _require_ops_auth.
    Yields the override function so tests can apply it themselves.
    """
    async def _pass() -> None:
        return None
    return _pass


# ---------------------------------------------------------------------------
# Helper: build overridden AsyncClient
# ---------------------------------------------------------------------------

async def _client(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_svc: MagicMock,
    bypass_ops_auth: bool = False,
) -> AsyncClient:
    """Return an AsyncClient with dependency overrides applied."""
    app.dependency_overrides[_get_redis] = lambda: fake_redis
    app.dependency_overrides[_get_service] = lambda: mock_svc
    if bypass_ops_auth:
        async def _no_auth() -> None:
            return None
        app.dependency_overrides[_require_ops_auth] = _no_auth
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /reconciliation/status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_empty_state(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /reconciliation/status → 200 with all-null audit fields when cache empty."""
    client = await _client(fake_redis, mock_service)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/status")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["billing_halted"] is False
    assert body["last_self_audit"] is None
    assert body["last_daily_audit"] is None
    assert body["last_audit_date"] is None
    assert body["last_audit_run_at"] is None


@pytest.mark.asyncio
async def test_get_status_billing_halted(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /reconciliation/status → billing_halted=True when wbe:billing_halted set."""
    await fake_redis.set("wbe:billing_halted", "1")
    client = await _client(fake_redis, mock_service)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/status")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json()["billing_halted"] is True


@pytest.mark.asyncio
async def test_get_status_with_cached_self_audit(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /reconciliation/status → last_self_audit populated from Redis cache."""
    result = _make_self_audit_result(buckets_audited=7)
    payload = json.dumps(dataclasses.asdict(result), default=str)
    await fake_redis.set("wbe:last_self_audit_result", payload)

    client = await _client(fake_redis, mock_service)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/status")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["last_self_audit"] is not None
    assert body["last_self_audit"]["buckets_audited"] == 7


@pytest.mark.asyncio
async def test_get_status_with_cached_daily_audit(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /reconciliation/status → last_daily_audit populated from Redis cache."""
    audit_date = date(2025, 8, 5)
    result = _make_daily_audit_result()
    result = dataclasses.replace(result, audit_date=audit_date)
    payload = json.dumps(dataclasses.asdict(result), default=str)
    await fake_redis.set("wbe:last_daily_audit_result", payload)

    client = await _client(fake_redis, mock_service)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/status")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["last_daily_audit"] is not None
    assert body["last_audit_date"] == "2025-08-05"


@pytest.mark.asyncio
async def test_get_status_cached_run_at(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /reconciliation/status → last_audit_run_at populated from Redis cache."""
    ts = datetime(2025, 8, 5, 2, 0, 0, tzinfo=timezone.utc)
    await fake_redis.set("wbe:last_audit_run_at", ts.isoformat())

    client = await _client(fake_redis, mock_service)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/status")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["last_audit_run_at"] is not None


@pytest.mark.asyncio
async def test_get_status_malformed_cache_returns_500(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /reconciliation/status → 500 if cached audit JSON is malformed."""
    await fake_redis.set("wbe:last_self_audit_result", "{invalid-json}")

    client = await _client(fake_redis, mock_service)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/status")
    finally:
        _clear_overrides()

    assert resp.status_code == 500
    assert resp.json()["detail"]["code"] == "INTERNAL_ERROR"


# ---------------------------------------------------------------------------
# POST /reconciliation/run-now
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_now_returns_403_without_ops_token(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """POST /reconciliation/run-now → 403 when no X-Ops-Token header provided."""
    app.dependency_overrides[_get_redis] = lambda: fake_redis
    app.dependency_overrides[_get_service] = lambda: mock_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.post("/reconciliation/run-now")
    finally:
        _clear_overrides()

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_run_now_with_valid_ops_token_returns_200(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """POST /reconciliation/run-now → 200 with ops token and self-audit result."""
    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.post("/reconciliation/run-now")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert "triggered_at" in body
    assert "result" in body
    assert body["result"]["billing_halted"] is False
    assert body["result"]["discrepancy_paise"] == 0
    mock_service.run_self_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_now_caches_result_in_redis(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """POST /run-now caches self-audit result and run_at timestamp in Redis."""
    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            await c.post("/reconciliation/run-now")
    finally:
        _clear_overrides()

    # Check Redis has both keys populated
    run_at = await fake_redis.get("wbe:last_audit_run_at")
    cached_result = await fake_redis.get("wbe:last_self_audit_result")
    assert run_at is not None
    assert cached_result is not None
    parsed = json.loads(cached_result)
    assert "billing_halted" in parsed


@pytest.mark.asyncio
async def test_run_now_billing_halted_result_caches_correctly(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """POST /run-now with billing_halted=True caches halted state in Redis."""
    halted_result = _make_self_audit_result(
        discrepancy_paise=50000,
        billing_halted=True,
        founder_action_created=True,
    )
    mock_service.run_self_audit = AsyncMock(return_value=halted_result)

    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.post("/reconciliation/run-now")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["billing_halted"] is True
    assert body["result"]["discrepancy_paise"] == 50000


@pytest.mark.asyncio
async def test_run_now_service_error_returns_500(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """POST /reconciliation/run-now → 500 when service raises RuntimeError."""
    mock_service.run_self_audit = AsyncMock(
        side_effect=RuntimeError("DB connection lost")
    )
    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.post("/reconciliation/run-now")
    finally:
        _clear_overrides()

    assert resp.status_code == 500
    assert resp.json()["detail"]["code"] == "AUDIT_FAILED"


# ---------------------------------------------------------------------------
# GET /reconciliation/platform/margin/report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_margin_report_returns_403_without_ops_token(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /platform/margin/report → 403 without ops auth."""
    app.dependency_overrides[_get_redis] = lambda: fake_redis
    app.dependency_overrides[_get_service] = lambda: mock_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/reconciliation/platform/margin/report")
    finally:
        _clear_overrides()

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_margin_report_returns_empty_list(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /platform/margin/report → 200 with empty list when no data."""
    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/platform/margin/report")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json() == []
    mock_service.generate_margin_report.assert_awaited_once()


@pytest.mark.asyncio
async def test_margin_report_returns_customer_rows(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /platform/margin/report → 200 with customer margin rows."""
    customer_id = uuid.uuid4()
    rows = [
        CustomerMarginRow(
            customer_id=customer_id,
            thread_type="DMA",
            revenue_paise=10000,
            cost_paise=3000,
            margin_pct=Decimal("70.00"),
        )
    ]
    mock_service.generate_margin_report = AsyncMock(return_value=rows)

    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/platform/margin/report")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["thread_type"] == "DMA"
    assert body[0]["revenue_paise"] == 10000
    assert body[0]["cost_paise"] == 3000


@pytest.mark.asyncio
async def test_margin_report_accepts_date_query_param(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /platform/margin/report?report_date=2025-08-05 → passes date to service."""
    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.get(
                "/reconciliation/platform/margin/report",
                params={"report_date": "2025-08-05"},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    # Verify service was called with the specified date
    call_args = mock_service.generate_margin_report.call_args
    assert call_args[0][0] == date(2025, 8, 5)


@pytest.mark.asyncio
async def test_margin_report_service_error_returns_500(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """GET /platform/margin/report → 500 when service raises ValueError."""
    mock_service.generate_margin_report = AsyncMock(
        side_effect=ValueError("Bad query")
    )
    client = await _client(fake_redis, mock_service, bypass_ops_auth=True)
    try:
        async with client as c:
            resp = await c.get("/reconciliation/platform/margin/report")
    finally:
        _clear_overrides()

    assert resp.status_code == 500
    assert resp.json()["detail"]["code"] == "REPORT_FAILED"


# ---------------------------------------------------------------------------
# CCT-SELFAUDIT-01 — HTTP 503 BILLING_INTEGRITY_HALT enforcement
# constitutional_basis: C-004 (Billing Halt), C-091 (Financial Correctness)
# Spec reference: architecture/reference/billing/wbe-component-spec.md §4
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cct_selfaudit_01_wallet_reserve_returns_503_when_halted() -> None:
    """
    CCT-SELFAUDIT-01: When billing is halted (wbe:billing_halted set in Redis),
    WalletService.reserve() must raise HTTPException(503) with
    code=BILLING_INTEGRITY_HALT.

    Flow:
      1. Set wbe:billing_halted = "1" in Redis (simulating post-self-audit halt)
      2. Call WalletService.reserve() with a billing-halted Redis
      3. Assert HTTP 503 with BILLING_INTEGRITY_HALT detail code

    Constitutional basis: C-004 (Billing Halt Enforcement)
    """
    import pytest
    from fastapi import HTTPException

    from wallet.service import WalletService

    # 1. Redis with halt flag set (bytes mode as WalletService.reserve uses raw redis)
    halt_redis = fakeredis.FakeAsyncRedis(decode_responses=False)
    await halt_redis.set("wbe:billing_halted", b"1")

    # 2. Create WalletService with a mock DB session (no DB writes needed — halt check
    #    exits before any DB access)
    mock_db = MagicMock()
    svc = WalletService(db=mock_db, redis_client=halt_redis)

    # 3. Call reserve — must raise 503 immediately
    with pytest.raises(HTTPException) as exc_info:
        await svc.reserve(
            customer_id=uuid.uuid4(),
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.uuid4(),
            redis_client=halt_redis,
        )

    assert exc_info.value.status_code == 503
    detail = exc_info.value.detail
    assert detail["code"] == "BILLING_INTEGRITY_HALT"
    assert "Billing suspended" in detail["message"]
    await halt_redis.aclose()


@pytest.mark.asyncio
async def test_cct_selfaudit_01_wallet_reserve_proceeds_when_not_halted() -> None:
    """
    CCT-SELFAUDIT-01 (negative): WalletService.reserve() proceeds past the halt
    check when wbe:billing_halted is NOT set.

    The reserve will fail on DB access (mock DB has no rows) but must NOT fail
    at the 503 halt check — proving halt check passes when key is absent.
    """
    from wallet.service import WalletService

    # No halt flag set
    no_halt_redis = fakeredis.FakeAsyncRedis(decode_responses=False)

    # DB mock will raise when queried — that's fine, we only care the 503 is not raised
    mock_db = MagicMock()
    mock_db.execute = AsyncMock(side_effect=RuntimeError("no rows"))

    svc = WalletService(db=mock_db, redis_client=no_halt_redis)

    # Should NOT raise HTTPException(503) — should raise the RuntimeError from DB
    with pytest.raises(RuntimeError, match="no rows"):
        await svc.reserve(
            customer_id=uuid.uuid4(),
            thread_type="DMA",
            amount_paise=1000,
            idempotency_key=uuid.uuid4(),
            redis_client=no_halt_redis,
        )
    await no_halt_redis.aclose()


# ===========================================================================
# WC-030 audit additions — router dependency coverage (lines 40, 56->exit)
# ===========================================================================


def test_get_redis_dependency_returns_redis_client():
    """Cover router.py line 40: _get_redis returns a Redis client."""
    from reconciliation.router import _get_redis, _get_settings
    settings = _get_settings()
    redis_client = _get_redis(settings=settings)
    assert redis_client is not None


@pytest.mark.asyncio
async def test_require_ops_auth_passes_with_valid_token(
    fake_redis: fakeredis.FakeAsyncRedis,
    mock_service: MagicMock,
) -> None:
    """Cover router.py 56->exit: valid ops token bypasses the 403 raise."""
    # Do NOT use bypass_ops_auth — _require_ops_auth must run for real
    client = await _client(fake_redis, mock_service, bypass_ops_auth=False)
    try:
        async with client as c:
            resp = await c.post(
                "/reconciliation/run-now",
                headers={"X-Ops-Token": "test-ops-token"},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == 200

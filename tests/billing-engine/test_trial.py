# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-03
# constitutional_basis: C-088 (CCT-TRIAL-01), C-089 (CCT-TRIAL-02 billing layer),
#                       C-090 (grandfather), C-019 (phone verification), C-059 (Traceability)
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from trial.router import _get_trial_service
from trial.service import TrialService


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE IF NOT EXISTS trial_allocations (
        trial_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        started_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        converted_at TEXT,
        new_subscription_id TEXT,
        UNIQUE (customer_id, agent_type)
    )""",
    """CREATE TABLE IF NOT EXISTS trial_free_unit_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trial_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        units_granted INTEGER NOT NULL,
        units_consumed INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE (trial_id, thread_type)
    )""",
    """CREATE TABLE IF NOT EXISTS wallet_buckets (
        id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        employment_contract_id TEXT NOT NULL,
        thread_type TEXT NOT NULL,
        balance_paise INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    )""",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def in_memory_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        for stmt in _DDL:
            await conn.execute(text(stmt))
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(in_memory_engine):
    return async_sessionmaker(in_memory_engine, expire_on_commit=False)


@pytest.fixture
async def mock_redis():
    client = fakeredis.FakeAsyncRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.fixture
def mock_settings():
    return MagicMock(
        TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50, "llm_local": 200}},
        TRIAL_DURATION_DAYS=14,
    )


@pytest.fixture
def trial_service(session_factory, mock_redis, mock_settings):
    return TrialService(
        session_factory=session_factory,
        redis_client=mock_redis,
        settings=mock_settings,
    )


# ---------------------------------------------------------------------------
# CCT-TRIAL-01 — One Trial Per Agent Per Customer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cct_trial_01_second_trial_same_agent_returns_409(trial_service):
    """CCT-TRIAL-01: Second start_trial same customer+agent_type → 409 TRIAL_ALREADY_USED."""
    from fastapi import HTTPException

    cid = uuid.uuid4()
    await trial_service.start_trial(cid, "DMA", phone_verified=True)

    with pytest.raises(HTTPException) as exc_info:
        await trial_service.start_trial(cid, "DMA", phone_verified=True)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "TRIAL_ALREADY_USED"


@pytest.mark.asyncio
async def test_different_agent_type_allowed_for_same_customer(trial_service, session_factory):
    """A second trial with a DIFFERENT agent_type is allowed (unique per agent_type)."""
    cid = uuid.uuid4()
    svc = TrialService(
        session_factory=session_factory,
        redis_client=trial_service._redis,
        settings=MagicMock(
            TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50}, "DPA": {"llm_cloud": 30}},
            TRIAL_DURATION_DAYS=14,
        ),
    )
    await svc.start_trial(cid, "DMA", phone_verified=True)
    result = await svc.start_trial(cid, "DPA", phone_verified=True)
    assert result.trial_id is not None


# ---------------------------------------------------------------------------
# CCT-TRIAL-02 — Trial billing layer: Redis key + ledger rows created
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cct_trial_02_redis_key_set_to_trial(trial_service, mock_redis):
    """CCT-TRIAL-02 (billing layer): Redis wbe:customer:{id}:mode = b'TRIAL' after start_trial."""
    cid = uuid.uuid4()
    await trial_service.start_trial(cid, "DMA", phone_verified=True)

    mode = await mock_redis.get(f"wbe:customer:{cid}:mode")
    assert mode == b"TRIAL"


@pytest.mark.asyncio
async def test_trial_duration_is_exactly_fourteen_days(session_factory, mock_redis):
    service = TrialService(
        session_factory=session_factory,
        redis_client=mock_redis,
        settings=MagicMock(
            TRIAL_FREE_UNITS={"DMA": {"llm_local": 200}},
            TRIAL_DURATION_DAYS=3,
        ),
    )

    before = datetime.now(tz=timezone.utc)
    result = await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True)
    after = datetime.now(tz=timezone.utc)

    assert before + timedelta(days=14) <= result.expires_at <= after + timedelta(days=14)


@pytest.mark.asyncio
async def test_cct_trial_02_ledger_rows_created_with_correct_units(trial_service, session_factory):
    """CCT-TRIAL-02: trial_free_unit_ledger rows created with units_granted from TRIAL_FREE_UNITS."""
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    async with session_factory() as session:
        ledger = await session.execute(
            text("SELECT thread_type, units_granted FROM trial_free_unit_ledger WHERE trial_id = :id")
            .bindparams(id=str(result.trial_id))
        )
        rows = {r[0]: r[1] for r in ledger.fetchall()}

    assert rows["llm_cloud"] == 50
    assert rows["llm_local"] == 200


@pytest.mark.asyncio
async def test_start_trial_creates_wallet_buckets(trial_service, session_factory):
    """Wallet buckets are created for each thread_type in TRIAL_FREE_UNITS."""
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    assert len(result.wallet_bucket_ids) == 2

    async with session_factory() as session:
        buckets = await session.execute(
            text("SELECT id, thread_type, balance_paise FROM wallet_buckets WHERE customer_id = :cid")
            .bindparams(cid=str(cid))
        )
        rows = {r[1]: r[2] for r in buckets.fetchall()}

    assert "llm_cloud" in rows
    assert "llm_local" in rows
    assert rows["llm_cloud"] == 50 * 100
    assert rows["llm_local"] == 200 * 100


@pytest.mark.asyncio
async def test_start_trial_returns_correct_free_unit_caps(trial_service):
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    assert result.free_unit_caps == {"llm_cloud": 50, "llm_local": 200}
    assert result.expires_at > datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Phone verification guard (C-019)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_trial_phone_not_verified_raises_422(trial_service):
    """C-019: phone_verified=False → HTTP 422 PHONE_NOT_VERIFIED."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await trial_service.start_trial(uuid.uuid4(), "DMA", phone_verified=False)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "PHONE_NOT_VERIFIED"


# ---------------------------------------------------------------------------
# Missing trial config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_trial_missing_config_raises_422(session_factory, mock_redis):
    """TRIAL_FREE_UNITS missing for agent_type → 422 TRIAL_CONFIG_MISSING."""
    from fastapi import HTTPException

    svc = TrialService(
        session_factory=session_factory,
        redis_client=mock_redis,
        settings=MagicMock(TRIAL_FREE_UNITS={}, TRIAL_DURATION_DAYS=14),
    )
    with pytest.raises(HTTPException) as exc_info:
        await svc.start_trial(uuid.uuid4(), "DMA", phone_verified=True)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "TRIAL_CONFIG_MISSING"


# ---------------------------------------------------------------------------
# Redis failure is non-fatal
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_trial_redis_failure_does_not_rollback_db(session_factory, mock_settings):
    """Redis failure after DB commit is logged and NOT re-raised (DB not rolled back)."""
    failing_redis = AsyncMock()
    failing_redis.set = AsyncMock(side_effect=OSError("Redis unavailable"))

    svc = TrialService(session_factory=session_factory, redis_client=failing_redis, settings=mock_settings)
    cid = uuid.uuid4()
    result = await svc.start_trial(cid, "DMA", phone_verified=True)

    # DB transaction committed despite Redis failure
    async with session_factory() as session:
        row = await session.execute(
            text("SELECT status FROM trial_allocations WHERE trial_id = :id").bindparams(id=str(result.trial_id))
        )
        assert row.fetchone()[0] == "ACTIVE"


# ---------------------------------------------------------------------------
# check_expiry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_expiry_marks_status_expired(trial_service, session_factory, mock_redis):
    """check_expiry() sets status=EXPIRED and clears Redis key."""
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    await trial_service.check_expiry(result.trial_id)

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT status FROM trial_allocations WHERE trial_id = :id").bindparams(id=str(result.trial_id))
        )
        assert row.fetchone()[0] == "EXPIRED"

    mode = await mock_redis.get(f"wbe:customer:{cid}:mode")
    assert mode is None


@pytest.mark.asyncio
async def test_check_expiry_idempotent_for_already_expired(trial_service):
    """check_expiry() on an already-expired trial does not raise."""
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    await trial_service.check_expiry(result.trial_id)
    await trial_service.check_expiry(result.trial_id)  # must not raise


@pytest.mark.asyncio
async def test_check_expiry_not_found_raises_404(trial_service):
    """check_expiry() on unknown trial_id → 404."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await trial_service.check_expiry(uuid.uuid4())

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# convert_to_paid + C-090 grandfather
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_convert_to_paid_sets_status_converted(trial_service, session_factory):
    """convert_to_paid() sets trial status to CONVERTED."""
    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    convert_result = await trial_service.convert_to_paid(start_result.trial_id, "pay_ref_001")

    assert convert_result.new_subscription_id is not None

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT status, new_subscription_id FROM trial_allocations WHERE trial_id = :id")
            .bindparams(id=str(start_result.trial_id))
        )
        db_row = row.fetchone()
        assert db_row[0] == "CONVERTED"
        assert db_row[1] == str(convert_result.new_subscription_id)


@pytest.mark.asyncio
async def test_convert_to_paid_grandfather_applies_within_14_days(trial_service):
    """C-090: grandfather_applied=True when converted within 14 days of trial start."""
    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    convert_result = await trial_service.convert_to_paid(start_result.trial_id, "pay_ref_002")

    assert convert_result.grandfather_applied is True


@pytest.mark.asyncio
async def test_convert_to_paid_sets_redis_mode_to_active(trial_service, mock_redis):
    """After conversion, Redis wbe:customer:{id}:mode = b'ACTIVE'."""
    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    await trial_service.convert_to_paid(start_result.trial_id, "pay_ref_003")

    mode = await mock_redis.get(f"wbe:customer:{cid}:mode")
    assert mode == b"ACTIVE"


@pytest.mark.asyncio
async def test_convert_to_paid_calls_wallet_service(trial_service):
    """convert_to_paid() calls wallet_service.activate_subscription when injected."""
    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    mock_wallet = MagicMock()
    mock_wallet.activate_subscription = AsyncMock(return_value=MagicMock())

    await trial_service.convert_to_paid(
        start_result.trial_id, "pay_ref_004", wallet_service=mock_wallet
    )

    mock_wallet.activate_subscription.assert_awaited_once()


@pytest.mark.asyncio
async def test_convert_to_paid_not_active_raises_409(trial_service):
    """convert_to_paid() on expired trial → 409 TRIAL_NOT_ACTIVE."""
    from fastapi import HTTPException

    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)
    await trial_service.check_expiry(start_result.trial_id)

    with pytest.raises(HTTPException) as exc_info:
        await trial_service.convert_to_paid(start_result.trial_id, "pay_ref_005")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_convert_to_paid_not_found_raises_404(trial_service):
    """convert_to_paid() on unknown trial_id → 404."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await trial_service.convert_to_paid(uuid.uuid4(), "pay_ref_006")

    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_returns_active_trial(trial_service):
    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    status = await trial_service.get_status(cid)

    assert status is not None
    assert status.trial_id == start_result.trial_id
    assert status.status == "ACTIVE"
    assert status.units_remaining["llm_cloud"] == 50
    assert status.units_remaining["llm_local"] == 200


@pytest.mark.asyncio
async def test_get_status_returns_none_for_unknown_customer(trial_service):
    status = await trial_service.get_status(uuid.uuid4())
    assert status is None


# ---------------------------------------------------------------------------
# Router-level tests (FastAPI dependency overrides)
# ---------------------------------------------------------------------------


def _make_mock_trial_service(start_result=None, status_result=None, convert_result=None):
    svc = MagicMock()
    svc.start_trial = AsyncMock(return_value=start_result or MagicMock(
        trial_id=uuid.uuid4(),
        expires_at=datetime.now(tz=timezone.utc) + timedelta(days=14),
        free_unit_caps={"llm_cloud": 50},
        wallet_bucket_ids=[uuid.uuid4()],
    ))
    svc.get_status = AsyncMock(return_value=status_result)
    svc.convert_to_paid = AsyncMock(return_value=convert_result or MagicMock(
        new_subscription_id=uuid.uuid4(),
        grandfather_applied=True,
    ))
    return svc


def _clear_overrides():
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_router_post_start_returns_200():
    mock_svc = _make_mock_trial_service()
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/trial/start", json={
                "customer_id": str(uuid.uuid4()),
                "agent_type": "DMA",
                "phone_verified": True,
            })
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert "trial_id" in body
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_router_post_start_service_error_propagates():
    from fastapi import HTTPException
    mock_svc = MagicMock()
    mock_svc.start_trial = AsyncMock(side_effect=HTTPException(409, {"code": "TRIAL_ALREADY_USED"}))
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/trial/start", json={
                "customer_id": str(uuid.uuid4()),
                "agent_type": "DMA",
                "phone_verified": True,
            })
    finally:
        _clear_overrides()

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_router_get_status_returns_200():
    cid = uuid.uuid4()
    tid = uuid.uuid4()
    now = datetime.now(tz=timezone.utc)
    from trial.service import TrialStatus
    mock_status = TrialStatus(
        trial_id=tid,
        agent_type="DMA",
        started_at=now,
        expires_at=now + timedelta(days=14),
        status="ACTIVE",
        units_consumed={"llm_cloud": 5},
        units_remaining={"llm_cloud": 45},
    )
    mock_svc = _make_mock_trial_service(status_result=mock_status)
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/trial/status/{cid}")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_router_get_status_not_found_returns_404():
    mock_svc = _make_mock_trial_service(status_result=None)
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get(f"/trial/status/{uuid.uuid4()}")
    finally:
        _clear_overrides()

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_router_post_convert_with_ops_token_returns_200():
    mock_svc = _make_mock_trial_service()
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/trial/convert",
                json={"trial_id": str(uuid.uuid4()), "payment_reference": "pay_001"},
                headers={"X-Ops-Token": "test-ops-token"},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert "grandfather_applied" in resp.json()


@pytest.mark.asyncio
async def test_router_post_convert_without_ops_token_returns_403():
    mock_svc = _make_mock_trial_service()
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/trial/convert",
                json={"trial_id": str(uuid.uuid4()), "payment_reference": "pay_001"},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == 403

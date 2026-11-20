# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-02
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-03
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
# constitutional_basis: C-088 (CCT-TRIAL-01), C-089 (CCT-TRIAL-02 billing layer),
#                       C-090 (grandfather), C-019 (phone verification), C-059 (Traceability)
from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from main import app
from trial.router import _get_trial_service
from trial.service import TrialService
from wallet.ledger import WalletLedger
from wallet.platform_accounts import PlatformAccounts


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE IF NOT EXISTS agent_trial_policies (
        agent_type TEXT NOT NULL,
        agent_version TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        authorized_by TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (agent_type, agent_version)
    )""",
    """CREATE TABLE IF NOT EXISTS trial_allocations (
        trial_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        agent_version TEXT NOT NULL,
        started_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        converted_at TEXT,
        new_subscription_id TEXT,
        UNIQUE (customer_id, agent_type, agent_version)
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
    """CREATE TABLE IF NOT EXISTS trial_identity_claims (
        identity_subject_hash TEXT NOT NULL,
        agent_type TEXT NOT NULL,
        agent_version TEXT NOT NULL,
        trial_id TEXT NOT NULL,
        claimed_at TEXT NOT NULL,
        PRIMARY KEY (identity_subject_hash, agent_type, agent_version)
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
def mock_settings():
    return MagicMock(
        TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50, "llm_local": 200}},
        TRIAL_DURATION_DAYS=14,
    )


@pytest.fixture
def trial_service(session_factory, mock_settings):
    return TrialService(
        session_factory=session_factory,
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
        settings=MagicMock(
            TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50}, "DPA": {"llm_cloud": 30}},
            TRIAL_DURATION_DAYS=14,
        ),
    )
    await svc.start_trial(cid, "DMA", phone_verified=True)
    result = await svc.start_trial(cid, "DPA", phone_verified=True)
    assert result.trial_id is not None


@pytest.mark.asyncio
async def test_different_agent_version_allowed_for_same_customer(trial_service):
    """A customer may use one Trial for each exact agent version."""
    cid = uuid.uuid4()

    first = await trial_service.start_trial(cid, "DMA", phone_verified=True, agent_version="1.0.0")
    second = await trial_service.start_trial(cid, "DMA", phone_verified=True, agent_version="2.0.0")

    assert first.trial_id != second.trial_id


@pytest.mark.asyncio
async def test_founder_authorized_agent_version_duration_override(
    trial_service,
    session_factory,
):
    async with session_factory() as session:
        await session.execute(text(
            "INSERT INTO agent_trial_policies "
            "(agent_type, agent_version, duration_days, authorized_by) "
            "VALUES ('DMA', '2.0.0', 21, 'founder')"
        ))
        await session.commit()

    result = await trial_service.start_trial(
        uuid.uuid4(),
        "DMA",
        phone_verified=True,
        agent_version="2.0.0",
    )

    assert result.expires_at - result.started_at == timedelta(days=21)


# ---------------------------------------------------------------------------
# CCT-TRIAL-02 — Trial billing layer: ledger rows created; no customer-level Redis flag (C3-02)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cct_trial_02_status_lives_only_in_postgres(trial_service):
    """C3-02: TrialService takes no Redis client and a started trial is visible only through its rows."""
    assert "redis_client" not in inspect.signature(TrialService).parameters
    cid = uuid.uuid4()
    started = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    status = await trial_service.get_status(cid, started.trial_id)

    assert not hasattr(trial_service, "_redis")
    assert status is not None and status.status == "ACTIVE"


@pytest.mark.asyncio
async def test_trial_duration_is_exactly_fourteen_days(session_factory):
    service = TrialService(
        session_factory=session_factory,
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
async def test_start_trial_missing_config_raises_422(session_factory):
    """TRIAL_FREE_UNITS missing for agent_type → 422 TRIAL_CONFIG_MISSING."""
    from fastapi import HTTPException

    svc = TrialService(
        session_factory=session_factory,
        settings=MagicMock(TRIAL_FREE_UNITS={}, TRIAL_DURATION_DAYS=14),
    )
    with pytest.raises(HTTPException) as exc_info:
        await svc.start_trial(uuid.uuid4(), "DMA", phone_verified=True)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "TRIAL_CONFIG_MISSING"


# ---------------------------------------------------------------------------
# check_expiry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_expiry_marks_status_expired(trial_service, session_factory):
    """check_expiry() sets status=EXPIRED."""
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    await trial_service.check_expiry(result.trial_id)

    async with session_factory() as session:
        row = await session.execute(
            text("SELECT status FROM trial_allocations WHERE trial_id = :id").bindparams(id=str(result.trial_id))
        )
        assert row.fetchone()[0] == "EXPIRED"


@pytest.mark.asyncio
async def test_check_expiry_idempotent_for_already_expired(trial_service):
    """check_expiry() on an already-expired trial does not raise."""
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    await trial_service.check_expiry(result.trial_id)
    await trial_service.check_expiry(result.trial_id)  # must not raise


@pytest.mark.asyncio
async def test_check_expiry_does_not_rewrite_converted_trial(
    trial_service, session_factory
):
    cid = uuid.uuid4()
    result = await trial_service.start_trial(cid, "DMA", phone_verified=True)
    async with session_factory() as session:
        await session.execute(
            text("UPDATE trial_allocations SET status = 'CONVERTED' WHERE trial_id = :id")
            .bindparams(id=str(result.trial_id))
        )
        await session.commit()

    status = await trial_service.check_expiry(result.trial_id)

    assert status == "CONVERTED"
    async with session_factory() as session:
        row = await session.execute(
            text("SELECT status FROM trial_allocations WHERE trial_id = :id")
            .bindparams(id=str(result.trial_id))
        )
        assert row.fetchone()[0] == "CONVERTED"


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
async def test_get_status_targets_exact_trial(trial_service):
    cid = uuid.uuid4()
    start_result = await trial_service.start_trial(cid, "DMA", phone_verified=True)

    status = await trial_service.get_status(cid, start_result.trial_id)

    assert status is not None
    assert status.trial_id == start_result.trial_id
    assert await trial_service.get_status(cid, uuid.uuid4()) is None


@pytest.mark.asyncio
async def test_get_status_targets_exact_agent_version(trial_service):
    cid = uuid.uuid4()
    await trial_service.start_trial(cid, "DMA", phone_verified=True, agent_version="1.0.0")
    expected = await trial_service.start_trial(
        cid,
        "DMA",
        phone_verified=True,
        agent_version="2.0.0",
    )

    status = await trial_service.get_status(cid, None, "DMA", "1.0.0")

    assert status is not None
    assert status.agent_version == "1.0.0"
    assert status.trial_id != expected.trial_id


@pytest.mark.asyncio
async def test_get_status_returns_none_for_unknown_customer(trial_service):
    status = await trial_service.get_status(uuid.uuid4())
    assert status is None


@pytest.mark.asyncio
async def test_get_status_projects_elapsed_active_trial_as_expired(
    trial_service,
    session_factory,
):
    cid = uuid.uuid4()
    started = await trial_service.start_trial(cid, "DMA", phone_verified=True)
    async with session_factory() as session:
        await session.execute(text(
            "UPDATE trial_allocations SET expires_at = :expired WHERE trial_id = :trial_id"
        ), {
            "expired": (datetime.now(tz=timezone.utc) - timedelta(minutes=1)).isoformat(),
            "trial_id": str(started.trial_id),
        })
        await session.commit()

    status = await trial_service.get_status(cid, started.trial_id)

    assert status is not None
    assert status.status == "EXPIRED"


# ---------------------------------------------------------------------------
# C3-03 — per-version trial bound to the verified identity (hash only)
# ---------------------------------------------------------------------------

HASH_A = "a" * 64
HASH_B = "b" * 64


def _settings(**overrides):
    return MagicMock(
        TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50, "llm_local": 200}, "DPA": {"llm_cloud": 30}},
        TRIAL_DURATION_DAYS=14,
        **overrides,
    )


async def _scalar(session_factory, sql: str, **params):
    async with session_factory() as session:
        return (await session.execute(text(sql).bindparams(**params))).scalar_one()


@pytest.mark.asyncio
async def test_default_mode_records_the_identity_claim_with_agent_and_version(trial_service, session_factory):
    started = await trial_service.start_trial(
        uuid.uuid4(), "DMA", phone_verified=True, agent_version="2.0.0", identity_subject_hash=HASH_A
    )

    async with session_factory() as session:
        row = (
            await session.execute(
                text("SELECT agent_type, agent_version, trial_id FROM trial_identity_claims WHERE identity_subject_hash = :h")
                .bindparams(h=HASH_A)
            )
        ).fetchone()
    assert tuple(row) == ("DMA", "2.0.0", str(started.trial_id))


@pytest.mark.asyncio
async def test_record_mode_keeps_the_first_claim_and_does_not_block_a_second_customer(session_factory):
    service = TrialService(session_factory=session_factory, settings=_settings(TRIAL_IDENTITY_BINDING_MODE="RECORD"))
    first = await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)
    second = await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)

    assert first.trial_id != second.trial_id
    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_identity_claims") == 1
    assert await _scalar(session_factory, "SELECT trial_id FROM trial_identity_claims") == str(first.trial_id)


@pytest.mark.asyncio
async def test_enforce_mode_refuses_the_same_identity_for_the_same_agent_version(session_factory):
    from fastapi import HTTPException

    service = TrialService(session_factory=session_factory, settings=_settings(TRIAL_IDENTITY_BINDING_MODE="ENFORCE"))
    await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)
    second_customer = uuid.uuid4()

    with pytest.raises(HTTPException) as error:
        await service.start_trial(second_customer, "DMA", phone_verified=True, identity_subject_hash=HASH_A)

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "TRIAL_ALREADY_USED_BY_IDENTITY"
    cid = str(second_customer)
    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_allocations WHERE customer_id = :c", c=cid) == 0
    assert await _scalar(session_factory, "SELECT COUNT(*) FROM wallet_buckets WHERE customer_id = :c", c=cid) == 0
    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_identity_claims") == 1


@pytest.mark.asyncio
async def test_enforce_mode_allows_new_versions_other_agents_and_other_identities(session_factory):
    service = TrialService(session_factory=session_factory, settings=_settings(TRIAL_IDENTITY_BINDING_MODE="ENFORCE"))
    customer = uuid.uuid4()

    await service.start_trial(customer, "DMA", phone_verified=True, agent_version="1.0.0", identity_subject_hash=HASH_A)
    await service.start_trial(customer, "DMA", phone_verified=True, agent_version="2.0.0", identity_subject_hash=HASH_A)
    await service.start_trial(customer, "DPA", phone_verified=True, agent_version="1.0.0", identity_subject_hash=HASH_A)
    await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, agent_version="1.0.0", identity_subject_hash=HASH_B)

    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_identity_claims") == 4


@pytest.mark.asyncio
async def test_off_mode_records_no_claim_and_never_blocks(session_factory):
    service = TrialService(session_factory=session_factory, settings=_settings(TRIAL_IDENTITY_BINDING_MODE="OFF"))

    await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)
    await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)

    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_identity_claims") == 0


@pytest.mark.asyncio
async def test_start_without_a_verified_identity_makes_no_claim_even_when_enforced(session_factory):
    service = TrialService(session_factory=session_factory, settings=_settings(TRIAL_IDENTITY_BINDING_MODE="ENFORCE"))

    await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True)
    await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True)

    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_identity_claims") == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_hash", ["", "abc", "A" * 64, "g" * 64, "a" * 63, "a" * 65, "+919876543210"])
async def test_malformed_identity_hash_is_refused_before_any_write(trial_service, session_factory, bad_hash):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as error:
        await trial_service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=bad_hash)

    assert error.value.status_code == 422
    assert error.value.detail["code"] == "IDENTITY_HASH_INVALID"
    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_allocations") == 0


@pytest.mark.asyncio
async def test_claim_survives_expiry_and_conversion(session_factory):
    from fastapi import HTTPException

    service = TrialService(session_factory=session_factory, settings=_settings(TRIAL_IDENTITY_BINDING_MODE="ENFORCE"))
    started = await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)
    await service.convert_to_paid(started.trial_id, "pay_ref_claim")

    with pytest.raises(HTTPException) as error:
        await service.start_trial(uuid.uuid4(), "DMA", phone_verified=True, identity_subject_hash=HASH_A)

    assert error.value.detail["code"] == "TRIAL_ALREADY_USED_BY_IDENTITY"


# ---------------------------------------------------------------------------
# C4-04 — trial grant credited to the relationship's TRIAL wallet account
# ---------------------------------------------------------------------------


@pytest.fixture
async def wallet_trial_factory(wallet_db):
    async with wallet_db.kw["bind"].begin() as connection:
        for statement in _DDL:
            await connection.execute(text(statement))
    return wallet_db


async def _trial_balance(factory, tenant_id, relationship_id):
    async with factory() as session:
        ledger = WalletLedger(session)
        account = await ledger.find_account(tenant_id, "TRIAL", relationship_id=relationship_id)
        if account is None:
            return None
        return await ledger.balance(account, datetime.now(tz=timezone.utc) + timedelta(seconds=1))


@pytest.mark.asyncio
async def test_shadow_mode_credits_the_trial_account_from_the_settings_fallback(wallet_trial_factory):
    service = TrialService(session_factory=wallet_trial_factory, settings=_settings(WALLET_AUTHORITY="SHADOW"))
    tenant, relationship = uuid.uuid4(), uuid.uuid4()

    await service.start_trial(
        uuid.uuid4(), "DMA", phone_verified=True, tenant_id=tenant, relationship_id=relationship
    )

    balance = await _trial_balance(wallet_trial_factory, tenant, relationship)
    assert balance.credited_paise == (50 + 200) * 100
    assert balance.available_paise == (50 + 200) * 100


@pytest.mark.asyncio
async def test_legacy_mode_makes_no_wallet_writes(wallet_trial_factory):
    service = TrialService(session_factory=wallet_trial_factory, settings=_settings(WALLET_AUTHORITY="LEGACY"))
    tenant, relationship = uuid.uuid4(), uuid.uuid4()

    await service.start_trial(
        uuid.uuid4(), "DMA", phone_verified=True, tenant_id=tenant, relationship_id=relationship
    )

    assert await _trial_balance(wallet_trial_factory, tenant, relationship) is None


@pytest.mark.asyncio
async def test_shadow_credit_failure_never_fails_the_legacy_trial(session_factory, monkeypatch):
    monkeypatch.setattr(PlatformAccounts, "credit_trial_grant", AsyncMock(side_effect=RuntimeError("wallet down")))
    service = TrialService(session_factory=session_factory, settings=_settings(WALLET_AUTHORITY="SHADOW"))

    started = await service.start_trial(
        uuid.uuid4(), "DMA", phone_verified=True, tenant_id=uuid.uuid4(), relationship_id=uuid.uuid4()
    )

    assert await _scalar(
        session_factory, "SELECT status FROM trial_allocations WHERE trial_id = :t", t=str(started.trial_id)
    ) == "ACTIVE"


@pytest.mark.asyncio
async def test_wallet_mode_credit_failure_fails_the_start_and_commits_nothing(session_factory, monkeypatch):
    monkeypatch.setattr(PlatformAccounts, "credit_trial_grant", AsyncMock(side_effect=RuntimeError("wallet down")))
    service = TrialService(session_factory=session_factory, settings=_settings(WALLET_AUTHORITY="WALLET"))

    with pytest.raises(RuntimeError):
        await service.start_trial(
            uuid.uuid4(), "DMA", phone_verified=True, tenant_id=uuid.uuid4(), relationship_id=uuid.uuid4()
        )

    assert await _scalar(session_factory, "SELECT COUNT(*) FROM trial_allocations") == 0


@pytest.mark.asyncio
async def test_unavailable_pricing_falls_back_to_settings_in_wallet_mode(session_factory):
    """Without the pricing table the grant lookup fails soft; the credit then fails closed in WALLET mode."""
    service = TrialService(session_factory=session_factory, settings=_settings(WALLET_AUTHORITY="WALLET"))

    assert await service._lookup_trial_grant("DMA", "1.0.0") is None
    with pytest.raises(SQLAlchemyError):
        await service.start_trial(
            uuid.uuid4(), "DMA", phone_verified=True, tenant_id=uuid.uuid4(), relationship_id=uuid.uuid4()
        )


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
    svc.check_expiry = AsyncMock(return_value="EXPIRED")
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
                "agent_version": "1.0.0",
                "phone_verified": True,
            })
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert "trial_id" in body
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_router_forwards_identity_hash_and_refuses_a_malformed_one():
    now = datetime.now(tz=timezone.utc)
    mock_svc = _make_mock_trial_service(
        start_result=MagicMock(
            trial_id=uuid.uuid4(),
            started_at=now,
            expires_at=now + timedelta(days=14),
            free_unit_caps={"llm_cloud": 50},
            wallet_bucket_ids=[uuid.uuid4()],
        )
    )
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    base = {
        "customer_id": str(uuid.uuid4()),
        "agent_type": "DMA",
        "agent_version": "1.0.0",
        "phone_verified": True,
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            ok = await c.post("/trial/start", json={**base, "identity_subject_hash": "c" * 64})
            bad = await c.post("/trial/start", json={**base, "identity_subject_hash": "+919876543210"})
    finally:
        _clear_overrides()

    assert ok.status_code == 200
    assert mock_svc.start_trial.await_args.kwargs["identity_subject_hash"] == "c" * 64
    assert bad.status_code == 422
    mock_svc.start_trial.assert_awaited_once()


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
                "agent_version": "1.0.0",
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
        agent_version="1.0.0",
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
            resp = await c.get(f"/trial/status/{cid}?trial_id={tid}")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"
    mock_svc.get_status.assert_awaited_once_with(cid, tid, None, None)


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


@pytest.mark.asyncio
async def test_router_post_expire_with_ops_token_returns_expired():
    trial_id = uuid.uuid4()
    mock_svc = _make_mock_trial_service()
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post(
                "/trial/expire",
                json={"trial_id": str(trial_id)},
                headers={"X-Ops-Token": "test-ops-token"},
            )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json() == {"trial_id": str(trial_id), "status": "EXPIRED"}
    mock_svc.check_expiry.assert_awaited_once_with(trial_id)


@pytest.mark.asyncio
async def test_router_post_expire_without_ops_token_returns_403():
    mock_svc = _make_mock_trial_service()
    app.dependency_overrides[_get_trial_service] = lambda: mock_svc
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/trial/expire", json={"trial_id": str(uuid.uuid4())})
    finally:
        _clear_overrides()

    assert resp.status_code == 403
    mock_svc.check_expiry.assert_not_awaited()

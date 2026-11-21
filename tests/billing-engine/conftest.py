import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest_asyncio
from hypothesis import HealthCheck, settings

# billing-engine uses flat imports (WORKDIR=/app in Docker)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

# Stub runtime service modules absent from the source tree (available in Docker only)
_db_stub = MagicMock()
_db_stub.get_db = AsyncMock()
_db_stub.init_db = AsyncMock()
_db_stub.close_db = AsyncMock()
_db_stub.get_session_factory = MagicMock(return_value=MagicMock())
sys.modules.setdefault("database", _db_stub)

_db2_stub = MagicMock()
_db2_stub.get_session = AsyncMock()
sys.modules.setdefault("db", _db2_stub)

_ce_stub = MagicMock()
_ce_stub.CE = MagicMock()
_ce_stub.CE.ValidateAction = AsyncMock(return_value=None)
sys.modules.setdefault("ce_validator", _ce_stub)

# Single settings instance returned by both `from config import settings`
# and `Settings()` — ensures string URLs so aioredis.from_url() doesn't fail.
_settings_instance = MagicMock(
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    REDIS_URL="redis://localhost:6379/0",
    OPS_AUTH_TOKEN="test-ops-token",
    WBE_INTERNAL_BASE_URL="http://localhost:8140",
    thread_catalog_cache_ttl_seconds=30,
    redis_url="redis://localhost:6379/0",
    TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50, "llm_local": 200}},
    TRIAL_DURATION_DAYS=14,
    MAX_DISCOUNT_PCT=50,
    RAZORPAY_KEY_ID="rzp_test_key",
    RAZORPAY_KEY_SECRET="rzp_test_secret",
    RAZORPAY_WEBHOOK_SECRET="rzp_wh_secret",
)
_config_stub = MagicMock()
_config_stub.settings = _settings_instance
_config_stub.Settings = MagicMock(return_value=_settings_instance)
sys.modules.setdefault("config", _config_stub)

# Suppress function_scoped_fixture health check globally for this service's tests.
# Our fixtures are stateless mocks — safe to share across hypothesis-generated inputs.
settings.register_profile("ci", suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
settings.load_profile("ci")

# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-02
# SQLite twin of the wallet entity (99zzzzzzzz-wc136-05-wallet-entity.sql) for service-level tests.
WALLET_SQLITE_DDL = (
    """CREATE TABLE business.wallet_accounts (
        account_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, owner_kind TEXT NOT NULL,
        owner_ref TEXT, account_class TEXT NOT NULL, scope_kind TEXT NOT NULL,
        relationship_id TEXT, skill_id TEXT, campaign_ref TEXT, lead_ref TEXT, environment TEXT,
        agent_type TEXT, agent_version TEXT, status TEXT NOT NULL, created_at TIMESTAMP NOT NULL
    )""",
    """CREATE UNIQUE INDEX business.wallet_accounts_key ON wallet_accounts (
        tenant_id, account_class,
        COALESCE(relationship_id, '00000000-0000-0000-0000-000000000000'),
        COALESCE(skill_id, ''), COALESCE(campaign_ref, ''), COALESCE(lead_ref, ''),
        COALESCE(environment, ''))""",
    """CREATE TABLE business.wallet_lots (
        lot_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, account_id TEXT NOT NULL,
        lot_kind TEXT NOT NULL, credited_paise INTEGER NOT NULL CHECK (credited_paise > 0),
        valid_from TIMESTAMP NOT NULL, valid_until TIMESTAMP NOT NULL, source_kind TEXT NOT NULL,
        source_ref TEXT NOT NULL, pinned_versions TEXT NOT NULL, evidence_id TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL
    )""",
    """CREATE TABLE business.wallet_reservations (
        reservation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, account_id TEXT NOT NULL,
        lot_id TEXT NOT NULL, component_id TEXT NOT NULL,
        reserved_paise INTEGER NOT NULL CHECK (reserved_paise > 0), actual_paise INTEGER,
        state TEXT NOT NULL, pinned_account_class TEXT NOT NULL, pinned_versions TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL, created_at TIMESTAMP NOT NULL, resolved_at TIMESTAMP
    )""",
    """CREATE TABLE business.wallet_entries (
        entry_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, account_id TEXT NOT NULL,
        lot_id TEXT, entry_kind TEXT NOT NULL, amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
        reservation_id TEXT, idempotency_key TEXT NOT NULL, request_digest TEXT NOT NULL,
        component_id TEXT, invocation_id TEXT, evidence_id TEXT, occurred_at TIMESTAMP NOT NULL,
        UNIQUE (tenant_id, idempotency_key, entry_kind)
    )""",
    """CREATE TABLE business.wallet_floor_uses (
        tenant_id TEXT NOT NULL, environment TEXT NOT NULL, use_id TEXT NOT NULL,
        purpose TEXT NOT NULL, component_id TEXT NOT NULL, amount_paise INTEGER NOT NULL,
        invocation_id TEXT, evidence_id TEXT NOT NULL, occurred_at TIMESTAMP NOT NULL,
        PRIMARY KEY (tenant_id, environment, use_id)
    )""",
    """CREATE TABLE institutional.pricing_versions (
        version_id TEXT PRIMARY KEY, kind TEXT NOT NULL, subject_key TEXT NOT NULL,
        version_no INTEGER NOT NULL, state TEXT NOT NULL, body TEXT NOT NULL,
        effective_from TIMESTAMP
    )""",
)


@pytest_asyncio.fixture
async def wallet_db():
    """Yield an async session factory over an in-memory database with the wallet schema attached."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.execute(text("ATTACH DATABASE ':memory:' AS business"))
        await connection.execute(text("ATTACH DATABASE ':memory:' AS institutional"))
        for statement in WALLET_SQLITE_DDL:
            await connection.execute(text(statement))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()

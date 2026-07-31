# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md §2.0, §3.1, §3.2, §3.3, §4.0
# constitutional_basis: C-023, C-059, C-063, C-089, C-091
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, MagicMock

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """Create an in-memory SQLite async engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(_create_tables)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session_factory(async_engine):
    """Create an async session factory."""
    async_session = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )
    return async_session


@pytest_asyncio.fixture
async def db_session(async_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for a single test."""
    async with async_session_factory() as session:
        yield session


def _create_tables(conn):
    """Create all required tables for testing (synchronous, called within async context)."""
    from sqlalchemy import (
        Column,
        Integer,
        String,
        Numeric,
        DateTime,
        MetaData,
        Table,
    )

    metadata = MetaData()

    # institutional.bundle_profiles
    Table(
        "bundle_profiles",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("agent_type", String(64), nullable=False, unique=False),
        Column("bundle_tier", String(64), nullable=False, unique=False),
        Column("cost_floor_paise", Integer, nullable=False),
        Column("minimum_margin_pct", Numeric(5, 2), nullable=False),
        Column("created_at", DateTime, nullable=False),
        Column("updated_at", DateTime, nullable=False),
    )

    # institutional.pricing_floor_log
    Table(
        "pricing_floor_log",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("agent_type", String(64), nullable=False),
        Column("bundle_tier", String(64), nullable=False),
        Column("proposed_price_paise", Integer, nullable=False),
        Column("cost_floor_paise", Integer, nullable=False),
        Column("constitutional_minimum_margin_pct", Numeric(5, 2), nullable=False),
        Column("minimum_compliant_price_paise", Integer, nullable=False),
        Column("outcome", String(16), nullable=False),  # 'APPROVED' or 'REJECTED'
        Column("idempotency_key", String(256), nullable=True, unique=True),
        Column("created_at", DateTime, nullable=False),
        Column("tenant_id", String(128), nullable=True),
    )

    # thread_catalog (if needed for direct queries in tests)
    Table(
        "thread_catalog",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("thread_type", String(64), nullable=False, unique=True),
        Column("cost_floor_paise", Integer, nullable=False),
        Column("margin_pct_min", Numeric(5, 2), nullable=False),
        Column("description", String(512), nullable=True),
    )

    metadata.create_all(conn)


# ============================================================================
# MOCK SERVICE FIXTURES
# ============================================================================


@pytest.fixture
def mock_wallet_service():
    """Mock IWalletService for pricing calculations."""
    service = AsyncMock()
    service.get_wallet_balance = AsyncMock(return_value=10000000)  # 100 INR in paise
    service.deduct_from_wallet = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_thread_catalog_service(db_session):
    """Mock ThreadCatalogService."""
    service = MagicMock()

    # Mock get_all_threads to return test thread catalog entries
    async def mock_get_all_threads():
        return [
            {
                "thread_type": "STANDARD",
                "cost_floor_paise": 500,
                "margin_pct_min": 15.0,
            },
            {
                "thread_type": "PREMIUM",
                "cost_floor_paise": 1500,
                "margin_pct_min": 20.0,
            },
            {
                "thread_type": "ENTERPRISE",
                "cost_floor_paise": 5000,
                "margin_pct_min": 25.0,
            },
        ]

    service.get_all_threads = AsyncMock(side_effect=mock_get_all_threads)
    return service


@pytest.fixture
def mock_logger():
    """Mock logger for testing without actual log output."""
    logger_mock = MagicMock(spec=logging.Logger)
    logger_mock.info = MagicMock()
    logger_mock.error = MagicMock()
    logger_mock.warning = MagicMock()
    logger_mock.debug = MagicMock()
    return logger_mock


# ============================================================================
# BUNDLE ENGINE FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def bundle_engine(db_session, mock_logger):
    """Provide a BundleEngine instance for tests."""
    from src.billing_engine.markup.bundle_engine import BundleEngine

    engine = BundleEngine(db_session=db_session, logger=mock_logger)
    return engine


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def sample_bundle_profiles(db_session):
    """Insert sample bundle profiles into the test database."""
    from sqlalchemy import insert

    # Define the bundle_profiles table metadata
    from sqlalchemy import MetaData, Table

    metadata = MetaData()
    Table(
        "bundle_profiles",
        metadata,
        autoload_with=db_session.sync_session_maker.kw["bind"],
    ) if hasattr(db_session, "sync_session_maker") else None

    # For in-memory SQLite, we use raw insert
    stmt_data = [
        {
            "agent_type": "AGENT_TYPE_STANDARD",
            "bundle_tier": "TIER_STARTER",
            "cost_floor_paise": 5000,
            "minimum_margin_pct": Decimal("15.00"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "agent_type": "AGENT_TYPE_STANDARD",
            "bundle_tier": "TIER_PROFESSIONAL",
            "cost_floor_paise": 15000,
            "minimum_margin_pct": Decimal("20.00"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "agent_type": "AGENT_TYPE_ENTERPRISE",
            "bundle_tier": "TIER_ENTERPRISE",
            "cost_floor_paise": 50000,
            "minimum_margin_pct": Decimal("25.00"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
    ]

    for data in stmt_data:
        await db_session.execute(
            insert(Table("bundle_profiles", MetaData(), autoload_with=None)).values(
                **data
            ),
        ) if False else None

    # Fallback: use raw SQL for SQLite
    for data in stmt_data:
        await db_session.execute(
            """
            INSERT INTO bundle_profiles
            (agent_type, bundle_tier, cost_floor_paise, minimum_margin_pct, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data["agent_type"],
                data["bundle_tier"],
                data["cost_floor_paise"],
                float(data["minimum_margin_pct"]),
                data["created_at"],
                data["updated_at"],
            ),
        )

    await db_session.commit()
    return stmt_data


@pytest.fixture
def price_validation_request_dict():
    """Provide a sample PriceValidationRequest payload."""
    return {
        "agent_type": "AGENT_TYPE_STANDARD",
        "bundle_tier": "TIER_STARTER",
        "proposed_price_paise": 6500,
        "idempotency_key": "test-validate-001",
    }


@pytest.fixture
def price_derive_request_dict():
    """Provide a sample PriceDeriveRequest payload."""
    return {
        "agent_type": "AGENT_TYPE_STANDARD",
        "bundle_tier": "TIER_PROFESSIONAL",
        "target_margin_pct": None,  # Use default from bundle_profiles
    }


# ============================================================================
# FASTAPI CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def client():
    """Provide a TestClient for FastAPI endpoint testing."""
    from fastapi.testclient import TestClient
    from src.billing_engine.main import app

    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Provide an async test client using httpx."""
    import httpx
    from src.billing_engine.main import app

    async with httpx.AsyncClient(app=app, base_url="http://test") as client_instance:
        yield client_instance


# ============================================================================
# CONTEXT & REQUEST FIXTURES
# ============================================================================


@pytest.fixture
def mock_grpc_metadata():
    """Mock gRPC metadata context (tenant_id, user_id)."""
    return {
        "tenant_id": "tenant-test-001",
        "user_id": "user-test-001",
        "authorization": "Bearer token-test",
    }


@pytest.fixture
def mock_request_context(mock_grpc_metadata):
    """Mock request context with tenant isolation."""
    return MagicMock(
        headers=mock_grpc_metadata,
        scope={
            "type": "http",
            "method": "POST",
            "path": "/pricing/validate",
            "headers": [(k.encode(), v.encode()) for k, v in mock_grpc_metadata.items()],
        },
    )


# ============================================================================
# CONSTITUTIONAL ENGINE MOCKS (C-023 validation)
# ============================================================================


@pytest.fixture
def mock_ce_validation_response():
    """Mock successful CE validation response."""
    return MagicMock(
        decision="Allow",
        audit_trail_id="audit-001",
        evidence_recorded=True,
    )


@pytest.fixture
def mock_ce_service(mock_ce_validation_response):
    """Mock ConstitutionalEngineService for C-023 compliance."""
    service = AsyncMock()
    service.validate_action = AsyncMock(return_value=mock_ce_validation_response)
    service.record_evidence = AsyncMock(return_value={"evidence_id": "ev-001"})
    return service


# ============================================================================
# ERROR SCENARIO FIXTURES
# ============================================================================


@pytest.fixture
def invalid_bundle_tier_dict():
    """Provide an invalid bundle tier for error testing."""
    return {
        "agent_type": "AGENT_TYPE_STANDARD",
        "bundle_tier": "TIER_NONEXISTENT",
        "proposed_price_paise": 6500,
    }


@pytest.fixture
def below_floor_price_dict():
    """Provide a price below cost floor for validation rejection testing."""
    return {
        "agent_type": "AGENT_TYPE_STANDARD",
        "bundle_tier": "TIER_STARTER",
        "proposed_price_paise": 2000,  # Below 5000 cost floor
        "idempotency_key": "test-below-floor-001",
    }


@pytest.fixture
def negative_price_dict():
    """Provide a negative proposed price for validation testing."""
    return {
        "agent_type": "AGENT_TYPE_STANDARD",
        "bundle_tier": "TIER_STARTER",
        "proposed_price_paise": -500,
        "idempotency_key": "test-negative-001",
    }


# ============================================================================
# UTILITY FIXTURES
# ============================================================================


@pytest.fixture
def utc_now():
    """Provide current UTC timestamp."""
    return datetime.utcnow()


@pytest.fixture
def create_pricing_log_entry(db_session):
    """Factory fixture to create pricing_floor_log entries for testing."""

    async def _create_entry(
        agent_type: str,
        bundle_tier: str,
        proposed_price_paise: int,
        cost_floor_paise: int,
        constitutional_minimum_margin_pct: float,
        minimum_compliant_price_paise: int,
        outcome: str,
        idempotency_key: str | None = None,
        tenant_id: str | None = None,
    ) -> dict:

        stmt_values = {
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "proposed_price_paise": proposed_price_paise,
            "cost_floor_paise": cost_floor_paise,
            "constitutional_minimum_margin_pct": constitutional_minimum_margin_pct,
            "minimum_compliant_price_paise": minimum_compliant_price_paise,
            "outcome": outcome,
            "created_at": datetime.utcnow(),
            "tenant_id": tenant_id,
        }
        if idempotency_key:
            stmt_values["idempotency_key"] = idempotency_key

        await db_session.execute(
            """
            INSERT INTO pricing_floor_log
            (agent_type, bundle_tier, proposed_price_paise, cost_floor_paise,
             constitutional_minimum_margin_pct, minimum_compliant_price_paise,
             outcome, created_at, tenant_id, idempotency_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stmt_values["agent_type"],
                stmt_values["bundle_tier"],
                stmt_values["proposed_price_paise"],
                stmt_values["cost_floor_paise"],
                stmt_values["constitutional_minimum_margin_pct"],
                stmt_values["minimum_compliant_price_paise"],
                stmt_values["outcome"],
                stmt_values["created_at"],
                stmt_values["tenant_id"],
                idempotency_key,
            ),
        )
        await db_session.commit()
        return stmt_values

    return _create_entry


@pytest.fixture
def cleanup_pricing_logs(db_session):
    """Fixture to clean up pricing_floor_log after tests."""

    async def _cleanup():
        await db_session.execute("DELETE FROM pricing_floor_log")
        await db_session.commit()

    return _cleanup


# ============================================================================
# PYTEST CONFIGURATION HELPERS
# ============================================================================


@pytest.fixture(scope="session")
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (requires pytest-asyncio)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test",
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test",
    )
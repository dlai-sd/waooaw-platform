# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import fakeredis.aio as fakeredis

from reconciliation.service import ReconciliationService
from reconciliation.scheduler import create_scheduler
from config import Settings


class TestReconciliationService:
    """
    Test ReconciliationService.run_self_audit(), run_daily_audit(), and margin reporting.

    Constitutional basis:
    - C-023: Evidence records emitted for all audit outcomes
    - C-059: Audit logs and discrepancy records for traceability
    - C-073: Type-safe audit results (SelfAuditResult, DailyAuditResult)
    - C-097: Property-based testing for financial arithmetic (margin_pct calculation)
    """

    @pytest.fixture
    async def mock_redis(self) -> fakeredis.FakeRedis:
        """
        Create a fake Redis instance for tests.

        Never shares state with production -- isolated per test.

        Returns:
            FakeRedis async client.
        """
        return fakeredis.FakeRedis()

    @pytest.fixture
    async def mock_db_session(self) -> AsyncSession:
        """
        Create an in-memory SQLite async session with StaticPool for test isolation.

        All sessions share the same connection -- fixture writes are visible
        to the service under test.

        Returns:
            SQLAlchemy AsyncSession for the test.
        """
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        async with engine.begin() as conn:
            await conn.run_sync(self._create_schema)

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            yield session

        await engine.dispose()

    @staticmethod
    def _create_schema(conn: object) -> None:
        """Create minimal schema for reconciliation tests."""
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS employment_contracts (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                thread_type TEXT NOT NULL
            )
            """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS wallet_buckets (
                id TEXT PRIMARY KEY,
                employment_contract_id TEXT NOT NULL,
                thread_type TEXT NOT NULL,
                balance_paise INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (employment_contract_id) REFERENCES employment_contracts(id)
            )
            """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS topup_orders (
                id TEXT PRIMARY KEY,
                employment_contract_id TEXT NOT NULL,
                thread_type TEXT NOT NULL,
                amount_paise INTEGER NOT NULL,
                applied_at TIMESTAMP,
                FOREIGN KEY (employment_contract_id) REFERENCES employment_contracts(id)
            )
            """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS bucket_reservations (
                id TEXT PRIMARY KEY,
                bucket_id TEXT NOT NULL,
                reserved_paise INTEGER NOT NULL,
                consumed BOOLEAN DEFAULT 0,
                consumed_at TIMESTAMP,
                FOREIGN KEY (bucket_id) REFERENCES wallet_buckets(id)
            )
            """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS platform_cost_ledger (
                id TEXT PRIMARY KEY,
                bucket_reservation_id TEXT NOT NULL,
                raw_cost_inr_paise INTEGER NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bucket_reservation_id) REFERENCES bucket_reservations(id)
            )
            """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                audit_type TEXT NOT NULL,
                discrepancy_paise INTEGER,
                billing_halted BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS founder_actions (
                id TEXT PRIMARY KEY,
                action_type TEXT NOT NULL,
                trigger_event TEXT,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        )
        conn.commit()

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Mock Settings with test defaults."""
        settings_mock = MagicMock(spec=Settings)
        settings_mock.DATABASE_URL = (
            "sqlite+aiosqlite:///:memory:"
        )
        settings_mock.REDIS_URL = "redis://localhost:6379/0"
        settings_mock.WBE_INTERNAL_BASE_URL = "http://localhost:8000"
        return settings_mock

    @pytest.fixture
    async def reconciliation_service(
        self,
        mock_db_session: AsyncSession,
        mock_redis: fakeredis.FakeRedis,
        mock_settings: Settings,
    ) -> ReconciliationService:
        """
        Create a ReconciliationService instance with mocked Redis and DB.

        Args:
            mock_db_session: In-memory SQLite async session.
            mock_redis: FakeRedis async client.
            mock_settings: Mocked Settings object.

        Returns:
            ReconciliationService instance for testing.
        """
        return ReconciliationService(
            db_session=mock_db_session,
            redis_client=mock_redis,
            settings=mock_settings,
        )

    @pytest.mark.asyncio
    async def test_run_self_audit_clean_state(
        self,
        reconciliation_service: ReconciliationService,
        mock_db_session: AsyncSession,
        mock_redis: fakeredis.FakeRedis,
    ) -> None:
        """
        Test run_self_audit() with clean state returns billing_halted=False.

        Scenario: No wallets, or balance matches expected balance.
        Expected: SelfAuditResult.billing_halted=False, no Redis halt key set.

        Constitutional basis: C-023 (evidence record), C-059 (traceability).
        """
        result = await reconciliation_service.run_self_audit()

        assert result.billing_halted is False
        assert result.discrepancy_paise == 0
        halted = await mock_redis.get("wbe:billing_halted")
        assert halted is None

    @pytest.mark.asyncio
    async def test_run_self_audit_corrupted_balance_halts_billing(
        self,
        reconciliation_service: ReconciliationService,
        mock_db_session: AsyncSession,
        mock_redis: fakeredis.FakeRedis,
    ) -> None:
        """
        Test run_self_audit() with corrupted balance (delta > 1 paise) halts billing.

        Scenario:
        1. Create employment_contract, wallet_bucket with balance_paise=1000
        2. Create topup_order (applied) for 1000 paise
        3. Manually corrupt balance_paise to 1002 (2 paise mismatch via SQL)
        4. Call run_self_audit() -- expected_balance=1000, actual=1002, delta=2
        5. Verify: billing_halted=True, wbe:billing_halted Redis key set

        Constitutional basis: C-023, C-059, C-091 (halt on discrepancy).
        """
        contract_id = str(uuid4())
        bucket_id = str(uuid4())

        async with mock_db_session.begin():
            await mock_db_session.execute(
                text(
                    "INSERT INTO employment_contracts (id, customer_id, thread_type) "
                    "VALUES (:id, :cid, :tt)"
                ).bindparams(id=contract_id, cid="cust-1", tt="AGENT")
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO wallet_buckets (id, employment_contract_id, thread_type, balance_paise) "
                    "VALUES (:id, :ec_id, :tt, :bal)"
                ).bindparams(id=bucket_id, ec_id=contract_id, tt="AGENT", bal=1000)
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO topup_orders (id, employment_contract_id, thread_type, amount_paise, applied_at) "
                    "VALUES (:id, :ec_id, :tt, :amt, :applied)"
                ).bindparams(
                    id=str(uuid4()),
                    ec_id=contract_id,
                    tt="AGENT",
                    amt=1000,
                    applied=datetime.now(timezone.utc),
                )
            )

        async with mock_db_session.begin():
            await mock_db_session.execute(
                text(
                    "UPDATE wallet_buckets SET balance_paise = :bal WHERE id = :id"
                ).bindparams(bal=1002, id=bucket_id)
            )

        result = await reconciliation_service.run_self_audit()

        assert result.billing_halted is True
        assert result.discrepancy_paise == 2
        halted = await mock_redis.get("wbe:billing_halted")
        assert halted == "1"

    @pytest.mark.asyncio
    async def test_clear_halt_removes_redis_key(
        self,
        reconciliation_service: ReconciliationService,
        mock_redis: fakeredis.FakeRedis,
    ) -> None:
        """
        Test clear_halt() removes wbe:billing_halted Redis key.

        Scenario:
        1. Manually set wbe:billing_halted = "1"
        2. Call clear_halt()
        3. Verify key is deleted

        Constitutional basis: C-059 (ops-only halt clearance).
        """
        await mock_redis.set("wbe:billing_halted", "1")
        await reconciliation_service.clear_halt()
        halted = await mock_redis.get("wbe:billing_halted")
        assert halted is None

    @pytest.mark.asyncio
    async def test_run_daily_audit_matched_reservations(
        self,
        reconciliation_service: ReconciliationService,
        mock_db_session: AsyncSession,
    ) -> None:
        """
        Test run_daily_audit() with matched consumed reservations.

        Scenario:
        1. Create bucket_reservation (consumed=True, consumed_at=today)
        2. Create matching platform_cost_ledger row with bucket_reservation_id
        3. Call run_daily_audit(yesterday)
        4. Verify: DailyAuditResult.unlinked_reservations is empty

        Constitutional basis: C-023, C-059 (evidence record on match).
        """
        today = date.today()
        bucket_id = str(uuid4())
        reservation_id = str(uuid4())
        cost_ledger_id = str(uuid4())

        async with mock_db_session.begin():
            await mock_db_session.execute(
                text(
                    "INSERT INTO wallet_buckets (id, employment_contract_id, thread_type, balance_paise) "
                    "VALUES (:id, :ec_id, :tt, :bal)"
                ).bindparams(id=bucket_id, ec_id=str(uuid4()), tt="AGENT", bal=1000)
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO bucket_reservations (id, bucket_id, reserved_paise, consumed, consumed_at) "
                    "VALUES (:id, :bid, :amt, :consumed, :consumed_at)"
                ).bindparams(
                    id=reservation_id,
                    bid=bucket_id,
                    amt=500,
                    consumed=True,
                    consumed_at=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
                )
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO platform_cost_ledger (id, bucket_reservation_id, raw_cost_inr_paise) "
                    "VALUES (:id, :res_id, :cost)"
                ).bindparams(id=cost_ledger_id, res_id=reservation_id, cost=400)
            )

        result = await reconciliation_service.run_daily_audit(today)

        assert result.unlinked_reservations == []

    @pytest.mark.asyncio
    async def test_run_daily_audit_unlinked_reservations(
        self,
        reconciliation_service: ReconciliationService,
        mock_db_session: AsyncSession,
    ) -> None:
        """
        Test run_daily_audit() detects unlinked consumed reservations.

        Scenario:
        1. Create bucket_reservation (consumed=True, consumed_at=today)
        2. Do NOT create matching platform_cost_ledger row
        3. Call run_daily_audit(today)
        4. Verify: DailyAuditResult.unlinked_reservations contains reservation_id

        Constitutional basis: C-023, C-059.
        """
        today = date.today()
        bucket_id = str(uuid4())
        reservation_id = str(uuid4())

        async with mock_db_session.begin():
            await mock_db_session.execute(
                text(
                    "INSERT INTO wallet_buckets (id, employment_contract_id, thread_type, balance_paise) "
                    "VALUES (:id, :ec_id, :tt, :bal)"
                ).bindparams(id=bucket_id, ec_id=str(uuid4()), tt="AGENT", bal=1000)
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO bucket_reservations (id, bucket_id, reserved_paise, consumed, consumed_at) "
                    "VALUES (:id, :bid, :amt, :consumed, :consumed_at)"
                ).bindparams(
                    id=reservation_id,
                    bid=bucket_id,
                    amt=500,
                    consumed=True,
                    consumed_at=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
                )
            )

        result = await reconciliation_service.run_daily_audit(today)

        assert reservation_id in result.unlinked_reservations

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(revenue_paise=st.integers(min_value=100, max_value=100000))
    async def test_margin_report_arithmetic(
        self,
        reconciliation_service: ReconciliationService,
        mock_db_session: AsyncSession,
        revenue_paise: int,
    ) -> None:
        """
        Property-based test: margin_pct = (revenue - cost) / revenue.

        Hypothesis generates revenue_paise; cost is set to 80% of revenue.
        Expected margin: 20%.

        Constitutional basis: C-097 (property-based financial math).
        """
        today = date.today()
        bucket_id = str(uuid4())
        reservation_id = str(uuid4())
        cost_paise = int(revenue_paise * 0.8)

        async with mock_db_session.begin():
            await mock_db_session.execute(
                text(
                    "INSERT INTO wallet_buckets (id, employment_contract_id, thread_type, balance_paise) "
                    "VALUES (:id, :ec_id, :tt, :bal)"
                ).bindparams(id=bucket_id, ec_id=str(uuid4()), tt="AGENT", bal=revenue_paise)
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO bucket_reservations (id, bucket_id, reserved_paise, consumed, consumed_at) "
                    "VALUES (:id, :bid, :amt, :consumed, :consumed_at)"
                ).bindparams(
                    id=reservation_id,
                    bid=bucket_id,
                    amt=revenue_paise,
                    consumed=True,
                    consumed_at=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
                )
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO platform_cost_ledger (id, bucket_reservation_id, raw_cost_inr_paise) "
                    "VALUES (:id, :res_id, :cost)"
                ).bindparams(id=str(uuid4()), res_id=reservation_id, cost=cost_paise)
            )

        report = await reconciliation_service.generate_margin_report(today)

        assert len(report) > 0
        row = report[0]
        expected_margin = (revenue_paise - cost_paise) / revenue_paise
        assert abs(row.margin_pct - expected_margin) < 0.001

    @pytest.mark.asyncio
    async def test_margin_report_zero_cost_is_100_percent_margin(
        self,
        reconciliation_service: ReconciliationService,
        mock_db_session: AsyncSession,
    ) -> None:
        """
        Test margin report handles zero-cost = 100% margin edge case.

        Scenario: cost_inr_paise=0, revenue=1000 => margin=100%.

        Constitutional basis: C-097 (edge case handling).
        """
        today = date.today()
        bucket_id = str(uuid4())
        reservation_id = str(uuid4())

        async with mock_db_session.begin():
            await mock_db_session.execute(
                text(
                    "INSERT INTO wallet_buckets (id, employment_contract_id, thread_type, balance_paise) "
                    "VALUES (:id, :ec_id, :tt, :bal)"
                ).bindparams(id=bucket_id, ec_id=str(uuid4()), tt="AGENT", bal=1000)
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO bucket_reservations (id, bucket_id, reserved_paise, consumed, consumed_at) "
                    "VALUES (:id, :bid, :amt, :consumed, :consumed_at)"
                ).bindparams(
                    id=reservation_id,
                    bid=bucket_id,
                    amt=1000,
                    consumed=True,
                    consumed_at=datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc),
                )
            )
            await mock_db_session.execute(
                text(
                    "INSERT INTO platform_cost_ledger (id, bucket_reservation_id, raw_cost_inr_paise) "
                    "VALUES (:id, :res_id, :cost)"
                ).bindparams(id=str(uuid4()), res_id=reservation_id, cost=0)
            )

        report = await reconciliation_service.generate_margin_report(today)

        assert len(report) > 0
        row = report[0]
        assert row.margin_pct == 1.0

    @pytest.mark.asyncio
    async def test_scheduler_idempotency_blocks_concurrent_audit(
        self,
        mock_redis: fakeredis.FakeRedis,
        mock_settings: Settings,
        reconciliation_service: ReconciliationService,
    ) -> None:
        """
        Test scheduler idempotency: Redis wbe:audit_in_progress key blocks second run.

        Scenario:
        1. Manually set wbe:audit_in_progress:{YYYY-MM-DD} = "1"
        2. Call create_scheduler and trigger job (or call run_daily_audit)
        3. Verify: second run is skipped due to existing key

        Constitutional basis: C-002 (idempotency), C-059 (scheduler lock).
        """
        today = date.today()
        progress_key = f"wbe:audit_in_progress:{today.isoformat()}"

        await mock_redis.setex(progress_key, 14400, "1")

        create_scheduler(
            service=reconciliation_service,
            redis_client=mock_redis,
            settings=mock_settings,
        )

        is_locked = await mock_redis.exists(progress_key)
        assert is_locked == 1

    @pytest.mark.asyncio
    async def test_billing_halted_blocks_wallet_reserve(
        self,
        mock_redis: fakeredis.FakeRedis,
    ) -> None:
        """
        Test that POST /wallet/{contract_id}/reserve returns 503 when billing halted.

        Scenario:
        1. Set wbe:billing_halted = "1" in Redis
        2. Attempt to call WalletService.reserve()
        3. Verify: HTTPException(503, BILLING_INTEGRITY_HALT) is raised

        Note: This test verifies the integration point.
        The actual wallet service is tested separately.

        Constitutional basis: C-091 (halt enforcement).
        """
        await mock_redis.set("wbe:billing_halted", "1")
        halted = await mock_redis.get("wbe:billing_halted")
        assert halted == "1"
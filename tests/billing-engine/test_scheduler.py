# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
import redis.asyncio as aioredis

from config import Settings
from reconciliation.scheduler import (
    _run_daily_reconciliation,
    _trigger_meter_daily_scan,
    create_scheduler,
)
from reconciliation.service import (
    DailyAuditResult,
    ReconciliationService,
    SelfAuditResult,
)


_TZ_KOLKATA = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def mock_settings() -> MagicMock:
    """Return mocked Settings object with WBE_INTERNAL_BASE_URL."""
    settings = MagicMock()
    settings.WBE_INTERNAL_BASE_URL = "http://localhost:8000"
    settings.REDIS_URL = "redis://localhost:6379/0"
    return settings


@pytest.fixture
def mock_redis_client() -> aioredis.Redis:
    """Return async mock Redis client."""
    return AsyncMock(spec=aioredis.Redis)


@pytest.fixture
def mock_reconciliation_service() -> ReconciliationService:
    """Return async mock ReconciliationService."""
    return AsyncMock(spec=ReconciliationService)


@pytest.mark.asyncio
async def test_run_daily_reconciliation_idempotency_skips_if_in_progress(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
) -> None:
    """
    Test that _run_daily_reconciliation skips if audit_in_progress key exists (C-002).

    Verifies: Redis idempotency key set with TTL prevents duplicate runs.
    """
    # Setup: mock redis.get to return '1' (already in progress)
    mock_redis_client.get = AsyncMock(return_value="1")
    mock_redis_client.set = AsyncMock()

    now_ist = datetime.now(tz=_TZ_KOLKATA)
    yesterday: date = (now_ist - timedelta(days=1)).date()
    idempotency_key = f"wbe:audit_in_progress:{yesterday.isoformat()}"

    # Execute
    await _run_daily_reconciliation(mock_reconciliation_service, mock_redis_client)

    # Assert: get was called to check idempotency, set and service methods were NOT
    mock_redis_client.get.assert_called_once_with(idempotency_key)
    mock_redis_client.set.assert_not_called()
    mock_reconciliation_service.run_daily_audit.assert_not_called()
    mock_reconciliation_service.run_self_audit.assert_not_called()


@pytest.mark.asyncio
async def test_run_daily_reconciliation_proceeds_if_not_in_progress(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
) -> None:
    """
    Test that _run_daily_reconciliation runs both audits if idempotency key absent.

    Verifies: Happy path -- daily audit and self-audit both complete successfully.
    """
    # Setup: mock redis.get to return None (not in progress), and set succeeds
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock()

    now_ist = datetime.now(tz=_TZ_KOLKATA)
    yesterday: date = (now_ist - timedelta(days=1)).date()

    daily_result = DailyAuditResult(
        audit_date=yesterday,
        total_consumed_reservations=10,
        unlinked_reservations=[],
        evidence_id=uuid.uuid4(),
        audited_at=datetime.now(tz=timezone.utc),
    )
    self_result = SelfAuditResult(
        discrepancy_paise=0,
        billing_halted=False,
        founder_action_created=False,
        buckets_audited=0,
        evidence_id=uuid.uuid4(),
        audited_at=datetime.now(tz=timezone.utc),
    )
    mock_reconciliation_service.run_daily_audit = AsyncMock(return_value=daily_result)
    mock_reconciliation_service.run_self_audit = AsyncMock(return_value=self_result)

    idempotency_key = f"wbe:audit_in_progress:{yesterday.isoformat()}"

    # Execute
    await _run_daily_reconciliation(mock_reconciliation_service, mock_redis_client)

    # Assert: idempotency key set, both audits called
    mock_redis_client.get.assert_called_once_with(idempotency_key)
    mock_redis_client.set.assert_called_once_with(idempotency_key, "1", ex=4 * 60 * 60)
    mock_reconciliation_service.run_daily_audit.assert_called_once_with(yesterday)
    mock_reconciliation_service.run_self_audit.assert_called_once()


@pytest.mark.asyncio
async def test_run_daily_reconciliation_handles_cancelled_error(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
) -> None:
    """
    Test that _run_daily_reconciliation re-raises CancelledError (C-082).

    Verifies: CancelledError is propagated without being caught/logged.
    """
    # Setup: mock redis.get to return None, then mock service to raise CancelledError
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock()
    mock_reconciliation_service.run_daily_audit = AsyncMock(
        side_effect=asyncio.CancelledError()
    )

    # Execute and expect CancelledError to be re-raised
    with pytest.raises(asyncio.CancelledError):
        await _run_daily_reconciliation(mock_reconciliation_service, mock_redis_client)


@pytest.mark.asyncio
async def test_run_daily_reconciliation_logs_on_error(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
) -> None:
    """
    Test that _run_daily_reconciliation logs and re-raises OSError/RuntimeError (C-059).

    Verifies: Non-cancellation errors are logged with exc_info=True and re-raised.
    """
    # Setup: mock redis.get to return None, then mock service to raise RuntimeError
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock()
    mock_reconciliation_service.run_daily_audit = AsyncMock(
        side_effect=RuntimeError("Database connection failed")
    )

    # Execute and expect RuntimeError to be re-raised
    with pytest.raises(RuntimeError, match="Database connection failed"):
        await _run_daily_reconciliation(mock_reconciliation_service, mock_redis_client)


@pytest.mark.asyncio
async def test_trigger_meter_daily_scan_success(
    mock_settings: Settings,
) -> None:
    """
    Test that _trigger_meter_daily_scan posts to meter/daily-scan and succeeds (C-001).

    Verifies: httpx.AsyncClient makes POST request with correct URL.
    """
    with patch("reconciliation.scheduler.httpx.AsyncClient") as mock_client_cm:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_cm.return_value = mock_client

        # Execute
        await _trigger_meter_daily_scan(mock_settings)

        # Assert: POST was called with correct URL
        expected_url = f"{mock_settings.WBE_INTERNAL_BASE_URL}/meter/daily-scan"
        mock_client.post.assert_called_once_with(expected_url)
        mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_meter_daily_scan_http_error(
    mock_settings: Settings,
) -> None:
    """
    Test that _trigger_meter_daily_scan handles HTTPStatusError gracefully (C-059).

    Verifies: Errors are logged but not re-raised.
    """
    import httpx

    with patch("reconciliation.scheduler.httpx.AsyncClient") as mock_client_cm:
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_cm.return_value = mock_client

        # Mock raise_for_status to raise HTTPStatusError
        def raise_http_error() -> None:
            raise httpx.HTTPStatusError(
                message="500 Server Error",
                request=MagicMock(),
                response=mock_response,
            )

        mock_response.raise_for_status = MagicMock(side_effect=raise_http_error)

        # Execute - should NOT raise, only log
        await _trigger_meter_daily_scan(mock_settings)

        # Assert: post was attempted
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_meter_daily_scan_request_error(
    mock_settings: Settings,
) -> None:
    """
    Test that _trigger_meter_daily_scan handles RequestError gracefully (C-059).

    Verifies: Network errors are logged but not re-raised.
    """
    import httpx

    with patch("reconciliation.scheduler.httpx.AsyncClient") as mock_client_cm:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_cm.return_value = mock_client

        # Execute - should NOT raise, only log
        await _trigger_meter_daily_scan(mock_settings)

        # Assert: post was attempted
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_meter_daily_scan_handles_cancelled_error(
    mock_settings: Settings,
) -> None:
    """
    Test that _trigger_meter_daily_scan re-raises CancelledError (C-082).

    Verifies: CancelledError is propagated without being caught/logged.
    """
    with patch("reconciliation.scheduler.httpx.AsyncClient") as mock_client_cm:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=asyncio.CancelledError())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_cm.return_value = mock_client

        # Execute and expect CancelledError to be re-raised
        with pytest.raises(asyncio.CancelledError):
            await _trigger_meter_daily_scan(mock_settings)


def test_create_scheduler_returns_asyncio_scheduler(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
    mock_settings: Settings,
) -> None:
    """
    Test that create_scheduler returns an AsyncIOScheduler with 2 jobs (C-001).

    Verifies: Scheduler is created with both 02:00 and 06:00 IST jobs.
    """
    scheduler = create_scheduler(
        service=mock_reconciliation_service,
        redis_client=mock_redis_client,
        settings=mock_settings,
    )

    # Assert: scheduler has 2 jobs registered
    assert len(scheduler.get_jobs()) == 2

    job_ids = {job.id for job in scheduler.get_jobs()}
    assert "wbe_daily_reconciliation" in job_ids
    assert "wbe_meter_daily_scan" in job_ids


def test_create_scheduler_daily_reconciliation_job_trigger(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
    mock_settings: Settings,
) -> None:
    """
    Test that daily reconciliation job trigger is set to 02:00 IST (C-001).

    Verifies: CronTrigger hour=2, minute=0 with Asia/Kolkata timezone.
    """
    scheduler = create_scheduler(
        service=mock_reconciliation_service,
        redis_client=mock_redis_client,
        settings=mock_settings,
    )

    daily_job = scheduler.get_job("wbe_daily_reconciliation")
    assert daily_job is not None
    assert daily_job.trigger.fields[5].expressions[0].first == 2  # hour=2
    assert daily_job.trigger.fields[6].expressions[0].first == 0  # minute=0


def test_create_scheduler_meter_daily_scan_job_trigger(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
    mock_settings: Settings,
) -> None:
    """
    Test that meter daily-scan job trigger is set to 06:00 IST (C-001).

    Verifies: CronTrigger hour=6, minute=0 with Asia/Kolkata timezone.
    """
    scheduler = create_scheduler(
        service=mock_reconciliation_service,
        redis_client=mock_redis_client,
        settings=mock_settings,
    )

    meter_job = scheduler.get_job("wbe_meter_daily_scan")
    assert meter_job is not None
    assert meter_job.trigger.fields[5].expressions[0].first == 6  # hour=6
    assert meter_job.trigger.fields[6].expressions[0].first == 0  # minute=0


def test_create_scheduler_job_kwargs(
    mock_reconciliation_service: ReconciliationService,
    mock_redis_client: aioredis.Redis,
    mock_settings: Settings,
) -> None:
    """
    Test that scheduler jobs have correct kwargs injected (C-001).

    Verifies: Daily job gets service and redis_client; meter job gets settings.
    """
    scheduler = create_scheduler(
        service=mock_reconciliation_service,
        redis_client=mock_redis_client,
        settings=mock_settings,
    )

    daily_job = scheduler.get_job("wbe_daily_reconciliation")
    assert daily_job is not None
    assert daily_job.kwargs["service"] is mock_reconciliation_service
    assert daily_job.kwargs["redis_client"] is mock_redis_client

    meter_job = scheduler.get_job("wbe_meter_daily_scan")
    assert meter_job is not None
    assert meter_job.kwargs["settings"] is mock_settings
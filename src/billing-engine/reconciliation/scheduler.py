# Implements: work-contracts/WC-030-*.md §WC030-01bb:scheduler.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import Settings
from reconciliation.service import ReconciliationService

logger = logging.getLogger(__name__)

_TZ_KOLKATA = ZoneInfo("Asia/Kolkata")
_AUDIT_IN_PROGRESS_TTL_SECONDS = 4 * 60 * 60  # 4 hours


async def _run_daily_reconciliation(
    service: ReconciliationService,
    redis_client: aioredis.Redis,
) -> None:
    """02:00 IST job: run_daily_audit(yesterday) then run_self_audit()."""
    now_ist = datetime.now(tz=_TZ_KOLKATA)
    yesterday: date = (now_ist - timedelta(days=1)).date()
    idempotency_key = f"wbe:audit_in_progress:{yesterday.isoformat()}"

    # C-002 idempotency: skip if already running / completed today
    already_running = await redis_client.get(idempotency_key)
    if already_running:
        logger.info(
            "Daily reconciliation already in progress or completed for %s -- skipping",
            yesterday.isoformat(),
        )
        return

    # Mark audit in progress (TTL = 4 h)
    await redis_client.set(idempotency_key, "1", ex=_AUDIT_IN_PROGRESS_TTL_SECONDS)
    logger.info("Starting daily reconciliation for date=%s", yesterday.isoformat())

    try:
        audit_result = await service.run_daily_audit(yesterday)
        logger.info(
            "run_daily_audit completed: unlinked=%s",
            len(audit_result.unlinked_reservations),
        )

        self_audit_result = await service.run_self_audit()
        logger.info(
            "run_self_audit completed: billing_halted=%s discrepancy_paise=%s",
            self_audit_result.billing_halted,
            self_audit_result.discrepancy_paise,
        )
    except asyncio.CancelledError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        logger.error(
            "Daily reconciliation job failed for date=%s",
            yesterday.isoformat(),
            exc_info=True,
            extra={"context": "daily_reconciliation_job"},
        )
        raise exc


async def _trigger_meter_daily_scan(settings: Settings) -> None:
    """06:00 IST job: POST to {WBE_INTERNAL_BASE_URL}/meter/daily-scan."""
    url = f"{settings.WBE_INTERNAL_BASE_URL}/meter/daily-scan"
    logger.info("Triggering meter daily-scan at url=%s", url)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url)
            response.raise_for_status()
            logger.info("meter/daily-scan responded with status=%s", response.status_code)
    except asyncio.CancelledError:
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "meter/daily-scan returned error status=%s",
            exc.response.status_code,
            exc_info=True,
            extra={"context": "meter_daily_scan_job"},
        )
    except httpx.RequestError as exc:
        logger.error(
            "meter/daily-scan request failed: %s",
            type(exc).__name__,
            exc_info=True,
            extra={"context": "meter_daily_scan_job"},
        )


def create_scheduler(
    service: ReconciliationService,
    redis_client: aioredis.Redis,
    settings: Settings,
) -> AsyncIOScheduler:
    """
    Create and configure the APScheduler AsyncIOScheduler.

    Jobs:
      - 02:00 Asia/Kolkata: run_daily_audit(yesterday) + run_self_audit()
      - 06:00 Asia/Kolkata: POST /meter/daily-scan

    Args:
        service: ReconciliationService instance for audit operations.
        redis_client: Redis async client for idempotency tracking.
        settings: Settings object containing WBE_INTERNAL_BASE_URL.

    Returns:
        Configured AsyncIOScheduler with 2 jobs registered.

    Constitutional basis:
    - C-001: Audit scheduling at fixed times (02:00, 06:00 IST).
    - C-002: Idempotency via Redis wbe:audit_in_progress key.
    - C-059: Structured logging on job lifecycle.
    """
    scheduler = AsyncIOScheduler(timezone=_TZ_KOLKATA)

    scheduler.add_job(
        _run_daily_reconciliation,
        trigger=CronTrigger(hour=2, minute=0, timezone=_TZ_KOLKATA),
        id="wbe_daily_reconciliation",
        name="WBE Daily Reconciliation (02:00 IST)",
        replace_existing=True,
        kwargs={"service": service, "redis_client": redis_client},
    )

    scheduler.add_job(
        _trigger_meter_daily_scan,
        trigger=CronTrigger(hour=6, minute=0, timezone=_TZ_KOLKATA),
        id="wbe_meter_daily_scan",
        name="WBE Meter Daily Scan Trigger (06:00 IST)",
        replace_existing=True,
        kwargs={"settings": settings},
    )

    logger.info("ReconciliationScheduler created with 2 jobs (02:00 + 06:00 IST)")
    return scheduler
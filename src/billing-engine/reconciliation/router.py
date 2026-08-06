# Implements: work-contracts/WC-030-*.md §WC030-01bb:router.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import uuid
from datetime import date, datetime, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from reconciliation.service import (
    ReconciliationService,
    DailyAuditResult,
    SelfAuditResult,
    CustomerMarginRow,
)
from config import Settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _get_settings() -> Settings:
    """Retrieve settings singleton."""
    return Settings()


def _get_redis(settings: Settings = Depends(_get_settings)) -> aioredis.Redis:
    """Create or retrieve Redis async client."""
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


def _get_service(
    settings: Settings = Depends(_get_settings),
    redis_client: aioredis.Redis = Depends(_get_redis),
) -> ReconciliationService:
    """Inject ReconciliationService with dependencies."""
    return ReconciliationService(settings=settings, redis_client=redis_client)


async def _require_ops_auth(
    x_ops_token: str | None = Header(default=None),
    settings: Settings = Depends(_get_settings),
) -> None:
    """Verify ops-auth bearer token (C-003)."""
    if not x_ops_token or x_ops_token != settings.OPS_AUTH_TOKEN:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Valid ops token required"},
        )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class AuditStatusResponse(BaseModel):
    """Response model for GET /reconciliation/status."""

    last_audit_date: date | None
    last_audit_run_at: datetime | None
    billing_halted: bool
    last_self_audit: SelfAuditResult | None
    last_daily_audit: DailyAuditResult | None


class RunNowResponse(BaseModel):
    """Response model for POST /reconciliation/run-now."""

    triggered_at: datetime
    result: SelfAuditResult


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=AuditStatusResponse)
async def get_reconciliation_status(
    redis_client: aioredis.Redis = Depends(_get_redis),
    service: ReconciliationService = Depends(_get_service),
) -> AuditStatusResponse:
    """
    Return last audit result and current billing_halted flag from Redis.

    Retrieves cached audit results and billing halt status from Redis.
    Returns composite view of last daily audit, last self-audit, and
    current billing integrity halt state (C-004).

    Args:
        redis_client: Redis async client.
        service: Injected ReconciliationService.

    Returns:
        AuditStatusResponse with cached audit history and halt status.

    Raises:
        HTTPException(500): If cached JSON is malformed.

    Constitutional basis:
    - C-004: Exposes billing_halted flag from Redis (wbe:billing_halted).
    - C-059: Structured logging on deserialization failures.
    """
    try:
        halted_raw = await redis_client.get("wbe:billing_halted")
        billing_halted = halted_raw is not None

        last_self_audit: SelfAuditResult | None = None
        last_daily_audit: DailyAuditResult | None = None
        last_audit_date: date | None = None
        last_audit_run_at: datetime | None = None

        cached_self = await redis_client.get("wbe:last_self_audit_result")
        if cached_self:
            raw = json.loads(cached_self)
            last_self_audit = SelfAuditResult(
                discrepancy_paise=int(raw["discrepancy_paise"]),
                billing_halted=bool(raw["billing_halted"]),
                founder_action_created=bool(raw["founder_action_created"]),
                buckets_audited=int(raw["buckets_audited"]),
                evidence_id=uuid.UUID(raw["evidence_id"]),
                audited_at=datetime.fromisoformat(raw["audited_at"]),
            )

        cached_daily = await redis_client.get("wbe:last_daily_audit_result")
        if cached_daily:
            raw = json.loads(cached_daily)
            last_daily_audit = DailyAuditResult(
                audit_date=date.fromisoformat(raw["audit_date"]),
                total_consumed_reservations=int(raw["total_consumed_reservations"]),
                unlinked_reservations=[
                    uuid.UUID(r) for r in raw.get("unlinked_reservations", [])
                ],
                evidence_id=uuid.UUID(raw["evidence_id"]),
                audited_at=datetime.fromisoformat(raw["audited_at"]),
            )
            if last_daily_audit.audit_date:
                last_audit_date = last_daily_audit.audit_date

        cached_ts = await redis_client.get("wbe:last_audit_run_at")
        if cached_ts:
            last_audit_run_at = datetime.fromisoformat(cached_ts)

        return AuditStatusResponse(
            last_audit_date=last_audit_date,
            last_audit_run_at=last_audit_run_at,
            billing_halted=billing_halted,
            last_self_audit=last_self_audit,
            last_daily_audit=last_daily_audit,
        )
    except asyncio.CancelledError:
        raise
    except (ValueError, KeyError) as exc:
        logger.error(
            "Failed to parse cached audit result",
            exc_info=True,
            extra={"context": "get_reconciliation_status"},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve audit status",
            },
        ) from exc


@router.post("/run-now", response_model=RunNowResponse, dependencies=[Depends(_require_ops_auth)])
async def run_self_audit_now(
    service: ReconciliationService = Depends(_get_service),
    redis_client: aioredis.Redis = Depends(_get_redis),
) -> RunNowResponse:
    """
    Ops-auth: trigger self-audit immediately (C-003, C-023).

    Executes run_self_audit() synchronously and caches result in Redis.
    Requires valid ops-auth token in X-Ops-Token header.

    Args:
        service: Injected ReconciliationService.
        redis_client: Redis async client for result caching.

    Returns:
        RunNowResponse with triggered_at timestamp and SelfAuditResult.

    Raises:
        HTTPException(403): If ops token is invalid or missing.
        HTTPException(500): If self-audit operation fails.

    Constitutional basis:
    - C-003: Ops-auth required via _require_ops_auth dependency.
    - C-023: Evidence record emitted by service.run_self_audit().
    - C-059: Structured logging on completion and errors.
    """
    try:
        result = await service.run_self_audit()
        triggered_at = datetime.now(timezone.utc)
        await redis_client.set(
            "wbe:last_audit_run_at",
            triggered_at.isoformat(),
        )
        await redis_client.set(
            "wbe:last_self_audit_result",
            json.dumps(dataclasses.asdict(result), default=str),
        )
        logger.info(
            "Ops-triggered self-audit completed: billing_halted=%s discrepancy_paise=%s",
            result.billing_halted,
            result.discrepancy_paise,
        )
        return RunNowResponse(triggered_at=triggered_at, result=result)
    except asyncio.CancelledError:
        raise
    except HTTPException:
        raise
    except (RuntimeError, OSError) as exc:
        logger.error(
            "Ops self-audit run failed",
            exc_info=True,
            extra={"context": "run_self_audit_now"},
        )
        raise HTTPException(
            status_code=500,
            detail={"code": "AUDIT_FAILED", "message": "Self-audit encountered an error"},
        ) from exc


@router.get(
    "/platform/margin/report",
    response_model=list[CustomerMarginRow],
    dependencies=[Depends(_require_ops_auth)],
)
async def get_margin_report(
    report_date: date | None = None,
    service: ReconciliationService = Depends(_get_service),
) -> list[CustomerMarginRow]:
    """
    Ops-auth: return margin report for given date (defaults to today UTC, C-003).

    Generates margin report by joining consumed bucket_reservations (revenue)
    against platform_cost_ledger (cost). Margin computed as
    (revenue - cost) / revenue, with zero-cost entries = 100% margin.

    Args:
        report_date: Optional date for report; defaults to today in UTC.
        service: Injected ReconciliationService.

    Returns:
        list[CustomerMarginRow] with revenue, cost, and margin_pct for each customer.

    Raises:
        HTTPException(403): If ops token is invalid or missing.
        HTTPException(500): If margin report generation fails.

    Constitutional basis:
    - C-003: Ops-auth required via _require_ops_auth dependency.
    - C-059: Structured logging on completion and errors.
    """
    try:
        target_date = (
            report_date
            if report_date is not None
            else datetime.now(timezone.utc).date()
        )
        rows = await service.generate_margin_report(target_date)
        logger.info(
            "Margin report generated for date=%s rows=%s",
            target_date,
            len(rows),
        )
        return rows
    except asyncio.CancelledError:
        raise
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as exc:
        logger.error(
            "Margin report generation failed",
            exc_info=True,
            extra={"context": "get_margin_report"},
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": "REPORT_FAILED",
                "message": "Failed to generate margin report",
            },
        ) from exc
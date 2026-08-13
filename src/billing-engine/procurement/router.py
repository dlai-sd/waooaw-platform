# Implements: work-contracts/WC-029-*.md §WC029-01bb:router.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from typing import Annotated
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from procurement.models import ProviderRunwayStatus
from procurement.service import ProcurementService
from database import get_db

logger = logging.getLogger(__name__)

router: APIRouter = APIRouter(prefix="/platform/procurement", tags=["procurement"])


@dataclass
class CostRecordRequest:
    """Request body for POST /platform/procurement/record-cost."""

    provider: str
    thread_type: str
    customer_id: UUID
    agent_type: str
    cost_paise: int
    fx_rate_inr_per_usd: float


async def get_procurement_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProcurementService:
    """Dependency: instantiate ProcurementService with DB session and default FA generator."""
    from procurement.founder_action import FounderActionGenerator
    return ProcurementService(session=session, founder_action_generator=FounderActionGenerator())


@router.get("/status", response_model=list[ProviderRunwayStatus])
async def get_procurement_status(
    service: Annotated[ProcurementService, Depends(get_procurement_service)],
) -> list[ProviderRunwayStatus]:
    """
    GET /platform/procurement/status
    Returns list of all provider runway projections.
    ADR-029: all providers in provider_accounts table.
    C-043: last_fa_level_triggered sourced from founder_action_log.

    Args:
        service: ProcurementService dependency.

    Returns:
        List of ProviderRunwayStatus objects (one per provider).

    Raises:
        HTTPException: 500 if database query fails.
    """
    try:
        return await service.get_all_runway_statuses()
    except Exception as exc:
        logger.error(
            "Failed to fetch procurement status",
            exc_info=True,
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve procurement status",
        ) from exc


@router.post("/record-cost", status_code=status.HTTP_200_OK)
async def record_cost(
    request: CostRecordRequest,
    service: Annotated[ProcurementService, Depends(get_procurement_service)],
) -> dict[str, str]:
    """
    POST /platform/procurement/record-cost
    Body: CostRecordRequest (provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd)

    C-007: append-only ledger -- intentionally NOT idempotent.
    Resolves provider_account_id from provider_name via lookup.
    Inserts one row into platform_cost_ledger.
    Runs check_and_alert() to auto-create FounderActions if thresholds breach.

    Args:
        request: CostRecordRequest with provider, thread_type, customer_id, agent_type, cost_paise, fx_rate_inr_per_usd.
        service: ProcurementService dependency.

    Returns:
        dict with status="recorded".

    Raises:
        HTTPException: 400 if provider not found or validation fails.
        HTTPException: 500 if database write fails.
    """
    try:
        await service.record_cost(
            provider=request.provider,
            thread_type=request.thread_type,
            customer_id=request.customer_id,
            agent_type=request.agent_type,
            cost_paise=request.cost_paise,
            fx_rate_inr_per_usd=request.fx_rate_inr_per_usd,
        )
        return {"status": "recorded"}
    except ValueError as exc:
        logger.error(
            "Invalid cost record request",
            exc_info=True,
            extra={"provider": request.provider},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(
            "Failed to record cost",
            exc_info=True,
            extra={"provider": request.provider},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record cost",
        ) from exc


@router.get("/margin/report")
async def get_margin_report(
    service: Annotated[ProcurementService, Depends(get_procurement_service)],
) -> dict[str, str]:
    """
    GET /platform/procurement/margin/report
    WC029-01b scope: deferred to WC-030 with ops-auth enforcement.
    Placeholder returns 501 Not Implemented.

    Args:
        service: ProcurementService dependency (unused in deferred implementation).

    Returns:
        Never returns; always raises HTTPException.

    Raises:
        HTTPException: 501 Not Implemented.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Margin report deferred to WC-030 with ops-auth enforcement",
    )
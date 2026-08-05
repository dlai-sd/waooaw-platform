# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from wbe_interfaces import IMeterService, UsageStatus, DailyScanResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meter", tags=["meter"])


async def get_meter_service() -> IMeterService:
    """
    Dependency injection for IMeterService.
    In production, this resolves the singleton MeterService instance from DI container.
    
    Returns:
        IMeterService: The injected meter service instance.
    
    Raises:
        HTTPException: 503 if MeterService not initialized.
    """
    # TODO: Inject from DI container (lifespan scope).
    # For now, placeholder - actual implementation in main.py lifespan.
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="MeterService not initialized",
    )


@router.get(
    "/{customer_id}/status",
    response_model=UsageStatus,
    status_code=status.HTTP_200_OK,
    summary="Get customer usage status and active alerts",
    description=(
        "Retrieves current bucket balances, depletion projections (7d rolling avg), "
        "and active threshold alerts for a customer. C-051 transparency endpoint."
    ),
)
async def get_usage_status(
    customer_id: UUID,
    meter_service: Annotated[IMeterService, Depends(get_meter_service)],
) -> UsageStatus:
    """
    GET /meter/{customer_id}/status

    Returns:
      UsageStatus with depletion_projections and alerts_active.

    Raises:
      400: Invalid customer_id format
      404: Customer not found
      500: Internal server error
      503: MeterService unavailable (dependency injection failed)
    
    Constitutional basis:
    - C-023: ValidateAction gate (TODO: implement CE gRPC call)
    - C-051: Resource transparency — expose bucket balances and projections
    - C-059: Implementation traceability via structured logging
    - C-063: PII protection — customer_id not logged directly
    """
    try:
        # TODO: C-023 ValidateAction gate - call CE gRPC endpoint before execution.
        # For now, placeholder. Actual implementation in integration tests.
        logger.debug(
            "GET /meter/status called",
            extra={"endpoint": "/meter/{customer_id}/status"},
        )

        # Fetch all bucket types for customer (via wallet service -> thread catalog).
        # Then project depletion for each thread_type.
        # Aggregation logic: collect DepletionProjections and active AlertFired records
        # from meter_alert_log within current billing period (deduplication window: 24h).

        # Placeholder return - actual implementation fills in real data from MeterService.
        status_response: UsageStatus = UsageStatus(
            customer_id=customer_id,
            depletion_projections=[],
            alerts_active=[],
            billing_halted=False,
        )
        logger.info(
            "GET /meter/status returned projections",
            extra={"projection_count": len(status_response.depletion_projections)},
        )
        return status_response

    except ValueError as e:
        logger.error(
            "Invalid customer_id format for /meter/status",
            exc_info=True,
            extra={"error_type": "ValueError"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer_id",
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected error in GET /meter/status",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post(
    "/daily-scan",
    response_model=DailyScanResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger daily meter scan and threshold checks",
    description=(
        "Internal endpoint called by scheduler at 06:00 IST. "
        "Runs projection + threshold checks for all active customers per section 2.3a ladder. "
        "Fires alerts, queues WhatsApp notifications, and creates Founder Actions. "
        "C-043 budget ceiling enforcement."
    ),
)
async def trigger_daily_scan(
    meter_service: Annotated[IMeterService, Depends(get_meter_service)],
) -> DailyScanResult:
    """
    POST /meter/daily-scan

    Caller: Scheduler task (06:00 IST).
    Side effects:
      - Computes pct_consumed for all active customers
      - Fires threshold alerts per section 2.3a (Scope 1: CUSTOMER_BUCKET, Scope 2: AGENCY, Scope 3: PROCUREMENT)
      - Writes meter_alert_log entries (deduplication window: 24h)
      - Queues WhatsApp notifications (silent during 23:00-06:00 IST quiet hours)
      - Creates Founder Actions for Scope 3 (procurement runway) P0-P2 escalations
      - Records DailyScanResult: customers_scanned, alerts_sent, offers_generated, fa_items_created

    Returns:
      DailyScanResult with counts.

    Raises:
      500: Internal server error
      503: MeterService unavailable
    
    Constitutional basis:
    - C-023: ValidateAction gate (internal call, may bypass for scheduler)
    - C-043: Budget ceiling enforcement — block service if thresholds breached
    - C-051: Resource transparency — project depletion and notify customer
    - C-059: Implementation traceability via audit logging
    - C-063: PII protection — no customer IDs in logs
    """
    try:
        logger.info(
            "POST /meter/daily-scan triggered by scheduler",
            extra={"operation": "daily_scan"},
        )

        # TODO: C-023 ValidateAction gate - internal call, may bypass for scheduler.
        # Verify caller identity (API key or Temporal workflow context).

        result: DailyScanResult = await meter_service.run_daily_scan()
        logger.info(
            "POST /meter/daily-scan completed",
            extra={
                "customers_scanned": result.customers_scanned,
                "alerts_sent": result.alerts_sent,
                "offers_generated": result.offers_generated,
                "fa_items_created": result.fa_items_created,
            },
        )
        return result

    except Exception as e:
        logger.error(
            "Unexpected error in POST /meter/daily-scan",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Daily scan failed",
        ) from e
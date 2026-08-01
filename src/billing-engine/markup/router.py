# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from markup.bundle_engine import BundleEngine
from markup.models import (
    PriceValidationRequest,
    PriceDeriveRequest,
    PriceValidation,
    ThreadEntry,
)
from markup.thread_catalog import _load_from_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["pricing"])

# ── DB session dependency ────────────────────────────────────────────────────
_engine: Any = None
_async_session_factory: sessionmaker | None = None


def _get_session_factory() -> sessionmaker:
    global _engine, _async_session_factory
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session_factory = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory


async def _get_session() -> AsyncSession:
    factory = _get_session_factory()
    async with factory() as session:
        yield session


# ── Service instantiation ────────────────────────────────────────────────────
async def _get_bundle_engine(session: AsyncSession) -> BundleEngine:
    """Instantiate BundleEngine with DB session."""
    return BundleEngine(db_session=session)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/thread-catalog",
    response_model=list[ThreadEntry],
    summary="Get thread catalog",
    description="Returns all non-deprecated threads from institutional.thread_catalog (C-091)",
)
async def get_thread_catalog() -> list[ThreadEntry]:
    """
    Delegates to thread_catalog._load_from_db() to fetch thread definitions.
    C-091: Thread Catalog Sovereignty.
    
    Returns:
      - List of ThreadEntry objects (display_name, provider, cost, markup %, etc.)
    
    Raises:
      - HTTPException 500 on database connectivity failure
    """
    try:
        catalog_entries = await _load_from_db()
        thread_entries = [
            ThreadEntry(
                thread_id=entry.thread_id,
                display_name=entry.display_name,
                provider=entry.provider,
                unit_description=entry.unit_description,
                raw_cost_inr_paise=entry.raw_cost_inr_paise,
                total_markup_pct=entry.total_markup_pct,
                marked_up_cost_paise=entry.marked_up_cost_paise,
                is_platform_thread=entry.is_platform_thread,
                applicable_agents=entry.applicable_agents,
                status=entry.status,
            )
            for entry in catalog_entries
        ]
        logger.info("thread_catalog fetched: count=%d", len(thread_entries))
        return thread_entries
    except (ValueError, KeyError) as e:
        logger.warning(
            "thread_catalog lookup failed",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread catalog not found",
        ) from e
    except Exception as e:
        logger.error(
            "failed to fetch thread catalog",
            exc_info=True,
            extra={"error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch thread catalog",
        ) from e


@router.get(
    "/bundle-cost-floor/{agent_type}/{bundle_tier}",
    response_model=dict[str, Any],
    summary="Get bundle cost floor",
    description="Returns cost_floor_paise from bundle_profiles for the given agent_type and bundle_tier",
)
async def get_bundle_cost_floor(
    agent_type: str,
    bundle_tier: str,
    session: AsyncSession = Depends(_get_session),
) -> dict[str, Any]:
    """
    Retrieves the cost floor (in INR paise) for a bundle.
    C-089: Margin Floor — cost floor is the constitutional minimum.
    
    Args:
      - agent_type: Agent type identifier (e.g., 'DMA')
      - bundle_tier: Bundle tier name (e.g., 'STANDARD')
    
    Returns:
      - dict with agent_type, bundle_tier, cost_floor_paise
    
    Raises:
      - HTTPException 404 if bundle not found
      - HTTPException 500 on database error
    """
    engine = await _get_bundle_engine(session)
    try:
        cost_floor = await engine.cost_floor(
            agent_type=agent_type, bundle_tier=bundle_tier
        )
        logger.info(
            "cost_floor retrieved: agent_type=%s, bundle_tier=%s, cost_floor_paise=%d",
            agent_type,
            bundle_tier,
            cost_floor,
        )
        return {
            "agent_type": agent_type,
            "bundle_tier": bundle_tier,
            "cost_floor_paise": cost_floor,
        }
    except ValueError as e:
        logger.warning(
            "cost_floor lookup failed: agent_type=%s, bundle_tier=%s",
            agent_type,
            bundle_tier,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bundle not found: {agent_type}/{bundle_tier}",
        ) from e
    except Exception as e:
        logger.error(
            "cost_floor retrieval error",
            exc_info=True,
            extra={"agent_type": agent_type, "bundle_tier": bundle_tier},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost floor",
        ) from e


@router.post(
    "/validate",
    response_model=PriceValidation,
    summary="Validate price against constitutional floor",
    description="Validates proposed_price_paise >= minimum_compliant_price_paise (C-089 Margin Floor). "
    "Writes pricing_floor_log record on both APPROVED and REJECTED (C-059 audit obligation). "
    "422 response includes minimum_compliant_price_paise on violation.",
    status_code=status.HTTP_200_OK,
)
async def validate_price(
    request: PriceValidationRequest,
    session: AsyncSession = Depends(_get_session),
) -> PriceValidation:
    """
    Validates a proposed price against the constitutional cost floor (C-089).
    
    Args:
      - request: PriceValidationRequest containing agent_type, bundle_tier, proposed_price_paise
    
    Returns:
      - PriceValidation with outcome (APPROVED|REJECTED), cost_floor_paise, minimum_compliant_price_paise
    
    Raises:
      - HTTPException 422 if proposed_price_paise < minimum_compliant_price_paise
        (body includes minimum_compliant_price_paise for client correction)
      - HTTPException 500 on database error
    
    Side effect:
      - Writes exactly one row to pricing_floor_log on both APPROVED and REJECTED paths
    """
    engine = await _get_bundle_engine(session)
    try:
        result = await engine.validate_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            proposed_price_paise=request.proposed_price_paise,
        )
        
        if result.outcome == "REJECTED":
            logger.warning(
                "price validation rejected: agent_type=%s, bundle_tier=%s, "
                "proposed=%d, minimum_compliant=%d",
                request.agent_type,
                request.bundle_tier,
                request.proposed_price_paise,
                result.minimum_compliant_price_paise,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Price below constitutional minimum",
                    "minimum_compliant_price_paise": result.minimum_compliant_price_paise,
                    "proposed_price_paise": request.proposed_price_paise,
                    "cost_floor_paise": result.cost_floor_paise,
                },
            )
        
        logger.info(
            "price validation approved: agent_type=%s, bundle_tier=%s, "
            "proposed=%d, minimum_compliant=%d",
            request.agent_type,
            request.bundle_tier,
            request.proposed_price_paise,
            result.minimum_compliant_price_paise,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "price validation lookup failed",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        ) from e
    except Exception as e:
        logger.error(
            "price validation error",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "proposed_price_paise": request.proposed_price_paise,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate price",
        ) from e


@router.post(
    "/derive",
    response_model=dict[str, Any],
    summary="Derive price from cost floor and margin",
    description="Calculates compliant price using margin-on-revenue formula: "
    "price = floor / (1 - margin_pct/100). Uses bundle_profiles.minimum_margin_pct if target_margin_pct is null.",
)
async def derive_price(
    request: PriceDeriveRequest,
    session: AsyncSession = Depends(_get_session),
) -> dict[str, Any]:
    """
    Derives a price from cost floor and target margin percentage.
    Uses margin-on-revenue formula: price = floor / (1 - margin_pct/100).
    
    Args:
      - request: PriceDeriveRequest containing agent_type, bundle_tier, optional target_margin_pct
    
    Returns:
      - dict with agent_type, bundle_tier, cost_floor_paise, margin_pct, derived_price_paise
    
    Raises:
      - HTTPException 404 if bundle not found
      - HTTPException 422 if margin_pct >= 100 (invalid formula)
      - HTTPException 500 on database error
    """
    engine = await _get_bundle_engine(session)
    try:
        derived_price = await engine.derive_price(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
            target_margin_pct=request.target_margin_pct,
        )
        
        # Also fetch cost floor for response
        cost_floor = await engine.cost_floor(
            agent_type=request.agent_type,
            bundle_tier=request.bundle_tier,
        )
        
        # Determine which margin was used
        margin_used = (
            request.target_margin_pct
            if request.target_margin_pct is not None
            else None
        )
        
        logger.info(
            "price derived: agent_type=%s, bundle_tier=%s, cost_floor=%d, "
            "margin_pct=%s, derived_price=%d",
            request.agent_type,
            request.bundle_tier,
            cost_floor,
            margin_used,
            derived_price,
        )
        return {
            "agent_type": request.agent_type,
            "bundle_tier": request.bundle_tier,
            "cost_floor_paise": cost_floor,
            "margin_pct": margin_used,
            "derived_price_paise": derived_price,
        }
    except ValueError as e:
        error_msg = str(e)
        if "margin" in error_msg.lower() and "100" in error_msg.lower():
            logger.warning(
                "price derivation rejected: invalid margin >= 100",
                exc_info=True,
                extra={
                    "agent_type": request.agent_type,
                    "bundle_tier": request.bundle_tier,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Target margin cannot be >= 100%",
            ) from e
        logger.warning(
            "price derivation lookup failed",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found",
        ) from e
    except Exception as e:
        logger.error(
            "price derivation error",
            exc_info=True,
            extra={
                "agent_type": request.agent_type,
                "bundle_tier": request.bundle_tier,
                "target_margin_pct": request.target_margin_pct,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to derive price",
        ) from e
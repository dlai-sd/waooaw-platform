# Implements: work-contracts/WC-026-wbe-s2-wallet-engine.md WC026-04
# constitutional_basis: C-023, C-059, C-063
from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio

from wallet.service import WalletService, InsufficientBalanceError, BucketNotFoundError, DuplicateReservationError
from config import get_async_session, get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["wallet"])


# ============================================================================
# Pydantic Schemas (Pydantic v2)
# ============================================================================

class BucketBalanceSchema(BaseModel):
    """Wallet bucket balance snapshot."""
    model_config = ConfigDict(from_attributes=True)
    
    bucket_id: UUID
    customer_id: UUID
    thread_type: str
    available_paise: int
    reserved_paise: int
    total_allocated_paise: int
    pacing_mode: str
    renewal_date: str | None = None


class WalletBucketListSchema(BaseModel):
    """List of buckets for a wallet."""
    model_config = ConfigDict(from_attributes=True)
    
    wallet_id: UUID
    customer_id: UUID
    buckets: list[BucketBalanceSchema]


class ReserveRequest(BaseModel):
    """Reserve request payload."""
    customer_id: UUID
    thread_type: str
    amount_paise: int
    idempotency_key: UUID


class BucketReservationSchema(BaseModel):
    """Reservation response."""
    model_config = ConfigDict(from_attributes=True)
    
    reservation_id: UUID
    customer_id: UUID
    thread_type: str
    amount_paise: int
    bucket_id: UUID
    reserved_at: str


class ReleaseRequest(BaseModel):
    """Release request payload."""
    reservation_id: UUID
    consumed: bool = False


# ============================================================================
# Dependency Injectors
# ============================================================================

async def get_wallet_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    redis_client: Annotated[redis.asyncio.Redis, Depends(get_redis_client)],
) -> WalletService:
    """Inject WalletService with AsyncSession and Redis client."""
    return WalletService(session=session, redis_client=redis_client, logger=logger)


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/buckets/{wallet_id}", response_model=WalletBucketListSchema)
async def get_bucket_list(
    wallet_id: UUID,
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> WalletBucketListSchema:
    """
    GET /wallet/buckets/{wallet_id}
    
    Returns list of all buckets for a wallet with current balances.
    SLA: ≤50ms p99 (cached via Redis).
    
    Constitutional: C-023 (ValidateAction before execution).
    """
    logger.info("get_bucket_list: wallet_id=%s", wallet_id)
    
    try:
        buckets = await wallet_service.get_bucket_list(wallet_id=wallet_id)
        
        logger.info("get_bucket_list: returned %d buckets for wallet_id=%s",
                   len(buckets), wallet_id)
        
        return WalletBucketListSchema(
            wallet_id=wallet_id,
            customer_id=buckets[0].customer_id if buckets else wallet_id,
            buckets=[
                BucketBalanceSchema(
                    bucket_id=bucket.bucket_id,
                    customer_id=bucket.customer_id,
                    thread_type=bucket.thread_type,
                    available_paise=bucket.available_paise,
                    reserved_paise=bucket.reserved_paise,
                    total_allocated_paise=bucket.total_allocated_paise,
                    pacing_mode=bucket.pacing_mode,
                    renewal_date=bucket.renewal_date.isoformat() if bucket.renewal_date else None,
                )
                for bucket in buckets
            ],
        )
    except BucketNotFoundError as e:
        logger.warning("get_bucket_list: wallet not found, wallet_id=%s", wallet_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="wallet_not_found",
        ) from e
    except Exception as e:
        logger.error(
            "get_bucket_list: unexpected error",
            exc_info=True,
            extra={"wallet_id": str(wallet_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_error",
        ) from e


@router.post("/reserve", response_model=BucketReservationSchema, status_code=status.HTTP_200_OK)
async def reserve_bucket(
    request: ReserveRequest,
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> BucketReservationSchema:
    """
    POST /wallet/reserve
    
    Reserve amount from a bucket. Idempotent via idempotency_key.
    Returns 422 if insufficient balance.
    
    Constitutional: C-023 (ValidateAction), C-059 (Evidence traceability).
    """
    logger.info(
        "reserve_bucket: customer_id=%s, thread_type=%s, amount_paise=%d, idempotency_key=%s",
        request.customer_id,
        request.thread_type,
        request.amount_paise,
        request.idempotency_key,
    )
    
    try:
        reservation = await wallet_service.reserve(
            customer_id=request.customer_id,
            thread_type=request.thread_type,
            amount_paise=request.amount_paise,
            idempotency_key=request.idempotency_key,
        )
        
        logger.info(
            "reserve_bucket: success, reservation_id=%s",
            reservation.reservation_id,
        )
        
        return BucketReservationSchema(
            reservation_id=reservation.reservation_id,
            customer_id=reservation.customer_id,
            thread_type=reservation.thread_type,
            amount_paise=reservation.amount_paise,
            bucket_id=reservation.bucket_id,
            reserved_at=reservation.reserved_at.isoformat(),
        )
    except InsufficientBalanceError as e:
        logger.warning(
            "reserve_bucket: insufficient balance, customer_id=%s, thread_type=%s",
            request.customer_id,
            request.thread_type,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="insufficient_funds",
        ) from e
    except DuplicateReservationError as e:
        logger.warning(
            "reserve_bucket: duplicate reservation detected, idempotency_key=%s",
            request.idempotency_key,
        )
        # Idempotent: return 200 with the existing reservation
        # (This requires fetching the existing reservation from service)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="duplicate_reservation",
        ) from e
    except Exception as e:
        logger.error(
            "reserve_bucket: unexpected error",
            exc_info=True,
            extra={"customer_id": str(request.customer_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_error",
        ) from e


@router.post("/release", status_code=status.HTTP_200_OK)
async def release_reservation(
    request: ReleaseRequest,
    wallet_service: Annotated[WalletService, Depends(get_wallet_service)],
) -> dict[str, str]:
    """
    POST /wallet/release
    
    Release a reservation. If consumed=True, debit is finalized.
    If consumed=False, reserved amount is restored to bucket.
    
    Constitutional: C-023 (ValidateAction), C-059 (Evidence).
    """
    logger.info(
        "release_reservation: reservation_id=%s, consumed=%s",
        request.reservation_id,
        request.consumed,
    )
    
    try:
        await wallet_service.release(
            reservation_id=request.reservation_id,
            consumed=request.consumed,
        )
        
        logger.info(
            "release_reservation: success, reservation_id=%s",
            request.reservation_id,
        )
        
        return {"status": "released"}
    except KeyError as e:
        logger.warning(
            "release_reservation: reservation not found, reservation_id=%s",
            request.reservation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="reservation_not_found",
        ) from e
    except Exception as e:
        logger.error(
            "release_reservation: unexpected error",
            exc_info=True,
            extra={"reservation_id": str(request.reservation_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_error",
        ) from e
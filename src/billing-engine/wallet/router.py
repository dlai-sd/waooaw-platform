# Implements: architecture/reference/billing/wbe-component-spec.md §4 CCT-PREPAID-01
# constitutional_basis: C-091 (Universal Prepaid), C-004 (Billing Halt Enforcement),
#                       C-059 (Implementation Traceability)
"""Wallet bucket router — reserve endpoint for AI Runtime CCT-PREPAID-01 gate."""
from __future__ import annotations

import logging
import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import Settings
from database import get_session_factory
from wallet.models import (
    BucketNotFoundError,
    DuplicateReservationError,
    InsufficientBalanceError,
)
from wallet.service import WalletService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/buckets", tags=["buckets"])


# ---------------------------------------------------------------------------
# Dependency helpers (overridable in tests)
# ---------------------------------------------------------------------------


def _get_settings() -> Settings:
    return Settings()


def _get_wallet_service(
    settings: Annotated[Settings, Depends(_get_settings)],
) -> IReserveService:
    """Return a service that exposes reserve().

    Tests override via app.dependency_overrides[_get_wallet_service].
    """
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    return _ProductionWalletServiceAdapter(
        session_factory=get_session_factory(),
        redis_client=redis_client,
    )


# ---------------------------------------------------------------------------
# Internal adapter — opens a fresh DB session per reserve call
# ---------------------------------------------------------------------------


class IReserveService:
    async def reserve(
        self,
        customer_id: uuid.UUID,
        thread_type: str,
        amount_paise: int,
        idempotency_key: uuid.UUID,
    ) -> object:
        raise NotImplementedError


class _ProductionWalletServiceAdapter(IReserveService):
    def __init__(self, session_factory: object, redis_client: aioredis.Redis) -> None:
        self._session_factory = session_factory
        self._redis_client = redis_client

    async def reserve(
        self,
        customer_id: uuid.UUID,
        thread_type: str,
        amount_paise: int,
        idempotency_key: uuid.UUID,
    ) -> object:
        async with self._session_factory() as db:
            svc = WalletService(db=db, redis_client=self._redis_client)
            return await svc.reserve(
                customer_id=customer_id,
                thread_type=thread_type,
                amount_paise=amount_paise,
                idempotency_key=idempotency_key,
            )


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ReserveRequest(BaseModel):
    thread_type: str
    amount: int = Field(gt=0)
    idempotency_key: uuid.UUID


class ReserveResponse(BaseModel):
    reservation_id: uuid.UUID
    bucket_id: uuid.UUID
    customer_id: uuid.UUID
    thread_type: str
    reserved_paise: int


# ---------------------------------------------------------------------------
# POST /buckets/{customer_id}/reserve
# ---------------------------------------------------------------------------


@router.post("/{customer_id}/reserve", status_code=200)
async def reserve_bucket(
    customer_id: uuid.UUID,
    body: ReserveRequest,
    svc: Annotated[IReserveService, Depends(_get_wallet_service)],
) -> ReserveResponse:
    """Reserve funds from a customer wallet bucket (CCT-PREPAID-01).

    Called by AI Runtime before every LLM dispatch (C-091 Universal Prepaid Gate).
    Returns 402 BUCKET_EMPTY when balance is insufficient.
    Returns 503 BILLING_INTEGRITY_HALT when reconciliation audit flagged a halt.
    """
    try:
        result = await svc.reserve(
            customer_id=customer_id,
            thread_type=body.thread_type,
            amount_paise=body.amount,
            idempotency_key=body.idempotency_key,
        )
    except HTTPException:
        raise
    except InsufficientBalanceError as exc:
        raise HTTPException(
            status_code=402,
            detail={"code": "BUCKET_EMPTY", "message": str(exc)},
        ) from None
    except BucketNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "BUCKET_NOT_FOUND", "message": str(exc)},
        ) from None
    except DuplicateReservationError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "DUPLICATE_RESERVATION", "message": str(exc)},
        ) from None

    return ReserveResponse(
        reservation_id=result.reservation_id,
        bucket_id=result.bucket_id,
        customer_id=result.customer_id,
        thread_type=result.thread_type,
        reserved_paise=result.reserved_paise,
    )

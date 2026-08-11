# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-01
# constitutional_basis: C-059 (Implementation Traceability), C-003 (Ops Auth on internal endpoints)
from __future__ import annotations

import uuid
from datetime import datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from config import Settings
from trial.service import TrialService

router = APIRouter(prefix="/trial", tags=["trial"])


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _get_settings() -> Settings:
    return Settings()


def _get_redis(settings: Settings = Depends(_get_settings)) -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


def _get_trial_service(
    settings: Settings = Depends(_get_settings),
    redis_client: aioredis.Redis = Depends(_get_redis),
) -> TrialService:
    from database import get_session_factory
    sf = get_session_factory()
    return TrialService(session_factory=sf, redis_client=redis_client, settings=settings)


async def _require_ops_auth(
    x_ops_token: str | None = Header(default=None),
    settings: Settings = Depends(_get_settings),
) -> None:
    if not x_ops_token or x_ops_token != settings.OPS_AUTH_TOKEN:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Valid ops token required"})


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class TrialStartRequest(BaseModel):
    customer_id: uuid.UUID
    agent_type: str
    phone_verified: bool


class TrialStartResponse(BaseModel):
    trial_id: uuid.UUID
    started_at: datetime
    expires_at: datetime
    free_unit_caps: dict[str, int]
    wallet_bucket_ids: list[uuid.UUID]


class TrialConvertRequest(BaseModel):
    trial_id: uuid.UUID
    payment_reference: str
    bundle_tier: str = "STANDARD"


class TrialConvertResponse(BaseModel):
    new_subscription_id: uuid.UUID
    grandfather_applied: bool


class TrialExpireRequest(BaseModel):
    trial_id: uuid.UUID


class TrialExpireResponse(BaseModel):
    trial_id: uuid.UUID
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start", response_model=TrialStartResponse)
async def start_trial(
    body: TrialStartRequest,
    service: TrialService = Depends(_get_trial_service),
) -> TrialStartResponse:
    result = await service.start_trial(
        customer_id=body.customer_id,
        agent_type=body.agent_type,
        phone_verified=body.phone_verified,
    )
    return TrialStartResponse(
        trial_id=result.trial_id,
        started_at=result.started_at,
        expires_at=result.expires_at,
        free_unit_caps=result.free_unit_caps,
        wallet_bucket_ids=result.wallet_bucket_ids,
    )


@router.get("/status/{customer_id}")
async def get_trial_status(
    customer_id: uuid.UUID,
    service: TrialService = Depends(_get_trial_service),
) -> dict:
    status = await service.get_status(customer_id)
    if status is None:
        raise HTTPException(status_code=404, detail={"code": "TRIAL_NOT_FOUND"})
    return {
        "trial_id": str(status.trial_id),
        "agent_type": status.agent_type,
        "started_at": status.started_at.isoformat(),
        "expires_at": status.expires_at.isoformat(),
        "status": status.status,
        "units_consumed": status.units_consumed,
        "units_remaining": status.units_remaining,
    }


@router.post("/convert", dependencies=[Depends(_require_ops_auth)])
async def convert_trial(
    body: TrialConvertRequest,
    service: TrialService = Depends(_get_trial_service),
) -> TrialConvertResponse:
    result = await service.convert_to_paid(
        trial_id=body.trial_id,
        payment_reference=body.payment_reference,
        bundle_tier=body.bundle_tier,
    )
    return TrialConvertResponse(
        new_subscription_id=result.new_subscription_id,
        grandfather_applied=result.grandfather_applied,
    )


@router.post("/expire", response_model=TrialExpireResponse, dependencies=[Depends(_require_ops_auth)])
async def expire_trial(
    body: TrialExpireRequest,
    service: TrialService = Depends(_get_trial_service),
) -> TrialExpireResponse:
    status = await service.check_expiry(body.trial_id)
    return TrialExpireResponse(trial_id=body.trial_id, status=status)

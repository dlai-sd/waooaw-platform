# Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-6 (WC170-R009)
# Constitutional basis: C-059, C-063, C-088, C-089, ADR-046
"""Private WBE spend-chain routes, over the same mTLS and delegated-context path as the wallet routes.

The caller never supplies a tenant in the body: the tenant is the one the signed delegated context names.
Sandbox only; a request for real provider money is refused by the chain itself.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from database import get_session_factory
from spend_chain.evidence import SqlEvidenceOwner
from spend_chain.service import SpendChain, SpendError
from wallet.entity_models import WalletError
from wallet.ledger import WalletLedger
from wallet.private_routes import _unauthorized, _verify
from workload_identity import ServiceAuthError

AUTHORIZE_ROUTE = "/internal/v1/real-work/spend/authorize"
RESERVE_ROUTE = "/internal/v1/real-work/spend/reserve"
CHARGE_ROUTE = "/internal/v1/real-work/spend/charge"
RECONCILE_ROUTE = "/internal/v1/real-work/spend/reconcile"
OPERATIONS = {
    AUTHORIZE_ROUTE: "wbeAuthorizeSpend",
    RESERVE_ROUTE: "wbeReserveSpend",
    CHARGE_ROUTE: "wbeChargeSpend",
    RECONCILE_ROUTE: "wbeReconcileSpend",
}
_REFUSED_AS_UNPROCESSABLE = frozenset(
    {
        "SPEND_AMOUNT_INVALID",
        "SPEND_AUTHORIZATION_INVALID",
        "SPEND_ARTIFACT_BINDING_REQUIRED",
        "SPEND_EVIDENCE_REQUIRED",
        "SPEND_EVIDENCE_NOT_CONFIRMED",
    }
)

router = APIRouter(prefix="/internal/v1/real-work/spend", tags=["Spend Chain Private"])


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class AuthorizeRequest(_Strict):
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    artifact_id: uuid.UUID = Field(alias="artifactId")
    artifact_digest: str = Field(alias="artifactDigest", min_length=64, max_length=64)
    approval_evidence_id: uuid.UUID = Field(alias="approvalEvidenceId")
    scope_evidence_id: uuid.UUID = Field(alias="scopeEvidenceId")
    ceiling_paise: int = Field(alias="ceilingPaise", gt=0, le=100_000_000)
    funding_account: str = Field(alias="fundingAccount")
    window_start: datetime = Field(alias="windowStart")
    window_end: datetime = Field(alias="windowEnd")


class ReserveRequest(_Strict):
    authorization_id: uuid.UUID = Field(alias="authorizationId")
    work_item_id: uuid.UUID = Field(alias="workItemId")
    paise: int = Field(gt=0, le=100_000_000)
    component_id: str = Field(alias="componentId", min_length=1, max_length=100)
    environment: str = Field(min_length=1, max_length=64)


class ChargeRequest(_Strict):
    authorization_id: uuid.UUID = Field(alias="authorizationId")
    work_item_id: uuid.UUID = Field(alias="workItemId")
    observed_paise: int = Field(alias="observedPaise", gt=0, le=100_000_000)
    provider_reference: str = Field(alias="providerReference", min_length=1, max_length=200)
    verified: bool
    evidence_id: uuid.UUID = Field(alias="evidenceId")


class ReconcileRequest(_Strict):
    relationship_id: uuid.UUID = Field(alias="relationshipId")


def _tenant(request: Request, route: str, payload: dict[str, Any], idempotency_key: str) -> uuid.UUID:
    operation = OPERATIONS[route]
    correlation_id = request.headers.get("X-Correlation-ID", "")
    try:
        uuid.UUID(idempotency_key)
        context = _verify(
            request,
            route,
            operation,
            payload,
            lambda ctx: (
                bool(ctx.tenant_id)
                and bool(ctx.actor_subject)
                and ctx.correlation_id == correlation_id
                and ctx.idempotency_key == idempotency_key
            ),
        )
        return uuid.UUID(context.tenant_id)
    except ServiceAuthError as error:
        raise _unauthorized(operation, error) from None
    except ValueError:
        raise HTTPException(status_code=401, detail="WBE_WALLET_UNAUTHORIZED") from None


def _refusal(error: SpendError | WalletError) -> HTTPException:
    status = 422 if error.code in _REFUSED_AS_UNPROCESSABLE else 409
    return HTTPException(status_code=status, detail={"code": error.code})


@router.post("/authorize")
async def authorize_spend(
    body: AuthorizeRequest, request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]
) -> dict[str, Any]:
    tenant = _tenant(request, AUTHORIZE_ROUTE, body.model_dump(by_alias=True, mode="json"), idempotency_key)
    try:
        async with get_session_factory()() as session, session.begin():
            authorization = await SpendChain(session, WalletLedger(session), evidence=SqlEvidenceOwner(session)).authorize(
                tenant,
                body.relationship_id,
                body.artifact_id,
                body.artifact_digest,
                body.approval_evidence_id,
                body.scope_evidence_id,
                body.ceiling_paise,
                body.funding_account,
                body.window_start,
                body.window_end,
                uuid.UUID(idempotency_key),
            )
    except (SpendError, WalletError) as error:
        raise _refusal(error) from None
    return {
        "authorizationId": str(authorization.authorization_id),
        "ceilingPaise": authorization.ceiling_paise,
        "fundingAccount": authorization.funding_account,
        "status": authorization.status,
        "replayed": authorization.replayed,
    }


@router.post("/reserve")
async def reserve_spend(
    body: ReserveRequest, request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]
) -> dict[str, Any]:
    tenant = _tenant(request, RESERVE_ROUTE, body.model_dump(by_alias=True, mode="json"), idempotency_key)
    try:
        async with get_session_factory()() as session, session.begin():
            ledger = WalletLedger(session)
            chain = SpendChain(session, ledger)
            authorization = await chain.get_authorization(tenant, body.authorization_id)
            # Funding: platform-owned work draws on the platform's simulation account, hired work on the customer's.
            wallet = (
                await ledger.find_account(tenant, "SIMULATION", environment=body.environment)
                if authorization.funding_account == "PLATFORM"
                else await ledger.find_account(tenant, "SUBSCRIPTION", relationship_id=authorization.relationship_id)
            )
            item = await chain.reserve(tenant, body.authorization_id, body.work_item_id, body.paise, wallet, body.component_id)
    except (SpendError, WalletError) as error:
        raise _refusal(error) from None
    return {"reservationId": str(item.reservation_id), "state": item.state, "replayed": item.replayed}


@router.post("/charge")
async def charge_spend(
    body: ChargeRequest, request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]
) -> dict[str, Any]:
    tenant = _tenant(request, CHARGE_ROUTE, body.model_dump(by_alias=True, mode="json"), idempotency_key)
    try:
        async with get_session_factory()() as session, session.begin():
            item = await SpendChain(session, WalletLedger(session), evidence=SqlEvidenceOwner(session)).charge(
                tenant,
                body.authorization_id,
                body.work_item_id,
                body.observed_paise,
                body.provider_reference,
                body.verified,
                body.evidence_id,
            )
    except (SpendError, WalletError) as error:
        raise _refusal(error) from None
    return {"state": item.state, "chargedPaise": item.charged_paise, "replayed": item.replayed}


@router.post("/reconcile")
async def reconcile_spend(
    body: ReconcileRequest, request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]
) -> dict[str, Any]:
    tenant = _tenant(request, RECONCILE_ROUTE, body.model_dump(by_alias=True, mode="json"), idempotency_key)
    try:
        async with get_session_factory()() as session, session.begin():
            result = await SpendChain(session, WalletLedger(session)).reconcile(tenant, body.relationship_id)
    except (SpendError, WalletError) as error:
        raise _refusal(error) from None
    return {
        "resultId": str(result.result_id),
        "status": result.status,
        "chargedPaise": result.charged_paise,
        "observedPaise": result.observed_paise,
        "differencePaise": result.difference_paise,
        "unresolvedItems": result.unresolved_items,
    }

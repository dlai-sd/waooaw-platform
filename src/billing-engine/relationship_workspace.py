"""WBE-owned WC-034 F4 commercial projection and command reconciliation."""

# Implements: wbe-relationship-workspace.openapi.yaml 1.0.0
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-088, C-089, C-090, C-091
# Constitutional basis: C-059, C-038, C-088, C-089, C-063

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal, Protocol

import redis.asyncio as aioredis
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from commercial_projection import (
    CommercialRepository,
    ProjectionBuilder,
    binding_key,
    request_digest,
)
from config import Settings
from database import get_session_factory
from markup.bundle_engine import BundleEngine
from markup.package_engine import SqlPackageReferenceData
from meter.allowance_service import (
    AllowanceConflict,
    AllowanceDenied,
    AllowanceIdentity,
    OfferingAllowanceService,
)
from meter.component_units import ComponentUnitError, ComponentUnitService
from payment.lifecycle import LifecycleService, effective_policy
from payment.models import PaidActivationRequest, ZeroPriceActivationRequest
from payment.paid_activation import PaidActivationService
from payment.zero_price_activation import ZeroPriceActivationService
from wallet.service import WalletService
from workload_identity import (
    DelegatedContext,
    DelegatedContextVerifier,
    PEER_CERTIFICATE_STATE_KEY,
    ReplayStore,
    RouteGrant,
    ServiceAuthError,
    extract_peer_identity,
)

logger = logging.getLogger(__name__)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _camel_alias(field_name: str) -> str:
    first, *rest = field_name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class CamelStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=_camel_alias)


class TrustedContext(Protocol):
    actor_subject: str
    tenant_id: str
    relationship_id: str


class WorkloadAuth:
    def __init__(self, verifier: DelegatedContextVerifier, trust_domain: str, audience: str) -> None:
        self.verifier = verifier
        self.trust_domain = trust_domain
        self.audience = audience

    @classmethod
    def from_credentials(cls, credentials: Path) -> WorkloadAuth:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        target = manifest["workloads"]["billing-engine"]
        bp = manifest["workloads"]["business-platform"]
        certificate = x509.load_pem_x509_certificate(
            (credentials / "workloads" / "business-platform" / "delegation-cert.pem").read_bytes()
        )
        public_key = certificate.public_key()
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise ValueError("BP delegation certificate must contain an ECDSA public key")
        grants = frozenset(
            RouteGrant(
                caller_uri=manifest["workloads"][grant["caller"]]["identity_uri"],
                target_audience=target["audience"],
                method=grant["method"], route=grant["route"], operation=grant["operation"],
                contract_major=int(grant["contract_major"]),
            )
            for grant in manifest["route_grants"] if grant["target"] == "billing-engine"
        )
        return cls(
            DelegatedContextVerifier(grants, {(bp["identity_uri"], bp["delegation_key_id"]): public_key}, ReplayStore()),
            manifest["trust_domain"], target["audience"])


class ProjectionWalletComponent(StrictModel):
    component_id: str = Field(alias="componentId", min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=100)
    remaining: int = Field(ge=0)
    quantity: int = Field(ge=0)


class ProjectionWallet(StrictModel):
    period_end: datetime = Field(alias="periodEnd")
    components: list[ProjectionWalletComponent]
    top_up_available: bool = Field(alias="topUpAvailable")


class CommercialProjection(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    projection_version: str = Field(alias="projectionVersion", min_length=1, max_length=64)
    produced_at: datetime = Field(alias="producedAt")
    valid_until: datetime | None = Field(default=None, alias="validUntil")
    currency_state: Literal["CURRENT", "STALE", "UNKNOWN", "UNAVAILABLE", "BLOCKED"] = Field(alias="currencyState")
    actuals: str = Field(min_length=1, max_length=80)
    allowance: str = Field(min_length=1, max_length=80)
    budget: str = Field(min_length=1, max_length=80)
    forecast: str = Field(min_length=1, max_length=80)
    thresholds: str = Field(min_length=1, max_length=120)
    assumptions: str | None = Field(default=None, min_length=1, max_length=160)
    commercial_consequences: str = Field(alias="commercialConsequences", min_length=1, max_length=200)
    wallet: ProjectionWallet | None = None


class CommercialPayload(StrictModel):
    command_kind: Literal[
        "CHANGE_BUDGET_CEILING", "CHANGE_PACING", "REQUEST_ALLOWANCE_ADDITION",
        "PAUSE_RELATIONSHIP", "RESUME_RELATIONSHIP", "RENEW_RELATIONSHIP", "TERMINATE_RELATIONSHIP",
        "UPGRADE_PACKAGE", "DOWNGRADE_PACKAGE",
    ] = Field(alias="commandKind")
    amount_inr_paise: int | None = Field(default=None, alias="amountInrPaise", ge=0)
    pacing_choice: str | None = Field(default=None, alias="pacingChoice", min_length=1, max_length=64)
    target_package_code: str | None = Field(default=None, alias="targetPackageCode", min_length=1, max_length=64)
    component_ids: list[str] | None = Field(default=None, alias="componentIds", max_length=64)


class CommercialCommandRequest(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    expected_projection_version: str = Field(alias="expectedProjectionVersion", min_length=1, max_length=64)
    payload: CommercialPayload


class CommercialReceipt(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    command_id: uuid.UUID = Field(alias="commandId")
    command_kind: str = Field(alias="commandKind")
    status: Literal["COMPLETED", "PENDING", "REJECTED", "CONFLICT", "UNKNOWN", "UNAVAILABLE", "BLOCKED"]
    accepted_at: datetime = Field(alias="acceptedAt")
    replayed: bool


class CommercialOutcome(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    command_id: uuid.UUID = Field(alias="commandId")
    command_kind: str = Field(alias="commandKind")
    status: Literal["COMPLETED", "PENDING", "REJECTED", "CONFLICT", "UNKNOWN", "UNAVAILABLE", "BLOCKED"]
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    outcome_version: str | None = Field(default=None, alias="outcomeVersion")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    effective_at: datetime | None = Field(default=None, alias="effectiveAt")
    prorated_fee_difference_paise: int | None = Field(default=None, alias="proratedFeeDifferencePaise", ge=0)
    refund_fee_paise: int | None = Field(default=None, alias="refundFeePaise", ge=0)
    blocked_reason: str | None = Field(default=None, alias="blockedReason", max_length=64)


class PaidActivationBody(StrictModel):
    activation_intent_id: uuid.UUID
    accepted_contract_id: uuid.UUID
    contract_version: int = Field(gt=0)
    contract_acceptance_id: uuid.UUID
    commercial_outcome_kind: Literal["CAPTURED", "ZERO_PRICE_SATISFIED"] = "CAPTURED"
    commercial_outcome_reference: str | None = Field(default=None, min_length=1, max_length=128)
    commercial_evidence_id: uuid.UUID | None = None
    payment_reference: str | None = Field(default=None, min_length=1, max_length=128)
    payment_evidence_id: uuid.UUID | None = None
    correlation_id: uuid.UUID


class OfferabilityValidationRequest(CamelStrictModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    offering_id: str = Field(min_length=1, max_length=128)
    agent_type: str = Field(min_length=1, max_length=50)
    bundle_tier: str = Field(min_length=1, max_length=20)
    proposed_price_paise: int = Field(gt=0)


class OfferabilityValidationResult(CamelStrictModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    relationship_id: uuid.UUID
    offering_id: str
    outcome: Literal["APPROVED", "REJECTED"]
    cost_floor_paise: int = Field(ge=0)
    minimum_compliant_price_paise: int = Field(ge=0)
    proposed_price_paise: int = Field(gt=0)
    direct_contribution_paise: int
    validation_version: str = Field(min_length=64, max_length=64)
    produced_at: datetime


class OfferingUsageCommand(CamelStrictModel):
    schema_version: Literal["1.0"]
    agent_instance_id: uuid.UUID
    professional_type: str = Field(min_length=1, max_length=64)
    professional_version: str = Field(min_length=1, max_length=64)
    skill_id: str = Field(min_length=1, max_length=100)
    skill_version: str = Field(min_length=1, max_length=64)
    work_item_id: uuid.UUID
    invocation_id: uuid.UUID
    component_id: str = Field(min_length=1, max_length=50)
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_evidence_id: uuid.UUID
    maximum_units: int | None = Field(default=None, gt=0)
    reservation_id: uuid.UUID | None = None
    actual_units: int | None = Field(default=None, ge=0)
    outcome_evidence_id: uuid.UUID | None = None


class OfferingUsageReceipt(CamelStrictModel):
    schema_version: Literal["1.0"] = "1.0"
    reservation_id: uuid.UUID
    state: Literal["RESERVED", "SETTLED", "RELEASED"]
    maximum_units: int
    reserved_raw_paise: int
    reserved_marked_up_paise: int
    catalogue_thread_id: str
    provider_account_id: uuid.UUID
    rate_version: str
    replayed: bool


def _unavailable_projection(relationship_id: uuid.UUID, at: datetime) -> CommercialProjection:
    return CommercialProjection(
        schemaVersion="1.0", relationshipId=relationship_id, projectionVersion="unavailable-1",
        producedAt=at, currencyState="UNAVAILABLE",
        actuals="Actual use unavailable", allowance="Allowance unavailable",
        budget="Budget unavailable", forecast="Forecast unavailable",
        thresholds="Threshold state unavailable",
        commercialConsequences="Consequential commercial commands are blocked",
    )


_LIFECYCLE_KINDS = frozenset({
    "PAUSE_RELATIONSHIP", "RESUME_RELATIONSHIP", "RENEW_RELATIONSHIP", "TERMINATE_RELATIONSHIP",
    "UPGRADE_PACKAGE", "DOWNGRADE_PACKAGE",
})


def _tenant(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None


class CommercialStore:
    """Durable commercial projection and command ledger (C4-09); every state lives in the database."""

    def __init__(
        self,
        open_session: Callable[[], Any],
        *,
        now: Callable[[], datetime] | None = None,
        rates: Any = None,
        packages: Any = None,
        policy: Any = None,
    ) -> None:
        self._open = open_session
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._rates = rates
        self._packages = packages
        self._policy = policy

    def _builder(self, session: Any) -> ProjectionBuilder:
        return ProjectionBuilder(session, now=self._now, packages=self._packages)

    def _lifecycle(self, session: Any) -> LifecycleService:
        return LifecycleService(
            session, rates=self._rates or SqlPackageReferenceData(session), packages=self._packages,
            policy=self._policy, now=self._now,
        )

    async def projection(self, tenant_id: str, relationship_id: uuid.UUID) -> CommercialProjection:
        tenant = _tenant(tenant_id)
        async with self._open() as session:
            repository = CommercialRepository(session)
            body = await self._builder(session).build(tenant, relationship_id)
            if body is not None:
                await repository.save_projection(
                    tenant, relationship_id, body["projectionVersion"], body,
                    datetime.fromisoformat(body["producedAt"]), datetime.fromisoformat(body["validUntil"]),
                )
                await session.commit()
                return CommercialProjection.model_validate(body)
            stored = await repository.latest_projection(tenant, relationship_id)
        if stored is None:
            return _unavailable_projection(relationship_id, self._now())
        projection = CommercialProjection.model_validate(stored.body)
        if stored.valid_until is not None and stored.valid_until < self._now():
            return projection.model_copy(update={"currency_state": "STALE"})
        return projection

    async def set_projection(self, tenant_id: str, projection: CommercialProjection) -> None:
        body = projection.model_dump(by_alias=True, mode="json", exclude_none=True)
        async with self._open() as session:
            await CommercialRepository(session).save_projection(
                _tenant(tenant_id), projection.relationship_id, projection.projection_version, body,
                projection.produced_at, projection.valid_until,
            )
            await session.commit()

    async def submit(self, context: TrustedContext, request: CommercialCommandRequest, key: str) -> CommercialReceipt:
        tenant = _tenant(context.tenant_id)
        relationship_id = uuid.UUID(context.relationship_id)
        digest = request_digest(request.model_dump(by_alias=True, mode="json"))
        binding = binding_key(context.actor_subject, context.tenant_id, context.relationship_id, key)
        payload = request.payload
        async with self._open() as session:
            repository = CommercialRepository(session)
            existing = await repository.find_command(tenant, relationship_id, binding)
            if existing is not None:
                if existing.request_digest != digest:
                    raise HTTPException(status_code=409, detail="WBE_COMMERCIAL_CONFLICT")
                return CommercialReceipt.model_validate(existing.receipt).model_copy(update={"replayed": True})
            command_id = uuid.uuid4()
            accepted = self._now()
            fields: dict[str, Any] = {}
            status = "PENDING"
            current = await self._builder(session).build(tenant, relationship_id)
            if current is None:
                stored = await repository.latest_projection(tenant, relationship_id)
                if stored is not None and (stored.valid_until is None or stored.valid_until >= accepted):
                    current = stored.body
            if payload.command_kind in {"RENEW_RELATIONSHIP", "TERMINATE_RELATIONSHIP"} and (
                await self._policy_absent(session, accepted)
            ):
                status, fields["blocked_reason"] = "BLOCKED", "POLICY_ABSENT"
            elif current is None:
                status = "UNAVAILABLE"
            elif current["currencyState"] != "CURRENT" and payload.command_kind != "TERMINATE_RELATIONSHIP":
                status = "UNAVAILABLE"
            elif (
                payload.command_kind != "TERMINATE_RELATIONSHIP"
                and current["projectionVersion"] != request.expected_projection_version
            ):
                status = "CONFLICT"
            elif payload.command_kind in _LIFECYCLE_KINDS:
                result = await self._lifecycle(session).execute(
                    payload.command_kind, tenant, relationship_id, command_id,
                    component_ids=payload.component_ids, target_package_code=payload.target_package_code,
                )
                status = result.status
                fields = {
                    "effective_at": result.effective_at,
                    "prorated_fee_difference_paise": result.prorated_fee_difference_paise,
                    "refund_fee_paise": result.refund_fee_paise,
                    "blocked_reason": result.blocked_reason,
                }
            receipt = CommercialReceipt(schemaVersion="1.0", commandId=command_id,
                commandKind=payload.command_kind, status=status, acceptedAt=accepted, replayed=False)
            outcome = CommercialOutcome(schemaVersion="1.0", commandId=command_id,
                commandKind=payload.command_kind, status=status, relationshipId=relationship_id,
                resolvedAt=accepted if status in {"COMPLETED", "BLOCKED", "UNAVAILABLE", "CONFLICT", "REJECTED"} else None,
                **fields)
            await repository.insert_command(
                command_id, tenant, relationship_id, binding, digest, payload.command_kind, status,
                receipt.model_dump(by_alias=True, mode="json"),
                outcome.model_dump(by_alias=True, mode="json"),
                accepted, outcome.resolved_at,
            )
            await session.commit()
            return receipt

    async def _policy_absent(self, session: Any, at: datetime) -> bool:
        policy = self._policy or (lambda moment: effective_policy(session, moment))
        return await policy(at) is None

    async def outcome(self, context: TrustedContext, command_id: uuid.UUID) -> CommercialOutcome | None:
        async with self._open() as session:
            stored = await CommercialRepository(session).get_command(
                _tenant(context.tenant_id), uuid.UUID(context.relationship_id), command_id
            )
        return None if stored is None else CommercialOutcome.model_validate(stored.outcome)


router = APIRouter(prefix="/internal/v1/relationships", tags=["Relationship Commercial Projection"])


def get_store(request: Request) -> CommercialStore:
    return request.app.state.relationship_commercial_store


def _digest(value: object | None) -> str:
    payload = b"" if value is None else json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def _authorize(request: Request, route: str, operation: str, relationship_id: uuid.UUID,
    body: object | None = None, idempotency_key: str | None = None) -> DelegatedContext:
    auth: WorkloadAuth | None = getattr(request.app.state, "relationship_workload_auth", None)
    certificate_der = request.scope.get("state", {}).get(PEER_CERTIFICATE_STATE_KEY)
    authorization = request.headers.get("Authorization", "")
    correlation_id = request.headers.get("X-Correlation-ID", "")
    if auth is None or certificate_der is None or not authorization.startswith("Bearer "):
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    peer_identity = extract_peer_identity(x509.load_der_x509_certificate(certificate_der), auth.trust_domain)
    return auth.verifier.verify(
        authorization.removeprefix("Bearer "), peer_identity, auth.audience, request.method,
        route, operation, 1, _digest(body),
        lambda context: context.relationship_id == str(relationship_id)
        and bool(context.tenant_id) and bool(context.actor_subject)
        and context.correlation_id == correlation_id
        and (idempotency_key is None or context.idempotency_key == idempotency_key))


def _rebind_paid_activation(
    context: DelegatedContext,
    relationship_id: uuid.UUID,
    body: PaidActivationBody,
    idempotency_key: str,
) -> None:
    exact = (
        context.effective_role == "EMPLOYER"
        and context.purpose == "activatePaidRelationship"
        and context.subject_reference == str(body.accepted_contract_id)
        and context.command_id == str(body.activation_intent_id)
        and context.idempotency_key == idempotency_key == str(body.correlation_id)
        and context.correlation_id == str(body.correlation_id)
        and context.relationship_id == str(relationship_id)
        and context.expected_versions == {
            "activation_intent": str(body.activation_intent_id),
            "contract": str(body.contract_version),
        }
        and bool(context.tenant_id)
        and bool(context.actor_subject)
    )
    if not exact:
        raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")


def _rebind_offerability_validation(
    context: DelegatedContext,
    relationship_id: uuid.UUID,
    body: OfferabilityValidationRequest,
) -> None:
    exact = (
        context.effective_role == "FOUNDER"
        and context.purpose == "validateRelationshipOfferability"
        and context.subject_reference == body.offering_id
        and context.relationship_id == str(relationship_id)
        and context.expected_versions == {
            "agent_type": body.agent_type,
            "bundle_tier": body.bundle_tier,
            "offering": body.offering_id,
            "proposed_price_paise": str(body.proposed_price_paise),
        }
        and bool(context.tenant_id)
        and bool(context.actor_subject)
    )
    if not exact:
        raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")


def _offering_identity(
    context: DelegatedContext,
    relationship_id: uuid.UUID,
    idempotency_key: str,
    body: OfferingUsageCommand,
) -> AllowanceIdentity:
    if (
        context.effective_role not in {"SYSTEM", "PROFESSIONAL"}
        or context.purpose != "OFFERING_COMPONENT_USAGE"
        or context.relationship_id != str(relationship_id)
        or context.idempotency_key != idempotency_key
        or context.command_id != str(body.invocation_id)
        or context.subject_reference != body.component_id
        or context.expected_versions
        != {
            "component": body.component_id,
            "professional": body.professional_version,
            "skill": body.skill_version,
        }
    ):
        raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")
    return AllowanceIdentity(
        tenant_id=uuid.UUID(context.tenant_id),
        relationship_id=relationship_id,
        agent_instance_id=body.agent_instance_id,
        professional_type=body.professional_type,
        professional_version=body.professional_version,
        skill_id=body.skill_id,
        skill_version=body.skill_version,
        work_item_id=body.work_item_id,
        invocation_id=body.invocation_id,
        component_id=body.component_id,
        idempotency_key=uuid.UUID(idempotency_key),
        request_digest=body.request_digest,
        owner_evidence_id=body.owner_evidence_id,
    )


def _usage_response(receipt: object) -> OfferingUsageReceipt:
    return OfferingUsageReceipt.model_validate(
        {"schemaVersion": "1.0", **receipt.__dict__}
    )


async def _offering_command(
    action: Literal["reserve", "settle", "release", "reconcile"],
    relationship_id: uuid.UUID,
    body: OfferingUsageCommand,
    request: Request,
    idempotency_key: str,
) -> OfferingUsageReceipt:
    route = f"/internal/v1/relationships/{{relationshipId}}/offering-usage/{action}"
    operation = f"{action}OfferingComponentUsage"
    payload = body.model_dump(by_alias=True, mode="json")
    try:
        context = _authorize(
            request, route, operation, relationship_id, payload, idempotency_key
        )
        identity = _offering_identity(context, relationship_id, idempotency_key, body)
        service = OfferingAllowanceService(get_session_factory())
        if action == "reserve":
            if (
                body.maximum_units is None
                or body.reservation_id is not None
                or body.actual_units is not None
                or body.outcome_evidence_id is not None
            ):
                raise AllowanceConflict("ALLOWANCE_RESERVE_SHAPE_INVALID")
            receipt = await service.reserve(identity, body.maximum_units)
        elif action == "settle":
            if (
                body.reservation_id is None
                or body.actual_units is None
                or body.outcome_evidence_id is None
                or body.maximum_units is not None
            ):
                raise AllowanceConflict("ALLOWANCE_SETTLEMENT_SHAPE_INVALID")
            receipt = await service.settle(
                identity, body.reservation_id, body.actual_units, body.outcome_evidence_id
            )
        elif action == "release":
            if (
                body.reservation_id is None
                or body.actual_units is not None
                or body.outcome_evidence_id is None
                or body.maximum_units is not None
            ):
                raise AllowanceConflict("ALLOWANCE_RELEASE_SHAPE_INVALID")
            receipt = await service.release(
                identity, body.reservation_id, body.outcome_evidence_id
            )
        else:
            if (
                body.maximum_units is not None
                or body.actual_units is not None
                or body.outcome_evidence_id is not None
            ):
                raise AllowanceConflict("ALLOWANCE_RECONCILE_SHAPE_INVALID")
            receipt = await service.reconcile(identity)
            if receipt is None:
                raise HTTPException(status_code=404, detail="ALLOWANCE_RESERVATION_UNKNOWN")
        return _usage_response(receipt)
    except ServiceAuthError as exc:
        logger.warning(
            "service_auth decision=deny target=billing-engine operation=%s reason_class=%s",
            operation,
            exc.code,
        )
        raise HTTPException(status_code=401, detail="WBE_OFFERING_USAGE_UNAUTHORIZED") from None
    except AllowanceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except AllowanceDenied as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post(
    "/{relationship_id}/offering-usage/reserve",
    response_model=OfferingUsageReceipt,
    response_model_by_alias=True,
)
async def reserve_offering_usage(
    relationship_id: uuid.UUID,
    body: OfferingUsageCommand,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OfferingUsageReceipt:
    return await _offering_command("reserve", relationship_id, body, request, idempotency_key)


@router.post(
    "/{relationship_id}/offering-usage/settle",
    response_model=OfferingUsageReceipt,
    response_model_by_alias=True,
)
async def settle_offering_usage(
    relationship_id: uuid.UUID,
    body: OfferingUsageCommand,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OfferingUsageReceipt:
    return await _offering_command("settle", relationship_id, body, request, idempotency_key)


@router.post(
    "/{relationship_id}/offering-usage/release",
    response_model=OfferingUsageReceipt,
    response_model_by_alias=True,
)
async def release_offering_usage(
    relationship_id: uuid.UUID,
    body: OfferingUsageCommand,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OfferingUsageReceipt:
    return await _offering_command("release", relationship_id, body, request, idempotency_key)


@router.post(
    "/{relationship_id}/offering-usage/reconcile",
    response_model=OfferingUsageReceipt,
    response_model_by_alias=True,
)
async def reconcile_offering_usage(
    relationship_id: uuid.UUID,
    body: OfferingUsageCommand,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OfferingUsageReceipt:
    return await _offering_command("reconcile", relationship_id, body, request, idempotency_key)


@router.get("/{relationship_id}/commercial-projection", response_model=CommercialProjection, response_model_by_alias=True)
async def get_projection(
    relationship_id: uuid.UUID, request: Request, store: CommercialStore = Depends(get_store)
) -> CommercialProjection:
    try:
        context = _authorize(request, "/internal/v1/relationships/{relationshipId}/commercial-projection",
            "getRelationshipCommercialProjection", relationship_id)
        logger.info("service_auth decision=allow target=billing-engine operation=projection policy_version=1.0")
        return await store.projection(context.tenant_id, relationship_id)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=projection reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None


@router.post("/{relationship_id}/paid-activation")
async def activate_paid_relationship(
    relationship_id: uuid.UUID,
    body: PaidActivationBody,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> dict[str, str]:
    route = "/internal/v1/relationships/{relationshipId}/paid-activation"
    operation = "activatePaidRelationship"
    payload = body.model_dump(mode="json")
    try:
        context = _authorize(request, route, operation, relationship_id, payload, idempotency_key)
        _rebind_paid_activation(context, relationship_id, body, idempotency_key)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=paid_activation reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_PAID_ACTIVATION_UNAUTHORIZED") from None

    session_factory = get_session_factory()
    async with session_factory() as db:
        redis_client = aioredis.from_url(Settings().REDIS_URL, decode_responses=True)
        try:
            outcome_reference = body.commercial_outcome_reference or body.payment_reference
            evidence_id = body.commercial_evidence_id or body.payment_evidence_id
            if outcome_reference is None or evidence_id is None:
                raise HTTPException(status_code=422, detail="COMMERCIAL_OUTCOME_MATERIAL_REQUIRED")
            wallet = WalletService(db=db, redis_client=redis_client)
            if body.commercial_outcome_kind == "ZERO_PRICE_SATISFIED":
                result = await ZeroPriceActivationService(db, wallet).activate(ZeroPriceActivationRequest(
                    tenant_id=uuid.UUID(context.tenant_id),
                    relationship_id=relationship_id,
                    activation_intent_id=body.activation_intent_id,
                    accepted_contract_id=body.accepted_contract_id,
                    contract_version=body.contract_version,
                    contract_acceptance_id=body.contract_acceptance_id,
                    commercial_outcome_reference=outcome_reference,
                    commercial_evidence_id=evidence_id,
                    correlation_id=body.correlation_id,
                ))
            else:
                result = await PaidActivationService(db, wallet).activate(PaidActivationRequest(
                    tenant_id=uuid.UUID(context.tenant_id),
                    relationship_id=relationship_id,
                    activation_intent_id=body.activation_intent_id,
                    accepted_contract_id=body.accepted_contract_id,
                    contract_version=body.contract_version,
                    contract_acceptance_id=body.contract_acceptance_id,
                    payment_reference=outcome_reference,
                    payment_evidence_id=evidence_id,
                    correlation_id=body.correlation_id,
                ))
        finally:
            await redis_client.aclose()
    return {"subscription_id": str(result.subscription_id), "status": result.status}


@router.post(
    "/{relationship_id}/offerability-validation",
)
async def validate_relationship_offerability(
    relationship_id: uuid.UUID,
    body: dict[str, object],
    request: Request,
) -> dict[str, object]:
    route = "/internal/v1/relationships/{relationshipId}/offerability-validation"
    operation = "validateRelationshipOfferability"
    try:
        validated_body = OfferabilityValidationRequest.model_validate(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="WBE_OFFERABILITY_REQUEST_INVALID") from None
    payload = validated_body.model_dump(by_alias=True, mode="json")
    try:
        context = _authorize(request, route, operation, relationship_id, payload)
        _rebind_offerability_validation(context, relationship_id, validated_body)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=offerability reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_OFFERABILITY_UNAUTHORIZED") from None

    session_factory = get_session_factory()
    try:
        async with session_factory() as db:
            validation = await BundleEngine(db).validate_price(
                validated_body.agent_type,
                validated_body.bundle_tier,
                validated_body.proposed_price_paise,
            )
    except ValueError:
        logger.warning("offerability_validation state=unavailable relationship_bound=true")
        raise HTTPException(status_code=503, detail="WBE_OFFERABILITY_UNAVAILABLE") from None

    version_source = ":".join((
        validated_body.agent_type,
        validated_body.bundle_tier,
        str(validation.cost_floor_paise),
        str(validation.minimum_compliant_price_paise),
        str(validation.proposed_price_paise),
        validation.outcome,
    ))
    result = OfferabilityValidationResult(
        schemaVersion="1.0",
        relationshipId=relationship_id,
        offeringId=validated_body.offering_id,
        outcome=validation.outcome,
        costFloorPaise=validation.cost_floor_paise,
        minimumCompliantPricePaise=validation.minimum_compliant_price_paise,
        proposedPricePaise=validation.proposed_price_paise,
        directContributionPaise=validation.proposed_price_paise - validation.cost_floor_paise,
        validationVersion=hashlib.sha256(version_source.encode()).hexdigest(),
        producedAt=datetime.now(timezone.utc),
    )
    return result.model_dump(by_alias=True, mode="json")


@router.post("/{relationship_id}/commercial-commands", response_model=CommercialReceipt, response_model_by_alias=True, status_code=202)
async def submit_command(relationship_id: uuid.UUID, command: CommercialCommandRequest,
    request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    store: CommercialStore = Depends(get_store)) -> CommercialReceipt:
    body = command.model_dump(by_alias=True, mode="json")
    try:
        context = _authorize(request, "/internal/v1/relationships/{relationshipId}/commercial-commands",
            "submitRelationshipCommercialCommand", relationship_id, body, idempotency_key)
        return await store.submit(context, command, idempotency_key)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=command reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None


@router.get("/{relationship_id}/commercial-commands/{command_id}", response_model=CommercialOutcome, response_model_by_alias=True)
async def get_command(relationship_id: uuid.UUID, command_id: uuid.UUID,
    request: Request, store: CommercialStore = Depends(get_store)) -> CommercialOutcome:
    try:
        context = _authorize(request, "/internal/v1/relationships/{relationshipId}/commercial-commands/{commandId}",
            "getRelationshipCommercialCommand", relationship_id)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=reconciliation reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None
    outcome = await store.outcome(context, command_id)
    if outcome is None:
        raise HTTPException(status_code=404, detail="WBE_COMMERCIAL_NOT_ACCESSIBLE")
    return outcome


class ComponentUnitCommand(CamelStrictModel):
    """One component-unit operation; ``action`` selects which of the fields below it needs."""

    schema_version: Literal["1.0"]
    action: Literal["CONSUME", "SELECT", "SWAP", "DESELECT", "ACCESS", "CLOSE"]
    component_id: str = Field(min_length=1, max_length=100)
    completion_evidence_id: uuid.UUID | None = None
    outcome: Literal["COMPLETED", "FAILED", "CANCELLED"] | None = None
    item_ref: str | None = Field(default=None, min_length=1, max_length=200)
    previous_item_ref: str | None = Field(default=None, min_length=1, max_length=200)
    connection_proof_id: uuid.UUID | None = None
    session_ref: str | None = Field(default=None, min_length=1, max_length=200)


class ComponentUnitResult(CamelStrictModel):
    schema_version: Literal["1.0"] = "1.0"
    component_id: str
    kind: str
    entry_id: uuid.UUID
    quantity: int
    used: int
    remaining: int
    released: int
    replayed: bool


_COMPONENT_REFUSAL_STATUS = {
    "COMPONENT_UNKNOWN": 404,
    "COMPONENT_ITEM_UNKNOWN": 404,
    "COMPONENT_IDEMPOTENCY_CONFLICT": 409,
    "COMPONENT_KIND_MISMATCH": 409,
}


def _component_unit_call(service: ComponentUnitService, tenant: uuid.UUID, relationship_id: uuid.UUID,
    body: ComponentUnitCommand, key: uuid.UUID):
    component = body.component_id
    if body.action == "CONSUME" and body.completion_evidence_id is not None:
        return service.consume(tenant, relationship_id, component, body.completion_evidence_id, key,
            outcome=body.outcome or "COMPLETED")
    if body.action == "SELECT" and body.item_ref:
        return service.select(tenant, relationship_id, component, body.item_ref, body.connection_proof_id, key)
    if body.action == "SWAP" and body.item_ref and body.previous_item_ref:
        return service.swap(tenant, relationship_id, component, body.previous_item_ref, body.item_ref,
            body.connection_proof_id, key)
    if body.action == "DESELECT" and body.item_ref:
        return service.deselect(tenant, relationship_id, component, body.item_ref, key)
    if body.action == "ACCESS":
        return service.record_access(tenant, relationship_id, component, key)
    if body.action == "CLOSE" and body.session_ref:
        return service.close(tenant, relationship_id, component, body.session_ref, key)
    return None


def _rebind_component_unit(
    context: DelegatedContext, relationship_id: uuid.UUID, idempotency_key: str, body: ComponentUnitCommand
) -> None:
    exact = (
        context.effective_role in {"SYSTEM", "EMPLOYER"}
        and context.purpose == "COMPONENT_UNIT_USAGE"
        and context.relationship_id == str(relationship_id)
        and context.idempotency_key == idempotency_key
        and context.subject_reference == body.component_id
    )
    if not exact:
        raise ServiceAuthError("SERVICE_AUTHORIZATION_DENIED")


@router.post("/{relationship_id}/component-units/consume", response_model=ComponentUnitResult,
    response_model_by_alias=True)
async def apply_component_unit(
    relationship_id: uuid.UUID,
    body: ComponentUnitCommand,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ComponentUnitResult:
    """Counts or records one component-unit operation of the relationship (C4-08)."""
    payload = body.model_dump(by_alias=True, mode="json", exclude_none=True)
    try:
        context = _authorize(
            request, "/internal/v1/relationships/{relationshipId}/component-units/consume",
            "applyRelationshipComponentUnit", relationship_id, payload, idempotency_key)
        _rebind_component_unit(context, relationship_id, idempotency_key, body)
        key = uuid.UUID(idempotency_key)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=component_unit reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMPONENT_UNIT_UNAUTHORIZED") from None
    except ValueError:
        raise HTTPException(status_code=400, detail="WBE_COMPONENT_UNIT_KEY_INVALID") from None
    tenant = _tenant(context.tenant_id)
    async with get_session_factory()() as session:
        service = ComponentUnitService(session, swaps_per_period=await _swaps_per_period(session))
        call = _component_unit_call(service, tenant, relationship_id, body, key)
        if call is None:
            raise HTTPException(status_code=400, detail="WBE_COMPONENT_UNIT_REQUEST_INVALID")
        try:
            receipt = await call
            await session.commit()
        except ComponentUnitError as refusal:
            await session.rollback()
            raise HTTPException(status_code=_COMPONENT_REFUSAL_STATUS.get(refusal.code, 422), detail=refusal.code) from None
    return ComponentUnitResult.model_validate({
        "schemaVersion": "1.0", "componentId": receipt.component_id, "kind": receipt.kind,
        "entryId": receipt.entry_id, "quantity": receipt.quantity, "used": receipt.used,
        "remaining": receipt.remaining, "released": receipt.released, "replayed": receipt.replayed,
    })


async def _swaps_per_period(session: Any) -> int:
    """The selection swaps a period allows come from the POLICY (selectedSwapsPerPeriod); none means none."""
    policy = await effective_policy(session, datetime.now(timezone.utc))
    extra = (policy.model_extra or {}) if policy is not None else {}
    value = extra.get("selectedSwapsPerPeriod", 0)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def configure_relationship_workspace(application: FastAPI) -> None:
    application.state.relationship_commercial_store = CommercialStore(lambda: get_session_factory()())
    credentials = os.getenv("WAOOAW_WORKLOAD_CREDENTIALS")
    application.state.relationship_workload_auth = WorkloadAuth.from_credentials(Path(credentials)) if credentials else None
"""WBE-owned WC-034 F4 commercial projection and command reconciliation."""

# Implements: wbe-relationship-workspace.openapi.yaml 1.0.0
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-088, C-089, C-090, C-091

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from pathlib import Path
from typing import Annotated, Literal, Protocol

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

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


class CommercialPayload(StrictModel):
    command_kind: Literal[
        "CHANGE_BUDGET_CEILING", "CHANGE_PACING", "REQUEST_ALLOWANCE_ADDITION",
        "PAUSE_RELATIONSHIP", "RESUME_RELATIONSHIP", "RENEW_RELATIONSHIP", "TERMINATE_RELATIONSHIP",
    ] = Field(alias="commandKind")
    amount_inr_paise: int | None = Field(default=None, alias="amountInrPaise", ge=0)
    pacing_choice: str | None = Field(default=None, alias="pacingChoice", min_length=1, max_length=64)


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


@dataclass(frozen=True)
class StoredCommand:
    tenant_id: str
    relationship_id: str
    digest: str
    receipt: CommercialReceipt
    outcome: CommercialOutcome


class CommercialStore:
    def __init__(self) -> None:
        self._projections: dict[tuple[str, uuid.UUID], CommercialProjection] = {}
        self._commands: dict[uuid.UUID, StoredCommand] = {}
        self._idempotency: dict[tuple[str, ...], uuid.UUID] = {}
        self._lock = Lock()

    def projection(self, tenant_id: str, relationship_id: uuid.UUID) -> CommercialProjection:
        with self._lock:
            current = self._projections.get((tenant_id, relationship_id))
        return current or CommercialProjection(
            schemaVersion="1.0", relationshipId=relationship_id, projectionVersion="unavailable-1",
            producedAt=datetime.now(timezone.utc), currencyState="UNAVAILABLE",
            actuals="Actual use unavailable", allowance="Allowance unavailable",
            budget="Budget unavailable", forecast="Forecast unavailable",
            thresholds="Threshold state unavailable",
            commercialConsequences="Consequential commercial commands are blocked",
        )

    def set_projection(self, tenant_id: str, projection: CommercialProjection) -> None:
        with self._lock:
            self._projections[(tenant_id, projection.relationship_id)] = projection

    def submit(self, context: TrustedContext, request: CommercialCommandRequest, key: str) -> CommercialReceipt:
        body = request.model_dump(by_alias=True, mode="json")
        digest = hashlib.sha256(json.dumps(body, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
        binding = (context.actor_subject, context.tenant_id, context.relationship_id, key)
        relationship_id = uuid.UUID(context.relationship_id)
        with self._lock:
            existing_id = self._idempotency.get(binding)
            if existing_id:
                existing = self._commands[existing_id]
                if existing.digest != digest:
                    raise HTTPException(status_code=409, detail="WBE_COMMERCIAL_CONFLICT")
                return existing.receipt.model_copy(update={"replayed": True})
            projection = self._projections.get((context.tenant_id, relationship_id))
            if request.payload.command_kind in {"RENEW_RELATIONSHIP", "TERMINATE_RELATIONSHIP"}:
                status = "BLOCKED"
            elif projection is None or projection.currency_state != "CURRENT":
                status = "UNAVAILABLE"
            elif projection.projection_version != request.expected_projection_version:
                status = "CONFLICT"
            else:
                status = "PENDING"
            command_id = uuid.uuid4()
            accepted = datetime.now(timezone.utc)
            receipt = CommercialReceipt(schemaVersion="1.0", commandId=command_id,
                commandKind=request.payload.command_kind, status=status, acceptedAt=accepted, replayed=False)
            outcome = CommercialOutcome(schemaVersion="1.0", commandId=command_id,
                commandKind=request.payload.command_kind, status=status, relationshipId=relationship_id,
                resolvedAt=accepted if status in {"BLOCKED", "UNAVAILABLE", "CONFLICT"} else None)
            self._idempotency[binding] = command_id
            self._commands[command_id] = StoredCommand(context.tenant_id, context.relationship_id, digest, receipt, outcome)
            return receipt

    def outcome(self, context: TrustedContext, command_id: uuid.UUID) -> CommercialOutcome | None:
        with self._lock:
            command = self._commands.get(command_id)
        if command is None or (command.tenant_id, command.relationship_id) != (context.tenant_id, context.relationship_id):
            return None
        return command.outcome


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


@router.get("/{relationship_id}/commercial-projection", response_model=CommercialProjection, response_model_by_alias=True)
def get_projection(
    relationship_id: uuid.UUID, request: Request, store: CommercialStore = Depends(get_store)
) -> CommercialProjection:
    try:
        context = _authorize(request, "/internal/v1/relationships/{relationshipId}/commercial-projection",
            "getRelationshipCommercialProjection", relationship_id)
        logger.info("service_auth decision=allow target=billing-engine operation=projection policy_version=1.0")
        return store.projection(context.tenant_id, relationship_id)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=projection reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None


@router.post("/{relationship_id}/commercial-commands", response_model=CommercialReceipt, response_model_by_alias=True, status_code=202)
def submit_command(relationship_id: uuid.UUID, command: CommercialCommandRequest,
    request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    store: CommercialStore = Depends(get_store)) -> CommercialReceipt:
    body = command.model_dump(by_alias=True, mode="json")
    try:
        context = _authorize(request, "/internal/v1/relationships/{relationshipId}/commercial-commands",
            "submitRelationshipCommercialCommand", relationship_id, body, idempotency_key)
        return store.submit(context, command, idempotency_key)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=command reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None


@router.get("/{relationship_id}/commercial-commands/{command_id}", response_model=CommercialOutcome, response_model_by_alias=True)
def get_command(relationship_id: uuid.UUID, command_id: uuid.UUID,
    request: Request, store: CommercialStore = Depends(get_store)) -> CommercialOutcome:
    try:
        context = _authorize(request, "/internal/v1/relationships/{relationshipId}/commercial-commands/{commandId}",
            "getRelationshipCommercialCommand", relationship_id)
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=billing-engine operation=reconciliation reason_class=%s", exc.code)
        raise HTTPException(status_code=401, detail="WBE_COMMERCIAL_UNAUTHORIZED") from None
    outcome = store.outcome(context, command_id)
    if outcome is None:
        raise HTTPException(status_code=404, detail="WBE_COMMERCIAL_NOT_ACCESSIBLE")
    return outcome


def configure_relationship_workspace(application: FastAPI) -> None:
    application.state.relationship_commercial_store = CommercialStore()
    credentials = os.getenv("WAOOAW_WORKLOAD_CREDENTIALS")
    application.state.relationship_workload_auth = WorkloadAuth.from_credentials(Path(credentials)) if credentials else None
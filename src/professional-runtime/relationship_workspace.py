"""PR-owned WC-034 F4 relationship execution projection and controls."""

# Implements: professional-runtime.openapi.yaml 1.2.0 relationship workspace operations
# constitutional_basis: C-001, C-023, C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, FastAPI, Header, Request
from fastapi.responses import JSONResponse
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


SCHEMA_VERSION: Literal["1.0"] = "1.0"
ControlStatus = Literal[
    "COMPLETED",
    "PENDING",
    "PARTIAL",
    "UNKNOWN",
    "REJECTED",
    "CONFLICT",
    "BLOCKED",
]
TARGET_NAME = "professional-runtime"
logger = logging.getLogger(__name__)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExecutionProjection(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    projection_version: str = Field(alias="projectionVersion", min_length=1, max_length=64)
    state: Literal["CURRENT", "STALE", "UNKNOWN", "UNAVAILABLE", "BLOCKED"]
    produced_at: datetime = Field(alias="producedAt")
    next_review_at: datetime | None = Field(default=None, alias="nextReviewAt")


class PauseWorkPayload(StrictModel):
    control_kind: Literal["PAUSE_WORK"] = Field(alias="controlKind")
    work_item_id: uuid.UUID = Field(alias="workItemId")
    reason: str = Field(min_length=1, max_length=240)


class ResumeWorkPayload(StrictModel):
    control_kind: Literal["RESUME_WORK"] = Field(alias="controlKind")
    work_item_id: uuid.UUID = Field(alias="workItemId")


class ProvideWorkInputPayload(StrictModel):
    control_kind: Literal["PROVIDE_WORK_INPUT"] = Field(alias="controlKind")
    work_item_id: uuid.UUID = Field(alias="workItemId")
    input_text: str = Field(alias="inputText", min_length=1, max_length=2000)


ControlPayload = Annotated[
    PauseWorkPayload | ResumeWorkPayload | ProvideWorkInputPayload,
    Field(discriminator="control_kind"),
]


class ExecutionControlRequest(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    expected_projection_version: str = Field(alias="expectedProjectionVersion", min_length=1, max_length=64)
    payload: ControlPayload


class ExecutionControlReceipt(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    control_id: uuid.UUID = Field(alias="controlId")
    control_kind: Literal["PAUSE_WORK", "RESUME_WORK", "PROVIDE_WORK_INPUT"] = Field(alias="controlKind")
    status: ControlStatus
    accepted_at: datetime = Field(alias="acceptedAt")
    replayed: bool


class ExecutionControlOutcome(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    control_id: uuid.UUID = Field(alias="controlId")
    control_kind: Literal["PAUSE_WORK", "RESUME_WORK", "PROVIDE_WORK_INPUT"] = Field(alias="controlKind")
    status: ControlStatus
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")


class RelationshipTrialStartRequest(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    trial_id: uuid.UUID = Field(alias="trialId")
    starts_at: datetime = Field(alias="startsAt")
    expires_at: datetime = Field(alias="expiresAt")
    inference_tier: Literal["LOCAL"] = Field(alias="inferenceTier")
    paid_provider_fallback: Literal[False] = Field(alias="paidProviderFallback")
    credential_use_allowed: Literal[False] = Field(alias="credentialUseAllowed")
    external_actions_allowed: Literal[False] = Field(alias="externalActionsAllowed")


class RelationshipTrialStartResult(StrictModel):
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    relationship_id: uuid.UUID = Field(alias="relationshipId")
    trial_id: uuid.UUID = Field(alias="trialId")
    workflow_state: Literal["TRIAL_DEMONSTRATING"] = Field(alias="workflowState")
    expires_at: datetime = Field(alias="expiresAt")
    replayed: bool


@dataclass(frozen=True)
class StoredControl:
    binding: tuple[str, ...]
    request_digest: str
    receipt: ExecutionControlReceipt
    outcome: ExecutionControlOutcome


class RelationshipExecutionStore:
    """Thread-safe owner state with explicit unavailable defaults and replay semantics."""

    def __init__(self) -> None:
        self._projections: dict[tuple[str, uuid.UUID], ExecutionProjection] = {}
        self._controls: dict[uuid.UUID, StoredControl] = {}
        self._idempotency: dict[tuple[str, ...], uuid.UUID] = {}
        self._trials: dict[tuple[str, uuid.UUID], RelationshipTrialStartResult] = {}
        self._lock = Lock()

    def projection(self, tenant_id: str, relationship_id: uuid.UUID) -> ExecutionProjection:
        with self._lock:
            projection = self._projections.get((tenant_id, relationship_id))
        return projection or ExecutionProjection(
            schemaVersion=SCHEMA_VERSION,
            relationshipId=relationship_id,
            projectionVersion="unavailable-1",
            state="UNAVAILABLE",
            producedAt=datetime.now(timezone.utc),
        )

    def set_projection(self, tenant_id: str, projection: ExecutionProjection) -> None:
        with self._lock:
            self._projections[(tenant_id, projection.relationship_id)] = projection

    def submit(
        self,
        context: DelegatedContext,
        request: ExecutionControlRequest,
        idempotency_key: str,
        request_digest: str,
    ) -> ExecutionControlReceipt:
        binding = (
            context.actor_subject,
            context.tenant_id,
            context.relationship_id,
            context.operation,
            idempotency_key,
        )
        relationship_id = uuid.UUID(context.relationship_id)
        with self._lock:
            existing_id = self._idempotency.get(binding)
            if existing_id is not None:
                existing = self._controls[existing_id]
                if existing.request_digest != request_digest:
                    raise ServiceAuthError("EXECUTION_IDEMPOTENCY_CONFLICT")
                return existing.receipt.model_copy(update={"replayed": True})

            projection = self._projections.get((context.tenant_id, relationship_id))
            status: ControlStatus
            if projection is None or projection.state != "CURRENT":
                status = "BLOCKED"
            elif projection.projection_version != request.expected_projection_version:
                status = "CONFLICT"
            else:
                status = "PENDING"
            control_id = uuid.uuid4()
            accepted_at = datetime.now(timezone.utc)
            receipt = ExecutionControlReceipt(
                schemaVersion=SCHEMA_VERSION,
                controlId=control_id,
                controlKind=request.payload.control_kind,
                status=status,
                acceptedAt=accepted_at,
                replayed=False,
            )
            outcome = ExecutionControlOutcome(
                schemaVersion=SCHEMA_VERSION,
                controlId=control_id,
                controlKind=request.payload.control_kind,
                status=status,
                relationshipId=relationship_id,
                resolvedAt=accepted_at if status in {"BLOCKED", "CONFLICT"} else None,
            )
            self._idempotency[binding] = control_id
            self._controls[control_id] = StoredControl(binding, request_digest, receipt, outcome)
            return receipt

    def outcome(self, context: DelegatedContext, control_id: uuid.UUID) -> ExecutionControlOutcome | None:
        with self._lock:
            control = self._controls.get(control_id)
        if control is None or control.binding[1:3] != (context.tenant_id, context.relationship_id):
            return None
        return control.outcome

    def start_trial(
        self,
        context: DelegatedContext,
        relationship_id: uuid.UUID,
        trial: RelationshipTrialStartRequest,
    ) -> RelationshipTrialStartResult:
        if trial.expires_at - trial.starts_at != timedelta(days=14):
            raise ServiceAuthError("TRIAL_DURATION_INVALID")
        key = (context.tenant_id, relationship_id)
        with self._lock:
            existing = self._trials.get(key)
            if existing is not None:
                if existing.trial_id != trial.trial_id or existing.expires_at != trial.expires_at:
                    raise ServiceAuthError("TRIAL_BINDING_CONFLICT")
                return existing.model_copy(update={"replayed": True})
            result = RelationshipTrialStartResult(
                schemaVersion=SCHEMA_VERSION,
                relationshipId=relationship_id,
                trialId=trial.trial_id,
                workflowState="TRIAL_DEMONSTRATING",
                expiresAt=trial.expires_at,
                replayed=False,
            )
            self._trials[key] = result
            self._projections[key] = ExecutionProjection(
                schemaVersion=SCHEMA_VERSION,
                relationshipId=relationship_id,
                projectionVersion=f"trial-{trial.trial_id}",
                state="CURRENT",
                producedAt=datetime.now(timezone.utc),
                nextReviewAt=trial.expires_at,
            )
            return result


class WorkloadAuth:
    def __init__(self, verifier: DelegatedContextVerifier, trust_domain: str, audience: str) -> None:
        self.verifier = verifier
        self.trust_domain = trust_domain
        self.audience = audience

    @classmethod
    def from_credentials(cls, credentials: Path) -> WorkloadAuth:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        target = manifest["workloads"][TARGET_NAME]
        bp = manifest["workloads"]["business-platform"]
        bp_certificate = x509.load_pem_x509_certificate(
            (credentials / "workloads" / "business-platform" / "delegation-cert.pem").read_bytes()
        )
        public_key = bp_certificate.public_key()
        if not isinstance(public_key, ec.EllipticCurvePublicKey):
            raise ValueError("BP delegation certificate must contain an ECDSA public key")
        grants = frozenset(
            RouteGrant(
                caller_uri=manifest["workloads"][grant["caller"]]["identity_uri"],
                target_audience=manifest["workloads"][grant["target"]]["audience"],
                method=grant["method"],
                route=grant["route"],
                operation=grant["operation"],
                contract_major=int(grant["contract_major"]),
            )
            for grant in manifest["route_grants"]
            if grant["target"] == TARGET_NAME
        )
        keys = {(bp["identity_uri"], bp["delegation_key_id"]): public_key}
        return cls(DelegatedContextVerifier(grants, keys, ReplayStore()), manifest["trust_domain"], target["audience"])


def _canonical_digest(value: object | None) -> str:
    payload = b"" if value is None else json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _problem(code: str, status: int, correlation_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://waooaw.com/problems/{code.lower().replace('_', '-')}",
            "title": "The requested execution operation could not be completed",
            "status": status,
            "code": code,
            "correlationId": correlation_id,
        },
    )


async def _authorize(
    request: Request,
    route: str,
    operation: str,
    relationship_id: uuid.UUID,
    body: object | None = None,
    idempotency_key: str | None = None,
    expected_tenant_id: str | None = None,
) -> DelegatedContext:
    correlation_id = request.headers.get("X-Correlation-ID", "00000000-0000-0000-0000-000000000000")
    auth: WorkloadAuth | None = getattr(request.app.state, "relationship_workload_auth", None)
    certificate_der = request.scope.get("state", {}).get(PEER_CERTIFICATE_STATE_KEY)
    authorization = request.headers.get("Authorization", "")
    if auth is None or certificate_der is None or not authorization.startswith("Bearer "):
        raise ServiceAuthError("SERVICE_AUTHENTICATION_FAILED")
    certificate = x509.load_der_x509_certificate(certificate_der)
    peer_identity = extract_peer_identity(certificate, auth.trust_domain)
    digest = _canonical_digest(body)
    return auth.verifier.verify(
        authorization.removeprefix("Bearer "),
        peer_identity,
        auth.audience,
        request.method,
        route,
        operation,
        1,
        digest,
        lambda context: (
            context.relationship_id == str(relationship_id)
            and bool(context.tenant_id)
            and (expected_tenant_id is None or context.tenant_id == expected_tenant_id)
            and bool(context.actor_subject)
            and context.correlation_id == correlation_id
            and (idempotency_key is None or context.idempotency_key == idempotency_key)
        ),
    )


async def authorize_paas_session_start(
    request: Request,
    relationship_id: uuid.UUID,
    body: object,
    tenant_id: str,
) -> DelegatedContext:
    return await _authorize(
        request,
        "/api/v1/paas/sessions",
        "startPAASSession",
        relationship_id,
        body,
        expected_tenant_id=tenant_id,
    )


router = APIRouter(prefix="/api/v1/internal/relationships", tags=["Internal"])


@router.get("/{relationship_id}/workspace-execution", response_model=ExecutionProjection, response_model_by_alias=True)
async def get_relationship_execution_projection(
    relationship_id: uuid.UUID,
    request: Request,
) -> ExecutionProjection | JSONResponse:
    try:
        context = await _authorize(
            request,
            "/api/v1/internal/relationships/{relationshipId}/workspace-execution",
            "getRelationshipExecutionProjection",
            relationship_id,
        )
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=professional-runtime operation=projection reason_class=%s", exc.code)
        return _problem(exc.code, 401, request.headers.get("X-Correlation-ID", str(uuid.uuid4())))
    logger.info("service_auth decision=allow target=professional-runtime operation=projection policy_version=1.0")
    store: RelationshipExecutionStore = request.app.state.relationship_execution_store
    return store.projection(context.tenant_id, relationship_id)


@router.post(
    "/{relationship_id}/evaluation-trial",
    response_model=RelationshipTrialStartResult,
    response_model_by_alias=True,
)
async def start_relationship_trial(
    relationship_id: uuid.UUID,
    trial: RelationshipTrialStartRequest,
    request: Request,
) -> RelationshipTrialStartResult | JSONResponse:
    body = trial.model_dump(by_alias=True, mode="json")
    try:
        context = await _authorize(
            request,
            "/api/v1/internal/relationships/{relationshipId}/evaluation-trial",
            "startRelationshipTrial",
            relationship_id,
            body,
        )
        store: RelationshipExecutionStore = request.app.state.relationship_execution_store
        return store.start_trial(context, relationship_id, trial)
    except ServiceAuthError as exc:
        status = 409 if exc.code == "TRIAL_BINDING_CONFLICT" else 422 if exc.code == "TRIAL_DURATION_INVALID" else 401
        return _problem(exc.code, status, request.headers.get("X-Correlation-ID", str(uuid.uuid4())))


@router.post("/{relationship_id}/workspace-controls", response_model=ExecutionControlReceipt, response_model_by_alias=True)
async def submit_relationship_execution_control(
    relationship_id: uuid.UUID,
    control: ExecutionControlRequest,
    request: Request,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> ExecutionControlReceipt | JSONResponse:
    body = control.model_dump(by_alias=True, mode="json")
    try:
        context = await _authorize(
            request,
            "/api/v1/internal/relationships/{relationshipId}/workspace-controls",
            "submitRelationshipExecutionControl",
            relationship_id,
            body,
            idempotency_key,
        )
        store: RelationshipExecutionStore = request.app.state.relationship_execution_store
        return store.submit(context, control, idempotency_key, _canonical_digest(body))
    except ServiceAuthError as exc:
        logger.warning("service_auth decision=deny target=professional-runtime operation=control reason_class=%s", exc.code)
        status = 409 if exc.code == "EXECUTION_IDEMPOTENCY_CONFLICT" else 401
        return _problem(exc.code, status, request.headers.get("X-Correlation-ID", str(uuid.uuid4())))


@router.get(
    "/{relationship_id}/workspace-controls/{control_id}",
    response_model=ExecutionControlOutcome,
    response_model_by_alias=True,
)
async def get_relationship_execution_control(
    relationship_id: uuid.UUID,
    control_id: uuid.UUID,
    request: Request,
) -> ExecutionControlOutcome | JSONResponse:
    try:
        context = await _authorize(
            request,
            "/api/v1/internal/relationships/{relationshipId}/workspace-controls/{controlId}",
            "getRelationshipExecutionControl",
            relationship_id,
        )
    except ServiceAuthError as exc:
        logger.warning(
            "service_auth decision=deny target=professional-runtime operation=reconciliation reason_class=%s", exc.code
        )
        return _problem(exc.code, 401, request.headers.get("X-Correlation-ID", str(uuid.uuid4())))
    store: RelationshipExecutionStore = request.app.state.relationship_execution_store
    outcome = store.outcome(context, control_id)
    if outcome is None:
        return _problem("EXECUTION_NOT_ACCESSIBLE", 404, request.headers.get("X-Correlation-ID", str(uuid.uuid4())))
    return outcome


def configure_relationship_workspace(application: FastAPI) -> None:
    application.state.relationship_execution_store = RelationshipExecutionStore()
    credentials_path = os.getenv("WAOOAW_WORKLOAD_CREDENTIALS")
    application.state.relationship_workload_auth = (
        WorkloadAuth.from_credentials(Path(credentials_path)) if credentials_path else None
    )

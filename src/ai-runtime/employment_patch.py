"""Proposal-only conversational-employment interpretation owned by AIR."""

# Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.4 AIR proposal operations
# Constitutional basis: C-023, C-049, C-059, C-062, C-063, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

from __future__ import annotations

import hashlib
import hmac
import json
import os
import asyncpg
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from pii.injection_guard import InjectionGuard
from employment_auth import (
    DelegatedContext,
    EmploymentAuthError,
    EmploymentWorkloadAuth,
    request_digest,
)
from employment_persistence import EmploymentPatchRepository

router = APIRouter(tags=["Employment Interpretation"])


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


class EmploymentModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="forbid")


class ImmutableContractReference(EmploymentModel):
    ref: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=64)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class Contribution(EmploymentModel):
    text: str = Field(min_length=1, max_length=20_000)
    locale: str = Field(min_length=2, max_length=35)


class BoundedContext(EmploymentModel):
    current_plan_version: str | None = Field(default=None, max_length=64)
    requirement_set_version: str | None = Field(default=None, max_length=64)


PatchType = Literal[
    "INDUCTION_CONTEXT",
    "GOAL",
    "PLAN",
    "CALENDAR",
    "DEPENDENCY",
    "OPERATING_CYCLE",
    "CORRECTIVE_PROPOSAL",
]
ProposalReasonCode = Literal[
    "SEMANTIC_PATH_UNREPRESENTABLE",
    "MATERIAL_UNCERTAINTY",
    "POLICY_REJECTED",
    "MODEL_UNAVAILABLE",
    "INTERNAL_FAILURE",
]
PATCH_TYPES = frozenset(
    {
        "INDUCTION_CONTEXT",
        "GOAL",
        "PLAN",
        "CALENDAR",
        "DEPENDENCY",
        "OPERATING_CYCLE",
        "CORRECTIVE_PROPOSAL",
    }
)


class EmploymentPatchProposalRequest(EmploymentModel):
    schema_version: Literal["1.0"]
    protocol_version: Literal["1.0-candidate"]
    relationship_ref: str = Field(min_length=1, max_length=160)
    contribution_ref: str = Field(min_length=1, max_length=160)
    agent_type: str = Field(min_length=1, max_length=100)
    agent_version: str = Field(min_length=1, max_length=64)
    manifest_version: str = Field(min_length=1, max_length=64)
    semantic_catalogue: ImmutableContractReference
    prompt_policy: ImmutableContractReference
    model_policy: ImmutableContractReference
    patch_type: PatchType
    contribution: Contribution
    request_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    bounded_context: BoundedContext | None = None


class ProposalOperation(EmploymentModel):
    op: Literal["ADD", "REPLACE", "REMOVE"]
    semantic_path: str = Field(min_length=1, max_length=240)
    value: Any | None = None
    rationale: str | None = Field(default=None, max_length=500)
    source_refs: tuple[str, ...] = ()


class EmploymentPatchProposalReceipt(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    proposal_id: UUID
    state: Literal["PENDING"] = "PENDING"
    protocol_version: Literal["1.0-candidate"] = "1.0-candidate"
    relationship_ref: str
    contribution_ref: str
    agent_type: str
    agent_version: str
    manifest_version: str
    patch_type: PatchType
    semantic_catalogue: ImmutableContractReference
    prompt_policy: ImmutableContractReference
    model_policy: ImmutableContractReference
    request_digest: str
    accepted_at: datetime
    reconciliation_uri: str


class EmploymentPatchProposal(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    proposal_id: UUID
    protocol_version: Literal["1.0-candidate"] = "1.0-candidate"
    relationship_ref: str
    contribution_ref: str
    agent_type: str
    agent_version: str
    manifest_version: str
    semantic_catalogue: ImmutableContractReference
    request_digest: str
    patch_type: PatchType
    state: Literal["PENDING", "PROPOSED", "UNREPRESENTABLE", "FAILED"]
    operations: tuple[ProposalOperation, ...]
    confidence: float = Field(ge=0, le=1)
    assumptions: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    source_refs: tuple[str, ...]
    prompt_policy: ImmutableContractReference
    model_policy: ImmutableContractReference
    model_decision_ref: str = Field(min_length=1, max_length=200)
    reason_code: ProposalReasonCode | None = None
    produced_at: datetime

    @model_validator(mode="after")
    def validate_state_payload(self) -> EmploymentPatchProposal:
        if self.state == "PROPOSED" and (not self.operations or self.reason_code is not None):
            raise ValueError("PROPOSED requires operations and prohibits a reason code")
        if self.state != "PROPOSED" and self.operations:
            raise ValueError("non-success proposal states cannot carry operations")
        if self.state in {"UNREPRESENTABLE", "FAILED"} and self.reason_code is None:
            raise ValueError("non-success terminal states require a reason code")
        if self.unresolved_questions and self.operations:
            raise ValueError("material uncertainty cannot carry operations")
        return self


class ProposalInterpretation(EmploymentModel):
    operations: tuple[ProposalOperation, ...] = ()
    confidence: float = Field(ge=0, le=1)
    assumptions: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    model_decision_ref: str = Field(min_length=1, max_length=200)


class SemanticCatalogue:
    def __init__(
        self,
        reference: ImmutableContractReference,
        allowed_paths_by_patch_type: dict[PatchType, frozenset[str]],
    ) -> None:
        self.reference = reference
        self.allowed_paths_by_patch_type = allowed_paths_by_patch_type

    def accepts(self, patch_type: PatchType, path: str) -> bool:
        return path in self.allowed_paths_by_patch_type.get(patch_type, frozenset())


class EmploymentProposalError(RuntimeError):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


class EmploymentPatchProposalService:
    def __init__(
        self,
        catalogues: tuple[SemanticCatalogue, ...],
        interpreter: Callable[[EmploymentPatchProposalRequest], ProposalInterpretation],
        injection_guard: InjectionGuard | None = None,
    ) -> None:
        self._catalogues = {(item.reference.ref, item.reference.version, item.reference.digest): item for item in catalogues}
        self._interpreter = interpreter
        self._injection_guard = injection_guard or InjectionGuard()
        self._proposals: dict[UUID, EmploymentPatchProposal] = {}
        self._proposal_tenants: dict[UUID, str] = {}
        self._idempotency: dict[
            tuple[str, str, UUID],
            tuple[str, UUID],
        ] = {}
        self._lock = Lock()

    def propose(
        self,
        workload_identity: str,
        idempotency_key: UUID,
        request: EmploymentPatchProposalRequest,
        *,
        tenant_id: str | None = None,
    ) -> tuple[EmploymentPatchProposalReceipt | EmploymentPatchProposal, bool]:
        digest = self.request_digest(request)
        if not hmac.compare_digest(digest, request.request_digest):
            raise EmploymentProposalError("AIR_EMPLOYMENT_INVALID", 400)
        identity = (workload_identity, request.relationship_ref, idempotency_key)
        with self._lock:
            existing = self._idempotency.get(identity)
            if existing is not None:
                prior_digest, proposal_id = existing
                if not hmac.compare_digest(prior_digest, digest):
                    raise EmploymentProposalError("AIR_EMPLOYMENT_CONFLICT", 409)
                return self._proposals[proposal_id], True
            if not self._injection_guard.scan(request.contribution.text):
                raise EmploymentProposalError("AIR_EMPLOYMENT_UNREPRESENTABLE", 422)
            catalogue_key = (
                request.semantic_catalogue.ref,
                request.semantic_catalogue.version,
                request.semantic_catalogue.digest,
            )
            catalogue = self._catalogues.get(catalogue_key)
            if catalogue is None:
                raise EmploymentProposalError("AIR_EMPLOYMENT_UNREPRESENTABLE", 422)

            interpretation = self._interpreter(request)
            operations = interpretation.operations
            if interpretation.unresolved_questions:
                operations = ()
            if any(not catalogue.accepts(request.patch_type, item.semantic_path) for item in operations):
                raise EmploymentProposalError("AIR_EMPLOYMENT_UNREPRESENTABLE", 422)

            proposal_id = uuid4()
            state: Literal["PROPOSED", "UNREPRESENTABLE"] = "PROPOSED" if operations else "UNREPRESENTABLE"
            reason_code: ProposalReasonCode | None = None if operations else "MATERIAL_UNCERTAINTY"
            now = datetime.now(timezone.utc)
            proposal = EmploymentPatchProposal(
                proposal_id=proposal_id,
                relationship_ref=request.relationship_ref,
                contribution_ref=request.contribution_ref,
                agent_type=request.agent_type,
                agent_version=request.agent_version,
                manifest_version=request.manifest_version,
                semantic_catalogue=request.semantic_catalogue,
                request_digest=request.request_digest,
                patch_type=request.patch_type,
                state=state,
                operations=operations,
                confidence=interpretation.confidence,
                assumptions=interpretation.assumptions,
                unresolved_questions=interpretation.unresolved_questions,
                source_refs=interpretation.source_refs,
                prompt_policy=request.prompt_policy,
                model_policy=request.model_policy,
                model_decision_ref=interpretation.model_decision_ref,
                reason_code=reason_code,
                produced_at=now,
            )
            self._proposals[proposal_id] = proposal
            self._proposal_tenants[proposal_id] = tenant_id or workload_identity
            self._idempotency[identity] = (digest, proposal_id)
            receipt = EmploymentPatchProposalReceipt(
                proposal_id=proposal_id,
                relationship_ref=request.relationship_ref,
                contribution_ref=request.contribution_ref,
                agent_type=request.agent_type,
                agent_version=request.agent_version,
                manifest_version=request.manifest_version,
                patch_type=request.patch_type,
                semantic_catalogue=request.semantic_catalogue,
                prompt_policy=request.prompt_policy,
                model_policy=request.model_policy,
                request_digest=request.request_digest,
                accepted_at=now,
                reconciliation_uri=f"/internal/v1/employment-patch-proposals/{proposal_id}",
            )
            return receipt, False

    def get(self, proposal_id: UUID, tenant_id: str | None = None) -> EmploymentPatchProposal:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            proposal_tenant = self._proposal_tenants.get(proposal_id)
        if proposal is None or (tenant_id is not None and proposal_tenant != tenant_id):
            raise EmploymentProposalError("AIR_EMPLOYMENT_NOT_FOUND", 404)
        return proposal

    @staticmethod
    def request_digest(request: EmploymentPatchProposalRequest) -> str:
        payload = request.model_dump(mode="json", by_alias=True, exclude={"request_digest"})
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        return hashlib.sha256(canonical).hexdigest()


def _service(request: Request) -> EmploymentPatchProposalService:
    service = getattr(request.app.state, "employment_patch_service", None)
    if not isinstance(service, EmploymentPatchProposalService):
        raise EmploymentProposalError("AIR_EMPLOYMENT_UNAVAILABLE", 503)
    return service


def _repository(request: Request) -> EmploymentPatchRepository:
    repository = getattr(request.app.state, "employment_patch_repository", None)
    if not isinstance(repository, EmploymentPatchRepository):
        raise EmploymentProposalError("AIR_EMPLOYMENT_UNAVAILABLE", 503)
    return repository


def _authorize(
    request: Request,
    route: str,
    operation: str,
    digest: str,
    relationship_id: str | None,
    idempotency_key: UUID | None,
) -> DelegatedContext:
    auth = getattr(request.app.state, "employment_workload_auth", None)
    if not isinstance(auth, EmploymentWorkloadAuth):
        raise EmploymentProposalError("AIR_EMPLOYMENT_UNAVAILABLE", 503)
    try:
        return auth.authorize(
            request,
            route,
            operation,
            digest,
            relationship_id,
            str(idempotency_key) if idempotency_key is not None else None,
        )
    except EmploymentAuthError:
        raise EmploymentProposalError("AIR_EMPLOYMENT_UNAUTHORIZED", 401) from None


@router.post("/internal/v1/employment-patch-proposals")
async def propose_employment_patch(
    payload: EmploymentPatchProposalRequest,
    request: Request,
    idempotency_key: UUID = Header(alias="Idempotency-Key"),
    correlation_id: UUID = Header(alias="X-Correlation-Id"),
) -> JSONResponse:
    try:
        context = _authorize(
            request,
            "/internal/v1/employment-patch-proposals",
            "proposeEmploymentPatch",
            request_digest(payload.model_dump(mode="json", by_alias=True)),
            payload.relationship_ref,
            idempotency_key,
        )
        repository = _repository(request)
        stored = await repository.find_by_idempotency(
            context.tenant_id,
            payload.relationship_ref,
            idempotency_key,
        )
        if stored is not None:
            if not hmac.compare_digest(stored.request_digest, payload.request_digest):
                raise EmploymentProposalError("AIR_EMPLOYMENT_CONFLICT", 409)
            replay = EmploymentPatchProposal.model_validate(stored.proposal_json)
            return JSONResponse(
                status_code=200,
                content=json.loads(replay.model_dump_json(by_alias=True)),
            )
        result, replayed = _service(request).propose(
            context.issuer_uri,
            idempotency_key,
            payload,
            tenant_id=context.tenant_id,
        )
        proposal = _service(request).get(result.proposal_id, context.tenant_id)
        try:
            await repository.save(
                context.tenant_id,
                payload.relationship_ref,
                idempotency_key,
                payload.request_digest,
                json.loads(result.model_dump_json(by_alias=True)),
                json.loads(proposal.model_dump_json(by_alias=True)),
            )
        except asyncpg.UniqueViolationError:
            stored = await repository.find_by_idempotency(
                context.tenant_id,
                payload.relationship_ref,
                idempotency_key,
            )
            if stored is None or not hmac.compare_digest(
                stored.request_digest,
                payload.request_digest,
            ):
                raise EmploymentProposalError("AIR_EMPLOYMENT_CONFLICT", 409) from None
            result = EmploymentPatchProposal.model_validate(stored.proposal_json)
            replayed = True
        return JSONResponse(
            status_code=200 if replayed else 202,
            content=json.loads(result.model_dump_json(by_alias=True)),
        )
    except EmploymentProposalError as error:
        return _problem(error, correlation_id)


@router.get("/internal/v1/employment-patch-proposals/{proposal_id}")
async def get_employment_patch_proposal(
    proposal_id: UUID,
    request: Request,
    correlation_id: UUID = Header(alias="X-Correlation-Id"),
) -> JSONResponse:
    try:
        context = _authorize(
            request,
            "/internal/v1/employment-patch-proposals/{proposalId}",
            "getEmploymentPatchProposal",
            request_digest(None),
            None,
            None,
        )
        try:
            result = _service(request).get(proposal_id, context.tenant_id)
        except EmploymentProposalError as error:
            if error.status != 404:
                raise
            stored = await _repository(request).get(context.tenant_id, proposal_id)
            if stored is None:
                raise
            result = EmploymentPatchProposal.model_validate(stored.proposal_json)
        if result.relationship_ref != context.relationship_id:
            raise EmploymentProposalError("AIR_EMPLOYMENT_NOT_FOUND", 404)
        return JSONResponse(
            status_code=200,
            content=json.loads(result.model_dump_json(by_alias=True)),
        )
    except EmploymentProposalError as error:
        return _problem(error, correlation_id)


def _problem(error: EmploymentProposalError, correlation_id: UUID) -> JSONResponse:
    return JSONResponse(
        status_code=error.status,
        media_type="application/problem+json",
        content={
            "type": f"https://waooaw.com/problems/{error.code.lower().replace('_', '-')}",
            "title": "Employment proposal could not be completed",
            "status": error.status,
            "code": error.code,
            "correlationId": str(correlation_id),
        },
    )


def configure_employment_patch(
    application: FastAPI,
    interpreter: Callable[[EmploymentPatchProposalRequest], ProposalInterpretation] | None = None,
) -> None:
    credentials_path = os.getenv("WAOOAW_WORKLOAD_CREDENTIALS")
    application.state.employment_workload_auth = (
        EmploymentWorkloadAuth.from_credentials(Path(credentials_path)) if credentials_path else None
    )
    raw_catalogue = os.getenv("EMPLOYMENT_SEMANTIC_CATALOGUE_JSON")
    if not raw_catalogue:
        application.state.employment_patch_service = None
        return
    try:
        configured = json.loads(raw_catalogue)
        reference = ImmutableContractReference.model_validate(configured["reference"])
        allowed_paths: dict[PatchType, frozenset[str]] = {}
        for patch_type, paths in configured["allowedPathsByPatchType"].items():
            if patch_type not in PATCH_TYPES or not isinstance(paths, list):
                raise ValueError("unsupported patch type or path collection")
            if not all(isinstance(path, str) and path for path in paths):
                raise ValueError("semantic paths must be non-empty strings")
            allowed_paths[cast(PatchType, patch_type)] = frozenset(paths)
        catalogue = SemanticCatalogue(reference, allowed_paths)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("EMPLOYMENT_SEMANTIC_CATALOGUE_JSON is invalid.") from error

    def unavailable_interpreter(
        request: EmploymentPatchProposalRequest,
    ) -> ProposalInterpretation:
        return ProposalInterpretation(
            confidence=0,
            unresolved_questions=("The configured interpretation provider is unavailable.",),
            source_refs=(request.contribution_ref,),
            model_decision_ref="employment-interpreter-unavailable",
        )

    application.state.employment_patch_service = EmploymentPatchProposalService(
        (catalogue,),
        interpreter or unavailable_interpreter,
    )

"""Private FastAPI transport for Agent Runtime Adapter Contract v1."""

# Implements: adr/ADR-049-agent-runtime-adapter-transport-and-isolation.md §Decision
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .adapter import AdapterContractError, ReferenceAdapter
from .models import AdapterInvocationEnvelopeV1, AdapterInvocationV1


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


def _wire(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_wire(item) for item in value]
    if isinstance(value, dict):
        return {key: _wire(item) for key, item in value.items()}
    if hasattr(value, "__dataclass_fields__"):
        return {_camel(key): _wire(item) for key, item in asdict(value).items()}
    return value


def _envelope(payload: dict[str, Any]) -> AdapterInvocationEnvelopeV1:
    try:
        values = payload["envelope"]
        return AdapterInvocationEnvelopeV1(
            schema_version=values["schemaVersion"],
            tenant_ref=values["tenantRef"],
            relationship_id=values["relationshipId"],
            professional_type_id=values["professionalTypeId"],
            professional_version=values["professionalVersion"],
            skill_id=values["skillId"],
            skill_version=values["skillVersion"],
            admission_content_digest=values["admissionContentDigest"],
            artifact_digest=values["artifactDigest"],
            customer_contract_digest=values["customerContractDigest"],
            decision_space_version=values["decisionSpaceVersion"],
            configuration_revision=values.get("configurationRevision"),
            goal_revision=values.get("goalRevision"),
            invocation_id=values["invocationId"],
            idempotency_key=values["idempotencyKey"],
            payload_digest=values["payloadDigest"],
            ce_decision_ref=values["ceDecisionRef"],
            evidence_context_ref=values["evidenceContextRef"],
            deadline=datetime.fromisoformat(values["deadline"].replace("Z", "+00:00")),
            traceparent=values.get("traceparent"),
            correlation_id=values["correlationId"],
            mode=values["mode"],
            stop_evidence_ref=values.get("stopEvidenceRef"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="ADAPTER_REQUEST_INVALID") from exc


def _invocation_wire(invocation: AdapterInvocationV1, replayed: bool = False) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0.0",
        "invocationId": invocation.envelope.invocation_id,
        "state": invocation.state.value,
        "stateVersion": invocation.state_version,
        "replayed": replayed,
        "updatedAt": invocation.updated_at.isoformat(),
    }


def create_app(adapter: ReferenceAdapter) -> FastAPI:
    app = FastAPI(title="WAOOAW Agent Runtime Adapter", version="1.0.0", docs_url=None, redoc_url=None)
    expected_workload = os.environ.get(
        "PR_WORKLOAD_URI",
        "spiffe://demo.waooaw.internal/workload/professional-runtime",
    )

    def require_professional_runtime(
        workload_uri: str = Header(alias="X-WAOOAW-Workload-URI"),
        authorization: str = Header(alias="Authorization"),
    ) -> None:
        if workload_uri != expected_workload or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=403, detail="ADAPTER_NOT_ACCESSIBLE")

    @app.exception_handler(AdapterContractError)
    async def contract_error(_request: Request, error: AdapterContractError) -> JSONResponse:
        status = 503 if error.retryable else 409
        return JSONResponse(
            status_code=status,
            media_type="application/problem+json",
            content={
                "type": f"https://waooaw.com/problems/{error.code.lower().replace('_', '-')}",
                "title": "Adapter request could not be completed",
                "status": status,
                "code": error.code,
                "correlationId": error.correlation_id,
                "retryable": error.retryable,
            },
        )

    @app.get("/health/live")
    async def liveness() -> dict[str, str]:
        return {"status": "ALIVE"}

    @app.get("/internal/v1/descriptor", dependencies=[Depends(require_professional_runtime)])
    async def describe() -> dict[str, Any]:
        return _wire(adapter.describe())

    @app.get("/internal/v1/health/ready", dependencies=[Depends(require_professional_runtime)])
    async def readiness() -> dict[str, str]:
        return adapter.health()

    @app.post("/internal/v1/configurations:validate", dependencies=[Depends(require_professional_runtime)])
    async def configure(payload: dict[str, Any]) -> dict[str, Any]:
        return adapter.configure(_envelope(payload), payload.get("payload", {}))

    @app.post("/internal/v1/plans", dependencies=[Depends(require_professional_runtime)])
    async def plan(payload: dict[str, Any]) -> dict[str, Any]:
        return adapter.plan(_envelope(payload), payload.get("payload", {}))

    @app.post("/internal/v1/invocations", dependencies=[Depends(require_professional_runtime)])
    async def execute(payload: dict[str, Any]) -> JSONResponse:
        outcome = adapter.execute(_envelope(payload), payload.get("payload", {}))
        return JSONResponse(status_code=202, content=_invocation_wire(outcome))

    @app.get("/internal/v1/invocations/{invocation_id}", dependencies=[Depends(require_professional_runtime)])
    async def status(invocation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _invocation_wire(adapter.status(_envelope(payload), invocation_id))

    @app.get("/internal/v1/invocations/{invocation_id}/events", dependencies=[Depends(require_professional_runtime)])
    async def events(invocation_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        return _wire(adapter.events(_envelope(payload), invocation_id))

    @app.post("/internal/v1/invocations/{invocation_id}:cancel", dependencies=[Depends(require_professional_runtime)])
    async def cancel(invocation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _invocation_wire(adapter.cancel(_envelope(payload), invocation_id))

    @app.post("/internal/v1/relationships/{relationship_id}:emergency-stop", dependencies=[Depends(require_professional_runtime)])
    async def emergency_stop(relationship_id: str, payload: dict[str, Any]) -> dict[str, str]:
        request_envelope = _envelope(payload)
        if request_envelope.relationship_id != relationship_id:
            raise HTTPException(status_code=404, detail="ADAPTER_NOT_ACCESSIBLE")
        return adapter.emergency_stop(request_envelope, payload.get("payload", {}).get("stopEvidenceRef", ""))

    @app.post("/internal/v1/relationships/{relationship_id}:resume", dependencies=[Depends(require_professional_runtime)])
    async def resume(relationship_id: str, payload: dict[str, Any]) -> dict[str, str]:
        request_envelope = _envelope(payload)
        if request_envelope.relationship_id != relationship_id:
            raise HTTPException(status_code=404, detail="ADAPTER_NOT_ACCESSIBLE")
        return adapter.resume(request_envelope)

    @app.get("/internal/v1/invocations/{invocation_id}/result", dependencies=[Depends(require_professional_runtime)])
    async def result(invocation_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _wire(adapter.result(_envelope(payload), invocation_id))

    return app
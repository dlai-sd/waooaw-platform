# Implements: architecture/reference/api-specs/professional-runtime.openapi.yaml VoiceOrchestrationV1
# constitutional_basis: C-001, C-023, C-025, C-042, C-049, C-059, C-063; ADR-018, ADR-029

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime
from typing import Protocol

import httpx
from fastapi import APIRouter, Depends, Header, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from routers.conversation_execution import (
    BPServiceContext,
    ConstitutionalDecision,
    ConversationConstitutionalGateway,
    _decode_service_assertion,
)

router = APIRouter(prefix="/api/v1/internal/relationships", tags=["Voice Orchestration"])
SUPPORTED_LOCALES = frozenset({"en-IN", "hi-IN", "mr-IN"})
SUPPORTED_MEDIA = frozenset({"audio/webm", "audio/ogg", "audio/wav"})
TERMINAL_STATES = frozenset({"REVIEW_REQUIRED", "COMPLETED", "CANCELLED", "REJECTED", "QUARANTINED", "UNAVAILABLE", "STOPPED"})


class StartVoiceOrchestrationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    contract_version: str = Field(alias="contractVersion")
    voice_session_id: uuid.UUID = Field(alias="voiceSessionId")
    payload_reference: uuid.UUID = Field(alias="payloadReference")
    locale: str
    media_type: str = Field(alias="mediaType")
    content_sha256: str = Field(alias="contentSha256", pattern=r"^[0-9a-f]{64}$")
    duration_seconds: int = Field(alias="durationSeconds", ge=1, le=180)
    size_bytes: int = Field(alias="sizeBytes", ge=1, le=15 * 1024 * 1024)


class VoiceOrchestration(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    contract_version: str = Field(default="1.0.0", alias="contractVersion")
    orchestration_id: uuid.UUID = Field(alias="orchestrationId")
    voice_session_id: uuid.UUID = Field(alias="voiceSessionId")
    state: str
    locale: str
    transcript: str | None = None
    confidence_band: str | None = Field(default=None, alias="confidenceBand")
    failure_code: str | None = Field(default=None, alias="failureCode")
    updated_at: datetime = Field(alias="updatedAt")


class AirTranscriptionClient(Protocol):
    async def start(self, orchestration_id: uuid.UUID, body: StartVoiceOrchestrationRequest, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, object]: ...

    async def cancel(self, transcription_id: uuid.UUID, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, object]: ...


class StopAuthority(Protocol):
    async def is_stopped(self, context: BPServiceContext, session_id: uuid.UUID, request_hash: str) -> bool: ...


class DependencyUnavailableError(RuntimeError):
    """A mandatory private orchestration dependency is unavailable."""


class UnavailableStopAuthority:
    async def is_stopped(self, context: BPServiceContext, session_id: uuid.UUID, request_hash: str) -> bool:
        raise DependencyUnavailableError


class ConstitutionalVoiceStopAuthority:
    def __init__(self, gateway: ConversationConstitutionalGateway) -> None:
        self._gateway = gateway

    async def is_stopped(self, context: BPServiceContext, session_id: uuid.UUID, request_hash: str) -> bool:
        if not await self._gateway.is_ready():
            raise DependencyUnavailableError
        decision = await self._gateway.authorize_execution(context, session_id, 1, request_hash)
        if decision == ConstitutionalDecision.STOPPED:
            return True
        if decision != ConstitutionalDecision.ALLOW:
            raise DependencyUnavailableError
        return False


class UnavailableAirClient:
    async def start(self, orchestration_id: uuid.UUID, body: StartVoiceOrchestrationRequest, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, object]:
        raise DependencyUnavailableError

    async def cancel(self, transcription_id: uuid.UUID, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, object]:
        raise DependencyUnavailableError


class HttpAirTranscriptionClient:
    def __init__(self, base_url: str, secret: str, client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret = secret
        self._client = client

    def _token(self) -> str:
        def encode(value: bytes) -> str:
            return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

        header = encode(b'{"alg":"HS256","typ":"JWT"}')
        claims = encode(json.dumps({"iss": "professional-runtime", "sub": "professional-runtime", "aud": "ai-runtime", "scope": "voice:transcribe", "exp": int(time.time()) + 30}, separators=(",", ":")).encode())
        signature = encode(hmac.new(self._secret.encode(), f"{header}.{claims}".encode(), hashlib.sha256).digest())
        return f"{header}.{claims}.{signature}"

    def _headers(self, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token()}", "Idempotency-Key": str(idempotency_key), "X-Correlation-Id": str(correlation_id)}

    async def start(self, orchestration_id: uuid.UUID, body: StartVoiceOrchestrationRequest, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, object]:
        payload = body.model_dump(by_alias=True, mode="json", exclude={"voice_session_id"})
        payload["orchestrationId"] = str(orchestration_id)
        response = await self._client.post(f"{self._base_url}/api/v1/internal/transcriptions", json=payload, headers=self._headers(idempotency_key, correlation_id))
        if response.status_code not in {200, 202, 503}:
            raise DependencyUnavailableError
        return response.json()

    async def cancel(self, transcription_id: uuid.UUID, idempotency_key: uuid.UUID, correlation_id: uuid.UUID) -> dict[str, object]:
        response = await self._client.delete(f"{self._base_url}/api/v1/internal/transcriptions/{transcription_id}", headers=self._headers(idempotency_key, correlation_id))
        if response.status_code != 200:
            raise DependencyUnavailableError
        return response.json()


async def get_voice_context(request: Request, authorization: str | None = Header(default=None, alias="Authorization")) -> BPServiceContext | None:
    secret = getattr(request.app.state, "bp_service_jwt_secret", None) or os.getenv("BP_SERVICE_JWT_SECRET")
    if not secret or not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        claims = _decode_service_assertion(authorization.removeprefix("Bearer ").strip(), str(secret))
        if claims.get("sub") != "business-platform" or "voice:orchestrate" not in set(str(claims.get("scope", "")).split()):
            return None
        values = (str(claims["contract_id"]), str(claims["tenant_id"]), str(claims["relationship_id"]), str(claims["delegated_actor_id"]), str(claims["participant_role"]))
        if not all(values):
            return None
        return BPServiceContext(*values)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _problem(status: int, code: str, correlation_id: uuid.UUID, *, reconcile: bool = False) -> JSONResponse:
    return JSONResponse(status_code=status, media_type="application/problem+json", content={"type": f"https://waooaw.com/problems/{code.replace('_', '-')}", "title": code, "status": status, "code": code, "correlationId": str(correlation_id), "reconciliationRequired": reconcile})


def _digest(body: StartVoiceOrchestrationRequest, context: BPServiceContext) -> str:
    value = {"body": body.model_dump(by_alias=True, mode="json"), "tenantId": context.tenant_id, "relationshipId": context.relationship_id}
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def _map_air(orchestration_id: uuid.UUID, body: StartVoiceOrchestrationRequest, air: dict[str, object]) -> VoiceOrchestration:
    state = str(air["state"])
    if state == "COMPLETED" and air.get("confidenceBand") != "HIGH":
        state = "REVIEW_REQUIRED"
    return VoiceOrchestration(orchestrationId=orchestration_id, voiceSessionId=body.voice_session_id, state=state, locale=body.locale, transcript=air.get("transcript"), confidenceBand=air.get("confidenceBand"), failureCode=air.get("failureCode"), updatedAt=air["updatedAt"])


@router.post("/{relationshipId}/voice-orchestrations", response_model=VoiceOrchestration, operation_id="startVoiceOrchestrationInternal")
async def start_voice_orchestration(
    body: StartVoiceOrchestrationRequest,
    request: Request,
    relationship_id: uuid.UUID = Path(alias="relationshipId"),
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    context: BPServiceContext | None = Depends(get_voice_context),
) -> JSONResponse:
    if context is None or context.relationship_id != str(relationship_id):
        return _problem(401, "relationship_forbidden", correlation_id)
    if body.contract_version != "1.0.0":
        return _problem(400, "contract_mismatch", correlation_id)
    if body.locale not in SUPPORTED_LOCALES or body.media_type not in SUPPORTED_MEDIA:
        return _problem(400, "invalid_media", correlation_id)
    orchestration_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{context.tenant_id}:{relationship_id}:{body.voice_session_id}:{idempotency_key}")
    digest = _digest(body, context)
    existing = request.app.state.voice_orchestration_store.get(orchestration_id)
    if existing is not None:
        if existing[0] != digest:
            return _problem(409, "idempotency_conflict", correlation_id)
        return JSONResponse(status_code=200, content=existing[1].model_dump(by_alias=True, mode="json", exclude_none=True))
    try:
        if await request.app.state.voice_stop_authority.is_stopped(context, body.voice_session_id, digest):
            return _problem(423, "stopped", correlation_id)
        air = await request.app.state.air_transcription_client.start(orchestration_id, body, idempotency_key, correlation_id)
    except (DependencyUnavailableError, httpx.HTTPError):
        return _problem(503, "transcription_unavailable", correlation_id, reconcile=True)
    result = _map_air(orchestration_id, body, air)
    request.app.state.voice_orchestration_store[orchestration_id] = (digest, result, uuid.UUID(str(air["transcriptionId"])), context.tenant_id, context.relationship_id, body)
    status = 503 if result.state == "UNAVAILABLE" else 202
    return JSONResponse(status_code=status, content=result.model_dump(by_alias=True, mode="json", exclude_none=True))


@router.get("/{relationshipId}/voice-orchestrations/{orchestrationId}", response_model=VoiceOrchestration, operation_id="getVoiceOrchestrationInternal")
async def get_voice_orchestration(orchestration_id: uuid.UUID = Path(alias="orchestrationId"), relationship_id: uuid.UUID = Path(alias="relationshipId"), *, request: Request, correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"), context: BPServiceContext | None = Depends(get_voice_context)) -> JSONResponse:
    existing = request.app.state.voice_orchestration_store.get(orchestration_id)
    if context is None or context.relationship_id != str(relationship_id):
        return _problem(401, "relationship_forbidden", correlation_id)
    if existing is None or existing[3] != context.tenant_id or existing[4] != context.relationship_id:
        return _problem(404, "relationship_forbidden", correlation_id)
    return JSONResponse(status_code=200, content=existing[1].model_dump(by_alias=True, mode="json", exclude_none=True))


@router.delete("/{relationshipId}/voice-orchestrations/{orchestrationId}", response_model=VoiceOrchestration, operation_id="cancelVoiceOrchestrationInternal")
async def cancel_voice_orchestration(orchestration_id: uuid.UUID = Path(alias="orchestrationId"), relationship_id: uuid.UUID = Path(alias="relationshipId"), *, request: Request, idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"), correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"), context: BPServiceContext | None = Depends(get_voice_context)) -> JSONResponse:
    existing = request.app.state.voice_orchestration_store.get(orchestration_id)
    if context is None or context.relationship_id != str(relationship_id):
        return _problem(401, "relationship_forbidden", correlation_id)
    if existing is None or existing[3] != context.tenant_id or existing[4] != context.relationship_id:
        return _problem(404, "relationship_forbidden", correlation_id)
    try:
        if await request.app.state.voice_stop_authority.is_stopped(context, existing[1].voice_session_id, existing[0]):
            return _problem(423, "stopped", correlation_id)
        air = await request.app.state.air_transcription_client.cancel(existing[2], idempotency_key, correlation_id)
    except (DependencyUnavailableError, httpx.HTTPError):
        return _problem(503, "transcription_unavailable", correlation_id, reconcile=True)
    result = existing[1] if existing[1].state in TERMINAL_STATES else _map_air(orchestration_id, existing[5], air)
    request.app.state.voice_orchestration_store[orchestration_id] = (existing[0], result, existing[2], existing[3], existing[4], existing[5])
    return JSONResponse(status_code=200, content=result.model_dump(by_alias=True, mode="json", exclude_none=True))
# Implements: architecture/reference/api-specs/ai-runtime-transcription.openapi.yaml
# constitutional_basis: C-001, C-023, C-042, C-049, C-059, C-063

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Protocol, cast

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/v1/internal/transcriptions", tags=["Provider-Neutral Transcription"])
SUPPORTED_LOCALES = frozenset({"en-IN", "hi-IN", "mr-IN"})
SUPPORTED_MEDIA = frozenset({"audio/webm", "audio/ogg", "audio/wav"})
TERMINAL_STATES = frozenset({"COMPLETED", "CANCELLED", "REJECTED", "QUARANTINED", "UNAVAILABLE"})


class TranscriptionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    contract_version: str = Field(alias="contractVersion")
    orchestration_id: uuid.UUID = Field(alias="orchestrationId")
    payload_reference: uuid.UUID = Field(alias="payloadReference")
    locale: str
    media_type: str = Field(alias="mediaType")
    content_sha256: str = Field(alias="contentSha256", pattern=r"^[0-9a-f]{64}$")
    duration_seconds: int = Field(alias="durationSeconds", ge=1, le=180)
    size_bytes: int = Field(alias="sizeBytes", ge=1, le=15 * 1024 * 1024)


class TranscriptionResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    contract_version: str = Field(default="1.0.0", alias="contractVersion")
    transcription_id: uuid.UUID = Field(alias="transcriptionId")
    orchestration_id: uuid.UUID = Field(alias="orchestrationId")
    state: str
    locale: str
    transcript: str | None = None
    confidence_band: str | None = Field(default=None, alias="confidenceBand")
    failure_code: str | None = Field(default=None, alias="failureCode")
    updated_at: datetime = Field(alias="updatedAt")


class ProviderResult(BaseModel):
    transcript: str
    confidence: float = Field(ge=0, le=1)


class TranscriptionProvider(Protocol):
    async def transcribe(self, request: TranscriptionRequest) -> ProviderResult:
        """Return content only from an approved provider-neutral adapter."""


class ProviderUnavailableError(RuntimeError):
    """No approved provider is active."""


class DisabledTranscriptionProvider:
    async def transcribe(self, request: TranscriptionRequest) -> ProviderResult:
        raise ProviderUnavailableError


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _authorized(request: Request, authorization: str | None) -> bool:
    secret = getattr(request.app.state, "pr_service_jwt_secret", None) or os.getenv("PR_SERVICE_JWT_SECRET")
    if not secret or not authorization or not authorization.startswith("Bearer "):
        return False
    try:
        header_part, payload_part, signature_part = authorization.removeprefix("Bearer ").split(".")
        signed = f"{header_part}.{payload_part}".encode()
        expected = hmac.new(str(secret).encode(), signed, hashlib.sha256).digest()
        if not hmac.compare_digest(_decode(signature_part), expected):
            return False
        header = json.loads(_decode(header_part))
        claims = json.loads(_decode(payload_part))
        audience = claims.get("aud")
        scopes = set(str(claims.get("scope", "")).split())
        return (
            header.get("alg") == "HS256"
            and claims.get("iss") == "professional-runtime"
            and claims.get("sub") == "professional-runtime"
            and (audience == "ai-runtime" or (isinstance(audience, list) and "ai-runtime" in audience))
            and "voice:transcribe" in scopes
            and int(claims["exp"]) > int(time.time())
            and int(claims.get("nbf", 0)) <= int(time.time())
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


async def require_service(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> bool:
    return _authorized(request, authorization)


def _problem(status: int, code: str, correlation_id: uuid.UUID) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"https://waooaw.com/problems/{code.replace('_', '-')}",
            "title": code,
            "status": status,
            "code": code,
            "correlationId": str(correlation_id),
        },
    )


def _store(request: Request) -> dict[uuid.UUID, tuple[str, TranscriptionResult]]:
    return cast(
        dict[uuid.UUID, tuple[str, TranscriptionResult]],
        request.app.state.transcription_store,
    )


def _request_hash(body: TranscriptionRequest) -> str:
    payload = body.model_dump(by_alias=True, mode="json")
    return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


@router.post("", response_model=TranscriptionResult, operation_id="startProviderNeutralTranscription")
async def start_transcription(
    body: TranscriptionRequest,
    request: Request,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    authorized: bool = Depends(require_service),
) -> JSONResponse:
    if not authorized:
        return _problem(401, "transcription_unavailable", correlation_id)
    if body.contract_version != "1.0.0":
        return _problem(400, "contract_mismatch", correlation_id)
    if body.locale not in SUPPORTED_LOCALES:
        return _problem(400, "unsupported_language", correlation_id)
    if body.media_type not in SUPPORTED_MEDIA:
        return _problem(400, "invalid_media", correlation_id)
    transcription_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{body.orchestration_id}:{idempotency_key}")
    digest = _request_hash(body)
    existing = _store(request).get(transcription_id)
    if existing is not None:
        if existing[0] != digest:
            return _problem(409, "idempotency_conflict", correlation_id)
        return JSONResponse(status_code=200, content=existing[1].model_dump(by_alias=True, mode="json", exclude_none=True))

    provider: TranscriptionProvider = request.app.state.transcription_provider
    now = datetime.now(timezone.utc)
    try:
        provider_result = await provider.transcribe(body)
        confidence_band = (
            "HIGH" if provider_result.confidence >= 0.9 else "REVIEW" if provider_result.confidence >= 0.7 else "LOW"
        )
        result = TranscriptionResult(
            transcriptionId=transcription_id,
            orchestrationId=body.orchestration_id,
            state="COMPLETED",
            locale=body.locale,
            transcript=provider_result.transcript,
            confidenceBand=confidence_band,
            updatedAt=now,
        )
        status = 202
    except ProviderUnavailableError:
        result = TranscriptionResult(
            transcriptionId=transcription_id,
            orchestrationId=body.orchestration_id,
            state="UNAVAILABLE",
            locale=body.locale,
            confidenceBand="UNAVAILABLE",
            failureCode="transcription_unavailable",
            updatedAt=now,
        )
        status = 503
    _store(request)[transcription_id] = (digest, result)
    return JSONResponse(status_code=status, content=result.model_dump(by_alias=True, mode="json", exclude_none=True))


@router.get("/{transcription_id}", response_model=TranscriptionResult, operation_id="getProviderNeutralTranscription")
async def get_transcription(
    transcription_id: uuid.UUID,
    request: Request,
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    authorized: bool = Depends(require_service),
) -> JSONResponse:
    if not authorized:
        return _problem(401, "transcription_unavailable", correlation_id)
    existing = _store(request).get(transcription_id)
    if existing is None:
        return _problem(404, "transcription_unavailable", correlation_id)
    return JSONResponse(status_code=200, content=existing[1].model_dump(by_alias=True, mode="json", exclude_none=True))


@router.delete("/{transcription_id}", response_model=TranscriptionResult, operation_id="cancelProviderNeutralTranscription")
async def cancel_transcription(
    transcription_id: uuid.UUID,
    request: Request,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    authorized: bool = Depends(require_service),
) -> JSONResponse:
    del idempotency_key
    if not authorized:
        return _problem(401, "transcription_unavailable", correlation_id)
    existing = _store(request).get(transcription_id)
    if existing is None:
        return _problem(404, "transcription_unavailable", correlation_id)
    result = existing[1]
    if result.state not in TERMINAL_STATES:
        result = result.model_copy(update={"state": "CANCELLED", "updated_at": datetime.now(timezone.utc)})
        _store(request)[transcription_id] = (existing[0], result)
    return JSONResponse(status_code=200, content=result.model_dump(by_alias=True, mode="json", exclude_none=True))

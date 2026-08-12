# Implements: architecture/reference/api-specs/ai-runtime-transcription.openapi.yaml
# constitutional_basis: C-001, C-023, C-042, C-049, C-059, C-063, C-076

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid

import pytest

from main import app
from transcription import DisabledTranscriptionProvider, ProviderResult

SECRET = "test-pr-service-secret"


class DeterministicProvider:
    async def transcribe(self, request):
        return ProviderResult(transcript=f"transcript:{request.locale}", confidence=0.92)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _token(*, scope: str = "voice:transcribe") -> str:
    header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _encode(
        json.dumps(
            {
                "iss": "professional-runtime",
                "sub": "professional-runtime",
                "aud": "ai-runtime",
                "scope": scope,
                "exp": int(time.time()) + 60,
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = _encode(hmac.new(SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def _body(orchestration_id: uuid.UUID | None = None) -> dict[str, object]:
    return {
        "contractVersion": "1.0.0",
        "orchestrationId": str(orchestration_id or uuid.uuid4()),
        "payloadReference": str(uuid.uuid4()),
        "locale": "hi-IN",
        "mediaType": "audio/webm",
        "contentSha256": "a" * 64,
        "durationSeconds": 12,
        "sizeBytes": 4096,
    }


def _headers(key: uuid.UUID | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Idempotency-Key": str(key or uuid.uuid4()),
        "X-Correlation-Id": str(uuid.uuid4()),
    }


@pytest.fixture(autouse=True)
def configure_runtime():
    app.state.pr_service_jwt_secret = SECRET
    app.state.transcription_provider = DeterministicProvider()
    app.state.transcription_store = {}
    yield
    app.state.pr_service_jwt_secret = None
    app.state.transcription_provider = DisabledTranscriptionProvider()
    app.state.transcription_store = {}


async def test_requires_scoped_service_assertion(client):
    response = await client.post(
        "/api/v1/internal/transcriptions",
        json=_body(),
        headers={"Idempotency-Key": str(uuid.uuid4()), "X-Correlation-Id": str(uuid.uuid4())},
    )

    assert response.status_code == 401


async def test_completes_without_exposing_provider_identity(client):
    response = await client.post("/api/v1/internal/transcriptions", json=_body(), headers=_headers())

    assert response.status_code == 202
    assert response.json()["state"] == "COMPLETED"
    assert response.json()["transcript"] == "transcript:hi-IN"
    assert response.json()["confidenceBand"] == "HIGH"
    assert "provider" not in response.text.lower()


async def test_replays_identical_request_and_rejects_conflicting_identity(client):
    key = uuid.uuid4()
    body = _body()
    first = await client.post("/api/v1/internal/transcriptions", json=body, headers=_headers(key))
    replay = await client.post("/api/v1/internal/transcriptions", json=body, headers=_headers(key))
    body["sizeBytes"] = 4097
    conflict = await client.post("/api/v1/internal/transcriptions", json=body, headers=_headers(key))

    assert first.status_code == 202
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


async def test_disabled_provider_fails_closed_and_is_reconcilable(client):
    app.state.transcription_provider = DisabledTranscriptionProvider()
    response = await client.post("/api/v1/internal/transcriptions", json=_body(), headers=_headers())

    assert response.status_code == 503
    assert response.json()["state"] == "UNAVAILABLE"
    transcription_id = response.json()["transcriptionId"]
    reconciled = await client.get(
        f"/api/v1/internal/transcriptions/{transcription_id}",
        headers={"Authorization": f"Bearer {_token()}", "X-Correlation-Id": str(uuid.uuid4())},
    )
    assert reconciled.status_code == 200
    assert reconciled.json() == response.json()


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("contractVersion", "2.0.0", "contract_mismatch"),
        ("locale", "fr-FR", "unsupported_language"),
        ("mediaType", "audio/mpeg", "invalid_media"),
    ],
)
async def test_rejects_nonconforming_contract_before_provider(client, field, value, code):
    body = _body()
    body[field] = value
    response = await client.post("/api/v1/internal/transcriptions", json=body, headers=_headers())

    assert response.status_code == 400
    assert response.json()["code"] == code


async def test_missing_or_wrong_scope_is_not_authorized(client):
    headers = _headers()
    headers["Authorization"] = f"Bearer {_token(scope='conversation:execute')}"
    response = await client.post("/api/v1/internal/transcriptions", json=_body(), headers=headers)

    assert response.status_code == 401


async def test_unknown_transcription_is_concealed(client):
    response = await client.get(
        f"/api/v1/internal/transcriptions/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {_token()}", "X-Correlation-Id": str(uuid.uuid4())},
    )

    assert response.status_code == 404


async def test_cancels_nonterminal_transcription_and_replays_terminal_result(client):
    transcription_id = uuid.uuid4()
    orchestration_id = uuid.uuid4()
    from datetime import datetime, timezone
    from transcription import TranscriptionResult

    pending = TranscriptionResult(
        transcriptionId=transcription_id,
        orchestrationId=orchestration_id,
        state="PROCESSING",
        locale="en-IN",
        updatedAt=datetime.now(timezone.utc),
    )
    app.state.transcription_store[transcription_id] = ("digest", pending)
    headers = _headers()
    cancelled = await client.delete(f"/api/v1/internal/transcriptions/{transcription_id}", headers=headers)
    replay = await client.delete(f"/api/v1/internal/transcriptions/{transcription_id}", headers=_headers())

    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "CANCELLED"
    assert replay.json() == cancelled.json()


async def test_cancel_unknown_transcription_is_not_found(client):
    response = await client.delete(f"/api/v1/internal/transcriptions/{uuid.uuid4()}", headers=_headers())

    assert response.status_code == 404
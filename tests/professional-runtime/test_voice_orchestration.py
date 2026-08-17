# Implements: architecture/reference/api-specs/professional-runtime.openapi.yaml VoiceOrchestrationV1
# constitutional_basis: C-001, C-023, C-025, C-042, C-049, C-059, C-063, C-076

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone

import pytest
import httpx

from professional_runtime_main import app
from routers.conversation_execution import BPServiceContext, ConstitutionalDecision
from routers.voice_orchestration import (
    ConstitutionalVoiceStopAuthority,
    DependencyUnavailableError,
    HttpAirTranscriptionClient,
    StartVoiceOrchestrationRequest,
    UnavailableAirClient,
    UnavailableStopAuthority,
    VoiceOrchestration,
)

SECRET = "voice-bp-secret"


class FakeStopAuthority:
    def __init__(self, stopped: bool = False) -> None:
        self.stopped = stopped

    async def is_stopped(self, context, session_id, request_hash) -> bool:
        return self.stopped


class FakeAirClient:
    def __init__(self) -> None:
        self.calls = 0

    async def start(self, orchestration_id, body, idempotency_key, correlation_id):
        self.calls += 1
        return {
            "contractVersion": "1.0.0",
            "transcriptionId": str(uuid.uuid4()),
            "orchestrationId": str(orchestration_id),
            "state": "COMPLETED",
            "locale": body.locale,
            "transcript": "namaste",
            "confidenceBand": "REVIEW",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

    async def cancel(self, transcription_id, idempotency_key, correlation_id):
        return {
            "transcriptionId": str(transcription_id),
            "state": "CANCELLED",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _token(relationship_id: uuid.UUID, *, tenant_id: str = "tenant-a", scope: str = "voice:orchestrate") -> str:
    header = _encode(b'{"alg":"HS256","typ":"JWT"}')
    claims = _encode(
        json.dumps(
            {
                "iss": "business-platform",
                "sub": "business-platform",
                "aud": "professional-runtime",
                "scope": scope,
                "contract_id": "contract-a",
                "tenant_id": tenant_id,
                "relationship_id": str(relationship_id),
                "delegated_actor_id": "actor-a",
                "participant_role": "CUSTOMER",
                "exp": int(time.time()) + 60,
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = _encode(hmac.new(SECRET.encode(), f"{header}.{claims}".encode(), hashlib.sha256).digest())
    return f"{header}.{claims}.{signature}"


def _headers(relationship_id: uuid.UUID, key: uuid.UUID | None = None, **token_args) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token(relationship_id, **token_args)}",
        "Idempotency-Key": str(key or uuid.uuid4()),
        "X-Correlation-Id": str(uuid.uuid4()),
    }


def _body() -> dict[str, object]:
    return {
        "contractVersion": "1.0.0",
        "voiceSessionId": str(uuid.uuid4()),
        "payloadReference": str(uuid.uuid4()),
        "locale": "mr-IN",
        "mediaType": "audio/webm",
        "contentSha256": "b" * 64,
        "durationSeconds": 8,
        "sizeBytes": 2048,
    }


@pytest.fixture(autouse=True)
def configure_voice_runtime():
    app.state.bp_service_jwt_secret = SECRET
    app.state.voice_stop_authority = FakeStopAuthority()
    app.state.air_transcription_client = FakeAirClient()
    app.state.voice_orchestration_store = {}
    yield
    app.state.bp_service_jwt_secret = None
    app.state.voice_stop_authority = UnavailableStopAuthority()
    app.state.air_transcription_client = UnavailableAirClient()
    app.state.voice_orchestration_store = {}


async def test_requires_exact_relationship_authority(client):
    route_relationship = uuid.uuid4()
    asserted_relationship = uuid.uuid4()
    response = await client.post(
        f"/api/v1/internal/relationships/{route_relationship}/voice-orchestrations",
        json=_body(),
        headers=_headers(asserted_relationship),
    )

    assert response.status_code == 401
    assert response.json()["code"] == "relationship_forbidden"


async def test_stop_blocks_before_air_dispatch(client):
    relationship_id = uuid.uuid4()
    air = FakeAirClient()
    app.state.voice_stop_authority = FakeStopAuthority(stopped=True)
    app.state.air_transcription_client = air
    response = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=_body(),
        headers=_headers(relationship_id),
    )

    assert response.status_code == 423
    assert response.json()["code"] == "stopped"
    assert air.calls == 0


async def test_maps_air_review_result_and_replays_without_redispatch(client):
    relationship_id = uuid.uuid4()
    key = uuid.uuid4()
    body = _body()
    headers = _headers(relationship_id, key)
    first = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=body,
        headers=headers,
    )
    replay = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=body,
        headers=_headers(relationship_id, key),
    )

    assert first.status_code == 202
    assert first.json()["state"] == "REVIEW_REQUIRED"
    assert first.json()["transcript"] == "namaste"
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert app.state.air_transcription_client.calls == 1


async def test_reconciliation_hides_other_tenant_outcome(client):
    relationship_id = uuid.uuid4()
    created = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=_body(),
        headers=_headers(relationship_id),
    )
    response = await client.get(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations/{created.json()['orchestrationId']}",
        headers={
            "Authorization": f"Bearer {_token(relationship_id, tenant_id='tenant-b')}",
            "X-Correlation-Id": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    [
        ("contractVersion", "2.0.0", "contract_mismatch"),
        ("locale", "fr-FR", "invalid_media"),
        ("mediaType", "audio/mpeg", "invalid_media"),
    ],
)
async def test_rejects_nonconforming_contract_before_dispatch(client, field, value, expected_code):
    relationship_id = uuid.uuid4()
    body = _body()
    body[field] = value
    response = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=body,
        headers=_headers(relationship_id),
    )

    assert response.status_code == 400
    assert response.json()["code"] == expected_code


async def test_unavailable_stop_authority_fails_closed(client):
    relationship_id = uuid.uuid4()
    app.state.voice_stop_authority = UnavailableStopAuthority()
    response = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=_body(),
        headers=_headers(relationship_id),
    )

    assert response.status_code == 503
    assert response.json()["reconciliationRequired"] is True


async def test_conflicting_replay_is_rejected(client):
    relationship_id = uuid.uuid4()
    key = uuid.uuid4()
    body = _body()
    first = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=body,
        headers=_headers(relationship_id, key),
    )
    body["sizeBytes"] = 4096
    conflict = await client.post(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
        json=body,
        headers=_headers(relationship_id, key),
    )

    assert first.status_code == 202
    assert conflict.status_code == 409


async def test_get_and_cancel_pending_orchestration(client):
    relationship_id = uuid.uuid4()
    orchestration_id = uuid.uuid4()
    transcription_id = uuid.uuid4()
    body = StartVoiceOrchestrationRequest.model_validate(_body())
    pending = VoiceOrchestration(
        orchestrationId=orchestration_id,
        voiceSessionId=body.voice_session_id,
        state="TRANSCRIBING",
        locale=body.locale,
        updatedAt=datetime.now(timezone.utc),
    )
    app.state.voice_orchestration_store[orchestration_id] = (
        "digest",
        pending,
        transcription_id,
        "tenant-a",
        str(relationship_id),
        body,
    )
    get_response = await client.get(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations/{orchestration_id}",
        headers={"Authorization": f"Bearer {_token(relationship_id)}", "X-Correlation-Id": str(uuid.uuid4())},
    )
    cancel_response = await client.delete(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations/{orchestration_id}",
        headers=_headers(relationship_id),
    )

    assert get_response.status_code == 200
    assert cancel_response.status_code == 200
    assert cancel_response.json()["state"] == "CANCELLED"


async def test_cancel_unknown_or_unavailable_is_safe(client):
    relationship_id = uuid.uuid4()
    unknown = await client.delete(
        f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations/{uuid.uuid4()}",
        headers=_headers(relationship_id),
    )
    assert unknown.status_code == 404


class FakeConstitutionalGateway:
    def __init__(self, decision=ConstitutionalDecision.ALLOW, ready=True):
        self.decision = decision
        self.ready = ready

    async def is_ready(self):
        return self.ready

    async def authorize_execution(self, context, session_id, version, request_hash):
        return self.decision


async def test_constitutional_stop_authority_maps_allow_stop_and_unavailable():
    context = BPServiceContext("contract", "tenant", "relationship", "actor", "CUSTOMER")
    session_id = uuid.uuid4()
    assert await ConstitutionalVoiceStopAuthority(FakeConstitutionalGateway()).is_stopped(context, session_id, "hash") is False
    assert (
        await ConstitutionalVoiceStopAuthority(FakeConstitutionalGateway(ConstitutionalDecision.STOPPED)).is_stopped(
            context, session_id, "hash"
        )
        is True
    )
    with pytest.raises(DependencyUnavailableError):
        await ConstitutionalVoiceStopAuthority(FakeConstitutionalGateway(ready=False)).is_stopped(context, session_id, "hash")
    with pytest.raises(DependencyUnavailableError):
        await ConstitutionalVoiceStopAuthority(FakeConstitutionalGateway(ConstitutionalDecision.DENY)).is_stopped(
            context, session_id, "hash"
        )


async def test_http_air_client_signs_start_and_cancel_requests(client):
    seen = []
    transcription_id = uuid.uuid4()

    async def handler(request: httpx.Request):
        seen.append(request)
        updated_at = datetime.now(timezone.utc).isoformat()
        if request.method == "POST":
            return httpx.Response(
                202,
                json={"state": "COMPLETED", "transcriptionId": str(transcription_id), "updatedAt": updated_at},
            )
        return httpx.Response(
            200,
            json={"state": "CANCELLED", "transcriptionId": str(transcription_id), "updatedAt": updated_at},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        air = HttpAirTranscriptionClient("http://air/", "secret", http_client)
        app.state.air_transcription_client = air
        relationship_id = uuid.uuid4()
        response = await client.post(
            f"/api/v1/internal/relationships/{relationship_id}/voice-orchestrations",
            json=_body(),
            headers=_headers(relationship_id),
        )
        await air.cancel(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

    assert response.status_code == 202
    stored = app.state.voice_orchestration_store[uuid.UUID(response.json()["orchestrationId"])]
    assert stored[2] == transcription_id
    assert len(seen) == 2
    assert all(request.headers["authorization"].startswith("Bearer ") for request in seen)
    assert "voiceSessionId" not in json.loads(seen[0].content)


async def test_http_air_client_rejects_unexpected_status():
    async def handler(request: httpx.Request):
        return httpx.Response(418)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        air = HttpAirTranscriptionClient("http://air", "secret", http_client)
        body = StartVoiceOrchestrationRequest.model_validate(_body())
        with pytest.raises(DependencyUnavailableError):
            await air.start(uuid.uuid4(), body, uuid.uuid4(), uuid.uuid4())
        with pytest.raises(DependencyUnavailableError):
            await air.cancel(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

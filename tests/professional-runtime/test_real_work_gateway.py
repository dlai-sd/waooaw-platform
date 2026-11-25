"""WC-170 signed PR-to-BP transport for real-work events."""

# Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R007
# Constitutional basis: C-001, C-023, C-059, C-063, C-076, ADR-046

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from execution_timeline import TimelineEvent, WorkItemState
from real_work_gateway import (
    ACTOR_SOURCE,
    OPERATION,
    PURPOSE,
    ROUTE,
    BusinessPlatformRealWorkGateway,
    RealWorkDeliveryError,
)

TENANT, RELATIONSHIP = uuid4(), uuid4()


def _gateway(handler) -> BusinessPlatformRealWorkGateway:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    key = ec.generate_private_key(ec.SECP256R1())
    return BusinessPlatformRealWorkGateway(
        "http://business-platform/", client, "spiffe://demo/workload/professional-runtime", "key-1", "urn:bp", key
    )


def _event() -> TimelineEvent:
    return TimelineEvent(
        event_id=uuid4(),
        tenant_id=TENANT,
        relationship_id=RELATIONSHIP,
        work_item_id=uuid4(),
        work_item_type="SOCIAL_POST",
        state=WorkItemState.COMPLETED,
        occurred_at=datetime(2026, 11, 25, tzinfo=timezone.utc),
        artifact_id=uuid4(),
        artifact_digest="a" * 64,
        evidence_refs=("provider:ok",),
        provider_reference="page_1_post_2",
    )


def _context(request: httpx.Request) -> dict[str, object]:
    token = request.headers["Authorization"].removeprefix("Bearer ")
    payload = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


@pytest.mark.asyncio
async def test_an_event_is_posted_with_a_signed_envelope_bound_to_the_exact_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    event = _event()
    gateway = _gateway(handler)

    await gateway.deliver(event)

    request = seen[0]
    assert str(request.url) == f"http://business-platform{ROUTE}"
    body = json.loads(request.content)
    assert body["type"] == "TIMELINE_EVENT" and body["event"]["providerReference"] == "page_1_post_2"
    assert body["event"]["artifactDigest"] == "a" * 64
    context = _context(request)
    assert context["request_digest"] == hashlib.sha256(request.content).hexdigest()
    assert (context["route"], context["operation"], context["purpose"]) == (ROUTE, OPERATION, PURPOSE)
    assert context["actor_source"] == ACTOR_SOURCE and context["method"] == "POST"
    assert context["expires_at"] - context["issued_at"] <= 60
    assert request.headers["Idempotency-Key"] == str(event.event_id)
    await gateway.close()


@pytest.mark.asyncio
async def test_a_proposal_and_a_claim_use_their_own_types_and_the_proposal_wire_names() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(201, json={})

    gateway = _gateway(handler)
    proposal = {
        "artifactType": "CAMPAIGN_BRIEF",
        "content": {"goal": "x"},
        "plainLanguageSummary": "A summary.",
        "limitations": ["Limit."],
        "draft": False,
    }

    await gateway.propose_artifact(TENANT, RELATIONSHIP, proposal)
    await gateway.report_claim(TENANT, RELATIONSHIP, {"claimId": "reach", "measureId": "REACH"})

    assert [body["type"] for body in bodies] == ["ARTIFACT_PROPOSAL", "AGENT_CLAIM"]
    assert bodies[0]["artifact"]["supersedesArtifactId"] is None
    assert bodies[0]["artifact"]["plainLanguageSummary"] == "A summary."
    assert bodies[1]["claim"]["claimId"] == "reach"


@pytest.mark.asyncio
async def test_unicode_text_is_sent_unescaped_so_both_sides_hash_the_same_bytes() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(201, json={})

    gateway = _gateway(handler)

    await gateway.propose_artifact(
        TENANT,
        RELATIONSHIP,
        {"artifactType": "CAMPAIGN_BRIEF", "content": {"goal": "Café ☕"}, "plainLanguageSummary": "Café offer"},
    )

    assert "Café ☕" in seen[0].content.decode("utf-8")
    assert _context(seen[0])["request_digest"] == hashlib.sha256(seen[0].content).hexdigest()


@pytest.mark.asyncio
async def test_a_refusal_or_an_unreachable_platform_is_a_delivery_error_never_assumed_delivered() -> None:
    refused = _gateway(lambda request: httpx.Response(409, json={"code": "REAL_WORK_ARTIFACT_NOT_EXECUTABLE"}))
    with pytest.raises(RealWorkDeliveryError, match="409"):
        await refused.deliver(_event())

    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(RealWorkDeliveryError, match="unreachable"):
        await _gateway(unreachable).deliver(_event())


@pytest.mark.asyncio
async def test_from_credentials_rejects_a_key_that_is_not_ecdsa_or_ed25519(tmp_path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    workload = tmp_path / "workloads" / "professional-runtime"
    workload.mkdir(parents=True)
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "workloads": {
                    "professional-runtime": {"identity_uri": "spiffe://x", "delegation_key_id": "k"},
                    "business-platform": {"audience": "urn:bp"},
                }
            }
        )
    )
    (workload / "delegation-key.pem").write_bytes(
        rsa.generate_private_key(65537, 2048).private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
        )
    )

    with pytest.raises(ValueError, match="ECDSA or Ed25519"):
        BusinessPlatformRealWorkGateway.from_credentials("http://bp", tmp_path)

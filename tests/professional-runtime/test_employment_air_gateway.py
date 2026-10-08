from __future__ import annotations

import base64
import json
from uuid import UUID

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from employment_air_gateway import EmploymentAirGateway
from workload_identity import DelegatedContext


def _trusted_context() -> DelegatedContext:
    return DelegatedContext(
        schema_version="1.0",
        key_id="bp-key",
        issuer_uri="spiffe://waooaw.test/workload/business-platform",
        target_audience="urn:waooaw:service:professional-runtime",
        method="POST",
        route="/conversation",
        operation="contribute",
        contract_major=1,
        actor_subject="customer-1",
        actor_source="BP_SESSION",
        effective_role="CUSTOMER",
        tenant_id="00000000-0000-0000-0000-000000000001",
        relationship_id="relationship-1",
        purpose="EMPLOYMENT_CONVERSATION",
        subject_reference="subject-1",
        request_digest="a" * 64,
        command_id="command-1",
        idempotency_key=None,
        expected_versions={"workspace": "workspace-1"},
        issued_at=1,
        not_before=1,
        expires_at=2,
        envelope_id="envelope-1",
        correlation_id="00000000-0000-0000-0000-000000000007",
    )


@pytest.mark.asyncio
async def test_gateway_signs_exact_pr_air_route_and_preserves_trusted_context() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(202, json={"accepted": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    key = ec.generate_private_key(ec.SECP256R1())
    gateway = EmploymentAirGateway(
        "https://air.test",
        client,
        "spiffe://waooaw.test/workload/professional-runtime",
        "pr-key",
        "urn:waooaw:service:ai-runtime",
        key,
    )
    payload = {
        "relationshipRef": "relationship-1",
        "requestDigest": "b" * 64,
    }

    response = await gateway.propose(
        _trusted_context(),
        UUID("00000000-0000-0000-0000-000000000009"),
        payload,
    )

    assert response.status_code == 202
    request = captured["request"]
    assert isinstance(request, httpx.Request)
    token = request.headers["Authorization"].removeprefix("Bearer ")
    encoded_payload = token.split(".", maxsplit=1)[0]
    decoded = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    envelope = json.loads(decoded)
    assert envelope["issuer_uri"].endswith("/professional-runtime")
    assert envelope["target_audience"] == "urn:waooaw:service:ai-runtime"
    assert envelope["relationship_id"] == "relationship-1"
    assert envelope["tenant_id"] == _trusted_context().tenant_id
    assert envelope["operation"] == "proposeEmploymentPatch"
    await gateway.close()

@pytest.mark.asyncio
async def test_gateway_rejects_caller_supplied_relationship_rebinding() -> None:
    gateway = EmploymentAirGateway(
        "https://air.test",
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(500))),
        "spiffe://waooaw.test/workload/professional-runtime",
        "pr-key",
        "urn:waooaw:service:ai-runtime",
        ec.generate_private_key(ec.SECP256R1()),
    )
    with pytest.raises(ValueError, match="relationship binding"):
        await gateway.propose(
            _trusted_context(),
            UUID("00000000-0000-0000-0000-000000000009"),
            {"relationshipRef": "relationship-2"},
        )
    await gateway.close()

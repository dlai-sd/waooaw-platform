"""Signed PR-to-BP transport that reports real-work events to the Business Platform's owner projections."""

# Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-4 (PR stream, BP projection)
# Constitutional basis: C-001, C-023, C-059, C-063, ADR-046
# IB: IB-170

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from execution_timeline import BlindRetryRefused, TimelineEvent
from workload_identity import DelegatedContext, DelegationPrivateKey, sign_delegated_context

ROUTE = "/internal/v1/real-work/events"
OPERATION = "ingestRealWorkEvent"
PURPOSE = "REAL_WORK_EVENTS"
ACTOR_SOURCE = "PR_RUNTIME"


class RealWorkDeliveryError(Exception):
    """BP refused or could not take the event. The caller reconciles; it does not assume delivery."""


def _refusal_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("code") if isinstance(body, dict) else None


def _artifact_payload(proposal: dict[str, Any]) -> dict[str, Any]:
    """BP's ArtifactProposal field names: the DMA builds the proposal, this only maps it onto the wire shape."""
    return {
        "artifactType": proposal["artifactType"],
        "content": proposal["content"],
        "plainLanguageSummary": proposal["plainLanguageSummary"],
        "limitations": proposal.get("limitations", []),
        "authorityBoundary": proposal.get("authorityBoundary"),
        "supersedesArtifactId": proposal.get("supersedesArtifactId"),
        "draft": bool(proposal.get("draft", False)),
        "vocabularyVersion": proposal.get("vocabularyVersion"),
        "vocabularyDigest": proposal.get("vocabularyDigest"),
    }


class BusinessPlatformRealWorkGateway:
    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient,
        issuer_uri: str,
        key_id: str,
        audience: str,
        private_key: DelegationPrivateKey,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._issuer_uri = issuer_uri
        self._key_id = key_id
        self._audience = audience
        self._private_key = private_key

    @classmethod
    def from_credentials(cls, base_url: str, credentials: Path) -> BusinessPlatformRealWorkGateway:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        caller = manifest["workloads"]["professional-runtime"]
        target = manifest["workloads"]["business-platform"]
        workload = credentials / "workloads" / "professional-runtime"
        private_key = load_pem_private_key((workload / "delegation-key.pem").read_bytes(), password=None)
        if not isinstance(private_key, (ec.EllipticCurvePrivateKey, ed25519.Ed25519PrivateKey)):
            raise ValueError("PR delegation key must be ECDSA or Ed25519")
        client = httpx.AsyncClient(
            verify=str(credentials / "trust" / "ca-bundle.pem"),
            cert=(str(workload / "tls-cert.pem"), str(workload / "tls-key.pem")),
            timeout=15.0,
        )
        return cls(base_url, client, caller["identity_uri"], caller["delegation_key_id"], target["audience"], private_key)

    async def deliver(self, event: TimelineEvent) -> None:
        await self.post(
            {
                "type": "TIMELINE_EVENT",
                "tenantId": str(event.tenant_id),
                "relationshipId": str(event.relationship_id),
                "event": event.to_payload(),
            },
            str(event.event_id),
        )

    async def propose_artifact(self, tenant_id: UUID, relationship_id: UUID, proposal: dict[str, Any]) -> httpx.Response:
        """Hand BP a proposal for the customer to decide on. BP versions it; nothing here is authority."""
        return await self.post(
            {
                "type": "ARTIFACT_PROPOSAL",
                "tenantId": str(tenant_id),
                "relationshipId": str(relationship_id),
                "artifact": _artifact_payload(proposal),
            },
            str(uuid4()),
        )

    async def report_claim(self, tenant_id: UUID, relationship_id: UUID, claim: dict[str, Any]) -> httpx.Response:
        """Report an agent-stated figure. BP stores it labelled as agent-stated, never as an independent result."""
        return await self.post(
            {
                "type": "AGENT_CLAIM",
                "tenantId": str(tenant_id),
                "relationshipId": str(relationship_id),
                "claim": claim,
            },
            str(uuid4()),
        )

    async def post(self, payload: dict[str, Any], key: str) -> httpx.Response:
        # Same canonical form BP hashes: sorted keys, compact, and text that is not escaped to ASCII.
        canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False, ensure_ascii=False).encode(
            "utf-8"
        )
        now = int(time.time())
        context = DelegatedContext(
            schema_version="1.0",
            key_id=self._key_id,
            issuer_uri=self._issuer_uri,
            target_audience=self._audience,
            method="POST",
            route=ROUTE,
            operation=OPERATION,
            contract_major=1,
            actor_subject="professional-runtime",
            actor_source=ACTOR_SOURCE,
            effective_role="PROFESSIONAL_RUNTIME",
            tenant_id=str(payload["tenantId"]),
            relationship_id=str(payload["relationshipId"]),
            purpose=PURPOSE,
            subject_reference=key,
            request_digest=hashlib.sha256(canonical).hexdigest(),
            command_id=key,
            idempotency_key=key,
            expected_versions={},
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id=str(uuid4()),
            correlation_id=key,
        )
        try:
            response = await self._client.post(
                f"{self._base_url}{ROUTE}",
                content=canonical,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {sign_delegated_context(context, self._private_key)}",
                    "Idempotency-Key": key,
                    "X-Correlation-Id": key,
                },
            )
        except httpx.HTTPError as error:
            raise RealWorkDeliveryError("business platform unreachable") from error
        if response.status_code >= 400:
            # BP keeps the durable record of an unknown outcome and refuses a second run of it; that refusal is the
            # runtime's own blind-retry rule surviving a restart or a second replica.
            if response.status_code == 409 and _refusal_code(response) == "REAL_WORK_BLIND_RETRY":
                raise BlindRetryRefused("business platform holds an unknown outcome for this step")
            raise RealWorkDeliveryError(f"business platform refused with {response.status_code}")
        return response

    async def close(self) -> None:
        await self._client.aclose()

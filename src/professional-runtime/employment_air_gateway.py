"""Signed PR-to-AIR transport for proposal-only employment interpretation."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from workload_identity import DelegatedContext, DelegationPrivateKey, sign_delegated_context


class EmploymentAirGateway:
    route = "/internal/v1/employment-patch-proposals"
    operation = "proposeEmploymentPatch"

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
    def from_credentials(
        cls,
        base_url: str,
        credentials: Path,
    ) -> EmploymentAirGateway:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        caller = manifest["workloads"]["professional-runtime"]
        target = manifest["workloads"]["ai-runtime"]
        workload = credentials / "workloads" / "professional-runtime"
        private_key = load_pem_private_key(
            (workload / "delegation-key.pem").read_bytes(),
            password=None,
        )
        if not isinstance(
            private_key,
            (ec.EllipticCurvePrivateKey, ed25519.Ed25519PrivateKey),
        ):
            raise ValueError("PR delegation key must be ECDSA or Ed25519")
        client = httpx.AsyncClient(
            verify=str(credentials / "trust" / "ca-bundle.pem"),
            cert=(str(workload / "tls-cert.pem"), str(workload / "tls-key.pem")),
            timeout=15.0,
        )
        return cls(
            base_url,
            client,
            caller["identity_uri"],
            caller["delegation_key_id"],
            target["audience"],
            private_key,
        )

    async def propose(
        self,
        trusted_context: DelegatedContext,
        idempotency_key: UUID,
        payload: dict[str, object],
    ) -> httpx.Response:
        relationship_id = str(payload.get("relationshipRef", ""))
        if not relationship_id or relationship_id != trusted_context.relationship_id:
            raise ValueError("AIR relationship binding does not match trusted context")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode()
        digest = hashlib.sha256(canonical).hexdigest()
        now = int(time.time())
        correlation_id = trusted_context.correlation_id
        context = DelegatedContext(
            schema_version="1.0",
            key_id=self._key_id,
            issuer_uri=self._issuer_uri,
            target_audience=self._audience,
            method="POST",
            route=self.route,
            operation=self.operation,
            contract_major=1,
            actor_subject=trusted_context.actor_subject,
            actor_source=trusted_context.actor_source,
            effective_role=trusted_context.effective_role,
            tenant_id=trusted_context.tenant_id,
            relationship_id=relationship_id,
            purpose="EMPLOYMENT_PATCH_PROPOSAL",
            subject_reference=trusted_context.subject_reference,
            request_digest=digest,
            command_id=trusted_context.command_id,
            idempotency_key=str(idempotency_key),
            expected_versions=trusted_context.expected_versions,
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id=str(uuid4()),
            correlation_id=correlation_id,
        )
        response = await self._client.post(
            f"{self._base_url}{self.route}",
            json=payload,
            headers={
                "Authorization": f"Bearer {sign_delegated_context(context, self._private_key)}",
                "Idempotency-Key": str(idempotency_key),
                "X-Correlation-Id": correlation_id,
            },
        )
        return response

    async def get(
        self,
        trusted_context: DelegatedContext,
        proposal_id: UUID,
    ) -> httpx.Response:
        route = "/internal/v1/employment-patch-proposals/{proposalId}"
        now = int(time.time())
        context = DelegatedContext(
            schema_version="1.0",
            key_id=self._key_id,
            issuer_uri=self._issuer_uri,
            target_audience=self._audience,
            method="GET",
            route=route,
            operation="getEmploymentPatchProposal",
            contract_major=1,
            actor_subject=trusted_context.actor_subject,
            actor_source=trusted_context.actor_source,
            effective_role=trusted_context.effective_role,
            tenant_id=trusted_context.tenant_id,
            relationship_id=trusted_context.relationship_id,
            purpose="EMPLOYMENT_PATCH_RECONCILIATION",
            subject_reference=trusted_context.subject_reference,
            request_digest=hashlib.sha256(b"").hexdigest(),
            command_id=trusted_context.command_id,
            idempotency_key=None,
            expected_versions=trusted_context.expected_versions,
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id=str(uuid4()),
            correlation_id=trusted_context.correlation_id,
        )
        return await self._client.get(
            f"{self._base_url}/internal/v1/employment-patch-proposals/{proposal_id}",
            headers={
                "Authorization": f"Bearer {sign_delegated_context(context, self._private_key)}",
                "X-Correlation-Id": trusted_context.correlation_id,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

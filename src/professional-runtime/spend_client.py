"""Signed PR-to-WBE spend client: reserve before a costing step, charge after the provider's own proof."""

# Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R011 (C1); architecture/reference/product/ae02-real-work-solution-contract.md DC-6
# Constitutional basis: C-059, C-063, C-088, ADR-046
# IB: IB-171

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from execution_timeline import ProviderResult, SpendRefused, WorkItem
from workload_identity import DelegatedContext, DelegationPrivateKey, sign_delegated_context

PURPOSE = "REAL_WORK_SPEND"
ACTOR_SOURCE = "PR_RUNTIME"
ROUTES = {
    "reserve": ("/internal/v1/real-work/spend/reserve", "wbeReserveSpend"),
    "charge": ("/internal/v1/real-work/spend/charge", "wbeChargeSpend"),
    "reconcile": ("/internal/v1/real-work/spend/reconcile", "wbeReconcileSpend"),
}


def _digest(body: dict[str, Any]) -> str:
    # The same canonical form WBE hashes (sorted keys, compact separators).
    return hashlib.sha256(json.dumps(body, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


class WbeSpendClient:
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
    def from_credentials(cls, base_url: str, credentials: Path) -> WbeSpendClient:
        manifest = json.loads((credentials / "manifest.json").read_text(encoding="utf-8"))
        caller = manifest["workloads"]["professional-runtime"]
        target = manifest["workloads"]["billing-engine"]
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

    async def reserve(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        authorization_id: UUID,
        work_item_id: UUID,
        paise: int,
        component_id: str,
        environment: str,
    ) -> None:
        await self._post(
            "reserve",
            tenant_id,
            relationship_id,
            {
                "authorizationId": str(authorization_id),
                "workItemId": str(work_item_id),
                "paise": paise,
                "componentId": component_id,
                "environment": environment,
            },
            work_item_id,
        )

    async def charge(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        authorization_id: UUID,
        work_item_id: UUID,
        observed_paise: int,
        provider_reference: str,
        verified: bool,
        evidence_id: UUID,
    ) -> None:
        await self._post(
            "charge",
            tenant_id,
            relationship_id,
            {
                "authorizationId": str(authorization_id),
                "workItemId": str(work_item_id),
                "observedPaise": observed_paise,
                "providerReference": provider_reference,
                "verified": verified,
                "evidenceId": str(evidence_id),
            },
            work_item_id,
        )

    async def _post(self, name: str, tenant_id: UUID, relationship_id: UUID, body: dict[str, Any], key_seed: UUID) -> None:
        route, operation = ROUTES[name]
        # One idempotency key per (operation, work item): a retry of the same step replays, never double-reserves.
        key = str(UUID(hashlib.sha256(f"{name}:{key_seed}".encode()).hexdigest()[:32]))
        now = int(time.time())
        context = DelegatedContext(
            schema_version="1.0",
            key_id=self._key_id,
            issuer_uri=self._issuer_uri,
            target_audience=self._audience,
            method="POST",
            route=route,
            operation=operation,
            contract_major=1,
            actor_subject="professional-runtime",
            actor_source=ACTOR_SOURCE,
            effective_role="PROFESSIONAL_RUNTIME",
            tenant_id=str(tenant_id),
            relationship_id=str(relationship_id),
            purpose=PURPOSE,
            subject_reference=key,
            request_digest=_digest(body),
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
                f"{self._base_url}{route}",
                content=json.dumps(body, separators=(",", ":"), sort_keys=True).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {sign_delegated_context(context, self._private_key)}",
                    "Idempotency-Key": key,
                    "X-Correlation-ID": key,
                },
            )
        except httpx.HTTPError as error:
            raise SpendRefused("billing engine unreachable") from error
        if response.status_code >= 400:
            raise SpendRefused(f"billing engine refused {name} with {response.status_code}")

    async def close(self) -> None:
        await self._client.aclose()


class ChainSpendHook:
    """Adapts the spend client to the timeline's hook for one relationship's authorized artifact."""

    def __init__(
        self,
        client: WbeSpendClient,
        authorization_for: Callable[[WorkItem], UUID | None],
        component_id: str,
        environment: str,
        evidence_for: Callable[[WorkItem, ProviderResult], UUID | None],
    ) -> None:
        self._client = client
        self._authorization_for = authorization_for
        self._component_id = component_id
        self._environment = environment
        self._evidence_for = evidence_for

    async def reserve(self, item: WorkItem) -> None:
        authorization = self._authorization_for(item)
        if authorization is None or item.spend_paise is None:
            raise SpendRefused("the step has no spend authorization")
        await self._client.reserve(
            item.tenant_id,
            item.relationship_id,
            authorization,
            item.work_item_id,
            item.spend_paise,
            self._component_id,
            self._environment,
        )

    async def charge(self, item: WorkItem, result: ProviderResult) -> None:
        authorization = self._authorization_for(item)
        evidence = self._evidence_for(item, result)
        if authorization is None or evidence is None or item.spend_paise is None or not result.provider_reference:
            raise SpendRefused("the charge lacks authorization, evidence or the provider's reference")
        await self._client.charge(
            item.tenant_id,
            item.relationship_id,
            authorization,
            item.work_item_id,
            item.spend_paise,
            result.provider_reference,
            True,
            evidence,
        )

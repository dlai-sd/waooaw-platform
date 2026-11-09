"""AIR accesses inference authority only through the authenticated BP owner."""

from __future__ import annotations

import base64
import hashlib
import json
import ssl
import time
from dataclasses import asdict, replace
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from conversation_generation import (
    GenerationContentRecoveryRequest,
    GenerationRequest,
    InferenceBinding,
    InferencePermit,
    InferenceReceipt,
    canonical,
)
from employment_auth import DelegatedContext


class BusinessPlatformGenerationOwner:
    def __init__(self, endpoint: str, credentials: Path) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("Inference owner requires institutional HTTPS")
        manifest = json.loads((credentials / "manifest.json").read_bytes())
        caller = manifest["workloads"]["ai-runtime"]
        target = manifest["workloads"]["business-platform"]
        workload = credentials / "workloads" / "ai-runtime"
        key = load_pem_private_key((workload / "delegation-key.pem").read_bytes(), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise ValueError("Inference owner requires the admitted ECDSA delegation key")
        self.endpoint, self.key = endpoint.rstrip("/"), key
        self.issuer, self.key_id, self.audience = caller["identity_uri"], caller["delegation_key_id"], target["audience"]
        tls = ssl.create_default_context(cafile=str(credentials / "trust" / "ca-bundle.pem"))
        tls.load_cert_chain(str(workload / "tls-cert.pem"), str(workload / "tls-key.pem"))
        self.client = httpx.AsyncClient(verify=tls, timeout=15, follow_redirects=False, trust_env=False)

    async def _post(
        self,
        request: GenerationRequest,
        context: DelegatedContext,
        key: UUID,
        action: str,
        permit: InferencePermit | None = None,
        usage: tuple[int, int] | None = None,
        recovery: GenerationContentRecoveryRequest | None = None,
    ) -> httpx.Response:
        body: dict[str, object] = {
            "executionId": str(request.execution_id),
            "conversationId": str(request.conversation_id),
            "contributionRef": str(request.contribution_ref),
            "relationshipRef": str(request.relationship_ref),
            "requestDigest": request.request_digest,
            "inputDigest": hashlib.sha256(request.input.text.encode()).hexdigest(),
            "inputLanguage": request.input.language,
            "operationalMandate": request.operational_mandate,
        }
        if request.batch is not None:
            body["batch"] = request.batch.model_dump(by_alias=True, mode="json")
        if permit is not None:
            body["reservationId"] = str(permit.reservation_id)
            body["commercialReservationId"] = str(permit.commercial_reservation_id)
        if usage is not None:
            body["inputTokens"], body["outputTokens"] = usage
        if recovery is not None:
            body = {"original": body, "permission": recovery.permission.model_dump(by_alias=True, mode="json")}
        payload = canonical(body)
        now = int(time.time())
        delegated = replace(
            context,
            issuer_uri=self.issuer,
            key_id=self.key_id,
            target_audience=self.audience,
            method="POST",
            route=f"/internal/v1/conversation-inference/{action}",
            operation="readConversationInferenceContent" if recovery is not None else f"{action}ConversationInference",
            purpose="CONVERSATION_CONTENT_RECOVERY" if recovery is not None else "CONVERSATION_INFERENCE_OWNER",
            command_id=context.command_id if recovery is not None else str(request.execution_id),
            idempotency_key=str(key),
            request_digest=hashlib.sha256(payload).hexdigest(),
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id=str(uuid4()),
        )
        envelope = json.dumps(asdict(delegated), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        signature = self.key.sign(envelope, ec.ECDSA(hashes.SHA256()))
        token = ".".join(base64.urlsafe_b64encode(part).rstrip(b"=").decode() for part in (envelope, signature))
        response = await self.client.post(
            self.endpoint + delegated.route,
            content=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response

    async def resolve(self, request: GenerationRequest, context: DelegatedContext, key: UUID) -> InferenceBinding:
        return InferenceBinding.model_validate((await self._post(request, context, key, "resolve")).json())

    async def reserve(
        self, request: GenerationRequest, context: DelegatedContext, key: UUID, binding: InferenceBinding
    ) -> InferencePermit:
        result = InferencePermit.model_validate((await self._post(request, context, key, "reserve")).json())
        if result.binding != binding:
            raise ValueError("Reservation changed the admitted provider binding")
        return result

    async def settle(
        self,
        request: GenerationRequest,
        context: DelegatedContext,
        key: UUID,
        permit: InferencePermit,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        await self._post(request, context, key, "settle", permit, (input_tokens, output_tokens))

    async def release(self, request: GenerationRequest, context: DelegatedContext, key: UUID, permit: InferencePermit) -> None:
        await self._post(request, context, key, "release", permit)

    async def reconcile(self, request: GenerationRequest, context: DelegatedContext, key: UUID) -> InferenceReceipt:
        return InferenceReceipt.model_validate((await self._post(request, context, key, "reconcile")).json())

    async def authorize_content(self, request: GenerationContentRecoveryRequest, context: DelegatedContext, key: UUID) -> None:
        result = (await self._post(request.generation, context, key, "read-content", recovery=request)).json()
        if result != {"state": "READ_ALLOWED"}:
            raise ValueError("Content recovery owner did not authorize the exact read")

    async def close(self) -> None:
        await self.client.aclose()

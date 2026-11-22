# Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.2
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
from cryptography import x509
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
from runtime_workload_credentials import CredentialHolder, CredentialSnapshot
from workload_identity import certificate_uris


class BusinessPlatformGenerationOwner:
    key: ec.EllipticCurvePrivateKey | None
    expected_peer: str | None = None

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

    @classmethod
    def from_holder(cls, endpoint: str, holder: CredentialHolder, tls: ssl.SSLContext) -> BusinessPlatformGenerationOwner:
        """Cloud form: signing material and trust follow the verified Key Vault snapshot, rotated without restart."""
        if not endpoint.startswith("https://"):
            raise ValueError("Inference owner requires institutional HTTPS")
        owner = cls.__new__(cls)
        owner.endpoint, owner.key, owner.expected_peer = endpoint.rstrip("/"), None, None
        owner.issuer = owner.key_id = owner.audience = ""
        owner.client = httpx.AsyncClient(verify=tls, timeout=15, follow_redirects=False, trust_env=False)
        holder.subscribe(owner._rotate)
        return owner

    def _rotate(self, snapshot: CredentialSnapshot) -> None:
        target = snapshot.manifest["workloads"]["business-platform"]
        if snapshot.delegation_key_pem is None or snapshot.delegation_key_id is None:
            raise ValueError("Inference owner requires the admitted delegation key")
        key = load_pem_private_key(snapshot.delegation_key_pem, password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise ValueError("Inference owner requires the admitted ECDSA delegation key")
        self.key, self.issuer, self.key_id = key, snapshot.identity_uri, snapshot.delegation_key_id
        self.audience, self.expected_peer = str(target["audience"]), str(target["identity_uri"])

    def _verify_peer(self, response: httpx.Response) -> None:
        # Cloud leaves carry only a URI SAN, so the owner is identified by its workload URI rather than a host name.
        if self.expected_peer is None:
            return
        stream = response.extensions.get("network_stream")
        ssl_object = stream.get_extra_info("ssl_object") if stream is not None else None
        der = ssl_object.getpeercert(binary_form=True) if ssl_object is not None else None
        if not der or certificate_uris(x509.load_der_x509_certificate(der)) != [self.expected_peer]:
            raise ValueError("Inference owner peer identity mismatch")

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
        return await self._send(delegated, payload)

    async def _send(self, delegated: DelegatedContext, payload: bytes, correlation_id: str | None = None) -> httpx.Response:
        envelope = json.dumps(asdict(delegated), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        key = self.key
        if key is None:
            raise RuntimeError("Workload credential is not yet available")
        signature = key.sign(envelope, ec.ECDSA(hashes.SHA256()))
        token = ".".join(base64.urlsafe_b64encode(part).rstrip(b"=").decode() for part in (envelope, signature))
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if correlation_id is not None:
            headers["X-Correlation-Id"] = correlation_id
        response = await self.client.post(self.endpoint + delegated.route, content=payload, headers=headers)
        self._verify_peer(response)
        response.raise_for_status()
        return response

    async def resolve_provider_credential(self, provider_name: str) -> dict[str, object] | None:
        """Names the active Key Vault secret version for a provider; the reply never carries a secret value."""
        body = canonical({"providerName": provider_name})
        now = int(time.time())
        command = str(uuid4())
        delegated = DelegatedContext(
            schema_version="1.0",
            key_id=self.key_id,
            issuer_uri=self.issuer,
            target_audience=self.audience,
            method="POST",
            route="/internal/v1/provider-credentials/resolve",
            operation="resolveProviderCredential",
            contract_major=1,
            actor_subject=self.issuer,
            actor_source="WORKLOAD",
            effective_role="WORKLOAD",
            tenant_id="platform",
            relationship_id="provider-credential",
            purpose="PROVIDER_CREDENTIAL_RESOLVE",
            subject_reference=provider_name,
            request_digest=hashlib.sha256(body).hexdigest(),
            command_id=command,
            idempotency_key=None,
            expected_versions={},
            issued_at=now,
            not_before=now,
            expires_at=now + 60,
            envelope_id=str(uuid4()),
            correlation_id=command,
        )
        try:
            response = await self._send(delegated, body, command)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise
        result = response.json()
        if not isinstance(result, dict) or result.get("providerName") != provider_name:
            raise ValueError("Provider credential reference does not match the request")
        return {key: result.get(key) for key in ("secretName", "secretVersion", "authStyle")}

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

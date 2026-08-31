"""Generic Professional Runtime gateway for admitted private adapters."""

# Implements: architecture/reference/components/professional-runtime.md §7
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any, Protocol

from admission_guard import AdmissionActivationBinding, AdmissionActivationGuard, AdmissionGuardError


class AdapterGatewayError(RuntimeError):
    """Stable private gateway denial."""

    def __init__(self, code: str, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable


class AdapterClient(Protocol):  # pragma: no cover
    def describe(self) -> Any: ...

    def execute(self, envelope: Any, payload: dict[str, Any]) -> Any: ...

    def status(self, envelope: Any, invocation_id: str) -> Any: ...

    def emergency_stop(self, envelope: Any, stop_evidence_ref: str) -> dict[str, str]: ...

    def resume(self, envelope: Any) -> dict[str, str]: ...

    def result(self, envelope: Any, invocation_id: str) -> Any: ...


class InvocationStore(Protocol):  # pragma: no cover
    def create_pending(self, envelope: Any) -> None: ...

    def record_outcome(self, invocation_id: str, outcome: Any) -> None: ...

    def record_unknown(self, invocation_id: str, code: str) -> None: ...


class WorkflowDispatcher(Protocol):  # pragma: no cover
    def start(self, workflow_id: str, envelope: Any) -> None: ...


@dataclass(frozen=True)
class ActiveAdapterBinding:
    environment: str
    activation: AdmissionActivationBinding
    protocol_version: str
    conformance_digest: str
    isolation_profile: str
    private_endpoint: str
    workload_uri_san: str
    audience: str


@dataclass(frozen=True)
class ResolvedAdapter:
    binding: ActiveAdapterBinding
    client: AdapterClient


class AdapterResolver:
    """Resolve only exact ACTIVE registry entries; never guess an endpoint."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str, str], ResolvedAdapter] = {}

    def register(self, resolved: ResolvedAdapter) -> None:
        activation = resolved.binding.activation
        key = (
            resolved.binding.environment,
            activation.professional_type_id,
            activation.professional_version,
            activation.artifact_digest,
        )
        if key in self._entries:
            raise AdapterGatewayError("ADAPTER_BINDING_CONFLICT")
        self._entries[key] = resolved

    def resolve(
        self,
        environment: str,
        professional_type_id: str,
        professional_version: str,
        artifact_digest: str,
    ) -> ResolvedAdapter:
        key = (environment, professional_type_id, professional_version, artifact_digest)
        resolved = self._entries.get(key)
        if resolved is None:
            raise AdapterGatewayError("ADAPTER_NOT_ACCESSIBLE")
        return resolved


class AgentRuntimeAdapterGateway:
    """Verify activation and immutable descriptor bindings before generic dispatch."""

    def __init__(self, resolver: AdapterResolver) -> None:
        self._resolver = resolver
        self._stop_barriers: dict[tuple[str, str], str] = {}

    def resolve_and_verify(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
    ) -> ResolvedAdapter:
        resolved = self._resolver.resolve(
            environment,
            activation.professional_type_id,
            activation.professional_version,
            activation.artifact_digest,
        )
        try:
            AdmissionActivationGuard(activation.runtime_version, activation.artifact_digest).require_admitted(activation)
        except AdmissionGuardError as exc:
            raise AdapterGatewayError("ADAPTER_EXECUTION_DENIED") from exc

        binding = resolved.binding
        descriptor = resolved.client.describe()
        valid = (
            binding.isolation_profile == "ONE_ARTIFACT_PER_DEPLOYMENT"
            and binding.protocol_version == "1.0.0"
            and descriptor.protocol_version == binding.protocol_version
            and descriptor.professional_type_id == activation.professional_type_id
            and descriptor.professional_version == activation.professional_version
            and hmac.compare_digest(descriptor.artifact_digest, activation.artifact_digest)
            and hmac.compare_digest(descriptor.admission_content_digest, activation.admission_content_digest)
            and binding.private_endpoint.startswith("https://")
            and binding.workload_uri_san.startswith("spiffe://")
            and bool(binding.audience)
            and bool(binding.conformance_digest)
        )
        if not valid:
            raise AdapterGatewayError("ADAPTER_BINDING_MISMATCH")
        return resolved

    def execute(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
        envelope: Any,
        payload: dict[str, Any],
    ) -> Any:
        barrier = self._stop_barriers.get((envelope.tenant_ref, envelope.relationship_id))
        if barrier is not None:
            raise AdapterGatewayError("ADAPTER_STOPPED")
        resolved = self.resolve_and_verify(environment, activation)
        try:
            return resolved.client.execute(envelope, payload)
        except AdapterGatewayError:
            raise
        except Exception as exc:
            code = getattr(exc, "code", "ADAPTER_UNAVAILABLE")
            retryable = bool(getattr(exc, "retryable", code == "ADAPTER_UNAVAILABLE"))
            raise AdapterGatewayError(code, retryable) from exc

    def reconcile(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
        envelope: Any,
        invocation_id: str,
    ) -> Any:
        resolved = self.resolve_and_verify(environment, activation)
        return resolved.client.status(envelope, invocation_id)

    def emergency_stop(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
        envelope: Any,
        stop_evidence_ref: str,
    ) -> dict[str, str]:
        barrier_key = (envelope.tenant_ref, envelope.relationship_id)
        self._stop_barriers[barrier_key] = stop_evidence_ref
        resolved = self.resolve_and_verify(environment, activation)
        try:
            return resolved.client.emergency_stop(envelope, stop_evidence_ref)
        except Exception as exc:
            raise AdapterGatewayError("ADAPTER_UNAVAILABLE", retryable=True) from exc

    def resume(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
        envelope: Any,
    ) -> dict[str, str]:
        barrier_key = (envelope.tenant_ref, envelope.relationship_id)
        barrier = self._stop_barriers.get(barrier_key)
        if barrier is None or envelope.stop_evidence_ref != barrier:
            raise AdapterGatewayError("ADAPTER_RESUME_DENIED")
        resolved = self.resolve_and_verify(environment, activation)
        acknowledgement = resolved.client.resume(envelope)
        del self._stop_barriers[barrier_key]
        return acknowledgement

    def result(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
        envelope: Any,
        invocation_id: str,
    ) -> Any:
        resolved = self.resolve_and_verify(environment, activation)
        return resolved.client.result(envelope, invocation_id)


class AdapterInvocationCoordinator:
    """Preserve store -> workflow -> adapter ordering and reconcile ambiguous dispatch."""

    def __init__(
        self,
        gateway: AgentRuntimeAdapterGateway,
        store: InvocationStore,
        workflow_dispatcher: WorkflowDispatcher,
    ) -> None:
        self._gateway = gateway
        self._store = store
        self._workflow_dispatcher = workflow_dispatcher

    def execute(
        self,
        environment: str,
        activation: AdmissionActivationBinding,
        envelope: Any,
        payload: dict[str, Any],
    ) -> Any:
        self._gateway.resolve_and_verify(environment, activation)
        self._store.create_pending(envelope)
        self._workflow_dispatcher.start(f"ara-{envelope.invocation_id}", envelope)
        try:
            outcome = self._gateway.execute(environment, activation, envelope, payload)
        except AdapterGatewayError as exc:
            if not exc.retryable:
                self._store.record_outcome(envelope.invocation_id, exc.code)
                raise
            try:
                outcome = self._gateway.reconcile(environment, activation, envelope, envelope.invocation_id)
            except Exception:
                self._store.record_unknown(envelope.invocation_id, exc.code)
                raise AdapterGatewayError("ADAPTER_RESULT_UNRESOLVED", retryable=True) from exc
        self._store.record_outcome(envelope.invocation_id, outcome)
        return outcome

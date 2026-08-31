"""Deterministic private reference adapter with fail-closed lifecycle rules."""

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §5.3-5.6
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from .models import (
    TERMINAL_STATES,
    AdapterDescriptorV1,
    AdapterEventV1,
    AdapterInvocationEnvelopeV1,
    AdapterInvocationV1,
    AdapterResultV1,
    InvocationState,
)


_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_VERSION = re.compile(r"^1\.[0-9]+\.[0-9]+$")
_MODES = frozenset({"TRIAL", "LIVE", "PLANNING"})


class AdapterContractError(RuntimeError):
    """Stable privacy-safe adapter failure."""

    def __init__(self, code: str, correlation_id: str, retryable: bool = False) -> None:
        super().__init__(code)
        self.code = code
        self.correlation_id = correlation_id
        self.retryable = retryable


class ReferenceAdapter:
    """Common v1 adapter implementation; domain behavior is injected as a handler."""

    def __init__(
        self,
        descriptor: AdapterDescriptorV1,
        handler: Callable[[AdapterInvocationEnvelopeV1, dict[str, Any]], dict[str, Any]],
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._descriptor = descriptor
        self._handler = handler
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._invocations: dict[str, AdapterInvocationV1] = {}
        self._replays: dict[str, tuple[str, str]] = {}
        self._events: dict[str, list[AdapterEventV1]] = {}
        self._stopped_relationships: dict[str, str] = {}
        self._configuration_revisions: set[tuple[str, str, str]] = set()
        self._lock = RLock()

    def describe(self) -> AdapterDescriptorV1:
        return self._descriptor

    def health(self) -> dict[str, str]:
        return {"schemaVersion": "1.0.0", "status": "READY"}

    def configure(self, envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_envelope(envelope, consequential=False)
        revision = envelope.configuration_revision
        if revision is None:
            raise self._error("ADAPTER_REQUEST_INVALID", envelope)
        binding = (envelope.tenant_ref, envelope.relationship_id, revision)
        with self._lock:
            self._configuration_revisions.add(binding)
        return {"schemaVersion": "1.0.0", "configurationRevision": revision, "valid": bool(payload)}

    def plan(self, envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_envelope(envelope, consequential=False)
        return {
            "schemaVersion": "1.0.0",
            "invocationId": envelope.invocation_id,
            "payloadDigest": self._digest(payload),
            "sideEffects": [],
        }

    def execute(self, envelope: AdapterInvocationEnvelopeV1, payload: dict[str, Any]) -> AdapterInvocationV1:
        self._validate_envelope(envelope, consequential=True)
        with self._lock:
            replay = self._replays.get(envelope.idempotency_key)
            if replay is not None:
                prior_digest, prior_invocation_id = replay
                if not hmac.compare_digest(prior_digest, envelope.payload_digest):
                    raise self._error("ADAPTER_IDEMPOTENCY_CONFLICT", envelope)
                return self._invocations[prior_invocation_id]
            if envelope.relationship_id in self._stopped_relationships:
                raise self._error("ADAPTER_STOPPED", envelope)

            invocation = AdapterInvocationV1(envelope=envelope)
            self._invocations[envelope.invocation_id] = invocation
            self._replays[envelope.idempotency_key] = (envelope.payload_digest, envelope.invocation_id)
            self._transition(invocation, InvocationState.VALIDATING)
            self._transition(invocation, InvocationState.ACCEPTED)
            self._transition(invocation, InvocationState.RUNNING)
        try:
            output = self._handler(envelope, payload)
            with self._lock:
                if invocation.state in {InvocationState.STOPPED, InvocationState.CANCELLED}:
                    return invocation
                invocation.output = output
                invocation.completion_reason = "COMPLETED"
                self._transition(invocation, InvocationState.SUCCEEDED)
        except AdapterContractError:
            with self._lock:
                if invocation.state in TERMINAL_STATES:
                    return invocation
                invocation.completion_reason = "DOMAIN_DENIED"
                self._transition(invocation, InvocationState.FAILED)
            raise
        except Exception as exc:
            with self._lock:
                if invocation.state in TERMINAL_STATES:
                    return invocation
                invocation.completion_reason = "INTERNAL_FAILURE"
                self._transition(invocation, InvocationState.FAILED)
            raise self._error("ADAPTER_INTERNAL_FAILURE", envelope) from exc
        return invocation

    def status(self, envelope: AdapterInvocationEnvelopeV1, invocation_id: str) -> AdapterInvocationV1:
        self._validate_envelope(envelope, consequential=False)
        with self._lock:
            invocation = self._owned_invocation(envelope, invocation_id)
            return invocation

    def events(self, envelope: AdapterInvocationEnvelopeV1, invocation_id: str) -> tuple[AdapterEventV1, ...]:
        self.status(envelope, invocation_id)
        return tuple(self._events[invocation_id])

    def cancel(self, envelope: AdapterInvocationEnvelopeV1, invocation_id: str) -> AdapterInvocationV1:
        self._validate_envelope(envelope, consequential=True)
        with self._lock:
            invocation = self._owned_invocation(envelope, invocation_id)
            if invocation.state in TERMINAL_STATES:
                return invocation
            self._transition(invocation, InvocationState.CANCEL_REQUESTED)
            invocation.completion_reason = "CANCELLED_BY_PLATFORM"
            self._transition(invocation, InvocationState.CANCELLED)
            return invocation

    def emergency_stop(self, envelope: AdapterInvocationEnvelopeV1, stop_evidence_ref: str) -> dict[str, str]:
        self._validate_envelope(envelope, consequential=False, permit_expired=True)
        if not stop_evidence_ref:
            raise self._error("ADAPTER_REQUEST_INVALID", envelope)
        with self._lock:
            self._stopped_relationships[envelope.relationship_id] = stop_evidence_ref
            for invocation in self._invocations.values():
                if invocation.envelope.relationship_id != envelope.relationship_id:
                    continue
                if invocation.state not in TERMINAL_STATES:
                    self._transition(invocation, InvocationState.STOP_REQUESTED)
                    invocation.completion_reason = "EMERGENCY_STOP"
                    self._transition(invocation, InvocationState.STOPPED)
        return {
            "schemaVersion": "1.0.0",
            "relationshipId": envelope.relationship_id,
            "state": "STOPPED",
            "stopEvidenceRef": stop_evidence_ref,
        }

    def resume(self, envelope: AdapterInvocationEnvelopeV1) -> dict[str, str]:
        self._validate_envelope(envelope, consequential=True)
        with self._lock:
            stop_ref = self._stopped_relationships.get(envelope.relationship_id)
            if stop_ref is None or not envelope.stop_evidence_ref:
                raise self._error("ADAPTER_RESUME_DENIED", envelope)
            if not hmac.compare_digest(stop_ref, envelope.stop_evidence_ref):
                raise self._error("ADAPTER_RESUME_DENIED", envelope)
            del self._stopped_relationships[envelope.relationship_id]
        return {
            "schemaVersion": "1.0.0",
            "relationshipId": envelope.relationship_id,
            "state": "ELIGIBLE",
            "authorityRef": envelope.ce_decision_ref,
        }

    def result(self, envelope: AdapterInvocationEnvelopeV1, invocation_id: str) -> AdapterResultV1:
        invocation = self.status(envelope, invocation_id)
        if invocation.state not in TERMINAL_STATES:
            raise self._error("ADAPTER_RESULT_UNRESOLVED", envelope, retryable=True)
        output = invocation.output or {}
        return AdapterResultV1(
            schema_version="1.0.0",
            invocation_id=invocation_id,
            state=invocation.state,
            completion_reason=invocation.completion_reason or "UNKNOWN",
            output=output,
            output_payload_digest=self._digest(output),
            evidence_references=invocation.evidence_references,
            warnings=(),
            started_at=invocation.created_at,
            completed_at=invocation.updated_at,
        )

    def _validate_envelope(
        self,
        envelope: AdapterInvocationEnvelopeV1,
        consequential: bool,
        permit_expired: bool = False,
    ) -> None:
        try:
            UUID(envelope.invocation_id)
        except ValueError as exc:
            raise self._error("ADAPTER_REQUEST_INVALID", envelope) from exc
        descriptor = self._descriptor
        exact_binding = (
            envelope.schema_version in descriptor.compatible_minor_versions
            and _VERSION.fullmatch(envelope.schema_version)
            and envelope.professional_type_id == descriptor.professional_type_id
            and envelope.professional_version == descriptor.professional_version
            and hmac.compare_digest(envelope.admission_content_digest, descriptor.admission_content_digest)
            and hmac.compare_digest(envelope.artifact_digest, descriptor.artifact_digest)
            and descriptor.skill_versions.get(envelope.skill_id) == envelope.skill_version
        )
        if not exact_binding:
            raise self._error("ADAPTER_BINDING_MISMATCH", envelope)
        if envelope.mode not in _MODES or not all(
            (
                envelope.tenant_ref,
                envelope.relationship_id,
                envelope.customer_contract_digest,
                envelope.decision_space_version,
                envelope.idempotency_key,
                envelope.ce_decision_ref,
                envelope.evidence_context_ref,
            )
        ):
            raise self._error("ADAPTER_REQUEST_INVALID", envelope)
        if not _DIGEST.fullmatch(envelope.payload_digest):
            raise self._error("ADAPTER_REQUEST_INVALID", envelope)
        if not permit_expired and envelope.deadline_utc() <= self._now():
            raise self._error("ADAPTER_DEADLINE_EXPIRED", envelope)
        if consequential and envelope.mode == "PLANNING":
            raise self._error("ADAPTER_EXECUTION_DENIED", envelope)

    def _owned_invocation(
        self,
        envelope: AdapterInvocationEnvelopeV1,
        invocation_id: str,
    ) -> AdapterInvocationV1:
        invocation = self._invocations.get(invocation_id)
        if invocation is None:
            raise self._error("ADAPTER_NOT_ACCESSIBLE", envelope)
        owned = (
            invocation.envelope.tenant_ref == envelope.tenant_ref
            and invocation.envelope.relationship_id == envelope.relationship_id
        )
        if not owned:
            raise self._error("ADAPTER_NOT_ACCESSIBLE", envelope)
        return invocation

    def _transition(self, invocation: AdapterInvocationV1, state: InvocationState) -> None:
        invocation.state = state
        invocation.state_version += 1
        invocation.updated_at = self._now()
        self._events.setdefault(invocation.envelope.invocation_id, []).append(
            AdapterEventV1(
                event_id=str(uuid4()),
                invocation_id=invocation.envelope.invocation_id,
                sequence=invocation.state_version,
                event_type="STATE_CHANGED",
                state=state,
                timestamp=invocation.updated_at,
                payload_digest=invocation.envelope.payload_digest,
                partial=state == InvocationState.PARTIAL,
            )
        )

    @staticmethod
    def _digest(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return f"sha256:{hashlib.sha256(encoded).hexdigest()}"

    @staticmethod
    def _error(
        code: str,
        envelope: AdapterInvocationEnvelopeV1,
        retryable: bool = False,
    ) -> AdapterContractError:
        return AdapterContractError(code, envelope.correlation_id, retryable)
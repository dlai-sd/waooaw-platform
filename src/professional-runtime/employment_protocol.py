"""PR-owned durable intent and reconciliation for conversational employment."""

# Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.3 PR reuse
# Constitutional basis: C-001, C-023, C-026, C-059, C-063, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from threading import Lock
from typing import Any, ClassVar
from uuid import UUID, uuid4

from fastapi import FastAPI


class EmploymentExecutionState(StrEnum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    RECONCILING = "RECONCILING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


TERMINAL_EXECUTION_STATES = frozenset(
    {
        EmploymentExecutionState.COMPLETED,
        EmploymentExecutionState.FAILED,
        EmploymentExecutionState.BLOCKED,
    }
)


@dataclass(frozen=True)
class EmploymentExecutionBinding:
    tenant_id: str
    relationship_id: UUID
    command_id: UUID
    agent_type: str
    agent_version: str
    protocol_version: str
    manifest_version: str
    plan_version: str
    decision_space_version: int
    operation_class: str
    idempotency_key: UUID
    request_digest: str
    owner_key: str
    action_instance_id: UUID


@dataclass(frozen=True)
class EmploymentExecutionRecord:
    execution_id: UUID
    binding: EmploymentExecutionBinding
    state: EmploymentExecutionState
    state_version: int
    provider_correlation_ref: str | None
    reason_code: str | None
    accepted_at: datetime
    updated_at: datetime


class EmploymentExecutionError(RuntimeError):
    pass


class EmploymentExecutionStore:
    _transitions: ClassVar[dict[EmploymentExecutionState, set[EmploymentExecutionState]]] = {
        EmploymentExecutionState.PENDING: {
            EmploymentExecutionState.DISPATCHED,
            EmploymentExecutionState.BLOCKED,
        },
        EmploymentExecutionState.DISPATCHED: {
            EmploymentExecutionState.PARTIAL,
            EmploymentExecutionState.UNKNOWN,
            EmploymentExecutionState.COMPLETED,
            EmploymentExecutionState.FAILED,
            EmploymentExecutionState.BLOCKED,
        },
        EmploymentExecutionState.PARTIAL: {
            EmploymentExecutionState.RECONCILING,
            EmploymentExecutionState.BLOCKED,
        },
        EmploymentExecutionState.UNKNOWN: {
            EmploymentExecutionState.RECONCILING,
            EmploymentExecutionState.BLOCKED,
        },
        EmploymentExecutionState.RECONCILING: {
            EmploymentExecutionState.COMPLETED,
            EmploymentExecutionState.FAILED,
            EmploymentExecutionState.BLOCKED,
            EmploymentExecutionState.UNKNOWN,
        },
    }

    def __init__(self) -> None:
        self._records: dict[UUID, EmploymentExecutionRecord] = {}
        self._idempotency: dict[
            tuple[str, UUID, str, UUID],
            tuple[str, UUID],
        ] = {}
        self._history: dict[UUID, list[EmploymentExecutionRecord]] = {}
        self._lock = Lock()

    def reserve(
        self,
        binding: EmploymentExecutionBinding,
    ) -> tuple[EmploymentExecutionRecord, bool]:
        self._validate_binding(binding)
        identity = (
            binding.tenant_id,
            binding.relationship_id,
            binding.operation_class,
            binding.idempotency_key,
        )
        with self._lock:
            existing = self._idempotency.get(identity)
            if existing is not None:
                prior_digest, execution_id = existing
                if not hmac.compare_digest(prior_digest, binding.request_digest):
                    raise EmploymentExecutionError("EMPLOYMENT_IDEMPOTENCY_CONFLICT")
                return self._records[execution_id], True
            now = datetime.now(timezone.utc)
            record = EmploymentExecutionRecord(
                execution_id=uuid4(),
                binding=binding,
                state=EmploymentExecutionState.PENDING,
                state_version=1,
                provider_correlation_ref=None,
                reason_code=None,
                accepted_at=now,
                updated_at=now,
            )
            self._records[record.execution_id] = record
            self._history[record.execution_id] = [record]
            self._idempotency[identity] = (binding.request_digest, record.execution_id)
            return record, False

    def transition(
        self,
        execution_id: UUID,
        expected_state_version: int,
        state: EmploymentExecutionState,
        *,
        provider_correlation_ref: str | None = None,
        reason_code: str | None = None,
    ) -> EmploymentExecutionRecord:
        with self._lock:
            current = self._records.get(execution_id)
            if current is None:
                raise EmploymentExecutionError("EMPLOYMENT_EXECUTION_NOT_FOUND")
            if current.state_version != expected_state_version:
                raise EmploymentExecutionError("EMPLOYMENT_VERSION_CONFLICT")
            if current.state in TERMINAL_EXECUTION_STATES:
                raise EmploymentExecutionError("EMPLOYMENT_EXECUTION_TERMINAL")
            if state not in self._transitions.get(current.state, set()):
                raise EmploymentExecutionError("EMPLOYMENT_ILLEGAL_TRANSITION")
            if (
                state
                in {
                    EmploymentExecutionState.UNKNOWN,
                    EmploymentExecutionState.PARTIAL,
                    EmploymentExecutionState.BLOCKED,
                    EmploymentExecutionState.FAILED,
                }
                and not reason_code
            ):
                raise EmploymentExecutionError("EMPLOYMENT_REASON_REQUIRED")
            updated = replace(
                current,
                state=state,
                state_version=current.state_version + 1,
                provider_correlation_ref=provider_correlation_ref or current.provider_correlation_ref,
                reason_code=reason_code,
                updated_at=datetime.now(timezone.utc),
            )
            self._records[execution_id] = updated
            self._history[execution_id].append(updated)
            return updated

    def reconcile(self, execution_id: UUID) -> EmploymentExecutionRecord:
        with self._lock:
            current = self._records.get(execution_id)
        if current is None:
            raise EmploymentExecutionError("EMPLOYMENT_EXECUTION_NOT_FOUND")
        if current.state not in {
            EmploymentExecutionState.UNKNOWN,
            EmploymentExecutionState.PARTIAL,
        }:
            raise EmploymentExecutionError("EMPLOYMENT_RECONCILIATION_NOT_REQUIRED")
        return self.transition(
            execution_id,
            current.state_version,
            EmploymentExecutionState.RECONCILING,
        )

    def get(
        self,
        tenant_id: str,
        relationship_id: UUID,
        execution_id: UUID,
    ) -> EmploymentExecutionRecord | None:
        with self._lock:
            current = self._records.get(execution_id)
        if current is None:
            return None
        if current.binding.tenant_id != tenant_id or current.binding.relationship_id != relationship_id:
            return None
        return current

    def history(self, execution_id: UUID) -> tuple[EmploymentExecutionRecord, ...]:
        with self._lock:
            return tuple(self._history.get(execution_id, ()))

    @staticmethod
    def canonical_digest(payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
        return hashlib.sha256(canonical).hexdigest()

    @staticmethod
    def _validate_binding(binding: EmploymentExecutionBinding) -> None:
        if binding.protocol_version != "1.0-candidate":
            raise EmploymentExecutionError("EMPLOYMENT_PROTOCOL_UNSUPPORTED")
        if binding.decision_space_version < 1:
            raise EmploymentExecutionError("EMPLOYMENT_DECISION_SPACE_INVALID")
        if len(binding.request_digest) != 64 or any(value not in "0123456789abcdef" for value in binding.request_digest):
            raise EmploymentExecutionError("EMPLOYMENT_REQUEST_DIGEST_INVALID")
        if not all(
            (
                binding.tenant_id,
                binding.agent_type,
                binding.agent_version,
                binding.manifest_version,
                binding.plan_version,
                binding.operation_class,
                binding.owner_key,
            )
        ):
            raise EmploymentExecutionError("EMPLOYMENT_EXECUTION_BINDING_INCOMPLETE")


def configure_employment_protocol(application: FastAPI) -> None:
    application.state.employment_execution_store = None

"""Shared identity, configuration, idempotency, and emulator foundations."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §5, §6, §10, §11, §13
# Constitutional basis: C-001, C-041, C-059, C-063, C-078, C-080

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse


class CdeReason(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    NOT_ACCESSIBLE = "NOT_ACCESSIBLE"
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHORITY_DENIED = "AUTHORITY_DENIED"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    SUPPRESSED = "SUPPRESSED"
    BUDGET_UNAVAILABLE = "BUDGET_UNAVAILABLE"
    ACCOUNT_UNSUPPORTED = "ACCOUNT_UNSUPPORTED"
    CAPABILITY_STALE = "CAPABILITY_STALE"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    STOPPED = "STOPPED"


class CdeDenied(ValueError):
    def __init__(self, reason: CdeReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True)
class ExecutionCoordinates:
    environment: str
    tenant_ref: str
    relationship_ref: str
    instance_ref: str
    package: str
    operation: str
    actor_ref: str
    authority_ref: str
    purpose: str
    evidence_ref: str
    deadline_at: datetime

    def require_same_boundary(self, other: ExecutionCoordinates) -> None:
        protected = (
            "environment",
            "tenant_ref",
            "relationship_ref",
            "instance_ref",
        )
        if any(getattr(self, name) != getattr(other, name) for name in protected):
            raise CdeDenied(CdeReason.NOT_ACCESSIBLE)


@dataclass(frozen=True)
class MutationIntent:
    intent_id: str
    idempotency_key: str
    request_digest: str
    coordinates: ExecutionCoordinates
    owner_versions: tuple[str, ...]


@dataclass(frozen=True)
class IntentResult:
    intent_id: str
    request_digest: str
    state: str
    correlation_ref: str | None = None


def canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def require_reference(value: str, *, expected_scheme: str, environment: str) -> str:
    normalized = value.strip()
    lowered = normalized.lower()
    if (
        not normalized
        or any(marker in lowered for marker in ("changeme", "placeholder", "fixture"))
        or ".invalid" in lowered
        or lowered.startswith("unresolved:")
        or "{" in normalized
        or "}" in normalized
    ):
        raise CdeDenied(CdeReason.NOT_CONFIGURED)
    parsed = urlparse(normalized)
    if parsed.scheme != expected_scheme or parsed.netloc != environment:
        raise CdeDenied(CdeReason.NOT_CONFIGURED)
    if not parsed.path.strip("/"):
        raise CdeDenied(CdeReason.NOT_CONFIGURED)
    return normalized


def safe_diagnostics(values: Mapping[str, Any]) -> dict[str, str]:
    prohibited = {
        "token",
        "secret",
        "authorization",
        "email",
        "phone",
        "audience",
        "lead",
        "content",
        "payload",
    }
    return {
        key: "[REDACTED]" if any(marker in key.lower() for marker in prohibited) else str(value)
        for key, value in values.items()
    }


class DeterministicOwnerEmulator:
    def __init__(self) -> None:
        self._results: dict[str, IntentResult] = {}
        self._stopped_scopes: set[tuple[str, str, str, str]] = set()
        self.dispatch_count = 0

    def stop(self, coordinates: ExecutionCoordinates) -> None:
        self._stopped_scopes.add(self._scope(coordinates))

    def submit(self, intent: MutationIntent, *, outcome: str = "ACCEPTED") -> IntentResult:
        if self._scope(intent.coordinates) in self._stopped_scopes:
            raise CdeDenied(CdeReason.STOPPED)
        previous = self._results.get(intent.idempotency_key)
        if previous:
            if previous.request_digest != intent.request_digest:
                raise CdeDenied(CdeReason.IDEMPOTENCY_CONFLICT)
            return previous
        self.dispatch_count += 1
        result = IntentResult(
            intent_id=intent.intent_id,
            request_digest=intent.request_digest,
            state=outcome,
            correlation_ref=f"emulator:{intent.intent_id}",
        )
        self._results[intent.idempotency_key] = result
        return result

    def reconcile(self, idempotency_key: str, *, verified_state: str) -> IntentResult:
        current = self._results.get(idempotency_key)
        if current is None:
            raise CdeDenied(CdeReason.OUTCOME_UNKNOWN)
        reconciled = IntentResult(
            intent_id=current.intent_id,
            request_digest=current.request_digest,
            state=verified_state,
            correlation_ref=current.correlation_ref,
        )
        self._results[idempotency_key] = reconciled
        return reconciled

    @staticmethod
    def _scope(coordinates: ExecutionCoordinates) -> tuple[str, str, str, str]:
        return (
            coordinates.environment,
            coordinates.tenant_ref,
            coordinates.relationship_ref,
            coordinates.instance_ref,
        )

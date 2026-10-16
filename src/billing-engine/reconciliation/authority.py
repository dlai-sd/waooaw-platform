"""PostgreSQL authority for Billing integrity and reconciliation."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §8
# Constitutional basis: C-002, C-023, C-026, C-059, C-080, C-091

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BillingAuthorityError(RuntimeError):
    """Base error for fail-closed Billing authority decisions."""


class BillingIntegrityHaltedError(BillingAuthorityError):
    """Consequential Billing work is denied by durable integrity state."""


class ReconciliationConflictError(BillingAuthorityError):
    """A durable execution identity was reused with a different payload."""


@dataclass(frozen=True)
class ReconciliationIdentity:
    environment: str
    tenant_id: uuid.UUID
    accounting_scope_id: uuid.UUID
    reconciliation_type: str
    covered_period_start: datetime
    covered_period_end: datetime
    source_watermark: str

    def canonical_key(self) -> str:
        return _digest(
            {
                "accounting_scope_id": str(self.accounting_scope_id),
                "covered_period_end": _utc(self.covered_period_end),
                "covered_period_start": _utc(self.covered_period_start),
                "environment": self.environment,
                "reconciliation_type": self.reconciliation_type,
                "source_watermark": self.source_watermark,
                "tenant_id": str(self.tenant_id),
            }
        )


@dataclass(frozen=True)
class ExecutionClaim:
    execution_id: uuid.UUID
    status: str
    replayed: bool


def _utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("reconciliation timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class BillingAuthority:
    """Transaction-bound access to durable Billing authority."""

    def __init__(self, session: AsyncSession, environment: str) -> None:
        self._session = session
        self._environment = environment

    async def _set_scope(self, tenant_id: uuid.UUID) -> None:
        if self._session.get_bind().dialect.name == "sqlite":
            return
        await self._session.execute(
            text(
                """
                SELECT
                    set_config('app.current_environment', :environment, true),
                    set_config('app.current_tenant_id', :tenant_id, true)
                """
            ),
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
            },
        )

    async def _integrity_state(
        self,
        *,
        tenant_id: uuid.UUID,
        accounting_scope_id: uuid.UUID,
    ) -> str | None:
        base_query = """
            SELECT state
            FROM integrity_states
            WHERE environment = :environment
              AND tenant_id = :tenant_id
              AND accounting_scope_id = :accounting_scope_id
        """
        statement = text(
            base_query
            if self._session.get_bind().dialect.name == "sqlite"
            else base_query + " FOR UPDATE"
        )
        result = await self._session.execute(
            statement,
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
            },
        )
        row = result.fetchone()
        return None if row is None else str(row[0])

    async def assert_writes_allowed(
        self,
        *,
        tenant_id: uuid.UUID,
        accounting_scope_id: uuid.UUID,
    ) -> None:
        await self._set_scope(tenant_id)
        result = await self._session.execute(
            text(
                """
                SELECT state
                FROM integrity_states
                WHERE environment = :environment
                  AND tenant_id = :tenant_id
                  AND accounting_scope_id = :accounting_scope_id
                """
            ),
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
            },
        )
        row = result.fetchone()
        if row is None or row[0] != "CLEAR":
            raise BillingIntegrityHaltedError(
                "Billing suspended pending authoritative reconciliation"
            )

    async def claim_execution(
        self,
        identity: ReconciliationIdentity,
        payload: object,
    ) -> ExecutionClaim:
        if identity.environment != self._environment:
            raise ReconciliationConflictError("reconciliation environment mismatch")
        if not identity.reconciliation_type.strip() or not identity.source_watermark.strip():
            raise ValueError("reconciliation type and source watermark are required")
        await self._set_scope(identity.tenant_id)
        execution_key = identity.canonical_key()
        payload_digest = _digest(payload)
        execution_id = uuid.uuid4()
        await self._session.execute(
            text(
                """
                INSERT INTO reconciliation_executions (
                    execution_id, environment, tenant_id, accounting_scope_id,
                    reconciliation_type, covered_period_start, covered_period_end,
                    source_watermark, execution_key, payload_digest, status
                )
                VALUES (
                    :execution_id, :environment, :tenant_id, :accounting_scope_id,
                    :reconciliation_type, :covered_period_start, :covered_period_end,
                    :source_watermark, :execution_key, :payload_digest, 'CLAIMED'
                )
                ON CONFLICT (execution_key) DO NOTHING
                """
            ),
            {
                "execution_id": str(execution_id),
                "environment": identity.environment,
                "tenant_id": str(identity.tenant_id),
                "accounting_scope_id": str(identity.accounting_scope_id),
                "reconciliation_type": identity.reconciliation_type,
                "covered_period_start": identity.covered_period_start,
                "covered_period_end": identity.covered_period_end,
                "source_watermark": identity.source_watermark,
                "execution_key": execution_key,
                "payload_digest": payload_digest,
            },
        )
        base_query = """
            SELECT execution_id, payload_digest, status
            FROM reconciliation_executions
            WHERE execution_key = :execution_key
        """
        statement = text(
            base_query
            if self._session.get_bind().dialect.name == "sqlite"
            else base_query + " FOR UPDATE"
        )
        result = await self._session.execute(
            statement,
            {"execution_key": execution_key},
        )
        row = result.one()
        if row.payload_digest != payload_digest:
            raise ReconciliationConflictError(
                "reconciliation identity was reused with a different payload"
            )
        return ExecutionClaim(
            execution_id=uuid.UUID(str(row.execution_id)),
            status=str(row.status),
            replayed=uuid.UUID(str(row.execution_id)) != execution_id,
        )

    async def record_halt(
        self,
        *,
        execution_id: uuid.UUID,
        tenant_id: uuid.UUID,
        accounting_scope_id: uuid.UUID,
        discrepancy_paise: int,
        expected_paise: int,
        actual_paise: int,
        actor_id: str,
        authority_reference: str,
        evidence_reference: str,
        reason: str,
        result_digest: str,
    ) -> uuid.UUID:
        if discrepancy_paise <= 1:
            raise ValueError("a Billing integrity halt requires discrepancy greater than one paise")
        if abs(actual_paise - expected_paise) != discrepancy_paise:
            raise ValueError("discrepancy does not match expected and actual amounts")
        if not all(
            value.strip()
            for value in (actor_id, authority_reference, evidence_reference, reason, result_digest)
        ):
            raise ValueError("halt authority and evidence fields are required")
        await self._set_scope(tenant_id)
        event_id = uuid.uuid4()
        outcome_id = uuid.uuid4()
        audit_result_id = uuid.uuid4()
        recorded_at = datetime.now(timezone.utc)
        prior_state = (
            await self._integrity_state(
                tenant_id=tenant_id,
                accounting_scope_id=accounting_scope_id,
            )
            or "CLEAR"
        )
        await self._session.execute(
            text(
                """
                INSERT INTO integrity_events (
                    event_id, environment, tenant_id, accounting_scope_id, event_type,
                    prior_state, resulting_state, discrepancy_paise, actor_id,
                    authority_reference, reason, evidence_reference
                )
                VALUES (
                    :event_id, :environment, :tenant_id, :accounting_scope_id, 'HALT',
                    :prior_state,
                    'HALTED', :discrepancy_paise, :actor_id,
                    :authority_reference, :reason, :evidence_reference
                )
                """
            ),
            {
                "event_id": str(event_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "prior_state": prior_state,
                "discrepancy_paise": discrepancy_paise,
                "actor_id": actor_id,
                "authority_reference": authority_reference,
                "reason": reason,
                "evidence_reference": evidence_reference,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO reconciliation_outcomes (
                    outcome_id, execution_id, environment, tenant_id,
                    accounting_scope_id, outcome, discrepancy_paise,
                    result_digest, evidence_reference, committed_at
                )
                VALUES (
                    :outcome_id, :execution_id, :environment, :tenant_id,
                    :accounting_scope_id, 'HALTED', :discrepancy_paise,
                    :result_digest, :evidence_reference, :recorded_at
                )
                ON CONFLICT (execution_id) DO NOTHING
                """
            ),
            {
                "outcome_id": str(outcome_id),
                "execution_id": str(execution_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "discrepancy_paise": discrepancy_paise,
                "result_digest": result_digest,
                "evidence_reference": evidence_reference,
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO discrepancy_evidence (
                    evidence_id, execution_id, outcome_id, environment, tenant_id,
                    accounting_scope_id, subject_type, subject_reference,
                    expected_paise, actual_paise, evidence_reference
                )
                VALUES (
                    :evidence_id, :execution_id, :outcome_id, :environment, :tenant_id,
                    :accounting_scope_id, 'WALLET_BUCKET', :subject_reference,
                    :expected_paise, :actual_paise, :evidence_reference
                )
                """
            ),
            {
                "evidence_id": str(uuid.uuid4()),
                "execution_id": str(execution_id),
                "outcome_id": str(outcome_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "subject_reference": str(accounting_scope_id),
                "expected_paise": expected_paise,
                "actual_paise": actual_paise,
                "evidence_reference": evidence_reference,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO audit_results (
                    audit_result_id, execution_id, environment, tenant_id,
                    accounting_scope_id, audit_type, outcome, result_digest,
                    evidence_reference, completed_at
                )
                VALUES (
                    :audit_result_id, :execution_id, :environment, :tenant_id,
                    :accounting_scope_id, 'SELF_AUDIT', 'HALTED', :result_digest,
                    :evidence_reference, :recorded_at
                )
                ON CONFLICT (audit_result_id) DO NOTHING
                """
            ),
            {
                "audit_result_id": str(audit_result_id),
                "execution_id": str(execution_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "result_digest": result_digest,
                "evidence_reference": evidence_reference,
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO audit_projections (
                    environment, tenant_id, accounting_scope_id, audit_type,
                    last_audit_result_id, last_completed_at, projection_version
                )
                VALUES (
                    :environment, :tenant_id, :accounting_scope_id, 'SELF_AUDIT',
                    :audit_result_id, :recorded_at, 1
                )
                ON CONFLICT (environment, tenant_id, accounting_scope_id, audit_type)
                DO UPDATE SET
                    last_audit_result_id = EXCLUDED.last_audit_result_id,
                    last_completed_at = EXCLUDED.last_completed_at,
                    projection_version = audit_projections.projection_version + 1
                """
            ),
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "audit_result_id": str(audit_result_id),
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO integrity_states (
                    environment, tenant_id, accounting_scope_id, state,
                    active_halt_event_id, state_version, updated_at
                )
                VALUES (
                    :environment, :tenant_id, :accounting_scope_id, 'HALTED',
                    :event_id, 1, :recorded_at
                )
                ON CONFLICT (environment, tenant_id, accounting_scope_id)
                DO UPDATE SET
                    state = 'HALTED',
                    active_halt_event_id = EXCLUDED.active_halt_event_id,
                    state_version = integrity_states.state_version + 1,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "event_id": str(event_id),
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                UPDATE reconciliation_executions
                SET status = 'COMMITTED', updated_at = :recorded_at
                WHERE execution_id = :execution_id
                """
            ),
            {"execution_id": str(execution_id), "recorded_at": recorded_at},
        )
        return event_id

    async def record_pass(
        self,
        *,
        execution_id: uuid.UUID,
        tenant_id: uuid.UUID,
        accounting_scope_id: uuid.UUID,
        discrepancy_paise: int,
        evidence_reference: str,
        result_digest: str,
    ) -> uuid.UUID:
        await self._set_scope(tenant_id)
        outcome_id = uuid.uuid4()
        audit_result_id = uuid.uuid4()
        recorded_at = datetime.now(timezone.utc)
        await self._session.execute(
            text(
                """
                INSERT INTO reconciliation_outcomes (
                    outcome_id, execution_id, environment, tenant_id,
                    accounting_scope_id, outcome, discrepancy_paise,
                    result_digest, evidence_reference, committed_at
                )
                VALUES (
                    :outcome_id, :execution_id, :environment, :tenant_id,
                    :accounting_scope_id, 'PASS', :discrepancy_paise,
                    :result_digest, :evidence_reference, :recorded_at
                )
                ON CONFLICT (execution_id) DO NOTHING
                """
            ),
            {
                "outcome_id": str(outcome_id),
                "execution_id": str(execution_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "discrepancy_paise": discrepancy_paise,
                "result_digest": result_digest,
                "evidence_reference": evidence_reference,
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO audit_results (
                    audit_result_id, execution_id, environment, tenant_id,
                    accounting_scope_id, audit_type, outcome, result_digest,
                    evidence_reference, completed_at
                )
                VALUES (
                    :audit_result_id, :execution_id, :environment, :tenant_id,
                    :accounting_scope_id, 'SELF_AUDIT', 'PASS', :result_digest,
                    :evidence_reference, :recorded_at
                )
                """
            ),
            {
                "audit_result_id": str(audit_result_id),
                "execution_id": str(execution_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "result_digest": result_digest,
                "evidence_reference": evidence_reference,
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO audit_projections (
                    environment, tenant_id, accounting_scope_id, audit_type,
                    last_audit_result_id, last_completed_at, projection_version
                )
                VALUES (
                    :environment, :tenant_id, :accounting_scope_id, 'SELF_AUDIT',
                    :audit_result_id, :recorded_at, 1
                )
                ON CONFLICT (environment, tenant_id, accounting_scope_id, audit_type)
                DO UPDATE SET
                    last_audit_result_id = EXCLUDED.last_audit_result_id,
                    last_completed_at = EXCLUDED.last_completed_at,
                    projection_version = audit_projections.projection_version + 1
                """
            ),
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "audit_result_id": str(audit_result_id),
                "recorded_at": recorded_at,
            },
        )
        await self._session.execute(
            text(
                """
                UPDATE reconciliation_executions
                SET status = 'COMMITTED', updated_at = :recorded_at
                WHERE execution_id = :execution_id
                """
            ),
            {"execution_id": str(execution_id), "recorded_at": recorded_at},
        )
        return outcome_id

    async def release_halt(
        self,
        *,
        tenant_id: uuid.UUID,
        accounting_scope_id: uuid.UUID,
        actor_id: str,
        authority_reference: str,
        reason: str,
        evidence_reference: str,
    ) -> uuid.UUID:
        if not all(
            value.strip()
            for value in (actor_id, authority_reference, reason, evidence_reference)
        ):
            raise ValueError("halt release authority and evidence fields are required")
        await self._set_scope(tenant_id)
        state = await self._integrity_state(
            tenant_id=tenant_id,
            accounting_scope_id=accounting_scope_id,
        )
        if state not in {"HALTED", "RECONCILIATION_REQUIRED"}:
            raise BillingAuthorityError("no releasable Billing halt exists")
        event_id = uuid.uuid4()
        recorded_at = datetime.now(timezone.utc)
        await self._session.execute(
            text(
                """
                INSERT INTO integrity_events (
                    event_id, environment, tenant_id, accounting_scope_id, event_type,
                    prior_state, resulting_state, actor_id, authority_reference,
                    reason, evidence_reference
                )
                VALUES (
                    :event_id, :environment, :tenant_id, :accounting_scope_id, 'RELEASE',
                    :prior_state, 'CLEAR', :actor_id, :authority_reference,
                    :reason, :evidence_reference
                )
                """
            ),
            {
                "event_id": str(event_id),
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "prior_state": state,
                "actor_id": actor_id,
                "authority_reference": authority_reference,
                "reason": reason,
                "evidence_reference": evidence_reference,
            },
        )
        await self._session.execute(
            text(
                """
                UPDATE integrity_states
                SET state = 'CLEAR',
                    active_halt_event_id = NULL,
                    state_version = state_version + 1,
                    updated_at = :recorded_at
                WHERE environment = :environment
                  AND tenant_id = :tenant_id
                  AND accounting_scope_id = :accounting_scope_id
                """
            ),
            {
                "environment": self._environment,
                "tenant_id": str(tenant_id),
                "accounting_scope_id": str(accounting_scope_id),
                "recorded_at": recorded_at,
            },
        )
        return event_id

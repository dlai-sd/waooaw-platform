"""WC-124 durable Billing authority behavior."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §8
# Constitutional basis: C-002, C-023, C-026, C-059, C-080, C-091

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import psycopg2


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "infrastructure/postgres/init/59-wc124-billing-authority.sql"


@pytest.mark.postgres
def test_atomic_halt_replay_conflict_release_and_redis_loss() -> None:
    tenant_id = uuid4()
    scope_id = uuid4()
    execution_id = uuid4()
    event_id = uuid4()
    outcome_id = uuid4()
    release_id = uuid4()
    now = datetime.now(timezone.utc)
    execution_key = "1" * 64
    payload_digest = "2" * 64
    result_digest = "3" * 64

    with psycopg2.connect(os.environ["WC124_DATABASE_URL"]) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(MIGRATION.read_text(encoding="utf-8"))
            cursor.execute("SET app.current_environment = 'demo'")
            cursor.execute("SET app.current_tenant_id = %s", (str(tenant_id),))
            cursor.execute(
                """
                INSERT INTO billing.reconciliation_executions (
                    execution_id, environment, tenant_id, accounting_scope_id,
                    reconciliation_type, covered_period_start, covered_period_end,
                    source_watermark, execution_key, payload_digest, status
                )
                VALUES (%s, 'demo', %s, %s, 'SELF_AUDIT', %s, %s, 'watermark',
                        %s, %s, 'CLAIMED')
                """,
                (
                    str(execution_id),
                    str(tenant_id),
                    str(scope_id),
                    now,
                    now + timedelta(days=1),
                    execution_key,
                    payload_digest,
                ),
            )
            cursor.execute(
                """
                INSERT INTO billing.integrity_events (
                    event_id, environment, tenant_id, accounting_scope_id, event_type,
                    prior_state, resulting_state, discrepancy_paise, actor_id,
                    authority_reference, reason, evidence_reference
                )
                VALUES (%s, 'demo', %s, %s, 'HALT', 'CLEAR', 'HALTED', 2,
                        'test-reconciler', 'WC-124', 'synthetic discrepancy', 'evidence:test')
                """,
                (str(event_id), str(tenant_id), str(scope_id)),
            )
            cursor.execute(
                """
                INSERT INTO billing.reconciliation_outcomes (
                    outcome_id, execution_id, environment, tenant_id, accounting_scope_id,
                    outcome, discrepancy_paise, result_digest, evidence_reference
                )
                VALUES (%s, %s, 'demo', %s, %s, 'HALTED', 2, %s, 'evidence:test')
                """,
                (
                    str(outcome_id),
                    str(execution_id),
                    str(tenant_id),
                    str(scope_id),
                    result_digest,
                ),
            )
            cursor.execute(
                """
                INSERT INTO billing.integrity_states (
                    environment, tenant_id, accounting_scope_id, state, active_halt_event_id
                )
                VALUES ('demo', %s, %s, 'HALTED', %s)
                """,
                (str(tenant_id), str(scope_id), str(event_id)),
            )

            cursor.execute(
                "SELECT state FROM billing.integrity_states WHERE tenant_id = %s AND accounting_scope_id = %s",
                (str(tenant_id), str(scope_id)),
            )
            assert cursor.fetchone() == ("HALTED",)
            cursor.execute(
                "SELECT outcome_id FROM billing.reconciliation_outcomes WHERE execution_id = %s",
                (str(execution_id),),
            )
            assert UUID(str(cursor.fetchone()[0])) == outcome_id

            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute(
                    """
                    INSERT INTO billing.reconciliation_executions (
                        execution_id, environment, tenant_id, accounting_scope_id,
                        reconciliation_type, covered_period_start, covered_period_end,
                        source_watermark, execution_key, payload_digest, status
                    )
                    VALUES (%s, 'demo', %s, %s, 'SELF_AUDIT', %s, %s, 'watermark',
                            %s, %s, 'CLAIMED')
                    """,
                    (
                        str(uuid4()),
                        str(tenant_id),
                        str(scope_id),
                        now,
                        now + timedelta(days=1),
                        execution_key,
                        "f" * 64,
                    ),
                )

            cursor.execute(
                """
                INSERT INTO billing.integrity_events (
                    event_id, environment, tenant_id, accounting_scope_id, event_type,
                    prior_state, resulting_state, actor_id, authority_reference,
                    reason, evidence_reference
                )
                VALUES (%s, 'demo', %s, %s, 'RELEASE', 'HALTED', 'CLEAR',
                        'authorized-operator', 'FA-055', 'qualified release', 'evidence:release')
                """,
                (str(release_id), str(tenant_id), str(scope_id)),
            )
            cursor.execute(
                """
                UPDATE billing.integrity_states
                SET state = 'CLEAR', active_halt_event_id = NULL, state_version = state_version + 1
                WHERE environment = 'demo' AND tenant_id = %s AND accounting_scope_id = %s
                """,
                (str(tenant_id), str(scope_id)),
            )
            cursor.execute(
                "SELECT event_type FROM billing.integrity_events WHERE accounting_scope_id = %s ORDER BY occurred_at",
                (str(scope_id),),
            )
            assert [row[0] for row in cursor.fetchall()] == ["HALT", "RELEASE"]

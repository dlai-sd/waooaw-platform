"""WC-124 Billing authority migration and cutover contracts."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§8-9.1
# Constitutional basis: C-005, C-023, C-026, C-059, C-080, C-091

from pathlib import Path

import pytest
import psycopg2
import yaml


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "infrastructure/postgres/init/59-wc124-billing-authority.sql"
PRINCIPALS = ROOT / "infrastructure/postgres/init/00-wc124-principal-bootstrap.sql"
HANDOFF = ROOT / "infrastructure/postgres/init/60-wc124-principal-handoff.sql"
LEDGER = ROOT / "work-contracts/WC-124-dataset-cutover-ledger.yaml"

TABLES = {
    "integrity_states",
    "integrity_events",
    "reconciliation_executions",
    "reconciliation_outcomes",
    "discrepancy_evidence",
    "audit_results",
    "audit_projections",
}


def test_migration_is_expand_only_and_declares_every_authority_object() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()

    assert "drop table" not in lowered
    assert "drop schema" not in lowered
    assert "truncate " not in lowered
    assert "create schema" not in lowered
    assert "create role" not in lowered
    assert "set local role billing_owner" in lowered
    assert "billing schema must be provisioned before migration" in lowered
    for table in TABLES:
        assert f"create table if not exists billing.{table}" in lowered
    assert "enable row level security" in lowered
    assert "force row level security" in lowered
    assert "app.current_environment" in lowered
    assert "app.current_tenant_id" in lowered
    assert "grant select on all tables in schema billing to billing_verifier" in lowered
    assert "grant all" not in lowered
    assert "bypassrls" not in lowered.replace("nobypassrls", "")


def test_complete_principal_inventory_is_non_owner_and_nobypassrls() -> None:
    bootstrap = PRINCIPALS.read_text(encoding="utf-8").lower()
    handoff = HANDOFF.read_text(encoding="utf-8").lower()
    for prefix in (
        "keycloak",
        "temporal",
        "ce",
        "bp",
        "pr",
        "air",
        "billing",
        "web_session",
    ):
        assert f"'{prefix}_owner'" in bootstrap
        assert f"'{prefix}_verifier'" in bootstrap
        assert f"'{prefix}_migrator'" in bootstrap
    for runtime in (
        "keycloak_runtime",
        "temporal_runtime",
        "ce_runtime",
        "bp_runtime",
        "pr_runtime",
        "air_runtime",
        "billing_runtime",
        "web_session_app",
    ):
        assert f"'{runtime}'" in bootstrap
    assert "login nosuperuser nobypassrls" in bootstrap
    assert "nologin nosuperuser nobypassrls" in bootstrap
    assert "grant billing_owner to billing_migrator" in bootstrap
    assert "create schema if not exists billing authorization billing_owner" in bootstrap
    assert "alter schema billing owner to billing_owner" in bootstrap
    # Transaction-mode PgBouncer rejects search_path as a startup parameter; the runtime relies
    # on this server-side role default for its unqualified table names.
    assert "alter role billing_runtime set search_path = billing, business, institutional, public" in bootstrap
    assert "revoke all on schema public from public" in handoff
    assert "d.deptype in ('a', 'i')" in handoff
    assert "force row level security" in handoff


def test_cutover_ledger_is_closed_world_demo_only_and_not_executed() -> None:
    ledger = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    expected_fields = {
        "source_revision_digest",
        "source_volume_id",
        "fence_timestamp",
        "source_watermark",
        "target_watermark",
        "schema_digest",
        "reconciliation_digest",
        "rollback_point",
    }

    assert ledger["schema"] == "waooaw.wc124-dataset-cutover-ledger/v1"
    assert ledger["status"] == "FOUNDER_AUTHORIZED_NOT_EXECUTED"
    assert ledger["synthetic_discard_authority"] == {
        "status": "FOUNDER_AUTHORIZED",
        "authorized_at": "2026-10-17T05:29:58Z",
        "scope": "demo_ephemeral_sidecars_only",
        "decision": "discard_current_demo_sidecar_content_and_reseed_persistent_postgresql",
        "basis": "legacy_demo_sidecars_use_EmptyDir_and_delete_then_reseed_on_revision_start",
        "excludes": ["uat", "prod"],
        "provider_mutation_authority": "none",
    }
    assert ledger["source_deletion_authority"]["status"] == "DECISION_AUTHORIZED_EXECUTION_BLOCKED"
    assert ledger["source_deletion_authority"]["execution_requires"] == (
        "separate_founder_deployment_and_traffic_authorization"
    )
    assert ledger["uat_disposition"] == "PRESERVE_AND_DEFER_MIGRATION"
    assert ledger["production_disposition"] == "OUT_OF_SCOPE_PRESERVE"
    assert [row["dataset"] for row in ledger["datasets"]] == [
        "constitutional_engine",
        "business_platform",
        "billing",
        "demo_temporal",
    ]
    for row in ledger["datasets"]:
        assert row["environment"] == "demo"
        assert row["migration_method"] == "synthetic_discard_and_clean_reseed"
        assert row["status"] == "FOUNDER_AUTHORIZED_NOT_EXECUTED"
        assert row["consistency"]
        assert row["write_fence"]
        assert set(row["generated_fields"]) == expected_fields
        assert set(row["generated_fields"].values()) == {"required_at_execution"}


@pytest.mark.postgres
def test_migration_reapplies_and_enforces_roles_rls_and_append_only_history(
    db_conn,
) -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    with db_conn.cursor() as cursor:
        cursor.execute(sql)
        cursor.execute(sql)

        cursor.execute(
            """
            SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls
            FROM pg_roles
            WHERE rolname IN ('billing_owner', 'billing_migrator', 'billing_runtime', 'billing_verifier')
            ORDER BY rolname
            """
        )
        roles = cursor.fetchall()
        assert [row[0] for row in roles] == [
            "billing_migrator",
            "billing_owner",
            "billing_runtime",
            "billing_verifier",
        ]
        assert all(row[1:] == (False, False, False, False) for row in roles)

        cursor.execute(
            """
            SELECT relname, relrowsecurity, relforcerowsecurity
            FROM pg_class
            JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
            WHERE nspname = 'billing' AND relkind = 'r'
              AND relname = ANY(%s)
            ORDER BY relname
            """,
            (list(TABLES),),
        )
        rows = cursor.fetchall()
        assert {row[0] for row in rows} == TABLES
        assert all(row[1:] == (True, True) for row in rows)

        cursor.execute(
            """
            SELECT table_name, privilege_type
            FROM information_schema.role_table_grants
            WHERE grantee = 'billing_runtime'
              AND table_schema = 'billing'
              AND privilege_type IN ('DELETE', 'TRUNCATE', 'TRIGGER', 'REFERENCES')
            """
        )
        assert cursor.fetchall() == []

        cursor.execute(
            """
            INSERT INTO billing.integrity_events (
                event_id, environment, tenant_id, accounting_scope_id, event_type,
                prior_state, resulting_state, discrepancy_paise, actor_id,
                authority_reference, reason, evidence_reference
            )
            VALUES (
                '00000000-0000-0000-0000-000000000124',
                'demo',
                '00000000-0000-0000-0000-000000000001',
                '00000000-0000-0000-0000-000000000002',
                'HALT', 'CLEAR', 'HALTED', 2, 'wc124-test',
                'WC-124', 'synthetic migration qualification', 'evidence:wc124-test'
            )
            ON CONFLICT (event_id) DO NOTHING
            """
        )
        with pytest.raises(psycopg2.errors.RaiseException, match="append-only"):
            cursor.execute(
                """
                UPDATE billing.integrity_events
                SET reason = 'mutation must fail'
                WHERE event_id = '00000000-0000-0000-0000-000000000124'
                """
            )
        db_conn.rollback()

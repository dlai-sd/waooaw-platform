# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
# Constitutional basis: C-005, C-023, C-059, C-063, ADR-051
"""The component-unit outbox migration keeps tenant isolation and a closed worker surface."""

from __future__ import annotations

import re
from pathlib import Path

SQL = (
    Path(__file__).resolve().parents[2]
    / "infrastructure/postgres/init/99zzzzzzzz-wc136-15-component-unit-outbox.sql"
)


def _sql() -> str:
    return SQL.read_text(encoding="utf-8")


def test_the_outbox_is_tenant_isolated_and_idempotent_on_the_evidence_id():
    sql = _sql()

    assert "CREATE TABLE IF NOT EXISTS business.component_unit_outbox" in sql
    assert "ALTER TABLE business.component_unit_outbox FORCE ROW LEVEL SECURITY" in sql
    assert "DROP POLICY IF EXISTS component_unit_outbox_tenant_isolation" in sql
    assert "app.current_tenant_id" in sql
    assert "UNIQUE (tenant_id, relationship_id, component_id, completion_evidence_id)" in sql


def test_the_customer_role_can_only_read_and_insert_rows_never_change_them():
    sql = _sql()

    grants = re.findall(r"GRANT ([A-Z, ]+) ON business\.component_unit_outbox TO business_app", sql)
    assert grants == ["SELECT, INSERT"]
    assert "REVOKE ALL ON business.component_unit_outbox FROM PUBLIC, business_app" in sql


def test_the_worker_surface_is_two_owner_defined_functions_with_a_pinned_search_path():
    sql = _sql()

    for name in ("claim_component_unit_work", "mark_component_unit_work"):
        assert f"CREATE OR REPLACE FUNCTION business.{name}(" in sql
        assert re.search(rf"FROM PUBLIC, business_app;\s*GRANT EXECUTE ON FUNCTION business\.{name}\(", sql)
    assert sql.count("SECURITY DEFINER") == 2
    assert sql.count("SET search_path = pg_catalog SET row_security = on") == 2
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "work.state = 'LEASED'" in sql


def test_every_statement_is_replayable():
    sql = _sql()

    assert not re.search(r"^\s*CREATE (TABLE|INDEX) (?!IF NOT EXISTS)", sql, re.MULTILINE)
    assert not re.search(r"^\s*CREATE POLICY", sql[: sql.index("DROP POLICY IF EXISTS")], re.MULTILINE)

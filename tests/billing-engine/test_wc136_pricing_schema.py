# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-05, C4-07
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""SQL-text contracts of the WC-136 pricing version, package key and thread catalogue init files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from wc124_init_chain_lint import lint_sql

ROOT = Path(__file__).resolve().parents[2]
INIT = ROOT / "infrastructure/postgres/init"
VERSIONS = INIT / "99zzzzzzzz-wc136-07-pricing-versions.sql"
CATALOGUE = INIT / "99zzzzzzzz-wc136-08-thread-catalogue-pending.sql"
COMPENSATING = ROOT / "infrastructure/postgres/compensating/wc136-bundle-profiles-key-restore.sql"
REPOSITORY = ROOT / "src/billing-engine/pricing/repository.py"

OWNER_FUNCTIONS = (
    "create_pricing_draft",
    "edit_pricing_draft",
    "transition_pricing_version",
    "apply_pricing_safety_successor",
    "project_package_profile",
    "set_package_sale_state",
)


@pytest.mark.parametrize("path", (VERSIONS, CATALOGUE), ids=lambda path: path.name)
def test_file_meets_the_idempotent_init_chain_standard(path: Path) -> None:
    assert lint_sql(path.name, path.read_text(encoding="utf-8")) == []


def test_pricing_tables_have_no_rls_and_are_closed_to_public_and_business_app() -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    assert not re.search(r"ROW\s+LEVEL\s+SECURITY|CREATE\s+POLICY", sql, re.I)
    assert re.search(r"REVOKE ALL ON .*FROM PUBLIC, business_app", sql, re.I | re.S)
    assert "TO business_app" not in sql
    assert "DROP TABLE" not in sql.upper()
    assert "GRANT SELECT ON institutional.pricing_versions, institutional.pricing_version_events TO wbe_app" in sql
    assert not re.search(r"GRANT\s+[^;]*\b(UPDATE|DELETE)\b[^;]*TO wbe_app", sql, re.I)


def test_pricing_versions_declare_the_lifecycle_constraints() -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS institutional.pricing_versions" in sql
    assert "CREATE TABLE IF NOT EXISTS institutional.pricing_version_events" in sql
    assert "UNIQUE (kind, subject_key, version_no)" in sql
    for state in ("DRAFT", "SIMULATED", "SUBMITTED", "AUTHORIZED", "EFFECTIVE", "SUPERSEDED", "DISCARDED"):
        assert f"'{state}'" in sql
    for kind in ("RATE", "PACKAGE", "POLICY", "GRANT", "BUDGET", "COUPON"):
        assert f"'{kind}'" in sql
    assert "CREATE OR REPLACE TRIGGER pricing_versions_guard" in sql
    assert "CREATE OR REPLACE TRIGGER pricing_version_events_append_only" in sql


def test_component_unit_tables_are_keyed_by_tenant() -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    assert "PRIMARY KEY (tenant_id, relationship_id, component_id, period_start)" in sql
    assert "UNIQUE (tenant_id, relationship_id, idempotency_key)" in sql
    assert "TO wbe_app" in sql


def test_bundle_profiles_key_replacement_is_declared_and_guarded() -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    assert "ADD COLUMN IF NOT EXISTS agent_version TEXT" in sql
    assert "ADD COLUMN IF NOT EXISTS package_version_id UUID" in sql
    assert "ALTER COLUMN bundle_tier TYPE VARCHAR(64)" in sql
    assert "DROP CONSTRAINT IF EXISTS uq_bundle_profile;" in sql
    assert "UNIQUE (agent_type, agent_version, bundle_tier, bundle_version)" in sql
    assert "conname = 'uq_bundle_profile_agent_version'" in sql


@pytest.mark.parametrize("function", OWNER_FUNCTIONS)
def test_owner_functions_are_security_definer_with_a_pinned_search_path(function: str) -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    match = re.search(
        rf"CREATE OR REPLACE FUNCTION institutional\.{function}\(.*?\$\$;?\s*(?=CREATE|REVOKE)",
        sql,
        re.S,
    )
    assert match, function
    declaration = match.group(0)
    assert "SECURITY DEFINER SET search_path = institutional, business, pg_temp" in declaration
    grant = re.search(r"GRANT EXECUTE ON FUNCTION(.*?)TO wbe_app;", sql, re.S)
    assert grant and f"institutional.{function}(" in grant.group(1)


def test_record_pricing_event_is_not_granted_to_the_application_role() -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    grant = re.search(r"GRANT EXECUTE ON FUNCTION(.*?)TO wbe_app;", sql, re.S)
    assert grant and "record_pricing_event" not in grant.group(1)


def test_repository_calls_only_functions_the_sql_defines() -> None:
    sql = VERSIONS.read_text(encoding="utf-8")
    called = set(re.findall(r"institutional\.(\w+)\(", REPOSITORY.read_text(encoding="utf-8")))
    assert called == set(OWNER_FUNCTIONS)
    for function in called:
        assert f"CREATE OR REPLACE FUNCTION institutional.{function}(" in sql


def test_pending_catalogue_entries_carry_no_invented_cost_and_are_not_active() -> None:
    sql = CATALOGUE.read_text(encoding="utf-8")
    for thread in (
        "stt_audio_minute",
        "tts_character_1k",
        "whatsapp_template_utility",
        "whatsapp_template_marketing",
        "whatsapp_template_authentication",
    ):
        assert f"('{thread}'" in sql
    assert sql.count("'PENDING_FOUNDER_AUTH'") == 5
    assert "'ACTIVE'" not in sql
    assert "ON CONFLICT (thread_id) DO NOTHING" in sql
    assert not re.search(r"[1-9]\d*\s*,\s*[0-9.]+\s*,\s*[0-9.]+\s*,\s*[0-9.]+\s*,\s*TRUE", sql)


def test_compensating_script_restores_the_old_key_and_is_not_in_the_init_chain() -> None:
    sql = COMPENSATING.read_text(encoding="utf-8")
    assert "UNIQUE (agent_type, bundle_tier, bundle_version)" in sql
    assert "DROP CONSTRAINT IF EXISTS uq_bundle_profile_agent_version" in sql
    assert COMPENSATING.parent.name == "compensating"
    assert not (INIT / COMPENSATING.name).exists()
    assert COMPENSATING.parent != INIT

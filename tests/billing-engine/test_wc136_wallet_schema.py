# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-01
# Constitutional basis: C-059, C-088, C-089, C-090
"""SQL-text contracts of the WC-136 wallet, platform-account and trial-identity init files."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from wc124_init_chain_lint import lint_sql

INIT = Path(__file__).resolve().parents[2] / "infrastructure/postgres/init"
WALLET = INIT / "99zzzzzzzz-wc136-05-wallet-entity.sql"
PLATFORM = INIT / "99zzzzzzzz-wc136-06-platform-accounts.sql"
CLAIMS = INIT / "99zzzzzzzz-wc136-02-trial-identity-claims.sql"
FILES = (CLAIMS, WALLET, PLATFORM)


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.name)
def test_file_meets_the_idempotent_init_chain_standard(path: Path) -> None:
    assert lint_sql(path.name, path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", FILES, ids=lambda path: path.name)
def test_wbe_tables_have_no_rls_and_are_closed_to_public_and_business_app(path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    assert not re.search(r"ROW\s+LEVEL\s+SECURITY|CREATE\s+POLICY", sql, re.I)
    assert re.search(r"REVOKE ALL ON .*FROM PUBLIC, business_app", sql, re.I | re.S)
    assert "TO wbe_app" in sql
    assert "TO business_app" not in sql
    assert "DROP TABLE" not in sql.upper()


def test_wallet_declares_the_four_tables_with_the_contract_constraints() -> None:
    sql = WALLET.read_text(encoding="utf-8")
    for table in ("wallet_accounts", "wallet_lots", "wallet_entries", "wallet_reservations"):
        assert f"CREATE TABLE IF NOT EXISTS business.{table}" in sql
    assert "UNIQUE (tenant_id, idempotency_key, entry_kind)" in sql
    assert "FOREIGN KEY (tenant_id, account_id) REFERENCES business.wallet_accounts" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS wallet_accounts_key" in sql
    assert "COALESCE(relationship_id, '00000000-0000-0000-0000-000000000000'::uuid)" in sql
    assert "lot_kind TEXT NOT NULL CHECK (lot_kind IN ('PERIOD_CREDIT', 'TOPUP_CREDIT', 'GRANT'))" in sql
    assert "credited_paise BIGINT NOT NULL CHECK (credited_paise > 0)" in sql
    assert "CHECK (valid_until > valid_from)" in sql
    assert "(owner_kind = 'PLATFORM') = (owner_ref IS NULL)" in sql
    assert "REFUNDABLE" not in sql.upper() and "ROLLOVER" not in sql.upper()


def test_wallet_lots_and_entries_are_immutable_and_reservations_change_three_columns_only() -> None:
    sql = WALLET.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE TRIGGER wallet_lots_immutable" in sql
    assert "CREATE OR REPLACE TRIGGER wallet_entries_immutable" in sql
    assert "BEFORE UPDATE OR DELETE ON business.wallet_lots" in sql
    assert "BEFORE UPDATE OR DELETE ON business.wallet_entries" in sql
    assert "GRANT UPDATE (state, actual_paise, resolved_at) ON business.wallet_reservations TO wbe_app" in sql
    assert len(re.findall(r"GRANT\s+[^;]*\bUPDATE\b", sql, re.I)) == 1
    assert "DELETE ON" not in sql.replace("UPDATE OR DELETE ON", "")


def test_wallet_available_is_stable_security_invoker_and_tenant_scoped() -> None:
    sql = WALLET.read_text(encoding="utf-8")
    definition = sql[sql.index("FUNCTION business.wallet_available") :]
    header = definition[: definition.index("$$")]
    assert "p_tenant UUID, p_account UUID, p_at TIMESTAMPTZ" in header
    assert "RETURNS BIGINT" in header and "STABLE" in header and "SECURITY INVOKER" in header
    assert "SECURITY DEFINER" not in sql
    assert definition.count("tenant_id = l.tenant_id") >= 3
    assert "l.tenant_id = p_tenant" in definition


def test_trial_identity_claim_key_is_hash_agent_type_and_exact_version() -> None:
    sql = CLAIMS.read_text(encoding="utf-8")
    assert "PRIMARY KEY (identity_subject_hash, agent_type, agent_version)" in sql
    assert "identity_subject_hash ~ '^[0-9a-f]{64}$'" in sql
    assert not re.search(r"\b(phone|email|name)\b", sql.split("\n", 4)[4], re.I)


def test_platform_floor_uses_are_append_only_and_carry_no_lead_reference() -> None:
    sql = PLATFORM.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS business.wallet_floor_uses" in sql
    assert "PRIMARY KEY (tenant_id, environment, use_id)" in sql
    assert "CREATE OR REPLACE TRIGGER wallet_floor_uses_immutable" in sql
    assert "lead_ref" not in sql

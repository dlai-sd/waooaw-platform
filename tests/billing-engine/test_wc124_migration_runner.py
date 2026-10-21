from pathlib import Path

from migrate import migration_sql


ROOT = Path(__file__).resolve().parents[2]


def test_migration_runner_removes_only_outer_transaction_markers() -> None:
    migration = ROOT / "infrastructure/postgres/init/59-wc124-billing-authority.sql"
    rendered = migration_sql(migration)
    assert "\nBEGIN;\n" not in f"\n{rendered}\n"
    assert "\nCOMMIT;\n" not in f"\n{rendered}\n"
    assert "CREATE TABLE IF NOT EXISTS billing.integrity_states" in rendered


def test_billing_image_contains_the_immutable_migration_set() -> None:
    dockerfile = (ROOT / "src/billing-engine/Dockerfile").read_text(encoding="utf-8")
    runner = (ROOT / "src/billing-engine/migrate.py").read_text(encoding="utf-8")
    assert "infrastructure/postgres/init/ ./migrations/" in dockerfile
    assert "pg_advisory_xact_lock" in runner
    assert "pg_has_role(session_user, $2, 'MEMBER')" in runner
    assert "migration login has prohibited elevated PostgreSQL attributes" in runner
    assert 'await connection.execute(f"SET LOCAL ROLE {MIGRATION_OWNER_ROLE}")' in runner
    assert "SET ROLE {" not in runner
    assert "statement_cache_size=0" in runner
    assert "migration ledger owner mismatch" in runner
    assert "waooaw_schema_migrations OWNER TO {MIGRATION_OWNER_ROLE}" in runner
    # Run 39543680599: #536 rewrote an already-applied 59-wc124-billing-authority.sql and the
    # migrator refused the digest change forever. Files are idempotent by standard, so the
    # migrator re-applies a changed file and updates its ledger row, like the provisioner does.
    assert "immutable migration digest changed" not in runner
    assert "migration digest changed, re-applying" in runner
    assert "ON CONFLICT (migration_name) DO UPDATE" in runner

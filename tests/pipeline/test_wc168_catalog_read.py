"""WC-168 R003/R004: the Founder-authorized Demo catalog read stays read-only, secret-free and self-cleaning."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "infrastructure/postgres/operations/wc168-catalog-read.sql"
SCRIPT = ROOT / "scripts/wc168_demo_db_catalog_read.sh"
FIX = ROOT / "infrastructure/postgres/init/99zzzzzzzz-wc168-01-provider-registry-runtime-access.sql"


def _statements(path: Path) -> str:
    return re.sub(r"--[^\n]*", "", path.read_text(encoding="utf-8"))


def _without_string_literals(text: str) -> str:
    return re.sub(r"'[^']*'", "''", text)


def test_the_catalog_query_runs_in_a_read_only_transaction_and_changes_nothing() -> None:
    text = _without_string_literals(_statements(SQL))
    assert re.match(r"\s*BEGIN READ ONLY;", text)
    assert text.rstrip().endswith("ROLLBACK;")
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|GRANT|REVOKE|CREATE|TRUNCATE|COPY)\b", text, re.IGNORECASE)


def test_the_catalog_query_reads_only_the_system_catalog_never_business_rows() -> None:
    sources = re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_.]+)", _statements(SQL), re.IGNORECASE)
    assert sources
    assert all(source.startswith("pg_") for source in sources), sources


def test_the_job_script_never_prints_the_connection_string_and_always_deletes_the_job() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "secretRef: db" in text and "keyVaultUrl" in text
    assert not re.search(r"(echo|printf)[^\n]*\$\{?DB_CONNECTION", text.replace("printf '%s' \"$DB_CONNECTION\" | tr", ""))
    assert "trap" in text and "containerapp job delete" in text
    assert "PGPASSWORD" in text and "set -eu" in text


def test_the_dry_run_touches_nothing_and_says_the_job_is_deleted() -> None:
    done = subprocess.run(["bash", str(SCRIPT), "dry-run"], capture_output=True, text=True, check=False)
    assert done.returncode == 0
    assert "never read here" in done.stdout and "deleted on exit" in done.stdout


def test_the_permission_fix_grants_only_what_the_provider_screen_does() -> None:
    text = _statements(FIX)
    assert "GRANT SELECT, INSERT ON business.provider_configs TO business_app;" in text
    assert "GRANT UPDATE (active_credential_version_id) ON business.provider_configs TO business_app;" in text
    assert not re.search(r"GRANT[^;]*\b(DELETE|ALL)\b", text, re.IGNORECASE)
    assert "FOR INSERT TO business_app" in text and "tenant_id IS NULL" in text

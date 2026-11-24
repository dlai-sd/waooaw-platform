"""WC-168 R012: the Founder-approved blocked-message read stays narrow, read-only and message-text free."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL = ROOT / "infrastructure/postgres/operations/wc168-blocked-outbox-read.sql"
SCRIPT = ROOT / "scripts/wc168_demo_db_catalog_read.sh"
FORBIDDEN_COLUMNS = (
    "payload_reference",
    "payload_digest",
    "recipient_binding_digest",
    "tenant_id",
    "template_name",
    "relationship_id",
    "conversation_id",
    "idempotency_key",
)


def _text() -> str:
    return re.sub(r"'[^']*'", "''", re.sub(r"--[^\n]*", "", SQL.read_text(encoding="utf-8")))


def test_the_blocked_message_read_is_a_read_only_transaction_that_changes_nothing() -> None:
    text = _text()
    assert re.match(r"\s*BEGIN READ ONLY;", text) and text.rstrip().endswith("ROLLBACK;")
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|GRANT|REVOKE|CREATE|TRUNCATE|COPY)\b", text, re.IGNORECASE)


def test_the_blocked_message_read_names_only_the_approved_columns_from_one_table() -> None:
    text = SQL.read_text(encoding="utf-8")
    code = re.sub(r"--[^\n]*", "", text)
    assert re.findall(r"\bFROM\s+([A-Za-z_.]+)", code) == ["business.conversation_outbox"] * 2
    for column in FORBIDDEN_COLUMNS:
        assert column not in code, column
    for column in ("outbox_id", "state", "blocked_reason", "created_at", "updated_at"):
        assert column in code


def test_the_job_script_can_run_the_blocked_message_read_and_keeps_its_output_filter() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert 'WC168_SQL_FILE:-' in script
    assert "OUTBOXSTATE" in script and "BLOCKED" in script

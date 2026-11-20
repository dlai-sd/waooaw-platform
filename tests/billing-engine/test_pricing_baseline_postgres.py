# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04, C5-06
# Constitutional basis: C-023, C-059, C-088, C-089, C-090, C-091
"""PostgreSQL checks of the Demo pricing baseline (-11) and the environment ceiling function (-10)."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from pricing.models import body_digest  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INIT = ROOT / "infrastructure/postgres/init"
BASELINE_SQL = INIT / "99zzzzzzzz-wc136-11-demo-pricing-baseline.sql"
CEILING_SQL = INIT / "99zzzzzzzz-wc136-10-budget-authority-function.sql"
DEPENDENCIES = (
    INIT / "99zzzzzzzz-wc136-07-pricing-versions.sql",
    INIT / "99zzzzzzzz-wc136-08-thread-catalogue-pending.sql",
)
EVIDENCE = "136c0000-0000-4000-8000-0000000000ff"

pytestmark = pytest.mark.integration


def _admin_url() -> str:
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    return url


def _apply(url: str, *files: Path) -> None:
    import psycopg2

    with psycopg2.connect(url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            for path in files:
                cursor.execute(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def migrated_url() -> str:
    url = _admin_url()
    _apply(url, *DEPENDENCIES, CEILING_SQL, BASELINE_SQL)
    return url


@pytest.fixture
def cursor(migrated_url: str) -> Iterator[object]:
    import psycopg2

    connection = psycopg2.connect(migrated_url)
    try:
        with connection.cursor() as opened:
            yield opened
    finally:
        connection.rollback()
        connection.close()


def test_the_baseline_replays_idempotently_and_every_seed_row_is_flagged(migrated_url: str) -> None:
    import psycopg2

    _apply(migrated_url, BASELINE_SQL)
    with psycopg2.connect(migrated_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT kind, state, seed FROM institutional.pricing_versions "
            "WHERE created_by = 'wc136-demo-baseline-seed' ORDER BY kind, subject_key"
        )
        rows = cursor.fetchall()
        cursor.execute(
            "SELECT count(*) FROM institutional.pricing_version_events WHERE actor = 'wc136-demo-baseline-seed'"
        )
        events = cursor.fetchone()[0]

    assert [(kind, state) for kind, state, _ in rows].count(("PACKAGE", "DRAFT")) == 1
    assert len(rows) == 7 and all(seed for _, _, seed in rows)
    assert events == 7
    assert ("POLICY", "EFFECTIVE", True) in rows


def test_the_sql_digest_equals_the_service_digest_of_the_stored_body(cursor: object) -> None:
    cursor.execute(
        "SELECT body, body_digest FROM institutional.pricing_versions WHERE created_by = 'wc136-demo-baseline-seed'"
    )
    rows = cursor.fetchall()

    assert len(rows) == 7
    for body, digest in rows:
        assert body_digest(body) == digest


def _authority(cursor: object, environment: str, maximum: int) -> None:
    cursor.execute(
        "INSERT INTO business.environment_spend_authorities "
        "(environment, authority_version, maximum_paise, active, migration_complete, authority_evidence_id, updated_at) "
        "VALUES (%s, 1, %s, true, true, %s::uuid, clock_timestamp())",
        (environment, maximum, EVIDENCE),
    )


def _apply_ceiling(cursor: object, environment: str, maximum: int, hard: int, dry_run: bool = False) -> tuple:
    cursor.execute(
        "SELECT outcome, previous_paise, applied_paise, blocking_paise "
        "FROM business.apply_environment_spend_ceiling(%s, %s, %s, %s::uuid, clock_timestamp(), %s)",
        (environment, maximum, hard, EVIDENCE, dry_run),
    )
    return cursor.fetchone()


def test_the_ceiling_function_refuses_above_the_hard_maximum_and_below_open_exposure(cursor: object) -> None:
    environment = f"wc136-{uuid4().hex[:12]}"
    _authority(cursor, environment, 50000)
    cursor.execute(
        "INSERT INTO business.environment_spend_attempts "
        "(environment, owner_kind, attempt_id, original_tenant_id, activation_digest, request_digest, "
        " reservation_reference, reserved_paise, state, reserved_at) "
        "VALUES (%s, 'MODEL', %s::uuid, %s::uuid, 'activation', %s, %s::uuid, 3000, 'RESERVED', clock_timestamp())",
        (environment, str(uuid4()), str(uuid4()), "a" * 64, str(uuid4())),
    )

    assert _apply_ceiling(cursor, environment, 60000, 50000) == ("ABOVE_HARD_MAXIMUM", 50000, None, 50000)
    assert _apply_ceiling(cursor, environment, 2000, 50000) == ("BELOW_EXPOSURE", 50000, None, 3000)
    assert _apply_ceiling(cursor, environment, 3000, 50000, dry_run=True) == ("DRY_RUN_OK", 50000, 3000, None)
    assert _apply_ceiling(cursor, environment, 3000, 50000) == ("APPLIED", 50000, 3000, None)
    assert _apply_ceiling(cursor, environment, 3000, 50000) == ("UNCHANGED", 3000, 3000, None)
    assert _apply_ceiling(cursor, environment, 120000, 200000) == ("APPLIED", 3000, 120000, None)
    cursor.execute(
        "SELECT maximum_paise, authority_version FROM business.environment_spend_authorities WHERE environment = %s",
        (environment,),
    )
    assert cursor.fetchone() == (120000, 3)


def test_the_ceiling_function_leaves_an_unprovisioned_environment_alone(cursor: object) -> None:
    assert _apply_ceiling(cursor, f"wc136-{uuid4().hex[:12]}", 100, 50000) == ("AUTHORITY_ABSENT", None, None, None)

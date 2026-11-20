# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-05, C4-07
# Constitutional basis: C-059, C-088, C-089, C-090, C-091
"""PostgreSQL checks of the WC-136 pricing version tables, owner functions and package key."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERSIONS_SQL = ROOT / "infrastructure/postgres/init/99zzzzzzzz-wc136-07-pricing-versions.sql"
CATALOGUE_SQL = ROOT / "infrastructure/postgres/init/99zzzzzzzz-wc136-08-thread-catalogue-pending.sql"
DIGEST = "a" * 64
PENDING_THREADS = (
    "stt_audio_minute",
    "tts_character_1k",
    "whatsapp_template_utility",
    "whatsapp_template_marketing",
    "whatsapp_template_authentication",
)
OWNER_FUNCTIONS = (
    "create_pricing_draft",
    "edit_pricing_draft",
    "transition_pricing_version",
    "apply_pricing_safety_successor",
    "project_package_profile",
    "set_package_sale_state",
)

pytestmark = pytest.mark.integration


def _admin_url() -> str:
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    return url


def _apply_migrations(url: str) -> None:
    import psycopg2

    with psycopg2.connect(url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(VERSIONS_SQL.read_text(encoding="utf-8"))
            cursor.execute(CATALOGUE_SQL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def migrated_url() -> str:
    url = _admin_url()
    _apply_migrations(url)
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


def _refused(cursor: object, sql: str, params: tuple, fragment: str) -> None:
    import psycopg2

    cursor.execute("SAVEPOINT refusal")
    with pytest.raises(psycopg2.Error) as caught:
        cursor.execute(sql, params)
    cursor.execute("ROLLBACK TO SAVEPOINT refusal")
    assert fragment in str(caught.value)


def _draft(cursor: object, kind: str, subject: str, body: dict, *, needs_second: bool = False) -> tuple:
    version_id = uuid4()
    cursor.execute(
        "SELECT version_no, state FROM institutional.create_pricing_draft("
        "%s::uuid, %s, %s, %s::jsonb, %s, %s, %s, clock_timestamp())",
        (str(version_id), kind, subject, json.dumps(body), DIGEST, "tester", needs_second),
    )
    return version_id, cursor.fetchone()


def _transition(
    cursor: object,
    version_id: object,
    to_state: str,
    *,
    authorized_by: str | None = None,
    second_confirmed_by: str | None = None,
) -> str:
    evidence = str(uuid4()) if authorized_by else None
    cursor.execute(
        "SELECT state FROM institutional.transition_pricing_version("
        "%s::uuid, %s, %s, %s, clock_timestamp(), %s, %s::uuid, NULL::timestamptz, NULL, %s)",
        (str(version_id), to_state, "tester", "test", authorized_by, evidence, second_confirmed_by),
    )
    return cursor.fetchone()[0]


def _make_effective(cursor: object, version_id: object) -> None:
    for state in ("SIMULATED", "SUBMITTED"):
        assert _transition(cursor, version_id, state) == state
    assert _transition(cursor, version_id, "AUTHORIZED", authorized_by="founder") == "AUTHORIZED"
    assert _transition(cursor, version_id, "EFFECTIVE") == "EFFECTIVE"


def _rate_body(raw_cost_paise: int) -> dict:
    return {
        "threadId": "stt_audio_minute",
        "rawCostPaise": raw_cost_paise,
        "fxBufferPct": 10,
        "opsOverheadPct": 15,
        "riskPremiumPct": 8,
        "provider": "Test provider",
        "unit": "minute",
    }


def test_migrations_are_idempotent_and_close_the_privileges(migrated_url: str) -> None:
    import psycopg2

    _apply_migrations(migrated_url)
    with psycopg2.connect(migrated_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT has_table_privilege('wbe_app', 'institutional.pricing_versions', 'SELECT'),
                   has_table_privilege('wbe_app', 'institutional.pricing_versions', 'UPDATE'),
                   has_table_privilege('wbe_app', 'institutional.pricing_version_events', 'INSERT'),
                   has_table_privilege('business_app', 'institutional.pricing_versions', 'SELECT'),
                   has_table_privilege('wbe_app', 'business.component_units', 'INSERT'),
                   has_table_privilege('business_app', 'business.component_units', 'SELECT')
            """
        )
        assert cursor.fetchone() == (True, False, False, False, True, False)
        cursor.execute(
            """
            SELECT p.proname, p.prosecdef, pg_get_userbyid(p.proowner),
                   has_function_privilege('wbe_app', p.oid, 'EXECUTE'),
                   has_function_privilege('business_app', p.oid, 'EXECUTE')
            FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'institutional' AND p.proname = ANY(%s)
            ORDER BY p.proname
            """,
            (list(OWNER_FUNCTIONS),),
        )
        rows = cursor.fetchall()
        assert [row[0] for row in rows] == sorted(OWNER_FUNCTIONS)
        assert all(row[1:] == (True, "wbe_owner", True, False) for row in rows)


def test_pending_catalogue_entries_are_present_and_not_active(cursor: object) -> None:
    cursor.execute(
        "SELECT count(*) FROM institutional.thread_catalog WHERE thread_id = ANY(%s)",
        (list(PENDING_THREADS),),
    )
    assert cursor.fetchone()[0] == len(PENDING_THREADS)
    cursor.execute(
        "SELECT count(*) FROM institutional.thread_catalog "
        "WHERE thread_id = ANY(%s) AND status = 'ACTIVE' AND founder_authorized_at IS NULL",
        (list(PENDING_THREADS),),
    )
    assert cursor.fetchone()[0] == 0


def test_bundle_profile_key_includes_the_agent_version(cursor: object) -> None:
    agent_type = f"wc136-{uuid4().hex[:12]}"
    tier = "PACKAGE-" + "X" * 40
    insert = (
        "INSERT INTO institutional.bundle_profiles "
        "(agent_type, agent_version, bundle_tier, bundle_version, display_name, thread_rations, "
        "cost_floor_paise) VALUES (%s, %s, %s, 1, 'Test package', '{}'::jsonb, 1)"
    )
    cursor.execute(insert, (agent_type, "1.0.0", tier))
    cursor.execute(insert, (agent_type, "1.1.0", tier))
    _refused(cursor, insert, (agent_type, "1.0.0", tier), "uq_bundle_profile_agent_version")
    cursor.execute(
        "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_bundle_profile' "
        "AND conrelid = 'institutional.bundle_profiles'::regclass"
    )
    assert cursor.fetchone()[0] == 0


def test_rate_lifecycle_supersedes_and_authorizes_the_catalogue_entry(cursor: object) -> None:
    first, created = _draft(cursor, "RATE", "stt_audio_minute", _rate_body(120))
    first_number = created[0]
    assert created[1] == "DRAFT"
    _refused(
        cursor,
        "SELECT state FROM institutional.transition_pricing_version("
        "%s::uuid, 'SUBMITTED', 'tester', 'test', clock_timestamp(), NULL, NULL, NULL, NULL, NULL)",
        (str(first),),
        "PRICING_ILLEGAL_TRANSITION",
    )
    _make_effective(cursor, first)
    cursor.execute(
        "SELECT status, marked_up_cost_paise, founder_authorized_by "
        "FROM institutional.thread_catalog WHERE thread_id = 'stt_audio_minute'"
    )
    assert cursor.fetchone() == ("ACTIVE", 160, "founder")
    cursor.execute(
        "SELECT count(*) FROM institutional.pricing_version_events WHERE version_id = %s::uuid",
        (str(first),),
    )
    assert cursor.fetchone()[0] == 5

    second, created = _draft(cursor, "RATE", "stt_audio_minute", _rate_body(130))
    assert created == (first_number + 1, "DRAFT")
    _make_effective(cursor, second)
    cursor.execute(
        "SELECT state FROM institutional.pricing_versions WHERE version_id = %s::uuid", (str(first),)
    )
    assert cursor.fetchone()[0] == "SUPERSEDED"
    cursor.execute(
        "SELECT supersedes::text FROM institutional.pricing_versions WHERE version_id = %s::uuid",
        (str(second),),
    )
    assert cursor.fetchone()[0] == str(first)


def test_versions_and_events_cannot_be_rewritten_or_deleted(cursor: object) -> None:
    version_id, _ = _draft(cursor, "RATE", "stt_audio_minute", _rate_body(120))
    _make_effective(cursor, version_id)
    _refused(
        cursor,
        "UPDATE institutional.pricing_versions SET body = '{}'::jsonb WHERE version_id = %s::uuid",
        (str(version_id),),
        "immutable after submission",
    )
    _refused(
        cursor,
        "UPDATE institutional.pricing_versions SET state = 'DRAFT' WHERE version_id = %s::uuid",
        (str(version_id),),
        "PRICING_ILLEGAL_TRANSITION",
    )
    _refused(
        cursor,
        "DELETE FROM institutional.pricing_versions WHERE version_id = %s::uuid",
        (str(version_id),),
        "append-only",
    )
    _refused(
        cursor,
        "UPDATE institutional.pricing_version_events SET reason = 'x' WHERE version_id = %s::uuid",
        (str(version_id),),
        "append-only",
    )


def test_a_draft_needing_second_confirmation_cannot_be_submitted_without_it(cursor: object) -> None:
    version_id, _ = _draft(
        cursor, "COUPON", f"wc136-{uuid4().hex[:12]}", {"code": "X"}, needs_second=True
    )
    assert _transition(cursor, version_id, "SIMULATED") == "SIMULATED"
    _refused(
        cursor,
        "SELECT state FROM institutional.transition_pricing_version("
        "%s::uuid, 'SUBMITTED', 'tester', 'test', clock_timestamp(), NULL, NULL, NULL, NULL, NULL)",
        (str(version_id),),
        "PRICING_NEEDS_SECOND_CONFIRMATION",
    )
    assert _transition(cursor, version_id, "SUBMITTED", second_confirmed_by="second") == "SUBMITTED"


def test_the_application_role_changes_pricing_only_through_the_owner_functions(
    cursor: object,
) -> None:
    cursor.execute("SET LOCAL ROLE wbe_app")
    version_id, created = _draft(cursor, "COUPON", f"wc136-{uuid4().hex[:12]}", {"code": "Y"})
    assert created[1] == "DRAFT"
    cursor.execute("SELECT count(*) FROM institutional.pricing_versions WHERE version_id = %s::uuid", (str(version_id),))
    assert cursor.fetchone()[0] == 1
    _refused(
        cursor,
        "UPDATE institutional.pricing_versions SET state = 'DISCARDED' WHERE version_id = %s::uuid",
        (str(version_id),),
        "permission denied",
    )
    _refused(
        cursor,
        "INSERT INTO institutional.pricing_version_events "
        "(event_id, version_id, to_state, direction, actor, occurred_at) "
        "VALUES (%s::uuid, %s::uuid, 'DRAFT', 'NORMAL', 'x', now())",
        (str(uuid4()), str(version_id)),
        "permission denied",
    )
    cursor.execute("RESET ROLE")
    cursor.execute("SET LOCAL ROLE business_app")
    _refused(
        cursor,
        "SELECT count(*) FROM institutional.pricing_versions",
        (),
        "permission denied",
    )
    cursor.execute("RESET ROLE")

# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09, C4-10
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
# Constitutional basis: C-059, C-088, C-089, C-090, C-063
"""Real-PostgreSQL checks of the commercial projection, command, period and billing adjustment tables."""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest

UNIQUE_VIOLATION = "23505"
CHECK_VIOLATION = "23514"
IMMUTABLE = "55000"
COMMERCIAL_SQL = Path("infrastructure/postgres/init/99zzzzzzzz-wc136-09-commercial-projection.sql")
RENEWAL_SQL = Path("infrastructure/postgres/init/99zzzzzzzz-wc136-16-renewal-collection-and-pricing-idempotency.sql")

pytestmark = pytest.mark.integration


def _url() -> str:
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    return url


@pytest.fixture(scope="module")
def migrated_url() -> str:
    import psycopg2

    url = _url()
    with psycopg2.connect(url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(COMMERCIAL_SQL.read_text(encoding="utf-8"))
            cursor.execute(RENEWAL_SQL.read_text(encoding="utf-8"))
    return url


@pytest.fixture
def cursor(migrated_url: str):
    import psycopg2

    connection = psycopg2.connect(migrated_url)
    try:
        with connection.cursor() as opened:
            yield opened
    finally:
        connection.rollback()
        connection.close()


def _refused(cursor, sql: str, params: tuple = ()) -> str | None:
    import psycopg2

    cursor.execute("SAVEPOINT refusal")
    try:
        cursor.execute(sql, params)
    except psycopg2.Error as error:
        cursor.execute("ROLLBACK TO SAVEPOINT refusal")
        return error.pgcode
    cursor.execute("RELEASE SAVEPOINT refusal")
    return None


def _command(cursor, tenant: str, relationship: str, key: str = "k1") -> str:
    command = str(uuid4())
    cursor.execute(
        """
        INSERT INTO business.commercial_commands
            (command_id, tenant_id, relationship_id, idempotency_key, request_digest, command_kind, status,
             receipt, outcome, accepted_at)
        VALUES (%s, %s, %s, %s, %s, 'PAUSE_RELATIONSHIP', 'PENDING', %s::jsonb, %s::jsonb, clock_timestamp())
        """,
        (command, tenant, relationship, key, "d" * 64, json.dumps({}), json.dumps({})),
    )
    return command


def test_migration_applies_twice_without_error(migrated_url: str) -> None:
    import psycopg2

    with psycopg2.connect(migrated_url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(COMMERCIAL_SQL.read_text(encoding="utf-8"))
            cursor.execute(RENEWAL_SQL.read_text(encoding="utf-8"))
            cursor.execute(RENEWAL_SQL.read_text(encoding="utf-8"))


def test_projections_are_append_only_and_unique_per_version(cursor) -> None:
    tenant, relationship = str(uuid4()), str(uuid4())
    insert = (
        "INSERT INTO business.commercial_projections "
        "(tenant_id, relationship_id, projection_version, body, produced_at) "
        "VALUES (%s, %s, 'v1', %s::jsonb, clock_timestamp())"
    )
    cursor.execute(insert, (tenant, relationship, json.dumps({"a": 1})))
    assert _refused(cursor, insert, (tenant, relationship, json.dumps({"a": 1}))) == UNIQUE_VIOLATION
    assert _refused(
        cursor,
        "UPDATE business.commercial_projections SET body = '{}'::jsonb WHERE tenant_id = %s",
        (tenant,),
    ) == IMMUTABLE
    assert _refused(cursor, "DELETE FROM business.commercial_projections WHERE tenant_id = %s", (tenant,)) == IMMUTABLE


def test_a_command_keeps_its_request_and_one_key_means_one_command(cursor) -> None:
    tenant, relationship = str(uuid4()), str(uuid4())
    command = _command(cursor, tenant, relationship)
    assert _refused(
        cursor,
        "INSERT INTO business.commercial_commands (command_id, tenant_id, relationship_id, idempotency_key, "
        "request_digest, command_kind, status, receipt, outcome, accepted_at) "
        "VALUES (%s, %s, %s, 'k1', %s, 'PAUSE_RELATIONSHIP', 'PENDING', '{}'::jsonb, '{}'::jsonb, now())",
        (str(uuid4()), tenant, relationship, "e" * 64),
    ) == UNIQUE_VIOLATION
    assert _refused(
        cursor,
        "UPDATE business.commercial_commands SET status = 'COMPLETED', resolved_at = now() WHERE command_id = %s",
        (command,),
    ) is None
    assert _refused(
        cursor, "UPDATE business.commercial_commands SET request_digest = %s WHERE command_id = %s",
        ("f" * 64, command),
    ) == IMMUTABLE
    assert _refused(
        cursor, "UPDATE business.commercial_commands SET status = 'DONE' WHERE command_id = %s", (command,)
    ) == CHECK_VIOLATION
    assert _refused(cursor, "DELETE FROM business.commercial_commands WHERE command_id = %s", (command,)) == IMMUTABLE


def test_billing_adjustment_is_positive_once_per_command_and_keeps_its_amount(cursor) -> None:
    tenant, relationship = str(uuid4()), str(uuid4())
    command = _command(cursor, tenant, relationship)
    insert = (
        "INSERT INTO business.billing_adjustments (adjustment_id, tenant_id, relationship_id, command_id, "
        "adjustment_kind, amount_paise, payment_reference, status, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, 'FEE_REFUND', %s, 'pay_1', 'PENDING_PROVIDER', now(), now())"
    )
    adjustment = str(uuid4())
    assert _refused(cursor, insert, (str(uuid4()), tenant, relationship, command, 0)) == CHECK_VIOLATION
    cursor.execute(insert, (adjustment, tenant, relationship, command, 1500))
    assert _refused(cursor, insert, (str(uuid4()), tenant, relationship, command, 1500)) == UNIQUE_VIOLATION
    assert _refused(
        cursor,
        "UPDATE business.billing_adjustments SET status = 'DISPATCHED', provider_reference = 'rfnd_1' "
        "WHERE adjustment_id = %s",
        (adjustment,),
    ) is None
    assert _refused(
        cursor, "UPDATE business.billing_adjustments SET amount_paise = 1 WHERE adjustment_id = %s", (adjustment,)
    ) == IMMUTABLE


def test_period_status_is_constrained_and_updatable(cursor) -> None:
    tenant, relationship = str(uuid4()), str(uuid4())
    cursor.execute(
        """
        INSERT INTO business.relationship_periods
            (tenant_id, relationship_id, period_start, period_end, package_version_id, fee_paid_paise,
             status, updated_at)
        VALUES (%s, %s, now(), now() + interval '30 days', %s, 30000, 'ACTIVE', now())
        """,
        (tenant, relationship, str(uuid4())),
    )
    assert _refused(
        cursor, "UPDATE business.relationship_periods SET status = 'PAUSED' WHERE tenant_id = %s", (tenant,)
    ) is None
    assert _refused(
        cursor, "UPDATE business.relationship_periods SET status = 'GONE' WHERE tenant_id = %s", (tenant,)
    ) == CHECK_VIOLATION


def test_one_payment_starts_one_period_and_an_upgrade_fee_is_collectable(cursor) -> None:
    tenant, relationship = str(uuid4()), str(uuid4())
    period = (
        "INSERT INTO business.relationship_periods (tenant_id, relationship_id, period_start, period_end, "
        "package_version_id, fee_paid_paise, status, updated_at, payment_reference) "
        "VALUES (%s, %s, now() + %s * interval '1 day', now() + %s * interval '1 day', %s, 30000, 'ACTIVE', "
        "now(), 'pay_1')"
    )
    cursor.execute(period, (tenant, relationship, 0, 30, str(uuid4())))
    assert _refused(cursor, period, (tenant, relationship, 30, 60, str(uuid4()))) == UNIQUE_VIOLATION

    command = _command(cursor, tenant, relationship, "upgrade")
    adjustment = str(uuid4())
    cursor.execute(
        "INSERT INTO business.billing_adjustments (adjustment_id, tenant_id, relationship_id, command_id, "
        "adjustment_kind, amount_paise, status, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, 'UPGRADE_FEE', 4000, 'PENDING_PROVIDER', now(), now())",
        (adjustment, tenant, relationship, command),
    )
    for status in ("ORDER_CREATED", "COLLECTED"):
        assert _refused(
            cursor, "UPDATE business.billing_adjustments SET status = %s WHERE adjustment_id = %s", (status, adjustment)
        ) is None
    assert _refused(
        cursor, "UPDATE business.billing_adjustments SET adjustment_kind = 'FEE_REFUND' WHERE adjustment_id = %s",
        (adjustment,),
    ) == IMMUTABLE


def test_pricing_admin_idempotency_keeps_one_response_per_actor_operation_and_key(cursor) -> None:
    insert = (
        "INSERT INTO business.pricing_admin_idempotency "
        "(actor_id, operation, idempotency_key, request_digest, status_code, payload, stored_at) "
        "VALUES ('founder-1', 'wbe_create_pricing_draft', %s, %s, 201, '{}'::jsonb, now())"
    )
    key = str(uuid4())
    cursor.execute(insert, (key, "a" * 64))
    assert _refused(cursor, insert, (key, "a" * 64)) == UNIQUE_VIOLATION
    assert _refused(cursor, insert, (str(uuid4()), "short")) == CHECK_VIOLATION

# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-01
# Constitutional basis: C-059, C-088, C-089, C-090
"""Real-PostgreSQL checks of the WC-136 wallet entity (accounts, lots, entries, reservations)."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

UNIQUE_VIOLATION = "23505"
CHECK_VIOLATION = "23514"
IMMUTABLE = "55000"
WALLET_SQL = Path("infrastructure/postgres/init/99zzzzzzzz-wc136-05-wallet-entity.sql")
PLATFORM_SQL = Path("infrastructure/postgres/init/99zzzzzzzz-wc136-06-platform-accounts.sql")
CLAIMS_SQL = Path("infrastructure/postgres/init/99zzzzzzzz-wc136-02-trial-identity-claims.sql")

pytestmark = pytest.mark.integration


def _url() -> str:
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    return url


@pytest.fixture
def cursor():
    import psycopg2

    connection = psycopg2.connect(_url())
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


def _account(cursor, tenant: str, *, relationship: str | None = None) -> str:
    account = str(uuid4())
    cursor.execute(
        """
        INSERT INTO business.wallet_accounts
            (account_id, tenant_id, owner_kind, owner_ref, account_class, scope_kind,
             relationship_id, status, created_at)
        VALUES (%s, %s, 'CUSTOMER', %s, 'SUBSCRIPTION', 'RELATIONSHIP', %s, 'ACTIVE',
                clock_timestamp())
        """,
        (account, tenant, str(uuid4()), relationship or str(uuid4())),
    )
    return account


def _lot(cursor, tenant: str, account: str, paise: int, start: str, end: str) -> str:
    lot = str(uuid4())
    cursor.execute(
        """
        INSERT INTO business.wallet_lots
            (lot_id, tenant_id, account_id, lot_kind, credited_paise, valid_from, valid_until,
             source_kind, source_ref, pinned_versions, evidence_id, created_at)
        VALUES (%s, %s, %s, 'PERIOD_CREDIT', %s,
                clock_timestamp() + %s::interval, clock_timestamp() + %s::interval,
                'PACKAGE_PERIOD', 'package:period-1', '{"package": "p1"}', %s, clock_timestamp())
        """,
        (lot, tenant, account, paise, start, end, str(uuid4())),
    )
    return lot


def _reservation(cursor, tenant: str, account: str, lot: str, paise: int) -> str:
    reservation = str(uuid4())
    cursor.execute(
        """
        INSERT INTO business.wallet_reservations
            (reservation_id, tenant_id, account_id, lot_id, component_id, reserved_paise,
             actual_paise, state, pinned_account_class, pinned_versions, expires_at, created_at,
             resolved_at)
        VALUES (%s, %s, %s, %s, 'llm_cloud', %s, NULL, 'RESERVED', 'SUBSCRIPTION', '{}',
                clock_timestamp() + interval '1 hour', clock_timestamp(), NULL)
        """,
        (reservation, tenant, account, lot, paise),
    )
    return reservation


def _entry(cursor, tenant: str, account: str, lot: str, kind: str, paise: int, key: str) -> str:
    entry = str(uuid4())
    cursor.execute(
        """
        INSERT INTO business.wallet_entries
            (entry_id, tenant_id, account_id, lot_id, entry_kind, amount_paise, idempotency_key,
             request_digest, occurred_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, clock_timestamp())
        """,
        (entry, tenant, account, lot, kind, paise, key, "a" * 64),
    )
    return entry


def _available(cursor, tenant: str, account: str) -> int:
    cursor.execute("SELECT business.wallet_available(%s, %s, clock_timestamp())", (tenant, account))
    return cursor.fetchone()[0]


def test_wc136_files_replay_and_leave_wbe_ownership_and_closed_grants() -> None:
    import psycopg2

    with psycopg2.connect(_url()) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            for path in (CLAIMS_SQL, WALLET_SQL, PLATFORM_SQL):
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(path.read_text(encoding="utf-8"))
            cursor.execute(
                """
                SELECT tablename, tableowner FROM pg_tables
                WHERE schemaname = 'business' AND tablename IN (
                    'wallet_accounts', 'wallet_lots', 'wallet_entries', 'wallet_reservations',
                    'wallet_floor_uses', 'trial_identity_claims')
                """
            )
            owners = dict(cursor.fetchall())
            assert len(owners) == 6 and set(owners.values()) == {"wbe_owner"}
            for table in owners:
                cursor.execute(
                    "SELECT has_table_privilege('business_app', %s, 'SELECT'),"
                    " has_table_privilege('wbe_app', %s, 'INSERT'),"
                    " has_table_privilege('wbe_app', %s, 'DELETE')",
                    (f"business.{table}",) * 3,
                )
                assert cursor.fetchone() == (False, True, False)
            cursor.execute(
                "SELECT has_column_privilege('wbe_app', 'business.wallet_reservations', 'state', 'UPDATE'),"
                " has_column_privilege('wbe_app', 'business.wallet_reservations', 'reserved_paise', 'UPDATE'),"
                " has_table_privilege('wbe_app', 'business.wallet_lots', 'UPDATE'),"
                " has_table_privilege('wbe_app', 'business.wallet_entries', 'UPDATE')"
            )
            assert cursor.fetchone() == (True, False, False, False)


def test_duplicate_account_key_is_refused(cursor) -> None:
    tenant = str(uuid4())
    insert = """
        INSERT INTO business.wallet_accounts
            (account_id, tenant_id, owner_kind, account_class, scope_kind, status, created_at)
        VALUES (%s, %s, 'PLATFORM', 'ACQUISITION', 'MARKETPLACE', 'ACTIVE', clock_timestamp())
    """
    assert _refused(cursor, insert, (str(uuid4()), tenant)) is None
    assert _refused(cursor, insert, (str(uuid4()), tenant)) == UNIQUE_VIOLATION
    assert _refused(cursor, insert, (str(uuid4()), str(uuid4()))) is None


def test_account_class_coherence_is_enforced(cursor) -> None:
    tenant = str(uuid4())
    trial_for_customer = """
        INSERT INTO business.wallet_accounts
            (account_id, tenant_id, owner_kind, owner_ref, account_class, scope_kind,
             relationship_id, agent_type, agent_version, status, created_at)
        VALUES (%s, %s, 'CUSTOMER', %s, 'TRIAL', 'RELATIONSHIP', %s, 'DMA', '1.0.0', 'ACTIVE',
                clock_timestamp())
    """
    assert _refused(
        cursor, trial_for_customer, (str(uuid4()), tenant, str(uuid4()), str(uuid4()))
    ) == CHECK_VIOLATION
    platform_with_owner = """
        INSERT INTO business.wallet_accounts
            (account_id, tenant_id, owner_kind, owner_ref, account_class, scope_kind, environment,
             status, created_at)
        VALUES (%s, %s, 'PLATFORM', %s, 'SIMULATION', 'ENVIRONMENT', 'demo', 'ACTIVE',
                clock_timestamp())
    """
    assert _refused(cursor, platform_with_owner, (str(uuid4()), tenant, str(uuid4()))) == CHECK_VIOLATION


def test_lot_and_entry_rows_are_immutable(cursor) -> None:
    tenant = str(uuid4())
    account = _account(cursor, tenant)
    lot = _lot(cursor, tenant, account, 1000, "-1 hour", "1 hour")
    entry = _entry(cursor, tenant, account, lot, "CREDIT", 1000, str(uuid4()))
    assert _refused(
        cursor, "UPDATE business.wallet_lots SET credited_paise = 1 WHERE lot_id = %s", (lot,)
    ) == IMMUTABLE
    assert _refused(cursor, "DELETE FROM business.wallet_lots WHERE lot_id = %s", (lot,)) == IMMUTABLE
    assert _refused(
        cursor, "UPDATE business.wallet_entries SET amount_paise = 1 WHERE entry_id = %s", (entry,)
    ) == IMMUTABLE
    assert _refused(cursor, "DELETE FROM business.wallet_entries WHERE entry_id = %s", (entry,)) == IMMUTABLE


def test_entry_idempotency_key_is_unique_per_kind(cursor) -> None:
    tenant = str(uuid4())
    account = _account(cursor, tenant)
    lot = _lot(cursor, tenant, account, 1000, "-1 hour", "1 hour")
    key = str(uuid4())
    _entry(cursor, tenant, account, lot, "CREDIT", 1000, key)
    savepoint_sql = """
        INSERT INTO business.wallet_entries
            (entry_id, tenant_id, account_id, lot_id, entry_kind, amount_paise, idempotency_key,
             request_digest, occurred_at)
        VALUES (%s, %s, %s, %s, %s, 5, %s, %s, clock_timestamp())
    """
    assert _refused(
        cursor, savepoint_sql, (str(uuid4()), tenant, account, lot, "CREDIT", key, "b" * 64)
    ) == UNIQUE_VIOLATION
    assert _refused(
        cursor, savepoint_sql, (str(uuid4()), tenant, account, lot, "ADJUST", key, "b" * 64)
    ) is None


def test_reservation_state_coherence_and_identity_are_enforced(cursor) -> None:
    tenant = str(uuid4())
    account = _account(cursor, tenant)
    lot = _lot(cursor, tenant, account, 1000, "-1 hour", "1 hour")
    reservation = _reservation(cursor, tenant, account, lot, 300)
    assert _refused(
        cursor,
        "UPDATE business.wallet_reservations SET state = 'SETTLED', resolved_at = clock_timestamp() "
        "WHERE reservation_id = %s",
        (reservation,),
    ) == CHECK_VIOLATION
    assert _refused(
        cursor,
        "UPDATE business.wallet_reservations SET reserved_paise = 1 WHERE reservation_id = %s",
        (reservation,),
    ) == IMMUTABLE
    assert _refused(
        cursor,
        "UPDATE business.wallet_reservations SET state = 'SETTLED', actual_paise = 250, "
        "resolved_at = clock_timestamp() WHERE reservation_id = %s",
        (reservation,),
    ) is None
    assert _refused(
        cursor,
        "UPDATE business.wallet_reservations SET state = 'RELEASED', actual_paise = 0 "
        "WHERE reservation_id = %s",
        (reservation,),
    ) is not None
    assert _refused(
        cursor, "DELETE FROM business.wallet_reservations WHERE reservation_id = %s", (reservation,)
    ) == IMMUTABLE


def test_wallet_available_excludes_expired_lots_and_counts_reservations(cursor) -> None:
    tenant = str(uuid4())
    account = _account(cursor, tenant)
    active = _lot(cursor, tenant, account, 1000, "-1 hour", "1 hour")
    _lot(cursor, tenant, account, 500, "-2 days", "-1 day")
    _lot(cursor, tenant, account, 700, "1 day", "2 days")
    assert _available(cursor, tenant, account) == 1000

    reservation = _reservation(cursor, tenant, account, active, 300)
    assert _available(cursor, tenant, account) == 700
    cursor.execute(
        "UPDATE business.wallet_reservations SET state = 'UNKNOWN' WHERE reservation_id = %s",
        (reservation,),
    )
    assert _available(cursor, tenant, account) == 700
    cursor.execute(
        "UPDATE business.wallet_reservations SET state = 'SETTLED', actual_paise = 250, "
        "resolved_at = clock_timestamp() WHERE reservation_id = %s",
        (reservation,),
    )
    assert _available(cursor, tenant, account) == 750
    _entry(cursor, tenant, account, active, "EXPIRE", 100, str(uuid4()))
    assert _available(cursor, tenant, account) == 650


def test_foreign_tenant_reads_nothing(cursor) -> None:
    tenant, other = str(uuid4()), str(uuid4())
    account = _account(cursor, tenant)
    _lot(cursor, tenant, account, 1000, "-1 hour", "1 hour")
    assert _available(cursor, tenant, account) == 1000
    assert _available(cursor, other, account) == 0
    cursor.execute("SELECT count(*) FROM business.wallet_accounts WHERE tenant_id = %s", (other,))
    assert cursor.fetchone()[0] == 0
    cursor.execute("SELECT count(*) FROM business.wallet_lots WHERE tenant_id = %s", (other,))
    assert cursor.fetchone()[0] == 0

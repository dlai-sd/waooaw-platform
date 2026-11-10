"""WC-134 WBE allowance schema and immutable identity integration checks."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest


def test_offering_identity_digest_is_canonical() -> None:
    from meter.allowance_service import canonical_digest

    assert canonical_digest({"b": 2, "a": 1}) == canonical_digest({"a": 1, "b": 2})
    assert canonical_digest({"a": 1}) != canonical_digest({"a": "1"})


@pytest.mark.integration
def test_offering_usage_migration_installs_owner_constraints() -> None:
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    import psycopg2

    migration = Path(
        "infrastructure/postgres/init/99zzzzz-wc134-offering-usage.sql"
    ).read_text(encoding="utf-8")
    with psycopg2.connect(url) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(migration)
            cursor.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid='business.offering_component_reservations'::regclass
            """
            )
            assert len(cursor.fetchall()) >= 5
            cursor.execute(
                """
                SELECT NOT has_table_privilege(
                    'business_app','business.offering_component_reservations','INSERT'
                )
                """
            )
            assert cursor.fetchone()[0]


@pytest.mark.integration
def test_environment_exposure_keeps_old_unresolved_and_replaces_settled() -> None:
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    import psycopg2

    environment = f"wc134-{uuid4()}"
    with psycopg2.connect(url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
            """
            INSERT INTO business.environment_spend_authorities
                (environment,authority_version,maximum_paise,active,migration_complete,
                 authority_evidence_id,updated_at)
            VALUES (%s,1,50000,true,true,%s,clock_timestamp())
            """,
                (environment, str(uuid4())),
            )
            unresolved, settled = uuid4(), uuid4()
            for attempt, state, reserved, actual, age in (
                (unresolved, "RESERVED", 700, None, "48 hours"),
                (settled, "SETTLED", 900, 300, "1 hour"),
            ):
                cursor.execute(
                """
                INSERT INTO business.environment_spend_attempts
                    (environment,owner_kind,attempt_id,original_tenant_id,
                     activation_digest,request_digest,reservation_reference,
                     reserved_paise,actual_paise,state,reserved_at,usage_at,
                     settlement_evidence_id)
                VALUES (%s,'MODEL',%s,%s,'activation',%s,%s,%s,%s,%s,
                    clock_timestamp()-(%s)::interval,
                    CASE WHEN %s='SETTLED' THEN clock_timestamp()-interval '1 hour' END,
                    CASE WHEN %s='SETTLED' THEN (%s)::uuid END)
                """,
                    (
                        environment,
                        str(attempt),
                        str(uuid4()),
                        "a" * 64,
                        str(uuid4()),
                        reserved,
                        actual,
                        state,
                        age,
                        state,
                        state,
                        str(uuid4()),
                    ),
                )
            cursor.execute(
                "SELECT business.environment_spend_exposure(%s,clock_timestamp())",
                (environment,),
            )
            assert cursor.fetchone()[0] == 1000
        connection.rollback()

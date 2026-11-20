# Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.3
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-03
# Constitutional basis: C-059, C-088, C-089
"""WC-134 WBE allowance schema and immutable identity integration checks."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
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


@pytest.mark.integration
async def test_shadow_mirror_and_parity_agree_over_the_real_schema() -> None:
    """C4-03: reserve, settle and release mirror into the wallet once; LEGACY writes nothing."""
    url = os.getenv("WC134_METER_POSTGRES_ADMIN_URL")
    if not url:
        pytest.skip("WC134_METER_POSTGRES_ADMIN_URL is required")
    from sqlalchemy import DateTime, bindparam, text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from database import asyncpg_engine_target
    from meter.allowance_service import OfferingAllowanceService
    from wallet.parity import compute_parity

    tenant, relationship, customer = uuid4(), uuid4(), uuid4()
    allocation = uuid4()
    now = datetime.now(timezone.utc)
    shadow = OfferingAllowanceService(None, SimpleNamespace(WALLET_AUTHORITY="SHADOW"))
    legacy = OfferingAllowanceService(None, SimpleNamespace(WALLET_AUTHORITY="LEGACY"))

    async def reserve(session, units: int, invocation) -> object:
        reservation = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO business.offering_component_reservations
                (reservation_id, allocation_id, tenant_id, customer_id, relationship_id,
                 agent_instance_id, professional_type, professional_version, skill_id,
                 skill_version, work_item_id, invocation_id, component_id, idempotency_key,
                 request_digest, owner_evidence_id, catalogue_thread_id, provider_account_id,
                 rate_version, raw_unit_cost_paise, marked_up_unit_cost_paise, maximum_units,
                 reserved_raw_paise, reserved_marked_up_paise, state, reserved_at)
                VALUES (:reservation, :allocation, :tenant, :customer, :relationship, :agent,
                        'marketing', '1.0.0', 'post', '1', :work_item, :invocation, 'llm_cloud',
                        :reservation, :digest, :owner, 'llm_cloud', :provider, 'rate-1', 40, 50,
                        :units, :raw, :marked, 'RESERVED', clock_timestamp())
                """
            ),
            {
                "reservation": str(reservation),
                "allocation": str(allocation),
                "tenant": str(tenant),
                "customer": str(customer),
                "relationship": str(relationship),
                "agent": str(uuid4()),
                "work_item": str(uuid4()),
                "invocation": str(invocation),
                "digest": "a" * 64,
                "owner": str(uuid4()),
                "provider": str(uuid4()),
                "units": units,
                "raw": units * 40,
                "marked": units * 50,
            },
        )
        return reservation

    target, connect_args = asyncpg_engine_target(url)
    engine = create_async_engine(target, connect_args=connect_args)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                try:
                    # Foreign keys to the catalogue and organisations are out of scope here.
                    await connection.execute(text("SET LOCAL session_replication_role = replica"))
                except DBAPIError:
                    pytest.skip("superuser is required to seed allowance rows without their catalogue")
                session = AsyncSession(bind=connection, expire_on_commit=False)
                await session.execute(
                    text(
                        """
                        INSERT INTO business.relationship_commercial_authorities
                        (tenant_id, relationship_id, customer_id, authority_kind, accepted_contract_id,
                         contract_version, bundle_profile_id, professional_type, professional_version,
                         active, valid_from, evidence_id)
                        VALUES (:tenant, :relationship, :customer, 'ACCEPTED_OFFERING', :contract, 1,
                                :bundle, 'marketing', '1.0.0', true, clock_timestamp(), :evidence)
                        """
                    ),
                    {
                        "tenant": str(tenant),
                        "relationship": str(relationship),
                        "customer": str(customer),
                        "contract": str(uuid4()),
                        "bundle": str(uuid4()),
                        "evidence": str(uuid4()),
                    },
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO business.offering_component_allocations
                        (allocation_id, tenant_id, relationship_id, component_id, period_start,
                         period_end, granted_units, authority_evidence_id)
                        VALUES (:allocation, :tenant, :relationship, 'llm_cloud', :period_start,
                                :period_end, 10, :evidence)
                        """
                    ).bindparams(
                        bindparam("period_start", type_=DateTime(timezone=True)),
                        bindparam("period_end", type_=DateTime(timezone=True)),
                    ),
                    {
                        "allocation": str(allocation),
                        "tenant": str(tenant),
                        "relationship": str(relationship),
                        "period_start": now - timedelta(days=1),
                        "period_end": now + timedelta(days=30),
                        "evidence": str(uuid4()),
                    },
                )

                settled = await reserve(session, 2, uuid4())
                released = await reserve(session, 1, uuid4())
                for _ in range(2):
                    await shadow._mirror(session, tenant, settled, "reserve")
                    await shadow._mirror(session, tenant, released, "reserve")
                assert (await compute_parity(session, tenant)).clean

                await session.execute(
                    text(
                        """
                        UPDATE business.offering_component_reservations
                        SET state = 'SETTLED', actual_units = 1, actual_raw_paise = 40,
                            actual_marked_up_paise = 50, settled_at = clock_timestamp(),
                            settlement_evidence_id = :evidence
                        WHERE reservation_id = :reservation
                        """
                    ),
                    {"evidence": str(uuid4()), "reservation": str(settled)},
                )
                await session.execute(
                    text(
                        """
                        UPDATE business.offering_component_reservations
                        SET state = 'RELEASED', actual_units = 0, actual_raw_paise = 0,
                            actual_marked_up_paise = 0, settled_at = clock_timestamp(),
                            non_dispatch_evidence_id = :evidence
                        WHERE reservation_id = :reservation
                        """
                    ),
                    {"evidence": str(uuid4()), "reservation": str(released)},
                )
                for _ in range(2):
                    await shadow._mirror(session, tenant, settled, "settle")
                    await shadow._mirror(session, tenant, released, "release")

                report = await compute_parity(session, tenant, relationship)
                assert report.clean and report.compared == 1
                row = report.rows[0]
                assert (row.wallet_open_paise, row.wallet_settled_paise) == (0, 50)
                entries = (
                    await session.execute(
                        text(
                            "SELECT entry_kind, COUNT(*) FROM business.wallet_entries "
                            "WHERE tenant_id = :tenant GROUP BY entry_kind"
                        ),
                        {"tenant": str(tenant)},
                    )
                ).all()
                assert dict(entries) == {"CREDIT": 1, "RESERVE": 2, "SETTLE": 1, "RELEASE": 1}
                available = (
                    await session.execute(
                        text(
                            "SELECT business.wallet_available(a.tenant_id, a.account_id, clock_timestamp()) "
                            "FROM business.wallet_accounts a WHERE a.tenant_id = :tenant"
                        ),
                        {"tenant": str(tenant)},
                    )
                ).scalar_one()
                assert available == 10 * 50 - 50

                unmirrored = await reserve(session, 1, uuid4())
                await legacy._mirror(session, tenant, unmirrored, "reserve")
                differing = (await compute_parity(session, tenant)).differences
                assert [r.allowance_open_paise - r.wallet_open_paise for r in differing] == [50]
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()

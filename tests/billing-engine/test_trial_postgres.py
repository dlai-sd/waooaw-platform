# Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R011
# constitutional_basis: C-002, C-059, C-088, C-089
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import fakeredis
import psycopg2
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from trial.service import TrialService


REPO_ROOT = Path(__file__).parents[2]


@pytest_asyncio.fixture
async def postgres_trial():
    sync_url = os.getenv("WC107_POSTGRES_URL")
    if not sync_url:
        pytest.skip("run through scripts/test-wc107-trial-postgres.sh")
    with psycopg2.connect(sync_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE EXTENSION IF NOT EXISTS pgcrypto;
                CREATE SCHEMA business;
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'wbe_app') THEN
                        CREATE ROLE wbe_app;
                    END IF;
                END
                $$;
            """)
            cursor.execute("CREATE TABLE business.organisations (id UUID PRIMARY KEY)")
            cursor.execute("""
                CREATE TABLE business.wallet_buckets (
                    id UUID PRIMARY KEY,
                    customer_id UUID NOT NULL,
                    employment_contract_id UUID NOT NULL,
                    thread_type VARCHAR(50) NOT NULL,
                    balance_paise INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
            """)
            cursor.execute((REPO_ROOT / "infrastructure/postgres/init/13-customer-acquisition.sql").read_text())
    engine = create_async_engine(
        sync_url.replace("postgresql://", "postgresql+asyncpg://"),
        connect_args={"server_settings": {"search_path": "business,public"}},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    redis = fakeredis.FakeAsyncRedis(decode_responses=False)
    customer_id = uuid.uuid4()
    async with factory() as session:
        await session.execute(text("INSERT INTO organisations (id) VALUES (:id)"), {"id": customer_id})
        await session.commit()
    yield factory, redis, customer_id
    await redis.aclose()
    await engine.dispose()
    with psycopg2.connect(sync_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA business CASCADE")


@pytest.mark.asyncio
async def test_trial_ledger_is_durable_and_duplicate_safe_on_postgres(postgres_trial):
    factory, redis, customer_id = postgres_trial
    service = TrialService(
        session_factory=factory,
        redis_client=redis,
        settings=MagicMock(TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50, "llm_local": 200}}),
    )

    started = await service.start_trial(customer_id, "DMA", phone_verified=True, agent_version="1.0.0")

    async with factory() as session:
        allocation = (
            await session.execute(
                text("SELECT status, expires_at - started_at FROM trial_allocations WHERE trial_id = :id"),
                {"id": started.trial_id},
            )
        ).one()
        ledger = (
            await session.execute(
                text(
                    "SELECT thread_type, units_granted, units_consumed FROM trial_free_unit_ledger "
                    "WHERE trial_id = :id ORDER BY thread_type"
                ),
                {"id": started.trial_id},
            )
        ).all()
        buckets = (
            await session.execute(text("SELECT count(*) FROM wallet_buckets WHERE customer_id = :id"), {"id": customer_id})
        ).scalar_one()
    assert allocation.status == "ACTIVE"
    assert allocation[1].days == 14
    assert ledger == [("llm_cloud", 50, 0), ("llm_local", 200, 0)]
    assert buckets == 2
    assert await redis.get(f"wbe:customer:{customer_id}:mode") == b"TRIAL"

    with pytest.raises(HTTPException) as duplicate:
        await service.start_trial(customer_id, "DMA", phone_verified=True, agent_version="1.0.0")
    assert duplicate.value.status_code == 409
    async with factory() as session:
        assert (
            await session.execute(text("SELECT count(*) FROM trial_allocations WHERE customer_id = :id"), {"id": customer_id})
        ).scalar_one() == 1


@pytest.mark.asyncio
async def test_trial_allows_same_agent_type_at_a_new_version(postgres_trial):
    factory, redis, customer_id = postgres_trial
    service = TrialService(
        session_factory=factory,
        redis_client=redis,
        settings=MagicMock(TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50}}),
    )

    await service.start_trial(customer_id, "DMA", phone_verified=True, agent_version="1.0.0")
    await service.start_trial(customer_id, "DMA", phone_verified=True, agent_version="2.0.0")

    async with factory() as session:
        versions = (
            (
                await session.execute(
                    text("SELECT agent_version FROM trial_allocations WHERE customer_id = :id ORDER BY agent_version"),
                    {"id": customer_id},
                )
            )
            .scalars()
            .all()
        )
    assert versions == ["1.0.0", "2.0.0"]


@pytest.mark.asyncio
async def test_concurrent_same_version_trial_has_one_authoritative_winner(postgres_trial):
    factory, redis, customer_id = postgres_trial
    service = TrialService(
        session_factory=factory,
        redis_client=redis,
        settings=MagicMock(TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50}}),
    )

    outcomes = await asyncio.gather(
        service.start_trial(customer_id, "DMA", phone_verified=True, agent_version="1.0.0"),
        service.start_trial(customer_id, "DMA", phone_verified=True, agent_version="1.0.0"),
        return_exceptions=True,
    )

    successes = [outcome for outcome in outcomes if not isinstance(outcome, Exception)]
    conflicts = [outcome for outcome in outcomes if isinstance(outcome, HTTPException)]
    assert len(successes) == 1, outcomes
    assert len(conflicts) == 1, outcomes
    assert conflicts[0].status_code == 409
    assert conflicts[0].detail["code"] == "TRIAL_ALREADY_USED"

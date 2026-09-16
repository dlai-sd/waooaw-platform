# Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-08
# constitutional_basis: C-002, C-065, C-071, C-076, C-088
from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import fakeredis
import psycopg2
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from payment.commercial_outcomes import ZeroPriceCommercialOutcomeStore
from payment.models import (
    PaidActivationRequest,
    RelationshipCheckoutRequest,
    ZeroPriceActivationRequest,
)
from payment.onboarding import OnboardingService
from payment.paid_activation import PaidActivationService
from payment.zero_price_activation import ZeroPriceActivationService
from wallet.service import WalletService


REPO_ROOT = Path(__file__).parents[2]


@pytest_asyncio.fixture
async def postgres_activation():
    sync_url = os.getenv("WC059_POSTGRES_URL")
    if not sync_url:
        pytest.skip("run through scripts/test-wc059-postgres.sh")
    with psycopg2.connect(sync_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA IF EXISTS business CASCADE; DROP SCHEMA IF EXISTS institutional CASCADE")
            cursor.execute("DROP ROLE IF EXISTS business_app; DROP ROLE IF EXISTS wbe_app")
            cursor.execute("""
                CREATE SCHEMA business; CREATE SCHEMA institutional;
                CREATE ROLE business_app; CREATE ROLE wbe_app;
                CREATE TABLE business.organisations (id UUID PRIMARY KEY);
                CREATE TABLE business.employment_relationships (
                    relationship_id UUID NOT NULL, tenant_id UUID NOT NULL,
                    PRIMARY KEY (tenant_id, relationship_id));
                CREATE TABLE business.payment_intents (
                    razorpay_payment_id VARCHAR(128) PRIMARY KEY,
                    razorpay_order_id VARCHAR(128) NOT NULL,
                    customer_id UUID NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), activated_at TIMESTAMPTZ);
                CREATE TABLE business.trial_allocations (
                    trial_id UUID PRIMARY KEY, customer_id UUID NOT NULL, status VARCHAR(32) NOT NULL,
                    converted_at TIMESTAMPTZ, new_subscription_id UUID);
                CREATE TABLE institutional.billing_profiles (
                    agent_type VARCHAR(64) PRIMARY KEY, status VARCHAR(32) NOT NULL);
            """)
            cursor.execute(
                (REPO_ROOT / "infrastructure/postgres/init/21b-ae01-contract-activation.sql").read_text()
            )
            migration = (REPO_ROOT / "infrastructure/postgres/init/21c-ae01-paid-activation-ordering.sql").read_text()
            cursor.execute(migration)
            cursor.execute(migration)
            zero_price_migration = (
                REPO_ROOT / "infrastructure/postgres/init/34-wc095-zero-price-outcomes.sql"
            ).read_text()
            cursor.execute(zero_price_migration)
            cursor.execute(zero_price_migration)
    url = sync_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(
        url,
        connect_args={"server_settings": {"search_path": "business,institutional,public"}},
    )
    identifiers = [uuid.uuid4() for _ in range(7)]
    tenant_id, relationship_id, contract_id, acceptance_id = identifiers[:4]
    customer_id, payment_evidence_id, consent_id = identifiers[4:]
    payment_reference = f"pay_{uuid.uuid4().hex}"
    async with engine.begin() as connection:
        values = {
            "customer": customer_id, "tenant": tenant_id, "relationship": relationship_id,
            "payment": payment_reference, "contract": contract_id, "contract_hash": "a" * 64,
            "acceptance": acceptance_id, "consent": consent_id, "evidence": payment_evidence_id,
            "trial": uuid.uuid4(),
        }
        await connection.execute(text(
            "INSERT INTO business.organisations (id) VALUES (:customer)"), values)
        await connection.execute(text(
            "INSERT INTO business.employment_relationships (tenant_id, relationship_id) "
            "VALUES (:tenant, :relationship)"), values)
        await connection.execute(text(
            "INSERT INTO institutional.billing_profiles (agent_type, status) "
            "VALUES ('DMA', 'FOUNDER_AUTHORIZED')"))
        await connection.execute(text("""INSERT INTO business.payment_intents (
                razorpay_payment_id, razorpay_order_id, customer_id, status, tenant_id,
                relationship_id, accepted_contract_id, contract_version, contract_hash,
                contract_acceptance_id, payment_consent_evidence_id, payment_evidence_id,
                agent_type, bundle_tier)
            VALUES (:payment, 'order_wc059', :customer, 'CAPTURED', :tenant,
                :relationship, :contract, 3, :contract_hash, :acceptance, :consent,
                :evidence, 'DMA', 'STARTER')"""), values)
        await connection.execute(text(
            "INSERT INTO business.trial_allocations (trial_id, customer_id, status) "
            "VALUES (:trial, :customer, 'ACTIVE')"), values)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    request = PaidActivationRequest(
        tenant_id=tenant_id, relationship_id=relationship_id, activation_intent_id=uuid.uuid4(),
        accepted_contract_id=contract_id, contract_version=3, contract_acceptance_id=acceptance_id,
        payment_reference=payment_reference, payment_evidence_id=payment_evidence_id,
        correlation_id=uuid.uuid4(),
    )
    yield factory, request
    await engine.dispose()


@pytest_asyncio.fixture
async def postgres_zero_price_activation(postgres_activation):
    factory, paid_request = postgres_activation
    checkout_intent_id = uuid.uuid4()
    async with factory() as session:
        payment = (await session.execute(text("""
            SELECT customer_id, contract_hash, payment_consent_evidence_id,
                agent_type, bundle_tier
            FROM payment_intents
            WHERE razorpay_payment_id = :payment_reference
        """).bindparams(payment_reference=paid_request.payment_reference))).one()
        settings = MagicMock()
        settings.WAOOAW_ENVIRONMENT = "demo"
        settings.DEMO_PROMOTION_ENABLED = True
        settings.DEMO_PROMOTION_VERSION = "demo-100-v1"
        settings.DEMO_RENEWAL_CONSEQUENCE = "Renews at the accepted monthly price."
        settings.MAX_DISCOUNT_PCT = 100
        settings.RAZORPAY_KEY_ID = ""
        settings.RAZORPAY_KEY_SECRET = ""
        checkout = await OnboardingService(
            razorpay_client=AsyncMock(),
            settings=settings,
            zero_price_outcomes=ZeroPriceCommercialOutcomeStore(session),
        ).create_relationship_checkout(RelationshipCheckoutRequest(
            checkout_intent_id=checkout_intent_id,
            tenant_id=paid_request.tenant_id,
            customer_id=uuid.UUID(str(payment.customer_id)),
            relationship_id=paid_request.relationship_id,
            contract_id=paid_request.accepted_contract_id,
            contract_version=paid_request.contract_version,
            contract_hash=payment.contract_hash,
            contract_acceptance_id=paid_request.contract_acceptance_id,
            payment_consent_evidence_id=uuid.UUID(str(payment.payment_consent_evidence_id)),
            agent_type=payment.agent_type,
            bundle_tier=payment.bundle_tier,
            gross_amount_inr_paise=249900,
            gst_amount_inr_paise=38120,
            quote_version="quote-v1",
            idempotency_key=str(uuid.uuid4()),
        ))
    yield factory, ZeroPriceActivationRequest(
        tenant_id=paid_request.tenant_id,
        relationship_id=paid_request.relationship_id,
        activation_intent_id=uuid.uuid4(),
        accepted_contract_id=paid_request.accepted_contract_id,
        contract_version=paid_request.contract_version,
        contract_acceptance_id=paid_request.contract_acceptance_id,
        commercial_outcome_reference=checkout.commercial_outcome_reference or "",
        commercial_evidence_id=checkout.commercial_evidence_id or uuid.UUID(int=0),
        correlation_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_postgres_competing_paid_activation_has_one_canonical_outcome(postgres_activation) -> None:
    factory, request = postgres_activation
    replay = replace(request, activation_intent_id=uuid.uuid4(), correlation_id=uuid.uuid4())

    async def activate(candidate):
        async with factory() as session:
            return await PaidActivationService(
                session, WalletService(db=session, redis_client=fakeredis.aioredis.FakeRedis())
            ).activate(candidate)

    outcomes = await asyncio.gather(activate(request), activate(replay), return_exceptions=True)

    assert sum(not isinstance(outcome, Exception) for outcome in outcomes) == 1
    async with factory() as session:
        payment = (await session.execute(text(
            "SELECT status, activation_intent_id, activation_correlation_id FROM payment_intents"
        ))).one()
        subscriptions = (await session.execute(text("SELECT count(*) FROM paid_subscriptions"))).scalar_one()
        assert payment.status == "ACTIVATED"
        assert payment.activation_intent_id == request.activation_intent_id
        assert payment.activation_correlation_id == request.correlation_id
        assert subscriptions == 1


@pytest.mark.asyncio
async def test_postgres_response_loss_replay_returns_stored_subscription(postgres_activation) -> None:
    factory, request = postgres_activation
    async with factory() as session:
        service = PaidActivationService(
            session, WalletService(db=session, redis_client=fakeredis.aioredis.FakeRedis())
        )
        first = await service.activate(request)
    async with factory() as session:
        replay = await PaidActivationService(
            session, WalletService(db=session, redis_client=fakeredis.aioredis.FakeRedis())
        ).activate(request)

    assert replay.subscription_id == first.subscription_id


@pytest.mark.asyncio
async def test_postgres_zero_price_activation_replays_one_subscription(
    postgres_zero_price_activation,
) -> None:
    factory, request = postgres_zero_price_activation
    async with factory() as session:
        first = await ZeroPriceActivationService(
            session, WalletService(db=session, redis_client=fakeredis.aioredis.FakeRedis())
        ).activate(request)
    async with factory() as session:
        replay = await ZeroPriceActivationService(
            session, WalletService(db=session, redis_client=fakeredis.aioredis.FakeRedis())
        ).activate(request)
        outcome = (await session.execute(text("""
            SELECT status, outcome_subscription_id
            FROM zero_price_commercial_outcomes
            WHERE outcome_reference = :outcome_reference
        """).bindparams(outcome_reference=request.commercial_outcome_reference))).one()
        subscription_count = (await session.execute(text("""
            SELECT count(*) FROM paid_subscriptions
            WHERE commercial_outcome_reference = :outcome_reference
        """).bindparams(outcome_reference=request.commercial_outcome_reference))).scalar_one()

    assert replay.subscription_id == first.subscription_id
    assert outcome.status == "ACTIVATED"
    assert outcome.outcome_subscription_id == first.subscription_id
    assert subscription_count == 1
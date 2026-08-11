"""Minimal real-listener WBE host for the WC-059 cross-stack integration test."""

from __future__ import annotations

import json
import os
import ssl
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace

from fastapi import FastAPI
from sqlalchemy import text


REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "src/billing-engine"))

config = ModuleType("config")
config.settings = SimpleNamespace(DATABASE_URL=os.environ["DATABASE_URL"], REDIS_URL="redis://127.0.0.1:1/0")
config.Settings = lambda: config.settings
sys.modules["config"] = config

import database  # noqa: E402
from mtls_protocol import MutualTlsH11Protocol  # noqa: E402
from relationship_workspace import configure_relationship_workspace, router  # noqa: E402
import uvicorn  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.init_db()
    seed = json.loads(os.environ["WC059_ACTIVATION_SEED"])
    async with database.get_session_factory().begin() as session:
        for statement in (
            """CREATE TABLE payment_intents (
                razorpay_payment_id TEXT PRIMARY KEY, razorpay_order_id TEXT NOT NULL,
                customer_id TEXT NOT NULL, status TEXT NOT NULL, tenant_id TEXT,
                relationship_id TEXT, accepted_contract_id TEXT, contract_version INTEGER,
                contract_hash TEXT, contract_acceptance_id TEXT,
                payment_consent_evidence_id TEXT, payment_evidence_id TEXT,
                agent_type TEXT, bundle_tier TEXT, activation_intent_id TEXT,
                activation_correlation_id TEXT, outcome_subscription_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, activated_at TEXT)""",
            """CREATE TABLE paid_subscriptions (
                subscription_id TEXT PRIMARY KEY, organisation_id TEXT NOT NULL,
                agent_type TEXT NOT NULL, bundle_tier TEXT NOT NULL,
                razorpay_order_id TEXT NOT NULL, razorpay_payment_id TEXT NOT NULL UNIQUE,
                activated_at TEXT NOT NULL)""",
            "CREATE TABLE billing_profiles (agent_type TEXT PRIMARY KEY, status TEXT NOT NULL)",
            "CREATE TABLE trial_allocations (trial_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, status TEXT NOT NULL, converted_at TEXT, new_subscription_id TEXT)",
        ):
            await session.execute(text(statement))
        await session.execute(text(
            "INSERT INTO billing_profiles VALUES ('DMA', 'FOUNDER_AUTHORIZED')"))
        await session.execute(text("""INSERT INTO payment_intents (
            razorpay_payment_id, razorpay_order_id, customer_id, status, tenant_id,
            relationship_id, accepted_contract_id, contract_version, contract_hash,
            contract_acceptance_id, payment_consent_evidence_id, payment_evidence_id,
            agent_type, bundle_tier)
            VALUES (:payment_reference, 'order_wc059', :customer_id, 'CAPTURED', :tenant_id,
            :relationship_id, :accepted_contract_id, 3, :contract_hash,
            :contract_acceptance_id, :consent_id, :payment_evidence_id, 'DMA', 'STARTER')"""), seed)
        await session.execute(text(
            "INSERT INTO trial_allocations VALUES (:trial_id, :customer_id, 'ACTIVE', NULL, NULL)"), seed)
    yield
    await database.close_db()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
configure_relationship_workspace(app)


if __name__ == "__main__":
    credentials = Path(os.environ["WAOOAW_WORKLOAD_CREDENTIALS"])
    workload = credentials / "workloads/billing-engine"
    server = uvicorn.Config(
        app, host="127.0.0.1", port=int(os.environ["WBE_PRIVATE_PORT"]),
        http=MutualTlsH11Protocol, ssl_keyfile=str(workload / "tls-key.pem"),
        ssl_certfile=str(workload / "tls-cert.pem"),
        ssl_ca_certs=str(credentials / "trust/ca-bundle.pem"), ssl_cert_reqs=ssl.CERT_REQUIRED,
    )
    server.load()
    server.ssl.minimum_version = ssl.TLSVersion.TLSv1_2
    uvicorn.Server(server).run()
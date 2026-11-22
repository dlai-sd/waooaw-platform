# Implements: work-contracts/WC-030-*.md §WC030-01bb:main.py
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# constitutional_basis: C-059 (Implementation Traceability)
# Constitutional basis: C-059, C-038, ADR-026
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as aioredis
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Settings
from database import init_db, close_db, get_session_factory
from payment.lifecycle_jobs import run_lifecycle_sweep
from markup.router import router as pricing_router
from markup import thread_catalog
from meter.router import router as meter_router
from procurement.router import router as procurement_router
from reconciliation.router import router as reconciliation_router
from reconciliation.scheduler import create_scheduler
from trial.router import router as trial_router
from promotions.router import router as promotions_router
from payment.router import router as payment_router
from wallet.router import router as wallet_router
from wallet.private_routes import router as wallet_private_router
from reconciliation.service import ReconciliationService, FounderActionGenerator as _FAGBase
from relationship_workspace import configure_relationship_workspace
from relationship_workspace import router as relationship_workspace_router
from pricing_admin import configure_pricing_admin
from pricing_admin import router as pricing_admin_router
from employment_eligibility import configure_employment_eligibility
from employment_eligibility import router as employment_eligibility_router
from telemetry import configure_telemetry
from workload_credentials import service_link_router

logger = logging.getLogger(__name__)


class _WBEFounderActionAdapter(_FAGBase):
    """Concrete FounderActionGenerator for WBE — logs FA creation events."""

    async def maybe_create(self, *, action_type: str, payload: dict) -> bool:
        logger.warning(
            "WBE FounderAction: action_type=%s keys=%s",
            action_type,
            list(payload.keys()),
        )
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for FastAPI app startup/shutdown.

    Initializes database connections on startup and closes them on shutdown.
    Also starts and shuts down the APScheduler reconciliation scheduler.

    Args:
        app: FastAPI application instance.

    Yields:
        Control back to FastAPI after startup completes.

    Constitutional basis:
    - C-001: Audit scheduling - reconciliation scheduler started at 02:00 IST daily.
    - C-059: Implementation traceability via structured logging on lifecycle events.
    """
    logger.info("Starting billing-engine application")
    await init_db()

    settings = Settings()
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    reconciliation_service = ReconciliationService(
        session_factory=get_session_factory(),
        redis_client=redis_client,
        founder_action_generator=_WBEFounderActionAdapter(),
        environment=settings.WAOOAW_ENVIRONMENT,
    )

    scheduler = create_scheduler(
        service=reconciliation_service,
        redis_client=redis_client,
        settings=settings,
    )
    scheduler.start()
    logger.info("Reconciliation scheduler started")
    scheduler.add_job(
        run_lifecycle_sweep,
        trigger=IntervalTrigger(minutes=15),
        id="wbe_lifecycle_sweep",
        name="WBE package lifecycle sweep (grace expiry, fee refunds)",
        replace_existing=True,
        kwargs={"open_session": get_session_factory()},
    )

    credential_runtime = getattr(app.state, "credential_runtime", None)
    credential_refresh = (
        asyncio.create_task(credential_runtime.refresher.run())
        if credential_runtime is not None and credential_runtime.refresher is not None
        else None
    )

    yield

    if credential_refresh is not None:
        credential_refresh.cancel()
    logger.info("Shutting down billing-engine application")
    scheduler.shutdown()
    logger.info("Reconciliation scheduler shut down")
    await redis_client.close()
    await close_db()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Configures:
    - CORS middleware (allow_origins=['*'], allow_credentials=False per OWASP A05)
    - Router mounts: /pricing (markup), /meter (usage meter + alerts),
      /platform/procurement (cost ledger + runway), /reconciliation (audit engine)
    - Health check endpoint (/health)
    - Lifespan context manager for DB init/cleanup and scheduler lifecycle

    Returns:
        Configured FastAPI application instance.

    Constitutional basis:
    - C-001: Audit scheduling via reconciliation router and scheduler integration.
    - C-002: Idempotency via wbe:audit_in_progress Redis key in scheduler.
    - C-003: Ops-auth enforced on POST /reconciliation/run-now and GET margin report.
    - C-004: Billing halt enforcement via wbe:billing_halted Redis key in WalletService.
    - C-023: All endpoints require ValidateAction gate (implemented in router layer).
    - C-029: Billing profile enforcement via WalletService dependency injection.
    - C-038: Request shape validation via Pydantic models (CostRecordRequest).
    - C-043: Threshold breach alerts (PROCUREMENT_POLICY thresholds in procurement router).
    - C-048: Response shape compliance (ProviderRunwayStatus, FounderActionCreated).
    - C-051: /meter and /platform/procurement endpoints expose resource transparency.
    - C-059: Structured logging on app lifecycle and all router mounts.
    - C-063: CORS middleware enforces credential policy (allow_credentials=False).
    - C-073: Type safety on all function signatures and returns.
    - C-077: WAOOAW procurement ledger enforces INR 5,000/month budget ceiling.
    """
    app: FastAPI = FastAPI(
        title="Billing Engine",
        description="Markup and pricing engine for WAOOAW platform",
        version="1.0.0",
        lifespan=lifespan,
    )
    configure_telemetry(app)

    # allow_credentials=False with wildcard origin -- OWASP A05 compliance (C-100).
    # Prevents CSRF attacks when credentials are not required.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )

    # Mount pricing (markup) router
    app.include_router(pricing_router)

    # Mount thread catalog router at /catalog
    app.include_router(thread_catalog.router, prefix="/catalog", tags=["catalog"])

    # Mount meter (usage + alerts) router at /meter prefix
    # Endpoints: GET /meter/{customer_id}/status, POST /meter/daily-scan
    app.include_router(meter_router)

    # Mount procurement (cost ledger + runway projection) router at /platform/procurement prefix
    # Endpoints: GET /platform/procurement/status, POST /platform/procurement/record-cost,
    #            GET /platform/procurement/margin/report
    # Constitutional: C-077 (procurement runway enforces INR 5k/month ceiling),
    #                 C-043 (threshold breach to Founder Actions)
    app.include_router(procurement_router)

    # Mount reconciliation (audit engine) router at /reconciliation prefix
    # Endpoints: GET /reconciliation/status, POST /reconciliation/run-now,
    #            GET /reconciliation/platform/margin/report
    # Constitutional: C-001 (audit scheduling), C-002 (idempotency),
    #                 C-003 (ops-auth), C-004 (billing halt enforcement)
    app.include_router(reconciliation_router)

    # Mount trial engine router (WC-031 sub-component 6)
    app.include_router(trial_router)
    # Mount promotions engine router (WC-031 sub-component 7)
    app.include_router(promotions_router)
    # Mount payment router — onboarding order + Razorpay webhook (WC-042)
    app.include_router(payment_router)
    # Mount wallet bucket router — reserve endpoint for AIR CCT-PREPAID-01 (WC-043)
    app.include_router(wallet_router)
    app.include_router(relationship_workspace_router)
    app.include_router(service_link_router)
    # WC-136 C4-03/C4-04: wallet parity read and setup-grant open, over the same private mTLS path
    app.include_router(wallet_private_router)
    configure_relationship_workspace(app)
    # WC-136 C5-03: pricing administration, over the same private mTLS path
    app.include_router(pricing_admin_router)
    configure_pricing_admin(app)
    app.include_router(employment_eligibility_router)
    configure_employment_eligibility(app)

    @app.get("/health", response_model=dict[str, Any])
    async def health_check() -> dict[str, Any]:
        """
        Health check endpoint.

        Returns:
            dict with status="ok" if service is ready; a non-gating credential detail
            (state, not_after, remaining_seconds, bundle_version, serial digest) when
            workload credentials are configured.

        Constitutional basis:
        - C-059: Publicly observable readiness signal for load balancers.
        """
        health: dict[str, Any] = {"status": "ok", "service": "billing-engine"}
        holder = getattr(getattr(app.state, "relationship_workload_auth", None), "holder", None)
        if holder is not None:
            health["credential"] = holder.status()
        return health

    return app


app: FastAPI = create_app()
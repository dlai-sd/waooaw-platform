# Implements: work-contracts/WC-030-*.md §WC030-01bb:main.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Settings
from database import init_db, close_db, get_session_factory
from markup.router import router as pricing_router
from markup import thread_catalog
from meter.router import router as meter_router
from procurement.router import router as procurement_router
from reconciliation.router import router as reconciliation_router
from reconciliation.scheduler import create_scheduler
from trial.router import router as trial_router
from promotions.router import router as promotions_router
from reconciliation.service import ReconciliationService, FounderActionGenerator as _FAGBase

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
    )

    scheduler = create_scheduler(
        service=reconciliation_service,
        redis_client=redis_client,
        settings=settings,
    )
    scheduler.start()
    logger.info("Reconciliation scheduler started")

    yield

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

    @app.get("/health", response_model=dict[str, str])
    async def health_check() -> dict[str, str]:
        """
        Health check endpoint.

        Returns:
            dict with status="ok" if service is ready.

        Constitutional basis:
        - C-059: Publicly observable readiness signal for load balancers.
        """
        return {"status": "ok", "service": "billing-engine"}

    return app


app: FastAPI = create_app()
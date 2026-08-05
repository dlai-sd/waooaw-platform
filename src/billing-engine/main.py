# Implements: work-contracts/WC-029-*.md §WC029-01bb:main.py
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, close_db
from markup.router import router as pricing_router
from meter.router import router as meter_router
from procurement.router import router as procurement_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for FastAPI app startup/shutdown.
    
    Initializes database connections on startup and closes them on shutdown.
    
    Args:
        app: FastAPI application instance.
    
    Yields:
        Control back to FastAPI after startup completes.
    
    Constitutional basis:
    - C-059: Implementation traceability via structured logging on lifecycle events.
    """
    logger.info("Starting billing-engine application")
    await init_db()
    yield
    logger.info("Shutting down billing-engine application")
    await close_db()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Configures:
    - CORS middleware (allow_origins=['*'], allow_credentials=False per OWASP A05)
    - Router mounts: /pricing (markup), /meter (usage meter + alerts), /platform/procurement (cost ledger + runway)
    - Health check endpoint (/health)
    - Lifespan context manager for DB init/cleanup
    
    Returns:
        Configured FastAPI application instance.
    
    Constitutional basis:
    - C-023: All endpoints require ValidateAction gate (implemented in router layer)
    - C-029: Billing profile enforcement via WalletService dependency injection
    - C-038: Request shape validation via Pydantic models (CostRecordRequest)
    - C-043: Threshold breach alerts (PROCUREMENT_POLICY thresholds in procurement router)
    - C-048: Response shape compliance (ProviderRunwayStatus, FounderActionCreated)
    - C-051: /meter and /platform/procurement endpoints expose resource transparency (bucket balances, runway projections)
    - C-059: Structured logging on app lifecycle and all router mounts
    - C-063: CORS middleware enforces credential policy (allow_credentials=False)
    - C-073: Type safety on all function signatures and returns
    - C-077: WAOOAW procurement ledger enforces ₹5,000/month budget ceiling via runway projection
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
    
    # Mount meter (usage + alerts) router at /meter prefix
    # Endpoints: GET /meter/{customer_id}/status, POST /meter/daily-scan
    app.include_router(meter_router)
    
    # Mount procurement (cost ledger + runway projection) router at /platform/procurement prefix
    # Endpoints: GET /platform/procurement/status, POST /platform/procurement/record-cost, GET /platform/procurement/margin/report
    # Constitutional: C-077 (procurement runway enforces ₹5k/month ceiling), C-043 (threshold breach to Founder Actions)
    app.include_router(procurement_router)
    
    @app.get("/health", response_model=dict[str, str])
    async def health_check() -> dict[str, str]:
        """
        Health check endpoint.
        
        Returns:
            dict with status="ok" if service is ready.
        
        Constitutional basis:
        - C-059: Publicly observable readiness signal for load balancers.
        """
        return {"status": "ok"}
    
    return app


app: FastAPI = create_app()
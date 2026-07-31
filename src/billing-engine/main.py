# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.billing_engine.config import settings
from src.billing_engine.markup.router import router as pricing_router

logger = logging.getLogger(__name__)

# ── FastAPI application setup ────────────────────────────────────────────────

app: FastAPI = FastAPI(
    title="WAOOAW Billing Engine",
    description="WBE — Wallet, Markup, Meter, Procurement, Reconciliation services",
    version="1.0.0",
)

# ── CORS middleware ──────────────────────────────────────────────────────────

if settings.environment != "production":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── Health check endpoint ────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "healthy"}


# ── Router registration ─────────────────────────────────────────────────────

app.include_router(pricing_router)

logger.info("WAOOAW Billing Engine started on port %d", settings.port)
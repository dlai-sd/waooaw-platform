# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from markup.router import router as markup_router

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application Setup
# ─────────────────────────────────────────────────────────────────────────────

app: FastAPI = FastAPI(
    title="WAOOAW Billing Engine",
    version="1.0.0",
    description="WBE: Wallet, Markup, Metering, Procurement, Reconciliation",
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS Configuration
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Router Registration
# ─────────────────────────────────────────────────────────────────────────────

# C-089: Markup Engine (pricing floor, derivation, validation)
# C-038: Price validation with minimum_compliant_price_paise on floor violation
# C-051: Non-discrimination (all agent types subject to same margin floor)
# C-048: Non-exploitation (margin floor prevents cost-inversion pricing)
app.include_router(
    markup_router,
    prefix="/pricing",
    tags=["pricing"],
)

logger.info("billing_engine_startup", extra={"service": "wbe", "port": 8140})


# ─────────────────────────────────────────────────────────────────────────────
# Health Check
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "ok", "service": "billing-engine"}
# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-038, C-048, C-051, C-059
from __future__ import annotations

import logging

from fastapi import FastAPI

from markup.router import router as pricing_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="WAOOAW Billing Engine (WBE)",
    description="Wallet, Markup, Meter, Procurement, Reconciliation, Trial, Promotions",
    version="1.0.0",
)

# ── Mount routers ────────────────────────────────────────────────────────────
app.include_router(pricing_router)

logger.info("Billing Engine (WBE) started; pricing router mounted at /pricing")


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for orchestration."""
    return {"status": "healthy"}
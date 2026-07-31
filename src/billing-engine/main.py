# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-01b
# constitutional_basis: C-023, C-059, C-063, C-088, C-089
from __future__ import annotations

from fastapi import FastAPI

from markup.thread_catalog import router as catalog_router
from markup.router import router as pricing_router

app: FastAPI = FastAPI(
    title="WAOOAW Wallet & Billing Engine (WBE)",
    description="Prepaid wallet, markup engine, usage meter, alert engine. ADR-034.",
    version="0.1.0",
)

app.include_router(catalog_router, prefix="/catalog", tags=["thread-catalog"])
app.include_router(pricing_router, prefix="/pricing", tags=["pricing"])


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for WBE service."""
    return {"status": "ok", "service": "billing-engine", "version": "0.1.0"}
# Implements: architecture/reference/billing/wbe-component-spec.md §1 Service Entry & §2.3 Markup Engine
# constitutional_basis: C-088, C-089, C-090, C-091, C-023, C-038, C-048, C-051, C-059, ADR-034

from __future__ import annotations

from fastapi import FastAPI

from markup.thread_catalog import router as catalog_router
from markup.router import router as markup_router

app: FastAPI = FastAPI(
    title="WAOOAW Wallet & Billing Engine (WBE)",
    description="Prepaid wallet, markup engine, usage meter, alert engine. ADR-034.",
    version="0.1.0",
)

app.include_router(catalog_router, prefix="/catalog", tags=["thread-catalog"])
app.include_router(markup_router, prefix="/pricing", tags=["markup-engine"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "billing-engine", "version": "0.1.0"}
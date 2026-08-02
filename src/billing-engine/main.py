# Implements: architecture/reference/billing/wbe-component-spec.md §1 Service Entry
# constitutional_basis: C-088 (Billing Profile), C-091 (Thread Catalog), C-059, ADR-034

from fastapi import FastAPI

from markup.thread_catalog import router as catalog_router

app = FastAPI(
    title="WAOOAW Wallet & Billing Engine (WBE)",
    description="Prepaid wallet, markup engine, usage meter, alert engine. ADR-034.",
    version="0.1.0",
)

app.include_router(catalog_router, prefix="/catalog", tags=["thread-catalog"])


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "billing-engine", "version": "0.1.0"}

from markup.router import router as pricing_router

app.include_router(pricing_router, prefix="/pricing", tags=["pricing"])

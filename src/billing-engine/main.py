# Implements: architecture/reference/billing/wbe-component-spec.md §2.1 WBE Architecture
# constitutional_basis: C-023, C-038, C-048, C-051, C-059, C-088, C-089, C-090, C-091
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from markup.router import router as markup_router
from thread_catalog import router as thread_catalog_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="WAOOAW Billing Engine",
    description="WBE: Markup Engine, Meter Engine, Procurement, Reconciliation, Trial, Promotions",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# ── CORS Configuration ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ── Router Registration ─────────────────────────────────────────────────────
# C-091: Thread Catalog provides agent→thread mappings (Tier 2 decision space)
app.include_router(thread_catalog_router)

# C-089: Markup Engine validates prices against constitutional margin floor
# C-038: /pricing endpoints return 422 on C-089 violation with minimum_compliant_price_paise
app.include_router(markup_router)

logger.info("billing_engine_initialized service=wbe version=1.0.0")


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "wbe"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.bind_host,
        port=settings.bind_port,
        log_level=settings.log_level.lower(),
    )
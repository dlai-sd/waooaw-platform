# Implements: architecture/reference/billing/wbe-component-spec.md §2.0 WBE Service
# constitutional_basis: C-088, C-089, C-090, C-091, C-038, C-048, C-051, C-059
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.billing_engine.config import settings
from src.billing_engine.markup.router import router as markup_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> object:
    """Lifecycle hooks: startup and shutdown."""
    logger.info("WBE service starting on port %d", settings.port)
    yield
    logger.info("WBE service shutting down")


app = FastAPI(
    title="WAOOAW Billing Engine",
    description="Constitutional billing, pricing, and metering service",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ────────────────────────────────────────────────────────────
app.include_router(markup_router, prefix="/pricing", tags=["pricing"])

logger.info("WBE service initialized")
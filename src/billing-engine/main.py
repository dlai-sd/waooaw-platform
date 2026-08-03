# Implements: WC027-01b — WC027-01ba
# constitutional_basis: C-059, C-082
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Settings
from database import init_db, close_db
from markup.router import router as pricing_router
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for FastAPI app startup/shutdown"""
    logger.info("Starting billing-engine application")
    await init_db()
    yield
    logger.info("Shutting down billing-engine application")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Billing Engine",
        description="Markup and pricing engine for WAOOAW platform",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(pricing_router)
    
    @app.get("/health")
    async def health_check() -> dict:
        """Health check endpoint"""
        return {"status": "ok"}
    
    return app


app = create_app()
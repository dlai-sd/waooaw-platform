# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §2 (oauth-vault)
# Implements: adr/ADR-021-external-platform-oauth-token-management.md §2
# constitutional_basis: C-003 (authority licensed), ADR-014 (secret management), ADR-021

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from .exception_handler import install_exception_handler
from .refresh_scheduler import RefreshScheduler
from .routes.tokens import router as tokens_router

logger = logging.getLogger(__name__)

VAULT_ALIAS = os.getenv("OAUTH_VAULT_ALIAS", "waooaw-dev-kv")
PR_INTERNAL_URL = os.getenv("PROFESSIONAL_RUNTIME_URL", "http://professional-runtime:5003")


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    scheduler = RefreshScheduler(vault_alias=VAULT_ALIAS, pr_internal_url=PR_INTERNAL_URL)
    application.state.scheduler = scheduler
    task = asyncio.create_task(scheduler.run_forever())
    logger.info("oauth-vault started. vault_alias=%s", VAULT_ALIAS)
    try:
        yield
    finally:
        scheduler.stop()
        task.cancel()


app = FastAPI(
    title="WAOOAW oauth-vault",
    description="Secure token storage and retrieval. ADR-021 §2.",
    version="1.0.0",
    lifespan=_lifespan,
)

install_exception_handler(app)
app.include_router(tokens_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "oauth-vault"}


if __name__ == "__main__":  # pragma: no cover
    uvicorn.run("oauth_vault.main:app", host="0.0.0.0", port=8130, reload=False)

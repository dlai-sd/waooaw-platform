"""Deterministic local server for the existing DMA social MCP deployables."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §6, §8.2
# Constitutional basis: C-023, C-041, C-059, C-063, C-070, C-078

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException

from mcp.common import CredentialHealth, DeterministicTokenBroker, SocialToolContext, SocialToolDenied
from mcp.facebook import FacebookMcp
from mcp.instagram import InstagramMcp
from mcp.platform_analytics import PlatformAnalyticsMcp


class AllowingCeEmulator:
    def validate(self, action: str, context: SocialToolContext) -> None:
        if not context.ce_evidence_ref or not action:
            raise ValueError("AUTHORITY_DENIED")


def create_app(service_name: str) -> FastAPI:
    now = datetime.now(timezone.utc)
    broker = DeterministicTokenBroker(
        CredentialHealth(
            state="VALID",
            credential_ref="emulator-only",
            token_version="1",
            scopes=frozenset(
                {
                    "instagram_content_publish",
                    "pages_manage_posts",
                    "instagram_manage_insights",
                    "read_insights",
                }
            ),
            account_ref="emulator-account",
            expires_at=now + timedelta(hours=1),
        )
    )
    ce = AllowingCeEmulator()
    owners = {
        "instagram-mcp": InstagramMcp(ce, broker),
        "facebook-mcp": FacebookMcp(ce, broker),
        "platform-analytics-mcp": PlatformAnalyticsMcp(ce, broker),
    }
    if service_name not in owners:
        raise ValueError("MCP_SERVICE_UNSUPPORTED")
    owner = owners[service_name]
    app = FastAPI(title=service_name, version="1.0.0-emulator")

    @app.get("/health")
    def health() -> dict[str, object]:
        return {"status": "ok", "emulator": True, "service": service_name}

    @app.get("/tools")
    def tools() -> dict[str, object]:
        return {"tools": sorted(owner.operations), "emulator": True}

    @app.post("/call/{operation}")
    def call(operation: str, context: SocialToolContext) -> dict[str, object]:
        if context.channel_account_ref != "emulator-account":
            raise HTTPException(status_code=403, detail="NOT_ACCESSIBLE")
        try:
            return owner.call(operation, context)
        except SocialToolDenied as error:
            raise HTTPException(status_code=409, detail=error.reason.value) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return app


app = create_app(os.environ.get("DMA_MCP_SERVICE", "instagram-mcp"))

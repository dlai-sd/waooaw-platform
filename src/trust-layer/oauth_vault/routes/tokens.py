# Implements: adr/ADR-021-external-platform-oauth-token-management.md §2 Token routes
# constitutional_basis: C-003 (authority licensed — revoke requires evidence first), ADR-014, ADR-021

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request

from ..models import StoreTokenRequest, TokenData, TokenHealthResponse
from ..vault_client import VaultClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tokens", tags=["tokens"])

VAULT_ALIAS = os.getenv("OAUTH_VAULT_ALIAS", "waooaw-dev-kv")
CE_GRPC_ADDRESS = os.getenv("CONSTITUTIONAL_ENGINE_ADDRESS", "constitutional-engine:7000")
# BP provider registry — used by revoke path to record erasure intent
BP_PROVIDER_URL = os.getenv("BUSINESS_PLATFORM_URL", "http://business-platform:5001")


def _vault(request: Request) -> VaultClient:
    """Resolve VaultClient from app state (allows test injection)."""
    client = getattr(request.app.state, "vault_client", None)
    if client is None:
        request.app.state.vault_client = VaultClient(VAULT_ALIAS)
    return request.app.state.vault_client


def _token_path(contract_id: str, provider_name: str) -> str:
    return f"providers/{contract_id}/{provider_name}"


# ─── Store ─────────────────────────────────────────────────────────────────────

@router.post("/{contract_id}/{provider_name}", status_code=201)
async def store_token(
    contract_id: str,
    provider_name: str,
    body: StoreTokenRequest,
    request: Request,
) -> dict:
    """Store OAuth token or API key in AKV. Token value never written to any log (ADR-014)."""
    vault = _vault(request)
    path = _token_path(contract_id, provider_name)

    token_data = TokenData(
        access_token=body.access_token,
        refresh_token=body.refresh_token,
        expires_at=body.expires_at,
        provider_name=provider_name,
        contract_id=contract_id,
        extra_data=body.extra_data,
    )
    await vault.store_token(path, token_data)

    # Register in scheduler registry so health checks include this token.
    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.register(contract_id, provider_name)

    logger.info(
        "store_token OK contract_id=%s provider_name=%s",
        contract_id, provider_name,
    )
    return {"stored": True, "contract_id": contract_id, "provider_name": provider_name}


# ─── Retrieve (with auto-refresh) ─────────────────────────────────────────────

@router.get("/{contract_id}/{provider_name}")
async def retrieve_token(
    contract_id: str,
    provider_name: str,
    request: Request,
) -> dict:
    """
    Retrieve current access token. Auto-refreshes if EXPIRING_SOON.
    Returns sanitised response — access_token omitted from log (ADR-014).
    """
    vault = _vault(request)
    path = _token_path(contract_id, provider_name)

    token_data = await vault.retrieve_token(path)
    if token_data is None:
        raise HTTPException(status_code=404, detail={"error": "TOKEN_NOT_FOUND"})

    status = token_data.health_status()

    if status == "EXPIRED":
        raise HTTPException(status_code=410, detail={"error": "TOKEN_EXPIRED", "status": "EXPIRED"})

    if status == "EXPIRING_SOON" and token_data.refresh_token:
        # Best-effort auto-refresh inline; failures are non-fatal.
        refreshed = await _try_refresh(contract_id, provider_name, token_data, vault, path)
        if refreshed:
            token_data = refreshed

    # ADR-014: access_token returned to caller but never written to logs.
    logger.info(
        "retrieve_token OK contract_id=%s provider_name=%s status=%s",
        contract_id, provider_name, status,
    )
    return {
        "access_token": token_data.access_token,
        "expires_at": token_data.expires_at.isoformat() if token_data.expires_at else None,
        "status": token_data.health_status(),
    }


async def _try_refresh(
    contract_id: str,
    provider_name: str,
    token_data: TokenData,
    vault: VaultClient,
    path: str,
) -> TokenData | None:
    """Attempt OAuth refresh_token flow. Returns refreshed TokenData or None on failure."""
    refresh_url = _provider_refresh_url(provider_name)
    if not refresh_url:
        logger.warning(
            "auto_refresh skipped: no refresh_url for provider=%s", provider_name
        )
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(refresh_url, data={
                "grant_type": "refresh_token",
                "refresh_token": token_data.refresh_token,
            })
        if resp.status_code != 200:
            logger.warning(
                "auto_refresh failed provider=%s status=%d", provider_name, resp.status_code
            )
            return None
        data = resp.json()
        from datetime import timedelta
        expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
        refreshed = TokenData(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", token_data.refresh_token),
            expires_at=expires_at,
            provider_name=provider_name,
            contract_id=contract_id,
            extra_data=token_data.extra_data,
        )
        await vault.store_token(path, refreshed)
        logger.info("auto_refresh OK provider=%s", provider_name)
        return refreshed
    except Exception as exc:
        # Log exception type only — no token, no refresh token.
        logger.warning("auto_refresh error provider=%s err=%s", provider_name, type(exc).__name__)
        return None


def _provider_refresh_url(provider_name: str) -> str | None:
    """Map provider name to its OAuth2 token refresh endpoint."""
    _refresh_urls: dict[str, str] = {
        "meta": "https://graph.facebook.com/oauth/access_token",
        "google": "https://oauth2.googleapis.com/token",
        "instagram": "https://api.instagram.com/oauth/access_token",
    }
    return _refresh_urls.get(provider_name.lower())


# ─── Revoke ────────────────────────────────────────────────────────────────────

@router.delete("/{contract_id}/{provider_name}", status_code=200)
async def revoke_token(
    contract_id: str,
    provider_name: str,
    request: Request,
) -> dict:
    """
    Revoke token. C-003: CE evidence record MUST be created before AKV deletion.
    Constitutional requirement: evidence first, then delete.
    """
    vault = _vault(request)
    path = _token_path(contract_id, provider_name)

    # C-003 / C-023: record revocation intent in CE audit sink BEFORE deleting token.
    ce_recorded = await _record_revocation_in_ce(contract_id, provider_name, request)
    if not ce_recorded:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "CE_UNAVAILABLE",
                "message": "Constitutional Engine unavailable. Revocation requires CE evidence record (C-003).",
            },
        )

    await vault.delete_token(path)

    scheduler = getattr(request.app.state, "scheduler", None)
    if scheduler is not None:
        scheduler.unregister(contract_id, provider_name)

    logger.info(
        "revoke_token OK contract_id=%s provider_name=%s ce_recorded=%s",
        contract_id, provider_name, ce_recorded,
    )
    return {"revoked": True, "contract_id": contract_id, "provider_name": provider_name}


async def _record_revocation_in_ce(
    contract_id: str,
    provider_name: str,
    request: Request,
) -> bool:
    """POST revocation intent to CE audit sink. Returns True on success."""
    ce_client = getattr(request.app.state, "ce_client", None)
    if ce_client is not None:
        # Test-injectable CE client: just call it directly.
        return await ce_client.record_revocation(contract_id, provider_name)

    ce_http_url = os.getenv("CE_HTTP_URL", f"http://{CE_GRPC_ADDRESS}")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{ce_http_url}/internal/revocation",
                json={"contract_id": contract_id, "provider_name": provider_name},
            )
        return resp.status_code in (200, 201, 202)
    except Exception as exc:
        logger.error("CE unavailable for revocation err=%s", type(exc).__name__)
        return False


# ─── Health ────────────────────────────────────────────────────────────────────

@router.get("/health/{contract_id}/{provider_name}", tags=["health"])
async def token_health(
    contract_id: str,
    provider_name: str,
    request: Request,
) -> TokenHealthResponse:
    """Token status: VALID | EXPIRING_SOON | EXPIRED | NOT_CONNECTED."""
    vault = _vault(request)
    path = _token_path(contract_id, provider_name)

    token_data = await vault.retrieve_token(path)
    if token_data is None:
        return TokenHealthResponse(
            status="NOT_CONNECTED",
            provider_name=provider_name,
            contract_id=contract_id,
        )

    status = token_data.health_status()
    return TokenHealthResponse(
        status=status,
        provider_name=provider_name,
        contract_id=contract_id,
        expires_at=token_data.expires_at,
    )

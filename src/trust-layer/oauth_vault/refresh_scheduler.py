# Implements: adr/ADR-021-external-platform-oauth-token-management.md §3 Token Refresh
# constitutional_basis: ADR-021 (background refresh), C-003 (authority licensed)

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx

from .models import TokenData
from .vault_client import VaultClient

logger = logging.getLogger(__name__)

_REFRESH_INTERVAL_SECONDS = 1800   # 30 minutes (ADR-021 §3)
_EXPIRY_WARN_SECONDS = 7200        # 2 hours: EXPIRING_SOON threshold


class RefreshScheduler:
    """
    Background task: checks all registered tokens every 30 minutes.
    EXPIRING_SOON tokens are proactively refreshed via provider OAuth2 endpoint.
    On refresh failure, PLATFORM_TOKEN_EXPIRED event posted to Professional Runtime.
    """

    def __init__(self, vault_alias: str, pr_internal_url: str) -> None:
        self._vault = VaultClient(vault_alias)
        self._pr_url = pr_internal_url
        self._registry: set[tuple[str, str]] = set()   # (contract_id, provider_name)
        self._running = True

    def register(self, contract_id: str, provider_name: str) -> None:
        self._registry.add((contract_id, provider_name))

    def unregister(self, contract_id: str, provider_name: str) -> None:
        self._registry.discard((contract_id, provider_name))

    def stop(self) -> None:
        self._running = False

    async def run_forever(self) -> None:
        """Run the refresh loop until stop() is called."""
        logger.info("RefreshScheduler started interval=%ds", _REFRESH_INTERVAL_SECONDS)
        while self._running:
            try:
                await self._run_once()
            except Exception as exc:
                logger.error("RefreshScheduler tick error: %s", type(exc).__name__)
            await asyncio.sleep(_REFRESH_INTERVAL_SECONDS)

    async def run_once(self) -> None:
        """Public entry point for tests — runs one tick synchronously."""
        await self._run_once()

    async def _run_once(self) -> None:
        if not self._registry:
            return
        logger.info("RefreshScheduler tick: checking %d tokens", len(self._registry))
        for contract_id, provider_name in list(self._registry):
            await self._check_and_refresh(contract_id, provider_name)

    async def _check_and_refresh(self, contract_id: str, provider_name: str) -> None:
        path = f"providers/{contract_id}/{provider_name}"
        token_data = await self._vault.retrieve_token(path)
        if token_data is None:
            return

        status = token_data.health_status()

        if status == "VALID":
            return

        if status == "EXPIRING_SOON" and token_data.refresh_token:
            success = await self._refresh_token(contract_id, provider_name, token_data, path)
            if not success:
                await self._notify_pr_token_expired(contract_id, provider_name)
            return

        if status in ("EXPIRED", "EXPIRING_SOON"):
            # Expired or EXPIRING_SOON with no refresh_token
            await self._notify_pr_token_expired(contract_id, provider_name)

    async def _refresh_token(
        self,
        contract_id: str,
        provider_name: str,
        token_data: TokenData,
        path: str,
    ) -> bool:
        """Attempt OAuth2 refresh flow. Returns True on success."""
        refresh_url = self._provider_refresh_url(provider_name)
        if not refresh_url:
            logger.warning("refresh_token: no refresh_url for provider=%s", provider_name)
            return False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(refresh_url, data={
                    "grant_type": "refresh_token",
                    "refresh_token": token_data.refresh_token,
                })

            if resp.status_code != 200:
                logger.warning(
                    "refresh_token: provider=%s returned status=%d",
                    provider_name, resp.status_code,
                )
                return False

            data = resp.json()
            expires_at = datetime.now(tz=timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))
            refreshed = TokenData(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", token_data.refresh_token),
                expires_at=expires_at,
                provider_name=provider_name,
                contract_id=contract_id,
                extra_data=token_data.extra_data,
            )
            await self._vault.store_token(path, refreshed)
            logger.info("refresh_token OK provider=%s contract_id=%s", provider_name, contract_id)
            return True

        except Exception as exc:
            logger.warning("refresh_token error provider=%s err=%s", provider_name, type(exc).__name__)
            return False

    async def _notify_pr_token_expired(self, contract_id: str, provider_name: str) -> None:
        """POST PLATFORM_TOKEN_EXPIRED event to Professional Runtime internal endpoint."""
        payload = {
            "event": "PLATFORM_TOKEN_EXPIRED",
            "contract_id": contract_id,
            "provider_name": provider_name,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{self._pr_url}/internal/events", json=payload)
            logger.info(
                "PR notified PLATFORM_TOKEN_EXPIRED contract_id=%s provider=%s",
                contract_id, provider_name,
            )
        except Exception as exc:
            logger.error(
                "PR notification failed contract_id=%s provider=%s err=%s",
                contract_id, provider_name, type(exc).__name__,
            )

    @staticmethod
    def _provider_refresh_url(provider_name: str) -> str | None:
        _urls: dict[str, str] = {
            "meta": "https://graph.facebook.com/oauth/access_token",
            "google": "https://oauth2.googleapis.com/token",
            "instagram": "https://api.instagram.com/oauth/access_token",
        }
        return _urls.get(provider_name.lower())

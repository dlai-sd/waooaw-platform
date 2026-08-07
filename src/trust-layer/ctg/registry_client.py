# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §2 step 1
# constitutional_basis: C-059 (traceability — provider config drives audit record fields)
from __future__ import annotations

import logging
import time
from uuid import UUID

import httpx

from .models import ProviderConfig

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 60.0


class ProviderRegistryClient:
    """
    Fetches ProviderConfig from BP GET /api/v1/providers/{name}.
    In-memory TTL cache (60 s) per (tenant_id, provider_name) key.
    """

    def __init__(self, bp_base_url: str, internal_jwt: str) -> None:
        self._bp_base_url = bp_base_url.rstrip("/")
        self._internal_jwt = internal_jwt
        # key: (tenant_id_str | None, provider_name) → (config, monotonic timestamp)
        self._cache: dict[tuple[str | None, str], tuple[ProviderConfig, float]] = {}

    async def get_config(self, tenant_id: UUID | None, provider_name: str) -> ProviderConfig:
        """Return ProviderConfig from cache or BP. Cache miss or stale → refresh."""
        key = (str(tenant_id) if tenant_id is not None else None, provider_name)
        now = time.monotonic()

        entry = self._cache.get(key)
        if entry is not None and now - entry[1] < _CACHE_TTL_SECONDS:
            return entry[0]

        url = f"{self._bp_base_url}/api/v1/providers/{provider_name}"
        headers = {"Authorization": f"Bearer {self._internal_jwt}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

        data = response.json()
        config = ProviderConfig(
            provider_name=data["provider_name"],
            auth_method=data["auth_method"],
            mcp_server_url=data.get("mcp_server_url"),
            vault_path_key=data["vault_path_key"],
            scope_set=list(data.get("scope_set") or []),
        )
        self._cache[key] = (config, now)
        logger.debug(
            "registry_client: cached provider_name=%s tenant=%s",
            provider_name,
            key[0],
        )
        return config

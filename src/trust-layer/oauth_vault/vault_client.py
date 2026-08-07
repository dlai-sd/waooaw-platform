# Implements: adr/ADR-021-external-platform-oauth-token-management.md §2 oauth-vault
# Implements: adr/ADR-014-secret-management.md §Tier 3 (Azure Key Vault cloud)
# constitutional_basis: ADR-014 (secret management), OWASP A02 (no secrets in logs)

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from .models import TokenData

logger = logging.getLogger(__name__)

# ADR-014: vault_alias logged only — never the full KV URL or any token fragment.
_NEVER_LOG = frozenset({"access_token", "refresh_token", "token", "secret", "key"})


def _make_secret_name(path: str) -> str:
    """Azure Key Vault secret names: alphanumeric + hyphens only, max 127 chars."""
    return path.replace("/", "--").replace("_", "-")[:127]


class VaultClient:
    """Azure Key Vault client. Sync SDK wrapped in asyncio.to_thread for non-blocking use."""

    def __init__(self, vault_alias: str) -> None:
        self._vault_alias = vault_alias
        vault_url = f"https://{vault_alias}.vault.azure.net/"
        self._client = SecretClient(vault_url=vault_url, credential=DefaultAzureCredential())

    async def store_token(self, path: str, token_data: TokenData) -> None:
        """Encrypt and store token in AKV. Token value never written to any log."""
        payload = json.dumps({
            "access_token": token_data.access_token,
            "refresh_token": token_data.refresh_token,
            "expires_at": token_data.expires_at.isoformat() if token_data.expires_at else None,
            "provider_name": token_data.provider_name,
            "contract_id": token_data.contract_id,
            "extra_data": token_data.extra_data,
        })
        secret_name = _make_secret_name(path)
        # ADR-014: log vault_alias and secret_name only — no token value.
        logger.info(
            "store_token vault_alias=%s secret_name=%s",
            self._vault_alias, secret_name,
        )
        await asyncio.to_thread(self._client.set_secret, secret_name, payload)

    async def retrieve_token(self, path: str) -> TokenData | None:
        """Retrieve token from AKV. Returns None if not found."""
        secret_name = _make_secret_name(path)
        try:
            secret = await asyncio.to_thread(self._client.get_secret, secret_name)
        except Exception as exc:
            # Log exception type only — no vault path, no token fragment.
            logger.warning("retrieve_token: not found vault_alias=%s err=%s", self._vault_alias, type(exc).__name__)
            return None

        if not secret.value:
            return None

        try:
            data = json.loads(secret.value)
            expires_at = datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None
            return TokenData(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_at=expires_at,
                provider_name=data["provider_name"],
                contract_id=data["contract_id"],
                extra_data=data.get("extra_data", {}),
            )
        except (KeyError, ValueError) as exc:
            logger.warning("retrieve_token: corrupt payload vault_alias=%s err=%s", self._vault_alias, type(exc).__name__)
            return None

    async def delete_token(self, path: str) -> None:
        """Begin AKV soft-delete. Caller MUST have called CE first (ADR-021 revoke requirement)."""
        secret_name = _make_secret_name(path)
        logger.info("delete_token vault_alias=%s secret_name=%s", self._vault_alias, secret_name)
        await asyncio.to_thread(self._client.begin_delete_secret, secret_name)

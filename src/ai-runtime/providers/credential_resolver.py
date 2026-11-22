# Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R005
# Implements: adr/ADR-042-provider-registry-constitutional-tool-gateway.md §1 (provider registry), ADR-014 (Key Vault)
# constitutional_basis: C-059, C-063, ADR-014 (no credential in logs or errors)
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

REGISTRY_CACHE_TTL_SECONDS = 30.0
_HTTP_TIMEOUT_SECONDS = 10.0
_VAULT_RESOURCE = "https://vault.azure.net"
_VAULT_API_VERSION = "7.4"
_IDENTITY_API_VERSION = "2019-08-01"
_TOKEN_EXPIRY_MARGIN_SECONDS = 120.0
_VAULT_NAME_PREFIX = "provider-"
_PROVIDER_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")
_SECRET_NAME = re.compile(r"^[A-Za-z0-9-]{1,127}$")
_SECRET_VERSION = re.compile(r"^[A-Za-z0-9]{1,64}$")


class ProviderCredentialUnavailable(Exception):  # noqa: N818 - contract name
    """No usable credential for a provider. The message carries a reason code only, never a value, URL or token."""

    def __init__(self, provider_name: str, reason: str) -> None:
        self.provider_name = provider_name
        self.reason = reason
        super().__init__(f"provider credential unavailable: provider={provider_name} reason={reason}")


@dataclass(frozen=True)
class _CredentialRef:
    secret_name: str
    secret_version: str


class ProviderCredentialResolver:
    """
    Resolves a provider API key from the BP provider registry and Key Vault.

    The registry names the active secret version (short TTL cache); that exact version is read from Key Vault with the
    container's managed identity. A new or rolled-back version is picked up on the next registry refresh, and values of
    superseded versions are dropped. Registry authentication mirrors ctg.registry_client.ProviderRegistryClient.
    """

    def __init__(
        self,
        bp_base_url: str | None = None,
        vault_url: str | None = None,
        internal_jwt: str = "",
        *,
        ttl_seconds: float = REGISTRY_CACHE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        base_url = bp_base_url if bp_base_url else os.getenv("BP_BASE_URL", "http://business-platform:5003")
        self._bp_base_url = base_url.rstrip("/")
        self._vault_url = vault_url if vault_url is not None else os.getenv("PROVIDER_CREDENTIALS_VAULT_URL", "")
        self._internal_jwt = internal_jwt
        self._ttl = ttl_seconds
        self._clock = clock
        self._wall_clock = wall_clock
        self._registry: dict[str, tuple[_CredentialRef | None, float]] = {}
        self._secrets: dict[tuple[str, str], str] = {}
        self._token: tuple[str, float] | None = None
        self._lock = asyncio.Lock()

    async def get_api_key(self, provider_name: str) -> str:
        if not _PROVIDER_NAME.fullmatch(provider_name or ""):
            raise ProviderCredentialUnavailable("invalid", "invalid_provider_name")
        async with self._lock:
            ref = await self._resolve_ref(provider_name)
            cached = self._secrets.get((ref.secret_name, ref.secret_version))
            if cached is not None:
                return cached
            value = await self._read_secret(provider_name, ref)
            self._secrets[(ref.secret_name, ref.secret_version)] = value
            return value

    async def _resolve_ref(self, provider_name: str) -> _CredentialRef:
        now = self._clock()
        entry = self._registry.get(provider_name)
        if entry is None or now - entry[1] >= self._ttl:
            ref = await self._fetch_ref(provider_name)
            self._registry[provider_name] = (ref, now)
        else:
            ref = entry[0]
        if ref is None:
            self._drop_superseded(f"{_VAULT_NAME_PREFIX}{provider_name}", None)
            raise ProviderCredentialUnavailable(provider_name, "no_active_credential")
        self._drop_superseded(ref.secret_name, ref.secret_version)
        return ref

    def _drop_superseded(self, secret_name: str, keep_version: str | None) -> None:
        self._secrets = {key: val for key, val in self._secrets.items() if key[0] != secret_name or key[1] == keep_version}

    async def _fetch_ref(self, provider_name: str) -> _CredentialRef | None:
        url = f"{self._bp_base_url}/api/v1/providers/{provider_name}"
        headers = {"Authorization": f"Bearer {self._internal_jwt}"}
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            self._warn(provider_name, "registry_unreachable", type(exc).__name__)
            raise ProviderCredentialUnavailable(provider_name, "registry_unreachable") from None
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            self._warn(provider_name, "registry_error", f"http_{response.status_code}")
            raise ProviderCredentialUnavailable(provider_name, "registry_error")
        try:
            data = response.json()
        except ValueError:
            raise ProviderCredentialUnavailable(provider_name, "registry_error") from None
        credential = data.get("credential") if isinstance(data, dict) else None
        if credential is None:
            return None
        if not isinstance(credential, dict):
            raise ProviderCredentialUnavailable(provider_name, "registry_error")
        name = credential.get("secretName", credential.get("secret_name"))
        version = credential.get("secretVersion", credential.get("secret_version"))
        if (
            not isinstance(name, str)
            or not isinstance(version, str)
            or not _SECRET_NAME.fullmatch(name)
            or not name.startswith(_VAULT_NAME_PREFIX)
            or not _SECRET_VERSION.fullmatch(version)
        ):
            raise ProviderCredentialUnavailable(provider_name, "registry_error")
        return _CredentialRef(name, version)

    async def _read_secret(self, provider_name: str, ref: _CredentialRef) -> str:
        vault_origin = self._vault_origin(provider_name)
        token = await self._managed_identity_token(provider_name)
        url = f"{vault_origin}/secrets/{ref.secret_name}/{ref.secret_version}"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    url,
                    params={"api-version": _VAULT_API_VERSION},
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            self._warn(provider_name, "vault_unreachable", type(exc).__name__)
            raise ProviderCredentialUnavailable(provider_name, "vault_unreachable") from None
        if response.status_code in (401, 403):
            self._token = None
        if response.status_code != 200:
            self._warn(provider_name, "vault_error", f"http_{response.status_code}")
            raise ProviderCredentialUnavailable(provider_name, "vault_error")
        try:
            value = response.json().get("value")
        except (ValueError, AttributeError):
            value = None
        if not isinstance(value, str) or not value:
            raise ProviderCredentialUnavailable(provider_name, "vault_error")
        return value

    def _vault_origin(self, provider_name: str) -> str:
        parts = urlsplit(self._vault_url or "")
        host = parts.hostname or ""
        if parts.scheme != "https" or not host.endswith(".vault.azure.net") or parts.port not in (None, 443):
            raise ProviderCredentialUnavailable(provider_name, "vault_not_configured")
        return f"https://{host}"

    async def _managed_identity_token(self, provider_name: str) -> str:
        if self._token is not None and self._wall_clock() < self._token[1] - _TOKEN_EXPIRY_MARGIN_SECONDS:
            return self._token[0]
        endpoint = os.getenv("IDENTITY_ENDPOINT", "")
        header = os.getenv("IDENTITY_HEADER", "")
        if not endpoint or not header:
            raise ProviderCredentialUnavailable(provider_name, "managed_identity_unconfigured")
        params = {"resource": _VAULT_RESOURCE, "api-version": _IDENTITY_API_VERSION}
        client_id = os.getenv("PROVIDER_CREDENTIALS_MANAGED_IDENTITY_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
        if client_id:
            params["client_id"] = client_id
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(endpoint, params=params, headers={"X-IDENTITY-HEADER": header})
            if response.status_code != 200:
                self._warn(provider_name, "token_error", f"http_{response.status_code}")
                raise ProviderCredentialUnavailable(provider_name, "token_unavailable")
            body = response.json()
            token = body["access_token"]
            expires_on = float(body["expires_on"])
        except ProviderCredentialUnavailable:
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            self._warn(provider_name, "token_error", type(exc).__name__)
            raise ProviderCredentialUnavailable(provider_name, "token_unavailable") from None
        if not isinstance(token, str) or not token:
            raise ProviderCredentialUnavailable(provider_name, "token_unavailable")
        self._token = (token, expires_on)
        return token

    @staticmethod
    def _warn(provider_name: str, reason: str, detail: str) -> None:
        logger.warning("provider credential lookup failed provider=%s reason=%s detail=%s", provider_name, reason, detail)

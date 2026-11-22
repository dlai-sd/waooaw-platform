# Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R005
# constitutional_basis: C-059, C-063, ADR-014 (no credential in logs or errors), C-076
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
import pytest
import respx

from pse import router
from pse.tiers import LlmTier
from providers.credential_resolver import ProviderCredentialResolver, ProviderCredentialUnavailable
from providers.sarvam_provider import SARVAM_API_ENDPOINT

BP = "http://bp.test"
VAULT = "https://kv-test.vault.azure.net"
IDENTITY = "http://identity.local/msi/token"
REGISTRY_URL = f"{BP}/api/v1/providers/sarvam"
TOKEN = "managed-identity-token-ZZZ"
JWT = "internal-jwt-QQQ"
V1 = "a" * 32
V2 = "b" * 32
SECRETS = {V1: "sk-sarvam-ONE", V2: "sk-sarvam-TWO"}


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class Registry:
    """Mutable BP registry entry; the active version changes the way a Founder save or rollback would."""

    def __init__(self) -> None:
        self.version: str | None = V1
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        credential = (
            None if self.version is None else {"secretName": "provider-sarvam", "secretVersion": self.version, "versionNo": 1}
        )
        return httpx.Response(200, json={"providerName": "sarvam", "credential": credential})


@pytest.fixture(autouse=True)
def managed_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IDENTITY_ENDPOINT", IDENTITY)
    monkeypatch.setenv("IDENTITY_HEADER", "identity-header-value")
    monkeypatch.setenv("PROVIDER_CREDENTIALS_MANAGED_IDENTITY_CLIENT_ID", "client-1")


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def registry() -> Registry:
    return Registry()


@pytest.fixture
def mocked(registry: Registry, clock: Clock):
    with respx.mock(assert_all_called=False) as mock:
        mock.get(REGISTRY_URL).mock(side_effect=registry)
        mock.get(IDENTITY).mock(
            return_value=httpx.Response(200, json={"access_token": TOKEN, "expires_on": str(int(clock.now) + 3600)})
        )
        for version, value in SECRETS.items():
            mock.get(f"{VAULT}/secrets/provider-sarvam/{version}", params={"api-version": "7.4"}).mock(
                return_value=httpx.Response(200, json={"value": value})
            )
        yield mock


def make_resolver(clock: Clock, **overrides: object) -> ProviderCredentialResolver:
    options: dict[str, object] = {
        "bp_base_url": BP,
        "vault_url": VAULT,
        "internal_jwt": JWT,
        "clock": clock,
        "wall_clock": clock,
    }
    options.update(overrides)
    return ProviderCredentialResolver(**options)  # type: ignore[arg-type]


async def test_save_then_rollback_is_used_on_registry_refresh_without_restart(
    mocked: respx.MockRouter, registry: Registry, clock: Clock
) -> None:
    resolver = make_resolver(clock)

    assert await resolver.get_api_key("sarvam") == SECRETS[V1]
    registry.version = V2
    assert await resolver.get_api_key("sarvam") == SECRETS[V1]
    clock.now += 31
    assert await resolver.get_api_key("sarvam") == SECRETS[V2]
    registry.version = V1
    clock.now += 31
    assert await resolver.get_api_key("sarvam") == SECRETS[V1]


async def test_registry_is_cached_for_the_ttl_and_the_pinned_secret_is_read_once(
    mocked: respx.MockRouter, registry: Registry, clock: Clock
) -> None:
    resolver = make_resolver(clock, ttl_seconds=30.0)
    vault_route = mocked.routes[2]

    for _ in range(3):
        assert await resolver.get_api_key("sarvam") == SECRETS[V1]
    assert registry.calls == 1
    clock.now += 29.9
    await resolver.get_api_key("sarvam")
    assert registry.calls == 1
    clock.now += 0.2
    await resolver.get_api_key("sarvam")
    assert registry.calls == 2
    assert vault_route.call_count == 1


async def test_registry_and_vault_requests_use_pinned_version_and_credentials(mocked: respx.MockRouter, clock: Clock) -> None:
    await make_resolver(clock).get_api_key("sarvam")

    registry_request = mocked.calls[0].request
    assert registry_request.headers["Authorization"] == f"Bearer {JWT}"
    identity_request = mocked.calls[1].request
    assert identity_request.headers["X-IDENTITY-HEADER"] == "identity-header-value"
    assert dict(identity_request.url.params) == {
        "resource": "https://vault.azure.net",
        "api-version": "2019-08-01",
        "client_id": "client-1",
    }
    vault_request = mocked.calls[2].request
    assert vault_request.url.path == f"/secrets/provider-sarvam/{V1}"
    assert dict(vault_request.url.params) == {"api-version": "7.4"}
    assert vault_request.headers["Authorization"] == f"Bearer {TOKEN}"


async def test_managed_identity_token_is_reused_until_near_expiry(mocked: respx.MockRouter, clock: Clock) -> None:
    resolver = make_resolver(clock, ttl_seconds=0.0)
    registry_route = mocked.routes[0]
    identity_route = mocked.routes[1]

    await resolver.get_api_key("sarvam")
    clock.now += 3000
    await resolver.get_api_key("sarvam")
    assert identity_route.call_count == 1
    assert registry_route.call_count == 2
    clock.now += 600
    resolver._secrets.clear()
    await resolver.get_api_key("sarvam")
    assert identity_route.call_count == 2


async def test_superseded_and_withdrawn_values_are_dropped(mocked: respx.MockRouter, registry: Registry, clock: Clock) -> None:
    resolver = make_resolver(clock)
    await resolver.get_api_key("sarvam")
    registry.version = V2
    clock.now += 31
    await resolver.get_api_key("sarvam")
    assert set(resolver._secrets) == {("provider-sarvam", V2)}

    registry.version = None
    clock.now += 31
    with pytest.raises(ProviderCredentialUnavailable) as raised:
        await resolver.get_api_key("sarvam")
    assert raised.value.reason == "no_active_credential"
    assert resolver._secrets == {}


@pytest.mark.parametrize(
    ("scenario", "reason"),
    [
        ("no_credential", "no_active_credential"),
        ("unknown_provider", "no_active_credential"),
        ("registry_500", "registry_error"),
        ("registry_unreachable", "registry_unreachable"),
        ("registry_not_json", "registry_error"),
        ("foreign_secret_name", "registry_error"),
        ("bad_version", "registry_error"),
        ("vault_not_configured", "vault_not_configured"),
        ("vault_http", "vault_not_configured"),
        ("identity_unconfigured", "managed_identity_unconfigured"),
        ("identity_error", "token_unavailable"),
        ("vault_forbidden", "vault_error"),
        ("vault_missing", "vault_error"),
        ("vault_unreachable", "vault_unreachable"),
        ("vault_empty_value", "vault_error"),
    ],
)
async def test_unavailable_cases_raise_typed_error_without_leaking(
    scenario: str,
    reason: str,
    mocked: respx.MockRouter,
    registry: Registry,
    clock: Clock,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    vault_route = mocked.routes[2]
    vault_url = VAULT
    if scenario == "no_credential":
        registry.version = None
    elif scenario == "unknown_provider":
        mocked.routes[0].mock(return_value=httpx.Response(404, json={"error": "PROVIDER_NOT_FOUND"}))
    elif scenario == "registry_500":
        mocked.routes[0].mock(return_value=httpx.Response(500, text=SECRETS[V1]))
    elif scenario == "registry_unreachable":
        mocked.routes[0].mock(side_effect=httpx.ConnectError(f"refused {BP}?token={SECRETS[V1]}"))
    elif scenario == "registry_not_json":
        mocked.routes[0].mock(return_value=httpx.Response(200, text="<html>"))
    elif scenario == "foreign_secret_name":
        mocked.routes[0].mock(
            return_value=httpx.Response(200, json={"credential": {"secretName": "web", "secretVersion": V1, "versionNo": 1}})
        )
    elif scenario == "bad_version":
        mocked.routes[0].mock(
            return_value=httpx.Response(
                200, json={"credential": {"secretName": "provider-sarvam", "secretVersion": "../x", "versionNo": 1}}
            )
        )
    elif scenario == "vault_not_configured":
        vault_url = ""
    elif scenario == "vault_http":
        vault_url = "http://kv-test.vault.azure.net"
    elif scenario == "identity_unconfigured":
        monkeypatch.delenv("IDENTITY_ENDPOINT")
    elif scenario == "identity_error":
        mocked.routes[1].mock(return_value=httpx.Response(400, text=TOKEN))
    elif scenario == "vault_forbidden":
        vault_route.mock(return_value=httpx.Response(403, text=SECRETS[V1]))
    elif scenario == "vault_missing":
        vault_route.mock(return_value=httpx.Response(404, json={"error": {"code": "SecretNotFound"}}))
    elif scenario == "vault_unreachable":
        vault_route.mock(side_effect=httpx.ConnectError(f"refused {VAULT}/secrets/provider-sarvam/{V1}?api-version=7.4"))
    elif scenario == "vault_empty_value":
        vault_route.mock(return_value=httpx.Response(200, json={"value": ""}))

    resolver = make_resolver(clock, vault_url=vault_url)
    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderCredentialUnavailable) as raised:
        await resolver.get_api_key("sarvam")

    assert raised.value.reason == reason
    assert raised.value.provider_name == "sarvam"
    resolver_logs = " ".join(r.getMessage() for r in caplog.records if r.name == "providers.credential_resolver")
    surfaced = f"{raised.value!s} {raised.value!r} {resolver_logs}"
    for sensitive in (*SECRETS.values(), TOKEN, JWT, "api-version", "vault.azure.net", "identity-header-value"):
        assert sensitive not in surfaced
    for sensitive in (*SECRETS.values(), TOKEN, JWT, "identity-header-value"):
        assert sensitive not in caplog.text
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ or raised.value.__context__ is None


@pytest.mark.parametrize("name", ["", "Sarvam", "../x", "a b", "x" * 80])
async def test_invalid_provider_names_never_reach_the_network(name: str, mocked: respx.MockRouter, clock: Clock) -> None:
    with pytest.raises(ProviderCredentialUnavailable) as raised:
        await make_resolver(clock).get_api_key(name)

    assert raised.value.reason == "invalid_provider_name"
    assert mocked.calls.call_count == 0


async def test_successful_lookup_logs_nothing_sensitive(
    mocked: respx.MockRouter, clock: Clock, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        await make_resolver(clock).get_api_key("sarvam")

    for sensitive in (*SECRETS.values(), TOKEN, JWT):
        assert sensitive not in caplog.text


async def test_forbidden_vault_response_forces_a_fresh_token_next_time(mocked: respx.MockRouter, clock: Clock) -> None:
    resolver = make_resolver(clock, ttl_seconds=0.0)
    vault_route = mocked.routes[2]
    vault_route.mock(return_value=httpx.Response(403))
    with pytest.raises(ProviderCredentialUnavailable):
        await resolver.get_api_key("sarvam")
    vault_route.mock(return_value=httpx.Response(200, json={"value": SECRETS[V1]}))

    assert await resolver.get_api_key("sarvam") == SECRETS[V1]
    assert mocked.routes[1].call_count == 2


# --- Sarvam dispatch through the PSE router --------------------------------------------------


@pytest.fixture
def router_resolver(mocked: respx.MockRouter, clock: Clock):
    resolver = make_resolver(clock)
    with patch.object(router, "_credential_resolver", resolver):
        yield resolver


async def test_sarvam_dispatch_uses_the_resolved_key_and_follows_a_new_version(
    mocked: respx.MockRouter, registry: Registry, clock: Clock, router_resolver: ProviderCredentialResolver
) -> None:
    sarvam = mocked.post(SARVAM_API_ENDPOINT).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "namaste"}}],
                "model": "saaras",
                "usage": {"total_tokens": 3},
            },
        )
    )

    result = await router._dispatch_mid("hello", "hi")

    assert sarvam.calls.last.request.headers["Authorization"] == f"Bearer {SECRETS[V1]}"
    assert result == {
        "tier": LlmTier.MID.value,
        "provider_id": "sarvam",
        "model_id": "saaras",
        "response": "namaste",
        "done": True,
        "usage": {"total_tokens": 3},
    }
    registry.version = V2
    clock.now += 31
    await router._dispatch_mid("hello", "hi")
    assert sarvam.calls.last.request.headers["Authorization"] == f"Bearer {SECRETS[V2]}"


async def test_sarvam_dispatch_without_credential_keeps_the_not_implemented_failure_path(
    mocked: respx.MockRouter, registry: Registry, router_resolver: ProviderCredentialResolver
) -> None:
    registry.version = None
    sarvam = mocked.post(SARVAM_API_ENDPOINT)

    with pytest.raises(NotImplementedError, match="MID_TIER provider dispatch unavailable") as raised:
        await router._dispatch_mid("hello", "hi")

    assert "no_active_credential" in str(raised.value)
    assert sarvam.call_count == 0


async def test_missing_credential_still_records_not_implemented_evidence(
    mocked: respx.MockRouter, registry: Registry, router_resolver: ProviderCredentialResolver
) -> None:
    registry.version = None
    session_factory = MagicMock()
    event_id = UUID("80000000-0000-0000-0000-000000000008")

    with (
        patch("pse.router._CTG_AVAILABLE", False),
        patch("pse.router.uuid.uuid4", return_value=event_id),
        patch("pse.router._record_dispatch_event", new_callable=AsyncMock) as record,
        pytest.raises(NotImplementedError),
    ):
        await router.route_and_dispatch("p", "medium", "hi", session_factory)

    record.assert_awaited_once_with(
        session_factory, str(event_id), LlmTier.MID, "sarvam", "saaras", "medium", "hi", "not_implemented", "NotImplementedError"
    )


async def test_non_indic_mid_dispatch_is_unchanged_and_does_not_consult_the_registry(
    mocked: respx.MockRouter, registry: Registry, router_resolver: ProviderCredentialResolver
) -> None:
    with pytest.raises(NotImplementedError, match="MID_TIER"):
        await router._dispatch_mid("hello", "en")

    assert registry.calls == 0

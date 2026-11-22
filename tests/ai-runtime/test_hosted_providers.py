# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R002..R005
# constitutional_basis: C-059, C-062, C-063, ADR-014 (no credential in URL, log or error)
"""Hosted adapters, ordered fallback, versioned credential resolution and the Business Platform probe route."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import respx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from fastapi import FastAPI
from starlette.requests import Request

from conversation_generation_owner import BusinessPlatformGenerationOwner
from employment_auth import PEER_CERTIFICATE_STATE_KEY, DelegatedContext, EmploymentAuthError, EmploymentWorkloadAuth, RouteGrant
from provider_generation_probe import (
    NIL_ID,
    PROBE_MAX_OUTPUT_TOKENS,
    PROBE_OPERATION,
    PROBE_PROMPT,
    PROBE_PURPOSE,
    PROBE_ROUTE,
    ProviderGenerationProbeService,
    _authorize,
)
from provider_generation_probe import router as probe_router
from providers.credential_resolver import ProviderCredentialResolver, ProviderCredentialUnavailable
from providers.hosted import HOSTED_ADAPTERS
from providers.hosted.base import HostedProviderError
from providers.hosted.fallback import ChainEntry, run_fallback_chain

KEY = "fake-provider-key-for-tests"
PROMPT = "Reply with one short sentence confirming you are working."

SUCCESS: dict[str, dict[str, Any]] = {
    "sarvam": {
        "model": "sarvam-105b-2025",
        "choices": [{"message": {"content": "Working."}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3},
    },
    "openai": {
        "model": "gpt-4o-mini-2024-07-18",
        "choices": [{"message": {"content": "Working."}}],
        "usage": {"prompt_tokens": 11, "completion_tokens": 3},
    },
    "anthropic": {
        "model": "claude-haiku-4-5-20251001",
        "content": [{"type": "text", "text": "Working."}],
        "usage": {"input_tokens": 11, "output_tokens": 3},
    },
    "google": {
        "modelVersion": "gemini-2.0-flash-001",
        "candidates": [{"content": {"parts": [{"text": "Working."}]}}],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 3},
    },
}
EXPECTED = {
    "sarvam": ("api.sarvam.ai", "/v1/chat/completions", "api-subscription-key", "sarvam-105b", "max_tokens"),
    "openai": ("api.openai.com", "/v1/chat/completions", "authorization", "gpt-4o-mini", "max_completion_tokens"),
    "anthropic": ("api.anthropic.com", "/v1/messages", "x-api-key", "claude-haiku-4-5", "max_tokens"),
    "google": (
        "generativelanguage.googleapis.com",
        "/v1beta/models/gemini-2.0-flash:generateContent",
        "x-goog-api-key",
        "gemini-2.0-flash",
        "generationConfig",
    ),
}


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False)


class Keys:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = values if values is not None else {name: KEY for name in SUCCESS}
        self.calls: list[str] = []

    async def get_api_key(self, provider_name: str) -> str:
        self.calls.append(provider_name)
        if provider_name not in self.values:
            raise ProviderCredentialUnavailable(provider_name, "no_active_credential")
        return self.values[provider_name]


@pytest.mark.parametrize("name", list(SUCCESS))
async def test_adapter_request_shape_key_placement_and_response_mapping(name: str, caplog: pytest.LogCaptureFixture) -> None:
    host, path, key_header, model, limit_field = EXPECTED[name]
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=SUCCESS[name])

    caplog.set_level(logging.DEBUG)
    adapter = HOSTED_ADAPTERS[name]
    result = await adapter.complete(client_for(handler), KEY, PROMPT, adapter.model_for(), 64)
    (request,) = seen
    assert request.url.scheme == "https" and request.url.host == host and request.url.path == path
    assert request.url.query == b"" and KEY not in str(request.url)
    carriers = [header for header, value in request.headers.items() if KEY in value]
    assert carriers == [key_header]
    body = json.loads(request.content)
    assert KEY not in request.content.decode() and PROMPT in request.content.decode()
    assert (body.get("model") == model) or name == "google"
    assert body[limit_field] == 64 or body[limit_field] == {"maxOutputTokens": 64}
    if name == "anthropic":
        assert request.headers["anthropic-version"] == "2023-06-01"
    if name == "openai":
        assert request.headers["authorization"] == f"Bearer {KEY}"
    assert (result.text, result.input_tokens, result.output_tokens) == ("Working.", 11, 3)
    assert result.reported_model == (SUCCESS[name].get("model") or SUCCESS[name].get("modelVersion"))
    assert KEY not in caplog.text


@pytest.mark.parametrize(
    ("name", "status", "reason"),
    [
        (name, status, reason)
        for name in SUCCESS
        for status, reason in (
            (401, "KEY_REJECTED"),
            (403, "KEY_REJECTED"),
            (429, "PROVIDER_ERROR"),
            (500, "PROVIDER_ERROR"),
            (400, "PROVIDER_ERROR"),
            (302, "PROVIDER_ERROR"),
        )
    ],
)
async def test_http_failures_map_to_reason_codes_without_echoing_bodies(name: str, status: int, reason: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=f"upstream body echoing {KEY}", headers={"location": "https://evil.example/"})

    with pytest.raises(HostedProviderError) as failure:
        await HOSTED_ADAPTERS[name].complete(client_for(handler), KEY, PROMPT, HOSTED_ADAPTERS[name].model_for(), 64)
    assert failure.value.reason == reason and KEY not in str(failure.value) and "upstream" not in str(failure.value)


async def test_gemini_invalid_key_is_a_400_with_an_api_key_reason() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"details": [{"reason": "API_KEY_INVALID"}]}})

    with pytest.raises(HostedProviderError) as failure:
        await HOSTED_ADAPTERS["google"].complete(client_for(handler), KEY, PROMPT, "gemini-2.0-flash", 64)
    assert failure.value.reason == "KEY_REJECTED"


@pytest.mark.parametrize(
    ("raised", "reason"),
    [(httpx.ReadTimeout("t"), "TIMEOUT"), (httpx.ConnectTimeout("t"), "TIMEOUT"), (httpx.ConnectError("c"), "PROVIDER_ERROR")],
)
async def test_transport_failures_map_to_timeout_or_provider_error(raised: Exception, reason: str) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        raise raised

    with pytest.raises(HostedProviderError) as failure:
        await HOSTED_ADAPTERS["openai"].complete(client_for(handler), KEY, PROMPT, "gpt-4o-mini", 64)
    assert failure.value.reason == reason


@pytest.mark.parametrize(
    "payload", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]}, {"choices": [{"message": {"content": "  "}}]}]
)
async def test_malformed_or_empty_completions_are_provider_errors(payload: dict[str, Any]) -> None:
    with pytest.raises(HostedProviderError) as failure:
        await HOSTED_ADAPTERS["openai"].complete(
            client_for(lambda _: httpx.Response(200, json=payload)), KEY, PROMPT, "gpt-4o-mini", 64
        )
    assert failure.value.reason == "PROVIDER_ERROR"


async def test_missing_usage_is_unknown_and_unsafe_models_or_keys_never_leave_the_process() -> None:
    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "model": "../evil"})

    result = await HOSTED_ADAPTERS["openai"].complete(client_for(handler), KEY, PROMPT, "gpt-4o-mini", 64)
    assert result.input_tokens is None and result.output_tokens is None and result.reported_model == "gpt-4o-mini"
    for model in ("a/b", "gpt 4", "x" * 65, "../x", "m:generateContent?key=1"):
        with pytest.raises(HostedProviderError) as unsupported:
            await HOSTED_ADAPTERS["google"].complete(client_for(handler), KEY, PROMPT, model, 64)
        assert unsupported.value.reason == "UNSUPPORTED"
    with pytest.raises(HostedProviderError) as rejected:
        await HOSTED_ADAPTERS["openai"].complete(client_for(handler), "bad key\nX-Injected: 1", PROMPT, "gpt-4o-mini", 64)
    assert rejected.value.reason == "KEY_REJECTED" and len(sent) == 1


async def test_model_is_overridable_by_environment_and_rejected_when_unsafe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIR_HOSTED_MODEL_ANTHROPIC", "claude-sonnet-4-5")
    assert HOSTED_ADAPTERS["anthropic"].model_for() == "claude-sonnet-4-5"
    assert HOSTED_ADAPTERS["anthropic"].model_for("claude-opus-4-1") == "claude-opus-4-1"
    monkeypatch.setenv("AIR_HOSTED_MODEL_ANTHROPIC", "bad/model")
    with pytest.raises(HostedProviderError):
        HOSTED_ADAPTERS["anthropic"].model_for()


async def test_fallback_chain_is_ordered_bounded_and_reports_sanitized_skips() -> None:
    order: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        order.append(request.url.host)
        if request.url.host == "api.sarvam.ai":
            return httpx.Response(401)
        if request.url.host == "api.openai.com":
            raise httpx.ReadTimeout("slow")
        return httpx.Response(200, json=SUCCESS["anthropic"])

    keys = Keys({"sarvam": KEY, "openai": KEY, "anthropic": KEY})
    entries = [ChainEntry("sarvam"), ChainEntry("openai"), ChainEntry("google"), ChainEntry("anthropic"), ChainEntry("nonesuch")]
    with pytest.raises(ValueError, match="between one and four"):
        await run_fallback_chain(entries, keys, client_for(handler), PROMPT, 64)
    answer, attempts = await run_fallback_chain(
        [ChainEntry("sarvam"), ChainEntry("openai"), ChainEntry("google"), ChainEntry("anthropic")],
        keys,
        client_for(handler),
        PROMPT,
        64,
    )
    assert answer is not None and answer.provider == "anthropic" and answer.reported_model == "claude-haiku-4-5-20251001"
    assert [(item.provider, item.outcome, item.reason) for item in attempts] == [
        ("sarvam", "SKIPPED", "KEY_REJECTED"),
        ("openai", "SKIPPED", "TIMEOUT"),
        ("google", "SKIPPED", "KEY_MISSING"),
        ("anthropic", "ANSWERED", None),
    ]
    assert order == ["api.sarvam.ai", "api.openai.com", "api.anthropic.com"]


async def test_fallback_stops_at_first_answer_and_reports_exhaustion_and_unsupported() -> None:
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hits.append(request.url.host)
        return httpx.Response(200, json=SUCCESS["openai"])

    answer, attempts = await run_fallback_chain(
        [ChainEntry("openai"), ChainEntry("sarvam")], Keys(), client_for(handler), PROMPT, 64
    )
    assert answer is not None and answer.provider == "openai" and len(attempts) == 1 and hits == ["api.openai.com"]
    none, skipped = await run_fallback_chain(
        [ChainEntry("nonesuch"), ChainEntry("openai", "bad/model")], Keys(), client_for(handler), PROMPT, 64
    )
    assert none is None and [item.reason for item in skipped] == ["UNSUPPORTED", "UNSUPPORTED"]


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


VAULT = "https://kv-test.vault.azure.net"
IDENTITY = "http://identity.local/msi/token"
V1, V2 = "a" * 32, "b" * 32


async def test_resolver_follows_owner_reference_versions_without_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IDENTITY_ENDPOINT", IDENTITY)
    monkeypatch.setenv("IDENTITY_HEADER", "identity-header-value")
    clock = Clock()
    state: dict[str, Any] = {"version": V1, "calls": 0, "fail": None}

    async def fetcher(provider: str) -> dict[str, object] | None:
        state["calls"] += 1
        if state["fail"] is not None:
            raise state["fail"]
        if state["version"] is None:
            return None
        return {"secretName": f"provider-{provider}", "secretVersion": state["version"], "authStyle": "BEARER"}

    resolver = ProviderCredentialResolver(vault_url=VAULT, clock=clock, wall_clock=clock, ref_fetcher=fetcher)
    assert resolver.vault_configured() and not ProviderCredentialResolver(vault_url="http://insecure").vault_configured()
    with respx.mock(assert_all_called=False) as mock:
        mock.get(IDENTITY).mock(
            return_value=httpx.Response(200, json={"access_token": "t", "expires_on": str(int(clock.now) + 3600)})
        )
        mock.get(f"{VAULT}/secrets/provider-openai/{V1}").mock(return_value=httpx.Response(200, json={"value": "key-ONE-0000"}))
        second = mock.get(f"{VAULT}/secrets/provider-openai/{V2}").mock(
            return_value=httpx.Response(200, json={"value": "key-TWO-0000"})
        )
        assert await resolver.get_api_key("openai") == "key-ONE-0000"
        state["version"] = V2
        assert await resolver.get_api_key("openai") == "key-ONE-0000" and state["calls"] == 1 and not second.called
        clock.now += 31
        assert await resolver.get_api_key("openai") == "key-TWO-0000"
        state["version"] = V1
        clock.now += 31
        assert await resolver.get_api_key("openai") == "key-ONE-0000"
        state["version"] = None
        clock.now += 31
        with pytest.raises(ProviderCredentialUnavailable) as missing:
            await resolver.get_api_key("openai")
        assert missing.value.reason == "no_active_credential"
        state["fail"] = httpx.ConnectError("down")
        clock.now += 31
        with pytest.raises(ProviderCredentialUnavailable) as down:
            await resolver.get_api_key("openai")
        assert down.value.reason == "registry_unreachable"
        state["fail"], state["version"] = ValueError("bad"), V1
        clock.now += 31
        with pytest.raises(ProviderCredentialUnavailable) as invalid:
            await resolver.get_api_key("openai")
        assert invalid.value.reason == "registry_error"
        state["fail"] = None
        state["version"] = "not a version!"
        clock.now += 31
        with pytest.raises(ProviderCredentialUnavailable):
            await resolver.get_api_key("openai")


async def test_owner_resolves_a_credential_reference_with_a_signed_workload_envelope() -> None:
    owner = BusinessPlatformGenerationOwner.__new__(BusinessPlatformGenerationOwner)
    owner.endpoint, owner.key = "https://business.test", ec.generate_private_key(ec.SECP256R1())
    owner.issuer, owner.key_id, owner.audience = "spiffe://waooaw.test/workload/ai-runtime", "air-key", "urn:business"
    seen: list[httpx.Request] = []
    reply: dict[str, Any] = {
        "status": 200,
        "json": {"providerName": "openai", "secretName": "provider-openai", "secretVersion": V1, "authStyle": "BEARER"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(reply["status"], json=reply["json"])

    owner.client = client_for(handler)
    assert await owner.resolve_provider_credential("openai") == {
        "secretName": "provider-openai",
        "secretVersion": V1,
        "authStyle": "BEARER",
    }
    request = seen[0]
    assert request.url.path == "/internal/v1/provider-credentials/resolve" and json.loads(request.content) == {
        "providerName": "openai"
    }
    payload = base64.urlsafe_b64decode(request.headers["authorization"].removeprefix("Bearer ").split(".")[0] + "==")
    envelope = json.loads(payload)
    assert (
        envelope["operation"] == "resolveProviderCredential" and envelope["route"] == "/internal/v1/provider-credentials/resolve"
    )
    assert envelope["issuer_uri"] == owner.issuer and envelope["subject_reference"] == "openai"
    assert envelope["correlation_id"] == request.headers["x-correlation-id"]
    reply.update(status=404, json={})
    assert await owner.resolve_provider_credential("openai") is None
    reply.update(status=500)
    with pytest.raises(httpx.HTTPStatusError):
        await owner.resolve_provider_credential("openai")
    reply.update(status=200, json={"providerName": "anthropic", "secretName": "provider-anthropic", "secretVersion": V1})
    with pytest.raises(ValueError, match="does not match"):
        await owner.resolve_provider_credential("openai")


BP_IDENTITY = "spiffe://waooaw.test/workload/business-platform"
PR_IDENTITY = "spiffe://waooaw.test/workload/professional-runtime"
AUDIENCE = "urn:waooaw:service:ai-runtime"


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _certificate(identity: str) -> x509.Certificate:
    key, now = ec.generate_private_key(ec.SECP256R1()), datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "caller")])
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(minutes=5))
        .add_extension(x509.SubjectAlternativeName([x509.UniformResourceIdentifier(identity)]), critical=True)
        .sign(key, hashes.SHA256())
    )


def _signed_request(
    identity: str, signer: ec.EllipticCurvePrivateKey, key_id: str, body: bytes, purpose: str = PROBE_PURPOSE
) -> Request:
    now = int(datetime.now(timezone.utc).timestamp())

    context = DelegatedContext(
        "1.0", key_id, identity, AUDIENCE, "POST", PROBE_ROUTE, PROBE_OPERATION, 1, "founder-1", "BP_SESSION", "FOUNDER", NIL_ID, NIL_ID,
        purpose, "providers", hashlib.sha256(body).hexdigest(), "command-1", None, {}, now, now, now + 60, f"envelope-{key_id}-{purpose}", "corr-1",
    )  # fmt: skip
    payload = json.dumps(asdict(context), ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
    token = f"{_b64(payload)}.{_b64(signer.sign(payload, ec.ECDSA(hashes.SHA256())))}"
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": PROBE_ROUTE,
            "headers": [(b"authorization", f"Bearer {token}".encode()), (b"x-correlation-id", b"corr-1")],
            "state": {PEER_CERTIFICATE_STATE_KEY: _certificate(identity).public_bytes(serialization.Encoding.DER)},
        }
    )


def test_probe_authorization_admits_only_the_business_platform_delegation_key() -> None:
    bp_key, pr_key = ec.generate_private_key(ec.SECP256R1()), ec.generate_private_key(ec.SECP256R1())
    now = int(datetime.now(timezone.utc).timestamp())
    grants = frozenset({RouteGrant(BP_IDENTITY, AUDIENCE, "POST", PROBE_ROUTE, PROBE_OPERATION, 1)})
    auth = EmploymentWorkloadAuth(
        grants, {(BP_IDENTITY, "bp-key"): bp_key.public_key()}, "waooaw.test", AUDIENCE, now=lambda: now
    )
    body = b'{"providers":[{"name":"openai","model":null}]}'
    assert _authorize(auth, _signed_request(BP_IDENTITY, bp_key, "bp-key", body), body) is not None
    # A caller without a grant or trusted delegation key is rejected even with a valid envelope shape.
    assert _authorize(auth, _signed_request(PR_IDENTITY, pr_key, "pr-key", body), body) is None
    assert _authorize(auth, _signed_request(BP_IDENTITY, pr_key, "bp-key", body), body) is None
    assert _authorize(auth, _signed_request(BP_IDENTITY, bp_key, "bp-key", body, "OTHER_PURPOSE"), body) is None
    assert _authorize(auth, _signed_request(BP_IDENTITY, bp_key, "bp-key", body), body + b" ") is None
    with pytest.raises(EmploymentAuthError):
        auth.authorize(
            _signed_request(BP_IDENTITY, bp_key, "bp-key", body), PROBE_ROUTE, "generateConversation", "0" * 64, None, None
        )


def _bp_signed_request(
    identity: str, signer: ec.EllipticCurvePrivateKey, body: bytes, actor_subject: str, **overrides: Any
) -> Request:
    # Mirrors ProviderGenerationProbe.cs AuthenticatedProviderProbeGateway + WorkloadIdentityClient.Sign: sorted keys,
    # compact JSON with System.Text.Json default string escaping, digest over the RAW body bytes, nil tenant/relationship.
    now = int(datetime.now(timezone.utc).timestamp())
    values: dict[str, Any] = {
        "actor_source": "BP_SESSION", "actor_subject": actor_subject, "command_id": "corr-bp", "contract_major": 1,
        "correlation_id": "corr-bp", "effective_role": "FOUNDER", "envelope_id": "0b0f7a3e-0000-4000-8000-000000000001",
        "expected_versions": {}, "expires_at": now + 60, "idempotency_key": None, "issued_at": now, "issuer_uri": identity,
        "key_id": "bp-key", "method": "POST", "not_before": now, "operation": PROBE_OPERATION, "purpose": PROBE_PURPOSE,
        "relationship_id": NIL_ID, "request_digest": hashlib.sha256(body).hexdigest(), "route": PROBE_ROUTE,
        "schema_version": "1.0", "subject_reference": "openai", "target_audience": AUDIENCE, "tenant_id": NIL_ID,
    }  # fmt: skip
    values.update(overrides)
    escaped = {"<": "\\u003C", ">": "\\u003E", "&": "\\u0026", "'": "\\u0027", "+": "\\u002B", "é": "\\u00E9"}

    def text(value: str) -> str:
        return '"' + "".join(escaped.get(character, character) for character in value) + '"'

    def encode(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, dict):
            return "{" + ",".join(f"{text(key)}:{encode(value[key])}" for key in sorted(value)) + "}"
        return text(value)

    payload = encode(values).encode()
    token = f"{_b64(payload)}.{_b64(signer.sign(payload, ec.ECDSA(hashes.SHA256())))}"
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": PROBE_ROUTE,
            "headers": [(b"authorization", f"Bearer {token}".encode()), (b"x-correlation-id", b"corr-bp")],
            "state": {PEER_CERTIFICATE_STATE_KEY: _certificate(identity).public_bytes(serialization.Encoding.DER)},
        }
    )


def test_probe_verifier_accepts_the_business_platform_signer_byte_for_byte() -> None:
    bp_key = ec.generate_private_key(ec.SECP256R1())
    now = int(datetime.now(timezone.utc).timestamp())
    grants = frozenset({RouteGrant(BP_IDENTITY, AUDIENCE, "POST", PROBE_ROUTE, PROBE_OPERATION, 1)})
    auth = EmploymentWorkloadAuth(
        grants, {(BP_IDENTITY, "bp-key"): bp_key.public_key()}, "waooaw.test", AUDIENCE, now=lambda: now
    )
    body = b'{"providers":[{"name":"openai","model":null},{"name":"google","model":"gemini-2.0-flash"}]}'
    for subject in ("founder-1", "o'brien+ops@example.com", "<Zoe & Co>", "caf\u00e9"):
        request = _bp_signed_request(BP_IDENTITY, bp_key, body, subject, envelope_id=f"env-{hash(subject)}")
        context = _authorize(auth, request, body)
        assert context is not None and context.actor_subject == subject and context.tenant_id == NIL_ID
    # Non-founder role, a tenant or relationship binding, or a wrong actor source never reaches the provider chain.
    for override in (
        {"effective_role": "CUSTOMER"},
        {"tenant_id": "tenant-1"},
        {"relationship_id": "3f2b0a8e-0000-4000-8000-000000000002"},
        {"actor_source": "WORKLOAD"},
    ):
        assert _authorize(auth, _bp_signed_request(BP_IDENTITY, bp_key, body, "founder-1", **override), body) is None


class RecordingAuth:
    def __init__(self, admit: bool = True) -> None:
        self.admit, self.calls = admit, 0

    def authorize(
        self, request: Request, route: str, operation: str, digest: str, relationship: str | None, key: str | None
    ) -> Any:
        self.calls += 1
        assert (route, operation, relationship, key) == (PROBE_ROUTE, PROBE_OPERATION, None, None)
        if not self.admit:
            raise EmploymentAuthError("AIR_EMPLOYMENT_UNAUTHORIZED")
        return SimpleNamespace(purpose=PROBE_PURPOSE, effective_role="FOUNDER", tenant_id=NIL_ID, relationship_id=NIL_ID)


def probe_app(auth: Any, service: Any) -> FastAPI:
    app = FastAPI()
    app.include_router(probe_router)
    app.state.provider_probe_auth, app.state.provider_generation_probe_service = auth, service
    return app


async def post_probe(app: FastAPI, body: Any) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://air") as client:
        return await client.post(
            "/internal/v1/provider-generations/probe", content=json.dumps(body), headers={"Authorization": "Bearer x"}
        )


async def test_probe_returns_a_real_answer_with_fixed_prompt_and_fallback_evidence() -> None:
    sent: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        if request.url.host == "api.openai.com":
            return httpx.Response(429)
        return httpx.Response(200, json={**SUCCESS["anthropic"], "content": [{"type": "text", "text": "y" * 900}]})

    service = ProviderGenerationProbeService(Keys(), client_for(handler))
    response = await post_probe(
        probe_app(RecordingAuth(), service),
        {"providers": [{"name": "openai", "model": None}, {"name": "anthropic", "model": "claude-sonnet-4-5"}]},
    )
    data = response.json()
    assert response.status_code == 200 and KEY not in response.text
    assert data["attempts"] == [
        {"provider": "openai", "outcome": "SKIPPED", "reason": "PROVIDER_ERROR"},
        {"provider": "anthropic", "outcome": "ANSWERED", "reason": None},
    ]
    assert set(data["answered"]) == {"provider", "model", "reportedModel", "text", "inputTokens", "outputTokens", "latencyMs"}
    assert data["answered"]["model"] == "claude-sonnet-4-5" and len(data["answered"]["text"]) == 500
    assert data["answered"]["inputTokens"] == 11 and data["answered"]["outputTokens"] == 3
    assert all(PROBE_PROMPT in json.dumps(body) for body in sent) and sent[-1]["max_tokens"] == PROBE_MAX_OUTPUT_TOKENS == 64
    exhausted = await post_probe(
        probe_app(RecordingAuth(), ProviderGenerationProbeService(Keys({}), client_for(handler))),
        {"providers": [{"name": "google"}]},
    )
    assert exhausted.json() == {
        "answered": None,
        "attempts": [{"provider": "google", "outcome": "SKIPPED", "reason": "KEY_MISSING"}],
    }


async def test_probe_rejects_other_callers_unconfigured_state_and_invalid_bodies() -> None:
    service = ProviderGenerationProbeService(Keys(), client_for(lambda _: httpx.Response(500)))
    denied = await post_probe(probe_app(RecordingAuth(admit=False), service), {"providers": [{"name": "openai"}]})
    assert denied.status_code == 401 and denied.json() == {"code": "PROBE_UNAUTHORIZED"}
    for auth, svc in ((None, service), (RecordingAuth(), None)):
        unavailable = await post_probe(probe_app(auth, svc), {"providers": [{"name": "openai"}]})
        assert unavailable.status_code == 503 and unavailable.json() == {"code": "PROVIDER_PROBE_UNAVAILABLE"}
    for body in (
        {"providers": []},
        {"providers": [{"name": "openai"}] * 2},
        {"providers": [{"name": n} for n in ("sarvam", "openai", "anthropic", "google", "x")]},
        {"providers": [{"name": "evil"}]},
        {"providers": [{"name": "openai", "model": "a/../b"}]},
        {"providers": [{"name": "openai"}], "prompt": "customer data"},
    ):
        invalid = await post_probe(probe_app(RecordingAuth(), service), body)
        assert invalid.status_code == 422 and invalid.json() == {"code": "PROBE_INVALID"}


async def test_unmounted_probe_state_is_503_on_the_real_application() -> None:
    from main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://air") as client:
        response = await client.post("/internal/v1/provider-generations/probe", json={"providers": [{"name": "openai"}]})
    assert response.status_code == 503 and response.json() == {"code": "PROVIDER_PROBE_UNAVAILABLE"}

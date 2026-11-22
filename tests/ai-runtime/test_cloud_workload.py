# Implements: ADR-046 Amendment 1 (cloud credential delivery) for the AI runtime private listener and BP owner client
# constitutional_basis: C-026, C-059, C-063, C-076, C-083, C-084, C-085

from __future__ import annotations

import asyncio
import hashlib
import json
import ssl
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

import cloud_workload
import entrypoint
import main
import private_server
import runtime_workload_credentials as wc
import wid_air_cloud_fixture as fx
from conversation_generation_owner import BusinessPlatformGenerationOwner
from employment_auth import EmploymentAuthError
from provider_generation_probe import PROBE_OPERATION, ProviderGenerationProbeService, _authorize
from runtime_workload_credentials import (
    CredentialError,
    CredentialHolder,
    KeyVaultSecretReader,
    authenticate_peer,
    build_snapshot,
    credential_holder_from_environment,
    register_holder,
    validate_vault_url,
    verify_trust_bundle,
)
from test_hosted_providers import _signed_request
from workload_identity import ServiceAuthError

TARGET = "ai-runtime"
DER = serialization.Encoding.DER


@pytest.fixture
def cloud() -> fx.Cloud:
    return fx.new_cloud()


@pytest.fixture(autouse=True)
def _clean_shared_holder():
    register_holder(None)
    yield
    register_holder(None)


def accept(pair: fx.Pair):
    trust = verify_trust_bundle(pair.texts[0], fx.TRUST_DOMAIN, "demo", pair.cloud.now)
    return build_snapshot(trust, pair.texts[1], TARGET, pair.cloud.now)


def secrets(pair: fx.Pair) -> dict[str, object]:
    return {wc.TRUST_BUNDLE_SECRET: pair.texts[0], f"wid-bundle-{TARGET}": pair.texts[1]}


class FakeReader:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get_secret(self, name: str) -> str:
        value = self.values[name]
        if isinstance(value, Exception):
            raise value
        assert isinstance(value, str)
        return value


def holder_for(cloud: fx.Cloud, values: dict[str, object], clock=None) -> CredentialHolder:
    return CredentialHolder(
        wc.SOURCE_KEYVAULT,
        TARGET,
        fx.TRUST_DOMAIN,
        environment="demo",
        reader=FakeReader(values),
        clock=clock or (lambda: cloud.now),
    )


def ready_holder(cloud: fx.Cloud, **options) -> tuple[CredentialHolder, fx.Pair]:
    pair = fx.build_pair(cloud, **options)
    holder = holder_for(cloud, secrets(pair))
    assert holder.refresh_once()
    return holder, pair


def test_valid_bundle_builds_an_ai_runtime_snapshot(cloud) -> None:
    pair = fx.build_pair(cloud)
    snapshot = accept(pair)
    assert snapshot.workload == TARGET and snapshot.identity_uri == fx.AIR_URI and snapshot.audience == fx.AIR_AUDIENCE
    assert {grant.operation for grant in snapshot.grants} == {"probeProviderGeneration", "generateConversation"}
    assert snapshot.delegation_key_id == pair.own_delegation[2]["key_id"] and snapshot.delegation_key_pem is not None
    assert snapshot.manifest["workloads"]["business-platform"]["audience"] == fx.BP_AUDIENCE
    assert len(snapshot.serial_digest) == 16


@pytest.mark.parametrize(
    ("reason", "options"),
    [
        ("ENVIRONMENT_MISMATCH", {"bundle_environment": "uat"}),
        ("TRUST_DOMAIN_MISMATCH", {"trust_domain": "other.waooaw.internal"}),
        ("LEAF_VALIDITY_INVALID", {"leaf_start": timedelta(hours=-30)}),
        ("LEAF_IDENTITY_MISMATCH", {"leaf_uri": fx.BP_URI}),
        ("LEAF_USAGE_INVALID", {"usages": [fx.SERVER]}),
        ("LEAF_KEY_MISMATCH", {"key_mismatch": True}),
        ("LEAF_REVOKED", {"revoked_uris": [fx.AIR_URI]}),
        ("DELEGATION_USAGE_INVALID", {"delegation": {"usages": [fx.CLIENT]}}),
        ("DELEGATION_IDENTITY_MISMATCH", {"delegation": {"uri": fx.PR_URI}}),
    ],
)
def test_bundle_that_bends_a_rule_is_rejected(cloud, reason, options) -> None:
    with pytest.raises(CredentialError) as raised:
        accept(fx.build_pair(cloud, **options))
    assert raised.value.code == reason


def test_tampered_or_foreign_trust_bundle_is_rejected(cloud) -> None:
    pair = fx.build_pair(cloud)
    tampered = json.loads(pair.texts[0]) | {"bundle_version": 999}
    with pytest.raises(CredentialError) as raised:
        verify_trust_bundle(json.dumps(tampered), fx.TRUST_DOMAIN, "demo", cloud.now)
    assert raised.value.code == "TRUST_BUNDLE_SIGNATURE_INVALID"
    with pytest.raises(CredentialError) as raised:
        verify_trust_bundle(json.dumps({"state": "UNISSUED"}), fx.TRUST_DOMAIN, "demo", cloud.now)
    assert raised.value.code in {"UNISSUED", "SCHEMA_INVALID"}


def test_holder_swaps_verified_bundles_rejects_rollback_and_fails_closed_on_expiry(cloud) -> None:
    pair = fx.build_pair(cloud)
    values = secrets(pair)
    now = [cloud.now]
    holder = holder_for(cloud, values, clock=lambda: now[0])
    seen: list[int] = []
    holder.subscribe(lambda snapshot: seen.append(snapshot.bundle_version))
    assert holder.state() == wc.STATE_UNISSUED and holder.current() is None and holder.remaining_seconds() == 0
    assert holder.refresh_once() and seen == [100] and holder.state() == wc.STATE_READY
    assert holder.status()["lastReason"] is None and holder.audience() == fx.AIR_AUDIENCE and holder.anchors() is not None
    assert holder.grants() and holder.delegation_keys() and holder.refreshable and holder.enforced
    values.update(secrets(fx.build_pair(cloud, version=99, own_version=99)))
    assert not holder.refresh_once() and holder.status()["lastReason"] == "BUNDLE_VERSION_ROLLBACK" and holder.current()
    values[wc.TRUST_BUNDLE_SECRET] = RuntimeError("vault down")
    assert not holder.refresh_once() and holder.status()["lastReason"] == "REFRESH_FAILED"
    now[0] = pair.leaf.not_valid_after_utc + timedelta(seconds=1)
    assert holder.current() is None and holder.state() == wc.STATE_UNAVAILABLE
    assert holder.grants() == frozenset() and holder.delegation_keys() == {} and holder.audience() is None
    with pytest.raises(ServiceAuthError):
        authenticate_peer(holder, pair.bp_leaf, now[0])


def test_peer_authentication_uses_the_current_trust_bundle(cloud) -> None:
    holder, pair = ready_holder(cloud)
    assert authenticate_peer(holder, pair.bp_leaf, cloud.now) == fx.BP_URI
    foreign_key, foreign = fx.new_cloud().issue(fx.BP_URI, [fx.CLIENT, fx.SERVER])
    assert foreign_key is not None
    with pytest.raises(ServiceAuthError):
        authenticate_peer(holder, foreign, cloud.now)


async def test_holder_run_refreshes_until_stopped(cloud) -> None:
    pair = fx.build_pair(cloud)
    holder = holder_for(cloud, secrets(pair))
    stop = asyncio.Event()
    task = asyncio.create_task(holder.run(stop))
    for _ in range(50):
        if holder.current() is not None:
            break
        await asyncio.sleep(0.02)
    stop.set()
    await asyncio.wait_for(task, 5)
    assert holder.state() == wc.STATE_READY


def vault_http(status: int = 200, token_status: int = 200):
    def get(url: str, headers: dict[str, str], _timeout: float) -> tuple[int, bytes]:
        if url.startswith("http://identity"):
            return token_status, json.dumps({"access_token": "t", "expires_on": str(int(time.time()) + 3600)}).encode()
        assert headers["Authorization"] == "Bearer t"
        return status, json.dumps({"value": "secret-value"}).encode()

    return get


ENV = {"IDENTITY_ENDPOINT": "http://identity/msi/token", "IDENTITY_HEADER": "header"}


@pytest.mark.parametrize(
    ("status", "token_status", "environ", "code"),
    [
        (403, 200, ENV, "VAULT_DENIED"),
        (404, 200, ENV, "SECRET_NOT_FOUND"),
        (500, 200, ENV, "VAULT_UNAVAILABLE"),
        (200, 500, ENV, "IDENTITY_UNAVAILABLE"),
        (200, 200, {}, "IDENTITY_UNAVAILABLE"),
    ],
)
def test_key_vault_reader_reports_stable_reason_codes(status, token_status, environ, code) -> None:
    reader = KeyVaultSecretReader("https://vault.vault.azure.net", "client", environ, vault_http(status, token_status))
    with pytest.raises(CredentialError) as raised:
        reader.get_secret("wid-trust-bundle")
    assert raised.value.code == code


def test_key_vault_reader_returns_the_secret_and_rejects_foreign_vault_hosts() -> None:
    reader = KeyVaultSecretReader("https://vault.vault.azure.net/", None, ENV, vault_http())
    assert reader.get_secret("wid-trust-bundle") == "secret-value" and reader.get_secret("wid-trust-bundle")
    for url in ("http://vault.vault.azure.net", "https://evil.example.com", ""):
        with pytest.raises(CredentialError):
            validate_vault_url(url)


def test_holder_is_selected_only_for_the_key_vault_source() -> None:
    assert credential_holder_from_environment({}) is None
    cloud_env = {
        "WAOOAW_WID_SOURCE": "keyvault",
        "WAOOAW_WID_WORKLOAD": TARGET,
        "WAOOAW_WID_TRUST_DOMAIN": fx.TRUST_DOMAIN,
        "WAOOAW_WID_VAULT_URL": "https://vault.vault.azure.net",
        "WAOOAW_WID_ENVIRONMENT": "demo",
    }
    holder = credential_holder_from_environment(cloud_env)
    assert holder is not None and holder.refreshable and holder.state() == wc.STATE_UNISSUED
    for change in (
        {"WAOOAW_WID_WORKLOAD": "billing-engine"},
        {"WAOOAW_WID_VAULT_URL": "http://x"},
        {"WAOOAW_WID_SOURCE": "other"},
    ):
        rejected = credential_holder_from_environment(cloud_env | change)
        assert rejected is not None and not rejected.refreshable and rejected.status()["lastReason"] == "CONFIG_INVALID"
    assert credential_holder_from_environment(cloud_env | {"WAOOAW_WID_REFRESH_SECONDS": "x"}) is not None


def test_snapshot_auth_admits_only_the_named_caller_and_fails_closed_without_a_snapshot(cloud) -> None:
    holder, pair = ready_holder(cloud)
    body = b'{"providers":[{"name":"openai","model":null}]}'
    key_id = pair.trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"][0]["key_id"]
    request = _signed_request(fx.BP_URI, pair.bp_key, key_id, body)
    context = cloud_workload.SnapshotWorkloadAuth(holder, "business-platform")
    assert _authorize(context, request, body) is not None
    other = cloud_workload.SnapshotWorkloadAuth(holder, "professional-runtime")
    assert _authorize(other, _signed_request(fx.BP_URI, pair.bp_key, key_id, body), body) is None
    empty = cloud_workload.SnapshotWorkloadAuth(holder_for(cloud, {}), "business-platform")
    with pytest.raises(EmploymentAuthError):
        empty.authorize(request, fx.PROBE_ROUTE, PROBE_OPERATION, hashlib.sha256(body).hexdigest(), None, None)


def test_client_tls_follows_snapshots_and_needs_a_key_directory(cloud, tmp_path: Path) -> None:
    holder, _ = ready_holder(cloud)
    tls = cloud_workload.HotReloadClientTls(holder, tmp_path)
    assert tls.context.verify_mode == ssl.CERT_REQUIRED and not tls.context.check_hostname and list(tmp_path.iterdir()) == []
    with pytest.raises(RuntimeError, match="tmpfs"):
        cloud_workload.HotReloadClientTls(holder, tmp_path / "missing")


class PeerStream:
    def __init__(self, der: bytes | None) -> None:
        self.der = der

    def get_extra_info(self, name: str):
        return SimpleNamespace(getpeercert=lambda binary_form: self.der) if name == "ssl_object" else None


async def test_cloud_owner_signs_with_the_snapshot_key_and_verifies_the_peer_uri(cloud) -> None:
    holder, pair = ready_holder(cloud)
    peers = {"der": pair.bp_leaf.public_bytes(DER)}

    def handler(_request: httpx.Request) -> httpx.Response:
        stream = PeerStream(peers["der"])
        return httpx.Response(
            200, json={"providerName": "openai", "secretName": "provider-openai"}, extensions={"network_stream": stream}
        )

    owner = BusinessPlatformGenerationOwner.from_holder("https://bp:5444/", holder, ssl.create_default_context())
    owner.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    assert owner.endpoint == "https://bp:5444" and owner.issuer == fx.AIR_URI and owner.audience == fx.BP_AUDIENCE
    assert owner.expected_peer == fx.BP_URI and isinstance(owner.key, ec.EllipticCurvePrivateKey)
    assert (await owner.resolve_provider_credential("openai"))["secretName"] == "provider-openai"
    for der in (None, pair.leaf.public_bytes(DER)):
        peers["der"] = der
        with pytest.raises(ValueError, match="peer identity"):
            await owner.resolve_provider_credential("openai")
    with pytest.raises(ValueError, match="HTTPS"):
        BusinessPlatformGenerationOwner.from_holder("http://bp", holder, ssl.create_default_context())
    await owner.close()


async def test_cloud_owner_refuses_to_sign_before_a_credential_and_without_a_delegation_key(cloud) -> None:
    unready = holder_for(cloud, {})
    owner = BusinessPlatformGenerationOwner.from_holder("https://bp", unready, ssl.create_default_context())
    with pytest.raises(RuntimeError, match="not yet available"):
        await owner.resolve_provider_credential("openai")
    holder, _ = ready_holder(cloud, own_delegation=False)
    with pytest.raises(ValueError, match="delegation key"):
        BusinessPlatformGenerationOwner.from_holder("https://bp", holder, ssl.create_default_context())
    await owner.close()


def test_private_listener_uses_the_gated_protocol_and_hot_reloaded_context_for_key_vault(monkeypatch, cloud, tmp_path) -> None:
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "keyvault")
    monkeypatch.setenv("WAOOAW_WID_KEY_TMPFS", str(tmp_path))
    config = private_server.private_listener_config()
    assert config.http is private_server.CredentialGatedProtocol and config.port == 5444 and private_server.keyvault_source()
    server = MagicMock()
    monkeypatch.setattr(private_server.uvicorn, "Server", MagicMock(return_value=server))
    fake = SimpleNamespace(ssl=None, load=lambda: None)
    monkeypatch.setattr(private_server, "private_listener_config", lambda: fake)
    with pytest.raises(RuntimeError, match="credential holder"):
        private_server.main()
    holder, pair = ready_holder(cloud)
    register_holder(holder)
    private_server.main()
    assert isinstance(fake.ssl, ssl.SSLContext) and fake.ssl.minimum_version == ssl.TLSVersion.TLSv1_2
    server.run.assert_called_once_with()
    reload = private_server.HotReloadTlsContext(holder, tmp_path)
    assert reload._refuse_when_unavailable(None, None, None) is None
    reload.install(accept(pair))
    with pytest.raises(RuntimeError, match="tmpfs"):
        private_server.HotReloadTlsContext(holder, tmp_path / "missing").install(accept(pair))
    assert (
        private_server.HotReloadTlsContext(holder_for(cloud, {}), tmp_path)._refuse_when_unavailable(None, None, None)
        == ssl.ALERT_DESCRIPTION_HANDSHAKE_FAILURE
    )


def test_gated_protocol_refuses_peers_that_do_not_chain_to_the_current_bundle(monkeypatch, cloud) -> None:
    holder, pair = ready_holder(cloud)
    accepted: list[object] = []
    monkeypatch.setattr(
        private_server.MutualTlsH11Protocol, "connection_made", lambda _self, transport: accepted.append(transport)
    )

    def connect(der: bytes | None) -> MagicMock:
        transport = MagicMock()
        transport.get_extra_info.return_value = SimpleNamespace(getpeercert=lambda binary_form: der)
        object.__new__(private_server.CredentialGatedProtocol).connection_made(transport)
        return transport

    assert connect(pair.bp_leaf.public_bytes(DER)).close.called and not accepted
    register_holder(holder)
    assert not connect(pair.bp_leaf.public_bytes(DER)).close.called and len(accepted) == 1
    foreign = fx.new_cloud().issue(fx.BP_URI, [fx.CLIENT, fx.SERVER])[1]
    assert connect(foreign.public_bytes(DER)).close.called and connect(None).close.called


def test_entrypoint_runs_the_private_listener_only_when_credentials_are_enabled() -> None:
    assert len(entrypoint.child_commands({})) == 1 and "5004" in entrypoint.child_commands({})[0]
    for env in ({"WAOOAW_WID_SOURCE": "keyvault"}, {"AIR_PRIVATE_LISTENER": "1"}, {"WAOOAW_WORKLOAD_CREDENTIALS": "/c"}):
        assert entrypoint.child_commands(env)[1][-1] == "private_server.py"


class Child:
    def __init__(self, status: int | None) -> None:
        self.status, self.stopped = status, False

    def poll(self) -> int | None:
        return None if self.stopped else self.status

    def terminate(self) -> None:
        self.stopped = True

    def kill(self) -> None:
        self.stopped = True

    def wait(self, timeout: float | None = None) -> int:
        return 0


def test_entrypoint_stops_every_child_when_one_exits_or_termination_is_requested() -> None:
    children = [Child(None), Child(3)]
    iterator = iter(children)
    assert entrypoint.supervise({"AIR_PRIVATE_LISTENER": "1"}, lambda _command: next(iterator), lambda _seconds: None) == 3
    assert children[0].stopped
    quiet = [Child(None), Child(None)]
    iterator = iter(quiet)
    assert (
        entrypoint.supervise({"AIR_PRIVATE_LISTENER": "1"}, lambda _command: next(iterator), lambda _s: None, lambda: True) == 143
    )
    assert all(child.stopped for child in quiet)


async def test_lifespan_wires_the_cloud_credential_into_owner_probe_and_listener_auth(monkeypatch, cloud, tmp_path) -> None:
    holder = holder_for(cloud, secrets(fx.build_pair(cloud)))
    closed: list[str] = []

    async def close_repository() -> None:
        closed.append("repository")

    async def connect(_database_url: str):
        return SimpleNamespace(pool=object(), close=close_repository)

    monkeypatch.setenv("DATABASE_URL", "postgresql://air@postgres/waooaw")
    monkeypatch.setenv("AIR_CONVERSATION_GENERATION_OWNER_URL", "https://ca-demo-business-platform:5444")
    monkeypatch.setenv("AIR_CONVERSATION_TOKENIZER_DIRECTORY", "/tokenizers")
    monkeypatch.setenv("WAOOAW_WID_KEY_TMPFS", str(tmp_path))
    monkeypatch.setenv("PROVIDER_CREDENTIALS_VAULT_URL", "https://vault.vault.azure.net")
    monkeypatch.setattr(main.EmploymentPatchRepository, "connect", connect)
    monkeypatch.setattr(main, "ConversationGenerationStore", lambda pool: pool)
    monkeypatch.setattr(main, "InstitutionalOllamaProvider", lambda directory, client: (directory, client))
    monkeypatch.setattr(main, "GovernedInferenceToolGateway", lambda provider: provider)
    monkeypatch.setattr(main, "GovernedGenerationService", lambda _store, owner, _gateway: owner)
    application = SimpleNamespace(state=SimpleNamespace(workload_credentials=holder))

    async with main.lifespan(application):
        for _ in range(100):
            if holder.current() is not None:
                break
            await asyncio.sleep(0.02)
        owner = application.state.conversation_generation_service
        assert owner.issuer == fx.AIR_URI and owner.expected_peer == fx.BP_URI
        assert isinstance(application.state.provider_probe_auth, cloud_workload.SnapshotWorkloadAuth)
        assert isinstance(application.state.provider_generation_probe_service, ProviderGenerationProbeService)

    assert application.state.provider_generation_probe_service is None and closed == ["repository"]
    assert isinstance(main.app.state.employment_workload_auth, object)


async def test_probe_is_mounted_without_database_tokenizers_or_a_published_binding(monkeypatch, cloud, tmp_path) -> None:
    holder = holder_for(cloud, secrets(fx.build_pair(cloud)))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AIR_CONVERSATION_TOKENIZER_DIRECTORY", raising=False)
    monkeypatch.setenv("AIR_CONVERSATION_GENERATION_OWNER_URL", "https://ca-demo-business-platform:5444")
    monkeypatch.setenv("WAOOAW_WID_KEY_TMPFS", str(tmp_path))
    monkeypatch.setenv("PROVIDER_CREDENTIALS_VAULT_URL", "https://vault.vault.azure.net")
    application = SimpleNamespace(state=SimpleNamespace(workload_credentials=holder))

    async with main.lifespan(application):
        assert application.state.employment_patch_repository is None
        assert application.state.conversation_generation_service is None
        assert isinstance(application.state.provider_probe_auth, cloud_workload.SnapshotWorkloadAuth)
        assert isinstance(application.state.provider_generation_probe_service, ProviderGenerationProbeService)

    assert application.state.provider_generation_probe_service is None and application.state.provider_probe_auth is None


async def test_probe_stays_unavailable_without_the_owner_address_or_vault(monkeypatch, cloud, tmp_path) -> None:
    holder = holder_for(cloud, secrets(fx.build_pair(cloud)))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("WAOOAW_WID_KEY_TMPFS", str(tmp_path))
    monkeypatch.delenv("AIR_CONVERSATION_GENERATION_OWNER_URL", raising=False)
    monkeypatch.setenv("PROVIDER_CREDENTIALS_VAULT_URL", "https://vault.vault.azure.net")
    application = SimpleNamespace(state=SimpleNamespace(workload_credentials=holder))
    async with main.lifespan(application):
        assert application.state.provider_generation_probe_service is None
    monkeypatch.setenv("AIR_CONVERSATION_GENERATION_OWNER_URL", "https://ca-demo-business-platform:5444")
    monkeypatch.delenv("PROVIDER_CREDENTIALS_VAULT_URL", raising=False)
    async with main.lifespan(application):
        assert application.state.provider_generation_probe_service is None

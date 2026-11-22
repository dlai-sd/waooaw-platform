# Implements: ADR-046 Amendment 1 (IB-147) Billing Engine side of workload credential delivery
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import asyncio
import base64
import json
import logging
import socket
import ssl
import sys
import threading
import time
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI, HTTPException

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

import entrypoint
import wid_cloud_fixture as fx
from mtls_protocol import MutualTlsH11Protocol, validated_protocol
from private_server import WorkloadTlsContext, await_first_snapshot
from relationship_workspace import WorkloadAuth, configure_relationship_workspace
from uvicorn.protocols.http.h11_impl import H11Protocol
from billing_workload_credentials import (
    CredentialHolder,
    CredentialRefresher,
    CredentialRejected,
    Expectation,
    KeyVaultReader,
    build_keyvault_runtime,
    parse_vault_url,
    probe_service_link,
    reset_keyvault_runtime,
    verify_credentials,
)
from workload_identity import (
    DELEGATION_SIGNING_OID,
    PEER_CERTIFICATE_STATE_KEY,
    DelegatedContext,
    DelegatedContextVerifier,
    DelegationKey,
    ReplayStore,
    ServiceAuthError,
    TrustAnchors,
    has_extended_key_usage,
)

EXPECT = Expectation("billing-engine", fx.TRUST_DOMAIN, "demo")
OPERATION = "getRelationshipCommercialProjection"
DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def auth_from_holder(holder, trust_domain: str):
    # Billing and Professional Runtime each define a module named relationship_workspace; static analysis cannot
    # tell which one this test imports, so the classmethod is looked up at run time.
    return getattr(WorkloadAuth, "from_holder")(holder, trust_domain)  # noqa: B009


@pytest.fixture
def cloud() -> fx.Cloud:
    return fx.new_cloud()


def accept(pair: fx.Pair, **changes):
    arguments = {"expectation": EXPECT, "current": pair.cloud.now} | changes
    return verify_credentials(*pair.texts, **arguments)


def reason_of(pair: fx.Pair, **changes) -> str:
    with pytest.raises(CredentialRejected) as raised:
        accept(pair, **changes)
    return raised.value.reason


def token(key, key_id: str, now: int, envelope_id: str = "envelope-1", **changes) -> str:
    values = {
        "schema_version": "1.0",
        "key_id": key_id,
        "issuer_uri": fx.BP_URI,
        "target_audience": fx.WBE_AUDIENCE,
        "method": "GET",
        "route": fx.PROJECTION_ROUTE,
        "operation": OPERATION,
        "contract_major": 1,
        "actor_subject": "actor",
        "actor_source": "BP_SESSION",
        "effective_role": "EMPLOYER",
        "tenant_id": "tenant-a",
        "relationship_id": "relationship-a",
        "purpose": OPERATION,
        "subject_reference": "relationship-a",
        "request_digest": DIGEST,
        "command_id": "read-1",
        "idempotency_key": None,
        "expected_versions": {},
        "issued_at": now - 1,
        "not_before": now - 1,
        "expires_at": now + 59,
        "envelope_id": envelope_id,
        "correlation_id": "correlation-1",
    } | changes
    payload = json.dumps(asdict(DelegatedContext(**values)), separators=(",", ":"), sort_keys=True).encode()
    signature = key.sign(payload, ec.ECDSA(hashes.SHA256()))

    def encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{encode(payload)}.{encode(signature)}"


def verify_token(verifier: DelegatedContextVerifier, signed: str) -> DelegatedContext:
    return verifier.verify(
        signed, fx.BP_URI, fx.WBE_AUDIENCE, "GET", fx.PROJECTION_ROUTE, OPERATION, 1, DIGEST, lambda _context: True
    )


def kid_of(pair: fx.Pair) -> str:
    return pair.trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"][0]["key_id"]


def test_valid_bundle_builds_a_snapshot(cloud) -> None:
    pair = fx.build_pair(cloud)
    snapshot = accept(pair)
    assert snapshot.identity_uri == fx.WBE_URI and snapshot.audience == fx.WBE_AUDIENCE
    assert snapshot.bundle_version == 100 and len(snapshot.serial_digest) == 16
    assert snapshot.not_after == pair.leaf.not_valid_after_utc
    assert (fx.BP_URI, kid_of(pair)) in snapshot.delegation_keys
    assert {grant.operation for grant in snapshot.grants} == {"probeServiceLink", OPERATION}
    assert "BEGIN" not in repr(snapshot)


@pytest.mark.parametrize(
    ("reason", "options"),
    [
        ("ENVIRONMENT_MISMATCH", {"bundle_environment": "uat"}),
        ("ENVIRONMENT_MISMATCH", {"trust_environment": "uat", "bundle_environment": "uat"}),
        ("TRUST_DOMAIN_MISMATCH", {"trust_domain": "other.waooaw.internal"}),
        ("LEAF_NOT_VALID", {"leaf_start": timedelta(hours=-30), "leaf_lifetime": timedelta(hours=24)}),
        ("LEAF_IDENTITY_MISMATCH", {"leaf_uri": f"spiffe://{fx.TRUST_DOMAIN}/workload/professional-runtime"}),
        ("LEAF_USAGE_INVALID", {"usages": [fx.CLIENT]}),
        ("KEY_MISMATCH", {"key_mismatch": True}),
        ("LEAF_REVOKED", {"revoke_leaf": True}),
        ("DELEGATION_INVALID", {"delegation": {"usages": [fx.CLIENT]}}),
    ],
)
def test_bundle_that_bends_a_rule_is_rejected(cloud, reason, options) -> None:
    assert reason_of(fx.build_pair(cloud, **options)) == reason


def test_expected_trust_domain_and_environment_are_exact(cloud) -> None:
    pair = fx.build_pair(cloud)
    assert reason_of(pair, expectation=Expectation("billing-engine", "uat.waooaw.internal")) == "TRUST_DOMAIN_MISMATCH"
    assert reason_of(pair, expectation=Expectation("billing-engine", fx.TRUST_DOMAIN, "uat")) == "ENVIRONMENT_MISMATCH"


def test_tampered_signature_lower_version_and_unissued_are_rejected(cloud) -> None:
    pair = fx.build_pair(cloud)
    pair.trust["bundle_version"] = 101
    assert reason_of(pair) == "SIGNATURE_INVALID"
    foreign = fx.build_pair(cloud)
    foreign.trust = cloud.trust_bundle(100, [], signing_key=ec.generate_private_key(ec.SECP256R1()))
    assert reason_of(foreign) == "SIGNATURE_INVALID"
    assert reason_of(fx.build_pair(cloud, 100, 100), last_bundle_version=101) == "VERSION_REGRESSION"
    assert reason_of(fx.build_pair(cloud, 100, 100), last_own_version=101) == "VERSION_REGRESSION"
    with pytest.raises(CredentialRejected, match="UNISSUED"):
        verify_credentials("UNISSUED", "UNISSUED", EXPECT, cloud.now)


def test_leaf_and_delegation_from_another_root_are_rejected(cloud) -> None:
    other = fx.new_cloud(cloud.now)
    pair = fx.build_pair(cloud)
    _, foreign_leaf = other.issue(fx.WBE_URI, [fx.SERVER])
    pair.bundle["tls_cert_pem"] = fx._pem(foreign_leaf, cloud.intermediate)
    assert reason_of(pair) == "LEAF_CHAIN_INVALID"
    assert reason_of(fx.build_pair(cloud, delegation={"issuer": other})) == "DELEGATION_INVALID"


def test_revoked_and_stale_delegation_certificates_are_excluded_not_fatal(cloud) -> None:
    _, _stale, stale_entry = cloud.delegation(start=timedelta(hours=-30), lifetime=timedelta(hours=24))
    _revoked_key, revoked, revoked_entry = cloud.delegation()
    pair = fx.build_pair(cloud, extra_delegations=[stale_entry, revoked_entry], revoked_serials=[revoked.serial_number])
    keys = accept(pair).delegation_keys
    assert (fx.BP_URI, kid_of(pair)) in keys and (fx.BP_URI, revoked_entry["key_id"]) not in keys
    assert (fx.BP_URI, stale_entry["key_id"]) not in keys
    assert not accept(fx.build_pair(cloud, revoked_uris=[fx.BP_URI])).delegation_keys


def test_refresher_keeps_the_previous_snapshot_on_every_failure(cloud, caplog) -> None:
    good = fx.build_pair(cloud, 100, 100)
    bad = fx.build_pair(cloud, 101, 101)
    bad.trust["bundle_version"] = 102
    source = {"texts": good.texts}
    holder = CredentialHolder("keyvault", now=lambda: cloud.now)
    refresher = CredentialRefresher(holder, lambda: source["texts"], EXPECT, now=lambda: cloud.now)
    caplog.set_level(logging.INFO)
    assert refresher.refresh_once() == "ACCEPTED"
    installed = holder.current()
    assert refresher.refresh_once() == "UNCHANGED"
    source["texts"] = bad.texts
    assert refresher.refresh_once() == "SIGNATURE_INVALID"
    source["texts"] = fx.build_pair(cloud, 99, 99).texts
    assert refresher.refresh_once() == "VERSION_REGRESSION"

    def unreachable() -> tuple[str, str]:
        raise httpx.ConnectError("vault down")

    refresher._fetch = unreachable
    assert refresher.refresh_once() == "FETCH_FAILED"
    assert holder.current() is installed and holder.status()["state"] == "READY"
    assert "decision=reject reason=VERSION_REGRESSION" in caplog.text
    assert "BEGIN" not in caplog.text


def test_hot_reload_swaps_the_delegation_key_set_without_restart(cloud) -> None:
    first = fx.build_pair(cloud, 100, 100)
    second = fx.build_pair(
        cloud, 101, 101, extra_delegations=first.trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"]
    )
    source = {"texts": first.texts}
    holder = CredentialHolder("keyvault", now=lambda: cloud.now)
    refresher = CredentialRefresher(holder, lambda: source["texts"], EXPECT, now=lambda: cloud.now)
    refresher.refresh_once()
    auth = auth_from_holder(holder, fx.TRUST_DOMAIN)
    now = int(cloud.now.timestamp())
    assert verify_token(auth.verifier, token(first.bp_key, kid_of(first), now, "e1")).envelope_id == "e1"
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
        verify_token(auth.verifier, token(second.bp_key, kid_of(second), now, "e2"))
    source["texts"] = second.texts
    assert refresher.refresh_once() == "ACCEPTED"
    assert verify_token(auth.verifier, token(second.bp_key, kid_of(second), now, "e3")).envelope_id == "e3"
    assert verify_token(auth.verifier, token(first.bp_key, kid_of(first), now, "e4")).envelope_id == "e4"


def test_envelope_key_must_be_active_currently_valid_chained_and_carry_the_oid(cloud) -> None:
    pair = fx.build_pair(cloud, delegation={"activate_after": timedelta(minutes=10)})
    snapshot = accept(pair)
    now = int(cloud.now.timestamp())
    verifier = DelegatedContextVerifier(
        snapshot.grants, snapshot.delegation_keys, ReplayStore(), now=lambda: now, anchors=lambda: snapshot.anchors
    )
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
        verify_token(verifier, token(pair.bp_key, kid_of(pair), now, "early"))
    later = now + 601
    verifier = DelegatedContextVerifier(
        snapshot.grants, snapshot.delegation_keys, ReplayStore(), now=lambda: later, anchors=lambda: snapshot.anchors
    )
    assert verify_token(verifier, token(pair.bp_key, kid_of(pair), later, "later")).envelope_id == "later"
    expired = now + int(timedelta(hours=25).total_seconds())
    verifier = DelegatedContextVerifier(
        snapshot.grants, snapshot.delegation_keys, ReplayStore(), now=lambda: expired, anchors=lambda: snapshot.anchors
    )
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
        verify_token(verifier, token(pair.bp_key, kid_of(pair), expired, "expired"))

    def attempt(key, certificate, anchors: TrustAnchors | None) -> DelegatedContext:
        keys = {(fx.BP_URI, "k"): DelegationKey(key.public_key(), certificate, 0)}
        direct = DelegatedContextVerifier(snapshot.grants, keys, ReplayStore(), now=lambda: now, anchors=lambda: anchors)
        return verify_token(direct, token(key, "k", now, f"direct-{certificate.serial_number}"))

    key, certificate, _ = cloud.delegation()
    assert attempt(key, certificate, snapshot.anchors).actor_subject == "actor"
    revoked_anchors = TrustAnchors(snapshot.anchors.roots, snapshot.anchors.intermediates, frozenset({certificate.serial_number}))
    unchained_key, unchained, _ = fx.new_cloud(cloud.now).delegation()
    no_oid_key, no_oid, _ = cloud.delegation(usages=[fx.CLIENT])
    assert not has_extended_key_usage(no_oid, DELEGATION_SIGNING_OID)
    for denied_key, denied, anchors in (
        (key, certificate, revoked_anchors),
        (unchained_key, unchained, snapshot.anchors),
        (no_oid_key, no_oid, snapshot.anchors),
        (key, certificate, None),
    ):
        with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
            attempt(denied_key, denied, anchors)


def test_expired_snapshot_fails_closed(cloud, caplog) -> None:
    pair = fx.build_pair(cloud)
    clock = {"now": cloud.now}
    holder = CredentialHolder("keyvault", now=lambda: clock["now"])
    CredentialRefresher(holder, lambda: pair.texts, EXPECT, now=lambda: cloud.now).refresh_once()
    auth = auth_from_holder(holder, fx.TRUST_DOMAIN)
    peer = pair.bp_leaf.public_bytes(serialization.Encoding.DER)
    assert holder.validate_peer(peer) and holder.status()["state"] == "READY"
    caplog.set_level(logging.WARNING)
    clock["now"] = pair.leaf.not_valid_after_utc + timedelta(seconds=1)
    status = holder.status()
    assert status["state"] == "UNAVAILABLE" and status["remaining_seconds"] == 0
    assert holder.current() is None and not holder.validate_peer(peer) and holder.delegation_keys() == {}
    assert "state=UNAVAILABLE previous=READY" in caplog.text
    with pytest.raises(ServiceAuthError):
        verify_token(auth.verifier, token(pair.bp_key, kid_of(pair), int(cloud.now.timestamp())))
    with pytest.raises(ServiceAuthError):
        _ = auth.audience


def test_peer_validation_checks_chain_revocation_usage_and_trust_domain(cloud) -> None:
    pair = fx.build_pair(cloud)
    holder = CredentialHolder.static(accept(pair), now=lambda: cloud.now)
    der = serialization.Encoding.DER
    assert holder.validate_peer(pair.bp_leaf.public_bytes(der))
    other = fx.new_cloud(cloud.now)
    assert not holder.validate_peer(other.issue(fx.BP_URI, [fx.CLIENT])[1].public_bytes(der))
    assert not holder.validate_peer(cloud.issue(fx.BP_URI, [fx.SERVER])[1].public_bytes(der))
    assert not holder.validate_peer(
        cloud.issue("spiffe://elsewhere/workload/business-platform", [fx.CLIENT])[1].public_bytes(der)
    )
    revoked_pair = fx.build_pair(cloud, revoked_serials=[pair.bp_leaf.serial_number])
    revoked_holder = CredentialHolder.static(accept(revoked_pair), now=lambda: cloud.now)
    assert not revoked_holder.validate_peer(pair.bp_leaf.public_bytes(der))
    assert not holder.validate_peer(b"not a certificate")


@pytest.mark.parametrize("url", ["https://kv-waooaw-demo.vault.azure.net", "https://kv-waooaw-demo.vault.azure.net/"])
def test_vault_url_accepts_only_https_azure_vault_hosts(url) -> None:
    assert parse_vault_url(url) == "https://kv-waooaw-demo.vault.azure.net"


@pytest.mark.parametrize(
    "url",
    [
        "http://kv.vault.azure.net",
        "https://kv.vault.azure.net.evil.example",
        "https://evil.example/kv.vault.azure.net",
        "https://user@kv.vault.azure.net",
        "https://.vault.azure.net",
        "https://kv.vault.azure.net:8443",
        "",
        "kv.vault.azure.net",
        "https://kv.vault.azure.net/secrets",
    ],
)
def test_vault_url_rejects_everything_else(url) -> None:
    with pytest.raises(ValueError, match="Key Vault"):
        parse_vault_url(url)


def test_key_vault_reader_uses_the_managed_identity_token_and_rest_api_7_4() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "localhost":
            return httpx.Response(200, json={"access_token": "t0ken", "expires_on": "4102444800"})
        return httpx.Response(200, json={"value": "payload"})

    environ = {"IDENTITY_ENDPOINT": "http://localhost:42356/msi/token", "IDENTITY_HEADER": "hdr"}
    reader = KeyVaultReader(
        "https://kv-waooaw-demo.vault.azure.net", "client-1", environ, httpx.MockTransport(handle), now=lambda: 1.0
    )
    assert reader.get_secret("wid-trust-bundle") == "payload"
    assert reader.get_secret("wid-bundle-billing-engine") == "payload"
    identity, vault, _ = seen[0], seen[1], seen[2]
    assert len(seen) == 3
    assert identity.headers["X-IDENTITY-HEADER"] == "hdr"
    assert dict(identity.url.params) == {
        "api-version": "2019-08-01",
        "resource": "https://vault.azure.net",
        "client_id": "client-1",
    }
    assert str(vault.url) == "https://kv-waooaw-demo.vault.azure.net/secrets/wid-trust-bundle?api-version=7.4"
    assert vault.headers["Authorization"] == "Bearer t0ken"
    bad = KeyVaultReader(
        "https://kv.vault.azure.net",
        "",
        {"IDENTITY_ENDPOINT": "http://10.0.0.4/msi", "IDENTITY_HEADER": "h"},
        httpx.MockTransport(handle),
    )
    with pytest.raises(ValueError, match="loopback"):
        bad.get_secret("wid-trust-bundle")


def test_keyvault_environment_never_crashes_and_reports_the_reason(monkeypatch) -> None:
    runtime = build_keyvault_runtime(
        {
            "WAOOAW_WID_VAULT_URL": "http://evil.example",
            "WAOOAW_WID_TRUST_DOMAIN": fx.TRUST_DOMAIN,
            "WAOOAW_WID_WORKLOAD": "billing-engine",
        }
    )
    assert runtime.refresher is None
    assert runtime.holder.status()["state"] == "UNAVAILABLE" and runtime.holder.status()["reason"] == "CONFIG_INVALID"
    valid = build_keyvault_runtime(
        {
            "WAOOAW_WID_VAULT_URL": "https://kv.vault.azure.net",
            "WAOOAW_WID_TRUST_DOMAIN": fx.TRUST_DOMAIN,
            "WAOOAW_WID_WORKLOAD": "billing-engine",
            "WAOOAW_WID_REFRESH_SECONDS": "5",
        }
    )
    assert valid.refresher is not None and valid.refresher._interval == 30

    monkeypatch.setenv("WAOOAW_WID_SOURCE", "keyvault")
    monkeypatch.delenv("WAOOAW_WID_VAULT_URL", raising=False)
    reset_keyvault_runtime()
    try:
        application = FastAPI()
        configure_relationship_workspace(application)
        assert application.state.relationship_workload_auth.holder is application.state.credential_runtime.holder
        assert application.state.credential_runtime.holder.status()["reason"] == "CONFIG_INVALID"
    finally:
        reset_keyvault_runtime()


def test_health_reports_credential_state_and_lifespan_starts_the_refresher(monkeypatch, cloud) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi.testclient import TestClient

    import main

    started = threading.Event()
    pair = fx.build_pair(cloud)
    holder = CredentialHolder("keyvault", now=lambda: cloud.now)
    refresher = CredentialRefresher(holder, lambda: pair.texts, EXPECT, now=lambda: cloud.now)

    async def run() -> None:
        started.set()
        await asyncio.sleep(3600)

    refresher.run = run
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "keyvault")
    reset_keyvault_runtime()
    application = main.create_app()
    application.state.credential_runtime = SimpleNamespace(holder=holder, refresher=refresher)
    application.state.relationship_workload_auth = auth_from_holder(holder, fx.TRUST_DOMAIN)
    assert TestClient(application).get("/health").json()["credential"]["state"] == "UNAVAILABLE"
    refresher.refresh_once()
    scheduler = MagicMock()
    with (
        patch("main.init_db", AsyncMock()),
        patch("main.close_db", AsyncMock()),
        patch("main.get_session_factory", return_value=MagicMock()),
        patch("main.create_scheduler", return_value=scheduler),
        patch("main.aioredis.from_url", return_value=AsyncMock()),
        TestClient(application) as client,
    ):
        body = client.get("/health").json()
        assert started.wait(5)
    reset_keyvault_runtime()
    assert body["status"] == "ok" and body["credential"]["state"] == "READY"
    assert set(body["credential"]) == {"source", "state", "serial_digest", "not_after", "remaining_seconds", "bundle_version"}
    assert "BEGIN" not in json.dumps(body)


def _probe_request(auth, peer: x509.Certificate | None):
    state = {PEER_CERTIFICATE_STATE_KEY: peer.public_bytes(serialization.Encoding.DER)} if peer is not None else {}
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(relationship_workload_auth=auth)), scope={"state": state})


def test_link_probe_answers_only_a_granted_authenticated_peer(cloud, caplog) -> None:
    pair = fx.build_pair(cloud)
    holder = CredentialHolder.static(accept(pair), now=lambda: cloud.now)
    auth = auth_from_holder(holder, fx.TRUST_DOMAIN)
    caplog.set_level(logging.INFO)
    answer = asyncio.run(probe_service_link(_probe_request(auth, pair.bp_leaf)))
    assert answer["status"] == "ok" and answer["peer_identity_uri"] == fx.BP_URI and answer["bundle_version"] == 100
    assert 0 < answer["remaining_seconds"] <= 86400
    assert "service_auth decision=allow target=billing-engine operation=probeServiceLink" in caplog.text
    ungranted = cloud.issue(f"spiffe://{fx.TRUST_DOMAIN}/workload/professional-runtime", [fx.CLIENT])[1]
    for request in (_probe_request(auth, ungranted), _probe_request(auth, None), _probe_request(None, pair.bp_leaf)):
        with pytest.raises(HTTPException) as denied:
            asyncio.run(probe_service_link(request))
        assert denied.value.status_code == 401


def _serve(context: ssl.SSLContext, outcomes: list) -> tuple[socket.socket, threading.Thread]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(4)

    def accept_loop() -> None:
        while True:
            try:
                connection, _ = listener.accept()
            except OSError:
                return
            try:
                with context.wrap_socket(connection, server_side=True) as secured:
                    outcomes.append(secured.getpeercert(binary_form=True))
                    secured.sendall(b"ok")
            except (ssl.SSLError, OSError) as error:
                outcomes.append(error)

    thread = threading.Thread(target=accept_loop, daemon=True)
    thread.start()
    return listener, thread


def _connect(port: int, pair: fx.Pair, folder: Path, sni: bool = True) -> bytes:
    cert, key = folder / "client.pem", folder / "client-key.pem"
    cert.write_text(fx._pem(pair.bp_leaf, pair.cloud.intermediate))
    key.write_text(fx._key_pem(pair.bp_leaf_key))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.load_verify_locations(cadata=fx._pem(pair.cloud.root))
    context.load_cert_chain(cert, key)
    with (
        socket.create_connection(("127.0.0.1", port), timeout=5) as raw,
        context.wrap_socket(raw, server_hostname="billing-engine.internal" if sni else None) as secured,
    ):
        server_certificate = secured.getpeercert(binary_form=True)
        assert secured.recv(2) == b"ok"
        return server_certificate


def test_listener_reloads_its_chain_in_the_same_context_and_fails_closed(cloud, tmp_path) -> None:
    first = fx.build_pair(cloud, 100, 100)
    second = fx.build_pair(cloud, 101, 101)
    second.cloud = cloud
    shm = tmp_path / "shm"
    shm.mkdir()
    clock = {"now": cloud.now}
    holder = CredentialHolder("keyvault", now=lambda: clock["now"])
    texts = {"value": first.texts}
    refresher = CredentialRefresher(holder, lambda: texts["value"], EXPECT, now=lambda: cloud.now)
    refresher.refresh_once()
    tls = WorkloadTlsContext(holder, shm)
    context = tls.context
    assert tls.reload() and not tls.reload()
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2 and context.verify_mode == ssl.CERT_REQUIRED
    outcomes: list = []
    listener, _ = _serve(context, outcomes)
    port = listener.getsockname()[1]
    try:
        assert _connect(port, first, tmp_path) == first.leaf.public_bytes(serialization.Encoding.DER)
        texts["value"] = second.texts
        assert refresher.refresh_once() == "ACCEPTED" and tls.reload() and tls.context is context
        assert _connect(port, first, tmp_path) == second.leaf.public_bytes(serialization.Encoding.DER)
        assert list(shm.iterdir()) == []
        clock["now"] = second.leaf.not_valid_after_utc + timedelta(seconds=1)
        with pytest.raises((ssl.SSLError, OSError)):
            _connect(port, first, tmp_path)
    finally:
        listener.close()
    assert isinstance(outcomes[-1], ssl.SSLError)


def test_listener_refuses_to_write_keys_outside_a_tmpfs_directory(cloud, tmp_path) -> None:
    holder = CredentialHolder.static(accept(fx.build_pair(cloud)), now=lambda: cloud.now)
    with pytest.raises(RuntimeError, match="tmpfs"):
        WorkloadTlsContext(holder, tmp_path / "missing").reload()


def test_peer_is_revalidated_per_connection_and_per_request(monkeypatch) -> None:
    class Transport:
        closed = False

        def get_extra_info(self, _name: str):
            return SimpleNamespace(getpeercert=lambda binary_form: b"peer")

        def close(self) -> None:
            self.closed = True

    verdict = {"valid": False}
    protocol = validated_protocol(lambda _der: verdict["valid"])
    refused = Transport()
    protocol.__new__(protocol).connection_made(refused)
    assert refused.closed

    monkeypatch.setattr(H11Protocol, "connection_made", lambda self, transport: None)
    seen: list[dict] = []

    async def application(scope, receive, send) -> None:
        seen.append(dict(scope.get("state", {})))

    verdict["valid"] = True
    instance = protocol.__new__(protocol)
    instance.app = application
    instance.connection_made(Transport())
    asyncio.run(instance.app({"type": "http"}, None, None))
    verdict["valid"] = False
    asyncio.run(instance.app({"type": "http"}, None, None))
    assert seen == [{PEER_CERTIFICATE_STATE_KEY: b"peer"}, {}]
    assert MutualTlsH11Protocol.peer_validator is None


def test_first_snapshot_is_awaited_with_retries(cloud) -> None:
    holder = CredentialHolder("keyvault", now=lambda: cloud.now)
    attempts: list[int] = []
    sleeps: list[float] = []

    def refresh() -> str:
        attempts.append(1)
        if len(attempts) == 3:
            holder.install(accept(fx.build_pair(cloud)))
        return "x"

    await_first_snapshot(refresh, holder, sleeps.append)
    assert len(attempts) == 3 and sleeps == [30, 30]


class FakeChild:
    def __init__(self, code: int | None = None) -> None:
        self.code = code
        self.signals: list[int] = []
        self.terminated = False

    def poll(self) -> int | None:
        return self.code

    def terminate(self) -> None:
        self.terminated = True
        self.code = -15

    def kill(self) -> None:
        self.code = -9

    def send_signal(self, signum: int) -> None:
        self.signals.append(signum)
        self.code = 0


def test_supervisor_exits_non_zero_and_stops_the_other_child_when_one_dies() -> None:
    survivor, dead = FakeChild(), FakeChild(3)
    children = [survivor, dead]
    exit_code = entrypoint.Supervisor([["a"], ["b"]], spawn=lambda _command: children.pop(0), sleep=lambda _seconds: None).run()
    assert exit_code == 3
    assert survivor.terminated
    clean_exit = [FakeChild(), FakeChild(0)]
    clean_code = entrypoint.Supervisor([["a"], ["b"]], spawn=lambda _command: clean_exit.pop(0), sleep=lambda _seconds: None).run()
    assert clean_code == 1


def test_supervisor_forwards_sigterm_and_exits_cleanly() -> None:
    children = [FakeChild(), FakeChild()]
    spawned = list(children)
    supervisor = entrypoint.Supervisor([["a"], ["b"]], spawn=lambda _command: spawned.pop(0), sleep=lambda _seconds: None)
    supervisor._sleep = lambda _seconds: supervisor.forward(15)
    assert supervisor.run() == 0
    assert [child.signals for child in children] == [[15], [15]]


def test_private_listener_is_supervised_only_for_cloud_delivery() -> None:
    assert len(entrypoint.child_commands({})) == 1
    assert len(entrypoint.child_commands({"WAOOAW_WID_SOURCE": "directory"})) == 1
    assert entrypoint.child_commands({"WAOOAW_WID_SOURCE": "keyvault"})[1][-1] == "private_server.py"
    assert len(entrypoint.child_commands({"WBE_PRIVATE_LISTENER": "1"})) == 2
    assert entrypoint.child_commands({})[0][-5:] == ["main:app", "--host", "0.0.0.0", "--port", "8140"]


class TestDirectoryMode:
    @pytest.fixture
    def bootstrapped(self, tmp_path: Path) -> Path:
        import bootstrap_workload_identity

        registry = Path(__file__).parents[2] / "infrastructure" / "workload-identity" / "registry.yaml"
        bootstrap_workload_identity.bootstrap(registry, "ci", tmp_path / "wid")
        return tmp_path / "wid"

    def _signer(self, credentials: Path):
        manifest = json.loads((credentials / "manifest.json").read_text())
        key = serialization.load_pem_private_key(
            (credentials / "workloads" / "business-platform" / "delegation-key.pem").read_bytes(), None
        )
        return key, manifest["workloads"]["business-platform"]

    def _verify(self, auth: WorkloadAuth, key, signer: dict, envelope_id: str) -> DelegatedContext:
        now = int(time.time())
        return auth.verifier.verify(
            token(key, signer["delegation_key_id"], now, envelope_id, issuer_uri=signer["identity_uri"]),
            signer["identity_uri"],
            auth.audience,
            "GET",
            fx.PROJECTION_ROUTE,
            OPERATION,
            1,
            DIGEST,
            lambda _context: True,
        )

    def test_bootstrap_output_is_accepted_with_chain_validity_and_oid_checks(self, bootstrapped) -> None:
        auth = WorkloadAuth.from_credentials(bootstrapped)
        key, signer = self._signer(bootstrapped)
        assert self._verify(auth, key, signer, "dir-1").envelope_id == "dir-1"
        assert auth.holder.status()["source"] == "directory" and auth.holder.status()["state"] == "READY"

    def test_delegation_certificate_from_another_root_is_refused(self, bootstrapped, tmp_path) -> None:
        import bootstrap_workload_identity

        registry = Path(__file__).parents[2] / "infrastructure" / "workload-identity" / "registry.yaml"
        bootstrap_workload_identity.bootstrap(registry, "ci", tmp_path / "other")
        other_key, _ = self._signer(tmp_path / "other")
        (bootstrapped / "workloads" / "business-platform" / "delegation-cert.pem").write_bytes(
            (tmp_path / "other" / "workloads" / "business-platform" / "delegation-cert.pem").read_bytes()
        )
        auth = WorkloadAuth.from_credentials(bootstrapped)
        _, signer = self._signer(bootstrapped)
        with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
            self._verify(auth, other_key, signer, "dir-2")

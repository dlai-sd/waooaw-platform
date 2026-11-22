# Implements: ADR-046 Amendment 1 (IB-147) Professional Runtime side of workload credential delivery
# constitutional_basis: C-026, C-059, C-063, C-076, C-083, C-084, C-085

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

import entrypoint
import private_server
import wid_pr_cloud_fixture as fx
import runtime_workload_credentials as wc
from mtls_protocol import MutualTlsH11Protocol
from professional_runtime_main import app as runtime_app
from professional_runtime_main import lifespan
from relationship_workspace import probe_service_link
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
    sign_delegated_context,
)

TARGET = "professional-runtime"
# Billing and Professional Runtime each define a module named relationship_workspace; loading the class by name
# keeps static analysis from resolving it against the other service's module.
WorkloadAuth = importlib.import_module("relationship_workspace").WorkloadAuth
DIGEST = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DER = serialization.Encoding.DER


def auth_from_holder(holder):
    return WorkloadAuth.from_holder(holder)


@pytest.fixture
def cloud() -> fx.Cloud:
    return fx.new_cloud()


@pytest.fixture(autouse=True)
def _clean_shared_holder():
    register_holder(None)
    yield
    register_holder(None)


def accept(pair: fx.Pair, environment: str | None = "demo", trust_domain: str = fx.TRUST_DOMAIN):
    trust = verify_trust_bundle(pair.texts[0], trust_domain, environment, pair.cloud.now)
    return build_snapshot(trust, pair.texts[1], TARGET, pair.cloud.now)


def reason_of(pair: fx.Pair, **changes) -> str:
    with pytest.raises(CredentialError) as raised:
        accept(pair, **changes)
    return raised.value.code


def resigned(pair: fx.Pair, **changes) -> fx.Pair:
    document = {name: value for name, value in pair.trust.items() if name != "signature"} | changes
    pair.trust = fx.sign(document, pair.cloud.intermediate_key)
    return pair


def secrets(pair: fx.Pair) -> dict[str, str]:
    return {wc.TRUST_BUNDLE_SECRET: pair.texts[0], f"wid-bundle-{TARGET}": pair.texts[1]}


class FakeReader:
    """Stand-in for KeyVaultSecretReader; a value that is an Exception is raised instead of returned."""

    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get_secret(self, name: str) -> str:
        value = self.values[name]
        if isinstance(value, Exception):
            raise value
        assert isinstance(value, str)
        return value


def keyvault_holder(cloud: fx.Cloud, values: dict[str, object], clock=None, **options) -> CredentialHolder:
    clock = clock or (lambda: cloud.now)
    return CredentialHolder(
        wc.SOURCE_KEYVAULT, TARGET, fx.TRUST_DOMAIN, environment="demo", reader=FakeReader(values), clock=clock, **options
    )


def envelope(key, key_id: str, now: int, envelope_id: str = "envelope-1", **changes) -> str:
    values = {
        "schema_version": "1.0",
        "key_id": key_id,
        "issuer_uri": fx.BP_URI,
        "target_audience": fx.PR_AUDIENCE,
        "method": "GET",
        "route": fx.PROJECTION_ROUTE,
        "operation": fx.PROJECTION_OPERATION,
        "contract_major": 1,
        "actor_subject": "actor",
        "actor_source": "BP_SESSION",
        "effective_role": "EMPLOYER",
        "tenant_id": "tenant-a",
        "relationship_id": "relationship-a",
        "purpose": fx.PROJECTION_OPERATION,
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
    return sign_delegated_context(DelegatedContext(**values), key)


def verify_envelope(verifier: DelegatedContextVerifier, signed: str) -> DelegatedContext:
    return verifier.verify(
        signed,
        fx.BP_URI,
        fx.PR_AUDIENCE,
        "GET",
        fx.PROJECTION_ROUTE,
        fx.PROJECTION_OPERATION,
        1,
        DIGEST,
        lambda _context: True,
    )


def kid_of(pair: fx.Pair) -> str:
    return pair.trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"][0]["key_id"]


def test_valid_bundle_builds_a_snapshot(cloud) -> None:
    pair = fx.build_pair(cloud)
    snapshot = accept(pair)
    assert snapshot.source == wc.SOURCE_KEYVAULT and snapshot.workload == TARGET
    assert snapshot.identity_uri == fx.PR_URI and snapshot.audience == fx.PR_AUDIENCE
    assert snapshot.bundle_version == 100 and snapshot.workload_bundle_version == 100 and len(snapshot.serial_digest) == 16
    assert snapshot.serial == pair.leaf.serial_number and snapshot.not_after == pair.leaf.not_valid_after_utc
    assert (fx.BP_URI, kid_of(pair)) in snapshot.delegation_keys
    assert {grant.operation for grant in snapshot.grants} == {"probeServiceLink", fx.PROJECTION_OPERATION}
    assert snapshot.tls_key_pem.startswith(b"-----BEGIN PRIVATE KEY") and snapshot.tls_chain_pem.count("BEGIN CERTIFICATE") == 2
    assert snapshot.delegation_key_pem is None and snapshot.delegation_key_id is None


@pytest.mark.parametrize(
    ("reason", "options"),
    [
        ("ENVIRONMENT_MISMATCH", {"bundle_environment": "uat"}),
        ("ENVIRONMENT_MISMATCH", {"trust_environment": "uat", "bundle_environment": "uat"}),
        ("TRUST_DOMAIN_MISMATCH", {"trust_domain": "other.waooaw.internal"}),
        ("LEAF_VALIDITY_INVALID", {"leaf_start": timedelta(hours=-30), "leaf_lifetime": timedelta(hours=24)}),
        ("LEAF_VALIDITY_INVALID", {"leaf_start": timedelta(minutes=10)}),
        ("LEAF_IDENTITY_MISMATCH", {"leaf_uri": fx.BP_URI}),
        ("LEAF_USAGE_INVALID", {"usages": [fx.SERVER]}),
        ("LEAF_USAGE_INVALID", {"usages": [fx.CLIENT]}),
        ("LEAF_KEY_MISMATCH", {"key_mismatch": True}),
        ("LEAF_REVOKED", {"revoke_leaf": True}),
        ("LEAF_REVOKED", {"revoked_uris": [fx.PR_URI]}),
        ("DELEGATION_USAGE_INVALID", {"delegation": {"usages": [fx.CLIENT]}}),
        ("DELEGATION_IDENTITY_MISMATCH", {"delegation": {"uri": fx.PR_URI}}),
    ],
)
def test_bundle_that_bends_a_rule_is_rejected(cloud, reason, options) -> None:
    assert reason_of(fx.build_pair(cloud, **options)) == reason


def test_leaf_inside_the_clock_skew_window_is_accepted(cloud) -> None:
    assert accept(fx.build_pair(cloud, leaf_start=timedelta(seconds=30))).identity_uri == fx.PR_URI


def test_expected_trust_domain_and_environment_are_exact(cloud) -> None:
    pair = fx.build_pair(cloud)
    assert reason_of(pair, trust_domain="uat.waooaw.internal") == "TRUST_DOMAIN_MISMATCH"
    assert reason_of(pair, environment="uat") == "ENVIRONMENT_MISMATCH"
    assert accept(pair, environment=None).environment == "demo"


def test_bundle_for_another_workload_or_identity_is_rejected(cloud) -> None:
    pair = fx.build_pair(cloud)
    pair.bundle["workload"] = "billing-engine"
    assert reason_of(pair) == "ENVIRONMENT_MISMATCH"
    pair = fx.build_pair(cloud)
    pair.bundle["identity_uri"] = fx.BP_URI
    assert reason_of(pair) == "LEAF_IDENTITY_MISMATCH"


def test_tampered_foreign_signed_and_foreign_chain_trust_bundles_are_rejected(cloud) -> None:
    pair = fx.build_pair(cloud)
    pair.trust["bundle_version"] = 101
    assert reason_of(pair) == "TRUST_BUNDLE_SIGNATURE_INVALID"
    pair = fx.build_pair(cloud)
    pair.trust["signature"] = "not base64!"
    assert reason_of(pair) == "TRUST_BUNDLE_SIGNATURE_INVALID"
    foreign = fx.build_pair(cloud)
    foreign.trust = cloud.trust_bundle(100, [], signing_key=ec.generate_private_key(ec.SECP256R1()))
    assert reason_of(foreign) == "TRUST_BUNDLE_SIGNATURE_INVALID"
    other = fx.new_cloud(cloud.now)
    swapped = resigned(fx.build_pair(cloud), intermediate_pem=fx.pem(other.intermediate))
    swapped.trust = fx.sign({k: v for k, v in swapped.trust.items() if k != "signature"}, other.intermediate_key)
    assert reason_of(swapped) == "TRUST_BUNDLE_CHAIN_INVALID"


@pytest.mark.parametrize(
    "document",
    ["UNISSUED", "  UNISSUED\n", "not json at all", "{", "[]", "{}", '{"environment": "demo"}'],
)
def test_unissued_or_malformed_documents_mean_no_credential(cloud, document) -> None:
    pair = fx.build_pair(cloud)
    with pytest.raises(CredentialError) as trust_error:
        verify_trust_bundle(document, fx.TRUST_DOMAIN, "demo", cloud.now)
    assert trust_error.value.code == "UNISSUED"
    trust = verify_trust_bundle(pair.texts[0], fx.TRUST_DOMAIN, "demo", cloud.now)
    with pytest.raises(CredentialError) as bundle_error:
        build_snapshot(trust, document, TARGET, cloud.now)
    assert bundle_error.value.code == "UNISSUED"


@pytest.mark.parametrize(
    ("reason", "changes"),
    [
        ("SCHEMA_INVALID", {"schema_version": "9.9"}),
        ("SCHEMA_INVALID", {"bundle_version": -1}),
        ("SCHEMA_INVALID", {"bundle_version": True}),
        ("SCHEMA_INVALID", {"root_pem": "garbage"}),
        ("SCHEMA_INVALID", {"ca_bundle_pem": ""}),
        ("SCHEMA_INVALID", {"revoked_serials": ["x"]}),
        ("SCHEMA_INVALID", {"revoked_serials": "1"}),
        ("SCHEMA_INVALID", {"revoked_identity_uris": [1]}),
    ],
)
def test_malformed_trust_bundle_fields_are_schema_errors(cloud, reason, changes) -> None:
    assert reason_of(resigned(fx.build_pair(cloud), **changes)) == reason


def test_root_and_intermediate_must_be_single_certificates(cloud) -> None:
    pair = resigned(fx.build_pair(cloud), root_pem=fx.pem(cloud.root, cloud.intermediate))
    assert reason_of(pair) == "SCHEMA_INVALID"
    pair = resigned(fx.build_pair(cloud), root_pem=fx.pem(cloud.intermediate))
    assert reason_of(pair) == "TRUST_BUNDLE_CHAIN_INVALID"


@pytest.mark.parametrize(
    ("reason", "mutate"),
    [
        ("ENVIRONMENT_MISMATCH", lambda m: {**m, "environment": "uat"}),
        ("MANIFEST_INVALID", lambda m: {**m, "route_grants": "nope"}),
        ("MANIFEST_INVALID", lambda m: {**m, "route_grants": [{"caller": "business-platform", "target": TARGET}]}),
        (
            "MANIFEST_INVALID",
            lambda m: {
                **m,
                "workloads": {**m["workloads"], TARGET: {"identity_uri": "spiffe://evil/workload/x", "audience": "a"}},
            },
        ),
        (
            "MANIFEST_INVALID",
            lambda m: {
                **m,
                "workloads": {
                    **m["workloads"],
                    "business-platform": {**m["workloads"]["business-platform"], "delegation_certificates": "x"},
                },
            },
        ),
        ("SCHEMA_INVALID", lambda m: {**m, "workloads": {k: v for k, v in m["workloads"].items() if k != TARGET}}),
    ],
)
def test_manifest_defects_are_rejected(cloud, reason, mutate) -> None:
    pair = fx.build_pair(cloud)
    assert reason_of(resigned(pair, manifest=mutate(pair.trust["manifest"]))) == reason


def test_leaf_and_delegation_from_another_root_are_rejected(cloud) -> None:
    other = fx.new_cloud(cloud.now)
    pair = fx.build_pair(cloud)
    _, foreign_leaf = other.issue(fx.PR_URI, [fx.SERVER, fx.CLIENT])
    pair.bundle["tls_cert_pem"] = fx.pem(foreign_leaf, cloud.intermediate)
    assert reason_of(pair) == "LEAF_CHAIN_INVALID"
    assert reason_of(fx.build_pair(cloud, delegation={"issuer": other})) == "DELEGATION_CHAIN_INVALID"


def test_revoked_and_stale_delegation_certificates_are_excluded_not_fatal(cloud) -> None:
    _, _stale, stale_entry = cloud.delegation(start=timedelta(hours=-30), lifetime=timedelta(hours=24))
    _, revoked, revoked_entry = cloud.delegation()
    pair = fx.build_pair(cloud, extra_delegations=[stale_entry, revoked_entry], revoked_serials=[revoked.serial_number])
    keys = accept(pair).delegation_keys
    assert (fx.BP_URI, kid_of(pair)) in keys and (fx.BP_URI, revoked_entry["key_id"]) not in keys
    assert (fx.BP_URI, stale_entry["key_id"]) not in keys
    assert not accept(fx.build_pair(cloud, revoked_uris=[fx.BP_URI])).delegation_keys


def test_signed_ca_bundle_extends_the_anchors_with_valid_authorities_only(cloud) -> None:
    other = fx.new_cloud(cloud.now)
    expired = fx.Cloud(cloud.now - timedelta(days=90))
    pair = fx.build_pair(cloud)
    resigned(pair, ca_bundle_pem=fx.pem(cloud.root, cloud.intermediate, other.root, other.intermediate, expired.root))
    anchors = accept(pair).anchors
    assert len(anchors.roots) == 2 and len(anchors.intermediates) == 2


def test_delegation_signing_material_is_verified_and_kept_secret(cloud) -> None:
    pair = fx.build_pair(cloud)
    key, certificate, _ = cloud.delegation(uri=fx.PR_URI, activate_after=timedelta(minutes=5))
    signing = {
        "delegation_key_pem": fx.key_pem(key),
        "delegation_cert_pem": fx.pem(certificate),
        "delegation_key_id": fx.key_id(key),
        "delegation_activate_after": (cloud.now + timedelta(minutes=5)).isoformat(),
    }
    pair.bundle.update(signing)
    snapshot = accept(pair)
    assert snapshot.delegation_key_id == fx.key_id(key) and snapshot.delegation_key_pem == signing["delegation_key_pem"].encode()
    assert snapshot.delegation_activate_after == int((cloud.now + timedelta(minutes=5)).timestamp())
    assert "PRIVATE KEY" not in repr(snapshot) and signing["delegation_cert_pem"] not in repr(snapshot)

    pair.bundle["delegation_key_pem"] = fx.key_pem(ec.generate_private_key(ec.SECP256R1()))
    assert reason_of(pair) == "DELEGATION_KEY_MISMATCH"
    pair.bundle["delegation_key_pem"] = garbage_pem("bm90IGEga2V5")
    assert reason_of(pair) == "DELEGATION_KEY_MISMATCH"
    pair.bundle["delegation_key_pem"] = signing["delegation_key_pem"]
    pair.bundle["delegation_cert_pem"] = fx.pem(cloud.issue(fx.BP_URI, [fx.DELEGATION_OID])[1])
    assert reason_of(pair) == "DELEGATION_IDENTITY_MISMATCH"
    del pair.bundle["delegation_key_id"]
    assert reason_of(pair) == "SCHEMA_INVALID"


def garbage_pem(body: str) -> str:
    # Assembled at run time so the repository holds no private-key-shaped literal for secret scanners.
    label = "PRIVATE" + " KEY"
    return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----\n"


def test_garbage_private_key_is_a_mismatch_and_never_echoed(cloud, caplog) -> None:
    pair = fx.build_pair(cloud)
    pair.bundle["tls_key_pem"] = garbage_pem("c2VjcmV0LXRva2Vu")
    caplog.set_level(logging.INFO)
    holder = keyvault_holder(cloud, secrets(pair))
    assert holder.refresh_once() is False and holder.status()["lastReason"] == "LEAF_KEY_MISMATCH"
    assert "c2VjcmV0LXRva2Vu" not in caplog.text + json.dumps(holder.status())


def test_refresh_installs_a_snapshot_and_reports_it(cloud, caplog) -> None:
    pair = fx.build_pair(cloud)
    holder = keyvault_holder(cloud, secrets(pair))
    assert holder.state() == wc.STATE_UNISSUED and holder.current() is None and holder.remaining_seconds() == 0
    assert holder.anchors() is None and holder.grants() == frozenset() and holder.audience() is None
    caplog.set_level(logging.INFO)
    assert holder.refresh_once() is True
    status = holder.status()
    assert status["state"] == wc.STATE_READY and status["bundleVersion"] == 100 and status["lastReason"] is None
    assert status["source"] == wc.SOURCE_KEYVAULT and status["serialDigest"] == holder.current().serial_digest
    assert 0 < status["remainingSeconds"] <= 86400 and status["notAfter"] == pair.leaf.not_valid_after_utc.isoformat()
    assert holder.audience() == fx.PR_AUDIENCE and holder.anchors() is not None and holder.grants()
    assert (fx.BP_URI, kid_of(pair)) in holder.delegation_keys()
    assert "workload_credential swapped" in caplog.text and "state_transition from=None to=READY" in caplog.text
    caplog.clear()
    assert holder.refresh_once() is True
    assert "swapped" not in caplog.text


def test_refresh_keeps_last_good_credentials_on_every_failure_and_never_logs_secrets(cloud, caplog) -> None:
    good = fx.build_pair(cloud, 100, 100)
    values = secrets(good)
    holder = keyvault_holder(cloud, values)
    caplog.set_level(logging.INFO)
    assert holder.refresh_once() is True
    installed = holder.current()
    tampered = fx.build_pair(cloud, 101, 101)
    tampered.trust["bundle_version"] = 102
    failures = {
        "TRUST_BUNDLE_SIGNATURE_INVALID": secrets(tampered),
        "BUNDLE_VERSION_ROLLBACK": secrets(fx.build_pair(cloud, 99, 99)),
        "UNISSUED": {wc.TRUST_BUNDLE_SECRET: "UNISSUED", f"wid-bundle-{TARGET}": "UNISSUED"},
        "VAULT_UNAVAILABLE": {wc.TRUST_BUNDLE_SECRET: CredentialError("VAULT_UNAVAILABLE"), f"wid-bundle-{TARGET}": ""},
        "SECRET_NOT_FOUND": {wc.TRUST_BUNDLE_SECRET: good.texts[0], f"wid-bundle-{TARGET}": CredentialError("SECRET_NOT_FOUND")},
        "REFRESH_FAILED": {wc.TRUST_BUNDLE_SECRET: RuntimeError("PRIVATE KEY leaked"), f"wid-bundle-{TARGET}": ""},
        "LEAF_REVOKED": secrets(fx.build_pair(cloud, 101, 101, revoke_leaf=True)),
        "ENVIRONMENT_MISMATCH": secrets(fx.build_pair(cloud, 101, 101, bundle_environment="uat")),
    }
    for reason, replacement in failures.items():
        values.clear()
        values.update(replacement)
        assert holder.refresh_once() is False, reason
        assert holder.current() is installed and holder.state() == wc.STATE_READY
        assert holder.status()["lastReason"] == reason and holder.status()["bundleVersion"] == 100
    assert "refresh_rejected source=keyvault reason=BUNDLE_VERSION_ROLLBACK" in caplog.text
    assert "BEGIN" not in caplog.text and "leaked" not in caplog.text
    values.clear()
    values.update(secrets(fx.build_pair(cloud, 101, 101)))
    assert holder.refresh_once() is True and holder.current() is not installed and holder.status()["lastReason"] is None


def test_bundle_versions_never_go_backwards(cloud) -> None:
    holder = keyvault_holder(cloud, secrets(fx.build_pair(cloud, 101, 101)))
    values = holder._reader.values
    assert holder.refresh_once() is True
    for trust_version, own_version in ((100, 101), (101, 100), (100, 100)):
        values.update(secrets(fx.build_pair(cloud, trust_version, own_version)))
        assert holder.refresh_once() is False and holder.status()["lastReason"] == "BUNDLE_VERSION_ROLLBACK"
        assert holder.status()["bundleVersion"] == 101
    values.update(secrets(fx.build_pair(cloud, 102, 101)))
    assert holder.refresh_once() is True and holder.status()["bundleVersion"] == 102
    values.update(secrets(fx.build_pair(cloud, 102, 102)))
    assert holder.refresh_once() is True and holder.current().workload_bundle_version == 102


def test_unissued_credentials_report_unissued_then_recover(cloud) -> None:
    values = {wc.TRUST_BUNDLE_SECRET: "UNISSUED", f"wid-bundle-{TARGET}": "UNISSUED"}
    holder = keyvault_holder(cloud, values)
    assert holder.refresh_once() is False and holder.state() == wc.STATE_UNISSUED and holder.status()["lastReason"] == "UNISSUED"
    values.update(secrets(fx.build_pair(cloud)))
    assert holder.refresh_once() is True and holder.state() == wc.STATE_READY


def test_first_rejection_is_unavailable_not_unissued(cloud) -> None:
    holder = keyvault_holder(cloud, secrets(fx.build_pair(cloud, usages=[fx.SERVER])))
    assert holder.refresh_once() is False and holder.state() == wc.STATE_UNAVAILABLE
    assert holder.status()["lastReason"] == "LEAF_USAGE_INVALID" and holder.status()["serialDigest"] is None


def test_subscribers_see_every_swap_and_cannot_break_it(cloud, caplog) -> None:
    values = secrets(fx.build_pair(cloud, 100, 100))
    holder = keyvault_holder(cloud, values)
    seen: list[int] = []

    def failing(_snapshot) -> None:
        raise RuntimeError("subscriber boom")

    holder.refresh_once()
    holder.subscribe(lambda snapshot: seen.append(snapshot.bundle_version))
    holder.subscribe(lambda snapshot: failing(snapshot) if snapshot.bundle_version > 100 else None)
    caplog.set_level(logging.WARNING)
    values.update(secrets(fx.build_pair(cloud, 101, 101)))
    assert holder.refresh_once() is True
    assert seen == [100, 101] and "subscriber_failed" in caplog.text


def test_expired_snapshot_fails_closed_and_reports_unavailable(cloud, caplog) -> None:
    pair = fx.build_pair(cloud)
    clock = {"now": cloud.now}
    holder = keyvault_holder(cloud, secrets(pair), clock=lambda: clock["now"])
    holder.refresh_once()
    assert holder.state() == wc.STATE_READY
    caplog.set_level(logging.INFO)
    clock["now"] = pair.leaf.not_valid_after_utc + timedelta(seconds=1)
    assert holder.current() is None and holder.state() == wc.STATE_UNAVAILABLE and holder.remaining_seconds() == 0
    assert holder.anchors() is None and holder.grants() == frozenset() and holder.delegation_keys() == {}
    assert holder.audience() is None and holder.status()["remainingSeconds"] == 0
    assert holder.refresh_once() is False and "state_transition from=READY to=UNAVAILABLE" in caplog.text
    with pytest.raises(ServiceAuthError, match="SERVICE_IDENTITY_UNAVAILABLE"):
        authenticate_peer(holder, pair.bp_leaf)


def test_refresh_loop_survives_failures_and_stops_on_request(cloud, monkeypatch) -> None:
    monkeypatch.setattr(wc, "MIN_REFRESH_SECONDS", 0.01)
    values: dict[str, object] = {wc.TRUST_BUNDLE_SECRET: CredentialError("VAULT_UNAVAILABLE"), f"wid-bundle-{TARGET}": ""}
    holder = keyvault_holder(cloud, values, refresh_seconds=0)

    async def scenario() -> None:
        stop = asyncio.Event()
        task = asyncio.create_task(holder.run(stop))
        await asyncio.sleep(0.05)
        assert holder.current() is None and not task.done()
        values.update(secrets(fx.build_pair(cloud)))
        for _ in range(200):
            if holder.current() is not None:
                break
            await asyncio.sleep(0.01)
        assert holder.current() is not None
        stop.set()
        await asyncio.wait_for(task, 5)

    asyncio.run(scenario())


def test_refresh_without_a_reader_is_inert(cloud) -> None:
    holder = CredentialHolder(wc.SOURCE_KEYVAULT, TARGET, fx.TRUST_DOMAIN, config_error="CONFIG_INVALID")
    assert not holder.refreshable and holder.refresh_once() is False
    assert holder.state() == wc.STATE_UNAVAILABLE and holder.status()["lastReason"] == "CONFIG_INVALID"
    assert CredentialHolder(wc.SOURCE_KEYVAULT, TARGET, fx.TRUST_DOMAIN).state() == wc.STATE_UNISSUED


def test_key_material_never_appears_in_reprs_or_status(cloud) -> None:
    pair = fx.build_pair(cloud)
    holder = keyvault_holder(cloud, secrets(pair))
    holder.refresh_once()
    snapshot = holder.current()
    rendered = repr(snapshot) + str(holder.status()) + json.dumps(holder.status())
    assert "PRIVATE KEY" not in rendered and "BEGIN" not in rendered
    assert pair.bundle["tls_key_pem"].splitlines()[1] not in rendered
    assert snapshot.tls_chain_pem not in rendered and snapshot.ca_bundle_pem not in rendered
    assert "PRIVATE KEY" not in repr(CredentialError("LEAF_KEY_MISMATCH")) + str(CredentialError("LEAF_KEY_MISMATCH"))


def test_hot_reload_swaps_the_delegation_key_set_without_restart(cloud) -> None:
    first = fx.build_pair(cloud, 100, 100)
    second = fx.build_pair(
        cloud, 101, 101, extra_delegations=first.trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"]
    )
    values = secrets(first)
    holder = keyvault_holder(cloud, values)
    holder.refresh_once()
    auth = auth_from_holder(holder)
    now = int(cloud.now.timestamp())
    assert verify_envelope(auth.verifier, envelope(first.bp_key, kid_of(first), now, "e1")).envelope_id == "e1"
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
        verify_envelope(auth.verifier, envelope(second.bp_key, kid_of(second), now, "e2"))
    values.update(secrets(second))
    assert holder.refresh_once() is True
    assert verify_envelope(auth.verifier, envelope(second.bp_key, kid_of(second), now, "e3")).envelope_id == "e3"
    assert verify_envelope(auth.verifier, envelope(first.bp_key, kid_of(first), now, "e4")).envelope_id == "e4"


def test_envelope_key_must_be_active_currently_valid_chained_and_carry_the_oid(cloud) -> None:
    pair = fx.build_pair(cloud, delegation={"activate_after": timedelta(minutes=10)})
    snapshot = accept(pair)
    now = int(cloud.now.timestamp())

    def verifier_at(moment: int, keys=None, anchors=None) -> DelegatedContextVerifier:
        return DelegatedContextVerifier(
            snapshot.grants,
            snapshot.delegation_keys if keys is None else keys,
            ReplayStore(),
            now=lambda: moment,
            anchors=lambda: snapshot.anchors if anchors is None else anchors,
        )

    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
        verify_envelope(verifier_at(now), envelope(pair.bp_key, kid_of(pair), now, "early"))
    later = now + 601
    assert verify_envelope(verifier_at(later), envelope(pair.bp_key, kid_of(pair), later, "later")).envelope_id == "later"
    expired = now + int(timedelta(hours=25).total_seconds())
    with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
        verify_envelope(verifier_at(expired), envelope(pair.bp_key, kid_of(pair), expired, "expired"))

    def attempt(key, certificate, anchors) -> DelegatedContext:
        keys = {(fx.BP_URI, "k"): DelegationKey(key.public_key(), certificate, 0)}
        direct = DelegatedContextVerifier(snapshot.grants, keys, ReplayStore(), now=lambda: now, anchors=lambda: anchors)
        return verify_envelope(direct, envelope(key, "k", now, f"direct-{certificate.serial_number}"))

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


def test_workload_auth_follows_the_holder_and_fails_closed_when_expired(cloud) -> None:
    pair = fx.build_pair(cloud)
    clock = {"now": cloud.now}
    holder = keyvault_holder(cloud, secrets(pair), clock=lambda: clock["now"])
    auth = auth_from_holder(holder)
    with pytest.raises(ServiceAuthError, match="SERVICE_IDENTITY_UNAVAILABLE"):
        auth.audience  # noqa: B018
    holder.refresh_once()
    assert auth.audience == fx.PR_AUDIENCE and auth.authenticate_peer(pair.bp_leaf) == fx.BP_URI
    now = int(cloud.now.timestamp())
    assert verify_envelope(auth.verifier, envelope(pair.bp_key, kid_of(pair), now)).relationship_id == "relationship-a"
    clock["now"] = pair.leaf.not_valid_after_utc + timedelta(seconds=1)
    with pytest.raises(ServiceAuthError):
        verify_envelope(auth.verifier, envelope(pair.bp_key, kid_of(pair), now, "after-expiry"))
    with pytest.raises(ServiceAuthError):
        auth.authenticate_peer(pair.bp_leaf)
    with pytest.raises(ServiceAuthError):
        auth.audience  # noqa: B018


def test_peer_authentication_checks_chain_revocation_usage_and_trust_domain(cloud) -> None:
    pair = fx.build_pair(cloud)
    holder = CredentialHolder.static(accept(pair))
    assert authenticate_peer(holder, pair.bp_leaf) == fx.BP_URI
    other = fx.new_cloud(cloud.now)
    wrong_domain = cloud.issue("spiffe://elsewhere/workload/business-platform", [fx.CLIENT])[1]
    server_only = cloud.issue(fx.BP_URI, [fx.SERVER])[1]
    foreign_root = other.issue(fx.BP_URI, [fx.CLIENT])[1]
    expired = cloud.issue(fx.BP_URI, [fx.CLIENT], start=timedelta(hours=-30))[1]
    revoked = CredentialHolder.static(accept(fx.build_pair(cloud, revoked_serials=[pair.bp_leaf.serial_number])))
    for denied_holder, certificate in (
        (holder, wrong_domain),
        (holder, server_only),
        (holder, foreign_root),
        (holder, expired),
        (revoked, pair.bp_leaf),
    ):
        with pytest.raises(ServiceAuthError, match="SERVICE_AUTHENTICATION_FAILED"):
            authenticate_peer(denied_holder, certificate)


@pytest.mark.parametrize("url", ["https://kv-waooaw-demo.vault.azure.net", "https://kv-waooaw-demo.vault.azure.net/"])
def test_vault_url_accepts_only_https_azure_vault_hosts(url) -> None:
    assert validate_vault_url(url) == "https://kv-waooaw-demo.vault.azure.net"


@pytest.mark.parametrize(
    "url",
    [
        "http://kv.vault.azure.net",
        "https://kv.vault.azure.net.evil.example",
        "https://evil.example/kv.vault.azure.net",
        "https://user@kv.vault.azure.net",
        "https://user:pass@kv.vault.azure.net",
        "https://.vault.azure.net",
        "https://vault.azure.net",
        "https://kv.vault.azure.net:8443",
        "https://kv.vault.azure.net/secrets",
        "https://kv.vault.azure.net?x=1",
        "https://kv.vault.azure.net#frag",
        "",
        "kv.vault.azure.net",
    ],
)
def test_vault_url_rejects_everything_else(url) -> None:
    with pytest.raises(CredentialError) as raised:
        validate_vault_url(url)
    assert raised.value.code == "CONFIG_INVALID"


class FakeHttp:
    def __init__(self, vault=(200, b'{"value": "payload"}'), identity=None) -> None:
        self.vault = vault
        self.identity = identity or (200, json.dumps({"access_token": "t0ken", "expires_on": "4102444800"}).encode())
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, url: str, headers, timeout: float):
        self.calls.append((url, dict(headers)))
        return self.identity if url.startswith("http://127.0.0.1") else self.vault


ENVIRON = {"IDENTITY_ENDPOINT": "http://127.0.0.1:42356/msi/token", "IDENTITY_HEADER": "hdr"}


def test_key_vault_reader_uses_the_managed_identity_token_and_rest_api_7_4() -> None:
    http = FakeHttp()
    reader = KeyVaultSecretReader("https://kv-waooaw-demo.vault.azure.net", "client-1", ENVIRON, http)
    assert reader.get_secret("wid-trust-bundle") == "payload"
    assert reader.get_secret("wid/bundle ../x") == "payload"
    assert len(http.calls) == 3
    identity_url, identity_headers = http.calls[0]
    assert identity_headers == {"X-IDENTITY-HEADER": "hdr"}
    assert "api-version=2019-08-01" in identity_url and "resource=https%3A%2F%2Fvault.azure.net" in identity_url
    assert "client_id=client-1" in identity_url
    vault_url, vault_headers = http.calls[1]
    assert vault_url == "https://kv-waooaw-demo.vault.azure.net/secrets/wid-trust-bundle?api-version=7.4"
    assert vault_headers == {"Authorization": "Bearer t0ken"}
    assert "/secrets/wid%2Fbundle%20..%2Fx?" in http.calls[2][0]


def test_key_vault_reader_without_client_id_and_with_token_expiry() -> None:
    clock = {"now": fx.new_cloud().now}
    http = FakeHttp()
    http.identity = (200, json.dumps({"access_token": "t", "expires_on": str(int(clock["now"].timestamp()) + 3600)}).encode())
    reader = KeyVaultSecretReader("https://kv.vault.azure.net", None, ENVIRON, http, clock=lambda: clock["now"])
    reader.get_secret("a")
    reader.get_secret("b")
    assert "client_id" not in http.calls[0][0] and sum(url.startswith("http://127") for url, _ in http.calls) == 1
    clock["now"] += timedelta(minutes=58)
    reader.get_secret("c")
    assert sum(url.startswith("http://127") for url, _ in http.calls) == 2


@pytest.mark.parametrize(
    ("code", "vault", "identity", "environ"),
    [
        ("VAULT_DENIED", (403, b""), None, ENVIRON),
        ("VAULT_DENIED", (401, b""), None, ENVIRON),
        ("SECRET_NOT_FOUND", (404, b""), None, ENVIRON),
        ("VAULT_UNAVAILABLE", (500, b""), None, ENVIRON),
        ("VAULT_UNAVAILABLE", (200, b"not json"), None, ENVIRON),
        ("VAULT_UNAVAILABLE", (200, b'{"value": 5}'), None, ENVIRON),
        ("VAULT_UNAVAILABLE", (200, b"x" * (wc.MAX_RESPONSE_BYTES + 1)), None, ENVIRON),
        ("IDENTITY_UNAVAILABLE", (200, b"{}"), (500, b""), ENVIRON),
        ("IDENTITY_UNAVAILABLE", (200, b"{}"), (200, b"{}"), ENVIRON),
        ("IDENTITY_UNAVAILABLE", (200, b"{}"), (200, b'{"access_token": "", "expires_on": "1"}'), ENVIRON),
        ("IDENTITY_UNAVAILABLE", (200, b"{}"), (200, b"x" * (wc.MAX_RESPONSE_BYTES + 1)), ENVIRON),
        ("IDENTITY_UNAVAILABLE", (200, b"{}"), None, {}),
    ],
)
def test_key_vault_reader_failures_carry_only_a_reason_code(code, vault, identity, environ) -> None:
    reader = KeyVaultSecretReader("https://kv.vault.azure.net", "", environ, FakeHttp(vault, identity))
    with pytest.raises(CredentialError) as raised:
        reader.get_secret("wid-trust-bundle")
    assert raised.value.code == code and str(raised.value) == code


def test_key_vault_reader_drops_a_rejected_token() -> None:
    http = FakeHttp(vault=(401, b""))
    reader = KeyVaultSecretReader("https://kv.vault.azure.net", "", ENVIRON, http)
    for _ in range(2):
        with pytest.raises(CredentialError):
            reader.get_secret("wid-trust-bundle")
    assert sum(url.startswith("http://127") for url, _ in http.calls) == 2


def test_default_http_transport_never_follows_redirects_and_maps_failures(monkeypatch) -> None:
    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> None:
            return None

        def read(self, limit: int) -> bytes:
            return b"x" * limit

    class Opener:
        def __init__(self, outcome) -> None:
            self.outcome = outcome

        def open(self, _request, timeout):
            if isinstance(self.outcome, Exception):
                raise self.outcome
            return self.outcome

    monkeypatch.setattr(wc, "_OPENER", Opener(Response()))
    status, body = wc._http_get("https://kv.vault.azure.net/x", {"A": "b"}, 1.0)
    assert status == 200 and len(body) == wc.MAX_RESPONSE_BYTES + 1
    monkeypatch.setattr(wc, "_OPENER", Opener(urllib.error.HTTPError("u", 403, "denied", None, None)))
    assert wc._http_get("https://kv.vault.azure.net/x", {}, 1.0) == (403, b"")
    for failure in (urllib.error.URLError("down"), TimeoutError(), OSError("reset")):
        monkeypatch.setattr(wc, "_OPENER", Opener(failure))
        with pytest.raises(CredentialError) as raised:
            wc._http_get("https://kv.vault.azure.net/x", {}, 1.0)
        assert raised.value.code == "VAULT_UNAVAILABLE"
    with pytest.raises(CredentialError, match="CONFIG_INVALID"):
        wc._http_get("file:///etc/passwd", {}, 1.0)
    assert wc._NoRedirect().redirect_request() is None


def keyvault_environment(**changes: str) -> dict[str, str]:
    return {
        "WAOOAW_WID_SOURCE": "keyvault",
        "WAOOAW_WID_VAULT_URL": "https://kv.vault.azure.net",
        "WAOOAW_WID_TRUST_DOMAIN": fx.TRUST_DOMAIN,
        "WAOOAW_WID_WORKLOAD": TARGET,
        **changes,
    }


def test_keyvault_environment_selects_a_refreshable_holder() -> None:
    holder = credential_holder_from_environment(
        keyvault_environment(
            WAOOAW_WID_REFRESH_SECONDS="5", WAOOAW_WID_ENVIRONMENT="demo", WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID="id"
        )
    )
    assert holder is not None and holder.refreshable and holder.enforced
    assert holder.refresh_seconds == wc.MIN_REFRESH_SECONDS and holder.environment == "demo"
    assert holder.state() == wc.STATE_UNISSUED
    default = credential_holder_from_environment(keyvault_environment())
    assert default is not None and default.refresh_seconds == wc.DEFAULT_REFRESH_SECONDS and default.environment is None


@pytest.mark.parametrize(
    "changes",
    [
        {"WAOOAW_WID_VAULT_URL": "http://evil.example"},
        {"WAOOAW_WID_VAULT_URL": ""},
        {"WAOOAW_WID_WORKLOAD": "billing-engine"},
        {"WAOOAW_WID_TRUST_DOMAIN": ""},
        {"WAOOAW_WID_REFRESH_SECONDS": "soon"},
        {"WAOOAW_WID_SOURCE": "vaultless"},
    ],
)
def test_keyvault_environment_never_crashes_and_reports_the_reason(changes, caplog) -> None:
    caplog.set_level(logging.ERROR)
    holder = credential_holder_from_environment(keyvault_environment(**changes))
    assert holder is not None and not holder.refreshable and holder.state() == wc.STATE_UNAVAILABLE
    assert holder.status()["lastReason"] == "CONFIG_INVALID" and "configuration_rejected" in caplog.text
    assert holder.refresh_once() is False


def test_no_environment_means_no_credential_holder(monkeypatch) -> None:
    monkeypatch.delenv("WAOOAW_WID_SOURCE", raising=False)
    monkeypatch.delenv("WAOOAW_WORKLOAD_CREDENTIALS", raising=False)
    assert credential_holder_from_environment() is None
    assert credential_holder_from_environment({"WAOOAW_WID_SOURCE": ""}) is None


class TestDirectoryMode:
    @pytest.fixture
    def credentials(self, tmp_path: Path) -> Path:
        import bootstrap_workload_identity

        registry = Path(__file__).parents[2] / "infrastructure" / "workload-identity" / "registry.yaml"
        bootstrap_workload_identity.bootstrap(registry, "ci", tmp_path / "wid")
        return tmp_path / "wid"

    def test_bootstrap_output_loads_as_a_static_unexpiring_holder(self, credentials) -> None:
        holder = credential_holder_from_environment({"WAOOAW_WORKLOAD_CREDENTIALS": str(credentials)})
        assert holder is not None and not holder.refreshable and not holder.enforced
        snapshot = holder.current()
        assert snapshot is not None and snapshot.source == wc.SOURCE_DIRECTORY and snapshot.bundle_version == 0
        assert snapshot.identity_uri.endswith("/workload/professional-runtime") and snapshot.grants and snapshot.delegation_keys
        assert holder.state() == wc.STATE_READY and holder.refresh_once() is False

    def test_directory_credentials_verify_an_envelope_and_the_service_link(self, credentials) -> None:
        auth = WorkloadAuth.from_credentials(credentials)
        manifest = json.loads((credentials / "manifest.json").read_text())
        signer = manifest["workloads"]["business-platform"]
        key = serialization.load_pem_private_key(
            (credentials / "workloads" / "business-platform" / "delegation-key.pem").read_bytes(), None
        )
        peer = x509.load_pem_x509_certificate((credentials / "workloads" / "business-platform" / "tls-cert.pem").read_bytes())
        now = int(fx.new_cloud().now.timestamp())
        signed = envelope(key, signer["delegation_key_id"], now, issuer_uri=signer["identity_uri"])
        context = auth.verifier.verify(
            signed,
            signer["identity_uri"],
            auth.audience,
            "GET",
            fx.PROJECTION_ROUTE,
            fx.PROJECTION_OPERATION,
            1,
            DIGEST,
            lambda _context: True,
        )
        assert context.issuer_uri == signer["identity_uri"] and auth.authenticate_peer(peer) == signer["identity_uri"]
        response = asyncio.run(probe_service_link(request_with(auth, peer)))
        assert response.status_code == 200 and json.loads(response.body)["bundle_version"] == 0


def request_with(auth, peer: x509.Certificate | None, headers=None) -> Request:
    state = {PEER_CERTIFICATE_STATE_KEY: peer.public_bytes(DER)} if peer is not None else {}
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/internal/v1/service-link",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "app": SimpleNamespace(state=SimpleNamespace(relationship_workload_auth=auth)),
        "state": state,
    }
    return Request(scope)


def ready_auth(cloud: fx.Cloud, **options) -> tuple[fx.Pair, CredentialHolder, WorkloadAuth]:
    pair = fx.build_pair(cloud, **options)
    holder = CredentialHolder.static(accept(pair))
    return pair, holder, auth_from_holder(holder)


def test_link_probe_answers_a_granted_authenticated_peer_without_an_actor(cloud, caplog) -> None:
    pair, _, auth = ready_auth(cloud)
    caplog.set_level(logging.INFO)
    response = asyncio.run(probe_service_link(request_with(auth, pair.bp_leaf)))
    body = json.loads(response.body)
    assert response.status_code == 200 and set(body) == {"status", "peer_identity_uri", "bundle_version", "remaining_seconds"}
    assert body["status"] == "ok" and body["peer_identity_uri"] == fx.BP_URI and body["bundle_version"] == 100
    assert 0 < body["remaining_seconds"] <= 86400
    assert "service_auth decision=allow target=professional-runtime operation=probeServiceLink" in caplog.text
    assert "BEGIN" not in response.body.decode() + caplog.text


def test_link_probe_denies_ungranted_unauthenticated_and_unconfigured_callers(cloud, caplog) -> None:
    pair, _, auth = ready_auth(cloud)
    ungranted = cloud.issue(fx.PR_URI.replace("professional-runtime", "ai-runtime"), [fx.CLIENT])[1]
    own_identity = cloud.issue(fx.PR_URI, [fx.CLIENT])[1]
    foreign = fx.new_cloud(cloud.now).issue(fx.BP_URI, [fx.CLIENT])[1]
    caplog.set_level(logging.WARNING)
    cases = (
        (request_with(auth, ungranted), "SERVICE_AUTHORIZATION_DENIED"),
        (request_with(auth, own_identity), "SERVICE_AUTHORIZATION_DENIED"),
        (request_with(auth, foreign), "SERVICE_AUTHENTICATION_FAILED"),
        (request_with(auth, None), "SERVICE_AUTHENTICATION_FAILED"),
        (request_with(None, pair.bp_leaf), "SERVICE_AUTHENTICATION_FAILED"),
    )
    for request, code in cases:
        response = asyncio.run(probe_service_link(request))
        assert response.status_code == 401 and json.loads(response.body)["code"] == code
        assert response.media_type == "application/problem+json"
    assert (
        "decision=deny target=professional-runtime operation=probeServiceLink reason_class=SERVICE_AUTHORIZATION_DENIED"
        in caplog.text
    )


def test_link_probe_is_unavailable_when_the_credential_has_expired(cloud) -> None:
    pair = fx.build_pair(cloud)
    clock = {"now": cloud.now}
    holder = keyvault_holder(cloud, secrets(pair), clock=lambda: clock["now"])
    holder.refresh_once()
    auth = auth_from_holder(holder)
    assert asyncio.run(probe_service_link(request_with(auth, pair.bp_leaf))).status_code == 200
    clock["now"] = pair.leaf.not_valid_after_utc + timedelta(seconds=1)
    response = asyncio.run(probe_service_link(request_with(auth, pair.bp_leaf)))
    assert response.status_code == 503 and json.loads(response.body)["code"] == "SERVICE_IDENTITY_UNAVAILABLE"


async def test_link_probe_is_served_by_the_real_app_and_needs_no_bearer_token(cloud, monkeypatch) -> None:
    pair, _, auth = ready_auth(cloud)
    monkeypatch.setattr(runtime_app.state, "relationship_workload_auth", auth, raising=False)
    peer = {"value": pair.bp_leaf.public_bytes(DER)}

    async def with_peer(scope, receive, send) -> None:
        if scope["type"] == "http" and peer["value"] is not None:
            scope.setdefault("state", {})[PEER_CERTIFICATE_STATE_KEY] = peer["value"]
        await runtime_app(scope, receive, send)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=with_peer), base_url="http://pr") as client:
        answer = await client.get("/internal/v1/service-link")
        peer["value"] = None
        refused = await client.get("/internal/v1/service-link")
    assert answer.status_code == 200 and answer.json()["peer_identity_uri"] == fx.BP_URI
    assert refused.status_code == 401


async def test_health_reports_the_credential_state_without_secrets(cloud, monkeypatch) -> None:
    pair = fx.build_pair(cloud)
    holder = keyvault_holder(cloud, secrets(pair))
    monkeypatch.setattr(runtime_app.state, "workload_credentials", holder, raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=runtime_app), base_url="http://pr") as client:
        before = (await client.get("/health")).json()
        holder.refresh_once()
        after = (await client.get("/health")).json()
    assert before["workloadCredential"]["state"] == wc.STATE_UNISSUED and after["workloadCredential"]["state"] == wc.STATE_READY
    assert set(after["workloadCredential"]) == {
        "source",
        "state",
        "serialDigest",
        "notAfter",
        "remainingSeconds",
        "bundleVersion",
        "lastReason",
    }
    assert "temporalConnected" in after and "BEGIN" not in json.dumps(after)


async def test_health_without_a_credential_holder_keeps_its_contract(monkeypatch) -> None:
    monkeypatch.setattr(runtime_app.state, "workload_credentials", None, raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=runtime_app), base_url="http://pr") as client:
        assert "workloadCredential" not in (await client.get("/health")).json()


async def test_lifespan_runs_the_refresher_and_stops_it_on_shutdown(cloud, monkeypatch) -> None:
    monkeypatch.setattr(wc, "MIN_REFRESH_SECONDS", 0.01)
    holder = keyvault_holder(cloud, secrets(fx.build_pair(cloud)), refresh_seconds=0)
    monkeypatch.setattr(runtime_app.state, "workload_credentials", holder, raising=False)
    async with lifespan(runtime_app):
        for _ in range(200):
            if holder.current() is not None:
                break
            await asyncio.sleep(0.01)
        assert holder.current() is not None
    static = CredentialHolder.static(accept(fx.build_pair(cloud)))
    monkeypatch.setattr(runtime_app.state, "workload_credentials", static, raising=False)
    async with lifespan(runtime_app):
        assert static.current() is not None


class Transport:
    def __init__(self, certificate: x509.Certificate | None = None, tls: bool = True) -> None:
        self.certificate = certificate
        self.tls = tls
        self.closed = False

    def get_extra_info(self, _name: str):
        if not self.tls:
            return None
        der = b"" if self.certificate is None else self.certificate.public_bytes(DER)
        return SimpleNamespace(getpeercert=lambda binary_form: der)

    def close(self) -> None:
        self.closed = True


def test_gated_protocol_refuses_connections_without_a_live_credential_or_trusted_peer(cloud, monkeypatch) -> None:
    accepted: list[object] = []
    monkeypatch.setattr(MutualTlsH11Protocol, "connection_made", lambda self, transport: accepted.append(transport))
    pair = fx.build_pair(cloud)
    gate = private_server.CredentialGatedProtocol.__new__(private_server.CredentialGatedProtocol)
    foreign = fx.new_cloud(cloud.now).issue(fx.BP_URI, [fx.CLIENT])[1]
    clock = {"now": cloud.now}
    holder = keyvault_holder(cloud, secrets(pair), clock=lambda: clock["now"])
    holder.refresh_once()

    no_holder = Transport(pair.bp_leaf)
    gate.connection_made(no_holder)
    register_holder(holder)
    refusals = [Transport(foreign), Transport(tls=False), Transport(None)]
    for transport in refusals:
        gate.connection_made(transport)
    assert no_holder.closed and all(transport.closed for transport in refusals) and not accepted

    trusted = Transport(pair.bp_leaf)
    gate.connection_made(trusted)
    assert accepted == [trusted] and not trusted.closed
    clock["now"] = pair.leaf.not_valid_after_utc + timedelta(seconds=1)
    expired = Transport(pair.bp_leaf)
    gate.connection_made(expired)
    assert expired.closed and len(accepted) == 1


def serve(context: ssl.SSLContext, outcomes: list) -> socket.socket:
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

    threading.Thread(target=accept_loop, daemon=True).start()
    return listener


def connect(port: int, pair: fx.Pair, folder: Path, sni: bool = True) -> bytes:
    certificate, key = folder / "client.pem", folder / "client-key.pem"
    certificate.write_text(fx.pem(pair.bp_leaf, pair.cloud.intermediate))
    key.write_text(fx.key_pem(pair.bp_leaf_key))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.load_verify_locations(cadata=fx.pem(pair.cloud.root))
    context.load_cert_chain(certificate, key)
    with (
        socket.create_connection(("127.0.0.1", port), timeout=5) as raw,
        context.wrap_socket(raw, server_hostname="professional-runtime.internal" if sni else None) as secured,
    ):
        server_certificate = secured.getpeercert(binary_form=True)
        assert secured.recv(2) == b"ok"
        return server_certificate


def await_outcome(outcomes: list, count: int) -> object:
    for _ in range(500):
        if len(outcomes) >= count:
            return outcomes[count - 1]
        time.sleep(0.01)
    raise AssertionError("listener never reported the connection outcome")


def test_private_listener_presents_the_reloaded_leaf_without_restart_and_fails_closed(cloud, tmp_path) -> None:
    first = fx.build_pair(cloud, 100, 100)
    second = fx.build_pair(cloud, 101, 101)
    shm = tmp_path / "shm"
    shm.mkdir()
    clock = {"now": cloud.now}
    values = secrets(first)
    holder = keyvault_holder(cloud, values, clock=lambda: clock["now"])
    tls = private_server.HotReloadTlsContext(holder, shm)
    context = tls.context
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2 and context.verify_mode == ssl.CERT_REQUIRED
    holder.subscribe(tls.install)
    assert holder.refresh_once() is True
    outcomes: list = []
    listener = serve(context, outcomes)
    port = listener.getsockname()[1]
    try:
        assert connect(port, first, tmp_path) == first.leaf.public_bytes(DER)
        values.update(secrets(second))
        assert holder.refresh_once() is True and tls.context is context
        assert connect(port, first, tmp_path) == second.leaf.public_bytes(DER)
        assert list(shm.iterdir()) == []
        clock["now"] = second.leaf.not_valid_after_utc + timedelta(seconds=1)
        with pytest.raises((ssl.SSLError, OSError)):
            connect(port, first, tmp_path)
        assert isinstance(await_outcome(outcomes, 3), ssl.SSLError)
    finally:
        listener.close()


def test_private_listener_trusts_only_the_current_signed_roots(cloud, tmp_path) -> None:
    pair = fx.build_pair(cloud)
    shm = tmp_path / "shm"
    shm.mkdir()
    holder = keyvault_holder(cloud, secrets(pair))
    tls = private_server.HotReloadTlsContext(holder, shm)
    holder.subscribe(tls.install)
    holder.refresh_once()
    holder.refresh_once()
    assert len(tls._roots) == 1
    outcomes: list = []
    listener = serve(tls.context, outcomes)
    stranger = fx.build_pair(fx.new_cloud(cloud.now))
    try:
        with pytest.raises((ssl.SSLError, OSError)):
            connect(listener.getsockname()[1], stranger, tmp_path)
        assert isinstance(await_outcome(outcomes, 1), ssl.SSLError)
    finally:
        listener.close()


def test_private_listener_refuses_to_write_keys_outside_a_tmpfs_directory(cloud, tmp_path) -> None:
    snapshot = accept(fx.build_pair(cloud))
    tls = private_server.HotReloadTlsContext(CredentialHolder.static(snapshot), tmp_path / "missing")
    with pytest.raises(RuntimeError, match="tmpfs"):
        tls.install(snapshot)


def test_private_listener_configuration_follows_the_credential_source(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "keyvault")
    assert private_server.keyvault_source()
    config = private_server.private_listener_config()
    assert config.http is private_server.CredentialGatedProtocol and config.ssl_keyfile is None and config.port == 5443
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "directory")
    monkeypatch.setenv("WAOOAW_WORKLOAD_CREDENTIALS", str(tmp_path))
    monkeypatch.setenv("PR_PRIVATE_PORT", "6000")
    config = private_server.private_listener_config()
    assert not private_server.keyvault_source() and config.http is MutualTlsH11Protocol and config.port == 6000


def test_private_listener_main_wires_the_holder_into_the_tls_context(cloud, monkeypatch, tmp_path) -> None:
    holder = keyvault_holder(cloud, secrets(fx.build_pair(cloud)))
    holder.refresh_once()
    config = MagicMock(ssl=None)
    server = MagicMock()
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "keyvault")
    monkeypatch.setenv("WAOOAW_WID_KEY_TMPFS", str(tmp_path))
    monkeypatch.setattr(private_server, "private_listener_config", lambda: config)
    monkeypatch.setattr(private_server.uvicorn, "Server", MagicMock(return_value=server))
    with pytest.raises(RuntimeError, match="credential holder"):
        private_server.main()
    register_holder(holder)
    private_server.main()
    assert isinstance(config.ssl, ssl.SSLContext) and config.ssl.minimum_version == ssl.TLSVersion.TLSv1_2
    assert len(holder._subscribers) == 1 and list(tmp_path.iterdir()) == []
    server.run.assert_called_once_with()


def test_private_listener_main_requires_tls_for_directory_source(monkeypatch) -> None:
    config = MagicMock(ssl=None)
    monkeypatch.setenv("WAOOAW_WID_SOURCE", "directory")
    monkeypatch.setattr(private_server, "private_listener_config", lambda: config)
    with pytest.raises(RuntimeError, match="requires TLS"):
        private_server.main()


class FakeChild:
    def __init__(self, code: int | None = None, hangs: bool = False) -> None:
        self.code = code
        self.hangs = hangs
        self.terminated = self.killed = False

    def poll(self) -> int | None:
        return self.code

    def terminate(self) -> None:
        self.terminated = True
        if not self.hangs:
            self.code = -15

    def kill(self) -> None:
        self.killed = True
        self.code = -9

    def wait(self, timeout: float | None = None) -> int:
        if self.hangs and not self.killed:
            raise subprocess.TimeoutExpired("child", timeout or 0)
        return self.code or 0


def test_supervisor_exits_non_zero_and_stops_the_other_child_when_one_dies() -> None:
    environ = {"WAOOAW_WID_SOURCE": "keyvault"}
    survivor, dead = FakeChild(), FakeChild(3)
    children = [survivor, dead]
    supervised = entrypoint.supervise(environ, spawn=lambda _c: children.pop(0), sleep=lambda _s: None)
    assert supervised == 3
    assert survivor.terminated and not dead.terminated
    clean = [FakeChild(), FakeChild(0)]
    supervised_clean = entrypoint.supervise(environ, spawn=lambda _c: clean.pop(0), sleep=lambda _s: None)
    assert supervised_clean == 1


def test_supervisor_stops_children_on_termination_and_kills_the_unresponsive() -> None:
    stubborn, polite = FakeChild(hangs=True), FakeChild()
    children = [stubborn, polite]
    status = entrypoint.supervise(
        {"PR_PRIVATE_LISTENER": "1"}, spawn=lambda _c: children.pop(0), sleep=lambda _s: None, terminated=lambda: True
    )
    assert status == 143 and stubborn.terminated and stubborn.killed and polite.terminated and not polite.killed


def test_supervisor_polls_until_a_child_exits() -> None:
    child = FakeChild()
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 3:
            child.code = 7

    assert entrypoint.supervise({}, spawn=lambda _c: child, sleep=sleep) == 7 and sleeps == [entrypoint.POLL_SECONDS] * 3


def test_private_listener_is_supervised_only_for_cloud_or_explicit_delivery() -> None:
    assert len(entrypoint.child_commands({})) == 1
    assert len(entrypoint.child_commands({"WAOOAW_WID_SOURCE": "directory"})) == 1
    assert entrypoint.child_commands({"WAOOAW_WID_SOURCE": " KeyVault "})[1][-1] == "private_server.py"
    assert len(entrypoint.child_commands({"PR_PRIVATE_LISTENER": "1"})) == 2
    assert entrypoint.child_commands({})[0][-5:] == ["main:app", "--host", "0.0.0.0", "--port", "5003"]


def test_entrypoint_main_translates_signals_into_a_clean_stop(monkeypatch) -> None:
    handlers: dict[int, object] = {}
    monkeypatch.setattr(entrypoint.signal, "signal", lambda number, handler: handlers.setdefault(number, handler))
    seen: dict[str, object] = {}

    def fake_supervise(terminated) -> int:
        seen["before"] = terminated()
        handlers[entrypoint.signal.SIGTERM](entrypoint.signal.SIGTERM, None)
        seen["after"] = terminated()
        return 143

    monkeypatch.setattr(entrypoint, "supervise", lambda terminated: fake_supervise(terminated))
    with pytest.raises(SystemExit) as stopped:
        entrypoint.main()
    assert stopped.value.code == 143 and seen == {"before": False, "after": True}
    assert set(handlers) == {entrypoint.signal.SIGTERM, entrypoint.signal.SIGINT}


def test_default_spawn_starts_a_real_child_process(monkeypatch) -> None:
    popen = MagicMock()
    monkeypatch.setattr(entrypoint.subprocess, "Popen", popen)
    assert entrypoint._spawn(["a", "b"]) is popen.return_value
    popen.assert_called_once_with(["a", "b"])

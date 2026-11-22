# Implements: ADR-046 Amendment 1 (section 12.2) cloud workload credential issuance, contract section 8
# constitutional_basis: C-026, C-059, C-063, C-083, C-084, C-085

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID

import wid_issuer
import workload_identity_issuance as wid
from workload_identity_issuance import (
    CloudFixture,
    FakeKeyVault,
    IssuanceError,
    KeyVaultClient,
    ManagedIdentityTokenProvider,
    build_cloud_fixture,
    renew_cloud_fixture,
    verify_chain,
    verify_trust_bundle,
)


REPO_ROOT = Path(__file__).parents[2]
REGISTRY_PATH = REPO_ROOT / "infrastructure/workload-identity/registry.yaml"
WORKLOADS = ["business-platform", "billing-engine", "professional-runtime"]
T0 = datetime(2026, 11, 22, 6, 0, 0, tzinfo=timezone.utc)
PRIVATE_MARKER = "PRIVATE KEY"


def _registry() -> dict[str, Any]:
    return wid.load_registry(REGISTRY_PATH)


def _vault() -> FakeKeyVault:
    return FakeKeyVault().provision(WORKLOADS)


def _json(vault: FakeKeyVault, secret: str) -> dict[str, Any]:
    return json.loads(vault.secrets[secret])


def _bundle(vault: FakeKeyVault, workload: str) -> dict[str, Any]:
    return _json(vault, f"wid-bundle-{workload}")


def _chain(pem: str) -> list[x509.Certificate]:
    return x509.load_pem_x509_certificates(pem.encode())


def _issue_all(now: datetime = T0) -> FakeKeyVault:
    vault = _vault()
    registry = _registry()
    wid.run_ca(vault, registry, "demo", now)
    wid.run_leaf(vault, registry, "demo", WORKLOADS, now)
    return vault


def _issue_all_with(vault: FakeKeyVault, now: datetime) -> None:
    registry = _registry()
    wid.run_ca(vault, registry, "demo", now)
    wid.run_leaf(vault, registry, "demo", WORKLOADS, now)


def test_ca_bootstrap_from_unissued_builds_root_intermediate_and_signed_trust_bundle() -> None:
    vault = _vault()
    assert vault.secrets["wid-ca-state"] == "UNISSUED"

    summary = wid.run_ca(vault, _registry(), "demo", T0)

    state = _json(vault, "wid-ca-state")
    root = x509.load_pem_x509_certificate(state["root_pem"].encode())
    intermediate = x509.load_pem_x509_certificate(state["intermediate_pem"].encode())
    assert summary["actions"] == ["bootstrap"]
    assert set(state) == {
        "schema_version",
        "bundle_version",
        "root_pem",
        "root_key_kid",
        "intermediate_pem",
        "intermediate_key_kid",
        "previous_root_pem",
        "previous_root_until",
    }
    assert state["schema_version"] == "1.1"
    assert state["root_key_kid"] == vault.keys["wid-root"][0]
    assert state["intermediate_key_kid"] == vault.keys["wid-intermediate"][0]
    assert isinstance(root.public_key(), ec.EllipticCurvePublicKey)
    assert root.public_key().curve.name == "secp256r1"
    assert root.not_valid_after_utc - root.not_valid_before_utc == timedelta(days=365)
    assert intermediate.not_valid_after_utc - intermediate.not_valid_before_utc == timedelta(days=90)
    assert intermediate.extensions.get_extension_for_class(x509.BasicConstraints).value.path_length == 0
    verify_chain([intermediate], [root], T0, subject_is_ca=True)

    trust = _json(vault, "wid-trust-bundle")
    verify_trust_bundle(trust, T0)
    assert trust["ca_bundle_pem"] == state["root_pem"] + state["intermediate_pem"]
    assert trust["revoked_serials"] == [] and trust["revoked_identity_uris"] == []
    assert trust["manifest"]["schema_version"] == "1.0"
    assert trust["manifest"]["policy_version"] == "1.1"
    assert trust["trust_domain"] == "demo.waooaw.internal"
    for text in vault.secrets.values():
        assert PRIVATE_MARKER not in text
    assert set(vault.sign_calls) == {state["root_key_kid"], state["intermediate_key_kid"]}


def test_ca_is_idempotent_and_never_republishes_unchanged_content() -> None:
    vault = _vault()
    registry = _registry()
    wid.run_ca(vault, registry, "demo", T0)
    writes = list(vault.secret_writes)
    before = dict(vault.secrets)

    summary = wid.run_ca(vault, registry, "demo", T0 + timedelta(hours=24))

    assert summary["actions"] == [] and summary["trust_bundle_published"] is False
    assert vault.secret_writes == writes
    assert vault.secrets == before


def test_malformed_ca_state_is_an_error_not_a_bootstrap() -> None:
    vault = _vault()
    vault.secrets["wid-ca-state"] = "{not json"

    with pytest.raises(IssuanceError, match="wid-ca-state"):
        wid.run_ca(vault, _registry(), "demo", T0)
    assert vault.secrets["wid-ca-state"] == "{not json"


def test_leaf_issues_registry_identities_with_24_hour_chains_and_section_8_documents() -> None:
    vault = _issue_all()
    registry = _registry()
    trust = _json(vault, "wid-trust-bundle")
    roots = wid.trusted_roots(trust)

    assert set(trust["manifest"]["workloads"]) == set(WORKLOADS)
    for workload in WORKLOADS:
        bundle = _bundle(vault, workload)
        assert set(bundle) == {
            "schema_version",
            "bundle_version",
            "environment",
            "workload",
            "identity_uri",
            "generated_at",
            "not_after",
            "tls_key_pem",
            "tls_cert_pem",
            "delegation_key_pem",
            "delegation_cert_pem",
            "delegation_key_id",
            "delegation_activate_after",
        }
        chain = _chain(bundle["tls_cert_pem"])
        leaf = chain[0]
        expected_uri = f"spiffe://demo.waooaw.internal/workload/{registry['workloads'][workload]['identity_path']}"
        san = leaf.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value
        assert san.get_values_for_type(x509.UniformResourceIdentifier) == [expected_uri]
        assert bundle["identity_uri"] == expected_uri
        assert len(chain) == 2
        assert leaf.not_valid_after_utc - leaf.not_valid_before_utc == timedelta(hours=24)
        assert datetime.fromisoformat(bundle["not_after"]) == leaf.not_valid_after_utc
        verify_chain(chain, roots, T0)
        record = trust["manifest"]["workloads"][workload]
        assert record["tls_certificate_sha256"] == leaf.fingerprint(hashes.SHA256()).hex()
        assert record["tls_serial"] == str(leaf.serial_number)
        assert record["identity_uri"] == expected_uri

    business_platform = _bundle(vault, "business-platform")
    delegation = x509.load_pem_x509_certificate(business_platform["delegation_cert_pem"].encode())
    entry = trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"][-1]
    assert business_platform["delegation_activate_after"] == (T0 + timedelta(minutes=10)).isoformat()
    assert entry == {
        "key_id": business_platform["delegation_key_id"],
        "certificate_pem": business_platform["delegation_cert_pem"],
        "not_before": delegation.not_valid_before_utc.isoformat(),
        "not_after": delegation.not_valid_after_utc.isoformat(),
        "activate_after": business_platform["delegation_activate_after"],
    }
    assert trust["manifest"]["workloads"]["business-platform"]["delegation_key_id"] == entry["key_id"]
    assert wid.DELEGATION_SIGNING_OID in delegation.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    assert _bundle(vault, "billing-engine")["delegation_key_pem"] is None
    assert trust["manifest"]["workloads"]["billing-engine"]["delegation_certificates"] == []
    private = ec_key_from(business_platform["tls_key_pem"])
    assert private.public_key().public_numbers() == _chain(business_platform["tls_cert_pem"])[0].public_key().public_numbers()


def ec_key_from(pem: str) -> Any:
    from cryptography.hazmat.primitives import serialization

    return serialization.load_pem_private_key(pem.encode(), password=None)


def test_trust_bundle_is_written_before_any_workload_bundle_and_routes_cover_the_probe() -> None:
    vault = _issue_all()

    first_bundle = min(index for index, name in enumerate(vault.secret_writes) if name.startswith("wid-bundle-"))
    last_trust = max(index for index, name in enumerate(vault.secret_writes) if name == "wid-trust-bundle")
    assert last_trust < first_bundle
    grants = _json(vault, "wid-trust-bundle")["manifest"]["route_grants"]
    assert {
        (grant["caller"], grant["target"], grant["route"])
        for grant in grants
        if grant["operation"] == "probeServiceLink"
    } == {
        ("business-platform", "billing-engine", "/internal/v1/service-link"),
        ("business-platform", "professional-runtime", "/internal/v1/service-link"),
    }
    assert {grant["caller"] for grant in grants} == {"business-platform"}


def test_trust_bundle_signature_binds_the_canonical_document() -> None:
    vault = _issue_all()
    trust = _json(vault, "wid-trust-bundle")
    unsigned = {key: value for key, value in trust.items() if key != "signature"}
    intermediate = x509.load_pem_x509_certificate(trust["intermediate_pem"].encode())

    intermediate.public_key().verify(
        base64.b64decode(trust["signature"]),
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"),
        ec.ECDSA(hashes.SHA256()),
    )
    tampered = dict(trust, revoked_serials=["1"])
    with pytest.raises(IssuanceError, match="signature"):
        verify_trust_bundle(tampered, T0)
    with pytest.raises(IssuanceError, match="expired"):
        verify_trust_bundle(trust, T0 + timedelta(days=91))


def test_chain_verification_matches_cryptography_client_verifier() -> None:
    from cryptography.x509 import verification

    vault = _issue_all()
    trust = _json(vault, "wid-trust-bundle")
    chain = _chain(_bundle(vault, "business-platform")["tls_cert_pem"])
    store = verification.Store(wid.trusted_roots(trust))
    policy = verification.PolicyBuilder().store(store).time(T0 + timedelta(minutes=1)).build_client_verifier()

    verified = policy.verify(chain[0], chain[1:])

    assert verified.chain[0] == chain[0]


def test_leaf_renews_at_eight_hours_and_keeps_old_delegation_until_its_own_expiry() -> None:
    vault = _issue_all()
    registry = _registry()
    first = _bundle(vault, "business-platform")
    first_trust = _json(vault, "wid-trust-bundle")

    result = wid.run_leaf(vault, registry, "demo", WORKLOADS, T0 + timedelta(hours=7, minutes=59))
    assert result["issued"] == []
    assert _bundle(vault, "business-platform") == first

    later = T0 + timedelta(hours=8)
    result = wid.run_leaf(vault, registry, "demo", WORKLOADS, later)
    renewed = _bundle(vault, "business-platform")
    trust = _json(vault, "wid-trust-bundle")
    assert sorted(item.split(":")[0] for item in result["issued"]) == sorted(WORKLOADS)
    assert renewed["bundle_version"] > first["bundle_version"]
    assert trust["bundle_version"] > first_trust["bundle_version"]
    assert renewed["tls_cert_pem"] != first["tls_cert_pem"]
    assert renewed["delegation_key_id"] != first["delegation_key_id"]
    assert renewed["delegation_activate_after"] == (later + timedelta(minutes=10)).isoformat()
    key_ids = [item["key_id"] for item in trust["manifest"]["workloads"]["business-platform"]["delegation_certificates"]]
    assert key_ids == [first["delegation_key_id"], renewed["delegation_key_id"]]
    assert trust["manifest"]["workloads"]["business-platform"]["delegation_key_id"] == renewed["delegation_key_id"]
    verify_chain(_chain(renewed["tls_cert_pem"]), wid.trusted_roots(trust), later)

    wid.run_leaf(vault, registry, "demo", WORKLOADS, T0 + timedelta(hours=24, minutes=2))
    remaining = _json(vault, "wid-trust-bundle")["manifest"]["workloads"]["business-platform"]["delegation_certificates"]
    assert first["delegation_key_id"] not in [item["key_id"] for item in remaining]
    assert renewed["delegation_key_id"] in [item["key_id"] for item in remaining]


def test_every_leaf_and_delegation_certificate_is_at_most_24_hours() -> None:
    fixture = build_cloud_fixture(REGISTRY_PATH, "demo", WORKLOADS, now=T0)
    for step in range(1, 7):
        fixture = renew_cloud_fixture(fixture, T0 + timedelta(hours=8 * step))
    trust = json.loads(fixture["wid-trust-bundle"])
    for workload in WORKLOADS:
        chain = _chain(json.loads(fixture[f"wid-bundle-{workload}"])["tls_cert_pem"])
        assert chain[0].not_valid_after_utc - chain[0].not_valid_before_utc <= timedelta(hours=24)
        for entry in trust["manifest"]["workloads"][workload]["delegation_certificates"]:
            certificate = x509.load_pem_x509_certificate(entry["certificate_pem"].encode())
            assert certificate.not_valid_after_utc - certificate.not_valid_before_utc <= timedelta(hours=24)
    with pytest.raises(IssuanceError, match="24 hours"):
        wid.build_leaf_certificate(
            "spiffe://demo.waooaw.internal/workload/billing-engine",
            ec.generate_private_key(ec.SECP256R1()).public_key(),
            _chain(_bundle(fixture.vault, "billing-engine")["tls_cert_pem"])[1],
            fixture.vault.get_signer(_json(fixture.vault, "wid-ca-state")["intermediate_key_kid"]),
            ["server_auth"],
            T0,
            timedelta(hours=24, seconds=1),
        )


def test_trust_bundle_stays_within_key_vault_secret_limit_with_overlapping_delegations_and_dual_trust() -> None:
    fixture = build_cloud_fixture(REGISTRY_PATH, "demo", WORKLOADS, now=T0)
    for step in range(1, 7):
        fixture = renew_cloud_fixture(fixture, T0 + timedelta(hours=8 * step))
    assert len(fixture["wid-trust-bundle"].encode()) < wid.MAX_SECRET_BYTES
    assert len(json.loads(fixture["wid-trust-bundle"])["manifest"]["workloads"]["business-platform"]["delegation_certificates"]) == 3


def test_fixture_renewal_uses_the_same_vault_and_raises_versions() -> None:
    first = build_cloud_fixture(REGISTRY_PATH, "demo", WORKLOADS, now=T0)
    second = renew_cloud_fixture(first, T0 + timedelta(hours=9))

    assert second.vault is first.vault
    assert set(second) == {"wid-trust-bundle", *(f"wid-bundle-{item}" for item in WORKLOADS)}
    assert json.loads(second["wid-trust-bundle"])["bundle_version"] > json.loads(first["wid-trust-bundle"])["bundle_version"]
    assert second["wid-bundle-billing-engine"] != first["wid-bundle-billing-engine"]
    assert json.loads(first["wid-bundle-billing-engine"])["bundle_version"] < json.loads(second["wid-bundle-billing-engine"])["bundle_version"]


def test_revoked_serial_forces_reissue_and_is_published_signed() -> None:
    vault = _issue_all()
    registry = _registry()
    before = _bundle(vault, "billing-engine")
    serial = str(_chain(before["tls_cert_pem"])[0].serial_number)
    trust_before = _json(vault, "wid-trust-bundle")

    result = wid.run_revoke(vault, registry, "demo", T0 + timedelta(minutes=1), serials=[serial])
    trust = _json(vault, "wid-trust-bundle")
    assert trust["revoked_serials"] == [serial]
    assert trust["bundle_version"] > trust_before["bundle_version"] and result["revoked_serials"] == 1
    verify_trust_bundle(trust, T0 + timedelta(minutes=1))

    result = wid.run_leaf(vault, registry, "demo", WORKLOADS, T0 + timedelta(minutes=30))
    assert result["issued"] == ["billing-engine:revoked-serial"]
    assert _bundle(vault, "billing-engine")["tls_cert_pem"] != before["tls_cert_pem"]
    assert _json(vault, "wid-trust-bundle")["revoked_serials"] == [serial]


def test_suspend_rejects_reissue_for_the_workload_and_resume_restores_it() -> None:
    vault = _issue_all()
    registry = _registry()
    professional = _bundle(vault, "professional-runtime")
    uri = professional["identity_uri"]
    serial = str(_chain(professional["tls_cert_pem"])[0].serial_number)

    wid.run_revoke(vault, registry, "demo", T0 + timedelta(minutes=1), suspend="professional-runtime")
    trust = _json(vault, "wid-trust-bundle")
    assert uri in trust["revoked_identity_uris"] and serial in trust["revoked_serials"]
    delegation_serial = str(
        x509.load_pem_x509_certificate(professional["delegation_cert_pem"].encode()).serial_number
    )
    assert delegation_serial in trust["revoked_serials"]

    with pytest.raises(IssuanceError, match="suspended or revoked: professional-runtime"):
        wid.run_leaf(vault, registry, "demo", WORKLOADS, T0 + timedelta(hours=9))
    assert _bundle(vault, "professional-runtime") == professional
    assert _bundle(vault, "business-platform")["generated_at"] == (T0 + timedelta(hours=9)).isoformat()

    wid.run_revoke(vault, registry, "demo", T0 + timedelta(hours=9, minutes=1), resume="professional-runtime")
    result = wid.run_leaf(vault, registry, "demo", WORKLOADS, T0 + timedelta(hours=9, minutes=30))
    assert result["issued"] == ["professional-runtime:revoked-serial"]
    assert _bundle(vault, "professional-runtime")["tls_cert_pem"] != professional["tls_cert_pem"]


def test_revoke_validates_inputs_and_requires_an_action() -> None:
    vault = _issue_all()
    registry = _registry()
    with pytest.raises(IssuanceError, match="decimal"):
        wid.run_revoke(vault, registry, "demo", T0, serials=["abc"])
    with pytest.raises(IssuanceError, match="registered workload identity"):
        wid.run_revoke(vault, registry, "demo", T0, identity_uris=["spiffe://demo.waooaw.internal/workload/other"])
    with pytest.raises(IssuanceError, match="Nothing to revoke"):
        wid.run_revoke(vault, registry, "demo", T0)
    with pytest.raises(IssuanceError, match="not registered"):
        wid.run_revoke(vault, registry, "demo", T0, suspend="nope")


def test_rollback_and_equal_versions_are_refused() -> None:
    vault = _issue_all()
    trust = _json(vault, "wid-trust-bundle")
    before = vault.secrets["wid-trust-bundle"]

    for version in (trust["bundle_version"] - 1, trust["bundle_version"]):
        with pytest.raises(IssuanceError, match="Refusing to publish"):
            wid.publish_json_secret(vault, "wid-trust-bundle", {**trust, "bundle_version": version})
    assert vault.secrets["wid-trust-bundle"] == before


def test_versions_strictly_increase_even_when_the_clock_goes_backwards() -> None:
    vault = _issue_all(T0 + timedelta(hours=1))
    registry = _registry()
    version = _json(vault, "wid-trust-bundle")["bundle_version"]

    wid.run_revoke(vault, registry, "demo", T0 + timedelta(hours=1, seconds=-30), serials=["5"])

    assert _json(vault, "wid-trust-bundle")["bundle_version"] == version + 1


def test_unknown_workload_and_missing_ca_state_are_errors() -> None:
    vault = _vault()
    registry = _registry()
    wid.run_ca(vault, registry, "demo", T0)
    with pytest.raises(IssuanceError, match="Unknown workload in request: ghost"):
        wid.run_leaf(vault, registry, "demo", ["billing-engine", "ghost"], T0)
    assert vault.secrets["wid-bundle-billing-engine"] == "UNISSUED"
    with pytest.raises(IssuanceError, match="has not been issued"):
        wid.run_leaf(_vault(), registry, "demo", WORKLOADS, T0)


def test_intermediate_renewal_republishes_the_trust_bundle_and_reissues_leaves() -> None:
    vault = _issue_all()
    registry = _registry()
    state = _json(vault, "wid-ca-state")
    old_leaf = _bundle(vault, "billing-engine")

    wid.run_ca(vault, registry, "demo", T0 + timedelta(days=59))
    assert _json(vault, "wid-ca-state") == state

    now = T0 + timedelta(days=60, minutes=1)
    summary = wid.run_ca(vault, registry, "demo", now)
    new_state = _json(vault, "wid-ca-state")
    assert summary["actions"] == ["renew-intermediate"]
    assert new_state["root_pem"] == state["root_pem"] and new_state["root_key_kid"] == state["root_key_kid"]
    assert new_state["intermediate_key_kid"] != state["intermediate_key_kid"]
    assert len(vault.keys["wid-intermediate"]) == 2 and len(vault.keys["wid-root"]) == 1
    assert new_state["bundle_version"] > state["bundle_version"]
    trust = _json(vault, "wid-trust-bundle")
    assert trust["intermediate_pem"] == new_state["intermediate_pem"]
    verify_trust_bundle(trust, now)
    assert set(trust["manifest"]["workloads"]) == set(WORKLOADS)

    result = wid.run_leaf(vault, registry, "demo", WORKLOADS, now)
    assert {item.split(":")[1] for item in result["issued"]} == {"expired"}
    renewed = _bundle(vault, "billing-engine")
    verify_chain(_chain(renewed["tls_cert_pem"]), wid.trusted_roots(_json(vault, "wid-trust-bundle")), now)
    assert renewed["tls_cert_pem"] != old_leaf["tls_cert_pem"]


def test_root_renewal_keeps_previous_root_for_seven_days_then_drops_it() -> None:
    vault = _issue_all()
    registry = _registry()
    original_state = _json(vault, "wid-ca-state")
    old_leaf_chain = _chain(_bundle(vault, "billing-engine")["tls_cert_pem"])
    now = T0
    for _ in range(4):
        now += timedelta(days=61)
        wid.run_ca(vault, registry, "demo", now)
    assert _json(vault, "wid-ca-state")["root_pem"] == original_state["root_pem"]

    now = T0 + timedelta(days=305)
    summary = wid.run_ca(vault, registry, "demo", now)
    state = _json(vault, "wid-ca-state")
    trust = _json(vault, "wid-trust-bundle")
    assert "renew-root" in summary["actions"]
    assert state["root_pem"] != original_state["root_pem"]
    assert state["previous_root_pem"] == original_state["root_pem"]
    assert state["previous_root_until"] == (now + timedelta(days=7)).isoformat()
    assert trust["ca_bundle_pem"] == state["root_pem"] + state["intermediate_pem"] + original_state["root_pem"]
    assert trust["previous_root_pem"] == original_state["root_pem"]
    verify_trust_bundle(trust, now)
    new_root = x509.load_pem_x509_certificate(state["root_pem"].encode())
    intermediate = x509.load_pem_x509_certificate(state["intermediate_pem"].encode())
    verify_chain([intermediate], [new_root], now, subject_is_ca=True)

    old_root = x509.load_pem_x509_certificate(original_state["root_pem"].encode())
    assert new_root.not_valid_after_utc > old_root.not_valid_after_utc
    old_intermediate = x509.load_pem_x509_certificate(original_state["intermediate_pem"].encode())
    verify_chain([old_intermediate], [old_root], T0 + timedelta(days=1), subject_is_ca=True)
    verify_chain(old_leaf_chain, [old_root], T0 + timedelta(hours=1))

    wid.run_ca(vault, registry, "demo", now + timedelta(days=6, hours=23))
    assert _json(vault, "wid-ca-state")["previous_root_pem"] == original_state["root_pem"]
    summary = wid.run_ca(vault, registry, "demo", now + timedelta(days=7))
    dropped = _json(vault, "wid-ca-state")
    assert "drop-previous-root" in summary["actions"]
    assert dropped["previous_root_pem"] is None and dropped["previous_root_until"] is None
    trust = _json(vault, "wid-trust-bundle")
    assert trust["ca_bundle_pem"] == dropped["root_pem"] + dropped["intermediate_pem"]
    assert "previous_root_pem" not in trust
    assert trust["bundle_version"] > 0


def test_signer_never_exposes_ca_private_keys_in_vault_state_or_reprs() -> None:
    vault = _issue_all()
    signer = vault.get_signer(vault.keys["wid-intermediate"][0])

    assert "PRIVATE" not in repr(signer) and "PRIVATE" not in repr(wid.LocalKeySigner(ec.generate_private_key(ec.SECP256R1())))
    for name in ("wid-ca-state", "wid-trust-bundle"):
        assert PRIVATE_MARKER not in vault.secrets[name]
    assert all(PRIVATE_MARKER in vault.secrets[f"wid-bundle-{item}"] for item in WORKLOADS)


def test_local_key_signer_certificate_equals_standard_signing_semantics() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    signer = wid.LocalKeySigner(key)
    subject = wid.name("test root")
    certificate = wid.build_ca_certificate(subject, subject, key.public_key(), signer, T0, timedelta(days=1), 1)

    key.public_key().verify(certificate.signature, certificate.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))
    assert certificate.signature_hash_algorithm is not None and certificate.signature_hash_algorithm.name == "sha256"
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(IssuanceError, match="invalid certificate signature"):
        wid.build_ca_certificate(subject, subject, other.public_key(), wid.LocalKeySigner(key), T0, timedelta(days=1), 1)
        wid.sign_certificate(
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(other.public_key())
            .serial_number(1)
            .not_valid_before(T0)
            .not_valid_after(T0 + timedelta(days=1)),
            _WrongKeySigner(key, other),
        )


class _WrongKeySigner(wid.Signer):
    key_ref = "wrong"

    def __init__(self, advertised: ec.EllipticCurvePrivateKey, actual: ec.EllipticCurvePrivateKey) -> None:
        self._advertised = advertised
        self._actual = actual

    def public_key(self) -> ec.EllipticCurvePublicKey:
        return self._advertised.public_key()

    def sign(self, data: bytes) -> bytes:
        return self._actual.sign(data, ec.ECDSA(hashes.SHA256()))


def test_development_bootstrap_chain_verifies_with_the_shared_library(tmp_path: Path) -> None:
    import bootstrap_workload_identity as bootstrap_module

    output = tmp_path / "dev"
    bootstrap_module.bootstrap(REGISTRY_PATH, "development", output)
    root = x509.load_pem_x509_certificate((output / "trust/root.pem").read_bytes())
    chain = x509.load_pem_x509_certificates((output / "workloads/billing-engine/tls-cert.pem").read_bytes())

    verify_chain(chain, [root], datetime.now(timezone.utc))
    assert bootstrap_module.DELEGATION_SIGNING_OID == wid.DELEGATION_SIGNING_OID


class _RestVault:
    """Key Vault REST emulation for 7.4: secrets, EC key versions and ES256 sign over a SHA-256 digest."""

    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}
        self.keys: dict[str, list[tuple[str, ec.EllipticCurvePrivateKey]]] = {}
        self.requests: list[tuple[str, str, dict[str, str], dict[str, Any] | None]] = []
        self.fail_once: dict[str, int] = {}

    def create_key(self, name: str) -> str:
        key = ec.generate_private_key(ec.SECP256R1())
        version = hashlib.sha256(f"{name}{len(self.keys.get(name, []))}".encode()).hexdigest()[:32]
        self.keys.setdefault(name, []).append((version, key))
        return version

    def __call__(self, method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
        payload = json.loads(body) if body else None
        self.requests.append((method, url, headers, payload))
        assert headers["Authorization"] == "Bearer token-1"
        match = re.fullmatch(r"https://kv-test\.vault\.azure\.net(/[^?]+)\?api-version=7\.4", url)
        assert match, url
        path = match.group(1)
        if self.fail_once.get(path):
            self.fail_once[path] -= 1
            return 503, b'{"error":{"code":"Throttled"}}'
        if path.startswith("/secrets/"):
            name = path.split("/")[2]
            if method == "PUT":
                assert payload is not None
                self.secrets[name] = payload["value"]
                return 200, b"{}"
            if name not in self.secrets:
                return 404, b'{"error":{"code":"SecretNotFound"}}'
            return 200, json.dumps({"value": self.secrets[name]}).encode()
        parts = path.split("/")
        name = parts[2]
        if parts[3:] == ["create"]:
            assert payload is not None and payload["kty"] == "EC" and payload["crv"] == "P-256"
            return 200, self._key_document(name, self.create_key(name))
        if method == "POST" and parts[4:] == ["sign"]:
            assert payload is not None and payload["alg"] == "ES256"
            digest = base64.urlsafe_b64decode(payload["value"] + "=" * (-len(payload["value"]) % 4))
            assert len(digest) == 32
            key = dict(self.keys[name])[parts[3]]
            r, s = utils.decode_dss_signature(key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256()))))
            raw = r.to_bytes(32, "big") + s.to_bytes(32, "big")
            return 200, json.dumps({"value": base64.urlsafe_b64encode(raw).rstrip(b"=").decode()}).encode()
        version = parts[3] if len(parts) > 3 else self.keys[name][-1][0]
        return 200, self._key_document(name, version)

    def _key_document(self, name: str, version: str) -> bytes:
        numbers = dict(self.keys[name])[version].public_key().public_numbers()

        def encode(value: int) -> str:
            return base64.urlsafe_b64encode(value.to_bytes(32, "big")).rstrip(b"=").decode()

        key = {
            "kid": f"https://kv-test.vault.azure.net/keys/{name}/{version}",
            "kty": "EC",
            "crv": "P-256",
            "x": encode(numbers.x),
            "y": encode(numbers.y),
        }
        return json.dumps({"key": key}).encode()


def _rest_client(rest: _RestVault) -> KeyVaultClient:
    return KeyVaultClient("https://kv-test.vault.azure.net", lambda: "token-1", transport=rest, sleep=lambda _: None)


def test_key_vault_rest_flow_signs_through_the_vault_api_and_converts_raw_signatures() -> None:
    rest = _RestVault()
    rest.create_key("wid-root")
    rest.create_key("wid-intermediate")
    client = _rest_client(rest)
    registry = _registry()

    wid.run_ca(client, registry, "demo", T0)
    wid.run_leaf(client, registry, "demo", WORKLOADS, T0)

    trust = json.loads(rest.secrets["wid-trust-bundle"])
    verify_trust_bundle(trust, T0)
    chain = _chain(json.loads(rest.secrets["wid-bundle-billing-engine"])["tls_cert_pem"])
    verify_chain(chain, wid.trusted_roots(trust), T0)
    signs = [item for item in rest.requests if item[0] == "POST" and item[1].split("?")[0].endswith("/sign")]
    assert signs and all(item[3]["alg"] == "ES256" and len(item[3]["value"]) == 43 for item in signs)
    assert all(item[1].endswith("?api-version=7.4") for item in rest.requests)
    assert not any(PRIVATE_MARKER in rest.secrets[name] for name in ("wid-ca-state", "wid-trust-bundle"))
    assert client.get_secret("wid-missing") is None


def test_key_vault_client_creates_key_versions_and_retries_throttling() -> None:
    rest = _RestVault()
    rest.create_key("wid-root")
    client = _rest_client(rest)
    rest.fail_once["/keys/wid-root"] = 2

    current = client.get_key_public("wid-root")
    created = client.create_key_version("wid-root")

    assert created.kid != current.kid and len(rest.keys["wid-root"]) == 2
    assert client.get_key_public(created.kid).public_key.public_numbers() == created.public_key.public_numbers()
    rest.fail_once["/keys/wid-root"] = 3
    with pytest.raises(IssuanceError, match="HTTP 503 Throttled"):
        client.get_key_public("wid-root")


def test_key_vault_signer_rejects_a_signature_from_the_wrong_key() -> None:
    rest = _RestVault()
    rest.create_key("wid-root")
    client = _rest_client(rest)
    ref = client.get_key_public("wid-root")
    impostor = wid.KeyVaultSigner(client, ref.kid, ec.generate_private_key(ec.SECP256R1()).public_key())

    with pytest.raises(IssuanceError, match="does not verify"):
        impostor.sign(b"data")


@pytest.mark.parametrize(
    "url",
    [
        "http://kv-test.vault.azure.net",
        "https://kv-test.vault.azure.net.evil.example",
        "https://evil.example",
        "https://user@kv-test.vault.azure.net",
        "https://kv-test.vault.azure.net/keys",
        "",
    ],
)
def test_vault_url_must_be_https_on_the_key_vault_domain(url: str) -> None:
    with pytest.raises(IssuanceError, match="vault.azure.net"):
        KeyVaultClient(url, lambda: "token-1")


def test_key_vault_client_never_sends_the_token_to_another_host() -> None:
    rest = _RestVault()
    client = _rest_client(rest)

    with pytest.raises(IssuanceError, match="outside the configured vault"):
        client.get_key_public("https://evil.vault.azure.net/keys/wid-root/abc")
    assert rest.requests == []


def test_managed_identity_token_provider_uses_identity_endpoint_header_resource_and_client_id() -> None:
    calls: list[tuple[str, str, dict[str, str]]] = []

    def transport(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
        calls.append((method, url, headers))
        return 200, json.dumps({"access_token": "abc", "expires_on": "4102444800"}).encode()

    provider = ManagedIdentityTokenProvider(
        "client-1", {"IDENTITY_ENDPOINT": "http://localhost:42356/msi/token", "IDENTITY_HEADER": "secret-header"}, transport
    )

    assert provider() == "abc" and provider() == "abc"
    assert len(calls) == 1
    method, url, headers = calls[0]
    assert method == "GET" and headers == {"X-IDENTITY-HEADER": "secret-header"}
    assert url.startswith("http://localhost:42356/msi/token?")
    assert "resource=https%3A%2F%2Fvault.azure.net" in url and "client_id=client-1" in url and "api-version=2019-08-01" in url
    with pytest.raises(IssuanceError, match="not configured"):
        ManagedIdentityTokenProvider(None, {})()


def _environ(**overrides: str) -> dict[str, str]:
    values = {
        "WID_ENVIRONMENT": "demo",
        "WID_VAULT_URL": "https://kv-test.vault.azure.net",
        "WID_WORKLOADS": ",".join(WORKLOADS),
        "WID_REGISTRY_PATH": str(REGISTRY_PATH),
    }
    values.update(overrides)
    return values


def test_cli_runs_ca_leaf_status_and_revoke_without_leaking_material(capsys: pytest.CaptureFixture[str]) -> None:
    vault = _vault()
    environ = _environ()

    assert wid_issuer.main(["status"], environ, vault, T0) == 1
    capsys.readouterr()
    assert wid_issuer.main(["ca"], environ, vault, T0) == 0
    assert wid_issuer.main(["leaf"], environ, vault, T0) == 0
    capsys.readouterr()
    assert wid_issuer.main(["status"], environ, vault, T0 + timedelta(hours=1)) == 0
    status = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert status["workloads"]["business-platform"]["remaining_seconds"] == 23 * 3600 - 60  # backdated by the 60 s clock skew
    assert status["root"]["days_left"] > 364 and status["intermediate"]["days_left"] > 89
    assert status["trust_bundle"]["bundle_version"] > 0 and status["problems"] == []
    serial = str(_chain(_bundle(vault, "billing-engine")["tls_cert_pem"])[0].serial_number)
    assert wid_issuer.main(["revoke", "--serial", serial], environ, vault, T0 + timedelta(hours=1)) == 0
    assert wid_issuer.main(["leaf"], environ, vault, T0 + timedelta(hours=1, minutes=30)) == 0
    output = capsys.readouterr()
    assert PRIVATE_MARKER not in output.out + output.err and "BEGIN" not in output.out + output.err
    assert wid_issuer.main(["status"], environ, vault, T0 + timedelta(hours=1, minutes=40)) == 0
    assert "BEGIN" not in capsys.readouterr().out


def test_cli_status_fails_below_four_hours_remaining_or_when_a_bundle_is_missing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vault = _issue_all()
    environ = _environ()

    assert wid_issuer.main(["status"], environ, vault, T0 + timedelta(hours=19, minutes=59)) == 0
    assert wid_issuer.main(["status"], environ, vault, T0 + timedelta(hours=20, minutes=1)) == 1
    summary = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "business-platform-remaining-below-4h" in summary["problems"]

    vault.secrets["wid-bundle-billing-engine"] = "UNISSUED"
    assert wid_issuer.main(["status"], environ, vault, T0) == 1
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["workloads"]["billing-engine"] == {"state": "missing"}


def test_cli_errors_are_one_line_and_never_include_key_material(capsys: pytest.CaptureFixture[str]) -> None:
    vault = _issue_all()

    assert wid_issuer.main(["leaf"], _environ(WID_WORKLOADS="billing-engine,ghost"), vault, T0) == 1
    assert capsys.readouterr().err == "ERROR: Unknown workload in request: ghost\n"
    assert wid_issuer.main(["ca"], _environ(WID_ENVIRONMENT="development"), vault, T0) == 1
    assert "WID_ENVIRONMENT must be one of demo, uat, prod" in capsys.readouterr().err
    assert wid_issuer.main(["ca"], _environ(WID_VAULT_URL=""), None, T0) == 1
    assert "WID_VAULT_URL is required" in capsys.readouterr().err

    class Exploding(FakeKeyVault):
        def get_secret(self, name: str) -> str | None:
            raise RuntimeError(f"-----BEGIN {PRIVATE_MARKER}----- leaked")

    assert wid_issuer.main(["leaf"], _environ(), Exploding(), T0) == 1
    error = capsys.readouterr().err
    assert error == "ERROR: unexpected RuntimeError\n"


def test_cli_rejects_registry_with_wildcard_identity(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import yaml

    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["workloads"]["domain-adapter"]["identity_path"] = "domain-adapter/*"
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(registry), encoding="utf-8")

    assert wid_issuer.main(["ca"], _environ(WID_REGISTRY_PATH=str(path)), _vault(), T0) == 1
    assert "wildcard or generic adapter" in capsys.readouterr().err


def test_leaf_never_issues_for_a_trust_bundle_of_another_environment() -> None:
    vault = _issue_all()
    trust = _json(vault, "wid-trust-bundle")
    vault.secrets["wid-trust-bundle"] = json.dumps({**trust, "environment": "uat"})

    with pytest.raises(IssuanceError, match="different environment"):
        wid.run_leaf(vault, _registry(), "demo", WORKLOADS, T0 + timedelta(hours=9))


def test_ca_state_with_a_foreign_key_version_is_refused() -> None:
    vault = _issue_all()
    state = _json(vault, "wid-ca-state")
    vault.secrets["wid-ca-state"] = json.dumps({**state, "root_key_kid": vault.keys["wid-intermediate"][0]})

    with pytest.raises(IssuanceError, match="does not match its certificate"):
        wid.run_ca(vault, _registry(), "demo", T0 + timedelta(days=1))


def test_fixture_type_is_a_plain_mapping_of_secret_names_to_json_strings() -> None:
    fixture = build_cloud_fixture(REGISTRY_PATH, "ci", ["billing-engine"], now=T0)

    assert isinstance(fixture, CloudFixture) and isinstance(fixture, dict)
    assert set(fixture) == {"wid-trust-bundle", "wid-bundle-billing-engine"}
    assert all(isinstance(value, str) for value in fixture.values())
    assert json.loads(fixture["wid-trust-bundle"])["trust_domain"] == "waooaw.ci"


def test_cli_prints_the_console_lines_that_the_azure_alerts_parse(capsys: pytest.CaptureFixture[str]) -> None:
    vault = _vault()
    environ = _environ()

    assert wid_issuer.main(["ca"], environ, vault, T0) == 0
    ca_lines = capsys.readouterr().out.splitlines()
    assert re.fullmatch(r"wid_status ca intermediate_days=\d+ root_days=\d+", ca_lines[0])
    assert "wid_issuer mode=ca result=ok" in ca_lines
    assert not any(line.startswith("wid_status workload=") for line in ca_lines)

    assert wid_issuer.main(["leaf"], environ, vault, T0) == 0
    leaf_lines = capsys.readouterr().out.splitlines()
    for workload in WORKLOADS:
        assert any(re.fullmatch(rf"wid_status workload={workload} remaining_seconds=\d+ bundle_version=\d+", line) for line in leaf_lines)
    assert "wid_issuer mode=leaf result=ok" in leaf_lines and json.loads(leaf_lines[-1])["mode"] == "leaf"

    assert wid_issuer.main(["status"], environ, vault, T0 + timedelta(hours=21)) == 1
    failed_lines = capsys.readouterr().out.splitlines()
    assert "wid_issuer mode=status result=failed reason=unhealthy" in failed_lines

    assert wid_issuer.main(["leaf"], _environ(WID_WORKLOADS="ghost"), vault, T0) == 1
    assert "wid_issuer mode=leaf result=failed reason=issuance-error" in capsys.readouterr().out.splitlines()

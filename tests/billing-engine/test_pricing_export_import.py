# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-06
# Constitutional basis: C-059, C-088, C-089, C-091
"""Signed export and draft-only import of pricing versions."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from markup.package_engine import ThreadRate  # noqa: E402
from pricing.body_adapter import to_public  # noqa: E402
from pricing.export_import import BundleSigner, _bundle_digest, canonical_digest, export_bundle, import_bundle  # noqa: E402
from pricing.models import ActorContext, EffectiveRole, PricingDraftInvalid, PricingKind, PricingUnavailable, VersionState  # noqa: E402
from pricing_support import (  # noqa: E402
    PACKAGE_SUBJECT,
    START,
    budget_body,
    dma_package_body,
    make_harness,
)

ADMIN = ActorContext("admin-1", EffectiveRole.PRICING_ADMIN)
BUDGET_SUBJECT = "budget:ENVIRONMENT_CEILING|demo"
DEPLOY_MAXIMUM = 50000
SIGNER = BundleSigner("bundle-key-1", b"bundle-secret-1")


def _source():
    harness = make_harness()
    harness.repository.seed(PricingKind.PACKAGE, PACKAGE_SUBJECT, dma_package_body())
    harness.repository.seed(PricingKind.BUDGET, BUDGET_SUBJECT, budget_body(40000))
    return harness


async def _exported(harness=None):
    return await export_bundle((harness or _source()).service, "admin-1", SIGNER, START)


def _resign(bundle):
    content = {key: bundle[key] for key in ("schemaVersion", "bundleVersion", "exportedAt", "exportedBy", "entries")}
    digest = _bundle_digest(content)
    return {**bundle, "bundleDigest": digest, "signature": SIGNER.sign(digest)}


async def test_the_export_lists_only_effective_versions_with_digests_and_a_verifiable_signature():
    harness = _source()
    await harness.service.create_draft(ADMIN, PricingKind.PACKAGE, dma_package_body(package_code="GROWTH"))

    bundle = await _exported(harness)

    assert {(entry["kind"], entry["subjectKey"]) for entry in bundle["entries"]} == {
        ("POLICY", "policy:platform"),
        ("PACKAGE", PACKAGE_SUBJECT),
        ("BUDGET", BUDGET_SUBJECT),
    }
    assert {entry["state"] for entry in bundle["entries"]} == {"EFFECTIVE"}
    assert all(len(entry["bodyDigest"]) == 64 and entry["authorizedBy"] for entry in bundle["entries"])
    assert bundle["entries"] == sorted(bundle["entries"], key=lambda e: (e["kind"], e["subjectKey"], e["versionNo"]))
    assert SIGNER.verify(bundle["bundleDigest"], bundle["signature"])
    assert bundle["signature"]["algorithm"] == "HMAC-SHA256"


async def test_a_round_trip_creates_drafts_only_and_nothing_becomes_effective():
    bundle = await _exported()
    target = make_harness(with_policy=False)

    result = await import_bundle(target.service, ADMIN, bundle, SIGNER, deploy_maximum_paise=DEPLOY_MAXIMUM)

    assert result["rejected"] == []
    assert {(item["kind"], item["state"]) for item in result["created"]} == {
        ("POLICY", "DRAFT"),
        ("PACKAGE", "DRAFT"),
        ("BUDGET", "DRAFT"),
    }
    assert {version.state for version in target.repository.versions.values()} == {VersionState.DRAFT}
    assert await target.service.effective_versions(PricingKind.PACKAGE) == []
    imported = await target.service.list_versions(kind=PricingKind.PACKAGE)
    assert canonical_digest(PricingKind.PACKAGE, imported[0].body) == canonical_digest(
        PricingKind.PACKAGE, dma_package_body()
    )


async def test_a_bundle_whose_content_was_changed_after_signing_is_refused_as_a_whole():
    bundle = await _exported()
    tampered = copy.deepcopy(bundle)
    next(entry for entry in tampered["entries"] if entry["kind"] == "BUDGET")["body"]["maximumPaise"] = 49999
    target = make_harness(with_policy=False)

    with pytest.raises(PricingDraftInvalid) as refused:
        await import_bundle(target.service, ADMIN, tampered, SIGNER, deploy_maximum_paise=DEPLOY_MAXIMUM)

    assert refused.value.violations[0].code == "BUNDLE_SIGNATURE_INVALID"
    assert target.repository.versions == {}


async def test_a_bundle_signed_with_another_key_or_of_another_shape_is_refused():
    bundle = await _exported()
    other = BundleSigner("bundle-key-1", b"another-secret")
    target = make_harness(with_policy=False)

    with pytest.raises(PricingDraftInvalid) as wrong_key:
        await import_bundle(target.service, ADMIN, bundle, other, deploy_maximum_paise=DEPLOY_MAXIMUM)
    with pytest.raises(PricingDraftInvalid) as shape:
        await import_bundle(target.service, ADMIN, {**bundle, "bundleVersion": 2}, SIGNER)

    assert wrong_key.value.violations[0].code == "BUNDLE_SIGNATURE_INVALID"
    assert shape.value.violations[0].code == "BUNDLE_SHAPE_INVALID"


async def test_an_entry_whose_digest_does_not_match_its_body_is_rejected_even_when_the_bundle_is_signed():
    bundle = await _exported()
    tampered = copy.deepcopy(bundle)
    budget = next(entry for entry in tampered["entries"] if entry["kind"] == "BUDGET")
    budget["body"]["maximumPaise"] = 30000
    target = make_harness(with_policy=False)

    result = await import_bundle(target.service, ADMIN, _resign(tampered), SIGNER, deploy_maximum_paise=DEPLOY_MAXIMUM)

    assert [item["subjectKey"] for item in result["rejected"]] == [BUDGET_SUBJECT]
    assert result["rejected"][0]["code"] == "PRICING_DRAFT_INVALID"
    assert result["rejected"][0]["violations"][0]["code"] == "BUNDLE_ENTRY_DIGEST_MISMATCH"
    assert {item["kind"] for item in result["created"]} == {"POLICY", "PACKAGE"}


async def test_an_imported_package_below_its_cost_floor_is_refused_by_the_validator_and_left_no_draft():
    bundle = await _exported()
    target = make_harness(with_policy=False)
    target.reference.rates["llm_pro"] = ThreadRate("llm_pro", 40000, True)

    result = await import_bundle(target.service, ADMIN, bundle, SIGNER, deploy_maximum_paise=DEPLOY_MAXIMUM)

    refused = next(item for item in result["rejected"] if item["kind"] == "PACKAGE")
    assert refused["code"] == "PRICING_BELOW_FLOOR"
    assert refused["violations"][0]["code"] == "PRICING_BELOW_FLOOR"
    assert all(item["kind"] != "PACKAGE" for item in result["created"])
    package_states = {v.state for v in target.repository.versions.values() if v.kind is PricingKind.PACKAGE}
    assert package_states == {VersionState.DISCARDED}


async def test_an_entry_of_an_unknown_kind_or_without_a_body_is_rejected_without_stopping_the_import():
    bundle = await _exported()
    changed = copy.deepcopy(bundle)
    changed["entries"].append({"kind": "SURPRISE", "subjectKey": "surprise:1", "body": {}, "bodyDigest": "0" * 64})
    changed["entries"].append({"kind": "BUDGET", "subjectKey": "budget:SIMULATION|x", "bodyDigest": "0" * 64})
    target = make_harness(with_policy=False)

    result = await import_bundle(target.service, ADMIN, _resign(changed), SIGNER, deploy_maximum_paise=DEPLOY_MAXIMUM)

    assert {item["subjectKey"] for item in result["rejected"]} == {"surprise:1", "budget:SIMULATION|x"}
    assert len(result["created"]) == 3


async def test_without_a_configured_key_export_and_import_fail_closed(monkeypatch):
    monkeypatch.delenv("WBE_PRICING_BUNDLE_KEY", raising=False)
    monkeypatch.delenv("WBE_PRICING_BUNDLE_KEY_ID", raising=False)
    unconfigured = BundleSigner.from_environment()

    with pytest.raises(PricingUnavailable):
        await export_bundle(_source().service, "admin-1", unconfigured, START)
    with pytest.raises(PricingUnavailable):
        await import_bundle(make_harness().service, ADMIN, await _exported(), unconfigured)


def test_a_seed_written_without_optional_defaults_has_the_same_digest_as_its_published_form():
    seed = dma_package_body()
    for component in seed["components"]:
        component.pop("topupAllowed", None)

    assert canonical_digest(PricingKind.PACKAGE, seed) == canonical_digest(
        PricingKind.PACKAGE, to_public(PricingKind.PACKAGE, seed)
    )

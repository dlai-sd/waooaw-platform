from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from goal006_manifest import RELEASE_MEMBERS, validate_manifest

RELEASE_ROOT = Path("release/goal006")
MANIFEST_PATH = RELEASE_ROOT / "release-manifest.json"
EVIDENCE_PATH = RELEASE_ROOT / "supply-chain-evidence.json"


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def assert_violation(manifest: dict[str, Any], code: str, root: Path = RELEASE_ROOT) -> None:
    assert code in validate_manifest(manifest, root)


def test_signed_exact_six_manifest_passes_offline_verification() -> None:
    assert validate_manifest(load_manifest(), RELEASE_ROOT) == []


def test_manifest_contains_exactly_six_members_including_billing() -> None:
    manifest = load_manifest()
    assert set(manifest["payload"]["members"]) == RELEASE_MEMBERS
    del manifest["payload"]["members"]["billing-engine"]
    assert_violation(manifest, "RELEASE_MEMBERSHIP_INVALID")


@pytest.mark.parametrize("extra", ["oauth-vault", "filesystem-mcp", "seventh-service"])
def test_excluded_or_additional_members_are_rejected(extra: str) -> None:
    manifest = load_manifest()
    manifest["payload"]["members"][extra] = copy.deepcopy(manifest["payload"]["members"]["web"])
    assert_violation(manifest, "RELEASE_MEMBERSHIP_INVALID")


def test_mutable_tag_or_digest_substitution_is_rejected() -> None:
    manifest = load_manifest()
    manifest["payload"]["members"]["web"]["digest"] = "waooaw-web:phase2"
    violations = validate_manifest(manifest, RELEASE_ROOT)
    assert "web:DIGEST_INVALID" in violations
    assert "MANIFEST_SIGNATURE_INVALID" in violations


def test_manifest_payload_tampering_invalidates_signature() -> None:
    manifest = load_manifest()
    manifest["payload"]["reviewed_config_digest"] = "sha256:" + "0" * 64
    assert_violation(manifest, "MANIFEST_SIGNATURE_INVALID")


def test_member_signature_substitution_is_rejected() -> None:
    manifest = load_manifest()
    manifest["payload"]["members"]["billing-engine"]["signature"] = manifest["payload"]["members"]["web"]["signature"]
    assert_violation(manifest, "billing-engine:SIGNATURE_INVALID")


def test_revoked_or_invalid_verification_key_is_rejected() -> None:
    manifest = load_manifest()
    manifest["verification_key"]["status"] = "revoked"
    violations = validate_manifest(manifest, RELEASE_ROOT)
    assert "VERIFICATION_KEY_INVALID" in violations
    assert "MANIFEST_SIGNATURE_INVALID" in violations


def test_untrusted_builder_and_invalid_source_commit_are_rejected() -> None:
    manifest = load_manifest()
    manifest["payload"]["builder_identity"] = "https://untrusted.invalid/builder"
    manifest["payload"]["source_commit"] = "main"
    violations = validate_manifest(manifest, RELEASE_ROOT)
    assert "BUILDER_UNTRUSTED" in violations
    assert "SOURCE_COMMIT_INVALID" in violations


def test_evidence_digest_tampering_is_rejected() -> None:
    manifest = load_manifest()
    manifest["payload"]["members"]["constitutional-engine"]["evidence"]["sha256"] = "0" * 64
    assert_violation(manifest, "constitutional-engine:EVIDENCE_DIGEST_MISMATCH")


@pytest.mark.parametrize(
    ("section", "field", "value", "code"),
    [
        ("sboms", "format", "unknown", "constitutional-engine:SBOM_INVALID"),
        ("provenance", "builder_identity", "untrusted", "constitutional-engine:PROVENANCE_INVALID"),
        ("scans", "policy_result", "fail", "constitutional-engine:SCAN_INVALID"),
    ],
)
def test_member_evidence_must_be_complete_and_policy_passing(
    tmp_path: Path, section: str, field: str, value: str, code: str
) -> None:
    manifest = load_manifest()
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence[section]["constitutional-engine"][field] = value
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    for member in manifest["payload"]["members"].values():
        member["evidence"] = {"path": evidence_path.name, "sha256": digest}
    assert_violation(manifest, code, tmp_path)


def test_qualification_counts_must_be_nonzero_equal_and_without_omission() -> None:
    manifest = load_manifest()
    manifest["payload"]["qualification"].update(executed=0, passed=0, skipped=["SEC-10"])
    violations = validate_manifest(manifest, RELEASE_ROOT)
    assert "QUALIFICATION_INVALID" in violations
    assert "QUALIFICATION_ACCOUNTING_INVALID" in violations
    assert "QUALIFICATION_OMISSION" in violations


@pytest.mark.parametrize("field", ["password", "secret_value", "private_key", "access_token", "connection_string"])
def test_secret_values_are_rejected_from_manifest(field: str) -> None:
    manifest = load_manifest()
    manifest[field] = "prohibited"
    assert_violation(manifest, "SECRET_VALUE_PRESENT")


def test_evidence_path_cannot_escape_release_root() -> None:
    manifest = load_manifest()
    manifest["payload"]["members"]["web"]["evidence"]["path"] = "../../pyproject.toml"
    assert_violation(manifest, "web:EVIDENCE_PATH_INVALID")
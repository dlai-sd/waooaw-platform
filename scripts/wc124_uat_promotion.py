#!/usr/bin/env python3
"""Validate the fail-closed WC-124 Demo-to-UAT promotion binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SHA256 = re.compile(r"sha256:[0-9a-f]{64}$")
DEMO_FIELDS = {
    "seven_application_oci_digests",
    "schema_digest",
    "migration_digest",
    "demo_manifest_digest",
    "dependency_manifest_digest",
}
UAT_FIELDS = {
    "uat_manifest_digest",
    "uat_dependency_manifest_digest",
    "temporal_cloud_endpoint_identity",
    "secret_catalog_digest",
    "authorization_tuple_digest",
}
RELEASE_MEMBERS = {"ce", "bp", "pr", "air", "web", "billing", "dma"}


class PromotionError(ValueError):
    """The UAT promotion record failed closed."""


def canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def validate_promotion(record: dict[str, Any]) -> str:
    demo = record.get("demo_identity")
    accepted = record.get("founder_acceptance")
    promoted = record.get("uat_promoted_demo_identity")
    uat = record.get("uat_identity")
    signatures = record.get("signatures")
    if not all(isinstance(value, dict) for value in (demo, accepted, promoted, uat, signatures)):
        raise PromotionError("promotion record sections are incomplete")
    if set(demo) != DEMO_FIELDS or set(promoted) != DEMO_FIELDS:
        raise PromotionError("Demo identity fields are incomplete")
    digests = demo["seven_application_oci_digests"]
    if not isinstance(digests, dict) or set(digests) != RELEASE_MEMBERS:
        raise PromotionError("exact-seven application identity is invalid")
    digest_values = [
        *digests.values(),
        demo["schema_digest"],
        demo["migration_digest"],
        demo["demo_manifest_digest"],
        demo["dependency_manifest_digest"],
    ]
    if any(SHA256.fullmatch(str(value)) is None for value in digest_values):
        raise PromotionError("Demo identity contains an invalid digest")
    demo_digest = canonical_digest(demo)
    if promoted != demo:
        raise PromotionError("UAT application/schema/migration identity differs from Demo")
    if (
        not str(accepted.get("accepted_by", "")).strip()
        or not str(accepted.get("accepted_at", "")).strip()
        or not str(accepted.get("evidence_reference", "")).strip()
        or accepted.get("accepted_demo_identity_digest") != demo_digest
    ):
        raise PromotionError("Founder Demo acceptance is missing or mismatched")
    if set(uat) != UAT_FIELDS or any(
        SHA256.fullmatch(str(value)) is None for key, value in uat.items() if key != "temporal_cloud_endpoint_identity"
    ):
        raise PromotionError("UAT identity fields are incomplete")
    if not str(uat["temporal_cloud_endpoint_identity"]).strip():
        raise PromotionError("UAT Temporal Cloud identity is missing")
    expected_identities = {
        "demo_writer": "id-waooaw-demo-deployment-writer",
        "demo_verifier": "id-waooaw-demo-independent-verifier",
        "uat_verifier": "id-waooaw-uat-independent-verifier",
    }
    if signatures != expected_identities:
        raise PromotionError("promotion signer identities are not environment-exact")
    return canonical_digest(record)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    arguments = parser.parse_args()
    record = json.loads(arguments.record.read_text(encoding="utf-8"))
    print(json.dumps({"promotion_digest": validate_promotion(record)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

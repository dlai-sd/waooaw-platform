import copy

import pytest

from scripts.wc124_persistent_state_lifecycle import canonical_digest
from scripts.wc124_uat_promotion import PromotionError, validate_promotion


DIGEST = "sha256:" + "a" * 64


def promotion() -> dict:
    demo = {
        "seven_application_oci_digests": {
            member: DIGEST for member in ("ce", "bp", "pr", "air", "web", "billing", "dma")
        },
        "schema_digest": DIGEST,
        "migration_digest": DIGEST,
        "demo_manifest_digest": DIGEST,
        "dependency_manifest_digest": DIGEST,
    }
    return {
        "demo_identity": demo,
        "founder_acceptance": {
            "accepted_by": "Founder",
            "accepted_at": "2026-10-16T12:00:00Z",
            "accepted_demo_identity_digest": canonical_digest(demo),
            "evidence_reference": "FA-future-demo-acceptance",
        },
        "uat_promoted_demo_identity": copy.deepcopy(demo),
        "uat_identity": {
            "uat_manifest_digest": DIGEST,
            "uat_dependency_manifest_digest": DIGEST,
            "temporal_cloud_endpoint_identity": "temporal-cloud:uat",
            "secret_catalog_digest": DIGEST,
            "authorization_tuple_digest": DIGEST,
        },
        "signatures": {
            "demo_writer": "id-waooaw-demo-deployment-writer",
            "demo_verifier": "id-waooaw-demo-independent-verifier",
            "uat_verifier": "id-waooaw-uat-independent-verifier",
        },
    }


def test_valid_uat_promotion_binding_passes() -> None:
    assert validate_promotion(promotion()).startswith("sha256:")


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("demo_identity", "schema_digest"),
        ("demo_identity", "migration_digest"),
        ("founder_acceptance", "accepted_demo_identity_digest"),
        ("uat_identity", "authorization_tuple_digest"),
        ("signatures", "uat_verifier"),
    ],
)
def test_each_mutated_promotion_binding_fails_closed(section: str, field: str) -> None:
    record = promotion()
    record[section][field] = "invalid"
    with pytest.raises(PromotionError):
        validate_promotion(record)


def test_rebuilt_or_reselected_uat_application_identity_is_denied() -> None:
    record = promotion()
    record["uat_promoted_demo_identity"]["seven_application_oci_digests"]["web"] = (
        "sha256:" + "b" * 64
    )
    with pytest.raises(PromotionError, match="differs"):
        validate_promotion(record)

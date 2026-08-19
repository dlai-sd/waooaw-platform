from __future__ import annotations

from typing import Any

import pytest

from goal006_deployment_inputs import LEASE_FIELDS, create_inputs
from goal006_registry_manifest import RELEASE_MEMBERS


def manifest() -> dict[str, Any]:
    images = {member: f"ghcr.io/dlai-sd/{member}@sha256:{'a' * 64}" for member in RELEASE_MEMBERS}
    return {
        "schema": "waooaw.registry-release/v1",
        "immutable": True,
        "source_commit": "a" * 40,
        "builder_workflow": ".github/workflows/ci.yaml",
        "qualification": {"status": "pass", "github_run_id": "123"},
        "images": images,
        "evidence": {
            member: {
                "scan": {
                    "artifact": f"goal006-scan-{member}",
                    "policy": "fixable-high-critical",
                    "sha256": "b" * 64,
                },
                "sbom": {
                    "artifact": f"goal006-attestation-{member}",
                    "format": "spdx",
                    "oci_subject": images[member],
                    "sha256": "c" * 64,
                },
                "provenance": {
                    "artifact": f"goal006-attestation-{member}",
                    "mode": "max",
                    "oci_subject": images[member],
                    "sha256": "d" * 64,
                },
                "signature": {
                    "artifact": f"goal006-attestation-{member}",
                    "issuer": "github-oidc",
                    "oci_subject": images[member],
                    "sha256": "e" * 64,
                },
            }
            for member in RELEASE_MEMBERS
        },
    }


def configuration() -> dict[str, Any]:
    values: dict[str, Any] = {
        "key_vault_secret_ids": {
            member: f"/subscriptions/test/resourceGroups/test/providers/Microsoft.KeyVault/vaults/test/secrets/{member}"
            for member in RELEASE_MEMBERS
        },
        "planned_incremental_monthly_cost_inr": 1000,
        "cumulative_one_time_cost_inr": 1000,
    }
    values.update({field: f"accepted-{field}" for field in LEASE_FIELDS})
    values["lease_state"] = "ACTIVE"
    return values


@pytest.mark.parametrize("environment", ["demo", "uat"])
def test_nonproduction_inputs_require_lease_and_preserve_exact_tuple(environment: str) -> None:
    inputs = create_inputs(environment, manifest(), configuration(), True)
    assert set(inputs["image_digests"]) == RELEASE_MEMBERS
    assert inputs["lease_state"] == "ACTIVE"
    assert inputs["ghcr_packages_public"] is True


def test_anonymous_ghcr_verification_is_required() -> None:
    with pytest.raises(ValueError, match="anonymous digest pulls"):
        create_inputs("demo", manifest(), configuration(), False)


def test_missing_member_or_lease_field_is_rejected() -> None:
    values = configuration()
    del values["key_vault_secret_ids"]["web"]
    with pytest.raises(ValueError, match="exactly the six"):
        create_inputs("demo", manifest(), values, True)
    values = configuration()
    del values["lease_expires_at"]
    with pytest.raises(ValueError, match="lease_expires_at"):
        create_inputs("uat", manifest(), values, True)


def test_production_requires_positive_accepted_replica_values() -> None:
    values = configuration()
    values.update(ce_min_replicas=1, pr_min_replicas=1)
    inputs = create_inputs("prod", manifest(), values, True)
    assert inputs["ce_min_replicas"] == inputs["pr_min_replicas"] == 1
    values["ce_min_replicas"] = 0
    with pytest.raises(ValueError, match="ce_min_replicas"):
        create_inputs("prod", manifest(), values, True)


def test_tampered_manifest_is_rejected_before_input_generation() -> None:
    release = manifest()
    release["images"]["web"] = "ghcr.io/dlai-sd/web:latest"
    with pytest.raises(ValueError, match="invalid release manifest"):
        create_inputs("demo", release, configuration(), True)


def test_missing_or_negative_cost_assumptions_are_rejected() -> None:
    values = configuration()
    del values["planned_incremental_monthly_cost_inr"]
    with pytest.raises(ValueError, match="planned_incremental_monthly_cost_inr"):
        create_inputs("demo", manifest(), values, True)
    values = configuration()
    values["cumulative_one_time_cost_inr"] = -1
    with pytest.raises(ValueError, match="cumulative_one_time_cost_inr"):
        create_inputs("uat", manifest(), values, True)
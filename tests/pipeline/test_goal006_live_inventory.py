from __future__ import annotations

from typing import Any

from goal006_live_inventory import IDENTITY_EDGE_IMAGE, KEYCLOAK_IMAGE, validate_inventory
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


def inventory(environment: str, release: dict[str, Any]) -> list[dict[str, str]]:
    live = [
        {"name": f"ca-{environment}-{member}", "image": image, "provisioningState": "Succeeded"}
        for member, image in release["images"].items()
    ]
    live.append(
        {
            "name": f"ca-{environment}-keycloak",
            "image": KEYCLOAK_IMAGE,
            "provisioningState": "Succeeded",
        }
    )
    live.append(
        {
            "name": f"ca-{environment}-identity-edge",
            "image": IDENTITY_EDGE_IMAGE,
            "provisioningState": "Succeeded",
        }
    )
    return live


def test_exact_six_live_inventory_passes() -> None:
    release = manifest()
    assert validate_inventory("demo", release, inventory("demo", release)) == []


def test_missing_extra_or_digest_mismatched_member_fails() -> None:
    release = manifest()
    live = inventory("uat", release)
    live.pop()
    live.append({"name": "ca-uat-extra", "image": "invalid", "provisioningState": "Succeeded"})
    live[0]["image"] = "ghcr.io/dlai-sd/web:latest"
    violations = validate_inventory("uat", release, live)
    assert "LIVE_MEMBERSHIP_INVALID" in violations
    assert any(code.endswith(":DIGEST_MISMATCH") for code in violations)


def test_incomplete_provisioning_fails() -> None:
    release = manifest()
    live = inventory("prod", release)
    live[0]["provisioningState"] = "Updating"
    assert any(code.endswith(":PROVISIONING_INCOMPLETE") for code in validate_inventory("prod", release, live))
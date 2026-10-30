from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from goal006_live_inventory import (
    AUTH_REDIS_IMAGE,
    DEMO_TEMPORAL_IMAGE,
    IDENTITY_EDGE_IMAGE,
    KEYCLOAK_IMAGE,
    PGBOUNCER_IMAGE,
    release_app_name,
    validate_inventory,
)
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
        {"name": release_app_name(environment, member), "image": image, "provisioningState": "Succeeded"}
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
    if environment == "demo":
        live.append(
            {
                "name": f"ca-{environment}-temporal",
                "image": DEMO_TEMPORAL_IMAGE,
                "provisioningState": "Succeeded",
            }
        )
    if environment in {"demo", "uat"}:
        live.append(
            {
                "name": f"ca-{environment}-pgbouncer",
                "image": PGBOUNCER_IMAGE,
                "provisioningState": "Succeeded",
            }
        )
        live.append(
            {
                "name": f"ca-{environment}-auth-redis",
                "image": AUTH_REDIS_IMAGE,
                "provisioningState": "Succeeded",
            }
        )
    return live


def test_exact_seven_and_pinned_environment_dependencies_pass() -> None:
    release = manifest()
    assert validate_inventory("demo", release, inventory("demo", release)) == []
    assert validate_inventory("uat", release, inventory("uat", release)) == []
    assert validate_inventory("prod", release, inventory("prod", release)) == []
    assert release_app_name("demo", "agent-runtime-adapter-digital-marketing") == "ca-demo-dma"


def test_demo_temporal_is_required_and_digest_pinned() -> None:
    release = manifest()
    live = inventory("demo", release)
    temporal = next(item for item in live if item["name"] == "ca-demo-temporal")
    temporal["image"] = "temporalio/auto-setup:latest"
    violations = validate_inventory("demo", release, live)
    assert "ca-demo-temporal:DIGEST_MISMATCH" in violations

    live.pop()
    assert "LIVE_MEMBERSHIP_INVALID" in validate_inventory("demo", release, live)


def test_environment_scoped_auth_redis_is_a_pinned_dependency_not_a_release_member() -> None:
    release = manifest()
    for environment in ("demo", "uat"):
        live = inventory(environment, release)
        redis = next(item for item in live if item["name"] == f"ca-{environment}-auth-redis")
        redis["image"] = "redis:latest"
        assert f"ca-{environment}-auth-redis:DIGEST_MISMATCH" in validate_inventory(environment, release, live)

    assert all(item["name"] != "ca-prod-auth-redis" for item in inventory("prod", release))
    assert "auth-redis" not in release["images"]


def test_wc124_pgbouncer_is_a_pinned_dependency_in_demo_and_uat_only() -> None:
    # PR 531 deployed ca-{env}-pgbouncer without adding it here, so a correct Demo deployment
    # would have failed independent verification with LIVE_MEMBERSHIP_INVALID.
    release = manifest()
    for environment in ("demo", "uat"):
        live = inventory(environment, release)
        pooler = next(item for item in live if item["name"] == f"ca-{environment}-pgbouncer")
        pooler["image"] = "pgbouncer/pgbouncer:latest"
        assert f"ca-{environment}-pgbouncer:DIGEST_MISMATCH" in validate_inventory(environment, release, live)
        live.remove(pooler)
        assert "LIVE_MEMBERSHIP_INVALID" in validate_inventory(environment, release, live)

    assert all(item["name"] != "ca-prod-pgbouncer" for item in inventory("prod", release))
    assert "pgbouncer" not in release["images"]


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


SUBSCRIPTION = "2ed11839-6a0f-4eaa-bd94-44ca96ff5d84"


def mirrored(environment: str, release: dict[str, Any], registry: str) -> list[dict[str, str]]:
    live = inventory(environment, release)
    release_apps = {release_app_name(environment, member) for member in release["images"]}
    for item in live:
        if item["name"] in release_apps:
            item["image"] = item["image"].replace("ghcr.io/", f"{registry}/", 1)
    return live


def test_release_members_from_the_environment_acr_at_the_same_digest_pass() -> None:
    # Run 41028762781: image_home=both resolved to azure, so every release app ran the identical digest
    # from acrwaooawdemo2ed118 and the exact-ghcr comparison reported seven DIGEST_MISMATCH violations.
    release = manifest()
    for environment in ("demo", "uat", "prod"):
        live = mirrored(environment, release, f"acrwaooaw{environment}2ed118.azurecr.io")
        assert validate_inventory(environment, release, live, SUBSCRIPTION) == []
        assert any(code.endswith(":DIGEST_MISMATCH") for code in validate_inventory(environment, release, live))


def test_acr_release_member_with_another_digest_repository_or_registry_fails() -> None:
    release = manifest()
    registry = "acrwaooawdemo2ed118.azurecr.io"
    web = release_app_name("demo", "web")

    def violations_for(image: str) -> list[str]:
        live = mirrored("demo", release, registry)
        next(item for item in live if item["name"] == web)["image"] = image
        return validate_inventory("demo", release, live, SUBSCRIPTION)

    assert f"{web}:DIGEST_MISMATCH" in violations_for(f"{registry}/dlai-sd/web@sha256:{'f' * 64}")
    assert f"{web}:DIGEST_MISMATCH" in violations_for(f"{registry}/dlai-sd/ai-runtime@sha256:{'a' * 64}")
    assert f"{web}:DIGEST_MISMATCH" in violations_for(f"acrwaooawuat2ed118.azurecr.io/dlai-sd/web@sha256:{'a' * 64}")
    assert f"{web}:DIGEST_MISMATCH" in violations_for(f"acrwaooawdemo999999.azurecr.io/dlai-sd/web@sha256:{'a' * 64}")
    assert f"{web}:DIGEST_MISMATCH" in violations_for(f"{registry}/dlai-sd/web:latest")


def test_pinned_dependencies_stay_exact_when_an_environment_acr_is_known() -> None:
    release = manifest()
    live = mirrored("demo", release, "acrwaooawdemo2ed118.azurecr.io")
    keycloak = next(item for item in live if item["name"] == "ca-demo-keycloak")
    keycloak["image"] = "acrwaooawdemo2ed118.azurecr.io/" + KEYCLOAK_IMAGE
    assert "ca-demo-keycloak:DIGEST_MISMATCH" in validate_inventory("demo", release, live, SUBSCRIPTION)


def test_subscription_id_must_be_a_guid() -> None:
    release = manifest()
    with pytest.raises(ValueError, match="GUID"):
        validate_inventory("demo", release, inventory("demo", release), "not-a-subscription")


def test_verification_script_passes_the_logged_in_subscription() -> None:
    script = (Path(__file__).resolve().parents[2] / "scripts/goal006_verify_deployment.sh").read_text(encoding="utf-8")
    assert '--subscription-id "$(az account show --query id -o tsv)"' in script

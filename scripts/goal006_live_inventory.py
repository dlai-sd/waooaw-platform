#!/usr/bin/env python3
"""Verify live Azure Container Apps equal one GOAL-006 exact-seven release tuple."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from goal006_registry_manifest import RELEASE_MEMBERS, validate_registry_manifest  # noqa: F401

KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
IDENTITY_EDGE_IMAGE = "nginxinc/nginx-unprivileged@sha256:62a904036bfc0e4a4f2b556e34cbf17bc136b47fde8cdb4628762725f48c5782"
DEMO_TEMPORAL_IMAGE = "temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"
AUTH_REDIS_IMAGE = "redis@sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2"
# WC-124 per-role connection pooler (modules/workload/main.tf azurerm_container_app.pgbouncer).
PGBOUNCER_IMAGE = "docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"
DMA_MEMBER = "agent-runtime-adapter-digital-marketing"
GHCR_PREFIX = "ghcr.io/"
SUBSCRIPTION_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def release_app_name(environment: str, member: str) -> str:
    suffix = "dma" if member == DMA_MEMBER else member
    return f"ca-{environment}-{suffix}"


def expected_dependencies(environment: str) -> dict[str, str]:
    dependencies = {
        f"ca-{environment}-keycloak": KEYCLOAK_IMAGE,
        f"ca-{environment}-identity-edge": IDENTITY_EDGE_IMAGE,
    }
    if environment == "demo":
        dependencies[f"ca-{environment}-temporal"] = DEMO_TEMPORAL_IMAGE
    if environment in {"demo", "uat"}:
        dependencies[f"ca-{environment}-auth-redis"] = AUTH_REDIS_IMAGE
        dependencies[f"ca-{environment}-pgbouncer"] = PGBOUNCER_IMAGE
    return dependencies


def environment_registry(environment: str, subscription_id: str | None) -> str | None:
    """Return the environment's own WC-127 image-home ACR login server, if a subscription is known."""
    if subscription_id is None:
        return None
    if not SUBSCRIPTION_ID.fullmatch(subscription_id.lower()):
        raise ValueError("subscription ID must be a GUID")
    return f"acrwaooaw{environment}{subscription_id.lower().replace('-', '')[:6]}.azurecr.io"


def release_image_matches(actual: object, expected: str, registry: str | None) -> bool:
    """Accept the exact release reference, or the same repository and digest in the environment ACR."""
    if actual == expected:
        return True
    if registry is None or not isinstance(actual, str) or not expected.startswith(GHCR_PREFIX):
        return False
    return actual == f"{registry}/{expected.removeprefix(GHCR_PREFIX)}"


def validate_inventory(
    environment: str,
    manifest: Mapping[str, Any],
    inventory: Sequence[Any],
    subscription_id: str | None = None,
) -> list[str]:
    violations = validate_registry_manifest(manifest)
    if environment not in {"demo", "uat", "prod"}:
        violations.append("ENVIRONMENT_INVALID")
        return sorted(set(violations))
    registry = environment_registry(environment, subscription_id)
    release = {release_app_name(environment, member): image for member, image in manifest.get("images", {}).items()}
    expected = dict(release)
    expected.update(expected_dependencies(environment))
    actual: dict[str, Mapping[str, Any]] = {}
    for item in inventory:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            violations.append("INVENTORY_RECORD_INVALID")
            continue
        actual[str(item["name"])] = item
    if set(actual) != set(expected):
        violations.append("LIVE_MEMBERSHIP_INVALID")
    for name, image in expected.items():
        record = actual.get(name, {})
        image_matches = (
            release_image_matches(record.get("image"), image, registry) if name in release else record.get("image") == image
        )
        if not image_matches:
            violations.append(f"{name}:DIGEST_MISMATCH")
        if str(record.get("provisioningState", "")).lower() != "succeeded":
            violations.append(f"{name}:PROVISIONING_INCOMPLETE")
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--subscription-id",
        help="also accept release images at the same digest in this subscription's environment ACR (WC-127 image home)",
    )
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    violations = validate_inventory(args.environment, manifest, inventory, args.subscription_id)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

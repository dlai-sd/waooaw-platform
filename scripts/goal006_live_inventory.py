#!/usr/bin/env python3
"""Verify live Azure Container Apps equal one GOAL-006 exact-six release tuple."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from goal006_registry_manifest import RELEASE_MEMBERS, validate_registry_manifest  # noqa: F401

KEYCLOAK_IMAGE = "quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
IDENTITY_EDGE_IMAGE = "nginxinc/nginx-unprivileged@sha256:62a904036bfc0e4a4f2b556e34cbf17bc136b47fde8cdb4628762725f48c5782"
DEMO_TEMPORAL_IMAGE = "temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"


def expected_dependencies(environment: str) -> dict[str, str]:
    dependencies = {
        f"ca-{environment}-keycloak": KEYCLOAK_IMAGE,
        f"ca-{environment}-identity-edge": IDENTITY_EDGE_IMAGE,
    }
    if environment == "demo":
        dependencies[f"ca-{environment}-temporal"] = DEMO_TEMPORAL_IMAGE
    return dependencies


def validate_inventory(environment: str, manifest: Mapping[str, Any], inventory: Sequence[Any]) -> list[str]:
    violations = validate_registry_manifest(manifest)
    if environment not in {"demo", "uat", "prod"}:
        violations.append("ENVIRONMENT_INVALID")
        return sorted(set(violations))
    expected = {f"ca-{environment}-{member}": image for member, image in manifest.get("images", {}).items()}
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
        if record.get("image") != image:
            violations.append(f"{name}:DIGEST_MISMATCH")
        if str(record.get("provisioningState", "")).lower() != "succeeded":
            violations.append(f"{name}:PROVISIONING_INCOMPLETE")
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    violations = validate_inventory(args.environment, manifest, inventory)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

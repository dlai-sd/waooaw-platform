#!/usr/bin/env python3
"""Create fail-closed GOAL-006 Terraform workload inputs from a release tuple."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from goal006_registry_manifest import RELEASE_MEMBERS, validate_registry_manifest

LEASE_FIELDS = frozenset(
    {
        "lease_purpose",
        "manifest_digest",
        "owner_principal_id",
        "lease_issued_at",
        "lease_expires_at",
        "lease_state",
        "cost_centre",
        "evidence_digest",
    }
)


def create_inputs(
    environment: str,
    manifest: Mapping[str, Any],
    configuration: Mapping[str, Any],
    ghcr_packages_public_verified: bool,
) -> dict[str, Any]:
    violations = validate_registry_manifest(manifest)
    if violations:
        raise ValueError("invalid release manifest: " + ", ".join(violations))
    if environment not in {"demo", "uat", "prod"}:
        raise ValueError("environment must be demo, uat, or prod")
    if not ghcr_packages_public_verified:
        raise ValueError("anonymous digest pulls must be verified for all exact-six GHCR packages")
    secret_ids = configuration.get("key_vault_secret_ids")
    if not isinstance(secret_ids, Mapping) or set(secret_ids) != RELEASE_MEMBERS:
        raise ValueError("key_vault_secret_ids must contain exactly the six release members")
    if not all(isinstance(value, str) and value.startswith("/subscriptions/") for value in secret_ids.values()):
        raise ValueError("every Key Vault secret reference must be an Azure resource ID")
    for field in ("planned_incremental_monthly_cost_inr", "cumulative_one_time_cost_inr"):
        value = configuration.get(field)
        if not isinstance(value, int | float) or value < 0:
            raise ValueError(f"{field} must be a nonnegative accepted INR value")

    inputs: dict[str, Any] = {
        "ghcr_packages_public": True,
        "image_digests": dict(manifest["images"]),
        "key_vault_secret_ids": dict(secret_ids),
    }
    if environment in {"demo", "uat"}:
        missing = sorted(field for field in LEASE_FIELDS if not configuration.get(field))
        if missing:
            raise ValueError("missing lease fields: " + ", ".join(missing))
        inputs.update({field: configuration[field] for field in LEASE_FIELDS})
        inputs["lease_revoked_at"] = configuration.get("lease_revoked_at")
    else:
        for field in ("ce_min_replicas", "pr_min_replicas"):
            value = configuration.get(field)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field} must be an accepted positive integer")
            inputs[field] = value
    return inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ghcr-packages-public-verified", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    configuration = json.loads(args.configuration.read_text(encoding="utf-8"))
    inputs = create_inputs(
        args.environment,
        manifest,
        configuration,
        args.ghcr_packages_public_verified,
    )
    args.output.write_text(json.dumps(inputs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
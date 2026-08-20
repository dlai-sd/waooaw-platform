#!/usr/bin/env python3
"""Create fail-closed GOAL-006 Terraform workload inputs from a release tuple."""

from __future__ import annotations

import argparse
import ipaddress
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


def add_key_vault_references(
    configuration: Mapping[str, Any],
    key_vault_id: str,
    key_vault_uri: str,
) -> dict[str, Any]:
    if not key_vault_id.startswith("/subscriptions/") or "/vaults/" not in key_vault_id:
        raise ValueError("key_vault_id must be an Azure Key Vault resource ID")
    if not key_vault_uri.startswith("https://") or not key_vault_uri.endswith(".vault.azure.net/"):
        raise ValueError("key_vault_uri must be an Azure Key Vault URI")
    values = dict(configuration)
    values["key_vault_secret_uris"] = {
        member: f"{key_vault_uri}secrets/{member}" for member in RELEASE_MEMBERS
    }
    values["key_vault_secret_resource_ids"] = {
        member: f"{key_vault_id}/secrets/{member}" for member in RELEASE_MEMBERS
    }
    return values


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
    secret_uris = configuration.get("key_vault_secret_uris")
    if not isinstance(secret_uris, Mapping) or set(secret_uris) != RELEASE_MEMBERS:
        raise ValueError("key_vault_secret_uris must contain exactly the six release members")
    if not all(
        isinstance(value, str) and value.startswith("https://") and ".vault.azure.net/secrets/" in value
        for value in secret_uris.values()
    ):
        raise ValueError("every Key Vault runtime reference must be a versionless secret URI")
    secret_resource_ids = configuration.get("key_vault_secret_resource_ids")
    if not isinstance(secret_resource_ids, Mapping) or set(secret_resource_ids) != RELEASE_MEMBERS:
        raise ValueError("key_vault_secret_resource_ids must contain exactly the six release members")
    if not all(
        isinstance(value, str) and value.startswith("/subscriptions/") and "/secrets/" in value
        for value in secret_resource_ids.values()
    ):
        raise ValueError("every Key Vault RBAC scope must be a secret resource ID")
    for field in ("planned_incremental_monthly_cost_inr", "cumulative_one_time_cost_inr"):
        value = configuration.get(field)
        if not isinstance(value, int | float) or value < 0:
            raise ValueError(f"{field} must be a nonnegative accepted INR value")

    inputs: dict[str, Any] = {
        "ghcr_packages_public": True,
        "image_digests": dict(manifest["images"]),
        "key_vault_secret_uris": dict(secret_uris),
        "key_vault_secret_resource_ids": dict(secret_resource_ids),
    }
    if environment in {"demo", "uat"}:
        missing = sorted(field for field in LEASE_FIELDS if not configuration.get(field))
        if missing:
            raise ValueError("missing lease fields: " + ", ".join(missing))
        inputs.update({field: configuration[field] for field in LEASE_FIELDS})
        inputs["lease_revoked_at"] = configuration.get("lease_revoked_at")
        if environment == "demo":
            founder_ipv4_cidr = configuration.get("founder_ipv4_cidr")
            try:
                founder_network = ipaddress.ip_network(founder_ipv4_cidr, strict=True)
            except (TypeError, ValueError) as error:
                raise ValueError("founder_ipv4_cidr must be one nonzero IPv4 /32") from error
            if founder_network.version != 4 or founder_network.prefixlen != 32 or founder_network.network_address.is_unspecified:
                raise ValueError("founder_ipv4_cidr must be one nonzero IPv4 /32")
            inputs["founder_ipv4_cidr"] = founder_ipv4_cidr
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
    parser.add_argument("--key-vault-id")
    parser.add_argument("--key-vault-uri")
    parser.add_argument("--ghcr-packages-public-verified", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    configuration = json.loads(args.configuration.read_text(encoding="utf-8"))
    if bool(args.key_vault_id) != bool(args.key_vault_uri):
        parser.error("--key-vault-id and --key-vault-uri must be provided together")
    if args.key_vault_id:
        configuration = add_key_vault_references(configuration, args.key_vault_id, args.key_vault_uri)
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
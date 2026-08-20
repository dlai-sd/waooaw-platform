#!/usr/bin/env python3
"""Validate immutable GOAL-006 runner bootstrap inputs before Azure mutation."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any

EXPECTED_ENVIRONMENT = "demo"
EXPECTED_ACTIVATION = "INACTIVE"
EXPECTED_STATE_ID = (
    "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/"
    "waooaw-platform-rg/providers/Microsoft.Storage/storageAccounts/waooawp3tfstate2ed118"
)
EXPECTED_BOOTSTRAP_PRINCIPAL = "77147af5-a32d-4151-b557-e719f319b55b"
IMMUTABLE_IMAGE = re.compile(r"^[a-z0-9.-]+(?:/[a-z0-9._-]+)+@sha256:[0-9a-f]{64}$")
PROHIBITED_KEYS = {"clientsecret", "password", "privatekey", "runnertoken", "secretvalue"}
REQUIRED_TEMPLATE_TERMS = {
    "Microsoft.App/jobs",
    "Microsoft.App/managedEnvironments",
    "Microsoft.KeyVault/vaults",
    "Microsoft.ManagedIdentity/userAssignedIdentities",
    "Microsoft.Network/networkSecurityGroups",
    "Microsoft.Network/privateEndpoints",
    "Microsoft.Network/privateDnsZones",
    "Microsoft.Network/virtualNetworks",
    "Microsoft.OperationalInsights/workspaces",
    "*/5 * * * *",
    "replicaTimeout: 3600",
    "replicaTimeout: 120",
    "deny-inbound",
    "deny-other-egress",
}
REQUIRED_SUBSCRIPTION_TERMS = {
    "Microsoft.Consumption/budgets",
    "Microsoft.KeyVault/vaults/secrets/setSecret/action",
    "Microsoft.KeyVault/vaults/secrets/delete/action",
    "goal006-cumulative-monthly",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key).replace("_", "").replace("-", "").lower())
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def validate_bootstrap_manifest(repository_root: Path, manifest_path: Path) -> list[str]:
    violations: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        violations.append("MANIFEST_SCHEMA_INVALID")
    if manifest.get("environment") != EXPECTED_ENVIRONMENT:
        violations.append("ENVIRONMENT_INVALID")
    if manifest.get("activation_state") != EXPECTED_ACTIVATION:
        violations.append("ACTIVATION_NOT_INACTIVE")

    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        violations.append("MANIFEST_FILES_INVALID")
        files = {}
    for relative_path, expected_digest in files.items():
        path = repository_root / relative_path
        if not path.is_file():
            violations.append(f"FILE_MISSING:{relative_path}")
        elif not re.fullmatch(r"[0-9a-f]{64}", str(expected_digest)):
            violations.append(f"DIGEST_INVALID:{relative_path}")
        elif _digest(path) != expected_digest:
            violations.append(f"DIGEST_MISMATCH:{relative_path}")

    parameter_path = repository_root / "infrastructure/deployment-stacks/goal006-runner/demo.parameters.json"
    parameters_document = json.loads(parameter_path.read_text(encoding="utf-8"))
    parameters = {
        key: item.get("value") for key, item in parameters_document.get("parameters", {}).items()
    }
    if parameters.get("environment") != EXPECTED_ENVIRONMENT:
        violations.append("PARAMETER_ENVIRONMENT_INVALID")
    if parameters.get("activationState") != EXPECTED_ACTIVATION:
        violations.append("PARAMETER_ACTIVATION_NOT_INACTIVE")
    if parameters.get("stateStorageAccountId") != EXPECTED_STATE_ID:
        violations.append("STATE_STORAGE_ID_INVALID")
    if parameters.get("bootstrapPrincipalId") != EXPECTED_BOOTSTRAP_PRINCIPAL:
        violations.append("BOOTSTRAP_PRINCIPAL_INVALID")
    if parameters.get("monthlyBudgetInr") != 10000:
        violations.append("MONTHLY_BUDGET_INVALID")
    for name in ("runnerImage", "reconcilerImage"):
        if not IMMUTABLE_IMAGE.fullmatch(str(parameters.get(name, ""))):
            violations.append(f"IMAGE_NOT_IMMUTABLE:{name}")
    if PROHIBITED_KEYS.intersection(_walk_keys(parameters_document)):
        violations.append("PROHIBITED_CREDENTIAL_FIELD")

    try:
        vnet = ipaddress.ip_network(str(parameters["runnerVnetAddressPrefix"]))
        runner = ipaddress.ip_network(str(parameters["runnerSubnetAddressPrefix"]))
        endpoints = ipaddress.ip_network(str(parameters["privateEndpointSubnetAddressPrefix"]))
        if not runner.subnet_of(vnet) or not endpoints.subnet_of(vnet) or runner.overlaps(endpoints):
            violations.append("NETWORK_BOUNDARY_INVALID")
    except (KeyError, ValueError):
        violations.append("NETWORK_BOUNDARY_INVALID")

    template_text = (repository_root / "infrastructure/deployment-stacks/goal006-runner/main.bicep").read_text(
        encoding="utf-8"
    )
    for term in sorted(REQUIRED_TEMPLATE_TERMS):
        if term not in template_text:
            violations.append(f"TEMPLATE_CONTRACT_MISSING:{term}")
    subscription_text = (
        repository_root / "infrastructure/deployment-stacks/goal006-runner/subscription.bicep"
    ).read_text(encoding="utf-8")
    for term in sorted(REQUIRED_SUBSCRIPTION_TERMS):
        if term not in subscription_text:
            violations.append(f"SUBSCRIPTION_CONTRACT_MISSING:{term}")
    if "Key Vault Crypto User" in template_text or "Key Vault Secrets Officer" in template_text:
        violations.append("PREMATURE_OR_BROAD_KEY_VAULT_ROLE")
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    violations = validate_bootstrap_manifest(args.repository_root, args.manifest)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
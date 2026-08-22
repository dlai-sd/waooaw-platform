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

ALLOWED_ENVIRONMENTS = ("demo", "uat", "prod")
ALLOWED_ACTIVATION_STATES = {"INACTIVE", "ACTIVE"}
EXPECTED_STATE_ID = (
    "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/"
    "waooaw-platform-rg/providers/Microsoft.Storage/storageAccounts/waooawp3tfstate2ed118"
)
EXPECTED_BOOTSTRAP_PRINCIPAL = "77147af5-a32d-4151-b557-e719f319b55b"
EXPECTED_COST_ESTIMATE = {
    "planned_incremental_monthly_cost_inr": 1000,
    "cumulative_one_time_cost_inr": 1000,
    "source_run_id": 32371262629,
    "source_configuration": "deployment-config/demo/workload-configuration.json",
}
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
    "/opt/waooaw/entrypoint.sh",
    "RUNNER_VAULT_URL",
    "RUNNER_TOKEN_SECRET_NAME",
    "RUNNER_ACTIVATION_STATE",
    "resource brokerIdentity",
    "resource brokerJob",
    "resource cleanupBrokerJob",
    "name: '${prefix}-broker'",
    "name: '${prefix}-cleanup'",
    "args: ['start'",
    "args: ['cleanup-correlated'",
    "triggerType: activationState == 'ACTIVE' ? 'Schedule' : 'Manual'",
    "manualTriggerConfig:",
    "cronExpression: '*/5 * * * *'",
    "replicaTimeout: 3600",
    "replicaTimeout: 120",
    "replicaTimeout: 300",
    "deny-inbound",
    "deny-other-egress",
}
REQUIRED_PREREQUISITE_TERMS = {
    "Microsoft.Consumption/budgets",
    "Microsoft.KeyVault/vaults/secrets/setSecret/action",
    "Microsoft.KeyVault/vaults/secrets/delete",
    "Microsoft.App/jobs/start/action",
    "Microsoft.App/jobs/stop/execution/action",
    "goal006-cumulative-monthly",
    "adb29209-aa1d-457b-a786-c913953d2891",
    "prerequisites-rg.bicep",
}
REQUIRED_SUBSCRIPTION_TERMS = {
    "existing =",
    "runnerControlPlane",
}
EXPECTED_NETWORKS = {
    "demo": ("10.70.0.0/24", "10.70.0.0/27", "10.70.0.32/27"),
    "uat": ("10.71.0.0/24", "10.71.0.0/27", "10.71.0.32/27"),
    "prod": ("10.72.0.0/24", "10.72.0.0/27", "10.72.0.32/27"),
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


def _parameters(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return {key: item.get("value") for key, item in document.get("parameters", {}).items()}


def validate_bootstrap_manifest(
    repository_root: Path, manifest_path: Path, environment: str = "demo"
) -> list[str]:
    violations: list[str] = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if environment not in ALLOWED_ENVIRONMENTS:
        return ["ENVIRONMENT_INVALID"]
    if manifest.get("schema_version") != 3:
        violations.append("MANIFEST_SCHEMA_INVALID")

    environments = manifest.get("environments")
    if not isinstance(environments, dict) or set(environments) != set(ALLOWED_ENVIRONMENTS):
        violations.append("MANIFEST_ENVIRONMENTS_INVALID")
        environments = {}
    environment_record = environments.get(environment, {})
    manifest_activation = environment_record.get("activation_state")
    if manifest_activation not in ALLOWED_ACTIVATION_STATES:
        violations.append("ACTIVATION_STATE_INVALID")

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

    parameter_value = environment_record.get("parameters")
    prerequisite_value = environment_record.get("prerequisites")
    if not isinstance(parameter_value, str) or not isinstance(prerequisite_value, str):
        violations.append("ENVIRONMENT_RECORD_INVALID")
        return sorted(set(violations))
    parameter_path = repository_root / parameter_value
    prerequisite_parameter_path = repository_root / prerequisite_value
    if not parameter_path.is_file() or not prerequisite_parameter_path.is_file():
        violations.append("ENVIRONMENT_FILE_MISSING")
        return sorted(set(violations))
    parameters_document = json.loads(parameter_path.read_text(encoding="utf-8"))
    parameters = _parameters(parameter_path)
    if parameters.get("environment") != environment:
        violations.append("PARAMETER_ENVIRONMENT_INVALID")
    param_activation = parameters.get("activationState")
    if param_activation not in ALLOWED_ACTIVATION_STATES:
        violations.append("PARAMETER_ACTIVATION_STATE_INVALID")
    if param_activation != manifest_activation:
        violations.append("ACTIVATION_STATE_MISMATCH")
    if parameters.get("runnerResourceGroupName") != f"waooaw-{environment}-runner-rg":
        violations.append("RESOURCE_GROUP_INVALID")
    if parameters.get("stateStorageAccountId") != EXPECTED_STATE_ID:
        violations.append("STATE_STORAGE_ID_INVALID")
    if parameters.get("bootstrapPrincipalId") != EXPECTED_BOOTSTRAP_PRINCIPAL:
        violations.append("BOOTSTRAP_PRINCIPAL_INVALID")
    prerequisite_parameters = _parameters(prerequisite_parameter_path)
    if prerequisite_parameters.get("environment") != environment:
        violations.append("PREREQUISITE_ENVIRONMENT_INVALID")
    if prerequisite_parameters.get("monthlyBudgetInr") != 10000:
        violations.append("MONTHLY_BUDGET_INVALID")
    if prerequisite_parameters.get("runnerResourceGroupName") != parameters.get(
        "runnerResourceGroupName"
    ):
        violations.append("PREREQUISITE_RESOURCE_GROUP_MISMATCH")
    if prerequisite_parameters.get("bootstrapPrincipalId") != EXPECTED_BOOTSTRAP_PRINCIPAL:
        violations.append("PREREQUISITE_PRINCIPAL_INVALID")
    for name in ("runnerImage", "reconcilerImage"):
        if not IMMUTABLE_IMAGE.fullmatch(str(parameters.get(name, ""))):
            violations.append(f"IMAGE_NOT_IMMUTABLE:{name}")
    if param_activation == "ACTIVE" and (
        parameters.get("githubAppId") == "PENDING"
        or parameters.get("githubAppInstallationId") == "PENDING"
        or not str(parameters.get("githubAppId", "")).isdigit()
        or not str(parameters.get("githubAppInstallationId", "")).isdigit()
        or
        parameters.get("githubAppKeyName") == "PENDING"
        or parameters.get("githubAppKeyVersion") == "PENDING"
    ):
        violations.append("GITHUB_APP_KEY_NOT_CONFIGURED")
    if param_activation == "ACTIVE" and not str(parameters.get("runnerImage", "")).startswith(
        "ghcr.io/dlai-sd/goal006-private-runner@sha256:"
    ):
        violations.append("RUNNER_IMAGE_NOT_PUBLISHED")
    if PROHIBITED_KEYS.intersection(_walk_keys(parameters_document)):
        violations.append("PROHIBITED_CREDENTIAL_FIELD")

    cost_path = repository_root / "infrastructure/deployment-stacks/goal006-runner/cost-estimate.json"
    if json.loads(cost_path.read_text(encoding="utf-8")) != EXPECTED_COST_ESTIMATE:
        violations.append("COST_ESTIMATE_INVALID")

    observed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    try:
        vnet = ipaddress.ip_network(str(parameters["runnerVnetAddressPrefix"]))
        runner = ipaddress.ip_network(str(parameters["runnerSubnetAddressPrefix"]))
        endpoints = ipaddress.ip_network(str(parameters["privateEndpointSubnetAddressPrefix"]))
        if (
            tuple(str(item) for item in (vnet, runner, endpoints)) != EXPECTED_NETWORKS[environment]
            or not runner.subnet_of(vnet)
            or not endpoints.subnet_of(vnet)
            or runner.overlaps(endpoints)
        ):
            violations.append("NETWORK_BOUNDARY_INVALID")
    except (KeyError, ValueError):
        violations.append("NETWORK_BOUNDARY_INVALID")
    for item_environment in ALLOWED_ENVIRONMENTS:
        record = environments.get(item_environment, {})
        item_path_value = record.get("parameters")
        if not isinstance(item_path_value, str):
            continue
        item_path = repository_root / item_path_value
        if not item_path.is_file():
            continue
        try:
            item_network = ipaddress.ip_network(
                str(_parameters(item_path)["runnerVnetAddressPrefix"])
            )
        except (KeyError, ValueError):
            violations.append(f"{item_environment}:NETWORK_BOUNDARY_INVALID")
            continue
        if any(item_network.overlaps(observed) for observed in observed_networks):
            violations.append("CROSS_ENVIRONMENT_NETWORK_OVERLAP")
        observed_networks.append(item_network)

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
    prerequisite_text = (
        repository_root / "infrastructure/deployment-stacks/goal006-runner/prerequisites.bicep"
    ).read_text(encoding="utf-8")
    for term in sorted(REQUIRED_PREREQUISITE_TERMS):
        if term not in prerequisite_text:
            violations.append(f"PREREQUISITE_CONTRACT_MISSING:{term}")
    if "Key Vault Crypto User" in template_text or "Key Vault Secrets Officer" in template_text:
        violations.append("PREMATURE_OR_BROAD_KEY_VAULT_ROLE")
    if "bootstrapKeySignAccess" in template_text or "bootstrapSecretAccess" in template_text:
        violations.append("HOSTED_BOOTSTRAP_CREDENTIAL_AUTHORITY")
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--environment", choices=ALLOWED_ENVIRONMENTS, required=True)
    args = parser.parse_args()
    violations = validate_bootstrap_manifest(
        args.repository_root, args.manifest, args.environment
    )
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
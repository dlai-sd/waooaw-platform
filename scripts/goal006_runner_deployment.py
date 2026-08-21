#!/usr/bin/env python3
"""Plan, apply, and verify immutable GOAL-006 runner control planes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from goal006_runner_bootstrap import validate_bootstrap_manifest
from goal006_runner_prerequisites import _parameters, verify as verify_prerequisites

PLAN_SCHEMA = "waooaw.goal006-runner-plan/v1"
DEPLOYMENT_SCHEMA = "waooaw.goal006-runner-deployment/v1"
ALLOWED_CHANGE_TYPES = {"Create", "Ignore", "Modify", "NoChange"}
SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40}$")
STACK_ROOT = Path("infrastructure/deployment-stacks/goal006-runner")


def _run(arguments: list[str], *, capture: bool = True) -> str:
    result = subprocess.run(  # noqa: S603
        arguments,
        check=False,
        capture_output=capture,
        text=True,
    )
    if result.returncode:
        detail = "\n".join(part for part in (result.stderr, result.stdout) if part)
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(arguments)}\n{detail}")
    return result.stdout


def _az(*arguments: str) -> Any:
    output = _run(["az", *arguments, "--only-show-errors", "-o", "json"])
    try:
        return json.loads(output) if output.strip() else None
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Azure CLI returned non-JSON output: {output[:500]}") from error


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _digest_file(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def environment_contract(
    repository_root: Path, manifest_path: Path, environment: str
) -> dict[str, Any]:
    violations = validate_bootstrap_manifest(repository_root, manifest_path, environment)
    if violations:
        raise RuntimeError("invalid bootstrap manifest: " + ", ".join(violations))
    manifest = _read_json(manifest_path)
    record = manifest["environments"][environment]
    parameter_path = repository_root / record["parameters"]
    prerequisite_path = repository_root / record["prerequisites"]
    parameters = _parameters(parameter_path)
    return {
        "environment": environment,
        "location": parameters["location"],
        "resource_group": parameters["runnerResourceGroupName"],
        "stack_name": f"goal006-{environment}-private-runner",
        "prerequisite_deployment_name": f"goal006-{environment}-runner-prerequisites",
        "parameter_path": parameter_path,
        "prerequisite_path": prerequisite_path,
        "template_path": repository_root / STACK_ROOT / "subscription.bicep",
        "manifest_path": manifest_path,
        "activation_state": parameters["activationState"],
        "runner_image": parameters["runnerImage"],
        "reconciler_image": parameters["reconcilerImage"],
    }


def normalize_changes(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for change in changes:
        change_type = str(change.get("changeType", ""))
        resource_id = str(change.get("resourceId", ""))
        if change_type not in ALLOWED_CHANGE_TYPES:
            raise RuntimeError(f"unsupported or destructive change rejected: {change_type} {resource_id}")
        if not resource_id.startswith("/subscriptions/"):
            raise RuntimeError(f"invalid planned resource ID: {resource_id}")
        normalized.append(
            {
                "change_type": change_type,
                "resource_id": resource_id,
                "details": {
                    key: value
                    for key, value in change.items()
                    if key not in {"changeType", "resourceId"}
                },
            }
        )
    return sorted(normalized, key=lambda item: (item["resource_id"].lower(), item["change_type"]))


def _compile(template_path: Path) -> None:
    _run(["az", "bicep", "build", "--file", str(template_path), "--stdout"])


def create_plan(
    *,
    repository_root: Path,
    manifest_path: Path,
    environment: str,
    subscription_id: str,
    source_commit: str,
) -> dict[str, Any]:
    if environment != "demo":
        raise RuntimeError("live runner delivery is currently authorized only for Demo")
    if SOURCE_COMMIT.fullmatch(source_commit) is None:
        raise RuntimeError("source commit must be a full lowercase SHA")
    contract = environment_contract(repository_root, manifest_path, environment)
    _compile(contract["template_path"])
    prerequisite_parameters = _parameters(contract["prerequisite_path"])
    verify_prerequisites(
        prerequisite_parameters,
        subscription_id,
        contract["prerequisite_deployment_name"],
    )
    _az(
        "stack",
        "sub",
        "validate",
        "--name",
        contract["stack_name"],
        "--location",
        contract["location"],
        "--template-file",
        str(contract["template_path"]),
        "--parameters",
        f"@{contract['parameter_path']}",
        "--deny-settings-mode",
        "denyDelete",
        "--action-on-unmanage",
        "detachAll",
    )
    what_if = _az(
        "deployment",
        "sub",
        "what-if",
        "--name",
        f"{contract['stack_name']}-what-if",
        "--location",
        contract["location"],
        "--template-file",
        str(contract["template_path"]),
        "--parameters",
        f"@{contract['parameter_path']}",
        "--result-format",
        "FullResourcePayloads",
        "--no-pretty-print",
    )
    payload: dict[str, Any] = {
        "schema": PLAN_SCHEMA,
        "environment": environment,
        "source_commit": source_commit,
        "subscription_id": subscription_id,
        "stack_name": contract["stack_name"],
        "resource_group": contract["resource_group"],
        "location": contract["location"],
        "activation_state": contract["activation_state"],
        "manifest_digest": _digest_file(manifest_path),
        "parameter_digest": _digest_file(contract["parameter_path"]),
        "template_digest": _digest_file(contract["template_path"]),
        "runner_image": contract["runner_image"],
        "reconciler_image": contract["reconciler_image"],
        "changes": normalize_changes(what_if.get("changes", [])),
    }
    return {"payload": payload, "plan_digest": _digest_bytes(_canonical(payload))}


def validate_reviewed_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    payload = plan.get("payload")
    if not isinstance(payload, dict) or payload.get("schema") != PLAN_SCHEMA:
        raise RuntimeError("reviewed plan schema invalid")
    if plan.get("plan_digest") != _digest_bytes(_canonical(payload)):
        raise RuntimeError("reviewed plan digest invalid")
    return payload


def apply_reviewed_plan(
    *,
    reviewed_plan: Mapping[str, Any],
    repository_root: Path,
    manifest_path: Path,
    environment: str,
    subscription_id: str,
    source_commit: str,
) -> dict[str, Any]:
    current_plan = revalidate_reviewed_plan(
        reviewed_plan=reviewed_plan,
        repository_root=repository_root,
        manifest_path=manifest_path,
        environment=environment,
        subscription_id=subscription_id,
        source_commit=source_commit,
    )
    contract = environment_contract(repository_root, manifest_path, environment)
    _run(
        [
            "az",
            "stack",
            "sub",
            "create",
            "--name",
            contract["stack_name"],
            "--location",
            contract["location"],
            "--template-file",
            str(contract["template_path"]),
            "--parameters",
            f"@{contract['parameter_path']}",
            "--deny-settings-mode",
            "denyDelete",
            "--action-on-unmanage",
            "detachAll",
            "--yes",
            "--only-show-errors",
            "-o",
            "none",
        ]
    )
    return verify_deployment(
        repository_root=repository_root,
        manifest_path=manifest_path,
        environment=environment,
        source_commit=source_commit,
        plan_digest=str(current_plan["plan_digest"]),
    )


def revalidate_reviewed_plan(
    *,
    reviewed_plan: Mapping[str, Any],
    repository_root: Path,
    manifest_path: Path,
    environment: str,
    subscription_id: str,
    source_commit: str,
) -> dict[str, Any]:
    validate_reviewed_plan(reviewed_plan)
    current_plan = create_plan(
        repository_root=repository_root,
        manifest_path=manifest_path,
        environment=environment,
        subscription_id=subscription_id,
        source_commit=source_commit,
    )
    if current_plan != reviewed_plan:
        raise RuntimeError("current Azure plan differs from reviewed plan")
    return current_plan


def _required_resource_names(environment: str) -> dict[str, str]:
    prefix = f"goal006-{environment}-runner"
    return {
        f"{prefix}-logs": "Microsoft.OperationalInsights/workspaces",
        f"{prefix}-nsg": "Microsoft.Network/networkSecurityGroups",
        f"{prefix}-vnet": "Microsoft.Network/virtualNetworks",
        f"{prefix}-identity": "Microsoft.ManagedIdentity/userAssignedIdentities",
        f"{prefix}-cleanup-identity": "Microsoft.ManagedIdentity/userAssignedIdentities",
        f"waooaw-{environment}-runner-kv": "Microsoft.KeyVault/vaults",
        f"{prefix}-state-pe": "Microsoft.Network/privateEndpoints",
        f"{prefix}-vault-pe": "Microsoft.Network/privateEndpoints",
        f"{prefix}-aca": "Microsoft.App/managedEnvironments",
        f"{prefix}-job": "Microsoft.App/jobs",
        f"{prefix}-reconciler": "Microsoft.App/jobs",
    }


def verify_deployment(
    *,
    repository_root: Path,
    manifest_path: Path,
    environment: str,
    source_commit: str,
    plan_digest: str,
) -> dict[str, Any]:
    contract = environment_contract(repository_root, manifest_path, environment)
    stack = _az("stack", "sub", "show", "--name", contract["stack_name"])
    if stack.get("provisioningState") != "Succeeded":
        raise RuntimeError("deployment stack is not Succeeded")
    if str(stack.get("denySettings", {}).get("mode", "")).lower() != "denydelete":
        raise RuntimeError("deployment stack deny mode is not denyDelete")
    action_on_unmanage = stack.get("actionOnUnmanage", {})
    if any(
        str(action_on_unmanage.get(resource_type, "")).lower() != "detach"
        for resource_type in ("resources", "resourceGroups", "managementGroups")
    ):
        raise RuntimeError("deployment stack action on unmanage is not detachAll")
    managed_resource_ids = {
        str(item.get("id", "")).lower()
        for item in stack.get("resources", [])
        if str(item.get("status", "")).lower() == "managed"
    }
    resources = _az("resource", "list", "--resource-group", contract["resource_group"])
    observed = {
        (str(item.get("name")), str(item.get("type"))): str(item.get("id", "")).lower()
        for item in resources
    }
    missing = sorted(
        (name, resource_type)
        for name, resource_type in _required_resource_names(environment).items()
        if (name, resource_type) not in observed
    )
    if missing:
        raise RuntimeError(f"runner resources missing: {missing}")
    unmanaged = sorted(
        (name, resource_type)
        for name, resource_type in _required_resource_names(environment).items()
        if observed[(name, resource_type)] not in managed_resource_ids
    )
    if unmanaged:
        raise RuntimeError(f"runner resources are not managed by deployment stack: {unmanaged}")
    prefix = f"goal006-{environment}-runner"
    for endpoint in (f"{prefix}-state-pe", f"{prefix}-vault-pe"):
        resource = _az(
            "network",
            "private-endpoint",
            "show",
            "--resource-group",
            contract["resource_group"],
            "--name",
            endpoint,
        )
        connections = resource.get("privateLinkServiceConnections", [])
        statuses = {
            item.get("privateLinkServiceConnectionState", {}).get("status")
            for item in connections
        }
        if statuses != {"Approved"}:
            raise RuntimeError(f"private endpoint is not approved: {endpoint} {statuses}")
    runner_job = _az(
        "containerapp",
        "job",
        "show",
        "--resource-group",
        contract["resource_group"],
        "--name",
        f"{prefix}-job",
    )
    reconciler_job = _az(
        "containerapp",
        "job",
        "show",
        "--resource-group",
        contract["resource_group"],
        "--name",
        f"{prefix}-reconciler",
    )
    if runner_job.get("properties", {}).get("configuration", {}).get("triggerType") != "Manual":
        raise RuntimeError("runner job trigger is not Manual")
    reconciler_configuration = reconciler_job.get("properties", {}).get("configuration", {})
    if reconciler_configuration.get("triggerType") != "Schedule":
        raise RuntimeError("reconciler job trigger is not Schedule")
    if reconciler_configuration.get("scheduleTriggerConfig", {}).get("cronExpression") != "*/5 * * * *":
        raise RuntimeError("reconciler job schedule is not every five minutes")
    runner_executions = _az(
        "containerapp",
        "job",
        "execution",
        "list",
        "--resource-group",
        contract["resource_group"],
        "--name",
        f"{prefix}-job",
    )
    active_execution_states = {"processing", "running", "waiting"}
    if any(
        str(item.get("properties", {}).get("status", "")).lower()
        in active_execution_states
        for item in runner_executions
    ):
        raise RuntimeError("runner job has an active execution while blueprint is INACTIVE")
    expected_jobs = (
        (
            runner_job,
            "runner",
            contract["runner_image"],
            'test "$RUNNER_ACTIVATION_STATE" = "ACTIVE" && test -n "$ACTIONS_RUNNER_INPUT_JITCONFIG" && exec ./run.sh --jitconfig "$ACTIONS_RUNNER_INPUT_JITCONFIG" || exit 0',
        ),
        (
            reconciler_job,
            "reconciler",
            contract["reconciler_image"],
            'test "$RUNNER_ACTIVATION_STATE" = "ACTIVE" && exit 64 || exit 0',
        ),
    )
    for job, container_name, expected_image, expected_argument in expected_jobs:
        containers = job.get("properties", {}).get("template", {}).get("containers", [])
        container = next(
            (item for item in containers if item.get("name") == container_name),
            None,
        )
        if container is None or container.get("image") != expected_image:
            raise RuntimeError(f"{container_name} job image differs from reviewed blueprint")
        environment_values = {
            item.get("name"): item.get("value") for item in container.get("env", [])
        }
        if environment_values.get("RUNNER_ACTIVATION_STATE") != contract["activation_state"]:
            raise RuntimeError(f"{container_name} job activation state differs from blueprint")
        if container.get("args") != [expected_argument]:
            raise RuntimeError(f"{container_name} job fail-closed command differs from blueprint")
    payload: dict[str, Any] = {
        "schema": DEPLOYMENT_SCHEMA,
        "environment": environment,
        "source_commit": source_commit,
        "manifest_digest": _digest_file(manifest_path),
        "parameter_digest": _digest_file(contract["parameter_path"]),
        "plan_digest": plan_digest,
        "stack_name": contract["stack_name"],
        "resource_group": contract["resource_group"],
        "activation_state": contract["activation_state"],
        "verified": True,
    }
    return {"payload": payload, "record_digest": _digest_bytes(_canonical(payload))}


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preview", "review", "apply"))
    parser.add_argument("--environment", choices=("demo",), required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--manifest",
        type=Path,
        default=STACK_ROOT / "bootstrap-manifest.json",
    )
    parser.add_argument("--reviewed-plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    root = arguments.repository_root.resolve()
    manifest = arguments.manifest
    if not manifest.is_absolute():
        manifest = root / manifest
    try:
        if arguments.operation == "preview":
            result = create_plan(
                repository_root=root,
                manifest_path=manifest,
                environment=arguments.environment,
                subscription_id=arguments.subscription_id,
                source_commit=arguments.source_commit,
            )
        elif arguments.operation in {"review", "apply"}:
            if arguments.reviewed_plan is None:
                parser.error("review and apply require --reviewed-plan")
            reviewed_plan = _read_json(arguments.reviewed_plan)
            common = {
                "reviewed_plan": reviewed_plan,
                "repository_root": root,
                "manifest_path": manifest,
                "environment": arguments.environment,
                "subscription_id": arguments.subscription_id,
                "source_commit": arguments.source_commit,
            }
            result = (
                apply_reviewed_plan(**common)
                if arguments.operation == "apply"
                else revalidate_reviewed_plan(**common)
            )
        _write_json(arguments.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except RuntimeError as error:
        print(json.dumps({"passed": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
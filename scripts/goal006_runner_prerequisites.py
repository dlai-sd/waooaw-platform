#!/usr/bin/env python3
"""Preview, apply, and verify GOAL-006 runner bootstrap prerequisites."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ALLOWED_ENVIRONMENTS = {"demo", "uat", "prod"}
BUILT_IN_ROLES = {
    "Azure Deployment Stack Owner": "adb29209-aa1d-457b-a786-c913953d2891",
    "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
    "Role Based Access Control Administrator": "f58310d9-a9f6-439a-9e8d-f62e7b41a168",
}


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


def _parameters(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return {name: item["value"] for name, item in document["parameters"].items()}


def verify_role_catalogue() -> None:
    for expected_name, role_id in BUILT_IN_ROLES.items():
        definitions = _az("role", "definition", "list", "--name", role_id)
        if len(definitions) != 1 or definitions[0].get("roleName") != expected_name:
            raise RuntimeError(f"Azure built-in role mismatch: {expected_name} ({role_id})")


def reject_deletes(changes: list[dict[str, Any]]) -> None:
    destructive = [change for change in changes if change.get("changeType") == "Delete"]
    if destructive:
        raise RuntimeError(f"prerequisite deletes rejected: {json.dumps(destructive)}")


def preview(
    template: Path,
    parameter_path: Path,
    *,
    deployment_name: str,
    location: str,
) -> dict[str, Any]:
    _run(
        [
            "az",
            "deployment",
            "sub",
            "validate",
            "--name",
            f"{deployment_name}-validate",
            "--location",
            location,
            "--template-file",
            str(template),
            "--parameters",
            f"@{parameter_path}",
            "--only-show-errors",
            "-o",
            "none",
        ]
    )
    result = _az(
        "deployment",
        "sub",
        "what-if",
        "--name",
        f"{deployment_name}-what-if",
        "--location",
        location,
        "--template-file",
        str(template),
        "--parameters",
        f"@{parameter_path}",
        "--result-format",
        "FullResourcePayloads",
        "--no-pretty-print",
    )
    changes = result.get("changes", [])
    reject_deletes(changes)
    return {
        "changes": len(changes),
        "change_types": sorted({change.get("changeType") for change in changes}),
        "resources": [
            {
                "change_type": change.get("changeType"),
                "resource_id": change.get("resourceId"),
            }
            for change in changes
        ],
    }


def apply(
    template: Path,
    parameter_path: Path,
    *,
    deployment_name: str,
    location: str,
) -> None:
    _run(
        [
            "az",
            "deployment",
            "sub",
            "create",
            "--name",
            deployment_name,
            "--location",
            location,
            "--template-file",
            str(template),
            "--parameters",
            f"@{parameter_path}",
            "--only-show-errors",
            "-o",
            "none",
        ]
    )


def verify(parameters: dict[str, Any], subscription_id: str) -> dict[str, Any]:
    environment = str(parameters["environment"])
    resource_group = str(parameters["runnerResourceGroupName"])
    principal_id = str(parameters["bootstrapPrincipalId"])
    subscription_scope = f"/subscriptions/{subscription_id}"
    runner_scope = f"{subscription_scope}/resourceGroups/{resource_group}"
    group = _az("group", "show", "--name", resource_group)
    assignments = _az(
        "role",
        "assignment",
        "list",
        "--assignee-object-id",
        principal_id,
        "--include-inherited",
        "--all",
    )
    observed = {
        (str(item.get("roleDefinitionName")), str(item.get("scope", "")).lower())
        for item in assignments
    }
    required = {
        ("Azure Deployment Stack Owner", subscription_scope.lower()),
        ("Contributor", runner_scope.lower()),
        ("Role Based Access Control Administrator", runner_scope.lower()),
    }
    missing = sorted(required - observed)
    if missing:
        raise RuntimeError(f"missing bootstrap role assignments: {missing}")
    budget = _az(
        "rest",
        "--method",
        "get",
        "--url",
        f"https://management.azure.com{subscription_scope}/providers/"
        "Microsoft.Consumption/budgets/goal006-cumulative-monthly?api-version=2023-11-01",
    )
    if float(budget["properties"]["amount"]) != float(parameters["monthlyBudgetInr"]):
        raise RuntimeError("cumulative budget amount mismatch")
    for suffix in ("Bootstrap Secret Writer", "Cleanup Secret Deleter"):
        role_name = f"GOAL-006 {environment} {suffix}"
        definitions = _az("role", "definition", "list", "--name", role_name)
        if len(definitions) != 1 or runner_scope.lower() not in {
            str(scope).lower() for scope in definitions[0].get("assignableScopes", [])
        }:
            raise RuntimeError(f"custom role scope mismatch: {role_name}")
    return {
        "environment": environment,
        "resource_group_id": group["id"],
        "verified_roles": sorted(role for role, _ in required),
        "budget_inr": parameters["monthlyBudgetInr"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=sorted(ALLOWED_ENVIRONMENTS), required=True)
    parser.add_argument("--parameters", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--location", default="centralindia")
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    parameters = _parameters(arguments.parameters)
    if parameters.get("environment") != arguments.environment:
        parser.error("--environment must match the reviewed parameter file")
    deployment_name = f"goal006-{arguments.environment}-runner-prerequisites"
    try:
        verify_role_catalogue()
        result: dict[str, Any] = {
            "environment": arguments.environment,
            "preview": preview(
                arguments.template,
                arguments.parameters,
                deployment_name=deployment_name,
                location=arguments.location,
            ),
            "applied": arguments.apply,
        }
        if arguments.apply:
            apply(
                arguments.template,
                arguments.parameters,
                deployment_name=deployment_name,
                location=arguments.location,
            )
            result["verification"] = verify(parameters, arguments.subscription_id)
        print(json.dumps(result, sort_keys=True))
        return 0
    except RuntimeError as error:
        print(json.dumps({"passed": False, "error": str(error)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
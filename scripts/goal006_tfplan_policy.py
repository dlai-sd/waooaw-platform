"""Fail closed when a GOAL-006 foundation plan would destroy resources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


KNOWN_ACTIONS = frozenset({"no-op", "create", "read", "update", "delete"})
TEMPORAL_ADDRESS = "module.workload.azurerm_container_app.temporal[0]"


def destructive_changes(plan: dict[str, Any]) -> list[str]:
    """Return resource addresses whose planned actions include deletion."""
    resource_changes = plan.get("resource_changes")
    if not isinstance(resource_changes, list):
        raise ValueError("Terraform plan must contain a resource_changes list")

    destructive: list[str] = []
    for resource_change in resource_changes:
        if not isinstance(resource_change, dict):
            raise ValueError("Terraform resource change must be an object")
        address = resource_change.get("address")
        change = resource_change.get("change")
        actions = change.get("actions") if isinstance(change, dict) else None
        if not isinstance(address, str) or not address:
            raise ValueError("Terraform resource change must have an address")
        if not isinstance(actions, list) or not actions or not all(isinstance(action, str) for action in actions):
            raise ValueError(f"Terraform resource change {address} has invalid actions")
        unknown_actions = set(actions) - KNOWN_ACTIONS
        if unknown_actions:
            raise ValueError(f"Terraform resource change {address} has unknown actions: {', '.join(sorted(unknown_actions))}")
        if "delete" in actions:
            destructive.append(address)
    return destructive


def enforce_plan(plan: dict[str, Any], scope: str) -> None:
    """Reject deletion and replacement in an application plan."""
    destructive = destructive_changes(plan)
    if destructive:
        raise ValueError(f"{scope.capitalize()} plan contains delete or replacement actions: " + ", ".join(destructive))
    if scope == "workload":
        enforce_temporal_contract(plan)


def enforce_temporal_contract(plan: dict[str, Any]) -> None:
    """Require the Demo Temporal plan to preserve its non-destructive lifecycle contract."""
    changes = plan["resource_changes"]
    temporal_changes = [change for change in changes if change.get("address") == TEMPORAL_ADDRESS]
    if not temporal_changes:
        return
    after = temporal_changes[0].get("change", {}).get("after")
    try:
        template = after["template"][0]
        containers = {container["name"]: container for container in template["container"]}
        temporal = containers["temporal"]
        postgres = containers["postgres"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("Workload plan has an incomplete Demo Temporal contract") from error
    violations: list[str] = []
    if template.get("min_replicas") != 1 or template.get("max_replicas") != 1:
        violations.append("Temporal must run exactly one replica")
    if temporal.get("startup_probe"):
        violations.append("Temporal startup probe must be absent")
    if temporal.get("readiness_probe"):
        violations.append("Temporal readiness probe must be absent")
    for name, container in (("Temporal", temporal), ("PostgreSQL", postgres)):
        if "@sha256:" not in str(container.get("image", "")):
            violations.append(f"{name} image must be digest-pinned")
    if violations:
        raise ValueError("Workload plan violates Demo Temporal contract: " + "; ".join(violations))


def enforce_foundation_plan(plan: dict[str, Any]) -> None:
    """Preserve the foundation-specific policy API for existing callers."""
    enforce_plan(plan, "foundation")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--scope", required=True, choices=("foundation", "workload"))
    arguments = parser.parse_args()
    try:
        plan = json.loads(arguments.plan.read_text(encoding="utf-8"))
        if not isinstance(plan, dict):
            raise ValueError("Terraform plan JSON must be an object")
        enforce_plan(plan, arguments.scope)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"status": "PASS", "destructive_changes": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

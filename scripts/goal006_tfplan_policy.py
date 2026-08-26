"""Fail closed when a GOAL-006 foundation plan would destroy resources."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


KNOWN_ACTIONS = frozenset({"no-op", "create", "read", "update", "delete"})


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
        if not isinstance(actions, list) or not actions or not all(
            isinstance(action, str) for action in actions
        ):
            raise ValueError(f"Terraform resource change {address} has invalid actions")
        unknown_actions = set(actions) - KNOWN_ACTIONS
        if unknown_actions:
            raise ValueError(
                f"Terraform resource change {address} has unknown actions: "
                f"{', '.join(sorted(unknown_actions))}"
            )
        if "delete" in actions:
            destructive.append(address)
    return destructive


def enforce_plan(plan: dict[str, Any], scope: str) -> None:
    """Reject deletion and replacement in an application plan."""
    destructive = destructive_changes(plan)
    if destructive:
        raise ValueError(
            f"{scope.capitalize()} plan contains delete or replacement actions: "
            + ", ".join(destructive)
        )


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
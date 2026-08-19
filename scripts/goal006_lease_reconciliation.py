#!/usr/bin/env python3
"""Validate GOAL-006 lease eligibility and deletion-only Terraform plans."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_ENVIRONMENTS = frozenset({"demo", "uat"})
DISPOSABLE_PREFIXES = (
    "module.workload.azurerm_container_app.member",
    "module.workload.azurerm_role_assignment.member_secret",
    "module.workload.azurerm_user_assigned_identity.member",
)


def lease_requires_reconciliation(inputs: Mapping[str, Any], now: datetime) -> bool:
    if inputs.get("lease_state") == "REVOKED":
        return inputs.get("lease_revoked_at") is not None
    if inputs.get("lease_state") != "ACTIVE":
        raise ValueError("lease state must be ACTIVE or REVOKED")
    try:
        expiry = datetime.fromisoformat(str(inputs["lease_expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError) as exc:
        raise ValueError("lease expiry must be RFC3339") from exc
    return expiry <= now.astimezone(timezone.utc)


def validate_deletion_plan(environment: str, plan: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    if environment not in ALLOWED_ENVIRONMENTS:
        violations.append("PRODUCTION_RECONCILIATION_PROHIBITED")
    for change in plan.get("resource_changes", []):
        actions = change.get("change", {}).get("actions")
        if actions in (["no-op"], ["read"]):
            continue
        address = str(change.get("address", ""))
        if actions != ["delete"] or not address.startswith(DISPOSABLE_PREFIXES):
            violations.append(f"MUTATION_PROHIBITED:{address}:{actions}")
    return sorted(violations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--inputs", type=Path)
    parser.add_argument("--plan", type=Path)
    args = parser.parse_args()
    if args.environment not in ALLOWED_ENVIRONMENTS:
        raise SystemExit("Production lease reconciliation is prohibited")
    if args.inputs is not None:
        inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
        print("true" if lease_requires_reconciliation(inputs, datetime.now(timezone.utc)) else "false")
        return 0
    if args.plan is None:
        parser.error("either --inputs or --plan is required")
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    violations = validate_deletion_plan(args.environment, plan)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
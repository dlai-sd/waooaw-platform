#!/usr/bin/env python3
"""Validate local WC-124 recovery, capacity, cost, and rollback evidence."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SHA256 = re.compile(r"sha256:[0-9a-f]{64}$")
LIMITS = {
    "demo": {"postgresql": 40, "pgbouncer": 40, "sleep_cost": 1100},
    "uat": {"postgresql": 100, "pgbouncer": 80, "sleep_cost": 1600},
}


def validate_qualification(evidence: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    environment = str(evidence.get("environment", ""))
    limits = LIMITS.get(environment)
    if limits is None:
        return ["ENVIRONMENT_INVALID"]
    if evidence.get("mode") != "local_synthetic_no_provider_claim":
        violations.append("PROVIDER_CLAIM_INVALID")

    recovery = evidence.get("recovery", {})
    if not isinstance(recovery, Mapping):
        recovery = {}
    if recovery.get("sanitized") is not True or recovery.get("isolated") is not True:
        violations.append("RESTORE_FIXTURE_UNSAFE")
    if recovery.get("migration_applied_twice") is not True:
        violations.append("MIGRATION_IDEMPOTENCY_UNPROVEN")
    if recovery.get("prior_release_readable") is not True:
        violations.append("PRIOR_RELEASE_INCOMPATIBLE")
    if not all(
        recovery.get(field) is True
        for field in (
            "role_matrix_passed",
            "force_rls_passed",
            "constitutional_reconciliation_passed",
            "financial_reconciliation_passed",
        )
    ):
        violations.append("RESTORE_INVARIANT_FAILED")
    if not isinstance(recovery.get("rpo_minutes"), (int, float)) or recovery["rpo_minutes"] > 5:
        violations.append("RPO_EXCEEDED")
    if not isinstance(recovery.get("rto_minutes"), (int, float)) or recovery["rto_minutes"] > 30:
        violations.append("RTO_EXCEEDED")

    capacity = evidence.get("capacity", {})
    if not isinstance(capacity, Mapping):
        capacity = {}
    for key in ("postgresql", "pgbouncer"):
        accepted = limits[key]
        if capacity.get(f"{key}_limit") != accepted:
            violations.append(f"{key.upper()}_LIMIT_DRIFT")
        planned = capacity.get(f"{key}_planned")
        if not isinstance(planned, int) or planned < 0 or planned > accepted * 0.8:
            violations.append(f"{key.upper()}_CAPACITY_EXCEEDED")

    cost = evidence.get("cost", {})
    if not isinstance(cost, Mapping):
        cost = {}
    if cost.get("currency") != "INR" or cost.get("tax_basis") != "before_GST":
        violations.append("COST_BASIS_INVALID")
    if cost.get("sleeping_monthly") != limits["sleep_cost"]:
        violations.append("SLEEP_COST_DRIFT")
    if not isinstance(cost.get("combined_sleeping_monthly"), (int, float)) or cost["combined_sleeping_monthly"] > 3200:
        violations.append("SLEEP_COST_RESERVE_EXCEEDED")
    if not isinstance(cost.get("active_monthly"), (int, float)) or cost["active_monthly"] > 10000:
        violations.append("ACTIVE_COST_STOP_EXCEEDED")

    rollback = evidence.get("rollback", {})
    if not isinstance(rollback, Mapping):
        rollback = {}
    prior_tuple = rollback.get("immutable_prior_tuple", {})
    if (
        not isinstance(prior_tuple, Mapping)
        or set(prior_tuple)
        != {
            "configuration",
            "dependency",
            "migration",
            "plan",
            "release",
            "schema",
            "secret_catalog",
        }
        or any(SHA256.fullmatch(str(value)) is None for value in prior_tuple.values())
    ):
        violations.append("ROLLBACK_TUPLE_INVALID")
    if rollback.get("additive_schema_retained") is not True:
        violations.append("ROLLBACK_SCHEMA_DESTRUCTIVE")
    if rollback.get("uncertain_state_enters_recovery_hold") is not True:
        violations.append("ROLLBACK_HOLD_MISSING")
    if rollback.get("provider_mutation_performed") is not False:
        violations.append("UNAUTHORIZED_PROVIDER_MUTATION_CLAIM")

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    arguments = parser.parse_args()
    evidence = json.loads(arguments.evidence.read_text(encoding="utf-8"))
    violations = validate_qualification(evidence)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())

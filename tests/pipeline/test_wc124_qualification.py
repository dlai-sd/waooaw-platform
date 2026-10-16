from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.wc124_qualification import validate_qualification


FIXTURE = Path("infrastructure/recovery/phase2/fixtures/wc124-demo-qualification.json")


def evidence() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_demo_local_qualification_contract_passes_without_provider_claim() -> None:
    assert validate_qualification(evidence()) == []


@pytest.mark.parametrize(
    ("section", "field", "value", "violation"),
    [
        ("recovery", "rpo_minutes", 5.01, "RPO_EXCEEDED"),
        ("recovery", "rto_minutes", 30.01, "RTO_EXCEEDED"),
        ("capacity", "postgresql_planned", 33, "POSTGRESQL_CAPACITY_EXCEEDED"),
        ("capacity", "pgbouncer_planned", 33, "PGBOUNCER_CAPACITY_EXCEEDED"),
        ("cost", "combined_sleeping_monthly", 3201, "SLEEP_COST_RESERVE_EXCEEDED"),
        ("cost", "active_monthly", 10001, "ACTIVE_COST_STOP_EXCEEDED"),
        ("rollback", "additive_schema_retained", False, "ROLLBACK_SCHEMA_DESTRUCTIVE"),
        ("rollback", "uncertain_state_enters_recovery_hold", False, "ROLLBACK_HOLD_MISSING"),
        ("rollback", "provider_mutation_performed", True, "UNAUTHORIZED_PROVIDER_MUTATION_CLAIM"),
    ],
)
def test_qualification_thresholds_fail_closed(
    section: str, field: str, value: object, violation: str
) -> None:
    mutated = copy.deepcopy(evidence())
    mutated[section][field] = value
    assert violation in validate_qualification(mutated)


def test_restore_invariants_and_prior_release_compatibility_are_blocking() -> None:
    mutated = evidence()
    mutated["recovery"]["prior_release_readable"] = False
    mutated["recovery"]["force_rls_passed"] = False
    violations = validate_qualification(mutated)
    assert "PRIOR_RELEASE_INCOMPATIBLE" in violations
    assert "RESTORE_INVARIANT_FAILED" in violations


def test_rollback_requires_complete_immutable_prior_tuple() -> None:
    mutated = evidence()
    del mutated["rollback"]["immutable_prior_tuple"]["plan"]
    assert "ROLLBACK_TUPLE_INVALID" in validate_qualification(mutated)

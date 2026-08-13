#!/usr/bin/env python3
"""Simulate the GOAL-006 C-067 release path without provider or traffic access."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from goal006_manifest import validate_manifest
from goal006_recovery import validate_bundle

SUCCESS_SEQUENCE = (
    "BUILD_ONCE",
    "VERIFY",
    "SIGNED_SIX_MEMBER_IMMUTABLE_MANIFEST",
    "PROMOTE_EXACT_DIGESTS",
    "GREEN_REVISION_AT_0_PERCENT",
    "VERIFY_GREEN",
    "BOUNDED_CANARY",
    "INDEPENDENT_CONFIRMATION",
    "GREEN_AT_100_PERCENT",
    "OBSERVE",
    "DEACTIVATE_BLUE_WITHIN_30_MINUTES",
)
FAILURE_SEQUENCE = (
    "RESTORE_BLUE_100_PERCENT",
    "DEACTIVATE_GREEN",
    "PRESERVE_FAILURE_EVIDENCE",
    "FAIL_RELEASE",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _event(state: str, blue: int, green: int, elapsed_seconds: int) -> dict[str, Any]:
    return {"state": state, "blue_weight": blue, "green_weight": green, "elapsed_seconds": elapsed_seconds}


def _failure(events: list[dict[str, Any]], elapsed_seconds: int, reason: str) -> dict[str, Any]:
    events.extend(_event(state, 100, 0, elapsed_seconds) for state in FAILURE_SEQUENCE)
    return {
        "status": "failed",
        "reason": reason,
        "events": events,
        "failure_evidence_preserved": True,
        "final_traffic": {"blue": 100, "green": 0},
        "provider_actions": 0,
    }


def simulate_release(
    policy: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_root: Path,
    recovery: Mapping[str, Any],
    recovery_root: Path,
) -> dict[str, Any]:
    """Return deterministic success or fail-closed transition evidence."""
    if policy.get("mode") != "offline_synthetic" or policy.get("live_actions_authorized") is not False:
        return _failure([], 0, "OFFLINE_BOUNDARY_INVALID")
    if tuple(_sequence(policy.get("requested_sequence"))) != SUCCESS_SEQUENCE:
        return _failure([], 0, "TRANSITION_SEQUENCE_INVALID")
    if policy.get("concurrency_key") != "goal006-phase2-release" or policy.get("concurrent_release_active") is not False:
        return _failure([], 0, "CONCURRENCY_GATE_FAILED")
    if policy.get("autonomous_halt") is not False:
        return _failure([], 0, "AUTONOMOUS_HALT_ACTIVE")
    if policy.get("workload_lease_active") is not True:
        return _failure([], 0, "WORKLOAD_LEASE_INACTIVE")
    if policy.get("drift_status") != "clean":
        return _failure([], 0, "DRIFT_GATE_FAILED")

    estimated_cost = policy.get("estimated_monthly_cost_inr")
    ceiling = policy.get("monthly_cost_ceiling_inr")
    if not isinstance(estimated_cost, int | float) or not isinstance(ceiling, int | float) or estimated_cost < 0 or estimated_cost > ceiling:
        return _failure([], 0, "COST_GATE_FAILED")
    if validate_manifest(manifest, manifest_root):
        return _failure([], 0, "MANIFEST_GATE_FAILED")
    if validate_bundle(recovery, recovery_root):
        return _failure([], 0, "RECOVERY_TUPLE_GATE_FAILED")

    canary_weight = policy.get("canary_weight")
    canary_seconds = policy.get("canary_duration_seconds")
    observation_seconds = policy.get("observation_duration_seconds")
    deadline_seconds = policy.get("blue_deactivation_deadline_seconds")
    if not isinstance(canary_weight, int) or not 0 < canary_weight < 100:
        return _failure([], 0, "CANARY_WEIGHT_INVALID")
    if not isinstance(canary_seconds, int) or canary_seconds <= 0:
        return _failure([], 0, "CANARY_DURATION_INVALID")
    if not isinstance(observation_seconds, int) or observation_seconds <= 0:
        return _failure([], 0, "OBSERVATION_DURATION_INVALID")
    if deadline_seconds != 1800 or observation_seconds > deadline_seconds:
        return _failure([], 0, "BLUE_DEACTIVATION_DEADLINE_INVALID")

    identities = _mapping(policy.get("identities"))
    author = identities.get("author")
    executor = identities.get("executor")
    confirmer = identities.get("independent_confirmer")
    if not all(isinstance(identity, str) and identity for identity in (author, executor, confirmer)):
        return _failure([], 0, "IDENTITY_GATE_FAILED")
    if confirmer in {author, executor} or author == executor:
        return _failure([], 0, "INDEPENDENCE_GATE_FAILED")
    confirmation = _mapping(policy.get("confirmation_evidence"))
    required_confirmation = {"manifest_verified", "green_at_zero_verified", "canary_healthy", "constitutional_gates_passed"}
    if set(confirmation) != required_confirmation or not all(confirmation.values()):
        return _failure([], 0, "CONFIRMATION_EVIDENCE_FAILED")

    events: list[dict[str, Any]] = []
    blue, green, elapsed_seconds = 100, 0, 0
    fail_at = policy.get("inject_failure_at")
    for state in SUCCESS_SEQUENCE:
        if state == "BOUNDED_CANARY":
            blue, green = 100 - canary_weight, canary_weight
            elapsed_seconds += canary_seconds
        elif state == "GREEN_AT_100_PERCENT":
            blue, green = 0, 100
        elif state == "OBSERVE":
            elapsed_seconds += observation_seconds
        if blue + green != 100 or min(blue, green) < 0:
            return _failure(events, elapsed_seconds, "TRAFFIC_CONSERVATION_FAILED")
        events.append(_event(state, blue, green, elapsed_seconds))
        if fail_at == state:
            return _failure(events, elapsed_seconds, f"INJECTED_GATE_FAILURE:{state}")

    confirmation_elapsed = next(event["elapsed_seconds"] for event in events if event["state"] == "INDEPENDENT_CONFIRMATION")
    deactivation_elapsed = events[-1]["elapsed_seconds"]
    if deactivation_elapsed - confirmation_elapsed > deadline_seconds:
        return _failure(events, deactivation_elapsed, "BLUE_DEACTIVATION_DEADLINE_EXCEEDED")
    return {
        "status": "passed",
        "events": events,
        "failure_evidence_preserved": False,
        "final_traffic": {"blue": 0, "green": 100},
        "provider_actions": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("recovery", type=Path)
    args = parser.parse_args()
    policy_path, manifest_path, recovery_path = (path.resolve() for path in (args.policy, args.manifest, args.recovery))
    policy = _mapping(json.loads(policy_path.read_text(encoding="utf-8")))
    manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")))
    recovery = _mapping(json.loads(recovery_path.read_text(encoding="utf-8")))
    result = simulate_release(policy, manifest, manifest_path.parent, recovery, recovery_path.parent)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
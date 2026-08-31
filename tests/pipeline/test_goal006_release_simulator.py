from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from goal006_release_simulator import FAILURE_SEQUENCE, SUCCESS_SEQUENCE, simulate_release

RELEASE_ROOT = Path("release/goal006")
RECOVERY_ROOT = Path("infrastructure/recovery/phase2/fixtures")
CI_PATH = Path(".github/workflows/ci.yaml")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        load_json(RELEASE_ROOT / "promotion-policy.json"),
        load_json(RELEASE_ROOT / "release-manifest.json"),
        load_json(RECOVERY_ROOT / "valid-recovery-bundle.json"),
    )


def simulate(policy: dict[str, Any], manifest: dict[str, Any], recovery: dict[str, Any]) -> dict[str, Any]:
    return simulate_release(policy, manifest, RELEASE_ROOT, recovery, RECOVERY_ROOT)


def test_complete_success_path_is_exact_and_provider_free() -> None:
    policy, manifest, recovery = inputs()
    result = simulate(policy, manifest, recovery)
    assert result["status"] == "passed"
    assert tuple(event["state"] for event in result["events"]) == SUCCESS_SEQUENCE
    assert result["final_traffic"] == {"blue": 0, "green": 100}
    assert result["provider_actions"] == 0


def test_success_path_conserves_traffic_at_every_transition() -> None:
    policy, manifest, recovery = inputs()
    result = simulate(policy, manifest, recovery)
    assert all(event["blue_weight"] + event["green_weight"] == 100 for event in result["events"])
    canary = next(event for event in result["events"] if event["state"] == "BOUNDED_CANARY")
    assert canary["green_weight"] == policy["canary_weight"]


@pytest.mark.parametrize("gate", SUCCESS_SEQUENCE[1:])
def test_every_post_build_gate_failure_restores_blue_and_preserves_evidence(gate: str) -> None:
    policy, manifest, recovery = inputs()
    policy["inject_failure_at"] = gate
    result = simulate(policy, manifest, recovery)
    assert result["status"] == "failed"
    assert tuple(event["state"] for event in result["events"][-4:]) == FAILURE_SEQUENCE
    assert result["final_traffic"] == {"blue": 100, "green": 0}
    assert result["failure_evidence_preserved"] is True
    assert result["provider_actions"] == 0


def test_transition_reordering_is_rejected_before_forward_progress() -> None:
    policy, manifest, recovery = inputs()
    policy["requested_sequence"][4], policy["requested_sequence"][5] = policy["requested_sequence"][5], policy["requested_sequence"][4]
    result = simulate(policy, manifest, recovery)
    assert result["reason"] == "TRANSITION_SEQUENCE_INVALID"
    assert tuple(event["state"] for event in result["events"]) == FAILURE_SEQUENCE


@pytest.mark.parametrize("weight", [-1, 0, 100, 101, 1.5])
def test_canary_weight_must_be_a_bounded_integer(weight: object) -> None:
    policy, manifest, recovery = inputs()
    policy["canary_weight"] = weight
    assert simulate(policy, manifest, recovery)["reason"] == "CANARY_WEIGHT_INVALID"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("canary_duration_seconds", 0, "CANARY_DURATION_INVALID"),
        ("observation_duration_seconds", 0, "OBSERVATION_DURATION_INVALID"),
        ("observation_duration_seconds", 1801, "BLUE_DEACTIVATION_DEADLINE_INVALID"),
        ("blue_deactivation_deadline_seconds", 1801, "BLUE_DEACTIVATION_DEADLINE_INVALID"),
    ],
)
def test_duration_and_c067_deadline_boundaries_fail_closed(field: str, value: int, reason: str) -> None:
    policy, manifest, recovery = inputs()
    policy[field] = value
    assert simulate(policy, manifest, recovery)["reason"] == reason


def test_confirmation_is_independent_from_author_and_executor() -> None:
    policy, manifest, recovery = inputs()
    policy["identities"]["independent_confirmer"] = policy["identities"]["author"]
    assert simulate(policy, manifest, recovery)["reason"] == "INDEPENDENCE_GATE_FAILED"


@pytest.mark.parametrize(
    "evidence",
    ["manifest_verified", "green_at_zero_verified", "canary_healthy", "constitutional_gates_passed"],
)
def test_confirmation_requires_every_evidence_class(evidence: str) -> None:
    policy, manifest, recovery = inputs()
    policy["confirmation_evidence"][evidence] = False
    assert simulate(policy, manifest, recovery)["reason"] == "CONFIRMATION_EVIDENCE_FAILED"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("autonomous_halt", True, "AUTONOMOUS_HALT_ACTIVE"),
        ("workload_lease_active", False, "WORKLOAD_LEASE_INACTIVE"),
        ("drift_status", "detected", "DRIFT_GATE_FAILED"),
        ("concurrent_release_active", True, "CONCURRENCY_GATE_FAILED"),
    ],
)
def test_halt_lease_drift_and_concurrency_controls_block_release(field: str, value: object, reason: str) -> None:
    policy, manifest, recovery = inputs()
    policy[field] = value
    assert simulate(policy, manifest, recovery)["reason"] == reason


def test_cost_above_ceiling_blocks_without_spend() -> None:
    policy, manifest, recovery = inputs()
    policy["estimated_monthly_cost_inr"] = policy["monthly_cost_ceiling_inr"] + 1
    result = simulate(policy, manifest, recovery)
    assert result["reason"] == "COST_GATE_FAILED"
    assert result["provider_actions"] == 0


def test_manifest_tamper_blocks_promotion() -> None:
    policy, manifest, recovery = inputs()
    manifest["payload"]["members"]["web"]["digest"] = "waooaw-web:phase2"
    assert simulate(policy, manifest, recovery)["reason"] == "MANIFEST_GATE_FAILED"


def test_incompatible_recovery_tuple_blocks_promotion() -> None:
    policy, manifest, recovery = inputs()
    recovery["release_tuple"]["data_version"] = "incompatible"
    assert simulate(policy, manifest, recovery)["reason"] == "RECOVERY_TUPLE_GATE_FAILED"


def test_live_action_authority_is_never_accepted() -> None:
    policy, manifest, recovery = inputs()
    policy["live_actions_authorized"] = True
    result = simulate(policy, manifest, recovery)
    assert result["reason"] == "OFFLINE_BOUNDARY_INVALID"
    assert result["provider_actions"] == 0


def test_blue_deactivation_occurs_after_confirmation_and_observation_within_30_minutes() -> None:
    policy, manifest, recovery = inputs()
    result = simulate(policy, manifest, recovery)
    states = [event["state"] for event in result["events"]]
    confirmation = result["events"][states.index("INDEPENDENT_CONFIRMATION")]
    observation = result["events"][states.index("OBSERVE")]
    deactivation = result["events"][states.index("DEACTIVATE_BLUE_WITHIN_30_MINUTES")]
    assert confirmation["elapsed_seconds"] < observation["elapsed_seconds"] <= deactivation["elapsed_seconds"]
    assert deactivation["elapsed_seconds"] - confirmation["elapsed_seconds"] <= 1800


def test_failure_does_not_mutate_input_policy() -> None:
    policy, manifest, recovery = inputs()
    original = copy.deepcopy(policy)
    policy["inject_failure_at"] = "VERIFY_GREEN"
    simulate(policy, manifest, recovery)
    original["inject_failure_at"] = "VERIFY_GREEN"
    assert policy == original


def test_ci_build_and_scan_matrices_contain_exactly_six_release_members() -> None:
    workflow = yaml.safe_load(CI_PATH.read_text(encoding="utf-8"))
    build_members = {entry["name"] for entry in workflow["jobs"]["build"]["strategy"]["matrix"]["service"]}
    scan_members = set(workflow["jobs"]["trivy"]["strategy"]["matrix"]["image"])
    expected = {
        "constitutional-engine",
        "business-platform",
        "professional-runtime",
        "ai-runtime",
        "web",
        "billing-engine",
    }
    assert build_members == expected
    assert scan_members == expected
    build_step = next(
        step for step in workflow["jobs"]["build"]["steps"] if step.get("uses") == "docker/build-push-action@v5"
    )
    assert build_step["with"]["context"] == "."
    scan_step = next(
        step for step in workflow["jobs"]["trivy"]["steps"] if step.get("uses", "").startswith("aquasecurity/trivy-action@")
    )
    assert scan_step["with"]["limit-severities-for-sarif"] is True


def test_ci_audits_billing_dependencies_and_release_qualification_has_no_provider_authority() -> None:
    ci_text = CI_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(ci_text)
    release_job = workflow["jobs"]["release-qualification"]
    release_job_text = json.dumps(release_job)
    assert "pip-audit -r src/billing-engine/requirements.txt --strict" in ci_text
    assert release_job["permissions"] == {"contents": "read"}
    assert "scripts/test-wc059-postgres.sh" in release_job_text
    assert "scripts/goal006_release_simulator.py" in release_job_text
    for prohibited in ("azure/login", "az login", "terraform apply", "secrets.", "continue-on-error"):
        assert prohibited not in release_job_text
from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_runtime_lifecycle_evidence import (  # noqa: E402
    runtime_gate_required,
    validate_runtime_evidence,
)


HEAD = "a" * 40
EVIDENCE = {
    "schema": "waooaw.goal006-runtime-lifecycle/v1",
    "passed": True,
    "commit_sha": HEAD,
    "runtime_image": f"goal006-professional-runtime-lifecycle:{HEAD[:12]}",
    "temporal_image": f"temporalio/auto-setup@sha256:{'b' * 64}",
    "postgres_image": f"postgres@sha256:{'c' * 64}",
    "initial_http_status": 503,
    "initial_health": {"temporalConnected": False, "constitutionalEngineReachable": True},
    "recovered_http_status": 200,
    "recovered_health": {"temporalConnected": True, "constitutionalEngineReachable": True},
    "professional_runtime_log_sha256": "d" * 64,
}


def body(evidence: dict[str, object] = EVIDENCE) -> str:
    return f"## Pre-PR Runtime Evidence\n\n```json\n{json.dumps(evidence)}\n```\n"


def test_runtime_gate_applies_to_runtime_and_deployment_changes() -> None:
    assert runtime_gate_required(["src/professional-runtime/main.py"])
    assert runtime_gate_required(["infrastructure/terraform/phase2/modules/workload/main.tf"])
    assert not runtime_gate_required(["docs/README.md"])


def test_runtime_evidence_accepts_commit_bound_transition() -> None:
    assert validate_runtime_evidence(body(), HEAD, True) == []


def test_runtime_evidence_is_required_and_rejects_stale_commit() -> None:
    assert validate_runtime_evidence("## Summary\n", HEAD, True) == ["RUNTIME_EVIDENCE_MISSING: run scripts/prepare_pr_body.py"]
    stale = {**EVIDENCE, "commit_sha": "d" * 40}
    violations = validate_runtime_evidence(body(stale), HEAD, True)
    assert "RUNTIME_EVIDENCE_INVALID: commit_sha must equal 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'" in violations


def test_runtime_evidence_rejects_missing_dependency_and_log_proof() -> None:
    incomplete = {
        **EVIDENCE,
        "initial_health": {"temporalConnected": False},
        "professional_runtime_log_sha256": "missing",
    }

    violations = validate_runtime_evidence(body(incomplete), HEAD, True)

    assert "RUNTIME_EVIDENCE_INVALID: initial_health must report CE reachable" in violations
    assert "RUNTIME_EVIDENCE_INVALID: runtime log SHA-256 is required" in violations

from pathlib import Path
import json
import os
import subprocess
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
    "interrupted_http_status": 503,
    "interrupted_health": {"temporalConnected": False, "constitutionalEngineReachable": True},
    "restart_recovered_http_status": 200,
    "restart_recovered_health": {"temporalConnected": True, "constitutionalEngineReachable": True},
    "professional_runtime_log_sha256": "d" * 64,
    "runtime_image_id": f"sha256:{'e' * 64}",
    "image_scan": {
        "passed": True,
        "scanner_image": f"aquasec/trivy@sha256:{'f' * 64}",
        "policy": "fixable-high-critical",
        "report_sha256": "1" * 64,
    },
}


def body(evidence: dict[str, object] = EVIDENCE) -> str:
    return f"## Pre-PR Runtime Evidence\n\n```json\n{json.dumps(evidence)}\n```\n"


def test_runtime_gate_applies_to_runtime_and_deployment_changes() -> None:
    assert runtime_gate_required(["src/professional-runtime/main.py"])
    assert runtime_gate_required(["infrastructure/terraform/phase2/modules/workload/main.tf"])
    assert not runtime_gate_required(["docs/README.md"])


def test_database_readiness_uses_the_temporal_network_endpoint() -> None:
    script = (ROOT / "scripts/run_goal006_runtime_lifecycle_gate.sh").read_text()
    assert 'docker run --rm --network "$NETWORK" "$POSTGRES_IMAGE"' in script
    assert "pg_isready -h postgres -U postgres -d temporal" in script
    assert 'docker exec "$POSTGRES" pg_isready' not in script


def test_runtime_gate_refreshes_and_scans_before_starting_application() -> None:
    script = (ROOT / "scripts/run_goal006_runtime_lifecycle_gate.sh").read_text()
    assert '--build-arg "SECURITY_REFRESH=$(date +%s%N)"' in script
    assert "--scanners vuln --severity HIGH,CRITICAL" in script
    assert "--ignore-unfixed --exit-code 1" in script
    assert script.index('"$TRIVY_IMAGE" image') < script.index('--name "$RUNTIME"')
    assert 'rm -f -- "$EVIDENCE_JSON"' in script


def test_runtime_evidence_rejects_missing_or_failed_image_scan() -> None:
    for scan in (None, {}, {**EVIDENCE["image_scan"], "passed": False},
                 {**EVIDENCE["image_scan"], "scanner_image": "aquasec/trivy:latest"},
                 {**EVIDENCE["image_scan"], "report_sha256": "missing"}):
        assert validate_runtime_evidence(body({**EVIDENCE, "image_scan": scan}), HEAD, True)


def test_failed_image_scan_stops_before_workloads_and_removes_stale_evidence(tmp_path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls = tmp_path / "calls"
    docker = bin_dir / "docker"
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\n'
        'if test "$1" = run; then exit 17; fi\n'
    )
    docker.chmod(0o755)
    python = bin_dir / "python"
    python.write_text("#!/bin/sh\nexit 0\n")
    python.chmod(0o755)
    git = bin_dir / "git"
    git.write_text(
        '#!/bin/sh\ncase "$*" in\n'
        '*--show-toplevel*) printf "%s\\n" "$REPOSITORY_ROOT";;\n'
        '*) printf "%s\\n" aaaaaaaaaaaa;;\nesac\n'
    )
    git.chmod(0o755)
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"passed": true}')

    result = subprocess.run(
        ["bash", str(ROOT / "scripts/run_goal006_runtime_lifecycle_gate.sh"), str(evidence)],
        cwd=ROOT,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
             "CALLS": str(calls), "REPOSITORY_ROOT": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 17, result.stderr
    assert not evidence.exists()
    commands = calls.read_text()
    assert "--ignore-unfixed --exit-code 1" in commands
    assert "--name" not in commands


def test_runtime_evidence_accepts_commit_bound_transition() -> None:
    assert validate_runtime_evidence(body(), HEAD, True) == []


def test_runtime_evidence_is_required_and_rejects_stale_commit() -> None:
    assert validate_runtime_evidence("## Summary\n", HEAD, True) == ["RUNTIME_EVIDENCE_MISSING: run scripts/prepare_pr_body.py"]
    stale = {**EVIDENCE, "commit_sha": "d" * 40}
    violations = validate_runtime_evidence(body(stale), HEAD, True)
    assert "RUNTIME_EVIDENCE_INVALID: commit_sha must equal 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'" in violations


def test_runtime_evidence_survives_documentation_only_descendant() -> None:
    evidence_head = "d" * 40
    retained = {**EVIDENCE, "commit_sha": evidence_head, "runtime_image": f"goal006-professional-runtime-lifecycle:{evidence_head[:12]}"}

    assert validate_runtime_evidence(body(retained), HEAD, True, ["docs/runtime-evidence.md"]) == []
    assert validate_runtime_evidence(body(retained), HEAD, True, ["src/professional-runtime/main.py"])


def test_runtime_evidence_rejects_missing_dependency_and_log_proof() -> None:
    incomplete = {
        **EVIDENCE,
        "initial_health": {"temporalConnected": False},
        "professional_runtime_log_sha256": "missing",
    }

    violations = validate_runtime_evidence(body(incomplete), HEAD, True)

    assert "RUNTIME_EVIDENCE_INVALID: initial_health must report CE reachable" in violations
    assert "RUNTIME_EVIDENCE_INVALID: runtime log SHA-256 is required" in violations


def test_runtime_evidence_rejects_missing_restart_recovery() -> None:
    incomplete = {
        **EVIDENCE,
        "interrupted_health": {"temporalConnected": True, "constitutionalEngineReachable": True},
        "restart_recovered_http_status": 503,
    }

    violations = validate_runtime_evidence(body(incomplete), HEAD, True)

    assert "RUNTIME_EVIDENCE_INVALID: interrupted Temporal state must be disconnected" in violations
    assert "RUNTIME_EVIDENCE_INVALID: restart_recovered_http_status must equal 200" in violations

from __future__ import annotations

import copy
import os
import subprocess
from pathlib import Path

import pytest

from goal006_aca_execution_evidence import classify_execution_events, correlate_runner_executions

REPOSITORY = Path(__file__).resolve().parents[2]
CAPTURE_HELPER = REPOSITORY / "scripts" / "goal006_capture_aca_execution.sh"
FAKE_AZ = """#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$AZ_CALLS"
case "$*" in
  "monitor log-analytics query"*) printf '[]\\n' ;;
  "containerapp job execution show"*) printf '{"name":"goal006-demo-runner-cleanup-abc1234"}\\n' ;;
  *) printf 'log line\\n' ;;
esac
"""


def run_capture_helper(tmp_path: Path, status: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "az").write_text(FAKE_AZ, encoding="utf-8")
    (bin_dir / "sleep").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    for tool in bin_dir.iterdir():
        tool.chmod(0o755)
    calls = tmp_path / "az-calls.txt"
    result = subprocess.run(
        [
            "bash",
            str(CAPTURE_HELPER),
            "--job", "goal006-demo-runner-cleanup",
            "--container", "cleanup-broker",
            "--execution", "goal006-demo-runner-cleanup-abc1234",
            "--status", status,
            "--attempt", "1",
            "--workspace", "00000000-0000-0000-0000-000000000000",
            "--resource-group", "waooaw-demo-runner-rg",
            "--prefix", str(tmp_path / "cleanup-attempt-1"),
        ],
        cwd=REPOSITORY,
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "AZ_CALLS": str(calls)},
        text=True,
        capture_output=True,
        check=False,
    )
    queries = [line for line in calls.read_text(encoding="utf-8").splitlines() if line.startswith("monitor log-analytics query")]
    return result, queries


def execution(name: str, status: str, run_id: str, run_attempt: str) -> dict[str, object]:
    return {
        "name": name,
        "properties": {
            "status": status,
            "template": {
                "containers": [
                    {
                        "env": [
                            {"name": "GITHUB_WORKFLOW_RUN_ID", "value": run_id},
                            {"name": "GITHUB_WORKFLOW_RUN_ATTEMPT", "value": run_attempt},
                        ]
                    }
                ]
            },
        },
    }


def event(reason: str, log: str) -> dict[str, str]:
    return {
        "ExecutionName_s": "goal006-demo-runner-job-failed",
        "Reason_s": reason,
        "Log_s": log,
    }


def test_correlates_exact_runner_execution_without_accepting_other_runs() -> None:
    executions = [
        execution("goal006-demo-runner-job-other", "Succeeded", "1", "1"),
        execution("goal006-demo-runner-job-match", "Failed", "2", "1"),
    ]

    result = correlate_runner_executions(executions, run_id="2", run_attempt="1")

    assert result["unambiguous"] is True
    assert result["matches"] == [{"name": "goal006-demo-runner-job-match", "status": "Failed"}]


def test_correlates_observed_azure_child_execution_shape() -> None:
    observed = execution(
        "goal006-demo-runner-job-qqueljh",
        "Running",
        "39380363878",
        "1",
    )

    result = correlate_runner_executions(
        [observed],
        run_id="39380363878",
        run_attempt="1",
    )

    assert result["unambiguous"] is True
    assert result["matches"] == [{"name": "goal006-demo-runner-job-qqueljh", "status": "Running"}]


def test_reports_ambiguous_correlated_executions() -> None:
    executions = [
        execution("goal006-demo-runner-job-first", "Failed", "2", "1"),
        execution("goal006-demo-runner-job-second", "Running", "2", "1"),
    ]

    result = correlate_runner_executions(executions, run_id="2", run_attempt="1")

    assert result["unambiguous"] is False
    assert len(result["matches"]) == 2


def test_allows_one_retry_only_for_proven_pre_pull_platform_failure() -> None:
    name = "goal006-demo-runner-job-failed"
    events = [
        event("AssigningReplica", f"Replica for Job Execution '{name}' has been scheduled to run on a node."),
        event("BackoffLimitExceeded", "Job has reached the specified backoff limit"),
    ]

    result = classify_execution_events(events, execution_name=name, status="Failed", attempt=1)

    assert result["retry_eligible"] is True
    assert result["application_code_started"] is False


def test_nonterminal_execution_is_observable_but_never_retry_eligible() -> None:
    name = "goal006-demo-runner-job-failed"
    events = [event("AssigningReplica", f"Replica for Job Execution '{name}' has been scheduled to run on a node.")]

    result = classify_execution_events(events, execution_name=name, status="Waiting", attempt=1)

    assert result["scheduled"] is True
    assert result["retry_eligible"] is False


@pytest.mark.parametrize(
    ("mutation", "status", "attempt"),
    (
        (lambda events: events.append(event("PulledImage", "Successfully pulled image")), "Failed", 1),
        (lambda events: events.append(event("ContainerCreated", "Created container 'runner'")), "Failed", 1),
        (lambda events: events.append(event("ContainerStarted", "Started container 'runner'")), "Failed", 1),
        (lambda events: events.pop(), "Failed", 1),
        (lambda events: None, "Succeeded", 1),
        (lambda events: None, "Failed", 2),
    ),
)
def test_rejects_retry_when_execution_may_have_started_or_is_not_first_platform_failure(
    mutation: object,
    status: str,
    attempt: int,
) -> None:
    name = "goal006-demo-runner-job-failed"
    events = [
        event("AssigningReplica", f"Replica for Job Execution '{name}' has been scheduled to run on a node."),
        event("BackoffLimitExceeded", "Job has reached the specified backoff limit"),
    ]
    mutation(events)

    result = classify_execution_events(events, execution_name=name, status=status, attempt=attempt)

    assert result["retry_eligible"] is False


def test_does_not_mutate_event_evidence() -> None:
    name = "goal006-demo-runner-job-failed"
    events = [event("AssigningReplica", f"Execution '{name}' scheduled")]
    original = copy.deepcopy(events)

    classify_execution_events(events, execution_name=name, status="Failed", attempt=1)

    assert events == original


def test_rejects_events_not_bound_to_exact_execution() -> None:
    name = "goal006-demo-runner-job-failed"
    events = [event("AssigningReplica", f"Execution '{name}' scheduled")]
    events[0]["ExecutionName_s"] = "goal006-demo-runner-job-other"

    with pytest.raises(ValueError, match="not bound"):
        classify_execution_events(events, execution_name=name, status="Failed", attempt=1)


def test_capture_helper_fails_closed_when_system_events_are_unavailable_for_non_success() -> None:
    helper = Path("scripts/goal006_capture_aca_execution.sh").read_text(encoding="utf-8")

    assert "ContainerAppSystemLogs_CL" in helper
    assert "where ExecutionName_s == '$execution'" in helper
    assert "evidence_polls=3" in helper
    assert "evidence_polls=18" not in helper
    assert 'if [ "$status" = Succeeded ]; then' in helper
    assert "else\n  evidence_polls=36" in helper
    assert 'for evidence_attempt in $(seq 1 "$evidence_polls")' in helper
    assert "az monitor log-analytics query" in helper
    assert '--output json > "${prefix}.events.json"' in helper
    assert "goal006_aca_execution_evidence.py classify" in helper
    assert ".application_code_started or .terminal_platform_failure" in helper
    query_block = helper.split("az monitor log-analytics query", 1)[1].split(
        "python3 scripts/goal006_aca_execution_evidence.py", 1
    )[0]
    assert "|| true" not in query_block
    exhausted_block = helper.split('if [ "$evidence_attempt" = "$evidence_polls" ]; then', 1)[1]
    # ARM Succeeded is authoritative; absent events are recorded, not fatal (run 39428513813).
    assert 'if [ "$status" = Succeeded ]' in exhausted_block
    assert "recorded as absent" in exhausted_block
    assert "system events were not observable" in exhausted_block
    assert "exit 1" in exhausted_block


def test_classification_records_whether_system_events_were_observed() -> None:
    absent = classify_execution_events(
        [], execution_name="goal006-demo-runner-cleanup-quqp9fl", status="Succeeded", attempt=1
    )
    assert absent["system_events_observed"] is False
    assert absent["application_code_started"] is False
    assert absent["retry_eligible"] is False

    present = classify_execution_events(
        [event("ContainerStarted", "Started container 'cleanup-broker'")],
        execution_name="goal006-demo-runner-job-failed",
        status="Succeeded",
        attempt=1,
    )
    assert present["system_events_observed"] is True
    assert present["application_code_started"] is True


def test_capture_helper_bounds_optional_evidence_after_azure_success(tmp_path: Path) -> None:
    result, queries = run_capture_helper(tmp_path, "Succeeded")

    assert result.returncode == 0, result.stderr
    assert len(queries) == 3
    assert result.stderr.index("reported Succeeded; collecting supporting system events") < result.stderr.index(
        "recorded as absent"
    )


def test_capture_helper_still_requires_system_events_for_failed_execution(tmp_path: Path) -> None:
    result, queries = run_capture_helper(tmp_path, "Failed")

    assert result.returncode == 1
    assert len(queries) == 36
    assert "system events were not observable" in result.stderr

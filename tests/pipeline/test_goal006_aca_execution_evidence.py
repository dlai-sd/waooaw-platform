from __future__ import annotations

import copy
from pathlib import Path

import pytest

from goal006_aca_execution_evidence import classify_execution_events, correlate_runner_executions


def execution(name: str, status: str, run_id: str, run_attempt: str) -> dict[str, object]:
    return {
        "name": name,
        "properties": {
            "status": status,
            "template": {
                "containers": [
                    {
                        "env": [
                            {"name": "GITHUB_RUN_ID", "value": run_id},
                            {"name": "GITHUB_RUN_ATTEMPT", "value": run_attempt},
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


def test_capture_helper_fails_closed_when_system_events_are_unavailable() -> None:
    helper = Path("scripts/goal006_capture_aca_execution.sh").read_text(encoding="utf-8")

    assert "ContainerAppSystemLogs_CL" in helper
    assert "where ExecutionName_s == '$execution'" in helper
    assert "for evidence_attempt in $(seq 1 6)" in helper
    assert "az monitor log-analytics query" in helper
    assert '--output json > "${prefix}.events.json"' in helper
    assert "goal006_aca_execution_evidence.py classify" in helper
    assert 'if [ "$status" = Succeeded ]' not in helper
    assert ".application_code_started or .terminal_platform_failure" in helper
    query_block = helper.split("az monitor log-analytics query", 1)[1].split(
        "python3 scripts/goal006_aca_execution_evidence.py", 1
    )[0]
    assert "|| true" not in query_block

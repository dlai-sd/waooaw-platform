"""Contracts for durable GOAL-006 cleanup evidence retrieval."""

from pathlib import Path


def test_cleanup_evidence_falls_back_to_exact_execution_logs() -> None:
    workflow = Path(
        ".github/workflows/goal006-private-runner-qualification.yaml"
    ).read_text(encoding="utf-8")

    assert "az monitor log-analytics query" in workflow
    assert "ContainerJobName_s == '$RUNNER_CLEANUP_BROKER_JOB'" in workflow
    assert "ContainerGroupName_s startswith '$execution'" in workflow
    assert "--timespan PT15M" in workflow
    assert "jq -r '.[].Log_s' cleanup-log-records.json" in workflow
    assert "scripts/goal006_runner_execution.py evidence" in workflow
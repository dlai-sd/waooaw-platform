"""Contracts for durable GOAL-006 cleanup evidence retrieval."""

from pathlib import Path


def test_cleanup_evidence_uses_durable_blob_pointer_after_success() -> None:
    workflow = Path(
        ".github/workflows/goal006-private-runner-qualification.yaml"
    ).read_text(encoding="utf-8")

    assert "scripts/goal006_runner_execution.py pointer" in workflow
    assert '--cleanup-execution-name "$execution"' in workflow
    assert 'cleanup/$GITHUB_RUN_ID/$GITHUB_RUN_ATTEMPT.json' in workflow
    assert "az monitor log-analytics query" not in workflow
    assert "scripts/goal006_runner_execution.py evidence" not in workflow
    assert "az containerapp job logs show" in workflow
    assert "|| true" in workflow
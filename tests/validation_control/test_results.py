"""WC102 structured result and aggregation contracts."""

import json
from pathlib import Path

import pytest

from validation_control.results import aggregate_results, build_result


BASE_SHA = "b" * 40
HEAD_SHA = "c" * 40
RUNNER_DIGEST = "sha256:" + "d" * 64


def result(gate: str, outcome: str = "PASS", first_cause: str = "") -> dict[str, object]:
    return build_result(
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        runner_digest=RUNNER_DIGEST,
        component="web",
        gate=gate,
        command_id=f"command-{gate}",
        started_at="2026-09-19T12:00:00Z",
        duration_ms=12,
        exit_code=0 if outcome == "PASS" else 1,
        result=outcome,
        failure_class="none" if outcome == "PASS" else "assertion",
        first_cause=first_cause,
        raw_artifacts=[f"test-results/{gate}.xml"],
    )


def test_result_schema_accepts_complete_envelope_and_redacts_first_cause() -> None:
    envelope = result("test-web", "FAIL", "Bearer secret-token customer@example.com\n" + "x" * 800)

    assert "secret-token" not in envelope["first_cause"]
    assert "customer@example.com" not in envelope["first_cause"]
    assert len(envelope["first_cause"]) <= 512


def test_aggregate_rejects_missing_stale_and_malformed_results(tmp_path: Path) -> None:
    schema = json.loads((Path(__file__).resolve().parents[2] / "validation/result.schema.json").read_text())

    with pytest.raises(ValueError, match="MISSING_RESULT: test-python"):
        aggregate_results([result("test-web")], ["test-web", "test-python"], BASE_SHA, HEAD_SHA, schema)

    stale = result("test-web")
    stale["head_sha"] = "d" * 40
    with pytest.raises(ValueError, match="STALE_RESULT: test-web"):
        aggregate_results([stale], ["test-web"], BASE_SHA, HEAD_SHA, schema)

    malformed = result("test-web")
    del malformed["runner_digest"]
    with pytest.raises(ValueError, match="MALFORMED_RESULT: test-web"):
        aggregate_results([malformed], ["test-web"], BASE_SHA, HEAD_SHA, schema)


def test_aggregate_reports_earliest_causal_failure() -> None:
    later = result("test-python", "FAIL", "later failure")
    later["started_at"] = "2026-09-19T12:00:02Z"
    first = result("test-web", "FAIL", "first failure")

    aggregate = aggregate_results([later, first], ["test-web", "test-python"], BASE_SHA, HEAD_SHA, schema=None)

    assert aggregate["result"] == "FAIL"
    assert aggregate["first_failure"]["gate"] == "test-web"
    assert aggregate["first_failure"]["first_cause"] == "first failure"


def test_aggregate_accepts_explicit_not_applicable_and_requires_native_artifacts(tmp_path: Path) -> None:
    not_applicable = result("test-web", "NOT_APPLICABLE", "not applicable to selected component")
    not_applicable["failure_class"] = "none"
    not_applicable["exit_code"] = 0
    not_applicable["raw_artifacts"] = []

    aggregate = aggregate_results([not_applicable], ["test-web"], BASE_SHA, HEAD_SHA, schema=None, artifact_root=tmp_path)
    assert aggregate["result"] == "PASS"

    missing = result("test-python")
    with pytest.raises(ValueError, match="MISSING_ARTIFACT: test-python"):
        aggregate_results([missing], ["test-python"], BASE_SHA, HEAD_SHA, schema=None, artifact_root=tmp_path)

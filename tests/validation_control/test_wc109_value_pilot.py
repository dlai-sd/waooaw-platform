"""WC-109 current-PR value evidence contracts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from validation_control.pilot import validate_value_baseline, validate_value_baseline_source


REPOSITORY = Path(__file__).resolve().parents[2]


def value_baseline() -> dict[str, object]:
    return {
        "schema": "waooaw.wc109-value-baseline/v1",
        "preserved_head": "a" * 40,
        "source_manifest": {
            "path": "test-results/wc109/rollback-602cea40.json",
            "digest": "sha256:" + "1" * 64,
            "candidate_sha": "c" * 40,
        },
        "measurements": {
            "gate_counts": {"attempted": 43, "pass": 38, "fail": 5},
            "total_gate_seconds": 2833.434,
            "first_failure": {"zero_based_index": 30, "gate_id": "integration:multi-tenant"},
            "seconds_before_first_failure": 1901.640,
            "seconds_after_first_failure": 931.601,
        },
        "limitations": ["Summed gate durations are not wall-clock elapsed time."],
        "customer_value_claimed": False,
    }


def test_value_baseline_accepts_digest_bound_failed_run() -> None:
    result = validate_value_baseline(value_baseline())

    assert result == {
        "preserved_head": "a" * 40,
        "source_candidate_sha": "c" * 40,
        "source_digest": "sha256:" + "1" * 64,
        "attempted_gate_count": 43,
        "failed_gate_count": 5,
        "total_gate_seconds": 2833.434,
        "seconds_after_first_failure": 931.601,
        "passed": True,
    }


def test_repository_value_baseline_matches_retained_source() -> None:
    record = json.loads((REPOSITORY / "validation/evidence/wc109-value-baseline.json").read_text(encoding="utf-8"))

    result = validate_value_baseline_source(record, REPOSITORY)

    assert result["attempted_gate_count"] == 43
    assert result["failed_gate_count"] == 5
    assert result["seconds_after_first_failure"] == 931.601


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda record: record["source_manifest"].update({"candidate_sha": "invalid"}), "full lowercase"),
        (lambda record: record["source_manifest"].update({"digest": "invalid"}), "sha256 digest"),
        (lambda record: record["measurements"]["gate_counts"].update({"attempted": 42}), "pass plus fail"),
        (lambda record: record["measurements"].update({"seconds_after_first_failure": -1}), "nonnegative"),
        (lambda record: record.update({"customer_value_claimed": True}), "cannot claim customer value"),
    ],
)
def test_value_baseline_rejects_unreliable_claims(mutation: object, message: str) -> None:
    record = deepcopy(value_baseline())
    mutation(record)

    with pytest.raises(ValueError, match=message):
        validate_value_baseline(record)

"""WC-109 two-PR pilot recorder contracts."""

from copy import deepcopy

import pytest

from validation_control.pilot import build_pilot_report, validate_pilot_record


def pilot_record(number: int, head_character: str = "a") -> dict[str, object]:
    return {
        "schema": "waooaw.wc109-pilot-record/v1",
        "pull_request": {
            "number": number,
            "repository": "dlai-sd/waooaw-platform",
            "url": f"https://github.com/dlai-sd/waooaw-platform/pull/{number}",
            "head_sha": head_character * 40,
            "base_sha": "b" * 40,
            "created_at": "2026-09-11T10:00:00Z",
        },
        "implementation_available_at": "2026-09-10T10:00:00Z",
        "eligibility": {
            "product_pr": True,
            "began_after_implementation": True,
            "already_advanced": False,
        },
        "applicable_stacks": ["business-platform"],
        "change_class": "product-source",
        "cache_runs": [
            {"state": "cold", "cache_identity": "sha256:" + "1" * 64},
            {"state": "warm", "cache_identity": "sha256:" + "2" * 64},
        ],
        "tier_elapsed_seconds": {"tier1": [2.0, 4.0], "tier2": [10.0], "tier3": [20.0], "tier4": [30.0]},
        "builds": [],
        "source_only_tier2": True,
        "precheck": {"first_pass": "PASS", "modeled_defect_recurrence": []},
        "repair_loops": {"count": 0, "first_causes": []},
        "gate_inventories": {
            "selected": ["test-dotnet:business-platform"],
            "complete_applicable": ["test-dotnet:business-platform", "security:secrets"],
            "full_ci_outcomes": {"test-dotnet:business-platform": "PASS", "security:secrets": "PASS"},
        },
        "shadow_comparison": {
            "exact_head": head_character * 40,
            "workflow_run_id": 12345,
            "artifact_name": f"wc109-shadow-comparison-{number}",
            "full_ci_authoritative": True,
            "false_negatives": [],
            "missing_gate_results": [],
        },
        "threshold_outcomes": {
            "quality": "PRESERVED",
            "coverage": "PRESERVED",
            "security": "PRESERVED",
            "cct": "PRESERVED",
        },
        "limitations": ["Two observations do not establish a performance trend."],
    }


def test_pilot_report_accepts_two_distinct_complete_records() -> None:
    report = build_pilot_report([pilot_record(201), pilot_record(202, "c")])

    assert report["passed"] is True
    assert report["pilot_count"] == 2
    assert report["unresolved_selection_false_negatives"] == 0
    assert report["selective_hosted_validation_authorized"] is False
    assert report["observations"][0]["tier_elapsed_distributions"]["tier1"] == {
        "samples": 2,
        "minimum_seconds": 2.0,
        "median_seconds": 3.0,
        "maximum_seconds": 4.0,
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda record: record["eligibility"].update({"already_advanced": True}), "non-advanced product PR"),
        (lambda record: record.update({"cache_runs": record["cache_runs"][:1]}), "cold and warm"),
        (lambda record: record["shadow_comparison"].update({"false_negatives": ["test-web"]}), "false negatives"),
        (lambda record: record["threshold_outcomes"].update({"coverage": "REDUCED"}), "must not be reduced"),
        (lambda record: record["gate_inventories"]["full_ci_outcomes"].pop("security:secrets"), "complete applicable"),
    ],
)
def test_pilot_record_rejects_incomplete_or_unsafe_evidence(mutation: object, message: str) -> None:
    record = pilot_record(201)
    mutation(record)

    with pytest.raises(ValueError, match=message):
        validate_pilot_record(record)


def test_source_only_tier2_rejects_builds() -> None:
    record = pilot_record(201)
    record["builds"] = [{"kind": "runner", "identity": "sha256:" + "3" * 64, "count": 1}]

    with pytest.raises(ValueError, match="zero runner and candidate builds"):
        validate_pilot_record(record)


def test_pilot_report_requires_two_distinct_real_observations() -> None:
    record = pilot_record(201)

    with pytest.raises(ValueError, match="distinct PRs and commits"):
        build_pilot_report([record, deepcopy(record)])


def test_deterministic_repair_loop_requires_regression_fixture() -> None:
    record = pilot_record(201)
    record["repair_loops"] = {
        "count": 1,
        "first_causes": [{"classification": "cache-boundary", "deterministic_control_plane_defect": True}],
    }

    with pytest.raises(ValueError, match="regression fixture"):
        validate_pilot_record(record)

"""WC-109 current-PR value evidence contracts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from validation_control.pilot import (
    validate_current_pr_value_record,
    validate_value_baseline,
    validate_value_baseline_source,
    validate_wc109_wc110_integration,
    wc109_scope_violations,
)


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


def integration_record() -> dict[str, object]:
    return {
        "schema": "waooaw.wc109-wc110-integration/v1",
        "base_sha": "b" * 40,
        "partition_commit": "3" * 40,
        "preserved_head": "cccc2ad8306a512bf0f80c149c89b599a74160a2",
        "preservation_branch": "wc/110-product-validation-qualification-repair",
        "preserved_authority_files": [
            "work-contracts/WC-110-product-validation-qualification-repair.md",
            "work-contracts/WC-110-requirements.yaml",
        ],
        "wc109_candidate": {
            "path_count": 86,
            "scope_violations": [],
            "product_owned_files_removed": 72,
            "historical_results_promoted": False,
        },
        "validation": {"result": "PASS", "test_count": 186, "execution_boundary": "repository-docker-runner"},
    }


def current_pr_value_record() -> dict[str, object]:
    return {
        "schema": "waooaw.wc109-current-pr-value/v1",
        "pull_request": {"number": 481, "head_sha": "a" * 40, "base_sha": "b" * 40},
        "source_evidence": {
            name: {"ref": name, "digest": "sha256:" + character * 64}
            for name, character in zip(
                ("baseline", "pre_pr", "qualification", "hosted_ci", "hosted_quality"), "12345", strict=True
            )
        },
        "pre_pr": {
            "executed_nodes": 4,
            "reused_nodes": 0,
            "failed_nodes": 0,
            "volatile_advisory_executed_fresh": True,
            "supplied_runner_execution": True,
        },
        "qualification": {
            "candidate_sha": "a" * 40,
            "run_state": "PASSED",
            "first_cause_gate": None,
            "gate_counts": {"pass": 40, "blocked_deferred": 3, "fail": 0, "missing": 0},
            "deferred_gate_ids": ["acceptance:as-001", "acceptance:as-003", "acceptance:as-005"],
            "lane_counts": {"executed": 40, "resumed": 0, "carry_forward": 0, "suppressed": 0},
            "total_gate_seconds": 2580.172,
        },
        "hosted_final_head": {
            "head_sha": "a" * 40,
            "workflow_runs": [
                {"id": 37070737169, "conclusion": "success"},
                {"id": 37070737215, "conclusion": "success"},
            ],
            "shadow": {
                "applicable_gate_count": 30,
                "artifact_backed_catalog_gate_count": 26,
                "false_negatives": 0,
                "missing_gate_results": 0,
                "selective_enforcement": False,
            },
            "runner_builds": [
                {"runner_id": runner_id, "identity": "sha256:" + str(index) * 64, "count": 0}
                for index, runner_id in enumerate(("python", "dotnet", "typescript", "full"), start=1)
            ],
            "candidate_builds": [
                {
                    "service": f"service-{index}",
                    "identity": "sha256:" + str(index) * 64,
                    "registry_digest": "sha256:" + str(index + 1) * 64,
                    "count": 1,
                }
                for index in range(1, 8)
            ],
        },
        "threshold_outcomes": {outcome: "PRESERVED" for outcome in ("quality", "coverage", "security", "cct")},
        "limitations": ["one sample", "gate-seconds are not wall-clock", "engineering value is not customer value"],
        "customer_value_claimed": False,
    }


def test_current_pr_value_record_accepts_exact_final_evidence() -> None:
    result = validate_current_pr_value_record(current_pr_value_record())

    assert result == {
        "head_sha": "a" * 40,
        "qualification_pass_count": 40,
        "deferred_gate_count": 3,
        "hosted_gate_count": 30,
        "runner_build_count": 0,
        "candidate_build_count": 7,
        "passed": True,
    }


def test_repository_current_pr_value_record_is_valid() -> None:
    record = json.loads((REPOSITORY / "validation/evidence/wc109-current-pr-value.json").read_text(encoding="utf-8"))

    result = validate_current_pr_value_record(record)

    assert result["head_sha"] == "2f96645871a3a2a4f1093634d51ab4ca4e81ef34"
    assert result["qualification_pass_count"] == 40
    assert result["deferred_gate_count"] == 3
    assert result["hosted_gate_count"] == 30


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda record: record["qualification"]["gate_counts"].update({"pass": 39}), "40 PASS"),
        (lambda record: record["hosted_final_head"]["shadow"].update({"false_negatives": 1}), "Shadow"),
        (lambda record: record["hosted_final_head"]["runner_builds"][0].update({"count": 1}), "runner build"),
        (lambda record: record.update({"customer_value_claimed": True}), "cannot claim customer value"),
    ),
)
def test_current_pr_value_record_rejects_unsupported_claims(mutation: object, message: str) -> None:
    record = current_pr_value_record()
    mutation(record)

    with pytest.raises(ValueError, match=message):
        validate_current_pr_value_record(record)


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


def test_repository_value_baseline_uses_durable_non_output_evidence() -> None:
    record = json.loads((REPOSITORY / "validation/evidence/wc109-value-baseline.json").read_text(encoding="utf-8"))

    result = validate_value_baseline_source(record, REPOSITORY)

    assert record["source_manifest"]["path"].startswith("validation/evidence/")
    assert result["passed"] is True


def test_value_baseline_rejects_source_outside_durable_evidence() -> None:
    record = json.loads((REPOSITORY / "validation/evidence/wc109-value-baseline.json").read_text(encoding="utf-8"))
    record["source_manifest"]["path"] = "test-results/wc109/rollback-602cea40.json"

    with pytest.raises(ValueError, match="durable validation evidence"):
        validate_value_baseline_source(record, REPOSITORY)


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


def test_wc109_scope_accepts_control_plane_and_exact_candidate_dockerfiles() -> None:
    assert (
        wc109_scope_violations(
            [
                ".github/workflows/ci.yaml",
                "scripts/validation_control/orchestrator.py",
                "tests/validation_control/test_catalog_contract.py",
                "validation/engineering-validation.yaml",
                "src/business-platform/Dockerfile",
                "web/Dockerfile",
                "web/package.json",
                "web/pnpm-lock.yaml",
                "work-contracts/WC-109-requirements.yaml",
            ]
        )
        == []
    )


def test_wc109_scope_rejects_product_and_wc110_surfaces() -> None:
    paths = [
        "architecture/reference/api-specs/business-platform.openapi.yaml",
        "infrastructure/keycloak/waooaw-realm.json",
        "src/business-platform/Program.cs",
        "tests/business-platform.Tests/IdentityControllerTests.cs",
        "web/components/shell/AppShell.tsx",
        "work-contracts/WC-110-requirements.yaml",
        "../outside",
    ]

    assert wc109_scope_violations(paths) == sorted(paths)


def test_wc109_wc110_integration_accepts_preserved_clean_partition() -> None:
    result = validate_wc109_wc110_integration(integration_record())

    assert result["preserved_head"] == "cccc2ad8306a512bf0f80c149c89b599a74160a2"
    assert result["candidate_path_count"] == 86
    assert result["product_owned_files_removed"] == 72
    assert result["passed"] is True


def test_repository_wc109_wc110_integration_record_is_valid() -> None:
    record = json.loads((REPOSITORY / "validation/evidence/wc109-wc110-integration.json").read_text(encoding="utf-8"))

    result = validate_wc109_wc110_integration(record)

    assert result["partition_commit"] == "07a091c920ac49fc75be0b3e6a9d279739aac6f0"
    assert record["post_wc110_integration"] == {
        "merged_base_sha": "1fedf83e744b2099de1c3707f1fec770159124e8",
        "integration_commit": "cc4acb21193b460513f1caf85d69e50bcb732dbf",
        "effective_candidate_paths": ["tests/validation_control/test_runner_contracts.py"],
        "scope_violations": [],
        "historical_results_promoted": False,
        "focused_docker_tests": {"passed": 143, "failed": 0},
    }
    assert result["passed"] is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda record: record.update({"preserved_head": "d" * 40}), "preserved head"),
        (lambda record: record["preserved_authority_files"].pop(), "authority files"),
        (lambda record: record["wc109_candidate"].update({"scope_violations": ["src/product.py"]}), "scope evidence"),
        (lambda record: record["wc109_candidate"].update({"historical_results_promoted": True}), "scope evidence"),
        (lambda record: record["validation"].update({"result": "FAIL"}), "validation is incomplete"),
    ),
)
def test_wc109_wc110_integration_rejects_incomplete_partition(mutation: object, message: str) -> None:
    record = deepcopy(integration_record())
    mutation(record)

    with pytest.raises(ValueError, match=message):
        validate_wc109_wc110_integration(record)

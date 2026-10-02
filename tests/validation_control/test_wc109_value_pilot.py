"""WC-109 current-PR value evidence contracts."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from validation_control.pilot import (
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


def test_repository_value_baseline_uses_tracked_blob_when_worktree_evidence_is_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = json.loads((REPOSITORY / "validation/evidence/wc109-value-baseline.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(Path, "read_bytes", lambda unused: pytest.fail("read mutable working-tree evidence"))

    result = validate_value_baseline_source(record, REPOSITORY)

    assert result["passed"] is True


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

"""WC102-00 baseline characterization tests."""

# Implements: work-contracts/WC-102-docker-only-validation-control-plane.md §3
# Constitutional basis: C-059, C-071, C-080

from pathlib import Path

from validation_control.baseline_probe import collect_baseline


REPOSITORY = Path(__file__).resolve().parents[2]


def test_latest_main_exposes_accepted_wc102_baseline() -> None:
    baseline = collect_baseline(REPOSITORY)

    assert baseline["defects"] == {
        "duplicate_runner_builds": True,
        "business_platform_uses_deprecated_runner": True,
        "dotnet_nuget_path_mismatch": True,
        "typescript_source_mount_missing": True,
        "integration_host_test_invocations": 4,
        "advisory_contract_checks": True,
        "single_machine_catalog_missing": False,
        "wc102_catalog_contract_missing": True,
        "common_result_schema_missing": True,
    }
    assert baseline["runner_build_invocations"] > 1
    assert baseline["root_runner_overrides"] > 0
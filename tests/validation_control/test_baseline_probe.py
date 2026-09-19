"""WC102-00 baseline characterization tests."""

# Implements: work-contracts/WC-102-docker-only-validation-control-plane.md §3
# Constitutional basis: C-059, C-071, C-080

import json
from pathlib import Path

from validation_control.baseline_probe import collect_baseline


REPOSITORY = Path(__file__).resolve().parents[2]


def test_latest_main_exposes_accepted_wc102_baseline(tmp_path: Path) -> None:
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "architecture/reference/dockerfiles").mkdir(parents=True)
    (tmp_path / "validation").mkdir()
    (tmp_path / "docker-compose.yml").write_text(
        "test-runner-ts:\n    build:\n"
        "      dockerfile: architecture/reference/dockerfiles/Dockerfile.test-runner-ts\n"
        "    profiles: [test-ts]\n"
        "    environment:\n      NUGET_PACKAGES: /tmp/nuget\n"
    )
    (tmp_path / ".github/workflows/ci.yaml").write_text(
        "profile: test\n            runner: test-runner\n"
        "docker compose --profile test build test-runner\n"
        "docker compose --profile test build test-runner\n"
        "docker compose run --user root test-runner\n"
    )
    (tmp_path / ".github/workflows/integration-tests.yaml").write_text(
        "pytest tests/a.py\n"
        "dotnet test tests/a.csproj\n"
        "pnpm test\n"
        "python scripts/check.py\n"
        "continue-on-error: true  # Advisory until service is deployed in CI\n"
    )
    (tmp_path / "architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet").write_text(
        "RUN --mount=type=cache,target=/root/.nuget/packages dotnet restore\n"
    )
    (tmp_path / "validation/engineering-validation.yaml").write_text("version: 1\n")

    baseline = collect_baseline(tmp_path)

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


def test_baseline_evidence_is_bound_to_accepted_main() -> None:
    evidence = json.loads((REPOSITORY / "validation/evidence/wc102-baseline.json").read_text())

    assert evidence["base_sha"] == "ff09197debf331a75d8f50bb6a817a683544ed33"
    assert evidence["unsupported_savings_claims"] is False
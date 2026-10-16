import json
from pathlib import Path

import pytest

from scripts.wc124_deployment_bundle import canonical_digest, create_bundle


SHA = "a" * 40


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def write_text(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    return path


def bundle_inputs(tmp_path: Path) -> dict[str, object]:
    return {
        "environment": "demo",
        "release_sha": SHA,
        "release_run_id": "1234",
        "actor": "dlai-sd",
        "workflow_run_id": "5678",
        "workflow_run_attempt": "1",
        "lease_expiry": "2026-10-26T12:00:00Z",
        "foundation_plan": write_json(
            tmp_path / "foundation-plan.json",
            {"format_version": "1.2", "resource_changes": []},
        ),
        "workload_plan": write_json(
            tmp_path / "workload-plan.json",
            {"format_version": "1.2", "resource_changes": []},
        ),
        "secret_catalog": write_json(tmp_path / "secret-catalog.json", {"entries": []}),
        "configuration": write_json(tmp_path / "configuration.json", {"environment": "demo"}),
        "dependency_files": [write_json(tmp_path / "release-manifest.json", {"images": {}})],
        "migration_files": [write_text(tmp_path / "migration.sql", "SELECT 1;\n")],
        "schema_files": [write_text(tmp_path / "schema.sql", "CREATE SCHEMA business;\n")],
    }


def test_apply_bundle_is_generated_from_internal_exact_run_evidence(tmp_path: Path) -> None:
    inputs = bundle_inputs(tmp_path)
    bundle = create_bundle(**inputs)

    assert bundle["schema"] == "waooaw.wc124-deployment-activation-bundle/v1"
    assert bundle["environment"] == "demo"
    assert bundle["release_run_id"] == "1234"
    assert bundle["authorization"] == {
        "founder_action_authority": "FA-GITHUB-WORKFLOW-DISPATCH-5678-dlai-sd",
        "runner_execution_identity": "id-waooaw-demo-deployment-writer",
        "release_sha": SHA,
        "plan_digest": bundle["authorization"]["plan_digest"],
        "secret_catalog_digest": canonical_digest({"entries": []}),
        "lease_id": "wc124-demo-5678-1",
        "lease_expiry": "2026-10-26T12:00:00Z",
    }
    assert set(bundle["tuple_digests"]) == {
        "configuration",
        "dependency",
        "migration",
        "release",
        "schema",
    }
    assert bundle["bundle_digest"].startswith("sha256:")


def test_bundle_digest_changes_when_either_reviewed_plan_changes(tmp_path: Path) -> None:
    inputs = bundle_inputs(tmp_path)
    first = create_bundle(**inputs)
    write_json(
        inputs["workload_plan"],
        {
            "format_version": "1.2",
            "resource_changes": [{"address": "module.workload.pgbouncer"}],
        },
    )
    second = create_bundle(**inputs)

    assert second["authorization"]["plan_digest"] != first["authorization"]["plan_digest"]
    assert second["bundle_digest"] != first["bundle_digest"]


@pytest.mark.parametrize("environment", ["prod", "invalid"])
def test_apply_bundle_rejects_unauthorized_environment(tmp_path: Path, environment: str) -> None:
    inputs = bundle_inputs(tmp_path)
    inputs["environment"] = environment

    with pytest.raises(ValueError, match="Demo and UAT"):
        create_bundle(**inputs)


def test_apply_bundle_rejects_missing_or_non_terraform_plan(tmp_path: Path) -> None:
    inputs = bundle_inputs(tmp_path)
    write_json(inputs["foundation_plan"], {"format_version": "1.2"})

    with pytest.raises(ValueError, match="foundation plan"):
        create_bundle(**inputs)


def test_apply_bundle_rejects_duplicate_or_empty_evidence_sets(tmp_path: Path) -> None:
    inputs = bundle_inputs(tmp_path)
    inputs["migration_files"] = []
    with pytest.raises(ValueError, match="must not be empty"):
        create_bundle(**inputs)

    migration = write_text(tmp_path / "duplicate.sql", "SELECT 1;\n")
    inputs["migration_files"] = [migration, migration]
    with pytest.raises(ValueError, match="must be unique"):
        create_bundle(**inputs)

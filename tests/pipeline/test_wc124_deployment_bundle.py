import json
from pathlib import Path

import pytest

from scripts.goal006_plan_provenance import create_provenance
from scripts.wc124_deployment_bundle import canonical_digest, create_bundle


SHA = "a" * 40


def write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def write_text(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    return path


def write_provenance(
    tmp_path: Path,
    *,
    scope: str,
    plan_json: Path,
    plan_binary: Path,
) -> Path:
    state = write_json(tmp_path / f"{scope}-state.json", {"lineage": f"{scope}-lineage", "serial": 7})
    provenance = create_provenance(
        environment="demo",
        release_sha=SHA,
        release_run_id="1234",
        workflow_run_id="5678",
        workflow_run_attempt="1",
        scope=scope,
        terraform_root=f"infrastructure/terraform/phase2/environments/demo/{scope}",
        backend_key=f"goal006/demo/{scope}.tfstate",
        plan_json=plan_json,
        plan_binary=plan_binary,
        state=state,
    )
    return write_json(tmp_path / f"{scope}-plan-provenance.json", provenance)


def bundle_inputs(tmp_path: Path) -> dict[str, object]:
    foundation_plan = write_json(
        tmp_path / "foundation-plan.json",
        {"format_version": "1.2", "resource_changes": []},
    )
    foundation_plan_binary = write_text(tmp_path / "foundation.tfplan", "foundation plan")
    workload_plan = write_json(
        tmp_path / "workload-plan.json",
        {"format_version": "1.2", "resource_changes": []},
    )
    workload_plan_binary = write_text(tmp_path / "workload.tfplan", "workload plan")
    return {
        "environment": "demo",
        "release_sha": SHA,
        "release_run_id": "1234",
        "actor": "dlai-sd",
        "workflow_run_id": "5678",
        "workflow_run_attempt": "1",
        "lease_expiry": "2026-10-26T12:00:00Z",
        "foundation_plan": foundation_plan,
        "foundation_plan_binary": foundation_plan_binary,
        "foundation_plan_provenance": write_provenance(
            tmp_path,
            scope="foundation",
            plan_json=foundation_plan,
            plan_binary=foundation_plan_binary,
        ),
        "workload_plan": workload_plan,
        "workload_plan_binary": workload_plan_binary,
        "workload_plan_provenance": write_provenance(
            tmp_path,
            scope="workload",
            plan_json=workload_plan,
            plan_binary=workload_plan_binary,
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
    assert set(bundle["plan_provenance"]) == {"foundation", "workload"}


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
    inputs["workload_plan_provenance"] = write_provenance(
        tmp_path,
        scope="workload",
        plan_json=inputs["workload_plan"],
        plan_binary=inputs["workload_plan_binary"],
    )
    second = create_bundle(**inputs)

    assert second["authorization"]["plan_digest"] != first["authorization"]["plan_digest"]
    assert second["bundle_digest"] != first["bundle_digest"]


def test_apply_bundle_rejects_plan_provenance_from_another_release(tmp_path: Path) -> None:
    inputs = bundle_inputs(tmp_path)
    provenance = json.loads(inputs["foundation_plan_provenance"].read_text(encoding="utf-8"))
    provenance["release_sha"] = "b" * 40
    write_json(inputs["foundation_plan_provenance"], provenance)

    with pytest.raises(ValueError, match="foundation plan provenance mismatch"):
        create_bundle(**inputs)


def test_apply_bundle_rejects_plan_binary_tampering(tmp_path: Path) -> None:
    inputs = bundle_inputs(tmp_path)
    write_text(inputs["workload_plan_binary"], "tampered workload plan")

    with pytest.raises(ValueError, match="workload plan provenance mismatch"):
        create_bundle(**inputs)


def test_plan_provenance_rejects_cross_environment_backend(tmp_path: Path) -> None:
    plan_json = write_json(tmp_path / "foundation-plan.json", {"format_version": "1.2", "resource_changes": []})
    plan_binary = write_text(tmp_path / "foundation.tfplan", "foundation plan")
    state = write_json(tmp_path / "foundation-state.json", {"lineage": "lineage", "serial": 1})

    with pytest.raises(ValueError, match="backend key is not environment-exact"):
        create_provenance(
            environment="demo",
            release_sha=SHA,
            release_run_id="1234",
            workflow_run_id="5678",
            workflow_run_attempt="1",
            scope="foundation",
            terraform_root="infrastructure/terraform/phase2/environments/demo/foundation",
            backend_key="goal006/uat/foundation.tfstate",
            plan_json=plan_json,
            plan_binary=plan_binary,
            state=state,
        )


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

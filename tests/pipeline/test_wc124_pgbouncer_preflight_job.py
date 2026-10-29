from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from wc124_pgbouncer_preflight_job import (
    DATABASE_PROBE,
    build_database_probe_template,
    build_preflight_patch,
    validate_patch_schema,
    verify_effective_job,
)


ROOT = Path(__file__).resolve().parents[2]
REAL_SHAPE_FIXTURE = ROOT / "tests/fixtures/wc124/aca-job-get-2024-03-01.sanitized.json"
PATCH_SCHEMA = ROOT / "infrastructure/environment-readiness/wc124-pgbouncer-preflight-job-patch.schema.json"
SUBSCRIPTION_ID = "00000000-0000-0000-0000-000000000000"


def billing_job_fixture():
    return {
        "id": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/waooaw-demo-rg/providers/Microsoft.App/jobs/"
              "job-demo-wc124-billing-migration",
        "name": "job-demo-wc124-billing-migration",
        "resourceGroup": "waooaw-demo-rg",
        "type": "Microsoft.App/jobs",
        "properties": {
            "configuration": {"secrets": [{"name": "migration-database",
                                          "keyVaultUrl": "https://kv-demo.vault.azure.net/secrets/db-billing-migration/version"}]},
            "template": {"containers": [{
                "name": "billing-migration",
                "image": "ghcr.io/dlai-sd/billing-engine@sha256:" + "a" * 64,
                "env": [{"name": "DATABASE_URL", "secretRef": "migration-database"}],
                "resources": {"cpu": 0.5, "memory": "1Gi", "ephemeralStorage": "2Gi"},
                "command": ["python", "migrate.py"],
            }]},
        },
    }


def test_database_probe_reuses_immutable_billing_image_and_secret_without_patching_job():
    job = billing_job_fixture()
    before = copy.deepcopy(job)
    template = build_database_probe_template(job, "demo", SUBSCRIPTION_ID)
    assert job == before
    container = template["containers"][0]
    assert container["image"] == job["properties"]["template"]["containers"][0]["image"]
    assert container["env"] == [{"name": "DATABASE_URL", "secretRef": "migration-database"}]
    assert container["command"] == ["python", "-c"]
    assert container["args"] == [DATABASE_PROBE, "demo"]
    assert container["resources"] == {"cpu": 0.5, "memory": "1Gi"}
    assert set(template) == {"containers"}
    compile(DATABASE_PROBE, "<database-preflight>", "exec")
    assert "readonly=True" in DATABASE_PROBE
    assert "statement_cache_size=0" in DATABASE_PROBE
    assert "SELECT 1" in DATABASE_PROBE


@pytest.mark.parametrize("case", ["scope", "image", "plaintext", "unversioned", "sidecar"])
def test_database_probe_rejects_untrusted_execution_inputs(case):
    job = billing_job_fixture()
    container = job["properties"]["template"]["containers"][0]
    if case == "scope":
        job["id"] = job["id"].replace("waooaw-demo-rg", "waooaw-uat-rg")
    elif case == "image":
        container["image"] = "ghcr.io/dlai-sd/billing-engine:latest"
    elif case == "plaintext":
        container["env"] = [{"name": "DATABASE_URL", "value": "must-not-use-inline-credentials"}]
    elif case == "unversioned":
        job["properties"]["configuration"]["secrets"][0]["keyVaultUrl"] = "https://kv-demo.vault.azure.net/secrets/db-billing-migration"
    else:
        job["properties"]["template"]["containers"].append(copy.deepcopy(container))
    with pytest.raises(ValueError):
        build_database_probe_template(job, "demo", SUBSCRIPTION_ID)


def test_database_probe_cli_generates_execution_template_without_site_packages(tmp_path):
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(billing_job_fixture()))
    output = tmp_path / "template.json"
    subprocess.run([
        sys.executable, "-S", str(ROOT / "scripts/wc124_pgbouncer_preflight_job.py"),
        "--job", str(job_path), "--environment", "demo", "--subscription-id", SUBSCRIPTION_ID,
        "--database-query", "--output", str(output),
    ], check=True)
    assert json.loads(output.read_text()) == build_database_probe_template(billing_job_fixture(), "demo", SUBSCRIPTION_ID)


def job_fixture() -> dict[str, object]:
    job = json.loads(REAL_SHAPE_FIXTURE.read_text(encoding="utf-8"))
    container = job["properties"]["template"]["containers"][0]
    container["env"] = [{"name": "UNCHANGED", "value": "true"}]
    container["volumeMounts"] = [{"volumeName": "unchanged", "mountPath": "/unchanged"}]
    return job


def test_projects_real_get_shape_to_schema_valid_write_model_without_mutating_source() -> None:
    job = job_fixture()
    original = copy.deepcopy(job)

    patch = build_preflight_patch(job, "demo", SUBSCRIPTION_ID)

    assert job == original
    Draft202012Validator(json.loads(PATCH_SCHEMA.read_text(encoding="utf-8"))).validate(patch)
    validate_patch_schema(patch, json.loads(PATCH_SCHEMA.read_text(encoding="utf-8")))
    container = patch["properties"]["template"]["containers"][0]
    assert container["command"] == ["/usr/bin/python3"]
    assert container["args"] == [
        "/opt/waooaw/wc124_db_provisioner.py",
        "--environment",
        "demo",
        "--pgbouncer-host",
        "ca-demo-pgbouncer",
        "--network-probe",
    ]
    assert container["image"] == original["properties"]["template"]["containers"][0]["image"]
    assert container["env"] == [{"name": "UNCHANGED", "value": "true"}]
    assert container["volumeMounts"] == [{"volumeName": "unchanged", "mountPath": "/unchanged"}]
    assert container["resources"] == {"cpu": 0.5, "memory": "1Gi"}
    assert "imageType" not in container
    assert "ephemeralStorage" not in container["resources"]
    assert patch == {
        "properties": {
            "template": {
                "containers": [container],
            }
        }
    }
    assert "identity" not in patch
    assert "configuration" not in patch["properties"]


def test_rejects_unpinned_schema_and_schema_invalid_payload() -> None:
    schema = json.loads(PATCH_SCHEMA.read_text(encoding="utf-8"))
    patch = build_preflight_patch(job_fixture(), "demo", SUBSCRIPTION_ID)
    altered_schema = copy.deepcopy(schema)
    altered_schema["title"] = "untrusted"

    with pytest.raises(ValueError, match="does not match the pinned"):
        validate_patch_schema(patch, altered_schema)

    patch["properties"]["template"]["containers"][0]["imageType"] = "ContainerImage"
    with pytest.raises(ValueError, match="unsupported fields"):
        validate_patch_schema(patch, schema)


def test_cli_runs_without_site_packages(tmp_path: Path) -> None:
    output = tmp_path / "patch.json"

    subprocess.run(
        [
            sys.executable,
            "-S",
            str(ROOT / "scripts/wc124_pgbouncer_preflight_job.py"),
            "--job",
            str(REAL_SHAPE_FIXTURE),
            "--environment",
            "demo",
            "--subscription-id",
            SUBSCRIPTION_ID,
            "--schema",
            str(PATCH_SCHEMA),
            "--output",
            str(output),
        ],
        check=True,
    )

    validate_patch_schema(json.loads(output.read_text(encoding="utf-8")), json.loads(PATCH_SCHEMA.read_text()))


def test_verifies_only_command_and_args_changed_in_effective_job() -> None:
    before = job_fixture()
    patch = build_preflight_patch(before, "demo", SUBSCRIPTION_ID)
    after = copy.deepcopy(before)
    after_container = after["properties"]["template"]["containers"][0]
    after_container["command"] = patch["properties"]["template"]["containers"][0]["command"]
    after_container["args"] = patch["properties"]["template"]["containers"][0]["args"]

    verify_effective_job(before, after, patch, "demo", SUBSCRIPTION_ID)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("identity", "type"), "SystemAssigned", "effective identity"),
        (("properties", "configuration", "replicaTimeout"), 60, "configuration"),
        (("properties", "environmentId"), "/wrong", "environmentId"),
        (("properties", "template", "containers", 0, "image"), "ghcr.io/example/image:latest", "immutable"),
        (("properties", "template", "containers", 0, "env", 0, "value"), "false", "does not match"),
        (("properties", "template", "containers", 0, "resources", "memory"), "2Gi", "does not match"),
    ),
)
def test_rejects_unexpected_effective_job_changes(path: tuple[object, ...], value: object, message: str) -> None:
    before = job_fixture()
    patch = build_preflight_patch(before, "demo", SUBSCRIPTION_ID)
    after = copy.deepcopy(before)
    after_container = after["properties"]["template"]["containers"][0]
    after_container["command"] = patch["properties"]["template"]["containers"][0]["command"]
    after_container["args"] = patch["properties"]["template"]["containers"][0]["args"]
    target = after
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value

    with pytest.raises(ValueError, match=message):
        verify_effective_job(before, after, patch, "demo", SUBSCRIPTION_ID)


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda job: job.update(name="job-demo-wrong"), "expected ACA Job"),
        (lambda job: job.update(id=job["id"].replace("waooaw-demo-rg", "other-rg")), "environment scope"),
        (lambda job: job.update(type="Microsoft.App/containerApps"), "resource type"),
        (lambda job: job.update(resourceGroup="other-rg"), "resource group"),
        (lambda job: job.update(unknownTopLevel="value"), "ACA Job contains unsupported fields"),
        (
            lambda job: job["properties"].update(unknownReadModelField="value"),
            "ACA Job properties contains unsupported fields",
        ),
        (
            lambda job: job["properties"]["template"].update(unknownTemplateField="value"),
            "ACA Job template contains unsupported fields",
        ),
        (lambda job: job["properties"].pop("template"), "no template"),
        (lambda job: job["properties"]["template"].update(containers=[]), "exactly one container"),
        (
            lambda job: job["properties"]["template"]["containers"][0].update(name="wrong"),
            "container identity is invalid",
        ),
        (
            lambda job: job["properties"]["template"]["containers"][0].update(image="ghcr.io/example/image:latest"),
            "immutable WAOOAW runner digest",
        ),
        (
            lambda job: job["properties"]["template"]["containers"][0].update(unrecognized="value"),
            "unsupported fields: unrecognized",
        ),
        (
            lambda job: job["properties"]["template"]["containers"][0]["resources"].update(readModelAddition="value"),
            "unsupported fields: readModelAddition",
        ),
        (
            lambda job: job["properties"]["template"].update(
                initContainers=[{"name": "unexpected", "image": "example.invalid/init"}]
            ),
            "must not define init containers",
        ),
        (
            lambda job: job["properties"]["template"].update(volumes=[{"name": "unexpected"}]),
            "must not define volumes",
        ),
    ),
)
def test_rejects_untrusted_job_shapes(mutation: object, message: str) -> None:
    job = job_fixture()
    mutation(job)

    with pytest.raises(ValueError, match=message):
        build_preflight_patch(job, "demo", SUBSCRIPTION_ID)


def test_rejects_production_mutation() -> None:
    job = job_fixture()
    job["name"] = "job-prod-wc124-db-provisioner"
    job["properties"]["template"]["containers"][0]["name"] = "job-prod-wc124-db-provisioner"

    with pytest.raises(ValueError, match="demo or uat"):
        build_preflight_patch(job, "prod", SUBSCRIPTION_ID)


def test_allows_only_the_named_disposable_demo_qualification_job() -> None:
    job = job_fixture()
    job["id"] = job["id"].replace("job-demo-wc124-db-provisioner", "job-demo-wc124-net-qual")
    job["name"] = "job-demo-wc124-net-qual"
    job["properties"]["template"]["containers"][0]["name"] = "job-demo-wc124-net-qual"

    patch = build_preflight_patch(job, "demo", SUBSCRIPTION_ID, qualification_job=True)

    assert patch["properties"]["template"]["containers"][0]["name"] == "job-demo-wc124-net-qual"
    with pytest.raises(ValueError, match="permitted only in demo"):
        build_preflight_patch(job, "uat", SUBSCRIPTION_ID, qualification_job=True)

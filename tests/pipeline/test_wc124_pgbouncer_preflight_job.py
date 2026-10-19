from __future__ import annotations

import copy

import pytest

from wc124_pgbouncer_preflight_job import build_preflight_patch


def job_fixture() -> dict[str, object]:
    return {
        "id": (
            "/subscriptions/sub/resourceGroups/waooaw-demo-rg/providers/"
            "Microsoft.App/jobs/job-demo-wc124-db-provisioner"
        ),
        "identity": {"type": "UserAssigned", "userAssignedIdentities": {"/identity": {}}},
        "name": "job-demo-wc124-db-provisioner",
        "properties": {
            "configuration": {
                "replicaRetryLimit": 0,
                "replicaTimeout": 1800,
                "triggerType": "Manual",
                "secrets": [{"name": "unchanged", "keyVaultUrl": "https://vault/secrets/name/version"}],
                "registries": [{"server": "ghcr.io", "identity": "/identity"}],
            },
            "template": {
                "initContainers": [{"name": "unchanged-init", "image": "example.invalid/init@sha256:" + ("b" * 64)}],
                "containers": [
                    {
                        "name": "job-demo-wc124-db-provisioner",
                        "image": "ghcr.io/dlai-sd/goal006-private-runner@sha256:" + ("a" * 64),
                        "command": ["/usr/bin/python3"],
                        "args": ["/opt/waooaw/wc124_db_handoff.py"],
                        "env": [{"name": "UNCHANGED", "value": "true"}],
                        "resources": {"cpu": 0.5, "memory": "1Gi"},
                    }
                ],
            }
        },
    }


def test_builds_typed_network_probe_patch_without_mutating_source() -> None:
    job = job_fixture()
    original = copy.deepcopy(job)

    patch = build_preflight_patch(job, "demo")

    assert job == original
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
    assert container["resources"] == {"cpu": 0.5, "memory": "1Gi"}
    assert patch["properties"]["template"]["initContainers"] == original["properties"]["template"]["initContainers"]
    assert set(patch) == {"properties"}
    assert set(patch["properties"]) == {"template"}
    assert "identity" not in patch
    assert "configuration" not in patch["properties"]
    actual_without_mutation = copy.deepcopy(patch["properties"]["template"])
    expected_without_mutation = copy.deepcopy(original["properties"]["template"])
    for template in (actual_without_mutation, expected_without_mutation):
        template["containers"][0].pop("command")
        template["containers"][0].pop("args")
    assert actual_without_mutation == expected_without_mutation


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda job: job.update(name="job-demo-wrong"), "expected ACA Job"),
        (lambda job: job.update(id=job["id"].replace("waooaw-demo-rg", "other-rg")), "environment scope"),
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
    ),
)
def test_rejects_untrusted_job_shapes(mutation: object, message: str) -> None:
    job = job_fixture()
    mutation(job)

    with pytest.raises(ValueError, match=message):
        build_preflight_patch(job, "demo")


def test_rejects_production_mutation() -> None:
    job = job_fixture()
    job["name"] = "job-prod-wc124-db-provisioner"
    job["properties"]["template"]["containers"][0]["name"] = "job-prod-wc124-db-provisioner"

    with pytest.raises(ValueError, match="demo or uat"):
        build_preflight_patch(job, "prod")

"""Contracts for reusable GOAL-006 runner deployment planning."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.goal006_runner_deployment import (
    _canonical,
    _digest_bytes,
    _required_resource_names,
    environment_contract,
    normalize_changes,
    revalidate_reviewed_plan,
    validate_reviewed_plan,
    verify_deployment,
    verify_signer_role_assignments,
)

REPOSITORY_ROOT = Path(__file__).parents[2]
MANIFEST = (
    REPOSITORY_ROOT
    / "infrastructure/deployment-stacks/goal006-runner/bootstrap-manifest.json"
)
RUNNER_TEMPLATE = (
    REPOSITORY_ROOT / "infrastructure/deployment-stacks/goal006-runner/main.bicep"
)


def test_every_environment_uses_one_deployment_contract() -> None:
    for environment in ("demo", "uat", "prod"):
        contract = environment_contract(REPOSITORY_ROOT, MANIFEST, environment)
        assert contract["stack_name"] == f"goal006-{environment}-private-runner"
        assert contract["resource_group"] == f"waooaw-{environment}-runner-rg"
        assert contract["activation_state"] in {"INACTIVE", "ACTIVE"}


def test_signer_roles_are_scoped_to_key_not_key_version() -> None:
    template = RUNNER_TEMPLATE.read_text(encoding="utf-8")

    assert "scope: githubAppKey\n" in template
    assert "scope: githubAppKeyVersionResource" not in template
    assert "Microsoft.KeyVault/vaults/keys/versions" not in template


def test_live_signer_verification_rejects_key_version_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key_scope = "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.KeyVault/vaults/vault/keys/app"

    def version_scoped_assignment(*arguments: str):
        if arguments[:2] == ("identity", "show"):
            return {"principalId": "principal"}
        if arguments[:3] == ("role", "assignment", "list"):
            return [
                {
                    "roleDefinitionName": "Key Vault Crypto User",
                    "scope": f"{key_scope}/versions/version-id",
                }
            ]
        raise AssertionError(arguments)

    monkeypatch.setattr("scripts.goal006_runner_deployment._az", version_scoped_assignment)

    with pytest.raises(RuntimeError, match="lacks Key Vault Crypto User"):
        verify_signer_role_assignments(
            resource_group="rg", prefix="goal006-demo-runner", key_scope=key_scope
        )


def test_azure_resource_names_respect_service_limits() -> None:
    resources = _required_resource_names("demo")
    job_names = [
        name
        for name, resource_type in resources.items()
        if resource_type == "Microsoft.App/jobs"
    ]

    assert all(len(name) <= 32 for name in job_names)
    assert "goal006-demo-runner-vaultcore-pe" in resources


def test_plan_normalization_is_stable() -> None:
    changes = [
        {"changeType": "Create", "resourceId": "/subscriptions/sub/resourceGroups/b"},
        {"changeType": "Ignore", "resourceId": "/subscriptions/sub/resourceGroups/a"},
    ]
    assert normalize_changes(changes) == [
        {
            "change_type": "Ignore",
            "resource_id": "/subscriptions/sub/resourceGroups/a",
            "details": {},
        },
        {
            "change_type": "Create",
            "resource_id": "/subscriptions/sub/resourceGroups/b",
            "details": {},
        },
    ]


def test_plan_normalization_preserves_property_delta() -> None:
    normalized = normalize_changes(
        [
            {
                "changeType": "Modify",
                "resourceId": "/subscriptions/sub/resourceGroups/a/providers/Test/resource/a",
                "before": {"properties": {"access": "Allow"}},
                "after": {"properties": {"access": "Deny"}},
                "delta": [
                    {"path": "properties.access", "propertyChangeType": "Modify"}
                ],
            }
        ]
    )
    assert normalized[0]["details"]["after"]["properties"]["access"] == "Deny"
    assert normalized[0]["details"]["delta"][0]["path"] == "properties.access"


@pytest.mark.parametrize("change_type", ["Delete", "Deploy", "Unsupported", ""])
def test_destructive_or_ambiguous_plan_is_rejected(change_type: str) -> None:
    with pytest.raises(RuntimeError, match="unsupported or destructive"):
        normalize_changes(
            [
                {
                    "changeType": change_type,
                    "resourceId": "/subscriptions/sub/resourceGroups/unsafe",
                }
            ]
        )


def test_reviewed_plan_digest_is_fail_closed() -> None:
    payload = {"schema": "waooaw.goal006-runner-plan/v1", "environment": "demo"}
    plan = {"payload": payload, "plan_digest": _digest_bytes(b'{"wrong":true}')}
    with pytest.raises(RuntimeError, match="digest invalid"):
        validate_reviewed_plan(plan)

    valid = deepcopy(plan)
    valid["plan_digest"] = _digest_bytes(_canonical(payload))
    assert validate_reviewed_plan(valid) == payload


def test_live_plan_rejects_unauthorized_environment() -> None:
    from scripts.goal006_runner_deployment import create_plan

    with pytest.raises(RuntimeError, match="not authorized for environment"):
        create_plan(
            repository_root=REPOSITORY_ROOT,
            manifest_path=MANIFEST,
            environment="staging",
            subscription_id="sub",
            source_commit="b" * 40,
        )


@pytest.mark.parametrize(
    ("activation_state", "reconciler_trigger", "reconciler_command", "expected_error"),
    [
        ("ACTIVE", "Schedule", ["python3", "-c"], None),
        ("INACTIVE", "Manual", ["python3", "-c"], None),
        ("ACTIVE", "Schedule", ["/bin/sh", "-c"], "reconciler job command differs"),
    ],
)
def test_live_verification_requires_approved_endpoints_and_guarded_jobs(
    monkeypatch: pytest.MonkeyPatch,
    activation_state: str,
    reconciler_trigger: str,
    reconciler_command: list[str],
    expected_error: str | None,
) -> None:
    environment = "demo"
    contract = {
        "stack_name": "goal006-demo-private-runner",
        "resource_group": "waooaw-demo-runner-rg",
        "activation_state": activation_state,
        "runner_image": "runner@sha256:expected",
        "reconciler_image": "reconciler@sha256:expected",
        "parameter_path": REPOSITORY_ROOT
        / "infrastructure/deployment-stacks/goal006-runner/demo.parameters.json",
    }
    monkeypatch.setattr(
        "scripts.goal006_runner_deployment.environment_contract",
        lambda *arguments: contract,
    )

    def live_azure(*arguments: str):
        command = arguments[:3]
        if command == ("stack", "sub", "show"):
            return {
                "provisioningState": "Succeeded",
                "denySettings": {"mode": "denyDelete"},
                "actionOnUnmanage": {
                    "resources": "detach",
                    "resourceGroups": "detach",
                    "managementGroups": "detach",
                },
                "resources": [
                    {
                        "id": f"/subscriptions/sub/resourceGroups/rg/providers/{resource_type}/{name}",
                        "status": "managed",
                    }
                    for name, resource_type in _required_resource_names(environment).items()
                ],
            }
        if command == ("resource", "list", "--resource-group"):
            return [
                {
                    "name": name,
                    "type": resource_type,
                    "id": f"/subscriptions/sub/resourceGroups/rg/providers/{resource_type}/{name}",
                }
                for name, resource_type in _required_resource_names(environment).items()
            ]
        if command == ("network", "private-endpoint", "show"):
            return {
                "privateLinkServiceConnections": [
                    {"privateLinkServiceConnectionState": {"status": "Approved"}}
                ]
            }
        if arguments[:2] == ("identity", "show"):
            return {"principalId": arguments[-1] + "-principal"}
        if command == ("role", "assignment", "list"):
            key_scope = (
                "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.KeyVault/"
                "vaults/waooaw-demo-runner-kv/keys/github-runner-app-signing"
            )
            return [
                {"roleDefinitionName": "Key Vault Crypto User", "scope": key_scope}
            ]
        if arguments[:4] == ("containerapp", "job", "execution", "list"):
            return []
        if command == ("containerapp", "job", "show"):
            job_name = arguments[-1]
            reconciler = job_name.endswith("-reconciler")
            broker = job_name.endswith("-broker")
            cleanup_broker = job_name.endswith("-cleanup")
            name = "reconciler" if reconciler else "broker" if broker else "cleanup-broker" if cleanup_broker else "runner"
            configuration = {
                "triggerType": reconciler_trigger if reconciler else "Manual",
            }
            if broker or cleanup_broker:
                configuration.update(
                    replicaTimeout=300,
                    manualTriggerConfig={"parallelism": 1, "replicaCompletionCount": 1},
                )
            if reconciler and reconciler_trigger == "Schedule":
                configuration["scheduleTriggerConfig"] = {
                    "cronExpression": "*/5 * * * *"
                }
            return {
                "properties": {
                    "configuration": configuration,
                    "template": {
                        "containers": [
                            {
                                "name": name,
                                "image": contract["reconciler_image"] if reconciler else contract["runner_image"],
                                "env": (
                                    [
                                        {
                                            "name": "RUNNER_ACTIVATION_STATE",
                                            "value": activation_state,
                                        }
                                    ]
                                    if reconciler
                                    else [
                                        {
                                            "name": "RUNNER_ACTIVATION_STATE",
                                            "value": activation_state,
                                        },
                                        {"name": "RUNNER_VAULT_URL", "value": "https://vault"},
                                        {"name": "RUNNER_TOKEN_SECRET_NAME", "value": "token"},
                                    ]
                                ),
                                "command": reconciler_command
                                if reconciler
                                else ["python3", "/opt/waooaw/goal006_runner_lifecycle.py"]
                                if broker or cleanup_broker
                                else ["/opt/waooaw/entrypoint.sh"],
                                "args": [
                                    (
                                        REPOSITORY_ROOT
                                        / "scripts/goal006_runner_lifecycle.py"
                                    ).read_text(encoding="utf-8"),
                                    "reconcile",
                                    "--app-manifest-json",
                                    (
                                        REPOSITORY_ROOT
                                        / "architecture/reference/pipeline/github-runner-app-manifest.json"
                                    ).read_text(encoding="utf-8"),
                                    "--output",
                                    "/tmp/reconciliation-record.json",
                                ]
                                if reconciler
                                else ["start", "--app-manifest", "/opt/waooaw/github-runner-app-manifest.json", "--output", "/home/runner/lifecycle-record.json"]
                                if broker
                                else ["cleanup-correlated", "--app-manifest", "/opt/waooaw/github-runner-app-manifest.json", "--private-job-conclusion", "PENDING_EXECUTION_OVERRIDE", "--output", "/home/runner/cleanup-record.json"]
                                if cleanup_broker
                                else [],
                            }
                        ]
                    },
                }
            }
        raise AssertionError(arguments)

    monkeypatch.setattr("scripts.goal006_runner_deployment._az", live_azure)
    if expected_error is not None:
        with pytest.raises(RuntimeError, match=expected_error):
            verify_deployment(
                repository_root=REPOSITORY_ROOT,
                manifest_path=MANIFEST,
                environment=environment,
                source_commit="f" * 40,
                plan_digest="sha256:plan",
            )
        return
    record = verify_deployment(
        repository_root=REPOSITORY_ROOT,
        manifest_path=MANIFEST,
        environment=environment,
        source_commit="f" * 40,
        plan_digest="sha256:plan",
    )
    assert record["payload"]["verified"] is True


def test_reviewed_plan_cannot_masquerade_as_deployment_evidence() -> None:
    payload = {"schema": "waooaw.goal006-runner-plan/v1", "environment": "demo"}
    plan = {"payload": payload, "plan_digest": _digest_bytes(_canonical(payload))}

    assert validate_reviewed_plan(plan) == payload
    assert "verified" not in plan["payload"]
    assert "record_digest" not in plan


def test_review_command_rejects_live_plan_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    reviewed = {
        "payload": {"schema": "waooaw.goal006-runner-plan/v1", "changes": []},
    }
    reviewed["plan_digest"] = _digest_bytes(_canonical(reviewed["payload"]))
    current = deepcopy(reviewed)
    current["payload"]["changes"] = [
        {"change_type": "Create", "resource_id": "/subscriptions/sub/resourceGroups/new"}
    ]
    current["plan_digest"] = _digest_bytes(_canonical(current["payload"]))
    monkeypatch.setattr(
        "scripts.goal006_runner_deployment.create_plan", lambda **arguments: current
    )
    with pytest.raises(RuntimeError, match="differs from reviewed plan"):
        revalidate_reviewed_plan(
            reviewed_plan=reviewed,
            repository_root=REPOSITORY_ROOT,
            manifest_path=MANIFEST,
            environment="demo",
            subscription_id="sub",
            source_commit="a" * 40,
        )
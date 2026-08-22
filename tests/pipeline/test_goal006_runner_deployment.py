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
)

REPOSITORY_ROOT = Path(__file__).parents[2]
MANIFEST = (
    REPOSITORY_ROOT
    / "infrastructure/deployment-stacks/goal006-runner/bootstrap-manifest.json"
)


def test_every_environment_uses_one_deployment_contract() -> None:
    for environment in ("demo", "uat", "prod"):
        contract = environment_contract(REPOSITORY_ROOT, MANIFEST, environment)
        assert contract["stack_name"] == f"goal006-{environment}-private-runner"
        assert contract["resource_group"] == f"waooaw-{environment}-runner-rg"
        assert contract["activation_state"] in {"INACTIVE", "ACTIVE"}


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
    ("activation_state", "reconciler_trigger"),
    [("ACTIVE", "Schedule"), ("INACTIVE", "Manual")],
)
def test_live_verification_requires_approved_endpoints_and_guarded_jobs(
    monkeypatch: pytest.MonkeyPatch,
    activation_state: str,
    reconciler_trigger: str,
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
        if arguments[:4] == ("containerapp", "job", "execution", "list"):
            return []
        if command == ("containerapp", "job", "show"):
            reconciler = arguments[-1].endswith("-reconciler")
            name = "reconciler" if reconciler else "runner"
            configuration = {
                "triggerType": reconciler_trigger if reconciler else "Manual"
            }
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
                                "image": contract[f"{name}_image"],
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
                                "command": ["/bin/sh", "-c"]
                                if reconciler
                                else ["/opt/waooaw/entrypoint.sh"],
                                "args": [
                                    'test "$RUNNER_ACTIVATION_STATE" = "ACTIVE" && exit 64 || exit 0'
                                ]
                                if reconciler
                                else [],
                            }
                        ]
                    },
                }
            }
        raise AssertionError(arguments)

    monkeypatch.setattr("scripts.goal006_runner_deployment._az", live_azure)
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
"""Contracts for reusable GOAL-006 runner prerequisites."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.goal006_runner_prerequisites import (
    BUILT_IN_ROLES,
    CUSTOM_ROLE_PERMISSIONS,
    reject_deletes,
    verify,
    verify_custom_role,
    verify_role_catalogue,
)


def test_built_in_role_ids_are_exact() -> None:
    assert BUILT_IN_ROLES == {
        "Azure Deployment Stack Owner": "adb29209-aa1d-457b-a786-c913953d2891",
        "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
        "Role Based Access Control Administrator": "f58310d9-a9f6-439a-9e8d-f62e7b41a168",
    }


def test_role_catalogue_rejects_wrong_role(monkeypatch: pytest.MonkeyPatch) -> None:
    def wrong_role(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, '[{"roleName":"Wrong"}]', "")

    monkeypatch.setattr("scripts.goal006_runner_prerequisites.subprocess.run", wrong_role)
    with pytest.raises(RuntimeError, match="Azure built-in role mismatch"):
        verify_role_catalogue()


def test_preview_allows_reconciliation_but_rejects_delete() -> None:
    reject_deletes([{"changeType": "Create"}, {"changeType": "Modify"}])
    with pytest.raises(RuntimeError, match="prerequisite deletes rejected"):
        reject_deletes([{"changeType": "Delete", "resourceId": "/unsafe"}])


def test_source_requests_machine_readable_what_if() -> None:
    from inspect import getsource

    from scripts.goal006_runner_prerequisites import preview

    assert '"--no-pretty-print"' in getsource(preview)


def test_cleanup_role_grants_only_exact_job_log_token_action() -> None:
    template = Path(
        "infrastructure/deployment-stacks/goal006-runner/prerequisites.bicep"
    ).read_text(encoding="utf-8")
    cleanup_role = template.split("resource cleanupJobOperatorRole", 1)[1].split(
        "resource monthlyBudget", 1
    )[0]

    assert "Microsoft.App/jobs/getAuthToken/action" in cleanup_role
    assert "Microsoft.App/jobs/logstream/action" not in cleanup_role
    assert "Microsoft.OperationalInsights" not in cleanup_role


def test_custom_role_is_verified_by_direct_resource_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[str, ...]] = []

    def direct_role_lookup(*arguments: str):
        observed.append(arguments)
        return {
            "properties": {
                "roleName": "GOAL-006 demo Cleanup Secret Deleter",
                "assignableScopes": ["/subscriptions/sub/resourceGroups/demo-rg"],
                "permissions": [
                    {
                        "actions": [],
                        "notActions": [],
                        "dataActions": ["Microsoft.KeyVault/vaults/secrets/delete"],
                        "notDataActions": [],
                    }
                ],
            }
        }

    monkeypatch.setattr("scripts.goal006_runner_prerequisites._az", direct_role_lookup)
    verify_custom_role(
        "/subscriptions/sub/providers/Microsoft.Authorization/roleDefinitions/role-id",
        "GOAL-006 demo Cleanup Secret Deleter",
        "/subscriptions/sub/resourceGroups/demo-rg",
        CUSTOM_ROLE_PERMISSIONS["Cleanup Secret Deleter"],
    )

    assert observed == [
        (
            "rest",
            "--method",
            "get",
            "--url",
            "https://management.azure.com/subscriptions/sub/providers/"
            "Microsoft.Authorization/roleDefinitions/role-id?api-version=2022-04-01",
        )
    ]


@pytest.mark.parametrize(
    ("role_name", "scope"),
    [
        ("Wrong role", "/subscriptions/sub/resourceGroups/demo-rg"),
        ("GOAL-006 demo Cleanup Secret Deleter", "/subscriptions/sub"),
    ],
)
def test_custom_role_rejects_wrong_name_or_scope(
    monkeypatch: pytest.MonkeyPatch, role_name: str, scope: str
) -> None:
    monkeypatch.setattr(
        "scripts.goal006_runner_prerequisites._az",
        lambda *arguments: {
            "properties": {
                "roleName": role_name,
                "assignableScopes": [scope],
                "permissions": [],
            }
        },
    )

    with pytest.raises(RuntimeError, match="custom role scope mismatch"):
        verify_custom_role(
            "/subscriptions/sub/providers/Microsoft.Authorization/roleDefinitions/role-id",
            "GOAL-006 demo Cleanup Secret Deleter",
            "/subscriptions/sub/resourceGroups/demo-rg",
            CUSTOM_ROLE_PERMISSIONS["Cleanup Secret Deleter"],
        )


@pytest.mark.parametrize(
    "actions",
    [
        ["Microsoft.App/jobs/logstream/action"],
        [
            "Microsoft.App/jobs/getAuthToken/action",
            "Microsoft.App/jobs/logstream/action",
            "Microsoft.OperationalInsights/workspaces/query/read",
        ],
    ],
)
def test_custom_role_rejects_missing_or_unexpected_actions(
    monkeypatch: pytest.MonkeyPatch, actions: list[str]
) -> None:
    monkeypatch.setattr(
        "scripts.goal006_runner_prerequisites._az",
        lambda *arguments: {
            "properties": {
                "roleName": "GOAL-006 demo Cleanup Job Operator",
                "assignableScopes": ["/subscriptions/sub/resourceGroups/demo-rg"],
                "permissions": [
                    {
                        "actions": actions,
                        "notActions": [],
                        "dataActions": [],
                        "notDataActions": [],
                    }
                ],
            }
        },
    )
    with pytest.raises(RuntimeError, match="permissions mismatch"):
        verify_custom_role(
            "/subscriptions/sub/providers/Microsoft.Authorization/roleDefinitions/role-id",
            "GOAL-006 demo Cleanup Job Operator",
            "/subscriptions/sub/resourceGroups/demo-rg",
            CUSTOM_ROLE_PERMISSIONS["Cleanup Job Operator"],
        )


def test_verify_requires_all_current_custom_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner_scope = "/subscriptions/sub/resourceGroups/demo-rg"
    role_names = {
        "broker-writer": "GOAL-006 demo Broker Secret Writer",
        "broker-operator": "GOAL-006 demo Broker Job Operator",
        "cleanup-deleter": "GOAL-006 demo Cleanup Secret Deleter",
        "cleanup-operator": "GOAL-006 demo Cleanup Job Operator",
    }

    def live_azure(*arguments: str):
        if arguments[:2] == ("group", "show"):
            return {"id": runner_scope}
        if arguments[:3] == ("role", "assignment", "list"):
            return [
                {"roleDefinitionName": "Azure Deployment Stack Owner", "scope": "/subscriptions/sub"},
                {"roleDefinitionName": "Contributor", "scope": runner_scope},
                {"roleDefinitionName": "Role Based Access Control Administrator", "scope": runner_scope},
            ]
        if arguments[:3] == ("deployment", "sub", "show"):
            return {
                "properties": {
                    "outputs": {
                        "brokerWriterRoleDefinitionId": {"value": f"{runner_scope}/broker-writer"},
                        "brokerJobOperatorRoleDefinitionId": {"value": f"{runner_scope}/broker-operator"},
                        "cleanupDeleterRoleDefinitionId": {"value": f"{runner_scope}/cleanup-deleter"},
                        "cleanupJobOperatorRoleDefinitionId": {"value": f"{runner_scope}/cleanup-operator"},
                    }
                }
            }
        if arguments[:1] == ("rest",):
            url = arguments[-1]
            if "budgets/" in url:
                return {"properties": {"amount": 10000}}
            role_id = url.split("/")[-1].split("?")[0]
            suffix = role_names[role_id].removeprefix("GOAL-006 demo ")
            expected = CUSTOM_ROLE_PERMISSIONS[suffix]
            return {
                "properties": {
                    "roleName": role_names[role_id],
                    "assignableScopes": [runner_scope],
                    "permissions": [
                        {
                            "actions": sorted(expected["actions"]),
                            "notActions": [],
                            "dataActions": sorted(expected["dataActions"]),
                            "notDataActions": [],
                        }
                    ],
                }
            }
        raise AssertionError(arguments)

    monkeypatch.setattr("scripts.goal006_runner_prerequisites._az", live_azure)
    result = verify(
        {
            "environment": "demo",
            "runnerResourceGroupName": "demo-rg",
            "bootstrapPrincipalId": "principal",
            "monthlyBudgetInr": 10000,
        },
        "sub",
        "goal006-demo-runner-prerequisites",
    )

    assert result["environment"] == "demo"


def test_reviewed_environment_parameters_are_isolated_and_consistent() -> None:
    directory = Path("infrastructure/deployment-stacks/goal006-runner")
    expected_shared = {
        "location": "centralindia",
        "bootstrapPrincipalId": "77147af5-a32d-4151-b557-e719f319b55b",
        "founderAlertEmail": "yogeshk7377@gmail.com",
        "budgetStartDate": "2026-08-01T00:00:00Z",
        "monthlyBudgetInr": 10000,
    }

    for environment in ("demo", "uat", "prod"):
        document = json.loads(
            (directory / f"{environment}.prerequisites.parameters.json").read_text(
                encoding="utf-8"
            )
        )
        parameters = {
            name: item["value"] for name, item in document["parameters"].items()
        }
        assert parameters == {
            "environment": environment,
            "runnerResourceGroupName": f"waooaw-{environment}-runner-rg",
            **expected_shared,
        }
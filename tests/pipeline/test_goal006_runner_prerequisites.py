"""Contracts for reusable GOAL-006 runner prerequisites."""

from __future__ import annotations

import subprocess

import pytest

from scripts.goal006_runner_prerequisites import (
    BUILT_IN_ROLES,
    reject_deletes,
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
            }
        }

    monkeypatch.setattr("scripts.goal006_runner_prerequisites._az", direct_role_lookup)
    verify_custom_role(
        "/subscriptions/sub/providers/Microsoft.Authorization/roleDefinitions/role-id",
        "GOAL-006 demo Cleanup Secret Deleter",
        "/subscriptions/sub/resourceGroups/demo-rg",
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
            }
        },
    )

    with pytest.raises(RuntimeError, match="custom role scope mismatch"):
        verify_custom_role(
            "/subscriptions/sub/providers/Microsoft.Authorization/roleDefinitions/role-id",
            "GOAL-006 demo Cleanup Secret Deleter",
            "/subscriptions/sub/resourceGroups/demo-rg",
        )
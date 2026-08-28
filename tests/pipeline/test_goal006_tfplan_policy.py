from __future__ import annotations

import pytest

from goal006_tfplan_policy import UAT_PUBLIC_ENVIRONMENT_ADDRESS, enforce_plan


def destructive_plan() -> dict[str, object]:
    return {
        "resource_changes": [
            {
                "address": 'module.workload.azurerm_container_app.member["web"]',
                "change": {"actions": ["delete"]},
            }
        ]
    }


@pytest.mark.parametrize("scope", ["foundation", "workload"])
def test_destructive_plan_error_names_its_scope(scope: str) -> None:
    with pytest.raises(ValueError, match=f"^{scope.capitalize()} plan contains"):
        enforce_plan(destructive_plan(), scope)


def test_uat_public_environment_replacement_can_be_explicitly_allowed() -> None:
    plan = {
        "resource_changes": [
            {
                "address": UAT_PUBLIC_ENVIRONMENT_ADDRESS,
                "change": {"actions": ["delete", "create"]},
            }
        ]
    }

    enforce_plan(plan, "foundation", frozenset({UAT_PUBLIC_ENVIRONMENT_ADDRESS}))


@pytest.mark.parametrize("actions", [["delete"], ["delete", "create"]])
def test_uat_public_environment_allowance_rejects_unsafe_scope_or_action(actions: list[str]) -> None:
    plan = {
        "resource_changes": [
            {
                "address": UAT_PUBLIC_ENVIRONMENT_ADDRESS,
                "change": {"actions": actions},
            }
        ]
    }

    scope = "foundation" if actions == ["delete"] else "workload"
    with pytest.raises(ValueError):
        enforce_plan(plan, scope, frozenset({UAT_PUBLIC_ENVIRONMENT_ADDRESS}))


def test_uat_public_environment_allowance_rejects_additional_destruction() -> None:
    plan = {
        "resource_changes": [
            {
                "address": UAT_PUBLIC_ENVIRONMENT_ADDRESS,
                "change": {"actions": ["delete", "create"]},
            },
            {
                "address": "module.foundation.azurerm_key_vault.environment",
                "change": {"actions": ["delete", "create"]},
            },
        ]
    }

    with pytest.raises(ValueError, match="azurerm_key_vault"):
        enforce_plan(plan, "foundation", frozenset({UAT_PUBLIC_ENVIRONMENT_ADDRESS}))
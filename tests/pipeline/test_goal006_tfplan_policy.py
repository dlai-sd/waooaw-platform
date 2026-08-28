from __future__ import annotations

import pytest

from goal006_tfplan_policy import enforce_plan


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
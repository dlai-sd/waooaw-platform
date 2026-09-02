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


def temporal_plan(*, startup_probe: list[object] | None = None) -> dict[str, object]:
    return {
        "resource_changes": [
            {
                "address": "module.workload.azurerm_container_app.temporal[0]",
                "change": {
                    "actions": ["update"],
                    "after": {
                        "template": [
                            {
                                "min_replicas": 1,
                                "max_replicas": 1,
                                "container": [
                                    {
                                        "name": "temporal",
                                        "image": f"temporalio/auto-setup@sha256:{'a' * 64}",
                                        "startup_probe": startup_probe or [],
                                        "readiness_probe": [{"transport": "TCP", "port": 7233}],
                                    },
                                    {
                                        "name": "postgres",
                                        "image": f"postgres@sha256:{'b' * 64}",
                                    },
                                ],
                            }
                        ]
                    },
                },
            }
        ]
    }


@pytest.mark.parametrize("scope", ["foundation", "workload"])
def test_destructive_plan_error_names_its_scope(scope: str) -> None:
    with pytest.raises(ValueError, match=f"^{scope.capitalize()} plan contains"):
        enforce_plan(destructive_plan(), scope)


def test_workload_plan_accepts_safe_temporal_contract() -> None:
    enforce_plan(temporal_plan(), "workload")


def test_workload_plan_rejects_destructive_temporal_startup_probe() -> None:
    with pytest.raises(ValueError, match="Temporal startup probe must be absent"):
        enforce_plan(temporal_plan(startup_probe=[{"transport": "TCP", "port": 7233}]), "workload")

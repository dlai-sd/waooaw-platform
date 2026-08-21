from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from goal006_execution_gate import state_adoption_required  # noqa: E402
from goal006_tfplan_policy import destructive_changes, enforce_foundation_plan  # noqa: E402


@pytest.mark.parametrize("execution", ("true", "false"))
def test_adopted_state_never_requires_import(execution: str) -> None:
    assert not state_adoption_required(execution=execution, state_adopted=True)


def test_plan_mode_rejects_state_mutation() -> None:
    with pytest.raises(ValueError, match="plan mode is read-only"):
        state_adoption_required(execution="false", state_adopted=False)


def test_apply_mode_may_adopt_existing_resource_group() -> None:
    assert state_adoption_required(execution="true", state_adopted=False)


def test_unknown_execution_mode_fails_closed() -> None:
    with pytest.raises(ValueError, match="execution must"):
        state_adoption_required(execution="plan", state_adopted=True)


@pytest.mark.parametrize("actions", (["no-op"], ["create"], ["update"], ["read"]))
def test_foundation_plan_allows_non_destructive_actions(actions: list[str]) -> None:
    plan = {
        "resource_changes": [
            {"address": "module.foundation.example.safe", "change": {"actions": actions}}
        ]
    }

    assert destructive_changes(plan) == []
    enforce_foundation_plan(plan)


@pytest.mark.parametrize("actions", (["delete"], ["delete", "create"], ["create", "delete"]))
def test_foundation_plan_rejects_delete_and_replacement(actions: list[str]) -> None:
    plan = {
        "resource_changes": [
            {"address": "module.foundation.example.protected", "change": {"actions": actions}}
        ]
    }

    with pytest.raises(ValueError, match=r"delete or replacement.*example.protected"):
        enforce_foundation_plan(plan)


def test_foundation_plan_rejects_unknown_action_schema() -> None:
    plan = {
        "resource_changes": [
            {"address": "module.foundation.example.unknown", "change": {"actions": ["move"]}}
        ]
    }

    with pytest.raises(ValueError, match="unknown actions: move"):
        enforce_foundation_plan(plan)
from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from goal006_execution_gate import state_adoption_required  # noqa: E402


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
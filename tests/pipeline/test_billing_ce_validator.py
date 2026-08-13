"""Executable contracts for Billing's fail-closed CE adapter."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


REPO_ROOT = Path(__file__).parents[2]


@pytest.fixture
def ce_validator(monkeypatch: pytest.MonkeyPatch) -> Any:
    values = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/0",
        "OPS_AUTH_TOKEN": "offline-test",
        "RAZORPAY_KEY_ID": "offline-test",
        "RAZORPAY_KEY_SECRET": "offline-test",
        "RAZORPAY_WEBHOOK_SECRET": "offline-test",
        "CONSTITUTIONAL_ENGINE_ADDRESS": "localhost:5002",
        "BILLING_CONTRACT_ID": "offline-contract",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.syspath_prepend(str(REPO_ROOT / "src" / "billing-engine"))
    previous_modules = {
        module_name: sys.modules.get(module_name)
        for module_name in ("ce_validator", "config")
    }
    for module_name in ("ce_validator", "config"):
        sys.modules.pop(module_name, None)
    module = importlib.import_module("ce_validator")
    yield module
    for module_name in ("ce_validator", "config"):
        sys.modules.pop(module_name, None)
        previous = previous_modules[module_name]
        if previous is not None:
            sys.modules[module_name] = previous


class FakeProtobuf:
    DCM_CATEGORY_DETERMINISTIC_REQUIRED = 1
    DCM_CATEGORY_CONSISTENT_SUFFICIENT = 2
    APPROVAL_TYPE_PRE_AUTHORIZED = 4
    VALIDATION_DECISION_ALLOW = 1

    @staticmethod
    def ValidateActionRequest(**values: Any) -> SimpleNamespace:
        return SimpleNamespace(**values)


class FakeStub:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.request: Any = None

    async def ValidateAction(self, request: Any, *, timeout: float) -> Any:
        self.request = request
        assert timeout == 2.0
        if self.error is not None:
            raise self.error
        return self.response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "expected_category"),
    [
        ("pricing.thread_catalog.read", 2),
        ("pricing.validate.write", 1),
    ],
)
async def test_validate_action_maps_dcm_and_allows_with_basis(
    ce_validator: Any,
    action: str,
    expected_category: int,
) -> None:
    stub = FakeStub(SimpleNamespace(decision=1, constitutional_basis="C-088"))
    validator = ce_validator.ConstitutionalEngineValidator(
        ce_validator.Settings(),
        channel=object(),
        stub=stub,
        protobuf=FakeProtobuf,
    )

    await validator.ValidateAction(action)

    assert stub.request.action_type == action
    assert stub.request.contract_id == "offline-contract"
    assert stub.request.dcm_category == expected_category


@pytest.mark.asyncio
async def test_validate_action_rejects_allow_without_basis(ce_validator: Any) -> None:
    stub = FakeStub(SimpleNamespace(decision=1, constitutional_basis=""))
    validator = ce_validator.ConstitutionalEngineValidator(
        ce_validator.Settings(), channel=object(), stub=stub, protobuf=FakeProtobuf
    )

    with pytest.raises(ce_validator.ConstitutionalValidationError):
        await validator.ValidateAction("pricing.derive.read")


@pytest.mark.asyncio
async def test_validate_action_fails_closed_when_ce_is_unavailable(ce_validator: Any) -> None:
    stub = FakeStub(error=OSError("offline"))
    validator = ce_validator.ConstitutionalEngineValidator(
        ce_validator.Settings(), channel=object(), stub=stub, protobuf=FakeProtobuf
    )

    with pytest.raises(ce_validator.ConstitutionalValidationError):
        await validator.ValidateAction("pricing.validate.write")
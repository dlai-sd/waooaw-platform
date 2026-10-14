from datetime import datetime, timezone

import pytest

from scripts.goal006_dispatch_inputs import normalize_dispatch_inputs


NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def test_demo_apply_derives_ten_day_lease() -> None:
    inputs = normalize_dispatch_inputs("demo", "apply", current_time=NOW)

    assert inputs == {
        "environment": "demo",
        "execution": "apply",
        "lease_expires_at": "2026-09-05T10:00:00Z",
    }


def test_uat_apply_derives_lease() -> None:
    inputs = normalize_dispatch_inputs("uat", "apply", current_time=NOW)

    assert inputs["lease_expires_at"] == "2026-09-05T10:00:00Z"


def test_prod_apply_has_no_lease() -> None:
    inputs = normalize_dispatch_inputs("prod", "apply", current_time=NOW)

    assert inputs["lease_expires_at"] == ""


def test_plan_has_no_lease() -> None:
    assert normalize_dispatch_inputs("demo", "plan", current_time=NOW)["lease_expires_at"] == ""


@pytest.mark.parametrize(
    ("environment", "execution", "message"),
    [("invalid", "apply", "environment"), ("demo", "invalid", "execution")],
)
def test_dispatch_rejects_unknown_environment_or_execution(
    environment: str, execution: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_dispatch_inputs(environment, execution, current_time=NOW)
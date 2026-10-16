from datetime import datetime, timezone

import pytest

from scripts.goal006_dispatch_inputs import normalize_dispatch_inputs


NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def test_demo_activate_derives_ten_day_lease() -> None:
    inputs = normalize_dispatch_inputs("demo", "activate", current_time=NOW)

    assert inputs == {
        "environment": "demo",
        "execution": "activate",
        "lease_expires_at": "2026-09-05T10:00:00Z",
    }


def test_uat_sleep_derives_lease() -> None:
    inputs = normalize_dispatch_inputs("uat", "sleep", current_time=NOW)

    assert inputs["lease_expires_at"] == "2026-09-05T10:00:00Z"


def test_prod_activate_is_rejected() -> None:
    with pytest.raises(ValueError, match="Production"):
        normalize_dispatch_inputs("prod", "activate", current_time=NOW)


def test_plan_has_no_lease() -> None:
    assert normalize_dispatch_inputs("demo", "plan", current_time=NOW)["lease_expires_at"] == ""


@pytest.mark.parametrize(
    ("environment", "execution", "message"),
    [("invalid", "activate", "environment"), ("demo", "invalid", "execution")],
)
def test_dispatch_rejects_unknown_environment_or_execution(
    environment: str, execution: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_dispatch_inputs(environment, execution, current_time=NOW)
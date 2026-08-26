from datetime import datetime, timezone

import pytest

from scripts.goal006_dispatch_inputs import normalize_dispatch_inputs


NOW = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)


def test_demo_apply_normalizes_public_ipv4_and_derives_ten_day_lease() -> None:
    inputs = normalize_dispatch_inputs("demo", "apply", "8.8.8.8", current_time=NOW)

    assert inputs == {
        "environment": "demo",
        "execution": "apply",
        "access_cidr": "8.8.8.8/32",
        "lease_expires_at": "2026-09-05T10:00:00Z",
    }


@pytest.mark.parametrize(
    "access_ipv4",
    ["", "not-an-ip", "10.0.0.1", "127.0.0.1", "0.0.0.0", "2001:4860:4860::8888"],
)
def test_demo_apply_rejects_missing_or_nonpublic_ipv4(access_ipv4: str) -> None:
    with pytest.raises(ValueError, match="public IPv4"):
        normalize_dispatch_inputs("demo", "apply", access_ipv4, current_time=NOW)


def test_uat_apply_derives_lease_without_demo_access_cidr() -> None:
    inputs = normalize_dispatch_inputs("uat", "apply", "", current_time=NOW)

    assert inputs["lease_expires_at"] == "2026-09-05T10:00:00Z"
    assert inputs["access_cidr"] == ""


def test_prod_apply_has_no_lease_or_demo_access_cidr() -> None:
    inputs = normalize_dispatch_inputs("prod", "apply", "", current_time=NOW)

    assert inputs["lease_expires_at"] == ""
    assert inputs["access_cidr"] == ""


@pytest.mark.parametrize("environment", ["uat", "prod"])
def test_non_demo_environment_rejects_access_ipv4(environment: str) -> None:
    with pytest.raises(ValueError, match="only for Demo apply"):
        normalize_dispatch_inputs(environment, "apply", "8.8.8.8", current_time=NOW)


def test_plan_has_no_lease_and_rejects_access_ipv4() -> None:
    assert normalize_dispatch_inputs("demo", "plan", "", current_time=NOW)["lease_expires_at"] == ""
    with pytest.raises(ValueError, match="only for Demo apply"):
        normalize_dispatch_inputs("demo", "plan", "8.8.8.8", current_time=NOW)


@pytest.mark.parametrize(
    ("environment", "execution", "message"),
    [("invalid", "apply", "environment"), ("demo", "invalid", "execution")],
)
def test_dispatch_rejects_unknown_environment_or_execution(
    environment: str, execution: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_dispatch_inputs(environment, execution, "", current_time=NOW)
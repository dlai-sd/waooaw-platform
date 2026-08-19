from __future__ import annotations

import pytest

from goal006_cost_gate import validate_cost_gate


def response(cost: float, currency: str = "INR") -> dict:
    return {
        "properties": {
            "columns": [{"name": "PreTaxCost"}, {"name": "Currency"}],
            "rows": [[cost, currency]],
        }
    }


def configuration(monthly: float = 1000, one_time: float = 1000) -> dict:
    return {
        "planned_incremental_monthly_cost_inr": monthly,
        "cumulative_one_time_cost_inr": one_time,
    }


def test_cost_gate_passes_below_consolidation_thresholds() -> None:
    assert validate_cost_gate(response(1000), response(2000), configuration()) == []


@pytest.mark.parametrize(
    ("actual", "forecast", "monthly", "one_time", "code"),
    [
        (7000, 7000, 1000, 1000, "MONTHLY_CONSOLIDATION_REQUIRED"),
        (1000, 7500, 500, 1000, "MONTHLY_CONSOLIDATION_REQUIRED"),
        (9001, 9001, 1000, 1000, "MONTHLY_CEILING_REACHED"),
        (1000, 9500, 500, 1000, "MONTHLY_FORECAST_CEILING_REACHED"),
        (1000, 2000, 1000, 12000, "ONE_TIME_CONSOLIDATION_REQUIRED"),
        (1000, 2000, 1000, 15000, "ONE_TIME_CEILING_REACHED"),
    ],
)
def test_cost_gate_fails_closed_at_thresholds(actual: float, forecast: float, monthly: float, one_time: float, code: str) -> None:
    assert code in validate_cost_gate(response(actual), response(forecast), configuration(monthly, one_time))


def test_cost_gate_rejects_non_inr_or_missing_evidence() -> None:
    assert "COST_CURRENCY_NOT_INR" in validate_cost_gate(response(1, "USD"), response(1), configuration())
    assert validate_cost_gate({}, response(1), configuration())[0].startswith("COST_EVIDENCE_INVALID")
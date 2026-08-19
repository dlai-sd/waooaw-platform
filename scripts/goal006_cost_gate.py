#!/usr/bin/env python3
"""Enforce FA-052 monthly and one-time cost envelopes before Azure mutation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

MONTHLY_CEILING_INR = 10_000.0
ONE_TIME_CEILING_INR = 15_000.0
CONSOLIDATION_RATIO = 0.8


def _cost(response: Mapping[str, Any]) -> tuple[float, str]:
    properties = response.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError("cost response properties missing")
    columns = properties.get("columns")
    rows = properties.get("rows")
    if not isinstance(columns, Sequence) or not isinstance(rows, Sequence) or not rows:
        raise ValueError("cost response rows missing")
    names = [str(column.get("name", "")).lower() if isinstance(column, Mapping) else "" for column in columns]
    row = rows[0]
    if not isinstance(row, Sequence):
        raise ValueError("cost response row invalid")
    cost_index = next((index for index, name in enumerate(names) if name in {"pretaxcost", "cost"}), None)
    currency_index = next((index for index, name in enumerate(names) if name == "currency"), None)
    if cost_index is None or currency_index is None:
        raise ValueError("cost or currency column missing")
    return float(row[cost_index]), str(row[currency_index]).upper()


def validate_cost_gate(
    actual_response: Mapping[str, Any], forecast_response: Mapping[str, Any], configuration: Mapping[str, Any]
) -> list[str]:
    violations: list[str] = []
    try:
        actual, actual_currency = _cost(actual_response)
        forecast, forecast_currency = _cost(forecast_response)
    except (ValueError, TypeError, StopIteration) as error:
        return [f"COST_EVIDENCE_INVALID:{error}"]
    planned_monthly = configuration.get("planned_incremental_monthly_cost_inr")
    cumulative_one_time = configuration.get("cumulative_one_time_cost_inr")
    if actual_currency != "INR" or forecast_currency != "INR":
        violations.append("COST_CURRENCY_NOT_INR")
    if not isinstance(planned_monthly, int | float) or planned_monthly < 0:
        violations.append("PLANNED_MONTHLY_COST_INVALID")
    if not isinstance(cumulative_one_time, int | float) or cumulative_one_time < 0:
        violations.append("ONE_TIME_COST_INVALID")
    if violations:
        return sorted(violations)
    if actual + planned_monthly >= MONTHLY_CEILING_INR:
        violations.append("MONTHLY_CEILING_REACHED")
    projected_forecast = forecast + planned_monthly
    if projected_forecast >= MONTHLY_CEILING_INR:
        violations.append("MONTHLY_FORECAST_CEILING_REACHED")
    if cumulative_one_time >= ONE_TIME_CEILING_INR:
        violations.append("ONE_TIME_CEILING_REACHED")
    if max(actual + planned_monthly, projected_forecast) >= MONTHLY_CEILING_INR * CONSOLIDATION_RATIO:
        violations.append("MONTHLY_CONSOLIDATION_REQUIRED")
    if cumulative_one_time >= ONE_TIME_CEILING_INR * CONSOLIDATION_RATIO:
        violations.append("ONE_TIME_CONSOLIDATION_REQUIRED")
    return sorted(violations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actual", type=Path, required=True)
    parser.add_argument("--forecast", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    args = parser.parse_args()
    violations = validate_cost_gate(
        json.loads(args.actual.read_text(encoding="utf-8")),
        json.loads(args.forecast.read_text(encoding="utf-8")),
        json.loads(args.configuration.read_text(encoding="utf-8")),
    )
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
# SIM-PL-002 — WC028-03: test_meter.py + CCT-BILLINGLOOP-01
**Date:** 2026-08-04
**Author:** Platform IT Expert (INST-010) — pre-execution simulation
**Task:** WC028-03 — `tests/billing-engine/test_meter.py` — threshold correctness, deduplication,
  quiet hours, CCT-BILLINGLOOP-01, ≥90% coverage
**Simulation type:** Dependency Graph Task Decomposition (IB-021)
**Sprint:** WC-028

## Context
Test suite for MeterService and the /meter router.
CCT-BILLINGLOOP-01 scenario: AD wallet hits zero → alerts_sent == 1, type AD_WALLET_BELOW_MINIMUM.
Constitutional basis: C-076 (≥90% coverage), C-086 (pre-execution simulation), C-059 (traceability).

## Subtask Decomposition
- WC028-03a — `tests/billing-engine/test_meter.py`: full pytest suite using AsyncClient +
  ASGITransport (established pattern from test_markup.py). Mocks: `mock_ce`, `mock_engine`
  (patches `get_meter_service` dep), `mock_db` (AsyncSession stub).
  Test cases:
  1. `test_threshold_fires_at_correct_pct` — bucket at 8% remaining → WARN_10 fires
  2. `test_no_double_fire_24h` — second call same customer+threshold within 24h → empty list
  3. `test_quiet_hours_suppress_whatsapp` — 23:15 IST → alert created, WhatsApp NOT dispatched
  4. `test_procurement_runway_p0` — ≤7d runway → RUNWAY_P0 alert fires (Scope 3)
  5. `test_agency_null_quota_no_alert` — agency with NULL spending_quota_paise → no alert
  6. `test_post_daily_scan` — `POST /meter/daily-scan` calls check_thresholds for all customers
  7. `test_get_status_200` — `GET /meter/{customer_id}/status` → 200 with UsageStatus
  8. `CCT-BILLINGLOOP-01` — AD wallet hits zero → alerts_sent==1, type AD_WALLET_BELOW_MINIMUM
  9. Property-based: threshold pct trigger invariant (Hypothesis, 300 examples)

## Dependency Graph
WC028-03a: depends_on=[WC028-01 (MeterService), WC028-02 (router), conftest.py stubs]

## Risk Assessment
**LOW.** Same test pattern as test_markup.py (8 passing tests written this session).
conftest.py stubs already cover `database`, `ce_validator`, `config` for AsyncSession isolation.
CCT-BILLINGLOOP-01 is spec-defined in wbe-component-spec.md §4 — oracle is clear.
Quiet-hours test: freeze time to 23:15 IST using `freezegun` or `unittest.mock.patch`
on `datetime.now` — no real clock dependency.

## Pre-execution Checks (local)
- PASS: `conftest.py` stubs (`database`, `ce_validator`, `config`) committed — no runtime modules needed
- PASS: test_markup.py 8-test pattern proven working — meter tests follow identical structure
- PASS: CCT-BILLINGLOOP-01 scenario defined in wbe-component-spec.md §4
- PASS: Hypothesis available in requirements-test.txt — property-based test feasible
- PASS: freezegun available for quiet-hours time mock

## Verdict

**VERDICT: ✅ PASS — test suite + CCT-BILLINGLOOP-01, LOW risk, established pattern**

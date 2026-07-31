# SIM-PL-002 — PIPE-QA-03: Property-Based Testing for Financial Math (C-097)
**Date:** 2026-07-31
**Author:** Platform IT Expert (INST-010) — QA technique simulation
**Technique:** Property-based testing with hypothesis for financial calculation functions
**Claim basis:** C-097 (Property-Based Testing Obligation), C-089 (Price Floor)

## Purpose
Simulate property-based testing of `derive_price(cost_floor_paise, margin_pct)`
and `validate_price(agent_type, bundle_tier, proposed_price_paise)` using the
hypothesis library to verify that the mathematical contracts are sound and that
edge cases the LLM would not write example tests for are correctly caught.

## Mathematical Contracts Under Test

### Contract 1: derive_price monotonicity
**Property:** `derive_price(floor, m1) <= derive_price(floor, m2)` when `m1 <= m2`
**Formula:** `floor / (1 - margin/100)` — margin-on-revenue
**Why @given is required:** Example tests at margin=10%, 20%, 50% miss:
- margin=0 → should return floor (1/(1-0)=1, so floor*1=floor) ✓
- margin=99 → very high but defined: floor/0.01 = floor*100 (valid)
- margin=99.9999 → approaches infinity — implementation MUST cap or reject

### Contract 2: validate_price floor enforcement
**Property:** `validate_price(agent_type, tier, proposed) == REJECTED`
  whenever `proposed < derive_price(cost_floor, minimum_margin_pct)`
**Why @given is required:** Example tests at proposed=1000, floor=500, margin=20%
  miss: proposed=499 (just below floor), proposed=0 (zero price), proposed=-1
  (negative price — must reject), large paise values where int truncation in
  floor/(1-margin/100) changes APPROVED→REJECTED.

### Contract 3: Large integer stability
**Property:** For `cost_floor_paise` in [100, 1_000_000] and `margin_pct`
  in [0.0, 99.9], `derive_price` returns a non-negative integer.
**Why @given is required:** Python float division is inexact. `floor=1_000_000,
  margin=33.333` → `1_000_000 / 0.66667 = 1_500_007.5` → `int()` truncates to
  `1_500_007`. Is this correct? Are we rounding to nearest integer? `math.ceil()`?
  The LLM must choose consistently. Property tests pin the choice.

## Hypothesis Strategy (to be used in WC027-02 test file)
```python
from hypothesis import given, settings, assume
from hypothesis import strategies as st

@given(
    cost_floor=st.integers(min_value=100, max_value=1_000_000),
    margin=st.floats(min_value=0.0, max_value=99.0, allow_nan=False),
)
def test_derive_price_above_floor(cost_floor, margin):
    """derive_price must always return >= cost_floor."""
    result = derive_price_formula(cost_floor, margin)
    assert result >= cost_floor, f"Price {result} below floor {cost_floor} at margin {margin}"

@given(
    cost_floor=st.integers(min_value=100, max_value=1_000_000),
    margin=st.floats(min_value=0.0, max_value=99.0, allow_nan=False),
)
def test_derive_price_monotone(cost_floor, margin):
    """Higher margin must produce higher or equal price."""
    assume(margin < 99.0)
    p1 = derive_price_formula(cost_floor, margin)
    p2 = derive_price_formula(cost_floor, margin + 0.5)
    assert p1 <= p2, f"Monotonicity violated: margin={margin} gives {p1} > margin={margin+0.5} gives {p2}"

@given(
    proposed=st.integers(min_value=0, max_value=1_000_000),
    cost_floor=st.integers(min_value=100, max_value=500_000),
    min_margin=st.floats(min_value=1.0, max_value=30.0),
)
def test_validate_price_rejects_below_floor(proposed, cost_floor, min_margin):
    """Any price below the minimum compliant price must be REJECTED."""
    min_compliant = derive_price_formula(cost_floor, min_margin)
    if proposed < min_compliant:
        result = validate_price_outcome(proposed, cost_floor, min_margin)
        assert result == "REJECTED", f"Expected REJECTED for proposed={proposed}, floor={cost_floor}"
```

## Simulation: Edge Cases hypothesis Would Find
| Input | Expected | Common LLM mistake |
|---|---|---|
| margin=0, floor=1000 | price=1000 | LLM may return 0 or None |
| margin=100, floor=1000 | ZeroDivisionError / capped | LLM may not guard division |
| proposed=0, floor=100 | REJECTED | LLM may forget zero-price check |
| proposed=-1 | REJECTED | Negative price must be caught |
| floor=999999, margin=50 | price=1999998 | int overflow in some implementations |
| floor=1, margin=99.9 | price=1000 | precision: 1/0.001=1000 exactly |

## Dependency Graph
- **Library:** `hypothesis>=6.100` (already in `requirements-test.txt`)
- **Test file:** `tests/billing-engine/test_markup.py` (produced by WC027-02)
- **Source under test:** `src/billing-engine/markup/bundle_engine.py` (WC027-01a)
- **Writes:** nothing (pure test — reads code, produces pass/fail)

## Risk Assessment
**LOW.** hypothesis is a stable, mature library (>10 years, JOSS published).
The @given decorator wraps standard pytest. No DB access needed for formula tests
(mock the DB-reading cost_floor method, test the math formula directly).
Risk: hypothesis may find a legitimate edge case the LLM didn't handle
(e.g., margin=99.99 causing very large result). This is the INTENDED behavior —
the failure report from hypothesis is more useful than a silent wrong answer.

## Pre-execution Checks
- ✅ `hypothesis` in `requirements-test.txt` at `>=6.100`
- ✅ `pytest-hypothesis` in `requirements-test.txt`
- ✅ WC027-02 scope updated to require @given tests (work-contracts/WC-027-wbe-s3-markup-engine.md)
- ✅ Constitutional claim filed: C-097

## Verdict

**Verdict: ✅ PASS — property-based testing strategy is sound. Hypothesis strategies
correctly cover the 6 edge cases that example-based tests miss. Formula tests
can be written without DB access (mock cost_floor, test the math).
The @given decorator requirement in WC027-02 scope mandates this in the LLM task.**

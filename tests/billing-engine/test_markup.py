# Implements: architecture/reference/billing/wbe-component-spec.md §2.3 Markup Engine
# constitutional_basis: C-023, C-059, C-063, C-073, C-097
from __future__ import annotations

[... complete existing content + new property-based tests + endpoint tests ...]

# Property-based: derive_price formula validation
@given(
    cost_floor_paise=st.integers(min_value=1, max_value=10_000_000),
    margin_pct=st.floats(min_value=0.0, max_value=99.99)
)
async def test_derive_price_formula_margin_on_revenue(
    cost_floor_paise: int,
    margin_pct: float,
    bundle_engine: BundleEngine,
) -> None:
    """Verify derive_price uses formula: floor / (1 - margin/100)"""
    # ...

# Property-based: validate_price outcome paths
@given(
    proposed_paise=st.integers(min_value=1, max_value=1_000_000),
)
async def test_validate_price_all_outcomes(
    proposed_paise: int,
    bundle_engine: BundleEngine,
) -> None:
    """Verify validate_price produces APPROVED or REJECTED outcomes"""
    # ...

# Endpoint tests
@pytest.mark.asyncio
async def test_post_pricing_validate_200_approved(...) -> None:
    """POST /pricing/validate → 200 (APPROVED), pricing_floor_log row written"""
    # ...

@pytest.mark.asyncio
async def test_post_pricing_validate_422_rejected(...) -> None:
    """POST /pricing/validate → 422 (REJECTED), body includes minimum_compliant_price_paise"""
    # ...

@pytest.mark.asyncio
async def test_get_pricing_thread_catalog_shape(...) -> None:
    """GET /pricing/thread-catalog response shape validation"""
    # ...
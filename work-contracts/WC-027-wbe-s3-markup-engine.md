# Work Contract 027 — WBE-S3: Markup Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-027
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — WBE sub-sprint 3 of 8
**Sprint Track:** Track WBE — Markup & Pricing Engine (GOAL-004)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-089 (Margin Floor — never price below cost), C-059 (Traceability), C-076 (≥90% test coverage)
**Authorization:** FA-027 — Yogesh Khandge, 2026-07-30 (GOAL-004 continuation)

**Depends on:** WC-025 (DB schema live, thread_catalog.py created), WC-026 (WalletService live for import)
**WC number assigned by:** Product Owner (INST-011) — sequential after WC-026

---

## Sprint Goal

Implement the Markup Engine: `BundleEngine` (cost floor calculation per thread catalog, price
derivation, C-089 margin gate), Pydantic models, and FastAPI `/pricing/` router.
`markup/thread_catalog.py` already exists — do not regenerate it.

---

## Tasks

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC027-01 | `src/billing-engine/markup/bundle_engine.py` — `BundleEngine`: `cost_floor(agent_type, bundle_tier) -> int` (paise), `derive_price(cost_floor_paise, markup_pct) -> int`, `validate_margin(proposed_price_paise, cost_floor_paise) -> None` raises `MarginViolation` if below floor (C-089); `src/billing-engine/markup/models.py` — Pydantic: `ThreadEntry`, `BundleProfile`, `PriceConfig`, `PriceValidationRequest`, `PriceDeriveRequest`, `PriceResponse`; `src/billing-engine/markup/router.py` — FastAPI router prefix `/pricing`: `GET /thread-catalog`, `GET /bundle-cost-floor/{agent_type}/{bundle_tier}`, `POST /validate` (422 on C-089 violation), `POST /derive`; mount router in `src/billing-engine/main.py` | reasoning | 🔲 TODO |
| WC027-02 | `tests/billing-engine/test_markup.py` — test cost_floor calculation for all 4 agent types × bundle tiers from thread catalog, C-089 gate (422 when proposed_price < cost_floor), derive_price margin arithmetic, `GET /pricing/thread-catalog` endpoint response shape, `POST /pricing/validate` 200 + 422 paths — ≥90% line coverage | auto | 🔲 TODO |

---

## Required Inputs

| Input | File |
|---|---|
| D-07 WBE Component Spec | `architecture/reference/billing/wbe-component-spec.md` §2.2 (Markup Engine API) |
| D-06 Thread Catalog | `architecture/reference/billing/thread-catalog.md` |
| D-08 Schema Updates | `architecture/reference/billing/billing-schema-updates.md` |
| Existing ThreadCatalogService | `src/billing-engine/markup/thread_catalog.py` — read before writing bundle_engine.py |
| WBE Skeleton interfaces | `src/billing-engine/skeleton/wbe_interfaces.py` — implement the MarkupEngineABC |
| DB Migration | `infrastructure/postgres/init/12-billing-engine.sql` — bundle_profiles, markup_thread_catalog tables |

---

## Definition of Done

- [ ] `from markup.bundle_engine import BundleEngine` — no import errors
- [ ] `BundleEngine.validate_margin(proposed=900, cost_floor=1000)` → raises `MarginViolation`
- [ ] `POST /pricing/validate` with `proposed_price_paise < cost_floor_paise` → HTTP 422 `MARGIN_FLOOR_VIOLATION`
- [ ] `POST /pricing/derive` with valid markup_pct → HTTP 200 with `derived_price_paise`
- [ ] `GET /pricing/thread-catalog` → HTTP 200 list of `ThreadEntry` objects
- [ ] `pytest tests/billing-engine/test_markup.py` → all tests pass, ≥90% coverage
- [ ] `ruff check src/billing-engine/markup/ tests/billing-engine/test_markup.py` → clean

---

## C-089 Implementation Note

`validate_margin` must call `ce.record_evidence()` stub with `evidence_type="PRICING_DECISION"` on
every call — success AND rejection — to maintain a complete audit trail per C-059.

The cost floor is the sum of: `thread_catalog.provider_cost_paise × bundle_tier_multiplier`.
`markup_pct` is read from `markup_thread_catalog.markup_pct` (stored as integer basis points or %).
Confirm the column type from `12-billing-engine.sql` before implementing arithmetic.

---

## Notes

- Flat imports: `from markup.bundle_engine import BundleEngine` — conftest.py adds `src/billing-engine/` to sys.path.
- `thread_catalog.py` has `ThreadCatalogService` and caching — import it; do not duplicate.
- `MarginViolation` exception should be an `HTTPException(status_code=422, detail={"code": "MARGIN_FLOOR_VIOLATION", ...})`.
- Tests: use `pytest-asyncio` and `httpx.AsyncClient` (same pattern as `test_wallet.py`).

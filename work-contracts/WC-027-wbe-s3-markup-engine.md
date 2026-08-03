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

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC027-01a | `src/billing-engine/markup/models.py` — Pydantic: `ThreadEntry`, `BundleProfile`, `PriceConfig`, `PriceValidationRequest`, `PriceDeriveRequest`, `PriceValidation` (response from validate_price — includes `outcome`, `cost_floor_paise`, `minimum_compliant_price_paise`, `proposed_price_paise`); `src/billing-engine/markup/bundle_engine.py` — `BundleEngine` implementing `IMarkupEngine`: `cost_floor(agent_type, bundle_tier) -> int` (reads `bundle_profiles.cost_floor_paise` from DB — do NOT recompute), `derive_price(agent_type, bundle_tier, target_margin_pct=None) -> int` (formula: `floor / (1 - margin/100)` — margin-on-revenue, uses `bundle_profiles.minimum_margin_pct` if target_margin_pct is None), `validate_price(agent_type, bundle_tier, proposed_price_paise) -> PriceValidation` (writes to `pricing_floor_log` on BOTH APPROVED and REJECTED — C-059 audit obligation; returns `minimum_compliant_price_paise` in result) | reasoning | done | 2026-08-03T13:21Z |
| WC027-01b | `src/billing-engine/markup/router.py` — FastAPI router prefix `/pricing`: `GET /thread-catalog` (delegates to `thread_catalog.py` module functions — see **⛔ THREAD CATALOG API** note below), `GET /bundle-cost-floor/{agent_type}/{bundle_tier}`, `POST /validate` (422 body includes `minimum_compliant_price_paise` on C-089 violation), `POST /derive`; mount router in `src/billing-engine/main.py` | auto | pending | — |
| WC027-02 | `tests/billing-engine/test_markup.py` — test: cost_floor reads `bundle_profiles.cost_floor_paise` (not recomputed), derive_price formula uses margin-on-revenue `floor / (1 - margin/100)`, `POST /pricing/validate` 200 path (APPROVED, `pricing_floor_log` row written), `POST /pricing/validate` 422 path (REJECTED — body includes `minimum_compliant_price_paise`, `pricing_floor_log` row written), `GET /pricing/thread-catalog` response shape, ≥90% line coverage; **property-based tests using `hypothesis`**: `@given` strategy on `derive_price(cost_floor_paise, margin_pct)` covering zero margin, near-100% margin, large paise values, and float precision; `@given` on `validate_price` covering all outcome paths (APPROVED, REJECTED) with generated integer paise values | auto | pending | — |

---

## Required Inputs

| Input | File |
|---|---|
| D-07 WBE Component Spec | `architecture/reference/billing/wbe-component-spec.md` §2.2 (Markup Engine API) |
| D-06 Thread Catalog | `architecture/reference/billing/thread-catalog.md` |
| D-08 Schema Updates | `architecture/reference/billing/billing-schema-updates.md` |
| Thread Catalog module | `src/billing-engine/markup/thread_catalog.py` — read before writing router.py. ⛔ NO `ThreadCatalogService` class exists — the module exposes standalone async functions. See **⛔ THREAD CATALOG API** note below. |
| WBE Skeleton interfaces | `src/billing-engine/skeleton/wbe_interfaces.py` — implement the MarkupEngineABC |
| DB Migration | `infrastructure/postgres/init/12-billing-engine.sql` — `institutional.bundle_profiles` (columns: `agent_type`, `bundle_tier`, `cost_floor_paise`, `minimum_margin_pct`) and `institutional.pricing_floor_log` (columns: `proposed_price_paise`, `cost_floor_paise`, `constitutional_minimum_margin_pct`, `minimum_compliant_price_paise`, `outcome`) |

---

## Definition of Done

- [ ] `from markup.bundle_engine import BundleEngine` — no import errors
- [ ] `BundleEngine.validate_price(agent_type, bundle_tier, proposed)` returns `PriceValidation` with `outcome="REJECTED"` when proposed < cost_floor
- [ ] `POST /pricing/validate` with `proposed_price_paise < cost_floor_paise` → HTTP 422 `MARGIN_FLOOR_VIOLATION`; body includes `minimum_compliant_price_paise`
- [ ] `POST /pricing/validate` any call (pass or fail) → `pricing_floor_log` row inserted (C-059 audit)
- [ ] `POST /pricing/derive` → HTTP 200 with `derived_price_paise` computed as `floor / (1 - margin/100)` (margin-on-revenue)
- [ ] `GET /pricing/thread-catalog` → HTTP 200 list of `ThreadEntry` objects
- [ ] `pytest tests/billing-engine/test_markup.py` → all tests pass, ≥90% coverage
- [ ] `ruff check src/billing-engine/markup/ tests/billing-engine/test_markup.py` → clean

---

## C-089 Implementation Note

`validate_price(agent_type, bundle_tier, proposed_price_paise)` must write to `institutional.pricing_floor_log`
on every call — APPROVED **and** REJECTED — to maintain a complete audit trail per C-059.
The log row captures: `proposed_price_paise`, `cost_floor_paise`, `constitutional_minimum_margin_pct`,
`minimum_compliant_price_paise`, `outcome` (VARCHAR(10): `"APPROVED"` or `"REJECTED"`), `evaluated_by`.

The cost floor (`cost_floor_paise`) is **pre-stored** in `institutional.bundle_profiles.cost_floor_paise`.
Do NOT recompute it from thread catalog at runtime — read it from the DB.

The margin formula is **margin-on-revenue** (standard billing): `price = cost_floor / (1 - margin_pct / 100)`.
Example: cost_floor=1000, margin=20% → price = 1000 / 0.80 = 1250 paise (not 1000 × 1.20 = 1200).
`minimum_margin_pct` is read from `bundle_profiles.minimum_margin_pct` (NUMERIC(5,2), nullable, default 20.0).

---

## Notes

- Flat imports: `from markup.bundle_engine import BundleEngine` — conftest.py adds `src/billing-engine/` to sys.path.
- **⛔ THREAD CATALOG API (CRITICAL):** `thread_catalog.py` does **NOT** have a `ThreadCatalogService` class. It exposes standalone async module-level functions. Use them directly:
  ```python
  from markup.thread_catalog import list_threads, get_thread_entry, get_all_threads, invalidate_thread_cache
  ```
  Exported symbols: `ThreadCatalogEntry` (dataclass), `get_all_threads()`, `get_thread(thread_id)`, `list_threads()`, `get_thread_entry(thread_id)`, `invalidate_cache()`, `invalidate_thread_cache()`.
  Do NOT write `from markup.thread_catalog import ThreadCatalogService` — that symbol does not exist and will raise `ImportError`.
- `MarginViolation` exception should be an `HTTPException(status_code=422, detail={"code": "MARGIN_FLOOR_VIOLATION", "minimum_compliant_price_paise": <int>, "cost_floor_paise": <int>})`.
- Tests: use `pytest-asyncio` and `httpx.AsyncClient` (same pattern as `test_wallet.py`).
- Test fixtures must seed `bundle_profiles` rows for at least 2 agent_types × 2 bundle_tiers before running pricing assertions.
- `IMarkupEngine` in `src/billing-engine/skeleton/wbe_interfaces.py` is the authoritative interface — `BundleEngine` must implement it exactly.
- **GO validation:** This WC was reviewed by EA (GOA-WC027-01) and SA (GOA-WC027-02). See `goals/GOAL-WC027-markup-engine.md` for full institutional record.

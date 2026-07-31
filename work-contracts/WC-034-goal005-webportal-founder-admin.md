# Work Contract 034 — GOAL-005: Web Portal Founder Admin Pages

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-034
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — GOAL-005 Web Portal Sprint
**Sprint Track:** Track GOAL-005 — Customer Acquisition (Founder admin tooling)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-064 (Three-Human Institution — Founder tooling is constitutional infrastructure), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** ⚠️ BLOCKED — Founder FA required (same gate as WC-031)

**Depends on:** WC-016 (Web Portal scaffold live — Next.js app, auth, routing), WC-031 (WBE trial + promotions APIs live), WC-027 (markup API live)

---

## Sprint Goal

Implement three Founder-only admin pages in the Next.js web portal:
1. **Markup Designer** — live pricing calculator + per-thread markup editing
2. **Trial Budget Config** — set trial duration and free unit caps per agent type
3. **Coupon Manager** — create/expire coupons, view referral tree

All three pages require `founder=true` JWT claim. Unauthorised access → redirect to 403.

---

## Tasks

| Task | Scope | model_hint | Status |
|---|---|---|---|
| WC034-01 | Read the existing web portal structure (`web/` or `web/app/` — find auth guard pattern and admin route convention). Create `web/app/admin/markup-designer/page.tsx` — fetches `GET /pricing/thread-catalog` from WBE, renders editable table (thread_type, cost_floor_paise, markup_pct, derived_price_paise, margin_pct), on markup_pct change calls `POST /pricing/validate` (live margin gate — show MARGIN_FLOOR_VIOLATION inline), on save calls `PATCH /pricing/thread-catalog/{thread_id}` (new WBE endpoint — add to WC-027 DoD extension or implement stub here). Founder-only auth guard wraps entire page. | reasoning | 🔲 TODO |
| WC034-02 | Create `web/app/admin/trial-config/page.tsx` — fetches `GET /trial/config` (implement stub endpoint in WBE trial/router.py if not already there), renders form: trial_duration_days (default 14), free_unit_caps table (agent_type × thread_type = N units), on save calls `PUT /trial/config`. Create `web/app/admin/coupon-manager/page.tsx` — fetches `GET /promotions/coupons` list (add to WBE promotions/router.py), renders active/expired coupons with uses_count, create-coupon form (discount_pct, agent_type, max_uses, valid_until), deactivate button (calls `PATCH /promotions/coupons/{coupon_id}` with `{active: false}`), referral tree view for selected customer. | reasoning | 🔲 TODO |
| WC034-03 | Vitest tests for all 3 pages: markup designer renders thread catalog data, margin violation shown inline on bad markup_pct, trial config form submits correct payload, coupon create form validation (discount_pct 0-100), coupon deactivate calls PATCH endpoint, auth guard redirects non-founder users to /403. Mock all WBE API calls. ≥90% line coverage on new page files. | auto | 🔲 TODO |

---

## Required Inputs

| Input | File |
|---|---|
| GOAL-005 Spec §7 | `architecture/reference/billing/customer-acquisition-spec.md` §7 — UI design and API calls |
| Web Portal structure | Read `web/` directory — find: auth guard component, admin route pattern, API client setup |
| WBE markup API | `work-contracts/WC-027-wbe-s3-markup-engine.md` — `/pricing/` endpoints |
| WBE trial API | `work-contracts/WC-031-goal005-wbe-trial-promotions.md` — `/trial/config`, `/promotions/coupons` |
| ADR-017 | `adr/ADR-017-web-application-framework.md` — Next.js version, App Router conventions |

---

## Definition of Done

- [ ] `/admin/markup-designer` renders thread catalog table with live margin validation
- [ ] Non-founder JWT → redirected to `/403` (not `/admin/markup-designer`)
- [ ] `/admin/trial-config` form submits correct `PUT /trial/config` payload
- [ ] `/admin/coupon-manager` shows coupons list, create form, deactivate button
- [ ] All Vitest tests pass: `pnpm test web/app/admin/`
- [ ] `biome lint web/app/admin/` → clean (or equivalent linter per ADR-017)
- [ ] No WBE API credentials or secrets hardcoded in frontend — all via env var or server-side API route

---

## Notes

- The WBE `PATCH /pricing/thread-catalog/{thread_id}` endpoint may not exist yet — if WC-027 did not
  implement it, add it as a subtask in THIS sprint (scope it in WC034-01 as "add WBE endpoint if missing").
- `GET /trial/config` and `PUT /trial/config` may need to be added to WBE trial/router.py —
  check if WC-031 implemented them. If not, add as a subtask here.
- All three pages are server components with client-side interactivity where needed (Next.js App Router pattern).
- WBE base URL should come from env var `NEXT_PUBLIC_WBE_URL` (or server-side env `WBE_INTERNAL_URL`).

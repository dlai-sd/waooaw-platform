# Work Contract 033 — GOAL-005: BP Trial Lifecycle Endpoints + Temporal Expiry Saga

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-033
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — GOAL-005 BP Sprint
**Sprint Track:** Track GOAL-005 — Customer Acquisition (Business Platform integration)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-088 (subscription lifecycle — trial is a subscription mode), C-090 (trial→paid conversion must honour grandfather), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** ⚠️ BLOCKED — Founder FA required (same gate as WC-031)

**Depends on:** WC-031 (TrialService live in billing-engine), WC-032 (PSE tier override live)
**Depends on:** Existing BP subscription router and Temporal client (identify exact files before modifying)

---

## Sprint Goal

Add the trial lifecycle to the Business Platform:
1. `POST /subscriptions/trial-start` — BP endpoint that validates phone/identity, then calls WBE
   `POST /trial/start`. Returns trial details to the frontend.
2. Temporal workflow `trial_expiry.py` — saga that fires at `trial.expires_at`, sends WhatsApp
   reminder 48h before expiry, calls `POST /trial/convert` if payment completes before expiry,
   or marks trial as LAPSED + sends lapse notification.

---

## Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC033-01 | Read the existing BP subscription router (find `src/bp/subscriptions/router.py` or equivalent). Add endpoint: `POST /subscriptions/trial-start` — validates `{ customer_id, agent_type, phone_verified: bool }`, checks phone_verified=True (C-023 evidence gate), calls WBE `POST /trial/start` via internal httpx, returns `TrialStartResponse`. If WBE returns 409 TRIAL_ALREADY_USED: propagate as 409. Mount endpoint alongside existing subscription routes. | reasoning | pending | — |
| WC033-02 | Create `src/bp/subscriptions/workflows/trial_expiry.py` — Temporal workflow: `TrialExpiryWorkflow(trial_id, customer_id, expires_at)` — (1) sleep until `expires_at - 48h`, (2) send WhatsApp reminder via WBE WhatsAppNotifier stub, (3) sleep until `expires_at`, (4) check if trial status=CONVERTED (poll WBE `GET /trial/status`), (5) if not converted: call WBE `POST /trial/convert` with lapse mode OR mark LAPSED and send lapse notification. Register workflow in existing Temporal worker (`src/bp/worker.py` or equivalent). | reasoning | pending | — |
| WC033-03 | `tests/bp/test_trial_lifecycle.py` — test: `POST /subscriptions/trial-start` with phone_verified=True → 200 + TrialStartResponse, phone_verified=False → 422 PHONE_NOT_VERIFIED, WBE 409 propagated as 409; Temporal workflow unit tests (mock WBE calls): 48h reminder fires at correct time, conversion path marks CONVERTED, lapse path marks LAPSED — ≥90% line coverage on new files | auto | pending | — |

---

## Required Inputs

| Input | File |
|---|---|
| GOAL-005 Spec | `architecture/reference/billing/customer-acquisition-spec.md` §2.1 (Trial API) |
| Existing BP subscription router | Find by searching `src/bp/` — read before modifying |
| Existing Temporal worker | Find `src/bp/worker.py` or equivalent — register new workflow there |
| WBE trial endpoints | `work-contracts/WC-031-goal005-wbe-trial-promotions.md` — contracts to call |
| WBE httpx client pattern | Look at how existing BP services call other internal services |

---

## Definition of Done

- [ ] `POST /subscriptions/trial-start` with `phone_verified=True` → 200, WBE called, TrialStartResponse
- [ ] `POST /subscriptions/trial-start` with `phone_verified=False` → 422 `PHONE_NOT_VERIFIED`
- [ ] `TrialExpiryWorkflow` registered in Temporal worker without error
- [ ] Temporal workflow: 48h reminder activity fires, lapse path marks trial LAPSED
- [ ] `pytest tests/bp/test_trial_lifecycle.py` → all tests pass, ≥90% coverage
- [ ] `ruff check src/bp/subscriptions/router.py src/bp/subscriptions/workflows/trial_expiry.py` → clean

---

## Notes

- Identify BP service language before implementing (may be .NET or Python — check `ADR-016`).
  If .NET: adapt task scopes to C# patterns. WC task text assumes Python/FastAPI — adjust if needed.
- Do not create a new Temporal client — reuse the existing client from BP infrastructure.
- `phone_verified` evidence must be recorded via `ce.record_evidence()` stub (C-023 — evidence first).

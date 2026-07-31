# Work Contract 032 — GOAL-005: AIR PSE Trial Tier Override

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** WC-032
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5) — GOAL-005 AIR Sprint
**Sprint Track:** Track GOAL-005 — Customer Acquisition (AIR integration)
**Gate:** G5 → MVI
**Reviewer:** Autonomous Sprint Reviewer (INST-010 PR Review hat)
**Constitutional Basis:** C-049 (Honest Limitation — agent must behave within trial constraints), C-059 (Traceability), C-076 (≥90% coverage)
**Authorization:** ⚠️ BLOCKED — Founder FA required (same gate as WC-031)

**Depends on:** WC-031 (TrialService live — sets Redis `wbe:customer:{id}:mode=TRIAL`)
**Scope:** Additive only — do not restructure pse/router.py. Add trial mode check, nothing else.

---

## Sprint Goal

The PSE (Provider Selection Engine) in AIR currently routes LLM calls by customer tier.
When a customer is in TRIAL mode, every call must be forced to `LlmTier.LOCAL` (Ollama).
This is a small additive change — read the existing PSE router, find the tier lookup, insert the
Redis check. Add tests that prove trial customers get LOCAL regardless of their configured tier.

---

## Tasks

| task_id | scope | model_hint | status | completed_at |
|---|---|---|---|---|
| WC032-01 | Read `src/ai-runtime/pse/router.py` in full. Find the existing `select_provider()` (or equivalent) function. Inject: before returning the tier, do `customer_mode = await redis.get(f"wbe:customer:{customer_id}:mode")` — if `customer_mode == b"TRIAL"` return `LlmTier.LOCAL`. Inject Redis import if not already present (use existing Redis client dependency from `ai-runtime/dependencies.py` or equivalent — do not create a new client). No other changes to pse/router.py. | reasoning | pending | — |
| WC032-02 | Add tests to `tests/ai-runtime/test_pse_router.py` (create if not exists): CCT-TRIAL-02 integration test: customer with TRIAL mode in Redis → PSE returns LOCAL tier regardless of customer configured tier; customer without TRIAL mode → PSE returns configured tier (existing behaviour unchanged); Redis key TTL expiry → PSE falls back to configured tier. ≥90% line coverage on modified lines. | auto | pending | — |

---

## Required Inputs

| Input | File |
|---|---|
| GOAL-005 Spec §6 PSE Override | `architecture/reference/billing/customer-acquisition-spec.md` §6 — exact implementation pattern |
| AIR PSE router | `src/ai-runtime/pse/router.py` — read before modifying |
| AIR dependencies | `src/ai-runtime/dependencies.py` (or equivalent) — find Redis client |
| CCT-TRIAL-02 | `architecture/reference/billing/customer-acquisition-spec.md` §4 — implement this CCT |

---

## Definition of Done

- [ ] Customer with Redis key `wbe:customer:{id}:mode=TRIAL` → PSE returns `LlmTier.LOCAL`
- [ ] Customer without TRIAL key → existing tier selection unchanged
- [ ] CCT-TRIAL-02 test passes
- [ ] `pytest tests/ai-runtime/test_pse_router.py` → all tests pass
- [ ] `ruff check src/ai-runtime/pse/router.py` → clean (no new violations)
- [ ] Lines added: ≤15 (additive only — if more, raise a reviewer flag)

---

## Notes

- Do not modify `LlmTier` enum or any existing PSE logic outside the single injection point.
- The Redis key is set by `TrialService.start_trial()` in billing-engine — AIR reads it as a
  cross-service Redis read (shared Redis instance per docker-compose.yml).
- If Redis is unavailable: let the existing PSE error handling handle it — do not add new error paths.

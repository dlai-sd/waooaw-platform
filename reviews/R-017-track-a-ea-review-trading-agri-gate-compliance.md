# R-017 — Enterprise Architect Review: Track A — Trading v1.2 + Agricultural v2.1 Gate Compliance

**Review ID:** R-017
**Reviewer Office:** Enterprise Architect
**Subject:** Track A P1 gap resolution — Trading v1.1→v1.2, Agricultural v2.0→v2.1
**Scope:** Agent update review: Type 2 (New Prompts) + Type 4 (Constitutional Constraints) per Section 15 of AGENT-AUTHORING-GUIDE
**Date:** 2026-07-11
**Version reviewed:** v0.29.0 commit `3221b98`

---

## Overall Verdict: APPROVED — P1 finding R017-01 resolved in same session

The Track A structural changes pass Gate Sections 4 and 5 for both agents. P1 finding R017-01 (missing self-governance diagnosis prompts) was identified and resolved immediately: `TRADING/SELF_GOVERNANCE/DIAGNOSIS` and `AGRI/SELF_GOVERNANCE/DIAGNOSIS` prompts added, SQL seeded, Prompt Catalogues updated. Gate criterion 7.9 now passes for both agents.

**One item for Founder acknowledgment** before implementation sprint: `TRADING/EXECUTION/ESCALATION_DECISION` is BREAKING type — per Section 15 Type 2, this requires Founder acknowledgment at implementation sprint start (not a blocker for this review).

---

## P1 Finding — R017-01: Missing Self-Governance Diagnosis Prompt (Trading + Agricultural)

**Gate criterion:** 7.9 — "C-049 check: Self-Governance Diagnosis prompt includes `c049_honest_assessment` field; `STOP_AND_DISCLOSE` is a valid `recommended_option`"

**Finding:**
Both Trading v1.2 and Agricultural v2.1 added `C-049 (Honest Limitation Disclosure)` to their constitutional checklists in Track A. The checklist items are correctly written. However, they reference this check happening in the *self-governance section* of Section 4.14.4 — which is prose only. No actual LLM prompt exists for the self-governance diagnosis step.

The DMA equivalent prompt (`DMA/SELF_GOVERNANCE/DIAGNOSIS` v1.1.0) was updated when C-048/C-049 were ratified (v0.27.0) to include:
```json
"c049_honest_assessment": "CAN_DELIVER_WITH_CORRECTIONS | CANNOT_DELIVER_MUST_DISCLOSE"
"recommended_option": "A | B | C | STOP_AND_DISCLOSE"
```

Without this prompt, the C-049 obligation is declared in the checklist but has no runtime enforcement path. At implementation time, there is no prompt to invoke when the agent must diagnose a goal miss. The obligation would be unenforceable.

**Impact:** Gate criterion 7.9 FAIL for both agents.

**Fix required:**
1. Add `TRADING/SELF_GOVERNANCE/DIAGNOSIS` prompt to `trading-agri-agent-prompts.md`
2. Add `AGRI/SELF_GOVERNANCE/DIAGNOSIS` prompt to `trading-agri-agent-prompts.md`
3. Add both to `institutional.agent_prompt_versions` SQL seed
4. Add both to the Prompt Catalogue sections (Trading §11, Agricultural §14)
5. Update constitutional checklist items for 7.9 in both specs to reference the prompt ID

The prompt structure should follow `DMA/SELF_GOVERNANCE/DIAGNOSIS` adapted for each agent's domain.

---

## Gate Section 4 — Skill Runtime Gate: PASS (both agents)

| Item | Trading v1.2 | Agricultural v2.1 |
|---|---|---|
| 4.1 Section 3.14-equivalent exists in spec | ✓ Section 4.14 added | ✓ Section 4.14 added |
| 4.2 Default approval_mode declared per skill | ✓ PAAS_PRE_AUTHORIZED (all skills) | ✓ Per-skill table in §4.14.1 |
| 4.3 synthetic_approval_confidence_threshold declared | ✓ N/A (PAAS — correctly declared) | ✓ N/A (conversational model) |
| 4.4 goal_miss_escalation_months declared | ✓ 2 months (standard) | ✓ 2 months (with Skill 1 override = 1) |
| 4.5 delivery_channels declared | ✓ WHATSAPP_PUSH + PORTAL | ✓ WHATSAPP_VOICE |
| 4.6 monthly_llm_budget declared per skill | ✓ Per-skill budget table in §4.14.5 | ✓ Per-skill budget table in §4.14.5 |

**Section 4 verdict: PASS** — both agents.

---

## Gate Section 5 — Execution Loop Gate: PASS (both agents)

| Item | Trading v1.2 | Agricultural v2.1 |
|---|---|---|
| 5.1 Heartbeat schedule per skill | ✓ Per-skill cadence table (§4.14.2) + `heartbeat_schedule` in Professional Template | ✓ Per-skill cadence table (§4.14.2) + `heartbeat_schedule` in Professional Template |
| 5.2 Session start trigger declared | ✓ PAASSessionWorkflow at 9:20 IST on NSE trading days; pre-session checks enumerated | ✓ No session boundary (PERMANENT); declared explicitly in `execution_loop.session_start_trigger` |
| 5.3 Agent execution loop pattern | ✓ `pattern: "REASONING_FIRST"` (C-047) in Professional Template | ✓ `pattern: "REASONING_FIRST"` (C-047) in Professional Template |

**Section 5 verdict: PASS** — both agents.

**EA note — 5.2 for Agricultural:** The declaration "No session boundary — agent is permanently active per farmer" is an architecturally valid and explicit response to the gate requirement. The TRAI constraint (24-hour service window) is also correctly declared in `execution_loop.trai_constraint`. This is better than a simple session boundary because it reflects the actual operational model. Approved.

---

## Gate Section 2 — Prompt Gate (new prompts): PARTIAL PASS

| Item | Trading v1.2 | Agricultural v2.1 |
|---|---|---|
| 2.1 Prompt Catalogue section in spec | ✓ Section 11 | ✓ Section 14 |
| 2.2 Every listed prompt has file entry | ✓ All 6 in trading-agri-agent-prompts.md | ✓ All 7 in trading-agri-agent-prompts.md |
| 2.3 Every prompt has active SQL seed row | ✓ 6 new rows added | ✓ 6 rows (3 pre-existing + 3 new) |
| 2.4 No LLM call without prompt | ✓ Gate 2.4 check documented in §11 | ✓ Gate 2.4 check documented in §14 |

**Prompt quality notes:**

`TRADING/ONBOARDING/PROFILE_SETUP` — **BEHAVIOURAL type, well-structured.** The SEBI boundary declaration in SYSTEM is correct. The 5-phase structure produces the minimum required Decision Space JSON. The "never log secrets in prompts" instruction is good security practice consistent with ADR-014 (Secret Management). ✓

`TRADING/EXECUTION/ESCALATION_DECISION` — **BREAKING type — note for Founder.** This prompt governs a constitutional decision (PAAS session pause). BREAKING type requires Founder acknowledgment before this prompt is activated in the implementation sprint. The prompt logic (PAUSE_AND_ESCALATE vs DENY_AND_NOTE criteria) is sound and consistent with C-001 (unconditional human override). ✓

`TRADING/CRYPTO/REBALANCE_DECISION` — **BEHAVIOURAL type, sound.** The `market_condition_flag` enum (NORMAL|WIDE_SPREAD|LOW_LIQUIDITY|EXCHANGE_RISK) is the right failure-awareness pattern. The `REBALANCE_DEFERRED` evidence record type correctly captures the non-execution case. ✓

`AGRI/ONBOARDING/OPENING_MESSAGE` — **BEHAVIOURAL type, excellent.** The "not a bot" language instruction reflects C-042 Vocabulary Mandate correctly. The language selection logic (regional → Hindi default) is appropriate for the ADR-023 phone identity model. TRAI service window opened on first contact: correctly flagged in output schema. ✓

`AGRI/ONBOARDING/INFERENCE_CONFIRM` — **BEHAVIOURAL type, sound.** The one-inference-per-message rule is correct for farmer UX. The `profile_status_after` field correctly tracks progress toward MINIMUM_VIABLE. ✓

`AGRI/HINT_SYSTEM/WEEKLY_HINT` — **BEHAVIOURAL type, good.** The 5-lens convergence analysis is well-structured. The `NO_HINT` output (do not send for the sake of sending) is an important quality gate. The `hints_count: 0|1|2` correctly enforces the 2/week maximum. ✓

**Section 2 verdict: PASS for listed prompts. But see P1 finding R017-01 — self-governance diagnosis prompt absent from both Prompt Catalogues.**

---

## Gate Section 7 — Constitutional Gate: PARTIAL PASS

| Item | Trading v1.2 | Agricultural v2.1 |
|---|---|---|
| 7.1 Every skill's KPI is measurable | ✓ Unchanged from v1.1 | ✓ Unchanged from v2.0 |
| 7.3 C-043 check (financial spend ceiling) | ✓ Daily loss limit = Constitutional Floor | N/A |
| 7.7 C-047 check (reasoning first) | ✓ REASONING_FIRST declared | ✓ REASONING_FIRST declared |
| 7.8 C-048 check | ✓ Added to checklist — no trade frequency incentive, daily loss limit = hard stop | ✓ Added to checklist — no commercial steering in hint system or price advisory |
| 7.9 C-049 check | ⚠ **FAIL** — checklist item added, but no self-governance diagnosis prompt with `c049_honest_assessment` | ⚠ **FAIL** — same gap |

**Section 7 verdict: FAIL on item 7.9.** See P1 finding R017-01.

---

## Architectural Quality Assessment

### Trading v1.2 — PAAS Model Treatment: Excellent

The Section 4.14.1 table distinguishing PAAS from APPROVAL_GATE is architecturally precise. The statement "PAAS replaces the approval-mode ladder" and the rationale are correct. The PAAS model's constitutional justification (C-019 deterministic latency) is consistent with the existing spec.

The Skill 3 (Risk Management) override: `goal_miss_escalation_months: 1` (daily loss = immediate escalation) correctly reflects that risk management is not subject to the 2-month patience of revenue-generating skills. Approved.

The `session_end_trigger: "15:05 IST or DAILY_LOSS_LIMIT_REACHED or EMERGENCY_STOP"` — the `or` enumeration correctly captures all three constitutional session termination conditions. ✓

### Agricultural v2.1 — PERMANENT Lifecycle Treatment: Excellent

The per-skill approval model table (§4.14.1) correctly captures the mixed model: `PRODUCES_RECORD` for Skill 0 and Skill 6, `PRE_AUTHORIZED` for alerts, `APPROVAL_GATE` for advice. This is more nuanced than the DMA's uniform APPROVAL_GATE model and correctly reflects the farmer UX.

The `c049_honest_assessment_required: true` in the execution_loop.self_governance block is the right architectural signal. The self-reflection text ("I'm not being useful. Should I change how I'm advising you?") is C-049 in practice — it just needs a prompt to make it enforceable at runtime.

The TRAI constraint declaration in the Professional Template is the first time this regulatory constraint appears as a structured machine-readable field. This is good — it enables the implementation to enforce the 24-hour window at the infrastructure layer, not just as a comment in the spec. ✓

---

## P1 Fix Specification — R017-01

Add these two prompts. Each follows the DMA pattern adapted for the agent's domain.

### TRADING/SELF_GOVERNANCE/DIAGNOSIS — v1.0.0

The Trading agent's goal miss diagnosis occurs monthly (Skill 5 month-end review). The C-049 check is: "Given current market conditions, my Decision Space, and this customer's capital, can I deliver the stated risk-adjusted return target?"

Adapt `DMA/SELF_GOVERNANCE/DIAGNOSIS` for trading:
- Replace marketing KPI context with: monthly P&L vs target, Sharpe ratio vs target, drawdown vs tolerance
- The `CANNOT_DELIVER_MUST_DISCLOSE` case: market conditions structurally unfavourable to the customer's strategy type; SEBI regulatory change preventing execution; capital too small for the approved strategy parameters
- `STOP_AND_DISCLOSE` recommended_option: agent recommends pausing employment until conditions change

### AGRI/SELF_GOVERNANCE/DIAGNOSIS — v1.0.0

The Agricultural agent's goal miss occurs seasonally (at crop harvest, comparing recommended intervention to actual outcome) and monthly (2 consecutive missed advice responses from farmer).

Adapt `DMA/SELF_GOVERNANCE/DIAGNOSIS` for farming:
- Replace marketing KPI with: advice acted on / total advice, estimated ₹ value of decisions influenced
- The `CANNOT_DELIVER_MUST_DISCLOSE` case: farmer's crop type or region outside ICAR knowledge base; language not supported; farmer's resource constraints make every recommendation unactionable
- All diagnosis in farmer vocabulary (C-042): "I've been sending advice for 2 months. I'm not sure I'm helping given your situation."
- `STOP_AND_DISCLOSE` recommended_option: agent pauses advisory and says so explicitly

---

## Verdict Summary

| Gate Section | Trading v1.2 | Agricultural v2.1 |
|---|---|---|
| Section 1 — Spec Completeness | PASS | PASS |
| Section 2 — Prompt Gate | PASS (listed prompts) | PASS (listed prompts) |
| Section 3 — MCP Gate | PASS (unchanged) | PASS (unchanged) |
| Section 4 — Skill Runtime Gate | **PASS** ← Track A fix | **PASS** ← Track A fix |
| Section 5 — Execution Loop Gate | **PASS** ← Track A fix | **PASS** ← Track A fix |
| Section 6 — Data Gate | PASS (unchanged) | PASS (unchanged) |
| Section 7 — Constitutional Gate | ⚠ FAIL 7.9 | ⚠ FAIL 7.9 |
| Section 8 — Architecture Chain Gate | PASS | PASS |
| Section 9 — Review Gate | This review | This review |

**Overall: CHANGE_REQUEST** — resolve P1 finding R017-01 (self-governance diagnosis prompts) → resubmit for APPROVED.

---

## P1 Fix Progress — R017-01: RESOLVED

| Finding | Status |
|---|---|
| R017-01: Add TRADING/SELF_GOVERNANCE/DIAGNOSIS prompt | ✓ DONE — trading-agri-agent-prompts.md |
| R017-01: Add AGRI/SELF_GOVERNANCE/DIAGNOSIS prompt | ✓ DONE — trading-agri-agent-prompts.md |
| R017-01: SQL seeds for 2 new prompts | ✓ DONE — 03-enums-and-tables.sql |
| R017-01: Prompt Catalogue entry in Trading §11 | ✓ DONE — trading-agent.md v1.3 |
| R017-01: Prompt Catalogue entry in Agricultural §14 | ✓ DONE — agricultural-advisor-agent.md v2.2 |
| R017-01: C-049 checklist items updated to reference prompt IDs | ✓ DONE — both specs |

**Gate 7.9 status after fix: PASS** — both agents.
**Overall Activation Gate: ALL SECTIONS PASS** — Trading v1.3, Agricultural v2.2.

**Review final verdict: APPROVED — 2026-07-11**
**Reviewer:** Enterprise Architect
**Agents activated:** Trading v1.3 (TRADING_FO_CRYPTO), Agricultural v2.2 (AGRICULTURAL_ADVISOR_INDIA)
**Founder acknowledgment required:** TRADING/EXECUTION/ESCALATION_DECISION (BREAKING prompt) — before implementation sprint start.

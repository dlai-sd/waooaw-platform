# Constitutional DNA Inheritance — Simulation Walkthrough

**Date:** 2026-07-19
**Purpose:** Verify all 7 agents inherit the 3 constitutional instincts correctly. Identify gaps.
**Authority:** C-070 (Constitutional DNA Inheritance Obligation)
**Grade scale:** A = all instincts fully satisfied | B = minor gap, not blocking | C = significant gap, must fix | FAIL = constitutional violation

---

## Walkthrough Method

For each agent, I trace a representative interaction through all 3 instincts:
1. Does the agent follow the constitution at every step?
2. Does it produce improvement signals?
3. Does it operate autonomously with trust-building evidence?

Gaps found are catalogued and bridged in `architecture/reference/agents/CONSTITUTIONAL_DNA_GAPS.md`.

---

## Agent 1: WoW Expert Digital Marketing Agent (DMA v2.9)

**Scenario:** Dr. Mehta's DMA agent (Skill 3) creates an Instagram Reel and publishes it.

### Instinct 1 — Follow Constitution

| Step | Constitutional Gate | Status | Gap? |
|---|---|---|---|
| Agent starts skill 3 session | Temporal PAASSessionWorkflow starts; Decision Space loaded | ✓ | — |
| Agent generates Reel content | LLM inference → C-051 UsageBudget evaluator | ✓ | — |
| Agent calls instagram-mcp `post.reels.create` | CE.ValidateAction → C-041 (instagram in authorized_actions?) | ✓ via C-041 | **GAP-DMA-01**: Skill 3 spec doesn't list CE.ValidateAction call sequence explicitly |
| Reel published | CE.RecordEvidence before publish returns success | ✓ C-023 | **GAP-DMA-02**: No Evidence First sequence described per skill in DMA spec |
| If content violates healthcare guidelines | Should DENY at C-041 or C-062 evaluator | **FAIL** | **GAP-DMA-03**: C-062 prompt injection evaluator covers adversarial input but no evaluator for domain-specific prohibited content (medical claim prohibition) |

**Instinct 1 Grade: B** — C-023/C-041 present in constitutional basis; CE.ValidateAction assumed but not per-skill documented; healthcare content constraint gap.

### Instinct 2 — Improve Itself

| Step | Improvement Signal | Status | Gap? |
|---|---|---|---|
| Reel published → 0 engagement in 7 days | Agent detects via Signal Intelligence Layer (C-053) | **Partial** | **GAP-DMA-04**: DMA spec doesn't define when low engagement triggers C-049 escalation |
| Agent files C-049: "Instagram reach strategy not delivering" | Escalation record in audit_records | **MISSING** | **GAP-DMA-05**: DMA spec has no C-049 trigger conditions per skill |
| Self-Improvement Analyst reads pattern | Detects after 3 similar signals | ✓ (C-069 infrastructure) | — |
| Sujay receives proposal | Via Steward Assistant | ✓ | — |

**Instinct 2 Grade: C** — No C-049 trigger conditions per skill; quality signal not defined per skill.

### Instinct 3 — Autonomous and Trust-Based

| Step | Trust/Autonomy | Status | Gap? |
|---|---|---|---|
| After 30 sessions, 0 violations | Trust score ~0.95 | ✓ (trust_ledger infrastructure) | — |
| Agent earns Tier 0 for content within approved calendar | Pre-authorized class | **MISSING** | **GAP-DMA-06**: DMA spec doesn't define which skill classes qualify for Tier 0 trust escalation |
| C-048 violation → immediate reset | — | ✓ (trust_ledger formula) | — |

**Instinct 3 Grade: B** — Trust infrastructure exists; Tier 0 progression not defined in spec.

**DMA Overall Grade: B** — Functional but missing per-skill constitutional detail.

---

## Agent 2: WoW Expert Trading Advisor (Trading v1.7)

**Scenario:** Rahul's trading agent (PAAS) detects a NIFTY signal, executes a trade, then market regime changes and the strategy stops working.

### Instinct 1 — Follow Constitution

| Step | Constitutional Gate | Status | Gap? |
|---|---|---|---|
| NIFTY signal detected (Skill 1) | Analysis only — no CE.ValidateAction needed | ✓ | — |
| Trade proposal generated (Skill 2) | CE.ValidateAction: C-043 daily loss limit check | ✓ (C-043 in basis) | — |
| Order placed via zerodha-mcp | CE.ValidateAction: C-041 tool authorization | ✓ | — |
| VIX spikes unexpectedly | Agent should PAUSE, not proceed | **GAP** | **GAP-TRADE-01**: No constitutional trigger for "market regime change → pause and disclose" |
| Emergency Stop | ≤250ms via Temporal signal | ✓ ADR-018 | — |

**Instinct 1 Grade: A** — Strongest constitutional basis of all customer agents. C-043 financial ceiling, C-041, ADR-018 all present. VIX pause gap is behavioral (Skill spec) not constitutional.

### Instinct 2 — Improve Itself

| Step | Improvement Signal | Status | Gap? |
|---|---|---|---|
| 3 consecutive losing trades | Performance signal detected | **MISSING** | **GAP-TRADE-02**: No SKILL_QUALITY_SIGNAL specification for trading skills |
| Agent should file C-049: "Strategy underperforming — regime change" | Honest limitation | **MISSING** | **GAP-TRADE-03**: C-049 trigger conditions not defined per trading skill |
| Self-Improvement Analyst reads signal | Would detect after threshold | ✓ (infrastructure) | — |

**Instinct 2 Grade: C** — No quality signals, no C-049 triggers defined per skill.

### Instinct 3 — Autonomous and Trust-Based

| Step | Trust/Autonomy | Status | Gap? |
|---|---|---|---|
| Session evidence recorded | Yes — PAAS session has rich audit trail | ✓ | — |
| Trust score computed | Sessions completed, C-043 violations, escalations | ✓ | — |
| After 30 sessions → Tier 0 within customer Decision Space | Pre-authorized PAAS | **PARTIAL** | **GAP-TRADE-04**: Trading spec doesn't define trust-based autonomy progression — it already uses PRE_AUTHORIZED but doesn't describe how trust gates evolve |

**Trading Overall Grade: B** — Constitutional enforcement strongest; improvement loop weakest.

---

## Agent 3: WoW Expert Agricultural Advisor (Agricultural v2.7)

**Scenario:** Suresh asks for pesticide timing advice. Agent gives advice. Advice turns out to be wrong (unexpected rain).

### Instinct 1 — Follow Constitution

| Step | Constitutional Gate | Status | Gap? |
|---|---|---|---|
| Advisory generated (no MCP tool) | Pure LLM inference + RAG | **GAP** | **GAP-AGRI-01**: Advisory skills with no MCP tool: does Evidence First apply? **YES — C-023 says "any customer-visible output".** But the spec doesn't describe Evidence First for advisory-only skills |
| Advisory sent via WhatsApp | Message delivery via WABA MCP | CE.ValidateAction: C-041 ✓ | — |
| Adverse weather event | IMD weather MCP called proactively | CE.ValidateAction ✓ | — |
| C-042 Vocabulary Mandate | Regional language output | ✓ (C-042 in basis) | — |
| Emergency Stop | WhatsApp channel → Temporal signal | **GAP** | **GAP-AGRI-02**: WhatsApp-native users have no portal — Emergency Stop via WhatsApp keyword must be specified explicitly |

**Instinct 1 Grade: B** — Evidence First for advisory (no MCP) not stated; WhatsApp Emergency Stop path ambiguous.

### Instinct 2 — Improve Itself

| Step | Improvement Signal | Status | Gap? |
|---|---|---|---|
| Advice given → outcome unknown until next message | Advisory quality unverifiable immediately | **GAP** | **GAP-AGRI-03**: Agricultural agent has no outcome-feedback loop. DMA can check engagement; Trading can check P&L. Agricultural: farmer must report back. Signal collection protocol not defined. |
| Farmer reports "rain damaged crop" | Should trigger C-049 quality signal | **MISSING** | **GAP-AGRI-04**: No C-049 trigger for "advice gave incorrect outcome" |
| Self-Improvement Analyst | Would catch cluster | ✓ (infrastructure) | — |

**Instinct 2 Grade: C** — No outcome feedback collection; no C-049 triggers per skill.

### Instinct 3 — Autonomous and Trust-Based

| Step | Trust/Autonomy | Status | Gap? |
|---|---|---|---|
| Suresh trusts agent after 6 months | Trust score builds naturally | ✓ | — |
| Agent earns right to give seasonal plan without confirmation | Tier 0 for advisory | **MISSING** | **GAP-AGRI-05**: Agricultural spec doesn't define which advice categories can become pre-authorized for trusted farmers |
| Language/dialect autonomy | Agent learns Suresh's preferred vocabulary | **PARTIAL** | Tone rules exist (3.0) but no trust-based vocabulary expansion model |

**Agricultural Overall Grade: C** — Rich domain spec; constitutional instinct gaps throughout.

---

## Agent 4: WoW Expert Private Tutor (v1.0)

**Scenario:** Priya's child (Class 8 Maths) has a lesson. Agent detects the child is struggling with geometry. Agent modifies lesson plan. Parent receives progress report via WhatsApp.

### Instinct 1 — Follow Constitution

| Step | Constitutional Gate | Status | Gap? |
|---|---|---|---|
| Lesson begins | Temporal workflow; C-060 (no camera on student) ✓ | ✓ | — |
| Agent modifies lesson plan | Internal decision — no MCP tool | CE.RecordEvidence for plan change? | **GAP-TUTOR-01**: Lesson plan modifications are customer-impacting decisions — should they go through CE? Spec unclear. |
| Whiteboard content generated | LLM inference → C-051 usage ✓ | ✓ | — |
| Progress report to parent (WhatsApp) | CE.ValidateAction: WhatsApp MCP | ✓ | — |
| C-060 compliance | No billing info to student view ✓ | ✓ | — |
| Emergency Stop | Parent can stop session immediately | **GAP-TUTOR-02**: Emergency Stop for a tutor session — is it lesson-stop or account-suspend? Not defined. |

**Instinct 1 Grade: B** — C-060 strongly compliant; Evidence First for internal decisions ambiguous.

### Instinct 2 — Improve Itself

| Step | Improvement Signal | Status | Gap? |
|---|---|---|---|
| Student gets question wrong 3 times | Quality signal: topic difficulty detected | **MISSING** | **GAP-TUTOR-03**: No SKILL_QUALITY_SIGNAL per learning skill defined |
| Agent should adapt — also file quality signal | Skill improvement needed | **MISSING** | **GAP-TUTOR-04**: No C-049 triggers defined for tutoring skills (e.g., "I cannot explain this concept effectively to this student") |
| Self-Improvement Analyst loop | Would work with signals | ✓ (infrastructure) | — |

**Instinct 2 Grade: C** — No quality signals; no C-049 triggers.

### Instinct 3 — Trust-Based

| Step | Trust/Autonomy | Status | Gap? |
|---|---|---|---|
| After 30 lessons, parent trusts the tutor | Trust score builds | ✓ | — |
| Trust progression for parent | Parent stops reviewing every lesson | **MISSING** | **GAP-TUTOR-05**: No trust-tier model for tutor-parent relationship |
| Student satisfaction | No signal collection defined | **MISSING** | **GAP-TUTOR-06**: Student signals (engagement, comprehension) not mapped to trust signals |

**Private Tutor Overall Grade: C** — Strong on C-060; weak on improvement and trust models.

---

## Agent 5: WAOOAW AI Agent — Platform IT Expert (v1.0)

**Scenario:** Developer implements CE ValidateAction evaluators (IB-NEW-1). Opens PR. Requests EA review.

### Instinct 1 — Follow Constitution

| Step | Constitutional Gate | Status | Gap? |
|---|---|---|---|
| Reads IB item | No CE involvement (read only) | ✓ | — |
| Creates branch, writes code | C-059 conventional commit ✓ | ✓ | — |
| Attempts to modify CONSTITUTION.md | Prohibited → Constitutional Blocker raised | ✓ | — |
| Opens PR | C-065 SDLC Separation — cannot self-merge | ✓ | — |
| CI gate fails | Stops — does not bypass CI | ✓ | — |

**Instinct 1 Grade: A** — Strongest spec. All prohibitions documented. Constitutional Blocker triggers listed.

### Instinct 2 — Improve Itself

| Step | Improvement Signal | Status | Gap? |
|---|---|---|---|
| PR rejected (code quality) | Learning signal | **MISSING** | **GAP-PLAT-01**: Platform IT Expert has no quality signal mechanism — unlike customer agents, its "sessions" are GitHub PRs. PR review outcomes should feed a quality signal. |
| Re-implementation after rejection | Knowledge retention | **MISSING** | **GAP-PLAT-02**: No mechanism for agent to learn from past PR review comments (R-NNN review files) systematically |

**Instinct 2 Grade: C** — The Platform IT Expert improves the platform but has no self-improvement loop for its own work quality.

### Instinct 3 — Trust-Based

| Step | Status | Gap? |
|---|---|---|
| Trust for internal agents is C-066 tier model | Different from customer trust ledger | **PARTIAL** | **GAP-PLAT-03**: Internal agents don't contribute to trust_ledger (correct — no customer). But they have no equivalent trust mechanism for expanding autonomy on the platform itself. |

**Platform IT Expert Overall Grade: B** — Excellent constitutional compliance; improvement loop missing.

---

## Agent 6: WAOOAW AI Agent — Self-Improvement Analyst (v1.0)

**Scenario:** Analyst detects DMA Skill 3 has 4 C-049 escalations in 7 days. Raises proposal. Sujay rejects with label `sia:false-positive`.

### Instinct 1 — Follow Constitution

| Step | Status | Gap? |
|---|---|---|
| Reads audit_records | Read-only ✓ | — |
| Creates GitHub Issue | CE.ValidateAction not applicable (no external tool via MCP) | **MINOR GAP-SIA-01**: SIA calls GitHub API directly — should this go through a CE validation? Likely not (GitHub API is platform-internal for this agent) but should be documented |
| Writes improvement_proposals | INSERT only, no UPDATE | ✓ | — |

**Instinct 1 Grade: A** — Well-spec'd. Minor documentation gap on GitHub API vs MCP boundary.

### Instinct 2 — Improve Itself (meta: the analyst improving itself)

| Step | Status | Gap? |
|---|---|---|
| Sujay applies `sia:false-positive` | Feedback loop defined in spec Section 6 ✓ | ✓ | — |
| Analyst reduces sensitivity for this pattern | Defined ✓ | ✓ | — |
| No mechanism to log its own improvement proposal quality | **MISSING** | **GAP-SIA-02**: The Self-Improvement Analyst itself produces no quality signal about its OWN proposals (false positive rate, acceptance rate) |

**Instinct 2 Grade: B** — Feedback loop from Sujay defined; self-quality signal missing.

### Instinct 3 — Trust

| Status | Gap? |
|---|---|
| No customer trust ledger (internal agent) | ✓ | — |
| Trust with Sujay: if acceptance rate is high, Sujay trusts proposals more | **MISSING** | **GAP-SIA-03**: No trust-based autonomy model for the analyst (e.g., after 90% acceptance rate, Sujay auto-approves certain proposal types) |

**Self-Improvement Analyst Overall Grade: B** — New spec, well-thought-out; meta-improvement gaps expected in v1.0.

---

## Agent 7: WAOOAW AI Agent — Steward Assistant (v1.0 — from steward-interface.md)

**Scenario:** Sujay asks "Is the platform safe to take a new customer today?" Agent queries CCT status, cost, blockers, and responds.

### Instinct 1 — Follow Constitution

| Step | Status | Gap? |
|---|---|---|
| Reads platform state | Read-only ✓ | — |
| Creates GitHub Issue on behalf of Sujay | GitHub API — C-059 commit gate applies ✓ | — |
| Files Constitutional Blocker | Blocker file + Issue + PR change request ✓ | — |
| Cannot impersonate customer (C-068) | Enforced at Keycloak layer ✓ | — |

**Instinct 1 Grade: A** — Strong spec. C-068 cryptographic separation enforced.

### Instinct 2 — Improve Itself

| Step | Status | Gap? |
|---|---|---|
| Steward satisfaction signals | No mechanism defined | **GAP-STEWARD-01**: No quality signal for Steward Assistant interactions. If Sujay says "that answer was wrong," there's no structured feedback path. |
| Steward Assistant prompt versioning | Covered by agent_prompts table ✓ | ✓ | — |

**Instinct 2 Grade: B** — Covered by infrastructure; interaction quality signal missing.

### Instinct 3 — Trust

| Step | Status | Gap? |
|---|---|---|
| Steward trust is implicit (3 named humans) | No need for earned trust model | ✓ | — |
| FRONTIER LLM always | Best reasoning always available ✓ | ✓ | — |

**Steward Assistant Overall Grade: A** — Strongest new agent spec.

---

## Simulation Summary

| Agent | Instinct 1 | Instinct 2 | Instinct 3 | Overall | Priority Gaps |
|---|---|---|---|---|---|
| DMA v2.9 | B | C | B | **B** | GAP-DMA-01 to 06 |
| Trading v1.7 | A | C | B | **B** | GAP-TRADE-01 to 04 |
| Agricultural v2.7 | B | C | C | **C** | GAP-AGRI-01 to 05 |
| Private Tutor v1.0 | B | C | C | **C** | GAP-TUTOR-01 to 06 |
| Platform IT Expert v1.0 | A | C | B | **B** | GAP-PLAT-01 to 03 |
| Self-Improvement Analyst v1.0 | A | B | B | **A-** | GAP-SIA-01 to 03 |
| Steward Assistant v1.0 | A | B | A | **A** | GAP-STEWARD-01 |

**Systemic finding:** Instinct 2 (Improve Itself) is the weakest across all agents. No existing spec defines per-skill C-049 trigger conditions or SKILL_QUALITY_SIGNAL types. This is a universal gap bridged by the Constitutional DNA additions below.

---

## Gap Bridge Plan

All gaps are addressed by one of:
1. **Constitutional DNA Amendment** (new section added to each spec header) — universal gaps
2. **Per-skill C-049 and quality signal addendum** added to each spec
3. **New CCTs** for verifiable gaps

See bridged agent spec amendments in CONSTITUTIONAL_DNA_GAPS.md.

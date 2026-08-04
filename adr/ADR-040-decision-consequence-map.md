# ADR-040 — Decision Consequence Map (DCM) Architecture

**Status:** Accepted  
**Date:** 2026-08-04  
**Authority:** C-099 (Decision Consequence Map — RATIFIED 2026-08-04)  
**Deciders:** Yogesh Khandge (Founder), Platform IT Expert  
**Supersedes:** Partial — extends ADR-039 §3 (UDCP), extends ADR-031 §2 (CE Fail-Safe)

---

## Context

WAOOAW agents make two fundamentally different kinds of decisions:

1. **Irreversible / consequential** — charging a customer, executing a trade, committing to a contract, advancing constitutional state. A wrong or inconsistent output from an LLM cannot be corrected by a subsequent run. The cost of error is permanent.

2. **Reversible / advisory** — generating content, drafting code, producing analysis, proposing improvements. A wrong output is caught by the verification loop (customer approval, PR review, CCT gate, monthly effectiveness review) and corrected without harm.

Before C-099/ADR-040, WAOOAW treated all decisions with the same verification depth. Every agent decision went through `CE.ValidateAction` (correct) but CE had no way to distinguish whether a ALLOW response meant "proceed and self-certify" or "proceed and independently verify before committing." This created two failure modes:

- **Under-trust**: Agents required human approval for advisory outputs → bottleneck, poor UX
- **Over-trust**: Agents self-certified irreversible outputs without independent verification → financial risk

The Decision Consequence Map resolves this by making the **consequence of error** — not the complexity of the decision — the routing criterion.

---

## Decision

Every WAOOAW agent must declare a **Decision Consequence Map (DCM)** in its specification (Section 3.25). The DCM classifies every consequential decision type into exactly one category:

```
DETERMINISTIC_REQUIRED  — wrong output causes irreversible harm
                          → CE returns PROCEED_DETERMINISTIC
                          → agent must invoke independent_verification_method before committing
                          → CCT-DCM-03 audits compliance post-execution

CONSISTENT_SUFFICIENT   — wrong output is caught by verification loop
                          → CE returns PROCEED_AUTONOMOUS
                          → agent may act and self-certify output
```

### CE.ValidateAction Extension

`ValidateActionRequest` is extended with `optional DcmCategory dcm_category = 10`.  
`ValidateActionResponse` is extended with `DcmOutcome dcm_outcome = 6`.

```protobuf
enum DcmCategory {
  DCM_CATEGORY_UNSPECIFIED            = 0;
  DCM_CATEGORY_DETERMINISTIC_REQUIRED = 1;
  DCM_CATEGORY_CONSISTENT_SUFFICIENT  = 2;
}

enum DcmOutcome {
  DCM_OUTCOME_UNSPECIFIED   = 0;
  DCM_PROCEED_AUTONOMOUS    = 1;
  DCM_PROCEED_DETERMINISTIC = 2;
  DCM_BLOCKED               = 3;
}
```

CE routing logic (to be implemented in `DcmEvaluator.cs`):

| dcm_category | ValidateAction decision | dcm_outcome |
|---|---|---|
| DETERMINISTIC_REQUIRED | ALLOW | PROCEED_DETERMINISTIC |
| CONSISTENT_SUFFICIENT | ALLOW | PROCEED_AUTONOMOUS |
| UNSPECIFIED (not declared) | DENY | DCM_BLOCKED |
| Any | DENY (other claim) | DCM_OUTCOME_UNSPECIFIED |

### DCM as C-070 Recursive Loop Filter

The DCM is the **calibration instrument** for C-070 Instinct 2 (improve itself):

| Decision type | Improvement path |
|---|---|
| DETERMINISTIC_REQUIRED | Founder authorization required before agent DNA is updated |
| CONSISTENT_SUFFICIENT | Self-Improvement Analyst may apply autonomously |

This makes the self-improvement loop safe at scale: correct friction where harm is permanent, correct speed where it is not.

### Enforcement Layers

**Authoring time** — Activation Gate Section 16 (5 checks). Agent spec without DCM = GATE BLOCKED.  
**CI gate** — CCT-DCM-01 (presence) + CCT-DCM-02 (completeness). Blocks PR merge.  
**Runtime** — CE DcmEvaluator consults DCM category on every ValidateAction call.  
**Audit** — CCT-DCM-03b: audit_records must contain verification_record_id for every DETERMINISTIC_REQUIRED action committed.

---

## Alternatives Considered

### A — Keep CE.ValidateAction as-is, rely on agent judgment

Rejected. Agent judgment about "how much verification is enough" is exactly the failure mode that produced UDCP's semantically-correct-but-wrong code generation. Verification depth must be structural, not advisory.

### B — Add human approval gate for all consequential actions

Rejected. Uniform human gate destroys the value of Instinct 3 (autonomous execution). It is also the approach taken by every competitor platform — and it is a bottleneck. WAOOAW's differentiation is that it earns the right to be autonomous by being constitutionally structured, not by requiring human sign-off on everything.

### C — Extend Decision Space (existing per-skill authorization)

Rejected. Decision Space answers: "is the agent authorized to do this?" DCM answers: "for each thing it does, what verification depth is required before committing?" These are orthogonal questions. Decision Space is about authorization scope. DCM is about commitment trust. Both are necessary. Neither replaces the other.

---

## Consequences

### Positive

- **Autonomy without drift**: agents execute `CONSISTENT_SUFFICIENT` decisions at full speed without human gates; `DETERMINISTIC_REQUIRED` decisions get independent verification without slowing advisory actions
- **C-070 loop is safe at scale**: Self-Improvement Analyst can apply prompt improvements to `CONSISTENT_SUFFICIENT` decisions autonomously; `DETERMINISTIC_REQUIRED` decisions still require Founder authorization
- **CCT-DCM-03 is a permanent audit guard**: any agent that commits an irreversible action without verification is detectable at the database level
- **Competitive differentiation**: no existing agent platform (Devin, Copilot Agent, Claude Code, OpenHands) separates decision consequence from decision complexity; WAOOAW is the first to make this structural

### Negative / Trade-offs

- **DcmEvaluator.cs must be implemented** in the CE before runtime enforcement is live (currently the field is structural — CE does not yet return DCM_BLOCKED for unspecified categories)
- **DB migration required**: `constitutional.audit_records` needs `dcm_category` + `verification_record_id` columns for CCT-DCM-03b to be unblocked
- **All 8 agent specs uplifted** (done 2026-08-04) — any new agent spec authored before the DCM standard existed must be retroactively uplifted

---

## Implementation Status

| Layer | Status |
|---|---|
| C-099 ratified | ✅ 2026-08-04 |
| AGENT-AUTHORING-GUIDE v5.0 (§9k + Gate §16) | ✅ 2026-08-04 |
| CONSTITUTIONAL_DNA v2.0 (§1.2a runtime pattern) | ✅ 2026-08-04 |
| All 8 agent specs uplifted (Section 3.25) | ✅ 2026-08-04 |
| CE proto: DcmCategory + DcmOutcome enums | ✅ 2026-08-04 |
| CCT-DCM-01 (spec presence) | ✅ 2026-08-04 — 60 PASS |
| CCT-DCM-02 (verification completeness) | ✅ 2026-08-04 — 60 PASS |
| CCT-DCM-03a (proto contract) | ✅ 2026-08-04 — 60 PASS |
| DcmEvaluator.cs (CE runtime) | ⬜ Pending implementation authorization |
| DB migration (audit_records DCM columns) | ⬜ Pending DcmEvaluator |
| CCT-DCM-03b (runtime audit integrity) | ⬜ Pending DcmEvaluator (skip marker in test) |

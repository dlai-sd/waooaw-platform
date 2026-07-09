## Summary

<!-- One sentence: what does this PR implement? -->


## IB Reference

<!-- Link the GitHub Issue this PR closes -->
Closes #

**IB Item:** IB-NNN  
**Work Contract:** WC-NNN  
**Office:** Runtime Professional / Enterprise Architect / ...  
**Sprint:** N  

---

## Constitutional Basis

<!-- Which constitutional claims, ADRs, or design principles does this implement? -->
| Reference | Type | What it requires |
|---|---|---|
| C-NNN | Claim | |
| ADR-NNN | Decision | |
| DP-NNN | Principle | |

---

## What Was Implemented

<!-- Brief list of what was built. Tie each item to the component spec. -->
- [ ] `src/service-name/Feature` — implements [component-spec section]
- [ ] `tests/constitutional/CCT-XX-NN` — proves [constitutional principle]

---

## Constitutional Compliance Test Coverage

<!-- List CCTs covered by this PR. All CCTs must pass in CI before merge. -->

| CCT ID | Principle | Status |
|---|---|---|
| CCT-EF-01 | Evidence First | ✅ Passing |
| CCT-XX-NN | Principle name | ✅ Passing / ❌ Not yet / N/A |

---

## Test Evidence

<!-- Paste CI test run summary or link to the Actions run -->

```
Unit tests:       PASS (NN/NN)
Integration:      PASS (NN/NN)
CCTs:             PASS (NN/NN)
Coverage:         NN% (threshold: NN%)
```

---

## Specification Compliance

<!-- Confirm implementation matches the approved architecture -->
- [ ] Every class/function traces to an approved component specification
- [ ] No unapproved dependencies introduced (check pyproject.toml / .csproj / package.json)
- [ ] No business logic invented beyond what the specification states
- [ ] Structured logging only — no console.log / print / Console.WriteLine
- [ ] OTel spans emitted for constitutional events (where applicable)
- [ ] `conventional commit` format used on all commits

---

## Reviewer Instructions

> **Constitutional review:** `@copilot review this PR as the [Reviewer Office per ORGANIZATION.md]`
>
> **Reviewer checklist:**
> - Does every change trace to an approved architecture specification?
> - Are all constitutional principles correctly implemented (not just mentioned)?
> - Do the CCTs prove the principle is architecturally enforced?
> - Are there any Decision Space violations (code outside the Work Contract scope)?

---

## Intermediate Commit Record

<!-- List significant milestones committed during this PR (per BOOTSTRAP checkpointing rule) -->
1. `feat(service): skeleton with /health endpoint`
2. `constitutional(ce): Evidence First enforcer implementation`
3. `cct(ce): CCT-EF-01 and CCT-EF-02 passing`

---

## Agent Lifecycle Gate (required for PRs that create or update any agent spec)

> Skip this section entirely if this PR does NOT touch any file in `architecture/reference/agents/`.
> If it DOES touch an agent spec, every row below must be completed.

**Change type:** NEW_AGENT | NEW_SKILL | NEW_PROMPT | NEW_MCP | NEW_CONSTRAINT | PERSONA_EXTENSION | VERSION_BUMP

**Agent affected:** [agent-name].md vX.X

| Gate Section | Status | Notes |
|---|---|---|
| 1 — Spec Completeness | ✅ PASS / ❌ FAIL | |
| 2 — Prompt Gate (C-045) | ✅ PASS / ❌ FAIL | All prompts in Prompt Library + seeded in SQL? |
| 3 — MCP Gate (C-041) | ✅ PASS / ❌ FAIL | All MCP servers in containers.md + catalogue + docker-compose? |
| 4 — Skill Runtime Gate (DP-014) | ✅ PASS / ❌ FAIL | Runtime config standard applied to all skills? |
| 5 — Execution Loop Gate (C-047) | ✅ PASS / ❌ FAIL | Heartbeat/session trigger declared? |
| 6 — Data Gate (AD-004) | ✅ PASS / ❌ FAIL | RLS + GRANT for every new table? |
| 7 — Constitutional Gate | ✅ PASS / ❌ FAIL | C-042/043/044/045/046/047 checks done? |
| 8 — Architecture Chain Gate | ✅ PASS / ❌ FAIL | All 16 layers in Section 11.1 verified? |
| 9 — Review Gate | ✅ PASS / ❌ FAIL | EA APPROVED + Founder approved? |

**Overall gate result:** ✅ ALL PASS — agent may be activated | ❌ BLOCKED — resolve failures first

> An EA reviewer who issues APPROVED without a completed gate table has violated GENESIS Part 05.

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

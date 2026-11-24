## Summary

Adds Work Contract WC-167: the read-only RCA of the missing Founder administrative menu and the Connections refusal on Demo, the five objectives left before the first acceptance run, and the UI styling and testing bar every changed page must meet. No source or infrastructure change.


## Required Traceability

**Work Contract:** WC-167
**Constitutional Basis:** C-023, C-049, C-063, C-065, C-080 | ADR-054 | ADR-055 | ADR-046


## IB Reference

Closes none (no GitHub Issue; Founder instruction in the 2026-11-24 conversation: "let me know rca of these points. Create new work contract with high level objectives as 5 items we need to do").

**IB Item:** IB-167
**Office:** Platform IT Expert (INST-010)
**Sprint:** N/A

---

## Constitutional Basis

| Reference | Type | What it requires |
|---|---|---|
| C-023 | Claim | Evidence First: every cause states what is confirmed and what is not yet proven |
| C-049 | Claim | The contract states what is not proven and what stays out of scope |
| C-063 | Claim | No secret was read or printed while gathering the evidence |
| C-065 | Claim | No code is written until the Founder authorizes each slice |
| ADR-046 | Decision | The pricing owner is wired through the governed workload path; no shared token carries actor or role |

---

## What Was Implemented

- [x] `work-contracts/WC-167-acceptance-demo-readiness.md`: five objectives (Founder admin access, coupon, Meta registration and Connections, acceptance enablement, sandbox completion and first calibration run), the RCA with evidence from Demo, scope, stop conditions and slice order
- [x] RCA-1 (no Founder menu): the server found no match for the signed-in identity against the one configured Founder; the reason is settled by the `/access` screen
- [x] RCA-2 (Connections): the membership check on customer routes refuses before the controller runs; the browser flattens every 401 and 403 into "not permitted to manage this connection"
- [x] RCA-3 (coupons): the Demo workload has no pricing-owner credential or Billing Engine address, so the coupons screen would return 503 (CB-021)
- [x] WC167-R006: every changed page follows the visual system and the UI acceptance layers (component tests, responsive and theme Playwright runs, axe, lint, build, 90 percent coverage, screenshots)
- [x] WC167-R007 to R009 and the additional findings the Founder added to scope ("add them"): AF-1 the production Meta secret decision, AF-2 database command log volume on Demo, AF-3 the standing DEAD_LETTER_AGE_BREACH PAGE alert (blocked outbound message since 2026-11-22)
- [x] Review of merged PR #618 (WC-149) against this contract (RV-1 to RV-5): Connections is offered to everyone but needs a customer membership; the classic Meta login dialog on Graph v21.0 is unproven for the Pages-use-case app; `/admin/providers` redirects instead of denying; partial UI test coverage; the "test users" assumption no longer holds
- [x] `work-contracts/WC-167-requirements.yaml` (9 requirements) and generated state refreshed

No `src/`, `web/` or Terraform file changed, and nothing was applied to Azure.

---

## Constitutional Compliance Test Coverage

| CCT ID | Principle | Status |
|---|---|---|
| None added | No new constitutional compliance test; the ledger carries the evidence | N/A |

---

## Test Evidence

All commands ran in Docker. The evidence for the RCA came from read-only reads of Demo (Log Analytics and the Container App settings); nothing was changed.

```
Requirement ledger WC-167:                      PASS (9 requirements)
Platform state refresh (derive/sync/verify):    PASS
Commit hook prechecks (gitleaks included):      PASS
```

Not run: the pull-request hosted gates (they run in CI); any code or infrastructure test, because none changed.

Open items for the Founder: the `/access` screen result (closes RCA-1) and whether a customer who completed a trial sees the same Connections error (closes RCA-2).

---

## Release Qualification Control

**Release Qualification:** ON
**Release Qualification Authority:** N/A

---

## Candidate Evidence Status

<!-- Generated from exact-candidate evidence; this block is authoritative over narrative summaries. -->

```json
{
  "candidate_sha": "a9b71df8ac4826d0d5506028144f9553ddfeff48",
  "hosted_pilot": "PENDING",
  "prechecks": "PASS",
  "qualification": "PENDING",
  "schema": "waooaw.candidate-evidence-status/v1"
}
```

## Author Review

<!-- Generated after final push by scripts/prepare_pr_body.py. -->
- [x] Reviewed the complete diff against the authorized scope
- [x] Reviewed test and quality-gate results
- [x] Reviewed security, constitutional, and rollback impact
- [x] Resolved every finding or recorded no findings

**Reviewed Commit:** a9b71df8ac4826d0d5506028144f9553ddfeff48
**Author Review Result:** PASS

## Specification Compliance

- [x] Every artifact traces to ADR-054, ADR-055 and the accepted architecture package
- [x] No unapproved dependencies introduced (no package manifest changed)
- [x] No business logic invented; the contract describes behavior read from the code and from Demo
- [x] Structured logging only
- [x] `conventional commit` format used on all commits

---

## Spec-Code Traceability Matrix (C-059)

Not applicable: this PR contains zero `src/` file changes.

---

## Founder Review

Author review and automated gates provide evidence, not approval. The Founder may review, return, request an institutional review, approve, or merge. The author must not invoke another institution, approve, or merge this PR.

---

## Intermediate Commit Record

1. `docs(wc): acceptance Demo readiness contract with RCA of the Founder menu and Connections (WC-167)`
2. `docs(wc): add the three additional findings and the PR 618 review to WC-167`


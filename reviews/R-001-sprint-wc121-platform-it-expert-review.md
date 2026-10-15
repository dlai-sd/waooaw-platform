# R-001 WC-121 Platform IT Expert Review

## Review Control

| Field | Value |
|---|---|
| Pull request | #513 |
| Office | Platform IT Expert |
| Substantive reviewed head | `a08224c91e7f197b7afc3d9dce1ce647fc9c7872` |
| Stacked base | `main` after #512 squash merge |
| Review result | CHANGES REQUIRED |

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| PIT-513-01 | BLOCKER | Code Quality, CI, validation-plan, and qualification did not run because both primary workflows accept pull requests only when the base is `main`; the stacked base is not protected by those checks. GitHub's `CLEAN` merge state therefore did not represent validation readiness. | PR marked draft. After #512 merges, retarget #513 to `main` and require successful exact-head hosted checks before Founder review or merge. |
| PIT-513-02 | HIGH | Gitleaks was eligible for identical-tree reuse even though it scans `BASE_SHA..HEAD_SHA`, contradicting WC-121's requirement that secret detection execute for every candidate. | Resolved in `a08224c91e7f197b7afc3d9dce1ce647fc9c7872` by setting the gate `reusable: false` and adding a regression assertion. |

## Evidence

- Focused precheck, reuse, and validation-policy tests: 102 passed; one unchanged baseline test deselected.
- Ruff lint and targeted format checks: passed.
- Remediation commit prechecks: passed.
- C-059 commit validation: passed.
- Pull request state after review: draft.
- Hosted Code Quality and CI evidence: absent; this remains the blocking condition.

## Required Closeout

1. Merge #512 through Founder authority.
2. Retarget #513 from `ib/123/auth-disclosure-repair` to `main`.
3. Confirm the PR diff remains the intended WC-121 efficiency range.
4. Run and pass Code Quality, CI, validation-plan, and applicable qualification checks on the exact head.
5. Refresh the exact-head PR body and return the PR to ready only after all evidence is present.

This review is evidence for Founder decision-making. It is not approval or merge authority.

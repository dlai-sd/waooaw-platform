# WC-095 Repository-Local Completion Evidence

Qualified source head: `09c6ad90c3f4629ec67f003f752e46302c810304`

Branch: `ib/095/employment-lifecycle-completion`

Qualification date: 2026-09-17

## Claim Boundary

This evidence qualifies the independently executable repository-local implementation delivered at
the implementation commit above. It does not claim WC-095 contract completion, provider-backed
Razorpay acceptance, exact DMA image compatibility,
deployment, Production readiness, customer traffic, PR approval or merge.

`WC095-05B` and `SIM-095-23` are `BLOCKED_EXTERNAL_INPUT`: merchant credentials and authority to use
them in Razorpay test mode were not supplied. `WC095-07` cannot be promoted because no governed
repository source supplies the exact specification, prompt and input/output schema digests for the
admitted runtime binding. These coordinates were not inferred or inserted as fixtures.

## Delivered Behavior

- BP resolves and persists immutable, relationship/participant/Skill-bound operational mandates only
  when current admission, contract, Decision Space, goal, context and exact runtime binding inputs exist.
- BP and PR reject missing, stale, stopped, mismatched or divergent mandate requests before domain work.
- BP uses short-lived workload assertions to call PR; the customer bearer is not forwarded.
- WBE binds capture and reconciliation to the exact checkout, tenant, relationship, contract,
  acceptance and consent tuple. Browser callbacks carry no payment truth.
- The Portal launches official Razorpay Checkout from server-created order data; dismissal is not
  reported as failure, and callback handling performs bodyless owner reconciliation.
- Seven review dimensions are stored separately in an append-only, forced-RLS review ledger and
  projected separately in the Portal. Customer responses are append-only, exact-versioned,
  actor-bound and idempotent. CE commits privacy-minimized evidence before persistence; exact replay
  does not call CE again, and CE failure leaves no response.
- Material review recommendations create customer alerts. Reassessment/dispute/pause decisions keep
  Operations locked, and command receipts reconcile independently of optional configuration state.
- The Portal exposes exact-version review decisions and separates delivery quality from external
  business outcome and attribution limits. Desktop, 360px, 200-percent-text, keyboard, Axe, Stop,
  relationship-switching, payable-pending and zero-price browser states are exercised.
- The Portal trial journey exercises Marketplace trial terms, explicit Trial intent, no-paid-tool
  disclosure, consent gating and an intent-preserving registration handoff. The Hire journey
  exercises exact contract acceptance, payable fail-closed handling and fully discounted activation.
- Operations and lifecycle projections consume the same non-mutating mandate readiness result.

## Docker Qualification

| Boundary | Command/check | Result |
|---|---|---|
| Business Platform | Exact CI restore, warning-as-error build, full assembly and coverage gate | PASS - 792/792; 91.49% line, 80.01% branch (4499/5623) |
| BP review and payment precheck repair | Focused service filters | PASS - review 24/24; payment 32/32 |
| BP trial and Hire workflow | Trial ownership, admission/controller, contract acceptance, payment, authenticated activation, evaluation, expiry and conversion filters | PASS - 77/77 |
| Mandate replay repair | Resolver and conversation focused filter | PASS - 24/24 |
| BP PostgreSQL | Migration 33 and 37 Testcontainers filter | PASS - 2/2 |
| Professional Runtime and OpenAPI | `tests/test_openapi_slice.py` plus PR conversation execution | PASS - 80/80 |
| Billing Engine trial and Hire workflow | Trial, payment, relationship workspace and paid-activation files | PASS - 80/80; 3 PostgreSQL cases delegated |
| WBE PostgreSQL | `scripts/test-wc059-postgres.sh` | PASS - 3/3 |
| WBE promotion and workload identity | Demo discount lifecycle and authenticated internal activation | PASS - 31/31 |
| Portal trial and Hire components | Relationship workspace and professional comparison Jest suites | PASS - 14/14 |
| TypeScript and Web unit precheck | Exact CI type check, zero-warning lint, Jest and global coverage gate | PASS - 62/62 suites, 375/375 tests; 90.48% statements, 80.28% branches, 90.14% functions, 93.62% lines |
| Browser acceptance | WC-095 Playwright desktop and 360px matrix | PASS - 11; 19 intentional project skips |
| Browser Hire workflow | Exact contract, payable fail-closed and zero-price journeys at desktop and 360px | PASS - 6/6 |
| Browser Trial workflow | Marketplace, governed limits, Trial disclosure, consent and registration continuation | PASS - 1/1 |
| Python static analysis | Ruff over every touched Python file | PASS |
| SQL static analysis | SQLFluff over migrations 21c, 33, 36 and 37 | PASS |
| Generated client | Canonical regeneration and before/after tree SHA-256 | PASS - byte-identical |
| Portal lint/build | Next lint and production build | PASS; warning-free |
| Patch integrity | `git diff --check` and generated/credential author review | PASS |

All tests and tooling executed through repository Docker runners or repository Docker orchestration.
No Python virtual environment was created or used.

## Author Review

Author review found and repaired a mandate replay defect: the first implementation returned a stored
mandate before checking actor, Skill and operational-purpose binding. Divergent replay now returns the
existing conversation idempotency conflict while exact retry replay remains stable. SQLFluff findings
in the touched migrations were mechanically repaired and the real-PostgreSQL checks rerun.

The completion audit additionally repaired locally minted review-response evidence and actor-agnostic
idempotency replay. Unresolved contract gaps are recorded in `scope-audit.md`. In particular, PR
cancellation remains fail-closed rather than implemented, migration 36 lacks a dedicated
real-PostgreSQL adversarial test, and provider/runtime-coordinate acceptance remains blocked.

The PR precheck repair corrected a stale Web assertion so the caller's validated idempotency key is
verified end to end. Report-guided tests exercise review and payment validation, reconciliation and
owner-identity branches without lowering either constitutional coverage threshold. The Test Champion
failure was downstream-only; C-065 is refreshed from the final pushed head after this evidence commit.
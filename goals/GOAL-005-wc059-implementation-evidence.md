# GOAL-005 WC-059 Implementation Evidence

**Work Contract:** WC-059 · **Office:** INST-010 Platform IT Expert
**Authorization:** FA-040 · GEP-08 · R-080 · ACK-08 · GOA-05 · ACC-05

## Scope

This record covers WC059-01 through WC059-08: immutable contract composition and acceptance,
contract-ordered hosted payment, BP-owned durable activation, WBE paid-subscription projection,
and customer web/WhatsApp presentation. It does not claim live Razorpay or provider activation,
WC-060 continuity, deployment, production/customer proof, merge, or self-review.

## Constitutional Compliance Matrix

| CCT | Evidence class | Executable proof | Result |
|---|---|---|---|
| `CCT-AE01-CONTRACT-01` | Component | Exact version/hash, fresh portal assurance, active same-tenant employer, replay, mismatched hash/role with zero mutation | PASS |
| `CCT-AE01-SCOPE-01` | Component | Fixed scope-boundary statement is distinct and required; omission performs zero acceptance mutation | PASS |
| `CCT-AE01-PAY-ORDER` | Component | Missing acceptance, missing proceed intent, stale assurance, mismatched amount, and bypass all stop before WBE | PASS |
| `CCT-AE01-ACT-01` | Temporal + mTLS + PostgreSQL 16 integration | Running callers join one real Temporal execution; the .NET gateway crosses a real mutually authenticated TLS listener twice and receives one stored WBE subscription; competing PostgreSQL transactions commit one subscription and one activation identity | PASS |
| `CCT-AE01-ACT-CONFLICT` | Component + PostgreSQL 16 integration | BP durable preflight rejects changed material before Temporal join; WBE component checks reject changed tenant/version/body/context; competing PostgreSQL intents leave the winning identity and one subscription | PASS |
| `CCT-AE01-ACT-FAIL` | Temporal + PostgreSQL 16 integration | Five real Temporal activity failures close one run as `FAILED_RETRYABLE`; failed-only ID reuse completes the same durable intent exactly once; response-loss replay returns PostgreSQL's stored subscription | PASS |
| `CCT-AE01-DARK-01` | Browser fixture | Jest and Playwright prove exact terms, no preselection/countdown/pressure, and symmetric Hire, Not now, Cancel, Exit at desktop and 360px | PASS |

## Validation Evidence

| Slice | Result |
|---|---|
| PostgreSQL migrations and owner mutation | PASS — `scripts/test-wc059-postgres.sh` applies 21b and applies/reapplies 21c on a fresh PostgreSQL 16 container; 2/2 integration cases prove competing-intent serialization, exact UUID/timestamp driver bindings, one subscription, and response-loss replay |
| Business Platform | PASS — 244/244 in the repository Docker test-runner; two activation tests execute the Temporal time-skipping server for running join and failed-only restart; one cross-stack test executes `AuthenticatedActivationBillingGateway` against the Python WBE private listener over real TLS |
| Billing Engine | PASS — 389/389 component tests plus the separately executed PostgreSQL 2/2; the component matrix covers route/audience/body/replay/context/tenant/version denial with zero mutation, while the cross-stack BP test supplies real mTLS transport proof and missing-client-certificate denial |
| ADR-046 PKI and private listeners | PASS — 15/15 bootstrap checks plus private-listener 1/1; generated TLS artifacts contain leaf/intermediate chains, listeners trust the root/intermediate CA bundle, and BP validates the custom-root chain plus exact URI SAN; affected Python lint clean |
| Business Platform affected coverage | PASS — core WC059 methods 93.33–100% lines except durable conflict/replay branches covered separately by PostgreSQL concurrency evidence; activation orchestration entry is 100% |
| Web component | PASS — 4/4 focused relationship journey tests; `ContractJourney` 100% lines, 97.22% statements, 93.75% branches, 91.66% functions |
| Web production build | PASS — strict TypeScript, lint, 23 generated routes |
| Browser acceptance | PASS — 4/4 Chromium expanded and compact 360; no serious/critical axe violations or horizontal overflow |
| OpenAPI | Paid activation command and truthful conflict/unresolved responses are specified; full generator validation reaches the new operation and retains only one pre-existing missing `#/components/responses/Forbidden` reference |
| Diff hygiene | Protected `.coverage` and `logs/blueprint_assurance_report.json` remain unstaged; no generated `bin`, `obj`, `.next`, provider credential, or deployment artifact is committed |
| Platform state check | Informational mismatch — canonical registry still names the prior completed baseline, so `SPRINT-REGISTRY.md` and this in-progress `PROJECT_STATE.md` checkpoint intentionally differ until reviewed completion; no automatic rewrite performed |

No row above is deployment or production/customer evidence. SQLite component tests are retained for
fast logic coverage but are not cited as PostgreSQL, Temporal, or network transport proof.

## Ownership And Failure Evidence

- BP alone owns D-03 relationship progression and records `ACTIVATION_PENDING` before WBE.
- WBE accepts paid activation only on the ADR-046 private mTLS/delegated-context route, rebinds tenant/version/material to its signature-verified captured-payment row, and owns one payment-keyed paid subscription; `CONVERTED` is billing projection only.
- CE evidence must commit before BP stores `ACTIVE`; uncertainty never fabricates success.
- Stable Temporal workflow identity is the distributed serialization boundary. Same-worker tuple
  serialization is defense in depth; migration uniqueness remains the durable canonical arbiter.
- WhatsApp cannot accept a contract or initiate payment and makes no WC-060 continuity claim.
- Payment secrets are entered only in Razorpay-hosted checkout; no live credential was configured.

R-081 findings R081-01 through R081-03 are remediated in implementation and executable evidence; closure remains pending independent INST-004 re-review.

## Residual Limits And Review Handoff

The full canonical BP OpenAPI validator remains blocked only by the inherited missing `Forbidden`
response component, which is outside WC-059. Browser evidence uses deterministic fixtures and is not
deployment or customer proof. Independent INST-004 Enterprise Architect and INST-002 Constitutional
Analyst review must verify architecture ownership, exactly-once ordering, ethical conversion, evidence
first behavior, tenant/participant isolation, and preservation of all exclusions. INST-010 does not
self-review or merge this contribution.
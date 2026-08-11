# Work Contract 059 — AE-01 Contract, Payment, and Exactly-Once Activation

**Goal:** GOAL-005 · **Epic stories:** AE-01-S07 and S08
**Office on execution:** Platform IT Expert (INST-010)
**Reviewer:** Enterprise Architect (INST-004) + Constitutional Analyst (INST-002)
**Status:** IN PROGRESS — IMPLEMENTATION AUTHORIZED AND ACCEPTED
**Authorization:** FA-040; GEP-GOAL-005-INST-013-08; R-080; ACK-GOAL-005-INST-001-08; GOA-GOAL-005-INST-010-05; ACC-GOAL-005-INST-010-05
**Track:** VERTICAL CUSTOMER OUTCOME
**Service scope:** BP (.NET), WBE (Python), CE (.NET), web, PR channel presentation

## Sprint Goal

Compose and explicitly accept one versioned Employment Contract, obtain one activation-eligible onboarding payment through completed WBE payment capability, and activate the durable Employment Relationship exactly once under the D-03 four-part tuple.

## Dependencies

WC-058 DONE; WC-042 and WC-043 DONE; accepted AEEC Foundation and D-03 model. Customer-initiated conversion only; no card/payment method is required at trial entry.

## Tasks

| Task | Scope | Model hint | Status |
|---|---|---|---|
| WC059-01 | Apply the exact Migration 21 blueprint in the D-06 Data Contract as `21b-ae01-contract-activation.sql` because `21-conversation-core.sql` already owns deployment sequence 21: immutable contract/acceptance records and one activation-intent row per canonical tuple, with material request hash, stored outcome, RLS, and replay semantics. Identical replay returns the prior result; divergent material records conflict without mutation. | reasoning | done |
| WC059-02 | Implement BP `EmploymentContractService`: compose common AEEC plus DMA schedule from accepted S06 configuration; present plain-language rights, obligations, price/tax, ad-spend treatment, limitations, cancellation, review, authority, and Stop terms; amendments create new versions. | reasoning | done |
| WC059-03 | Implement the canonical contract proposal/acceptance endpoints. Acceptance is Tier-4 web only and requires fresh Keycloak authentication, active same-tenant `EMPLOYER` role, exact version/hash, separate scope confirmation, and committed evidence. Conversation, default checkbox, silence, deep-link possession, MPIN, or trial consent cannot accept. | reasoning | done |
| WC059-04 | Integrate WC-042 onboarding order/webhook APIs and the D-06 Security Contract payment-consent flow. Present contract-linked itemized INR/GST/subscription/refund consequences, record explicit proceed intent, redirect to Razorpay-hosted checkout, verify webhook signatures, and expose dispute/refund evidence. Never collect payment secrets in WAOOAW UI or chat. | reasoning | pending |
| WC059-05 | Implement `ActivationOrchestrationService` and durable Temporal workflow exactly as ordered in the D-06 Solution Contract: load/lock intent, validate contract/payment/authority, enter `ACTIVATION_PENDING`, activate WBE idempotently, commit evidence, then transition relationship once to `ACTIVE`. | reasoning | pending |
| WC059-06 | Repair partial-failure ordering so WBE billing `CONVERTED` is emitted only as the projection of successful paid activation, never as a D-03 relationship state. Uncertainty stays on the same retryable activation intent; retries reuse correlation and return stored outcome without a second charge or relationship. | reasoning | pending |
| WC059-07 | Build web and WhatsApp contract summary/link, explicit acceptance, payment status, retry-safe activation result, cancellation/not-now path, and honest paid-capability differences. No countdown, confirm-shaming, preselection, or repeated solicitation. | reasoning | pending |
| WC059-08 | Add CCTs for version/hash acceptance, unauthorized participant, scope confirmation, payment ordering, webhook replay, concurrent activation, conflicting tuple, WBE/CE failure, and exactly-one charge/relationship/active transition. | auto | pending |

## Required Inputs

AEEC-01 through AEEC-15 · D-03 identity/state model · D-04 continuity contract · D-05 amended trial policy · `architecture/reference/product/ae01-business-boundary-contract.md` · `architecture/reference/product/ae01-solution-contract.md` · `architecture/reference/product/ae01-relationship-data-contract.md` · `architecture/reference/product/ae01-security-contract.md` · WC-042 payment API and CCTs · WC-043 reconciliation evidence · ADR-022 · ADR-023 · ADR-044.

## Constitutional Compliance Tests

| CCT | Assertion |
|---|---|
| CCT-AE01-CONTRACT-01 | Only exact presented version/hash accepted by authorized same-tenant participant becomes accepted |
| CCT-AE01-SCOPE-01 | Scope-boundary confirmation is distinct from ordinary approval |
| CCT-AE01-PAY-ORDER | Payment/order/activation cannot precede explicit accepted contract |
| CCT-AE01-ACT-01 | Concurrent and replayed canonical tuple produces one relationship activation and one charge |
| CCT-AE01-ACT-CONFLICT | Same intent with different material content is explicit conflict with zero mutation |
| CCT-AE01-ACT-FAIL | CE/WBE/evidence uncertainty remains pre-active and safely retryable |
| CCT-AE01-DARK-01 | Hire, not-now, cancellation, and exit have symmetric visibility and no dark-pattern behavior |

## Definition of Done

- Customer can inspect, export, and explicitly accept the exact governing contract.
- One valid payment activates one relationship exactly once; replay returns the original outcome.
- No partial failure can leave WBE `CONVERTED` while the relationship is not durably active without an explicit recoverable unresolved record.
- Customer-initiated conversion and ethical-conversion controls are executable and tested.
- BP/WBE/CE/web/integration suites, billing reconciliation, manifests/OpenAPI, and state synchronization pass.

## Validation Commands

```bash
docker compose --profile test run --rm test-runner dotnet test tests/business-platform.Tests/ tests/constitutional-engine.Tests/
docker compose --profile test-python run --rm test-runner-python pytest tests/billing-engine/ -v
docker compose --profile test run --rm test-runner npm --prefix web test
docker compose --profile test run --rm test-runner npm --prefix web run build
```

## Boundaries

No campaign execution, live Razorpay/provider credential activation, provider account setup, renewal redesign, WC-060, deployment, production/customer proof, self-review, or merge. FA-040 satisfies the current-session consent gate but no implementation starts before the GEP-08 CA/ACK/GOA/ACC chain is complete.
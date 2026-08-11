# R-081 - WC-059 Implementation Enterprise Architecture Review

| Field | Value |
|---|---|
| Reviewer office | INST-004 Enterprise Architect |
| Work Contract | WC-059 - AE-01 Contract, Payment, and Exactly-Once Activation |
| Reviewed range | `1d9876595921607997bcadca53e13048030d4e5f..6d4fce5aa327b2b1ceefc48ee4e9b0df9d5b5fd6` |
| Review date | 2026-08-11 |
| Decision | **CHANGES REQUESTED** |

## Verdict

WC-059 preserves the intended high-level ownership and activation order in its core orchestration service: BP owns the D-03 relationship state, WBE owns payment and subscription truth, `CONVERTED` remains a WBE billing projection, and BP records `ACTIVATION_PENDING` before WBE activation and constitutional evidence before `ACTIVE`.

The contribution is not approvable because the production activation command added at `6d4fce5` bypasses the accepted BP-to-WBE workload-authentication architecture and its Temporal join strategy prevents the contractually required retry and conflict semantics after a workflow execution already exists. The direct service tests pass but do not exercise either production boundary.

## Findings

### R081-01 - CRITICAL - Paid activation bypasses the authenticated BP-to-WBE owner boundary

**Evidence**

- `src/billing-engine/payment/router.py:170-178` exposes `POST /payments/paid-activation` with no workload-authentication dependency, peer-certificate check, delegated-context verification, route grant, audience binding, body digest, replay protection, or target-owned relationship rebinding.
- `src/business-platform/Services/ActivationOrchestrationService.cs:337-353` calls that route through the generic `WBE` client.
- `src/business-platform/Program.cs:94-103` configures plain HTTP and only adds an optional shared `X-Ops-Token`; the paid-activation route does not validate that header.
- `docker-compose.yml:462-468` maps WBE port 8140 to the host, so network location is not even an isolated-container boundary.
- The repository already implements the controlling pattern in `src/business-platform/Services/RelationshipWorkspaceOwnerGateway.cs:48-148` and `src/billing-engine/relationship_workspace.py:187-254`: mTLS workload identity, signed delegated context, exact audience/route/operation binding, and target-side rebinding.

**Impact**

Any caller that can reach WBE and obtain or guess the payment and contract material can invoke a consequential commercial mutation without proving it is BP or that it is authorized for the exact route and relationship. The endpoint can create a paid subscription and project a trial as `CONVERTED`. An optional shared operations token on the caller is neither enforced by WBE nor constitutionally sufficient workload identity.

**Required correction**

Move paid activation into the accepted ADR-046 private owner-command surface. Require exact BP mTLS identity and a signed delegated-context envelope bound to the WBE audience, HTTP method, route, operation, body digest, tenant, relationship, purpose, contract version, activation intent, correlation, and idempotency identity. WBE must rebind the relationship/payment material to its own stored truth and fail closed. Add positive and negative transport, route, audience, replay, confused-deputy, cross-tenant, and body-rebinding tests. Plain HTTP or shared-token fallback is not acceptable.

**Constitutional and architectural basis**

ADR-046 sections 2, 3.2, 3.3, and 10; C-003, C-005, C-006, C-008, C-023, C-026, C-032; AD-004, AD-009; DP-006, DP-007; AE-01 Solution Contract component ownership and failure contract.

### R081-02 - HIGH - Stable Temporal workflow reuse defeats retryable failure and material-conflict semantics

**Evidence**

- `src/business-platform/Workflows/ActivationWorkflow.cs:10-27` gives the activity five attempts and derives a workflow ID only from tenant, relationship, accepted contract, and payment reference.
- `src/business-platform/Services/ActivationWorkflowDispatchService.cs:24-38` catches every `WorkflowAlreadyStartedException` and attaches to the existing workflow result. It does not distinguish a running execution, a completed success, or a completed failure, and it does not configure a failed-only workflow ID reuse policy or continue the failed workflow.
- `src/business-platform/Services/ActivationWorkflowDispatchService.cs:88-98` deliberately derives the same workflow ID when other material changes.
- `tests/business-platform.Tests/ActivationOrchestrationServiceTests.cs:72-123` proves conflict and retry only by calling `ActivationOrchestrationService` directly. `CanonicalTupleHasStableTemporalWorkflowIdentity` and the dispatch tests do not run a Temporal execution through failure, replay, or divergent material.

**Impact**

After WBE or CE uncertainty exhausts the five activity attempts, the workflow closes failed while the activation intent remains `FAILED_RETRYABLE`. A later customer retry receives the same failed workflow result and cannot resume the same intent, contradicting D-03 and D-06. Separately, a divergent command for an existing canonical tuple joins the prior execution before `ActivationOrchestrationService.HashMaterial` can compare the new material, so the API can return the prior success or failure instead of the required explicit conflict with zero mutation.

**Required correction**

Define Temporal lifecycle semantics that preserve one canonical activation intent while allowing owner uncertainty to resume after a closed failure. Before joining an existing workflow, reconcile the persisted activation intent and material hash. Join only a running identical execution or return a stored identical success; reject divergent material before returning an existing result. A failed execution must be restartable or continuable under an explicitly safe Temporal reuse policy without creating a second intent, charge, subscription, or relationship transition. Add Temporal integration tests for running replay, completed success replay, completed owner/evidence failure followed by retry, and divergent material against running and completed executions.

**Constitutional and architectural basis**

C-002, C-023, C-032, C-084, C-085; D-03 Exactly-Once Activation and Failure and Degradation; D-06 S08 and adversarial ordering simulation; AE-01 Solution Contract Activation Choreography and Failure Contract; AE-01 Data Contract Migration 21 replay semantics.

### R081-03 - MEDIUM - CCT evidence does not cover the production activation boundaries

**Evidence**

- `goals/GOAL-005-wc059-implementation-evidence.md:15-23` marks `CCT-AE01-ACT-01`, `CCT-AE01-ACT-CONFLICT`, and `CCT-AE01-ACT-FAIL` as PASS.
- The BP activation tests use EF Core InMemory, a mocked billing gateway, and direct service calls; they do not execute a Temporal test server or authenticated WBE owner route.
- `tests/billing-engine/test_payment.py` proves sequential SQLite replay but has no concurrent PostgreSQL paid-activation test and no ADR-046 authentication test for `/payments/paid-activation`.

**Impact**

The green test counts demonstrate useful local logic but overstate production-path proof. They cannot falsify the two findings above, and therefore do not satisfy WC059-08's integration requirement for conflicting tuple, owner failure, exactly-once activation, and owner-boundary security.

**Required correction**

After R081-01 and R081-02 are repaired, replace or supplement direct mocks with executable Temporal and authenticated BP-to-WBE integration evidence. Run concurrent paid-activation cases against PostgreSQL 16, including response loss after WBE commit, competing requests, failed execution retry, divergent replay, and owner-authentication denial with zero mutation. Update the evidence matrix so each PASS names the production boundary it actually executes.

**Constitutional and architectural basis**

C-065, C-071, C-073, C-076; ADR-046 section 10; WC059-08; AE-01 Solution Contract failure semantics.

## Conformance Confirmed

- D-03 state ownership is preserved in `ActivationOrchestrationService`: WBE never writes the Employment Relationship state.
- The normal-path order is contract/acceptance validation, evidenced `ACTIVATION_PENDING`, WBE activation, constitutional evidence, then atomic BP `ACTIVE` plus stored intent outcome.
- WBE `CONVERTED` is a billing projection only and is written after paid subscription activation.
- Migration 21b supplies immutable contract and acceptance records, tenant RLS, canonical activation-tuple uniqueness, terminal intent immutability, and stored outcome constraints.
- The public BP activation endpoint derives contract, acceptance, authority, participant, and correlation from authenticated/canonical BP state; only payment reference and deterministic payment evidence identity cross the public request.
- OpenAPI describes success, ineligible/conflicting, and unresolved outcomes without claiming payment alone activates employment.
- WhatsApp remains unable to accept a contract or initiate payment, and the web journey preserves explicit Hire, Not now, Cancel, and Exit choices.
- No live Razorpay credential activation, provider account setup, deployment, production/customer proof, WC-060 continuity implementation, or merge is present in the reviewed range.

## Checks Run

| Check | Result |
|---|---|
| Branch and range verification | PASS - `ib/014/wc059-implementation`; baseline `1d98765`; HEAD `6d4fce5`; nine WC-059 commits |
| Focused BP activation tests | PASS - 9/9 in Docker test-runner |
| Full BP suite | PASS - 239/239 in Docker test-runner |
| Focused WBE payment tests | PASS - 19/19 in Docker test-runner |
| Full WBE suite | PASS - 377/377 in Docker test-runner |
| Full web unit suite | PASS - 84/84 in Docker test-runner |
| Next.js production build | PASS - strict TypeScript/lint/build; 23 static pages generated |
| Committed artifact boundary scan | PASS - no committed `.coverage`, `logs/blueprint_assurance_report.json`, `bin`, `obj`, or `.next` artifact |
| `git diff --check 1d98765..HEAD` | FAIL - trailing whitespace in `goals/GOAL-005-wc059-implementation-evidence.md:3`; non-blocking hygiene defect, but the evidence file should be cleaned during remediation |
| Protected local artifacts | PRESERVED - pre-existing unstaged `.coverage` and `logs/blueprint_assurance_report.json` were not staged or modified by this review |

## Residual Risks

- The review did not invoke live Razorpay, external providers, deployment, or production infrastructure; those remain unauthorized and unproven.
- Browser acceptance and migration/concurrency results cited by the implementation record were inspected but not fully rerun in this review. Their local claims do not mitigate R081-01 through R081-03.
- The inherited canonical OpenAPI `Forbidden` response reference remains pre-existing debt outside WC-059; it is not a basis for this verdict.
- State synchronization remains intentionally pending review closure and must not be represented as WC-059 completion while this verdict is open.

## Re-review Gate

Re-review requires all three findings to be remediated in implementation and executable evidence. INST-004 will verify the authenticated owner route, Temporal completed-run retry/conflict behavior, PostgreSQL concurrency, unchanged D-03/D-06 ownership and ordering, and preservation of all deployment/live-provider exclusions. No merge or production activation is authorized by this review.
# R-066 - WC-034 F4 ADR-046 Business Review

## G-10 Attestation

| Attestation field | Value |
|---|---|
| `institution_id` | INST-003 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-003-06 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T16:02:13+00:00 |
| Date | 2026-08-10 |
| `authorization_id` | [GOA-GOAL-005-INST-003-05](../goals/GOAL-005-execution-plan.md#goa-goal-005-inst-003-05), issued 2026-08-10T15:57:39+00:00 |
| `acceptance_record` | [ACC-GOAL-005-INST-003-05](../goals/GOAL-005-execution-plan.md#acc-goal-005-inst-003-05), accepted 2026-08-10T15:57:40+00:00 |
| Execution Plan | [GEP-GOAL-005-INST-013-05](../goals/GOAL-005-execution-plan.md#amendment-4--wc-034-f4-workload-authentication-adr-closure) |
| Learning output | [LR-GOAL-005-INST-003-02](../goals/GOAL-005-f4-workload-identity-business-learning.md) |
| **Verdict** | **APPROVED WITH CONDITIONS** |

## 1. Independence, Inputs, And Decision Space

This review was produced by INST-003 after its matching Acceptance Record and within the one-session Participation Window. This context did not author or edit [ADR-046](../adr/ADR-046-workload-identity-and-service-authentication.md), `CR-GOAL-005-INST-004-10`, or `LR-GOAL-005-INST-004-06`. It did not perform the later INST-002 Constitutional review and did not rely on authentication design preference as a substitute for business assessment.

Review inputs were:

- ADR-046 and its Order 1 Contribution and Learning Records;
- GEP-GOAL-005-INST-013-05, GOA-GOAL-005-INST-003-05, and ACC-GOAL-005-INST-003-05;
- the approved F4 Relationship Workspace business semantics in `CR-GOAL-005-INST-003-04`;
- Founder Vision business-outcome primacy, capabilities 6.1 through 6.4, and AD-002, AD-004, AD-008, AD-009, and AD-010; and
- R-064 condition EA-F4-01, including the disclosed ADR-007 route/environment mismatch.

The review covers business-driver and capability coverage, operational continuity, customer-rights effects, truthful unavailable/blocked behavior, Emergency Stop independence, environment parity as a business-risk control, owner boundaries, customer outcomes, support/incident implications, and future evidence sufficiency. It does not choose architecture mechanisms, repair or accept ADR-046, resolve F4-POL-01 through F4-POL-06, produce Constitutional review, authorize implementation, or authorize deployment.

## 2. Business Determination

ADR-046 is aligned with the F4 business purpose. It permits BP to compose one relationship-bound customer view while preserving WBE commercial truth, PR execution truth, CE constitutional authority, and private professional/domain semantics. Mandatory fail-closed behavior prevents missing or invalid workload identity from becoming anonymous access, cross-relationship leakage, fabricated owner truth, or false command success. Environment parity is a business-risk control because development and CI must exercise the same identity, audience, denial, privacy, replay, and isolation meanings that protect customer relationships in cloud environments.

The decision also preserves customer rights. Authentication failure cannot grant authority, create evidence, change commercial or execution truth, or disable the dedicated Emergency Stop path. Affected capability families remain truthfully `UNAVAILABLE` or `BLOCKED`, and public errors remain privacy-safe. The no-plaintext-fallback migration rule accepts bounded feature unavailability rather than exposing customers to unauthenticated continuity; this is the correct business priority when truthful consequence and recovery support are supplied.

Approval is conditional because ADR-046 Section 10 is predominantly security and transport evidence. It says authentication success is not business success, but it does not yet require executable proof that an authenticated F4 request reaches the correct owner-confirmed business outcome, preserves the customer's intended consequence, and remains honestly unresolved when any downstream owner or constitutional step fails. It also lacks a complete business-continuity and support evidence obligation for planned migration unavailability, credential incidents, restoration, and customer-impact reconciliation.

## 3. Business Capability Matrix

| F4 capability | Business value and customer right | Accountable truth owner | ADR-046 coverage | Required unavailable/blocked behavior | Review result |
|---|---|---|---|---|---|
| Relationship context and Plan | Understand the selected professional, current goal, intended work, dependencies, and authority needs | BP governance projection; professional prepares plan; customer owns outcome acceptance | Exact BP caller/target binding and relationship rebinding protect the selected relationship | Unknown or unavailable context must not present a current plan or grant action | PASS, subject to end-to-end outcome evidence |
| Needs your attention | See only authoritative, material customer decisions in accountable order | BP owns the complete authoritative order; downstream owners supply facts | Exact route, operation, purpose, tenant, and relationship binding prevents cross-context use | Owner outage or authentication failure must not be replaced by browser ranking or cached authority | PASS, subject to continuity and restoration evidence |
| Work and governed commands | Understand what is happening and exercise only valid customer actions | BP owns public command state; PR owns execution truth; CE retains required authorization/evidence | Authentication is separated from authority, CE permission, evidence, and completion; replay/idempotency semantics preserve unknown outcomes | Failure remains `BLOCKED`, `REJECTED`, `UNKNOWN`, `PARTIAL`, or `UNAVAILABLE` as owner truth requires, with no optimistic success | PASS, subject to end-to-end business-consequence evidence |
| Results | Judge professional value against a baseline, measure, period, evidence, and attribution limit | Professional/domain owner defines outcome semantics; BP composes; CE evidence does not manufacture outcome | Adapter identity is explicit and private; technical success is expressly not a customer result | Missing owner evidence remains outcome unavailable, evidence pending, stale, disputed, or attribution unknown | PASS WITH CONDITION: future evidence must prove this distinction end to end |
| Usage and budget | Understand allowance actuals, remaining allowance, ceiling, forecast, assumptions, and consequences | WBE is the sole commercial-truth owner; BP relays without recomputation | WBE audience and owner rebinding preserve commercial ownership and distinct `BLOCKED` truth | Authentication or WBE failure must not become zero use, available budget, rejected policy, or successful command | PASS, subject to owner-confirmed outcome and incident-reconciliation evidence |
| Rights and control | Inspect scope, authority, lifecycle, evidence access, pause/terminate rights, and unconditional Stop | BP projects rights; CE licenses authority and records constitutional evidence; dedicated Stop remains separately governed | Authentication cannot create authority or evidence; Stop is independent of F4 owner routes, envelope issuance, rotation, WBE, adapters, and CE authentication | Rights remain reachable and affected non-Stop actions fail honestly; Stop remains available | PASS WITH CONDITION: support and incident proof must cover rights impact and restoration |
| Platform operation across environments | Receive consistent protection and truthful behavior before production exposure | BP/WBE/PR/CE/domain owners within their boundaries; platform/security owners manage service identity | Same identity, audience, denial, error, replay, and isolation semantics in development, CI, and cloud; only issuance/custody differ | No environment-only bypass or plaintext continuity; affected F4 family remains unavailable or blocked | PASS as a business-risk control |

## 4. ADR-007 Mismatch And Migration Continuity

ADR-046 correctly discloses that ADR-007 still permits plain development transport for existing BP-to-CE and PR-to-CE routes while the new F4 routes require parity. It does not silently generalize or amend ADR-007. From a business-continuity perspective, this leaves two risks that must remain visible:

1. evidence from the stronger F4 route model cannot be generalized to existing CE routes; and
2. a shared BP-to-PR transport migration can affect already completed F3 behavior and must not be characterized as harmless merely because F4 authentication tests pass.

ADR-046 correctly rejects dual-mode plaintext fallback and allows an affected F4 family to remain `UNAVAILABLE` or `BLOCKED` when atomic cutover is not possible. That protects customer rights better than insecure continuity. However, planned unavailability still requires an accountable impact window, customer-language consequence, support path, preservation of pending intent, owner-by-owner restoration checks, and reconciliation before the capability returns to available. Technical listener health alone is not sufficient restoration evidence.

## 5. Exact Conditions

**APPROVED WITH CONDITIONS.** The following conditions are exact and mandatory:

1. **ADR repair - business outcome evidence:** Before ADR-046 may become Accepted, INST-004 must be prospectively authorized to repair Section 10 so future executable evidence includes an end-to-end business-operation matrix for every enabled F4 owner path. For each BP-to-WBE, BP-to-PR, and BP-to-domain-adapter read or command family, the matrix must prove: authenticated transport; correct owner receipt; required CE authorization/evidence where applicable; owner-confirmed business state and consequence; BP public translation; and the final customer-visible state. It must include negative and partial cases proving that successful mTLS/envelope validation, request acceptance, technical completion, or evidence recording alone never becomes completed work, available authority, actual commercial truth, or achieved business outcome.
2. **ADR repair - continuity, customer disclosure, and support evidence:** Before ADR-046 may become Accepted, INST-004 must be prospectively authorized to repair Sections 7.2 and 10 so future migration and incident evidence names, for each affected F4 family and any shared F3 BP-to-PR route: accountable business owner; planned or incident impact window; customer-language `UNAVAILABLE`, `BLOCKED`, or unknown consequence; rights and Emergency Stop status; preservation and reconciliation of pending customer intent and unknown outcomes; privacy-safe correlation and support escalation; owner-by-owner restoration criteria; and post-restoration confirmation that no duplicate mutation, cross-relationship state, lost decision, false success, or stale authority is exposed. Availability may be restored only after business-state reconciliation, not merely certificate, listener, or request-health success.

This review does not perform either repair. ADR-046 remains `PROPOSED` until both conditions are satisfied and the later fresh INST-002 review approves its own scope.

## 6. Unresolved Risks

1. Until Condition 1 is added, technically successful authentication can be over-reported as F4 success without proving the intended owner and customer outcome chain.
2. Until Condition 2 is added, fail-closed migration or credential incidents can protect security while still producing unmanaged customer deadlines, lost intent, support ambiguity, or premature restoration claims.
3. ADR-007's accepted development mismatch remains outside this review and prevents parity evidence from being generalized to BP-to-CE or PR-to-CE.
4. F4-POL-01 through F4-POL-06 remain unresolved and fail-closed; authentication cannot choose a customer-rights or commercial default.
5. Concrete future owner contracts, executable G-F4-10 evidence, F4 implementation, deployment, provider operation, and customer-proof evidence do not yet exist.
6. DMA current-version Founder approval and live customer-proof evidence remain absent; specification, transport health, work completion, or provider metrics cannot be presented as customer value.

## 7. Owner Boundaries And Review Boundary

- BP remains the sole ordinary public F4 facade, relationship-governance projection owner, public command-state owner, and privacy-safe error translator.
- WBE remains the sole owner of allowance, actual, budget, ceiling, forecast, threshold, pacing, commercial consequence, and distinct `BLOCKED` truth.
- PR remains the owner of professional execution truth and gains no public relationship, rights, commercial, or outcome authority.
- CE remains the constitutional validation, authority-licensing, and constitutional-evidence authority; service authentication neither calls CE as a trust oracle nor substitutes for CE obligations.
- Professional/domain adapters remain private owners of domain outcome semantics and provenance; they do not grant authority, order attention, calculate WBE truth, or prove customer success by transport completion.
- Web remains a BP public/generated-client consumer with no private credential, service, provider, or ledger access.

No architecture mechanism, ADR text, policy default, canonical contract, generated client, source, test, infrastructure, deployment, or customer outcome was produced or authorized by this review.
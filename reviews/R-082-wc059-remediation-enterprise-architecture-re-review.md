# R-082 - WC-059 Remediation Enterprise Architecture Re-review

| Field | Value |
|---|---|
| Reviewer office | INST-004 Enterprise Architect |
| Work Contract | WC-059 - AE-01 Contract, Payment, and Exactly-Once Activation |
| Prior review | R-081 - CHANGES REQUESTED |
| Remediation commits | `a95de68268ebec6f5c5154f581d369eb0bf3695c`, `6c82aee` |
| Reviewed range | `1d9876595921607997bcadca53e13048030d4e5f..6c82aee` |
| Review date | 2026-08-11 |
| Decision | **CHANGES REQUESTED** |

## Verdict

The two remediation commits correct the implementation defects identified by R-081. The generic unauthenticated paid-activation route is absent. BP now invokes an ADR-046 authenticated WBE owner command, and WBE denies unbound requests before owner mutation and rebinds the request to its captured-payment truth. BP now performs durable material preflight before Temporal, returns stored success directly, rejects divergent material before workflow join, and configures failed-only workflow ID reuse while preserving one activation-intent row.

The contribution is not approvable because the executable evidence still does not exercise the production boundaries it claims, and the accepted canonical WBE contract publication is stale after the new operation was added. R081-03 therefore remains open, and R082-01 records the new blocking contract-registry drift.

## R-081 Finding Dispositions

### R081-01 - CLOSED - Paid activation uses the authenticated BP-to-WBE owner boundary

**Verified correction**

- No production or specification path named `/payments/paid-activation` exists in the reviewed range. The only current paid-activation operation is `POST /internal/v1/relationships/{relationshipId}/paid-activation`; the old string remains only in R-081 history.
- `AuthenticatedActivationBillingGateway` creates its client through `WorkloadIdentityClient.CreateClient`, which presents BP client identity and validates the exact WBE server identity.
- The signed delegated envelope is bound to the WBE audience, `POST`, route template, `activatePaidRelationship`, contract major 1, canonical body digest, server-derived tenant, relationship, active EMPLOYER role, purpose, accepted contract, contract version, activation intent, correlation, and idempotency identity.
- The WBE route requires the transport-captured peer certificate and signed envelope. Signature, issuer-to-peer identity, audience, method, route, operation, contract major, digest, expiry, replay, relationship, correlation, and idempotency validation complete before a database session or owner service is opened.
- WBE then loads the captured `payment_intents` row and independently compares tenant, relationship, accepted contract, contract version, contract acceptance, and payment evidence before subscription or trial mutation. Activated replay must also match activation intent and correlation.
- The workload registry grants only BP the exact paid-activation operation. The private WBE listener requires client certificates and TLS 1.2 or newer. The private OpenAPI and WBE manifest name the same internal route and owner.

**Disposition:** The implementation finding is closed. Executable end-to-end proof of this boundary remains required under R081-03.

### R081-02 - CLOSED - Durable preflight and failed-only Temporal reuse preserve retry semantics

**Verified correction**

- `ActivationWorkflowDispatchService.StartAsync` derives protected activation material from authenticated BP relationship, participant, acceptance, and authority state.
- `ActivationOrchestrationService.PrepareDispatchAsync` loads or creates the canonical durable intent and compares the complete material hash before `StartOrJoinAsync` is called.
- Divergent material raises `ActivationConflictException` before Temporal join. Identical stored success is returned directly without starting or joining a workflow.
- Running identical replay may join the existing execution. A closed failed execution may restart under `WorkflowIdReusePolicy.AllowDuplicateFailedOnly`; a successful execution is not reused because durable preflight returns its stored outcome first.
- `FAILED_RETRYABLE` reuses the existing database intent and stable correlation. Database uniqueness on tenant, relationship, accepted contract, and payment reference remains the canonical arbiter, so workflow restart does not create a second durable intent.
- BP still records `ACTIVATION_PENDING` before WBE activation, requires CE evidence before `ACTIVE`, and stores the successful intent outcome atomically with the relationship transition.

**Disposition:** The implementation finding is closed. Temporal execution evidence remains required under R081-03.

### R081-03 - RETAINED - Evidence does not execute the claimed production boundaries

**Evidence gap**

- The cited WBE `40/40` slice consists of SQLite paid-activation tests, direct delegated-context verifier tests, direct `_rebind_paid_activation` tests, and one FastAPI request proving missing identity is denied. It does not start the WBE private listener, complete a BP-to-WBE mTLS handshake, invoke `AuthenticatedActivationBillingGateway`, or execute a successful signed request through the route into captured-payment mutation.
- No WBE test references `private_listener_config` or `MutualTlsH11Protocol`; the repository's private-listener tests cover Professional Runtime only.
- No BP test references `AuthenticatedActivationBillingGateway`.
- The BP `11/11` activation slice uses EF Core InMemory, a recording billing gateway, and a recording workflow starter. No test executes `TemporalActivationWorkflowStarter`, starts a Temporal test server, observes a failed execution, or asserts `AllowDuplicateFailedOnly` behavior through Temporal.
- PostgreSQL 16 first/reapply is valid when independently rerun, but there is no committed executable migration harness for migrations 21b/21c or concurrent paid activation against PostgreSQL.
- The implementation evidence matrix therefore overstates `CCT-AE01-ACT-01`, `CCT-AE01-ACT-CONFLICT`, and `CCT-AE01-ACT-FAIL` as production-boundary proof.

**Required correction**

Add executable evidence that:

1. Starts the WBE private listener with real test certificates and invokes it through BP's authenticated client.
2. Proves positive mutation and missing/invalid/replayed/wrong-audience/wrong-route/wrong-body/confused-deputy/cross-tenant/stale-version denial with zero owner mutation.
3. Runs Temporal with identical running replay, stored completed success, divergent running/completed material, exhausted owner/evidence failure, and failed-only restart of the same durable intent.
4. Runs competing paid activations and response-loss replay against PostgreSQL 16, and packages migration 21b/21c first-apply/reapply as a reproducible repository check.
5. Updates the evidence matrix to distinguish unit, component, integration, PostgreSQL, and deployment provenance accurately.

## New Finding

### R082-01 - HIGH - Canonical WBE contract attestation is stale

**Evidence**

- `architecture/reference/api-specs/wbe-relationship-workspace.openapi.yaml` is now version `1.1.0`, has SHA-256 `b8ace8ccf218e430b61abb979bbd426843ca84b14a6e2adcfe46243aa1122623`, and contains four operations including `activatePaidRelationship`.
- `architecture/reference/components/relationship-workspace-canonical-contracts.md` still fixes WBE at version `1.0.0`, SHA-256 `999b6687f7a0e96e6b362ca286805ee4bb44058f0e67e3dad2f928d74d78eaff`, and an exact inventory of three operations.
- That document's owner attestation says the fixed bytes matched and were accepted. Those statements are no longer true for the current committed file.
- The workload registry and WBE manifest include the fourth route, while the canonical contract set and owner-attestation matrix omit it. Test traceability headers also still identify WBE OpenAPI `1.0.0`.

**Impact**

The implementation range changed an accepted private-owner contract without synchronizing the hash-bound canonical publication and owner operation inventory. This breaks C-008/C-032 constitutional-chain traceability and DP-009 API-first consistency. A reviewer cannot treat the manifest, route registry, OpenAPI, canonical contract set, and accepted owner attestation as one coherent architecture record.

**Required correction**

Route the WBE `1.1.0` contract through the constitutionally authorized architecture/owner-attestation update. Recompute and record the canonical hash, add `activatePaidRelationship` to the exact owner operation inventory, reconcile traceability headers, and run the canonical compatibility/hash validation. INST-010 must not rewrite the accepted architecture or attest its own implementation.

## Conformance Confirmed

- BP remains the sole public relationship facade and D-03 relationship-state owner.
- WBE remains the captured-payment, paid-subscription, and trial billing-projection owner; `CONVERTED` is not a relationship state.
- CE evidence remains required before BP stores `ACTIVE`.
- The generic unauthenticated route is absent and the legacy generic `WBE` HttpClient is not used for paid activation.
- Migration 21b preserves immutable contracts/acceptances, canonical activation uniqueness, stored outcomes, terminal immutability, and forced tenant RLS.
- Migration 21c preserves captured payment material and payment-keyed subscription uniqueness.
- WhatsApp cannot accept a contract or initiate payment.
- No live Razorpay/provider activation, credentials/account setup, WC-060, deployment, production/customer proof, self-review, merge, or push is introduced or authorized.

## Checks Run

| Check | Result |
|---|---|
| Branch and range | PASS - `ib/014/wc059-implementation`; baseline `1d98765`; HEAD `6c82aee` |
| Remediation commits | PASS - `a95de68` and `6c82aee` present after R-081 |
| Generic route scan | PASS - `/payments/paid-activation` absent outside R-081 historical text |
| Focused BP activation tests | PASS - 11/11 in Docker test-runner |
| Focused WBE activation/authentication tests | PASS - 40/40 in Docker test-runner-python |
| ADR-046 PKI/registry bootstrap tests | PASS - 15/15 in Docker test-runner-python |
| PostgreSQL 16 migration first/reapply | PASS - migration 19 once, then 21b/21c twice; activation intent and paid-subscription tables present; three forced-RLS policies present |
| Canonical WBE contract hash/version/inventory | FAIL - current `1.1.0`/`b8ace8...`/four operations conflicts with accepted `1.0.0`/`999b66...`/three operations |
| Production-boundary test inventory | FAIL - no WBE private-listener, BP authenticated-gateway, Temporal execution, or committed PostgreSQL integration test |
| `git diff --check 1d98765..HEAD` | PASS |
| Committed prohibited-artifact scan | PASS - no `.coverage`, blueprint report, `bin`, `obj`, or `.next` in the committed range |
| Protected local artifacts | PRESERVED - pre-existing unstaged `.coverage` and `logs/blueprint_assurance_report.json` remain unstaged and unmodified by this review |

## Residual Risks

- Live Razorpay, cloud credential custody/rotation/revocation, deployment, and customer operation remain unauthorized and unproven.
- The accepted ADR-046 private-listener design exists in source, but this review has no executable network evidence that the paid-activation route behaves identically through the real TLS transport.
- The failed-only Temporal behavior is supported by source inspection, not by execution evidence.
- PostgreSQL migration reapply passed an isolated reviewer-created prerequisite baseline; the repository still lacks a reproducible committed migration/concurrency test for this slice.
- The inherited Business Platform OpenAPI `Forbidden` reference remains pre-existing debt outside WC-059.

## Re-review Gate

Re-review requires R081-03 and R082-01 to be resolved. The next INST-004 reviewer must verify real authenticated owner-route execution, real Temporal failed-only reuse and pre-join conflict behavior, PostgreSQL concurrency/reapply evidence, corrected evidence provenance, and a synchronized canonical WBE contract publication. No merge, deployment, provider activation, or production claim is authorized by this review.
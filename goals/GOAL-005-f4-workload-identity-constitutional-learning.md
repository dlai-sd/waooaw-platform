# GOAL-005 F4 Workload Identity Constitutional Review Learning

## G-10 Attestation

| Attestation field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-002-02 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-10T16:36:33+00:00 |
| Date | 2026-08-10 |
| `authorization_id` | [GOA-GOAL-005-INST-002-04](GOAL-005-execution-plan.md#goa-goal-005-inst-002-04), issued 2026-08-10T16:20:02+00:00 |
| `acceptance_record` | [ACC-GOAL-005-INST-002-04](GOAL-005-execution-plan.md#acc-goal-005-inst-002-04), accepted 2026-08-10T16:20:03+00:00 |
| Execution Plan | [GEP-GOAL-005-INST-013-05](GOAL-005-execution-plan.md#amendment-4--wc-034-f4-workload-authentication-adr-closure) |
| Reviewed decision | [ADR-046](../adr/ADR-046-workload-identity-and-service-authentication.md) at commit `2547276aea7aa7e597a93f36cf9a1bf0e6c0ec97` |
| Contribution | [R-067 / CR-GOAL-005-INST-002-08](../reviews/R-067-wc034-f4-adr046-constitutional-review.md) |
| `improvement_signal` | Constitutional review of a private service route must trace secure admission, delegated context, owner truth, applicable CE obligations, public translation, customer consequence, and restoration as separate links; no link may be inferred from authentication or evidence at another link. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |

This record was produced after the matching Acceptance Record, within the Order 3 Participation Window, and in the same fresh INST-002 context as its linked Contribution Record. Its identifier was reserved by the authorization and had no prior Learning Record artifact.

## 1. Independence And Reviewed Scope

This learning was produced by the fresh INST-002 context that authored only R-067. The context is distinct from R-065, R-063, Amendment 4 authoring and repair, R-066, and every prior non-persisting draft. It did not edit ADR-046, repair R-066, perform Business review, accept the ADR, or produce implementation evidence.

The reviewed scope was ADR-046 at commit `2547276`, its original and repair CR/LR chain, R-066 Conditions 1 and 2, Amendment 4 authority, ratified Constitution/GENESIS/claims, ADR-007 and ADR-014, and the approved F4 BP, WBE, PR, CE, domain-adapter, browser, ledger, and shared-F3 boundaries.

## 2. Constitutional Discovery And Evolution Rationale

`constitutional_discovery` is **no** because the review found no new constitutional principle, contradiction, or underdetermined constitutional meaning. Existing Articles II, III, IV, VI, VII, IX, X, XI, XII, XIII, XIV, and XV; Amendment A-003; C-001, C-002, C-003, C-005, C-006, C-008, C-023, C-026, C-031, C-032, C-063, C-065, C-083, C-084, and C-085 already require the relevant separation, traceability, evidence, privacy, review, and Stop properties.

`evolution_triggered` is **no** because the accepted constitutional model and existing Institutional Decision Spaces are sufficient. The review requires no new claim, precedent, amendment, Institution, charter, WIOM Stage W-5 process, or governance mechanism. R-066 exposed missing future evidence obligations, and the authorized INST-004 repair resolved them without changing the selected mechanism or constitutional structure.

## 3. Reusable Learning

The reusable constitutional-review rule is:

> Authenticate the workload exactly, authorize the exact route separately, rebind delegated context to owner truth, invoke CE only for the constitutional step it owns, and prove business meaning through the accountable owner and customer surface. Never let one successful link stand in for another.

Apply that rule as seven independent questions:

1. **Identity:** Which exact asymmetric workload, environment trust domain, and peer certificate made the call?
2. **Least privilege:** Was that identity authorized for this exact audience, adapter, method/route, operation, body, purpose, and contract major?
3. **Delegation:** Did the target bind short-lived delegated actor, tenant, relationship, role, purpose, and version claims to authenticated BP and its own relationship/resource truth?
4. **Constitutional authority:** Did each applicable CE authorization, authority-licensing, and Evidence First step occur without making CE the transport-authentication oracle?
5. **Owner truth:** Did the accountable BP, WBE, PR, or domain owner confirm its own authoritative state and consequence without another layer recomputing it?
6. **Customer meaning:** Did BP and the generated-client/browser preserve unavailable, blocked, unknown, partial, rejected, stale, disputed, and attribution-limited meaning without optimistic upgrade?
7. **Recovery:** After migration or credential failure, were pending intent and unknown outcomes reconciled owner-by-owner before availability returned?

This reasoning generalizes beyond mTLS. Authentication can prove who presented a credential. It cannot prove that the caller has constitutional authority, that evidence was recorded, that an owner mutation committed, that a commercial fact is current, that work completed, or that a business outcome occurred.

## 4. Rejected Shortcuts

| Rejected shortcut | Constitutional rejection reason |
|---|---|
| Treat exact mTLS success as operation authority | Identity is not authority. Exact route, operation, audience, purpose, version, and owner policy remain independently required under Articles III, IV, and VII. |
| Treat a signed delegated envelope as a capability token | Context becomes concentrated bearer power unless rebound to authenticated BP, the target call, tenant/relationship mapping, and target-owned truth. |
| Ask CE to authenticate TLS or validate every envelope | CE owns constitutional validation, licensing, and evidence, not transport identity. Making it the authentication oracle conflates powers and couples Stop/recovery to CE availability. |
| Infer commercial or execution truth from request acceptance | WBE and PR retain their own authoritative states; transport or technical completion cannot create owner truth. |
| Infer customer outcome from evidence presence | Evidence supports review and trust but does not manufacture attribution, completed work, commercial actual, or business value. |
| Restore availability when certificates/listeners become healthy | Technical health does not reconcile pending intent, unknown commit, duplicate mutation, stale authority, cross-relationship state, or customer consequence. |
| Use a generic adapter identity, audience, wildcard SAN, or broad route family | Broad matching makes least privilege unfalsifiable and permits cross-domain confused-deputy use. |
| Use shared HMAC, plaintext dev/CI, or network location for convenience | Environment-specific bypass produces false parity evidence and cannot prove a unique asymmetric workload. |
| Generalize ADR-007 to new routes or ADR-046 back to CE routes | Accepted ADR scope cannot be expanded by analogy; silent amendment violates C-031 and the Constitutional Chain. |
| Count a future evidence specification as executable proof | A falsifiable obligation is not its test result. Specification, fixture, integration, browser, deployment, and customer evidence retain distinct provenance. |

## 5. Downstream Preservation Rules

1. R-067 has `APPROVED` ADR-046 with `Conditions: NONE`; this permits only mechanical ADR acceptance and EA-F4-01 closure.
2. G-F4-10 executable closure, `F4-POL-01` through `F4-POL-06`, G-F4-12 implementation, G-F4-13 deployment, provider activation, production operation, and F5-F8 remain open, blocked, unresolved, or excluded exactly as before.
3. Every future enabled owner family needs a row in both the Section 10.1 business-operation matrix and the Section 10.2 migration/incident matrix.
4. Shared F3 BP-to-PR behavior must be proven compatible and reconciled explicitly; ADR-046 acceptance does not amend the existing F3 contract or ADR-007.
5. WBE `BLOCKED`, PR execution truth, CE authority/evidence, domain provenance, BP public translation, browser isolation, and Stop independence are mandatory preservation criteria, not optional implementation notes.
6. Passing future implementation evidence can satisfy only the gate named by the later authorization. It cannot prove deployment, provider activation, customer use, attribution, or business outcome.

## 6. Follow-Up Owner

| Follow-up | Accountable owner | Boundary |
|---|---|---|
| Verify R-067 and this Learning Record, then record ADR-046 Accepted and EA-F4-01 closed | INST-013 | Mechanical Amendment 4 Order 4 closure only; no reinterpretation, repair, implementation, or deployment authority |
| Resolve `F4-POL-01` through `F4-POL-06` | Registrant/Founder and prospectively authorized accountable owners | Separate policy authority; no defaults arise from authentication approval |
| Plan owner contracts and executable evidence | Prospectively authorized INST-005, INST-007, BP, WBE, PR, CE, and domain owners | Must preserve ADR-046, both evidence matrices, F3 compatibility, provenance labels, and all owner boundaries |
| Produce future implementation evidence | INST-010 after a separate amendment, fresh CA readiness, exact Registrant acknowledgement, valid GOA, and acceptance | No current implementation, provider activation, or deployment authority |
| Authorize deployment or customer operation | Separately authorized release/deployment owner and Founder process | G-F4-13 remains blocked; implementation evidence is not deployment or customer proof |

The immediate next action is INST-013's mechanical Amendment 4 Order 4 closure. This Learning Record triggers no constitutional evolution and grants no downstream execution authority.

# GOAL-005 — Goal Execution Plan

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-01 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-08T10:40:09+00:00 |
| Status | COMPLETE — D-01 through D-07 RATIFIED by R-046; implementation NONE |

## Registrant Acknowledgement Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-01 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-08T10:53:16+00:00 |
| Acknowledged plan | GEP-GOAL-005-INST-013-01 |
| Decision | ACKNOWLEDGED — proceed phase-by-phase through D-07 and stop before implementation |

## Phase 1 Authorization Records

### GOA-GOAL-005-INST-003-01

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-003-01 |
| `record_type` | Authorization Record |
| `produced_at` | 2026-08-08T10:53:17+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-003-01 |
| Authorized Institution | INST-003 — Business Architect |
| Contribution scope | D-01 Employment Capability Confirmation |
| Participation Window | 2 constitutional sessions after valid acceptance |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-08T10:53:17+00:00 |

### GOA-GOAL-005-INST-011-01

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-011-01 |
| `record_type` | Authorization Record |
| `produced_at` | 2026-08-08T10:53:18+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-011-01 |
| Authorized Institution | INST-011 — Product Owner |
| Contribution scope | D-01 product-outcome and release-boundary input |
| Participation Window | 1 constitutional session after valid acceptance |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-08T10:53:18+00:00 |

## Phase 2 Authorization Records

### GOA-GOAL-005-INST-004-01

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-01 |
| `record_type` | Authorization Record |
| `produced_at` | 2026-08-08T11:07:00+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-01 |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | D-03 Identity and Employment State Model architecture |
| Evidence required | Shared identity invariants, aggregate boundary, lifecycle states and transitions, exactly-once activation semantics, correlation rules, and cross-wave boundary |
| Participation Window | 3 constitutional sessions after valid acceptance |
| Constraint | Consume D-01; do not finalize product policy, D-02, D-04, D-06, or implementation design |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-08T11:07:00+00:00 |

### GOA-GOAL-005-INST-006-01

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-006-01 |
| `record_type` | Authorization Record |
| `produced_at` | 2026-08-08T11:07:01+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-006-01 |
| Authorized Institution | INST-006 — Data Architect |
| Contribution scope | D-03 durable identity, state, idempotency, evidence-correlation, and continuity data contribution |
| Evidence required | Identifier ownership, relationship aggregate semantics, transition persistence, idempotency keys, evidence correlation, retention, and tenant boundaries |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Constraint | Contribute data semantics only; do not approve own evidence or derive implementation schemas |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-08T11:07:01+00:00 |

## Phase 3 Authorization Records

### GOA-GOAL-005-INST-004-02

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-02 |
| `record_type` | Authorization Record |
| `produced_at` | 2026-08-08T12:31:00+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-004-02 |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | D-02 Agent Employment Experience Contract Foundation v1.0 |
| Participation Window | 3 constitutional sessions after valid acceptance |
| Constraint | Consume D-01/D-03; define normative foundation only; no D-04 transport or implementation design |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-08T12:31:00+00:00 |

### GOA-GOAL-005-INST-002-01

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-002-01 |
| `record_type` | Authorization Record |
| `produced_at` | 2026-08-08T12:31:01+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-002-01 |
| Authorized Institution | INST-002 — Constitutional Analyst |
| Contribution scope | D-02 constitutional rights, consent, Human Override, evidence, and traceability contribution |
| Participation Window | 1 constitutional session after valid acceptance |
| Constraint | Constitutional contribution only; INST-001 remains independent final validator |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-08T12:31:01+00:00 |

## Phase 4 Authorization Records

| Authorization | Authorized Institution | Scope | Issued at | Participation Window |
|---|---|---|---|---|
| GOA-GOAL-005-INST-004-03 | INST-004 — Enterprise Architect | D-04 omnichannel continuity architecture and state ownership | 2026-08-08T13:27:00+00:00 | 3 sessions after acceptance |
| GOA-GOAL-005-INST-007-01 | INST-007 — Security Architect | D-04 authentication, participant verification, tenant isolation, threats and controls | 2026-08-08T13:27:01+00:00 | 2 sessions after acceptance |
| GOA-GOAL-005-INST-005-01 | INST-005 — Solution Architect | D-04 channel-neutral contract, events, failures, degradation, conformance interfaces | 2026-08-08T13:27:02+00:00 | 2 sessions after acceptance |

Each row is an `Authorization Record` with `institution_id` INST-013, `goal_id` GOAL-005, `record_id` and `authorization_id` equal to the listed Authorization, `produced_at` equal to Issued at, and `issued_by` INST-013. Scope is specification-only: consume D-02/D-03; define no implementation, provider selection, or D-06 release package.

## Phase 5 Authorization Records

| Authorization | Authorized Institution | Scope | Issued at | Participation Window |
|---|---|---|---|---|
| GOA-GOAL-005-INST-011-02 | INST-011 — Product Owner | D-05 Shared Gap Closure Plan, including G5-TRIAL-POLICY-01 product decision and all Wave 1 foundation closure evidence | 2026-08-08T14:02:00+00:00 | 2 sessions after acceptance |
| GOA-GOAL-005-INST-004-04 | INST-004 — Enterprise Architect | D-05 architecture review for sequencing, D-02/D-03/D-04 conformance, ordering evidence, and threat-proof mapping | 2026-08-08T14:02:01+00:00 | 1 session after acceptance |

Each row is an `Authorization Record` with `institution_id` INST-013, `goal_id` GOAL-005, `record_id` and `authorization_id` equal to Authorization, `produced_at` equal to Issued at, and `issued_by` INST-013. D-05 defines closure decisions and evidence only; it authorizes no implementation or D-06 finalization.

## Phase 6A Authorization Records

| Authorization | Authorized Institution | Scope | Issued at | Participation Window |
|---|---|---|---|---|
| GOA-GOAL-005-INST-011-03 | INST-011 — Product Owner | Incorporate and attest the Founder-directed DMA domain synthesis; propose the governed D-05 amendment from “14 days or 3 sessions” to 14 calendar days; prepare D-06 release grooming inputs without finalizing the package | 2026-08-08T12:19:29+00:00 | 1 constitutional session after acceptance |
| GOA-GOAL-005-INST-004-05 | INST-004 — Enterprise Architect | Independently review the proposed D-05 duration amendment for D-02/D-03/D-04 conformance and confirm whether CB-003 may close | 2026-08-08T12:19:29+00:00 | 1 constitutional session after INST-011 contribution |

Each row is an `Authorization Record` with `institution_id` INST-013, `goal_id` GOAL-005, `record_id` and `authorization_id` equal to Authorization, `produced_at` equal to Issued at, and `issued_by` INST-013. Phase 6A is permitted because the mandatory domain input now exists. It does not authorize the remaining D-06 offices, acceptance or finalization of the D-06 package, D-07, implementation Work Contracts, or implementation. INST-011 must not attribute generated synthesis to Sujay; INST-004 remains independent of product ownership.

## Phase 6B Authorization Records

| Authorization | Authorized Institution | Scope | Issued at | Participation Window |
|---|---|---|---|---|
| GOA-GOAL-005-INST-011-04 | INST-011 — Product Owner | D-06 primary release-grooming package, simulation acceptance, and proposed implementation Work Contract set | 2026-08-08T12:32:00+00:00 | 3 constitutional sessions after acceptance |
| GOA-GOAL-005-INST-003-02 | INST-003 — Business Architect | D-06 customer-outcome and generic-capability review | 2026-08-08T12:32:01+00:00 | 1 session after package delivery |
| GOA-GOAL-005-INST-004-06 | INST-004 — Enterprise Architect | D-06 architecture and cross-wave boundary review | 2026-08-08T12:32:02+00:00 | 1 session after package delivery |
| GOA-GOAL-005-INST-005-02 | INST-005 — Solution Architect | D-06 component, interface, failure, and Work Contract implementability review | 2026-08-08T12:32:03+00:00 | 1 session after package delivery |
| GOA-GOAL-005-INST-006-02 | INST-006 — Data Architect | D-06 identity, state, idempotency, evidence, and tenant-data review | 2026-08-08T12:32:04+00:00 | 1 session after package delivery |
| GOA-GOAL-005-INST-007-02 | INST-007 — Security Architect | D-06 authentication, takeover, replay, downgrade, and cross-tenant review | 2026-08-08T12:32:05+00:00 | 1 session after package delivery |

Each row is an `Authorization Record` with `institution_id` INST-013, `goal_id` GOAL-005, `record_id` and `authorization_id` equal to Authorization, `produced_at` equal to Issued at, and `issued_by` INST-013. Phase 6B starts after R-040 closed CB-003. These authorizations produce specifications, simulation evidence, reviews, and proposed Work Contracts only. They do not authorize INST-010, source changes, schema execution, deployment, or implementation.

## Phase 7 Authorization Records

| Authorization | Authorized Institution | Scope | Issued at | Participation Window |
|---|---|---|---|---|
| GOA-GOAL-005-INST-002-02 | INST-002 — Constitutional Analyst | Assemble the D-07 evidence package, trace rights/consent/Human Override/evidence obligations, and state unresolved constitutional risk; no ratification | 2026-08-08T15:20:00+00:00 | 1 session after D-06 acceptance |
| GOA-GOAL-005-INST-001-02 | INST-001 — Founder | Independently validate accumulated D-01 through D-06 evidence and ratify, return, or block the specification; record implementation boundary separately | 2026-08-08T15:20:01+00:00 | 1 constitutional session after D-07 package delivery |

Each row is an `Authorization Record` issued by INST-013 under the acknowledged plan. INST-002 may prepare but may not ratify because it contributed to D-02. INST-001 alone records the D-07 decision. Ratification approves specifications and proposed Work Contracts only; it does not authorize INST-010, implementation, deployment, or production use.

## Outcome and Boundary

Coordinate D-01 through D-07 to approve shared Agent Employment foundations and produce implementation-ready AE-01 Work Contract candidates. AE-01 remains generic and is proven first by a simulation of a WhatsApp-first DMA trial-to-hire journey. AE-02 through AE-06 remain at their confirmed skeleton depth. The plan stops before implementation.

## Execution Sequence

| Phase | Deliverable | Dependency | Participating Institutions | Gate to next phase |
|---|---|---|---|---|
| 1 | D-01 Employment Capability Confirmation | R2-03 plan approval and acknowledgement | INST-003 primary; INST-011 product-outcome input | Business capabilities, actors, vocabulary, and AE-01 outcome boundaries approved |
| 2 | D-03 Identity and Employment State Model | D-01 accepted | INST-004 primary; INST-006 data contribution | Participant identifiers, aggregate, state transitions, idempotency, and evidence correlation approved |
| 3 | D-02 AEEC Foundation v1.0 | D-01 and D-03 accepted | INST-004 primary; INST-002 constitutional contribution | Normative clauses and constitutional review approved |
| 4 | D-04 Omnichannel Continuity Contract | D-02 and D-03 accepted | INST-004 primary; INST-007 security contribution; INST-005 solution-contract contribution | WhatsApp/web/mobile handoff, state ownership, degradation, and conformance rules approved |
| 5 | D-05 Shared Gap Closure Plan | D-01 through D-04 accepted | INST-011 primary; INST-004 architecture review | Every foundation gap has sequence, owner, acceptance evidence, and epic gate |
| 6 | D-06 AE-01 Release Grooming and Simulation | D-01 through D-05 accepted | INST-011 primary; INST-003 outcome review; INST-004 architecture review; INST-005 contract review; INST-006 data review; INST-007 security review | Simulation passes; proposed AE-01 Work Contracts meet WC-038 through WC-040 quality; no foundation gap remains open |
| 7 | D-07 Independent Validation and Ratification | D-06 accepted | INST-001 final independent validator and ratifier; INST-002 evidence-package preparation only | Founder ratification decision and separate implementation boundary recorded |

Sujay's DMA workshop is required input to D-06 simulation and grooming. Because Sujay is a domain authority rather than a registered Institution, the workshop evidence is incorporated and attested by INST-011; it is not represented as an independent GO-authorized Contribution Record.

## Per-Institution Evidence Specifications

| Institution | Required contribution records | Minimum content | Participation Window | Independence constraint |
|---|---|---|---|---|
| INST-003 Business Architect | D-01 Capability Confirmation; D-06 Outcome Review | Generic capabilities, actors, personas, vocabulary, measurable AE-01 outcomes, DMA boundary | D-01: 2 constitutional sessions; D-06 review: 1 session after package delivery | May not approve architecture or perform final validation |
| INST-011 Product Owner | D-01 Product Outcome Input; D-05 Gap Closure Plan; D-06 Release Grooming Package | Release boundary, gap priority, closure evidence, simulation acceptance, proposed WC set and dependencies | D-01: 1 session; D-05: 2 sessions; D-06: 3 sessions | May not invent architecture or authorize implementation |
| INST-004 Enterprise Architect | D-03 State Model architecture; D-02 AEEC; D-04 Continuity architecture; D-05/D-06 reviews | Shared invariants, normative contracts, cross-wave boundaries, required ADR decisions, architecture conformance | 3 sessions per primary contribution; 1 session per review | May not prioritize stories or perform final validation |
| INST-006 Data Architect | D-03 Data Contribution; D-06 Data Review | Durable identifiers, aggregate and state semantics, idempotency, evidence correlation, continuity data impacts | D-03: 2 sessions; D-06 review: 1 session | Must not validate its own D-03 evidence |
| INST-002 Constitutional Analyst | D-02 Constitutional Review; D-07 evidence-package preparation | Rights, consent, Human Override, evidence rules, constitutional traceability, unresolved-risk statement | D-02: 1 session; D-07 package: 1 session | Because INST-002 contributes, INST-001 performs final G-6/D-07 validation |
| INST-007 Security Architect | D-04 Security Contribution; D-06 Security Review | Authentication, participant verification, consent protection, channel handoff, tenant isolation, threats and controls | D-04: 2 sessions; D-06 review: 1 session | Must not validate its own D-04 evidence |
| INST-005 Solution Architect | D-04 Solution Contract; D-06 Contract Review | Component boundaries, APIs, events, failure/degradation contracts, conformance interfaces | D-04: 2 sessions; D-06 review: 1 session | Must consume approved architecture and may not alter it silently |
| INST-001 Founder | D-07 Final Validation and Ratification | Validate accumulated evidence, resolve any final constitutional decision, ratify or reject AEEC package, state implementation boundary | 1 constitutional session after D-07 package delivery | Independent final validator because INST-002 contributed earlier |

## Phased Authorization Rules

1. No GO Authorization is valid until this plan passes CA Readiness Review and the Registrant acknowledges it.
2. Phase 1 authorizations cover only D-01.
3. Each later phase is authorized only after the preceding gate's Contribution Records are accepted.
4. D-06 drafts may be prepared earlier as non-final working material, but no D-06 Contribution Record may be accepted before D-01 through D-05 close.
5. INST-010 receives no GO Authorization under this plan.
6. Any new Institution requires a Collaboration Amendment and updated Execution Plan.

## Readiness Checks Requested

- Institution status and Offering Scope match.
- Dependencies are acyclic and foundation-first.
- Evidence Specifications are complete and measurable.
- Participation Windows are explicit.
- INST-002 contribution and INST-001 final validation preserve G-02 independence.
- Simulation-first WhatsApp/DMA proof is mandatory before D-06 acceptance.
- No implementation authority is implied.

---

## Amendment 1 — INST-010 WC-034 F2 Contribution

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-02 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-09T18:00:00+00:00 |
| Amends | GEP-GOAL-005-INST-013-01 |
| Amendment basis | G-F2-12 closed by R-056 (APPROVED WITH NOTES, 2026-08-09); FA-031 (WC-034 Phase B authorization, 2026-08-09) and FA-034 (execution release, 2026-08-09) in effect; Founder in-session statement "I do authorize WC-034 F2 implementation for the current session" (Yogesh Khandge, 2026-08-09) |

### What This Amendment Changes

The original Execution Plan (GEP-GOAL-005-INST-013-01) was produced for specification-only phases (D-01 through D-07) and explicitly stated: "INST-010 receives no GO Authorization under this plan." That restriction was correct at the time: the specification had not been produced, reviewed, or ratified.

The following facts now obtain and were not present at original plan issuance:

1. D-01 through D-07 are complete and ratified (R-046, Founder).
2. G-F2-12 (independent INST-004 architecture re-review) is closed by R-056 (APPROVED WITH NOTES, 2026-08-09).
3. FA-031 authorized WC-034 Phase B implementation; FA-034 released execution under that authorization.
4. The Founder has stated authorization of WC-034 F2 implementation in the current session (2026-08-09).
5. GEOM G-7 requires a valid GO Authorization from INST-013 before INST-010 may act on GOAL-005.

This amendment adds a single new phase (Phase 8 — WC-034 F2 Implementation) to the Execution Plan. All D-01 through D-07 contributions, authorization records, and acceptance records are unchanged. This amendment does not affect any prior CA readiness review, acknowledgement, or authorization record.

### Amendment: Phased Authorization Rule 5 Modification

**Rule 5 as written in GEP-GOAL-005-INST-013-01:** "INST-010 receives no GO Authorization under this plan."

**Rule 5 as amended by GEP-GOAL-005-INST-013-02:** INST-010 may receive a GO Authorization under Amendment 1 (GEP-GOAL-005-INST-013-02) for WC-034 F2 implementation only. GOA-GOAL-005-INST-010-01 is reserved and will be issued by INST-013 only after both: (a) CA Readiness Review of this amendment is complete and APPROVED; and (b) a valid Registrant Acknowledgement Record referencing GEP-GOAL-005-INST-013-02 is recorded in the Goal Register.

### Phase 8 — WC-034 F2 Implementation (Amendment 1)

| Field | Value |
|---|---|
| Deliverable | WC-034 F2 Identity and Registration implementation |
| Dependency | Phases 1–7 complete (DONE — D-07 ratified R-046); G-F2-12 closed (DONE — R-056); G-F2-01 READY (DONE — R-052); FA-031/FA-034 in effect |
| Participating Institutions | INST-010 primary implementation; INST-004 independent review (separate session) |
| Gate to completion | Independent INST-004 review APPROVED; ≥90% affected-service line coverage achieved; Docker-only evidence committed to PR |

### Evidence Specification — INST-010 WC-034 F2

| Field | Value |
|---|---|
| Record types required | Implementation Contribution Record; Docker test evidence record; coverage report; INST-004 independent review Contribution Record |
| Participation Window | 5 constitutional sessions after valid acceptance |
| Independence constraint | INST-004 independently reviews in a separate context under C-065; INST-010 may not approve its own PR or declare its own contribution complete |

**Minimum contribution content:**

1. Google OIDC provider: identity/registration implementation for all 13 BP OpenAPI F2 operations per `architecture/reference/api-specs/business-platform.openapi.yaml`; ADR-008 Amendment 1 invariants preserved; Keycloak as sole web credential authority
2. Email-fallback (Keycloak credential path): registration implementation including confirmed-email completion and progressive mobile verification per ADR-008 Amendment 1 §Customer Account Completion and §Progressive Mobile Verification
3. Facebook: Keycloak client configuration designed per ADR-008 Amendment 1 §Facebook Login Scope Isolation; activation gate G-F2-03 NOT bypassed; no live Facebook credential flow activated
4. Apple: Keycloak client configuration designed per ADR-008 Amendment 1; activation gate G-F2-14 NOT bypassed; no live Apple credential flow activated
5. Canonical 13-operation BP TypeScript client generated from `architecture/reference/api-specs/business-platform.openapi.yaml` F2 surface; strict TypeScript compilation pass (OpenAPI Generator 7.17.0 or compatible)
6. Approved F2 UX per `architecture/reference/components/identity-boundary.md` and `architecture/reference/ux/wc-034-implementation-decomposition.md`; provider-subject binding, proof-of-control linking, non-enumerating behavior, AAL3\_FRESH freshness gates, and sign-out/account-switch sentinel implemented
7. Docker-only test evidence; no host Python, no host Node outside the container environment; no manual patches to generated clients
8. ≥90% line coverage on all affected services (Next.js identity routes, BP identity handlers, and any shared identity middleware)
9. No WC-034 F3 through F8 implementation
10. No deployment to any environment; G-F2-13 (deployment authorization) remains independently blocked pending a separate Founder action
11. No PR merge without independent INST-004 review and Founder review

**Excluded from INST-010 scope under this amendment:**

| Excluded item | Authority blocking |
|---|---|
| F3 Conversation core | Canonical BP conversation/stream contracts required |
| F4 Relationship workspace | Plan/Priority Work and Consumption projections required |
| F5 Omnichannel continuity | WC-060 completion required |
| F6 Voice interaction | Voice consent, retention, transcription, and API decisions required |
| F7 Founder administration | Canonical BP Founder facade and WBE management APIs required |
| F8 Integrated acceptance and hardening | All selected F-components complete required |
| Facebook activation | G-F2-03 blocked by FA-002/FA-018 |
| Apple activation | G-F2-14 blocked by FA-019 |
| Deployment | G-F2-13 blocked; separate Founder action required |
| Employment, billing, payment | Outside WC-034 F2 scope |

### Reserved GO Authorization (PENDING — not yet valid)

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-01 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-010-01 |
| Authorized Institution | INST-010 — Platform IT Expert |
| Contribution scope | WC-034 F2 Identity and Registration implementation (Phase 8 — Amendment 1) per Evidence Specification above |
| Participation Window | 5 constitutional sessions after valid acceptance |
| `issued_by` | INST-013 |
| `issued_at` | **RESERVED — not yet issued** |
| **Status** | **PENDING — constitutionally void until: (1) CA Readiness Review of GEP-GOAL-005-INST-013-02 is APPROVED by an independent Constitutional Analyst; and (2) a valid ACK-GOAL-005-INST-001-02 referencing GEP-GOAL-005-INST-013-02 is recorded in the Goal Register** |

An Institution presenting this record prior to a valid `issued_at` timestamp has no constitutional standing under GEOM G-7 and GEOM §G-4 R2-05.

### Registrant Authorization Basis

The following Founder statement is recorded as prima facie evidence of Registrant intent, attached to this amendment as supporting context:

> "I do authorize WC-034 F2 implementation for the current session" — Yogesh Khandge, Founder (INST-001), 2026-08-09

**Constitutional status of this statement:** The intent is unambiguous. This statement cannot itself constitute a formal `Acknowledgement Record` for GEP-GOAL-005-INST-013-02 under GEOM R2-03 for the following reason: the statement was made before this amendment document was produced in the current session, and therefore does not — and cannot — reference GEP-GOAL-005-INST-013-02 by record ID. GEOM requires acknowledgement of the specific Execution Plan; the original acknowledgement (ACK-GOAL-005-INST-001-01) acknowledged GEP-GOAL-005-INST-013-01 and explicitly stated "stop before implementation."

A formal `ACK-GOAL-005-INST-001-02` referencing `GEP-GOAL-005-INST-013-02` is required before INST-013 may issue GOA-GOAL-005-INST-010-01. The CA Readiness Review of this amendment must determine whether the Founder's recorded session statement is sufficient for CA to certify acknowledgement under GEOM R2-04 (CA certification when Registrant present but has not produced a formally structured record), or whether the Founder must produce the explicit ACK record.

### Preserved Plan Constraints (Unchanged from GEP-GOAL-005-INST-013-01)

- D-01 through D-07 contribution records, authorization records, and acceptance records are final and unaffected
- INST-013 may not issue a GO Authorization to itself (GEOM G-13 / R2-11)
- Rule 6 (Phased Authorization Rules): any Institution beyond INST-010 not yet listed requires a further Collaboration Amendment and updated Execution Plan
- R2-02: Phase 8 (INST-010) is gated on D-07 ratification — satisfied (R-046 RATIFY)
- R2-03: Both CA Readiness Review of this amendment AND a valid Registrant Acknowledgement Record are required before GOA-GOAL-005-INST-010-01 is constitutionally valid
- G-5 Goal Journey rules: INST-010 must publish evidence before releasing the Goal; INST-004 must independently review; INST-010 may not declare its own contribution complete

### Question for Independent CA Readiness Review

The following exact question must be decided by a fresh Constitutional Analyst (one who has not contributed to GOAL-005 in any prior capacity) before INST-013 may issue GOA-GOAL-005-INST-010-01:

> Under GEOM R2-03, does the Founder's in-session statement "I do authorize WC-034 F2 implementation for the current session" (Yogesh Khandge, 2026-08-09) constitute a sufficient Registrant Acknowledgement of GEP-GOAL-005-INST-013-02 (Amendment 1 to the GOAL-005 Execution Plan), given that the statement was made before this amendment document was produced and does not reference it by record ID? If this statement is not constitutionally sufficient as a formal Acknowledgement Record, state precisely what additional action the Founder must take before INST-013 may issue GOA-GOAL-005-INST-010-01. If CA determines that GEOM R2-04 applies — that is, that the success criteria for this amendment are unambiguous and unchanged from Registration, and that the Founder's explicit in-session authorization constitutes effective acknowledgement despite the absence of a formally structured ACK record — state the constitutional basis for that determination and confirm whether CA certification alone is sufficient to satisfy R2-03 condition (2).
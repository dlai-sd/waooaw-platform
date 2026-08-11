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

### Phase 8 Authorization Record — GOA-GOAL-005-INST-010-01 (ISSUED)

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
| `issued_at` | 2026-08-09T20:30:01+00:00 |

Both R2-03 conditions are met: (1) CR-GOAL-005-INST-002-03 / R-057 PASSED CA Readiness Review; (2) ACK-GOAL-005-INST-001-02 recorded (produced_at 2026-08-09T20:30:00+00:00). This record is constitutionally valid under GEOM G-7 and GEOM §G-4 R2-05. INST-010 must record Goal Acceptance Timestamp after 2026-08-09T20:30:01+00:00.

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
## CA Readiness Review Record — Amendment 1 (R2-03 Condition 1)

| Attestation field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-002-03 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-09 |
| `references` | R-057 |
| R2-03 condition 1 | **PASSED** — plan is constitutionally ready; see R-057 for full analysis |
| R2-03 condition 2 | **NOT MET** — ACK-GOAL-005-INST-001-02 required; Registrant is present and reachable; R2-04 does not apply |
| **Decision** | **APPROVED WITH CONDITIONS** |

Produced by a fresh independent INST-002 instance that has not contributed to GOAL-005 in any prior capacity (separate from the instance that produced CR-GOAL-005-INST-002-02 / D-07 evidence package).

INST-013 may NOT issue GOA-GOAL-005-INST-010-01 until the Registrant records ACK-GOAL-005-INST-001-02 by providing:

> **"I acknowledge GEP-GOAL-005-INST-013-02 and authorize INST-013 to issue GOA-GOAL-005-INST-010-01."**

---

## Registrant Acknowledgement Record — Amendment 1

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-02 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-09T20:30:00+00:00 |
| Acknowledged plan | GEP-GOAL-005-INST-013-02 |
| Registrant | Yogesh Khandge / Founder |
| Decision | ACKNOWLEDGED — INST-013 authorized to issue GOA-GOAL-005-INST-010-01 |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-02 and authorize INST-013 to issue GOA-GOAL-005-INST-010-01." |

This record supersedes ACK-GOAL-005-INST-001-01 with respect to INST-010 implementation authorization and satisfies GEOM R2-03 condition (2). ACK-GOAL-005-INST-001-01 remains valid for D-01 through D-07 and is not modified.

---

## Phase 8 Acceptance Record — ACC-GOAL-005-INST-010-01

| Field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-010-01 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-09T20:45:00+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-010-01 |
| `acceptance_timestamp` | 2026-08-09T20:45:00+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | WC-034 F2 Identity and Registration implementation only — Google and email-fallback provider paths; Facebook and Apple activation remain BLOCKED by G-F2-03/FA-002/FA-018 and G-F2-14/FA-019 respectively |
| Excluded authority | No deployment (G-F2-13); no F3–F8 implementation; no provider activation beyond Google and email-fallback; no architectural decisions; no self-approval of contribution completeness |

INST-010 accepts this authorization under the Phase 8 scope and Evidence Specification defined in GEP-GOAL-005-INST-013-02 (Amendment 1). Contribution completeness requires independent INST-004 review per G-5.

---

## Amendment 2 — INST-010 WC-034 F3 Conversation Core Contribution

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-03 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-10T01:44:29+00:00 |
| Amends | GEP-GOAL-005-INST-013-02 |
| Amendment basis | FA-031 and FA-034 remain in effect; PR #249 merged as `cc80e812`; R-059 APPROVED and PR #250 merged as `5010753`; G-F3-01 through G-F3-07 are closed; GEOM G-7 requires a new GO Authorization before INST-010 may act |
| Status | CA READINESS APPROVED WITH CONDITIONS — Registrant acknowledgement required before GOA issuance |

### What This Amendment Changes

This amendment adds WC-034 F3 Conversation Core as a parallel Phase 8 contribution. The approved decomposition permits F2 and F3 service-contract work to proceed independently after F1, while preventing authenticated end-to-end conversation closure until both pass. F2 merged before this amendment was produced; no F2 scope is reopened.

The amendment does not treat architecture approval as implementation authority. It creates the GEOM evidence specification required for INST-010 implementation and reserves `GOA-GOAL-005-INST-010-02`. Under GEOM R2-03, that authorization remains constitutionally void until both CA readiness review and Registrant acknowledgement of this specific amendment are recorded.

### Phase 8B — WC-034 F3 Conversation Core Implementation

| Field | Value |
|---|---|
| Deliverable | WC-034 F3 Conversation Core implementation |
| Dependency | F1 complete; FA-031/FA-034 in effect; G-F3-01 through G-F3-07 closed by R-059; PR #250 merged as `5010753` |
| Participating Institutions | INST-010 primary implementation; INST-004 independent implementation review in a separate context |
| Participation Window | 5 constitutional sessions after valid acceptance |
| Gate to completion | All mapped F3 acceptance evidence passes; affected-service line coverage is at least 90%; independent INST-004 review is APPROVED; implementation PR is ready for Founder review |
| Dispatch path | Autonomous Sprint Pipeline only; this Copilot session may govern and dispatch but may not author production implementation |

### Evidence Specification — INST-010 WC-034 F3

| Field | Value |
|---|---|
| Record types required | Implementation Contribution Record; Docker test evidence; coverage report; generated-client evidence; browser acceptance evidence; INST-004 independent review Contribution Record |
| Participation Window | 5 constitutional sessions after valid acceptance |
| Independence constraint | INST-004 reviews independently under C-065; INST-010 may not approve its own contribution or declare Goal completion |

**Minimum contribution content:**

1. Implement the BP OpenAPI 1.2.0 conversation timeline, send, retry, read-position, cancellation, and resumable SSE operations as the sole ordinary public ingress.
2. Implement the PR OpenAPI 1.1.0 internal execution, cancellation, and resumable SSE operations with BP service authentication only.
3. Preserve Message V1, Action/Plan/Deliverable/Decision Card V1, BP Event V1, and PR Event V1 compatibility rules.
4. Enforce request-hash-bound UUID idempotency, replay, divergent-conflict, unknown-outcome, cursor, and client-message reconciliation semantics.
5. Derive tenant authority only from validated JWT or service assertions; preserve normalized inaccessible-resource behavior and privacy-safe telemetry.
6. Preserve independent delivery, processing, Stop, and CE-confirmed Evidence First states; reconnect must not release Stop or fabricate success.
7. Implement the canonical RFC 9457 public and internal error contracts without dependency-detail leakage.
8. Generate the public F3 TypeScript client from the canonical BP OpenAPI with OpenAPI Generator 7.17.0 or a proven compatible version; strict TypeScript must pass without manual generated-code patches.
9. Implement the approved F3 conversation UX without `@ai-sdk/react`, direct browser-to-PR access, or direct browser-to-model-provider access.
10. Pass UX-CONV-01 through UX-CONV-07, CCT-UX-HO-01 through CCT-UX-HO-03, CCT-UX-EF-01 and CCT-UX-EF-02, UX-PWA-03, UX-RES-01, and their mapped contract, accessibility, privacy, and tenant checks.
11. Run tests in the repository Docker test runner and demonstrate at least 90% line coverage for every affected service and changed interactive web surface.
12. Publish implementation evidence before independent INST-004 review and prepare, but do not merge, the implementation PR for Founder review.

### Explicit Exclusions

| Excluded item | Boundary preserved |
|---|---|
| Attachments and voice | Not part of the approved F3 contract |
| F4 through F8 | No automatic expansion beyond Conversation Core |
| F5 cross-channel checkpoint behavior | WC-060 and F5 gates remain controlling |
| `@ai-sdk/react` | Not an approved F3 dependency |
| Ordinary browser-to-PR or model-provider traffic | BP remains the sole public conversation ingress |
| Provider activation and deployment | G-F3-09 remains blocked pending separate Founder action |
| Self-review or self-merge | C-065 independence and Founder merge boundary remain mandatory |

### Reserved Authorization — NOT ISSUED

`GOA-GOAL-005-INST-010-02` is reserved for the scope above. It may be issued only after:

1. CA Readiness Review of GEP-GOAL-005-INST-013-03 is recorded as APPROVED or APPROVED WITH CONDITIONS that are satisfied; and
2. `ACK-GOAL-005-INST-001-03` records Registrant acknowledgement of GEP-GOAL-005-INST-013-03.

Required Registrant statement:

> "I acknowledge GEP-GOAL-005-INST-013-03 and authorize INST-013 to issue GOA-GOAL-005-INST-010-02."

After valid issuance, INST-010 must record `ACC-GOAL-005-INST-010-02` with an acceptance timestamp later than the GOA `issued_at`. No implementation task may be queued or dispatched before that acceptance record exists.

### Operational Dispatch Condition

The repository `SPRINT_STATE_MACHINE` reports `autonomous_halt: false`, `platform_phase: IMPLEMENTATION`, and WC-043 DONE. GitHub Sprint Dashboard Issue #7 is closed and retains stale `sprint:halted` state from 2026-08-06. Before F3 dispatch, INST-013 must reconcile the dashboard and pipeline entry state without changing F3 scope or bypassing pre-sprint simulation.

---

## Registrant Acknowledgement Record — Amendment 2

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-03 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-10T09:02:35+05:30 |
| Acknowledged plan | GEP-GOAL-005-INST-013-03 |
| Registrant | Yogesh Khandge / Founder |
| Decision | ACKNOWLEDGED — INST-013 authorized to issue GOA-GOAL-005-INST-010-02 |
| Evidence | Founder approved and merged PR #251 as `da6824c`; the PR's sole purpose and Authorization Boundary explicitly identify GEP-GOAL-005-INST-013-03, the required acknowledgement, and GOA-GOAL-005-INST-010-02 |
| Post-merge direction | "ok pr 251 is merged. please keep focus and decipline to follow constitution and progress" |

The authenticated Founder approval and merge of the exact Execution Plan, followed by an explicit direction to progress constitutionally, records Registrant acknowledgement of GEP-GOAL-005-INST-013-03. This satisfies GEOM R2-03 condition 2 and R-060 condition 1 without expanding the approved contribution scope.

---

## Phase 8B Authorization Record — GOA-GOAL-005-INST-010-02 (ISSUED)

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-02 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-010-02 |
| Authorized Institution | INST-010 — Platform IT Expert |
| Contribution scope | WC-034 F3 Conversation Core implementation per GEP-GOAL-005-INST-013-03 Evidence Specification |
| Participation Window | 5 constitutional sessions after valid acceptance |
| Collaboration type | Primary — Phase 8B Amendment 2 |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T03:35:03+00:00 |

Both GEOM R2-03 conditions are met: CR-GOAL-005-INST-002-04 / R-060 passed CA Readiness Review, and ACK-GOAL-005-INST-001-03 records Registrant acknowledgement. This authorization excludes attachments, voice, F4-F8, `@ai-sdk/react`, direct browser-to-PR or provider traffic, provider activation, deployment, self-review, and self-merge.

---

## Phase 8B Acceptance Record — ACC-GOAL-005-INST-010-02

| Field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-010-02 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-10T03:35:04+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-010-02 |
| `acceptance_timestamp` | 2026-08-10T03:35:04+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | WC-034 F3 Conversation Core implementation only, through the Autonomous Sprint Pipeline |
| Excluded authority | Attachments, voice, F4-F8, `@ai-sdk/react`, direct browser-to-PR/provider traffic, provider activation, deployment, architectural changes, self-review, and self-merge |

INST-010 accepts the GEP-GOAL-005-INST-013-03 contribution one second after GOA issuance, satisfying GEOM G-03 and R2-12. The five-session Participation Window begins at this acceptance timestamp. Execution remains pending a valid WC-034 F3 pipeline entry, C-086 pre-sprint simulation, and fail-fast preflight.

---

## Amendment 3 — WC-034 F4 Architecture And Owner-Contract Closure

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-04 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-10T13:14:51+00:00 |
| Status | PROPOSED — CA Readiness Review and Registrant acknowledgement required before any Amendment 3 GOA is issued |

### Amendment Purpose

This amendment adds one bounded architecture/dependency-closure phase for WC-034 F4 Relationship Workspace. It maps the logical Business Platform, WAOOAW Billing Engine, and selected professional/domain owner responsibilities to registered Institutions, selects Digital Marketing Agent (DMA) as the first-release profession, and defines the evidence needed to close G-F4-01 through G-F4-11.

This amendment issues no GO Authorization. It does not authorize implementation, source or test changes, OpenAPI modification, generated-client production, provider activation, deployment, F5-F8, or INST-010 participation. G-F4-12 and G-F4-13 remain blocked. A later Collaboration Amendment is required before any F4 implementation GOA may be reserved or issued.

### Non-Retroactivity And Candidate Inputs

The F4 documents prepared before Amendment 3 authorization are candidate inputs, not retroactively valid Contribution Records. After valid GOA issuance and acceptance, each Institution must independently re-open, verify, amend if needed, and attest its own candidate artifact within its Decision Space. Re-attestation may adopt an unchanged artifact only after the Institution verifies that it satisfies this amendment's Evidence Specification. No Institution may accept another Institution's draft as its own contribution.

Candidate inputs are:

- `goals/GOAL-005-f4-business-contribution.md`;
- `architecture/reference/components/relationship-workspace.md`;
- `architecture/reference/components/relationship-workspace-solution-contract.md`;
- `architecture/reference/data/relationship-workspace-data-contract.md`;
- `architecture/reference/security/relationship-workspace-security-contract.md`; and
- `architecture/reference/product/f4-relationship-workspace-release-contract.md`.

### Phase 8C — F4 Architecture And Dependency Closure

| Order | Contribution | Dependency | Participating Institution | Gate evidence |
|---:|---|---|---|---|
| 1 | Business meanings and first-release product composition | Valid Amendment 3 GOAs and acceptances | INST-003 business semantics; INST-011 product composition and DMA selection | G-F4-01 and G-F4-06 contribution records |
| 2 | Enterprise, data, and security architecture | Order 1 accepted | INST-004 enterprise ownership; INST-006 data semantics; INST-007 security assurance | G-F4-02, G-F4-04, and G-F4-05 contribution records |
| 3 | Solution and logical component-owner contracts | Orders 1-2 accepted | INST-005 Solution Architect acting within component/API/integration Decision Space | G-F4-03, BP owner G-F4-07, and WBE owner G-F4-08 contribution records |
| 4 | DMA domain outcome contract | DMA selected by Registrant; Orders 1-3 accepted | INST-011 incorporates attested DMA domain-authority evidence; INST-003 validates business-outcome semantics; INST-005 validates adapter conformance | G-F4-09 DMA outcome/evidence/attribution/attention compatibility package |
| 5 | Canonical contract compatibility | Orders 1-4 accepted | INST-005 with logical BP contract ownership | G-F4-10 OpenAPI and generated-client compatibility specification; no canonical OpenAPI edit or generated client under this amendment |
| 6 | Constitutional and integrated independent review | Orders 1-5 accepted | INST-002 constitutional review; fresh INST-004 integrated review context that did not author the reviewed contribution | G-F4-11 reviews and unresolved-risk statement |

### Per-Institution Evidence Specifications

| Institution | Amendment 3 Contribution Record | Minimum content | Participation Window | Independence constraint |
|---|---|---|---|---|
| INST-003 Business Architect | F4 business-semantics re-attestation; DMA outcome-semantics validation | Plan, attention, work, results, usage/budget, rights/control meanings; outcome vs technical metric; DMA baseline, measure, attribution, and attention semantics | 2 constitutional sessions after acceptance | May not approve architecture, API contracts, or its own integrated review |
| INST-011 Product Owner | F4 release-composition re-attestation; DMA selection and domain-authority evidence incorporation | Mandatory views/actions, truthful states, deferrals, policy escalations, named DMA authority evidence and provenance | 2 constitutional sessions after acceptance | May not invent DMA professional judgment, architecture, or implementation authority |
| INST-004 Enterprise Architect | F4 ownership re-attestation; fresh integrated review | BP/WBE/CE/PR/web/domain boundaries, no new deployable component, gate integrity, ADR impact, independent package verdict | 2 sessions for ownership plus 1 fresh review session | Review context must not author the INST-005, INST-006, INST-007, or INST-011 contribution it reviews |
| INST-006 Data Architect | F4 data-contract re-attestation | Provenance, versions, freshness, stable sequence, commercial categories, evidence states, correction, minimisation, tenant/relationship isolation | 2 constitutional sessions after acceptance | Must not approve its own contribution or define concrete persistence schema |
| INST-007 Security Architect | F4 security-contract re-attestation | C1-C5 controls, assurance, acknowledgement, authorization, privacy-safe errors, export, browser privacy, service authentication, adversarial acceptance | 2 constitutional sessions after acceptance | Must not approve its own contribution or select unresolved product policy |
| INST-005 Solution Architect | F4 solution re-attestation; BP owner contract; WBE owner contract; DMA adapter conformance; G-F4-10 compatibility specification | Public/internal contract families, generated-client boundary, BP governance ownership, WBE commercial ownership, owner reconciliation, DMA adapter compatibility, deterministic future OpenAPI/generator evidence requirements | 3 constitutional sessions after acceptance | May not implement, edit canonical OpenAPI, generate production clients, or independently approve its own package |
| INST-002 Constitutional Analyst | Amendment 3 readiness review; final F4 architecture constitutional review | GOA validity, rights, Human Override, Evidence First, tenant isolation, traceability, Decision Space compliance, unresolved policy and implementation boundary | 1 session per review | Does not replace fresh INST-004 technical integration review or Registrant acknowledgement |

### DMA Domain Authority Rule

DMA is the sole first-release profession selected for G-F4-09. A named DMA domain authority supplies the F4-specific outcome vocabulary, baselines, measures, evidence sources, attribution limits, uncertainty, review cadence, and material attention candidates. Because a domain authority is not a registered Institution, INST-011 incorporates and attests that evidence with explicit provenance; INST-003 validates business semantics; INST-005 validates generic adapter conformance. Generic adapter acceptance alone cannot close G-F4-09.

For WC-034 F4, Yogesh Khandge is the named DMA domain authority. The Founder direction recorded on 2026-08-10 is: "Yogesh will do this. Sujay will come in picture once waooaw is operational." Existing approved DMA knowledge and an F4-specific institutional professional synthesis may be presented to Yogesh for governance and review; neither the synthesis nor prior DMA material may be represented as direct Yogesh testimony. Sujay has no current F4 contribution, review, approval, or availability dependency and enters only through a separately authorized operational-stage process after WAOOAW is operational.

No other profession enters F4 under this amendment. No DMA-specific field or rule may enter the generic Relationship Workspace contract.

### Gate And Authorization Rules

1. Amendment 3 GOAs may be issued only after CA Readiness Review is APPROVED or APPROVED WITH CONDITIONS that are satisfied and the Registrant acknowledges `GEP-GOAL-005-INST-013-04`.
2. Acceptance timestamps must be later than their matching GOA issuance timestamps. Before any Order N+1 GOA is issued, every required Order N Contribution Record must be published to the Goal Register; an acceptance timestamp alone does not complete an order.
3. Candidate inputs do not close gates until their owning Institution publishes a valid post-acceptance Contribution Record.
4. G-F4-07 and G-F4-08 are authored by INST-005 as logical component-owner contracts and independently reviewed by fresh INST-004 context.
5. G-F4-09 closes only with the DMA-specific evidence chain defined above.
6. G-F4-10 under this amendment specifies and independently reviews compatibility evidence; canonical OpenAPI changes and generated production clients remain implementation work under a later authorization.
7. G-F4-11 requires a fresh INST-002 constitutional reviewer that did not author the Amendment 3 readiness record or contribute to the reviewed F4 package, plus a fresh INST-004 integrated technical reviewer that did not author the contribution it reviews.
8. Architecture closure does not authorize implementation. G-F4-12 requires a later Execution Plan amendment, CA readiness, Registrant acknowledgement, GOA issuance, and INST-010 acceptance.
9. Deployment remains separately blocked by G-F4-13.

### Required Registrant Acknowledgement

Before any Amendment 3 GOA is issued, the Registrant must record:

> "I acknowledge GEP-GOAL-005-INST-013-04, select Digital Marketing Agent as the WC-034 F4 first-release profession, and authorize INST-013 to issue architecture and owner-contract closure GO Authorizations only. This does not authorize F4 implementation or deployment."

### Explicit Exclusions

- no application code, tests, migrations, build artifacts, canonical OpenAPI edits, or generated production clients;
- no INST-010 implementation contribution or implementation GOA;
- no provider activation or direct browser access to PR, WBE, CE, domain adapters, providers, or ledgers;
- no browser ranking or secondary sorting of Needs your attention;
- no BP recreation of WBE actual, allowance, forecast, threshold, pricing, or commercial truth;
- no new deployable component;
- no F5-F8 scope;
- no deployment, self-review, self-merge, or retrospective authorization.

---

## Registrant Acknowledgement Record — Amendment 3

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-04 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-10T13:25:19+00:00 |
| Acknowledged plan | GEP-GOAL-005-INST-013-04 |
| Registrant | Yogesh Khandge / Founder |
| Decision | ACKNOWLEDGED — architecture and owner-contract closure GO Authorizations only |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-04, select Digital Marketing Agent as the WC-034 F4 first-release profession, and authorize INST-013 to issue architecture and owner-contract closure GO Authorizations only. This does not authorize F4 implementation or deployment." |

R-062 / CR-GOAL-005-INST-002-05 satisfies GEOM R2-03 condition 1. This record satisfies condition 2. Amendment 3 architecture GOAs may now issue in dependency order; implementation and deployment remain unauthorized.

## Amendment 3 Order 1 Authorization Records

### GOA-GOAL-005-INST-003-03

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-003-03 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-003-03 |
| Authorized Institution | INST-003 — Business Architect |
| Contribution scope | Re-open and attest WC-034 F4 business semantics; validate DMA outcome semantics after domain-authority evidence is incorporated |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Architecture approval, API contracts, implementation, canonical OpenAPI changes, generated clients, deployment, F5-F8, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T13:25:20+00:00 |

### GOA-GOAL-005-INST-011-05

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-011-05 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-011-05 |
| Authorized Institution | INST-011 — Product Owner |
| Contribution scope | Re-open and attest WC-034 F4 release composition and DMA first-release selection; identify the named DMA domain-authority evidence required for Order 4 incorporation |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Professional judgment invention, architecture, API contracts, implementation, canonical OpenAPI changes, generated clients, deployment, F5-F8, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T13:25:21+00:00 |

## Amendment 3 Order 1 Acceptance Records

### ACC-GOAL-005-INST-003-03

| Field | Value |
|---|---|
| `institution_id` | INST-003 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-003-03 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-003-03 |
| `acceptance_timestamp` | 2026-08-10T13:25:22+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | WC-034 F4 business-semantics re-attestation and later DMA semantic validation only |

### ACC-GOAL-005-INST-011-05

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-011-05 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-011-05 |
| `acceptance_timestamp` | 2026-08-10T13:25:23+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | WC-034 F4 release-composition/DMA-selection re-attestation and named domain-authority evidence requirement only |

## Amendment 3 Order 2 Authorization Records

### GOA-GOAL-005-INST-004-07

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-07 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-004-07 |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | Re-open and attest WC-034 F4 enterprise ownership, service boundaries, domain-adapter placement, gate integrity, and ADR impact |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Product prioritization, concrete API contracts, implementation, canonical OpenAPI changes, generated clients, deployment, F5-F8, integrated review in the same authoring context, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T13:33:43+00:00 |

### GOA-GOAL-005-INST-006-03

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-006-03 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-006-03 |
| Authorized Institution | INST-006 — Data Architect |
| Contribution scope | Re-open and attest WC-034 F4 canonical data semantics, provenance, ordering, commercial categories, evidence states, correction, minimisation, and isolation |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Concrete persistence schema, migrations, API contracts, implementation, canonical OpenAPI changes, generated clients, deployment, F5-F8, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T13:33:44+00:00 |

### GOA-GOAL-005-INST-007-03

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-007-03 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-007-03 |
| Authorized Institution | INST-007 — Security Architect |
| Contribution scope | Re-open and attest WC-034 F4 security assurance, authorization, acknowledgement, privacy, export, service-authentication, replay, and adversarial-acceptance controls |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Product policy selection, API contracts, implementation, canonical OpenAPI changes, generated clients, deployment, F5-F8, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T13:33:45+00:00 |

## Amendment 3 Order 2 Acceptance Records

### ACC-GOAL-005-INST-004-07

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-07 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-004-07 |
| `acceptance_timestamp` | 2026-08-10T13:33:46+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 enterprise-ownership re-attestation only; later integrated review requires a fresh context |

### ACC-GOAL-005-INST-006-03

| Field | Value |
|---|---|
| `institution_id` | INST-006 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-006-03 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-006-03 |
| `acceptance_timestamp` | 2026-08-10T13:33:47+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 data-contract re-attestation only |

### ACC-GOAL-005-INST-007-03

| Field | Value |
|---|---|
| `institution_id` | INST-007 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-007-03 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-007-03 |
| `acceptance_timestamp` | 2026-08-10T13:33:48+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 security-contract re-attestation only |

## Amendment 3 Order 3 Authorization Record

### GOA-GOAL-005-INST-005-03

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-03 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-005-03 |
| Authorized Institution | INST-005 — Solution Architect |
| Contribution scope | Re-open and attest the F4 solution contract; author and attest logical BP and WBE component-owner contracts for G-F4-03, G-F4-07, and G-F4-08 |
| Evidence required | Public/internal contract families, BP relationship-governance ownership, WBE commercial-truth ownership, versions, freshness, idempotency, reconciliation, failure semantics, service boundaries, owner acceptance, and future compatibility evidence specification |
| Participation Window | 3 constitutional sessions after valid acceptance |
| Excluded authority | DMA domain evidence, canonical OpenAPI edits, generated production clients, source, tests, migrations, implementation, deployment, F5-F8, integrated review, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T13:41:00+00:00 |

## Amendment 3 Order 3 Acceptance Record

### ACC-GOAL-005-INST-005-03

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-005-03 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-005-03 |
| `acceptance_timestamp` | 2026-08-10T13:41:01+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 solution re-attestation and logical BP/WBE owner-contract records only |

## Amendment 3 Order 4 Authorization Records

### GOA-GOAL-005-INST-011-06

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-011-06 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-011-06 |
| Authorized Institution | INST-011 — Product Owner |
| Contribution scope | Incorporate and attest F4-specific DMA domain-authority evidence governed by Yogesh Khandge; preserve explicit source provenance and prepare the Product contribution to G-F4-09 |
| Evidence required | DMA outcome vocabulary, baselines, measures, evidence sources, attribution limits, uncertainty, review cadence, material attention candidates, authority provenance, and explicit distinction between synthesis and direct authority testimony |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Inventing DMA professional judgment, attributing synthesis to Yogesh, any Sujay dependency, generic architecture changes, OpenAPI edits, generated clients, source, tests, implementation, deployment, F5-F8, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T14:00:24+00:00 |

### GOA-GOAL-005-INST-003-04

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-003-04 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-003-04 |
| Authorized Institution | INST-003 — Business Architect |
| Contribution scope | Validate the incorporated F4 DMA evidence as customer-outcome semantics for G-F4-09 after the INST-011 Contribution Record is published |
| Evidence required | Outcome versus technical-metric distinction, baseline and measure fitness, attribution boundary, uncertainty, review cadence, attention materiality, and compatibility with the generic F4 business semantics |
| Participation Window | 1 constitutional session after the required INST-011 Contribution Record is published |
| Excluded authority | Domain-authority impersonation, Product ownership, API or adapter design, OpenAPI edits, source, tests, implementation, deployment, F5-F8, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T14:00:25+00:00 |

### GOA-GOAL-005-INST-005-04

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-04 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-005-04 |
| Authorized Institution | INST-005 — Solution Architect |
| Contribution scope | Validate the published F4 DMA evidence and business-semantics records against the generic RelationshipOutcomeAdapter contract for G-F4-09 |
| Evidence required | Adapter version compatibility, relationship/goal binding, provenance, evidence-reference form, attribution and uncertainty fields, attention-candidate boundaries, and proof that DMA semantics do not enter the generic workspace contract |
| Participation Window | 1 constitutional session after the required INST-003 Contribution Record is published |
| Excluded authority | Altering DMA professional judgment, canonical OpenAPI edits, generated production clients, source, tests, migrations, implementation, deployment, F5-F8, integrated review, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T14:00:26+00:00 |

## Amendment 3 Order 4 Acceptance Records

### ACC-GOAL-005-INST-011-06

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-011-06 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-011-06 |
| `acceptance_timestamp` | 2026-08-10T14:00:27+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 DMA domain-evidence incorporation and provenance attestation only; Yogesh is current authority and Sujay is deferred until WAOOAW is operational |

### ACC-GOAL-005-INST-003-04

| Field | Value |
|---|---|
| `institution_id` | INST-003 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-003-04 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-003-04 |
| `acceptance_timestamp` | 2026-08-10T14:00:28+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 DMA business-outcome semantic validation after publication of the INST-011 record only |

### ACC-GOAL-005-INST-005-04

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-005-04 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-005-04 |
| `acceptance_timestamp` | 2026-08-10T14:00:29+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | F4 DMA adapter-conformance validation after publication of the INST-003 record only |

## Amendment 3 Order 5 Authorization Record

### GOA-GOAL-005-INST-005-05

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-05 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-005-05 |
| Authorized Institution | INST-005 — Solution Architect |
| Contribution scope | Define and attest the G-F4-10 canonical BP OpenAPI and generated-client compatibility evidence specification for the approved F4 package |
| Evidence required | Required future OpenAPI paths/schemas inventory, reference and operation-ID validation, backward-compatible versioning, pinned deterministic generation, two-run hash comparison, strict TypeScript compile, forbidden-surface scan, fixture/contract outcomes, and acceptance trace |
| Participation Window | 1 constitutional session after valid acceptance |
| Excluded authority | Canonical OpenAPI edits, generated production clients, generator execution claimed as implementation evidence, source, tests, migrations, build artifacts, implementation, provider activation, deployment, F5-F8, integrated review, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T14:24:53+00:00 |

## Amendment 3 Order 5 Acceptance Record

### ACC-GOAL-005-INST-005-05

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-005-05 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-005-05 |
| `acceptance_timestamp` | 2026-08-10T14:24:54+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | G-F4-10 compatibility evidence specification only; no canonical contract edit, generation, implementation, or deployment |

## Amendment 3 Order 6 Authorization Records

### GOA-GOAL-005-INST-002-03

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-002-03 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-002-03 |
| Authorized Institution | INST-002 — Constitutional Analyst |
| Contribution scope | Independently review the complete WC-034 F4 Orders 1-5 architecture package for constitutional readiness and unresolved risk under G-F4-11 |
| Evidence required | GOA and temporal trace, Decision Space compliance, Human Override, Evidence First, tenant isolation, privacy, rights, authority/scope/lifecycle distinctions, DMA provenance, gate integrity, unresolved policies, and implementation/deployment boundary |
| Participation Window | 1 constitutional session after valid acceptance |
| Independence constraint | Must use a fresh context that did not author R-062 or contribute to Orders 1-5; may identify findings but may not repair the package it reviews |
| Excluded authority | Architecture authorship, canonical OpenAPI edits, generated clients, source, tests, implementation, deployment, F5-F8, GOA issuance, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T14:38:59+00:00 |

### GOA-GOAL-005-INST-004-08

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-08 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-004-08 |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | Independently review the integrated WC-034 F4 Orders 1-5 architecture package for technical coherence, ownership, dependency closure, and ADR impact under G-F4-11 |
| Evidence required | BP/WBE/CE/PR/web/domain authority consistency, public/private boundaries, owner contracts, DMA adapter neutrality, compatibility specification, gate trace, contradiction scan, ADR impact, unresolved risks, and implementation/deployment boundary |
| Participation Window | 1 constitutional session after valid acceptance |
| Independence constraint | Must use a fresh context that did not author CR-GOAL-005-INST-004-08 or any reviewed INST-005/006/007/011 contribution; may identify findings but may not repair the package it reviews |
| Excluded authority | Reviewed-package authorship, product or policy selection, canonical OpenAPI edits, generated clients, source, tests, implementation, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T14:39:00+00:00 |

## Amendment 3 Order 6 Acceptance Records

### ACC-GOAL-005-INST-002-03

| Field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-002-03 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-002-03 |
| `acceptance_timestamp` | 2026-08-10T14:39:01+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | Fresh independent F4 constitutional review only; no repair, implementation authorization, or deployment authority |

### ACC-GOAL-005-INST-004-08

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-08 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-004-08 |
| `acceptance_timestamp` | 2026-08-10T14:39:02+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | Fresh independent F4 integrated technical review only; no repair, implementation authorization, or deployment authority |

---

## Amendment 4 — WC-034 F4 Workload-Authentication ADR Closure

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-05 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-10T14:54:58+00:00 |
| Status | PROPOSED — CA Readiness Review and exact Registrant acknowledgement required before any Amendment 4 GOA |

### Purpose And Trigger

R-064 / `CR-GOAL-005-INST-004-09` condition EA-F4-01 found that the accepted ADR set does not decide workload identity and mutual authentication for BP-to-WBE, BP-to-PR, and BP-to-professional/domain-adapter traffic. Amendment 3 is complete and cannot be expanded retrospectively. This prospective Collaboration Amendment authorizes only the architecture decision and independent reviews needed to close that condition before any G-F4-12 implementation amendment.

The authorized architecture output is `ADR-046-workload-identity-and-service-authentication.md`. If the architecture process instead proposes amending an existing ADR, INST-013 must first publish a prospective Execution Plan amendment identifying that ADR and obtain fresh CA readiness plus a new exact Registrant acknowledgement. Amendment 4 must not be stretched to authorize another architecture instrument or silently generalize ADR-007 or ADR-014.

### Ordered Contributions

| Order | Contribution | Dependency | Institution | Completion evidence |
|---:|---|---|---|---|
| 1 | Workload-authentication architecture decision | CA readiness, exact Registrant acknowledgement, valid GOA and later acceptance | INST-004 — Enterprise Architect | ADR-046 plus attested Contribution Record and Learning Record |
| 2 | Business-driver and capability review | Order 1 Contribution and Learning Records published | INST-003 — Business Architect | Independent review Contribution Record with explicit decision/conditions plus Learning Record |
| 3 | Constitutional and claim-traceability review | Orders 1-2 Contribution and Learning Records published | Fresh INST-002 — Constitutional Analyst | Independent review Contribution Record with explicit decision/conditions plus Learning Record |
| 4 | ADR acceptance and checkpoint | Both reviews APPROVED and conditions satisfied | INST-013 records closure; ADR status follows accepted review evidence | Accepted ADR status and reconciled PROJECT_STATE checkpoint |

### Architecture Evidence Specification — INST-004

The architecture contribution must decide, for BP-to-WBE, BP-to-PR, and BP-to-professional/domain-adapter traffic:

1. workload identity source and trust root in development, CI, and cloud;
2. mutual authentication protocol and transport protection;
3. intended audience, caller identity, delegated actor/tenant/relationship purpose, operation, and version validation;
4. credential issuance, storage, rotation, revocation, expiry, and compromise response;
5. fail-closed behavior, privacy-safe errors, observability, and Emergency Stop independence;
6. environment parity and explicitly permitted differences without development bypass becoming production behavior;
7. least privilege, confused-deputy resistance, replay/idempotency interaction, and cross-tenant denial;
8. compatibility and migration impact for existing BP, WBE, PR, CE, and domain-adapter contracts; and
9. alternatives, tradeoffs, rejected options, ADR impact, and implementation evidence obligations.

The decision must preserve BP as the sole ordinary public F4 facade, WBE commercial truth, PR execution truth, CE constitutional validation/evidence authority, private domain adapters, and zero browser access to internal services or ledgers.

### Participation Windows And Independence

| Institution | Participation Window | Independence constraint |
|---|---|---|
| INST-004 Enterprise Architect | 2 constitutional sessions after valid acceptance | Authors the architecture decision; may not approve its own ADR or implement it |
| INST-003 Business Architect | 1 constitutional session after its valid acceptance | Reviews business-driver/capability coverage only; may not edit the ADR or approve implementation |
| INST-002 Constitutional Analyst | 1 constitutional session after its valid acceptance | Fresh context distinct from Amendment 4 readiness review; may not edit the ADR or replace INST-003 review |

### Authorization Rules

1. No Amendment 4 GOA may issue until a fresh CA Readiness Review is APPROVED or APPROVED WITH CONDITIONS that are satisfied and the Registrant records the exact acknowledgement below.
2. Every acceptance timestamp must be later than its GOA issuance timestamp.
3. An Order N+1 GOA may issue only after every required Order N Contribution Record is published.
4. The INST-004 author may not review or accept its own ADR.
5. Every Order 1-3 participant must publish a G-10-attested Contribution Record linked to its GOA and Acceptance Record and a Learning Record before evidence validation or closure. Review records must state an explicit decision and exact conditions.
6. ADR status may become Accepted only after both independent reviews approve and every review condition is satisfied.
7. INST-013 closure is mechanical: it may verify published approvals, record ADR status, and update the checkpoint, but may not author, repair, accept, or self-review ADR-046.
8. ADR acceptance closes only EA-F4-01. It does not close executable G-F4-10, resolve F4-POL-01 through F4-POL-06, or authorize G-F4-12 or G-F4-13.
9. A separate later implementation amendment requires fresh CA readiness, a separate exact Registrant acknowledgement, a valid INST-010 GOA, and later acceptance.

### Required Registrant Acknowledgement

> "I acknowledge GEP-GOAL-005-INST-013-05 and authorize INST-013 to issue GO Authorizations only for ADR-046 workload-identity and service-authentication architecture, independent Business and Constitutional reviews, and ADR closure. This does not authorize F4 implementation, OpenAPI changes, generated clients, policy defaults, provider activation, or deployment."

### Explicit Exclusions

- no source, tests, migrations, canonical OpenAPI edits, generated clients, builds, implementation, or deployment;
- no G-F4-10 executable evidence and no G-F4-12 or G-F4-13 authority;
- no resolution or default for F4-POL-01 through F4-POL-06;
- no provider activation, F5-F8, self-review, self-merge, or retrospective authorization;
- no change to BP, WBE, PR, CE, web, or domain ownership beyond the workload-authentication decision; and
- no weakening of Emergency Stop, Evidence First, tenant/relationship isolation, or private-service boundaries.

---

## Registrant Acknowledgement Record — Amendment 4

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-05 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-10T15:10:35+00:00 |
| Acknowledged plan | GEP-GOAL-005-INST-013-05 |
| Registrant | Yogesh Khandge / Founder |
| Decision | ACKNOWLEDGED — ADR-046 architecture, independent reviews, and ADR closure only |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-05 and authorize INST-013 to issue GO Authorizations only for ADR-046 workload-identity and service-authentication architecture, independent Business and Constitutional reviews, and ADR closure. This does not authorize F4 implementation, OpenAPI changes, generated clients, policy defaults, provider activation, or deployment." |

R-065 / `CR-GOAL-005-INST-002-07` satisfies GEOM R2-03 condition 1, with CA-F4-A4-01 through CA-F4-A4-06 binding. This record satisfies condition 2. Amendment 4 GOAs may now issue in dependency order; implementation and deployment remain unauthorized.

## Amendment 4 Order 1 Authorization Record

### GOA-GOAL-005-INST-004-09

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-09 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-004-09 |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | Author ADR-046 workload-identity and service-authentication architecture for BP-to-WBE, BP-to-PR, and BP-to-professional/domain-adapter traffic; publish G-10-attested `CR-GOAL-005-INST-004-10` linked to this GOA and its Acceptance Record plus `LR-GOAL-005-INST-004-06` before evidence validation |
| Evidence specification | Decide every item in the Amendment 4 Architecture Evidence Specification, preserve its ownership boundaries and exact ADR-046 output boundary, and state implementation evidence obligations without producing executable artifacts |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Independence constraint | May author ADR-046 but may not approve or accept its own ADR, perform either independent review, or implement the decision |
| Excluded authority | Existing-ADR amendment, source, tests, migrations, canonical OpenAPI changes, generated clients, builds, implementation, policy defaults, provider activation, deployment, F5-F8, self-review, and self-merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T15:10:36+00:00 |

## Amendment 4 Order 1 Acceptance Record

### ACC-GOAL-005-INST-004-09

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-09 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-004-09 |
| `acceptance_timestamp` | 2026-08-10T15:10:37+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | ADR-046 architecture decision plus attested Contribution and Learning Records only; no review, implementation, policy-default, provider-activation, or deployment authority |

## Amendment 4 Order 2 Authorization Record

### GOA-GOAL-005-INST-003-05

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-003-05 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-003-05 |
| Authorized Institution | INST-003 — Business Architect |
| Contribution scope | Independently review ADR-046 for business-driver, capability, operational-continuity, customer-rights, and ownership-boundary coverage; publish G-10-attested `CR-GOAL-005-INST-003-06` with explicit decision and conditions plus `LR-GOAL-005-INST-003-02` |
| Evidence specification | Verify the workload-authentication decision supports the approved F4 customer relationship capabilities across development, CI, and cloud; preserves BP/WBE/PR/CE/domain ownership, truthful unavailable/blocked behavior, Emergency Stop, business continuity, and customer-rights effects; identify exact business conditions without editing ADR-046 |
| Participation Window | 1 constitutional session after valid acceptance |
| Independence constraint | Review only; may not edit ADR-046, replace the later Constitutional review, accept the ADR, or authorize implementation |
| Excluded authority | Architecture authorship or repair, constitutional review, source, tests, migrations, canonical OpenAPI changes, generated clients, builds, implementation, policy defaults, provider activation, deployment, F5-F8, self-review, and self-merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T15:57:39+00:00 |

## Amendment 4 Order 2 Acceptance Record

### ACC-GOAL-005-INST-003-05

| Field | Value |
|---|---|
| `institution_id` | INST-003 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-003-05 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-003-05 |
| `acceptance_timestamp` | 2026-08-10T15:57:40+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | Independent ADR-046 Business review plus attested Contribution and Learning Records only; no ADR editing, implementation, policy-default, provider-activation, or deployment authority |

## Amendment 4 Order 2 Condition-Repair Authorization Record

### GOA-GOAL-005-INST-004-10

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-10 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-004-10 |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | Repair ADR-046 Sections 7.2 and 10 only to satisfy R-066 Conditions 1 and 2; publish G-10-attested `CR-GOAL-005-INST-004-11` linked to this GOA and its Acceptance Record plus `LR-GOAL-005-INST-004-07` before Order 3 |
| Evidence specification | Add future end-to-end owner-to-customer business-consequence evidence for every enabled BP-to-WBE, BP-to-PR, and BP-to-domain-adapter family; add migration and credential-incident evidence for customer disclosure, support, pending-intent preservation, reconciliation, rights and Stop status, owner-by-owner restoration, and business-state restoration |
| Participation Window | 1 constitutional session after valid acceptance |
| Independence constraint | May repair only the two review-mandated evidence obligations; may not approve or accept ADR-046, alter its authentication mechanism, perform Order 3 review, or implement the decision |
| Excluded authority | New architecture instrument, existing-ADR amendment, mechanism change, source, tests, migrations, canonical OpenAPI changes, generated clients, builds, implementation, policy defaults, provider activation, deployment, F5-F8, self-review, and self-merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T16:11:26+00:00 |

## Amendment 4 Order 2 Condition-Repair Acceptance Record

### ACC-GOAL-005-INST-004-10

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-10 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-004-10 |
| `acceptance_timestamp` | 2026-08-10T16:11:27+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | R-066 Conditions 1 and 2 repair to ADR-046 Sections 7.2 and 10 plus new Contribution and Learning Records only; no mechanism change, review, implementation, policy-default, provider-activation, or deployment authority |

## Amendment 4 Order 3 Authorization Record

### GOA-GOAL-005-INST-002-04

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-002-04 |
| `record_type` | Authorization Record |
| `authorization_id` | GOA-GOAL-005-INST-002-04 |
| Authorized Institution | Fresh INST-002 — Constitutional Analyst |
| Contribution scope | Independently review repaired ADR-046 at commit `2547276` for constitutional and claim traceability; publish G-10-attested `CR-GOAL-005-INST-002-08` with explicit decision and exact conditions plus `LR-GOAL-005-INST-002-02` |
| Evidence specification | Verify R-066 Conditions 1 and 2 are satisfied; trace the mechanism, owner boundaries, delegated context, customer rights, Human Override and Emergency Stop, Evidence First, fail-closed behavior, privacy-safe support, migration/incident reconciliation, environment parity, and future proof obligations to ratified claims and accepted architecture; distinguish authentication from authority, evidence, owner truth, completed work, and business outcome |
| Participation Window | 1 constitutional session after valid acceptance |
| Independence constraint | Fresh context distinct from R-065, R-063, Amendment 4 authoring and repair, and Business review; review only and may not edit ADR-046, repair a condition, accept the ADR, or authorize implementation |
| Excluded authority | Architecture authorship or repair, Business review replacement, ADR acceptance, source, tests, migrations, canonical OpenAPI changes, generated clients, builds, implementation, policy defaults, provider activation, deployment, F5-F8, self-review, and self-merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-10T16:20:02+00:00 |

## Amendment 4 Order 3 Acceptance Record

### ACC-GOAL-005-INST-002-04

| Field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-002-04 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-002-04 |
| `acceptance_timestamp` | 2026-08-10T16:20:03+00:00 |
| Decision | ACCEPTED |
| Contribution scope accepted | Fresh independent Constitutional and claim-traceability review of repaired ADR-046 plus attested Contribution and Learning Records only; no ADR editing, repair, acceptance, implementation, policy-default, provider-activation, or deployment authority |

---

## Amendment 5 — WC-034 F4 Policy Resolution And Implementation

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-06 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-11 |
| Status | PROPOSED — fresh CA Readiness Review, exact Registrant acknowledgement, current-session implementation authorization, valid GOAs, and later acceptances required |

### Purpose And Current Gate State

This prospective amendment adds the smallest dependency-ordered path from the accepted WC-034 F4 architecture to executable F4 evidence. Amendment 3 conditionally approved the integrated architecture and specified future G-F4-10 evidence. Amendment 4 accepted ADR-046 and closed EA-F4-01. The current remaining prerequisites are:

1. `F4-POL-01` through `F4-POL-06` require accountable-owner recommendations and exact Registrant/Founder decisions; until decided, every affected command remains `BLOCKED` or `UNAVAILABLE` under the approved fail-closed behavior.
2. Executable G-F4-10 requires canonical BP OpenAPI bytes, approved internal WBE and PR contracts, registered DMA adapter transport, deterministic generated-client evidence, strict TypeScript, forbidden-surface scans, fixtures, and acceptance traceability.
3. G-F4-12 requires this amendment, fresh CA readiness, exact Registrant acknowledgement, the mandatory current-session implementation authorization, valid per-Institution GOAs, and acceptances later than issuance.
4. G-F4-13 remains separately blocked. No deployment, provider activation, production operation, customer-proof claim, or F5-F8 work is authorized by this amendment.

| Policy | Decision boundary | Recommendation owners before Founder decision |
|---|---|---|
| `F4-POL-01` | Material approval/rejection classes requiring typed acknowledgement | INST-011 product treatment; INST-003 consequence classes; INST-007 assurance floor; INST-005 BP feasibility |
| `F4-POL-02` | Evidence-export self-service by sensitivity, recipient, use, redaction, and completeness | INST-011 customer route; INST-007 export/privacy floor; INST-005 BP Evidence Reader feasibility |
| `F4-POL-03` | Allowance-threshold and budget-ceiling pause, degrade, continue, or paid-addition treatment | INST-003 business consequence; INST-011 product treatment; INST-005 WBE/BP feasibility |
| `F4-POL-04` | Customer self-service authority changes and unrecoverable-work consequences | INST-003 authority consequence; INST-011 customer treatment; INST-007 assurance floor; INST-005 BP/CE feasibility |
| `F4-POL-05` | Pause, resume, renewal, termination, billing/allowance, evidence retention, re-entry, and fresh-assurance treatment | INST-003 lifecycle consequence; INST-011 customer treatment; INST-005 BP/WBE/PR feasibility; INST-007 assurance floor |
| `F4-POL-06` | Permissible customer action during stale, unknown, partial, unavailable, or unresolved owner state | INST-011 degraded-state treatment; INST-003 business consequence; INST-005 owner feasibility; INST-007 fail-closed floor |

### Ordered Contributions And Implementation Slices

| Order | Slice | Direct owner(s) | Dependency gate | Completion evidence |
|---:|---|---|---|---|
| 1 | Policy recommendation package for `F4-POL-01` through `F4-POL-06` | INST-011 Product Owner coordinates customer-language choices; INST-003 Business Architect validates outcome and consequence meaning; INST-005 Solution Architect incorporates BP/WBE owner feasibility; INST-007 Security Architect states assurance, export, degraded-state, and rights floors | Amendment 5 CA readiness, exact Registrant acknowledgement, valid GOAs and acceptances | One option matrix per policy with recommendation, alternatives, customer consequence, owner impact, security/constitutional floor, blocked default, reversibility, and exact Founder decision question; no policy is selected by a contributing Office |
| 2 | Founder policy decisions and owner incorporation | INST-001 Registrant/Founder decides; INST-011 records product policy; INST-005 incorporates owner-contract consequences; INST-007 confirms no security floor is weakened | Order 1 Contribution and Learning Records published | Six prospective policy decision records or an explicit decision to defer a named policy fail-closed; updated owner specifications preserve distinct `BLOCKED`; fresh INST-002 constitutional policy review |
| 3 | Canonical contracts and executable G-F4-10 | INST-005 owns BP public and private owner contracts; logical BP, WBE, PR, CE, and DMA owners attest their boundaries; INST-010 performs deterministic generation and executable compatibility checks only after contract publication | Order 2 complete for enabled command families; deferred policies remain structurally blocked; ADR-046 Accepted; no source implementation yet | Exact fourteen-operation BP OpenAPI inventory; approved WBE `BLOCKED` outcome; BP-only PR and registered DMA adapter contracts; parse/reference/operation-ID validation; two clean generation hashes; strict TypeScript pass; forbidden private-service, ledger, provider, tenant-authority, and ranking surfaces absent; fixture matrix for success, conflict, stale, unavailable, blocked, partial, unknown, CE-unavailable, and unsupported versions |
| 4 | Workload identity and service-authentication foundation | INST-010 implementation; INST-007 security validation; fresh INST-004 architecture conformance review | Order 3 contract versions fixed; ADR-046 identity registry, audiences, route grants, and envelope schema published | ADR-046 Section 10 items 1-6 and 9-12: deterministic dev/CI PKI, exact URI SANs, mTLS-only listeners, signed delegated context, rotation/revocation/compromise behavior, privacy-safe OTel, CE-independent authentication, Emergency Stop independence, environment-parity matrix, and negative identity/audience/route/replay/isolation tests |
| 5 | Owner projections and reconciliation | INST-010 implements WBE, PR, and DMA adapter private contracts; INST-005 validates owner-contract conformance; INST-003 validates business-state consequence preservation | Order 4 service identity available; Order 3 owner contracts approved | WBE commercial projection and commands preserve `BLOCKED`; PR execution projection/control remains private; DMA adapter remains domain-only; owner receipt, idempotency, unknown-outcome reconciliation, freshness, version, cross-relationship denial, and zero false-success tests pass |
| 6 | BP Relationship Workspace aggregate and public facade | INST-010 implementation; INST-005 contract conformance; INST-007 security verification | Orders 3-5 complete for each enabled family | BP composes one relationship-bound projection without recomputing owner truth; exact authoritative attention order; fourteen public operations; typed commands; CE authorization and Evidence First where applicable; privacy-safe RFC 9457; partial/unknown reconciliation; no private browser route; affected policy-deferred commands remain `BLOCKED` |
| 7 | Generated-client web workspace | INST-010 implementation; INST-011 product acceptance; INST-007 accessibility/privacy/security verification | Order 6 public contract and executable G-F4-10 pass | Generated client has no manual patch; Plan, Needs your attention, Work, Results, Usage & budget, and Rights & control preserve authoritative meaning; exact 360px and desktop behavior; keyboard, RTL, reduced motion, PWA privacy, no overflow, no browser ranking, relationship-switch isolation, and persistent independent Emergency Stop pass |
| 8 | Integrated business-operation, migration, and constitutional evidence | INST-010 assembles executable evidence; fresh INST-004 performs integrated technical review; fresh INST-002 performs constitutional review | Orders 1-7 complete; all enabled policy decisions incorporated; all deferred policies remain fail-closed | ADR-046 Sections 10.1 and 10.2 matrices; all F4 acceptance IDs and CCT obligations below pass; affected code is at least 90% line coverage; Docker-only evidence; independent reviews approve; PR complete and unmerged |

Orders are strict. An Order N+1 GOA may issue only after the required Order N Contribution and Learning Records are published. A slice may progress family-by-family only when every dependency for that family passes; a blocked or deferred family remains unavailable and cannot borrow evidence from another family.

### Per-Institution Evidence Specifications

| Institution | Required contribution | Participation Window | Independence constraint |
|---|---|---|---|
| INST-011 | Policy option/recommendation package; final product-policy incorporation; customer-language and release acceptance | 2 sessions per contribution | May recommend but may not make Founder decisions, choose architecture, author security floors, implement, or review its own evidence |
| INST-003 | Business consequence, continuity, rights, and owner-to-customer outcome validation | 1 session per contribution | May not choose architecture, API shape, implementation, or approve its own contribution |
| INST-005 | Canonical BP/WBE/PR/DMA contracts, owner compatibility, policy incorporation, and implementation conformance | 3 sessions for contracts; 1 session per conformance review | May not implement application source or independently approve contracts it authored |
| INST-007 | Security-floor recommendations and ADR-046 implementation/security evidence validation | 2 sessions for recommendations; 1 session per validation | May not choose product/commercial policy, implement, or approve its own authored security contribution |
| INST-010 | Contract generation, implementation slices, Docker evidence, coverage, and review package | 5 sessions after valid implementation acceptance | May not author policy, alter accepted architecture, self-review, self-merge, deploy, activate providers, or enter F5-F8 |
| INST-004 | Fresh architecture conformance and final integrated technical review | 1 session per review | Review contexts may not author or repair the contribution under review |
| INST-002 | Amendment readiness, policy constitutional review, and final constitutional review | 1 session per review | Each review context is fresh from the contribution reviewed and may not repair it or replace Registrant decisions |

Every contributing Institution must publish a G-10-attested Contribution Record and Learning Record linked to its GOA and later Acceptance Record. Records must distinguish specification, fixture, integration, browser, deployment, and customer-proof provenance.

### Mandatory CCT And Quality Obligations

At minimum, the implementation evidence must pass:

1. `UX-CONV-06`, `UX-CONV-07`, `UX-CONV-08`, `UX-SHELL-06`, `CCT-UX-BOUNDARY-01`, `CCT-UX-RIGHTS-01`, and `CCT-UX-EF-01` with the exact accepted F4 meanings.
2. C-001 Human Override and Emergency Stop evidence proving F4 route, credential, WBE, adapter, CE-authentication, and reconciliation failures cannot delay or disable Stop.
3. C-023 Evidence First evidence proving transport success, owner receipt, technical completion, or pending evidence never becomes governed success.
4. C-026 tenant and Employment Relationship isolation across projections, cursors, commands, idempotency, exports, owner routes, adapter contributions, browser state, and support correlation.
5. C-059 traceability from this amendment and policy records through contracts, source annotations, tests, acceptance IDs, and review evidence.
6. C-063 minimisation and privacy scans for logs, metrics, traces, URLs, browser storage, generated clients, errors, exports, certificates, signatures, actor, tenant, relationship, owner, and provider data.
7. C-065 author/reviewer separation and C-076 at least 90% affected-code line coverage.
8. C-080 Docker-only Python and web validation; no host virtual environment or direct host Python test execution.
9. ADR-046 Section 10 obligations in full, including negative identity, audience, route, operation, contract-major, replay, confused-deputy, credential lifecycle, CE-unavailability, shared-F3 compatibility, owner-to-customer outcome, migration, incident, support, and restoration evidence.

### Acceptance Criteria And Gate Closure

G-F4-10 closes only when the canonical contract and complete executable compatibility evidence in Order 3 pass without manual generated-client patches. G-F4-12 closes only when Orders 1-8 are complete, every enabled policy has a valid Founder decision and owner incorporation, deferred policy families remain demonstrably fail-closed, all mandatory CCT and quality obligations pass, and both independent final reviews approve.

Implementation acceptance additionally requires zero BP recomputation of WBE truth, zero browser/private-service or ledger access, zero browser ranking or secondary sorting, zero DMA-specific field in the generic adapter, zero cross-relationship carry-over, zero fabricated success, distinct WBE `BLOCKED`, and unchanged F3 behavior unless separately migrated with the ADR-046 evidence package.

G-F4-13 deployment remains blocked after implementation acceptance. Deployment requires a separate environment-specific release amendment naming rollout, rollback, credential custody, impact windows, customer/support treatment, independent confirmer, and post-deployment evidence.

### Authorization Rules And Mandatory Stops

1. This proposed amendment issues no GOA and authorizes no contribution by itself.
2. No Amendment 5 GOA may issue until a fresh INST-002 CA Readiness Review is APPROVED or all stated conditions are satisfied and the Registrant records the exact acknowledgement below.
3. Policy recommendation GOAs do not authorize policy selection. Only INST-001 may decide `F4-POL-01` through `F4-POL-06`.
4. No implementation, canonical OpenAPI edit, generated production client, source, test, migration, build artifact, or infrastructure artifact may be created until the Founder gives the mandatory current-session implementation authorization in response to the exact implementation-gate question.
5. A current-session implementation authorization does not resolve a policy, authorize deployment, activate a provider, approve a PR, or permit merge.
6. INST-013 may issue GOAs, sequence work, verify records, and mechanically checkpoint; it may not contribute policy recommendations, contracts, architecture, security, implementation, tests, or independent review.
7. Every GOA acceptance timestamp must be later than issuance. No Institution may self-review or merge its own contribution.

### Required Registrant Acknowledgement

Before any Amendment 5 GOA is issued, the Registrant must record:

> "I acknowledge GEP-GOAL-005-INST-013-06 and authorize INST-013 to route WC-034 F4 policy recommendations, Founder decision incorporation, dependency-ordered implementation, and independent review exactly as specified. I understand that F4-POL-01 through F4-POL-06 remain my decisions, current-session implementation authorization remains separately mandatory, and this acknowledgement does not authorize deployment, provider activation, F5-F8, PR merge, or self-review."

### Explicit Exclusions

- no deployment, provider activation, production operation, or customer-proof claim;
- no F5-F8 scope and no unrelated WC-034 component work;
- no weakening or silent extension of ADR-046, ADR-007, ADR-014, Evidence First, Emergency Stop, owner truth, tenant/relationship isolation, or privacy boundaries;
- no policy default inferred by Product, Business, Solution, Security, implementation, or review contexts;
- no direct web access to PR, WBE, CE, adapters, providers, or ledgers;
- no autonomous sprint runner, autonomous-pipeline mode, retrospective authorization, self-review, self-merge, or merge by any AI office.

---

## Amendment 5 Registrant Acknowledgement Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-06 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-11T01:27:33+00:00 |
| Acknowledged plan | GEP-GOAL-005-INST-013-06 |
| Registrant | Yogesh Khandge / Founder |
| Decision | ACKNOWLEDGED — Amendment 5 routing only |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-06 and authorize INST-013 to route WC-034 F4 policy recommendations, Founder decision incorporation, dependency-ordered implementation, and independent review exactly as specified. I understand that F4-POL-01 through F4-POL-06 remain my decisions, current-session implementation authorization remains separately mandatory, and this acknowledgement does not authorize deployment, provider activation, F5-F8, PR merge, or self-review." |

R-068 / `CR-GOAL-005-INST-002-09` satisfies GEOM R2-03 condition 1 subject to CA-F4-A5-01 through CA-F4-A5-06. This exact record satisfies condition 2. FA-036 separately satisfies the current-session implementation gate. Neither record selects a policy or authorizes deployment.

## Amendment 5 Order 1 Authorization Records

### GOA-GOAL-005-INST-011-07

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-011-07 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-011 — Product Owner |
| Contribution scope | Coordinate the customer-language option and recommendation matrix for `F4-POL-01` through `F4-POL-06`; publish `CR-GOAL-005-INST-011-07` and a Learning Record |
| Evidence specification | For each policy: recommendation, alternatives, customer consequence, release effect, blocked default, reversibility, accountable-owner dependencies, and exact Founder question; incorporate but do not override Business, Solution, or Security evidence |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Policy selection, architecture, security-floor authorship, implementation, source, tests, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T01:27:34+00:00 |

### GOA-GOAL-005-INST-003-06

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-003-06 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-003 — Business Architect |
| Contribution scope | Validate business outcomes, consequence classes, continuity, rights effects, and customer harm/tradeoffs for the six policy options; publish `CR-GOAL-005-INST-003-07` and a Learning Record |
| Evidence specification | Exact outcome and consequence analysis for material acknowledgement, export, commercial thresholds, authority, lifecycle, and degraded owner state, including the safe fail-closed baseline |
| Participation Window | 1 constitutional session after valid acceptance |
| Excluded authority | Policy selection, architecture, API design, security mechanisms, implementation, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T01:27:35+00:00 |

### GOA-GOAL-005-INST-005-06

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-06 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-005 — Solution Architect |
| Contribution scope | Assess BP, WBE, PR, CE, evidence-reader, and DMA owner feasibility and contract consequences for each policy option; publish `CR-GOAL-005-INST-005-10` and a Learning Record |
| Evidence specification | Owner and command-family impact, required authoritative inputs, reconciliation behavior, versioning, distinct `BLOCKED`, dependency risk, and smallest implementable option without choosing policy |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Policy selection, implementation, canonical OpenAPI edits, generated clients, source, tests, deployment, F5-F8, integrated review, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T01:27:36+00:00 |

### GOA-GOAL-005-INST-007-06

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-007-06 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-007 — Security Architect |
| Contribution scope | Define non-weakenable assurance, acknowledgement, export, privacy, authority, lifecycle, and degraded-state floors for each policy option; publish `CR-GOAL-005-INST-007-06` and a Learning Record |
| Evidence specification | Required assurance and typed acknowledgement floors, recipient/export protections, stale/unknown/partial constraints, anti-enumeration, minimisation, rights and Stop preservation, and prohibited options |
| Participation Window | 1 constitutional session after valid acceptance |
| Excluded authority | Product or commercial policy selection, architecture beyond security constraints, implementation, source, tests, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T01:27:37+00:00 |

## Amendment 5 Order 1 Acceptance Records

| Acceptance Record | Institution | Authorization | Acceptance timestamp | Decision |
|---|---|---|---|---|
| ACC-GOAL-005-INST-011-07 | INST-011 | GOA-GOAL-005-INST-011-07 | 2026-08-11T01:27:38+00:00 | ACCEPTED — policy recommendation coordination only |
| ACC-GOAL-005-INST-003-06 | INST-003 | GOA-GOAL-005-INST-003-06 | 2026-08-11T01:27:39+00:00 | ACCEPTED — business consequence analysis only |
| ACC-GOAL-005-INST-005-06 | INST-005 | GOA-GOAL-005-INST-005-06 | 2026-08-11T01:27:40+00:00 | ACCEPTED — owner feasibility analysis only |
| ACC-GOAL-005-INST-007-06 | INST-007 | GOA-GOAL-005-INST-007-06 | 2026-08-11T01:27:41+00:00 | ACCEPTED — security-floor analysis only |

## Amendment 5 Founder Policy Decision Records

The Founder selected each option prospectively in the current session after receiving the four-Office Order 1 recommendation package. These decisions choose policy only. They do not choose API shape, security mechanism, persistence, implementation design, deployment, provider activation, F5-F8 scope, PR approval, or merge.

| Record ID | Institution | Policy | Decision | Selected first-release policy | `produced_at` |
|---|---|---|---|---|---|
| FPD-GOAL-005-F4-POL-01 | INST-001 | `F4-POL-01` | Option A | Typed acknowledgement for irreversible loss, cancellation, financial consequence, legal consequence, safety consequence, and deadline consequence classes | 2026-08-11T02:05:11+00:00 |
| FPD-GOAL-005-F4-POL-02 | INST-001 | `F4-POL-02` | Option A | Self-service only for the customer's own authorized evidence view/export routes already within approved sensitivity and recipient boundaries; all other exports use an alternate route | 2026-08-11T02:05:11+00:00 |
| FPD-GOAL-005-F4-POL-03 | INST-001 | `F4-POL-03` | Option B | Continue read-only and non-consequential access while pausing affected consequential work at an allowance threshold or budget ceiling | 2026-08-11T02:05:11+00:00 |
| FPD-GOAL-005-F4-POL-04 | INST-001 | `F4-POL-04` | Option A | Self-service permits protective reduction only; authority grant, expansion, and restoration remain non-self-service | 2026-08-11T02:05:11+00:00 |
| FPD-GOAL-005-F4-POL-05 | INST-001 | `F4-POL-05` | Option B | Emergency Stop remains immediate; selected owner-approved pause/resume paths may be enabled with explicit consequence and re-entry treatment; renewal/termination remain closed | 2026-08-11T02:05:11+00:00 |
| FPD-GOAL-005-F4-POL-06 | INST-001 | `F4-POL-06` | Option A | Permit read-only review of still-authoritative facts; withhold affected consequential commands and success claims while required owner state is unresolved | 2026-08-11T02:05:11+00:00 |

Every selected option remains bound by `CR-GOAL-005-INST-003-07`, `CR-GOAL-005-INST-005-10`, and `CR-GOAL-005-INST-007-06`. An owner must preserve the accepted fail-closed default wherever a selected family lacks complete authoritative inputs or an approved implementation contract.

## Amendment 5 Order 2 Authorization Records

### GOA-GOAL-005-INST-011-08

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-011-08 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-011 — Product Owner |
| Contribution scope | Incorporate `FPD-GOAL-005-F4-POL-01` through `FPD-GOAL-005-F4-POL-06` into the F4 product release contract; publish `CR-GOAL-005-INST-011-08` and a Learning Record |
| Evidence specification | Record the six selected options, customer-visible treatment, enabled versus still-unavailable command families, release composition, exact fail-closed behavior, and dependencies on Solution and Security incorporation without inventing architecture or mechanisms |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Founder decision reinterpretation, architecture, API or schema design, security-floor authorship, implementation, source, tests, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:05:12+00:00 |

### GOA-GOAL-005-INST-005-07

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-07 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-005 — Solution Architect |
| Contribution scope | Incorporate the six Founder decisions into the canonical F4 owner and relationship-workspace specifications; publish `CR-GOAL-005-INST-005-11` and a Learning Record |
| Evidence specification | Map each selected policy to BP, WBE, PR, CE, Evidence Reader, and DMA ownership; preserve distinct `BLOCKED`, authoritative-input, acknowledgement, reconciliation, version, and unavailable-family semantics; identify the exact Order 3 contract work without editing canonical OpenAPI |
| Participation Window | 3 constitutional sessions after valid acceptance |
| Excluded authority | Policy reinterpretation, implementation, canonical OpenAPI edits, generated clients, source, tests, deployment, F5-F8, integrated review, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:05:13+00:00 |

### GOA-GOAL-005-INST-007-07

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-007-07 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-007 — Security Architect |
| Contribution scope | Verify the six selected policies against the accepted F4 security floors and publish `CR-GOAL-005-INST-007-07` plus a Learning Record |
| Evidence specification | For each policy, state PASS or exact blocking condition for acknowledgement, export/privacy, commercial continuation, authority, lifecycle, degraded state, anti-enumeration, minimisation, rights, and Emergency Stop; no mechanism or product-policy invention |
| Participation Window | 1 constitutional session after valid acceptance |
| Excluded authority | Product/commercial policy reinterpretation, non-security architecture, implementation, source, tests, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:05:14+00:00 |

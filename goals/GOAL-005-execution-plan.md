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
| Status | ACTIVE — CA readiness, exact Registrant acknowledgement, current-session implementation authorization, Order 1 recommendations, and Order 2 policy decisions/incorporation are complete; Order 3 may begin under R-069 conditions |

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

## Amendment 5 Order 2 Owner Acceptance Records

| Acceptance Record | Institution | Authorization | Acceptance timestamp | Decision |
|---|---|---|---|---|
| ACC-GOAL-005-INST-011-08 | INST-011 | GOA-GOAL-005-INST-011-08 | 2026-08-11T02:09:53+00:00 | ACCEPTED — Founder-selected policy incorporation into the product release contract only |
| ACC-GOAL-005-INST-005-07 | INST-005 | GOA-GOAL-005-INST-005-07 | 2026-08-11T02:10:17+00:00 | ACCEPTED — Founder-selected policy incorporation into owner and relationship-workspace specifications only |
| ACC-GOAL-005-INST-007-07 | INST-007 | GOA-GOAL-005-INST-007-07 | 2026-08-11T02:08:11+00:00 | ACCEPTED — security-floor verification of the selected policies only |

The resulting records are `CR-GOAL-005-INST-011-08` / `LR-GOAL-005-INST-011-06`, `CR-GOAL-005-INST-005-11` / `LR-GOAL-005-INST-005-02`, and `CR-GOAL-005-INST-007-07` / `LR-GOAL-005-INST-007-02`. Each preserves the exact `A, A, B, A, B, A` decisions and the accepted fail-closed behavior.

## Amendment 5 Order 2 Constitutional Review Authorization Record

### GOA-GOAL-005-INST-002-10

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-002-10 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-002 — Constitutional Analyst |
| Contribution scope | Independently review the six Founder Policy Decision Records and the Product, Solution, and Security Order 2 incorporations; publish `CR-GOAL-005-INST-002-10` and a Learning Record |
| Evidence specification | Decide APPROVED, APPROVED WITH CONDITIONS, or RETURNED; verify exact decision fidelity, Founder Decision Space, Human Override and Emergency Stop, Evidence First, tenant/relationship isolation, minimisation, rights, distinct `BLOCKED`/`UNAVAILABLE`, fail-closed defaults, author/reviewer separation, and whether Order 3 may begin |
| Participation Window | 1 constitutional session after valid acceptance |
| Independence constraint | Fresh review context; may not author, repair, or reinterpret Founder, Product, Solution, or Security records |
| Excluded authority | Policy selection, contribution repair, architecture or API authorship, implementation, source, tests, deployment, F5-F8, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:12:35+00:00 |

## Amendment 5 Order 2 Constitutional Review Acceptance And Decision

| Field | Value |
|---|---|
| Acceptance Record | ACC-GOAL-005-INST-002-10 |
| Institution | INST-002 — Constitutional Analyst |
| Authorization | GOA-GOAL-005-INST-002-10 |
| Acceptance timestamp | 2026-08-11T02:17:49+00:00 |
| Contribution Record | CR-GOAL-005-INST-002-10 |
| Learning Record | LR-GOAL-005-INST-002-03 |
| Review | R-069 — WC-034 F4 Policy Incorporation Constitutional Review |
| Decision | APPROVED WITH CONDITIONS |
| Order 3 gate | MAY BEGIN WITH CONDITIONS |

R-069 conditions bind Order 3: contract work must remain within `CR-GOAL-005-INST-005-11`; the six Founder decisions may not be reinterpreted; distinct `BLOCKED`/`UNAVAILABLE`, fail-closed unresolved-state handling, and Emergency Stop independence must remain explicit; and no implementation, generated-client, deployment, G-F4-12, or G-F4-13 closure may be inferred.

## Amendment 5 Order 3 Canonical Contract Authorization Record

### GOA-GOAL-005-INST-005-08

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-08 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-005 — Solution Architect and logical contract owner |
| Contribution scope | Publish the canonical WC-034 F4 BP public contract and private WBE, PR, CE-coverage, and registered DMA adapter contract surfaces required before executable G-F4-10 validation; publish `CR-GOAL-005-INST-005-12` and `LR-GOAL-005-INST-005-03` |
| BP evidence specification | Update the canonical Business Platform OpenAPI with exactly the fourteen accepted F4 operation IDs, dependency-closed schemas, typed command unions, policy-selected availability, idempotency, expected versions, reconciliation, RFC 9457 errors, security, and no private/browser-forbidden surface |
| Private-owner evidence specification | Publish versioned BP-only WBE and PR projection/command/reconciliation contracts; preserve WBE `BLOCKED`; publish one registered DMA adapter transport for the approved generic three-operation interface without DMA fields in the generic workspace; map every selected consequence to existing CE gRPC coverage and raise a blocker rather than silently invent a CE contract |
| Policy and review constraints | Preserve `A, A, B, A, B, A`, R-069 Conditions 1-3, distinct `BLOCKED`/`UNAVAILABLE`, fail-closed unresolved state, owner truth, Evidence First, tenant/relationship isolation, and independent Emergency Stop |
| Participation Window | 3 constitutional sessions after valid acceptance |
| Excluded authority | Policy reinterpretation, source implementation, migrations, persistence design, generator execution, generated production clients, executable compatibility claims, tests, deployment, provider activation, F5-F8, integrated review, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:21:49+00:00 |

Owner attestations, INST-010 deterministic generation, executable G-F4-10 closure, and Order 4 remain blocked until this Contribution and Learning Record are published and the canonical contract versions are fixed.

## Amendment 5 Order 3 Canonical Contract Acceptance And Publication

| Field | Value |
|---|---|
| Acceptance Record | ACC-GOAL-005-INST-005-08 |
| Institution | INST-005 — Solution Architect and logical contract owner |
| Authorization | GOA-GOAL-005-INST-005-08 |
| Acceptance timestamp | 2026-08-11T02:26:15+00:00 |
| Contribution Record | CR-GOAL-005-INST-005-12 |
| Learning Record | LR-GOAL-005-INST-005-03 |
| Canonical BP | `business-platform.openapi.yaml` 1.3.0 / SHA-256 `357c14bb359d15c6318192e9adf94eac0a4f0537626e9910363539e731d9c22e` |
| Canonical PR | `professional-runtime.openapi.yaml` 1.2.0 / SHA-256 `a1aba55e7612cf0f8d342eab51f662d68127f4dd5aabaaa6695dc4e418a51f46` |
| Canonical WBE | `wbe-relationship-workspace.openapi.yaml` 1.0.0 / SHA-256 `999b6687f7a0e96e6b362ca286805ee4bb44058f0e67e3dad2f928d74d78eaff` |
| Canonical DMA adapter | `dma-relationship-outcome-adapter.openapi.yaml` 1.0.0 / SHA-256 `594524da76b4192493dbaf8ea4515f2d9d5c858dbd896c6020ea055e7230b26b` |
| CE coverage | `relationship-workspace-ce-contract-coverage.md` 1.0.0 / SHA-256 `c11bd9e82680fd8173353ded2e029d1b69a115983cd1b9c160e86adc060e9478` |
| Validation | Docker F4 slice extraction and four-spec YAML, local-reference, operation-ID, and required-inventory validation PASS; existing unrelated BP reference debt remains outside the dependency-closed F4 slice |

This publication fixes the contract bytes for owner attestation. It does not complete owner attestation, run a generator, create a generated client, close executable G-F4-10, authorize source implementation, or advance Order 4.

## Amendment 5 Order 3 Logical Owner Attestation Authorization

### GOA-GOAL-005-INST-005-09

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-09 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-005 — Solution Architect acting as registered logical component/API owner under the Amendment 3 ownership mapping |
| Contribution scope | Attest the fixed BP, WBE, PR, CE-coverage, and DMA adapter canonical boundaries at commit `9b126bd`; publish `CR-GOAL-005-INST-005-13` and `LR-GOAL-005-INST-005-04` |
| Evidence specification | For each owner surface, verify exact artifact hash/version, accepted authority and truth boundary, caller/audience, operation inventory, policy tuple effect, `BLOCKED`/`UNAVAILABLE`, version/reconciliation behavior, Emergency Stop independence, and absence of browser/private-owner transfer |
| Fixed inputs | BP `357c14bb...d9c22e`; PR `a1aba55e...a51f46`; WBE `999b6687...78eaff`; DMA `594524da...0b26b`; CE coverage `c11bd9e8...e9478` |
| Decision rule | ACCEPT each unchanged owner boundary, RETURN the package, or raise a Constitutional Blocker; do not repair or modify canonical artifacts in this attestation slice |
| Participation Window | 1 constitutional session after valid acceptance |
| Excluded authority | Contract edits, policy reinterpretation, generator execution, generated clients, source, tests, migrations, implementation, deployment, provider activation, F5-F8, independent review, self-review, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:36:29+00:00 |

## Amendment 5 Order 3 Logical Owner Attestation Acceptance

| Field | Value |
|---|---|
| Acceptance Record | ACC-GOAL-005-INST-005-09 |
| Institution | INST-005 — Solution Architect / registered logical component owner |
| Authorization | GOA-GOAL-005-INST-005-09 |
| Acceptance timestamp | 2026-08-11T02:41:33+00:00 |
| Contribution Record | CR-GOAL-005-INST-005-13 |
| Learning Record | LR-GOAL-005-INST-005-04 |
| Decision | ACCEPT — BP, PR, WBE, DMA adapter, and CE coverage boundaries accepted 5/5 against fixed hashes |
| Canonical byte state | UNCHANGED — all five externally verifiable hashes match the publication record |

This acceptance satisfies the logical owner-attestation prerequisite only. Executable G-F4-10 still requires a separate INST-010 GOA and acceptance plus deterministic Docker evidence; source implementation and Order 4 remain separate.

## Amendment 5 Order 3 Executable Compatibility Authorization

### GOA-GOAL-005-INST-010-03

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-03 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-010 — Runtime Implementation Professional |
| Contribution scope | Produce executable G-F4-10 compatibility evidence from canonical commit `9b126bd` and owner attestation `CR-GOAL-005-INST-005-13`; publish `CR-GOAL-005-INST-010-03` and `LR-GOAL-005-INST-010-01` |
| Evidence specification | Docker-only parse/reference/security/inventory checks; deterministic dependency-closed F4 slice; exact OpenAPI Generator `7.17.0`; two clean generation runs and hashes; strict TypeScript compile; no-manual-patch proof; forbidden-surface scan; success/conflict/stale/unavailable/blocked/partial/unknown/CE-unavailable/unsupported-version fixtures; acceptance and provenance manifest |
| Fixed inputs | BP 1.3.0 hash `357c14bb...d9c22e`; compatibility specification `CR-GOAL-005-INST-005-09`; owner attestation `CR-GOAL-005-INST-005-13`; R-069 Conditions 1-3 |
| Output boundary | Temporary generated trees and reproducible evidence only; no tracked production client, BP/WBE/PR/CE/DMA service implementation, web feature, persistence, migration, infrastructure, provider activation, or deployment |
| Participation Window | 2 constitutional sessions after valid acceptance |
| Excluded authority | Contract mutation, policy reinterpretation, application feature implementation, Order 4 workload identity, Orders 5-8, F5-F8, deployment, self-review, self-merge, and merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T02:43:06+00:00 |

---

## Amendment 6 — WC-034 F5 / WC-060 Contract Unification

**Status:** REVIEW APPROVED — R-073, R-074, AND R-075; NO IMPLEMENTATION AUTHORITY
**Founder decision:** FA-037
**Purpose:** Remove duplicate omnichannel implementation authority by making WC-060 the sole implementation Work Contract for WC-034 F5 while preserving all existing dependency, constitutional, security, data, evidence, Stop, and review gates.

### Controlling Determination

1. WC-034 F5 remains the customer-facing component and acceptance boundary.
2. WC-060 is its sole implementation Work Contract and owns the complete BP/PR/CE/web continuity implementation and evidence package.
3. WC-060 completion closes F5 only when WC-059 is DONE, explicit current-session implementation authorization exists, all WC-060 tasks and adversarial CCTs pass, mapped F5 UX acceptance passes, proportional F8 evidence passes, and independent INST-007, INST-006, and INST-004 reviews approve the package.
4. No second F5 implementation Work Contract or follow-on implementation pass is created after WC-060.
5. Historical D-04 through D-07 contribution and ratification records remain unchanged; this amendment reconciles future execution authority only.

### Review And Execution Order

| Order | Office | Contribution |
|---|---|---|
| 1 | INST-004 + INST-005 | Confirm architecture and component/API ownership remain complete and non-duplicative |
| 2 | INST-011 | Confirm release composition and proportional F8 acceptance |
| 3 | INST-007 + INST-006 | Confirm no security, replay, privacy, retention, evidence, or Stop gate was weakened |
| 4 | INST-002 | Independently review constitutional traceability, authorization boundaries, and separation of duties |
| 5 | INST-013 | Mechanically record approved readiness and route the existing WC-060 authorization gate |
| 6 | INST-010 | Execute WC-060 only after its prerequisites and explicit Founder implementation authorization pass |

### Independent Review Evidence

| Record | Office | Verdict |
|---|---|---|
| R-073 | INST-004 + INST-011 architecture and product review | APPROVED — complete F5 scope, ownership, acceptance, and proportional F8 coverage with no duplicate contract |
| R-074 | INST-007 + INST-006 security and data review | APPROVED — no security, replay, privacy, retention, evidence, data-isolation, or Stop gate weakened |
| R-075 | INST-002 constitutional review | APPROVED — C-059 traceability, C-065 separation, and all authorization exclusions preserved |

Orders 1 through 5 are complete. Order 6 remains blocked until WC-059 is DONE and the Founder explicitly authorizes WC-060 implementation for the current session.

### Authorization Boundary

This amendment and FA-037 authorize specification, Work Contract, and execution-plan reconciliation only. They do not issue a GO Authorization, satisfy WC-060's explicit current-session implementation authorization, permit source/tests/migrations/generated production clients, activate a provider, deploy, merge, or begin F6-F8 feature implementation.

---

## Amendment 7 — WC-058 Implementation Routing

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-07 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-11 |
| Status | CA READY — R-077 APPROVED; exact Registrant acknowledgement required before GOA issuance |
| Amends | GEP-GOAL-005-INST-013-06 prospectively; Amendment 6 and all prior records remain unchanged |

### Purpose And Entry State

This amendment adds the smallest dependency-ordered execution envelope for WC-058 only. D-07 and R-046 ratified WC-058 as implementation-ready, WC-057 is DONE through R-076 and merged PR #262, and FA-038 records the Founder's exact current-session directive `Authorize implementation of WC-058`. That directive satisfies the separate implementation-consent gate but does not substitute for GEOM R2-03 readiness, acknowledgement, GO Authorization, or Goal Acceptance.

### Phase 9 — WC-058 Discover, Interview, Trial, And Configure

| Field | Value |
|---|---|
| Primary Institution | INST-010 — Platform IT Expert |
| Contribution scope | Implement WC058-01 through WC058-08 exactly as specified in WC-058 across BP, PR, AIR, WBE, web, the ADR-023 WhatsApp boundary, Migration 20, the DMA-owned adapter, and non-DMA conformance fixtures |
| Required inputs | WC-057 DONE; D-06 DMA synthesis and Product Attestation accepted; D-01 through D-07 and R-046 ratified; WC-031/032/033/040/041 DONE; all paths listed in WC-058 Required Inputs present and approved |
| Participation Window | Five constitutional sessions after valid INST-010 acceptance |
| Required implementation evidence | Task-by-task traceability; Docker-only component, integration, security, and CCT results; affected-surface line coverage at least 90%; deterministic Migration 20 evidence; OpenAPI/manifests/state synchronization; S01-S06 simulation; all 19 DMA skills plus three-skill non-DMA conformance |
| Required safety evidence | Fourteen calendar days independent of session count; zero paid-provider calls; zero credentials; zero external publish, spend, message, campaign, or provider mutation; no direct trial-to-active transition; explicit unresolved expiry uncertainty; Evidence First; tenant and relationship isolation; one new decision-relevant question per cycle |
| Independent review | INST-011 Product Owner and INST-003 Business Architect review the completed contribution independently; INST-010 may not review or approve its own work |
| Completion boundary | Prepare an unmerged PR after all tasks, evidence, and independent reviews pass; Founder approval and merge remain separate |

### Evidence Specification

INST-010 must publish an attested Contribution Record and Learning Record linked to the issued GOA and later Acceptance Record. The Contribution Record must identify every changed contract, migration, implementation surface, generated artifact, fixture, CCT, validation command, result, coverage measurement, residual limitation, and provenance class. It must prove that shared BP/PR/AIR/WBE/web logic contains no DMA-specific branch and that DMA expertise remains confined to its domain-owned Professional Evaluation Adapter.

Independent INST-011 and INST-003 review records must verify customer ordering and decision rights; honest trial and inactivity semantics; professional suitability without preferred-customer exclusion; generic platform/domain separation; all-skill demonstration coverage; and preservation of the no-paid-API, no-external-action, no-false-conversion boundary. Review authorization is routed only after the implementation contribution and learning records are published.

### Explicit Exclusions

- WC-059, WC-060, F6-F8 feature implementation, provider activation, provider credentials, account setup, deployment, production operation, and customer-proof claims.
- Real campaigns, publishing, spending, third-party messages, consequential external mutation, contract acceptance, payment, activation, or direct trial-to-active conversion.
- Architecture reinterpretation, weakening any R-046/WC-058 obligation, self-review, self-approval, self-merge, direct push to `main`, or merge authority.

### Reserved Authorization — Not Issued

`GOA-GOAL-005-INST-010-04` is reserved for this contribution and may be issued only after:

1. a fresh INST-002 CA Readiness Review approves GEP-GOAL-005-INST-013-07, with every condition satisfied; and
2. `ACK-GOAL-005-INST-001-07` records the Founder's exact acknowledgement of this amendment.

Required acknowledgement:

> `I acknowledge GEP-GOAL-005-INST-013-07 and authorize INST-013 to issue GOA-GOAL-005-INST-010-04 for WC-058 implementation only. This does not authorize provider activation, WC-059 or WC-060, deployment, merge, or self-review.`

After valid issuance, INST-010 must record `ACC-GOAL-005-INST-010-04` at a timestamp later than the GOA `issued_at`. No implementation task, source change, migration, generated production artifact, or build artifact may begin before that Acceptance Record exists.

### Fresh CA Readiness Decision

R-077 / `CR-GOAL-005-INST-002-11` independently APPROVES Amendment 7 with no conditions. GEOM R2-03 condition 1 is satisfied. Condition 2 remains open: `ACK-GOAL-005-INST-001-07` must contain the exact acknowledgement above before INST-013 may issue GOA-GOAL-005-INST-010-04.

### Registrant Acknowledgement — ACK-GOAL-005-INST-001-07

| Field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-07 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-11T06:54:41Z |
| Acknowledged plan | GEP-GOAL-005-INST-013-07 |
| Decision | ACKNOWLEDGED — INST-013 authorized to issue GOA-GOAL-005-INST-010-04 for WC-058 only |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-07 and authorize INST-013 to issue GOA-GOAL-005-INST-010-04 for WC-058 implementation only. This does not authorize provider activation, WC-059 or WC-060, deployment, merge, or self-review." |

R-077 and this record satisfy both GEOM R2-03 pre-issuance conditions. The acknowledgement does not itself issue a GOA, accept participation for INST-010, or expand FA-038.

### Authorization Record — GOA-GOAL-005-INST-010-04

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-04 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-010 — Platform IT Expert |
| Contribution scope | Implement WC058-01 through WC058-08 exactly within GEP-GOAL-005-INST-013-07 and WC-058; publish an attested Contribution Record and Learning Record before independent review |
| Evidence specification | Task traceability; Docker-only component/integration/security/CCT evidence; affected-surface line coverage at least 90%; exact Migration 20; S01-S06; all 19 DMA skills; three-skill non-DMA fixture; no paid API, credentials, external mutation, false conversion, or destructive expiry |
| Participation Window | Five constitutional sessions after valid acceptance |
| Independence constraint | INST-010 may implement but may not independently review, approve, merge, deploy, or declare Goal completion |
| Excluded authority | Provider activation or credentials; WC-059/WC-060; F6-F8; real campaigns/publish/spend/messages; contract/payment/activation; deployment; production/customer proof; architecture reinterpretation; self-review; merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T06:54:42Z |

### Acceptance Record — ACC-GOAL-005-INST-010-04

| Field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-010-04 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-11T06:54:43Z |
| `authorization_id` | GOA-GOAL-005-INST-010-04 |
| Accepted scope | WC058-01 through WC058-08 implementation and evidence under Amendment 7 only |
| Participation Window | 2026-08-11T06:54:43Z through five constitutional sessions |
| Acceptance boundary | No provider activation, WC-059/WC-060, deployment, merge, self-review, architecture reinterpretation, or production/customer-proof authority |

The Acceptance timestamp is later than the GOA issuance timestamp, satisfying GEOM G-03 and R2-12. WC-058 implementation may begin under FA-038, GEP-07, R-077, ACK-07, GOA-04, and ACC-04.

---

## Amendment 8 — WC-059 Implementation Routing

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-08 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-11 |
| Status | PROPOSED — fresh CA readiness and exact Registrant acknowledgement required before GOA issuance |
| Amends | GEP-GOAL-005-INST-013-07 prospectively; Amendment 7 and all prior records remain unchanged |

### Purpose And Groomed Entry State

This amendment adds the smallest dependency-ordered execution envelope for WC-059 only. D-07 and R-046 ratified WC-059 as implementation-ready, WC-058 is DONE through PR #263 and merge reconciliation PR #264, WC-042/WC-043 payment and reconciliation foundations are DONE, and FA-040 records the Founder's exact current-session directive `Authorize implementation of WC-059`. That directive satisfies the separate implementation-consent gate but does not substitute for GEOM R2-03 readiness, acknowledgement, GO Authorization, or Goal Acceptance.

A fresh read-only grooming audit and INST-004 architecture readiness review found no unresolved owner, ordering, API, security, data, failure, or acceptance decision. Missing Migration 21 tables, canonical endpoints, services, workflow, presentation, and CCTs are the enumerated WC059-01 through WC059-08 implementation scope, not specification gaps. Because `21-conversation-core.sql` already occupies sequence 21, WC059-01 preserves deterministic init ordering as `21b-ae01-contract-activation.sql` without changing the approved Migration 21 blueprint.

### Phase 10 — WC-059 Contract, Payment, And Exactly-Once Activation

| Field | Value |
|---|---|
| Primary Institution | INST-010 — Platform IT Expert |
| Contribution scope | Implement WC059-01 through WC059-08 exactly as specified across BP, WBE, CE, web, PR channel presentation, Migration 21b, WC-042 onboarding payment integration, and durable activation orchestration |
| Required inputs | WC-058 DONE; WC-042/WC-043 DONE; D-03 and D-06 accepted; D-07/R-046 ratified; AEEC-01 through AEEC-15; ADR-022/023/044; all paths listed in WC-059 Required Inputs present and approved |
| Participation Window | Five constitutional sessions after valid INST-010 acceptance |
| Required implementation evidence | Task-by-task traceability; Docker-only BP/WBE/CE/web/integration/security/CCT results; affected-surface line coverage at least 90%; deterministic Migration 21b first/reapply/RLS/immutability/concurrency evidence; OpenAPI/manifests/state synchronization; S07-S08 synthetic journey; WC-042/WC-043 regression and reconciliation evidence |
| Required safety evidence | Exact version/hash and separate scope confirmation; Tier-4 fresh Keycloak authentication and same-tenant `EMPLOYER`; contract before payment; Razorpay-hosted checkout with no payment secrets; signature/replay checks; one canonical activation tuple, charge, subscription, evidence outcome, relationship, and `ACTIVE` transition; explicit retryable uncertainty; WBE `CONVERTED` as billing projection only; symmetric not-now/cancel/exit behavior |
| Independent review | INST-004 Enterprise Architect and INST-002 Constitutional Analyst review the completed contribution independently; INST-010 may not review or approve its own work |
| Completion boundary | Prepare an unmerged PR after all tasks, evidence, and independent reviews pass; Founder approval and merge remain separate |

### Grooming Traceability

| Task | Controlling owner contract | Existing implementation anchor | Discriminating executable proof |
|---|---|---|---|
| WC059-01 | D-06 relationship data contract, Migration 21 | Migrations 19/20b/21 patterns | First apply, reapply, forced RLS, immutable versions/acceptances, tuple concurrency/replay/conflict |
| WC059-02 | AEEC-01 through AEEC-15; D-06 business/solution/data contracts | WC-058 accepted configuration projection | Deterministic version/hash, complete plain-language terms, amendment creates new immutable version |
| WC059-03 | D-06 solution/security contracts | BP JWT tenant/participant authority and CE evidence gateways | Tier-4 freshness, same-tenant employer, exact hash, separate scope confirmation, replay/conflict |
| WC059-04 | ADR-022; WC-042/WC-043; D-06 security contract | WBE onboarding order, HMAC webhook, payment intents, reconciliation | Contract-before-payment, itemized INR/GST, proceed evidence, signature/replay, dispute/refund projection |
| WC059-05 | D-03 lifecycle; D-06 activation choreography | BP lifecycle/evidence gateway and Temporal workflow patterns | Ordered pending/WBE/evidence/active choreography under replay and concurrency |
| WC059-06 | D-06 failure contract and WBE billing projection | WC-058 expiry repair and WBE trial/subscription state | CE/WBE uncertainty reuses one intent; no second charge/relationship; no false `CONVERTED` lifecycle |
| WC059-07 | D-06 web/security/business contracts; ADR-023 Tier 4 | WC-058 relationship workspace and WhatsApp journey | Responsive/accessibility tests; portal-only acceptance/payment; symmetric hire/not-now/cancel/exit; no dark patterns |
| WC059-08 | WC-059 seven CCT assertions | Existing BP/WBE/CE/web constitutional suites | Version/hash, authority, scope, ordering, replay, concurrency, conflict, failure, and ethical UX all pass |

### Explicit Exclusions

- Live Razorpay mode, provider credentials or account setup, campaign/provider execution, WC-060, F6-F8 feature implementation, deployment, production operation, and customer-proof claims.
- Payment-secret collection in WAOOAW UI/chat, payment before accepted contract, acceptance through WhatsApp/MPIN/silence/default, direct trial-to-active conversion, duplicate charge/subscription/relationship, or WBE `CONVERTED` as a D-03 state.
- Architecture reinterpretation, weakening D-03/D-06/R-046/WC-059 obligations, self-review, self-approval, self-merge, direct push to `main`, or merge authority.

### Reserved Authorization — Not Issued

`GOA-GOAL-005-INST-010-05` is reserved for this contribution and may be issued only after:

1. a fresh INST-002 CA Readiness Review approves GEP-GOAL-005-INST-013-08, with every condition satisfied; and
2. `ACK-GOAL-005-INST-001-08` records the Founder's exact acknowledgement of this amendment.

Required acknowledgement:

> `I acknowledge GEP-GOAL-005-INST-013-08 and authorize INST-013 to issue GOA-GOAL-005-INST-010-05 for WC-059 implementation only. This does not authorize live Razorpay or provider activation, WC-060, deployment, merge, or self-review.`

After valid issuance, INST-010 must record `ACC-GOAL-005-INST-010-05` at a timestamp later than the GOA `issued_at`. No implementation task, source change, migration, generated production artifact, or build artifact may begin before that Acceptance Record exists.

### Fresh CA Readiness Decision

R-080 / `CR-GOAL-005-INST-002-12` independently APPROVES Amendment 8 with no
readiness condition. GEOM R2-03 condition 1 is satisfied. Condition 2 remains open:
`ACK-GOAL-005-INST-001-08` must contain the exact acknowledgement above before
INST-013 may issue GOA-GOAL-005-INST-010-05.

### Registrant Acknowledgement — ACK-GOAL-005-INST-001-08

| Field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-08 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-11T10:21:57Z |
| Acknowledged plan | GEP-GOAL-005-INST-013-08 |
| Decision | ACKNOWLEDGED — INST-013 authorized to issue GOA-GOAL-005-INST-010-05 for WC-059 only |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-08 and authorize INST-013 to issue GOA-GOAL-005-INST-010-05 for WC-059 implementation only. This does not authorize live Razorpay or provider activation, WC-060, deployment, merge, or self-review" |

R-080 and this record satisfy both GEOM R2-03 pre-issuance conditions. The acknowledgement does not itself issue a GOA, accept participation for INST-010, activate Razorpay or another provider, authorize WC-060, deploy, approve a PR, or permit merge.

### Authorization Record — GOA-GOAL-005-INST-010-05

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-05 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-010 — Platform IT Expert |
| Contribution scope | Implement WC059-01 through WC059-08 exactly within GEP-GOAL-005-INST-013-08 and WC-059; publish attested Contribution and Learning Records before independent review |
| Evidence specification | Task traceability; Docker-only BP/WBE/CE/web/integration/security/CCT evidence; affected-surface line coverage at least 90%; deterministic Migration 21b; S07-S08 synthetic journey; one charge/subscription/relationship/`ACTIVE` transition; explicit conflict and retryable uncertainty |
| Participation Window | Five constitutional sessions after valid acceptance |
| Independence constraint | INST-010 may implement but may not independently review, approve, merge, deploy, activate a provider, or declare Goal completion |
| Excluded authority | Live Razorpay/provider activation or credentials; account setup; WC-060/F6-F8; campaign/provider execution; deployment; production/customer proof; architecture reinterpretation; self-review; merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-11T10:21:58Z |

### Acceptance Record — ACC-GOAL-005-INST-010-05

| Field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-010-05 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-11T10:21:59Z |
| `authorization_id` | GOA-GOAL-005-INST-010-05 |
| Accepted scope | WC059-01 through WC059-08 implementation and evidence under Amendment 8 only |
| Participation Window | 2026-08-11T10:21:59Z through five constitutional sessions |
| Acceptance boundary | No live Razorpay/provider activation, credentials/account setup, WC-060, deployment, merge, self-review, architecture reinterpretation, or production/customer-proof authority |

The Acceptance timestamp is later than GOA issuance, satisfying GEOM G-03 and R2-12. WC-059 implementation may begin under FA-040, GEP-08, R-080, ACK-08, GOA-05, and ACC-05.

---

## Amendment 9 — WC-060 Implementation Readiness Routing

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-09 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-11 |
| Status | CA READY — R-086 APPROVED; exact Registrant acknowledgement and separate future current-session implementation authorization required |
| Amends | GEP-GOAL-005-INST-013-08 prospectively; Amendment 8 and all prior records remain unchanged |

### Purpose And Groomed Entry State

This amendment adds the dependency-ordered execution envelope for WC-060 only. WC-059 is DONE
through PR #265 and merge `b0dbe9c`. FA-037 and Amendment 6 make WC-060 the sole WC-034 F5
implementation contract. CB-004 is resolved after canonical BP OpenAPI, CE protobuf, D-06
Migration 22, security, export, erasure, and adversarial HMAC test contracts were repaired and
independently reviewed by INST-005, INST-006, INST-007, INST-004, and INST-002.

This amendment records implementation-ready specification scope only. Unlike Amendments 7 and
8 at their implementation start, no Founder current-session implementation directive exists.
Architecture approval, CA readiness, Registrant acknowledgement, or blocker closure cannot
substitute for the future exact directive `Authorize implementation of WC-060`.

### Phase 11 — WC-060 Omnichannel Continuity, Evidence, And Emergency Stop

| Field | Value |
|---|---|
| Primary Institution | INST-010 — Platform IT Expert |
| Contribution scope | After every authorization gate passes, implement WC060-01 through WC060-09 exactly across BP, PR, CE, web, Migration 22, and ADR-023 Phone Identity integration |
| Required inputs | WC-059 DONE; D-03 through D-07 and R-046 ratified; FA-037 and R-073/R-074/R-075 controlling; CB-004 resolved; canonical BP OpenAPI v1.7.0, CE protobuf, D-06 solution/data/security contracts, and every WC-060 Required Input current |
| Participation Window | Five constitutional sessions after valid INST-010 acceptance |
| Required implementation evidence | Task traceability; Docker-only BP/PR/CE/web/integration/security/CCT evidence; affected-surface line coverage at least 90%; Migration 22 first/reapply/RLS/transition/immutability/concurrency proof; OpenAPI/protobuf/generated-client conformance; exact 360px and expanded browser acceptance; proportional F8 evidence |
| Required safety evidence | Tenant/relationship/role isolation; fresh target authentication; HMAC-SHA256 continuity-envelope verification; replay/conflict/out-of-order denial with zero unauthorized mutation; role-filtered Evidence Reader/export; erased-payload proof retention; cross-channel Stop within the existing constitutional budget; Tier-4 evidence-linked Stop release only |
| Independent review | INST-007 Security Architect and INST-006 Data Architect review their completed implementation surfaces; fresh INST-004 performs final integrated acceptance; INST-010 may not review or approve its own work |
| Completion boundary | Prepare one complete unmerged PR after all nine tasks, F5 UX acceptance, proportional F8 evidence, and independent reviews pass; Founder review and merge remain separate |

### Grooming Traceability

| Task | Controlling contract | Required discriminating proof |
|---|---|---|
| WC060-01 | D-06 Migration 22 exact blueprint | First apply/reapply, valid composite FKs, forced RLS, checks/triggers, append-only acknowledgements, 15-minute checkpoint expiry, 48-hour dedup cleanup, replay/concurrency |
| WC060-02 | ADR-023 and D-06 Security Contract | Meta HMAC/timestamp/dedup, opt-in, tenant-scoped 30-minute phone JWT, MPIN lockout, phone-attach Tier-4 proof, takeover/confused-deputy denial |
| WC060-03 | BP OpenAPI handoffs and D-06 Solution Contract | Signed RFC 8785 envelope, fresh target role/assurance, evidence-before-commit, source preservation, identical replay, divergent conflict, HMAC CCT |
| WC060-04 | PR session-routing ownership | Multiple channel sessions resolve one relationship/current authority while retaining separate delivery state; reconnect reauthenticates and cannot duplicate lifecycle outcome |
| WC060-05 | BP Evidence Reader OpenAPI and CE `QueryEvidenceRecords` | Tenant/relationship/role projection, opaque-ID CE query, bounded cursor, no existence disclosure, erased proof retention, deterministic signed JSON export |
| WC060-06 | F5 hybrid UX and acknowledgement semantics | Timeline/evidence/authority/cost/trial/Stop across web and WhatsApp; transport acceptance remains distinct from participant observation; unresolved delivery shown honestly |
| WC060-07 | D-06 Stop and release contract | One-channel Stop halts every relationship session within budget; later consequential commands deny; release requires fresh Tier-4 EMPLOYER and originating Stop evidence chain |
| WC060-08 | Nine WC-060 CCT assertions | Takeover, replay, confused deputy, downgrade, cross-tenant, out-of-order, offline, duplicate, HMAC forgery/replay, Stop, unauthorized release, and reconstructability pass |
| WC060-09 | WC-034 F5 and proportional F8 acceptance | UX-CONV-03, UX-RES-02, UX-CONT-01 through UX-CONT-06, generated client, accessibility, privacy, lint, build, coverage, and regression evidence pass |

### Authorization Rules And Mandatory Stops

1. This proposed amendment issues no GO Authorization and authorizes no implementation.
2. `GOA-GOAL-005-INST-010-06` is reserved and may issue only after a fresh INST-002 CA
	Readiness Review approves this exact amendment, the Registrant records the exact
	acknowledgement below, and the Founder gives the separate current-session directive
	`Authorize implementation of WC-060`.
3. After valid GOA issuance, INST-010 must record `ACC-GOAL-005-INST-010-06` at a timestamp
	later than `issued_at`. No implementation task may start before that acceptance exists.
4. Registrant acknowledgement authorizes future GOA routing only; it is not implementation
	consent and cannot be inferred from PR approval, merge, architecture approval, G5 CLEAR,
	backlog priority, blocker closure, or Work Contract status.
5. INST-013 may sequence and mechanically verify records but may not contribute source,
	migrations, generated clients, tests, implementation evidence, or independent review.
6. INST-010 may implement only after all gates pass and may not deploy, activate providers,
	self-review, self-approve, self-merge, merge, or begin F6-F8 feature implementation.

### Required Future Registrant Acknowledgement

Before `GOA-GOAL-005-INST-010-06` may issue, the Registrant must record exactly:

> `I acknowledge GEP-GOAL-005-INST-013-09 and authorize INST-013 to issue GOA-GOAL-005-INST-010-06 for WC-060 implementation only after I separately authorize implementation for that current session. This does not authorize provider activation, deployment, F6-F8 feature implementation, PR merge, self-review, or self-merge.`

The acknowledgement above does not satisfy the separate implementation gate. In the future
implementation session, the Founder must also state exactly:

> `Authorize implementation of WC-060`

### Fresh CA Readiness Decision

R-086 / `CR-GOAL-005-INST-002-13` independently APPROVES Amendment 9 with no
readiness condition. GEOM R2-03 condition 1 is satisfied. Condition 2 remains open:
`ACK-GOAL-005-INST-001-09` must contain the exact acknowledgement above. The separate
current-session implementation gate also remains open and requires the future exact Founder
directive `Authorize implementation of WC-060`. R-086 issues no GOA or ACC and authorizes no
implementation.

### Registrant Acknowledgement — ACK-GOAL-005-INST-001-09

| Field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-09 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-12T02:44:57Z |
| Acknowledged plan | GEP-GOAL-005-INST-013-09 |
| Decision | ACKNOWLEDGED — INST-013 may issue GOA-GOAL-005-INST-010-06 only after the separate current-session Founder implementation directive |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-09 and authorize INST-013 to issue GOA-GOAL-005-INST-010-06 for WC-060 implementation only after I separately authorize implementation for that current session. This does not authorize provider activation, deployment, F6-F8 feature implementation, PR merge, self-review, or self-merge." |

R-086 and this record satisfy both GEOM R2-03 pre-issuance conditions. The acknowledgement does
not satisfy the separate current-session implementation gate, issue a GOA, accept participation
for INST-010, authorize implementation, activate a provider, deploy, approve or merge a PR, or
permit self-review or self-merge.

### Current-Session Implementation Authorization — FA-041

The Founder stated exactly `Authorize implementation of WC-060` on 2026-08-12. FA-041 records
that directive and satisfies Amendment 9's separate current-session implementation-consent gate.
It does not substitute for GOA issuance or later INST-010 acceptance and does not authorize
provider activation, deployment, F6-F8 feature implementation, PR merge, self-review, or
self-merge.

### Authorization Record — GOA-GOAL-005-INST-010-06

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-06 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-010 — Platform IT Expert |
| Contribution scope | Implement WC060-01 through WC060-09 exactly within GEP-GOAL-005-INST-013-09 and WC-060; publish attested Contribution and Learning Records before independent review |
| Evidence specification | Task traceability; Docker-only BP/PR/CE/web/integration/security/CCT evidence; affected-surface line coverage at least 90%; Migration 22 safety; OpenAPI/protobuf/generated-client conformance; exact 360px and expanded browser acceptance; proportional F8 evidence |
| Participation Window | Five constitutional sessions after valid acceptance |
| Independence constraint | INST-010 may implement but may not independently review, approve, merge, deploy, activate a provider, or declare Goal completion |
| Excluded authority | Provider activation or credentials; deployment; F6-F8 feature implementation; production/customer proof; architecture reinterpretation; self-review; PR approval; merge; self-merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T02:53:21Z |

### Acceptance Record — ACC-GOAL-005-INST-010-06

| Field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-010-06 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-12T04:00:00Z |
| `authorization_id` | GOA-GOAL-005-INST-010-06 |
| Accepted scope | WC060-01 through WC060-09 implementation and evidence under Amendment 9 only |
| Participation Window | 2026-08-12T04:00:00Z through five constitutional sessions |
| Acceptance boundary | No provider activation or credentials; no deployment; no F6-F8 feature implementation; no production/customer-proof authority; no self-review; no PR approval; no merge; no self-merge; no architecture reinterpretation |

The Acceptance timestamp is later than the GOA issuance timestamp (2026-08-12T02:53:21Z), satisfying GEOM G-03 and R2-12. WC-060 implementation may begin under FA-041, GEP-09, R-086, ACK-09, GOA-06, and ACC-06.

### Explicit Exclusions

- no implementation source, Migration 22 SQL, generated production client, test or build
  artifact in this readiness contribution;
- no provider credential, account setup, live provider activation, deployment, production
  operation, customer-proof claim, PR approval, or merge;
- no AE-02 campaign execution, F6-F8 feature implementation, architecture reinterpretation,
  weakening of D-03/D-06/R-046/WC-060, or duplicate F5 implementation pass; and
- no retrospective authorization, inferred consent, self-review, self-approval, self-merge,
  or direct push to `main`.

---

## Amendment 10 — WC-062 Voice Interaction Prospective Routing

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-10 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-12 |
| Status | RECONCILED CANDIDATE — initial CA routing-readiness review and exact Registrant acknowledgement required before any specification GOA; no GOA or Acceptance is issued by this amendment |
| Amends | GEP-GOAL-005-INST-013-09 prospectively; Amendment 9 and all prior records remain unchanged |

### Purpose, Scope, And Fixed Inputs

This amendment routes WC-062 as the separate WC-034 F6 contract for a reusable platform voice
capability. It does not authorize a DMA-specific implementation or reopen completed F1–F5 work.
The fixed implementation scope is WC062-01 through WC062-07 exactly as defined in WC-062. The
normative routing inputs are WC-062, the F6 section of the WC-034 implementation decomposition,
the accepted F1–F5 contracts, C-001/C-023/C-042/C-049/C-051/C-059/C-060/C-061/C-063/C-065/
C-071/C-076/C-080, and ADR-017/020/023/029. Where those inputs do not decide an F6 policy,
the accountable specification owner must decide it within its own Decision Space; INST-013 must
not supply or infer the decision.

### Routing Preconditions

Before any specification GOA below may issue:

1. a fresh INST-002 context that will not perform the later package review must approve this
	reconciled routing plan as `CR-GOAL-005-INST-002-14`; and
2. the Registrant must record `ACK-GOAL-005-INST-001-10` using the exact acknowledgement below.

Those records satisfy GEOM R2-03 for specification routing only. They do not authorize
implementation, issue a GOA, create an Acceptance, start a Participation Window, or predetermine
any contribution or review verdict.

### Ordered Specification Contributions

| Order | Planned GOA / Acceptance | Institution | Contribution scope and required records | Participation Window after valid Acceptance | Independence constraint |
|---:|---|---|---|---|---|
| 1A | `GOA-GOAL-005-INST-011-09` / `ACC-GOAL-005-INST-011-09` | INST-011 Product Owner | Publish the first-release channel/language, consent, correction, confidence, fallback, failure, duration/size, and customer-visible acceptance contract as `CR-GOAL-005-INST-011-10` plus `LR-GOAL-005-INST-011-07` | 2 constitutional sessions | May decide product behavior and acceptance meaning only; may not design APIs, storage, security mechanisms, implementation, or approve its own contribution |
| 1B | `GOA-GOAL-005-INST-005-11` / `ACC-GOAL-005-INST-005-11` | INST-005 Solution Architect | Publish provider-neutral BP public schemas/operations, PR/AIR private ownership, sequence, idempotency, failure semantics, generated-client boundary, and C-095 determination as `CR-GOAL-005-INST-005-14` plus `LR-GOAL-005-INST-005-05` | 3 constitutional sessions | May author component and interface contracts only; may not choose product/privacy policy, implement source, or perform Order 2 integrated review |
| 1C | `GOA-GOAL-005-INST-006-04` / `ACC-GOAL-005-INST-006-04` | INST-006 Data Architect | Publish classification, minimisation, storage ownership, retention, erasure, evidence/payload separation, lineage, language metadata, and migration decision as `CR-GOAL-005-INST-006-05` plus `LR-GOAL-005-INST-006-03` | 2 constitutional sessions | May decide data architecture only; may not choose product behavior, API ownership outside data surfaces, security controls, implementation, or self-review |
| 1D | `GOA-GOAL-005-INST-007-08` / `ACC-GOAL-005-INST-007-08` | INST-007 Security Architect | Publish consent/permission threats, authenticated upload, validation/scanning, replay, encryption, residency, abuse, observability, privacy-safe failure, and adversarial CCT obligations as `CR-GOAL-005-INST-007-08` plus `LR-GOAL-005-INST-007-03` | 2 constitutional sessions | May define non-weakenable security/privacy floors only; may not choose product behavior, author owner APIs, implement, or approve its own contribution |
| 2 | `GOA-GOAL-005-INST-004-11` / `ACC-GOAL-005-INST-004-11` | INST-004 Enterprise Architect | After 1A–1D publish, reconcile their exact committed versions and approve or reject the integrated architecture as `CR-GOAL-005-INST-004-12` plus `LR-GOAL-005-INST-004-08` | 1 constitutional session | Fresh review context; did not author or repair Orders 1A–1D; may identify findings but may not edit the reviewed contributions |
| 3 | `GOA-GOAL-005-INST-002-11` / `ACC-GOAL-005-INST-002-11` | INST-002 Constitutional Analyst | After approved Order 2, independently review the fixed package, this amendment, and WC-062 Entry Gate as `CR-GOAL-005-INST-002-15` plus `LR-GOAL-005-INST-002-04` | 1 constitutional session | Fresh context distinct from `CR-GOAL-005-INST-002-14`; did not author, repair, integrate, or approve any reviewed contribution |

Orders 1A–1D may execute in parallel after their own valid GOA and later Acceptance. Order 2 may
begin only after all four Contribution and Learning Records are published. Order 3 may begin only
after Order 2 publishes an APPROVED integrated review. A rejected or conditional record returns
only to its accountable owner; INST-013 may reroute the repair but may not perform it.

### Per-Institution Evidence Specifications

Every Contribution and Learning Record must contain all GEOM G-10 and G-05 fields, identify its
GOA and Acceptance, cite exact source versions or hashes, distinguish specification evidence from
implementation/runtime/customer proof, list unresolved decisions, and state a verdict limited to
the Institution's Decision Space.

| Institution | Minimum complete evidence |
|---|---|
| INST-011 | First-release browser channel and supported-language policy; permission and consent copy/state model; record/pause/resume/cancel/review/correct/explicit-send journey; confidence and unsupported-language behavior; complete text fallback; duration/size recommendation; exact acceptance ID, scenario, fixture, and pass-condition matrix |
| INST-005 | Versioned BP OpenAPI changes; generated-client-compatible schemas and operation IDs; private PR/AIR contracts; upload/transcription/correction state sequence; idempotency and reconciliation; provider abstraction; typed failure/degradation semantics; no direct browser-to-private-service path; C-095 manifest/skeleton decision |
| INST-006 | Audio/transcript/evidence classifications; authoritative owner per state; residency and encryption-relevant data flow inputs; minimisation; retention clock and deletion/erasure behavior; immutable evidence versus erasable payload; lineage/correction model; migration blueprint or reasoned no-migration decision |
| INST-007 | Threat actors and trust boundaries; permission/consent abuse; MIME/signature/codec and size/duration validation; malware/quarantine flow; authenticated tenant/relationship binding; replay/idempotency and confused-deputy controls; encryption/key and provider-residency floors; privacy-safe logs/errors; adversarial CCT matrix |
| INST-004 | Version-pinned matrix proving Product, Solution, Data, and Security consistency; ownership and dependency graph; no unresolved policy delegated to code; acceptance-to-contract traceability; ADR/C-095 decision validation; explicit APPROVED, APPROVED WITH CONDITIONS, or REJECT verdict |
| INST-002 | GEOM ordering and temporal validity; C-001/C-023/C-042/C-049/C-051/C-060/C-061/C-063/C-065/C-080 compliance; Decision Space and independence; complete Entry Gate matrix; exact remaining Registrant/session authorization/GOA/Acceptance stops; explicit readiness verdict |

### Exact Acceptance Inventory To Reconcile

INST-011 must define, and Orders 2–3 must approve, these exact IDs in
`architecture/reference/ux/hybrid-ui-acceptance-contract.md`; an ID may be strengthened but not
renamed, silently omitted, or assigned a meaning outside the label below:

| ID | Required meaning |
|---|---|
| `UX-VOICE-01` | Permission denied or unavailable preserves a complete text path |
| `UX-VOICE-02` | Record, pause, resume, cancel, timer, playback, and draft controls are truthful and stable |
| `UX-VOICE-03` | Review and explicit send are separate; recording/upload/transcription never implies consent to send |
| `UX-VOICE-04` | Low confidence and unsupported language require correction or text fallback before consequential use |
| `UX-VOICE-05` | Upload/provider failure is recoverable without duplicate contribution or fabricated success |
| `UX-VOICE-06` | Offline/reconnect reconciles authoritative state before retry and preserves the original idempotency identity |
| `UX-VOICE-07` | Malformed, unsupported, oversized, over-duration, or quarantined content fails safely and privately |
| `UX-VOICE-08` | Retention and erasure treatment is visible without claiming durable evidence was deleted |
| `UX-VOICE-09` | Exact 360x800, intermediate, and expanded layouts preserve composer controls and Stop without overflow |
| `UX-VOICE-10` | Keyboard and screen-reader journey completes record/review/correct/send or equivalent text fallback |
| `UX-VOICE-11` | RTL, eleven-locale fallback, reduced motion, and 200% zoom preserve meaning and operation |
| `UX-VOICE-12` | Emergency Stop remains independent and effective during capture, upload, transcription, correction, and retry |
| `CCT-VOICE-EF-01` | Evidence First distinguishes transport, transcription, correction, acceptance, and recorded evidence |
| `CCT-VOICE-TENANT-01` | Tenant, relationship, participant, and assurance bindings deny cross-boundary access |
| `CCT-VOICE-REPLAY-01` | Duplicate, replayed, and uncertain requests cannot duplicate contributions or evidence |
| `CCT-VOICE-PRIV-01` | Audio/transcript content and sensitive identifiers do not leak through URL, logs, metrics, traces, or errors |

The implementation evidence package must also preserve all applicable shell, contract,
responsive, accessibility, RTL, PWA/privacy, CCT-UX-HO, CCT-UX-EF, and `UX-VIS-03` obligations.

### Implementation Entry And Evidence Boundary

After Order 3 approves the fixed package, the Registrant must acknowledge that exact reconciled
package. FA-042 remains dormant. In the separate human session that will write implementation
code, the Founder must freshly answer the mandatory implementation-gate question. Only after
both records exist may INST-013 issue a WC-062 implementation GOA to INST-010. The implementation
Participation Window is **five constitutional sessions after valid INST-010 Acceptance**.

Implementation evidence must trace WC062-01 through WC062-07 to the approved contracts and exact
acceptance IDs; prove canonical/generated contract conformance; use Docker-only unit, contract,
integration, security, privacy, and CCT execution; achieve at least 90% affected-surface line
coverage; include Chromium/Firefox/WebKit at exact 360x800, 768x1024, and 1440x900 plus keyboard,
screen reader, RTL, reduced motion, 200% zoom, axe, offline/replay, Stop, and proportional F8
evidence; and receive fresh Data, Security, integrated EA, and Constitutional reviews. Completion
is one complete unmerged PR; Founder review and merge remain separate.

### Required Registrant Acknowledgement

Before any specification GOA is issued, the Registrant must record exactly:

> "I acknowledge GEP-GOAL-005-INST-013-10 and authorize INST-013 to route the WC-062 Product, Solution, Data, Security, integrated Enterprise Architecture, and independent Constitutional Analyst specification contributions exactly as specified. I understand that this acknowledgement does not authorize implementation, issue a GOA by itself, create Acceptance, start a Participation Window, activate a provider, deploy, approve or merge a PR, or replace the fresh implementation-session confirmation required after the Entry Gate closes."

### Mandatory Stops

1. This amendment defines prospective identifiers but issues no GOA, records no Acceptance, and authorizes no contribution or implementation by itself.
2. No candidate or pre-existing document may be retroactively treated as an authorized WC-062 contribution.
3. No specification GOA may issue before `CR-GOAL-005-INST-002-14` and `ACK-GOAL-005-INST-001-10` are both recorded.
4. No Order 2 or 3 GOA may issue before its dependency records are complete and version-pinned.
5. FA-042 cannot authorize the future implementation session. No implementation GOA may issue before Order 3 approval, exact package acknowledgement, and fresh explicit Founder confirmation in the session that will write implementation code.
6. INST-010 must record Acceptance later than implementation GOA issuance before WC062-01 begins.
7. No provider activation, credential setup, deployment, DMA-specific behavior, production/customer proof, PR approval, merge, self-review, or self-merge is included.

### Current Decision

WC-062 is **READY FOR INDEPENDENT CA ROUTING-READINESS REVIEW ONLY** and remains **NOT
IMPLEMENTATION-READY**. FA-042 records Founder implementation intent but is dormant. No owner
contribution, integrated review, final CA readiness decision, Registrant acknowledgement,
future-session implementation confirmation, GOA, Acceptance, or active Participation Window has
been recorded.

### Amendment 10 Routing-Readiness And Registrant Acknowledgement

R-090 / `CR-GOAL-005-INST-002-14` independently APPROVES this reconciled amendment for exact
Registrant acknowledgement and prospective specification routing. The review was produced at
2026-08-12T09:54:30Z against commit `4a267e1`. It issues no authority.

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-10 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-12T09:56:28Z |
| Acknowledged plan | GEP-GOAL-005-INST-013-10 |
| Registrant | Yogesh Khandge / Founder |
| Decision | ACKNOWLEDGED — WC-062 specification routing only |
| Exact quoted acknowledgement | "I acknowledge GEP-GOAL-005-INST-013-10 and authorize INST-013 to route the WC-062 Product, Solution, Data, Security, integrated Enterprise Architecture, and independent Constitutional Analyst specification contributions exactly as specified. I understand that this acknowledgement does not authorize implementation, issue a GOA by itself, create Acceptance, start a Participation Window, activate a provider, deploy, approve or merge a PR, or replace the fresh implementation-session confirmation required after the Entry Gate closes." |

This record satisfies GEOM R2-03 condition 2 for Amendment 10 specification routing. Together
with R-090 it permits INST-013 to issue the Order 1A-1D GOAs below. It does not issue a GOA,
record Acceptance, start a Participation Window, or authorize implementation.

### Amendment 10 Order 1 Specification GOAs

#### GOA-GOAL-005-INST-011-09

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-011-09 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-011 — Product Owner |
| Contribution scope | Produce Amendment 10 Order 1A exactly as specified; publish `CR-GOAL-005-INST-011-10` and `LR-GOAL-005-INST-011-07` |
| Evidence specification | Amendment 10 INST-011 minimum evidence and exact voice acceptance inventory; fixed inputs and exclusions remain binding |
| Participation Window | 2 constitutional sessions after valid `ACC-GOAL-005-INST-011-09` |
| Excluded authority | API/data/security design, implementation, provider activation, deployment, integrated or constitutional review, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T09:56:29Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

#### GOA-GOAL-005-INST-005-11

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-005-11 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-005 — Solution Architect |
| Contribution scope | Produce Amendment 10 Order 1B exactly as specified; publish `CR-GOAL-005-INST-005-14` and `LR-GOAL-005-INST-005-05` |
| Evidence specification | Amendment 10 INST-005 minimum evidence; canonical generated-client-compatible BP and private PR/AIR boundaries; fixed inputs and exclusions remain binding |
| Participation Window | 3 constitutional sessions after valid `ACC-GOAL-005-INST-005-11` |
| Excluded authority | Product/privacy policy, data/security ownership outside solution scope, implementation, provider activation, deployment, integrated review, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T09:56:30Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

#### GOA-GOAL-005-INST-006-04

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-006-04 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-006 — Data Architect |
| Contribution scope | Produce Amendment 10 Order 1C exactly as specified; publish `CR-GOAL-005-INST-006-05` and `LR-GOAL-005-INST-006-03` |
| Evidence specification | Amendment 10 INST-006 minimum evidence, including migration blueprint or reasoned no-migration decision; fixed inputs and exclusions remain binding |
| Participation Window | 2 constitutional sessions after valid `ACC-GOAL-005-INST-006-04` |
| Excluded authority | Product behavior, API ownership outside data surfaces, security mechanism selection, implementation, provider activation, deployment, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T09:56:31Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

#### GOA-GOAL-005-INST-007-08

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-007-08 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-007 — Security Architect |
| Contribution scope | Produce Amendment 10 Order 1D exactly as specified; publish `CR-GOAL-005-INST-007-08` and `LR-GOAL-005-INST-007-03` |
| Evidence specification | Amendment 10 INST-007 minimum evidence and adversarial CCT matrix; fixed inputs and exclusions remain binding |
| Participation Window | 2 constitutional sessions after valid `ACC-GOAL-005-INST-007-08` |
| Excluded authority | Product behavior, owner API authorship, data-policy decisions outside security floors, implementation, provider activation, deployment, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T09:56:32Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

No Acceptance Record exists for these GOAs at issuance. Each Institution must explicitly accept
after its `issued_at`; only that later timestamp starts its Participation Window. Order 2 remains
blocked until all four Contribution and Learning Records are published.

### Amendment 10 Order 1 Acceptance Records

| `record_id` | Institution | `authorization_id` | `acceptance_timestamp` | Decision and boundary |
|---|---|---|---|---|
| ACC-GOAL-005-INST-011-09 | INST-011 | GOA-GOAL-005-INST-011-09 | 2026-08-12T10:00:31Z | ACCEPTED — Order 1A product behavior and acceptance specification only |
| ACC-GOAL-005-INST-005-11 | INST-005 | GOA-GOAL-005-INST-005-11 | 2026-08-12T10:07:17Z | ACCEPTED — Order 1B provider-neutral solution and contract specification only |
| ACC-GOAL-005-INST-006-04 | INST-006 | GOA-GOAL-005-INST-006-04 | 2026-08-12T10:07:18Z | ACCEPTED — Order 1C data architecture and migration-decision specification only |
| ACC-GOAL-005-INST-007-08 | INST-007 | GOA-GOAL-005-INST-007-08 | 2026-08-12T10:07:19Z | ACCEPTED — Order 1D security floors and adversarial CCT specification only |

Each record has `institution_id` equal to the named accepting Institution, `goal_id` GOAL-005,
`record_type` Acceptance Record, and the listed `authorization_id`. Each timestamp is later than
its GOA `issued_at`. The corresponding Participation Window is now active for the duration stated
in the GOA. These Acceptances authorize specification contributions only and do not authorize
implementation, provider activation, deployment, integrated review, PR approval, or merge.

### Amendment 10 Order 1 Completion

The version-pinned owner package at commit `0c994b5` contains:

- INST-011: `CR-GOAL-005-INST-011-10` and `LR-GOAL-005-INST-011-07`;
- INST-005: `CR-GOAL-005-INST-005-14` and `LR-GOAL-005-INST-005-05`;
- INST-006: `CR-GOAL-005-INST-006-05` and `LR-GOAL-005-INST-006-03`; and
- INST-007: `CR-GOAL-005-INST-007-08` and `LR-GOAL-005-INST-007-03`.

The same commit contains all sixteen exact voice acceptance IDs in the canonical acceptance
contract. Order 1A-1D is complete for integrated review. This completion assertion is mechanical
and does not approve the package.

### GOA-GOAL-005-INST-004-11

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-11 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | Independently review and integrate the fixed WC-062 owner package at commit `0c994b5`; publish `CR-GOAL-005-INST-004-12` and `LR-GOAL-005-INST-004-08` |
| Evidence specification | Amendment 10 INST-004 minimum evidence, including version matrix, ownership/dependency graph, acceptance-to-contract traceability, C-095/ADR determination, unresolved-decision check, and explicit verdict |
| Participation Window | 1 constitutional session after valid `ACC-GOAL-005-INST-004-11` |
| Independence constraint | Fresh INST-004 context that authored or repaired none of Orders 1A-1D; may identify findings but may not edit the reviewed package |
| Excluded authority | Owner contribution repair, implementation, source, tests, migration, generated client, provider activation, deployment, constitutional review, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T10:22:28Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

Order 3 remains blocked until this review publishes an APPROVED integrated verdict and its
Learning Record.

### ACC-GOAL-005-INST-004-11

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-11 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-004-11 |
| `acceptance_timestamp` | 2026-08-12T10:25:53Z |
| Decision | ACCEPTED |
| Contribution scope accepted | Independent integrated review of the exact WC-062 owner package at commit `0c994b5` only |
| Participation Window | One constitutional session from this Acceptance |
| Independence attestation | Fresh INST-004 context that authored or repaired none of Orders 1A-1D |
| Exclusions | No owner repair, implementation, source, tests, migration, generated client, provider activation, deployment, constitutional review, PR approval, or merge |

The Acceptance timestamp is later than the GOA issuance timestamp. Order 2 is active; Order 3 and
all implementation remain blocked.

### Amendment 10 Order 2 Completion

R-091 / `CR-GOAL-005-INST-004-12` and `LR-GOAL-005-INST-004-08` independently APPROVE the
integrated owner package at commit `0c994b5`. The approved review is fixed at commit `c5d903f` and
imposes no architectural condition. Order 2 is complete; this does not authorize implementation.

### GOA-GOAL-005-INST-002-11

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-002-11 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-002 — Constitutional Analyst |
| Contribution scope | Independently review Amendment 10, WC-062 Entry Gate, owner package `0c994b5`, and R-091 at `c5d903f`; publish `CR-GOAL-005-INST-002-15` and `LR-GOAL-005-INST-002-04` |
| Evidence specification | Amendment 10 INST-002 minimum evidence, including GEOM chronology, constitutional obligations, Decision Spaces, independence, exact Entry Gate matrix, residual human/GOA/Acceptance stops, and explicit final readiness verdict |
| Participation Window | 1 constitutional session after valid `ACC-GOAL-005-INST-002-11` |
| Independence constraint | Fresh INST-002 context distinct from R-090 and all owner/EA contexts; may identify findings but may not author, repair, integrate, or approve reviewed contributions outside this verdict |
| Excluded authority | Specification repair, implementation, source, tests, migration, generated client, provider activation, deployment, Registrant acknowledgement, implementation GOA, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T10:39:23Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

### ACC-GOAL-005-INST-002-11

| Field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-002-11 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-002-11 |
| `acceptance_timestamp` | 2026-08-12T10:40:15Z |
| Decision | ACCEPTED |
| Contribution scope accepted | Final independent readiness review of Amendment 10, WC-062 Entry Gate, owner package `0c994b5`, and R-091 at `c5d903f` only |
| Participation Window | One constitutional session from this Acceptance |
| Independence attestation | Fresh INST-002 context distinct from R-090 and all owner/EA contexts |
| Exclusions | No specification repair, implementation, source, tests, migration, generated client, provider activation, deployment, Registrant acknowledgement, implementation GOA, PR approval, or merge |

The Acceptance timestamp is later than the GOA issuance timestamp. Order 3 is active. Final
readiness remains undecided until the Contribution and Learning Records are published.

### Amendment 10 Canonical Contract Repair

CR-GOAL-005-INST-005-15 and LR-GOAL-005-INST-005-06 publish the canonical contract bytes omitted
from the original Solution contribution. Commit `1e80dfd` fixes BP OpenAPI `1.8.0`, PR OpenAPI
`1.3.0` with `VoiceOrchestrationV1` `1.0.0`, and AIR `ProviderNeutralTranscriptionV1` `1.0.0` by
exact SHA-256 in the Solution repair attestation. The repair is specification-only and grants no
implementation authority.

R-091 remains an accurate review of package `0c994b5`, but it cannot approve the repaired package
and is superseded for current Entry Gate readiness. GOA-GOAL-005-INST-002-11 and
ACC-GOAL-005-INST-002-11 remain valid historical records scoped only to the old package; no final
CA contribution was published from that scope. Fresh integrated EA approval and a later fresh CA
scope are mandatory.

### GOA-GOAL-005-INST-004-12

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-004-12 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-004 — Enterprise Architect |
| Contribution scope | Independently review and integrate the repaired WC-062 package at commit `1e80dfd`; publish `CR-GOAL-005-INST-004-13` and `LR-GOAL-005-INST-004-09` |
| Evidence specification | Amendment 10 INST-004 evidence plus exact canonical contract versions/hashes, OpenAPI ownership and browser/private boundary, acceptance traceability, C-095/ADR determination, unresolved-decision check, and explicit verdict |
| Participation Window | 1 constitutional session after valid `ACC-GOAL-005-INST-004-12` |
| Independence constraint | Fresh INST-004 context that authored or repaired none of the owner package or canonical contracts; may identify findings but may not edit the reviewed package |
| Excluded authority | Owner repair, implementation, source, tests, migration, generated client, provider activation, deployment, constitutional review, Registrant acknowledgement, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T11:00:16Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

Final CA readiness is blocked until this fresh EA scope is accepted and publishes an APPROVED
Contribution and Learning Record. All implementation remains blocked.

### ACC-GOAL-005-INST-004-12

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-004-12 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-004-12 |
| `acceptance_timestamp` | 2026-08-12T11:03:22Z |
| Decision | ACCEPTED |
| Contribution scope accepted | Independent integrated review of repaired package `1e80dfd` only |
| Participation Window | One constitutional session from this Acceptance |
| Independence attestation | Fresh INST-004 context that authored or repaired none of the reviewed package |
| Exclusions | No owner repair, implementation, source, tests, migration, generated client, provider activation, deployment, constitutional review, Registrant acknowledgement, PR approval, or merge |

The Acceptance is later than the GOA issuance. R-093 / CR-GOAL-005-INST-004-13 and
LR-GOAL-005-INST-004-09 APPROVE the repaired package. Fresh Amendment 10 Order 2 is complete;
Order 3 still requires a new CA GOA and Acceptance. No implementation authority exists.

### GOA-GOAL-005-INST-002-12

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-002-12 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-002 — Constitutional Analyst |
| Contribution scope | Independently review Amendment 10, WC-062 Entry Gate, repaired package `1e80dfd`, and R-093 at `d991272`; publish `CR-GOAL-005-INST-002-16` and `LR-GOAL-005-INST-002-05` |
| Evidence specification | GEOM chronology; constitutional obligations; Decision Spaces and independence; exact canonical contract hashes; 16 acceptance IDs; complete Entry Gate matrix; exact remaining acknowledgement, fresh-session authority, GOA, and Acceptance stops; explicit readiness verdict |
| Participation Window | 1 constitutional session after valid `ACC-GOAL-005-INST-002-12` |
| Independence constraint | Fresh INST-002 context distinct from R-090, the stale pre-repair CA scope, all owner contexts, and both EA contexts; may identify findings but may not author, repair, or integrate reviewed artifacts |
| Excluded authority | Specification repair, implementation, source, tests, migration, generated client, provider activation, deployment, Registrant acknowledgement, implementation GOA, PR approval, merge, and self-review |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T11:17:24Z |
| State | ISSUED — awaiting Acceptance; Participation Window inactive |

Final readiness remains undecided. No CA contribution may be published until a valid Acceptance
later than this issuance activates the Participation Window.

### ACC-GOAL-005-INST-002-12

| Field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-002-12 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-002-12 |
| `acceptance_timestamp` | 2026-08-12T11:23:50Z |
| Decision | ACCEPTED |
| Contribution scope accepted | Final independent readiness review of Amendment 10, WC-062, repaired package `1e80dfd`, and R-093 at `d991272` only |
| Participation Window | One constitutional session from this Acceptance |
| Independence attestation | Fresh INST-002 context distinct from R-090, the unpublished pre-repair draft, all owner contexts, and both EA contexts |
| Exclusions | No specification repair, implementation, source, tests, migration, generated client, provider activation, deployment, Registrant acknowledgement, implementation GOA, PR approval, or merge |

The Acceptance timestamp is later than GOA issuance. R-094 / CR-GOAL-005-INST-002-16 and
LR-GOAL-005-INST-002-05 APPROVE the repaired specification package and complete Amendment 10
Order 3. WC-062 Entry Gate items 1–5 are complete; item 6 remains open.

### ACK-GOAL-005-INST-001-11 — Repaired-Package Acknowledgement

| Field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-11 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-12T11:29:30Z |
| Exact acknowledged package | Canonical repair `1e80dfd`; R-093 at `d991272`; R-094 / `CR-GOAL-005-INST-002-16` |
| Entry Gate effect | Item 6 COMPLETE only |
| Excluded authority | Implementation, GOA issuance, INST-010 Acceptance, provider activation, deployment, PR approval, and merge |

The Registrant stated exactly:

> "I acknowledge the repaired WC-062 specification package at commit 1e80dfd, the fresh integrated Enterprise Architecture approval R-093 at commit d991272, and the final Constitutional Analyst approval R-094 / CR-GOAL-005-INST-002-16. I understand that this acknowledgement closes Entry Gate item 6 only and does not authorize implementation, issue a GOA, create INST-010 Acceptance, activate a provider, deploy, approve or merge a PR, or replace the fresh current-session Founder implementation authorization still required by item 7."

ACK-GOAL-005-INST-001-11 satisfies WC-062 Entry Gate item 6. Implementation remains blocked by
item 7 fresh current-session Founder authorization, item 8 GOA issuance, and item 9 INST-010
Acceptance in that order.

### Current-Session Implementation Authorization — FA-043

After INST-013 asked exactly `This would begin writing implementation code. Do you authorize
WC-062 implementation for the current session?`, the Founder replied exactly `yes i do authorize
WC062 for implementation`. FA-043 records that explicit scoped confirmation and satisfies WC-062
Entry Gate item 7 for this session. It does not substitute for GOA issuance or later Acceptance.

### Authorization Record — GOA-GOAL-005-INST-010-07

| Field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GOA-GOAL-005-INST-010-07 |
| `record_type` | Authorization Record |
| Authorized Institution | INST-010 — Platform IT Expert |
| Contribution scope | Deliver WC062-01 through WC062-07 as one complete implementation contribution under GEP-GOAL-005-INST-013-12 and the approved Amendment 10 package |
| Evidence specification | Task/spec traceability; Docker-only unit, contract, integration, migration, privacy, security, CCT, lint, and coverage evidence; generated-client conformance; Chromium/Firefox/WebKit acceptance at 360x800, 768x1024, and 1440x900; keyboard, screen-reader, RTL, reduced-motion, 200% zoom, offline/replay, Stop, and proportional F8 evidence; at least 90% affected-surface line coverage; fresh independent Data, Security, EA, and CA reviews |
| Participation Window | Five constitutional sessions after valid Acceptance |
| Independence constraint | INST-010 may implement and publish evidence but may not independently review, approve, merge, deploy, activate a provider, or declare Goal completion |
| Excluded authority | Live or paid provider activation or credentials; deployment; DMA-specific speech behavior; production/customer proof; WC-063; architecture reinterpretation; self-review; PR approval; merge; self-merge |
| `issued_by` | INST-013 |
| `issued_at` | 2026-08-12T12:02:00Z |

### Acceptance Record — ACC-GOAL-005-INST-010-07

| Field | Value |
|---|---|
| `institution_id` | INST-010 |
| `goal_id` | GOAL-005 |
| `record_id` | ACC-GOAL-005-INST-010-07 |
| `record_type` | Acceptance Record |
| `produced_at` | 2026-08-12T12:02:01Z |
| `authorization_id` | GOA-GOAL-005-INST-010-07 |
| `acceptance_timestamp` | 2026-08-12T12:02:01Z |
| Decision | ACCEPTED |
| Contribution scope accepted | WC062-01 through WC062-07 as one complete implementation and evidence contribution under GEP-GOAL-005-INST-013-12 |
| Participation Window | 2026-08-12T12:02:01Z through five constitutional sessions |
| Acceptance boundary | No live or paid provider activation or credentials; no deployment; no DMA-specific behavior; no production/customer-proof authority; no WC-063; no architecture reinterpretation; no self-review; no PR approval; no merge; no self-merge |

The Acceptance timestamp is later than GOA issuance, satisfying GEOM G-03 and R2-12. All nine
WC-062 Entry Gate items are complete. INST-010 may begin WC062-01 through WC062-07 within this
accepted Contribution Envelope.

---

## Amendment 11 — WC-063 Founder Administration Prospective Routing

> **SUPERSEDED 2026-08-12:** Founder-sponsored commercial-governance discovery replaced this
> screen-led proposal prospectively with Amendment 12 and WC-064 through WC-069. No contribution,
> GO Authorization, Acceptance, or implementation occurred under Amendment 11.

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-11 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-12 |
| Status | SUPERSEDED — no contribution, acknowledgement, authorization, Acceptance, or implementation occurred |
| Amends | GEP-GOAL-005-INST-013-10 prospectively; Amendments 9–10 and all prior records remain unchanged |

### Purpose And Contribution Order

This amendment routes WC-063 as the separate WC-034 F7 contract for Founder-only Markup
Designer, Trial Budget Configuration, and Coupon Manager capabilities. Product, Solution, Data,
and Security owners contribute first; Enterprise Architecture then integrates the package; an
independent Constitutional Analyst performs readiness review last. The first four contributions
may proceed in parallel but must reconcile before integrated review.

The canonical topology is browser to BP through a generated client, then private authenticated
BP-to-WBE management operations. The direct browser-to-WBE direction in the older acquisition
specification is not an implementation input and must be corrected or explicitly superseded.

| Field | Prospective value |
|---|---|
| Primary implementation Institution | INST-010 — Platform IT Expert, only after every implementation gate closes |
| Contribution scope | WC063-01 through WC063-07 exactly as defined in WC-063 |
| Required inputs | Approved admin workflows and acceptance IDs; canonical BP Founder OpenAPI; private WBE management contracts; versioning/effective-date/immutability blueprint; Founder assurance, CSRF/replay, tenant, service-authentication, financial, conflict, evidence, and reconciliation rules; integrated and CA readiness approval |
| Evidence specification | Task traceability; generated-contract conformance; Docker-only unit/contract/integration/migration/security/financial/CCT evidence; at least 90% affected-surface coverage; exact-360, expanded, keyboard, RTL, axe, privacy/network, margin-floor, stale-version, duplicate, and proportional F8 proof |
| Participation Window | Placeholder only — duration must be approved in the reconciled specification package and begins only after valid INST-010 Acceptance |
| Independent review | Fresh Security and Data review of their implemented surfaces; fresh Enterprise Architecture integrated acceptance; no self-review by INST-010 or INST-013 |
| Completion boundary | One complete unmerged PR after all tasks and independent reviews pass; Founder review and merge remain separate |

### Mandatory Stops

1. This proposed amendment issues and reserves no GO Authorization and authorizes no contribution or implementation.
2. Existing WBE code, completed billing Work Contracts, or architecture text does not substitute for approved management contracts or BP public ingress.
3. Owner contribution authorization records may be defined only after each Decision Space and Evidence Specification is approved; no candidate document may be retroactively treated as an authorized contribution.
4. A future reconciled amendment revision must name every contribution GOA, Acceptance, Participation Window, and independence constraint before owner work begins.
5. A WC-063 implementation GOA may issue only after owner contributions, integrated review, CA readiness approval of the exact reconciled plan, Registrant acknowledgement of that plan, and the separate current-session Founder directive `Authorize implementation of WC-063`.
6. INST-010 must record Acceptance later than GOA issuance before WC063-01 begins.
7. No pricing/policy decision, provider activation, credential setup, deployment, production/customer proof, PR approval, merge, self-review, or self-merge is included.

### Current Decision

WC-063 was groomed but never became implementation-ready or implementation-authorized. Amendment
12 supersedes this prospective route. No CA readiness decision, Registrant acknowledgement,
Founder implementation authorization, GOA, Acceptance, or Participation Window was recorded.

---

## Amendment 12 — Founder Commercial Governance Program Design And Iteration Routing

| Attestation field | Value |
|---|---|
| `institution_id` | INST-013 |
| `goal_id` | GOAL-005 |
| `record_id` | GEP-GOAL-005-INST-013-13 |
| `record_type` | Execution Plan |
| `produced_at` | 2026-08-12 |
| Status | PROPOSED FOR REVIEW — selected planning scope; owner contributions and implementation unauthorized |
| Amends | GEP-GOAL-005-INST-013-11 prospectively; Amendment 11 and WC-063 remain preserved as superseded evidence |

### Purpose

Founder-sponsored discovery determined that WC-063 organized Markup Designer, Trial Budget
Configuration, and Coupon Manager around administration surfaces rather than the institutional
decision outcome required by the Founder. WC-064 replaces that route with one federated Founder
Commercial Governance program design spanning five implementation iterations.

The program must be designed across all iterations before WC-065 is groomed to implementation
depth. WC-066 through WC-069 remain at stable outcome, dependency, and boundary depth until
evidence from earlier iterations justifies detailed grooming.

| Sequence | Work Contract | Routing state | Outcome |
|---|---|---|---|
| Design | WC-064 | selected planning scope; contribution GOAs gated by CA readiness and Registrant acknowledgement | Cross-iteration design spine and detailed WC-065 grooming |
| Iteration 1 | WC-065 | planned candidate; implementation unauthorized | Founder Offerability and Commercial Composition |
| Iteration 2 | WC-066 | planned candidate; implementation unauthorized | Customer and Employed-Agent Oversight |
| Iteration 3 | WC-067 | planned candidate; implementation unauthorized | Operational Exceptions and Reconciliation |
| Iteration 4 | WC-068 | planned candidate; implementation unauthorized | Portfolio Economics and Institutional Learning |
| Iteration 5 | WC-069 | deferred candidate; grooming and implementation unauthorized | Helpdesk and Support Administration |

### Contribution Envelope

| Field | Prospective value |
|---|---|
| Primary Institution | INST-013 coordinates; it does not decide product, commercial, architecture, data, security, implementation, or constitutional questions |
| Contribution scope | WC064-01 through WC064-08 only |
| Owner offices | INST-011, INST-003, INST-004, INST-005, INST-006, INST-007, INST-010, and INST-002 within their respective Decision Spaces and Knowledge Specifications |
| Evidence specification | Attested owner contributions; loaded-context declarations; conflict and missing-contribution record; integrated version-pinned program design; EA approval; independent CA readiness review |
| Participation Window | Begins only after owner-specific GO Authorizations and later Acceptances are recorded; this amendment itself issues none |
| Completion boundary | Approved WC-064 design package and implementation-ready WC-065 grooming record; no source, migration, test, generated artifact, deployment, provider activation, PR approval, or merge |

### Mandatory Stops

1. No WC-064 owner-contribution GO Authorization may be reserved or issued until an independent
	CA Readiness Review approves this exact amendment and a valid Registrant Acknowledgement Record
	referencing `GEP-GOAL-005-INST-013-13` is recorded in the Goal Register.
2. Amendment 12 authorizes no implementation work in WC-065 through WC-069.
3. Each office reads only its Knowledge Specification; a missing contribution remains missing.
4. WBE remains the sole source of billing and financial truth throughout every iteration.
5. WC-064 may define stable concepts and boundaries for all iterations but may detail APIs,
	schemas, migrations, UI components, and implementation tasks only for WC-065 when justified.
6. WC-065 requires approved owner contracts, integrated and Constitutional readiness review,
	Registrant acknowledgement, fresh Founder implementation confirmation, GO Authorization, and
	later Acceptance before any implementation begins.
7. WC-066 through WC-069 require separate future grooming and authorization; completion of WC-064
	or any earlier iteration does not authorize them.
8. Helpdesk remains deferred until real customer-case evidence satisfies WC-069 prerequisites.
9. No direct browser-to-WBE route, duplicate financial truth, silent calculated risk, retroactive
	pricing, fabricated settlement, direct agent modification, or constitutional override is allowed.

### Current Decision

R-099 / `CR-GOAL-005-INST-002-18` independently approves this exact amendment at reviewed commit
`31b80e4`. `ACK-GOAL-005-INST-001-12` below records the Registrant's exact acknowledgement. GEOM
R2-03 conditions 1 and 2 are therefore satisfied for future WC-064 owner-contribution routing.

INST-013 may now define and issue the individual WC-064 owner-contribution GO Authorizations in
dependency order. No contribution has yet been accepted, and no Participation Window is active.
WC-065 through WC-069 remain implementation-unauthorized. No implementation GOA, implementation
Acceptance, deployment authority, PR approval, or merge authority is issued here.

### Registrant Acknowledgement — ACK-GOAL-005-INST-001-12

| Attestation field | Value |
|---|---|
| `institution_id` | INST-001 |
| `goal_id` | GOAL-005 |
| `record_id` | ACK-GOAL-005-INST-001-12 |
| `record_type` | Acknowledgement Record |
| `produced_at` | 2026-08-12T17:35:28Z |
| Acknowledged plan | GEP-GOAL-005-INST-013-13 at reviewed commit `31b80e4` |
| Independent readiness | R-099 / CR-GOAL-005-INST-002-18 — APPROVED |
| Registrant | Yogesh Khandge — Founder, INST-001 |
| Decision | ACKNOWLEDGED — WC-064 owner-contribution routing only |

> "I acknowledge GEP-GOAL-005-INST-013-13 and authorize INST-013 to issue GO Authorizations for
> WC-064 owner contributions exactly as specified in Amendment 12. I understand that this
> acknowledgement does not authorize implementation in WC-064 or any WC-065 through WC-069
> iteration, does not issue any GOA or Acceptance itself, does not invent owner decisions, does
> not activate providers, does not deploy, does not approve or merge a PR, and does not replace
> the separate implementation confirmations required for each future iteration."

The Registrant affirmed this exact statement in the activating session on 2026-08-12. This record
satisfies GEOM R2-03 condition 2 only. The acknowledgement does not itself issue a GOA or
Acceptance, begin a Participation Window, authorize implementation, approve PR #275, or authorize
merge. The INST-002 context that produced R-099 may not serve as the future WC-064 constitutional
owner contributor or subsequent independent package reviewer.

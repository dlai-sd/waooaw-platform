# R-104 — Independent Constitutional Review: GOAL-005 WC-065 INST-002 Legal/Privacy Decision Space Proposal

## G-10 Attestation Record

| Field | Value |
|---|---|
| `institution_id` | INST-002 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-002-22 |
| `record_type` | Clearance Record |
| `produced_at` | 2026-08-13 |

---

## Reviewed Artifact

| Field | Value |
|---|---|
| File | `goals/GOAL-005-wc065-inst002-legal-decision-space-proposal.md` |
| Commit | `f7bd91a5391b276596b6565f3302489448852bb3` |
| SHA-256 | `df318c170da72678d8776e4bc207db20b0b323226293c1cd58420dd3e2cee170` |
| Produced by | INST-CI-001 under FA-044 |
| Proposal record | CR-GOAL-005-INST-CI-001-01 |

---

## Independence Declaration

This review is produced by a fresh INST-002 context that did not participate in drafting the proposal, has not executed any WC-065 contribution prior to this session, and is distinct from INST-CI-001 in all respects. The session memory file `/memories/session/crc-fa044-session-context.md` was not read during this session; BOOTSTRAP was executed first and the review proceeds solely from the proposal document at the stated commit and the canonical reference documents listed in the CA Office Knowledge Specification (BOOTSTRAP.md): `constitution/CONSTITUTION.md`, `constitution/GENESIS.md`, `constitution/ORGANIZATION.md` Office 02, `constitution/INSTITUTION-REGISTRY.md` INST-002 entry, `constitution/GEOM.md` §G-02/G-7/G-10, `security/FOUNDER-ACTIONS.md` FA-044, `blockers/CB-005-wc065-legal-decision-space-2026-08-13.md`, and the PDR-065-07 row in `goals/GOAL-005-wc065-implementation-authorization-package.md`. No implementation artifact, architecture document, or session memory was consulted.

This review satisfies GEOM G-02 (CA Independence Requirement). This reviewer is ineligible to perform the final WC-065 Constitutional readiness review at Stage G-6.

---

## Reference Documents Consulted

| Document | Relevant Provision |
|---|---|
| FA-044 (`security/FOUNDER-ACTIONS.md`) | Activates INST-CI-001 to draft only the narrow amendment assigning exact legal/privacy Decision Space required by WC-065 PDR-065-07 to INST-002; does not ratify amendment or issue GOA/ACC |
| CB-005 (`blockers/CB-005-wc065-legal-decision-space-2026-08-13.md`) | Founder selected Path 2: amend INST-002 charter; independent review and Founder ratification mandatory before any legal-owner GOA may issue |
| Office 02 charter (`constitution/ORGANIZATION.md` §166–261) | INST-002 Decision Space: institutional knowledge; Constitutional Obligations: no architectural recommendations, no business capabilities, no technology selection, no CONFIRMED claims without adversarial evidence, equal service to all offices |
| INST-002 registry entry (`constitution/INSTITUTION-REGISTRY.md` §49–65) | Current Decision Space: claim production, confidence assessment, relationship mapping, contradiction detection, graduation recommendations; Independence Note: separate CA instance for Stage G-6 |
| GEOM G-02 | Validating CA must not have participated in Goal Journey; independence is mandatory |
| GEOM G-7 | INST-013 may issue GO Authorizations only to registered OPERATIONAL Institutions |
| GEOM G-10 | Five mandatory attestation fields; Clearance Record is a valid record_type per 2026-08-08 amendment |
| PDR-065-07 | Requires owner-attributed exact legal basis, grandfathering, remedy, recipient/redaction, payload erasure, and retention values; state `BLOCKED_PENDING_M2_M3` |

---

## Findings

### F-01 — WC-065-Only Minimality and Expiry

**Check:** Does the amendment limit INST-002 authority strictly to WC-065 and expire at WC-065 closure?

The ORGANIZATION.md insert is headed "WC-065 Bounded Legal/Privacy Decision Space (Amendment — FA-044)" and states "Amendment scope: WC-065 only. Expires at WC-065 closure." The Termination clause reads: "This bounded authority terminates upon WC-065 closure. It does not extend to any subsequent Work Contract, Goal, or general charter amendment." The proposed INSTITUTION-REGISTRY.md amendment includes "expires at WC-065 closure" in both the Decision Space field and the Amendment field.

**Result: PASS.** Amendment is minimally scoped. Expiry is explicit and unconditional.

---

### F-02 — Valid G-10 Contribution

**Check:** Does the proposal carry a valid G-10 attestation record?

The proposal's G-10 block contains all five required fields: `institution_id` (INST-CI-001), `goal_id` (GOAL-005), `record_id` (CR-GOAL-005-INST-CI-001-01), `record_type` (Contribution Record), and `produced_at` (2026-08-13). All field values are plausible and internally consistent.

**Result: PASS.** The amendment text is constitutionally valid. INST-CI-001 is present in `constitution/INSTITUTION-REGISTRY.md` under Constitutional Instruments with Status OPERATIONAL and Founder-only activation; the G-10 `institution_id` field satisfies the registry-match requirement.

---

### F-03 — No General Legal Office

**Check:** Does the amendment charter a permanent or general Legal institution?

The amendment amends an existing OPERATIONAL institution's charter temporarily — consistent with CB-005 Resolution Path 2. No new INST-NNN legal institution is created. The ORGANIZATION.md insert explicitly prohibits "Provide general legal advice outside the six PDR-065-07 topics" and the authority terminates at WC-065 closure. No AGENT-ENTRY.md modification is proposed.

**Result: PASS.** No general legal institution is created.

---

### F-04 — Approved Legal Source Documents Without Invented Law

**Check:** Does the amendment require approved legal source documents and prohibit invented legal conclusions?

The amendment mandates: INST-002 must use approved legal source documents and applicable authoritative law as primary inputs. Where law is genuinely ambiguous, INST-002 must record the ambiguity as unresolved rather than resolve it by inference. Where authoritative legal support is insufficient, INST-002 must record that Founder-directed qualified external counsel is required before the decision can be closed.

These are the correct guardrails. The amendment does not name specific source documents — appropriate, because that specification belongs in the GOA execution plan, not in the charter amendment. The proposal imposes no invented legal standard and asserts no legal conclusions itself.

**Result: PASS.** Correct source-document discipline imposed. No invented law present.

---

### F-05 — Preservation of Product/Business/Data/Security/Founder Decision Spaces and Constitutional Floors

**Check:** Does the amendment leave all other Decision Spaces intact and preserve constitutional floors?

The Boundaries block explicitly prohibits INST-002 from making "Product, Business, Data, Security, or Founder-reserved decisions." The Dependency Impact table states: "INST-002 existing Decision Space | Unchanged for all purposes other than WC-065 PDR-065-07 under a valid GOA"; "ORGANIZATION.md all other sections | Unchanged"; "INSTITUTION-REGISTRY.md all other entries | Unchanged"; "Constitutional floors | All preserved; no floor is waived, relaxed, or subject to exception." The No-Authority Boundary section disclaims all twelve categories of authority including every PDR-065-07 topic.

The six PDR-065-07 topic areas addressed (legal basis, grandfathering, remedy, recipient/redaction, payload erasure, retention) were already reserved by the prior Product, Data, Security, and Constitutional owner contributions as protected decisions requiring a legal owner. The amendment does not expand any existing institution's scope; it routes an already-identified gap.

**Result: PASS.** All Decision Spaces preserved. Constitutional floors explicitly non-waivable.

---

### F-06 — GOA Then Later Acceptance Sequence

**Check:** Does the proposed Contribution Sequence correctly prescribe GOA before Acceptance before work?

The Contribution Sequence states (post-ratification): (1) INST-013 issues GOA-GOAL-005-INST-002-NN scoped to GOAL-005/WC-065 and the six PDR-065-07 topics; (2) INST-002 records a corresponding Acceptance; (3) INST-002 produces the Contribution Record within the authorized Participation Window. This is the correct GEOM sequence. No GOA identifier beyond "NN" is pre-assigned, and no Acceptance is claimed to exist. The proposal correctly defers numeric identifiers to the live GOA/ACC exchange.

**Result: PASS.** GOA → Acceptance → Contribution sequence correctly prescribed and not pre-empted.

---

### F-07 — Separate Final CA Readiness Review

**Check:** Does the amendment require a separate CA context for the final WC-065 Constitutional readiness review?

The Boundaries block prohibits INST-002 under this amendment from performing "the final Constitutional readiness review for WC-065." The proposed INSTITUTION-REGISTRY.md entry's Independence Note reads: "The INST-002 context that produces the WC-065 legal/privacy Contribution Record is ineligible to perform the final WC-065 Constitutional readiness review; a separate INST-002 context or INST-001 must perform that review." This is a correct and complete application of GEOM G-02.

**Result: PASS.** Independence for final CA review is structurally enforced in both the charter insert and the registry entry.

---

### F-08 — No Implementation/GOA/Policy Authority in the Proposal

**Check:** Does the proposal assert implementation authority, issue GOAs, or make policy decisions?

The Authority and Status section explicitly disclaims: ratifying any amendment, resolving CB-005, deciding PDR-065-07, issuing any GOA or ACC record, authorizing implementation of WC-065, activating any policy or provider, authorizing WC-066 through WC-069. The No-Authority Boundary section lists twelve specific authority categories the proposal does not exercise. No legal conclusion (basis, grandfathering scope, remedy type, recipient class, redaction rule, erasure timing, retention period) is asserted anywhere in the document.

**Result: PASS.** The proposal is authority-free in all prohibited directions.

---

### F-09 — No Effect on WC-066 Through WC-069

**Check:** Does the amendment leave WC-066 through WC-069 unaffected?

The Dependency Impact table states: "WC-066 through WC-069 | Remain evidence-gated; no change." The Authority and Status section lists non-authorization of WC-066 through WC-069 as an explicit disclaimer. The amendment scope is confined to WC-065/PDR-065-07 and terminates at WC-065 closure; no authority or obligation transfers forward.

**Result: PASS.** WC-066 through WC-069 unaffected.

---

## Verdict

**APPROVED**

All nine test criteria pass. No notes or conditions attach to the amendment text. The proposal is constitutionally valid and ready for Founder ratification.

---

## Mechanical Ratification Conditions

The following conditions must be satisfied in sequence before the amendment is constitutionally effective:

1. This review (R-104 / CR-GOAL-005-INST-002-22) must be committed to the repository.
2. The Founder must explicitly ratify the amendment by issuing a new Founder Action (FA-045 or the next available FA-NNN) in `security/FOUNDER-ACTIONS.md`, referencing this review and the proposal commit `f7bd91a5391b276596b6565f3302489448852bb3`.
3. Upon Founder ratification, an authorized recorder (not INST-002 and not INST-CI-001) must apply the mechanical charter updates:
   a. Insert the "WC-065 Bounded Legal/Privacy Decision Space" block into `constitution/ORGANIZATION.md` Office 02, after the existing Constitutional Obligations block.
   b. Replace the INST-002 entry in `constitution/INSTITUTION-REGISTRY.md` with the proposed amended entry verbatim.
   c. Update CB-005 (`blockers/CB-005-wc065-legal-decision-space-2026-08-13.md`) to record the amendment as ratified and state the remaining open condition (legal-owner GOA not yet issued).
   d. Update `constitution/PROJECT_STATE.md` to reflect the ratified amendment and remaining CB-005 gate state.
4. Only after all mechanical updates are committed and recorded in the Institution Registry may INST-013 issue a legal-owner GO Authorization (GOA-GOAL-005-INST-002-NN) to INST-002.
5. The GOA must be scoped exactly to GOAL-005/WC-065 and the six PDR-065-07 topics. No wider scope is authorized by this review or the amendment.

---

## Authority Boundary

This review:

- Does NOT ratify the proposed amendment.
- Does NOT resolve CB-005.
- Does NOT decide any PDR-065-07 topic (legal basis, grandfathering, remedy, recipient/redaction, payload erasure, or retention).
- Does NOT authorize WC-065 implementation, policy activation, provider activation, or deployment.
- Does NOT issue any GO Authorization or Acceptance record.
- Does NOT authorize WC-066 through WC-069.
- Does NOT constitute the final WC-065 Constitutional readiness review (Stage G-6); that review is a separate obligation, conducted by a separate INST-002 context or INST-001 after the legal/privacy Contribution Record is produced.

Ratification authority belongs exclusively to the Founder (INST-001).

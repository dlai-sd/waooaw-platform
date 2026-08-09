# WC-034 Enterprise Architecture Assessment

**Office:** Enterprise Architect (INST-004)
**Work Contract:** WC-034 Phase A
**Assessment date:** 2026-08-08
**Status:** REVIEW CANDIDATE — INDEPENDENT REVIEW REQUIRED
**Verdict:** ARCHITECTURALLY GROOMED, NOT IMPLEMENTATION-READY
**Constitutional basis:** C-001, C-008, C-023, C-031, C-032, C-042, C-059, C-063, C-065, C-071, C-076, C-095

## Assessment Scope

This assessment covers the hybrid application shell, conversation-first experience, visual system, authentication boundaries, API ownership, responsive/mobile behavior, accessibility/RTL, PWA/privacy behavior, implementation decomposition, and Platform IT Expert readiness.

It does not approve implementation, select product priorities, amend the Platform IT Expert specification, approve its own architecture, or replace Solution Architect and Product Owner review.

## Findings and Disposition

| Severity | Finding | Disposition |
|---|---|---|
| P0 | Transactional cross-channel resume requires WC-060 checkpoints, authentication, deduplication, ordering, replay protection, and acknowledgement semantics | Shell distinguishes merged history from committed handoff; F5 remains blocked until WC-060 |
| P0 | Canonical OpenAPI lacks the complete durable conversation, Plan/Priority Work, Consumption, registration/linking, and Founder management surfaces required by the experience | Owner/gap matrix published; affected components cannot invent or privately call endpoints |
| P0 | Current Platform IT Expert has no dedicated frontend/conversational/PWA skill | Candidate Skill 16 proposal input published; implementation entry gate requires completed new-skill lifecycle |
| P1 | WC-016 conflicts with current identity, conversation, Stop, testing, and sprint-boundary decisions | Formally superseded for future implementation planning; historical artifact preserved |
| P1 | Current Vercel chatbot template stack is incompatible with the accepted WAOOAW baseline | Template limited to interaction reference; no scaffold, auth, persistence, provider, or database adoption |
| P1 | Direct AI SDK/provider use could bypass PR/AIR/CE and Evidence First | INST-005 does not approve `@ai-sdk/react` as an F3 dependency; reconsideration requires the canonical BP/PR stream contract and a presentation-only adapter review |
| P1 | Voice lacks consent, retention, correction, provider, upload, evidence, and accessibility contracts | F6 isolated and blocked until Product/Security/Data/Solution decisions close |
| P1 | Delivery, professional processing, and constitutional evidence could collapse into misleading shared status | Three status systems are normative and have explicit CCT acceptance |
| P1 | Offline/PWA behavior could leak authenticated conversation data | Service-worker and browser-cache boundary prohibits authenticated payload caching |
| P2 | The architecture homepage prototype was rejected by the Founder | Artifact permanently deleted; no composition, token, copy, or implementation authority remains |
| P2 | One broad WC-034 implementation sprint would mix foundation, identity, conversation, continuity, voice, Founder, and hardening risks | F0–F8 decomposition published with independent dependencies and acceptance IDs |

## Architecture Decisions Closed

- One Next.js 14 App Router PWA remains the web stack; no client-only or second SPA.
- Conversation is the primary work surface; relationship views govern and verify it.
- Desktop uses navigation, conversation, and optional context; compact mobile uses edge-to-edge conversation and full-screen secondary views.
- Mobile navigation is Conversation, Plan, Work, and WaooaW Experts.
- `Needs your attention` is the customer label for global priority presentation; it remains absent until server-owned ordering and relationship-scoped resolution contracts exist.
- Authentication remains a distinct Keycloak-brokered surface with mandatory verified email and mobile identity handling.
- Public, authentication, customer, Founder, and system routes have separate layout and authorization ownership.
- The browser does not own tenant identity, lifecycle transitions, priority ranking, evidence truth, model dispatch, or cross-channel commit.
- Business Platform is the sole public ingress for ordinary customer and Founder application traffic; WBE and ordinary PR execution remain internal, with only the dedicated Emergency Stop path excepted.
- `@ai-sdk/react` is not an F3 architecture dependency and may not be introduced before the canonical BP/PR stream contract is approved and independently reviewed.
- `web/WAOOAWHome.html` is the Founder-approved inspiration source for logo treatment, fonts, color themes, and design language across public and authenticated surfaces; adaptations must retain recognizable continuity while ratified visual and constitutional constraints control conflicts.
- WC-016 is not controlling for future implementation where it conflicts with WC-034 and GOAL-005.

## Product Decisions Closed by INST-011

- Customer-visible source labels are `My WaooaW Experts`, `Needs your attention`, `Conversation`, `Plan`, `Work`, `Results`, `Usage & budget`, and `Rights & control`; internal terms do not become navigation copy.
- The first customer conversation release is text-only. Attachments, voice, F5/WC-060 cross-channel notification suppression, global priority aggregation, and public Concierge are deferred and leave no enabled or dead-end controls.
- F8 is a mandatory proportional gate for every selected release, not a successor owned only by F7 Founder administration.
- Skill 16 receives an INST-011 `APPROVE_FOR_SPEC` recommendation and remains blocked on Founder decision, Type 1 execution, activation gate, and independent EA review.

## Decisions Routed, Not Delegated

| Decision | Required owner | Blocking component |
|---|---|---|
| Attachment types, limits, scanning, and preview | Product Owner + Security + service owner | F3 attachments |
| Voice consent, retention, transcript correction, provider, and evidence lineage | Product Owner + Security/Data/Solution | F6 |
| Active-channel notification suppression | Product Owner + Solution Architect | F5 |
| Global priority ordering contract | Product Owner + Business Platform owner | F4 |
| Missing canonical service operations | Respective BP, PR, WBE, and identity owners | F2, F3, F4, F7 |

## Capability Traceability

| Experience surface | Capability basis |
|---|---|
| Public professionals and pre-hire disclosure | 1.1 Evaluate Professional Candidates; 1.6 Browse Agent and Skill Catalogue |
| Registration and session | 6.1 Authenticate and Authorize Customers; 6.2 Isolate Tenant Data |
| Conversation and configuration | 1.7 Configure Agent via Conversation; AD-013 |
| Plan, goals, and work | 1.2 Configure Employment Terms; 1.3 Define Decision Space; 4.5 Set and Update Skill Goals |
| Actions and approvals | 2.1 Review Proposed Actions; 2.2 Approve or Reject; 2.3 Confirm Scope-Boundary Crossings |
| Emergency Stop | 2.4 Exercise Emergency Stop; AD-001 |
| Activity and evidence | 2.5 Monitor Activity; 2.6 Audit Evidence Ledger; 6.3 Record Constitutional Evidence |
| Performance | 4.1 Assess Performance; 2.7 Monitor Skill Performance; AD-012 |
| Consumption and billing | 6.5 Bill Customers with Pro-Rata Precision; AD-014 |
| Pause, resume, and lifecycle | 5.1 Suspend Employment; 5.2 Terminate Employment; C-034 |

## Implementation Entry Criteria

Implementation remains prohibited until all conditions are true:

1. INST-005 approves component ownership, API boundaries, failure semantics, and dependency decisions.
2. INST-011 approves information architecture, labels, release composition, deferred decisions, and customer acceptance.
3. Missing service contracts required by the selected component are approved and generated-client compatible.
4. The Platform IT Expert skill proposal completes Product Owner review, Founder approval, Type 1 update, activation gate, and independent EA review.
5. Product/Security/Data/Solution decisions required by attachments, continuity, voice, or Founder operations are complete for the selected release.
6. The Founder separately authorizes the selected implementation Work Contract for the execution session.

## Independent Review Request

INST-005 is requested to review:

- route, rendering, service, stream, generated-client, state, continuity, and failure ownership;
- API gap routing, the BP public-ingress invariant, and the decision not to adopt an AI SDK dependency before the stream contract;
- F0–F8 dependency ordering and component separability.

INST-011 is requested to review:

- customer information architecture, navigation, labels, progressive registration, and relationship mental model;
- release composition, deferred voice/attachment/notification choices, and customer-visible acceptance;
- WC-016 supersession and proposed child Work Contract boundaries.

Both reviewers must produce independent records. INST-004 cannot approve this package under C-065.

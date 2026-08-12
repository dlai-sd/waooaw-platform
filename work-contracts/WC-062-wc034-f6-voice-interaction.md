# Work Contract 062 — WC-034 F6 Voice Interaction

**Goal:** GOAL-005 — Agent Employment Experience Program
**Parent:** WC-034 F6 — Voice Interaction
**Track:** Generic WAOOAW platform capability
**Grooming Office:** Goal Orchestrator (INST-013)
**Implementation Office:** Platform IT Expert (INST-010)
**Required specification owners:** Product Owner (INST-011), Solution Architect (INST-005), Data Architect (INST-006), Security Architect (INST-007)
**Integrated architecture reviewer:** Enterprise Architect (INST-004)
**Readiness reviewer:** Constitutional Analyst (INST-002)
**Status:** IMPLEMENTATION COMPLETE — WC062-01 THROUGH WC062-07 DONE; R-096/R-097/R-098 APPROVED; UNMERGED PR PENDING
**Constitutional basis:** C-001, C-023, C-042, C-049, C-051, C-059, C-060, C-061, C-063, C-065, C-071, C-076, C-080; ADR-017, ADR-020, ADR-023, ADR-029

## Outcome

Provide one reusable WAOOAW voice-contribution capability for professional conversations. An authenticated customer can record, review, correct, and explicitly send a voice contribution in a supported language without weakening text fallback, consent, privacy, Evidence First, Emergency Stop, accessibility, or tenant isolation.

F6 is a platform capability, not a DMA-specific feature. Agent specifications may declare whether and how they use voice, but they must consume the same governed capture, transcription, correction, evidence, and retention boundary.

## Scope Boundary

### Included

- browser permission, record, pause, resume, cancel, duration, playback, upload progress, retry, and explicit send;
- supported-language selection, transcription confidence, correction before consequential use, and text fallback;
- authenticated BP public boundary and generated TypeScript client;
- internal PR/AIR transcription orchestration only through approved service contracts;
- consent, retention, erasure, payload/evidence separation, and evidence lineage;
- MIME/content validation, size and duration limits, malware scanning, replay/idempotency protection, encryption, and privacy-safe errors;
- keyboard and screen-reader operation, RTL, reduced motion, offline/reconnect, and stable exact-360px composition; and
- proportional F8 contract, browser, accessibility, privacy, security, coverage, lint, build, and regression evidence.

### Excluded

- voice cloning, biometric voiceprints, speaker identification, synthetic impersonation, or Digital Twin capability;
- agent-specific speech policy, advice quality, vocabulary, or domain execution;
- provider activation, credentials, production deployment, live-customer proof, or unsupported-language claims;
- attachment or general media upload beyond the approved F6 audio envelope;
- acceptance inferred from recording, upload, transcription, silence, timeout, or low-confidence text;
- direct browser access to PR, AIR, an MCP server, object storage, or a transcription provider; and
- any source, test, migration, generated client, build artifact, or provider configuration before every entry gate below closes.

## Required Specification Contributions

| Order | Institution | Required contribution | Closure evidence |
|---|---|---|---|
| 1 | INST-011 Product Owner | Supported first-release channels/languages, consent and correction journey, text fallback, customer-visible confidence and failure states, duration/size policy, and dedicated voice acceptance matrix | Attested Product Contribution and Learning Records |
| 2 | INST-005 Solution Architect | Canonical BP public operations and schemas, internal PR/AIR ownership, upload/transcription/correction sequence, provider abstraction, generated-client boundary, idempotency, failure semantics, and C-095 determination | Approved component contract and BP OpenAPI update |
| 3 | INST-006 Data Architect | Audio/transcript classification, minimisation, storage ownership, retention, erasure, evidence/payload separation, lineage, regional-language metadata, and migration decision | Approved data contract and migration blueprint or explicit no-migration decision |
| 4 | INST-007 Security Architect | Permission/consent threat model, content validation, malware scanning, size/duration limits, authenticated upload, replay prevention, encryption, provider/data-residency controls, abuse controls, and privacy-safe observability | Approved security contract and adversarial CCT matrix |
| 5 | INST-004 Enterprise Architect | Integrated dependency and architecture review across Orders 1–4; confirms no policy or ownership decision remains delegated to code | APPROVED integrated readiness review |
| 6 | INST-002 Constitutional Analyst | Independent readiness review of the execution-plan amendment and this Work Contract | APPROVED Constitutional Clearance/Readiness Record |

Orders 1–4 may proceed in parallel but must reconcile into one version-pinned package before Order 5. INST-013 coordinates and verifies records; it does not author these domain decisions or review its own orchestration.

## Implementation Tasks

Implementation tasks remain dormant until the Entry Gate is fully satisfied.

| Task | Scope | Model hint | Status |
|---|---|---|---|
| WC062-01 | Implement the approved BP voice-contribution public contract, authenticated tenant/relationship authority, idempotency, Evidence First transitions, privacy-safe failures, and any approved persistence/migration blueprint. | reasoning | done |
| WC062-02 | Implement the approved internal PR/AIR transcription orchestration and provider-neutral adapter boundary; no browser/provider coupling and no paid or live provider activation. | reasoning | done |
| WC062-03 | Implement consent, confidence, correction, retention/erasure, evidence lineage, unresolved outcome, and text-fallback behavior exactly as approved. | reasoning | done |
| WC062-04 | Generate the TypeScript client without manual patches and implement the web recorder/review/correction/send experience with stable dimensions and no dead-end controls. | reasoning | done |
| WC062-05 | Add unit, contract, integration, migration where applicable, tenant-isolation, replay, malformed-content, malware, downgrade, consent, retention, erasure, provider-failure, offline, and Emergency Stop preservation tests. | auto | done |
| WC062-06 | Execute the dedicated voice acceptance matrix across Chromium, Firefox, WebKit, exact 360×800, intermediate, and expanded viewports, including keyboard, screen reader, RTL, reduced motion, and text fallback. | auto | done |
| WC062-07 | Run proportional F8 validation: generated-contract conformance, privacy/security inspection, Docker-only regression, at least 90% affected-surface line coverage, lint, strict TypeScript, production build, and independent implementation review. | auto | done |

## Entry Gate — All Required

1. Orders 1–6 above are complete, attested, and mutually consistent.
2. The dedicated F6 voice acceptance IDs exist in `architecture/reference/ux/hybrid-ui-acceptance-contract.md`.
3. The canonical BP OpenAPI and all internal owner contracts are approved and generated-client compatible.
4. Data and Security contracts close consent, retention, erasure, scanning, replay, encryption, residency, and evidence-lineage decisions.
5. A GOAL-005 Execution Plan amendment defines the contribution scope, evidence specification, Participation Window, review sequence, and exclusions.
6. The Registrant acknowledges that exact amendment after CA readiness approval.
7. The Founder explicitly authorizes WC-062 implementation for the current session.
8. INST-013 issues a WC-062-specific GO Authorization only after items 1–7.
9. INST-010 records Acceptance after the GO Authorization issuance timestamp.

`G5 CLEAR`, this Work Contract, a future backlog priority, or completion of specification grooming does not satisfy items 6–9.

## Implementation Definition Of Done

- A customer can record, review, correct, and explicitly send supported audio while text remains a complete fallback.
- No audio or transcript becomes consequential input before the approved consent and correction gates pass.
- Tenant, relationship, participant, and assurance boundaries pass positive and adversarial tests.
- Audio payload retention/erasure and durable constitutional evidence remain correctly separated.
- Malformed, oversized, replayed, malicious, unsupported, low-confidence, provider-unavailable, and offline cases fail safely and honestly.
- Emergency Stop remains visible and effective throughout recording, upload, transcription, correction, and retry.
- Generated-client conformance, all assigned acceptance IDs, Docker suites, at least 90% affected-surface coverage, lint, build, accessibility, privacy, and security gates pass.
- Fresh independent implementation review approves one complete unmerged PR.

## Current Readiness Decision

**IMPLEMENTATION AUTHORIZED AND ACCEPTED.** Entry Gate items 1–6 remain approved under R-093,
R-094, and ACK-GOAL-005-INST-001-11. FA-043 closes item 7 for this session;
GOA-GOAL-005-INST-010-07 and the later ACC-GOAL-005-INST-010-07 close items 8–9.

Implementation is limited to WC062-01 through WC062-07. Live or paid provider activation,
credentials, deployment, WC-063, production/customer proof, PR approval, merge, self-review, and
self-merge remain unauthorized.

## Implementation Closure

WC062-01 through WC062-07 are complete in `09f7056..57a1494`. Integrated executor evidence is
recorded in `goals/GOAL-005-wc062-implementation-evidence.md`. Fresh independent implementation
reviews R-096 (Security), R-097 (Data), and R-098 (Enterprise Architecture) approve the repaired
range for unmerged PR submission. Provider/scanner activation, credentials, deployment,
production/customer proof, WC-063, PR approval, merge, and self-merge remain excluded.
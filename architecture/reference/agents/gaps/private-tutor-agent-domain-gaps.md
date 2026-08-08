# Private Tutor Agent — Domain Gap Register

**Agent:** Private Tutor Professional v1.1 (`PRIVATE_TUTOR_INDIA`)
**Purpose:** Grooming input for customer release; not an approved implementation backlog
**Evidence date:** 2026-08-08
**Current status:** Activation Gate pass recorded; no standalone review, Founder approval, customer activation, or customer-proof evidence; not activated

## Release Boundary

The first release must let a parent configure and employ a tutor for one child, run a child-safe voice and whiteboard lesson for one board/class/subject scope, measure comprehension without surveillance, send an evidence-backed parent report, and let the parent stop or suspend sessions immediately.

Shared WAOOAW discovery, interview runtime, trial/hire, common billing lifecycle, generic alerts, and employment lifecycle capabilities are excluded from this register.

## Evidence Sources

- `architecture/reference/agents/private-tutor-agent.md` §8 (controlling dependency inventory; the shared skill dependency register has no Tutor section)
- `architecture/reference/billing/billing-profiles/private-tutor-billing-profile.md`
- `simulation/018-private-tutor-simulation.md`
- `simulation/SIM-018-constitutional-dna-inheritance-walkthrough.md`
- `tests/QA-STRATEGY.md`
- `architecture/reference/platform-component-registry.yaml` and `constitution/PROJECT_STATE.md` (platform maturity and customer-proof baseline)

## Domain Gaps

| Priority | Gap | Customer impact | Grooming outcome |
|---|---|---|---|
| P0 | Parent-employer, minor-beneficiary, guardian-consent, and payer roles are not operational | A minor could receive service without valid authority or correct data access | Relationship model, verified guardian consent, custody-change process, role-specific access, revocation, and audit |
| P0 | Child-safe lesson application is not implemented | The tutor has no real teaching environment | Mobile/web lesson shell, voice, text, whiteboard, no-camera enforcement, reconnection, accessibility, and session-quality telemetry |
| P0 | Whiteboard authority and synchronization are incomplete | Student and tutor actions may conflict or expose inappropriate content | Separate drawing areas, permissions, real-time sync, undo/history, moderation, export/retention, and failure recovery |
| P0 | Parent Emergency Stop is not connected to the lesson runtime | Parent cannot reliably freeze an unsafe or unwanted session | WhatsApp and app stop paths, session freeze within 250ms, screen clearing, child-safe message, evidence, and controlled reactivation |
| P0 | Commercial information is not structurally isolated from the child | Billing status or upsell may exploit or distress a minor | Parent-only billing context, child-channel deny rules, grace behavior, completed-session protection, and C-060 tests |
| P0 | Child-safety/content moderation and statutory incident handling are not executable | Unsafe content may reach a minor without mandatory response | Age policy, content classifier, CSAM protocol, immediate halt/purge/evidence/reporting, guardian notification boundaries, and runbook |
| P1 | Curriculum/syllabus knowledge is not operationally sourced or versioned | Lessons may teach the wrong board, class, chapter, or exam pattern | Initial board/subject scope, licensed/public sources, version/date, ingestion review, citation, and correction process |
| P1 | Learning profile and comprehension signals are simulation-only | Tutor cannot consistently adapt or prove learning progress | Privacy-minimal signal model, false-confirmation detection, mastery update, explainability, parent correction, and bias checks |
| P1 | Regional voice and teaching-story content are not production-ready | Teaching quality may degrade across language, topic, or culture | Voice provider, pronunciation tests, curriculum-safe story bank, age/topic metadata, and content review |
| P1 | Parent reporting lacks an executable evidence and recipient model | Reports may be generic, delayed, or visible to the wrong party | Post-session note, periodic report schema, source evidence, concern escalation, delivery receipt, and co-guardian rules |
| P1 | Academic-integrity controls are not integrated across homework and assessment | Tutor may complete assessed work for the student | Assessment detection, hint ladder, refusal/redirect, parent disclosure, and audit evidence |
| P1 | Trial data minimization and deletion are not proven | Child data may persist without an employment relationship | Draft profile, minimal collection, conversion boundary, seven-day deletion, guardian request, and deletion evidence |
| P2 | Schedule-quality recommendations are not operational | Repeated low-engagement slots may continue unnoticed | Engagement trend, recommendation threshold, parent confirmation, timetable update, and no blame language |
| P2 | Multi-child household separation is unproven | Learning history, billing, or reports may cross siblings | Per-child contract/context/bucket, shared guardian controls, sibling isolation tests, and household summary rules |

## Specialized Customer Interface

- Parent configuration and guardian controls
- Child lesson room with voice, text, and interactive whiteboard
- Schedule, makeup sessions, and session readiness
- Child-safe pause screen and parent Emergency Stop
- Topic/mastery map, learning signals, and evidence-backed parent reports
- Curriculum/board/version visibility and correction request

## Release Decisions and Dependencies

1. Select one board, class range, and subject for the first customer proof.
2. Approve the guardian/child data model and statutory child-safety operating procedure.
3. Select voice and whiteboard technology with accessibility and moderation support.
4. Define educational-record retention, guardian deletion rights, and trial-data deletion.

## Grooming Exit

Every accepted item must include guardian authority, child-safe failure behavior, C-060/C-061 controls, accessibility, executable tests, incident response, and real parent/student acceptance evidence.
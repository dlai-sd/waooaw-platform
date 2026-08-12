# WC-062 Voice Product Contract

| Field | Value |
|---|---|
| Institution | INST-011 — Product Owner |
| Goal / Work Contract | GOAL-005 / WC-062 F6 |
| Authorization / Acceptance | GOA-GOAL-005-INST-011-09 / ACC-GOAL-005-INST-011-09 at 2026-08-12T10:00:31Z |
| Contribution / Learning | CR-GOAL-005-INST-011-10 / LR-GOAL-005-INST-011-07 |
| `produced_at` | 2026-08-12T10:18:09Z |
| Status | COMPLETE — product specification only |

## Product Decision

F6 first release supports authenticated browser conversations only. English (`en-IN`), Hindi
(`hi-IN`), and Marathi (`mr-IN`) are transcription-supported launch languages. Every other locale
keeps a complete text composer and may not be described as transcription-supported until a later
approved product contribution adds it.

The default customer operating limit is 3 minutes and 15 MiB per draft. Security may impose a
lower effective limit but not silently raise either value. The UI announces the effective limit
before recording and before retry.

Recording permission, capture, transcription, correction, and send are distinct states. Browser
permission is requested only after the customer invokes voice. Permission denial or revocation
immediately returns focus to the complete text path. Recording, upload, transcription, playback,
correction, silence, timeout, or confidence never means send consent. Only an explicit enabled
`Send voice contribution` command sends the reviewed text and audio under the approved contract.

## Customer Journey

1. The authenticated customer selects voice; the UI names microphone use, transcription,
   correction, retention summary, and the always-available text alternative.
2. Record, pause, resume, cancel, timer, and draft status remain explicit. Cancel discards the
   unsent draft subject to Data-confirmed deletion.
3. After upload, the customer can play audio and review transcript. The transcript is editable.
4. Confidence is displayed as `high` (>=0.90), `review` (0.70–0.89), or `low` (<0.70). `review`
   and `low` require an explicit correction/confirmation action before Send is enabled. Missing,
   unsupported, or unavailable transcription routes to text without claiming failure-free voice.
5. Send creates a pending state until authoritative evidence confirmation. Unknown outcomes are
   reconciled before retry with the same idempotency identity.
6. Permission, upload, transcription, scanning, offline, Stop, and retention failures name a safe
   next action without exposing provider or security internals.

## Customer Rights And Accessibility

Customers can inspect audio and corrected transcript before send, cancel before send, request
payload erasure after send, and understand that durable constitutional evidence is retained even
when payload is erased. Emergency Stop remains visible and independent throughout. The complete
journey must work by keyboard and screen reader, at 200% zoom, in RTL, reduced motion, exact
360x800, 768x1024, and 1440x900. Unsupported locales use localized text fallback and never a
fabricated transcription.

## Acceptance Ownership

The canonical acceptance contract contains `UX-VOICE-01` through `UX-VOICE-12` and
`CCT-VOICE-EF-01`, `CCT-VOICE-TENANT-01`, `CCT-VOICE-REPLAY-01`, and `CCT-VOICE-PRIV-01` with the
exact Amendment 10 meanings. Product owns customer-visible scenario meaning; Solution, Data, and
Security own the mechanisms and evidence needed to pass them.

## Boundaries And Dependencies

This record does not define endpoints, schemas, persistence, encryption, scanning, provider
selection, implementation, or review. Solution must expose generated-client-compatible states;
Data must confirm payload/evidence retention and erasure; Security must confirm hard validation
ceilings and safe error floors. Any conflict returns to the accountable owner before EA approval.

## Learning Record — LR-GOAL-005-INST-011-07

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-011-07 |
| `record_type` | Learning Record |
| `improvement_signal` | Voice readiness requires the correction and text-fallback journey to be decided before provider or recorder implementation; language support must be claimed per approved locale, not inferred from provider availability. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |
| `produced_at` | 2026-08-12T10:18:09Z |

**Verdict:** CR-GOAL-005-INST-011-10 satisfies Amendment 10 Order 1A within INST-011 Decision
Space. It authorizes no implementation or self-review.

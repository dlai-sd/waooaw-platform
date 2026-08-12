# WC-062 Voice Security Contract

| Field | Value |
|---|---|
| Institution | INST-007 — Security Architect |
| Goal / Work Contract | GOAL-005 / WC-062 F6 |
| Authorization / Acceptance | GOA-GOAL-005-INST-007-08 / ACC-GOAL-005-INST-007-08 at 2026-08-12T10:07:19Z |
| Contribution / Learning | CR-GOAL-005-INST-007-08 / LR-GOAL-005-INST-007-03 |
| `produced_at` | 2026-08-12T10:18:12Z |
| Status | COMPLETE — security specification only |

## Threat Boundary

Protected assets are raw audio, transcript/correction content, consent and send decisions,
lineage, idempotency identities, provider credentials, and encryption keys. Threats include hidden
or stale microphone permission, malicious media, decompression bombs, malware, replay, cross-tenant
or cross-relationship access, confused deputy calls, provider exfiltration, transcript tampering,
content leakage through telemetry/errors, cost abuse, and Emergency Stop bypass.

## Non-Weakenable Controls

1. Browser permission is necessary but insufficient. Every public operation requires authenticated
   actor, tenant-from-JWT, active relationship authority, accepted contract major, and allowed state.
2. Each upload is bound to actor, tenant, relationship, session, operation, idempotency key, payload
   hash, and expiry. Same key/different hash is rejected; cross-boundary reuse is denied.
3. Effective Product limits must not exceed 5 minutes or 25 MiB. Validate declared MIME, magic
   bytes, container, codec, duration, decoded size, and stream length. Initial permitted containers
   are WebM/Opus, Ogg/Opus, and WAV PCM; MP3/M4A remain blocked until independently threat-tested.
4. Upload enters quarantine before transcription. Scanning is fail-closed for malware, malformed
   content, parser timeout, archive/polyglot content, and unavailable scanner. Quarantined content
   is never transcribed, replayed, downloaded, or sent.
5. Audio and transcript are encrypted in transit and at rest with environment-approved keys from
   secret custody. Provider credentials never enter browser/BP payloads or logs. Provider routing
   is PR-to-AIR only through authenticated private service identity.
6. Provider contracts prohibit training, secondary use, and retention beyond the request. Region
   must satisfy the approved Data residency contract; no fallback crosses that boundary silently.
7. Consent to record, transcribe, correct, and send remains separable. Only the approved transcript
   version and audio hash may bind the send decision. Silence, timeout, confidence, or upload never
   grants consent.
8. Emergency Stop is checked independently during capture, upload, transcription, correction, and
   retry. Stop prevents new ordinary work, cancels/bounds in-flight work, and does not depend on the
   provider or scanner path.
9. Errors and observability contain opaque correlation/session IDs, coarse state, control outcome,
   and latency only. They exclude audio, transcript, tenant/relationship identifiers, filenames,
   locale where identifying, provider body, malware signature, token, key, or storage URI.
10. Rate limits cover session creation, bytes, duration, concurrent transcription, retry, and
    erasure without applying any limit that delays Emergency Stop.

## Privacy-Safe Failure Contract

Public outcomes are limited to `permission_required`, `invalid_media`, `limit_exceeded`,
`quarantined`, `temporarily_unavailable`, `review_required`, `not_authorized`, `conflict`,
`unknown`, and `stopped`. Detailed scanner, provider, tenant, relationship, and policy reasons stay
inside restricted evidence. Anti-enumeration responses do not reveal whether another tenant,
relationship, session, or payload exists.

## Adversarial CCT Matrix

| ID | Required proof |
|---|---|
| CCT-VOICE-SEC-01 | Permission grant cannot bypass authenticated relationship and state authorization |
| CCT-VOICE-SEC-02 | MIME/magic/container/codec disagreement and decompression bomb fail before transcription |
| CCT-VOICE-SEC-03 | Malware or unavailable scanner quarantines fail-closed with no provider dispatch |
| CCT-VOICE-SEC-04 | Oversize, over-duration, truncation, and chunk-order attacks fail without partial success |
| CCT-VOICE-SEC-05 | Same-key/different-hash, replay, and cross-session reuse are rejected |
| CCT-VOICE-SEC-06 | Cross-tenant, cross-relationship, and confused-deputy calls expose no payload or existence |
| CCT-VOICE-SEC-07 | Transcript or correction tampering breaks hash/version binding and cannot be sent |
| CCT-VOICE-SEC-08 | Logs, traces, metrics, URLs, and errors contain no voice content or sensitive identifiers |
| CCT-VOICE-SEC-09 | Provider retention/training/residency or credential failure blocks dispatch truthfully |
| CCT-VOICE-SEC-10 | Emergency Stop remains effective during every voice state and provider/scanner outage |
| CCT-VOICE-SEC-11 | Erasure requires current authority and cannot erase immutable evidence |
| CCT-VOICE-SEC-12 | Cost/rate abuse is bounded without delaying Stop or fabricating completion |

These supplement, not replace, Amendment 10 `CCT-VOICE-EF-01`, `CCT-VOICE-TENANT-01`,
`CCT-VOICE-REPLAY-01`, and `CCT-VOICE-PRIV-01`.

## Boundaries And Dependencies

Product owns customer behavior and operating limits below the hard ceiling. Solution owns operation
and service shapes. Data owns classification, retention, erasure, and residency truth. Security
owns the floors above and does not select product copy, API shape, persistence schema, provider, or
implementation.

## Learning Record — LR-GOAL-005-INST-007-03

| Field | Value |
|---|---|
| `institution_id` | INST-007 |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-007-03 |
| `record_type` | Learning Record |
| `improvement_signal` | Voice security must validate decoded media and bind consent, transcript version, and idempotency identity across service boundaries; browser permission and file extension are not security controls. |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |
| `produced_at` | 2026-08-12T10:18:12Z |

**Verdict:** CR-GOAL-005-INST-007-08 satisfies Amendment 10 Order 1D within INST-007 Decision
Space. It authorizes no implementation, provider activation, deployment, or self-review.

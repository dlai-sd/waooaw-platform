# WAOOAW Hybrid Application UI Acceptance Contract

**Document type:** Architecture Reference — Executable Acceptance
**Office:** Enterprise Architect (INST-004)
**Work Contract:** WC-034 / WC034-A06
**Status:** RATIFIED - WC-034 released scope accepted through independent review and Founder merge
**Normative parents:** `hybrid-application-shell.md`, `hybrid-visual-system-contract.md`, `constitutional-ux-vocabulary.md`
**Constitutional basis:** C-001, C-002, C-009, C-023, C-042, C-059, C-063, C-065, C-071, C-076

## Purpose

This contract defines the executable evidence required before WC-034 implementation may be called complete. It specifies test behavior, not test code. INST-010 implements these checks only after separate Founder authorization.

No acceptance check may use production fallback mocks to manufacture success. Service-dependent scenarios use controlled contract fixtures or an integrated test environment with the same generated schemas.

## Required Test Layers

| Layer | Tooling boundary | Required evidence |
|---|---|---|
| Component | Jest + Testing Library | States, keyboard behavior, accessible names, locale/direction, error recovery |
| Contract | Generated TypeScript client + fixture server | Schema conformance, auth failure, missing capability, conflict, unknown outcome |
| Browser | Playwright | Routes, responsive composition, auth boundaries, PWA, offline/reconnect, screenshots |
| Accessibility | `@axe-core/playwright` + keyboard assertions | Zero critical axe violations and no unreviewed serious violations |
| Visual | Playwright screenshot comparison | Light/dark, compact/expanded, LTR/RTL, loading/error/stopped states |
| Quality | Jest coverage + Next.js lint/build | At least 90% changed interactive line coverage; strict TypeScript and production build pass |

Chromium, Firefox, and WebKit are required for the browser suite. Exact 360×800 compact and 1440×900 expanded projects are mandatory; 768×1024 intermediate coverage is required for layout transitions.

## Acceptance Matrix

### Shell and Route Ownership

| ID | Scenario | Pass condition |
|---|---|---|
| UX-SHELL-01 | Public direct navigation | No authenticated relationship request, customer navigation, or protected payload is emitted |
| UX-SHELL-02 | Authenticated relationship direct navigation | Server validates session and relationship access before protected data renders |
| UX-SHELL-03 | Founder route without Founder claim | `/403` is rendered without Founder data or navigation disclosure |
| UX-SHELL-04 | Safe return target | External, protocol-relative, and unauthorized return targets are rejected |
| UX-SHELL-05 | Loading and route error | Layout remains stable; error states provide next action and correlation reference where available |
| UX-SHELL-06 | Capability contract absent | Feature is unavailable or blocked; no private endpoint or fabricated successful state is used |
| UX-CONTRACT-01 | Public service ingress | Ordinary customer and Founder traffic uses generated BP contracts; browser bundles and network traces contain no private WBE or PR URL, except the dedicated Emergency Stop path |

### Responsive and Native-Mobile Behavior

| ID | Scenario | Pass condition |
|---|---|---|
| UX-RESP-01 | Every required route at 360×800 | `scrollWidth <= clientWidth`; no clipped controls or horizontal overflow |
| UX-RESP-02 | Mobile keyboard opens in composer | Input, send, release-enabled composer controls, and Stop remain reachable; layout does not jump incoherently |
| UX-RESP-03 | Mobile context navigation | Plan, Work, Results, Usage & budget, and Rights & control open full-screen and return focus/context correctly |
| UX-RESP-04 | Intermediate layout | Conversation remains at least 360px; context does not compress beside it |
| UX-RESP-05 | Expanded layout | Navigation, conversation, and context meet minimum widths without overlap |
| UX-RESP-06 | Long translated labels and 200% zoom | Controls retain meaning and content reflows without loss or overlap |

### Authentication and Identity

| ID | Scenario | Pass condition |
|---|---|---|
| UX-AUTH-01 | Login/register path switch | Locale and non-secret values persist; secrets and one-time codes do not |
| UX-AUTH-02 | Verified federated email | Verified claim is accepted only through Keycloak-brokered server session |
| UX-AUTH-03 | Provider lacks verified email | Separate verification is required; account is not completed |
| UX-AUTH-04 | Existing WhatsApp identity links on web | Deterministic linking path is used; duplicate customer is not minted |
| UX-AUTH-05 | High-risk action | Fresh or stronger assurance is requested without losing relationship context |
| UX-AUTH-06 | Session expiry with draft | Non-secret draft survives safe re-entry; protected content is hidden immediately |

### Conversation and Work

| ID | Scenario | Pass condition |
|---|---|---|
| UX-CONV-01 | Send message | Draft becomes sending, then server-accepted or failed; no premature delivered/evidence state |
| UX-CONV-02 | Retry failed send | Original idempotency key and payload hash are reused; one message appears after reconciliation |
| UX-CONV-03 | Reconnect after uncertain outcome | Authoritative cursor is fetched before retry; duplicate delivery cannot duplicate the message or action |
| UX-CONV-04 | Stream response | Content is announced politely, cancellation works, focus remains stable, partial content is labelled |
| UX-CONV-05 | Delivery, processing, evidence | Each status has distinct icon, text, accessible name, and semantic meaning |
| UX-CONV-06 | Structured cards | Action, Plan, Deliverable, and Decision cards expose owner, state, effect, and keyboard-operable commands |
| UX-CONV-07 | Multiple professionals | Switcher changes the complete relationship context; drafts and item links never cross relationships |
| UX-CONV-08 | Needs your attention, when released | Browser displays server order and does not calculate an independent priority ranking; destination is absent before the aggregate contract is approved |

### Voice Interaction (F6/WC-062 Only)

| ID | Scenario | Pass condition |
|---|---|---|
| UX-VOICE-01 | Permission denied or unavailable | A complete text path remains focused and usable; no recording or transcription success is implied |
| UX-VOICE-02 | Capture controls | Record, pause, resume, cancel, timer, playback, and draft status remain truthful and dimensionally stable |
| UX-VOICE-03 | Review and explicit send | Recording, upload, transcription, playback, or correction never sends; only the enabled explicit send command does |
| UX-VOICE-04 | Low confidence or unsupported language | Review/low confidence requires correction or confirmation; unsupported language preserves text fallback before consequential use |
| UX-VOICE-05 | Upload or provider failure | Recovery preserves the draft and idempotency identity without duplicate contribution or fabricated success |
| UX-VOICE-06 | Offline and reconnect | Authoritative session state is reconciled before retry; the original idempotency identity is retained |
| UX-VOICE-07 | Invalid or quarantined media | Malformed, unsupported, oversized, over-duration, or quarantined content fails safely without provider dispatch or private detail |
| UX-VOICE-08 | Retention and erasure | Customer-visible treatment distinguishes erasable payload from durable constitutional evidence |
| UX-VOICE-09 | Responsive composition | Exact 360x800, 768x1024, and 1440x900 preserve composer controls and Stop without overflow or overlap |
| UX-VOICE-10 | Keyboard and screen reader | Record/review/correct/send or the equivalent text-fallback journey completes without pointer or focus loss |
| UX-VOICE-11 | Language, RTL, zoom, and motion | Supported locales, localized fallback, RTL, reduced motion, and 200% zoom preserve meaning and operation |
| UX-VOICE-12 | Emergency Stop | Stop remains visible, independent, and effective during capture, upload, transcription, correction, and retry |
| CCT-VOICE-EF-01 | Evidence First states | Transport, transcription, correction, send acceptance, and recorded evidence remain semantically distinct |
| CCT-VOICE-TENANT-01 | Authority boundaries | Tenant, relationship, participant, and assurance bindings deny cross-boundary access without enumeration |
| CCT-VOICE-REPLAY-01 | Replay and uncertainty | Duplicate, replayed, and uncertain requests cannot duplicate contributions or evidence |
| CCT-VOICE-PRIV-01 | Privacy inspection | Audio, transcript, credentials, and sensitive identifiers do not leak through URL, logs, metrics, traces, errors, or browser persistence |

### Constitutional Controls

| ID | Scenario | Pass condition |
|---|---|---|
| CCT-UX-HO-01 | Emergency Stop from every authenticated professional route | Reachable without overflow menu, keyboard operable, visible at 360px and expanded widths |
| CCT-UX-HO-02 | Stop during stream | Stream rendering stops immediately; partial content is incomplete; ordinary reconnect cannot release Stop |
| CCT-UX-HO-03 | Stop confirmation | Dedicated constitutional path confirms or reports unknown outcome; no local-only success |
| CCT-UX-EF-01 | Evidence pending then recorded | Pending orange precedes authoritative confirmation; evidence green appears only after confirmed record |
| CCT-UX-EF-02 | Transport delivered without evidence | Delivery status never displays evidence mark or `Recorded` text |
| CCT-UX-BOUNDARY-01 | Scope-boundary confirmation | Boundary and consequence are explicitly named and remain distinct from normal approval |
| CCT-UX-RIGHTS-01 | Rights visibility | Rights, current authority, lifecycle, and Stop are reachable from relationship governance without technical vocabulary |

### Accessibility, Language, and RTL

| ID | Scenario | Pass condition |
|---|---|---|
| CCT-UX-A11Y-01 | Automated accessibility scan | Zero critical axe violations on every required route and state |
| CCT-UX-A11Y-02 | Keyboard-only journey | Login, switch professional, send, open work, approve/reject, inspect evidence, and Stop complete without pointer |
| CCT-UX-A11Y-03 | Focus lifecycle | Skip link works; dialogs/sheets trap and restore focus; route transitions place focus predictably |
| CCT-UX-A11Y-04 | Screen-reader stream/status | Status changes are announced once, with no repeated timeline narration or focus theft |
| CCT-UX-RTL-01 | Urdu route and component suite | Navigation, message alignment, directional icons, panel order, and Stop position mirror correctly |
| CCT-UX-RTL-02 | Urdu typography | Noto Nastaliq Urdu is active, line height is at least 2.0, and no glyph clips |
| CCT-UX-I18N-01 | All eleven locales | No missing key, fallback identifier, clipped label, or manually reduced script size appears |
| CCT-UX-MOTION-01 | Reduced motion | Sliding, pulsing, cycling, and nonessential movement are absent; state remains understandable |

### Offline, PWA, Privacy, and Resilience

| ID | Scenario | Pass condition |
|---|---|---|
| UX-PWA-01 | Installability | Manifest, icons, theme metadata, service worker, and HTTPS requirements pass browser checks |
| UX-PWA-02 | Offline application load | Public/static shell may load; authenticated payload is not served from service-worker cache |
| UX-PWA-03 | Offline draft | Draft is retained relationship-locally, visibly unsent, and submitted once after reconciliation |
| UX-PWA-04 | Sign out/account switch | Drafts and protected client state are cleared according to policy; no prior-customer content remains |
| UX-PRIV-01 | URL and telemetry inspection | No message, attachment, email, mobile, evidence payload, token, or tenant identifier appears |
| UX-PRIV-02 | Attachment preview | Retrieval is authorized and short-lived; no durable public URL is generated |
| UX-RES-01 | Service timeout/unknown outcome | UI preserves uncertainty and retry identity; it never reports success by timeout assumption |
| UX-RES-02 | Cross-channel feature before WC-060 | UI does not claim committed handoff or exactly-once continuity |

### Omnichannel Continuity (F5/WC-060 Only)

| ID | Scenario | Pass condition |
|---|---|---|
| UX-CONT-01 | Prepare target-channel handoff | BP returns a prepared checkpoint without changing the active source channel or relationship lifecycle |
| UX-CONT-02 | Target authentication and activation | Target content renders only after current participant, tenant, role, and assurance are server-verified and checkpoint activation is evidenced |
| UX-CONT-03 | Handoff failure or timeout | Source remains authoritative; target reports unresolved or reverted state and does not imply synchronization |
| UX-CONT-04 | Identical and divergent replay | Identical replay renders the prior outcome; divergent payload under the same idempotency key renders conflict with zero local mutation |
| UX-CONT-05 | Assurance downgrade or cross-tenant attempt | Capability is reduced or denied without relationship existence or protected content disclosure |
| UX-CONT-06 | Emergency Stop during handoff | Stop preempts handoff, applies across channel projections, and reconnect or handoff activation cannot release it |

### Visual and Performance

| ID | Scenario | Pass condition |
|---|---|---|
| UX-VIS-01 | Screenshot matrix | Approved baselines exist for compact/expanded, light/dark, English/Urdu, loading/error/stopped |
| UX-VIS-02 | Constitutional color audit | Override red appears only on Stop surfaces; delivery, processing, and evidence remain distinct |
| UX-VIS-03 | Stable dimensions | Release-enabled voice or attachment states, loading, long labels, status changes, and avatars do not resize fixed-format regions |
| UX-PERF-01 | Core Web Vitals profile | FCP ≤1.5s, LCP ≤2.5s, CLS ≤0.10, INP ≤200ms under the approved 4G profile |
| UX-PERF-02 | Initial payload | Public compressed weight ≤200KB; authenticated shell ≤400KB; initial JS ≤100KB gzipped |
| UX-PERF-03 | Active font subset | Only required language subset is preloaded and each subset remains within the approved budget |

## Screenshot Matrix

Baselines are required for:

- public home, login, registration, conversation, Plan, Work, Results, Usage & budget, Rights & control, Settings, Profile, Founder shell, `/403`, and not-found;
- compact light English, compact dark Urdu, expanded light English, and expanded dark Urdu;
- conversation loading, empty, failed send, offline draft, streaming, Stop pending, stopped, evidence pending, and evidence recorded;
- longest approved labels and representative Indic-script content.

Baseline changes require reviewer-visible artifacts and a stated reason. Bulk baseline replacement without route-by-route inspection fails review.

For component-level closure before F8, only baselines for routes and states owned by that authorized component are required. F8 executes the complete matrix above across the selected release and cannot be inferred from an earlier component's partial visual pass.

## Quality Gate Commands

Implementation evidence must include successful repository-standard equivalents of:

```text
npm run lint
npm run test:coverage
npm run build
npm run test:e2e
```

The implementation PR records browser projects, viewport sizes, locale/theme matrix, axe results, coverage percentage, build result, and screenshot-diff artifacts. A command passing without the required scenario evidence is insufficient.

## Release Blocking Rules

Release is blocked by any of the following:

- a critical axe violation or inaccessible Emergency Stop;
- horizontal overflow, overlap, clipping, or unreachable commands at 360px;
- RTL direction or Urdu glyph failure;
- constitutional evidence shown before authoritative confirmation;
- authenticated content stored by the service worker or leaked through telemetry;
- production fallback mock, undocumented endpoint, or browser-derived authorization;
- coverage below 90% for changed interactive code;
- failed lint, strict TypeScript build, browser project, or required screenshot comparison;
- a continuity claim that depends on incomplete WC-060 behavior.

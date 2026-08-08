# WAOOAW Hybrid Application Visual System Contract

**Document type:** Architecture Reference — Visual System
**Office:** Enterprise Architect (INST-004)
**Work Contract:** WC-034 / WC034-A03
**Status:** REVIEW CANDIDATE
**Normative parent:** `architecture/reference/ux/constitutional-ux-vocabulary.md`
**Companion:** `architecture/reference/ux/hybrid-application-shell.md`
**Constitutional basis:** C-001, C-002, C-009, C-023, C-042, C-063, C-071, C-076

## Purpose and Precedence

This contract maps the ratified WAOOAW visual vocabulary into the public, authentication, customer, Founder, and shared-system surfaces defined by WC-034. It does not replace the constitutional UX vocabulary. If this contract, a static HTML design input, or a component example conflicts with that vocabulary, the vocabulary controls.

## Static HTML Review Status

| Artifact | Founder decision | Architecture treatment |
|---|---|---|
| `architecture/reference/ux/homepage-prototype.html` | REJECTED on 2026-08-08 | Permanently deleted; no design, composition, token, copy, or implementation authority remains |
| `web/WAOOAWHome.html` | PENDING CONFIRMATION | May be reviewed as an existing artifact but is not normative and must not be migrated until confirmed |

The visual contract below is derived from the ratified constitutional UX vocabulary, not from either static HTML artifact.

## Token Layers

Every component consumes semantic or constitutional tokens. Raw primitives may appear only in the central token definition.

1. Primitive tokens define raw color, spacing, type, radius, duration, and elevation values.
2. Semantic tokens define surface, text, border, focus, command, success, warning, error, and information roles.
3. Constitutional tokens define override, evidence, pending evidence, and Decision Space boundary roles.

The required brand primitives are:

| Token | Value | Meaning |
|---|---|---|
| `--color-brand-blue` | `#1A66C2` | Scope and professional trust |
| `--color-brand-green` | `#3DAD35` | Evidence and confirmation graphics |
| `--color-brand-orange` | `#F7941D` | Pending governed work |
| `--color-brand-navy` | `#1E3352` | Institutional voice and primary light-theme text |

Text uses the approved text-safe variants. Hardcoded component colors are prohibited. Every semantic and constitutional token has a dark-theme value that preserves its meaning and required contrast.

## Constitutional Color Rules

- `--color-override` is exclusive to Emergency Stop and Stop-confirmation surfaces.
- Generic destructive, validation, and service errors use `--color-error`, never override red.
- Evidence green appears only after the authoritative evidence state is confirmed.
- Pending orange may indicate waiting for constitutional confirmation; it must not imply success.
- Boundary blue identifies Decision Space, scope, authority, and rights surfaces.
- Every status combines text, icon, and color. Color alone is never sufficient.
- Message-delivery ticks cannot use the evidence mark or evidence label.

Emergency Stop must achieve at least 7:1 contrast, remain visually distinct in light and dark themes, expose a minimum 56×56px touch target, and remain reachable without opening an overflow menu.

## Typography and Script Contract

| Role | Size / line height | Use |
|---|---|---|
| Display | 48px / 1.1 | Public hero only |
| H1 | 32px / 1.2 | Page title |
| H2 | 24px / 1.3 | Major section |
| H3 | 20px / 1.3 | Compact panel or card title |
| Body L | 18px / 1.6 | Primary reading content |
| Body | 16px / 1.5 | Standard text and conversation |
| Body S | 14px / 1.5 | Secondary labels |
| Caption | 12px / 1.4 | Timestamps and metadata only |

No text may render below 12px. Font size must not scale with viewport width. Letter spacing is zero unless a script-specific accessibility review approves another value.

The initial response resolves locale and direction before interactive rendering. Only the active script subset is preloaded. Urdu uses Noto Nastaliq Urdu, `dir="rtl"`, and minimum line height 2.0. Components must not compensate for Indic scripts with manual font-size reduction.

## Spacing, Shape, and Density

Spacing uses the existing 4px scale. Standard control padding is 16px; mobile page padding is 24px where the conversation is not edge-to-edge; desktop section padding is 32px.

| Element | Shape rule |
|---|---|
| Commands and fields | 8px radius |
| Genuine repeated cards | 12px radius, one-level elevation only |
| Compact status badges | Pill permitted |
| Emergency Stop | Pill or circle permitted because shape is a safety signal |
| Tooltips | 6px radius |
| Page sections and context regions | Unframed; do not wrap in decorative cards |

Cards must not contain decorative cards. Message bubbles, structured work cards, sheets, dialogs, and repeated professional entries may be framed; navigation columns, page sections, and desktop context panels are layout regions, not cards.

## Responsive Composition

The layout uses content-driven transitions rather than device names:

- **Compact:** 360px upward. One primary column, edge-to-edge conversation, full-screen secondary routes, four-item bottom navigation.
- **Intermediate:** when the conversation can remain at least 360px wide beside navigation. Collapsible navigation plus conversation; context opens as a sheet or route.
- **Expanded:** when navigation, a conversation column of at least 480px, and a context panel of at least 320px fit without overflow. Three-region composition is permitted.

No breakpoint may shrink fixed-format controls below their stable dimensions. Composer tools, Stop, bottom navigation, avatars, status controls, and structured cards must reserve dimensions so labels, loading states, and translations do not shift surrounding layout.

## Component Families

### Global Chrome

- Full WAOOAW logo appears in expanded public and application navigation; the mark alone appears in compact navigation and PWA assets.
- Icon commands use the established icon library, accessible labels, and tooltips where meaning is not universal.
- Theme and language controls are controls, not promotional cards.
- The skip link is the first focusable element.

### Conversation

- Professional avatars appear in identity locations, not beside every message.
- Customer and professional messages remain distinguishable without relying only on bubble color.
- The composer has stable height bands for text, attachments, voice state, validation, and send status.
- Structured Action, Plan, Deliverable, and Decision cards use compact headings and stable action areas.
- A live streamed response uses a polite live region and never steals focus.

### Context and Governance

- Plan, Work, Performance, Consumption, and Governance use unframed sections with dividers and clear headings.
- Business outcomes lead performance; technical metrics are supporting detail.
- Scope, authority, rights, evidence, and lifecycle are stated in plain language.
- Confirmation controls name the effect; ambiguous `OK` and color-only controls are prohibited.

### Authentication

- Authentication uses a focused desktop column and full-width compact flow without a decorative container around the entire page.
- Entered non-secret values, locale, and identity-path choice survive recoverable errors.
- Secret fields, one-time codes, and tokens are never retained after failed submission or navigation.
- Marketing content does not compete with the authentication task.

## Focus, Motion, and Feedback

- Focus is always visible at 3:1 contrast and is not replaced by a color change alone.
- All controls are keyboard operable in logical reading order.
- Dialogs and sheets trap focus while open and return it to the invoking control.
- Standard durations are 150ms, 250ms, and 400ms. No other duration enters component CSS without review.
- Reduced motion makes transitions instant or opacity-only and removes pulsing, sliding, parallax, and cycling text.
- Loading indicators reserve space and include text when the wait affects customer understanding.
- No animation flashes more than three times per second or blocks Emergency Stop.

## Asset and Imagery Policy

Public and authenticated critical paths are text-first. Allowed assets are the WAOOAW logo, familiar interface icons, configured professional identity avatars, customer attachments, necessary work-product previews, and approved blog media. Stock, atmospheric, decorative, background, hero-carousel, and ornamental SVG imagery is prohibited.

Assets declare dimensions, use responsive sources where applicable, and do not enter the critical rendering path unless they are identity-critical. The logo is never recolored, shadowed, or separated from its mark/wordmark rules.

## Visual Review Gate

A visual implementation fails review if it:

- imports Inter or alternate constitutional colors outside the ratified token system;
- uses override red outside Emergency Stop;
- defaults to a dark-only experience;
- places cards inside cards or frames whole page sections as cards;
- clips translated, Indic, or Urdu text;
- changes layout when status, loading, voice, attachment, or long labels appear;
- communicates delivery, processing, or evidence through one shared tick vocabulary;
- introduces decorative imagery, glow, or gradients unrelated to a command or state.

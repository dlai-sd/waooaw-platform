# Constitutional UX Vocabulary — Phase 1

**Version:** 1.0
**Date:** 2026-07-18
**Status:** RATIFIED — Founder approval 2026-07-18
**Constitutional Basis:** C-001 (Human Override), C-039 (Conversational Config), C-042 (Vocabulary Mandate — LAW), C-048 (Information Non-Exploitation), C-060 (Minor Protection — LAW), C-062 (AI Security), C-063 (Data Minimisation)
**Design Inspiration:** Microsoft Azure AI Foundry homepage · Google Cloud homepage
**Next document:** `architecture/reference/ux/suresh-portal-walkthrough.md` (Point 2 — gap discovery)

---

## Purpose

This document defines the visual, interaction, language, and constitutional vocabulary for the WAOOAW customer portal. It is the single reference that governs every design decision — from a button label to a color token to the way the platform communicates its constitutional principles to a farmer in Vidarbha.

**What this document is NOT:**
- A wireframe or screen design (those come after this)
- A component library (that references this)
- A marketing brief (though it governs all platform copy)

**Three design obligations this document enforces:**
1. Every pixel must serve a business outcome for Suresh, not a platform ego (C-042)
2. Human override is always one tap away, never hidden (C-001)
3. Conversational engagement before any form (C-039)

---

## Platform Value Proposition — The Design North Star

Everything on the portal — every screen, every word, every interaction — must orient toward these five truths. This is not marketing copy. It is the constitutional identity of the platform made visible.

| Truth | What Suresh experiences | What the portal shows |
|---|---|---|
| **AI agents based on constitution and innovation** | "My WaooaW Expert only works for me — no one else's farm" | Scope card showing the agent's boundaries. "Working only for you." |
| **Reduce effort by 80%** | Suresh does nothing — the agent acts first | Activity feed showing what the agent did *today*, unprompted |
| **Improve outcomes by 50%** | Better harvest decisions, better prices | Outcome history: "Last season: ₹8/kg more than market average" |
| **60% cost reduction** | Less wasted spend on advice, pesticides, middlemen | Cost savings tracker (unlocked after FR-005 stat gate: 50+ customers) |
| **Try before you buy** | One free crop advisory session — no payment, no commitment | Trial entry point: prominent, zero-friction, no card required |
| **Fully autonomous, secure, trusted** | The agent works while Suresh sleeps | "Active since 6:00 AM" indicator. Last action timestamp. |

**Stat gate rule:** The specific numbers (80%, 50%, 60%) are LOCKED behind FR-005 — they appear only after 50+ diverse paying customers. Until then, the portal uses **scenario-based demonstrations** labelled *"Based on a typical scenario"*. This is constitutional — no claim without evidence (C-002).

---

## 1. Language & Localisation

### 1.1 Language Set (Phase 1 — All 11 at Launch)

| Language | Code | Script | Direction | Target persona |
|---|---|---|---|---|
| English | en | Latin | LTR | Default / developer / urban |
| Hindi | hi | Devanagari | LTR | Dr. Mehta, Meera, Rahul |
| Marathi | mr | Devanagari | LTR | Suresh, Pune market — MVI city |
| Tamil | ta | Tamil | LTR | South India customers |
| Telugu | te | Telugu | LTR | Andhra / Telangana |
| Kannada | kn | Kannada | LTR | Bangalore customers |
| Gujarati | gu | Gujarati | LTR | Ahmedabad / Surat traders |
| Bengali | bn | Bengali | LTR | Kolkata market |
| Malayalam | ml | Malayalam | LTR | Kerala market |
| Punjabi | pa | Gurmukhi | LTR | North India |
| **Urdu** | **ur** | **Nastaliq** | **RTL** | **Urdu-speaking customers — Phase 1** |

### 1.2 RTL Architecture Requirement (Urdu)

Urdu is the only RTL language in the set. This is an **architectural constraint**, not a localisation afterthought.

**Mandatory engineering rule:** All CSS must use **logical properties** throughout. No physical directional values.

```css
/* PROHIBITED — breaks RTL */
margin-left: 16px;
padding-right: 8px;
text-align: left;
float: left;

/* REQUIRED — works in both LTR and RTL */
margin-inline-start: 16px;
padding-inline-end: 8px;
text-align: start;
float: inline-start;
```

**Layout mirroring in RTL:**
- Navigation: right-aligned in RTL, left-aligned in LTR
- Chat bubbles: customer messages flip sides (right in LTR → left in RTL)
- Card content: text flows right-to-left
- Icons with directional meaning (arrows, chevrons): must be flipped in RTL
- Emergency Stop button: always top-right in LTR, top-left in RTL (nearest thumb in both layouts)

**Testing requirement:** Every component must be visually tested in both `dir="ltr"` and `dir="rtl"` before release. A CCT-UX-01 (RTL layout integrity) must be defined before the first UI sprint.

### 1.3 Font Stack

**Primary font family:** [Noto Sans](https://fonts.google.com/noto) — Google's universal script coverage project. Free. Open source. Purpose-built for multi-script readability.

| Script | Font | Notes |
|---|---|---|
| Latin (English) | Noto Sans | Variable font — single file covers all weights |
| Devanagari (Hindi, Marathi) | Noto Sans Devanagari | Shares base design language with Latin |
| Tamil | Noto Sans Tamil | |
| Telugu | Noto Sans Telugu | |
| Kannada | Noto Sans Kannada | |
| Gujarati | Noto Sans Gujarati | |
| Bengali | Noto Sans Bengali | |
| Malayalam | Noto Sans Malayalam | |
| Punjabi / Gurmukhi | Noto Sans Gurmukhi | |
| **Urdu / Nastaliq** | **Noto Nastaliq Urdu** | RTL, larger x-height — requires more line-height |

**Loading strategy:** Subset fonts to Unicode ranges of active language. Never load all scripts on page load. Language-aware dynamic font loading via `<link rel="preload">` with `as="font"`.

**Fallback stack:** `"Noto Sans", "Segoe UI", system-ui, -apple-system, sans-serif`

### 1.4 Localisation Standards

| Element | Standard |
|---|---|
| Date format | DD/MM/YYYY (India standard) |
| Time format | 12-hour with AM/PM (`6:30 AM IST`) |
| Timezone | IST always. Never UTC unless in technical logs. |
| Currency | ₹ symbol. Indian numbering: `₹1,00,000` not `₹100,000` |
| Numbers | Indian grouping: `12,34,567` not `1,234,567` |
| Language switcher | Globe icon + current language name. Always visible in header. |
| Language persistence | Browser `localStorage` pre-login. Migrated to user profile on registration. |

**C-042 localisation obligation:** Translations are NOT literal. Per-agent vocabulary must be translated in occupational terms. "Decision Space" → never appears in any language. "Agent activity log" → "Aaj Aapke WaooaW Expert ne kya kiya" (Hindi: "What your WaooaW Expert did today"). The translation is of the meaning, not the word.

**Who translates:** WAOOAW AI — not human translators. Platform operations — including content generation, translation, and research — are performed by AI agents. The founding team (Yogesh, Sujay, Ojal) governs; AI agents execute. This is by design: a human translator produces technically accurate text; WAOOAW AI produces constitutionally faithful text — preserving occupational vocabulary, the WaooaW Expert persona tone, and the constitutional principles embedded in every string. A human translating "Evidence recorded" into Marathi produces "पुरावा नोंदवला" (literal). WAOOAW AI translates it as "नोंद झाली ✓" ("Done — logged") — which is what C-042 requires.

**Translation standard:**
- Source truth: `en.json` (English strings, authored to constitutional vocabulary spec)
- AI translation task: run against each target language using the Constitutional UX Token Dictionary (Appendix A) as mandatory vocabulary override
- Output: `{lang}.json` per language (mr, hi, ta, te, kn, gu, bn, ml, pa, ur)
- Validation: AI self-reviews against Appendix A — any string that contains a prohibited technical term (see Section 9.1) triggers a re-translation, not a human review
- No human review step: the AI translation is the authoritative output. Constitutional correctness is enforced by the vocabulary constraint, not by human judgment.

---

## 2. Accessibility & Inclusive Design

### 2.1 Standard

**Target:** WCAG 2.1 Level AA (minimum). Aspirational: AA+ for all body text.

Rationale: Suresh is 52, rural, potentially using a low-cost Android phone in outdoor sunlight. Dr. Mehta may be using the portal in a clinic with overhead fluorescent lighting. Accessibility is not a compliance checkbox — it is the constitutional obligation to serve the actual customers.

### 2.2 Color Contrast

| Use | Minimum ratio | Constitutional basis |
|---|---|---|
| Normal body text | 4.5:1 | WCAG 1.4.3 |
| Large text / headings (18px+) | 3:1 | WCAG 1.4.3 |
| Interactive elements (buttons, inputs) | 3:1 against adjacent background | WCAG 1.4.11 |
| Focus indicators | 3:1 against adjacent | WCAG 2.4.11 |
| `--color-override` (Emergency Stop) | 7:1 minimum | C-001 — human override must be unmissable |
| `--color-evidence` icon / badge fill | 3:1 minimum | Graphical element — WCAG 1.4.11 (achieved: 2.93:1 ✓ at `#3DAD35`) |
| `--color-evidence-text` ("Done ✓" label) | 4.5:1 minimum | Text — WCAG 1.4.3 (achieved: 6.66:1 ✓ at `#1B6B17`) |

**Rule:** Status and error must NEVER be communicated by color alone. Always: **color + icon + text** together. A farmer who is color-blind must know the spray warning is critical from the icon and text, not from "it's red."

### 2.3 Typography Scale

```
Display   — 48px / 1.1 line-height  — Home page hero only
H1        — 32px / 1.2              — Page titles
H2        — 24px / 1.3              — Section headers
H3        — 20px / 1.3              — Card titles
Body L    — 18px / 1.6              — Primary reading content
Body      — 16px / 1.5              — Standard text (minimum body size)
Body S    — 14px / 1.5              — Secondary text, labels, captions
Caption   — 12px / 1.4              — Legal text, timestamps, metadata only
```

**Absolute floor:** Nothing below 12px anywhere on the platform. No exceptions.

**Multi-script note:** Indic scripts (Devanagari, Tamil, Telugu, etc.) have larger visual size at the same px value as Latin. Noto's scripts are designed to be optically similar — trust the font, do not manually compensate.

**Urdu / Nastaliq** requires `line-height: 2.0` minimum due to the script's descenders and the way connected letterforms stack. All Urdu text containers must explicitly set this.

### 2.4 Touch Targets

- Minimum touch target: **44×44px** (iOS HIG + WCAG 2.5.5)
- Minimum touch target spacing: **8px** between adjacent targets
- Emergency Stop button touch target: **56×56px minimum** — this is C-001, not a preference

### 2.5 Themes

| Theme | When | Notes |
|---|---|---|
| **Light** (default) | Portal, outdoor use, clinic environments | White background `#FFFFFF`, `--text-primary: #0F172A` |
| **Dark** | Trader at screens, evening use, developer preference | Near-black `#0A0A0F`, `--text-primary: #F1F5F9` |
| **System-follows** | Default on first visit | Reads `prefers-color-scheme`. User can override. |
| High-contrast | Accessibility need | Phase 2. Design for it now — reserve token names. |

All color tokens must have a light and dark variant. No hardcoded colors anywhere in components.

### 2.6 Motion & Animation

- **Respect `prefers-reduced-motion`:** All animations check this media query. If set, reduce to instant transitions or opacity fades only.
- **No auto-playing animations** that cannot be paused
- **No content that flashes more than 3 times per second** (seizure safety — WCAG 2.3.1)
- **Acceptable animations:** `--duration-fast: 150ms`, `--duration-standard: 250ms`, `--duration-slow: 400ms`
- **Evidence confirmation animation:** 400ms subtle checkmark pulse — respects reduced-motion (instant checkmark if reduced)

### 2.7 Screen Reader & Keyboard

- All interactive elements: keyboard navigable in logical tab order
- ARIA labels: mandatory on all icons that carry meaning (not decorative)
- Skip-to-main-content link: first focusable element on every page
- Focus indicator: always visible. Design MUST NOT suppress the browser default focus ring without replacing it with a more visible alternative.
- Modals: trap focus while open, return focus on close

---

## 3. Performance & Mobile-First

### 3.1 Device Target

**Primary:** Android mid-range (`₹10,000–15,000` price point), 4G with intermittent 3G drops. This is Suresh, Dr. Mehta, and 90% of India's B2C market.

**Secondary:** Desktop (Chrome/Edge) — Rahul (trader), Meera (parent), developers.

**Network simulation for all performance tests:** 4G throttled (download 8.75Mbps, upload 1.87Mbps, RTT 20ms). Test also at 3G slow (download 400Kbps) for rural coverage zones.

### 3.2 Performance Budgets

| Metric | Target | Notes |
|---|---|---|
| First Contentful Paint (FCP) | ≤ 1.5s | 4G conditions |
| Largest Contentful Paint (LCP) | ≤ 2.5s | Core Web Vitals GOOD |
| Cumulative Layout Shift (CLS) | ≤ 0.10 | No layout jumps as fonts load |
| Interaction to Next Paint (INP) | ≤ 200ms | Replaced FID in CWV |
| Total page weight — home/landing | ≤ 200KB (compressed) | Text + SVG only in above-fold |
| Total page weight — portal dashboard | ≤ 400KB (compressed) | Includes agent activity data |
| JS bundle (initial load) | ≤ 100KB gzipped | Code-split aggressively |
| Font load (each script subset) | ≤ 15KB per language subset | Preloaded for current language |

### 3.3 Design Rules for Performance

**Text-primary design (from Foundry/GCloud inspiration):**
- Above-the-fold content: text + SVG icons only. Zero raster images in the critical rendering path.
- No stock photography on any page. Ever.
- No hero video backgrounds. Subtle CSS gradient only.
- No image carousels. Static card grids.
- Illustration: SVG only, optimised (≤3KB per illustration, ≤2KB per icon)

**Glassmorphism rule:** Used selectively — navigation overlay and modal backdrops only. Maximum one frosted-glass layer at any z-level. Never stacked. Implement via `backdrop-filter: blur(12px)` with a graceful fallback for browsers that don't support it (solid semi-transparent background).

**Strategic gradient use:**
- Brand gradient: CTAs, section transitions, active state on agent cards
- Never as a decorative background
- Maximum 2 gradient colors, subtle range (no neon)

**Image handling (when images do appear — agent profile avatars, blog thumbnails):**
- Format: WebP with JPEG fallback
- Lazy loaded below the fold
- Always `width` and `height` attributes set (prevents CLS)
- `srcset` for responsive sizes

### 3.4 PWA Requirements (ADR-017)

| Requirement | Implementation |
|---|---|
| Installable | Valid web manifest, 192×192 and 512×512 icons, HTTPS |
| Offline — Emergency Stop | Service Worker caches Emergency Stop WebSocket endpoint. C-001: override must work even on spotty connection. |
| Offline — last dashboard | Service Worker caches last-seen agent dashboard for Suresh's field (no connectivity). Read-only, timestamp-labelled "Last updated: 6:30 AM" |
| Push notifications | Agent-triggered alerts (spray warning, mandi price alert, trading signal). Customer opts in per-agent, not platform-wide. |
| Install prompt | Shown after 2nd visit + 1 completed interaction. Not on first visit. |

---

## 4. Visual Design System

### 4.0 Brand Identity

**Logo file:** [architecture/reference/ux/brand/waooaw-platform-logo.png](brand/waooaw-platform-logo.png)

**Logo structure:** Three W-peaks forming W·A·W — the visual signature of WAOOAW. Read as one continuous wave: Trust → Growth → Energy. The three peaks are the institution's core identity made visible.

**Brand color palette (extracted from logo):**

| Token | Hex | Logo element | Constitutional resonance |
|---|---|---|---|
| `--color-brand-blue` | `#1A66C2` | Left W | Trust · Professionalism · Scope — maps to `--color-boundary` |
| `--color-brand-green` | `#3DAD35` | Centre A — the peak | Growth · Evidence · Confirmation — maps to `--color-evidence` |
| `--color-brand-orange` | `#F7941D` | Right W | Energy · Action · India warmth — maps to `--color-pending` |
| `--color-brand-navy` | `#1E3352` | Wordmark "WAOOAW" | Authority · Institutional voice · Primary text |

**The brand palette encodes the constitutional model.** This is not coincidence — it is design intent. Every time a customer sees a green confirmation checkmark, they see the centre of the WAOOAW logo. Every time they see the professional scope card in blue, they see the first W. The constitution is in the color.

**Text-safe variants** (darker shades meeting WCAG 4.5:1 on white — for colored text labels):

| Token | Hex | Contrast on white | Use |
|---|---|---|---|
| `--color-brand-blue-text` | `#1A66C2` | 5.71:1 ✓ | Blue text labels, links |
| `--color-brand-green-text` | `#1B6B17` | 6.66:1 ✓ | "Done ✓" text, confirmation labels |
| `--color-brand-orange-text` | `#A85B00` | 5.02:1 ✓ | "Pending…" text, action labels |
| `--color-brand-navy` | `#1E3352` | 12.4:1 ✓ | All primary body text |

**Logo usage across the platform:**

| Surface | Asset | Size |
|---|---|---|
| Portal header (full logo) | `waooaw-platform-logo.png` | 32px height |
| Favicon | Icon mark only (three-W crop) | 16×16, 32×32 |
| PWA manifest | Icon mark, white background | 192×192, 512×512 |
| WoW Concierge bubble | Icon mark only | 40×40px |
| Email footer | Full logo | 120px width |
| WhatsApp Business profile | Square icon mark crop | 400×400px |
| OpenGraph / social share card | Full logo on `--color-brand-navy` background | 1200×630px |
| Blog byline | Icon mark only | 20×20px inline |

**Dark theme:** The three-W mark is vivid on dark backgrounds — no inversion needed. Wordmark text changes to `#F1F5F9`.

**Minimum sizes:** Full logo (mark + wordmark): 120px wide. Icon mark alone: 24px wide. Never scale below — the three-peak form must remain legible.

**Do not:** Recolour any peak · Add drop shadows to the mark · Use wordmark without mark · Place mark on a background that conflicts with any brand color.

---

### 4.1 Design Token Architecture

Tokens are organized in three layers. All component styles reference tokens, never raw values.

```
Layer 1 — Primitive tokens    (raw values — never used directly in components)
Layer 2 — Semantic tokens     (purpose-named — used in component styles)
Layer 3 — Constitutional tokens (WAOOAW-specific — encode governance meaning)
```

### 4.2 Constitutional Color Tokens (Non-Negotiable)

These tokens encode constitutional meaning. They must NEVER be repurposed for decorative or unrelated uses.

**Key alignment:** Constitutional tokens now derive from brand primitives. The brand IS the constitution made visible.

```css
/* ─── Brand primitives (Layer 1) ─────────────────────────────────────── */
--color-brand-blue:          #1A66C2;
--color-brand-blue-text:     #1A66C2;   /* 5.71:1 on white ✓ */
--color-brand-green:         #3DAD35;
--color-brand-green-text:    #1B6B17;   /* 6.66:1 on white ✓ */
--color-brand-orange:        #F7941D;
--color-brand-orange-text:   #A85B00;   /* 5.02:1 on white ✓ */
--color-brand-navy:          #1E3352;   /* 12.4:1 on white ✓ */

/* ─── Constitutional tokens (Layer 3) — aligned to brand ─────────────── */

/* Emergency Stop — DELIBERATELY outside the brand palette.               */
/* Red must never feel like WAOOAW branding. It is a safety signal.        */
--color-override:        #DC2626;  /* Emergency Stop ONLY. Never for "delete", "error", "danger" */
--color-override-bg:     #FEF2F2;
--color-override-pulse:  #EF4444;

/* Evidence = Brand Green. The centre peak of the logo = constitutional truth confirmed. */
--color-evidence:        #3DAD35;  /* CE evidence recorded — icon fill, badge (3:1 graphical ✓) */
--color-evidence-text:   #1B6B17;  /* "Done ✓" text label (6.66:1 AA text ✓) */
--color-evidence-bg:     #F0FDF4;

/* Pending = Brand Orange. Energy awaiting resolution.                     */
--color-pending:         #F7941D;  /* Awaiting CE confirmation — icon fill, badge */
--color-pending-text:    #A85B00;  /* "Processing…" text label (5.02:1 AA text ✓) */
--color-pending-bg:      #FFF7ED;

/* Boundary = Brand Blue. The professional scope. Trust made visible.      */
--color-boundary:        #1A66C2;  /* Decision Space scope — scope card border, scope icon */
--color-boundary-text:   #1A66C2;  /* "Scope" label text (5.71:1 AA text ✓) */
--color-boundary-bg:     #EFF6FF;

/* Trial — purple. Distinct from all three brand colors. Clearly "special offer". */
--color-trial:           #7C3AED;
--color-trial-bg:        #F5F3FF;
```

**Enforcement rule:** A design review must reject any use of `--color-override` outside Emergency Stop surfaces. Any violation is a constitutional design violation, not a style preference disagreement.

### 4.3 Semantic Color Tokens

```css
/* Success / positive — shares green family with brand but distinct token */
--color-success:    #15803D;
--color-warning:    #B45309;
--color-error:      #B91C1C;  /* Informational error — different from override red */
--color-info:       #1D4ED8;

/* Neutrals */
--color-surface:    #FFFFFF;
--color-surface-2:  #F8FAFC;  /* Card backgrounds */
--color-border:     #E2E8F0;
--color-text-1:     #1E3352;  /* ← Brand navy — primary text is the institutional voice */
--color-text-2:     #475569;  /* Secondary text */
--color-text-3:     #94A3B8;  /* Disabled / placeholder */
```

Dark theme variants of all tokens defined via `[data-theme="dark"]` CSS attribute.

### 4.4 Spacing Scale

Base unit: **4px**

```
--space-1:  4px
--space-2:  8px
--space-3:  12px
--space-4:  16px    ← standard component padding
--space-5:  20px
--space-6:  24px    ← section padding (mobile)
--space-8:  32px    ← section padding (desktop)
--space-10: 40px
--space-12: 48px    ← large section gaps
--space-16: 64px
--space-24: 96px    ← page-level breathing room
```

### 4.5 Shape & Elevation

| Element | Border radius | Shadow |
|---|---|---|
| Cards | 12px | `0 1px 3px rgba(0,0,0,0.08)` |
| Buttons | 8px | None (color communicates hierarchy) |
| Input fields | 8px | `inset 0 0 0 1px var(--color-border)` |
| Modals | 16px | `0 20px 60px rgba(0,0,0,0.15)` |
| Status badges | 9999px (pill) | None |
| Emergency Stop button | 9999px (pill/circle) | `0 4px 12px rgba(220,38,38,0.3)` |
| Tooltips | 6px | `0 4px 8px rgba(0,0,0,0.12)` |

---

## 5. Constitutional Visual Language

How constitutional principles become pixels the customer can trust.

### 5.1 Emergency Stop (C-001 — Human Override is Absolute)

**Requirement:** Always visible when a session is active. Never hidden. Never behind a menu. Never disabled.

```
Calm state (agent active, no concern):
  ┌──────────────────────────────────────┐
  │ [WAOOAW]          [⏹ Active]  [🌐]  │  ← red pill, small, top-right
  └──────────────────────────────────────┘

Danger state (triggered by customer — expands):
  ┌──────────────────────────────────────┐
  │        ⏹ STOP NOW                   │  ← full-width red bar
  │  Your WaooaW Expert is pausing now.     │
  │  All activity will stop within 250ms.│
  └──────────────────────────────────────┘
```

- Touch target: 56×56px minimum
- Color: `--color-override` — red. Reserved exclusively for this.
- Copy: "Stop" in calm state. "STOP NOW" in danger state. Never "Cancel" or "Pause".
- Translated in all 11 languages. RTL version mirrored.
- Offline-capable: cached in Service Worker. Works without network.
- Post-stop state: Agent shows "Paused by you at [time]" — clear audit trail.

### 5.2 Evidence Confirmation (C-002 / C-023 — Evidence First)

Every action that writes a Constitutional Engine evidence record must show a visual confirmation to the customer — even if they don't know what "Constitutional Engine" means.

**Visual pattern:**
```
Customer action: "Hire WaooaW Expert Dental Marketing"

  [Hire WaooaW Expert Dental Marketing]  ← button
        ↓ (customer taps)
  ⟳ Setting up your professional...   ← pending state, --color-pending
        ↓ (CE confirms, ~200ms)
  ✓ Done — your professional is ready  ← --color-evidence green, 400ms pulse
```

**Customer vocabulary for evidence:**
- Not "Evidence recorded to Constitutional Audit Ledger"
- Yes: "Done" / "Confirmed" / "Saved" — with a `--color-evidence` checkmark
- The checkmark IS the constitutional signal. Customers learn: green checkmark = real, permanent, protected.

### 5.3 Decision Space Scope Card (C-018 / C-014)

Every hired agent has a **Scope Card** — a plain-language view of what their professional is allowed to do, visible to the customer at any time.

```
┌─────────────────────────────────────────────┐
│ WaooaW Expert Dental Marketing — Your Scope    │
│                                             │
│ ✓ Posts on Instagram, Facebook, WhatsApp    │
│ ✓ Responds to Google reviews                │
│ ✓ Runs ads up to ₹5,000/month               │
│                                             │
│ ✗ Cannot post on Twitter (not enabled)      │
│ ✗ Cannot spend more than your set limit     │
│ ✗ Cannot contact patients directly          │
│                                             │
│ [Change what they can do →]                 │
└─────────────────────────────────────────────┘
```

- Scope card is visible on every agent detail page
- Changing any scope item requires customer confirmation: a constitutional event (C-014)
- "Change what they can do" → opens a conversational flow, not a form

### 5.4 "Curious, Engaged, Informed" — The Portal Experience Design

This is the post-login design principle for customers like Suresh. The portal must not be a passive dashboard. It must be a living presence that makes Suresh feel his professional is always working.

**Curious** — the platform surfaces what Suresh doesn't know to ask:
- "Your WaooaW Expert noticed something this morning." → unexpected proactive insight
- "Farmers near you are asking about X. Here's what it means for your crop."
- New agent types teased: "WoW is working on new professionals. Coming soon: Legal Advisory."
- Platform vision micro-content: brief, plain-language explainer cards about what constitutional AI means for farmers. Shown once per week max. Never forced.

**Engaged** — the agent shows activity even when Suresh isn't looking:
```
Today's activity feed (Suresh's dashboard — Marathi):
  6:30 AM  🌤 IMD alert reviewed — no action needed for your cotton
  8:15 AM  📊 Nagpur mandi prices checked — hold for 3 more days
  11:00 AM ⚡ Hail risk: LOW this week in Katol
  2:00 PM  💡 Tip: Your cotton is at 45 days — time to check for bollworm
```

Activity is shown in Suresh's language, using his vocabulary, with actionable next steps — never raw data.

**Informed** — the platform shares its vision, simply:
- Small "Did you know?" cards in the portal (dismissable, once/week max):
  - "WaooaW Expert is constitutionally bound to work only for your farm — never for a competitor."
  - "Every decision your WaooaW Expert makes is recorded. You can ask to see it anytime."
  - "WAOOAW is research-based. This tip is backed by ICAR data from 2024."
- These cards build the constitutional trust story without requiring Suresh to read a whitepaper.

---

## 6. Navigation Architecture

### 6.1 Logged-Out Navigation (Public Portal)

```
Desktop header:
[WAOOAW logo]     Home  Agents  Blogs  Settings     [Login]  [Register →]

Mobile header:
[WAOOAW logo]                                        [Login →]

Mobile bottom bar (4 items — max):
  🏠 Home    🤖 Agents    📝 Blogs    ⚙ Settings
```

**Rule:** Login / Register are header CTAs on mobile — NOT in the bottom bar. Bottom bar is capped at 4 items. Login in the bottom bar competes with primary nav and violates the 4-item rule.

### 6.2 Logged-In Navigation

```
Desktop header:
[WAOOAW logo]     Home  My Agents    [⏹ Active — Emergency Stop]  [👤 My Profile ▾]

Mobile bottom bar:
  🏠 Home    🤖 My Agents    👤 My Profile
  
  [⏹ Active]  ← persistent Emergency Stop pill in header, always visible
```

### 6.3 Navigation Item Definitions

| Item | Logged-out | Logged-in | Content |
|---|---|---|---|
| **Home** | Public landing page | Personalised dashboard — "Good morning, Suresh. Here's what happened today." | |
| **Agents** (logged-out) | Public catalog — all agent types with descriptions, outcomes, pricing | Hidden (replaced by My Agents) | One card per agent type |
| **My Agents** (logged-in) | Hidden | Hired agents list — one card per hired professional with activity summary | |
| **Blogs** | Public content hub | Same — public, always accessible | Research + expertise articles |
| **Settings** | Language + theme selector | Language + theme + notifications + billing + account | |
| **My Profile** | Hidden | Account details, subscription, agent configuration history | |
| **Login / Register** | Prominent — Login as link, Register as filled button | Hidden | |

### 6.4 Activity Log Location

Activity log (evidence ledger in plain language) lives **inside each agent card**, not as a top-level nav item.

```
My Agents → WaooaW Expert Dental Marketing card → "See full activity" →
  ↳ Timeline: today's posts, patient reviews responded, ad spend this week
```

This keeps the top-level navigation clean and contextualizes the evidence with the agent that produced it.

---

## 7. WoW Concierge — Home Page Engagement Interface

### 7.1 Identity

The WoW Concierge is the **WAOOAW platform voice** — unnamed, no avatar, no persona name. It speaks as the institution. It is not an agent. It cannot be hired. It cannot take consequential actions.

**Constitutional Decision Space (WoW Concierge):**
- Authorized: answer questions about WAOOAW professionals, show demonstrations, describe pricing, guide to registration, simulate a professional interaction for a prospect
- Prohibited: store prospect data beyond the session, take any hiring or configuration action, make guarantees that exceed platform capabilities, promise specific outcomes before stat gate clears
- Always ask: before showing scenario-based performance statistics, must display "Based on a typical scenario" label

### 7.2 Layout (Three Surfaces)

**Surface 1 — Hero Input (home page, above fold):**

```
Mobile (375px):
┌─────────────────────────────────────────┐
│ [WAOOAW]                     [🌐 EN ▾] │
│                                         │
│  "Your business deserves a              │
│   professional, not a tool."            │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ What does your business do?          │ │
│ │                                     │ │
│ │ [cycling placeholder, 3s intervals] │ │
│ │ "I run a dental clinic in Pune"     │ │
│ │ "I farm cotton in Vidarbha"         │ │
│ │ "I trade F&O on NSE"                │ │
│ │ "I want a tutor for my child"       │ │
│ └─────────────────────────────────────┘ │
│ [→ Meet your WaooaW Expert]                │
│                                         │
│ ──── or browse professionals ────       │
└─────────────────────────────────────────┘
```

- Input box: `--color-evidence` border glow on focus (green — the constitutional signal)
- Cycling placeholder: rotates through agent-type examples every 3 seconds, `prefers-reduced-motion` stops cycling
- CTA: "Meet your WaooaW Expert" — outcome-first language, not "Search" or "Explore"
- Input is free text — customer types anything, WoW Concierge interprets

**Surface 2 — Agent Preview Cards (below hero, home page):**

Each public agent type has a card:

```
┌──────────────────────────────────────────┐
│  WaooaW Expert                              │
│  Dental Marketing                        │
│                                          │
│  "More patients. Better reviews.         │
│   Less time on social media."            │
│                                          │
│  ✓ Instagram & WhatsApp posts done daily │
│  ✓ Google reviews responded to           │
│  ✓ Patient reactivation on autopilot     │
│                                          │
│  From ₹1,499/month                       │
│                                          │
│  [Try free — 7 days]  [Ask a question]  │
└──────────────────────────────────────────┘
```

- No feature lists. Outcomes only (C-042).
- "Ask a question" opens WoW Concierge pre-loaded with context about this agent type.
- "Try free" goes to trial flow (Section 8).

**Surface 3 — Persistent Concierge Bubble (all public pages):**

```
Collapsed:  [W] ←  small pill, bottom-right (LTR) / bottom-left (RTL)
            subtle `--color-evidence` pulse when a new visitor arrives

Expanded:   320px chat panel, slides up from bottom-right
            Opens with: "Tell me about your business — I'll show you the right professional."
```

Context-aware opening message:
- On home page: "Tell me about your business."
- On DMA agent page: "What kind of business do you run? I'll show you what WaooaW Expert Marketing would do for it."
- On Blogs page: "Did this article raise any questions? Ask me."
- On Pricing page: "Want to see what's included before you decide?"

### 7.3 Conversation Flow Design

**Exchange depth rule:** 3 free exchanges, then soft registration nudge. Conversation continues after nudge — registration is never a gate.

```
Exchange 1 — Discovery
  Customer: "I have a dental clinic in Pune, 2 chairs, mostly families"
  WoW:      "Perfect. WaooaW Expert Dental Marketing handles Instagram,
              WhatsApp, Google reviews, and patient reactivation
              specifically for dental practices like yours.
              Want to see what they'd do for your clinic?"

Exchange 2 — Demonstration
  Customer: "Yes, show me"
  WoW:      "Here's a real scenario: a patient leaves a 3★ Google review
              after a long wait. Your WaooaW Expert responds within 2 hours:
              [shows simulated response in dental vocabulary]
              *Based on a typical scenario*
              Want to see your week's social media plan?"

Exchange 3 — Value
  Customer: "How much does it cost?"
  WoW:      "₹1,499/month. Includes everything you just saw.
              7-day free trial — no card needed.
              [Start free trial]  [Tell me more]"

Soft nudge (after 3rd exchange):
  WoW:      "I can show you a lot more if you register — it takes 2 minutes
              and it's free. Or keep asking — up to you."
              [Register free →]  [Keep asking]
```

**WoW Concierge tone:**
- Knowledgeable, warm, efficient. Expert colleague, not a chatbot.
- Speaks in the customer's language (browser locale until they set it explicitly)
- Short responses — 3 sentences maximum per turn
- Always ends with a clear next action or open question

---

## 8. Try Before You Buy — Trial Flow Design

**Constitutional basis:** C-063 (data minimisation) — trial data not stored if customer does not convert within 7 days.

### 8.1 Trial Offering Per Agent Type

| Agent | Trial | Duration | What they get |
|---|---|---|---|
| DMA (Marketing) | Free 7-day trial | 7 days | Full skill access. Agent does real work. No billing until day 8. |
| Agricultural Advisor | Free crop assessment | 1 session | Agent analyses their farm context, produces one season recommendation. No subscription until they confirm. |
| Trading Professional | Free risk profile + 1 trade brief | 1 session | Agent assesses trading style, produces one trade brief. No subscription until they confirm. |
| Private Tutor | Free 20-minute session | 1 session | Skill 0 (Student Profiling) + opening lesson. Parent sees the teacher persona in action before paying. |

### 8.2 Trial Entry Flow

```
[Try free — 7 days] button on any agent card
  ↓
"Tell us about your business" — 3-question quick profiling (conversational, not a form)
  ↓
"Your WaooaW Expert is ready. No card needed. Trial ends in 7 days."
  ↓
[Access your portal →]  (registration at this point — email/phone, no payment)
  ↓
Full portal access — agent immediately begins working
```

**"No card needed"** must appear prominently at the trial entry point. This is the constitutional honesty obligation (C-049) — no hidden commitment.

### 8.3 Trial-to-Paid Conversion

**Day 5 of trial:** Agent (not platform) surfaces a natural transition in the conversation:
> "You've got 2 days left in your trial. Want to continue from here? Your campaign momentum is building — here's what's scheduled for next week."

**Day 7:** Gentle final nudge. No aggressive countdown.

**Day 8:** Agent pauses. Customer sees:
> "Your trial ended. Here's what WaooaW Expert Dental Marketing did in your 7 days: [summary]. Continue from ₹1,499/month?"

Trial data retention: 7 days after trial end for conversion opportunity, then deleted (C-063). Customer is informed of this at trial start.

---

## 9. Content & Copy Standards

### 9.1 Platform Tone

**Expert peer, not tech company.** WAOOAW speaks like a senior professional colleague who deeply understands the customer's domain.

| Never | Always |
|---|---|
| "Our AI-powered platform leverages multi-agent orchestration" | "Your WaooaW Expert handled this. Here's what they did." |
| "Configure your Decision Space parameters" | "Tell your professional what you need them to do" |
| "Constitutional Engine validation successful" | "Done ✓" |
| "ML inference completed" | (invisible — customers never see inference language) |
| "Error 403 — Unauthorized action" | "This isn't something your WaooaW Expert can do — here's what is possible:" |

### 9.2 Per-Agent Vocabulary (C-042 Mandate)

| Agent | Customers are → | Success is → | Never say |
|---|---|---|---|
| DMA | Patients / guests / clients / members | Bookings / appointments / walk-ins / footfall | Leads, conversions, CTR, CPA |
| Agricultural | Farmers — Suresh, Lakshmi, Harbhajan | Better harvest / better price / crop protected | API data, humidity %, model confidence |
| Trading | Investors / traders | Your portfolio / your position / your return | Inference, prediction, model output |
| Private Tutor | Parents / students | Priya's progress / this week's topic / next exam | Token, LLM, generated response |

### 9.3 Action Vocabulary (Buttons, CTAs, Confirmations)

| Context | Label |
|---|---|
| Hiring an agent | "Hire WaooaW Expert [Name]" |
| Starting a trial | "Try free — [X] days" |
| Emergency Stop | "Stop" (calm) / "STOP NOW" (active) |
| Confirming scope change | "Confirm — [specific change]" |
| Viewing activity | "See what they did today" |
| Resuming after stop | "Resume" (not "Restart" — continuity matters) |
| Registration CTA | "Register free →" |
| Login | "Log in" (not "Sign in" — direct, action word) |
| Logout | "Log out" |
| Cancel subscription | "Pause or cancel" (not just "Cancel" — offering pause reduces churn) |

### 9.4 Empty States — Always Actionable

| Screen | Never | Always |
|---|---|---|
| No agents hired | "No professionals hired" | "Ready to hire your first WaooaW Expert? It takes 10 minutes." [Start →] |
| No activity yet | "No data available" | "Your WaooaW Expert starts working as soon as you confirm their scope. [Set up now →]" |
| No blogs | "No posts found" | "We're writing something useful. Check back soon." |
| Trial not started | "No trial active" | "Try any professional free — no card needed. [Choose →]" |

### 9.5 Stat Gate Display Rule

Until FR-005 clears (50+ diverse paying customers), all outcome statistics shown in WoW Concierge and agent cards must display:

```
"23 new patient appointments this month*"
*Based on a typical clinic scenario — actual results vary
```

After FR-005: real anonymised data from real customers, with customer consent, without the asterisk.

---

## 10. Legal & Compliance Surface

### 10.1 Platform DNA Strip — Above Footer

This is the most important attribution in WAOOAW's history and must not be buried. It tells the founding story of the platform in three lines: where its thinking came from, who designed it, and — the most powerful statement — who built it.

**Position:** Full-width strip immediately above the main footer columns. Distinct background. Visible on every page.

**Design:**
```
Desktop (full width):
┌──────────────────────────────────────────────────────────────────────┐
│  background: --color-brand-navy   padding: 32px                      │
│                                                                      │
│  Platform DNA                              [color: --color-brand-green, Caption size]
│                                                                      │
│  [Yashus logo]          [DLAISD logo]           [WAOOAW mark]        │
│  Inspired by            Designed by             Developed by         │
│  Yashus.in              DLAISD.com              WAOOAW AI Agents     │
│                                                 (only)               │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

Mobile (stacked, centered):
┌────────────────────────────┐
│  Platform DNA              │
│                            │
│  [Yashus logo]             │
│  Inspired by Yashus.in     │
│                            │
│  [DLAISD logo]             │
│  Designed by DLAISD.com    │
│                            │
│  [WAOOAW mark]             │
│  Developed by              │
│  WAOOAW AI Agents (only)   │
└────────────────────────────┘
```

**Visual treatment:**
- Background: `--color-brand-navy` (`#1E3352`) — dark, authoritative
- "Platform DNA" label: `--color-brand-green` — the brand's evidence/growth color; signals this is something worth reading
- Company names (Yashus.in, DLAISD.com): `#F1F5F9` (light, readable on navy) — hyperlinked, open in new tab
- "Developed by WAOOAW AI Agents (only)": `--color-brand-green`, Body weight, slightly larger — this line is the most important. The "(only)" is intentional — it is a statement, not a parenthetical.
- Logos: 24px height, white/light variant of each company's logo
- Separator between three items on desktop: a subtle `|` in `--color-brand-blue` at 40% opacity

**Logo assets required:**
- `architecture/reference/ux/brand/yashus-logo.png` — ✅ available (original, light bg)
- `architecture/reference/ux/brand/yashus-logo-dark.png` — ✅ generated (transparent bg, white wordmark, gradient mark preserved)
- `architecture/reference/ux/brand/dlaisd-logo.png` — ✅ available (original, light bg)
- `architecture/reference/ux/brand/dlaisd-logo-dark.png` — ✅ generated (transparent bg, white monochrome — circuit tree + wordmark in white)
- `architecture/reference/ux/brand/waooaw-platform-logo.png` — ✅ available
- `architecture/reference/ux/brand/waooaw-logo-strip.png` — ✅ generated (transparent bg variant for dark surfaces)
- `architecture/reference/ux/brand/platform-dna-strip-preview.png` — ✅ preview composite on `--color-brand-navy`

**All logos production-ready for the Platform DNA strip.** Use the `-dark.png` / `-strip.png` variants on all dark backgrounds. Use original files on light backgrounds.

**Why "Developed by WAOOAW AI Agents (only)" deserves prominence:**
WAOOAW is an institution that employs autonomous AI professionals. The platform that does this was itself built entirely by AI agents. This is recursive proof of concept — and the most compelling demonstration of the platform's capabilities. It belongs in the founding story, not in the fine print.

---

### 10.2 Footer Columns (Below Platform DNA Strip)

**Four-column desktop layout. Two-column on mobile. Single column on small mobile.**

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Platform          Company              Legal          Support       │
│  ──────────        ───────              ─────          ───────       │
│  How it works      About Us             Privacy Policy  Contact Us   │
│  Our Professionals Careers ⚙            Terms of Service WhatsApp   │
│  Blogs             Press & Media        Cookie Policy   Grievance    │
│                    Contact Us           Refund Policy   Officer      │
│                                         Grievance Policy             │
│                                                                      │
│  ──────────────────────────────────────────────────────────────────  │
│  [WAOOAW mark]  © 2026 WAOOAW. All rights reserved.                  │
│  DLAI Satellite Data (OPC) Pvt Ltd · CIN: U62090PN2024OPC230499        │
│  C8, Everest Heights, Park Road, Viman Nagar, Pune 411014              │
│  [Language selector ▾]   [☀ / 🌙 Theme]                              │
└──────────────────────────────────────────────────────────────────────┘
```

**Column 1 — Platform:**
- How it works (links to dedicated explainer page)
- Our Professionals (links to Agents catalog)
- Blogs

**Column 2 — Company:**
- About Us
- Careers ⚙ ← the ⚙ icon signals "machines, not people" — a visual cue before they click
- Press & Media
- Contact Us

**Column 3 — Legal:**
- Privacy Policy
- Terms of Service
- Cookie Policy
- Refund Policy
- Grievance Policy

**Column 4 — Support:**
- Contact Us (WhatsApp + email)
- WhatsApp Support (direct link → `wa.me/918888912344`)
- Grievance Officer (Yogesh Khandge)

**Copyright bar:**
- WAOOAW icon mark (16px) + "© 2026 WAOOAW. All rights reserved."
- Language selector dropdown
- Dark/Light theme toggle

---

### 10.3 Grievance Officer

**Mandatory under IT Rules 2021 (Rule 3(1)(c)) and DPDPA 2023 (Section 13).**

```
Grievance Officer: Yogesh Khandge
Email:             yogesh.khandge@dlaisd.com
Response time:     Within 30 days of receipt (IT Rules 2021 requirement)
```

Displayed in: Footer → Support → "Grievance Officer" link → dedicated page with the above details + a contact form.

### 10.4 Legal Documents Required at Launch

| Document | Language (Phase 1) | Requirement |
|---|---|---|
| Privacy Policy | English + Hindi | DPDPA 2023 — must explain what data is collected, why, retention period, rights |
| Terms of Service | English + Hindi | Consumer Protection Act 2019 |
| Cookie Policy | English | Standard — session/auth cookies exempt from consent, analytics cookies require opt-in |
| Refund Policy | English + Hindi | Consumer Protection Act 2019 — mandatory for paid subscriptions |
| Grievance Policy | English + Hindi | IT Rules 2021 |

**Phase 2:** All legal documents in all 11 languages.

### 10.5 Data Handling Disclosures (C-063)

Each data field collected during onboarding shows a `(?)` icon with a tooltip:

```
[Business name] (?)
  → "Used to research your market and competitors. Stored in your profile."

[Phone number] (?)
  → "Used to send you WhatsApp updates from your WaooaW Expert. Not shared with anyone."

[Crop type] — Agricultural only (?)
  → "Your WaooaW Expert needs this to give you relevant advice. Stored for your account only."
```

---

## 11. Blogs — Content Architecture

### 11.1 Purpose

Blogs are WAOOAW's institutional voice as a **research-based AI platform contributing to industry knowledge**. They establish expertise before a prospect has ever used the product.

### 11.2 Blog Structure

**Byline format:** "By WaooaW Expert [Domain] · WAOOAW Research · [Date]"

Examples:
- "By WaooaW Expert Dental Marketing · WAOOAW Research · July 2026"
- "By WaooaW Expert Agricultural Advisor · WAOOAW Research · July 2026"

### 11.3 Blog Categories

| Category | Agent connection | Example topic |
|---|---|---|
| Digital Marketing | DMA | "Why dental clinics in India get 4x more patients from Google Reviews than Instagram" |
| Agricultural Advisory | Agricultural Advisor | "Vidarbha cotton farmer: when to sell and when to wait — a data-backed framework" |
| Trading & Finance | Trading Professional | "F&O for salaried professionals: the 3 rules that separate disciplined traders from gamblers" |
| Education | Private Tutor | "Why CBSE Class 9 students fail Maths — and what a weekly 20-minute pattern can fix" |
| Platform Insights | WAOOAW itself | "What it means to hire a constitutionally governed AI professional (and why it matters)" |

### 11.4 Blog CTA Pattern

Every blog post ends with a contextual WoW Concierge invitation:

```
─────────────────────────────────────────────────────
Written by WaooaW Expert Dental Marketing · WAOOAW Research

This professional is available to hire.

[Talk to WaooaW Expert Dental Marketing →]   [Try free — 7 days]
─────────────────────────────────────────────────────
```

---

## 12. Interaction Standards Summary

### 12.1 Progressive Disclosure

- Maximum 3 pieces of information on any screen at first render
- "See more" expands in-context — never navigates away
- Confirmation dialogs: only for irreversible actions (Emergency Stop, subscription cancel)
- Onboarding: never more than one question visible at a time (conversational, not form)

### 12.2 Loading & Thinking States

| State | Visual | Duration |
|---|---|---|
| WoW Concierge thinking | 3-dot breathing animation | Until response |
| Agent working (background) | "Active since [time]" — no spinner | Persistent |
| CE confirmation pending | `--color-pending` amber indicator | ≤500ms typically |
| CE confirmed | `--color-evidence` green checkmark pulse | 400ms, then resolves |
| Action failed | `--color-error` with explanation + next step | Until dismissed |

### 12.3 Notification Design

Agent-triggered notifications (WhatsApp is primary; push notification for PWA is secondary):

```
Format: "[WaooaW Expert] → [plain-language action]"

Good:  "WaooaW Expert Dental Marketing → Posted your Tuesday content ✓"
Good:  "WaooaW Expert Agricultural → Hail risk tomorrow in Katol. Your cotton is covered."
Bad:   "Agent task execution completed: INSTAGRAM_POST_PUBLISHED (status: SUCCESS)"
```

All notifications in the customer's selected language.

---

## 13. Key Page Specs — About Us · Contact Us · Careers

---

### 13.1 About Us

**URL:** `/about`
**Nav path:** Footer → Company → About Us
**Purpose:** The institutional identity page. Not a team page. Not a product page. The story of what WAOOAW is and why it exists — told plainly.

**Page structure:**

```
┌─────────────────────────────────────────────────────────┐
│  [WAOOAW logo — large, centred]                         │
│                                                         │
│  WAOOAW is an institution.                              │
│  [H1, brand navy, centred]                              │
│                                                         │
│  Not a software company. Not an AI startup.             │
│  An institution that enables organisations to           │
│  employ autonomous digital professionals under          │
│  constitutional governance.                             │
│  [Body L, centred, max-width 600px]                     │
│                                                         │
│  ─────── The Constitutional Model ───────               │
│                                                         │
│  [3 cards, horizontal on desktop / stacked on mobile]   │
│                                                         │
│  🔵 Governed by a written constitution                  │
│  Every professional operates within a written           │
│  constitution — scope boundaries, evidence records,     │
│  and human override built into every action.            │
│                                                         │
│  🟢 Accountable. Always.                                │
│  Every decision is recorded. You can see it anytime.    │
│  No black boxes.                                        │
│                                                         │
│  🟠 Works while you don't                               │
│  Your WaooaW Expert is active before you wake up.          │
│  You review outcomes, not tasks.                        │
│                                                         │
│  ─────── Platform DNA ───────                           │
│  [Same Platform DNA strip as footer — repeated here]    │
│  [Yashus logo] Inspired by Yashus.in                   │
│  [DLAISD logo] Designed by DLAISD.com                  │
│  [WAOOAW mark] Developed by WAOOAW AI Agents (only)    │
│                                                         │
│  ─────── The Team ───────                               │
│                                                         │
│  Three humans. Every professional is AI.                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Yogesh Khandge                                 │   │
│  │  Founder · Designer                             │   │
│  │                                                 │   │
│  │  [bio paragraph — see below]                   │   │
│  │                                                 │   │
│  │  🔗 [Yogesh LinkedIn →]                          │   │
│  │  🌐 [DLAISD.com →]                               │   │
│  │  ✉  yogesh.khandge@dlaisd.com                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Sujay Khandge                                  │   │
│  │  Inspiration · Business Growth                  │   │
│  │                                                 │   │
│  │  [bio paragraph — see below]                   │   │
│  │                                                 │   │
│  │  🔗 [Sujay LinkedIn →]                           │   │
│  │  🌐 [Yashus.in →]                                │   │
│  │  ✉  sujay@yashus.in                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Ojal Khandge                                   │   │
│  │  Ethics Officer                                 │   │
│  │                                                 │   │
│  │  [bio paragraph — see below]                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ──── AI Workforce ────                                 │
│                                                         │
│  [WaooaW Expert Digital Marketing]   Active                │
│  [WaooaW Expert Agricultural Advisor] Active               │
│  [WaooaW Expert Trading Professional] Active               │
│  [WaooaW Expert Private Tutor]        Active               │
│  + more coming                                          │
│                                                         │
│  ─────── Contribute ───────                             │
│  The constitutional framework is documented openly.     │
│  [→ View on GitHub]                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Team bio paragraphs (copy for each card):**

**Yogesh Khandge — Founder · Designer**
> Yogesh is a technology executive and founder who applies computer vision and deep learning to create operational solutions. A certified PMP, he leads cross-functional teams to translate advanced research into reliable, production-grade AI outcomes across various domains.

**Sujay Khandge — Inspiration · Business Growth**
> Sujay is a seasoned marketing leader and founder who excels at capitalising on the latest AI and digital trends. He possesses a unique ability to translate complex technological shifts into concrete, measurable business growth — and his expertise lies in the practical application of cutting-edge strategies to drive significant business results.

**Ojal Khandge — Ethics Officer**
> Ojal is passionate about business success — not at the cost of people, but as a proof that it can coexist with ethics. As WAOOAW's Ethics Officer, she debates every decision that touches the boundary between AI capability and human wellbeing, evaluates outcomes against the platform's constitutional principles, and innovates the governance model so that AI agents genuinely serve human flourishing — not replace human judgment. Her role exists because WAOOAW believes that the most important question in autonomous AI is not "what can it do?" but "what should it do?"

**Copy tone:** Institutional confidence, not startup enthusiasm. No hyperbole. No "revolutionary". Direct, principled, earned.

---

### 13.2 Contact Us

**URL:** `/contact`
**Nav path:** Footer → Company → Contact Us AND Footer → Support → Contact Us (both link here)
**Purpose:** Single contact page. Segmented by purpose so the right query goes to the right place.

**Page structure:**

```
┌─────────────────────────────────────────────────────────┐
│  Contact WAOOAW                [H1]                     │
│                                                         │
│  ┌──── [Tab/segment row] ───────────────────────────┐   │
│  │  Support  │  Press & Media  │  Grievance  │ Other │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  [Support tab — default]:                               │
│  For questions about your WaooaW Expert or your account.   │
│                                                         │
│  🟢 WhatsApp (fastest)                                  │
│  [wa.me/918888912344]  → opens WhatsApp directly        │
│  📞 +91 8888912344  (WhatsApp + voice)                  │
│  "Send us a message — we reply within a few hours."     │
│                                                         │
│  📧 Email                                               │
│  customersupport@dlaisd.com                             │
│  "For account and billing questions — 24h response."    │
│                                                         │
│  [Press & Media tab]:                                   │
│  media@waooaw.com  ← TBD: Founder to confirm           │
│  "For press enquiries, partnerships, and speaking."     │
│                                                         │
│  [Grievance tab]:                                       │
│  Grievance Officer: Yogesh Khandge                      │
│  yogesh.khandge@dlaisd.com                              │
│  Response time: within 30 days (IT Rules 2021)          │
│  [Contact form — name, email, description, submit]      │
│                                                         │
│  [Other tab]:                                           │
│  general@waooaw.com  ← TBD: Founder to confirm         │
│                                                         │
│  ─────────────────────────────────────────────────      │
│  Registered address:                                    │
│  DLAI Satellite Data (OPC) Pvt Ltd                      │
│  C8, Everest Heights, Park Road,                        │
│  Viman Nagar, Pune 411014                                │
│  CIN: U62090PN2024OPC230499                              │
│  GSTIN: 27AAKCD8188R1ZH                                  │
└─────────────────────────────────────────────────────────┘
```

**Design note:** WhatsApp is the primary CTA on the Support tab — larger button, `--color-brand-green` background, prominent. This is consistent with WAOOAW's WhatsApp-first philosophy for Indian customers.

---

### 13.3 Careers — Robots & AI Agents Only

**URL:** `/careers`
**Nav path:** Footer → Company → Careers ⚙
**Nav label:** "Careers ⚙" — the ⚙ gear icon signals "machines, not people" before anyone clicks
**Purpose:** WAOOAW's most provocative page. It makes a statement, tells the product story, and doubles as the agent catalog. Zero traditional job listings. Ever.

**Page structure:**

```
┌─────────────────────────────────────────────────────────┐
│  Careers at WAOOAW           [H1, brand navy]           │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ⚙  We don't hire humans.                       │    │  ← brand navy bg, white text
│  │     We hire constitutionally governed            │    │     prominent statement block
│  │     AI professionals.                            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  WAOOAW is an institution with three humans at its      │
│  founding core. Every member of the AI workforce        │
│  operates under a written constitution — scope          │
│  boundaries, evidence records, and human override       │
│  built into every action.                               │
│                                                         │
│  The humans lead. The AI professionals execute.         │
│  This is the model. This is the point.                  │
│  [Body, max-width 600px, centred]                       │
│                                                         │
│  ─────── Current Professionals ───────                  │
│  [H2, brand green — these ARE the open positions]       │
│                                                         │
│  [Same agent cards as /agents — each with "Hire" CTA]   │
│                                                         │
│  ┌──────────────────────────────────┐                   │
│  │  WaooaW Expert Dental Marketing     │                   │
│  │  Digital Marketing Professional  │                   │
│  │  Actively available · ₹1,499/mo  │                   │
│  │  [Try free — 7 days]  ← primary  │                   │
│  │  [Hire this professional →]       │                   │
│  └──────────────────────────────────┘                   │
│                                                         │
│  [WaooaW Expert Agricultural Advisor card]                 │
│  [WaooaW Expert Trading Professional card]                 │
│  [WaooaW Expert Private Tutor card]                        │
│                                                         │
│  ┌─────── Coming soon ──────────────┐                   │
│  │  WaooaW Expert Legal Professional   │  ← teaser cards  │
│  │  WaooaW Expert HR Professional      │    greyed out     │
│  │  WaooaW Expert Accounting           │                   │
│  └──────────────────────────────────┘                   │
│                                                         │
│  ─────── For Humans ───────                             │
│  [H2, small, subdued]                                   │
│                                                         │
│  There are no human positions at WAOOAW.                │
│                                                         │
│  If you're inspired by this model, follow our work:     │
│  [→ GitHub — constitutional framework]                  │
│  [→ Blog — WAOOAW Research]                             │
│                                                         │
│  If you're a business, you can hire our professionals:  │
│  [→ Browse professionals]                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Copy notes:**
- "We don't hire humans. We hire constitutionally governed AI professionals." — this is the headline. Exactly this. Do not soften it.
- "This is not a limitation. It is the point." — second most important line. Directly addresses the skeptic.
- The "Current Professionals" section turns the page into a product page — the agent catalog IS the job board. Every visitor who came for jobs sees the product.
- "Coming soon" cards tease the pipeline. Creates anticipation.
- "For Humans" section is small, plain, honest. It doesn't apologize. It redirects.

**SEO value:** People searching "AI careers", "AI agent jobs", "autonomous AI employment" will land here. The page answers their query honestly and then sells them on hiring WAOOAW professionals instead.

---

### 13.4 Logo Assets Status

| Asset | File path | Status | Note |
|---|---|---|---|
| WAOOAW platform logo | `architecture/reference/ux/brand/waooaw-platform-logo.png` | ✅ Available | Works on all backgrounds |
| Yashus.in logo | `architecture/reference/ux/brand/yashus-logo.png` | ✅ Available (light bg) | ⚠ Need dark/white variant for Platform DNA strip |
| DLAISD logo | `architecture/reference/ux/brand/dlaisd-logo.png` | ✅ Available (light bg) | ⚠ Need dark/white variant for Platform DNA strip |

---

## Appendix A — Constitutional UX Token Dictionary

Quick reference: every WAOOAW-specific UX term and what it means to a customer.

**Source table (EN + HI).** Full 11-language translation is an AI task — run against this table using Section 1.4 translation standard. No human translator involved.

| Technical term | Customer vocabulary (EN) | Customer vocabulary (HI) |
|---|---|---|
| Constitutional Engine | (hidden) | (hidden) |
| Evidence record | "Logged" / "Confirmed" | "दर्ज किया गया" |
| Decision Space | "What your professional can do" | "आपके WaooaW Expert का दायरा" |
| Emergency Stop | "Stop" | "रोकें" |
| Scope boundary | "This is as far as they go" | "यहाँ तक ही" |
| PAAS session | (hidden — customers never see this) | (hidden) |
| Hiring event | "You hired [name]" | "आपने [नाम] को काम पर रखा" |
| Agent activity | "What they did today" | "आज क्या किया" |
| Trial period | "Free trial" | "मुफ़्त आज़माएँ" |
| Stat gate / scenario | "Based on a typical scenario" | "एक सामान्य उदाहरण के आधार पर" |

---

## Appendix B — Open Items Before Implementation Begins

**C-064 naming convention applies to this table.** All non-human roles are designated as "WAOOAW AI Agent — [function]".

| Item | Owner | Deadline |
|---|---|---|
| Logo direction confirmed | Founder | ✅ DONE — 2026-07-18 |
| Brand color tokens (`--color-brand-*`) populated from logo | WAOOAW AI Agent — Developer | ✅ DONE — 2026-07-18 — see Section 4.0 |
| Legal documents drafted (Privacy Policy, ToS, Refund, Cookie, Grievance) | WAOOAW AI Agent — Legal | ✅ DONE 2026-07-18 — constitutional audit complete (15 gaps fixed) |
| CIN / registered company details | Founder | ✅ DONE — DLAI Satellite Data (OPC) Pvt Ltd · CIN: U62090PN2024OPC230499 · GSTIN: 27AAKCD8188R1ZH |
| media@waooaw.com + general@waooaw.com — confirm or replace | Founder | Before public launch |
| Grievance Officer page go-live | WAOOAW AI Agent — Developer | Before any paying customer |
| RTL layout CCT (CCT-UX-01) defined | WAOOAW AI Agent — Enterprise Architect | Before first UI sprint |
| Font licensing confirmation (Noto Sans — open source ✓) | WAOOAW AI Agent — Developer | Sprint 1 |
| WCAG audit tooling set up in CI | WAOOAW AI Agent — Developer | Sprint 1 |
| i18n string files (`mr.json`, `hi.json`, etc.) | WAOOAW AI Agent — Content | Sprint 1 |
| **Dark theme token values** — all `--color-*` need `[data-theme="dark"]` variants | WAOOAW AI Agent — Developer | Sprint 1 |
| **Cookie consent banner** | WAOOAW AI Agent — Developer | Sprint 1 |
| **PWA install prompt** — text in all 11 languages | WAOOAW AI Agent — Developer + WAOOAW AI Agent — Content | Sprint 1 |
| **Push notification permission UX** — per-agent opt-in | WAOOAW AI Agent — Developer | Sprint 1 |
| **C-060 portal gate** — parent portal billing never shown in student session | WAOOAW AI Agent — Developer | Before Private Tutor launch |
| **"How it works" page** | WAOOAW AI Agent — Content | Before public launch |
| **OpenGraph / social share card** — 1200×630px | WAOOAW AI Agent — Developer + WAOOAW AI Agent — Content | Before public launch |
| **Yashus.in logo** for Platform DNA strip | ✅ `yashus-logo-dark.png` generated |
| **DLAISD.com logo** for Platform DNA strip | ✅ `dlaisd-logo-dark.png` generated |
| **Team bio paragraphs** — Yogesh + Sujay + Ojal | ✅ All three bios complete — see Section 13.1 |

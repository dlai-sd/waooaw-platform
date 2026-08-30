# Work Contract 078 - Public Acquisition Experience Implementation Plan

**Office:** Chief Solution Architect (INST-005)
**Future executor:** Platform IT Expert (INST-010), Skill 16
**Assigned by:** Founder instruction, 2026-08-30
**Status:** PLAN REPAIRED - PENDING FOUNDER ACCEPTANCE; IMPLEMENTATION NOT AUTHORIZED FOR THIS SESSION
**Delivery unit:** Public landing, public content, search discovery, and consent-governed acquisition
**Constitutional basis:** C-002, C-019, C-023, C-032, C-039, C-042, C-048, C-059, C-063, C-065, C-071, C-076, C-077, C-080, C-095, C-100

## Objective

Implement the Founder-approved WAOOAW public experience as server-rendered Next.js application
routes, preserving the recognizable design, content, and trust narrative of the historical
`web/WAOOAWHome.html` while retaining the current App Router as the only runtime entry point.

The implementation must make public-site colors, fonts, themes, copy, links, section visibility,
provider visibility, contact details, search metadata, and marketing destination identifiers
changeable through central typed configuration and locale content catalogs. It must provide a
complete search-discovery foundation and consent-governed acquisition measurement without exposing
customer, employment, constitutional, or institutional activity to advertising systems.

The implementation handoff must be executable without requiring INST-010 to invent route ownership,
visual behavior, event schemas, privacy rules, test scope, Docker workflow, evidence shape, or release
gates.

## Founder Decisions Fixed By This Contract

1. `web/WAOOAWHome.html`, recoverable from `798c183^:web/WAOOAWHome.html`, is the approved public
   design and content baseline. The restored file is a review input, not a production runtime.
2. The hero right-side headline is exactly **“From trial to autonomous productivity — in minutes”**.
   No exact setup-time or guaranteed productivity claim may be added without accepted evidence.
3. The hero right-side visualization becomes the finite **Autonomy Handoff Console** specified below.
4. Every approved historical content family is retained. Presentation and wording may be adapted to
   ratified accessibility, language, privacy, performance, and truthful-claim rules; no content
   family is silently omitted.
5. GA4, server-side GTM, Meta Pixel, Search Console verification, and UTM attribution are planned as
   environment-configured capabilities. Activation remains destination- and environment-gated.
6. Public content and presentation use typed repository configuration and locale catalogs. No CMS,
   content database, or public content-authoring service is introduced by WC-078.
7. The sole public contact address for support, media, general enquiries, and grievances is
   `customersupport@dlaisd.com`. No other public email address is rendered.
8. WAOOAW remains an AI-agent-managed platform. Public contact routing must not imply separate human
   departments or publish personal contact details.
9. The single-contact rule controls WAOOAW public rendering when a legal source record contains an
  internal, personal, departmental, telephone, or superseded contact. The legal substance, version,
  effective date, rights, and escalation sequence remain unchanged; every rendered contact command
  uses `customersupport@dlaisd.com` as the sole public intake address.

## Authority And Scope

This Work Contract authorizes plan creation only. It does not authorize application-source changes,
dependency installation, provider activation, environment mutation, deployment, spend, DNS changes,
customer traffic, UAT, Production, PR approval, or merge.

After separate explicit Founder implementation authorization, INST-010 may modify the existing web
application, its tests, Docker qualification tooling, CI alignment, and mandatory evidence needed to
deliver tasks PA-00 through PA-12. Any change under `src/`, any new deployable service, or any cloud
action requires its own authority and is not implied by this contract.

### Plan Acceptance And Implementation Authority

Founder acceptance of this repaired plan confirms the implementation boundaries and acceptance
criteria only. It does not authorize source changes. A future implementation session starts only
after the Founder explicitly authorizes WC-078 implementation for that session and every
pre-implementation gate below is satisfied. Plan acceptance, implementation authorization,
implementation completion, Founder acceptance of Demo, and release authorization are separate
control points and must never be reported as one another.

### In Scope

- Founder-approved landing-page migration into the current Next.js App Router.
- Public shared header, mobile navigation, announcement, Platform DNA, and footer.
- Public routes for home, professional discovery/detail, blogs/detail, About, Contact, Careers,
  Press, Constitution, Privacy, Terms, Cookies, Refund, and Grievance.
- Central typed site, theme, content, SEO, contact, provider-visibility, and marketing configuration.
- Eleven-locale public content architecture, including Urdu RTL behavior.
- Route metadata, canonical and locale alternates, robots, sitemap, Open Graph, social cards, and
  schema.org structured data.
- Consent banner/preferences, consent persistence, DNT/GPC handling, public-only tag loading,
  first-party acquisition events, attribution, deduplication, and environment destination routing.
- Public Login and Register commands that enter the Keycloak-brokered customer identity flow and
  reflect server-owned provider readiness.
- Accessibility, responsive, visual, browser, privacy, SEO, performance, security, and Docker
  qualification evidence.

### Out Of Scope

- Customer workspace design after login, including zero/evaluating/trial/active/paused/multiple
  professional start views. That is the next separately discussed UI component.
- Institutional workspace and `/admin/login` design, office navigation, and role-specific tools.
  That is the subsequent separately discussed UI component.
- Identity-provider account creation, Keycloak realm mutation, Meta or Apple activation, or changes
  to the canonical identity contracts owned by WC-077.
- A CMS, public content database, drag-and-drop editor, feature-flag service, or new design-system
  dependency.
- Public WaooaW Concierge runtime, free-form prospect chat, or model-provider call. The approved
  Concierge concept remains unavailable until its service, privacy, retention, token-budget, and
  abuse contracts are separately approved.
- Unsupported performance statistics, customer testimonials, guarantees, or fabricated availability.
- UAT, Production, customer traffic, DNS, Search Console property mutation, campaign launch, or
  advertising spend.

## Required Inputs And Pre-Implementation Gates

| Input | Required state | Use |
|---|---|---|
| `web/WAOOAWHome.html` at historical blob `798c183^` | Founder-approved design/content baseline | Migration inventory only |
| `architecture/reference/ux/constitutional-ux-vocabulary.md` | RATIFIED | Controlling language, navigation, footer, public-page, accessibility, performance, and content rules |
| `architecture/reference/ux/hybrid-visual-system-contract.md` | `RATIFIED` before any implementation source change | Token, shape, typography, motion, imagery, and precedence rules; no implementation-time reconciliation |
| `architecture/reference/ux/hybrid-application-shell.md` | `RATIFIED` before any implementation source change | App Router, server/client, route, privacy, and API boundaries; no implementation-time reconciliation |
| `architecture/reference/ux/hybrid-ui-acceptance-contract.md` | `RATIFIED` before any implementation source change | Existing executable quality floor; no implementation-time reconciliation |
| `architecture/reference/components/identity-boundary.md` | Canonical; provider activation gates remain controlling | Login/register and provider-readiness projection |
| `architecture/reference/api-specs/business-platform.openapi.yaml` | Canonical | Generated identity/provider client source |
| `adr/ADR-008-keycloak-identity-broker.md` | Accepted v3 | Keycloak-only credential authority |
| `adr/ADR-017-web-application-framework.md` | Accepted | Next.js, TypeScript, SSR, PWA, and generated-client boundary |
| `legal/privacy-policy.md`, `legal/terms-of-service.md`, `legal/cookie-policy.md`, `legal/refund-policy.md`, `legal/grievance-policy.md` | Existing legal source records; public rendering requires owner confirmation that versions remain current | Public legal pages |
| `security/SECURITY-HEADERS.md` | Active | CSP, referrer, permissions, transport, and browser security headers |
| `constitution/PROJECT_STATE.md` | Re-read at implementation and deployment start | Current session/environment authority |

Before source changes, INST-010 must confirm Skill 16 remains active, all controlling specifications
are `RATIFIED`, the Founder has explicitly authorized WC-078 implementation for the current session,
the public-catalogue and acquisition boundaries below remain approved and unchanged, and the
implementation branch is not `main`. A `REVIEW CANDIDATE` controlling input is a stop, not a deferred
implementation task.

## Component Determination And Runtime Boundary

WC-078 introduces no new platform deployable component. C-095 is satisfied by the approved existing
Web Application component under ADR-017. The following are internal modules of that component:

1. **Public Experience Renderer** - server components, route composition, content catalogs, and
   metadata generation.
2. **Public Site Configuration** - typed, validated, environment-aware non-secret configuration.
3. **Consent Controller** - minimal client island for explicit preferences and withdrawal.
4. **Acquisition Event Boundary** - same-origin Next.js server endpoint that validates, minimizes,
   deduplicates, and routes approved public events.
5. **Destination Adapters** - server-owned GA4 and server-side GTM dispatch plus a consent-gated
   public Meta browser adapter when activated.

The Business Platform remains the sole public business API facade. Keycloak remains credential
authority. Public pages do not read relationship, customer, tenant, evidence, billing, conversation,
or institutional data.

### Public Professional Catalogue Boundary

The anonymous `/professionals` and `/professionals/[slug]` routes do not call the authenticated,
outcome-based Business Platform endpoints `/api/v1/professionals` or
`/api/v1/professionals/{professionalType}/disclosure`. They render only a typed, repository-backed
public publication catalogue owned by the Web Application component. Each admitted record has a
stable public slug, professional type and version, approved public copy, approved trial/price display
state, publication state, modification date, and source approval reference.

The catalogue is release configuration, not a production fallback mock or live availability source.
It may say only what its approval record supports and must not infer runtime capacity, eligibility,
price, customer fit, or current service health. Dynamic discovery or availability requires a
separately approved Business Platform public contract. INST-010 must stop rather than expose the
authenticated endpoints, invent an anonymous endpoint, query protected data, or manufacture a live
availability projection.

### Public Acquisition Runtime Boundary

The same-origin acquisition endpoint and destination adapters are internal modules of the existing
Web Application component. The endpoint is stateless across requests: it validates and minimizes the
event, re-derives public context, applies consent and environment policy, and forwards the stable
event ID to each enabled destination that supports retry deduplication. It introduces no database,
Redis key, durable queue, file store, raw-event ledger, or new public Business Platform API.

WC-078 stores no raw acquisition event first-party. It does not promise exactly-once dispatch.
Browser retries reuse the same event ID, destination adapters preserve that ID, and bounded retries
remain destination-specific. Consent state is limited to the versioned first-party preference
defined below. Any durable acquisition audit, cross-instance deduplication, attribution store,
retention service, or new adapter contract requires separate architecture, privacy, security, and
Founder approval. INST-010 must stop rather than choose persistence technology or silently weaken
this boundary.

## Public Information Architecture

| Route | Indexing | Source and purpose | Required primary action |
|---|---|---|---|
| `/` | Index | Approved landing composition and institutional value proposition | Meet/interview a professional; Login; Register |
| `/professionals` | Index | Searchable public professional catalogue | Inspect an available professional |
| `/professionals/[slug]` | Index only for admitted, publicly available versions | Domain-specific outcomes, scope, limits, trial and availability | Start approved trial/registration path |
| `/blogs` | Index | Research and professional guidance hub | Open an approved article |
| `/blogs/[slug]` | Index only when publication state is `PUBLISHED` | Server-rendered research article | Contextual professional CTA |
| `/about` | Index | Institutional identity, constitutional model, Platform DNA, three-human governance | Browse professionals or constitutional record |
| `/contact` | Index | One contact channel segmented by customer intent | Email `customersupport@dlaisd.com` |
| `/careers` | Index | AI-professional employment model and professional catalogue | Browse/hire professionals |
| `/press` | Index | Approved media facts and downloadable approved assets | Email `customersupport@dlaisd.com` |
| `/constitution` | Index | Plain-language constitutional overview with canonical-document link | Read governance model |
| `/privacy` | Index | Current approved privacy policy | Contact support |
| `/terms` | Index | Current approved terms | Contact support |
| `/cookies` | Index | Current approved cookie policy and preference entry | Open cookie preferences |
| `/refund` | Index | Current approved refund policy | Contact support |
| `/grievance` | Index | Current approved grievance policy and contact route | Email `customersupport@dlaisd.com` |
| `/login`, `/register`, `/verify`, `/account-link`, `/auth/*` | Noindex, follow | Customer identity | Complete the selected identity task |
| `/admin/*`, authenticated, system, API, and error routes | Noindex, nofollow | Non-public surfaces | None |

Unknown professional/blog slugs return a real 404. Draft, blocked, retired, or unavailable content
must not render a crawlable success page. Query strings never create canonical variants.

## Approved Landing Composition

The home route renders these ordered content families. Each becomes a named server component with
typed content input; visual components contain no business copy or destination identifiers.

| Order | Component | Historical source | Required behavior |
|---|---|---|---|
| 1 | Announcement bar | `announce-bar` | Optional configured campaign; dismissible; no local tracking before consent |
| 2 | Public header | historical nav plus ratified navigation contract | Logo, Home, Professionals, Blogs, Settings, Login, Register; compact four-item navigation |
| 3 | Hero offer | `hero` | Preserve prominent WAOOAW identity, clear professional-employment offer, two honest actions |
| 4 | Autonomy Handoff Console | replaces `tl-frame` | Finite four-state demonstration defined below |
| 5 | Getting started | `how` | Conversational, low-effort progression; no exact time guarantee |
| 6 | Professional catalogue preview | `agents` | Server-owned available professional data/approved fixtures; no unavailable capability as active |
| 7 | Trust journey | `trust journey` | Scenario-labelled demonstrations only; no unproven customer result or testimonial |
| 8 | Constitutional promise | `promise` | Stop, evidence, honest limits, trial, data isolation, governed improvement |
| 9 | Final action | `final-cta` | Registration/trial and browse actions with truthful availability |
| 10 | Platform DNA | `dna-strip` | Approved Yashus, DLAISD, and WAOOAW assets and exact attribution |
| 11 | Public footer | historical footer plus ratified Section 10 | Platform, Company, Legal, Support, company identity, locale and theme controls |

The current “Three steps in 10 minutes” copy is replaced with **“Three clear steps. Then productive
work begins.”** The plan does not authorize exact duration labels such as `2 min`, `5 min`, or
`10 minutes` unless an accepted claim record later supplies evidence and the content configuration
explicitly activates those labels.

## Hero Autonomy Handoff Console

### Purpose

The hero's right-side frame demonstrates the core USP: a person can move from trial into governed,
autonomously productive work in minutes. It must look like trustworthy system activity, not a
decorative progress diagram.

### Stable Structure

- One restrained frame using semantic surface, border, and elevation tokens.
- Header: **“From trial to autonomous productivity — in minutes”**.
- Four vertically stacked status rows with stable reserved dimensions:
  1. `Trial started` - `Explore the professional with no commitment.`
  2. `Business understood` - `Your goals and working context are captured.`
  3. `Scope approved` - `You confirm what the professional may and may not do.`
  4. `Working autonomously` - `Productive work has started.`
- Each row contains a small semantic icon, title, one-line explanation, and non-numeric state label.
- Completed rows use a text-plus-icon confirmed treatment. Confirmation green appears only in this
  demonstration when the entire frame is visibly labelled `Illustrative journey`; it must not be
  presented as live customer evidence.
- The final row settles into a quiet `Active` state. It has no spinner and does not imply guaranteed
  continuous availability.

### Motion Contract

- On first viewport entry, rows reveal in order using opacity plus at most 8px block-axis transform.
- Total sequence duration is at most 4.8 seconds and runs once per page load. It never loops.
- Each transition uses only approved 150ms, 250ms, or 400ms durations.
- Layout dimensions are reserved before animation; CLS contribution is zero.
- No connecting track, large circles, rotating ring, progress percentage, scaling pulse, parallax,
  autoplay video, canvas, or animation dependency is permitted.
- `prefers-reduced-motion: reduce` renders all four rows immediately in the settled state.
- The complete semantic content exists in initial server-rendered HTML. Motion is enhancement only.
- The status sequence is not an ARIA live region; screen readers receive one stable ordered list and
  are not forced through decorative state announcements.
- If animation initialization fails, the settled state remains complete and usable.

### Responsive Contract

- Expanded: console occupies the right hero region and aligns with the offer block.
- Intermediate: console remains beside the offer only when both retain readable minimum widths;
  otherwise it moves below the offer.
- Compact: full-width vertical console below the primary hero actions. No horizontal timeline or
  clipped label is permitted at exactly 360px and 200% zoom.
- RTL: icon/text ordering and reveal direction use logical properties; the content order remains
  semantically 1 through 4.

## Configurable Public Experience Contract

### Configuration Layers

1. `web/config/site.ts` - company identity, canonical origin, contact, route availability, navigation,
   footer, social links, section switches, and non-secret environment labels.
2. `web/config/theme.ts` - primitive typography, color, spacing, radius, elevation, and duration values
   mapped to CSS custom properties.
3. `web/config/marketing.ts` - typed environment destination enablement and public identifiers only.
4. `web/content/en.ts` and one same-shape catalog per remaining locale - public source copy and SEO
   content. Existing catalogs may be migrated rather than duplicated if one canonical shape remains.
5. Server-only environment parsing - secret references, destination endpoints, and verification
   values. Invalid or incomplete configuration disables the affected destination safely.

All configuration is schema-validated at build/start. Unknown keys, duplicate route/section IDs,
invalid colors, unsupported locale, unsafe URL protocol, wildcard destination, secret-like value in
public configuration, missing English source, untranslated required key, or enabled destination with
missing readiness values fails qualification.

### Theme Rules

- Components consume semantic and constitutional CSS variables only. Raw values remain in the theme
  definition.
- The approved primitives remain blue `#1A66C2`, green `#3DAD35`, orange `#F7941D`, navy `#1E3352`,
  and Noto script families unless changed by a later approved configuration revision.
- No Georgia or alternate display font remains. No font size scales with viewport width.
- No physical directional CSS (`left`, `right`, `margin-left`, `padding-right`, or equivalents) is
  used where a logical property exists.
- Light, dark, and system themes are complete. High-contrast token names are reserved but high
  contrast remains outside this delivery unless separately selected.
- Changing one primitive must update all consuming components without component edits and must pass
  contrast, screenshot, and constitutional color checks.

### Content Rules

- English is source truth; all 11 locale catalogs share the exact key schema.
- Urdu uses Noto Nastaliq Urdu, `dir=rtl`, and line-height at least 2.0.
- Public claims follow C-002 and C-042. No technical architecture language, unsupported percentage,
  guaranteed outcome, or false availability appears in acquisition copy.
- Personal names and direct personal contact details are not published as routing channels. The
  approved About page may identify the three governing humans, but all contact actions resolve to
  `customersupport@dlaisd.com`.
- Legal pages render approved legal source content without silently rewriting legal meaning. A source
  version and effective date are visible.

## Search Discovery Contract

### Metadata

Every indexable route supplies a unique, localized title, description, canonical URL, locale
alternates, Open Graph type/title/description/url/image, and social-card metadata through the Next.js
Metadata API. The root metadata becomes a fallback, not the public acquisition message.

- Canonical host is environment-configured and HTTPS outside local development.
- Canonicals remove tracking parameters, fragments, and non-content query parameters.
- Locale alternates include every actually translated public route plus `x-default`.
- Login, registration, admin, authenticated, API, preview, draft, error, and fixture routes cannot be
  indexed.
- Social images are approved, dimensioned assets. No runtime image-generation dependency is added.

### Crawl And Sitemap

- Implement Next.js `robots.ts` and `sitemap.ts` as server-owned metadata routes.
- Production permits approved public routes and references the production sitemap.
- Demo and UAT disallow all crawling and emit `noindex, nofollow` independently of robots behavior.
- Sitemap entries include only canonical, published, indexable URLs with real modification dates.
- Draft/blocked/retired content, auth routes, protected routes, APIs, preview routes, and query variants
  are excluded.
- Search Console verification is environment configuration. Verification and sitemap submission are
  external activation evidence, not hardcoded application success.

### Structured Data

Use serialized JSON from typed objects, never hand-built JSON strings. Only data visible on the page
may appear in structured data.

| Route | Required schema.org types |
|---|---|
| `/` | `Organization`, `WebSite`, and `Service` only where offer data is approved |
| `/professionals/[slug]` | `Service`, `Offer` only when current approved public price/availability exists, and `BreadcrumbList` |
| `/blogs/[slug]` | `Article`, authoring organization, dates, and `BreadcrumbList` |
| `/about`, `/contact`, `/careers`, legal pages | `BreadcrumbList`; `ContactPoint` only with the single approved support address |

Structured data must not claim reviews, ratings, customer counts, outcomes, prices, availability, or
FAQ answers that are absent or unapproved in visible source content.

### Content And Internal Linking

- One primary search intent, one H1, and one truthful route summary per indexable page.
- Professional detail pages target approved domain/outcome language, not generic keyword repetition.
- Blog posts use the ratified category/byline/CTA model and are published only from approved content.
- Header, body CTAs, breadcrumbs, professional cards, related articles, and footer form a crawlable
  `<a href>` internal-link graph. Navigation must not depend on JavaScript click handlers.
- Heading levels are sequential; links use descriptive labels; duplicate pages are not generated for
  campaign parameters.
- Core Web Vitals and public payload budgets remain release gates because search discoverability and
  accessibility depend on them.

## Consent-Governed Acquisition Contract

### Consent Categories And State

| Category | Default | Purpose |
|---|---|---|
| `necessary` | Always on | Security, server session, locale, theme, consent record |
| `analytics` | Off | Anonymous public acquisition measurement and GA4 |
| `advertising` | Off | Meta campaign measurement and advertising attribution |

Consent is explicit, granular, versioned, reversible, and not bundled with registration. Reject is as
easy as accept. DNT or Global Privacy Control forces analytics and advertising off. Withdrawal takes
effect before any subsequent destination dispatch. The consent controller stores only category
choices, policy version, and timestamps in a secure first-party preference. It stores no identity,
tenant, relationship, or campaign profile.

The cookie policy and runtime cookie names, purposes, duration, security flags, and actual behavior
must match before release. Necessary authentication and CSRF cookies are not described as optional.

### Versioned Event Vocabulary

| Event | Trigger | Required event data beyond common envelope |
|---|---|---|
| `public_page_viewed` | One accepted public route view | `route_id`, optional `content_id` |
| `professional_viewed` | Public professional detail becomes visible | `professional_type` |
| `registration_started` | User invokes Register | `entry_route`, optional `professional_type` |
| `identity_provider_selected` | User selects a server-enabled provider | `provider_id` |
| `registration_completed` | Server confirms account completion | No account or identity field |
| `hire_journey_started` | User invokes an approved trial/hire journey | `professional_type`, `entry_route` |
| `contact_invoked` | User selects the support mail command | `contact_intent` |
| `consent_updated` | Consent preference changes | Category booleans only; updates the versioned first-party preference and is never routed to advertising |

Common envelope version `1.0` contains only: UUID event ID, event name, schema version, UTC timestamp,
public route ID, locale, environment, consent-category snapshot, optional UTM source/medium/campaign,
optional referrer classification (`direct`, `search`, `social`, `campaign`, `other`), and anonymous
session-scoped deduplication ID. It does not contain raw referrer URL.

The browser cannot add arbitrary fields. It submits a discriminated event union to the same-origin
boundary. The server validates the event, re-derives route/environment, removes unapproved fields,
applies consent and destination policy, preserves the event ID for destination-native retry
deduplication, and returns `202` without revealing destination details. The response confirms
request acceptance, not destination delivery. Invalid input returns a privacy-safe problem response.

### Prohibited Acquisition Data

Never emit name, email, phone, IP as an event field, tenant/account/relationship IDs, provider subject
or token, authorization code, message or form content, business name, goals, plans, work, results,
evidence, billing/payment data, assurance state, institutional route/activity, full URL containing
query values, raw referrer, user-agent fingerprint, or persistent cross-context identifier.

Infrastructure may process source IP and user agent transiently for transport/security, but
destination payload builders must not copy them unless a separately approved legal/security contract
explicitly requires it.

### Destination And Environment Matrix

| Destination | Demo | UAT | Production | Loading/dispatch rule |
|---|---|---|---|---|
| First-party boundary | Test mode | Validation mode | Live | Always available for consent operations; acquisition event acceptance remains category-gated |
| GA4 | Test property | Non-production property/debug validation | Approved production property | Server-dispatched after analytics consent |
| Server-side GTM | Test endpoint/container | Non-production endpoint/container | Approved production endpoint/container | Server-dispatched after matching consent; strict HTTPS allowlist |
| Meta Pixel | Test pixel/event tooling | Non-production validation | Approved production pixel | Public routes only, advertising consent only; browser script and server event use one deduplication ID |
| Search Console | Verification only; no public indexing | Verification only; no public indexing | Approved property and sitemap | No behavioral tracking tag required |

Configuration uses explicit per-environment enablement. Missing ID, endpoint, secret reference,
allowlist, consent, or readiness record disables only that destination and records a privacy-safe
operational result. It never blocks the page, registration, another destination, or public rendering.

Public identifiers may enter browser configuration only when necessary for an activated browser tag.
GA4 Measurement Protocol secrets, server-side GTM credentials, and any provider secret remain
server-only secret references. Marketing scripts are absent from protected customer and all
institutional layouts, bundles, network traces, and service-worker caches.

### Attribution, Retention, And Failure

- Accept only normalized `utm_source`, `utm_medium`, and `utm_campaign` values with bounded length and
  character allowlists. Discard arbitrary campaign parameters.
- Attribution is held only in the consent-scoped browser session, bounded to the configured
  acquisition window, and sent only in an allowed event envelope. WC-078 creates no server-side
  attribution profile or raw-event store.
- Duplicate browser/server Meta events share one event ID. Retry uses the same ID with bounded
  exponential backoff; no unbounded queue or request blocking is permitted.
- Destination failure does not fail navigation, authentication, registration, or hiring. It emits a
  privacy-safe operational metric without customer payload.
- WAOOAW does not retain raw accepted acquisition events first-party under WC-078. Destination
  retention remains separately governed and must be reflected in the approved public policy before
  that destination is enabled.
- Consent withdrawal prevents future dispatch and clears optional browser identifiers/cookies within
  the same interaction. No claim of deleting data already lawfully received by a destination is made
  unless confirmed by that destination.

## Security And Privacy Requirements

- Apply the repository security-header policy, including HSTS outside local development, CSP,
  frame-ancestors, content-type, referrer, and permissions policies.
- CSP destination allowlists are generated from validated enabled configuration. GTM or Meta
  activation cannot widen script/connect/image/frame origins beyond the exact approved hosts.
- No `unsafe-eval`, wildcard source, provider secret, inline executable string, or remote script is
  introduced outside the approved nonce/hash strategy.
- Public pages, metadata, structured data, browser logs, analytics, errors, and URLs contain no
  protected or personally identifying data.
- Service workers cache only approved static shell assets. Marketing scripts, consent state,
  acquisition payloads, auth responses, and protected content are never cached.
- External links use approved HTTPS origins and safe opener/referrer behavior.
- Contact uses a `mailto:` command to `customersupport@dlaisd.com`; WC-078 does not create a contact
  form or data-collection endpoint.

## LLM And Token-Cost Controls

Implementation and qualification must not require live LLM calls. Public copy, translations,
metadata, structured data, fixtures, and expected results are deterministic repository inputs.

- Use no model call for page render, metadata generation, SEO generation, translation at runtime,
  tests, screenshots, visual comparison, lint, build, scanning, or evidence synthesis.
- If a separately authorized content-generation activity uses an LLM, batch all required routes and
  locales into one bounded task, send only the English source keys and mandatory vocabulary subset,
  use the least-cost approved model meeting language quality, cache by source/config hash, and never
  regenerate unchanged keys.
- Record model, prompt/catalog version, input/output token totals, cost estimate, cache hits, changed
  keys, and author-review result. Enforce a Founder-approved hard budget before dispatch.
- No autonomous retry follows a valid model response. One retry is permitted only for a documented
  transport/provider failure and reuses the same bounded request.
- Generated copy is never accepted merely because generation succeeded; deterministic schema,
  vocabulary, prohibited-claim, missing-key, and locale checks remain mandatory.

## Ordered Implementation Work Components

| Task | Scope and required output | Focused development check |
|---|---|---|
| PA-00 | Re-read gates; stop unless all three controlling UX contracts are `RATIFIED`; inventory historical sections against current routes; record one migrate/adapt location per content family; confirm the public catalogue and stateless acquisition boundaries; and confirm no new deployable component. | Gate check plus configuration/schema unit test skeleton fails for one invalid fixture, proving the check is active |
| PA-01 | Normalize public primitives and semantic/constitutional tokens; remove alternate fonts, hardcoded component colors, viewport-scaled type, and RTL-breaking physical properties in touched public styles. | Token schema plus light/dark and LTR/RTL component test |
| PA-02 | Add typed site/theme/marketing configuration and same-shape locale catalogs with build/start validation. | Valid config loads; unknown key, unsafe URL, missing locale key, and secret-like public value fail |
| PA-03 | Implement shared public header, compact navigation, announcement, Platform DNA, and complete footer using approved assets and route-aware links. | Header/footer component test plus one 360px browser smoke |
| PA-04 | Migrate the approved landing composition and implement the Autonomy Handoff Console exactly as specified. | Hero component test plus reduced-motion and zero-CLS browser example |
| PA-05 | Complete public professional, About, Contact, Careers, Press, Constitution, and legal routes; route every contact action to the single support address. | Endpoint examples for each route, 404 behavior, heading/link integrity, and no protected requests |
| PA-06 | Implement deterministic repository-backed blog index/detail publication model, category/byline/CTA rules, draft exclusion, and related internal links. | Published/draft/unknown slug examples and Article schema test |
| PA-07 | Implement route metadata, canonical/alternate rules, social metadata/assets, robots, sitemap, and typed JSON-LD. | Endpoint examples parse HTML, robots, sitemap, canonicals, noindex, and structured data |
| PA-08 | Implement consent controller, category persistence, DNT/GPC override, withdrawal, policy-version behavior, and cookie-policy/runtime reconciliation. | Accept/reject/withdraw/DNT/GPC browser examples with cookie and network assertions |
| PA-09 | Implement the stateless same-origin acquisition endpoint, discriminated event schema, minimization, session-bounded attribution normalization, stable destination event identity, and privacy-safe failures without first-party raw-event persistence. | Endpoint examples for every event plus prohibited-field, same-event-ID retry, malformed, no-consent, and no-persistence cases |
| PA-10 | Implement environment adapters for GA4, server-side GTM, Meta, and Search Console verification; enforce public-only loading and independent safe disablement. | Destination fixture examples for Demo/UAT/Production and protected-layout absence |
| PA-11 | Extend existing F1 browser, axe, visual, privacy, PWA, performance, locale/RTL, metadata, CSP, and marketing suppression checks to the complete public surface. | Run only newly affected suites while repairing; no full campaign yet |
| PA-12 | Freeze commit history, build hash-tagged images once, run the complete Docker qualification once, repair only evidenced defects, bind final evidence and PR author review to final HEAD, validate repository gates, and push once. | `wc078-qualification.json` reports PASS and binds source/config/image/evidence hashes |

Do not run the full campaign after each task. During PA-00 through PA-11, run endpoint-focused or
component-focused checks at the first substantive edit and at bounded task completion. Group related
edits before the next focused run. Coverage, full browser matrix, production build, SBOM, Trivy,
Gitleaks, and complete evidence generation run once during PA-12 unless a failure requires repairing
the same slice and rerunning only the failed gate before one final clean qualification.

## Docker-Only Execution And Qualification Protocol

### Absolute Environment Rule

WAOOAW is Docker infrastructure. Python or Node virtual environments, host `pip`, host `pytest`, host
`npm`/`pnpm` tests, and ad hoc host-installed scanners are prohibited. Docker/Compose and repository
shell/git commands may orchestrate work; test, build, coverage, browser, SBOM, Trivy, and Gitleaks
execution occurs in pinned containers or repository Docker images.

### 1. Docker Preflight

Run before tests or builds:

```sh
docker version
docker compose version
docker system df
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}'
docker compose config --quiet
```

If free Docker capacity is inadequate, capture `docker system df -v` first. Remove only disposable
artifacts:

```sh
docker image prune --force
docker builder prune --force --filter 'until=24h'
```

Never use `docker system prune`, `docker volume prune`, broad `docker container prune`, or delete a
running, pinned, evidence, database, or user-named image/container/volume. Record before/after space
in qualification evidence. If safe cleanup does not provide adequate capacity, stop and report the
capacity blocker.

### 2. Quick Configuration And Smoke

Start with `docker compose config --quiet`. Build the changed service and test runner with the current
source/config hashes. Run one smoke test per changed service before broader development checks. For a
web-only change, prove the production image starts, its health route answers, `/` renders, and one
invalid route returns 404. If another service is changed under separate authority, add exactly one
service-owned health/contract smoke before its focused tests.

### 3. Immutable Local Image Identity

Calculate:

```text
SOURCE_HASH = first 12 hex of SHA-256 over tracked WC-078 implementation inputs
CONFIG_HASH = first 12 hex of SHA-256 over normalized Compose plus public config/lock/tool inputs
IMAGE_TAG   = wc078-${SOURCE_HASH}-${CONFIG_HASH}
```

The qualification script must define the exact sorted file inventory and normalization algorithm.
Build `waooaw-web:${IMAGE_TAG}` and the corresponding TypeScript test image once for final
qualification. Record immutable image IDs and content digests. Reuse those exact image IDs for smoke,
tests, coverage, build verification, SBOM, Trivy, and evidence capture. Do not rebuild between gates.
Any source, lock, Dockerfile, Compose, tool-version, or relevant configuration change invalidates the
hash and requires one new image pair and a new final qualification.

### 4. Evidence-First Retry Rule

On failure, capture before cleanup or retry:

```sh
docker compose ps --all
docker compose logs --no-color --timestamps <changed-service>
docker inspect <container>
docker system df
```

Classify the failure as code/configuration, assertion, security finding, capacity, daemon/network,
registry, or external dependency. Retry unchanged code once only when logs and resource state show an
infrastructure failure. Do not retry a deterministic test failure, lint/build error, scan finding, or
contract mismatch. Repair it, rebuild under a new hash when required, and rerun the failed focused
gate.

### 5. Focused Development Checks

Use the pinned `test-runner-ts` image and existing Jest/Playwright selectors for the touched route,
component, endpoint, locale, or acceptance ID. Run a focused check immediately after the first
substantive implementation edit. Thereafter run focused checks at bounded task completion, not after
every snippet or visual adjustment.

Endpoint-focused examples must cover actual Next.js responses while coding: status, headers,
canonical/noindex behavior, JSON-LD parsing, sitemap/robots, consent event acceptance/denial, and
destination fixture dispatch. Reserve the deterministic all-route, all-browser, all-locale campaign
for PA-12.

### 6. One Final Qualification Campaign

INST-010 must add one repository command:

```sh
./scripts/wc078_qualify.sh --output test-results/wc078/wc078-qualification.json
```

The script is a Docker-only orchestrator. It may use host POSIX shell, Docker/Compose, git, and jq for
orchestration and evidence assembly, but it must not execute a host language runtime, package manager,
test, build, or scanner. It must fail closed, use pinned image/tool versions already accepted by the
repository or explicitly recorded in the script, and produce the JSON only from observed command
results.

The one command performs, in order:

1. Docker capacity/state capture, safe disposable cleanup when needed, Compose config validation, and
   one smoke per changed service.
2. Source/config hash calculation and one final build of the reusable tagged web/test images.
3. Focused WC-078 endpoint/contract examples as a fast qualification guard.
4. Full Jest coverage with at least 90% changed interactive line coverage.
5. Production Next.js build verification and generated-route inspection from the exact qualified web
  image. The Docker image build produces the application build once; this gate inspects and starts
  that artifact and does not invoke a second application build.
6. Complete Chromium, Firefox, WebKit, 360x800, 768x1024, 1440x900, English/Urdu, light/dark,
   axe, keyboard, reduced-motion, screenshot, privacy, PWA, metadata, structured-data, consent,
  destination-suppression, and performance campaign. Browser tests set `BASE_URL` to the already
  running qualified web image so Playwright does not trigger its current build-on-start fallback.
7. CycloneDX or SPDX SBOM generation from the exact qualified image.
8. Trivy HIGH/CRITICAL vulnerability scan using the repository-pinned policy.
9. Gitleaks full-history/diff scan using the repository-pinned policy.
10. C-059 traceability, commit-format, generated-artifact drift, and relevant architecture-fitness
    gates used by the repository workflows.
11. Evidence JSON assembly and schema validation.

The evidence JSON contains at minimum:

```json
{
  "schema_version": "1.0",
  "work_contract": "WC-078",
  "result": "PASS",
  "head_sha": "40-character commit",
  "source_hash": "12 hex",
  "config_hash": "12 hex",
  "images": [{"name": "waooaw-web", "tag": "...", "id": "sha256:...", "digest": "sha256:..."}],
  "docker_preflight": {"before": {}, "cleanup": [], "after": {}},
  "smokes": [],
  "focused_examples": [],
  "tests": [],
  "coverage": {},
  "build": {},
  "browsers": {},
  "accessibility": {},
  "performance": {},
  "seo": {},
  "consent_and_marketing": {},
  "sbom": {"path": "...", "sha256": "..."},
  "trivy": {"result": "PASS", "report": "...", "sha256": "..."},
  "gitleaks": {"result": "PASS", "report": "...", "sha256": "..."},
  "repository_gates": [],
  "started_at": "RFC3339",
  "completed_at": "RFC3339"
}
```

`PASS` is emitted only when every mandatory gate passes against the recorded HEAD and image IDs.
Command lines, pinned versions, exit codes, counts, report paths, and report hashes are recorded.
Secrets, tokens, cookies, raw URLs with query values, customer data, and scanner credentials are
redacted and never enter evidence.

Qualification reports are generated under the repository's ignored test-results/evidence boundary or
uploaded as PR/CI artifacts. They are not committed after qualification. Committing generated evidence
would change HEAD and invalidate the evidence binding; only its path, schema version, SHA-256, and
artifact locator are recorded in the PR body.

### 7. Commit, Evidence, PR, And Push Order

1. Complete implementation and focused repair checks.
2. Finalize the intended implementation commits with repository-conforming subjects and mandatory
   traceability bodies.
3. Run the one complete qualification against that finalized HEAD.
4. Do not change implementation after qualification. A code/config/tool change invalidates evidence.
5. Prepare the PR body from `.github/pull_request_template.md`, including WC-078, constitutional
   basis, exact qualification evidence path/hash, image IDs, SBOM/scan results, rollback, and findings.
6. Perform mandatory author review against the complete diff and exact qualification results.
7. Complete the PR template's Author Review checklist, set `Reviewed Commit` to the full
  40-character HEAD, and set `Author Review Result` to `PASS` only after reviewing the complete diff
  and final qualification evidence.
8. Through the repository-approved execution environment, run
  `python scripts/validate_author_review.py --pr-body-file <pr-body-file> --head <full-head-sha>` and
  `python scripts/validate_c059.py --pr-body-file <pr-body-file> --base origin/main --head <full-head-sha>`.
  Both must pass before push.
9. Push once and create or update the unmerged PR for Founder review. Hosted commitlint, C-059,
  author-review, and remaining PR gates must pass against that same HEAD before Founder review or
  merge. Any later commit invalidates qualification and bound review evidence and requires
  requalification, rebinding, and a justified additional push.

## Implementation-Completion Acceptance Matrix

These conditions are future runtime completion evidence. Their presence and structural validation in
an accepted plan does not mean the implementation tasks or acceptance conditions have passed.

| ID | Acceptance condition |
|---|---|
| PA-ACC-01 | The App Router is the only production entry; no static parallel landing runtime remains |
| PA-ACC-02 | Every approved historical content family maps to a rendered server component and disposition record |
| PA-ACC-03 | Autonomy Handoff Console follows the exact content, finite-motion, reduced-motion, SSR, RTL, and zero-CLS contract |
| PA-ACC-04 | One central configuration change can alter an approved primitive, link, contact, section switch, or destination ID without editing consuming components |
| PA-ACC-05 | All 11 locale catalogs conform; Urdu RTL and 200% zoom have no clipping, overlap, or horizontal overflow |
| PA-ACC-06 | Every public route has correct status, H1, metadata, canonical, alternates, internal links, and index/noindex behavior |
| PA-ACC-07 | Sitemap, robots, Open Graph, social assets, and typed structured data validate and exclude non-public states |
| PA-ACC-08 | All contact paths resolve only to `customersupport@dlaisd.com` |
| PA-ACC-09 | Login/Register remain Keycloak-brokered; provider visibility is server-owned and unavailable providers are not presented as active |
| PA-ACC-10 | Consent accept, reject, withdrawal, DNT, GPC, and policy-version changes deterministically control optional storage and dispatch |
| PA-ACC-11 | Event union rejects arbitrary/prohibited fields; server re-derives context, normalizes only session-bounded attribution, preserves stable event identity for destination-native retry deduplication, and creates no first-party raw-event persistence |
| PA-ACC-12 | GA4, server-side GTM, Meta, and Search Console behavior is independently environment-gated and fails without blocking the customer journey |
| PA-ACC-13 | Advertising code and events are absent from authenticated and institutional bundles, pages, service-worker caches, and network traces |
| PA-ACC-14 | Security headers and exact CSP allowlists pass; no secret or protected value appears in source, browser, logs, evidence, URLs, or metadata |
| PA-ACC-15 | FCP <=1.5s, LCP <=2.5s, CLS <=0.10, INP <=200ms under the approved profile; public compressed weight <=200KB and initial JS <=100KB gzipped |
| PA-ACC-16 | Zero critical axe violations, no unreviewed serious violations, keyboard journeys pass, and focus behavior is stable |
| PA-ACC-17 | No runtime/test LLM call occurs; any separately authorized content-generation call has hard budget and token evidence |
| PA-ACC-18 | One Docker qualification command produces schema-valid PASS evidence bound to final HEAD and reused image IDs |
| PA-ACC-19 | Full coverage, build, browsers, SBOM, Trivy, Gitleaks, local traceability, and author-review validation pass before the initial push; hosted PR gates pass against the same HEAD before Founder review or merge |

## Rollback And Release

- Build once and promote the same digest through separately authorized Demo, UAT, and Production
  gates. Do not rebuild per environment.
- Public configuration is environment-bound and schema-versioned. Destination enablement can be
  disabled independently without rolling back the public page.
- Marketing failure rollback first disables the affected destination; it does not disable login,
  registration, contact, or public content.
- A content/config rollback restores the prior accepted configuration version and image digest.
- Database-destructive rollback is not applicable because WC-078 introduces no content database.
- Demo proof precedes Founder acceptance. UAT remains prohibited until that acceptance, and Production
  remains separately authorized. Search indexing and campaign activation occur only in Production
  after exact authority.

## Stops

- Stop before application-source implementation without explicit Founder authorization for WC-078 in
  the current session.
- Stop if controlling UX status is unresolved or an implementation choice would alter Reference
  Architecture, introduce a deployable component, CMS, telemetry dependency, or public API.
- Stop rather than run any virtual environment, host package installation, host test runtime, or
  unpinned scanner.
- Stop rather than omit an approved historical content family without Founder disposition.
- Stop rather than publish an exact productivity duration, outcome percentage, testimonial, rating,
  price, availability, or customer count without accepted evidence.
- Stop rather than activate Meta or Apple login before their independent identity gates pass.
- Stop rather than load optional tags before consent, ignore DNT/GPC, emit prohibited data, or allow
  advertising code on protected/institutional surfaces.
- Stop rather than add wildcard CSP origins, expose a secret, cache acquisition/auth/protected data,
  or fabricate a successful destination dispatch.
- Stop if safe Docker cleanup cannot provide capacity; never delete persistent volumes or protected
  artifacts to force a run.
- Stop on a deterministic failing test or scan finding; do not hide it through retry, exclusion,
  baseline replacement, threshold reduction, or skip.
- Stop if final evidence is stale relative to HEAD, source/config hash, image ID, tool version, or PR
  author-review metadata.
- Never self-approve, self-merge, push directly to `main`, mutate an environment without exact current
  authority, or treat search ranking as guaranteed.

## Plan Definition Of Done

- The public professional catalogue source is explicitly repository-backed and cannot be confused
  with the authenticated Business Platform discovery endpoints or live availability.
- The acquisition endpoint is explicitly stateless, introduces no persistence technology, and does
  not claim exactly-once destination delivery or first-party raw-event retention.
- All controlling UX specifications are named as `RATIFIED` pre-implementation gates; no
  implementation-time status reconciliation remains.
- Plan acceptance is distinct from implementation authorization and runtime completion evidence.
- No unresolved plan decision requires INST-010 to invent an API, persistence architecture,
  authorization rule, legal contact route, or completion claim.

## Future Implementation Definition Of Done

- This contract provides INST-010 complete route, content, configuration, hero, SEO, consent,
  acquisition, privacy, security, Docker, evidence, rollback, and stop contracts.
- Implementation tasks PA-00 through PA-12 and acceptance IDs PA-ACC-01 through PA-ACC-19 are
  traceable in source, tests, evidence, commits, and PR metadata.
- The approved historical design remains recognizable while ratified UX rules control adaptations.
- Theme, font, content, contact, route composition, and environment destination changes are centrally
  configurable without editing consuming components.
- Search-discovery implementation is truthful, crawlable, server-rendered, fast, localized, and
  structurally valid; no ranking guarantee is made.
- Marketing automation is consent-governed, privacy-minimized, environment-specific, independently
  disableable, and absent from protected surfaces.
- Docker execution uses focused development checks and exactly one clean final qualification campaign
  against finalized commits and reusable hash-tagged images.
- Final qualification evidence, author review, repository gates, and unmerged PR are bound to the
  same 40-character HEAD. Founder retains approval and merge.

## Author Review

**Original result:** PASS - plan complete; implementation remained separately gated.

**Focused repair result:** PASS - one Founder-requested concurrent INST-004/INST-005 review pass was
limited to the four reported architecture gaps. The repaired contract now makes UX ratification a
pre-source gate, defines the repository-backed public catalogue boundary, defines a stateless
no-persistence acquisition boundary, separates plan acceptance from implementation completion, and
records the Founder-fixed single public contact rule. No generic second review was performed.

INST-005 reviewed the complete WC-078 output against the Founder-approved historical page, ratified
UX vocabulary, current App Router and F1 acceptance implementation, identity boundary, legal source
records, security-header policy, consolidated foundation assessment, and every explicit Founder
instruction from 2026-08-30.

The review checked requirements coverage, route and component ownership, server/client boundaries,
truthful claims, theme configurability, all eleven locales and RTL, public content completeness,
search metadata and structured data, consent and destination isolation, data minimization, failure
behavior, no-new-component status, LLM token controls, Docker-only execution, disk safety, focused
development checks, image reuse, evidence-first retry, single final qualification, final-commit
ordering, evidence/PR binding, rollback, and constitutional stops.

Original findings repaired in this contract include the conflict between the historical numeric timeline and
the approved non-numeric headline, ambiguity between public landing scope and later customer/admin UI,
the difference between search optimization and vendor tags, browser/server Meta deduplication, DNT/GPC
behavior, exact support routing, test frequency, disposable Docker cleanup, stale evidence after a
rebuild, the current-main author-review/C-059 gate path and hosted-gate ordering, and the prohibition
on runtime/test LLM calls. No unresolved in-scope author-review finding remains.
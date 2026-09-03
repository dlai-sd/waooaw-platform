# WC-078 Public Experience Visual Remediation Implementation Plan

**Artifact type:** Solution Architecture component contract and implementation Work Component plan
**Owning office:** Chief Solution Architect (INST-005)
**Implementation office:** Platform IT Expert (INST-010), Skill 16
**Requirements input:** `architecture/reference/ux/wc-078-visual-experience-requirements-input.md`
**Parent delivery:** WC-078 Public Acquisition Experience, merged through PR #376 at `e20539b`
**Status:** REVIEW CANDIDATE - FOUNDER ACCEPTANCE AND IMPLEMENTATION AUTHORIZATION REQUIRED
**New deployable component:** NO - existing Web Application component only
**Application implementation authority:** NOT GRANTED BY THIS PLAN
**Environment authority:** NONE
**Constitutional basis:** C-002, C-032, C-039, C-042, C-059, C-063, C-065, C-071, C-076, C-080, C-095, C-100; ADR-017

## 1. Work Package Objective

Remediate the visual, content, motion, responsive, localization, and substantive screenshot quality
of the existing WC-078 public landing experience without reopening or weakening the accepted public
platform delivered by WC-078.

Platform IT Expert must implement the smallest additive and substitutive UI change that:

- restores recognizable continuity with the Founder-approved `web/WAOOAWHome.html`;
- replaces only the current hero handoff console and duplicated getting-started presentation with a
  two-professional journey;
- repairs defects VR-01 through VR-12;
- preserves every unaffected WC-078 route, contract, privacy rule, acquisition rule, identity
  boundary, search-discovery behavior, legal projection, configuration boundary, and acceptance
  outcome;
- authors complete deterministic tests alongside each story but executes all Docker tests, builds,
  browsers, screenshots, scans, and qualification only after implementation is complete;
- produces one final Docker-only executable evidence package plus named substantive screenshot review.

This plan is self-contained for implementation after all entry gates pass. It does not grant those
gates.

### 1.1 Work Package Outcome

The completed work package is one Founder-reviewable PR that contains the narrowly bounded public
UI remediation and its tests, preserves WC-078 behavior outside the approved visual delta, passes
one end-of-implementation Docker qualification against finalized source, and binds all automated and
substantive visual evidence to the same 40-character HEAD.

## 2. Precedence And Amendment Boundary

The following precedence applies:

1. Ratified constitutional UX vocabulary, accepted ADRs, security policy, identity boundary, and
   legal source records.
2. Ratified hybrid application shell, visual system, and UI acceptance contracts.
3. WC-078 public acquisition plan, except the exact clauses superseded below after Founder acceptance.
4. This plan and its requirements input.
5. Implementation code and tests.

Founder acceptance of this plan records the selected solution but does not authorize application
source changes. Before implementation, the owner of the hybrid visual system and WC-078 must ratify
or Founder must explicitly accept these exact deltas:

| Existing clause | Superseding clause in this plan | Everything else remains |
|---|---|---|
| WC-078 Founder Decision 2, exact old hero-console headline | Section 8 fixed hero copy and claim gate | All truthful-claim restrictions |
| WC-078 Founder Decision 3 and Hero Autonomy Handoff Console | Sections 7 through 10 two-professional journey | SSR, accessibility, reduced motion, RTL, zero-CLS, no fabricated live state |
| WC-078 landing composition item 5, separate getting-started section | Section 6 disposition `MERGE INTO HERO` | Every other approved historical content family |
| WC-078 PA-ACC-03 | VRA-02 through VRA-05 and Section 19 acceptance mapping | PA-ACC-01/02 and PA-ACC-04 through PA-ACC-19 |
| Hybrid visual system prohibition on connecting track/cycling movement | Section 9 finite interactive rail and one-run state machine | Approved transition primitives, reduced motion, stable dimensions, semantic fallback |
| Hybrid visual system text-first asset restriction | Section 10 functional editorial explanation | No stock/atmospheric/decorative imagery, asset budgets, CSP, accessibility |
| WC-078 focused test after each implementation slice | Sections 15.3 and 17 end-of-implementation Docker campaign | Every focused check remains mandatory; only execution timing changes to avoid repeated container/build overhead |

If those deltas are not accepted, implementation is BLOCKED. INST-010 must not reconcile normative
conflicts in code.

## 3. Implementation Entry Gate

Before touching `web/`, tests, dependencies, screenshots, Docker tooling, or generated evidence,
INST-010 must record all of the following:

| Gate | Required evidence |
|---|---|
| Session authority | Founder explicitly authorizes WC-078 visual-remediation implementation in the current session |
| Branch | Working branch is not `main`; unrelated changes are identified and left untouched |
| Skill | Platform IT Expert Skill 16 remains ACTIVE |
| Plan | This plan is Founder-accepted and no longer `REVIEW CANDIDATE` |
| Normative deltas | Every Section 2 visual/motion amendment is accepted by its owner or explicit Founder decision |
| Claims | Accepted approval references exist for `ten minutes a day`, `10 min`, and `24/7` or the remediation remains disabled |
| Content | OD-01 through OD-05 recommendations are accepted; no implementation-time copy invention remains |
| Localization | Approved English source and reviewed translations are supplied or incomplete locales are disabled according to Section 14 |
| Dependencies | Existing icon/tooling availability is confirmed; no new runtime or design-system dependency is needed |
| Component | C-095 no-new-component determination remains valid |
| Baseline | Prior merged WC-078 qualification evidence is recorded as the accepted baseline; no Docker rerun occurs before implementation |
| Docker | Docker execution is deferred to WC-09; repository configuration is not changed merely to make local execution convenient |

Failure of any gate is a stop. A TO-DO, issue, merged WC-078, accepted plan, or `G5 CLEAR` is not
current-session implementation authorization.

## 4. Good-Work Preservation Contract

WC-078 is an accepted working baseline. This remediation is not permission to redesign its platform
architecture or opportunistically refactor it.

### 4.1 Frozen Behavior

The following are `PRESERVE_AND_REGRESSION_TEST`; they are not implementation work unless a focused
test proves this remediation caused a regression:

| WC-078 area | Preservation rule |
|---|---|
| App Router and route inventory | Remain the only runtime; no static parallel landing, route rename, or route removal |
| Typed configuration | Existing site/theme/marketing schema and safe-disable behavior remain; add only fields required by this plan |
| Professional catalogue | Repository-backed publication state remains authoritative; do not call protected discovery or infer live availability |
| Public information routes | Professional, blog, company, Constitution, and legal route content/metadata remain unchanged except shared shell presentation |
| Identity | Login/Register continue only through the WC-077 Keycloak-brokered paths and server-owned provider readiness |
| Contact | Every public contact command remains `customersupport@dlaisd.com`; no form or new collection endpoint |
| SEO | Metadata, canonical, alternates, robots, sitemap, social metadata, and typed JSON-LD behavior remain |
| Consent | Categories, DNT/GPC, withdrawal, policy version, storage minimization, and equal reject/accept behavior remain |
| Acquisition events | Existing discriminated union, stateless same-origin boundary, minimization, event identity, retry, and no-persistence rules remain |
| Destination adapters | Existing environment and consent gates remain; no activation, endpoint, secret, or allowlist change |
| Privacy and security | CSP, HSTS, public/protected separation, service-worker cache exclusions, and no-PII rules remain |
| PWA | Existing manifest, icons, offline public shell, and protected-cache exclusions remain |
| Performance | FCP <=1.5s, LCP <=2.5s, CLS <=0.10, INP <=200ms, public compressed <=200KB, initial JS <=125KB gzip |
| Evidence | Existing WC-078 Docker qualification and final-HEAD binding are extended, not replaced |

### 4.2 Change Discipline

- Do not touch `src/`, infrastructure, identity services, Business Platform contracts, legal source
  files, marketing destination code, or deployment workflows.
- Do not rename exported configuration fields, routes, event names, locale IDs, consent categories,
  metadata types, or test projects unless this plan explicitly requires it.
- Do not reformat or restructure unaffected files.
- Preserve passing tests. Update an existing assertion only when it asserts an explicitly
  superseded hero/getting-started behavior; record the old assertion, new acceptance ID, and reason.
- A failing preserved test is evidence of drift. Repair the visual slice rather than deleting,
  weakening, skipping, or broadly regenerating the test.
- Snapshot and screenshot changes are route/state-specific. Bulk baseline replacement is prohibited.
- Do not add a generalized animation framework, global state store, CMS, content service, telemetry,
  persistence, endpoint, or new deployable module.

## 5. Existing Component And Ownership Boundary

No new platform component or C-095 skeleton is required. Work remains inside the ADR-017 Web
Application and these existing internal modules:

| Internal module | Ownership in this plan |
|---|---|
| Public Experience Renderer | Server-owned route composition, content projection, SEO-preserving HTML, and section disposition |
| Public Site Configuration | Server/build-owned non-secret presentation switches, claim approval references, campaign revision, and content validation |
| Minimal Motion Island | Browser-owned presentation state only: professional/stage selection, finite timer, reduced motion, and scroll-state enhancement |
| Consent Controller | Existing behavior preserved; only its non-obstructive visible entry placement may change |
| Acquisition Event Boundary and Destination Adapters | No behavioral change; regression tests only |

The browser must not infer professional availability, claim approval, customer fit, runtime health,
identity readiness, consent, authorization, or acquisition outcomes. It receives display-safe,
server-validated public content and uses local state only to choose which illustrative card is shown.

## 6. Landing Composition And Disposition Ledger

| Order | Content family | Disposition | Unique customer purpose | Implementation constraint |
|---|---|---|---|---|
| 1 | Announcement | ADAPT | Show one optional current notice | Configuration-driven, consent-neutral, dismissible, no content overlap |
| 2 | Public header | ADAPT | Establish brand and reach public actions | Transparent at top; floating readable surface after scroll; routes unchanged |
| 3 | Hero offer | REPLACE COPY/PRESENTATION | Explain value and primary action | Fixed copy; two ranked existing destinations; claim gate |
| 4 | Autonomy Handoff Console | REPLACE INTERNAL PRESENTATION | Show concrete professional journey | Replace with `ProfessionalJourneyShowcase`; no second runtime or data source |
| 5 | Getting started | MERGE INTO HERO | Explain setup with no repetition | Remove rendered section only; its meaning moves to hero stages |
| 6 | Professional catalogue preview | ADAPT PRESENTATION | Help compare truthful admitted professionals | Publication state unchanged; improve card hierarchy and differentiation |
| 7 | Trust journey | CONSOLIDATE COPY | Explain safeguards through distinct examples | No repeated hero/setup copy; preserve truthful scenario label |
| 8 | Constitutional promise | CONSOLIDATE COPY | Explain review, pause, stop, limits, isolation | Plain language; no removed safeguard or fabricated evidence |
| 9 | Final action | ADAPT PRESENTATION | Repeat one clear next step after proof | Same route authority and truthful availability |
| 10 | Platform DNA | REPAIR | Attribute Yashus, DLAISD, WAOOAW | Approved assets/content; complete contrast in every theme |
| 11 | Public footer | ADAPT PRESENTATION | Company, legal, support, locale/theme, cookie access | Routes/contact unchanged; no floating obstruction |

No other public route or WC-078 content family is removed.

Every observed defect has one bounded remediation and proof owner:

| Defect | Remediation owner | Required proof |
|---|---|---|
| VR-01 | WC-05 | Platform DNA light/dark contrast checks and reviewed screenshots |
| VR-02 | WC-05, WC-08 | Density constraints and 360/768/1440 substantive screenshot review |
| VR-03 | WC-03, WC-04 | Concrete two-professional semantic and motion journey |
| VR-04 | WC-05, WC-07 | Publication-state label/icon/CTA fixture matrix |
| VR-05 | WC-05, WC-07 | Consent/footer access and fixed-control collision matrix |
| VR-06 | WC-03, WC-05 | Unique-purpose disposition and rendered content assertions |
| VR-07 | WC-03, WC-05 | One CTA hierarchy and destination assertions |
| VR-08 | WC-02, WC-08 | Logo/header dimensional checks and visual acceptance |
| VR-09 | WC-05, WC-08 | Light-first theme rhythm and transition screenshots |
| VR-10 | WC-05 | Comparable professional-card content/state tests |
| VR-11 | WC-07, WC-08, WC-09 | Route/state baselines plus named substantive review bound to HEAD |
| VR-12 | WC-01, WC-06, WC-08 | Translation ledger, fallback detection, script/RTL screenshots |

## 7. Revised Component Contract

### 7.1 Component Tree

The implementation may adapt local names to existing conventions, but ownership must remain:

```text
PublicHomePage                         [server]
  AnnouncementBar                     [client only for dismiss action]
  PublicHeader                        [client only for scroll/menu controls]
  HeroOffer                           [server]
    HeroActions                       [server links]
    ProfessionalJourneyShowcase       [minimal client island]
      ProfessionalSelector            [presentation control]
      JourneyViewport                 [presentational]
        DomainIllustration             [presentational]
        JourneyCard                    [presentational]
      JourneyRail                     [presentation control]
      SettledWorkStatus                [presentational]
  ProfessionalCataloguePreview        [server]
  TrustAndControl                     [server]
  FinalAction                         [server]
  PlatformDna                         [server]
  PublicFooter                        [server with existing control islands]
```

Do not make the whole page a client component. Only dismissal, scroll threshold, compact navigation,
professional/stage selection, and finite motion require browser state.

### 7.2 Typed Inputs

The showcase receives a read-only, same-shape localized model from server-owned content:

```ts
type JourneyStageId =
  | "opening"
  | "business"
  | "goals"
  | "agreement"
  | "ready"
  | "working";

type JourneyRailId = "business" | "goals" | "ways-of-working" | "working";
type ProfessionalStoryId = "agricultural-advisor" | "digital-marketing-professional";

type ProfessionalJourneyStory = Readonly<{
  id: ProfessionalStoryId;
  selectorLabel: string;
  contextLabel: string;
  illustrationLabel: string;
  stages: ReadonlyArray<Readonly<{
    id: JourneyStageId;
    railId: JourneyRailId;
    title: string;
    summary: string;
    details: ReadonlyArray<string>;
    state: "intro" | "active" | "attention" | "complete";
  }>>;
}>;
```

This defines shape, not a requirement to create these exact exported names. Existing locale schema
conventions control placement. The build validator must reject duplicate IDs, missing six-stage
coverage, invalid rail mappings, empty labels/details, untranslated required keys, unknown state,
and unsupported professional ID.

### 7.3 Server And Client Responsibilities

| Server/build responsibility | Browser responsibility |
|---|---|
| Validate configuration, locale shape, claims, publication state, CTA destination, and announcement campaign | Select one already-approved story/stage for display |
| Render complete meaningful initial HTML and fallback | Apply finite 150/250/400ms visual transitions |
| Supply approved public copy only | Stop autoplay permanently on user interaction |
| Keep all stories available without network fetch | Honor reduced motion and visibility lifecycle |
| Own metadata, links, and acquisition event semantics | Maintain focus, pressed/selected state, and stable dimensions |

No hero interaction calls an API, writes acquisition data, changes consent, or claims live runtime
state. Existing link invocation may continue to emit only already-approved WC-078 events.

## 8. Resolved Content Recommendations And Claim Gate

These recommendations become fixed implementation inputs only when the Founder accepts this plan:

| Requirement decision | Selected solution |
|---|---|
| OD-01 selector | Primary labels: `Agricultural Advisor` and `Digital Marketing Professional`; supporting contexts: `Farm business` and `Growing business` |
| OD-02 final message | `Your AI professionals work 24/7. You step in when needed.` |
| OD-03 marketing example | Clearly labelled illustrative profile: `A growing dental clinic in Pune`; no customer name, testimonial, metric, or claimed result |
| OD-04 CTAs | Preserve existing destinations; primary `Meet a professional`, secondary `Start with a trial`; primary uses filled command treatment, secondary outlined treatment |
| OD-05 announcement | Existing configured campaign copy/destination; dismissal stores only campaign revision and dismissed state until revision changes; footer provides no announcement rediscovery requirement |
| OD-06 compact ratio | `4 / 3` at >=480 CSS px available width; `1 / 1` below 480 only for the internal showcase, with centered single-card sequence |
| OD-07 technology | Existing React, CSS, approved icon library, and repository assets only; no Lottie, canvas, video, animation package, or new runtime dependency |
| OD-08 claims | Remediation enablement fails validation unless non-empty accepted approval references are configured for ten-minute and continuous-availability claims |

### 8.1 Fixed Hero Copy

```text
Grow your business with WAOOAW AI professionals

Guide the work in just ten minutes a day. Spend more time growing your business.
```

### 8.2 Claim Configuration

Use the existing typed public configuration pattern. The architecture requires equivalent fields,
not these exact property names:

```text
visual_remediation_enabled
ten_minute_claim_approval_ref
continuous_availability_claim_approval_ref
announcement_campaign_revision
```

Rules:

- When remediation is disabled, the current accepted WC-078 experience remains available.
- Enabling remediation without both accepted claim references fails build/start validation.
- References are non-secret record identifiers, not arbitrary justification text.
- UI does not show references or infer their validity; qualification checks them against the
  approved configuration fixture.
- INST-010 must not replace, qualify, or partially publish the fixed copy to avoid this gate.
- `24/7` means the approved professional may continue scheduled/monitored work; it is not a service
  availability SLO, uninterrupted provider promise, or guaranteed outcome.

## 9. Hero Motion State Machine

### 9.1 Semantic And Rail Mapping

All six semantic stages are represented. Four rail controls group them without omitting meaning:

| Semantic stage | Rail control | Agriculture | Digital Marketing |
|---|---|---|---|
| Opening | Business | Illustrative farm profile enters | Illustrative growing clinic profile enters |
| Your business | Business | 2-acre farm, Junnar, Pune, year-round water | Pune clinic, services, current website/social presence |
| Your need | Goals | Crop productivity, crop choice, harvest and market timing | Digital footprint, relevant enquiries, channel and campaign goal |
| Your agreement | Ways of working | Track crop, fertilizer, irrigation, weather, market | Four posts weekly, channels, review points, sensitive approvals |
| Ready to work | Ways of working | Share goals, review plan, approve material change, receive alerts | Share goals, review campaign, approve sensitive work, receive alerts |
| Working 24/7 | Working 24/7 | Weather/crop/irrigation/market status | Campaign/content/response/enquiry status |

### 9.2 Deterministic States

```text
IDLE_INITIAL
  -> AUTO_AGRI_OPENING
  -> AUTO_AGRI_BUSINESS
  -> AUTO_AGRI_GOALS
  -> AUTO_AGRI_AGREEMENT
  -> AUTO_AGRI_READY
  -> AUTO_AGRI_WORKING
  -> AUTO_DMA_OPENING
  -> AUTO_DMA_BUSINESS
  -> AUTO_DMA_GOALS
  -> AUTO_DMA_AGREEMENT
  -> AUTO_DMA_READY
  -> AUTO_DMA_WORKING
  -> SETTLED_SHARED

Any AUTO_* -- user selector/rail/key/pointer --> MANUAL_SELECTION
Any state -- reduced motion at initialization --> SETTLED_SHARED
Any state -- initialization failure --> STATIC_COMPLETE_FALLBACK
```

The complete automatic story lasts 8-12 seconds. Every card transition uses only existing 150ms,
250ms, or 400ms primitives; remaining time is a stable reading dwell, not a new animation duration.
Use one schedule table, not chained independent timers. Cleanup runs on unmount. Background-tab
visibility pauses progression without catching up through skipped announcements. Returning to the
tab resumes from the current state unless the user has interacted.

### 9.3 Interaction Rules

- Autoplay starts once after the showcase first enters the viewport and never loops.
- Any selector, rail, keyboard, or pointer selection cancels autoplay for that page lifetime.
- Professional selector changes only illustrative story content and retains the nearest semantic
  stage; no page navigation or network request occurs.
- Rail controls use buttons with `aria-pressed` or an equivalent selected-state pattern. They are not
  links, tabs for route content, sliders, or an ARIA live timeline.
- Left/Right follows visual rail order in LTR; logical previous/next behavior mirrors in RTL. Tab
  order remains DOM order. Home/End may move to first/final rail control.
- Focus never moves automatically. Story changes are not announced step-by-step. One concise static
  accessible description explains the full journey.
- Previous/next cards may peek only above 480px available width. Compact mode renders one centered
  card and preserves all controls.
- Completed uses icon plus text plus green. Active uses icon/text/blue. Attention uses icon/text/
  orange. Inactive uses icon/text/neutral. No state relies on color alone.
- No bounce, flip, spin, pulse, rotating ring, parallax, glow, autoplay video, canvas, or infinite
  translation.

### 9.4 Reduced Motion And Failure

With `prefers-reduced-motion: reduce`, render `SETTLED_SHARED` immediately, disable autoplay and card
travel, and keep professional/rail controls available with instant or opacity-only state changes.
Server-rendered content and a no-JavaScript/failure path expose both professional names, all stage
meaning, CTAs, and the final message without requiring animation.

## 10. Visual System Delta

### 10.1 Layout And Density

| Region | Expanded | Intermediate | Compact |
|---|---|---|---|
| Content width | max 1280px, 32-48px inline padding | 24-32px | 16-24px |
| Section spacing | 64-80px block, no arbitrary min-height | 56-64px | 40-56px |
| Hero | two columns; copy min 400px, showcase 540-600px | stack when either minimum fails | one column, copy then showcase |
| Showcase | `4 / 3`, one restrained frame | `4 / 3` while >=480px | `1 / 1` below 480px, one centered card |
| Cards | one elevation level, radius <=12px | same | same; no nested cards |

No section uses viewport height merely to create space. Content determines height. After
implementation, screenshots at 1440x900, 768x1024, and 360x800 must show the next meaningful section
cue without unexplained blank bands.

### 10.2 Announcement And Header

- Announcement is fixed above the header only when configured and not dismissed. Expanded target
  height is 47-48px; compact may wrap to at most two lines and must reserve measured height.
- Dismiss button is at least 44x44px, has an accessible label, visible focus, and does not overlap
  campaign text/link.
- Dismissal stores only `{campaignRevision, dismissed: true}` in necessary first-party storage. A new
  revision makes the new notice visible. No consent or identity field is stored.
- Header is transparent at page top and uses a readable light-first treatment over the hero canvas.
  At 24px document scroll, it becomes a sticky/fixed translucent surface with backdrop blur,
  one-pixel border, and restrained shadow. Use a deterministic threshold, not continuous scroll
  animation.
- Announcement height and visibility feed one CSS custom property used by header offset, skip target,
  and main padding. Dismissal causes no overlap or stale gap.
- Expanded logo target is 64-72px visual height within an 80-88px header. Compact logo target is
  40-48px within a 60-64px header. Preserve approved proportions and clear space.
- Existing route links, Login/Register readiness, locale, theme, skip link, and compact navigation
  behavior remain. Controls must not visually outweigh the logo and primary action.

### 10.3 Typography And Color

- Use the existing Noto-led stack and locale-specific Noto script. No new font or remote font source.
- Hero H1 uses the existing public display role: 48px expanded, 40px intermediate, 36px compact,
  each via breakpoints rather than viewport-scaled font size; line height 1.1-1.2; letter spacing 0.
- Standard body remains at least 16px; no visible text below 12px; Urdu line height >=2.0.
- Components consume semantic tokens only. No new hardcoded component colors.
- Blue means active/scope; green confirmed/healthy; orange attention/pending; navy/light neutrals
  carry surfaces/text; neutral means inactive. Override red remains exclusive to Emergency Stop.
- Page is light-first in both composition and visual weight. Dark theme remains complete but does not
  turn every section into one navy band.

### 10.4 Functional Editorial Explanation

The hero visual is functional explanatory UI, not decorative imagery. Build it from existing React,
CSS, approved icon components, and repository-owned approved assets. Do not hand-draw decorative SVG,
add stock/photographic assets, or load remote media. It must:

- use domain shapes/icons and content to distinguish Agriculture from Digital Marketing;
- allocate approximately 55% of the viewport to the domain scene and 45% to inspectable interface
  information at expanded width;
- expose useful text alternatives without duplicating every visible label;
- declare stable dimensions before hydration;
- preserve CSP and add zero remote origins;
- keep the complete page within WC-078 payload and Core Web Vitals limits.

If the existing icon library lacks required domain icons, stop for a dependency/asset decision.
Do not add a package or invent an unreviewed asset.

### 10.5 Professional Cards, Trust, CTA, DNA, Footer, Consent

- Professional cards remain repository-catalogue projections. Show role, domain, one approved
  outcome statement, publication/availability label, scope-or-limits path, and one action.
- Green check/available treatment appears only for catalogue state whose approval reference supports
  it. Prepared/unavailable uses neutral text and disabled/unavailable semantics, not green.
- Hero and final CTA use the same hierarchy. Catalogue cards use one local next action and do not
  create a third competing primary style.
- Trust/control content is consolidated into distinct proof: review work, approve important work,
  pause/stop, honest limits, and data isolation. Do not repeat the setup stages.
- Cookie preferences are reachable from the consent banner and a normal footer control. Remove the
  persistent floating text pill; no cookie control may cover page content or another fixed control.
- Platform DNA has a theme-owned surface/text pair. Yashus, DLAISD, and WAOOAW assets, names, roles,
  and links remain visible at 4.5:1 text contrast and 3:1 non-text contrast where applicable.
- Footer preserves all existing legal, support, company, locale, and theme behavior.

## 11. Responsive, Accessibility, And RTL Contract

Required viewport/state matrix:

| Dimension | Values |
|---|---|
| Viewport | 360x800, 768x1024, 1440x900 |
| Zoom/reflow | default and 200% |
| Direction | English LTR, Urdu RTL |
| Theme | light, dark, system resolution |
| Motion | normal, reduced |
| Announcement | visible, dismissed |
| Consent | undecided/banner, preferences open, closed |
| Hero | both professionals, each rail stage, shared settled state |
| Content | longest approved labels and representative Indic-script expansion |

Pass conditions:

- `scrollWidth <= clientWidth`; no clipped text/control, overlap, hidden focus, or inaccessible action.
- Touch targets are at least 44x44px; focus contrast is at least 3:1; text and non-text contrast meet
  WCAG 2.1 AA.
- Skip link lands below fixed chrome. Dialog/sheet focus remains governed by existing behavior.
- RTL uses logical properties. Header/menu, directional icons, rail meaning, card travel, and
  previous/next controls mirror without reversing semantic stage order in source.
- Urdu uses Noto Nastaliq Urdu and line height >=2.0; no manual font-size reduction.
- At 200% zoom, the hero stacks, selector and rail wrap or scroll internally without page overflow,
  and sticky/fixed controls do not cover content.
- Axe reports zero critical and no unreviewed serious violations. Automated pass does not substitute
  for keyboard, zoom, contrast, or screenshot review.

## 12. Localization Contract

English remains source truth and all existing locale IDs remain. INST-010 implements schema,
rendering, and deterministic validation; it does not invent translations.

Required inputs per locale:

```text
locale_id
source_catalog_hash
translator_or_approved_method
reviewer
review_status
reviewed_at
glossary_version
```

Rules:

- An existing locale remains selectable only when every new required key has a genuine reviewed
  translation and the review ledger says `APPROVED`.
- Missing, English-identical where not a proper noun, placeholder, or unreviewed generated strings
  fail qualification. Approved brand names and proper nouns are allowlisted explicitly.
- An incomplete locale is hidden or marked unavailable according to existing route policy; it is not
  silently filled with English under another locale.
- Full linguistic and visual review is mandatory for English and Urdu. At least one Devanagari and
  one Dravidian-script locale join the screenshot sample; deterministic key/fallback/expansion checks
  cover all eleven.
- Legal meaning, policy version, effective date, support address, and company identity are unchanged.
- Runtime translation, live LLM translation, and test-time generated translation are prohibited.

## 13. Dependency, Performance, Privacy, And Failure Decision

### 13.1 Dependency Decision

`NO_NEW_RUNTIME_DEPENDENCY` is selected. Existing React, Next.js, CSS, and approved icon tooling are
sufficient. Lottie references remain motion inspiration only. This avoids licensing uncertainty,
client payload growth, CSP expansion, hydration complexity, reduced-motion gaps, and maintenance
surface.

### 13.2 Performance Budgets

- Initial JavaScript remains <=125KB gzip; the remediation's preferred incremental JS target is
  <=8KB gzip and must not force the total ceiling.
- Public compressed payload remains <=200KB.
- FCP <=1.5s, LCP <=2.5s, CLS <=0.10, INP <=200ms under the existing approved profile.
- Reserve announcement, header, hero, selector, cards, rail, and font dimensions before hydration.
- Do not preload inactive illustration media or all locale font subsets.
- Use CSS transforms/opacity only for moving cards; no layout-property animation.

### 13.3 Privacy And Failure

- Hero content is illustrative and contains no real customer/business data.
- Hero selection is not a new acquisition event. Do not extend the event union under this plan.
- No story state enters URL, storage, telemetry, service worker, cookie, or server request.
- Announcement dismissal contains no identity and is necessary presentation state only.
- Motion initialization failure shows complete static content.
- Claim/config validation fails closed before release; it never substitutes unapproved text.
- Existing consent, DNT/GPC, protected-route, cache, and marketing-suppression tests remain mandatory.

## 14. Open-Decision Closure Record

| ID | Recommendation | Accepting authority | State before plan acceptance |
|---|---|---|---|
| OD-01 | Role-name selector plus plain business-context label | Founder/content owner | PROPOSED |
| OD-02 | Plural final sentence in Section 8 | Founder/claim owner | PROPOSED |
| OD-03 | Illustrative growing dental clinic in Pune | Founder/content owner | PROPOSED |
| OD-04 | Preserve existing destinations and named CTA hierarchy | Founder/product owner | PROPOSED |
| OD-05 | Revision-scoped announcement dismissal | Founder/product/privacy owner | PROPOSED |
| OD-06 | `4 / 3` >=480px, `1 / 1` below | Founder visual acceptance | PROPOSED |
| OD-07 | No new dependency; React/CSS/icons | Solution Architecture; Founder accepts plan | RECOMMENDED |
| OD-08 | Required non-secret approval references; fail closed | Founder/claim owner | BLOCKING |

Founder acceptance of this plan may close OD-01 through OD-07. OD-08 closes only when the actual
accepted claim record identifiers are supplied; plan acceptance alone is not claim evidence.

## 15. Token And Time Optimization Protocol

This protocol applies to INST-005 planning maintenance and INST-010 implementation. It reduces model
and CI cost without reducing evidence.

### 15.1 Compact Context Envelope

At each Work Component, load only:

1. `.github/agent-context/office-platform-it-expert.md`;
2. Skill 16 section of `platform-it-expert-agent.md`;
3. this plan's global Sections 2 through 5 plus the selected Work Component;
4. the exact touched source files and nearest tests named by that component;
5. one owning contract section only when the task references it;
6. the latest focused failure output, if any.

Do not re-read full WC-078, full agent specification, all ADRs, all UX references, unrelated routes,
or prior terminal logs during every task. Use `rg` for exact symbols/acceptance IDs and language-server
usages before opening files. Keep a compact task ledger of verified facts, changed files, focused
command, result, and unresolved blocker; reuse it instead of rediscovering context.

### 15.2 Deterministic-First Execution

- Form one falsifiable local hypothesis and specify one deferred Docker check before each first edit.
- Prefer existing component patterns, typed schemas, tests, CSS tokens, and icon library.
- Use deterministic tools for search, formatting, schema checks, translation completeness, contrast,
  screenshots, diffing, hashing, build, coverage, scanning, and evidence assembly.
- No LLM call occurs in runtime, tests, screenshots, translation, metadata, or evidence generation.
- No review subagent or broad repository exploration is used unless the Founder explicitly asks.
- Use a higher-reasoning model only for WC-03 state-machine/RTL defects or a contract ambiguity;
  mechanical copy/token/test updates use the least-cost capable model.
- Batch independent reads. Do not batch unrelated edits.
- During WC-01 through WC-08, use editor diagnostics, language-server references, exact-ID searches,
  and diff inspection only. These are implementation inspections, not test evidence.
- After a WC-09 deterministic failure, inspect that evidence and repair the same slice. Do not spend
  model tokens rerunning unchanged commands or reopening broad context.

### 15.3 Test Economy

- Author each component/unit/browser/accessibility/visual test with its owning story, but execute no
  Docker test, build, browser, screenshot, scanner, coverage, or qualification command during WC-00
  through WC-08.
- Mark WC-01 through WC-08 `IMPLEMENTED_PENDING_QUALIFICATION`; editor diagnostics and diff review do
  not convert that state to PASS.
- After all implementation and test code is complete, run the complete WC-09 Docker campaign once at
  finalized HEAD. It starts with the cheapest deferred component/configuration checks and stops on
  first deterministic failure before expensive browser/scanner stages.
- If WC-09 fails, capture evidence, repair only the failing slice, run that failed Docker gate once,
  then perform one new clean final campaign against the new finalized HEAD.
- Reuse exact hash-tagged web/test image IDs throughout final qualification; do not rebuild per gate.

### 15.4 Token/Cost Evidence

PR evidence records:

- Work Components completed and context envelope exceptions;
- whether any external model call occurred (`expected: none`);
- any model/provider, purpose, input/output token count, retry, and cost if separately authorized;
- focused versus full Docker command counts;
- reused image IDs and avoided duplicate qualification runs.

Token optimization never authorizes skipped tests, reduced locale coverage, bulk screenshot approval,
weakened assertions, unreviewed generated copy, or incomplete author review.

## 16. Ordered Platform IT Expert Work Components

All tasks use INST-010 Skill 16. Estimates are relative engineering effort after inputs exist; they
are not calendar or model guarantees.

WC-00 closes as `READY_TO_IMPLEMENT` after document/authority inspection. WC-01 through WC-08 close
only as `IMPLEMENTED_PENDING_QUALIFICATION`. `PASS` is available only after WC-09 executes every
deferred Docker check and the substantive screenshot gate against finalized HEAD.

### 16.1 Initial File Ownership Map

WC-00 must verify actual symbols before editing, but it starts from this bounded map supplied by the
requirements and parent WC. A missing path triggers one local search for its current equivalent; it
does not authorize a repository scan.

| Path or bounded glob | Intended disposition | Work Components |
|---|---|---|
| `web/app/(public)/page.tsx` | TOUCH - landing composition only | WC-03, WC-05 |
| `web/app/(public)/layout.tsx` | TOUCH only if public chrome composition owns the required behavior | WC-02 |
| `web/components/public/AutonomyHandoffConsole.tsx` | REPLACE internal presentation or retire after references prove unused | WC-03, WC-04 |
| `web/components/public/ProfessionalJourneyShowcase.tsx` | CREATE only if local component convention confirms this boundary/name | WC-03, WC-04 |
| `web/components/public/PublicFooter.tsx` | TOUCH presentation/cookie entry only | WC-05 |
| `web/components/shell/AppShell.tsx` | TOUCH public chrome presentation only; authenticated behavior frozen | WC-02 |
| `web/app/globals.css` | TOUCH only existing public selectors/tokens; no unrelated reformat | WC-02, WC-04, WC-05, WC-06 |
| `web/config/site.ts` | ADD remediation/claim/announcement fields only if this is the existing owner | WC-01 |
| `web/config/theme.ts` | ADD/ADAPT semantic public tokens only; existing primitives preserved | WC-02, WC-05 |
| `web/config/marketing.ts` | REGRESSION_ONLY - no behavior or destination change | WC-00, WC-07, WC-09 |
| `web/content/en.ts` and existing same-shape locale catalogs | ADD reviewed hero/journey keys; unrelated strings preserved | WC-01, WC-06 |
| `web/components/public/PublicExperience.test.tsx` | EXTEND; change old hero assertions only with supersession trace | WC-01 through WC-07 |
| `web/tests/e2e/wc078-public-acquisition.spec.ts` | EXTEND VRA matrix; preserve all PA checks | WC-02 through WC-09 |
| Existing route-specific WC-078 visual baselines | UPDATE one named state at a time with review reason | WC-07, WC-08 |
| `scripts/wc078_qualify.sh` | ADDITIVE evidence orchestration only if VRA fields are not already supported | WC-09 |
| `test-results/wc078/` | GENERATED/IGNORED evidence only; never post-qualification source input | WC-08, WC-09 |

`src/**`, legal sources, identity/provider code, acquisition/destination behavior, infrastructure,
deployment workflows, database files, and unrelated public routes are `PROHIBITED` under this plan.

### 16.2 Engineering Implementation Rules

- Use strict TypeScript. Do not introduce `any`, unbounded casts, ignored type errors, dynamic code
  execution, or string-built structured data.
- Prefer server components. Add `use client` only at the smallest dismissal, scroll/menu, or journey
  interaction boundary; never promote the public page or layout wholesale.
- Keep render functions pure. Derive display state from typed props and the explicit state machine;
  do not mirror props into state or create a second content source.
- Use one finite timer/schedule owner with deterministic cleanup. Do not create cascading timers,
  stale closures, unstable keys, random IDs, wall-clock-dependent snapshots, or hydration-dependent
  initial content.
- Use semantic HTML and the existing approved icon library. Every icon-only command has an accessible
  name and tooltip when its meaning is not universal.
- Use CSS logical properties, semantic tokens, stable dimensions, approved duration tokens, and
  transform/opacity motion. Do not add physical-direction hacks, raw component colors, viewport-
  scaled font sizes, negative letter spacing, nested cards, or layout-property animation.
- Preserve typed central content/configuration ownership. Do not hardcode copy, routes, approval
  references, provider state, publication state, or contact data inside visual components.
- Keep tests deterministic with fake timers/controlled media and visibility fixtures. Do not add
  arbitrary waits, network dependence, live providers, runtime LLM calls, or blanket retries.
- Treat accessibility, privacy, security, RTL, localization, PWA, payload, and performance as design
  inputs, not end-of-task cleanup.
- Add comments only when a non-obvious state-machine invariant cannot be expressed by types or names.
- Keep commits and diffs scoped to one completed Work Component; no unrelated refactor or formatting
  churn.

### WC-00 - Gate, Baseline, And Preservation Ledger

**Entry:** Section 3 gates except the baseline result itself; no source edit.

**Inputs:** This plan; accepted amendment/claim/content/translation records; current branch; existing
WC-078 Docker qualification command and tests.

**Actions:**

1. Record accepted IDs for plan, normative deltas, claims, content, translations, and session authority.
2. Map current files to `TOUCH`, `REGRESSION_ONLY`, and `PROHIBITED`.
3. Record the merged WC-078 qualification artifact/commit as the accepted baseline without rerunning it.
4. Record known pre-existing findings without repairing unrelated behavior.
5. Confirm no new dependency, component, endpoint, event, storage, or environment action.

**Outputs:** Gate record; preservation ledger; prior-baseline reference; exact task file list.

**Deferred Docker falsifying check (WC-09):** Docker Compose config plus existing WC-078 public
component test executes first in the final campaign.

**Completion:** Authority and document inspection completes as `READY_TO_IMPLEMENT`; no Docker command
or source change occurs.

**Acceptance:** VRA-17; PA-ACC-01 through PA-ACC-19 baseline recorded.

**Model hint / estimate:** least-cost capable / XS.

**Stop:** Any missing gate, unexplained baseline failure, dirty conflicting file, or broader change need.

### WC-01 - Typed Content And Claim Validation

**Entry:** WC-00 `READY_TO_IMPLEMENT`; accepted English strings, selector/CTA decisions, claim references, and
translation ledger supplied.

**Touch surfaces:** Existing public content catalogs, site/theme content types and validators, and
their nearest configuration/content tests only.

**Actions:**

1. Add the two story models, six semantic stages, four rail labels, hero copy, final message, and
   accessibility description through the existing locale schema.
2. Add remediation enablement and non-secret claim approval-reference validation through the
   existing typed configuration pattern.
3. Add negative fixtures for missing claims, stage, rail mapping, translation, and duplicate IDs.
4. Do not alter marketing configuration, event vocabulary, legal content, route availability, or
   professional publication authority.

**Deferred Docker falsifying check (WC-09):** Remediation enabled with a missing claim reference must
fail validation.

**Completion:** Implementation and deterministic tests are authored, editor diagnostics are clean,
and the task is `IMPLEMENTED_PENDING_QUALIFICATION`.

**Acceptance:** VRA-02, VRA-04, VRA-13, VRA-17, VRA-19; PA-ACC-04/05/17.

**Model hint / estimate:** least-cost capable / S.

**Rollback:** Remove additive schema keys/content only; current remediation-disabled config remains valid.

**Stop:** Claim references, source copy, translation review, or existing schema ownership is missing.

### WC-02 - Historical Shell Fidelity

**Entry:** WC-01 `IMPLEMENTED_PENDING_QUALIFICATION`; announcement decision accepted.

**Touch surfaces:** Existing public layout/shell, announcement/header components, logo projection,
public style tokens, and their nearest component/browser tests.

**Actions:**

1. Implement revision-scoped announcement dismissal without changing consent state.
2. Implement transparent-at-top and floating-at-24px header states with one offset variable.
3. Restore approved expanded/compact logo prominence and balanced controls.
4. Preserve navigation routes, provider readiness, theme/locale controls, skip link, and compact nav.
5. Add top/scrolled, announcement visible/dismissed, keyboard, 360px, RTL, and 200% zoom checks.

**Deferred Docker falsifying check (WC-09):** Component test proves dismissal changes the shared
chrome offset while preserving focus and storing no value beyond campaign revision/dismissed state.

**Completion:** Implementation and VRA-06 tests are authored, preserved route/identity/consent
assertions remain intact, editor diagnostics are clean, and status is
`IMPLEMENTED_PENDING_QUALIFICATION`.

**Acceptance:** VRA-01, VRA-06, VRA-08, VRA-16/17; PA-ACC-01/04/05/09/16.

**Model hint / estimate:** standard / M.

**Rollback:** Revert only shell presentation and additive announcement state; preserve current routes.

**Stop:** Header change requires identity, navigation ownership, consent semantics, or a new dependency.

### WC-03 - Semantic Journey And Static Fallback

**Entry:** WC-01 `IMPLEMENTED_PENDING_QUALIFICATION`; WC-02 may proceed independently; story content complete.

**Touch surfaces:** Public home composition, replacement showcase component(s), existing hero test,
and server-render/no-JavaScript assertions.

**Actions:**

1. Replace the old console internally with the Section 7 component boundary.
2. Render fixed hero copy, ranked existing CTAs, selectors, all semantic story content, rail, and
   static settled meaning from typed inputs.
3. Remove only the duplicate getting-started rendering; preserve all other section families.
4. Implement complete static/reduced-motion/failure presentation before autoplay.
5. Keep the page server-owned and the client boundary limited to the showcase.

**Deferred Docker falsifying check (WC-09):** Component test disables motion/JavaScript assumptions
and asserts both professional names, six-stage meaning, CTAs, and final message remain available.

**Completion:** Semantic order, heading, SSR, CTA, disposition, and reduced-motion tests are authored;
editor diagnostics are clean; status is `IMPLEMENTED_PENDING_QUALIFICATION`.

**Acceptance:** VRA-02 through VRA-05, VRA-09, VRA-12, VRA-16/17; PA-ACC-01/02/03 superseded/04/16.

**Model hint / estimate:** reasoning for state/semantic boundary / M.

**Rollback:** Restore old hero console and getting-started rendering behind remediation disablement.

**Stop:** Implementation needs a route/API, client fetch, global state, or unapproved copy.

### WC-04 - Finite Motion And Journey Controls

**Entry:** WC-03 `IMPLEMENTED_PENDING_QUALIFICATION`; approved transition tokens and no-new-dependency decision confirmed.

**Touch surfaces:** Showcase client island, its styles, timer/interaction tests, and focused hero
Playwright scenarios.

**Actions:**

1. Implement the Section 9 deterministic schedule and one-run viewport entry behavior.
2. Implement professional selector and four rail controls with manual cancellation.
3. Implement centered active card, quiet prior card, next-card peek above 480px, and compact single card.
4. Implement RTL logical direction, visibility pause, cleanup, reduced motion, and initialization fallback.
5. Assert no focus movement, live narration, CLS, infinite timer, or prohibited motion.

**Deferred Docker falsifying check (WC-09):** Fake-timer component test starts autoplay, selects a
rail stage, advances time, and proves the selected state does not change.

**Completion:** Timer, keyboard, reduced-motion, and viewport browser tests are authored; editor
diagnostics are clean; status is `IMPLEMENTED_PENDING_QUALIFICATION`.

**Acceptance:** VRA-03 through VRA-05, VRA-16/18; PA-ACC-03 superseded/05/15/16.

**Model hint / estimate:** reasoning / L.

**Rollback:** Disable remediation to restore accepted static/current hero; no data migration.

**Stop:** Timer behavior cannot be deterministic, payload exceeds budget, or icon/package gap appears.

### WC-05 - Visual System And Defect Remediation

**Entry:** WC-02 and WC-04 `IMPLEMENTED_PENDING_QUALIFICATION`; current catalogue publication fixtures available.

**Touch surfaces:** Public home server sections, professional preview, trust/control, final CTA,
Platform DNA, footer, cookie-preference entry, public styles, and nearest tests.

**Actions:**

1. Apply Section 10 density, typography, palette, illustration, and card rules.
2. Consolidate repeated copy without removing safeguards or changing legal meaning.
3. Repair truthful availability icon/label/CTA projection from existing publication state.
4. Remove persistent floating cookie text pill; retain banner and footer preferences access.
5. Repair Platform DNA theme pair and preserve all approved attributions/assets.
6. Preserve all section destinations, metadata content, event triggers, and consent behavior.

**Deferred Docker falsifying check (WC-09):** Theme component test renders Platform DNA in light/dark
and fails if any required name/role/link falls below contrast or disappears.

**Completion:** VR-01/02/04 through VR-10 tests and screenshot specifications are authored without
modifying preserved contract assertions; editor diagnostics are clean; status is
`IMPLEMENTED_PENDING_QUALIFICATION`.

**Acceptance:** VRA-01, VRA-07 through VRA-12, VRA-16/17; PA-ACC-02/04/05/08 through 16.

**Model hint / estimate:** standard / L.

**Rollback:** Revert presentation by bounded region; no catalogue/config authority changes.

**Stop:** Truthful card state cannot be derived from existing publication record or content
consolidation would remove an approved family.

### WC-06 - Genuine Localization And RTL

**Entry:** WC-01 content schema stable; approved review ledger and translations supplied.

**Touch surfaces:** Existing eleven locale catalogs, deterministic locale validator, localized public
component tests, and focused locale screenshots only.

**Actions:**

1. Add only reviewed new strings; retain existing unrelated translations.
2. Enforce review-ledger, fallback, identical-English allowlist, missing-key, and expansion checks.
3. Verify Urdu direction/font/line-height and showcase rail/card semantics.
4. Verify one Devanagari and one Dravidian sample in addition to English/Urdu visual review.
5. Hide/disable incomplete locale according to existing route policy; never synthesize translation.

**Deferred Docker falsifying check (WC-09):** Locale validator receives one English fallback under a
non-English locale and must fail with locale/key identification.

**Completion:** Deterministic tests cover all eleven and required linguistic sign-offs are present;
English/Urdu/Indic screenshot cases are authored; editor diagnostics are clean; status is
`IMPLEMENTED_PENDING_QUALIFICATION`.

**Acceptance:** VRA-03/06/13 through 16; PA-ACC-05/16/17.

**Model hint / estimate:** least-cost capable; no translation generation / M after translations exist.

**Rollback:** Revert only new keys/review ledger; never overwrite accepted prior catalog content.

**Stop:** Any required translation or qualified review is absent.

### WC-07 - Focused Regression And Acceptance Expansion

**Entry:** WC-02 through WC-06 `IMPLEMENTED_PENDING_QUALIFICATION`.

**Touch surfaces:** Existing WC-078 public component and E2E suites, route-specific visual baselines,
and acceptance/evidence schema required for VRA results.

**Actions:**

1. Add VRA-01 through VRA-20 traceability without duplicating existing PA-ACC coverage.
2. Preserve route, SEO, identity, consent, acquisition, privacy, CSP, PWA, and marketing tests.
3. Add viewport/theme/locale/motion/announcement/consent/story/Platform-DNA/footer screenshot states.
4. Add 200% zoom, fixed-element collision, keyboard, focus, contrast, and payload assertions.
5. Store baselines route/state-specifically with reviewer-readable names and reasons.

**Deferred Docker falsifying check (WC-09):** Compact English-light Playwright case with announcement
and consent visible must detect a seeded fixed-control overlap or equivalent active fixture proving
collision checks work.

**Completion:** Changed component/browser tests and acceptance traceability are authored, all
preserved WC-078 tests remain present, editor diagnostics are clean, and status is
`IMPLEMENTED_PENDING_QUALIFICATION`. No test has run yet.

**Acceptance:** VRA-01 through VRA-20; PA-ACC-01 through PA-ACC-19.

**Model hint / estimate:** standard / L.

**Rollback:** Remove only new VRA cases/baselines when paired feature is rolled back; preserve all
existing tests.

**Stop:** A baseline is being updated without an explained visible requirement or a preserved test
would need weakening.

### WC-08 - Screenshot Matrix And Review Preparation

**Entry:** WC-07 `IMPLEMENTED_PENDING_QUALIFICATION`; candidate implementation and tests complete.

**Touch surfaces:** Screenshot project configuration, deterministic artifact index schema, review
checklist/ledger, and route-state baseline declarations only.

**Actions:**

1. Declare every Section 11 screenshot case without generating it.
2. Define the contact sheet/index grouping by viewport, theme, locale, announcement, consent, story,
   DNA, and footer state.
3. Define the author/Founder review checklist for clipping, density, hierarchy, brand fidelity,
   truthfulness, control collision, script quality, and professional polish.
4. Define required `ACCEPT`, `REJECT`, and finding fields per route/state.
5. Defer screenshot generation and all substantive review to WC-09 after the final Docker image exists.

**Deferred Docker falsifying check (WC-09):** Artifact index validation fails when a required state or
reviewer verdict is absent.

**Completion:** Matrix, index schema, and review checklist are authored; editor diagnostics are clean;
status is `IMPLEMENTED_PENDING_QUALIFICATION`. No screenshot has been generated or accepted.

**Acceptance:** VRA-01/03/06 through 16; VRA-15 is the controlling gate.

**Model hint / estimate:** no model for image review synthesis; human review / M.

**Rollback:** Remove only unaccepted additive matrix/index declarations with their paired feature.

**Stop:** Founder/human visual acceptance is unavailable or any screenshot is approved solely by diff.

### WC-09 - Final Docker Qualification And PR Evidence

**Entry:** WC-01 through WC-08 are `IMPLEMENTED_PENDING_QUALIFICATION`; intended commits finalized;
working tree contains no uncommitted source/config change; final HEAD fixed.

**Touch surfaces:** Existing WC-078 qualification orchestrator/evidence schema only where additive VRA
fields are required; PR body. No application edit after qualification starts.

**Actions:**

1. Run Docker preflight and calculate WC-078 source/config hashes.
2. Build final hash-tagged web/test images once.
3. Run every deferred WC-00 through WC-08 component/configuration test first; stop on failure.
4. Run coverage, production artifact inspection, full browser matrix, axe, screenshots, privacy, PWA,
  SEO, consent/marketing, performance, SBOM, Trivy, Gitleaks, and repository gates.
5. Generate the screenshot contact sheet/index and obtain named substantive human/Founder review;
  `ACCEPT` is mandatory and pixel comparison alone is insufficient.
6. Extend qualification evidence with VRA matrix, screenshot artifact hash/index, substantive reviewer
   identity/verdict, translation ledger hash, claims refs, token-cost record, and preserved-test counts.
7. Perform complete diff and evidence author review.
8. Prepare exact PR body and run C-059/C-065 validators through the repository-approved Docker/tool
   boundary before push.
9. Push once and submit unmerged PR for Founder review; do not approve or merge.

**First falsifying check:** Existing WC-078 focused qualification guard in the final tagged test image.

**Completion:** One clean qualification reports PASS and binds source, config, images, tests, scans,
screenshots, substantive review, claims, translations, author review, and PR metadata to one full HEAD.

**Acceptance:** VRA-01 through VRA-20; PA-ACC-01 through PA-ACC-19.

**Model hint / estimate:** deterministic commands and least-cost evidence summary / M plus Docker runtime.

**Rollback:** Preserve prior accepted image digest/config; remediation switch restores current WC-078.

**Stop:** Any source/config/tool change after qualification, stale evidence, scan/test failure, or
request to self-approve/merge/deploy.

## 17. Docker-Only Execution Plan

Host shell and git may orchestrate. Host Node, npm, pnpm, Python, pip, pytest, Playwright, browser
runner, scanner, formatter, linter, build, or test execution is prohibited.

No Docker test, build, browser, screenshot, coverage, scanner, or qualification command runs during
WC-00 through WC-08. All executable validation occurs after implementation in WC-09. This deliberate
cadence avoids repeated image startup/build overhead; it does not remove, reduce, or waive any test.

### 17.1 End-Of-Implementation Preflight

Run only when WC-01 through WC-08 are `IMPLEMENTED_PENDING_QUALIFICATION` and intended source/test
commits are finalized:

```sh
docker version
docker compose version
docker system df
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}'
docker compose config --quiet
```

If capacity is low, capture `docker system df -v`. Only `docker image prune --force` and
`docker builder prune --force --filter 'until=24h'` are allowed after verifying artifacts are
disposable. Never run system/volume/container prune or delete a running, database, evidence, pinned,
or user-named resource.

### 17.2 Deferred Focused Gates

Within WC-09, use the repository's pinned TypeScript test container and existing package scripts for
the deferred checks authored by WC-01 through WC-08. Run them from cheapest to most expensive and
stop on first deterministic failure. Exact selectors must be recorded in WC-00; equivalent shape:

```sh
docker compose run --rm test-runner-ts npm test -- --runInBand <focused-test-file-or-pattern>
docker compose run --rm test-runner-ts npx playwright test <focused-spec> --project=<one-project>
```

Do not copy these examples blindly if the accepted Compose service or package script differs. WC-00
records the exact existing command for later WC-09 execution. Do not install a package on host or
mutate lockfiles to make a command convenient.

### 17.3 Final Qualification

Extend and run the existing WC-078 command once against finalized HEAD:

```sh
./scripts/wc078_qualify.sh --output test-results/wc078/wc078-qualification.json
```

The host script may use POSIX shell, git, Docker/Compose, and `jq` only for orchestration. Language
runtimes, package managers, builds, tests, browsers, SBOM, Trivy, and Gitleaks run in pinned images.
Use one built image identity for all gates. A changed source/config/lock/tool input requires a new hash,
new images, focused repair, and one new clean final campaign.

On failure, capture Compose state, timestamped changed-service logs, container inspection, image ID,
and Docker capacity before cleanup. Retry unchanged code once only for proven infrastructure failure.
Never retry a deterministic assertion, build, lint, security, accessibility, visual, or contract failure.

## 18. Evidence Contract

The existing `wc078-qualification.json` remains authoritative and gains an additive
`visual_remediation` object equivalent to:

```json
{
  "plan": "wc-078-visual-experience-implementation-plan",
  "plan_acceptance_ref": "accepted-record-id",
  "claim_approval_refs": ["ten-minute-ref", "continuous-availability-ref"],
  "preserved_pa_acceptance": {"passed": 19, "changed_assertions": []},
  "vra": {"passed": 20, "failed": 0},
  "localization_review_ledger_sha256": "sha256:...",
  "screenshots": {"index": "artifact-path", "sha256": "sha256:...", "count": 0},
  "substantive_review": {
    "reviewer": "named-reviewer",
    "reviewed_head": "40-character-sha",
    "result": "ACCEPT",
    "findings": []
  },
  "token_cost": {
    "runtime_or_test_llm_calls": 0,
    "authorized_development_model_calls": [],
    "focused_docker_runs": 0,
    "full_qualification_runs": 1
  }
}
```

Actual counts replace placeholders. Evidence records exact commands, versions, exit codes, browser
projects, viewport/locale/theme/state matrix, coverage, performance, image IDs/digests, artifact paths
and hashes, timestamps, and final HEAD. It contains no secret, cookie, token, customer data, raw query
URL, or scanner credential. Generated evidence is retained in the ignored/artifact boundary and is
not committed after qualification because that would invalidate HEAD binding.

## 19. Acceptance Traceability

| Requirement | Owning Work Components | Executable or review proof |
|---|---|---|
| VRA-01 historical fidelity | WC-02, WC-05, WC-08 | shell/component checks plus accepted screenshot ledger |
| VRA-02 hero and no duplicate steps | WC-01, WC-03 | SSR component/content/disposition test |
| VRA-03 responsive frame | WC-04, WC-06, WC-07 | 360/768/1440 plus zoom screenshots/overflow assertions |
| VRA-04 both journeys and settle | WC-01, WC-04 | fake-timer state test plus browser sequence |
| VRA-05 reduced motion | WC-03, WC-04 | media-emulation component/browser test |
| VRA-06 announcement/header | WC-02, WC-07 | visible/dismissed, top/scrolled, keyboard/zoom matrix |
| VRA-07 Platform DNA | WC-05, WC-08 | contrast assertion plus light/dark screenshots |
| VRA-08 density | WC-05, WC-08 | viewport screenshots and section-gap assertions |
| VRA-09 CTA truth/hierarchy | WC-01, WC-03, WC-05 | destination/publication fixture and visual review |
| VRA-10 cookie collision | WC-05, WC-07 | consent states at viewport/zoom with overlap assertion |
| VRA-11 professional cards | WC-05 | catalogue-state component and visual tests |
| VRA-12 unique section purpose | WC-03, WC-05 | disposition/content ledger and rendered heading/copy assertions |
| VRA-13 genuine translations | WC-01, WC-06 | review-ledger, fallback, key, script, RTL checks |
| VRA-14 screenshot matrix | WC-07, WC-08 | hashed route/state artifact index |
| VRA-15 substantive review | WC-08, WC-09 | named reviewer ACCEPT bound to HEAD |
| VRA-16 accessibility | WC-02 through WC-07 | axe, keyboard, focus, contrast, zoom, reduced motion |
| VRA-17 WC-078 preservation | WC-00, WC-07, WC-09 | unchanged PA-ACC regression suite and diff ledger |
| VRA-18 performance/dependency | WC-04, WC-09 | no-new-dependency diff, bundle/CWV/payload gates |
| VRA-19 claim binding | WC-00, WC-01, WC-09 | negative config fixture and accepted refs in evidence |
| VRA-20 final-HEAD binding | WC-09 | qualification, artifacts, review, validators, PR use one SHA |

Every existing WC-078 acceptance outcome remains explicit:

| Existing acceptance | Disposition | Regression owner |
|---|---|---|
| PA-ACC-01 | PRESERVE - App Router remains sole runtime | WC-00, WC-03, WC-07, WC-09 |
| PA-ACC-02 | PRESERVE WITH APPROVED DISPOSITION - getting-started meaning moves into hero; every other family remains | WC-03, WC-05, WC-07, WC-09 |
| PA-ACC-03 | SUPERSEDE PRESENTATION ONLY - VRA-02 through VRA-05 replace the old console while preserving finite motion, SSR, RTL, reduced motion, and zero CLS | WC-03, WC-04, WC-07, WC-09 |
| PA-ACC-04 | PRESERVE - central typed configuration remains | WC-01, WC-07, WC-09 |
| PA-ACC-05 | PRESERVE AND STRENGTHEN - eleven-locale shape plus genuine review, Urdu, zoom, overflow | WC-01, WC-06, WC-07, WC-09 |
| PA-ACC-06 | PRESERVE - public route status, H1, metadata, canonical, alternates, links, indexing | WC-07, WC-09 |
| PA-ACC-07 | PRESERVE - sitemap, robots, social assets, structured data | WC-07, WC-09 |
| PA-ACC-08 | PRESERVE - sole public support address | WC-05, WC-07, WC-09 |
| PA-ACC-09 | PRESERVE - Keycloak and server-owned provider readiness | WC-02, WC-07, WC-09 |
| PA-ACC-10 | PRESERVE - consent, withdrawal, DNT/GPC, policy version | WC-05, WC-07, WC-09 |
| PA-ACC-11 | PRESERVE - minimized stateless event union and stable identity | WC-07, WC-09 |
| PA-ACC-12 | PRESERVE - destination environment gates and safe failure | WC-07, WC-09 |
| PA-ACC-13 | PRESERVE - advertising absent from protected/institutional surfaces | WC-07, WC-09 |
| PA-ACC-14 | PRESERVE - security headers, CSP, and no secrets/protected values | WC-07, WC-09 |
| PA-ACC-15 | PRESERVE - Core Web Vitals and payload ceilings | WC-04, WC-07, WC-09 |
| PA-ACC-16 | PRESERVE AND STRENGTHEN - axe, keyboard, focus, visual usability | WC-02 through WC-09 |
| PA-ACC-17 | PRESERVE - no runtime/test LLM; bounded separately authorized generation only | WC-00 through WC-09 |
| PA-ACC-18 | PRESERVE AND EXTEND - one Docker qualification gains VRA evidence | WC-09 |
| PA-ACC-19 | PRESERVE AND EXTEND - complete gates and final-HEAD author review | WC-09 |

PA-ACC-03 is not deleted or skipped. Only its old visual structure is superseded after Section 2
acceptance; its quality properties remain mandatory through VRA-02 through VRA-05.

## 20. Rollback And Release Boundary

- The remediation is an additive typed public-configuration revision. Before release acceptance,
  disabling it restores the current accepted WC-078 composition and copy.
- No data migration, API rollback, database rollback, identity rollback, consent migration, event
  rollback, or destination rollback is introduced.
- Build once and promote the same accepted digest only through separately authorized Demo, UAT, and
  Production gates.
- Demo proof and substantive Founder visual acceptance precede UAT. UAT, Production, indexing,
  campaign activation, provider activation, DNS, spend, and traffic remain independently authorized.
- Record the prior accepted WC-078 image digest, config revision, screenshot set, and rollback command
  before any environment action.
- Implementation completion, PR creation, Founder visual acceptance, merge, deployment, and
  Production acceptance are distinct states.

## 21. Stops

Stop rather than proceed when:

- current-session implementation authorization is absent;
- this plan, the Section 2 deltas, or required claims are not accepted;
- a translation/review record or selected content decision is absent;
- existing WC-078 baseline behavior fails or would need weakening;
- work expands beyond the public visual shell/landing scope into `src/`, APIs, persistence, identity,
  legal source, acquisition semantics, destination activation, infrastructure, or deployment;
- an implementation choice would invent availability, customer proof, claim, route, event, consent,
  authorization, lifecycle, or service behavior;
- a new dependency, icon set, asset source, remote media origin, font, framework, or state store appears;
- exact 360px, RTL, accessibility, privacy, CSP, PWA, coverage, payload, or performance gates cannot
  pass without changing architecture;
- host language/package/test/scanner tooling is requested;
- a deterministic failure is being retried, skipped, threshold-reduced, or hidden by baseline update;
- screenshot generation/pixel diff is being treated as substantive visual acceptance;
- source/config/tooling changes after final qualification or evidence no longer matches HEAD/images;
- self-approval, self-merge, direct `main` push, cloud mutation, Demo/UAT/Production action, campaign
  activation, or claim publication is requested without exact authority.

## 22. Work Package Definition Of Done

### 22.1 Plan Ready For Implementation Authorization

The plan is ready for implementation authorization only when:

- Founder accepts the plan recommendations and the exact Section 2 normative deltas;
- actual claim approval references and reviewed translations are supplied;
- WC-00 records the accepted prior WC-078 qualification baseline without rerunning it;
- all VRA-01 through VRA-20 map to bounded Work Components and evidence;
- PA-ACC-01 through PA-ACC-19 remain mandatory and traceable;
- INST-010 can implement without deciding architecture, copy, motion semantics, responsive behavior,
  localization policy, dependency, test scope, evidence, rollback, or release authority;
- no implementation or environment authority is inferred from plan acceptance.

### 22.2 Implementation Done

The work package is `DONE` only when:

- WC-01 through WC-08 implementation and deterministic tests are complete with no work outside the
  Section 16 file/scope boundary;
- WC-09 executes the first and only planned Docker campaign after implementation, and every deferred
  component, configuration, route, browser, accessibility, visual, localization, privacy, security,
  PWA, SEO, consent, marketing-suppression, performance, coverage, SBOM, Trivy, Gitleaks, and
  repository gate passes;
- all VRA-01 through VRA-20 pass and PA-ACC-01 through PA-ACC-19 remain passing, with only the
  explicitly accepted PA-ACC-03 presentation supersession;
- English and Urdu receive full linguistic/visual review, all eleven locale catalogs pass
  deterministic completeness/fallback checks, and required Indic samples pass;
- the screenshot matrix is complete and a named human/Founder gives substantive `ACCEPT`; screenshot
  generation or zero pixel diff alone is not acceptance;
- FCP, LCP, CLS, INP, public payload, initial JavaScript, WCAG, 360px, 200% zoom, reduced motion, RTL,
  and theme gates meet Sections 10 through 13;
- claim approval references, translation ledger, preserved-behavior results, image IDs, screenshots,
  scans, token/cost record, author review, and PR metadata bind to the same final 40-character HEAD;
- the PR contains only authorized public-experience source, tests, and additive qualification changes,
  is pushed once after qualification, and remains unmerged for Founder review;
- prior WC-078 image/config rollback is recorded and no Demo, UAT, Production, provider, campaign,
  DNS, spend, traffic, approval, or merge state is claimed.

## 23. Solution Architect Author Review

INST-005 reviewed this plan against the groomed requirements input, WC-078 objective, scope, runtime
boundaries, configuration, SEO, consent, acquisition, security/privacy, token controls, PA tasks,
Docker protocol, PA-ACC-01 through PA-ACC-19, Skill 16 Decision Space/workflow, ratified visual and UI
acceptance contracts, and the explicit requirement to preserve WC-078 good work.

The review verified: no new component/API/persistence/dependency; exact supersession boundaries;
preservation ledger; resolved recommendations and accepting authority; six-stage/four-rail state
mapping; server/client ownership; responsive, RTL, reduced-motion and failure behavior; genuine
translation gate; claim fail-closed behavior; end-of-implementation Docker-only qualification;
token-efficient context and test protocol; VRA and PA acceptance traceability; substantive
screenshot review; final-HEAD evidence; rollback; and constitutional stops.

**Result:** PASS AS REVIEW CANDIDATE - implementation remains blocked by Section 3.
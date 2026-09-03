# WC-078 Public Experience Visual Remediation Requirements Input

**Artifact type:** Groomed requirements input for Solution Architecture
**Requesting office:** Platform IT Expert (INST-010), Skill 16
**Target office:** Chief Solution Architect (INST-005)
**Source delivery:** WC-078 Public Acquisition Experience, merged in PR #376 as `e20539b`
**Solution plan:** `architecture/reference/ux/wc-078-visual-experience-implementation-plan.md`
**Status:** FOUNDER REQUIREMENTS CAPTURED - SOLUTION PLAN REVIEW CANDIDATE
**Implementation authority:** NOT GRANTED BY THIS ARTIFACT
**Environment authority:** NONE - no Demo, UAT, Production, provider, DNS, or traffic action
**Constitutional basis:** C-002, C-032, C-039, C-042, C-059, C-063, C-065, C-071, C-076, C-095, C-100; ADR-017

## 1. Purpose

Produce a detailed, self-sufficient Solution Architecture package and ordered Work Component plan
to remediate the WC-078 public landing experience. The plan must restore recognizable fidelity to
the Founder-approved `web/WAOOAWHome.html`, replace the repetitive hero and getting-started journey
with one polished two-professional motion story, repair observed visual defects, and make visual,
content, localization, responsive, interaction, conversion, and screenshot review real release
gates rather than incidental test outputs.

The resulting implementation handoff must allow INST-010 Skill 16 to execute without inventing
visual behavior, copy, breakpoints, animation state, component ownership, accessibility semantics,
localization policy, test cases, evidence shape, dependency choice, or acceptance thresholds.

## 2. Authority Boundary

This artifact authorizes requirements capture and Solution Architecture planning only. It does not
authorize changes to `web/`, dependencies, tests, workflows, Docker images, source specifications,
cloud resources, or deployed environments. The Solution Architect must identify every normative
contract amendment and approval required before a future implementation session.

The following are inspiration references, not code, asset, dependency, license, or architecture
authority:

- `https://lottiefiles.com/motion-template/azure-interactive-navigation-bar-8QWh0RSwTo`
  - inspiration: stable bottom navigation/progress rail and selected-stage attention;
- `https://lottiefiles.com/motion-template/upcoming-event-card-f6PtYZm2Rm`
  - inspiration: previous/active/next horizontal card movement and centered-card emphasis;
- `https://lottiefiles.com/motion-template/progress-indicator-p4OOrxefN4`
  - inspiration: final progress completion and checked state.

No Lottie runtime, template asset, copied motion, new package, canvas renderer, or external runtime
may enter the plan unless the Solution Architect supplies licensing, payload, accessibility,
security, operability, and ADR/dependency approval analysis. Prefer repository-native React, CSS,
Lucide icons, and approved assets when they can satisfy the requirements.

## 3. Controlling Inputs

| Input | Required use |
|---|---|
| `web/WAOOAWHome.html` | Founder-approved inspiration for logo, Noto-led typography, light color character, announcement bar, transparent-to-floating navigation, progressive journey cues, restrained cards, CTA treatment, Platform DNA, and footer |
| `work-contracts/WC-078-public-acquisition-experience-plan.md` | Current route, privacy, SEO, consent, performance, configuration, and acceptance boundary |
| `architecture/reference/ux/hybrid-visual-system-contract.md` | Current visual tokens, component rules, motion limits, imagery policy, and visual review gate |
| `architecture/reference/ux/hybrid-application-shell.md` | Public route/layout and server/client ownership |
| `architecture/reference/ux/hybrid-ui-acceptance-contract.md` | Browser, responsive, localization, screenshot, accessibility, and performance evidence floor |
| PR #376 and `test-results/wc078/` | Exact delivered implementation and prior qualification claims |
| Founder-supplied Demo screenshots, 2026-09-02 | Direct evidence of current visual defects at expanded desktop width |
| Current `web/app/(public)/`, `web/components/public/`, `web/components/shell/`, public configuration, locale catalogs, styles, and tests | Implementation baseline to inventory; not authority to preserve defects |

## 4. Founder-Fixed Experience Direction

### 4.1 Communication Point Of View

The landing page speaks to the business owner using second-person language: `you`, `your business`,
and `your professional`. WAOOAW is the enabling guide, not the protagonist. Primary acquisition copy
uses common business language across clinics, farms, retailers, agencies, educators, traders,
consultants, and growing companies.

Primary copy avoids internal terms such as Decision Space, authority licensing, autonomous
productivity, constitutional governance, workflow, configuration, and evidence state. Those ideas
may appear later as plain-language safeguards or proof when needed.

Preferred verbs are: tell, share, choose, agree, start, work, review, track, approve, pause, and stop.
Do not promise a business result, fabricate availability, or imply accepted customer evidence.

### 4.2 Hero Copy

Replace the current left-side hero title and description with:

> **Grow your business with WAOOAW AI professionals**
>
> **Guide the work in just ten minutes a day. Spend more time growing your business.**

The Solution Architect must treat `ten minutes a day` as a claim requiring an accepted evidence or
Founder-authorized claim record before public release. If that authority is absent, implementation
must stop rather than silently weaken, qualify, or publish the statement. The plan must name the
claim owner, evidence needed, approval gate, and safe pre-release behavior.

The left hero retains two clearly ranked actions. The primary conversion path must be unambiguous;
the secondary action must not compete through equal visual weight or generic underlined styling.

### 4.3 Hero Motion Story

Replace the current right-side `AutonomyHandoffConsole` and remove the later repetitive
`Three clear steps` section from the landing flow. One hero motion story must carry both ideas.

The motion frame uses a stable `4 / 3` landscape aspect ratio, approximately 540-600px wide when the
expanded two-column hero permits it. It is an unframed illustrated work surface or one restrained
frame, not a television bezel, nested card stack, decorative dashboard, or carousel.

The story demonstrates two examples using one WAOOAW journey:

1. Agricultural Advisor serving a 2-acre farm in Junnar, Pune with year-round water availability.
2. Digital Marketing Professional serving a broadly understandable growing local business.

Show one active story at a time. A keyboard- and touch-operable professional selector keeps the
inactive professional discoverable but visually quiet. Candidate plain-language labels are
`Farm Business` and `Growing Business`; final selector labels remain an explicit content decision.
After both examples have been introduced, the experience settles into one shared `Working 24/7`
state. It must not restart as an endless autoplay carousel.

### 4.4 Journey Stages And Content Model

| Stage | Customer meaning | Agricultural example | Digital Marketing example |
|---|---|---|---|
| Opening | A business and professional enter one simple guided journey | Farm profile enters | Business profile enters |
| Your business | Tell us about your business | Business name; farming domain; 2 acres; Junnar, Pune; year-round water; current digital presence where relevant | Business name; profession/domain; location; current website/social/digital presence |
| Your need | Tell us what you want to achieve | Improve crop productivity; choose crop; plan harvest; plan market timing | Establish or grow digital presence; increase relevant enquiries; clarify channels and campaign outcome |
| Your agreement | Set goals and agree how the professional works | Decide crop; track progress; guide fertilizer and irrigation; watch weather and market | Establish digital footprint; plan four posts each week; agree channels, review points, and sensitive approvals |
| Ready to work | Choose where your time and approval are needed | Share goals; review plan; track progress; approve material changes; receive alerts | Share goals; review campaign; track progress; approve sensitive work; receive alerts |
| Working 24/7 | The professional continues useful work and asks for attention only when needed | Weather checked; crop progress tracked; irrigation/fertilizer action prepared; market window watched | Campaign planned; content prepared; response tracked; enquiry/update ready for review |

Candidate final shared message, requiring content confirmation:

> **Your AI professionals work 24/7. You step in when needed.**

The phrase `24/7` describes continuous agent availability only where runtime and environment
evidence supports it. The Solution Architect must identify its claim/evidence gate and distinguish
availability from guaranteed outcomes or uninterrupted provider operation.

### 4.5 Motion And Navigation Behavior

The frame combines two approved inspiration ideas:

- a fixed bottom journey navigation/progress rail;
- previous, active, and next cards moving horizontally with the centered active card receiving focus.

The bottom rail exposes concise, familiar stages. The Solution Architect must test candidate labels
against compact width and genuine translations; current intent is:

`Business` -> `Goals` -> `Ways of working` -> `Working 24/7`

Required behavior:

- active stage is identifiable by text, icon, position, and state, not color alone;
- progress moves continuously toward the `10 min` transition marker;
- completed stages use a restrained checked state;
- selecting a stage navigates directly to that story state and is keyboard/touch operable;
- previous and next cards may remain partially visible only when their dimensions and labels do not
  clip at the approved viewport;
- the active card centers and gains modest emphasis through translation, opacity, and one-level
  elevation; no flip, spin, bounce, pulse, parallax, or glow;
- automatic storytelling runs once in approximately 8-12 seconds to represent, not literally wait
  for, the ten-minute customer journey;
- final `Working 24/7` state may use calm, bounded status changes but no distracting infinite travel;
- user interaction pauses automatic progression and never fights the selected state;
- semantic content exists without animation; animation failure leaves a complete usable frame;
- reduced-motion mode renders a stable final state immediately and keeps manual stage navigation;
- motion never blocks page actions, shifts hero dimensions, steals focus, or creates an ARIA live
  announcement stream.

### 4.6 Illustration And Color Direction

No photography, stock imagery, human portrait, humanoid AI avatar, robot head, circuit brain,
decorative hero carousel, atmospheric image, or generic abstract AI art is used.

Combine:

- custom editorial domain illustration;
- crisp product-interface cards showing concrete business details, goals, agreed work, alerts, and
  review/approval moments.

Agriculture and Digital Marketing do not receive competing product color systems. Distinguish them
through scene geometry, domain icons, labels, and content. Both share the WAOOAW palette:

- blue: active progress, selection, and scope;
- green: confirmed/completed/healthy state only;
- orange: attention, pending work, or alert only;
- navy and light neutrals: primary surfaces and text;
- muted neutral: inactive stages.

The approximate composition target is 55% domain illustration and 45% interface information. The
Solution Architect may adjust this only with a screenshot-supported rationale.

## 5. Historical Visual Fidelity Requirements

The redesign must be recognizably descended from `web/WAOOAWHome.html`, not merely use the same four
colors. The plan must specify and test these inherited behaviors:

1. Optional configured announcement bar at the top, dismissible and consent-neutral. Its copy,
   destination, persistence, focus, mobile truncation/wrapping, and return behavior are specified.
2. Public navigation visually merges with the page at the top. After a small scroll threshold it
   becomes a legible floating/sticky surface with approved translucency, blur, border, and shadow.
3. Dismissing the announcement moves navigation and main content without jump, overlap, hidden focus,
   or stale offset.
4. The approved stylized WAOOAW logo is prominent, proportionate, and legible. It is not reduced to
   the tiny mark seen in the current Demo.
5. Noto-led typography, light trust-focused canvas, restrained tinted accents, soft depth, and
   progressive journey cues remain recognizable.
6. Blue, green, orange, navy, and neutral tokens retain their approved semantic roles. Avoid both a
   dark-only navy stack and a one-note palette.
7. Public sections form a deliberate visual rhythm with constrained content width and useful next
   action. They do not become large empty viewport bands or isolated floating cards.
8. Platform DNA uses the approved Yashus, DLAISD, and WAOOAW assets and readable names/roles in every
   theme. No text may become invisible against a mismatched section surface.
9. Footer hierarchy, logo treatment, company identity, legal links, support route, locale, and theme
   controls are visually complete without competing with the primary conversion journey.

Pixel copying is not required. Recognizable continuity, correct behavior, and professional execution
are required.

## 6. Current Defects To Resolve

| ID | Severity | Finding | Required outcome |
|---|---|---|---|
| VR-01 | Critical | Platform DNA text/content becomes effectively invisible in dark mode against a light surface | All assets, names, roles, and links pass contrast and visual review in light, dark, and system themes |
| VR-02 | High | Excessive vertical whitespace makes Professionals, final CTA, and Platform DNA feel unfinished | Define section density, content-width, min/max spacing, and viewport-height rules; no empty band without deliberate content purpose |
| VR-03 | High | Landing page lacks a concrete visual explanation of what customers hire | Hero motion demonstrates Agriculture and Digital Marketing through editorial scenes plus inspectable work/status cards |
| VR-04 | High | `Professionals being prepared`, green confirmation icons, trial CTAs, and productivity claims conflict | One truthful availability vocabulary derives labels, icons, CTA enablement, and catalogue state from approved publication/admission data |
| VR-05 | Medium | Floating Cookie Preferences control persistently competes with content and can cover actions | Specify a non-obstructive preference entry with safe-area, compact, zoom, sticky/fixed collision, and CTA/footer rules |
| VR-06 | Medium | Governance/scope/control/evidence messages repeat without adding customer proof | Consolidate repeated content; each section must add a distinct customer question, proof, example, or action |
| VR-07 | Medium | Primary and secondary CTAs compete through inconsistent button/link treatment | Define one conversion hierarchy and progressive CTA purpose across hero, catalogue, trust proof, and final action |
| VR-08 | Medium | Header logo is too small while controls dominate | Restore prominent brand treatment and balanced navigation/action hierarchy across expanded and compact layouts |
| VR-09 | Medium | Dark navy bands and abrupt light/dark transitions make the page mechanically assembled | Define cohesive light-first art direction, bounded dark emphasis bands, and theme-complete transitions |
| VR-10 | Low | Professional cards are generic containers with weak differentiation and inspectability | Define comparable agent cards with domain identity, supported outcome, availability, scope/limits, and one clear next action |
| VR-11 | High | Prior automation proved structure but not visual quality or historical fidelity | Add approved screenshot baselines, perceptual diff thresholds, and mandatory route-by-route substantive review evidence |
| VR-12 | High | Locale tests proved key shape/font/direction but not genuine translated language | Require human- or approved-language-quality review, no English fallback disguised as translation, expansion tests, and locale-specific screenshot review |

## 7. Information Architecture And Conversion Requirements

The Solution Architect must produce a landing-page content ledger that gives every retained section
one unique purpose, target customer question, proof, primary action, and disposition. At minimum:

| Customer question | Required response |
|---|---|
| Is this for a business like mine? | Hero and two-agent story demonstrate physical and digital-service domains without implying only those domains are supported |
| What will the professional do? | Concrete domain work, outputs, monitoring, and review moments replace abstract governance repetition |
| How quickly can I begin? | Ten-minute journey claim appears only after its evidence gate; visual sequence explains the steps |
| How much time will this need from me? | Daily guidance proposition and alert/review model are stated plainly without hiding approval obligations |
| Can I trust and control the work? | Plain-language safeguards and inspectable examples appear after the value proposition, not as repeated slogans |
| Which professional should I inspect? | Comparable professional cards show truthful admitted/available state, outcome, scope/limits entry, and one next action |
| What should I do now? | One primary CTA hierarchy advances from discovery to professional detail to trial/registration without dead or misleading paths |

The plan must explicitly decide which current WC-078 sections are retained, merged, rewritten,
relocated, or removed. Removing the separate getting-started section is Founder-fixed because its
story moves into the hero. Other content families may not be silently omitted.

## 8. Responsive And Interaction Requirements

The Solution Architecture plan must define stable compositions for at least:

- expanded desktop: 1440x900;
- intermediate/tablet: 768x1024;
- compact mobile: 360x800;
- 200% text zoom/reflow;
- English LTR and Urdu RTL;
- light, dark, and system theme;
- reduced motion and motion enabled;
- announcement visible and dismissed;
- consent undecided, preferences open, and preferences closed;
- longest approved translated labels.

Expanded layout uses hero copy and `4:3` motion frame side by side only while both retain their
minimum readable width. Intermediate and compact layouts place the frame below the hero copy.
Compact mode may adapt the internal frame toward `1 / 1` only if the Solution Architect proves that
`4 / 3` cannot retain readable card and rail labels; the outer page must not horizontally scroll.

Controls must feel usable, not merely pass accessibility APIs:

- stage navigation has stable touch targets and obvious selected/complete states;
- language and theme controls use familiar icons/labels, do not dominate the brand, and fit long
  translations;
- announcement dismissal, navigation, CTA, card selection, consent, and motion controls have clear
  hover, focus, pressed, disabled, and unavailable behavior;
- sticky/fixed elements declare collision and stacking rules;
- no control covers content, footer links, another command, or browser safe areas;
- automatic motion can be paused by interaction and never resets a customer's chosen state.

## 9. Localization Quality Requirements

All eleven configured locales remain in scope only if each has genuine, complete public copy. The
plan must define:

1. English source-copy ownership and freeze procedure.
2. Translation workflow, qualified reviewer or approved quality method, glossary, and sign-off state.
3. Business-language adaptation rather than literal translation of internal platform terminology.
4. Locale completeness and English-fallback detection at build/qualification time.
5. Expansion fixtures and representative long labels for every component family.
6. Urdu Nastaliq font, `dir=rtl`, logical layout, progress direction semantics, card travel behavior,
   icon placement, and line-height.
7. Screenshot and content review for each locale, with mandatory full review for English and Urdu
   plus a justified sampling strategy for the remaining Indic scripts.
8. A release rule that hides or marks an incomplete locale unavailable rather than presenting
   untranslated English under that locale selector.

Legal source meaning, policy version, effective date, company identity, and sole public support
address remain unchanged unless their owning records authorize a change.

## 10. Solution Architect Required Outputs

The Solution Architect must produce one coherent package containing:

1. **Current-state inventory and disposition ledger**
   - map historical HTML features, current WC-078 components, defects VR-01 through VR-12, retained
     route/content families, reused assets, removed duplication, and migration destination;
2. **Revised public experience component contract**
   - component tree, server/client ownership, state boundaries, typed content/configuration inputs,
     failure behavior, no-new-component determination, and file ownership;
3. **Hero motion specification**
   - exact `4:3` composition, two-agent story state machine, timing, user navigation, pause/settle,
     reduced-motion, RTL, semantic fallback, responsive adaptation, and stable dimensions;
4. **Visual system delta**
   - historical fidelity, logo/header/announcement behavior, tokens, typography, section rhythm,
     professional cards, CTA hierarchy, consent entry, Platform DNA, footer, and light/dark rules;
5. **Content and localization contract**
   - final source strings, content schema, claim gates, translation workflow, glossary, fallback
     policy, locale evidence, and owner decisions;
6. **Acceptance contract amendment**
   - executable IDs for visual fidelity, density, hierarchy, controls, conversion, theme contrast,
     two-agent motion, responsive composition, genuine translation, and substantive screenshots;
7. **Dependency and performance decision**
   - CSS/React versus Lottie or another runtime, with license, bundle, CSP, accessibility, security,
     maintenance, failure, and rollback consequences;
8. **Ordered implementation Work Components**
   - narrow dependency-ordered tasks with owner, exact files/surfaces, prerequisites, exclusions,
     acceptance IDs, focused first check, completion check, model hint, and estimate;
9. **Qualification and evidence plan**
   - Docker commands, component tests, browser matrix, axe, screenshot baselines/diffs, contrast,
     localization, performance/bundle, CSP/privacy, author review, final-HEAD binding, and artifact
     retention;
10. **Release and rollback plan**
    - feature/config rollback, prior image digest, baseline restoration, Demo acceptance, UAT and
      Production gates, and no claim that implementation completion equals deployment acceptance;
11. **Stops and unresolved-decision ledger**
    - every architecture, claim, content, translation, asset, dependency, environment, or authority
      gap that blocks implementation.

The package must reconcile, not bypass, all current normative contracts. If a current contract must
change, the exact section, owner, amendment, review, and approval order must be named.

## 11. Architecture Conflicts The Plan Must Resolve

The agreed direction conflicts with the current WC-078 and visual-system baseline in material ways:

| Current rule | New requirement | Required architecture action |
|---|---|---|
| WC-078 prohibits a connecting track | Bottom navigation/progress rail is required | Amend motion contract before implementation and define accessible progress/navigation semantics |
| WC-078 caps the full sequence at 4.8 seconds | New representative story runs approximately 8-12 seconds | Define approved total timing while retaining only reviewed transition-duration primitives or amend those primitives |
| WC-078 prohibits cycling text and never loops | Two agent stories are introduced sequentially and settle | Define a finite state machine, one-run behavior, interaction pause, and final settled state; prohibit endless carousel behavior |
| WC-078 current structure is four vertical rows | New structure is centered moving cards in a `4:3` frame | Replace the normative structure and responsive contract before source change |
| Current asset policy is text-first and prohibits decorative hero imagery | Custom editorial illustration is required | Classify illustrations as functional explanatory UI, define allowed asset form, dimensions, ownership, CSP, accessibility, and payload |
| Current plan withholds exact time claims | Hero says `ten minutes a day` and rail marks `10 min` | Obtain accepted evidence/Founder claim authority and define blocked-state behavior before public release |
| Current motion durations allow only 150/250/400ms | Journey requires coordinated multi-stage timing | Specify how approved transition primitives compose into the total sequence or amend the visual contract |

No implementation may begin while these conflicts remain implicit.

## 12. Acceptance Requirements For The Future Plan

The Solution Architecture package is implementation-ready only when it provides measurable pass
conditions for all of the following:

| ID | Acceptance requirement |
|---|---|
| VRA-01 | Founder-approved historical fidelity ledger covers announcement, floating navigation, logo, typography, palette, hero, cards, CTA, Platform DNA, and footer |
| VRA-02 | Hero contains the fixed left copy and one two-agent motion story; the separate repetitive getting-started section is absent |
| VRA-03 | `4:3` expanded motion frame and approved compact adaptation show no clipping, overflow, layout shift, overlap, or unreadable text |
| VRA-04 | Agriculture and Digital Marketing stories traverse every defined stage, respond to bottom navigation, run once, and settle at `Working 24/7` |
| VRA-05 | Reduced-motion mode exposes the complete meaning and manual navigation without card travel or automatic cycling |
| VRA-06 | Announcement and navigation transitions pass visible/dismissed, top/scrolled, keyboard, zoom, compact, and safe-offset scenarios |
| VRA-07 | Platform DNA content and assets are visible and contrast-compliant in light, dark, and system themes |
| VRA-08 | Section-density assertions and screenshots show no unexplained empty bands at 360x800, 768x1024, and 1440x900 |
| VRA-09 | One CTA hierarchy is consistent; every visible professional/trial action is truthful, enabled only by approved state, and reaches the expected route |
| VRA-10 | Cookie preference entry never covers hero actions, cards, footer links, navigation, or another fixed control at required viewports and zoom |
| VRA-11 | Professional cards provide comparable domain, outcome, availability, scope/limits, and action information without false active-state color |
| VRA-12 | Every retained section answers a unique customer question and passes the content/disposition ledger; repeated abstract governance copy is removed |
| VRA-13 | All locale catalogs contain reviewed genuine translations; fallback detection, expansion, Indic scripts, and Urdu RTL pass |
| VRA-14 | Screenshot baselines cover expanded/compact, light/dark, English/Urdu, announcement states, consent states, motion stages, both professionals, final state, Platform DNA, and footer |
| VRA-15 | Screenshot evidence is reviewed route-by-route by a named human/Founder acceptance actor; passing pixel generation or zero-diff alone is insufficient |
| VRA-16 | WCAG, keyboard, focus, touch target, contrast, zoom, reduced motion, axe, and semantic fallback checks pass without making visual acceptance automatic |
| VRA-17 | Existing WC-078 privacy, consent, SEO, CSP, PWA, public/protected separation, and no-PII acquisition behavior do not regress |
| VRA-18 | Existing or amended payload/Core Web Vitals limits pass against the exact production build; any new dependency has accepted authority |
| VRA-19 | Ten-minute and 24/7 copy is bound to accepted claim evidence before release; absence of evidence blocks publication |
| VRA-20 | Final qualification, screenshot artifacts, substantive review verdict, author review, and PR metadata bind to the same final 40-character HEAD |

## 13. Required Work Component Shape

The future Work Component plan must be thin, ordered, and independently falsifiable. At minimum it
must separate:

1. contract/claim/dependency closure;
2. historical shell fidelity: announcement, floating navigation, logo, tokens, typography;
3. hero copy and two-agent semantic state model;
4. motion frame and interaction implementation;
5. section consolidation, professional cards, CTA hierarchy, Platform DNA, footer, consent entry;
6. genuine localization and RTL remediation;
7. focused component/accessibility/responsive tests;
8. screenshot baseline production and substantive review;
9. complete Docker qualification, final-HEAD evidence, rollback, and Founder-ready PR.

Each Work Component must state:

- owner and skill;
- authority and local entry gate;
- exact inputs and source surfaces;
- output and explicit exclusions;
- acceptance IDs;
- first focused test capable of falsifying the implementation hypothesis;
- bounded completion test;
- dependency/model decision and token/cost controls;
- estimate and rollback;
- stop conditions.

Do not package the entire visual remediation as one broad implementation task.

## 14. Explicit Open Decisions

These decisions are bounded but not fixed by the Founder discussion. The Solution Architect must
recommend one answer, state the evidence/trade-off, identify the accepting authority, and prevent
implementation from choosing implicitly:

| ID | Open decision | Fixed boundary |
|---|---|---|
| OD-01 | Professional selector labels, including whether to use `Farm Business` and `Growing Business` | Both professionals must be plainly distinguishable without separate color brands |
| OD-02 | Final shared sentence and singular/plural treatment of `Your AI professional(s) work(s) 24/7` | It must communicate continued work and customer attention only when needed; claim gate applies |
| OD-03 | Exact broadly understandable business used in the Digital Marketing story | It must not narrow the platform to one specialist segment or imply an unsupported customer result |
| OD-04 | Hero and downstream CTA labels and destinations | Exactly one primary conversion hierarchy; all availability and trial states remain truthful |
| OD-05 | Announcement campaign copy, destination, persistence duration, and rediscovery behavior | Announcement remains optional, dismissible, accessible, consent-neutral, and non-obstructive |
| OD-06 | Compact motion-frame aspect ratio | Expanded frame is `4 / 3`; compact adaptation may approach `1 / 1` only with readability evidence |
| OD-07 | Motion implementation technology | No Lottie, asset, runtime, or package is pre-approved; dependency and licensing gate applies |
| OD-08 | Evidence and approval records for `ten minutes a day`, `10 min`, and `24/7` | Claims do not publish without accepted authority; implementation must not rewrite fixed hero copy silently |

## 15. Stops

Stop planning or implementation rather than assume when:

- ten-minute or 24/7 claim evidence/authority is absent;
- historical HTML and current visual contracts conflict without an approved amendment path;
- a Lottie/template license, payload, CSP, accessibility, or dependency decision is unresolved;
- motion state, content ownership, locale quality, or responsive behavior is left for implementation
  to invent;
- a professional is shown available, active, or trial-ready without approved publication/admission
  state;
- a visual baseline is accepted only because screenshot generation or pixel comparison ran;
- Platform DNA, cookie preferences, sticky navigation, announcement, or motion frame obscures content
  in any required state;
- a locale is exposed with English fallback or unreviewed machine translation;
- the plan weakens existing privacy, consent, identity, public/protected, SEO, CSP, PWA, performance,
  or accessibility controls;
- application source, dependency, environment, deployment, Production, approval, or merge action is
  requested without its separate authority.

## 16. Definition Of Done For Solution Architecture

This requirements input is satisfied when the Solution Architect delivers a self-contained package
covering every required output in Section 10, closes or explicitly blocks every conflict in Section
11, maps every VRA acceptance ID to an ordered Work Component, and proves that INST-010 can implement
the selected scope without making an architecture, content, animation, dependency, localization,
claim, or acceptance decision.

Plan completion is not implementation authorization. Implementation completion is not Demo, UAT,
Production, claim, visual, or Founder acceptance.

## 17. Requirements Author Review

The Platform IT Expert must review this input against the Founder discussion, supplied Demo
screenshots, historical HTML/CSS, WC-078 boundaries, current visual and acceptance contracts, Skill
16 Decision Space, and every recorded defect. Any ambiguity that delegates a material design or
authority decision to implementation must be repaired before handoff.

**Result:** PASS - fixed requirements, open decisions, twelve observed defects, seven normative
conflicts, twenty measurable acceptance outcomes, required Solution Architecture outputs, Work
Component shape, authority limits, and stops are explicitly represented.
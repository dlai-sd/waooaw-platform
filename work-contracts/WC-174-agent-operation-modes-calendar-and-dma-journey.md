# WC-174 - Agent Operation: Modes, Calendar And The DMA Journey (Agent Operation Track, Milestone AO-M1) - GROOMED

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-174 |
| Office | Platform IT Expert (INST-010), with a single-pass Solution Architect review of the modes declaration, the Calendar block and the plan tree before build. The Founder is the DMA domain authority for wording and for the content rules |
| Initiative | IB-174 |
| Roadmap | [ROADMAP.md](../ROADMAP.md), section 10 "WAOOAW Agent Operation with DMA", milestone AO-M1 |
| Founder assignment | 2026-11-26: every agent has three modes (Induct, Goal Setting, Operations) with context menus of their own beside the WAOOAW menu, and a calendar as the background screen; DMA is the first candidate; "I want you to create a work contract covering full scope we are discussing". Roadmap deviation approved the same day: "Approved. add next section in roadmap called WAOOAW Agent operation with DMA and create first milestone under it" |
| Status | **GROOMED 2026-11-26 (documents only).** The build is not authorized. The Founder authorizes it in the session that starts it |
| Depends on | WC-171 merged (navigation declaration, alert policy, operations console) and WC-149 (customer account connection) merged. The Demo read-backs of WC-168 to WC-172 do not block grooming; they block the Demo proof of this contract |
| Controlling documents | [agent-experience-platform-architecture.md](../architecture/reference/agent-experience-platform-architecture.md) (kernel K1 to K9, sections 6.2, 6.4, 6.5), [digital-marketing-agent.md](../architecture/reference/agents/digital-marketing-agent.md) (Skills 0, 1, 1b, 2, 4, 8, 9, section 3.21, section 4), [GOAL-005-D06-dma-domain-authority-synthesis.md](../goals/GOAL-005-D06-dma-domain-authority-synthesis.md) (progressive context, skill-to-goal configuration), [customer-digital-presence-vision-note-2026-11-24.md](../strategy/customer-digital-presence-vision-note-2026-11-24.md) (consent first, maturity sizes the package), [WC-171](./WC-171-agent-navigation-alerts-and-oversight.md), [WC-149](./WC-149-paid-provider-consumption-and-customer-account-connection.md) |
| Requirement ledger | [WC-174-requirements.yaml](./WC-174-requirements.yaml) |
| Constitutional basis | C-001, C-005, C-007, C-023, C-048, C-049, C-058, C-059, C-061, C-063, C-065, C-088 |
| Deployment | One Environment Deployment of Demo after the build merges |

## Why This Contract Exists

WAOOAW now has the platform around an agent: hire and price, connected accounts, real work and spend, alerts and menus, billing and lifecycle. What a customer actually lives with is still missing: **a way to be known, to set goals and to watch an agent work.** Today a hired DMA opens a fixed workbench (Overview, Goals, Capabilities, Decisions, Monitor, Work, Wallet, Evidence). Nothing guides the customer through telling DMA about the business, nothing shows the year ahead, and nothing lets the customer plan content by month.

The Founder's model, restated in the platform's own terms:

1. **Three modes for every agent.** Induct (the agent learns the customer and the sources it will work from), Goal Setting (goals skill by skill, with plans on a calendar), Operations (the agent works, the customer approves, results are watched and improved). Every agent has the same three modes and fills them with its own menus and functions.
2. **A calendar as the background screen** of every agent relationship, carrying the events that matter to that customer's world.
3. **Agent menus beside the WAOOAW menu** (WC-171 gave the shell; this contract gives it modes).
4. **DMA is the first agent**; the model stays generic so Agriculture, Tutor, Trading and later agents declare their own content and reuse the same platform parts.

The milestone is **AO-M1: a synthetic customer is inducted by DMA, sets goals skill by skill, plans a month on the calendar, approves content, has it published to a connected sandbox account and sees results, on Demo, through the three modes; and a declaration-only second agent renders its own three modes through the same code.**

## Founder Decisions Recorded 2026-11-26

| Id | Decision | Founder words |
|---|---|---|
| FD1 | Consent and test, never stored passwords | "yes" (to consent-and-test instead of storing passwords) |
| FD2 | Modes are lenses with gates; the customer hops freely | "gates but customer can easily hop among them" |
| FD3 | The agent researches the calendar events from the business profile; the customer adds their own events and placeholders | "the agent from research based on customer business profile. Customer can put their own events/placeholders" |
| FD4 | One Work Contract for the full scope, a new section and first milestone in the roadmap | "create a work contract covering full scope" and "Approved. add next section in roadmap called WAOOAW Agent operation with DMA and create first milestone under it" |
| FD5 | The layout and flow take their inspiration from a planner-style workspace (grouped tool rail, a view switcher, an always-present AI button, one clear next step); the DMA conversation is visible all the time, driven by context and guiding the customer; customers are expected to spend most of their time on AI-driven outcomes | "dma agent conversation handy/visible all the time and context driven, guided dialouge. We expect maximum time customer to use AI driven outcomes." |

## What Grooming Found (verified in the repository on 2026-11-26)

| Area | Finding |
|---|---|
| Kernel fit | The kernel already has the pieces each mode needs: Induct is K1 Start, K9 Conversation and K8 consent; Goal Setting is K2 Goal and Plan and K3 Capabilities; Operations is K4 Operate, K5 Decide, K6 Monitor and K7 Evidence. Modes add no kernel primitive |
| Navigation | `agent-experience-contract.v1.schema.json` has an optional `navigation` list of up to twelve flat entries (WC-171). It has no notion of modes, readiness per mode or a home surface. The closed icon set already includes `calendar` |
| Calendar | No calendar block exists. Architecture section 6.5 says a block two agents need is promoted to a shared E2 block, and the declaration already has `plan.calendar_windows`. The web has no month view |
| DMA induction | `src/digital-marketing-agent/contracts/induction-requirements.v1.json` lists 17 requirements and `induction-summary-contract.v1.json` has the states INCOMPLETE, PARTIAL, READY. Nothing renders them to a customer. Current channels (IND-010) and read-only connected-account consent (IND-012) are **never mandatory**, which conflicts with the Founder's rule that every platform is either "not present" or connected |
| Progressive context | D06 section 4: at most one new context question per cycle, credentials and sensitive items only after trust and purpose are established, inference becomes fact only on customer confirmation. The Founder wants a focused conversation that confirms labels; these agree if the conversation stays one question at a time |
| Skill-to-goal | D06 section 5 already requires, for every skill, a goal, baseline, target or threshold, evidence source, review cadence and authority state before live execution. Goal Setting is this, made visible |
| DMA skills | The shipped manifest has `CUSTOMER_PROFILING`, `MARKET_RESEARCH_AND_MATURITY`, `CONTENT_STRATEGY_AND_CALENDAR`, `SOCIAL_CONTENT_CREATION_AND_PUBLISHING`, `VISUAL_AND_VIDEO_CONTENT` and `MARKETING_PERFORMANCE_AND_IMPROVEMENT`, in package B1 (draft only) and B2 (publish approved versions, observe connected accounts), both default off. Components `CONTENT_PLAN`, `CONTENT_DRAFT`, `CONTENT_ASSET`, `SOCIAL_PUBLICATION`, `SOCIAL_OBSERVATION` count what the customer buys |
| Theme cascade | Spec section 3.21 and Skill 2 define master theme, weekly sub-themes and platform content variants with review checks. SQL tables exist (`business.content_campaigns`, `campaign_weekly_themes`, `campaign_content_items`) but no service or screen uses them. The Founder's extra levels (individual theme, story, actors, screenplay, duration) are new |
| Creation | `VISUAL_AND_VIDEO_CONTENT` is "asset metadata only" in B1: nothing generates a picture, video or audio today. No media provider or rate exists |
| Connections | Only the Meta Page connection exists (WC-149: consent, token in the vault, test post through a broker). Instagram through Meta, the customer's own WhatsApp Business account, YouTube, LinkedIn and Google Business Profile have no connector. Meta App Review has not happened |
| Measurement | `digital_marketing/measurement.py` observes and proposes improvements only; business results (enquiries, visits, bookings) depend on customer-owned sources (IND-017) that nothing collects |
| Public data | The GST registry and open government data are named by the Founder; no lawful-use decision or connector exists |

## Objectives

| Id | Objective |
|---|---|
| O1 | Every agent relationship has three modes, declared as data, each with its own context menu and readiness, and the customer can open any of them at any time |
| O2 | A shared Calendar is the background screen; the agent proposes events from the confirmed business profile and the customer adds, edits and hides events and placeholders |
| O3 | DMA inducts the customer in a focused conversation, confirms the business as highlighted labels, and records for every platform whether it is present, not present or connected and tested |
| O4 | Goals are set skill by skill with a baseline, target, evidence source, cadence and authority state |
| O5 | Content is planned month, week, individual theme and story on the calendar, created per platform, approved by the customer and published to a connected account within the package |
| O6 | Results are read from connected and customer-owned sources against the goals and feed the next month's goals |
| O7 | Another agent proves the model generic with a declaration only and no change to shared code |
| O8 | The agent's conversation is always in view and guides the customer from the context they are in; the customer can get every outcome by asking, or by using the tools, and can hand an item over or take it back; most of a customer's time is spent on AI-driven outcomes, and that is measured |

## Authority And Scope

In scope: the `modes` declaration and its admission validation; the mode shell and context menus; the workspace layout, tool rail, view chips and tour; the docked, context-driven DMA conversation with hand over and suggestions; the shared Calendar block and event research; the Induct conversation surface over the DMA induction contract (version 1.1.0); the platform presence inventory with connection, test, repair and revoke; public-source enrichment within lawful limits; the confirmed profile and maturity report screens; skill-by-skill goal setting; the content planning hierarchy and plan tree; creation, approval and scheduled publishing for connected accounts; results and the improve loop; the share-by-route measure; alerts through the WC-171 policy; acceptance slice 6 and a declaration-only fixture agent.

Out of scope: real customers and real money (WC-172 go-live), a real second agent (WC-173, which then uses this model), Instagram, YouTube, LinkedIn and Google connectors that need outside approval until that approval exists (the screen says so honestly), the second "outside WAOOAW" measurement bucket, paid ads (`AD_BOOST`), mobile app, changing prices or package contents.

Authority limits: no password, token or secret value is typed into, shown by or stored by a screen in this contract (consent and vault only); nothing is published without the exact version being approved by the customer and a separate publication authority; Emergency Stop and revoke work from every mode; sensitive event categories and content follow C-061; the author does not merge or self-approve; any story that needs a shared-kernel change that only DMA needs stops for the Founder.

## Proposed Model (for the Founder to confirm, decisions MD1 to MD5)

| Id | Proposal | Why |
|---|---|---|
| MD1 | Three fixed mode ids in platform vocabulary: `INDUCT`, `GOALS`, `OPERATIONS`. The agent gives each a label in its own words (DMA: "Get to know my business", "Set my goals", "Run and improve") and its own entries | One shape for every agent; no agent invents a fourth mode |
| MD2 | Gates advise, they never lock the door. Each mode shows a readiness line ("14 of 17 items confirmed"); what a gate blocks is an **action with a side effect** (for example publishing), never opening a screen | FD2: the customer hops freely; D06: no unconfirmed fact drives live work |
| MD3 | The Calendar is the home surface of a relationship; the mode menu sits beside it. Themes, content and publish slots are layers on it | FD3 and the Founder's "background base screen" |
| MD4 | Calendar events have a state: `SUGGESTED` by the agent, `ACCEPTED`, `HIDDEN`, `CUSTOMER_ADDED`. Categories are declared by the agent (DMA: festival, sport, art, politics, local, religion, season). Religion and politics suggestions are shown only after the customer turns that category on; content on them is always approval-gated | FD3 with C-061; the Founder may relax the default |
| MD5 | A platform's presence status is one of `NOT_PRESENT`, `PUBLIC_ONLY`, `CONNECTED_TESTED`, `NEEDS_REPAIR`, plus `NOT_YET_CONNECTABLE` where WAOOAW has no connector or approval. Every listed platform must have an explicit answer before Induct reads READY; connecting is offered, never required | FD1 and the Founder's rule that each platform is either absent or reachable |
| MD6 | The agent's conversation is a docked panel beside the workspace in every mode and view (a bottom sheet on a phone), one durable conversation shared with WhatsApp. It knows the mode, the view, the selected item and the readiness gap, opens with the one next step, and offers buttons plus free text | FD5; one conversation across channels is already the platform rule (ADR-052) |
| MD7 | AI-first parity: every tool action can be asked for in words, and every asked-for action appears on the workspace where the customer can see, change or undo it. Both routes call the same platform commands with the same evidence | FD5; a screen changes state only through platform commands (architecture section 6.5) |
| MD8 | Every item has an author state: `AGENT_SUGGESTED` (shown as a suggestion, not applied until accepted), `CUSTOMER_EDITED`, `CUSTOMER_OWNED` (the agent leaves it alone until handed back), `APPROVED_VERSION` (locked). The customer can hand an item over or take it back at any time; undo creates a new version and never deletes | FD5; D06: nothing expands authority silently |
| MD9 | The layout follows the build order: a top bar (relationship and month, undo and redo, the mode switcher, the assistant, the package meter, help), view chips, a left tool rail grouped by purpose and changing with the mode, flyouts that appear only when a tool is chosen, a small options panel with one primary action, and a status bar | FD5 and the Founder's reference screens |

## Generic Model And What Each Agent Declares

| Platform provides (agent-neutral) | Each agent declares (data only) | DMA (first) | Other agents (illustrations) |
|---|---|---|---|
| Mode shell, readiness line, context menus, deep links | Mode labels, entries per mode, readiness source, gates | The three DMA modes above | Agriculture: farm and plot, season plan, daily advice. Tutor: student, exam plan, sessions. Trading: risk profile and broker, limits, sessions |
| Calendar block and event states | Event categories and research sources | Festivals, sport, art, politics, local, religion, season | Sowing and mandi days; exams and school terms; market holidays and expiry |
| Confirm-labels conversation and the confirmed profile | Requirement list, confirmation rules, sources | 17 DMA-IND requirements plus platform presence | Plot and crop; student and syllabus; risk and broker |
| Source inventory with connect, test, repair, revoke | Which sources exist and what each gives | Facebook, Instagram, WhatsApp, YouTube, LinkedIn, Google, website, registries | Weather and mandi feeds; school systems; broker |
| Goal per skill (D06 fields) and the plan tree | Skills, measures, hierarchy levels | Profile, Planner, Creation, Publishing, Operations | Season, month, task; term, week, session |
| Approval, scheduling, evidence, alerts, spend, stop | Approval ladder and hard limits | Customer approval per exact version | Per skill; per session; pre-authorized with limits |

## Workspace Layout And Flow

Inspired by the Founder's reference screens of a planner-style workspace: tools grouped in the order a person builds, choices that appear only when needed, one clear next step, and an always-present AI button. For DMA the conversation is not a button: it is docked and always visible.

```
[ Business · Month  ↶ ↷ ]   [ Induct | Goals | Operations ]   [ package meter ]  [ ? ]
[ view chips: Month | Week | Platforms | Storyboard ]            [ readiness line + next step ]

 Left rail (by mode)     Calendar (the workspace)            DMA conversation (docked, always on)
 ── Anchors                                                   Knows: mode, view, selected item, gap
   Event · Placeholder                                         "Next: confirm your Instagram."
 ── Plan                                                      [Do it for me] [Let me do it] [Explain]
   Theme · Weekly · Story                                      free text: "make Diwali week family-led"
 ── Content
   Post · Reel · Video → flyout: Image / Reel / Carousel / Text
 ── Publish
   Slot · Note                  Options: ☐ suggestions ☐ sensitive categories ☐ competitor events
                                [ Preview on platform ]
 Status bar: nothing selected · last edited by · posts 3 of 8 · synced / freshness
```

| Part | Rule |
|---|---|
| Top bar | Relationship and month with undo and redo on the left; the mode switcher in the centre; the package meter and help on the right. The assistant is not a button here because the conversation panel is always docked (a bottom sheet on a phone) |
| View chips | Month, Week, Platforms (one lane per platform), Storyboard: four views of one plan, always in sync, shown by a small sync pill |
| Left rail | Grouped in build order, separated by dividers, and changing with the mode. Induct: Business, Platforms, Sources, Audience, Brand. Goals: one entry per skill, then Anchors, Plan, Content, Publish. Operations: Approvals, Published, Results, Improve |
| Flyouts | Choosing a tool opens only its options (a post type: Image, Reel, Carousel, Text); nothing else is shown until a tool is chosen |
| Readiness line | Replaces a hint bar: it always names the one next step with one primary button ("Confirm profile", "Approve this story", "Publish 3 approved posts") |
| Options and preview | A small panel of toggles (suggestions, sensitive categories, competitor events) and one primary action, usually "Preview on platform" |
| Today jump | Month arrows and a Today button replace the compass |
| Tour | A short coachmark tour once in Induct (what the modes, the calendar and the conversation are), skippable and replayable from help |

### The conversation as the main way to work

| Rule | Meaning |
|---|---|
| Always on, context aware | It shows in every mode and view and knows the mode, view, selected item, readiness gap and package limits |
| Guided | It opens with the one next step, asks one new question at a time (D06), offers buttons and free text, and always allows "Do it for me", "Let me do it" and "Explain" |
| Same result either way | Asking and using a tool call the same commands; whatever the agent does appears on the workspace as a suggestion until accepted |
| Hand over and take back | The customer can say "I'll write this one myself" or "take it back and polish it"; the author state of the item changes and the agent respects it |
| Cost aware | Every reply counts against the package's conversation budget (spec section 3.16); the customer sees what is left, and a limit is explained plainly, never a silent stop |
| One conversation | The same durable conversation continues on WhatsApp, where the workspace is replaced by the next three items and a link |

### Flow in build order

| Mode | Flow, with the next step always on the readiness line |
|---|---|
| Induct | Understand, confirm labels, platforms, sources, confirm profile |
| Goals | Choose a month, master theme, weekly themes, individual themes, story, create |
| Operations | Approvals, publish, results, improve, which feeds the next month's goals |

## Canonical Requirement Index

| Id | Requirement |
|---|---|
| WC174-R001 | The Agent Experience Contract gains an additive optional `modes` field: the three fixed ids, an agent label per mode, entries per mode (reusing the navigation entry shape), a readiness source and gates for side-effect actions; admission refuses a fourth mode, markup, duplicate ids and entries that open nothing; schema, both copies, generated clients and digests change together; a declaration without `modes` still admits and shows the WC-171 menu |
| WC174-R002 | The customer can open any mode at any time; each shows a readiness line; a gate blocks only an action with a side effect and says what to do next; the chosen mode and the last surface are remembered per relationship; deep links address a mode and surface; the same three modes exist as conversation context on WhatsApp |
| WC174-R003 | Choosing an agent opens its mode menu: the fixed platform surfaces first (WC-171 R002), then the current mode's declared entries; the existing workbench views map onto Operations without lost function; old links keep working |
| WC174-R004 | A declaration-only fixture agent from another profession declares different modes, entries, event categories and hierarchy levels and renders through the same code with no agent name in shared web or Business Platform code, proved by a grep test and a render test |
| WC174-R005 | A shared Calendar block is the base screen of a relationship: month view with layers (events, themes, content, publish slots, customer notes), keyboard and screen-reader operable, a list view on narrow screens, a fallback of the next three items plus a link on WhatsApp; it carries an owner, evidence state and source freshness |
| WC174-R006 | DMA proposes calendar events from the confirmed profile (business domain, location, language, audience) with a source, relevance reason and confidence for each; the customer accepts, edits, hides or adds events and placeholders; sensitive categories follow MD4; every change is evidence; events are suggestions and never publish anything by themselves |
| WC174-R007 | Themes, content items and publish slots appear on the Calendar and the customer can move them; a move follows the approval rules of the item; the package limits (plans, drafts, assets, posts, observed accounts) are visible where the customer plans |
| WC174-R008 | The Induct conversation asks one new question per cycle in the customer's language, opens by showing what the agent already found, shows the business as highlighted labels the customer confirms or corrects, keeps inference and confirmed fact apart, resumes across web and WhatsApp, and never asks for a sensitive item before its purpose is explained (D06 section 4, C-048) |
| WC174-R009 | The DMA induction contract moves to version 1.1.0: every listed platform needs an explicit answer (present or not present) before READY; connection stays optional; the 17 requirements, the INCOMPLETE, PARTIAL and READY states and the rule that unknown, stale or conflicted is not READY are shown to the customer with the next action |
| WC174-R010 | The platform presence inventory shows each platform with its status (MD5); the customer connects by consent, the connection is tested, and it can be repaired or revoked; no password or secret is typed into or shown by WAOOAW; tokens live in the vault (WC-149 pattern); Facebook and Instagram through Meta work first; every platform without a connector or approval says "not yet connectable" and offers public-only reading |
| WC174-R011 | Public enrichment reads the website, public social pages, the Google listing and, where the Founder confirms the lawful basis, public registries (including GST) and open data; each fact carries its source, time, confidence and lawful basis; nothing is read in breach of a platform's terms; the customer can see, correct and remove what was found |
| WC174-R012 | The customer confirms the profile and sees the maturity report (Skills 0, 1 and 1b) with evidence, confidence and a correction path; confirmation moves the Goals readiness line; the score sizes a package and never excludes the customer (D06) |
| WC174-R013 | Goal Setting works skill by skill for Profile, Content Planner, Content Creation, Publishing and Operations; each skill has a versioned goal with a baseline, target or decision threshold, evidence source, review cadence and authority state (D06 section 5); a material change needs the customer's confirmation; the package limits are shown |
| WC174-R014 | The Content Planner builds a monthly master theme, weekly sub-themes, individual themes and a story for each individual theme (actors, screenplay, duration, platform), each level proposed from the calendar and the profile and approved by the customer before the next is built; the platform mix comes from the maturity report and the connected accounts |
| WC174-R015 | The plan is a generic N-level plan tree block (extending the PLAN block) used by DMA with four levels and by the fixture agent with different levels; each node has an owner, state, approval and calendar placement; the block has the standard fallback |
| WC174-R016 | Content Creation turns an approved story into text, pictures and, where a media provider is enabled, short video and audio for each subscribed platform, tuned to the platform's style with the same message; the existing review checks, brand voice, claims, rights and likeness rules (C-058) and content safety (C-061) run before the customer sees a draft; drafts and assets are counted by their components |
| WC174-R017 | The customer approves an exact version of each piece with a preview; any change after approval is a new version; approval, rejection and rework are evidence; the approval ladder starts at approval of every piece (spec Skill 2) |
| WC174-R018 | Publishing schedules approved items on the Calendar within the purchased `SOCIAL_PUBLICATION` count, through the customer's consented connection and the broker, only with a separate publication authority; on Demo only to a connected sandbox or tester account; Emergency Stop halts it; an expired or withdrawn connection becomes NEEDS_REPAIR and raises an alert through the WC-171 policy |
| WC174-R019 | Media generation providers and their rates are Founder decisions on the Pricing screen, off by default; a generation never runs, and never spends, without an authorized rate and the WC-170 spend chain; the customer sees a plain "not enabled yet" instead of a failed attempt |
| WC174-R020 | Operations shows results against each goal from connected and customer-owned sources: observed accounts, reach, enquiries, visits and bookings where a source exists; where no source exists it says "not measured" and how to connect one; every number carries its source and freshness; only work done by WAOOAW is attributed |
| WC174-R021 | The improve loop gives a monthly digest and the D06 two-month review: goal versus baseline and current, what worked and what did not, one recommendation and at most one customer request; a recommendation is a proposal and changes nothing until the customer decides; accepted changes become the next month's goal versions |
| WC174-R022 | Operations raises alerts (a goal behind pace, a connection needing repair, a publish failed, a package component nearly used) through the WC-171 policy, and the operator console shows failed publishes and connection repairs without database access |
| WC174-R023 | Package counts and prices are unchanged; every count the customer sees (plans, drafts, assets, posts, observed accounts) equals what the owner counts; activation of B1 and B2 stays a separate Founder decision; nothing in the modes bypasses a package limit |
| WC174-R024 | Every screen follows the visual system and UX vocabulary and passes the WC-167 R006 layers (Jest, Playwright at 360, 768 and 1440 in light and dark, axe, lint, strict types, production build, 90 percent changed-line coverage); labels come from the vocabulary keys so a regional language can be added without code change |
| WC174-R025 | Acceptance slice 6 runs on Demo for a synthetic customer, working mainly through the docked conversation: induct (labels confirmed, each platform answered, one tester account connected and tested), maturity report, goals for the five skills, a month planned on the calendar with a customer event, one agent suggestion accepted and one item taken over by the customer, one story approved, one post published to the tester account, results read, a monthly digest; plus the fixture agent's three modes; one calibration report whose every NOT-WITNESSED or FAIL item has an owner |
| WC174-R026 | Close-out: after the Demo deployment the ledger rows are set from their read-backs, the `ROADMAP.md` progress record is refreshed, README, SPRINT-REGISTRY and PROJECT_STATE are refreshed by the state refresh |
| WC174-R027 | The workspace follows the layout of MD9: top bar, view chips, a left tool rail grouped in build order that changes with the mode, flyouts shown only when a tool is chosen, an options panel with one primary action, a status bar, a Today jump, and a short replayable tour; the tool groups, flyouts and views are declared by the agent as data and rendered by the platform (no agent layout or code) |
| WC174-R028 | The agent's conversation is docked beside the workspace in every mode and view (a bottom sheet on a phone), is one durable conversation shared with WhatsApp, survives a change of mode or view, and shows what is left of the conversation budget; on WhatsApp the workspace is replaced by the next three items and a link |
| WC174-R029 | The conversation is context driven and guided: it knows the mode, view, selected item, readiness gap and package limits; opens with the one next step; asks one new question at a time; offers buttons and free text and always "Do it for me", "Let me do it" and "Explain"; refuses nothing the screen allows and never invents an action the platform does not offer |
| WC174-R030 | AI-first parity and hand over: every tool action can be asked in words and every asked action appears on the workspace; both call the same idempotent commands with the same evidence; an agent change appears as a suggestion until the customer accepts it; each item carries an author state (suggested, customer edited, customer owned, approved version) the customer can change at any time; undo creates a new version and deletes nothing |
| WC174-R031 | The readiness line always shows the one next step with one primary action per mode, computed from the readiness source and the gates, and it is the same text the conversation uses |
| WC174-R032 | The platform records, per relationship, how each outcome was reached (asked in words, accepted from a suggestion, or done with a tool) and shows the Founder the share reached with the assistant; the Founder sets the target; no content of the conversation is stored in the measure |

## Epics And Groomed Stories

Size: S small, M medium, L large (relative). "Proof" is slice 6 in Epic H.

### Epic M. Modes and menus (R001 to R004)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| M1 | As the platform I accept modes as declared data | Additive `modes` field; admission refuses a fourth mode, markup, duplicates, empty targets; legacy declarations admit; specifications, clients and digests move together | BP, specs | L | R001 |
| M2 | As a customer I open my agent and see where I am | Mode menu beside the calendar; readiness line per mode; I can switch at any time; the last mode and surface are remembered | Web | L | R002, R003 |
| M3 | As a customer I am told what a gate needs, not locked out | A gated action explains the missing step and links to it; opening any screen is never refused | Web, BP | M | R002 |
| M4 | As a WhatsApp customer I continue in the same mode | The three modes are conversation context; a hand-off keeps the mode; the next-three-items fallback works | BP, conversation | M | R002, R005 |
| M5 | As the platform I prove another agent needs no shared-code change | The fixture agent's modes, entries, categories and levels render through the same code; a grep test finds no agent name in shared code | BP, Web | M | R004 |

### Epic K. Calendar (R005 to R007)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| K1 | As a customer I see my business year on a calendar | Shared month view with layers, list view on narrow screens, keyboard and screen reader operable, owner and freshness shown | Web | L | R005 |
| K2 | As the DMA customer I see events that matter to my business | Agent proposes events with source, reason and confidence from the confirmed profile; sensitive categories off until I turn them on; I accept, edit or hide | DMA, BP, Web | L | R006 |
| K3 | As a customer I add my own events and placeholders | Own events and placeholders are first-class items; evidence kept; never published by themselves | BP, Web | M | R006 |
| K4 | As a customer I plan on the calendar | Themes, content and publish slots appear and move; the move follows the item's approval rule; package limits are visible | BP, Web | L | R007 |

### Epic I. Induct (R008 to R012)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| I1 | As a customer I am met with what the agent already knows | First screen shows public findings first, then one question at a time, in my language | DMA, Web | L | R008 |
| I2 | As a customer I confirm my business as labels | Highlighted labels I confirm or correct; inference and fact kept apart; resumable on web and WhatsApp | DMA, BP, Web | L | R008 |
| I3 | As the platform I require an answer for every platform | Induction contract 1.1.0: present or not present for each listed platform before READY; unknown, stale or conflicted is not READY; next action shown | DMA contract, BP | M | R009 |
| I4 | As a customer I connect a platform by consent and see it tested | Connect, test, repair, revoke for Facebook and Instagram through Meta; no secret typed or shown; the others say "not yet connectable" and read public data | BP, Web | L | R010 |
| I5 | As the DMA customer my public footprint is read | Website, public social pages, Google listing; each fact with source, time, confidence; correct or remove | DMA, BP | L | R011 |
| I6 | As the DMA customer my registry data is used only if lawful | GST and open-data reads behind the Founder's lawful-basis decision; off until decided | DMA, BP | M | R011 |
| I7 | As a customer I confirm my profile and read my maturity report | Evidence, confidence and correction path; confirmation updates Goals readiness; the score never excludes me | DMA, Web | L | R012 |

### Epic G. Goal setting (R013 to R015)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| G1 | As a customer I set a goal for each skill | Five skills each with baseline, target or threshold, evidence source, cadence, authority state; versioned; material change needs my confirmation | DMA, BP, Web | L | R013 |
| G2 | As a customer I choose my monthly master theme | Proposals from the calendar and profile; I approve before weekly themes are built | DMA, Web | L | R014 |
| G3 | As a customer I approve weekly and individual themes and a story for each | Actors, screenplay, duration, platform per story; each level approved before the next | DMA, Web | L | R014 |
| G4 | As the platform I show any plan as a tree | N-level plan tree block with fallback; used by DMA (four levels) and the fixture agent | BP, Web | M | R015 |

### Epic C. Creation and publishing (R016 to R019)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| C1 | As a customer I get platform-ready drafts | Text and pictures per subscribed platform with one message and each platform's style; review checks run first | DMA | L | R016 |
| C2 | As a customer I get short video and audio when enabled | Behind the media provider gate; rights and likeness rules; "not enabled yet" when off | DMA, BP | L | R016, R019 |
| C3 | As a customer I approve exact versions with a preview | Preview, approve, reject, rework; a change is a new version; evidence | BP, Web | M | R017 |
| C4 | As a customer I see my approved posts scheduled | Publish slots within my purchased count on the calendar | BP, Web | M | R018 |
| C5 | As the platform I publish only what was approved | Consented connection and broker; separate publication authority; Demo sandbox only; Stop halts; expired connection becomes NEEDS_REPAIR and alerts | BP | L | R018 |
| C6 | As the Founder I control media generation | Providers and rates on Pricing, default off; no spend without an authorized rate and the spend chain | BP, billing engine, Web | M | R019 |

### Epic O. Operations (R020 to R023)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| O1 | As a customer I see results against my goals | Each goal with source and freshness; "not measured" with how to connect a source | DMA, BP, Web | L | R020 |
| O2 | As a customer I get a monthly digest and a two-month review | One recommendation and at most one request; proposals only; accepted ones become next goals | DMA, Web | M | R021 |
| O3 | As a customer and operator I am alerted to what needs me | Alerts through the WC-171 policy; the operator console shows failed publishes and repairs | BP, Web | M | R022 |
| O4 | As the platform I keep package counts honest | Every count on screen equals the owner's count; B1 and B2 activation stays a Founder decision | BP, billing engine | S | R023 |

### Epic W. Workspace and conversation (R027 to R032)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| W1 | As a customer I find tools where I expect them | Left rail grouped in build order, changing with the mode; flyouts only on choice; the agent declares groups, flyouts and views as data | BP, Web | L | R027 |
| W2 | As a customer I always have the agent beside me | Conversation docked in every mode and view, bottom sheet on a phone, kept across mode changes, budget left shown | Web, BP | L | R028 |
| W3 | As a customer I am guided from where I am | Context passed to the agent (mode, view, selection, gap, limits); one next step first; buttons, free text, Do it for me, Let me do it, Explain | DMA, BP | L | R029 |
| W4 | As a customer I get the same result by asking or by clicking | Same commands and evidence both ways; agent changes shown as suggestions until accepted | BP, Web | L | R030 |
| W5 | As a customer I hand an item over or take it back | Author state per item; the agent respects it; undo makes a new version | BP, Web | M | R030 |
| W6 | As a customer I always see my next step | Readiness line with one primary action per mode, same text as the conversation; a short tour | Web | M | R031, R027 |
| W7 | As the Founder I see how much work is done with the assistant | Per-relationship share by route (asked, accepted, tool); no conversation content in the measure; target set by me | BP, Web | S | R032 |

### Epic H. Proof and close-out (R024 to R026)

| Story | As a ... I can ... | Acceptance | Owner | Size | Req |
|---|---|---|---|---|---|
| H1 | As a user on any device I can use every screen | The WC-167 R006 layers; vocabulary keys for labels | Web | M | R024 |
| H2 | As the Founder I see the whole journey proven on Demo | Slice 6 with the fixture agent, one calibration report | Acceptance harness | L | R025 |
| H3 | As the Founder I see the record closed | Ledger, roadmap progress, state refresh | Docs | S | R026 |

## Founder-Reserved Items

The author decides every technical point. Only these need the Founder:

| Item | When | What |
|---|---|---|
| Authorize the build | Before any code | Explicit words in the session that starts the build |
| MD1 to MD5 | At grooming acceptance | Confirm three fixed modes, gates that block actions not screens, the Calendar as home, the event states and sensitive-category default, the presence statuses |
| MD6 to MD9 | At grooming acceptance | Confirm the always-docked conversation, AI-first parity, the author states with suggestions held until accepted, and the layout |
| AI-first target | Before the proof | The share of outcomes the Founder expects to be reached with the assistant (R032) |
| Conversation budget | Before the build | How much conversation a package includes and what the customer sees at the limit (spec section 3.16) |
| DMA wording | During the build | The labels of the three modes, the DMA entries, the calendar categories and the story levels |
| Lawful public sources | Before story I6 | Whether and how GST and other registries may be read |
| Platforms and approvals | Before each connector | Which platform goes live in which order; Meta App Review, YouTube, LinkedIn and Google approvals and their lead times |
| Media providers and rates | Before story C2 and C6 | Which image, video and audio providers; authorize their rates on Pricing |
| Package activation | Before the proof | Activate B1 and B2 and complete the Demo package so Hire opens (a Founder step already pending) |
| Deploy | After the build merges | One Environment Deployment of Demo |

## PR And Deployment Plan

| Step | What | Who |
|---|---|---|
| 1 | This grooming pull request (documents and the roadmap section) merges | Founder |
| 2 | Demo read-backs of WC-168 to WC-172 after the current deployment | Author reads back |
| 3 | Build pull request: all stories, one Docker pass, state refresh, bound PR body. **Proposed build order inside it:** Epic M, K and W first (modes, calendar, workspace and the docked conversation), then I, then G, then C and O, so that a split is clean if the build proves too large | Author builds, Founder authorizes and merges |
| 4 | One Environment Deployment of Demo | Founder |
| 5 | Read back each requirement, run slice 6, record the calibration report and ledger rows in a short follow-up commit | Author |

If the build proves larger than one pull request, the author asks for a split at that point in this order: M, K and W together, then I, then G, then C and O. Each part stays independently usable and each leaves the Demo working.

## Journey Simulation (grooming review)

| Step | Expectation after the build | Risk found in grooming | Response |
|---|---|---|---|
| Customer opens the hired DMA | Calendar, a mode menu and the DMA conversation already open with the next step; Induct shows 3 of 17 confirmed | Fixed workbench, no modes, conversation only behind a link | M1 to M3, W2, W3 |
| DMA opens the conversation | Shows what it found, asks one question, highlights the labels | Questionnaire feel; D06 forbids hidden questionnaires | I1, I2 |
| "Do you have Instagram, YouTube, Facebook, WhatsApp, LinkedIn?" | Each answered present or not present; Facebook and Instagram can be connected and tested; others say not yet connectable | Only Meta exists; no passwords allowed | I3, I4, FD1 |
| Customer jumps to Goals before finishing | Opens freely, readiness says what is missing, publishing stays blocked | Locked doors would frustrate | M3, MD2 |
| Calendar shows Diwali, a local match, a clinic anniversary the customer added | Suggestions with reasons, customer note kept, religion and politics off until chosen | Content safety and offence risk | K2, K3, MD4 |
| Planner proposes the October master theme | Weekly themes, individual themes and a story with actors and duration, each approved in turn | New levels beyond the current engine | G2 to G4 |
| Creation makes a post for Facebook and a short video for YouTube | Post works; video says "not enabled yet" until a provider and rate are authorized | No media provider, no rate, metadata only today | C1, C2, C6 |
| Approved post publishes | Goes to the tester Page, counted once, Stop works | Real publishing needs separate authority | C5 |
| Month ends | Digest, results against goals, one recommendation | Business results need customer-owned sources | O1, O2 |
| A second agent is added | Its own modes, events and levels, same code | Agent names creeping into shared code | M5 |
| Customer says "make Diwali week family-led" in the conversation | The calendar shows the changed week as a suggestion; the customer accepts one item, takes another over to write it themselves | Silent changes and lost trust | W4, W5 |
| Customer uses the tools instead | Same commands, same evidence, the conversation sees the change and offers the next step | Two routes drifting apart | W4, W3 |

## Gaps Found In Grooming And How They Were Fixed

| Id | Gap | Evidence | Status |
|---|---|---|---|
| G1 | The Founder's wish to "get credentials" can read as storing passwords | Vision note section 7, WC-149 consent flow, platform terms | FIXED: FD1, consent and test, no passwords (R010) |
| G2 | Navigation has no modes | Schema `navigation` is a flat list | FIXED: R001, M1 |
| G3 | No calendar block | Architecture 6.5 promotes shared blocks; none exists | FIXED: R005, K1 |
| G4 | Induction does not require a platform answer | IND-010 and IND-012 are "NEVER" mandatory | FIXED: contract 1.1.0, R009, I3 |
| G5 | "Collect all details" and D06's one question per cycle can clash | D06 section 4 | FIXED: R008, one question at a time, labels confirmed as a summary |
| G6 | Theme tables exist with no code and the story levels are new | SQL only | RECORDED: author decides reuse or new owner tables in the build; either way the plan tree is the screen |
| G7 | Creation is metadata only today | `content-social-manifest` B1 | RECORDED: text and pictures first, video and audio behind the provider gate (R016, R019) |
| G8 | Only the Meta Page connector exists | WC-149 | RECORDED: other platforms are honest about not being connectable (R010); approvals are Founder items |
| G9 | Lawful use of GST and open data is undecided | No decision on record | FIXED: Founder item and story I6, off until decided |
| G10 | The scope is very large | Eight epics | RECORDED: one pull request is planned; the split order is stated above |
| G11 | The outside-WAOOAW measurement bucket | Founder note: later | RECORDED: out of scope, only WAOOAW's own work is attributed (R020) |
| G12 | The roadmap guard test assumes exactly six iteration rows | `test_roadmap_single_source.py` | FIXED: the new section uses its own track table, and the test lists WC-174 as written |
| G13 | The conversation is a separate place today | Architecture finding F4: the workspace shows only a "Continue in conversation" link | FIXED: R028, W2 |
| G14 | An always-on, AI-first workspace spends model budget on every reply | Spec section 3.16 token economy; WC-170 spend chain | RECORDED: the budget is shown to the customer and a limit is explained; the amount is a Founder item (R028) |
| G15 | "Maximum AI use" could push customers to accept suggestions without thought | D06: no silent authority expansion | FIXED: suggestions stay unapplied until accepted, publishing needs exact-version approval (R017, R030) |

## Stop Conditions

- The Founder has not authorized the build: no code.
- A story needs a shared-kernel change that only DMA needs: stop and ask the Founder.
- A screen, log or store would hold a password, token or secret value outside the vault: stop.
- Anything would be published without the customer's approval of that exact version and a separate publication authority, or to a non-sandbox account on Demo: do not publish.
- Content on religion, politics or another sensitive category would be created or suggested against the customer's setting or C-061: stop.
- A generation would run or spend without an authorized rate: stop.
- An agent change would be applied to the customer's plan or to anything visible outside WAOOAW without the customer accepting it: stop.
- The conversation would act on something the screen does not offer, or store its content in the usage measure: stop.
- A registry or platform would be read in breach of its terms or before the Founder's lawful-basis decision: do not read it.
- An E3 embedded surface is needed: stop; it needs its own security review.

## Definition Of Done

Build pull request: every requirement has a ledger row with executable evidence; the single Docker validation pass is green on the commit gate commands; the pull request body is bound to the final commit. Post-merge qualification: the Founder deploys once, the author reads each requirement back on Demo, runs slice 6, and records the calibration report and the ledger rows. AO-M1 is met only when the read-backs and the slice 6 run pass; real customers and real money stay off until WC-172's separate written go-live approval.

## Implementation Record

Not started. The build is not authorized.

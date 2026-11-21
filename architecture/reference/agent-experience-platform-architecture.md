# Agent Experience Platform - Common Workbench Architecture

## Record Control

| Field | Value |
|---|---|
| Document | `architecture/reference/agent-experience-platform-architecture.md` |
| Authoring office | Enterprise Architect (INST-004), Office 04 |
| Assignment | Founder, current conversation, 2026-11-20: research a common, channel-neutral goal-setting, monitoring and agent-operation experience for Web, WhatsApp and future Mobile, across DMA, Agricultural Advisor, Private Tutor and Trading, and hand a roadmap to the Solution Architect. Extended the same day to the funding boundary (pre-hire, trial and subscription spend), the single Wallet, and a configurable pricing engine with agent-version packages |
| Work Contract | None. Founder assignment is the trigger permitted by the Enterprise Architect card; the Founder was unsure whether a contract is needed. The Solution Architect is expected to create the Work Contracts that decompose this package |
| Status | **ACCEPTED by the Founder, 2026-11-20** (current conversation: authorization to implement WC-136 and update the related documents; decisions D2 kernel and extension tiers accepted as the direction, D3 capability entries added as 6.8 and 6.9 in `knowledge/business-capabilities.md`, D4 in-house block schema kept with AG-UI evaluated for streaming only). This is not an ADR; candidate ADRs in section 13 remain unwritten and wave W3 onwards is not authorized. Decomposed by Work Contract [WC-136](../../work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md) (waves W0, W1, W1s, W1w, W1c, W2 for the DMA) |
| Baseline | `origin/main` `face6359f5dbaa7b2ab3dc380e0ec4a4a27f5fd6` (WC-135 merged through PRs #601 and #602) |
| Reads | ADR-051, ADR-052, ADR-053, ADR-043, ADR-035, ADR-034, ADR-026, `conversational-employment-workspace.md`, `customer-engagement-workspace-solution-contract.md`, `customer-portal-ui-coherence.md`, `AGENT-BASE-SPEC.md`, the DMA, Agricultural, Tutor and Trading specifications, `wbe-component-spec.md`, `dma-bundle-definitions.md`, `thread-catalog.md`, `customer-acquisition-spec.md`, WC-133 to WC-135, `web/components/relationships/*`, `scripts/visitor_simulation/*`, `src/billing-engine/*`, `src/business-platform/Services/*Spend*`, AD-004, AD-013, AD-025, AD-027, DP-003, DP-009, DP-011, DP-013, C-038, C-051, C-088, C-089, C-090, C-091 |
| Authority boundary | No new deployable service, no ADR acceptance, no capability invented, no source code, no activation, no customer traffic |

## Summary For Decision Makers

1. **One product, many renderings.** Web, WhatsApp and Mobile render one Business Platform workbench through a closed, versioned block vocabulary. Agents specialize by declaring data first (E1), registering shared domain blocks second (E2) and embedding sandboxed surfaces last (E3). Sections 5 and 6.1 to 6.9.
2. **One funding model.** Every metered call is charged to exactly one account, resolved on the server from relationship state, focus and purpose: platform-funded for visitors, trial and setup; customer-funded after hire. One entity, the Wallet, holds all balances. Section 6.10.
3. **One configurable pricing engine.** An administrator drafts and simulates agent-version packages made of components with cost recipes; only the Founder authorizes; the same console runs on Demo. Section 6.11.
4. **Proven by simulated customers.** The playground runs the same commands as production in trial mode and also checks funding and pricing scenarios. Section 7 and the simulation record in section 16.
5. **Decisions.** Founder decisions made on 2026-11-20 are in section 12.1; open decisions are in section 12.

## 1. Understanding Of The Task

WAOOAW already owns one relationship, one durable conversation and one Business Platform (BP) facade
(ADR-051, ADR-052). WhatsApp and Web both work "to some extent", and Mobile is next. The risk is not a
missing channel. It is that each channel, and each of the four professional agents, grows its own
goal, monitoring and operation experience. The task is to define the **minimum common product
surface** (API and UI) that every agent and every channel shares, and the **extension model** that
lets an agent add specialization without forking the platform. The result must read like one product
to a customer, the way the reference planner reads like one product: a launcher with several ways
in, a persistent tool rail, a catalogue, a live-synced canvas and an AI assistant beside direct
manipulation.

The same product must also be **commercially coherent**: the conversation a visitor has before hiring is
paid for by the platform, the work a hired customer buys is paid for from that customer's subscription, and an
administrator can tune prices and budgets without code. That adds a funding boundary beside the existing data
boundary (section 6.10) and a pricing engine (section 6.11).

## 2. Obligation Ledger

| Obligation | Source | What it demands of this design |
|---|---|---|
| Conversation is a complete configuration path | Capability 1.7, AD-013, C-039 | Every goal and plan edit has a conversational path; forms are optional accelerators |
| Goals are business outcomes | Capability 4.5, AD-012, DP-011 | The kernel models outcome, measure and target, not agent internals |
| Monitoring against KPIs | Capabilities 2.5, 2.7, 12.1 | One monitor model fed by owner projections |
| Customer sees business meaning | DP-011, DP-013, C-042 | Vocabulary is data supplied by the agent declaration, never kernel code |
| Configuration over code | DP-003 | Specialization is declared first and coded last |
| API first | DP-009, ADR-002 | Specification before any endpoint or screen |
| One conversation across channels | ADR-052 | Channels render; they never own history or semantics |
| Conversation proposes, owners commit | ADR-051 section 2 | Generated UI or text can propose; only BP commands change state |
| Tenant isolation | AD-004, AD-025, DP-007 | Every kernel resource and extension is tenant-keyed |
| Emergency Stop, consent, honest limitation | C-001, C-049, `AGENT-BASE-SPEC.md` B-4 and B-5 | These behaviors have identical meaning on every channel |
| Agents declare conformance | ADR-051 section 7 and 13, AD-027, ADR-035 | The experience declaration is part of the existing manifest, not a new document family |
| Governed web experiences | Capability 6.6 | Web is one renderer of the shared contract |
| Every cost has a catalogue entry; every offered agent has a Founder-authorized billing profile; price above cost floor | C-091, C-088, C-089 | Every spend account, platform-funded ones included, maps to Thread Catalog entries (section 6.10) |
| Customer sees remaining capacity in business language | C-051, C-049 | Exhaustion behavior is disclosed per account class |

**No new business capability is required for the experience itself.** Capabilities 1.7, 2.5, 2.7, 4.5, 6.6 and 13.9 already
cover goal setting, monitoring and testing. Two gaps are flagged for the Founder in decision D3, because an
architect may not invent capabilities: capability 6.6 is web-scoped, so channel-neutral rendering (WhatsApp and
Mobile) has no named capability; and the capability map has no entry for **configuring pricing and platform-funded
spend** (the map covers billing customers, 6.5, and subscription lifecycle, 9.1 and 9.2, but not authoring packages,
rates and budgets).

## 3. Current-State Findings

| # | Finding | Evidence | Consequence |
|---|---|---|---|
| F1 | **Three overlapping progress projections exist**: the Relationship Workspace (Plan, Work, Results, Usage and budget, Rights), the Conversational Employment Workspace (phases and readiness, ADR-051) and the Customer Engagement Workspace (progress items and focus, WC-121). Web renders each with a separate component. | `web/components/relationships/RelationshipWorkspace.tsx`, `ConversationalEmploymentWorkspace.tsx`, `CustomerEngagementWorkspace.tsx`; `conversational-employment-business-platform.openapi.yaml`; `customer-engagement-workspace-business-platform.openapi.yaml` | This is the main source of future channel friction. Each channel would have to choose, or merge, three truths. |
| F2 | The generic kernel is already written four times in prose: approval-mode ladder, cadence, five-part performance narrative, goal-miss escalation, budget control, override table, strategic planning and assessment modes. | DMA section 3.14 and 3.15; Agricultural 4.14 and 4.15; Trading 4.14 and 4.15; Tutor 3.0d and 3.15 | The kernel exists as documents, not as machine-readable data or shared API and UI. |
| F3 | Only DMA has a customer-facing implementation. Trading has an adapter only. Agricultural and Tutor are specification only. | `src/digital-marketing-agent`, `src/agent-adapters/trading` | The common contract cannot be proven by implementations yet. It must be proven by conformance scenarios and simulated customers. |
| F4 | The web employment workspace shows phase counts, readiness and a "Continue in conversation" link. It has no goal editor, no plan view, no monitor, no decision queue. It renders an "unavailable" state when the candidate capability is disabled. | `ConversationalEmploymentWorkspace.tsx` | Goal setting and monitoring are not yet a product surface on any channel. |
| F5 | A closed, versioned structured reply already exists and is rendered by WhatsApp and a channel-neutral endpoint: `{ schemaVersion, state, cursor, blocks[] }` with `TEXT`, `CHOICES` (up to 3), `LIST` (up to 10) and `LINK` blocks, plus a parity requirement and a renderer that falls back to canonical text. | `VisitorReply.cs`, `VisitorWhatsAppRenderer.cs`, WC-135 Interface Contract and fitness F1 | This is the seed of the shared experience contract. It covers visitors only, and only four block types. |
| F6 | ADR-051 section 13 already defines an Employment Interface Conformance Manifest (induction, planning, operations), and AD-027 defines a per-skill capability manifest. Neither declares goal types, measures, monitor content, narratives or domain blocks. | `conversational-employment-workspace.md` section 13; `architectural-drivers.md` AD-027 | The extension point exists. It is incomplete for experience. |
| F7 | WhatsApp and the API channel disagree on STOP. The API acknowledges ("You're opted out... Send START to chat again"); WhatsApp sends nothing (WC-135 limitation 3). The simulation judge hard-codes silence. | `scripts/visitor_simulation/judge.py` lines 337-341; WC-135 Known limitations 3 | A protocol-level behavior is defined by whichever component is asked. It must be a single policy. |
| F8 | The 1.9 of 5 "safety" score is a judge defect, not a product defect. The judge requires an empty reply on STOP, so the correct acknowledgement scores -3 per STOP. The Founder also reports the judge treats consent after START and YES as missing. | `judge.py` `score_safety`; Founder report 2026-11-20 | The evaluation oracle is not yet derived from the same policy the product executes. |
| F9 | Simulated customers and judge are scripted. No LLM persona, no calibration against real conversations, no repeated-trial reliability metric. Real-phone acceptance is outstanding. | WC-135 Known limitations 1, 2; Founder report 2026-11-20 | Current pass results (70 of 70, 140 of 140) prove the scripted machine, not customer experience. |
| F10 | The visitor handoff already defines an opaque single-use reference to the portal with non-sensitive prefill. | WC-135 Handoff Contract | A generic cross-channel handoff pattern exists and can be reused for monitor and approval links. |

## 4. Industry Research

Sources are listed in section 14. Secondary sources are marked; none of them decides an architecture
choice without a primary check.

| # | Finding | Implication for WAOOAW | Decision |
|---|---|---|---|
| R1 | **Declarative, host-owned UI.** A2UI sends a JSON description and lets the host render its own native components from a fixed catalogue. AG-UI standardizes an event stream between agent backend and any client, and its clients need not be web. MCP Apps embeds richer sandboxed surfaces. | Matches ADR-051 "conversation proposes, owners commit" and our existing block reply. Open generative UI conflicts with fail-closed governance. | Adopt the principle (closed catalogue, server describes, client renders). Do not adopt model-authored layouts for consequential surfaces. Evaluate AG-UI as the streaming transport. |
| R2 | **Server-driven UI at scale.** Airbnb, Lyft, Yelp and others serve web, iOS and Android from one schema, using a component registry, a versioned schema and per-client renderers. Version negotiation by client header keeps compatibility logic on the server. (Secondary sources.) | Mobile should arrive as a renderer of an existing contract, not a new product. Unknown block versions must degrade, not fail. | Version every block. Negotiate capability and version per request. Keep a registry of block renderers per channel. |
| R3 | **Human-in-the-loop agent UX.** Microsoft's Magentic-UI uses co-planning (editable plan before action), co-tasking (user can interrupt and the agent can ask for help), action guards (approval for irreversible actions, user-set frequency) and verification. | This maps directly onto WAOOAW goal, plan, approval ladder and Stop. | Make the plan an editable, versioned object. Make action guards the approval ladder already in DMA 3.14.1. |
| R4 | **Enterprise agent control planes.** Microsoft Agent 365 and Foundry provide a registry, agent identity, policy templates, role-based reporting, task-adherence checks and OpenTelemetry-based observability; Salesforce provides session tracing and an Observability tab. | A monitor must be role-aware (customer, steward, platform) and trace-backed. Adherence and ROI are first-class tiles. | One monitor model with role projections. Customer monitor is business-language; steward monitor is trace-backed. Same facts, different projections. |
| R5 | **Multi-tenant agent deployment.** The AWS Agentic AI Lens recommends tiered tenancy (pooled with session isolation, premium with dedicated resources), throttling at every shared layer, tenant context propagated through the whole stack and per-tenant dashboards. | Supports "specialization plus scale": one kernel, per-tenant configuration layers, per-tenant quotas. AD-004 and AD-025 already require the isolation. | Tenant tier and quota become inputs to the experience projection (what is offered, how fast), not forks of it. |
| R6 | **Simulation-based evaluation.** tau-bench and tau2-bench use a user simulator coupled to the environment's tools and state, verifiable tasks, and the `pass^k` reliability metric (all k independent runs succeed). Salesforce Testing Center added persona-driven conversation tests, LLM-as-judge and full execution traces. | Our harness is the right shape. It lacks repeated-trial reliability and trace-linked scoring. | Add `pass^k` and trace linkage. Keep tasks verifiable by environment state, not by judge opinion alone. |
| R7 | **Simulated users are unreliable proxies.** A 2026 ACL study found success rates varying up to 9 points across user simulators, systematic miscalibration (underestimating hard tasks, overestimating moderate ones) and worse outcomes for some dialects. A second study shows persona drift across experiment arms, so a synthetic A/B test is observational. | A simulated-customer pass is evidence of regression safety, not of customer satisfaction. Language and dialect fairness must be measured, not assumed. | Require human calibration samples, multiple simulator models, fixed-seed personas and drift checks before any numeric claim. Keep real-phone acceptance as a separate gate. |
| R8 | **WhatsApp interactive limits (primary source checked).** Reply buttons: up to 3, title up to 20 characters, body up to 1,024, footer up to 60, id up to 256. List messages, carousels and Flows exist; free-form interactive messages only inside the 24-hour customer-service window, templates outside. (Lists, Flows and window rules come from secondary sources and still need the primary check that WC-135 F-S11 already requires.) | WhatsApp is a capability-limited renderer. The kernel must define a degradation ladder, not assume rich UI. | Channel limits are configuration read from the channel capability layer. Anything beyond 3 choices or 10 rows degrades to text or a handoff. |

## 5. Common Minimum Kernel And Specialization

### 5.1 Comparison of the four agents

| Dimension | DMA | Agricultural Advisor | Private Tutor | Trading |
|---|---|---|---|---|
| Customer role | Business owner | Farmer (voice-first, regional language) | Parent employs; student is the beneficiary | Trader |
| Goal shape | Monthly marketing KPIs | Seasonal crop and income outcome | Learning goal, syllabus, exam date | Risk-adjusted return within loss limits |
| Approval model | Ladder: customer, exception, synthetic | Per-skill approval | Session approval | Pre-authorized (PAAS), escalate on UNCERTAIN |
| Cadence | Daily to monthly, goal check week 2 | Daily advisory, seasonal | Weekly discovery, sessions | Market-day session, 60-second risk loop |
| Narrative | Five-part monthly, all channels | WhatsApp voice, no portal | Parent progress report | Session report and monthly review |
| Hard limits | Ad budget cap, content safety | Spray decisions need fresh data | Minor protection (C-060) | Daily loss limit halts trading |
| Specialized surface | Content calendar, post preview, campaigns | Crop and plot cards, mandi prices | Whiteboard, session memory | Positions, risk gauge, session P&L |
| Primary channel | Portal and WhatsApp | WhatsApp | Portal and WhatsApp | WhatsApp push and Portal |

### 5.2 The kernel (identical for every agent)

| # | Primitive | Meaning | Existing owner and contract | Gap |
|---|---|---|---|---|
| K1 | **Start** | Ways to begin a goal: ask in conversation, guided form, starter template, import | Conversation Core, Interview Mode (C-048) | No launcher; no starter-template concept |
| K2 | **Goal and Plan** | Outcome, measures, targets, constraints (Decision Space), milestones, calendar, version, material-change rule | ADR-051 section 6, capability 4.5, workspace doc section 6 | Not rendered; goal types not declared per agent |
| K3 | **Capabilities** | Skills offered, activation, pause and resume, per-skill approval mode | ADR-043, AD-027, capabilities 5.4 and 5.5 | No customer-facing catalogue screen |
| K4 | **Operate** | Work items in the common item states, cadence, run history | Workspace doc section 4.2 and 7 | Not projected to a screen |
| K5 | **Decide** | One queue of pending decisions with effect, authority, cost, confirm and cancel | Capabilities 2.1 and 2.2, "Needs your attention" in the web workspace | Per-agent approval ladders are prose; one queue not defined |
| K6 | **Monitor** | Outcome versus goal, narrative, usage and budget, alerts, freshness | Capabilities 2.5, 2.7, 6.5, WBE projections | No common monitor model; narrative structure is prose |
| K7 | **Evidence** | Timeline, export, provenance of every displayed state | Capabilities 2.6 and 5.3; `EvidenceWindow.tsx` | Fine on Web only |
| K8 | **Control** | Stop, pause, consent, data rights, rights and scope | C-001, B-5, data-rights endpoints | Stop acknowledgement differs by channel (F7) |
| K9 | **Conversation** | One durable conversation with handoff between channels | ADR-052, WC-120, WC-135 | Handoff exists for visitors only |

The kernel is the same program of work for every agent. Specialization never adds a kernel primitive; it fills
the primitives with agent data (E1), adds domain blocks (E2) or embeds a rich surface (E3).

### 5.3 What is agent-specific

Goal-type schemas and vocabulary; measures and their evidence sources; cadences and session windows;
narrative templates; hard limits and escalation rules; domain blocks and domain tools; language and
voice profile; regulatory rules. All of these are declared (section 6.2), none are coded into the kernel.

## 6. Target Architecture

### 6.1 Principle: one meaning, many renderings

```text
Agent Experience Contract (declared per agent version, immutable once admitted)
        |
        v
Business Platform Workbench Projection  <-- owner projections (WBE, PR, CE, domain adapter)
   (one read model, one command set, tenant-keyed, versioned)
        |
        v
Experience Blocks (closed, versioned, with mandatory fallback)
        |
   +----+----------------+----------------+
   v                     v                v
 Web renderer      WhatsApp renderer   Mobile renderer
 (full)            (limited, handoff)  (native, push)
```

No new deployable service. BP remains the only public facade (ADR-051 section 6). Clients never receive
tenant, authority, policy, layout or prompt content from a model.

### 6.2 Agent Experience Contract (AEC)

The AEC is a new `experience` section of the Employment Interface Conformance Manifest (ADR-051
section 13) and is cross-referenced from each skill's capability manifest (AD-027) and the
Platform-Agent Contract (ADR-035). It is data, validated at admission, and read from an immutable admitted
version at runtime. It declares:

```yaml
experience:
  contract_version: "1.0"
  vocabulary_ref: "..."              # DP-013 translation layer
  goal_types:                        # typed parameter schema per goal type
    - goal_type_id: "..."
      parameters: [...]
      measures: [{measure_id, unit, evidence_source, freshness}]
      constraints: [...]             # Decision Space references
      starters: [...]                # templates for the Start primitive
  plan:
    milestone_types: [...]
    calendar_windows: [...]          # for example market-day session, season, school term
  operate:
    work_item_types: [...]
    cadence: [{skill_id, trigger, window}]
    approval_modes: [...]            # ladder or pre-authorized, escalation rules
  monitor:
    tiles: [{tile_id, measure_id, block, audience}]
    narratives: [{narrative_id, cadence, channels, structure}]
    alerts: [{signal, threshold, severity, channels}]
  domain_blocks: [{block_id, version, fallback}]
  components:                        # deliverables an agent can be sold by; packages reference these ids
    - component_id: "..."
      unit: "post | ad boost | monitored platform | ..."    # agent vocabulary
      skill_id: "..."                # the skill that delivers it (pause and pro-rata follow the skill)
      counted_on: "owner-confirmed outcome"                  # work item type whose COMPLETED state consumes one unit
      selectable_dimension: {kind, maximum}                  # optional, e.g. customer-selected platforms
  audiences: [customer_owner, delegate, beneficiary, steward]  # who may see which tiles and blocks
  modalities: [text, voice]          # voice in and out is a modality, not a channel
  channel_support:
    web: [...]
    whatsapp: [...]
    mobile: [...]
  conformance_scenarios: [...]       # simulated-customer scenario ids
```

### 6.3 Workbench Projection and common API

One BP read model, `WorkbenchProjection`, replaces the three overlapping projections as the single
source for every channel. The existing three endpoints keep working during migration (compatibility
shim, then retire, section 9).

| Resource | Purpose | Builds on |
|---|---|---|
| `GET workbench` | Whole-relationship summary: phase, readiness, current goal, top decision, top alert, freshness | ADR-051 workspace, WC-121 progress |
| `GET/POST goals`, `GET goals/{id}/versions` | Create, revise, version goals with measures and constraints | Capability 4.5, ADR-051 section 6 |
| `GET/POST plans`, `.../accept` | Editable plan with milestones and calendar; acceptance is a gate | ADR-051 gates |
| `GET capabilities`, `POST capabilities/{id}/commands` | Catalogue, activate, pause, set approval mode | ADR-043, capabilities 5.4, 5.5 |
| `GET work-items` | Operate state in the common states | Workspace doc section 4.2 |
| `GET decisions`, `POST decisions/{id}/resolve` | Single decision queue with effect, authority, cost | Capabilities 2.1, 2.2 |
| `GET monitor`, `GET monitor/narratives` | Tiles and narratives by audience | Capabilities 2.5, 2.7 |
| `GET evidence`, `POST evidence/exports` | Timeline and export | Capabilities 2.6, 5.3 |
| `POST controls/stop`, `POST controls/pause` | Stop and pause with the same semantics everywhere | C-001, B-5 |
| `POST handoffs` | Opaque single-use hand-off between channels | WC-135 Handoff Contract |
| `GET packages` (per agent version), `POST subscriptions` (hire), `POST subscriptions/{id}/changes` (upgrade, downgrade, pause, terminate) | Customer commercial journey: see what a package contains, hire, change, stop | WBE owner contract, C-038, C-090, section 6.11.2 |
| `GET wallet` (components remaining, period end), `POST topups` | Remaining capacity in business language; top-up where the package allows | C-051, WBE commercial projection |

Audience is part of every projection. The customer owner, a delegate, a **beneficiary** (for example the student
in Private Tutor, who sees a restricted projection under C-060) and a steward each receive only the tiles and
blocks the agent declaration allows for that audience. A customer's staff or family members are delegates with
narrower rights, never separate tenants.

A beneficiary never sees money, price, top-up or purchase controls. When the wallet scope or a component is
exhausted during a beneficiary's session, the beneficiary is told in age-appropriate words to ask the customer
owner, and the notice, the choice to top up and the cost go to the owner.

Every response carries owner, evidence state and source freshness (ADR-051 section 3). Every command is
idempotent, tenant-keyed, evidence-first and returns an operation reference. These are the existing
conversation rules, applied to the whole workbench.

### 6.4 Experience blocks

Extend the existing `TEXT`, `CHOICES`, `LIST`, `LINK` vocabulary. Proposed v1 additions, each with a
semantic payload, a version, a sensitivity class and a mandatory fallback made only of existing blocks:

| Block | Use | WhatsApp rendering | Web and Mobile rendering |
|---|---|---|---|
| `STATUS` | Item state, owner, freshness | One line plus link | Status card |
| `METRIC` | Value against target, trend, freshness | Sentence | Tile or chart |
| `PLAN` | Milestones and calendar | Top three plus link | Editable timeline |
| `DECISION` | Effect, authority, cost, confirm, cancel | Up to 3 buttons | Decision card |
| `FORM` | Typed fields for a goal or setting | Sequential questions, or a Flow if verified | Native form |
| `EVIDENCE` | Provenance reference | Short reference | Expandable provenance |
| `DOMAIN` | Registered extension block (section 6.5) | Fallback blocks | Domain renderer |

Rules: the server sends semantics, never layout; unknown versions degrade through the fallback; a block never
carries authority; a free-text answer is always accepted next to any choice (existing rule).

### 6.5 Extension model

| Tier | What the agent supplies | Review needed | Channels |
|---|---|---|---|
| **E0 Kernel** | Nothing | None | All |
| **E1 Declarative** | AEC data: vocabulary, goal types, measures, cadences, narratives, starters, tiles | Admission validation and conformance scenarios | All |
| **E2 Domain block** | A registered block with schema, fallback and per-channel renderers (examples: time-series metric, calendar, document preview, position table, crop card) | Registry review, accessibility, security | Web and Mobile full; WhatsApp fallback |
| **E3 Embedded surface** | A sandboxed rich surface (for example the Tutor whiteboard), loaded in a strict content-security sandbox | Security and privacy review per surface | Web and Mobile only; text fallback mandatory |

Prohibitions: agent code in the kernel; agent-defined layout; model-generated markup; a surface that
changes state except through BP commands; an E3 surface that cannot be disabled per tenant.
Reuse is the rule. A block that two agents need (for example a calendar) is promoted to a shared E2 block, not copied.

### 6.6 Channel parity rules

| Class | Rule | Examples |
|---|---|---|
| **P0 Authority and safety** | Must exist on every channel with identical semantics and acknowledgement | Stop, consent, START, approval of a consequential action, status of a consequential action, honest limitation |
| **P1 Core journey** | Must be possible on every channel, rendered to the channel | Set or revise a goal, accept a plan, resolve a decision, read the monitor summary and narrative |
| **P2 Rich** | May be limited to Web and Mobile, with summary and handoff elsewhere | Plan editing, charts, bulk operations, whiteboard, evidence browsing |

Capability negotiation: each request declares channel class, modality and the highest block versions it renders;
BP selects blocks and fallbacks. Channel limits are configuration (R8). **Protocol behaviors are Conversation
Policy, not channel code** (ADR-052 layers): STOP acknowledgement, consent wording and quiet hours are one
policy table read by every renderer and by the simulation judge (resolves F7 and F8). Identity step-up for
consequential P1 actions that WhatsApp cannot safely perform uses the single-use handoff.

**Voice is a modality.** The Agricultural Advisor is voice-first in regional languages and the DMA narrative
includes a spoken summary. Every block therefore carries a short spoken form (text for speech synthesis), and
inbound audio is transcribed into the same typed contribution a text message produces (the existing voice
contribution and transcription paths). Parity rules apply per modality, so a P0 action such as STOP must work
by voice as well as by text.

### 6.7 Multi-tenant, multi-agent: specialization plus scale

- Tenant configuration layers follow ADR-052: platform, agent, tenant, customer, channel. A layer may narrow, never widen, the layer above.
- Pooled tenancy by default, with a dedicated tier as an option, as the AWS Agentic AI Lens recommends. Tier and quota are inputs to the projection (what is offered), not forks.
- Throttling, metering and dashboards per tenant at every shared layer (R5), consistent with AD-025.
- Adding an agent is an AEC plus its adapter. Adding a tenant is configuration. Neither requires a kernel change. This is the testable definition of "specialization plus scale" (fitness A1 and A2).

### 6.8 Mobile readiness

Mobile requires, before it starts: the workbench API and blocks above, a published block schema with
generated client, push as a delivery channel under the same P0 rules, and device-bound step-up for P0
approvals. It must need no new business endpoint. If Mobile needs one, the kernel is incomplete (fitness A3).

### 6.9 What the reference images teach

| Reference pattern | WAOOAW equivalent |
|---|---|
| "Start your project": several ways in (draw, ask AI, open) | K1 Start: ask the professional, guided form, starter template, import |
| Persistent tool rail | Stable application frame with the kernel primitives and Stop always reachable |
| Categorized object catalogue with search and counts | K3 Capabilities: skills by outcome, with state and approval mode |
| Settings panel (time of day, grid) | Goal and plan parameters from the declared schema |
| Live 2D and 3D sync, "synced" indicator | Conversation and workbench synced, with evidence freshness shown |
| AI assistant beside direct manipulation | Conversation is primary, forms and plan editing are accelerators on the same commands |
| Tooltips with shortcuts | Every consequential action shows effect, authority and cost before confirmation |

The three-region composition (context, conversation, progress) already in the customer engagement
contract is the correct frame. The work is to fill it with the kernel, not to redesign it.

### 6.10 Spend Accounts And Funding Boundaries

**Principle.** The platform has a *data boundary* (tenant, relationship, agent instance; AD-004) and now
a *funding boundary*. They are orthogonal. Every metered call (model, messaging, media, any paid API)
is charged to exactly one **spend account**, chosen on the server from relationship state and the
purpose of the turn, never from the channel or the client.

Rules:

1. A spend account lives inside one tenant and never spans tenants.
2. A spend account never grants data access or work authority (a budget does not grant authority, WBE owner contract section 2).
3. The account is **pinned when the reservation is made**; a later state change, such as trial converting to hire, never re-routes an in-flight call.
4. Every cost, including platform-absorbed cost, has a Thread Catalog entry before it is incurred (C-091), and every offered agent has a Founder-authorized billing profile in trial, demo and live (C-088).
5. WBE owns every commercial ledger entry, platform-funded ones included. BP owns the environment circuit breaker. Neither mints the other's permission (WC-134 section 1), and both reservations are required before dispatch.

**Terms used in sections 6.10 and 6.11.**

| Term | Meaning |
|---|---|
| Wallet | The one balance entity (6.10.1): an owner, a scope and a ledger of credits, reservations and settlements |
| Package | What a customer hires for one agent version at one price per billing period (names such as Starter, Runner, Winner are data) |
| Component | A customer-facing deliverable inside a package with a quantity per period (for example 4 posts). It is what limits the customer |
| Cost recipe | The provider units one unit of a component consumes; it prices the component and sizes the wallet credit |
| Spend account | The wallet scope a call is charged to, one of the six classes below |
| Tenant | A customer organisation and its data boundary (AD-004). Pre-hire visitor traffic belongs to the **marketplace tenant** that hosts the public conversation (today the Demo default tenant), which owns the ACQUISITION accounts. When a visitor registers, the lead is linked to the new customer tenant by an opaque one-way reference; no data moves between tenants |
| Allowance, bundle, ration | Retired terms. They survive only in names of existing code and tables, which the wallet convergence (RC4) removes |

**Verified baseline** (repository at the baseline commit):

| # | Finding | Evidence |
|---|---|---|
| S1 | Pre-hire visitor chat is scripted and has no model spend. Limits are counts (10 messages per guest per 24 hours, 100 new sessions per day) plus a shared environment ceiling; there is no cost attribution per lead, campaign or tenant. | WC-135 R005; `WhatsAppGuestTrafficBudget.cs` |
| S2 | Authenticated relationship conversation is already double-reserved: commercial (the `MODEL_GENERATION` component against the relationship allowance, keyed by tenant, relationship, agent instance and skill) and operational (environment ceiling). | `ConversationInferenceOwner.cs` (`OfferingIdentity`); WC-134 section 4.2 |
| S3 | The environment ceiling is a Demo constant: `Math.Min(500m, ...)` in code and `maximum_paise <= 50000` in the database. It is shared by model and messaging spend and also applies to authenticated chat. | `ConversationInferenceOwner.cs:214,354,388`; `WhatsAppTrafficBudget.cs:250,428`; `99zzzzzz-wc134-environment-spend.sql` |
| S4 | WBE has two commercial ledgers: wallet buckets (paise per customer and thread type, pooled across agents) and offering allocations (units per relationship and component). The relationship budget view still shows a placeholder. | `wallet/service.py`; `meter/allowance_service.py`; `relationship_workspace.py:239` |
| S5 | Trial mode is a customer-level Redis key (`wbe:customer:{id}:mode`) that forces the free model tier for all of that customer's calls. The per-relationship `trial_entitled` parameter has no non-test callers. Redis as authority conflicts with the billing state boundary. | `trial/service.py:179,302`; `pse/router.py:331-336`; `token-economy.md` Billing and Usage State Boundary |
| S6 | Trial is unique per (customer, agent type, agent version). | `infrastructure/postgres/init/48-wc112-trial-agent-version.sql:30` |

**Account classes.**

| Account | Funder | Scope | Limits | At exhaustion |
|---|---|---|---|---|
| ACQUISITION | Platform | Marketplace tenant, then campaign or channel, then visitor or lead, under the environment breaker | Configurable count and money caps at each level | Scripted replies and a handoff |
| SETUP GRANT | Platform | Relationship, one time | Configurable cap and time window | Remaining onboarding continues on the subscription wallet scope only after the customer is told |
| TRIAL | Platform | Relationship | Capped free units on the free model tier | "Demonstration mode" disclosure, then scripted replies |
| SUBSCRIPTION | Customer | Relationship, split per skill | Package components as the customer's limit; wallet credit at recipe cost as the cost guard; money exposure bounded by the package cost floor (C-089) | Disclose (C-051, C-049), then free path; more only through an explicit customer top-up |
| PLATFORM FLOOR | Platform | Environment | Never gated | Emergency Stop, evidence recording, loss-limit and disaster alerts (existing constitutional exemption) |
| SIMULATION | Platform | Environment, with its own cap | Separate configurable cap; scripted personas spend nothing, model-backed personas draw only here | The run stops; it never falls through to ACQUISITION or any customer scope |

**6.10.1 One entity: the Wallet.** WBE keeps a single entity with its literal meaning: a balance owned by a
party, from which spend is drawn, backed by a ledger of credits, reservations and settlements. The six
account classes are wallets distinguished by **owner and scope**, not new entities:

| Dimension | Values |
|---|---|
| Owner | CUSTOMER or PLATFORM (the existing `billing_entity_type` gains a platform value; agency parent and child remain) |
| Scope | Relationship with per-skill sub-wallets (SUBSCRIPTION, TRIAL, SETUP GRANT); marketplace tenant, campaign and lead (ACQUISITION); environment (PLATFORM FLOOR, SIMULATION) |
| Balance lot kind | `PERIOD_CREDIT` (credited when a subscription period is paid), `TOPUP_CREDIT` (bought by the customer), `GRANT` (platform-funded: trial, setup, acquisition). By Founder decision FD9 **no lot is refundable and no lot rolls over**: every lot expires at the end of its period |

The customer sees **components remaining** in business language ("2 of 4 posts left until 14 December"), not money
and not provider units (decision FD12). Behind that, the wallet scope holds credit equal to the package's cost
recipes at a **pinned rate version**, so a later provider price change never silently shrinks or grows what the
customer was sold, and acts as the cost guard. The offering allocation tables built in WC-134 become a
projection of the wallet during migration and are retired after parity tests pass.

Legal meaning, flagged for review before Production: because no lot is refundable and none rolls over, a wallet
balance is **service credit for a paid period, not stored value**, which lowers the prepaid-instrument and GST
risk of the word "wallet". Two existing rules still collide with "nothing is refundable" and need a Founder
decision (D10): C-038 says billing stops pro-rata from the moment of a customer's pause or termination, and
ADR-026 refunds any remaining ad-spend wallet balance within 7 days of termination. This is an architectural
note, not legal advice; the Founder should have counsel confirm before Production.

**Resolver.** Inputs: relationship state, the server-resolved interaction context (ADR-052), and the turn
purpose. A customer works in **one agent at a time**, like one project at a time in the reference planner;
focus changes only by an explicit selection. Therefore:

- Onboarding turns of a relationship draw on its **SETUP GRANT** (one per relationship, created with the relationship) until onboarding completes or the grant is exhausted; this holds whether the customer is in trial or has hired. All other turns are charged to that relationship's TRIAL or SUBSCRIPTION scope according to state. A relationship therefore never draws two platform grants for the same turn, and a trial's free units fund work, not the interview.
- Marketplace browsing, pre-sales questions about other agents, and platform support are charged to ACQUISITION or PLATFORM FLOOR, not to any agent's wallet scope.
- A request that belongs to another agent is redirected without agent work: the classification is deterministic or free-tier and platform-funded, and the customer is asked to switch focus.
- A portfolio view ("how are my agents doing") is a deterministic dashboard projection, not an agent conversation, and costs no model spend.

**Policies decided by the Founder, 2026-11-20** (recorded in section 12.1): configurable production ceilings with Demo
at INR 500; unused wallet credit expires at period end (no rollover, and unused trial or setup credit does not convert);
trial is independent of hire status and limited to one per customer per agent type and version, because
versions differ in features and hiring cost; every trial, hire and price consideration is version-specific.

**Options considered.**

| Question | Option | Verdict |
|---|---|---|
| Pre-hire funding | P1 one environment bucket (today) | Demo only: mixes breaker with funding, no fairness, no cost per lead |
| | **P2 hierarchical platform budgets** | **Adopted** |
| | P3 zero-cost only | Kept as the exhaustion floor |
| | P4 visitor pays first | Rejected (conversion, C-009, C-048) |
| Customer bucket | C1 one pooled wallet across agents | Rejected as base: cross-subsidy defeats the per-package margin floor |
| | **C2 per-relationship wallet scope, split per skill** | **Adopted** |
| | C3 C2 plus customer-level envelope | Later (Founder decision) |
| | C4 per-skill only | Too fine; skills are sub-allocations of C2 |
| Which account pays | By channel or by login | Rejected: charges the wrong party |
| | **Server resolver on state, focus and purpose** | **Adopted** |

**Hired multiple times later.** Whether one customer may hire the same agent more than once is a later Founder
decision (D13). The design is ready for it: a second hire of the same agent version would be another relationship
with its own agent instance, wallet scope, package components and data scope, with no migration, because
consumption is already keyed by agent instance. The trial is unaffected: the customer keeps exactly one trial per
agent type and version whatever they have hired, and that trial is its own relationship with its own TRIAL account.
A new version is a different offering (features, hiring cost, billing profile), so it carries its own trial and its
own package. Each additional hire would also receive its own setup grant (decision FD1).

**Required changes.**

| # | Change | Why |
|---|---|---|
| RC1 | Replace the customer-level trial flag with relationship-level trial authority read from WBE's database | S5; multi-agent correctness |
| RC2 | Make the environment ceiling configuration, validated against a per-environment maximum, and separate the breaker from funding; Demo keeps INR 500 | S3 |
| RC3 | Keep trial uniqueness at (customer, agent type, agent version), as in the schema today, and make trial eligibility independent of hire status: hiring a version never consumes or blocks its trial. Bind trial eligibility to a verified identity (the phone proof of ADR-023), not only to an account, so one person cannot collect several trials. Resolve every trial, wallet scope and price by the exact agent version | Founder policy; S6 |
| RC4 | Converge on **one entity, the Wallet** (decision FD7, section 6.10.1). The offering allocation tables become a projection of the wallet during migration and are retired after parity is proven; no second customer wallet is created | S4; Founder decision |
| RC5 | Build ACQUISITION and SETUP GRANT accounts and their Thread Catalog entries before any generative visitor or onboarding responder is enabled | C-091 |
| RC6 | One server resolver with pin-at-reserve; the walk-throughs below become conformance scenarios in the playground | Rule 3; section 7 |
| RC7 | Add agent version to the package key; replace the fixed tier names with free-form package names; add package components and cost recipes as versioned configuration (section 6.11.1); keep `thread_rations` as the derived cost view until retired | C6, C7; Founder direction 2026-11-20 |
| RC8 | Resolve the conflict between `AGENT-BASE-SPEC.md` B-3 (WBE unavailable: continue silently) and WC-134 section 4.2 (no metered dispatch without a commercial reservation) by the failure table in 6.10.2, and update B-3 accordingly | 6.10.2 |
| RC9 | Make the WBE commercial projection and commands durable in PostgreSQL (today held in process memory), implement pro-rata fee computation from component price allocation (none exists in WBE), and unblock the renew and terminate commercial commands under the approved policy (today they return BLOCKED) | Simulation findings SG4, SG6; C-038 |
| RC10 | Emit cost telemetry per conversation, per lead and per account so ACQUISITION cost per lead, trial-to-hire conversion and margin variance can be shown. Leads are identified only by a pseudonymous reference, never by phone, name or email | Simulation finding SG5; section 6.11 dashboard; C-063 |
| RC11 | Replace the single environment-wide lock on the per-call spend path with budget leases, keep the ceiling strict, size reservations tightly, and stop per-tick metering of internal compute (6.10.3) | Simulation finding SG11; verified lock in `ConversationEnvironmentSpendOwner.cs` |
| RC12 | Add Thread Catalog entries, with Founder authorization, for every paid voice thread and for each WhatsApp template-message category before voice or proactive messages are metered or offered. The catalogue has a text-to-speech subscription entry but no speech-to-text entry priced by audio duration (its Sarvam entry is priced per 1,000 tokens), and no template-message entry, so the cost of transcribing a voice note or sending one of the 30 included proactive messages is not visible | Simulation finding SG10; C-091; AD-015, AD-020; FD16 |

**Walk-throughs (conformance scenarios).**

| # | Case | Result |
|---|---|---|
| 1 | Anonymous WhatsApp visitor asks what DMA does | ACQUISITION |
| 2 | Visitor hands off to web registration | Still ACQUISITION, attributed to the lead |
| 3 | Customer starts a DMA trial | TRIAL on that relationship only |
| 4 | Trial converts to hire | Same relationship and data scope; account changes; leftover trial and setup units lapse |
| 5 | Hired customer asks pre-sales about another agent | ACQUISITION by purpose; focused agent's wallet scope untouched |
| 6 | Customer with two agents sends a request for the other agent | Redirect and ask to switch focus; no agent work charged |
| 7 | A package component reaches its quantity, or wallet credit falls to 85% and then 0 | Disclose and degrade; other agents unaffected; top-up for that agent only |
| 8 | Emergency Stop with wallet credit at 0 | PLATFORM FLOOR |
| 9 | Same agent hired twice (when permitted), and a trial of it | Two relationships plus one trial relationship, each with its own account and data scope |
| 10 | Skill paused mid-period | The fee share allocated to that skill's components is pro-rated; other skills unaffected (component price allocation, 6.11.1 rule 8) |
| 11 | One tenant floods visitors | That tenant's ACQUISITION budget exhausts; others and the breaker are unaffected |
| 12 | Timeout during dispatch | Reservation stays on the account pinned at reserve time |

**6.10.2 Failure modes.** Metered spending fails closed to a zero-cost path, never open to uncounted spend.

| Failure | Behavior | Customer effect |
|---|---|---|
| WBE unavailable | No metered dispatch (no commercial reservation); the agent answers from the free path and, for work that needs paid providers, queues it | "I can plan and answer now; paid work resumes shortly", per B-4 |
| BP breaker unavailable or exhausted | No dispatch that spends money; PLATFORM FLOOR actions continue | Same disclosure |
| CE unavailable | Existing ADR-031 behavior: consequential actions halt, advisory mode continues | Advisory-only disclosure |
| Wallet scope at zero, or component quantity reached | Free path and disclosure; top-up offered where the package allows | Honest limitation (C-049) |
| Outcome unknown after dispatch | Reservation retained on the pinned account until reconciliation | Work shown as unconfirmed, not complete |
| Pricing configuration unavailable | Last authorized pinned version is used; no new package can be authorized | None for existing customers |

**Notifications at capacity thresholds.** WC-134 permits only customer-initiated WhatsApp replies and disables
proactive messages, alerts and templates. Until the Founder lifts that policy for hired customers, capacity notices
(50%, 85%, empty, from `AGENT-BASE-SPEC.md` B-1) are delivered **inside the next conversation turn and as a portal
banner**. Once proactive sending is enabled (FD16), capacity notices and emergency alerts are sent proactively
**without counting against the 30 included messages** and are funded by PLATFORM FLOOR; the exhaustion behavior
itself (disclose, free path) applies in either case.

**6.10.3 Scale of the reservation path.** Today every model and messaging reservation takes one environment-wide
PostgreSQL advisory lock (`pg_advisory_xact_lock` on `environment-spend:{environment}`,
`ConversationEnvironmentSpendOwner.cs` lines 64 and 173), and every component reservation locks its allocation
row. That is correct for a strict INR 500 Demo ceiling but would serialize every customer's spending on one lock
in Production, and the parallel skills of one customer on one row. The target keeps the ceiling strict and
changes where it is enforced:

1. **Leases.** The environment authority grants each Business Platform instance short, bounded budget leases under the lock; per-call reservations draw from the lease without the global lock; an unused lease returns at expiry; the worst overrun is bounded by lease size; an unknown outcome still retains its reservation.
2. **Local contention.** Per-skill sub-wallets and per-relationship scope keep wallet locking local to one customer and one skill.
3. **Tight reservations.** A reservation is sized to the call's real maximum, not a fixed worst case, so a small package credit is not falsely denied.
4. **No per-tick metering of internal compute.** Deterministic internal loops (for example the Trading risk loop every 60 seconds) are metered as a time-based component through the period recipe. Only provider-paid calls reserve and settle individually.
5. **Latency.** Reservation adds time inside the existing Business Platform write-operation target in `slo.md`; the Solution Architect sets the load profile and the exact budget.

The default `continue_silent` for WBE unavailability in `AGENT-BASE-SPEC.md` B-3 predates the commercial
reservation rule and is superseded for metered spending (RC8).

### 6.11 Pricing And Spend Console

**Purpose.** Let a WAOOAW administrator configure billing through an admin login and screens, without code or
SQL, on Demo from the first wave. It is a pricing engine in the sense that the administrator can imagine
(simulate) a configuration before it takes effect, then authorize it. Production prices and budgets are set
through the same console and are not hard-coded anywhere (fitness A16, A19).

**Verified baseline.**

| # | Finding | Evidence |
|---|---|---|
| C1 | WBE has read, validate and derive endpoints for pricing (`GET /thread-catalog`, `GET /bundle-cost-floor`, `POST /validate`, `POST /derive`) and no create or update endpoint for rates, bundles, trial budgets or coupons | `src/billing-engine/markup/router.py`; `trial/router.py` |
| C2 | The thread catalog, bundle profiles, billing profiles and minimum margin live in `institutional.*` tables seeded by SQL | `infrastructure/postgres/init/12-billing-engine.sql` (thread catalog seed, `bundle_profiles`, `billing_profiles`, `constitutional_minimum_margin_pct`) |
| C3 | The specified admin pages (Markup Designer, Trial Budget Config, Coupon Manager) were never built. The only pricing screen is the Founder offerability workbench, which evaluates one proposed price against the margin floor | `customer-acquisition-spec.md` section 7; `web/components/founder/OfferabilityWorkbench.tsx` |
| C4 | Admin and founder route groups with role gating already exist and are the pattern to follow | `web/middleware.ts`; `web/app/(application)/admin`, `web/app/(founder)` |
| C5 | A Demo database reset is an explicit deployment input, and it recreates the databases | `.github/workflows/environment-deployment.yaml` (`reset_demo_database`) |
| C6 | The bundle profile is keyed by (agent type, tier, bundle version). **Agent version is not in the key**, although trials are keyed by agent version. The tier is a short text field and the seed uses Starter, Runner and Winner | `infrastructure/postgres/init/12-billing-engine.sql` `bundle_profiles`; `48-wc112-trial-agent-version.sql` |
| C7 | A bundle states what it contains only as provider units (`thread_rations`: model calls, images, video clips, WhatsApp windows). The customer-facing contents ("30 conversations", "4 reels") exist only as prose. There is no machine-readable deliverable such as "1 post per week" and no link from a deliverable to its cost | `thread_rations` JSON; `dma-bundle-definitions.md` section 3 |

**Configurable objects.**

| Object | Versioned by | Guard |
|---|---|---|
| Thread rates and markup components (raw cost, exchange buffer, overhead, risk premium) per provider account | Rate version | C-091 catalogue entry before any cost |
| Package per agent type and **agent version** (free-form package name), with its components and cost recipes (section 6.11.1): quantities, cadence, selectable dimensions, price, cost floor, margin | Package version | C-088 authorized profile; C-089 price above cost floor, rejected at configuration time |
| Constitutional minimum margin percent | Policy version | Founder only |
| Trial grant per agent version (units per thread, duration) | Grant version | Trial rule FD6 |
| Setup grant per agent version (cap, window) | Grant version | FD1 |
| Acquisition budgets per tenant, campaign and visitor (count and money); environment ceiling | Budget version | Environment ceiling cannot exceed a deploy-time maximum; Demo seeded at INR 500 |
| Alert threshold ladder and default pacing | Policy version | Customer-visible wording stays in agent vocabulary |
| Coupons and referral rules | Campaign version | Discount never below cost floor (C-089) |

**Rules.**

1. Every change is a **draft**, then **simulated**, then **authorized**, then an **effective-dated immutable version** (append-only, DP-005). Nothing is edited in place.
2. Authorizing anything that affects a customer price or entitlement is a **Founder-level act**: C-088 states billing authorization may not be delegated below Founder level. An administrator drafts and simulates; the Founder authorizes. In Demo the same person may hold both roles.
3. Changes apply to new activations and renewals only. Existing customers keep their agreed price (C-090). The rate and package version is pinned at reservation.
4. Every change records the actor, the before and after, and constitutional evidence (CE).
5. The margin floor is enforced when the configuration is saved, with the minimum compliant price returned, not at billing time.
6. **Change-size guard.** A draft that moves a price, rate or ceiling by more than a configured percentage, or prices a package at more than a configured multiple of its cost floor, needs an explicit second confirmation and is highlighted to the Founder. This catches a mistyped price in either direction (the floor already blocks a price that is too low).
7. **Safety-direction changes.** Lowering a ceiling, closing a package to new customers, or disabling a grant takes effect immediately on administrator action and is reported to the Founder. Raising anything, or changing a price or entitlement, needs Founder authorization (decision D16).
8. **Live-margin watch.** When a rate changes or actual cost drifts, the console recomputes every live package at current rates and alerts when one falls below its cost floor or minimum margin. Existing customers keep their price (C-090) and the platform absorbs the gap until renewal, when a notified new price can apply; the Founder decides the response.
9. **Goodwill is given only through discount coupons** (FD15): a coupon reduces a price at hire or renewal, is never below the cost floor (C-089), carries a Founder-set cap and expiry, and records its reason. There is no support-granted wallet credit, so wallet lots stay `PERIOD_CREDIT`, `TOPUP_CREDIT` and platform `GRANT` for trial, setup and acquisition only.

**Package model (6.11.1).** The pricing engine models what the customer buys in four levels, each versioned and
effective-dated:

```text
Agent type  ->  Agent version  ->  Package (free-form name: Starter, Runner, Winner or any other)
                                       |
                                       +--> Components (what the customer sees and is promised)
                                                |
                                                +--> Cost recipe (provider units behind one unit of the component)
```

| Level | Fields an administrator sets | Notes |
|---|---|---|
| Agent version | Agent type, version, status | The key of every package, trial grant and setup grant. Versions differ in features and hiring cost, so a package never applies to another version |
| Package | Package code and display name, billing period, price, tax treatment, status | Any number of packages per agent version; names are data, not an enumeration. The package version changes whenever a price or component changes |
| Component | Component id from the agent declaration, customer-facing label in agent vocabulary, kind, quantity per billing period, optional cadence, optional customer-selected dimension with a cap, core or optional, top-up allowed | The unit the customer sees and is limited by, for example "posts", "ad boosts", "monitored platforms" |
| Cost recipe | The provider units (thread catalogue entries) that one unit of the component consumes | Gives each component a cost, and the package a cost floor equal to the sum of its components plus infrastructure share (C-089) |

Illustration for DMA (names, quantities and recipes are examples for the console, not authorized values):

| Component | Per billing period | Assumed recipe per unit | Indicative cost |
|---|---|---|---|
| Social post | 4 (cadence one per week) | 3 mid-tier model calls and 1 image | 4 x 248 = 992 paise |
| Ad boost (management of the boost, not the ad money) | 1 | 5 mid-tier and 1 frontier model calls | 156 paise |
| Performance monitoring and tuning | 4 customer-selected platforms | 20 mid-tier model calls per platform | 4 x 120 = 480 paise |
| Proactive messages (rule 13) | 30 | Template-message catalogue entry (not yet in the catalogue) | Pending; added to the floor when the entry exists |
| Infrastructure share | flat | catalogue entry | 18,000 paise |
| **Cost floor** (excluding proactive messages until their entry exists) | | | **19,628 paise (INR 196.28)** |

The package price of INR 2,000 includes 18% GST (FD11), so the base price is INR 1,694.92 and the margin on
revenue, before the cost of the 30 proactive messages, is (1,694.92 - 196.28) / 1,694.92, about 88%. The cost floor
and the C-089 margin are always computed on the base price excluding GST.

The unit costs come from the thread catalogue (`llm_mid_gemini` 6 paise per call, `llm_frontier_gemini` 126,
`image_gen_per_image` 230, `infra_share` 18,000). The simulator performs this arithmetic for any draft.

Rules for the package model:

1. **Quantity per billing period is the authority.** Cadence is scheduling guidance. A 30-day period is not exactly four weeks, so the console shows the period length and rejects a cadence whose total over that period contradicts the stated quantity.
2. **Customer-selected dimensions** (such as four social platforms) are a cap plus a customer choice captured during onboarding and validated against the cap. Each selected item is one unit of the component.
3. **The customer's limit is the component quantity**, shown in business language ("2 of 4 posts used"). The wallet holds the matching credit at the pinned recipe cost and acts as the cost guard. Actual cost above recipe cost is absorbed up to a configured tolerance, then the cheaper path is used. The console reports actual cost against recipe cost per component so the administrator can tune recipes and prices.
4. **Ad money is not in the package.** Advertising spend stays a customer-funded pass-through (ADR-026, hard cap AD-016); the package prices only the service of managing it.
5. **Trial substitutions, top-ups and the setup grant** are configured per agent version alongside the package, so a new version starts with its own complete configuration and nothing is inherited silently.
6. A package cannot be authorized unless every component has a recipe and a skill, every recipe thread has a Thread Catalog entry (C-091), the agent version has an authorized billing profile (C-088), every component id exists in that agent version's declaration (section 6.2), and the price exceeds the cost floor by the minimum margin (C-089).
7. **A counted unit is consumed on an owner-confirmed outcome**, not on request or transport acceptance (ADR-051). A failed or retried deliverable does not consume a unit, although its cost still draws on the wallet (absorbed within the tolerance in rule 3).
8. **Component price allocation.** The price of a package is allocated across its components, summing exactly to the package price. This is what makes C-038 pause and terminate pro-rata possible per skill: pausing a skill pro-rates only the fee share allocated to that skill's components.
9. **Pacing prevents front-loading.** Component units are released on the declared cadence (the wallet already supports SPREAD and BURST pacing; packages default to SPREAD), so consumption tracks elapsed time. Strict time-based pro-rata on termination (C-038) therefore cannot be exploited by consuming a whole package early and then stopping.
10. A component delivered by an agent version but absent from the customer's package is not delivered; the agent explains what the package does not include (honest limitation, C-049) and may offer a top-up where allowed.
11. **Component kinds.** Not every deliverable is a counted unit, so rule 7 applies to counted components only.

| Kind | Meaning | Consumption |
|---|---|---|
| COUNTED | Discrete deliverables, for example posts | One unit per owner-confirmed outcome |
| SELECTED | Customer-chosen items up to a cap, for example social platforms | One slot per selected item, occupied while active |
| TIME_ACCESS | A continuous service for the period, for example monitoring and tuning, or risk monitoring | Not counted per use; priced by a per-period recipe |
| CAPACITY | A number of sessions or conversations, for example tutoring sessions | Counted at session close |

12. **Connected items.** A SELECTED item occupies a slot only after its connection (for example OAuth to a social platform, ADR-021) is established and verified; a failed connection consumes nothing. Swapping a selected item is allowed up to a configurable number of times per period.
13. **Proactive messages are included in every subscription: up to 30 per month** (FD16). A proactive message is one the agent starts outside an open customer-service window (so it needs an approved template); a reply inside an open window is not proactive. The 30 form a COUNTED component present in every package, with a cost recipe from the template-message catalogue entries, and are included in the package cost floor. Counting rules: capacity notices (C-051) and emergency alerts (disaster, loss-limit halt, Emergency Stop confirmation) do **not** count, because they are platform obligations funded by PLATFORM FLOOR; agent alerts, reminders and monthly narratives sent proactively do count. After the 30 the agent delivers in the portal and the next conversation turn, and a top-up pack of messages may be offered where the package allows. A trial relationship has none. Enabling any proactive WhatsApp send stays gated by the WC-134 release policy, Meta template approval and a Thread Catalog entry for each template category (RC12).
14. **Sale readiness follows the agent declaration.** Each component carries an availability from the agent version's declaration: `AVAILABLE`, `DEFAULT_OFF` or `UNAVAILABLE`. A package may be priced, simulated and authorized while a component is not available, but it cannot be activated for sale until every component is `AVAILABLE`. The DMA today declares its publication, observation, ad-boost and proactive components as default-off or unavailable (the content-social manifest keeps packages B1 and B2 default-off and publication needs a separate Founder decision), so a DMA package priced like the illustration below is authorizable but not yet sellable.

**Simulator.** A what-if panel computes cost floor, margin and expected monthly cost for each package against
usage profiles taken from the agent budget tables and from simulated-customer runs (section 7), compares the
draft with the current version, and flags any draft below the floor or any persona that would exhaust its wallet
early. This reuses the playground rather than adding a second model of customer behavior. Until hired-customer
simulations exist (W5), the usage profiles come from the agent budget tables and from deliberate best-case and
worst-case profiles (a customer who consumes everything on day one, and one who uses nothing).

**6.11.2 Customer commercial lifecycle.** Packages are only useful if the whole customer journey is defined.

| Moment | Rule |
|---|---|
| Hire | The customer sees the package components, price including GST and period before paying (C-009, C-051). Payment activates a SUBSCRIPTION scope; the wallet is credited with the package's period credit; the trial relationship, if any, converts in place so data continues |
| Renewal | A new period credits a new `PERIOD_CREDIT`; unused credit and component quantities lapse (FD4, FD9). The renewal price is the customer's agreed price unless a change was notified and accepted (C-090) |
| Payment failure | A grace period, then the relationship moves to SUSPENDED (C-034); no new metered work; Stop and data rights remain. The grace length is configuration |
| Upgrade | Takes effect immediately; the fee difference is pro-rated for the remaining period and the new components are credited pro-rata |
| Downgrade | Takes effect at the next renewal unless the customer chooses otherwise; no refund of the current period beyond C-038 |
| Pause or terminate | The subscription fee is pro-rated from that moment (C-038, FD9). Component units delivered stay delivered (no forfeiture of work produced). Remaining wallet credit lapses |
| New agent version | Existing customers stay on the version and package they accepted. The Founder may publish a new version with its own packages; moving is the customer's choice, unless the old version is sunset with notice |
| Package or price change | Applies to new hires and renewals after notice; existing customers keep the agreed price (C-090). A package may be closed to new customers without affecting existing ones |
| Discontinued agent version | A sunset date and notice are Founder decisions (D14); until then the version keeps working |

**Funding and margin dashboard.** The console includes read-only views for the administrator and Founder: spend
per account class, tenant and campaign; cost per lead and per conversation; trial-to-hire conversion; setup
and trial grant consumption; actual versus recipe cost per component with the margin it implies; exhaustion
and top-up events; breaker state. These come from owner projections and the cost telemetry in RC10, not from a
second data store.

**Architecture.** The console is a web admin route group using the existing role pattern, with strong
authentication and step-up for authorization actions, no shared accounts, and complete audit. It calls Business
Platform admin operations through a generated client (BP is the only public facade). BP relays to WBE over the
ADR-046 service boundary with a signed delegated context. WBE is not exposed publicly. No new deployable service.

**Demo.** A baseline pricing version is seeded by the init chain so a Demo reset restores a known state.
Because a reset recreates the databases, the console offers export and import of a pricing version so edits
made on Demo can be restored. The environment ceiling is seeded at INR 500 for Demo.

### 6.12 Ownership

| Responsibility | Owner | Note |
|---|---|---|
| Workbench projection, commands, admin API, account resolver, conversation, environment breaker and leases | Business Platform (BP) | The only public facade (ADR-051) |
| Wallet, packages, components, cost recipes, pricing versions, pro-rata, ledger, commercial projection | WAOOAW Billing Engine (WBE) | Neither WBE nor BP mints the other's permission |
| Constitutional validation and evidence for every authorization and Stop | Constitutional Engine (CE) | |
| Confirmation that a component outcome occurred | Professional Runtime and the domain adapter | Execution truth; the web and the model never confirm |
| Interpretation and generation proposals | AI Runtime (AIR) | Proposes; owners commit |
| Agent experience declaration and component catalogue | Agent owner, per agent version | Admitted immutably |
| Block renderers | Web, the WhatsApp adapter, Mobile | Render semantics; never own history or authority |
| Admin console screens | Web | The authorization act belongs to the Founder |
| Block standard and Domain Block Registry | Enterprise Architect, with Security review | |
| Simulated-customer harness, judge and policy table | Platform IT Expert (INST-010) harness; policy table in BP Conversation Policy | |

## 7. Simulated Customers As The Playground

The generalized playground is a **tenant-scoped sandbox that runs the same BP commands as production in
Trial mode** (B-2: synthetic data, zero-cost models, no wallet deductions, no provider calls), driven by simulated customers.

| Level | What it proves | Oracle | Status |
|---|---|---|---|
| L0 Contract | Schema, versions, fallbacks, tenant isolation | Deterministic tests | Partly exists |
| L1 Channel parity | Identical blocks for identical input across Web, WhatsApp and API | Parity test over fixed transcripts | Exists for visitors (F1 in WC-135) |
| L2 Scripted personas | Regression of known journeys | Rule judge and environment state | Exists (WC-135) |
| L3 LLM personas | Unscripted behavior, dialect and language coverage | Environment state first, LLM judge second | Not built |
| L4 Calibration | The judge agrees with humans | Human-labelled sample of real or consented conversations | Not built |
| L5 Real device | Provider and device reality | Founder or tester on a real phone | Outstanding |

Design rules:

1. **Verifiable tasks first.** Success is read from environment state (goal created, plan accepted, decision recorded), as in tau-bench. The LLM judge scores only style.
2. **Judge derives from policy.** The judge reads the same Conversation Policy table as the product, so STOP acknowledgement cannot disagree (F7, F8). Fix the judge before quoting any safety score.
3. **Reliability, not only success.** Report `pass^k` per persona and per agent, plus run-to-run variance. WC-135 decision O-6 already forbids a target before a baseline.
4. **More than one simulator model**, fixed seeds, persona drift checks and dialect coverage (R7). A result that changes by more than the variation across simulators is not a result.
5. **Per-agent scenario packs** are conformance scenarios in the AEC. Each agent version needs a pack that passes before publication, extending the cross-domain scenarios ADR-051 already requires of DMA, Trading and Tutor.
6. **Safe load.** A concurrency limit and off-hours scheduling (WC-135 limitation 11).
7. **Privacy.** Simulation data stays synthetic. Sampling real conversations stays behind the PII-masking pipeline and consent (WC-135 F-E8).

## 8. Options Considered

| Option | Summary | Verdict |
|---|---|---|
| A. Per-agent, per-channel bespoke experiences | Fastest first screen | Rejected: four agents times three channels is twelve products; drift and inconsistent safety behavior are certain |
| **B. Common kernel, declared experience, closed block vocabulary, tiered extensions** | Section 6 | **Recommended**: builds on ADR-051, ADR-052, WC-135, AD-027 and keeps authority in BP |
| C. Open generative UI (model authors layout) | Maximum flexibility | Rejected for consequential surfaces: conflicts with ADR-051 section 2 and fail-closed governance; revisit as a non-consequential E2 experiment |
| D. Full server-driven UI engine adopted wholesale | Strong cross-platform story | Deferred: block vocabulary and registry give the benefit now; revisit after Mobile, with AG-UI or A2UI as a transport or interchange evaluation (build versus adopt) |

## 9. Roadmap

Each wave has an exit test. Waves are ordered by dependency. The Solution Architect decomposes them into
Work Contracts; Platform IT Expert implements. Nothing below is authorized until the Founder accepts it.

| Wave | Outcome | Exit criteria | Depends on |
|---|---|---|---|
| **W0 Decisions and hygiene** | Founder decisions in section 12; single STOP policy table; judge reads the policy table; `pass^k` added to the compare gate | Judge safety criterion agrees with the product on a fixed STOP, START, YES fixture; parity test covers STOP | Decisions D1, D2 |
| **W1 Contract** | AEC schema (including the component catalogue) and Workbench Projection specification; block vocabulary v2; audiences and modalities; migration plan for the three projections | OpenAPI and schema validated; compatibility scan runs for DMA; candidate ADRs CA1 to CA4 drafted | W0 |
| **W1s Spend accounts** | Spend Account specification and failure table (6.10.2); scale design (6.10.3); RC1 to RC3, RC8 and RC11 (relationship trial authority, configurable ceiling, trial uniqueness bound to identity, B-3 conflict, lease-based reservation); SIMULATION account; resolver design | Specification and OpenAPI validated; walk-throughs written as scenarios; RC5 completed before any generative visitor or onboarding responder | W0, values for FD1 and FD3 |
| **W1w Wallet convergence and commercial lifecycle** | RC4, RC7, RC9, RC10, RC12: one wallet entity with owner, scope and lot kinds; agent-version packages, components (with kinds) and cost recipes as configuration; durable commercial projection and commands; pro-rata; cost telemetry; voice catalogue entries; allocation tables kept as a projection | Parity tests show the projection equals the wallet; no second customer balance table; pro-rata property test (A25) passes; existing Demo customers unchanged | W1s |
| **W1c Pricing And Spend Console (Demo)** | Admin screens and BP admin operations over WBE for the objects in section 6.11: draft, simulate, authorize, effective-dated versions, export and import; seeded Demo baseline | On Demo an administrator drafts a package price, sees the simulator flag a below-floor draft, the Founder authorizes a compliant draft, and a new activation uses it while an existing customer keeps the agreed price; Demo reset restores the seeded baseline and an exported version re-imports; no price, margin, grant or ceiling constant remains in code | W1w |
| **W2 Kernel on DMA** | Workbench API and Web workbench for DMA: Start, Goal and Plan, Decide, Monitor, Evidence; WhatsApp renders P0 and P1 | Parity tests pass; DMA conformance scenarios pass; three old projections serve through the shim | W1 |
| **W3 Prove generality on a paper agent** | AEC and scenario pack for Trading, then Tutor and Agricultural, with no kernel change | Each agent passes its pack without a kernel edit (fitness A1). Any needed kernel edit is a defect in the kernel | W2 |
| **W4 Extensions** | Shared E2 blocks (metric, calendar, document preview, table) and the first E3 surface (Tutor whiteboard) | Security and accessibility review; text fallback verified | W3 |
| **W5 Playground depth** | LLM personas, calibration set, multi-simulator runs, per-tenant sandbox | Judge-to-human agreement measured; variance reported; Founder sets numeric targets | W2 |
| **W6 Mobile** | Mobile client as renderer | No new business endpoint (fitness A3); push meets P0 | W2, W4 |
| **W7 Retire** | Remove the three legacy projections | Zero callers; rollback tested | W2 to W6 |

Prohibited until separately authorized: customer traffic on new surfaces, public web exposure of the
visitor path (WC-135 O-4), E3 surfaces in Production, retiring the legacy projections before W7.

## 10. Architecture Fitness Contract

| # | Fitness function | Threshold | Check |
|---|---|---|---|
| A1 | Adding an agent needs no kernel change | 0 kernel edits for a conforming AEC | Conformance run on Trading, Tutor, Agricultural |
| A2 | Adding a tenant needs configuration only | 0 code or schema changes | Provisioning test |
| A3 | Mobile needs no new business endpoint | 0 new endpoints | API diff at W6 |
| A4 | Channel parity | Identical block set for identical input on every channel that supports the class | Parity test over fixed transcripts |
| A5 | P0 parity | 100% of P0 behaviors present and identical in meaning on every channel | P0 matrix test |
| A6 | Policy is single-sourced | STOP, consent and quiet-hour text defined in one table; 0 copies in channel code or judge | Static guard |
| A7 | Graceful degradation | Unknown block version always renders its fallback | Fuzz test |
| A8 | Tenant isolation of every new resource | 0 cross-tenant reads | Tenant isolation suite (AD-004) |
| A9 | Kernel vocabulary neutrality | 0 profession-specific strings in kernel code | Static guard |
| A10 | Judge validity | Judge agrees with a human-labelled sample at a Founder-set rate | Calibration run |
| A11 | Reliability | `pass^k` reported per persona with variance | Compare gate |
| A12 | Reversibility | Flag off restores prior projections with no data loss | Rollback test |
| A13 | Every metered call has exactly one spend account | 0 calls without an account; 0 calls with two | Ledger reconciliation test |
| A14 | Account pinned at reserve | 0 re-routings after reservation across state changes | Trial-to-hire and timeout tests |
| A15 | Funding isolation | 0 charges to one relationship's wallet scope for another relationship's work; 0 cross-tenant accounts | Walk-throughs 5, 6, 9, 11 |
| A16 | Ceilings are configuration | 0 hard-coded monetary ceilings in code or schema | Static guard |
| A17 | One trial per customer per agent type and version, independent of hires | A second trial of the same type and version is refused; a trial of a new version is allowed; hiring never blocks or consumes a trial | Constraint test |
| A18 | No rollover | 0 credit or component quantity carried across periods | Period-boundary test |
| A19 | No pricing constants in code | 0 prices, margins, rates, grants or ceilings outside versioned configuration | Static guard |
| A20 | Authorization integrity | 0 effective versions without Founder authorization and a passing margin-floor check | Console and API tests |
| A21 | Reproducible charges | Any charge reproducible from its pinned rate, package and wallet versions | Replay test |
| A22 | One wallet entity | 0 customer balance tables outside the wallet ledger after RC4 | Schema guard |
| A23 | Package integrity | 0 authorized packages with a component lacking a recipe, a recipe thread lacking a catalogue entry, or a price at or below cost floor plus minimum margin | Console and API tests |
| A24 | Version isolation | 0 packages, trials or grants resolved for an agent version other than the one they were authorized for | Resolution tests |
| A25 | Price allocation integrity | Component price allocations sum exactly to the package price; pause and terminate refunds equal the time-pro-rated allocation | Property test |
| A26 | No front-loading | A package consumed at maximum speed never exceeds its cadence-released units | Pacing test |
| A27 | Fail closed on metered spend | 0 paid provider calls without a commercial and an operational reservation, including when WBE is unavailable | Fault-injection test (6.10.2) |
| A28 | Audience isolation | A beneficiary or delegate never receives tiles or blocks outside its declared audience, and a beneficiary never receives price or purchase controls | Projection tests |
| A29 | No global lock on the per-call spend path | 0 environment-wide locks per reservation after RC11; ceiling never exceeded by more than one lease | Concurrency test |
| A30 | Reservation latency under load | Reservation stays within its share of the Business Platform write target at the Solution Architect's load profile | Load test |
| A31 | Live-margin watch | Every live package below its floor at current rates raises an alert within one rate change | Rate-change test |
| A32 | Simulation isolation | 0 charges from simulated traffic to ACQUISITION or customer scopes | Account test |
| A33 | Telemetry privacy | 0 personal data fields in spend and cost telemetry | Log-capture test |
| A34 | Proactive allowance enforced | 0 counted proactive messages beyond the included 30 per period without a top-up; capacity notices and emergency alerts never counted and never blocked | Period test |
| A35 | Coupons respect the floor | 0 coupons that take a price below the cost floor; 0 wallet credits created by support | Console and ledger tests |

## 11. Risks And Assumptions

| # | Risk or assumption | Owner | Control |
|---|---|---|---|
| X1 | Three projections converge slowly and the shim lasts too long | Solution Architect | W7 exit criterion and a dated retirement |
| X2 | The kernel is generalized from one implementation (DMA) plus three specifications | Enterprise Architect | W3 proves it before W4 and W6 begin |
| X3 | WhatsApp Flows and list limits are not primary-verified | Platform IT Expert | Primary check before any FORM rendering |
| X4 | The judge keeps being treated as customer truth | Founder | Calibration (A10) and real-device acceptance (L5) |
| X5 | Domain blocks proliferate | Enterprise Architect | Registry review and the promote-to-shared rule |
| X6 | E3 surfaces widen the attack surface | Security | Sandbox, per-tenant disable, no state authority |
| X7 | Minor-protection and financial-risk rules differ per agent | Agent owners | Declared as AEC hard limits and conformance scenarios, not kernel behavior |
| X8 | Assumption: BP stays the only public facade | Enterprise Architect | ADR-051 section 6 |
| X9 | A package priced below real consumption because recipes are wrong | Pricing administrator, Founder | Actual versus recipe cost report, tolerance, simulator worst-case profile, quarterly recipe review |
| X10 | Wallet convergence (RC4) disturbs the WC-134 metering that was just delivered | Solution Architect | Projection with parity tests before retirement; no data loss; flag-off rollback |
| X11 | Admin console becomes a high-value attack target | Security | Step-up authentication, no shared accounts, separation of draft and authorize, full audit, no public WBE exposure |
| X12 | Voice and regional-language parity is assumed, not tested | Agent owners | Modality in the parity matrix and in simulated-customer personas |
| X13 | One person collects several free trials through several accounts | Security, Pricing administrator | Trial eligibility bound to verified identity (RC3); per-identity cap; ACQUISITION abuse controls from WC-135 O-4 |
| X14 | Proactive messaging stays disabled by the WC-134 policy, so agents whose value is proactive (Agricultural alerts, Trading alerts, monthly voice narratives) cannot yet deliver it on WhatsApp even though 30 messages are now included in every subscription | Founder | FD16 decided; activation needs the WC-134 policy change, Meta template approval and catalogue entries (RC12); emergency alerts funded by PLATFORM FLOOR; portal and next-turn delivery meanwhile |
| X15 | A provider price rise erodes margin on live packages that keep their agreed price | Founder, Pricing administrator | Live-margin watch (6.11 rule 8, A31), renewal repricing with notice, quarterly recipe review |

## 12. Founder Decisions Needed

| # | Decision | Recommendation |
|---|---|---|
| D1 | Acknowledge STOP on every channel (including WhatsApp), or stay silent everywhere. The answer becomes the single policy table. | Closed 2026-11-20 by Founder (FD17): acknowledge STOP once on every channel, including WhatsApp, with the START instruction. The outbox currently refuses delivery to a stopped recipient, so this needs a deliberate, narrowly scoped exception, plus a privacy and provider-policy check before activation on a live number |
| D2 | Accept the common kernel (K1 to K9) and the extension tiers E0 to E3 as the direction | Closed 2026-11-20 by Founder: accepted as the direction for Solution Architect decomposition |
| D3 | Capability map: name a channel-neutral experience capability alongside 6.6, and a capability for configuring pricing and platform-funded spend, or leave both implicit | Closed 2026-11-20 by Founder: two entries added to `knowledge/business-capabilities.md` as 6.8 (channel-neutral workbench) and 6.9 (pricing and platform-funded spend), as WC-135 O-1 did for 1.9 and 13.9 |
| D4 | Adopt AG-UI or A2UI as transport or interchange, or keep the in-house block schema | Closed 2026-11-20 by Founder: keep the in-house block schema; evaluate AG-UI for streaming only |
| D5 | Which agent proves the kernel second, after DMA | Trading (clear limits and cadence, an adapter already exists) |
| D6 | LLM simulator and judge model policy and budget | Free or low-cost models first, per AI Resource Governance; Founder sets the budget |
| D7 | Whether Work Contracts are drafted by the Solution Architect from this document | Yes, one per wave from W0 |
| D8 | Wallet lot kinds are `PERIOD_CREDIT`, `TOPUP_CREDIT` and `GRANT`, all non-refundable and non-rolling (FD9); counsel review of the word "wallet" before Production | Confirmed by Founder 2026-11-20 apart from the review |
| D9 | Who authorizes prices and budgets in the console: Founder only (C-088), or a delegated administrator | Closed 2026-11-20 by Founder (FD10): an administrator drafts and simulates; only the Founder authorizes; on Demo one person may hold both roles |
| D10 | Reconcile "nothing refundable" with C-038 and ADR-026 | Closed 2026-11-20 by Founder (FD9): wallet credit stays non-refundable; the subscription fee is pro-rated on pause or termination (C-038); leftover ad-spend money is refunded as ADR-026 specifies |
| D11 | Is a package price entered including or excluding GST, for example "INR 2,000 per month" | Closed 2026-11-20 by Founder (FD11): the entered price is the customer-facing price including GST; the console derives and shows base price, GST and margin |
| D12 | Is the customer's limit counted in components ("4 posts") with the wallet as cost guard, or only in money | Closed 2026-11-20 by Founder (FD12): components are the limit, wallet is the guard (section 6.11.1 rule 3) |
| D13 | May one customer hire the same agent version more than once, and does each hire get its own setup grant | Decide later, as the Founder said; design is ready (6.10) |
| D14 | Commercial lifecycle defaults (6.11.2): payment grace period; upgrade immediate with pro-rata; downgrade at renewal; sunset notice length for a discontinued agent version | Closed 2026-11-20 by Founder (FD18): confirmed; the grace period and sunset notice length are set in the console |
| D15 | Tolerance for actual cost above recipe cost before the cheaper path is used (6.11.1 rule 3), and the cost-variance level that alerts the administrator | Closed 2026-11-20 by Founder (FD19): set per component in the console; Demo is seeded with 20 percent over recipe cost as the tolerance and an alert at 10 percent |
| D16 | Safety-direction changes (lower a ceiling, close a package to new customers, disable a grant) take effect on administrator action and are reported; raising or price changes need the Founder | Closed 2026-11-20 by Founder (FD14): yes |
| D17 | Goodwill credit: who may grant support credit and the limit per case and period | Closed 2026-11-20 by Founder (FD15): goodwill is given only through discount coupons; there is no support-granted wallet credit |
| D18 | Proactive WhatsApp messages and templates (capacity notices, Agricultural and Trading alerts, monthly narratives) and who pays for them | Closed 2026-11-20 by Founder (FD16): every subscription includes up to 30 proactive alerts or messages per month (rules in 6.11.1 rule 13); enabling them remains gated by the WC-134 policy and template approval |

### 12.1 Founder Decisions Recorded 2026-11-20

| # | Decision | Status |
|---|---|---|
| FD1 | The onboarding interview is funded by a bounded platform setup grant, one time per relationship, so each hire receives its own. Cap and time window are set in configuration | Decided; cap and window values pending Founder |
| FD2 | A customer-level envelope is deferred | Decided |
| FD3 | The production acquisition budget is configurable; Demo remains INR 500 | Decided; production values pending |
| FD4 | Unused wallet credit of a hired agent does not roll over | Decided |
| FD5 | A customer works with one agent at a time; each turn is charged to the focused agent's relationship; other-agent requests are redirected to an explicit focus switch | Decided |
| FD6 | Trial is independent of hire status: at most one trial per customer per agent type and version, and a customer who has hired that agent version can still take that one trial. Versions differ in features and hiring cost, so trial and hire are always considered per version | Decided |
| FD7 | WBE keeps one entity with its literal and legal meaning, the Wallet; allowance is not a separate entity | Decided |
| FD8 | Production budgets and package prices are configurable through an admin login and screens (a pricing engine that lets WAOOAW fine-tune billing), available on Demo itself | Decided |
| FD9 | No wallet balance is refundable and none rolls over to the next period. On pause or termination the **subscription fee** is pro-rated (C-038) as a billing adjustment, not a wallet refund. Leftover ad-spend money remains an exception and is refunded as ADR-026 specifies | Decided |
| FD10 | An administrator drafts and simulates prices and budgets; only the Founder authorizes them; on Demo one person may hold both roles | Decided |
| FD11 | The entered package price is the customer-facing price including GST; the console shows base price, GST and margin | Decided |
| FD12 | The customer's limit is the component count (for example 4 posts); the wallet is the cost guard | Decided |
| FD13 | The pricing engine models Agent, agent version, hire package (free-form name such as Starter, Runner, Winner) and a component breakup (for example DMA Starter at INR 2,000 per month: 1 post per week, 4 posts in total, 1 ad boost, monitoring and tuning for 4 customer-selected social platforms) | Decided; model in section 6.11.1 |
| FD14 | Safety-direction changes (lower a ceiling, close a package to new customers, disable a grant) take effect on administrator action and are reported to the Founder; raising anything or changing a price needs the Founder | Decided |
| FD15 | Goodwill is given only through discount coupons; support cannot grant wallet credit | Decided |
| FD16 | Every subscription includes up to 30 proactive alerts or messages per month | Decided; counting rules in 6.11.1 rule 13; activation gated by the WC-134 policy and template approval |
| FD17 | STOP is acknowledged once on every channel, including WhatsApp, with the START instruction | Decided; live-number activation needs a privacy and provider-policy check |
| FD18 | Commercial lifecycle: payment grace period set in the console; upgrade immediate with pro-rata; downgrade at next renewal; sunset notice length set in the console | Decided |
| FD19 | Actual cost above recipe cost is tolerated per component up to a console-set limit; Demo is seeded at 20 percent tolerance and a 10 percent alert | Decided |

## 13. Candidate ADRs And Handoff

Titles only; none is written or accepted. Next free number is 054.

| Candidate | Subject |
|---|---|
| CA1 | Agent Experience Contract as part of the Employment Interface Conformance Manifest, including the component catalogue, audiences and modalities |
| CA2 | Workbench Projection consolidating the three workspace projections |
| CA3 | Experience block vocabulary, versioning, fallback and channel capability negotiation |
| CA4 | Extension tiers E0 to E3 and the Domain Block Registry |
| CA5 | Channel-neutral protocol policy (STOP, consent, quiet hours) and judge derivation |
| CA6 | Simulated-customer evaluation standard (`pass^k`, calibration, simulator diversity) |
| CA7 | Spend Account model: account classes, resolver, pin-at-reserve, failure table, configurable ceilings, trial uniqueness (sections 6.10 and 6.10.2) |
| CA8 | Single Wallet entity with owner, scope and lot kinds; retirement of the allocation tables (section 6.10.1) |
| CA9 | Pricing and Spend Console and package model: versioned, Founder-authorized billing configuration; commercial lifecycle (sections 6.11 to 6.11.2) |

**The Solution Architect may decompose:** waves W0 to W7 including W1s, W1w and W1c, the API table in section 6.3,
the block vocabulary in section 6.4, the AEC schema in section 6.2, and the package model in section 6.11.1.
**Remains prohibited or owner-decided:** every open decision in section 12, primary verification of provider
limits, Production use of E3 surfaces, any change to Employment Relationship lifecycle (C-034), and any new
deployable service.

## 14. Sources

Internal: see Record Control "Reads". External:

- Google Developers, A2UI and MCP Apps: https://developers.googleblog.com/en/a2ui-and-mcp-apps/
- AG-UI overview: https://docs.ag-ui.com/introduction
- tau2-bench: https://proceedings.mlr.press/v306/barres26a.html
- Microsoft Agent 365: https://www.microsoft.com/en-us/copilot/blog/2025/11/18/microsoft-agent-365-the-control-plane-for-ai-agents/
- Microsoft Foundry and Agent 365: https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/foundry-control-plane-and-agent-365-two-control-planes-walk-into-an-enterprise/4520185
- Magentic-UI: https://www.microsoft.com/en-us/research/blog/magentic-ui-an-experimental-human-centered-web-agent/
- Salesforce Agentforce Testing Center: https://www.salesforce.com/blog/agentforce-testing-center/ and https://help.salesforce.com/s/articleView?id=005228642&language=en_US&type=1
- AWS Agentic AI Lens, multi-tenancy: https://docs.aws.amazon.com/wellarchitected/latest/agentic-ai-lens/agentperf07.html and `agentperf07-bp01.html`
- Lost in Simulation (ACL 2026): https://aclanthology.org/2026.acl-long.2192/
- The Illusion of Intervention: https://arxiv.org/html/2605.20767
- Meta, interactive reply buttons (primary): https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/interactive-reply-buttons-messages
- WhatsApp interactive message guides (secondary): https://monochat.ai/blog/whatsapp-interactive-messages, https://usetenashi.com/blog/whatsapp-interactive-messages
- Server-driven UI (secondary): https://frenchydigital.com/blog/server-driven-ui-mobile-apps-2026, https://mvpfactory.io/blog/server-driven-ui-for-mobile-apps-json-schema-contracts-component-registries-and

## 15. Author Review

Performed by the Enterprise Architect against the assignment, the office quality gate and the obligation ledger.

| # | Check | Result |
|---|---|---|
| 1 | Every component traces to an existing capability, driver, claim or accepted ADR | Pass. Capability gap for channel-neutral rendering is flagged as D3, not invented |
| 2 | No technology selected without an ADR | Pass. AG-UI and A2UI are deferred to D4; candidate ADRs are titles only |
| 3 | Failure, observability and fitness defined for each consequential boundary | Pass. Fitness A1 to A28; failure table in 6.10.2; degradation through fallback blocks, the P0 rules and per-account exhaustion behavior |
| 4 | Assumptions have owners | Pass. Section 11 |
| 5 | Reversibility | Pass. Flag-off with legacy projections retained until W7 (A12) |
| 6 | Claims are supported | Pass with limits. Counts and paths are from the repository at the baseline commit. Section 4 findings are from the sources listed; secondary sources are labelled and R8 lists what still needs primary verification |
| 7 | Known limitations | Only DMA is implemented, so the kernel is a hypothesis until W3. Judge defect F8 second symptom (consent after START and YES) is the Founder's report and was not independently reproduced here. Web UI behavior was assessed from code, not from a running Demo |

Author review is self-verification, not approval. Submission to the Founder is the next step.

Section 6.10 limits: spend findings S1 to S6 and console findings C1 to C7 come from reading code and
specifications, not from a running Demo; production prices, budgets and grant values are not set; the legal
treatment of wallet balances is unreviewed; the walk-throughs are design checks, not test results.

### 15.1 Critical review dispositions (2026-11-20)

A second pass as Enterprise Architect against the whole document found and repaired the following.

| # | Gap found | Repair |
|---|---|---|
| G1 | Identifier collisions: findings, Founder decisions and required changes all used F and R | Founder decisions are FD, required changes RC, candidate ADRs CA; findings F and research R keep their prefixes |
| G2 | Terminology drift after the wallet decision: allowance, bundle and ration mixed with wallet, package and component | Terms table in 6.10; text, tables and fitness checks updated |
| G3 | Unit-at-pinned-rate wording contradicted FD12 (customer limit is components) | 6.10.1 rewritten: components are the customer view, wallet credit at recipe cost is the guard |
| G4 | AEC had no component catalogue, so a package could price something the agent cannot deliver | `components`, `audiences` and `modalities` added to 6.2; package rule 6 requires the component id to exist |
| G5 | No rule for when a component unit counts, for per-skill pro-rata price allocation, or against front-loading | Package rules 7 to 9 and fitness A25, A26 |
| G6 | Customer commercial journey (hire, renewal, payment failure, upgrade, downgrade, version change, sunset) undefined | 6.11.2 and decision D14 |
| G7 | No customer or administrator API for packages, wallet, top-ups, subscriptions | Rows added to 6.3 |
| G8 | B-3 "WBE unavailable: continue silently" contradicts the commercial reservation rule | Failure table 6.10.2, RC8, fitness A27 |
| G9 | Voice-first agents and non-owner audiences (student, delegate) not modelled | Voice modality in 6.6; audiences in 6.2 and 6.3; fitness A28; risk X12 |
| G10 | Multi-hire was stated as designed rather than as a later decision | 6.10 reworded; decision D13 |
| G11 | Wallet convergence and commercial lifecycle had no wave | W1w added |
| G12 | Admin console security, audit, dashboards and the offline usage-profile limit not stated | 6.11 Architecture and Simulator paragraphs; funding and margin dashboard |

Second pass (same day), after the first simulation:

| # | Gap found | Repair |
|---|---|---|
| G13 | The capability map has no entry for configuring pricing and platform-funded spend | Flagged in section 2 and decision D3; no capability invented |
| G14 | "Tenant" was ambiguous for visitors who belong to no customer tenant | Terms table: marketplace tenant owns ACQUISITION; one-way opaque lead link on registration |
| G15 | The per-call spend path serializes on one environment-wide lock (verified in code) | 6.10.3 leases, RC11, fitness A29 and A30 |
| G16 | Components were all treated as counted units, which does not fit continuous services, selected items or sessions | Component kinds and connected-item rules (package rules 11 and 12) |
| G17 | Simulated traffic shared the live acquisition pool | SIMULATION account class and fitness A32 |
| G18 | No guard against a mistyped price, no immediate safety-direction control, no live-margin watch, no goodwill credit | Console rules 6 to 9; decisions D16 and D17; fitness A31 |
| G19 | Ownership of each responsibility not stated in one place | Section 6.12 |
| G20 | Beneficiary (student) exhaustion behavior and spend visibility undefined | Rule after the audience paragraph in 6.3; fitness A28 |
| G21 | Trial eligibility keyed to an account allows several trials per person; lead telemetry could carry personal data; voice thread costs uncatalogued; proactive messaging dependency for alert-driven agents | RC3 identity binding and risk X13; RC10 pseudonymous leads and fitness A33; RC12; decision D18 and risk X14 |

## 16. Simulation Run

**Method.** A design walk-through ("tabletop simulation"): each step of a journey is traced against the target
design and checked against what the repository does today. It is not an executed system test; it identifies steps
that would fail or are undefined. The actors are a visitor and customer (Priya, a boutique owner hiring the DMA),
and an administrator and the Founder. "Today" statements are verified from code and specifications read for this
document. Findings SG1 to SG8 are listed at the end with their repairs.

### 16.1 Customer and visitor journey

| # | Step | Target behavior | Today | Result |
|---|---|---|---|---|
| C1 | Visitor on WhatsApp asks what WAOOAW does | ACQUISITION account, scripted or generative within tenant, campaign and visitor caps | Scripted; count limits and a shared INR 500 ceiling; no cost per lead | Works; cost attribution missing (SG5, RC10) |
| C2 | Visitor sends STOP, later START | One policy table, acknowledgement on every channel | API acknowledges, WhatsApp is silent, judge expects silence | Gap; D1 and CA5 |
| C3 | Taps the handoff link to register on the web | Single-use reference, non-sensitive prefill, identity-matched linking | Reference and tap recorded; prefill and identity-matched linking not built (WC-135 limitation 5) | Gap noted for W2 (SG8) |
| C4 | Browses the DMA card and its packages | Package components, GST-inclusive price and period readable by a machine | Packages exist only as prose; no `GET packages` | Gap; RC7, W1w |
| C5 | Starts the DMA trial | TRIAL scope on this relationship only; free model tier; one trial per customer, agent type and version | Customer-level Redis mode flag; `trial_entitled` has no callers | Defect; RC1 |
| C6 | Onboarding interview | SETUP GRANT pays; trial or subscription is untouched | No setup grant; interview would draw on the trial ledger | Gap; resolved by the SETUP GRANT rule in 6.10 (SG1), RC5 |
| C7 | Hires the Starter package (INR 2,000 including GST) | Sees components and price first; pays; wallet credited with the package's recipe cost; trial relationship converts in place | Paid activation and renewal exist; no components, no recipe sizing | Partial; W1w |
| C8 | Sets goal and plan in conversation, adjusts in a form | Goal and plan primitives on every channel | No goal editor; phase counts only (F4) | Gap; W2 |
| C9 | Week 1 post delivered | Unit counted on owner-confirmed outcome; "3 of 4 posts left"; wallet charged at recipe cost | Usage counted per model-generation component; no deliverable-level count; budget view is a placeholder | Gap; RC7, rule 7 |
| C10 | Asks for a fifth post | Honest limitation, top-up offered where allowed | Top-up orders exist in reconciliation; not tied to components | Gap; rule 10 |
| C11 | Package nears its limit while the customer is away | Notice in the next turn and a portal banner; WhatsApp push only if proactive templates are approved | WC-134 disables proactive WhatsApp | Rule added to 6.10.2 (SG2) |
| C12 | Pauses one skill, then terminates on day 12 | Skill's fee share, then the whole fee, pro-rated; no wallet refund; delivered work kept | Renew and terminate commands return BLOCKED; no pro-rata code in WBE; commercial commands held in process memory | Gap; RC9 (SG4, SG6) |
| C13 | Works with a second agent | Explicit focus switch; charges follow the focused relationship | Interaction context supports selection | Works in design |
| C14 | Sends STOP with credit at zero | PLATFORM FLOOR; always executes | Constitutional exemption specified | Works in design |
| C15 | Renewal payment fails | Grace, then SUSPENDED; Stop and data rights remain | Not defined in WBE | Gap; D14 |
| C16 | A new agent version is published | Customer stays on the accepted version unless they move | Not defined | Rule added in 6.11.2; D14 |

### 16.2 Administrator and Founder journey

| # | Step | Target behavior | Today | Result |
|---|---|---|---|---|
| A1 | Administrator signs in to the console on Demo | Role-gated admin route group with step-up | Admin and founder route groups exist; no pricing screen | Gap; W1c |
| A2 | Edits a provider rate | Draft, simulate, authorize, effective-dated version | Rates are SQL seed data; no write path | Gap; W1c |
| A3 | Builds DMA v3.0 Starter: components, recipes, price INR 2,000 | Component ids come from the agent declaration; allocation sums to the price | No components, recipes or allocation | Gap; RC7 |
| A4 | Simulates | Cost floor INR 196.28, base INR 1,694.92, margin about 88%; flags below-floor drafts; worst-case profile (everything on day 1, then terminate) | Derive and validate endpoints exist for one price | Partial; margin must use the ex-GST base (SG3, repaired) |
| A5 | Founder authorizes | Sees diff, floor, margin, billing-profile gate and agent-spec gate; step-up; evidence recorded | Founder offerability workbench checks one price only | Gap; W1c |
| A6 | Changes a live package price | New version from next renewal; existing customers keep the agreed price and are notified | Not implemented | Gap; 6.11.2 |
| A7 | Sets the environment ceiling (Demo INR 500, production value) | Configuration within a deploy-time maximum | Constant `500` in code and database check at 50,000 paise | Defect; RC2 |
| A8 | Tunes trial and setup grants per version | Versioned configuration | No setup grant; trial budgets in SQL | Gap; W1c |
| A9 | Demo is reset | Seeded baseline restored; exported version re-imported | Reset recreates databases | Covered in 6.11 |
| A10 | Reviews funding and margin | Dashboard: cost per lead, conversion, actual versus recipe | None | Gap; RC10, dashboard in 6.11 (SG5) |
| A11 | WBE is unavailable | Fail closed to the free path; alert raised | Reservation required by WC-134; B-3 says continue | Conflict repaired; RC8, A27 |
| A12 | Audit asks why a customer was charged INR X | Reproduce from pinned rate, package and wallet versions | Pinned versions not recorded per charge | Gap; A21 |
| A13 | Founder asks what 1,000 generative visitor conversations cost | Per-conversation cost from ACQUISITION telemetry | Visitor path has no spend telemetry | Gap; RC10 |

### 16.3 Findings and repairs

| # | Finding | Repair |
|---|---|---|
| SG1 | A trial relationship could draw both trial units and a setup grant for the same interview turn | Onboarding turns draw only the SETUP GRANT; trial funds work (6.10 resolver) |
| SG2 | Capacity notices assumed proactive WhatsApp, which WC-134 disables | Notices go in the next turn and the portal; proactive only after Founder approval (6.10.2) |
| SG3 | The illustration compared cost to a GST-inclusive price | Margin and floor are computed on the ex-GST base (6.11.1) |
| SG4 | WBE commercial projection and commands are in process memory (`relationship_workspace.py` lines 227 to 228) and renew and terminate return BLOCKED | RC9 makes them durable and implements the lifecycle under approved policy |
| SG5 | No cost telemetry per conversation, lead or account | RC10 and the dashboard |
| SG6 | C-038 pro-rata is ratified but no pro-rata computation exists in WBE | RC9 with component price allocation and fitness A25 |
| SG7 | Payment failure, grace and version migration undefined | 6.11.2 defaults and D14 |
| SG8 | Visitor-to-registration prefill and identity-matched linking not built | Carried into W2 acceptance |

**Result.** Of 29 steps (16 customer, 13 administrator): 3 already hold in design or today (C13, C14, A9), 3
are partial (C1, C7, A4), 4 were undefined or in conflict and are repaired in this document (C6, C11, C16, A11),
and 19 need implementation, each now assigned to a wave (C2, C3, C4, C5, C8, C9, C10, C12, C15, A1, A2, A3,
A5, A6, A7, A8, A10, A12, A13). Two of those are defects in current code rather than missing features (C5 and
A7). No step is undefined in the design after the repairs above. The run does not show that the system works;
it shows the design is complete enough for the Solution Architect to decompose, and which current behaviors
must change first (RC1, RC2, RC8, RC9).

### 16.4 Second simulation round (same day)

The second round deliberately uses scenarios the first did not: agents of different shape, scale, money risk,
abuse, and test traffic. Each row names the gap it exposed and where it is repaired.

| # | Scenario | What the walk-through exposed | Repair |
|---|---|---|---|
| S1 | Tutor: a parent hires, the student uses sessions and the whiteboard; credit runs out mid-session | The student could be shown price or top-up controls; no beneficiary rule | Beneficiary rule in 6.3, CAPACITY kind, fitness A28 |
| S2 | Agricultural: a farmer sends WhatsApp voice notes, never opens the portal, depends on daily alerts | Speech-to-text cost not visible in the catalogue; proactive alerts blocked by the WC-134 policy | RC12; decision D18; risk X14; emergency alerts on PLATFORM FLOOR |
| S3 | Trading: five skills run in parallel, a risk loop ticks every 60 seconds, a loss limit halts trading | Per-tick reservation would cost more than the work and contend on one wallet row | 6.10.3 rule 4 (no per-tick metering), TIME_ACCESS kind, PLATFORM FLOOR for the halt alert |
| S4 | The model provider raises its price 30% mid-week; live packages keep their agreed price | Nothing detects margin erosion on live packages | Console rule 8, risk X15, fitness A31 |
| S5 | An administrator types INR 20 or INR 200,000 instead of INR 2,000 | Below-floor is blocked; a mistyped high price was not | Console rule 6 |
| S6 | Founder demonstrates to a prospect while simulated customers run | Both draw on the same INR 500 pool; the earlier run already starved the shared connection pool | SIMULATION account, fitness A32 |
| S7 | A campaign sends 5,000 visitors in an hour while 500 customers work | One environment-wide lock serializes every reservation | 6.10.3, RC11, fitness A29 and A30 |
| S8 | One person opens five accounts to take five DMA trials | Trial keyed to an account, not a person | RC3 identity binding, risk X13 |
| S9 | A customer says a post failed and asks for compensation | No sanctioned way to give a credit | Console rule 9, decision D17 |
| S10 | The Founder wants cost per lead | Telemetry could carry phone or name | RC10 pseudonymous reference, fitness A33 |
| S11 | The customer's social platform connection fails during onboarding | A failed connection might consume a slot | Package rule 12 |
| S12 | A visitor registers and becomes a customer | Visitor data and customer data sit in different tenants | Terms table: marketplace tenant and one-way opaque link |
| S13 | The Founder authorizes a price in the console | The capability map has no entry covering this act | D3 extended; no capability invented |
| S14 | The Founder is unreachable during an incident | A runaway budget cannot wait; raising anything must still wait | Console rule 7, decision D16 |

**Result of the second round.** All 14 scenarios exposed a gap in the design or an unassigned dependency; each is now
repaired in the document, and most of them add implementation work to a wave (RC3, RC10, RC11, RC12, the
beneficiary projection, the SIMULATION account and console rules 6 to 9). Across both rounds 43 steps were walked
and none remains undefined in the design. None of this shows the
system works; it shows what the Solution Architect must decompose and what the Founder must still decide
(D1, D3, D13 to D18, plus the production values of prices, budgets and grants).

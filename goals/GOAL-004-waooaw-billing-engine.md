# GOAL-004 — WAOOAW Billing Engine

**Goal ID:** GOAL-004
**Status:** IN_UNDERSTANDING → PLANNED
**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-07-30
**Goal Orchestrator Session:** 2026-07-30 (INST-013 — human session with Founder)
**Reviewer:** Constitutional Analyst (INST-002)

---

## Goal Statement (as registered)

> "Design and implement the WAOOAW Billing Engine — the bilateral cost-and-revenue
> infrastructure that makes every WAOOAW product commercially sustainable,
> prepaid-enforced across all constrained resources, operationally autonomous,
> and extensible to any future agent without a code change."

---

## Goal Understanding Record

*Produced by: Goal Orchestrator (INST-013) — 2026-07-30*

### What This Goal Actually Means

The Founder's statement contains four distinct obligations. Understanding them separately
prevents misrouting to the wrong institutions.

**"Bilateral"** means this Goal must work on two ledger sides simultaneously:
- Side A — Customer Revenue: how WAOOAW charges customers (subscriptions, wallets, top-ups)
- Side B — Platform Procurement: how WAOOAW tracks what it pays to providers (LLM APIs, video
  generation, WhatsApp BSP, ad networks)
  
Today Side A is partially built (Razorpay subscriptions, ad_spend_wallets, GST invoices).
Side B does not exist. A billing system with only Side A is commercially blind — WAOOAW
cannot calculate margin, detect cost overruns, or project procurement needs.

**"Prepaid-enforced across all constrained resources"** means the prepaid principle —
which today applies only to ad spend (ad_spend_wallets must be funded before campaigns run) —
must extend to every variable-cost thread: LLM tokens, video generation credits, WhatsApp
conversation windows, image generation. No WAOOAW service fires unless the customer has
confirmed capacity in their wallet bucket for that resource.

This is not a feature — it is a constitutional insurance principle. Customer default on
variable costs is eliminated by making every resource access a balance check, not a
post-hoc invoice.

**"Operationally autonomous"** means the billing engine runs without human intervention
under normal conditions. This covers: daily projections of both customer wallet depletion
and platform procurement depletion, threshold-triggered alerts (50%/60%/85%/95%) to
customers via WhatsApp, proactive top-up offers, progressive renewal failure handling,
and automatic Founder Action generation when WAOOAW's own provider accounts are running
low. Humans intervene only for exceptions and pricing decisions.

**"Extensible to any future agent without a code change"** means the engine is
agent-agnostic. When WAOOAW adds a new agent (Restaurant, Legal, Healthcare), the billing
system configuration is updated via an Agent Billing Profile document — not a code deployment.
The Thread Catalog and Bundle Profile system must accommodate any new combination of
platform threads (LLM, WhatsApp) and agent-specific threads (domain data APIs, specialized
generation tools) through configuration alone.

### What This Goal Is NOT

- Agency billing (multi-tier wallet management, Model A–D) → GOAL-AGENCY in backlog
- White-label / reseller pricing tables → GOAL-AGENCY
- VMP2–VMP6 ad funding mode implementation → future DMA release cycle iterations
- Bundle implementation for Trading, Agricultural, Private Tutor agents → those agents'
  own future sprints (profiles are produced here; bundles are not implemented here)
- This Goal closes at approved specs + autonomous sprint execution plan (D-10).
  Code delivery is the autonomous pipeline's responsibility, not this Goal's.

### Key Design Decisions Confirmed During Understanding

| Decision | Resolved |
|---|---|
| Wallet architecture | One wallet per customer, multiple reservation buckets |
| Bundle naming | Starter / Runner / Winner (applies per agent type) |
| Pacing model | Customer choice at period start (spread vs burst) — WAOOAW does not decide |
| Top-up model | Three types: resource unit top-up, event pack, auto-refill authorization |
| Proactive offers | WBE projects depletion velocity and offers top-ups before customer runs out |
| Trial mode | Zero-cost API substitution for all threads — no bundle consumption |
| Onboarding payment | Single Razorpay transaction activates subscription + seeds wallet |
| Grandfather pricing | Customer's contract price is locked — changes apply only at renewal with 30-day notice |
| Minimum margin | Constitutional floor enforced computationally — no offering priced below it |
| Thread Catalog authority | Every billable cost must be in Thread Catalog before it can be charged or absorbed |
| Agency model scope | Design must leave all data structures agency-model-ready — zero closed doors in schema |

### Operational Scenarios That Must Be Satisfied

The following 17 scenarios were identified in the Understanding phase. Any spec or
implementation that cannot handle these has failed the understanding requirement.

| # | Scenario | Resolution Path |
|---|---|---|
| S-01 | Midnight campaign surge — quiet hours alert policy | Threshold-to-action mapping: 30%=hold during quiet hours, 5%=pause regardless |
| S-02 | New month zero gap — wallet below minimum at renewal | WBE checks minimum operating threshold at renewal; sends refill prompt Day 1 |
| S-03 | Week-1 LLM blowout — bucket empty, 20 days remain | Graceful degradation: ZERO_COST path + customer-visible explanation + upsell |
| S-04 | WhatsApp window trap — window cost varies by behavior | WhatsApp windows are a metered bucket; agent adjusts verbosity at 85% |
| S-05 | WAOOAW procurement crisis — Kling AI account running low | Platform Procurement Ledger: days-remaining projection; auto-FA generation at <7 days |
| S-06 | Margin inversion — heavy user exceeds cost floor | Bundle caps are the primary protection; Markup Engine derives price from ration floor |
| S-07 | FX shift — USD-denominated threads cost more | FX buffer built into thread markup %; monthly reconciliation feeds Markup Engine |
| S-08 | Mid-month bundle upgrade — pro-rata ration calculation | Pro-rata rations: remaining days × (new bundle ration / period days) + carry-forward |
| S-09 | Trial-to-paid race condition — 4-second activation gap | Mode switch on payment_intent CONFIRMED, not subscription object creation |
| S-10 | Pause cascade — saga with external provider | Temporal saga: Meta campaign pause is Gate 1; billing state does not change until confirmed |
| S-11 | New agent launch — zero code change required | Agent Billing Profile → WBE reads config; Razorpay plans auto-created via API |
| S-12 | Cross-agent thread contention — two agents share LLM | Customer choice at multi-agent enrollment: separate allocations vs shared pool |
| S-13 | Dormant customer re-engagement | Re-engagement Brief: what changed, grandfather price confirmed, wallet status |
| S-14 | Failed renewal cascade — 3 retries over 7 days | Progressive Response Policy: Day 1 alert → Day 3 reduced mode → Day 7 suspension saga |
| S-15 | Skill activation mid-period — thread requirements exceed bundle | WBE presents choice: degrade gracefully with disclosure vs top-up vs upgrade |
| S-16 | Agency velocity anomaly — child drains shared wallet | Per-child spending quota configurable at agency enrollment; velocity alert on 2× avg |
| S-17 | Thread pricing change — existing subscriptions protected | Grandfather pricing preserved; new subscribers on new price; 30-day notice constitutional |

### New Constitutional Claims This Goal Surfaces

The following claims do not yet exist and must be ratified before implementation:

| Claim ID | Title | Statement |
|---|---|---|
| C-088 | Agent Billing Profile Requirement | No WAOOAW agent may be published to customers without a Founder-authorized Agent Billing Profile. An agent without a Profile is constitutionally unpublishable regardless of how complete its agent specification is. |
| C-089 | Constitutional Minimum Margin Floor | The final offering price for any WAOOAW product must exceed the bundle cost floor by at least the Founder-set minimum margin %. No agent, bundle, or top-up may be priced below this floor. WBE enforces this computationally; the Founder sets and may revise the floor % via Founder Action only. |
| C-090 | Grandfather Pricing Protection | A customer's subscription price may not increase during an active contract period. Price changes apply only at renewal and require 30-day advance notice. This notice is a constitutional act recorded in the audit ledger with customer acknowledgment, not a marketing communication. |
| C-091 | Thread Catalog Sovereignty | Every billable cost incurred by WAOOAW in service delivery must have an entry in the Thread Catalog before that cost may be absorbed or charged to any customer. Costs outside the Thread Catalog are unaccounted institutional liability and trigger an automatic Founder Action for catalog registration. |

---

## Classification

*Per GEOM §G-3 — produced by Goal Orchestrator (INST-013)*

| Dimension | Value | Rationale |
|---|---|---|
| **Scope** | Cross-domain | Touches CE (prepaid gate enforcement), BP (subscription + wallet API), AIR (LLM cost tracking), Web (onboarding payment UX), and a new WBE service |
| **Nature** | Design + Build | Spec phase produces 10 deliverables; Build phase is autonomous sprint execution |
| **Risk** | High | Touches financial infrastructure — all customer money flows through WBE. A bug in the prepaid gate or the wallet engine causes customer money loss or incorrect charges. |
| **Urgency** | Elevated | Required before first paying DMA customer. WC-016 (Web Portal) delivers the portal that will accept payment — WBE must be ready when the portal goes live. |

**Priority Tier:** P3 — Elevated. Serves before Routine Goals; may not suspend P1/P2 Goals.

**CA Classification Review Window:** One constitutional session from this document's publication.

---

## Participating Institutions + GO Authorizations

*Per GEOM §G-4 — issued by Goal Orchestrator (INST-013)*

### Spec Phase Participants

| Institution | Role | Deliverables | Sequence |
|---|---|---|---|
| Constitutional Analyst (INST-002) | Produce + validate constitutional claims | D-01: Claims C-088–C-091 | First — all other spec work depends on the constitutional foundation |
| Chief Business Architect (INST-003) | Business model and product definitions | D-05: Bundle Definitions (DMA Starter/Runner/Winner) · D-06: Thread Catalog reference · D-09: Agent Billing Profiles × 4 | Parallel with EA (D-03 available) |
| Enterprise Architect (INST-004) | Architectural decisions | D-02: ADR-022 Amendment · D-03: ADR-034 (WBE) · D-04: ADR-024 Amendment | After D-01; D-02/D-03/D-04 in parallel |
| Solution Architect (INST-005) | Component specification | D-07: WBE Component Spec (5 sub-components) | After D-03 |
| Chief Data Architect (INST-006) | Schema update specification | D-08: DB Schema Updates (Thread Catalog table, Bundle Profiles, Procurement Ledger, bucket extensions) | After D-07 |
| Goal Orchestrator (INST-013) | Sprint execution plan | D-10: Autonomous Sprint Execution Plan | After D-01 through D-09 all approved |

### Implementation Phase Participant

| Institution | Role | Deliverables | Authorization |
|---|---|---|---|
| Platform IT Expert (INST-010) | Autonomous sprint execution | WC-017 through WC-024 (code, tests, CCTs) | Authorized when D-10 is approved AND Founder sets implementation authorization per C-066 |

### GO Authorizations

```
GOA-GOAL-004-INST-002-01
  goal_id:            GOAL-004
  institution_id:     INST-002 (Constitutional Analyst)
  contribution_scope: D-01 — Produce claims C-088, C-089, C-090, C-091
                      Then serve as reviewer for D-02 through D-09 spec outputs
  participation_window: Spec Phase — begin immediately; complete before D-02 begins
  collaboration_type: Primary
  issued_by:          INST-013
  issued_at:          2026-07-30

GOA-GOAL-004-INST-003-01
  goal_id:            GOAL-004
  institution_id:     INST-003 (Chief Business Architect)
  contribution_scope: D-05 Bundle Definitions · D-06 Thread Catalog · D-09 Billing Profiles × 4
  participation_window: Spec Phase — begin after D-03 is available (parallel with D-03)
  collaboration_type: Primary
  issued_by:          INST-013
  issued_at:          2026-07-30

GOA-GOAL-004-INST-004-01
  goal_id:            GOAL-004
  institution_id:     INST-004 (Enterprise Architect)
  contribution_scope: D-02 ADR-022 Amendment · D-03 ADR-034 · D-04 ADR-024 Amendment
  participation_window: Spec Phase — begin after D-01 complete
  collaboration_type: Primary
  issued_by:          INST-013
  issued_at:          2026-07-30

GOA-GOAL-004-INST-005-01
  goal_id:            GOAL-004
  institution_id:     INST-005 (Solution Architect)
  contribution_scope: D-07 WBE Component Spec (wallet, markup engine, meter, procurement, reconciliation)
  participation_window: Spec Phase — begin after D-03 approved
  collaboration_type: Primary
  issued_by:          INST-013
  issued_at:          2026-07-30

GOA-GOAL-004-INST-006-01
  goal_id:            GOAL-004
  institution_id:     INST-006 (Chief Data Architect)
  contribution_scope: D-08 DB Schema Update Spec
  participation_window: Spec Phase — begin after D-07 approved
  collaboration_type: Primary
  issued_by:          INST-013
  issued_at:          2026-07-30

GOA-GOAL-004-INST-013-01
  goal_id:            GOAL-004
  institution_id:     INST-013 (Goal Orchestrator)
  contribution_scope: D-10 Autonomous Sprint Execution Plan
  participation_window: Spec Phase — final act; begin after D-01 through D-09 all approved
  collaboration_type: Primary
  issued_by:          INST-013 (self-issued — GO producing the sprint plan)
  issued_at:          2026-07-30
  note:               GO is not contributing to any Goal it orchestrates (G-13) EXCEPT
                      D-10, which is orchestration output — not a domain contribution.
                      The sprint plan is the GO's orchestration closing act.

GOA-GOAL-004-INST-010-01
  goal_id:            GOAL-004
  institution_id:     INST-010 (Platform IT Expert)
  contribution_scope: WC-017 through WC-024 — implementation of all approved specs
  participation_window: Implementation Phase — begins after D-10 approved AND Founder C-066 authorization
  collaboration_type: Primary
  issued_by:          INST-013
  issued_at:          2026-07-30
```

---

## Spec Phase — Deliverable Specifications

### D-01 — Constitutional Claims C-088 through C-091
**Claims:** C-088, C-089, C-090, C-091
**Producer:** Constitutional Analyst (INST-002)
**Input:** Brainstorm record (this document), CONSTITUTION.md, existing claims corpus
**Output:** Four ratified claims in `knowledge/claims/` with simulation evidence
**Completeness criteria:** Each claim is typed (LAW / CONFIRMED / CANDIDATE), has a simulation
scenario validating it, and has been reviewed by CA before submission for Founder ratification.
**Dependency:** None — first in sequence.

### D-02 — ADR-022 Amendment (Extended Prepaid + Single Onboarding Payment)
**Producer:** Enterprise Architect (INST-004)
**Input:** D-01, existing ADR-022
**Output:** Amendment section added to `adr/ADR-022-payment-processing-razorpay-india.md`
**Must cover:**
- Razorpay Order + Subscription combination for single onboarding payment
- Extended prepaid definition: LLM bucket, video bucket, WhatsApp window bucket,
  image generation bucket — all governed by the same prepaid gate as ad_spend_wallet
- Payment intent activation timing (mode switch precedes subscription object creation — S-09)
- Progressive renewal failure policy (Days 1, 3, 7, 14 — S-14)
- Grandfather pricing enforcement mechanism (C-089)

### D-03 — ADR-034 (WAOOAW Billing Engine)
**Producer:** Enterprise Architect (INST-004)
**Input:** D-01, brainstorm record (this document)
**Output:** New `adr/ADR-034-waooaw-billing-engine.md`
**Must cover:**
- WBE as an agent-agnostic Python service (separate from BP, integrated via internal API)
- Five sub-component architecture: Wallet Engine, Markup Engine, Usage Meter + Alert Engine,
  Platform Procurement Ledger, Reconciliation Engine
- Thread Catalog as single source of truth (C-090)
- Agent Billing Profile as constitutional gate (C-088)
- Minimum margin floor as computational enforcement (C-088)
- Agency-model-ready schema constraint (no closed doors)
- WBE self-audit: daily balance reconciliation against ledger sum

### D-04 — ADR-024 Amendment (Bundle Rations Replace Token Economy Tiers)
**Producer:** Enterprise Architect (INST-004)
**Input:** D-01, D-03, existing ADR-024
**Output:** Amendment section added to `adr/ADR-024-token-economy-model-tier-routing.md`
**Must cover:**
- How bundle ration profiles (Starter/Runner/Winner) map to the existing LOCAL/MID_TIER/FRONTIER
  routing architecture — the routing stays; the bucket limits are new
- How the prepaid bucket check integrates with the PSE (Provider Selection Engine)
  before each LLM dispatch — PSE queries bucket, not just plan_tier
- Customer pacing choice effect on per-period bucket availability

### D-05 — Bundle Definitions: DMA Starter / Runner / Winner
**Producer:** Chief Business Architect (INST-003)
**Input:** D-03, brainstorm record, existing DMA agent spec, FOUNDER-ACTION.md cost data
**Output:** `architecture/reference/billing/dma-bundle-definitions.md`
**Must cover:**
- Per-resource rations per bundle (LLM tiers, video clips, WhatsApp windows, image gen)
- Customer-facing outcome description (what they hear, not technical units)
- Pricing derivation per bundle (Layer 1 markup → Layer 2 bundle cost → Layer 3 platform margin)
- Minimum ad wallet threshold per bundle (Curtain Raiser, Growth Engine, Maturity Phase)
- Pacing choice options and their operational implications
- Top-up availability per bundle (which top-ups each bundle can access)
- Trial profile (zero-cost substitutions for all threads)
- Upgrade/downgrade rules (pro-rata ration calculation)

### D-06 — Thread Catalog Reference
**Producer:** Chief Business Architect (INST-003)
**Input:** D-03, FOUNDER-ACTION.md (FA-012 through FA-015 cost data), ADR-029, ADR-026
**Output:** `architecture/reference/billing/thread-catalog.md`
**Must cover every current thread:**
- LLM tiers: LOCAL (₹0), MID_TIER (Gemini Flash), FRONTIER (Gemini Pro)
- Video generation: Kling AI (per clip), HeyGen (per minute), ElevenLabs (flat), Runway ML
- WhatsApp windows: BSP rate, quiet hours policy reference
- Image generation: current capability + placeholder for future providers
- Infrastructure: Azure Container Apps, PostgreSQL, Redis — shared cost amortisation method
- Ad spend: pass-through (not a Thread Catalog cost — customer's money)
- Agent-specific threads: market data, climate data, crop data, school syllabus (current + future)
**Format per thread:** provider, unit, raw INR cost, FX buffer %, operational overhead %,
risk premium %, total markup %, marked-up cost, review frequency.

### D-07 — WBE Component Specification
**Producer:** Solution Architect (INST-005)
**Input:** D-03 (ADR-034), D-04, D-05, D-06
**Output:** `architecture/reference/billing/wbe-component-spec.md`
**Must specify all five sub-components:**

*Wallet Engine:*
- Bucket types: subscription_llm_mid, subscription_llm_frontier, subscription_video,
  subscription_whatsapp, subscription_image, ad_spend (existing), topup_* variants
- Balance check API (called by AIR before every LLM dispatch, by task executor before video)
- Bucket reservation (lock before execution, release on completion or failure)
- Bucket refill triggers (period renewal, top-up purchase, auto-refill execution)
- One wallet / multiple buckets per customer (wallet_id → bucket rows)

*Markup Engine:*
- Thread Catalog read (raw cost → markup % → marked-up cost)
- Bundle cost floor derivation (Σ marked-up thread × ration)
- Platform margin application (cost floor ÷ (1 - margin %))
- Minimum margin floor enforcement (C-088 gate — blocks below-floor price)
- Price change propagation: new subscribers on new price; existing on grandfather price

*Usage Meter + Alert Engine:*
- Per-customer per-bucket daily consumption tracking
- Velocity calculation: rolling 7-day average consumption rate
- Depletion projection: current_balance ÷ daily_rate = days_remaining
- Threshold triggers: 50% → advisory WhatsApp; 60% → top-up offer; 85% → urgent;
  95% → campaign pause (ad_spend only); 0% → graceful degradation
- Quiet hours policy: 23:00–07:00 IST — hold advisory, immediate only for 5% threshold
- Proactive Offer Engine: seasonal event calendar + velocity projection → auto-offer
- Platform procurement alerts: WAOOAW provider account projection → auto-FA generation

*Platform Procurement Ledger:*
- WAOOAW-side spend tracking per provider account (Kling AI, HeyGen, ElevenLabs,
  Vertex AI, WhatsApp BSP, Meta MBM, Google MCC)
- Daily spend actuals vs projected
- Days-remaining projection per provider account
- Founder Action auto-generation when days_remaining < 7
- FX reconciliation: USD-billed providers at actual daily exchange rate

*Reconciliation Engine:*
- Daily: actual per-customer cost (all threads) vs bundle cost floor
- Monthly: margin per customer, margin per agent type, platform total margin
- WBE self-audit: computed bucket balance vs sum of ledger entries (must match exactly)
- Discrepancy threshold: any variance > ₹1 triggers alert before customer notification

### D-08 — DB Schema Update Specification
**Producer:** Chief Data Architect (INST-006)
**Input:** D-07 (WBE Component Spec)
**Output:** `architecture/reference/data/billing-schema-updates.md` + draft SQL migration
**Must specify new/updated tables:**

New tables:
- `institutional.thread_catalog` — all provider threads with costs and markup
- `institutional.bundle_profiles` — versioned bundle definitions per agent type
- `business.customer_wallets` — one wallet per customer (extends existing wallet concept)
- `business.wallet_buckets` — N buckets per wallet (replaces/extends ad_spend_wallets)
- `business.bucket_reservations` — in-flight reservations (lock before execution)
- `business.topup_orders` — top-up purchase records
- `business.pacing_preferences` — customer's monthly pacing choice per bundle resource
- `institutional.platform_procurement_ledger` — WAOOAW's own provider spend tracking
- `institutional.provider_accounts` — WAOOAW's accounts at each provider with balance + threshold
- `business.billing_profiles` — Agent Billing Profile per agent type (C-088 compliance)

Updated tables:
- `business.ad_spend_wallets` → migrate to wallet_buckets (ad_spend becomes a bucket type)
- `business.subscription_billing_events` → add bucket_type, thread_id columns
- `business.subscription_tiers` → add bundle_version, cost_floor_paise columns
- `business.gst_invoices` → add thread-level line items for drill-down billing

Agency-ready columns (added now, used in GOAL-AGENCY):
- `business.organisations` → add `billing_entity_type` (DIRECT / AGENCY / RESELLER / CHILD)
- `business.organisations` → add `parent_organisation_id` (NULL for direct customers)
- `business.wallet_buckets` → add `spending_quota_paise` (NULL = no limit)

### D-09 — Agent Billing Profiles × 4
**Producer:** Chief Business Architect (INST-003)
**Input:** D-06 (Thread Catalog), each existing agent spec, D-05 (DMA bundle as template)
**Output:** `architecture/reference/billing/billing-profiles/` (one file per agent)
**Files:**
- `dma-billing-profile.md` — Digital Marketing Agent
- `trading-billing-profile.md` — Trading Professional
- `agricultural-billing-profile.md` — Agricultural Advisor
- `private-tutor-billing-profile.md` — Private Tutor

**Per profile, must specify:**
- Agent type identifier
- Platform threads used (inherited from platform baseline)
- Agent-specific threads (domain data APIs, specialized generation)
- Default bundle rations for Starter/Runner/Winner (even if not implemented yet)
- Minimum wallet requirements (some agents need ad wallet; some don't)
- Trial profile: zero-cost substitutions for each thread
- Constitutional obligations specific to this agent's billing (e.g., C-060 for Private Tutor —
  subscription billing information never surfaced to minor student)

### D-10 — Autonomous Sprint Execution Plan
**Producer:** Goal Orchestrator (INST-013)
**Input:** D-01 through D-09 all approved
**Output:** Section appended to this document + `work-contracts/` stubs for WC-017 through WC-NNN
**This is GOAL-004's closing deliverable. GOAL-004 closes when D-10 is Founder-authorized.**

---

## Success Criteria

| SC | Criterion | Measured By |
|---|---|---|
| SC-01 | Thread Catalog operational — every current provider cost registered with raw cost, markup %, marked-up cost | Thread Catalog reference document exists + table populated |
| SC-02 | Markup Engine derives offering prices from 3 layers and computationally enforces minimum margin floor (C-088) | WBE rejects below-floor price configuration in tests |
| SC-03 | Prepaid gate extended to ALL constrained resources — LLM, video, WhatsApp windows, image generation | CCT-PREPAID-01: attempt to fire LLM call with empty bucket → rejected |
| SC-04 | DMA Starter/Runner/Winner bundles live with per-resource rations and customer pacing choice | Portal shows bundle options; pacing preference recorded; ration enforcement active |
| SC-05 | Top-Up Plans available: resource unit top-up, event packs, auto-refill authorization | Customer can purchase top-up via single WhatsApp interaction; auto-refill executes without interruption |
| SC-06 | Single onboarding payment: subscription activation + wallet seed in one Razorpay transaction | CCT-ONBOARD-01: one UPI tap → subscription active + wallet seeded (≤2 min) |
| SC-07 | Autonomous Billing Loop: daily projection, threshold alerts (50/60/85/95%), proactive top-up offers, progressive renewal failure | CCT-BILLINGLOOP-01: simulated 17 operational scenarios all handled per policy |
| SC-08 | Platform Procurement Ledger: WAOOAW provider spend tracked; Founder Action auto-generated when days_remaining < 7 | Platform Operations agent produces procurement projection daily; FA auto-created in test |
| SC-09 | All 4 existing agents have completed Agent Billing Profiles (C-088 compliance) | 4 files in `architecture/reference/billing/billing-profiles/` — reviewed and approved |
| SC-10 | Claims C-088, C-089, C-090, C-091 ratified | 4 files in `knowledge/claims/` with Founder ratification stamps |

---

## Autonomous Sprint Execution Plan (D-10 — to be written)

*This section is intentionally empty. It will be completed by Goal Orchestrator (INST-013)
as D-10 — the final act of the spec phase — once D-01 through D-09 are all approved.*

*Estimated sprint sequence: WC-017 through WC-024 (8 sprints)*
*Estimated total implementation time: 4 weeks at current autonomous sprint cadence (3 hours)*
*The actual sprint decomposition and task specifications will be derived from approved specs.*

---

## Spec Phase Sequencing Diagram

```
Week 1:
  D-01 (CA) — Constitutional Claims C-088–C-091
    ↓
  D-02 (EA) ─── ADR-022 Amendment           ┐
  D-03 (EA) ─── ADR-034 WBE Architecture   ─┤ Parallel
  D-05 (BA) ─── DMA Bundle Definitions      │ (D-03 available → BA starts)
  D-06 (BA) ─── Thread Catalog Reference    ┘

Week 2:
  D-04 (EA) ─── ADR-024 Amendment           ┐ After D-03 approved
  D-07 (SA) ─── WBE Component Spec          ┘
  D-09 (BA) ─── Agent Billing Profiles × 4    After D-05, D-06

Week 3:
  D-08 (DA) ─── DB Schema Update Spec         After D-07 approved

Week 3–4:
  CA Review all spec outputs
  Founder approval of full spec package

Week 4:
  D-10 (GO) ─── Autonomous Sprint Execution Plan  After all approved
  Founder authorizes implementation (C-066)
  Autonomous pipeline begins WC-017
```

---

## Open Decisions for Founder

The following decisions are needed before the corresponding spec can be finalized:

| Decision | Needed For | Options |
|---|---|---|
| Minimum margin floor % (C-088) | D-03, D-05 | Suggest 55% — leaves room for top-up discounting while protecting platform |
| Thread markup % per category | D-06 | Suggest: LLM 45%, Video 20%, WhatsApp 17%, Infrastructure amortised flat |
| Starter/Runner/Winner ration sizes | D-05 | BA to propose; Founder approves before D-05 is final |
| FX buffer % built into markups | D-06 | Suggest 5% — covers moderate INR depreciation cycle |
| Platform margin target % | D-05 | Suggest 60–65% — consistent with current implied margins |
| Pacing option default | D-05 | Suggest "spread" as default — customer explicitly chooses "burst" |
| Auto-refill pre-authorization ceiling | D-07 | Suggest ₹500/month max without re-asking customer |

---

## Evidence Register

*Append-only — each contribution is recorded here as produced.*

| Date | Institution | Contribution | Status |
|---|---|---|---|
| 2026-07-30 | INST-013 (Goal Orchestrator) | Goal Understanding Record (this document) | PRODUCED |
| 2026-07-30 | INST-013 (Goal Orchestrator) | Goal Classification + GO Authorizations issued | PRODUCED |
| 2026-07-30 | INST-013 (Goal Orchestrator) | Spec Phase Deliverable Specifications D-01 through D-10 | PRODUCED |
| 2026-07-30 | INST-002 (CA) | D-01 Claims C-088–C-091 | ✅ PRODUCED |
| 2026-07-30 | INST-004 (EA) | D-02 ADR-022 Amendment | ✅ PRODUCED |
| 2026-07-30 | INST-004 (EA) | D-03 ADR-034 WBE Architecture | ✅ PRODUCED |
| 2026-07-30 | INST-004 (EA) | D-04 ADR-024 Amendment | ✅ PRODUCED |
| 2026-07-30 | INST-003 (BA) | D-05 DMA Bundle Definitions | ✅ PRODUCED |
| 2026-07-30 | INST-003 (BA) | D-06 Thread Catalog Reference | ✅ PRODUCED |
| 2026-07-30 | INST-003 (BA) | D-09 Agent Billing Profiles × 4 | ✅ PRODUCED |
| — | INST-005 (SA) | D-07 WBE Component Spec | PENDING |
| — | INST-006 (DA) | D-08 DB Schema Updates | PENDING |
| — | INST-013 (GO) | D-10 Autonomous Sprint Execution Plan | PENDING |

---

*This document is the authoritative GOAL-004 record. All spec deliverables reference it.*
*GOAL-004 is CLOSED when D-10 is approved and the autonomous sprint plan is Founder-authorized.*

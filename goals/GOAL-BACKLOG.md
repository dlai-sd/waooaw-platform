# WAOOAW Goal Backlog Register

**Authority:** Goal Orchestrator (INST-013) — maintained per GEOM §G-2
**Last Updated:** 2026-08-08
**Status:** Living document — updated at each Goal registration or session close

---

## Purpose

This register is the single view of all Goals in the WAOOAW ecosystem —
formalized Goals (numbered, with Understanding Records), backlog Goals
(identified, not yet formalized), and closed Goals (evidence committed to
Constitutional Audit Ledger).

A Goal enters this register when the Founder articulates a desired outcome.
A Goal receives a number when the Goal Orchestrator produces a Goal
Understanding Record and the Founder acknowledges the Execution Plan.

---

## Formalized Goals

| Goal ID | Statement | Status | Sprint(s) | Closed |
|---|---|---|---|---|
| GOAL-001 | Semantic Brain Transformation — transform WAOOAW into a Goal-driven semantic brain capable of outcome-based dialogue and execution | CLOSED | — | 2026-07-27 |
| GOAL-002 | Universal AI Execution Layer — implement MagicLLM + GoalExecutor as the universal AI intelligence substrate for all autonomous sprint execution | CLOSED | — | 2026-07-27 |
| GOAL-003 | PTR Dynamic Knowledge Asset — replace static JSON context with a live, multi-stack Prompt Template Repository assembled from source files | CLOSED | — | 2026-07-27 |
| GOAL-004 | WAOOAW Billing Engine | **SPEC COMPLETE** — implementation WBE-S1→WBE-S8 awaiting Founder authorization | WBE-S1→WBE-S8 (est.) | — |
| GOAL-005 | Agent Employment Experience Program — one constitutional relationship across discovery, hire, work, lifecycle, multiple agents, and organizational delegation | **G-3 CLASSIFICATION PROVISIONAL** — Cross-domain · Build · Constitutional · Elevated; R2-10 window open; no implementation authorization | WC-055; AE-01→AE-06 remain outcome epics | — |

---

## Backlog — Identified, Not Yet Formalized

Backlog Goals are outcomes the Founder has articulated and the Goal Orchestrator
has captured in exploratory discussion. They do not yet have a Goal Understanding
Record. They carry no sequence number until formalized.

---

### GOAL-AGENCY — Multi-Tier Agency and Reseller Billing Extension

**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-07-30
**Prerequisite:** GOAL-004 (Billing Engine core must exist before agency models are layered on)

**Desired Outcome:**
Enable WAOOAW to serve digital marketing agencies and resellers under four
billing models, each with its own money flow, margin structure, and customer
identity arrangement — without requiring code changes to the core Billing Engine.

**Business Aspiration:**
WAOOAW's DMA agent today serves individual business owners directly. The next
commercial frontier is onboarding agencies who manage 10–50 SMB clients each.
One agency relationship = 50 customers without direct sales effort. The platform
must support four distinct agency configurations:

```
Model A — Agency WITH own wallet, clients WITHOUT own ad account
  Agency deposits lump sum. WAOOAW runs campaigns on MBM for each client.
  Agency earns by marking up WAOOAW's subscription + management fees.
  WAOOAW revenue: subscription + 10% ad management fee per client.
  Complexity: per-child sub-wallet quotas, concentration risk management.

Model B — Agency WITH own wallet, clients WITH own ad account
  Agency pays WAOOAW subscription. Client's own Meta/Google card pays ad spend.
  WAOOAW earns subscription only — no management fee (money never routed).
  Revenue model: possibly add per-campaign flat fee to compensate for lost mgmt fee.

Model C — Agency WITHOUT own wallet, clients WITHOUT own ad account
  Three sub-models:
    C-1 Referral: Client pays WAOOAW directly. WAOOAW pays agency 15% commission.
    C-2 White-label: Agency resells under own brand at bulk/reseller rate.
    C-3 Revenue share: WAOOAW shares management fee split with agency.
  Complexity: white-label identity, GST invoice routing, commission payout system.

Model D — Agency WITHOUT own wallet, clients WITH own ad account
  Pure reseller / partner program.
  Agency earns partner commission. WAOOAW services client at reseller rate.
  Highest-scale model — lowest per-customer revenue, zero WAOOAW sales cost.
```

**Key Design Decisions Needed Before Formalization:**
1. Which models are in scope for GOAL-AGENCY MVP vs future iterations?
2. White-label identity: is the end client's Employment Contract with WAOOAW or the reseller? (Constitutional + legal implication — Ojal review required)
3. Commission payout architecture: monthly bank transfer? TDS implications?
4. Minimum commitment for agencies: quarterly or annual? (concentration risk mitigation)
5. Partner dashboard scope: what billing data does the agency see about their clients?

**Key Operational Scenarios Identified:**
- Agency wallet drained by one high-velocity child client (Scenario 16 — velocity anomaly)
- Agency/reseller churn: single event removes 50 clients (concentration risk)
- White-label client who wants to move to WAOOAW direct (portability question)
- Per-child spending quota enforcement in agency shared wallet
- Commission payout reconciliation at month end
- GST invoice routing: WAOOAW invoices agency; agency invoices clients separately
- Reseller pricing table: three price tiers for the same bundle (direct / agency / reseller)

**Margin Map (explored in brainstorming):**
```
Model A (VMP3):    ~₹1,663/client/month WAOOAW margin (83%)
Model B (VMP4):    ~₹749/client/month WAOOAW margin (75%) — least attractive
Model C white-label: ~₹1,464/client/month (81%) + zero sales cost
Model D reseller:  ~₹1,464/client/month (81%) + zero sales cost
Direct customer:   ~₹2,163/client/month (86%)
```

**The Franchise Analogy:**
WAOOAW = franchisor. Agency = franchisee type depends on model:
- Model A = master franchisee (holds the float, manages the outlets)
- Model B = management contractor (runs outlets, client owns the shop)
- Model C = private-label retailer (buys wholesale, sells under own brand)
- Model D = regional distributor (finds customers, earns referral)

**Constitutional Implications (flagged for CA review at formalization):**
- Employment Contract identity under white-label (who is the employer?)
- C-048 Non-Exploitation enforcement when agent operates under reseller brand
- C-049 Honest Limitation when customer thinks they are on "DigitalFirst AI Platform"
- TDS and GST compliance on commission payouts (Ojal — legal review)
- Concentration risk: single agency default = mass customer impact

**Inputs Required at Formalization:**
- GOAL-004 completed (Billing Engine, Thread Catalog, Agent Billing Profiles exist)
- Founder decision on white-label identity (legal review first)
- Ojal sign-off on constitutional obligations under white-label
- Legal counsel input on commission structure and TDS treatment

**Estimated Scope:** Large — deserves its own multi-sprint Goal with CA review before
EA begins architecture. Not suitable for single sprint delivery.

---

### GOAL-STEWARD-INTERFACE — Steward Interface and Authenticated Governance Platform

**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-07-30
**Prerequisite:** WC-016 (Web Portal infrastructure must exist before Steward Portal is built)

**The Observation That Registered This Goal:**
During GOAL-004 pricing authorization, the Founder explicitly rejected the pattern of
approving pricing decisions via AI conversation and markdown files:
> "I don't want to put it as design/development time values. I want a login, role, and
> interface for these inputs on the running app."

This is constitutionally correct. Every Founder Action, Tier 1 authorization, and Ethics
Officer review must eventually be performed through an authenticated, auditable interface
— not through markdown files or AI conversations. FOUNDER-ACTION.md is a bootstrap
artifact, valid only until the platform is live with paying customers.

**Desired Outcome:**
WAOOAW has an authenticated Steward Interface at `ops.waooaw.ai` where all three stewards
perform their constitutional duties through their own login and role-gated panels. Every
action is recorded as an immutable entry in the Constitutional Audit Ledger — not in a
markdown file. The Steward Interface IS the constitutional enforcement mechanism for
human governance of the platform.

**Three Roles — Three Access Profiles:**

```
Yogesh (Founder):
  → Founder Action Panel: approve/reject pricing, implementation gates, agent publication
  → Thread Catalog management: add/modify/deprecate cost entries (C-091)
  → Minimum margin floor setting (C-089)
  → Constitutional ratification panel (claim ratification log)
  → Platform margin dashboard + procurement runway view
  → Emergency Override (C-001 Human Override button — always visible)

Sujay (Business Growth / Tier 1):
  → Sprint Dashboard: monitor autonomous pipeline, open PRs
  → Skill Proposal review (Product Owner — Office 11)
  → Key Vault Tier-1 secret updates (non-FA-level)
  → Agent output quality review panel

Ojal (Ethics Officer):
  → Constitutional violation alerts (flagged by CA)
  → Agent approval for domains involving minors (C-060 — Private Tutor)
  → Ethics incident review and response panel
  → New agent constitutional obligation sign-off
```

**Why This Is Constitutional, Not Just UX:**

The current markdown approach has three structural failures:
1. **No authentication** — any AI agent in a session can write to FOUNDER-ACTION.md. There
   is no cryptographic proof that Yogesh approved something vs an agent doing it on his behalf.
2. **No role separation enforcement** — Sujay could technically write a Founder Action in
   markdown. The interface enforces this technically, not by convention.
3. **No audit chain** — constitutional audit requires immutable records. A markdown file is
   mutable and not signed. The DB is the right audit ledger per C-007.

**Proposed New Constitutional Claims (to be ratified by CA before spec begins):**

- **C-092: Steward Interface as Constitutional Enforcement Mechanism** — All Founder Actions,
  Tier 1 authorizations, and Ethics Officer reviews must be performed through the
  authenticated Steward Interface. Actions via markdown or AI conversation are provisional
  bootstrap artifacts only — they expire when the first paying customer is onboarded.

- **C-093: Steward Role Separation** — The three steward roles are enforced at the
  authentication layer. No steward may perform actions assigned to another role. Technical
  enforcement, not policy convention.

**New DB Tables Needed:**
- `constitutional.steward_actions` — immutable log of every action taken by any steward
- `constitutional.ratification_log` — formal claim ratification records
- `constitutional.founder_action_queue` — pending FA items served to Yogesh's panel
- `constitutional.pricing_authorization_log` — every pricing change with steward signature

**Bootstrap Migration Plan:**
- All entries in `FOUNDER-ACTION.md` must be migrated to `constitutional.steward_actions`
  before the platform accepts its first paying customer
- Migration is a formal IB item created from this Goal
- Until migration: FOUNDER-ACTION.md remains valid as bootstrap-only artifact

**Inputs Required at Formalization:**
- WC-016 (Web Portal) complete — Steward Interface shares the Next.js infrastructure
- C-092 and C-093 ratified (CA session)
- Legal review of cryptographic audit requirements (Ojal)

**Relationship to Existing Architecture:**
- Steward Assistant agent (INST-009 — ops.waooaw.ai) is already approved
- ADR-008 (Keycloak) already defines the OAuth allowlist for 3 steward accounts (C-068)
- The interface panel is the frontend that invokes the Steward Assistant AND records
  governance actions to the DB — not just a chat interface

**Estimated Scope:** Medium-large. Frontend + DB tables + auth + migration.
Recommend: one dedicated Goal after WC-016 completes.

---

```
2026-07-30 (Goal Orchestrator — INST-013):
  GOAL-AGENCY registered from Founder brainstorming session.
  Prerequisite dependency on GOAL-004 confirmed.
  Constitutional review flags raised for formalization.
  Founder to decide on scope boundaries before this Goal is formalized.

  GOAL-004 objectives confirmed by Founder. Goal Understanding Record produced.
  10 Success Criteria confirmed. Spec phase deliverables D-01 through D-10 specified.
  GO Authorizations issued to INST-002, INST-003, INST-004, INST-005, INST-006,
  INST-013, INST-010. GOAL-004 status: PLANNED — awaiting spec phase execution.
  Full Goal document: goals/GOAL-004-waooaw-billing-engine.md
```

---

*Archive: All closed Goal evidence is in `goals/GOAL-00N-*.md` + `goals/goal_register.jsonl`*
*This register is updated by Goal Orchestrator at each session close.*

---

### GOAL-AGENT-BASE — Agent Base Specification and Platform-Agent Contract Framework

**Registrant:** Yogesh Khandge (Founder) via EA session 2026-07-30
**Registered:** 2026-07-30
**Prerequisite:** WBE-S8 (Gap Scanner needs WBE signal infrastructure)

**Desired Outcome:**
Every WAOOAW agent — current and future — has a formally declared Platform-Agent
Contract specifying its behavior for platform signals, trial/live mode, and
graceful degradation. The Gap Scanner runs automatically after every platform
component addition to detect which agents need spec updates. Zero manual agent-hunting.

**Spec Work Already Done (2026-07-30):**
- AGENT-BASE-SPEC.md v1.0 — architecture/reference/agents/AGENT-BASE-SPEC.md
- WBE Signal Schema (AsyncAPI-aligned) — architecture/reference/signals/wbe-signal-schema.yaml
- ADR-035 (PAC Standard) — adr/ADR-035-platform-agent-contract-standard.md
- C-094 ratified (Agent Base Spec Compliance)
- PAC sections added to all 4 existing agent specs (DMA, Trading, Agricultural, Private Tutor)
- CONSTITUTIONAL_DNA.md + AGENT-AUTHORING-GUIDE v5.0 updated

**Remaining Implementation:**
- scripts/gap_scanner.py (WBE-S8 or dedicated sprint)
- institutional.platform_signal_schemas table (addendum to D-08)
- Gap Scanner wired into CI PR gate

**Industry Alignment:** AsyncAPI 3.0 (signal contracts), CloudEvents 1.0 (envelope),
Anthropic Constitutional AI (document-based base spec model)

---

### GOAL-SERVICING-CENTER — Constitutional Customer Servicing and Agent Lifecycle Management

**Registrant:** Yogesh Khandge (Founder) via EA session 2026-07-30
**Registered:** 2026-07-30
**Prerequisite:** WBE-S1→S8 (customer wallets must exist); GOAL-AGENT-BASE spec work (Base Spec v1.1 triggers from this Goal)

**Desired Outcome:**
WAOOAW has a defined, constitutional, and operational servicing mechanism for every
live customer employment contract. Customers are protected when platform changes
affect their agent. The institution learns from every customer outcome. The flywheel
spins without manual intervention.

**Five Components (S-1 through S-5):**

S-1 Agent Version Governance Policy (new ADR)
  Defines three update tiers: SECURITY (silent), BEHAVIORAL (next session),
  CAPABILITY (30-day notice + consent). Customer protection for mid-contract changes.
  Impact on PAC: needs agent_spec_version field + version_governance signal handlers.

S-2 Customer Health Monitor (Platform Operations agent extension)
  Per-customer daily health check: goal velocity, engagement signals, anomaly detection.
  Proactive outreach before customer churns. Platform-ops-signal-schema.yaml needed.

S-3 Constitutional Complaint Investigation (Platform Operations extension)
  Structured process: evidence audit → constitutional assessment → remediation → root cause routing.
  Routes to: Platform IT Expert (code bug) | Goal Orchestrator (spec gap) | CA (constitutional gap).

S-4 Monthly Business Review Dual Output (agent spec amendment for all agents)
  Adds OUTPUT B: institutional signal to institutional.customer_outcome_signals.
  Fields: goal_achievement_pct, skills_used_vs_available, customer_health_signal, improvement_proposals.
  Self-Improvement Analyst reads this to close the production→design feedback loop.

S-5 Constitutional Recall Mechanism (Platform Operations + WBE + all agents)
  When a bug or constitutional gap affects live customers: identify scope, remediate,
  notify each affected customer, record every remediation action per C-007.

**Direct Impact on Agent Base Spec → triggers v1.1 bump:**
  B-7: Monthly Business Review Institutional Output (S-4 connection)
  B-8: Version Update Consent Behavior (S-1 connection)
  B-9: Recall Mode Behavior (S-5 connection)

**New Signal Schemas needed:**
  architecture/reference/signals/platform-ops-signal-schema.yaml
  Channels: recall-initiated, recall-complete, capability-update-notice,
            security-update-applied, customer-health-alert

**New PAC service block in all agents:**
  platform_ops: { handles_signals: [...], schema_version: "1.0" }
  version_governance: { agent_spec_version: "[current]", handles_signals: [...] }

**The Flywheel Connection:**
  Without this Goal: production behavior never feeds back to design office.
  With this Goal: every 30-day Monthly Business Review produces an institutional
  signal → Self-Improvement Analyst aggregates → Goal Orchestrator routes improvements.
  The flywheel turns on customer time, not human session time.

---

---

### GOAL-PLATFORM-REGISTRY — Blueprint-First Platform Engineering Model (Final Flywheel)

**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-07-30
**Status:** PLANNED — spec complete, awaiting FA-026 authorization
**Full Goal Document:** goals/GOAL-PLATFORM-REGISTRY.md
**Simulation:** SIM-PLATFORM-001 PASS (30/30) — simulation/sim_platform_001_manifest_skeleton_pipeline_impact.py

**Desired Outcome:**
Blueprint-first engineering model operational. Every platform component has a
Component Manifest (YAML) and EA-produced Code Skeleton before implementation.
The autonomous pipeline reads manifests and skeletons, eliminating type-invention
errors (75% token reduction proven). 15-day Blueprint Assurance Run validates
runtime conformance to blueprints. This is the final flywheel model.

**Scope:**
- Manifests + skeletons for 5 existing services (CE, BP, PR, AIR, WBE — retroactive)
- ADR-036 (EA Skeleton Standard) + C-095 (Component Manifest Obligation) — done
- 6 pipeline upgrades (context_builder, task_decomposer, retry_advisor, etc.)
- gap_scanner.py + blueprint_assurance.py
- Platform Component Registry YAML

**Prerequisites:** None — can begin immediately after FA-026
**Enables:** GOAL-004 WBE sprints (75% cheaper) + all future Goals run blueprint-first

---

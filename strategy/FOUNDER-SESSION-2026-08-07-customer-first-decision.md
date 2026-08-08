# Founder Strategy Session — Customer-First Decision & Pillar Roadmap
**Date:** 2026-08-07  
**Participants:** Yogesh Khandge (Founder, INST-001) + GitHub Copilot (Steward Assistant)  
**Session Type:** Strategic Direction — Post-WC-043 · First Paying Customer Precedence  
**Continues from:** `strategy/FOUNDER-SESSION-2026-08-06-platform-vision.md`  
**Handover:** Enterprise Architecture (INST-004) for WC grooming  

> **Status: PARTIALLY SUPERSEDED — WC-049, 2026-08-08.** The revised Wave 1→5 decision in Section 11 is the controlling roadmap. Earlier alternatives are preserved as deliberation history. Component statuses below are reconciled to WC-043 evidence; roadmap identifiers WC-044→048 are reserved, but their Work Contracts do not yet exist.

---

## 1. Context — Where the Platform Stands

Following WC-043 (wallet router, CCT-PREPAID-01 + CCT-SELFAUDIT-01), the platform reached a structural milestone:

- **40 Work Contracts closed.** All infrastructure layers have implementations.
- **VERSION 1.44.0.** 361/361 tests passing. 94% coverage. Ruff clean.
- **Critical discovery:** The platform infrastructure is complete. The agents it was built to run **do not exist as code.** Zero lines of DMA, Trading, Agricultural, or Tutor agent in `src/`. They are 5,000-line specifications in `architecture/reference/agents/`.

> The employment management system is ready. No employee has been hired to it.

This session was convened to answer: what is the correct direction from this point?

---

## 2. The Debate

### Position A — Complete Pillars First, Then Customer Journey
Build the remaining infrastructure pillars (Agency Engine, Learning Flywheel, full Web Portal, Compliance Spine) before attempting to serve any customer.

**Rationale:** Structural integrity first. No technical debt at first customer contact.  
**Risk:** Indefinite deferral. Building infrastructure for customers who don't yet exist.

### Position B — Customer Journey First, Parallel Pillar Grooming *(Founder's decision)*
Start the customer journey now. Run pillar grooming and build as a parallel track, introducing each pillar when the customer journey creates a natural demand for it.

**Rationale:** Pillars are validated only by use. The first customer is the proof of concept for the entire constitutional model. Speed to commercial proof matters.  
**Risk (acknowledged):** Mid-to-long term structural compromise if pillars are genuinely dropped rather than tracked and groomed.

---

## 3. The Founder's Decision

> *"I vouch for: start early with customer journey and keep grooming/adding pillars."*
> — Yogesh Khandge, Founder (INST-001), 2026-08-07

**The decision is recorded as Founder Precedence.**

### Critical Clarification — "Parallel" Does Not Mean "Optional"

The debate was NOT between shipping fast vs. doing it right. It was about sequencing.

Two pillars are NOT parallelisable — they are **embedded inside the customer journey itself** and must ship with the first customer:

1. **DPDPA Compliance Spine** — WAOOAW's own privacy policy commits to DPDPA 2023 compliance. Yogesh is constitutionally designated as Grievance Officer. The first byte of a customer's audience data processed without consent infrastructure creates personal legal exposure. Not deferrable.

2. **Customer Evidence Window** — The Constitution defines the Customer Evidence Ledger as owned by the customer with an unconditional right to audit. Without evidence surfacing, constitutional rights are unenforceable and commercial renewal is impossible. Not deferrable.

These are not pillars alongside the customer journey. They are part of it.

---

## 4. Platform Pillar Register

All 17 pillars identified across 2026-08-06 and 2026-08-07 sessions.

### Layer 0 — Constitutional Governance

| # | Pillar | Objective | Expected Outcome | Status |
|---|---|---|---|---|
| P-01 | **Constitutional Engine (CE)** | Enforce constitutional constraints on every agent action via gRPC authority | Every tool call, decision, and state change is constitutionally validated before execution | ✅ Built — WC-019 |
| P-02 | **Evidence First Enforcer** | Reject any claim not backed by tamper-evident evidence | No agent can assert an outcome it did not produce; audit trail is the source of truth | ✅ Built |
| P-03 | **Emergency Stop** | True operational halt via Temporal signal — cancels in-flight sagas | Customer or platform can halt an agent within 250ms regardless of execution state | ✅ Built — ADR-018 |
| P-04 | **Constitutional Audit Trail Sink** | Persist every tool call, decision, and state transition to immutable Postgres (WORM) | Full constitutional audit history; DPDPA audit compliance as a product feature | ✅ Implemented and tested — WC-037; deployment/customer proof unverified |

### Layer 1 — Execution Infrastructure

| # | Pillar | Objective | Expected Outcome | Status |
|---|---|---|---|---|
| P-05 | **Professional Runtime (PAAS)** | Per-session Temporal isolation for every agent execution | Agents run in constitutional isolation; no cross-session data leakage | ✅ Built — WC-036 |
| P-06 | **AI Runtime (PSE / RAG / PII)** | Model tier routing by task complexity + PII scrubbing before every prompt | Right model for right task; no PII in LLM prompt history | ✅ Built |
| P-07 | **UDCP / Multi-Stack Compile Gate** | Zero structural drift — AST-driven scaffold; LLM fills logic only; compile before commit | No hallucinated imports, no broken builds; constitutional code generation | ✅ Built — WC-036/038 |

### Layer 2 — Trust & Integration

| # | Pillar | Objective | Expected Outcome | Status |
|---|---|---|---|---|
| P-08 | **Trust Layer (CTG + oauth-vault + Provider Registry + Token Refresh)** | Constitutional Tool Gateway as the only entry point for external API calls; customer credentials never in LLM history | Platform can connect to any OAuth2 / API-key provider via declarative config; credentials injected at socket boundary only | ✅ Core implemented and tested — WC-038/039; real customer platform adapters and production proof remain |

### Layer 3 — Business Engine

| # | Pillar | Objective | Expected Outcome | Status |
|---|---|---|---|---|
| P-09 | **Billing Engine (WBE)** | Universal prepaid gate; per-action metering; reconciliation; self-audit; wallet | Every agent action is metered and billed; platform revenue is constitutionally sound | ✅ Built — WC-043 closes WBE |
| P-10 | **Agency / Reseller Engine** | Enable agencies and resellers to bring customers to WAOOAW with commission tracking | Distribution channel beyond direct sales; India SME market reached via agencies | 🔲 Not built — design committed for month 3 |

### Layer 4 — Skill Architecture

| # | Pillar | Objective | Expected Outcome | Status |
|---|---|---|---|---|
| P-11 | **Skill Architecture (Registry + Intent Crystallizer + Assignment)** | Skills are platform registry entries, not code changes; agents are skill compositions | Adding a new capability to an agent = registry entry, not a sprint | ✅ Implemented and tested — WC-040/041; deep agent skill inventory remains |
| P-12 | **DMA Agent v1** | First customer-facing agent: content_publish + ad_campaign_manager as runnable code on Professional Runtime | Platform serves a real paying customer; constitutional model is proven in production | 🔲 Not built — 5,000-line spec exists; 0 code in `src/` |

### Layer 5 — Customer Interface & Trust

| # | Pillar | Objective | Expected Outcome | Status |
|---|---|---|---|---|
| P-13 | **DPDPA Compliance Spine** | Consent record at onboarding, right-to-withdraw, data processor agreements with Meta/Google | Platform processes customer data lawfully from first interaction; Founder protected from personal liability | 🔲 Not built — legal docs committed, platform code absent; NOT DEFERRABLE |
| P-14 | **Customer Evidence Window** | Surface the Customer Evidence Ledger to the customer (WhatsApp summary → portal view) | Customer can audit what their agent did; constitutional right is enforceable; renewal is justified | 🔲 Not built; minimum = daily WhatsApp summary; NOT DEFERRABLE |
| P-15 | **Web Portal (WC-034)** | Customer-facing portal: hire agent, view employment contract, view evidence, manage consent | Customers onboard without Founder involvement; self-service from customer #3 | ⚠ Blocked — Keycloak dependency unresolved; WC-034 in BLOCKED state |
| P-16 | **WhatsApp-First Hiring Wizard** | WhatsApp-native onboarding flow for customers without portal dependency | Onboarding in a channel customers already use; lowers acquisition friction in India | 🔲 Not built — ADR-023 specified |
| P-17 | **Learning Flywheel (MBR + Agent Improvement)** | Monthly Business Review data collection from day 1; agent performance improvement cycle | WAOOAW agents demonstrably improve month-over-month; competitive moat vs. static AI tools | 🔲 Not built — data collection must start at first customer; processing deferred to month 2 |

---

## 5. Customer Journey × Pillar Intersection Map

Which pillars are embedded in the customer journey (cannot be separated) vs. genuinely parallel:

| Customer Journey Step | Pillar(s) Required | Sequencing |
|---|---|---|
| Agent executes first campaign | P-12 DMA Agent v1, P-08 Trust Layer | **Must exist before customer #1** |
| Onboarding consent | P-13 DPDPA Compliance Spine | **Embedded — ships with DMA Agent** |
| Customer sees what agent did | P-14 Evidence Window v1 | **Embedded — ships with DMA Agent** |
| Billing for agent actions | P-09 Billing Engine | ✅ Already built |
| Constitutional validation of every action | P-01 CE, P-03 Emergency Stop | ✅ Already built |
| Immutable audit record | P-04 Audit Trail Sink | ⚠ Backlog P0 — needed before public launch |
| Self-service onboarding (customer #3+) | P-15 Web Portal | Deferred — Yogesh onboards #1 manually |
| Distribution via agencies | P-10 Agency Engine | Parallel — design now, code month 3 |
| Agent improves over time | P-17 Learning Flywheel | Data collection at #1; processing deferred |
| Agent skill expansion | P-11 Skill Architecture | Parallel — DMA v1 hardcodes 2 skills; registry formalised after |

---

## 6. High-Level Sprint Plan — Customer + Pillars Dual Track

Each sprint has a **goal** (strategic), **objective** (what gets built), and **outcome** (platform/customer state after).

---

### Sprint Wave 1 — WC-044: Customer Journey Launch

**Goal:** Make the first paying customer technically and constitutionally possible.

**Objective:**
- DMA Agent v1: `content_publish` + `ad_campaign_manager` skills as runnable Python on Professional Runtime
- DPDPA Minimum Consent Spine: consent record at onboarding + right-to-withdraw mechanism + data processor agreement template for Meta/Google
- Customer Evidence Window v1: daily WhatsApp summary of what the agent executed (uses existing Audit Trail data)
- Pillar grooming (parallel): Agency Engine design + Skill Registry ADR-043 draft

**Outcome:** Platform can serve one real customer with constitutional integrity. DMA agent connects to a real Meta account, executes real campaigns, surfaces real evidence.

**Pillars advanced:** P-12 (DMA Agent) ✅, P-13 (DPDPA Spine) ✅, P-14 (Evidence Window v1) ✅

---

### Sprint Wave 2 — WC-045: Customer #1 Live + Flywheel Seed

**Goal:** Land customer #1. Start the data collection that will power the learning flywheel.

**Objective:**
- Manual onboarding of customer #1 (Yogesh executes employment contract + Meta token setup)
- MBR data schema and collection hooks (no processing yet — record exists from day 1)
- Agent Performance Report v1 (auto-generated from Audit Trail; evidence-backed; no LLM)
- Evidence Window v2: structured summary with campaign metrics (clicks, impressions, posts executed)
- Pillar grooming: Keycloak investigation for WC-034 unblock; Agency Engine v1 IB item opened

**Outcome:** First revenue-generating customer on the platform. Constitutional model proven in production. Flywheel data seeded from day 1.

**Pillars advanced:** P-14 (Evidence Window v2) ✅, P-17 (Flywheel data collection begins) ⚠ partial

---

### Sprint Wave 3 — WC-046: Self-Service Gate (Web Portal Unblock)

**Goal:** Platform onboards customers without Founder involvement.

**Objective:**
- Web Portal minimum viable: Keycloak resolved + hire agent + employment contract view + consent capture in portal
- WhatsApp token re-authorization flow (ADR-025 magic link — customer reconnects expired Meta token without portal)
- Provider Registry + Token Refresh Broker (completes Trust Layer — P-08)
- Pillar grooming: Agency Engine spec finalised; Skill Registry v1 design complete

**Outcome:** Customer #2 and #3 onboard self-service. Yogesh is no longer a bottleneck. Trust Layer is complete.

**Pillars advanced:** P-08 (Trust Layer) ✅, P-15 (Web Portal v1) ✅

---

### Sprint Wave 4 — WC-047: Distribution Engine

**Goal:** Open the agency/reseller distribution channel. WAOOAW can grow beyond direct sales.

**Objective:**
- Agency/Reseller Engine v1: referral code generation + commission tracking + agency portal view
- WhatsApp-First Hiring Wizard v1 (ADR-023): end-to-end onboarding via WhatsApp for customers without portal preference
- Skill Architecture v1: Skill Registry + skill-to-agent assignment; DMA Agent migrated from hardcoded to registry-driven
- Pillar grooming: Agricultural Agent spec review; Trading Agent activation planning

**Outcome:** Agencies can refer customers and earn commission. New platform distribution channel open. Skill architecture makes adding agent #2 a configuration sprint, not an engineering sprint.

**Pillars advanced:** P-10 (Agency Engine) ✅, P-11 (Skill Architecture v1) ✅, P-16 (WhatsApp Wizard) ✅

---

### Sprint Wave 5 — WC-048: Differentiation Lock-In

**Goal:** WAOOAW agents demonstrably improve over time. The competitive moat forms.

**Objective:**
- Learning Flywheel v1: first MBR analysis pipeline + agent improvement cycle (uses month 1 data collected from customer #1)
- Agent Performance Report v2: trend analysis, benchmark comparison, improvement narrative
- Constitutional Audit Trail Sink (P-04): immutable Postgres WORM implementation; every tool call persisted
- Pillar grooming: agent #2 (Agricultural or Trading) backlog grooming; Autonomy Dial spec

**Outcome:** Month-3 agent outperforms month-1 agent. Customer can see evidence of improvement. Constitutional audit is complete and durable. WAOOAW is no longer comparable to a static LLM tool.

**Pillars advanced:** P-04 (Audit Trail Sink) ✅, P-17 (Flywheel v1) ✅

---

## 7. Pillar Status Summary — Post-Decision Roadmap

| Pillar | Current Status | Target Sprint | Track |
|---|---|---|---|
| P-01 Constitutional Engine | ✅ Built | — | — |
| P-02 Evidence First Enforcer | ✅ Built | — | — |
| P-03 Emergency Stop | ✅ Built | — | — |
| P-04 Audit Trail Sink | ✅ Implemented/tested; deployment proof unverified | — | Foundation |
| P-05 Professional Runtime | ✅ Built | — | — |
| P-06 AI Runtime | ✅ Built | — | — |
| P-07 UDCP / Compile Gate | ✅ Built | — | — |
| P-08 Trust Layer core | ✅ Implemented/tested; real platform adapters remain | WC-045/046 | Customer Journey |
| P-09 Billing Engine | ✅ Built | — | — |
| P-10 Agency / Reseller Engine | 🔲 Not built | WC-047 | Parallel → Customer |
| P-11 Skill Architecture | ✅ Catalog + Runtime implemented/tested; agent skill depth remains | WC-045 | Customer Journey |
| P-12 DMA Agent v1 | 🔲 Not built | **WC-044** | **Customer Journey — first** |
| P-13 DPDPA Compliance Spine | 🔲 Not built | **WC-044** | **Embedded in journey** |
| P-14 Customer Evidence Window | 🔲 Not built | **WC-044 / WC-045** | **Embedded in journey** |
| P-15 Web Portal (WC-034) | ⚠ Blocked | WC-046 | Customer Journey |
| P-16 WhatsApp Hiring Wizard | 🔲 Not built | WC-047 | Parallel → Customer |
| P-17 Learning Flywheel | 🔲 Not built | Data: WC-045 · Processing: WC-048 | Parallel → Customer |

---

## 8. Guard Rails — What This Decision Does NOT Mean

The Founder's customer-first decision is not a licence to cut pillars. The following are standing constraints:

1. **P-13 DPDPA and P-14 Evidence Window ship with WC-044 or WC-044 does not ship.** These are a constitutional unit with the DMA Agent, not optional additions.
2. **No pillar is closed without a WC.** Grooming is not building. A pillar moves to ✅ only when a Work Contract closes it with passing CCTs.
3. **Agency Engine and Learning Flywheel have design commitments made now.** They enter the IB as P0 items in their target sprint waves, not as deferred ideas. Their data requirements (referral schema, MBR schema) must be defined in WC-044/045 even if the processing logic ships later.
4. **The Audit Trail Sink (P-04) exists in repository scope.** Environment deployment and customer Evidence Window proof remain hard gates before public launch.

---

## 9. Authorisation Record

| Decision | Made By | Date |
|---|---|---|
| Customer Journey takes precedence over pillar-first sequencing | Yogesh Khandge (Founder, INST-001) | 2026-08-07 |
| WC-044 scope: DMA Agent v1 + DPDPA Spine + Evidence Window v1 as a constitutional unit | Yogesh Khandge (Founder, INST-001) | 2026-08-07 |
| P-10, P-11, P-16, P-17 committed to parallel track — design now, code at designated sprint wave | Yogesh Khandge (Founder, INST-001) | 2026-08-07 |

---

*Document prepared as Founder Vision record. Handover to Enterprise Architecture (INST-004) for WC-044 IB grooming and ADR-043 (Skill Architecture) production.*  
*Next session: Founder authorises WC-044 sprint start or delegates to EA for grooming.*

---

## 10. Session Continuation — DMA Depth & Wave Plan Revision (2026-08-07 Evening)

### 10.1 Founder's Concern

After reviewing the initial wave plan, the Founder raised a critical challenge:

> *"DMA is our best bet and that's how I dreamed about WAOOAW — basically to create CMA and realised the opportunity to make it a broader agent hiring platform. I have too many ideas and business skills for Digital Marketing Agent and Sujay (a veteran in this business) will have plenty more. Customer journey launch with DMA v1 may restrict us from making DMA really an exponential value creator."*

> *"WAOOAW is generic — still it gives a uniform playground to customers irrespective of agent skills. Like Trial, Hire, Learn — customer business/context shall be done in 10 minutes with WhatsApp, our own web or mobile app."*

The concern is valid. The initial wave plan (WC-044 = DMA v1 with 2 skills) was structurally incorrect. This section documents the revised understanding and updated wave plan.

---

### 10.2 The Four Tensions Identified

**Tension 1 — "DMA v1 with 2 skills" misrepresents DMA**

The DMA spec (v3.1, 5,322 lines) defines a clear prerequisite chain:

```
Skill 0 — Customer Profiling ──────────────→ feeds everything downstream
Skill 1 — Market Research + Maturity Score → activates Phase 1 execution
  ↓
Skills 2–8 — Phase 1 (Curtain Raiser) ────→ activated for all customers
  ↓ Score 3+ (2–3 months of Phase 1 data)
Skills 9–11 — Phase 2 (Growth Engine) ────→ the exponential value
  ↓ Score 5+
Skills 12–13 — Phase 3 (Maturity) ────────→ the competitive edge
```

Running `content_publish` or `ad_campaign_manager` without Skills 0 and 1 means: no customer profile, no maturity score, no domain vocabulary, no campaign brief. That is an API wrapper, not a professional. The minimum coherent DMA unit is **Skills 0+1+2+3+4**. The spec's own Phase 1 definition is the floor, not 2 arbitrary skills.

**Tension 2 — DVE is a platform primitive being built as DMA code**

The Domain Vocabulary Engine (DVE) — the mechanism that makes DMA work identically for a dental clinic, a gym, a restaurant, and a law firm via generic tokens (`{CUSTOMER}`, `{VISIT}`, `{BOOKING_PLATFORM}`) — is not DMA-specific. It is the mechanism that makes WAOOAW generic for any business domain. If DVE is built inside a DMA sprint, the Agricultural agent and Trading agent will each need their own version. DVE belongs in the platform layer.

**Tension 3 — WC-044 mixed two different layers**

| Layer | Examples | Correct home |
|---|---|---|
| Generic Platform | Trial/Hire/Learn onboarding, Employment Contract, DPDPA consent, Evidence Window, Skill Registry, DVE | Platform — built once, used by every agent |
| DMA Agent | Skills 0–8, Campaign Brief workflow, Meta/Instagram/GBP integration, DVE instance | DMA — deeply specialised, first instance on generic platform |

Building both in one sprint causes platform decisions to get baked into agent code with no path to reuse.

**Tension 4 — Sujay hasn't reviewed the v3.1 spec**

The DMA spec was written by the platform team. Sujay's domain expertise (15+ years in digital marketing) could: validate and reprioritise Phase 1 skills, add skills the spec missed (event marketing, WhatsApp Business integration, seasonal campaigns, influencer identification), identify customer pain points the spec doesn't address, and define what evidence actually matters to a paying DMA customer. Building DMA code before Sujay validation creates technical debt that arrives on the customer's first day.

---

### 10.3 The Layer Separation Principle (New Standing Decision)

> **WAOOAW Platform Layer** — generic, identical for every agent and every customer.  
> Trial, Hire, Learn in 10 minutes via WhatsApp/web/mobile. DPDPA consent. Evidence Window. Employment Contract. Skill Registry. DVE.  
>
> **Agent Layer** — deeply specialised per domain.  
> DMA: Sujay-validated skill set, Phase 1 through Phase 3. Agricultural, Trading, Tutor: each equally deep in their domain.  
>
> **These layers are built in order, not mixed in one sprint.**

---

### 10.4 Revised Wave Plan

The original Wave 1 (WC-044 = DMA Agent v1 + DPDPA + Evidence Window) is superseded by the following:

| Wave | Sprint | Goal | Objective | Outcome |
|---|---|---|---|---|
| **1** | **WC-044** | Generic platform customer journey exists for ANY agent | 10-minute WhatsApp-first onboarding (name + location + website → Employment Contract → Trial state) · DPDPA consent generic · Evidence Window skeleton (reads Audit Trail for any agent) · Skill Registry v1 · DVE platform service · Trial → Active state machine | Any future agent — DMA, Agricultural, Trading, Tutor — can be hired through this identical flow. Platform layer is reusable, not DMA-specific. |
| **1.5** | **Sujay Workshop** *(design event, runs parallel to WC-044 — not a WC)* | DMA skill design validated and expanded by domain expert before code is written | 2–4 hour session with Sujay: validate Phase 1 skill priorities, expand skill set with domain knowledge, define what evidence a DMA customer needs to see, confirm customer persona table | Sujay-validated DMA Phase 1 design delivered into WC-045. No code written during this event. No rework after. |
| **2** | **WC-045** | DMA Phase 1 built correctly and deeply on the generic platform | Skills 0+1+1b+2+3+4+5 (Customer Profiling + Market Research + Platform Health Check + Campaign Brief + Instagram + Facebook + GBP) · DVE instance · Meta/Instagram/GBP integration on Trust Layer · Evidence Window DMA instance · Constitutional compliance (C-036 through C-057) | DMA Phase 1 is a genuinely impressive agent. Sujay-validated. Runs on generic platform. Not a prototype. Customer who hires it sees intelligence, not just posting. |
| **3** | **WC-046** | Customer #1 live with an agent that makes them an advocate | Manual onboarding by Yogesh · Meta account connection via oauth-vault · First campaign executed · Evidence Window live · First revenue collected via Razorpay | First paying customer experiences constitutional governance + DMA Phase 1 excellence. This is the story WAOOAW tells the world. |
| **4** | **WC-047** | Self-service + distribution channel opens | Web Portal unblock (WC-034) · Agency/Reseller Engine v1 · WhatsApp Hiring Wizard v2 · MBR data collection matures | Customers #2+ onboard self-service. Agencies refer customers. Yogesh is no longer the onboarding bottleneck. |
| **5** | **WC-048** | DMA Phase 2 + differentiation lock-in | Skills 9–11 (Growth Engine — activated at Score 3+ from Phase 1 data) · Learning Flywheel v1 · Constitutional Audit Trail Sink · DMA Phase 2 is the exponential value Sujay will design | Month-3 agent outperforms month-1 agent. Customer sees evidence of improvement. WAOOAW moat forms. |

---

### 10.5 What the Revision Changes vs. the Original Plan

| Original (superseded) | Revised |
|---|---|
| DMA rushed to 2 skills in WC-044 | DMA built fully in WC-045, Sujay-validated before code starts |
| Platform + DMA mixed in one sprint | Platform layer clean in WC-044 · DMA layer clean in WC-045 |
| DVE baked into DMA code | DVE in platform layer — Agricultural, Trading, Tutor inherit it for free |
| Sujay input arrives after code is written | Sujay workshop runs parallel to WC-044 — no timeline delay, no rework |
| Customer #1 experiences a 2-skill prototype | Customer #1 experiences Phase 1 at full, Sujay-validated capability |
| Every future agent needs its own onboarding flow | Every future agent runs through the same generic WC-044 platform |

---

### 10.6 Updated Authorisation Record

| Decision | Made By | Date |
|---|---|---|
| Original WC-044 scope (DMA v1 with 2 skills) — **superseded** | Session analysis | 2026-08-07 |
| Layer Separation Principle: Platform layer built generically in WC-044; DMA as first instance in WC-045 | Yogesh Khandge (Founder, INST-001) | 2026-08-07 |
| Sujay Workshop to run parallel to WC-044 before DMA code begins | Yogesh Khandge (Founder, INST-001) | 2026-08-07 |
| WC-044 scope: Generic platform customer journey (onboarding + DPDPA + Evidence Window + Skill Registry + DVE) | Yogesh Khandge (Founder, INST-001) | 2026-08-07 |
| WC-045 scope: DMA Phase 1 full implementation (Skills 0–5+, Sujay-validated) | Pending Founder confirmation after Sujay Workshop | — |

---

*Session closed 2026-08-07. Founder to review tomorrow.*  
*Next session: Confirm revised wave plan → authorise WC-044 → schedule Sujay Workshop.*

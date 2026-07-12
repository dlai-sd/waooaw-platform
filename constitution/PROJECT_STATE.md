# PROJECT_STATE.md

**Last Updated:** 2026-07-12
**Version:** 0.35.0
**Session:** 2026-07-12 — IN PROGRESS (C-053 Signal Intelligence Layer, C-054 Skill Intelligence Router, Skill Dependency Register, Secret Vault, Agent Skill Proposal Loop)

---

## IN-PROGRESS CHECKPOINT (Session 2026-07-12)

| Milestone | Status |
|---|---|
| C-053 Signal Intelligence Layer (SIL) — claim, AD-026, DP-022, Section 3.18, SQL, RLS | ✓ DONE — v0.35.0 |
| C-054 Skill Intelligence Router (SIR) — claim, AD-027, DP-023, Section 3.19, AI Runtime, SQL, RLS | pending v0.36.0 |
| Skill Dependency Register per agent | pending v0.37.0 |
| Secret Vault oauth-vault backing decision | pending v0.37.1 |
| Agent → Skill Proposal governance loop (Section 3.20, issue template) | pending v0.38.0 |
| EA Review + Founder approval | pending |
| Simulation runs (DMA, Trading, Agricultural) | NEXT AFTER THIS SPRINT |

| Milestone | Status |
|---|---|
| Track A P1 gap resolution (Trading v1.2, Agricultural v2.1) | ✓ DONE — v0.29.0 |
| R-017 + R-018 EA reviews APPROVED | ✓ DONE — v0.30.0 |
| C-050 Strategic Cognition Layer | ✓ DONE — v0.31.0 |
| C-051 Token Economy Layer (66-74% cost reduction) | ✓ DONE — v0.32.0 |
| Section 3.17 Off-Topic Boundary Standard | ✓ DONE — v0.33.0 |
| C-052 Context Fidelity + SEBI Isolation + Creative Fingerprint Uniqueness | ✓ DONE — v0.34.0 |
| NEXT SESSION: Simulation runs of all 3 agents | pending |

---

## SESSION CLOSE BRIEFING — READ THIS FIRST

```
INSTITUTION:  WAOOAW — autonomous digital professionals under constitutional governance
GATE:         G5 prerequisites met (G5 CLEAR ≠ implementation authorization)
VERSION:      0.34.0
FOCUS:        FULL SESSION ARCHITECTURE COMPLETE. 52 claims. 3 agents. 45 prompts.
              Gate 11/11 PASS for all 3 agents.
              
NEXT SESSION: Simulation runs of DMA, Trading, Agricultural agents on platform.
              Implementation: NOT authorized. Awaiting explicit Founder "start coding".

AGENTS:       DMA v2.4 | Trading v1.7 | Agricultural v2.6
CLAIMS:       C-001 through C-052 — 52 ratified claims
OPEN P1:      None.
FOUNDER NOTE: TRADING/EXECUTION/ESCALATION_DECISION (BREAKING prompt) — acknowledge before Trading IB-009 sprint.
```

---

## What This Session Completed (2026-07-11)

| Version | What |
|---|---|
| v0.29.0 | Track A P1 — Trading v1.2, Agricultural v2.1 (Sections 4+5 gate) |
| v0.30.0 | R-017 APPROVED — Trading v1.3, Agricultural v2.2 (gate full) |
| v0.31.0 | **C-050 Strategic Cognition Layer** — Section 3.15, planning + assessment prompts, Gate Section 10 |
| v0.32.0 | **C-051 Token Economy Layer** — 66–74% cost reduction; UsageUnits; 4-layer architecture; 44 prompts |
| v0.33.0 | **Section 3.17 Off-Topic Boundary** — 3-attempt graduation, 5 redirect hooks/agent, adjacent routing |
| v0.34.0 | **C-052 Context Fidelity + SEBI Isolation + Creative Fingerprint** |
| | C-052 claim ratified (52nd constitutional claim) |
| | AD-025: Real-time Cross-Customer Isolation (HARD, SEBI regulatory basis) |
| | DP-021: Creative Fingerprint Uniqueness |
| | Agent Memory Layer in ai-runtime.md: Context Bootstrap (M-1), Cross-Customer Isolation Enforcer (M-2), Creative Fingerprint Enforcer (M-3), Agricultural Timing Stagger (M-4) |
| | DMA v2.3→v2.4: C-052 check; Creative Fingerprint declared; uniqueness_score in evidence record |
| | Trading v1.6→v1.7: C-052 check; SEBI prohibition documented; Tier 3 temporal fence |
| | Agricultural v2.5→v2.6: C-052 check; per-farm independence; timing stagger declared |
| | SQL: `business.customer_creative_fingerprints` (pgvector, uniqueness tracking) |
| | SQL: `institutional.tier3_eligibility_log` (24h lag enforcement) |
| | AGENT-AUTHORING-GUIDE: C-052 added to Constitutional Checklist |

---

## What This Session Completed (2026-07-09)

| Version | What |
|---|---|
| v0.14.0–v0.19.0 | DMA v2.0 (14 skills, 3-phase bundles, billing); Simulation 004; developer gap filling; P2 SQL |
| v0.20.0 | AI-native execution layer: C-045/046/047, Prompt Library (24 prompts), AI Execution Loop, Platform Operations Agent, Reasoning Traces |
| v0.21.0 | All prompts complete; Trading/Agricultural review + simulations; AD-013/020 amendments |
| v0.22.0 | Agent Lifecycle Gate: AGENT-AUTHORING-GUIDE v2.0 (Section 14 + 15) — gate enforced |
| v0.23.0 | Agent lifecycle issue templates + label routing + copilot flow detection |
| v0.24.0 | ADR-023 WhatsApp Phone Identity for Agricultural Advisor (PR #2, R-015 APPROVED) |
| v0.25.0 | Billing: Agricultural ₹200/month UPI AutoPay, Trading ₹1,999/₹2,499, multi-agent COMBINED (PR #4, R-016 APPROVED) |
| v0.26.0 | Session close: PRs #2+#4 merged, razorpay-mcp full catalogue, R-016-01 UPI AutoPay fix |
| v0.27.0 | Ethics layer: C-048 (Information Non-Exploitation LAW) + C-049 (Honest Limitation Disclosure LAW) |
| v0.28.0 | Session close: all status updated, version incremented |

---

## SESSION CLOSE BRIEFING — READ THIS FIRST

```
INSTITUTION:  WAOOAW — autonomous digital professionals under constitutional governance
GATE:         G5 prerequisites met (G5 CLEAR ≠ implementation authorization)
VERSION:      0.26.0
FOCUS:        Full session — DMA v2.0, agent governance gate, WhatsApp identity,
              billing for all 3 agents. 3 agents approved, 2 PRs merged.
              Implementation: NOT authorized. Awaiting explicit Founder "start coding".
              
OPEN PRs:     PR #2 MERGED (WhatsApp identity ADR-023)
              PR #4 MERGED (billing + UPI AutoPay)
              
NEXT:         Founder indicated an important point to discuss — see WORK MENU below.
```

---

## What This Session Completed (2026-07-09)

| Version | What |
|---|---|
| v0.14.0–v0.15.0 | DMA v2.0: 14 skills, 3-phase bundles, portal layer, C-043, Domain 11, Architecture Chain, R-014 EA approved |
| v0.16.0 | Synthetic Approval model: C-044, AD-017, DP-015, Skill Runtime Config Standard (Section 3.14), 3 new SQL tables |
| v0.17.0 | Simulation 004 (Kiran Fitness): 25 gaps found, 4 constitutional discoveries |
| v0.18.0 | Developer simulation: proto extended, 9 OpenAPI endpoints, MCP catalogues, Temporal workflows, ADR-021/022 |
| v0.19.0 | P2 SQL completions: payment/GST tables, Fitness Studio persona, domain taxonomy, retention |
| v0.20.0 | AI-native execution layer: C-045/046/047, AD-018/019, DP-016/017/018, Prompt Library (7 prompts), AI Execution Loop, Platform Operations Agent, Reasoning Trace, 6 SQL tables |
| v0.21.0 | All 24 prompts complete (Trading + Agricultural added), simulations 005+006, AD-013/020 amendments |
| v0.22.0 | Agent Lifecycle Gate: AGENT-AUTHORING-GUIDE v2.0 (Section 14 gate + Section 15 update template), GENESIS Part 05 amended |
| v0.23.0 | Agent lifecycle issue templates (new-agent.yml + agent-update.yml), 10 new labels, copilot instruction routing |
| v0.24.0 | PR #2: ADR-023 (WhatsApp Phone-as-Identity), agricultural-advisor v2.0, phone-identity-service, TRAI compliance — R-015 APPROVED |
| v0.25.0 | PR #4: Trading billing (₹1,999/₹2,499), Agricultural billing (₹200/month WhatsApp UPI AutoPay), multi-agent COMBINED billing default |
| v0.26.0 | Session close: both PRs merged, R-016-01 fix (UPI AutoPay mandate tools), razorpay-mcp full catalogue, all status updated |

---

## Platform Status — Current

### Agents (GENESIS Part 05 Registry)

| Agent | Type | Version | EA Review | Status |
|---|---|---|---|---|
| Digital Marketing | `DIGITAL_MARKETING_HEALTHCARE` | v2.0 | R-014 | APPROVED — 14 skills, 3-phase bundles, billing ₹1,499/₹2,499/₹3,999 |
| Trading | `TRADING_FO_CRYPTO` | v1.1 + billing | R-012 | APPROVED — 5 skills, billing ₹1,999/₹2,499; Sections 4+5 gate partial (P1 before IB-009) |
| Agricultural Advisor | `AGRICULTURAL_ADVISOR_INDIA` | v2.0 | R-013 + R-015 | APPROVED — WhatsApp-native identity (ADR-023), billing ₹200/month UPI AutoPay |

### Open Infrastructure Items

| Item | Status | Blocking |
|---|---|---|
| Trading + Agricultural: Section 4 (Skill Runtime Config) and Section 5 (Execution Loop) | P1 gap per Section 16 of AGENT-AUTHORING-GUIDE | Before Trading/Agricultural IB-009 sprint |
| 3 HSM templates for Agricultural billing | Pending Meta pre-approval | Before farmer billing goes live |
| ADR-023: OAuth vault for WhatsApp voice MCP STT service | AD-020 identifies need for ADR-023 extension | Before STT service selection |
| Trading v1.2 + Agricultural v2.1 EA re-review (Track A changes) | Pending | Before implementing these agents in IB-009 sprint |

### Architecture Layers

| Layer | Status |
|---|---|
| Claims | C-001 to C-049, all RATIFIED |
| Capabilities | Domains 1–12 (Platform Operations added) |
| Drivers | AD-001 to AD-020 |
| Principles | DP-001 to DP-018 |
| ADRs | ADR-001 to ADR-023 |
| Reference Architecture | containers.md + 23 MCP servers + 2 internal services |
| Component Specs | CE + BP + PR + AIR (all updated with AI-native execution) |
| Prompt Library | 30 active prompts across 4 agent types (24 DMA + 6 Trading + 7 Agri + 1 PlatOps; 6 new added v0.29.0) |
| MCP Tool Catalogues | 11 servers + razorpay-mcp fully specified |
| Temporal Workflows | 5 workflows defined |
| Data Architecture | All tables, RLS, indexes complete |
| Local Environment | docker-compose: 23 MCP stubs + 2 internal services |

---

## WORK MENU — Present this on /resume

**WAOOAW Engineering Organization — Session 2026-07-11 (next)**
**Version:** v0.29.0 | **Gate:** G5 prerequisites met | **3 agents fully gate-compliant**

Track A is COMPLETE. All three agents now pass the full Activation Gate (Sections 1–9).
All three agents are architecturally complete. All 10 activation gate sections pass. 39 active prompts. The platform is ready for the IB-009 Foundation Implementation sprint — pending explicit Founder authorization each session.

---

**Track A — ✓ COMPLETED** (v0.29.0 + v0.30.0)
**Strategic Cognition Layer — ✓ COMPLETED** (v0.31.0, C-050, R-018 APPROVED)
**Token Economy Layer — ✓ COMPLETED** (v0.32.0, C-051, R-019 APPROVED)
**Off-Topic Boundary — ✓ COMPLETED** (v0.33.0, Section 3.17)
**Context Fidelity + SEBI Isolation + Creative Fingerprint — ✓ COMPLETED** (v0.34.0, C-052)

---

**NEXT SESSION — Simulation Runs**

*All three agents are architecturally complete. The next session will run live simulations of each agent to surface any constitutional gaps before the IB-009 implementation sprint.*

Simulation tracks:
1. **DMA Simulation** — Run a dental clinic through full lifecycle: onboarding, Skill 1 maturity report, SKILL_ACTIVATION_PLAN, content creation (uniqueness check), monthly assessment
2. **Trading Simulation** — Run a PAAS trading session: onboarding, SESSION_PREP, TRADE_SETUP, LOSS_LIMIT_ALERT escalation, SESSION_REPORT
3. **Agricultural Simulation** — Run a full farmer journey: WhatsApp onboarding, SEASONAL_ADVISORY_PLAN, morning check-in, weather alert, mandi price advice, off-topic deflection test

Each simulation will test: Strategic Cognition Layer, Token Economy (classification gate), Off-Topic Boundary, Context Bootstrap continuity, and constitutional evidence chain.

---

**Track B — New Agent specification**

*Office: Business Architect → Enterprise Architect → Founder*

Use `type:new-agent` issue template to trigger the flow for:
- Legal Professional — contract review, compliance advisory for India SMEs
- HR Professional — hiring, onboarding, performance management
- Accounting Professional — GST filing, TDS compliance, bookkeeping
- Real Estate Advisory — property search, legal due diligence

---

**Track C — IB-009 Foundation Implementation authorization**

*Requires explicit Founder "start coding" per session.*

All architecture prerequisites met. All 3 agents approved. Prompt library complete. All gaps resolved. The platform is implementation-ready for a first sprint on the Constitutional Engine skeleton. One sentence from the Founder unlocks it.

---

**Track D — Simulation runs for newer architectural components**

*Office: Business Architect + Constitutional Analyst*

No simulation covers: Synthetic Approval (C-044) activation flow, Platform Operations Agent (L1 health monitoring), or the AI Execution Loop (C-047). Running a simulation for any of these will surface constitutional gaps before implementation begins.

---

---

## SESSION CLOSE BRIEFING — READ THIS FIRST

This file is the single source of truth for the next session start. Read it top to bottom before doing anything.

```
INSTITUTION:  WAOOAW — autonomous digital professionals under constitutional governance
GATE:         G5 prerequisites met (G5 CLEAR ≠ implementation authorization)
VERSION:      0.15.0
FOCUS:        Digital Marketing Agent v2.0 APPROVED and committed.
              3 agents fully approved. Architecture chain complete and consistent.
              Implementation: NOT authorized. Awaiting explicit Founder "start coding" per session.
```

---

## What This Session Completed (2026-07-09)

| Commit | Version | What |
|---|---|---|
| v0.13.0 | Session start | Resumed from 2026-07-08 close |
| v0.14.0 | digital-marketing-agent.md v2.0 | 6 new skills (0: Customer Profiling, 1: Market Research, 10: SEO, 11: PPC, 12: CRO, 13: Competitive Intelligence); 3-phase bundle packaging (Curtain Raiser / Growth Engine / Maturity Phase); portal sales presentation layer; AI-native onboarding flow; updated Professional Template |
| v0.14.1 | Architecture Chain Run (Section 11) | C-043 (Financial Spend Cap LAW); Domain 11 capabilities (6 caps); AD-016 (Budget Hard Cap); DP-014 (Maturity-Driven Skill Activation); containers.md — 18 MCP servers added; ai-runtime.md — Profiling Pipeline + Market Research Pipeline; 5 new SQL tables; docker-compose — 18 new MCP stub services (ports 8105–8122) |
| v0.14.2 | R-014 EA Review — APPROVED | 5 P1 findings fixed: C-043 Produces corrected; social-profile-mcp auth ambiguity resolved; CE.ValidateAction in Market Research Pipeline; PATIENT_IMAGE_CONSENT_CONFIRMED resolved (R-011 note closed); capability-to-container-map.md updated with Domain 11 |
| v0.15.0 | Session close | All statuses updated; GENESIS registry updated; Founder approval granted; committed and pushed |
| v0.16.0 | Synthetic Approval + Skill Runtime Operating Standard | C-044 (Synthetic Approval LAW); AD-017 (Confidence Gate HARD); DP-015 (Learned Delegation); Capability 4.6; Skill Runtime Config Standard (Section 3.14) — approval ladder, cadence, narrative, self-governance, API budget; AI Runtime Pipelines 8+9 (Synthetic Approval + Self-Governance); SQL — 5 new ENUMs, 3 new tables (skill_runtime_configurations, synthetic_approval_records, skill_self_governance_log); P2 fixes from R-014 (execution_model_type + 3 VARCHAR→ENUM) |
| v0.17.0 | Simulation 004 — Kiran Fitness Studio Bangalore | Full lifecycle simulation. 25 gaps: 4 P0, 8 P1, 13 P2. 4 constitutional discoveries (CD-001 through CD-004). C-045 candidate. ADR-021/022 identified. |
| v0.18.0 | Developer simulation — fill all spec gaps | Proto extended (BudgetContext, SyntheticApprovalContext, ApprovalType). 9 new OpenAPI endpoints. RLS for 8 tables. MCP Tool Catalogues. 5 Temporal workflow definitions. ADR-021 (OAuth vault). ADR-022 (Razorpay India + GST). 5 new infrastructure containers. ADR-INDEX updated. |
| v0.19.0 | P2 complete: Payment/GST tables, Fitness Studio, OAuth/retention, domain taxonomy | SQL: +organisations/contracts/profile/skill_config columns; business_domain_taxonomy; payment_transactions; gst_invoices; data_retention_records. Agent spec: Fitness Studio persona, Skill 7/8 fixes. ADR-021 GA4 + token revocation. |
| v0.20.0 | AI-native execution layer — constitution through local environment | C-045 (Prompt=Constitutional Artifact LAW); C-046 (Platform under governance LAW); C-047 (Agent-Driven Execution LAW). AD-018 (Prompt Versioning HARD); AD-019 (Agent-Driven Orchestration HARD). DP-016/017/018. Domain 12 (Platform Operations, 5 capabilities). Reasoning Trace spec + SQL schema. Prompt Library: README + 7 core DMA+CE+Ops prompts with output schemas. Agent Execution Loop spec (the fundamental C-047 shift). Platform Operations Agent spec (L1/L2/L3, 4 skills, agent comms protocol, capability registry). CE proto: reasoning_trace_id in ValidateAction. AI Runtime: Prompt Registry + Execution Loop Coordinator + Reasoning Trace Writer components. SQL: agent_prompt_versions (seeded), agent_reasoning_traces, agent_capability_registry, agent_messages, platform_operations_events, agent_health_scores. RLS/grants for institutional schema. New containers: platform-operations-mcp (8126), prompt-registry-mcp (8127). |
| v0.21.0 | Prompt library complete + Trading/Agricultural review + Simulations 005+006 | 9 missing DMA prompts completed (total 24 active). GENESIS Part 05 prompt governance. Trading Agent: C-043 added, 3 prompts, 3 missing MCPs (market-data-mcp 8132, crypto-exchange-mcp 8133, nse-calendar-mcp 8134). Agricultural Advisor: 4 prompts, 2 missing MCPs (enam-mcp 8135, government-scheme-mcp 8136). AD-013 amended (distributed onboarding for C-042). AD-020 (STT India Regional Languages HARD). Simulation 005 (Rahul Trading Pune): 10 gaps, 2 constitutional discoveries. Simulation 006 (Suresh Agricultural Nagpur): 8 gaps, 2 constitutional discoveries. SQL: weather_alert_log +imd_warning_id/stt_confidence; farmer_profiles +WhatsApp/language; trading_profiles table; trading_session_records table. |

---

## What This Session Completed (2026-07-08)

| Commit | Version | What |
|---|---|---|
| v0.12.0 | Architecture simulation | 9 layer gaps found + fixed for 2 new agents (Agricultural, Trading) |
| v0.12.1 | R-013 + AGENT-AUTHORING-GUIDE | EA review of Agricultural Agent (3 P0 fixes); guide expanded to 13 sections |
| v0.12.2 | GENESIS AS-005 ratification | Agricultural Agent approved by Founder; GENESIS registry of 3 ratified agents |
| v0.13.0 | Session close | PROJECT_STATE updated; ready for next session |

---

## Platform Status — Snapshot

### Agents (GENESIS Part 05 Registry)

| Agent | Type | AS | EA Review | Status |
|---|---|---|---|---|
| Digital Marketing (Healthcare/Dental) | `DIGITAL_MARKETING_HEALTHCARE` | AS-001, AS-002 | R-011 (v1.0) · R-014 (v2.0) | v2.0 APPROVED 2026-07-09 |
| Trading (F&O + Crypto) | `TRADING_FO_CRYPTO` | AS-003 | R-012 | APPROVED |
| Agricultural Advisory (India Farmers) | `AGRICULTURAL_ADVISOR_INDIA` | AS-005 | R-013 | APPROVED |

### Architecture Layers — Consistency Status

| Layer | File | Last Updated | Status |
|---|---|---|---|
| Claims | `knowledge/claims/` C-001–C-042 | v0.11.0 | ✓ Current |
| Capabilities | `knowledge/business-capabilities.md` | v0.12.0 | ✓ 10 domains, 56+ capabilities |
| Drivers | `knowledge/architectural-drivers.md` | v0.12.0 | ✓ AD-001–AD-015 |
| Principles | `knowledge/design-principles.md` | v0.12.0 | ✓ DP-001–DP-013 |
| ADRs | `adr/` | v0.9.0 | ✓ ADR-001–ADR-020 |
| Reference Architecture | `architecture/reference/containers.md` | v0.12.0 | ✓ + MCP Integration Layer |
| Component Specs | `architecture/reference/components/` | v0.12.1 | ✓ AI Runtime VTL expanded |
| Data Architecture | `infrastructure/postgres/init/` | v0.12.0 | ✓ + farmer_profiles, agent_progressive_state, weather_alert_log |
| Local Infrastructure | `docker-compose.yml` | v0.12.0 | ✓ + 5 MCP stubs (ports 8100–8104) |
| Agent Specs | `architecture/reference/agents/` | v0.12.2 | ✓ 3 approved |
| GENESIS | `constitution/GENESIS.md` | v0.12.2 | ✓ AS-005 + Ratified Types registry |

### Knowledge/Claims

42 ratified claims (C-001–C-042). Last additions:
- C-040: Domain Specialization as constitutional obligation (LAW)
- C-041: Every MCP tool call governed by Decision Space (LAW)
- C-042: Vocabulary Mandate — no technical data to low-literacy customers (LAW)

---

## Backlog Status — What Is and Is Not Open

| IB | Goal | Status | Note |
|---|---|---|---|
| IB-001–008 | Constitution through Infrastructure | DONE | All architecture layers |
| IB-009 | Foundation Implementation (skeleton) | AUTHORIZED — NOT STARTED | Requires explicit "start coding" per session |
| IB-010 | Security Architecture | DONE | R-009 approved |
| IB-011 | Engineering Quality Standards | DONE | |
| IB-012 | OpenAPI Specs | DONE | |
| IB-013 | Tech Stack ADRs 016/017/018 | DONE | |
| IB-014 | Customer Self-Service Portal (Domain 7) | WAITING — design frame exists in backlog | Does not require IB-009 for architecture work |
| IB-015 | Constitutional CS Agents (Domain 8) | WAITING — design frame exists in backlog | Does not require IB-009 for architecture work |
| IB-016 | Platform Operations Architecture | WAITING — design frame exists in backlog | Does not require IB-009 for architecture work |
| IB-017 | Phase 2 Readiness | DONE | |
| IB-018 | Agent Teams | DEFERRED — Post-MVI Enterprise | |

---

## Open Architectural Work (Non-Implementation) — Next Session Options

These are all valid pulls for the next session. No implementation gate applies to any of them.

---

## WORK MENU — Present this on /resume

> When the next session starts with `/resume`, read this section and present these options to the Founder verbatim. Do not re-derive from INSTITUTIONAL_BACKLOG.md — this menu is already filtered, gate-checked, and sequenced.

---

**WAOOAW Engineering Organization — Session 2026-07-09 (next)**
**Version:** v0.15.0 | **Gate:** G5 prerequisites met | **3 agents fully approved**

Digital Marketing Agent v2.0 approved with 14 skills, 3-phase bundles, and full architecture chain. Architecture is consistent across all layers. Founder indicated a next discussion point — present the menu below and await selection.

---

**Track A — Digital Marketing Agent simulation (new v2.0 skills)**

*Office: Business Architect (narrative) + Constitutional Analyst (claims extraction)*

The DMA v2.0 introduced Customer Profiling, Market Research, and the maturity score model. No simulation case exercises these new skills yet. Running a simulation of a new customer onboarding (Dr. Mehta or Sana) through the full v2.0 flow — registration → profiling conversation → market research → Maturity Report → Phase Bundle selection — would validate the constitutional constraints and potentially surface new claims (e.g., around the maturity scoring rubric, the AI-native interview interaction, or the budget enforcement chain). The same simulation process that produced C-042 from the agricultural agent design.

---

**Track B — New agent specification**

*Office: Business Architect (spec) → Enterprise Architect (review) → Founder (approval)*

Candidates the Founder mentioned or that are logically next for the Indian SME market:
- **Legal Professional** — contract review, compliance advisory for India SMEs
- **HR Professional** — hiring, onboarding, performance management for SMEs
- **Accounting Professional** — GST filing, TDS compliance, bookkeeping for India SMEs
- **Real Estate Advisory** — property search, legal due diligence for India buyers

Process: 13-section AGENT-AUTHORING-GUIDE + Architecture Chain Update (Section 11) + EA review + Founder approval + GENESIS amendment.

---

**Track C — Portal and CS agent architecture (IB-014 + IB-015)**

*Office: Business Architect + Solution Architect*

IB-014 (Domain 7 — Customer Self-Service Portal): 8 capabilities, 2 missing OpenAPI endpoints.
IB-015 (Domain 8 — Constitutional Customer Success Agents): CS agent specs (L1 + L2). First agent type where WAOOAW itself is the customer — interesting constitutional territory.

---

**Track D — Red Team + Confidence Register refresh**

*Office: Constitutional Analyst*

- C-043 (Financial Spend Cap) not yet in RED_TEAM.md — does it open attack surfaces?
- `knowledge/confidence-register.md` needs C-036–C-043 entries
- `knowledge/index.md` needs v0.14.x–v0.15.0 entries
- DMA v2.0: do the new MCP servers (meta-ads, google-ads, social-profile) open new attack vectors?

---

**Track E — Foundation Implementation (IB-009)**

*Requires explicit Founder "start coding" authorization for the session.*

G5 prerequisites met. All architecture approved. Implementation can begin when Founder authorizes. The first sprint would implement the Constitutional Engine skeleton + basic Professional Runtime + one acceptance scenario.

---
- A TO-DO list, a GitHub Issue, a Work Contract, a P0 label is NOT authorization
- Before any file in `src/`: STOP. Ask: "Do you authorize implementation for this session?"
- Code from v0.10.0 (commit dfbaf0b) can be restored with `git checkout dfbaf0b -- src/`

**Vocabulary Mandate (C-042) — design pattern established:**
- Any agent serving low-literacy customers: Vocabulary Translation Layer is mandatory (DP-013)
- Structural enforcement — not a prompt instruction
- AD-015: voice-primary interface for C-042 agents

**Architecture Chain Protocol (AGENT-AUTHORING-GUIDE Section 11):**
- Every new agent spec: 10 layers must be reviewed/updated alongside the spec
- Every agent update: targeted layer list by change type
- Every PR with agent changes: Architecture Chain Update table required in PR body
- Simulation runs validate correctness; the checklist prevents drift

**Constitutional design landmark (R-013 finding):**
- C-023 Evidence First → PMFBY insurance evidence chain: zero additional implementation effort
- First case of a constitutional compliance mechanism delivering direct customer financial benefit
- Pattern to apply to future agents: what other compliance mechanisms can become customer benefits?

**Three-tier RAG architecture (ADR-019):**
- Tier 1: Domain Knowledge (WAOOAW IP, shared per professional type)
- Tier 2: Customer Context (private per tenant, pgvector in business schema)
- Tier 3: Platform Intelligence (aggregate anonymized patterns, WAOOAW IP)
- Static data (ICAR, NBSS&LUP, etc.) = Tier 1 RAG, not MCP servers

**MCP Architecture (ADR-020, C-041):**
- AI Runtime is the MCP client
- CE.ValidateAction before every MCP tool call — enforced in AI Runtime, not MCP servers
- MCP servers are stateless adapters only: no business logic, no state
- 5 servers defined: weather-ensemble, agmarknet, whatsapp-voice, broker-api, whatsapp-business
- enam-mcp, policy-data-mcp: DEGRADABLE, deferred to Skills 3/5 implementation

---

## Git History — Key Commits

| Commit | Version | Description |
|---|---|---|
| 4e36f23 | v0.11.0 | Agricultural Agent DRAFT + C-042 |
| 1e59a33 | v0.12.0 | Architecture simulation — 9 gaps fixed |
| c118f30 | v0.12.1 | R-013 + AGENT-AUTHORING-GUIDE 13-section protocol |
| 03a4906 | v0.12.2 | GENESIS AS-005 ratification |
| (this) | v0.13.0 | Session close |
| dfbaf0b | v0.10.0 | VIOLATION — src/ code (removable with git checkout) |

| Milestone | Status |
|---|---|
| R-011 EA review digital-marketing-agent.md | ✓ DONE — APPROVED WITH NOTE |
| Institutional schema in postgres init | ✓ DONE |
| CE skeleton: .NET 9 gRPC + RecordEvidence | ✓ DONE |
| BP skeleton: .NET 9 REST + JWT + /health | ✓ DONE |
| PR skeleton: Python FastAPI + /health + WS stub | ✓ DONE |
| AI Runtime skeleton: Python FastAPI + /health | ✓ DONE |
| CCT-EF-01: Evidence First test | ✓ DONE — pattern + stub |
| v0.10.0 commit + push | ✓ DONE |

---

## RESUME BRIEFING — IB-009 Sprint 2 Next

### Where we are
```
Version:  0.10.0  |  Gate: G5 IN PROGRESS  |  4 service skeletons committed
Services: CE (gRPC + RecordEvidence) | BP (REST + Evidence First) | PR (WS stub) | AI (MCP stub)
CCT-EF-01: pattern verified, integration test skeleton in tests/constitutional/bp/
```

### TO-DO LIST — Next Session (Sprint 2)
**P0 — Make docker compose up work:**
1. Run `./scripts/setup.sh` — verify all services start with /health = 200
2. Fix any startup issues (proto compile, DB migration, JWT config)
3. Run CCT-EF-01 against live services (TestContainers)

**P1 — Sprint 2 implementation:**
4. CE: EF Core InitialBaseline migration (engineering-standards §9)
5. BP → CE: gRPC connection working end-to-end (not stub)
6. PR Emergency Stop: CE.TriggerEmergencyStop + Temporal signal (ADR-018)
7. CCT-HO-01: Emergency Stop latency ≤250ms measured

**P1 — Trading Agent specification:**
8. `architecture/reference/agents/trading-agent.md` (AS-003 — FO/Crypto trader)

---

**Previous Session Reference:** v0.9.0 — Digital Marketing Agent + RAG/MCP

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| Claims C-040/041 + GENESIS Agent Protocol | ✓ DONE |
| ADR-019 RAG + ADR-020 MCP architecture | ✓ DONE |
| AI Runtime component spec update | ✓ DONE |
| Agent Authoring Guide (template) | ✓ DONE |
| Digital Marketing Agent specification | ✓ DONE |
| v0.9.0 commit + push | ✓ DONE |

---

## RESUME BRIEFING — Updated

### Where we are
```
Version:  0.9.0  |  Claims: C-001–C-041  |  ADRs: 20  |  Agent Specs: 1
Architecture COMPLETE. Digital Marketing Agent fully specified. Implementation AUTHORIZED.
```

### TO-DO LIST — Next Session
**P0:** IB-009 — Foundation Implementation (first working code)
**P1:** EA review of digital-marketing-agent.md (pending) → Founder approval
**P1:** Trading Agent specification (AS-003 — FO/Crypto trader)
**P1:** ADR-019 institutional schema creation (add to postgres init scripts)

---

**Previous Session Reference:** v0.8.0 — Skills, Performance, Billing, Conversational Config

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| New claims C-036 to C-039 | ✓ DONE |
| Capabilities + drivers + principles (BA) | ✓ DONE |
| Domain model + containers (EA) | ✓ DONE |
| Component specs: BP + AI Runtime (SA) | ✓ DONE |
| Data architecture: skills + perf + billing (DA) | ✓ DONE |
| OpenAPI: skill + subscription + performance (SA) | ✓ DONE |
| v0.8.0 commit + push | ✓ DONE |

---

## RESUME BRIEFING — Updated for next session

### Where we are
```
Version:  0.8.0  |  Gate: G5 CLEAR  |  Claims: C-001–C-039 | Capabilities: 42+
Status:   Architecture COMPLETE and fully percolated. Implementation AUTHORIZED.
```

### TO-DO LIST — Next Session
**P0:** IB-009 Foundation Implementation — first working code sprint
**P1:** IB-014 API addenda (SA) | IB-016 Platform Ops | ADR-019 (institutional data store)
**Founder one-time:** GitHub Project matrix view setup

---

**Previous Session Reference:** v0.7.0 — FR-002/003/004

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| FR-002/003/004 recorded | ✓ DONE |
| Trial fields: domain model + DB + OpenAPI | ✓ DONE |
| Institutional learning zone + data classification | ✓ DONE |
| IB-018 Agent Teams (deferred) | ✓ DONE |
| v0.7.0 commit + push | ✓ DONE |

---

## RESUME BRIEFING — Updated for next session

### Where we are
```
Version:  0.7.0  |  Gate: G5 CLEAR  |  Epoch: 1 — Employment
Status:   Architecture COMPLETE. Implementation AUTHORIZED. First sprint not yet started.
Active FRs: FR-001 (CS Agents) | FR-002 (Trial) | FR-003 (Learning IP) | FR-004 (Teams — deferred)
```

### TO-DO LIST — Next Session

**P0 — Start the first development sprint:**
1. `@copilot You are Product Owner. Produce Sprint Plan for Sprint 1.` → `/approved` → create IB-009 issue → assign to @copilot
2. IB-009 targets: CE RecordEvidence stub + /health | BP /contracts + JWT | PR Emergency Stop | AI /health | CCT-EF-01

**P1 — Parallel:**
3. IB-014 API addenda (SA, 30 min): /contracts/{id}/status + /professional-templates
4. IB-016 Platform Operations: OTel metrics + P0 runbooks
5. ADR-019: Institutional learning data store decision (pgvector vs external — FR-003 consequence)

**Founder one-time:**
6. GitHub Project matrix view setup (UI, 10 min)
7. OD-003: DA scope boundary review (operational-discoveries.md)

---

**Previous Session Reference:** v0.6.0 — Agent Efficiency Baseline

---

## RESUME BRIEFING — Read this on /resume

### Where we are
```
Version:  0.6.0  |  Gate: G5 CLEAR  |  Epoch: 1 — Employment
Status:   Architecture COMPLETE. Implementation AUTHORIZED. First sprint not yet started.
```

### What was accomplished (2026-07-07 full day)

| Phase | Status |
|---|---|
| Architecture (G2–G4): 35 claims, 26 capabilities, 18 ADRs, all reference docs | ✅ |
| Phase 2 Readiness: CI/CD, CCT framework, DB init, Keycloak realm, Dockerfiles | ✅ |
| GitHub Operating Model: issue templates, PM workflow, Office 12, 67 labels live | ✅ |
| Agent Efficiency: AGENT-ENTRY.md, ADR-INDEX.md, COMPONENT-QUICK-REF.md, 5 office cards | ✅ |
| Spec gaps: emergency-stop-ws.md, ARCHITECTURE.md, CHANGELOG.md, commitlint.config.js | ✅ |
| **IB-009 Foundation Implementation — NOT STARTED** | ⬜ NEXT |

---

### TO-DO LIST — Next Session

**P0 — Start the first development sprint:**

1. Create Sprint 1 GitHub Issue and assign to @copilot:
   - Template: `.github/ISSUE_TEMPLATE/ib-implementation.yml`
   - Fill: IB-009, office:runtime-professional, sprint:1, gate:G5, component:all
   - Or invoke PO first: `@copilot You are Product Owner. Produce Sprint Plan for Sprint 1.`

2. IB-009 targets per service (first working code):
   - CE: /health (gRPC health) + RecordEvidence stub
   - BP: /health + POST /api/v1/employment/contracts + JWT middleware + EF Core baseline
   - PR: /health + Emergency Stop WebSocket
   - AI: /health + LLM inference stub
   - First CCT to pass: CCT-EF-01 (Evidence First)

**P1 — Parallel to IB-009:**

3. IB-014 API addenda (SA, 30 min): add /contracts/{id}/status + /professional-templates
4. IB-016 Platform Operations (PA): OTel metric names + P0 runbooks

**Founder one-time (GitHub UI, 10 min):**

5. Create GitHub Project "WAOOAW Platform Matrix" with views:
   Sprint Execution | Customer Readiness | NFR Coverage
   Labels are live — filter by component:* and domain:*

**Deferred (do not start without Founder decision):**

6. OD-003: DA scope boundary review (work-contracts/operational-discoveries.md)
7. AI Architect sprint (GAP-006b): LLM failover, UNCERTAIN PAAS path, token budget

---

### Efficiency: How the agent should start tomorrow

```
1. constitution/AGENT-ENTRY.md          ← routing + current state (200 lines)
2. adr/ADR-INDEX.md                     ← all 18 ADRs (18 lines)
3. .github/agent-context/office-{name}.md  ← charter (50 lines)
4. Work Contract + COMPONENT-QUICK-REF.md
```
This saves ~25,000 tokens before the first line of code.

---

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| ADR-INDEX.md + AGENT-ENTRY.md | ✓ DONE |
| COMPONENT-QUICK-REF.md | ✓ DONE |
| Office Quick-Start cards (.github/agent-context/) | ✓ DONE |
| BOOTSTRAP updated to use indices | ✓ DONE |
| GitHub labels script + create labels | ✓ DONE — 67 labels live on repo |
| CB-001 CB-002 fixes + emergency-stop-ws.md | ✓ DONE (CB-001/002 already resolved; ws spec produced) |
| ARCHITECTURE.md CHANGELOG.md commitlint | ✓ DONE |
| v0.6.0 commit + push + session memory | ✓ DONE |

---

## What v0.6.0 Delivered

### Agent Efficiency Index Layer (60-70% token reduction)
- `constitution/AGENT-ENTRY.md` — master routing file (200 lines replaces 3,000+ lines of scanning)
- `adr/ADR-INDEX.md` — all 18 ADRs in 18 lines; full ADRs fetched only when needed
- `architecture/reference/COMPONENT-QUICK-REF.md` — all 4 services, CCT targets, DB permissions, latency budgets in one page
- `.github/agent-context/office-*.md` — 5 office quick-start cards (50 lines each vs 880-line ORGANIZATION.md)
- BOOTSTRAP updated: Step 3 + 5 now route through index layer first

### GitHub Operational Setup
- `scripts/setup-github-labels.sh` — 67 labels created and live on `dlai-sd/waooaw-platform`
- Labels cover: type, office, component, domain, gate, sprint (1-10), status, priority, awaiting

### Specification Gaps Closed
- `architecture/reference/api-specs/emergency-stop-ws.md` — WebSocket frame format, connection lifecycle, reconnection strategy, heartbeat, latency budget per segment (R-010-01 outstanding finding)
- CB-001/CB-002 verified as already resolved in actual files (were simulation-only findings)

### GENESIS Repository Contract Fulfilled
- `ARCHITECTURE.md` — altitude map, 4 services, ADR link, constitutional traceability
- `CHANGELOG.md` — full history v0.1.0 through v0.6.0
- `commitlint.config.js` — enforces conventional commits + `constitutional` type

## Next Session — IB-009 Foundation Implementation (Sprint 1)

**Office:** Runtime Professional  
**Branch pattern:** `ib/009/{component-slug}`  
**Start with:** `./scripts/setup.sh` → verify `docker compose up` works → first CCT

**Reminder for session start:**
1. Read `constitution/AGENT-ENTRY.md` FIRST (not BOOTSTRAP directly — it routes you through indices)
2. Read `adr/ADR-INDEX.md` (not individual ADRs)
3. Read `.github/agent-context/office-runtime-professional.md` (not full ORGANIZATION.md)
4. Read your Work Contract + COMPONENT-QUICK-REF.md

This order saves ~25,000 tokens before the first line of code.

---

**Previous Session Reference:** v0.5.0 — GitHub Operating Model Baseline

## Current Status

| Item | Status |
|---|---|
| Architecture phase | ✅ COMPLETE |
| Phase 2 Readiness (IB-017) | ✅ COMPLETE |
| GitHub Operating Model | ✅ COMPLETE — v0.5.0 |
| IB-009 Foundation Implementation | AUTHORIZED — next sprint |
| Sprint 1 simulation | See below |

---

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| Issue templates (.github/ISSUE_TEMPLATE/) | ✓ DONE |
| CODEOWNERS | ✓ DONE |
| PR template | ✓ DONE |
| PM report workflow | ✓ DONE |
| Project automation workflow | ✓ DONE |
| copilot-instructions.md updated | ✓ DONE |
| ORGANIZATION.md Office 12 added | ✓ DONE |
| README operating commands | ✓ DONE |
| Commit + push | ✓ DONE |

---

## GitHub Operating Model — Implemented

This session delivered the full GitHub-grounded autonomous agent operating model.

**Artifacts produced:**

| Artifact | Purpose |
|---|---|
| `.github/ISSUE_TEMPLATE/ib-implementation.yml` | Structured IB issue form: IB ID, office, sprint, gate, components, domain, success criteria |
| `.github/ISSUE_TEMPLATE/ib-architecture.yml` | Architecture IB form |
| `.github/ISSUE_TEMPLATE/constitutional-blocker.yml` | CB form with blocker type, resolution path |
| `.github/ISSUE_TEMPLATE/sprint-plan-approval.yml` | Sprint plan approval with `/approved` activation pattern |
| `.github/ISSUE_TEMPLATE/config.yml` | Template chooser with backlog link |
| `.github/pull_request_template.md` | PR body: IB reference, constitutional basis, CCT coverage, spec compliance checklist |
| `.github/CODEOWNERS` | Founder (@dlai-sd) as required reviewer on all paths |
| `.github/workflows/pm-report.yaml` | Scheduled + event-driven delivery matrix report (Office 12) |
| `.github/workflows/project-automation.yaml` | Auto-label on agent assignment, blocker propagation, sprint activation on `/approved` |
| `.github/copilot-instructions.md` | Updated with GitHub issue mode, PR review mode, PM mode, branch/commit conventions |
| `constitution/ORGANIZATION.md` | Office 12 — Platform Delivery Tracker added |
| `README.md` | Operating commands section: dev env, sprint operations, status, CI/CD, label reference |

**Five operating patterns (bare minimum invocations):**
1. Sprint start: `@copilot You are Product Owner. Produce Sprint Plan for Sprint N.`
2. Sprint execution: assign GitHub Issue to `@copilot`
3. PR review: `@copilot review this PR as the Enterprise Architect`
4. Status report: `@copilot You are Platform Delivery Tracker. Status report.`
5. Sprint approval: comment `/approved` on the sprint plan issue

---

**Previous Session Reference:** Coding Agent Readiness Fixes + v0.4.0 Baseline

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| Postgres init .sh fix + TEMPORAL_DB_PASSWORD | ✓ DONE |
| buf.yaml + Dockerfile templates | ✓ DONE |
| docker-compose CE healthcheck fix | ✓ DONE |
| EF Core migration bootstrap + SET LOCAL docs | ✓ DONE |
| Keycloak dev JWT + .env.example | ✓ DONE |
| README version + v0.4.0 tag + commit | ✓ DONE |

---

## v0.4.0 Baseline Summary

Version 0.4.0 marks the completion of the full Architecture + Phase 2 Readiness phase.
The coding agent can begin IB-009 with all 7 identified confidence gaps resolved.

**Seven fixes applied this session:**
1. Postgres init: `.sql` → `.sh` (bash script, proper env var interpolation); `TEMPORAL_DB_PASSWORD` added to `.env.example`
2. Proto toolchain: `buf.yaml` + `buf.gen.yaml` in `architecture/reference/proto/`
3. Dockerfile templates: `.NET 9`, `Python 3.12`, `Next.js` in `architecture/reference/dockerfiles/`
4. docker-compose CE healthcheck: `grpc_health_probe` → `nc -z localhost 5002` (dev); web service healthcheck added
5. EF Core migration bootstrap: empty initial migration technique documented in engineering-standards.md §9
6. `SET LOCAL` interceptor: `TenantDbCommandInterceptor` pseudocode in CE + BP component specs; JWT middleware pipeline order specified
7. Dev JWT: `waooaw-dev-client` added to Keycloak realm; dev user seeded; `scripts/get-dev-token.sh` created; `DEV_TEST_USER/PASSWORD` in `.env.example`

---

**Previous Session Reference:** IB-017 Phase 2 Readiness Sprint

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| IB-017 added to backlog | ✓ DONE |
| WC-010 created (PA + EA joint sprint) | ✓ DONE |
| Engineering Quality Standards (IB-011) | ✓ DONE |
| CCT Framework specification | ✓ DONE |
| CI/CD workflows (.github/workflows/) | ✓ DONE |
| Infrastructure postgres init SQL | ✓ DONE |
| Keycloak realm JSON | ✓ DONE |
| Temporal dynamic config | ✓ DONE |
| Bootstrap script + directory structure | ✓ DONE |
| Governance close + commit | IN PROGRESS |

---

**Previous Session Reference:** FR-001 (CS Agent Path A) + IB-014/015/016 design frames

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| FR-001 recorded (Path A decision) | ✓ DONE |
| IB-014 corrected + added to backlog | ✓ DONE |
| IB-015 Path A added to backlog | ✓ DONE |
| IB-016 corrected + added to backlog | ✓ DONE |
| Governance close + commit | ✓ DONE |

---

## Current State Summary

| Item | Status |
|---|---|
| Architecture Phase (G1–G4) | ✓ COMPLETE |
| Gate G5 | ✓ CLEAR — all prerequisites met |
| Phase 2 Readiness (IB-017) | ✓ COMPLETE |
| IB-009 Foundation Implementation | **READY TO BEGIN** |

---

## Phase 2 Readiness — What Was Produced (IB-017)

**Engineering governance (IB-011 — EA):**
- `architecture/reference/engineering-standards.md` — Runtime Professional's Decision Space specification: coding standards, coverage targets, security gates, CCT mandate, OTel metric names
- `tests/constitutional/README.md` — CCT framework: 12 CCTs defined (EF-01/02, HO-01/02, AL-01/02, MT-01/02, PAAS-01, RU-01), failure procedure, template

**CI/CD pipeline (PA):**
- `.github/workflows/ci.yaml` — PR pipeline: build all 5 images, unit tests (.NET + Python + TypeScript), OpenAPI/proto lint, SAST (CodeQL), Trivy image scan, secret detection
- `.github/workflows/promote.yaml` — Merge pipeline: dev deploy, integration tests, CCTs (mandatory gate), promote to :qa on CCT pass

**Infrastructure initialization (PA):**
- `infrastructure/postgres/init/01-schemas.sql` — three constitutional schema zones
- `infrastructure/postgres/init/02-users-and-permissions.sql` — constitutional_app/business_app/runtime_app/temporal with precise grants per ledger-design.md
- `infrastructure/postgres/init/03-enums-and-tables.sql` — all enums and tables including action_instance_id, paas_sessions (GAP-004), creative_standard_embeddings (GAP-005), professional_templates (IB-015)
- `infrastructure/postgres/init/04-rls-policies.sql` — tenant isolation RLS on all tenant-scoped tables
- `infrastructure/postgres/init/05-append-only-rules.sql` — PostgreSQL RULE enforcement (belt-and-suspenders on C-007)
- `infrastructure/keycloak/waooaw-realm.json` — realm with tenant_id claim mapper, waooaw-web + waooaw-platform clients, Google IDP, 15-min token expiry
- `infrastructure/temporal/dynamicconfig.yaml` — Temporal dev configuration with PAAS-suitable 24h workflow timeout

**Dev bootstrap (PA):**
- `scripts/setup.sh` — one-command: .env → validate dirs → `docker compose up` → health checks → smoke tests
- `tests/unit/`, `tests/integration/`, `src/` directories created (GENESIS repository structure contract)

---

## Next Session — IB-009 (Runtime Professional)

**The Runtime Professional may now begin.** The development environment is governed.

Pre-flight checklist (carry forward from prior sessions):
- R006-01: `TEMPORAL_DB_PASSWORD` to `.env.example` — now handled in `02-users-and-permissions.sql` and `.env.example` needs the var
- R006-02: Healthcheck on `web` service — add to `docker-compose.yml` in IB-009
- R009: CE Container App — `ingress: internal` in Azure config
- R010-01: Produce `emergency-stop-ws.md` (WebSocket frame spec)

The Runtime Professional reads `architecture/reference/engineering-standards.md` as their Professional Standard BEFORE writing the first line of code.

---

**Previous Session Reference:** R-007 Gap Closure — EA (ADR-016/017/018) + Security Architect + Solution Architect (OpenAPI)

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| IB-010/012/013 added to backlog | ✓ DONE |
| WC-007 created (EA — ADR-016/017/018 + Emergency Stop fan-out) | ✓ DONE |
| ADR-016 language selection | ✓ DONE |
| ADR-017 web framework | ✓ DONE |
| ADR-018 Emergency Stop Temporal signal | ✓ DONE |
| Component specs updated (CE + PR — Emergency Stop fan-out) | ✓ DONE |
| WC-008 created (Security Architect) | ✓ DONE |
| Security Architecture + Threat Model produced | ✓ DONE |
| WC-009 created (Solution Architect — OpenAPI) | ✓ DONE |
| business-platform.openapi.yaml produced | ✓ DONE |
| professional-runtime.openapi.yaml produced | ✓ DONE |
| Governance records closed + Gate G5 authorized | ✓ DONE |

---

## Current State Summary

| Item | Status |
|---|---|
| Gate G2 | ✓ PASSED |
| Gate G3 | ✓ PASSED |
| Gate G4 | ✓ PASSED |
| Gate G5 | ✓ CLEAR — all R-007 P0 gaps closed |
| Architecture Phase | COMPLETE |
| Implementation | AUTHORIZED — Runtime Professional may begin IB-009 |

---

## Completed This Session

**EA Sprint 007 (IB-013) — R-008 APPROVED:**
- ADR-016: .NET 9 for CE/BP, Python 3.12 for PR/AI Runtime — rationale, alternatives, version pins
- ADR-017: Next.js 14 TypeScript PWA (Phase 1) → React Native (Phase 2)
- ADR-018: Emergency Stop Temporal signal routing — resolves GAP-003 (R-007)
- professional-runtime.md updated: PAAS session explicitly as PAASSessionWorkflow with EmergencyStop signal handler
- constitutional-engine.md updated: Temporal client dependency added (narrow, for signal routing only)

**Security Architecture Sprint 008 (IB-010) — R-009 APPROVED:**
- architecture/reference/security/threat-model.md — full STRIDE analysis, 6 threat actors, 30+ threats
- architecture/reference/security/security-architecture.md — network topology, JWT spec, secret management, OWASP Top 10, security CCTs
- GAP-006a from R-007 resolved

**Solution Architect Sprint 009 (IB-012) — R-010 APPROVED:**
- architecture/reference/api-specs/business-platform.openapi.yaml — 16 endpoints, all domain schemas
- architecture/reference/api-specs/professional-runtime.openapi.yaml — Emergency Stop, PAAS sessions, internal API
- ADR-002 (spec-first) now fulfilled
- GAP-002 from R-007 resolved

---

## R-007 Gap Closure Summary

| Gap | Severity | Resolution |
|---|---|---|
| GAP-001: Missing tech stack ADRs | HIGH | ✓ ADR-016, ADR-017 produced |
| GAP-002: OpenAPI specs missing | HIGH | ✓ Both specs produced (IB-012) |
| GAP-003: Emergency Stop fan-out | HIGH | ✓ ADR-018 — Temporal signal routing |
| GAP-006a: Security Architecture | HIGH | ✓ IB-010 complete (threat model + security arch) |
| GAP-004: PAAS session table | MEDIUM | Partially addressed — PAASSession schema in OpenAPI; `paas_sessions` DB table is IB-009 |
| GAP-005: pgvector embeddings | MEDIUM | Deferred to AI Architect sprint (IB-011 scope) |
| GAP-006b: AI Architecture | MEDIUM | Deferred (IB-011 scope) |

---

## Next Session — IB-009 (Runtime Professional)

**Authorized office: Runtime Professional (WC-010)**

Pre-flight checklist (from all reviews this session):
- R006-01: Add `TEMPORAL_DB_PASSWORD` to `.env.example`; create dedicated `temporal` DB user in postgres init scripts
- R006-02: Add healthcheck to `web` service in `docker-compose.yml`
- R006-03: Confirm AI Runtime pgvector access (`runtime_app` needs SELECT on embeddings table)
- R009 finding: CE Container App must have `ingress: internal` set
- R010-01: Produce `emergency-stop-ws.md` (WebSocket frame format, reconnection, heartbeat)

IB-009 success gate: `docker compose up` starts all services; each passes healthcheck; first CCT (Evidence First) passes; Runtime Universality skeleton test passes.

## IN-PROGRESS CHECKPOINT (update as work completes — prevents session-timeout loss)

| Milestone | Status |
|---|---|
| WC-006 created (Platform Architect) | ✓ DONE |
| R-006 (EA review of IB-008) | ✓ DONE — APPROVED |
| IB-008 DONE + backlog updated | ✓ DONE |
| Proto file produced (CA-R004-01) | ✓ DONE — constitutional_service.proto |
| Gate G4 formally closed | ✓ DONE — 2026-07-07 |

---

---

## Current State Summary

| Item | Status |
|---|---|
| Epoch 0 — Institution | ✓ Complete |
| Epoch 1 — Engineering Organization | ✓ Complete (Gate G1 passed) |
| Epoch 2 — Knowledge System | ✓ Complete (Gate G2 passed) |
| Gate G2 | ✓ PASSED — 2026-07-07 |
| Gate G3 | ✓ PASSED — 2026-07-07 |
| Gate G4 | ✓ PASSED — 2026-07-07 |
| Gate G5 | AUTHORIZED — IB-009 may begin |
| Implementation | AUTHORIZED — Runtime Professional may produce code |

---

## Last Completed Work (This Session — WC-006 + SA proto)

### Sprint 006 (Platform Architect — WC-006)
- WC-006 created
- docker-compose.yml and .env.example reviewed against component specs and all ADRs
- R-006 produced: EA review of IB-008 — **APPROVED**
- Three IB-009 implementation notes raised (R006-01 Temporal DB user, R006-02 web healthcheck, R006-03 AI Runtime pgvector access)
- IB-008 marked **DONE**

### Solution Architect — CA-R004-01 (proto file)
- `architecture/reference/proto/constitutional_service.proto` produced
- Complete gRPC interface specification for Constitutional Engine:
  - `RecordEvidence` — Evidence First Enforcer
  - `ValidateAction` — PAAS Boundary Validator
  - `GrantAuthorityLicense` / `RevokeAuthorityLicense` — Authority License Manager
  - `EvaluatePolicy` — Policy Evaluator
  - `TriggerEmergencyStop` — Emergency Stop Handler
- All message types defined with field-level constitutional basis notes
- Tenant ID via gRPC metadata (not request field) — specified in file header
- Latency budget targets documented per AD-001, AD-005

### Gate G4 Formally Closed
- All G4 items DONE: IB-005, IB-006, IB-007, IB-008, proto file
- README updated: Gate G4 PASSED, Gate G5 AUTHORIZED
- Implementation now constitutionally authorized

- R-004 produced: Constitutional Analyst review of WC-003 (Reference Architecture + Component Specs) — **APPROVED**
- R-005 produced: Business Architect review of WC-003 — **APPROVED** (all 26 capabilities verified)
- IB-005 marked DONE — Gate G3 confirmed passed
- IB-006 marked DONE — component specs accepted (proto file gap CA-R004-01 noted, required before Gate G5)

### Sprint 005 Executed (Data Architect — WC-005)

- WC-005 created: Data Architect Sprint 005 (IB-007)
- `architecture/reference/data/evidence-schema.md` produced — **complete evidence state machine specification**:
  - ABANDONED state added to evidence_state enum
  - action_instance_id column specified (missing from ledger-design.md — critical gap closed)
  - Approval-Gate vs PAAS execution model variants fully specified
  - Emergency Stop evidence record sequence specified (two-record pattern: stop event + ABANDONED records)
  - Scope-boundary confirmation event record pattern specified
  - State transition table: all valid and prohibited transitions with constitutional basis
  - constitutional_basis field format specification
  - DB enforcement approach: Constitutional Engine application-layer state machine validation
- IB-007 marked DONE

### Governance Records Updated

- `constitution/INSTITUTIONAL_BACKLOG.md` — IB-005, IB-006, IB-007 DONE; IB-008 IN_PROGRESS; index updated
- `README.md` — Gate G3 PASSED, Gate G4 IN_PROGRESS, Epoch 3 Architecture, authorized offices updated

---

## Gate G4 Remaining Work

| Item | Status | What remains |
|---|---|---|
| IB-008 — Infrastructure / Docker Compose | IN_PROGRESS | `docker-compose.yml` + `.env.example` exist (produced in prior session). Need: WC-006 (Platform Architect) created, formal review R-006 produced, IB-008 marked DONE. |
| Proto file (CA-R004-01) | OUTSTANDING | `architecture/reference/proto/constitutional_service.proto` must be produced before Gate G5. Assigned to Solution Architect scope. |

Gate G4 formally passes when IB-008 is reviewed (R-006) and `docker-compose.yml` is validated against the data architecture and component specs.

---

## Next Session Work

**IB-009 is authorized. Runtime Professional may begin foundation implementation.**

All architecture is complete. The following G5-parallel items exist and will be executed alongside IB-009:
- IB-014: Customer Portal Domain 7 + 2 API addenda (Business Architect + SA)
- IB-015: CS Agents Domain 8 Path A (Business Architect + Runtime Professional)
- IB-016: Platform Operations Architecture (Platform Architect)

Pre-flight checklist for IB-009 (from all prior reviews):
- R006-01: `TEMPORAL_DB_PASSWORD` to `.env.example`; dedicated `temporal` DB user in postgres init scripts
- R006-02: Healthcheck on `web` service in `docker-compose.yml`
- R006-03: `runtime_app` pgvector SELECT permission for AI Runtime embeddings
- R009: CE Container App must have `ingress: internal` set in Azure config
- R010-01: Produce `emergency-stop-ws.md` (WebSocket frame spec, reconnection, heartbeat)

Per R-007 — the following must be produced before the Runtime Professional starts implementation:

| Priority | Action | Office |
|---|---|---|
| P0 | ADR-016 — language selection (.NET 9 / Python 3.12) | Enterprise Architect |
| P0 | ADR-017 — web framework (Next.js / TypeScript) | Enterprise Architect |
| P0 | `architecture/reference/api-specs/business-platform.openapi.yaml` | Solution Architect |
| P0 | `architecture/reference/api-specs/professional-runtime.openapi.yaml` | Solution Architect |
| P0 | Emergency Stop fan-out mechanism specified (Temporal signal approach) | Enterprise Architect |
| P0 | Security Architecture sprint — threat model, network topology, JWT spec | Security Architect |
| P1 | `paas_sessions` table in data architecture | Data Architect |
| P1 | pgvector embeddings table for Creative Standard Profiles | AI / Data Architect |
| P1 | DP-011 — Constitutional Observability principle | Business Architect |

**Recommended next session:** Enterprise Architect — produce ADR-016, ADR-017, and Emergency Stop fan-out specification. This unblocks Security Architect and OpenAPI specs.

---

## Architecture Decisions Summary

| Decision | Choice |
|---|---|
| Deployment target | Azure India Central (Pune) |
| MVI scenarios | All 3: Dental Marketing, Beauty Artist, NIFTY Trading |
| Services | 4: Business Platform (.NET 9), Constitutional Engine (.NET 9), Professional Runtime (Python), AI Runtime (Python) |
| Workflow orchestration | Temporal (self-hosted dev → Temporal Cloud prod) |
| No Kafka | PostgreSQL event tables + Temporal queuing at MVI scale |
| No API gateway | Container Apps ingress handles routing at MVI scale |
| Mobile | Next.js PWA (Phase 1) → React Native (Phase 2) |
| Identity | Keycloak as OAuth broker — Google default, expandable |
| Observability | OpenTelemetry → Jaeger (dev) → Azure Monitor (cloud) |
| Database | PostgreSQL Flex + pgvector + Row-Level Security for multi-tenancy |
| JWT propagation | Customer JWT → gRPC metadata → PostgreSQL SET LOCAL → AI context |
| Testing | Zero manual, image promotion, Constitutional Compliance Tests |
| Cost | Dev ~INR 5-6k/month, each non-prod env within INR 10k limit |
| Evidence state machine | Append-only event records; state transitions = new INSERTs; action_instance_id groups events |
| Emergency Stop evidence | Two-record pattern: stop event record + ABANDONED records for in-flight actions |


---

## Current State Summary

| Item | Status |
|---|---|
| Epoch 0 — Institution | ✓ Complete |
| Epoch 1 — Engineering Organization | ✓ Complete (Gate G1 passed) |
| Epoch 2 — Knowledge System | ✓ Sprint 001 complete — IB-001 DONE |
| Gate G2 | ✓ PASSED — 2026-07-07 |
| Amendment A-005 | ✓ Ratified — Creative Identity as Protected Right |
| Gate G3 | Not Started — IB-002, IB-003, IB-004 now authorized |
| Gate G4+ | Blocked |
| Implementation | Constitutionally prohibited until Gate G5 |

---

## Last Completed Work

Architecture phase initiated by Founder (acting as Chief Architect):

- `architecture/100k/README.md` v0.5 — Full system context, solution layers, Docker Compose design, mobile strategy, service decomposition, Temporal orchestration, CI/CD philosophy, cost breakdown
- `architecture/32k/README.md` — Service communication, JWT propagation, API design, scaling strategy, 9 pending ADRs

Engineering governance additions to GENESIS:
- Engineering Quality Mandate (zero manual testing, image promotion pipeline)
- Constitutional Compliance Tests (WAOOAW-specific test category)
- Operations Discovery Rule

Agent infrastructure:
- `.github/copilot-instructions.md` — Copilot auto-inject entry point
- `BOOTSTRAP.md` — Updated with context and role-ask
- `standards/` — 5 professional standards

---

## Architecture Decisions Made (This Session)

| Decision | Choice |
|---|---|
| Deployment target | Azure India Central (Pune) |
| MVI scenarios | All 3: Dental Marketing, Beauty Artist, NIFTY Trading |
| Services | 4: Business Platform (.NET), Constitutional Engine (.NET), Professional Runtime (Python), AI Runtime (Python) |
| Workflow orchestration | Temporal (self-hosted dev → Temporal Cloud prod) |
| No Kafka | PostgreSQL event tables + Temporal queuing at MVI scale |
| No API gateway | Container Apps ingress handles routing at MVI scale |
| Mobile | Next.js PWA (Phase 1) → React Native (Phase 2) |
| Identity | Keycloak as OAuth broker — Google default, expandable |
| Observability | OpenTelemetry → Jaeger (dev) → Azure Monitor (cloud) |
| Database | PostgreSQL Flex + pgvector + Row-Level Security for multi-tenancy |
| JWT propagation | Customer JWT → gRPC metadata → PostgreSQL SET LOCAL → AI context |
| Testing | Zero manual, image promotion, Constitutional Compliance Tests |
| Cost | Dev ~INR 5-6k/month, each non-prod env within INR 10k limit |

---

## Completed Work (This Session)

### ADR Set Complete — 15 ADRs Formally Ratified (commit 4ec4248)

**ADR-001–009 gaps fixed:**
- ADR-001: Proto file ownership + versioning rule added
- ADR-002: Toolchain named (openapi-generator, Spectral, schemathesis)
- ADR-003: `active_contracts` removed from JWT (stale-session authorization risk)
- ADR-004: JWT transport secured — Authorization header only, never query params (OWASP A02)
- ADR-005: Replica failure recovery path added for PAAS sessions
- ADR-006: ASP.NET Core built-in rate limiting added as per-tenant backstop (zero infra cost)
- ADR-007: Concrete cloud portability escape hatch for mTLS documented
- ADR-008: Keycloak version pinning + upgrade protocol added
- ADR-009: Alert routing targets defined (P0: constitutional violations; P1: PAAS latency)

**ADR-010–015 — New ADRs ratified:**

| ADR | Decision | Roles |
|---|---|---|
| ADR-010 | Cloud Portability Posture — Azure-first, named escape hatches per Azure dependency | Enterprise Arch + Platform Arch |
| ADR-011 | Database Migration Strategy — EF Core Migrations; Audit Ledger: no destructive migrations | Data Arch + Platform Arch |
| ADR-012 | Container Image Registry — GHCR (free, cloud-agnostic, GitHub Actions native) | Platform Arch + Enterprise Arch |
| ADR-013 | CI/CD Pipeline Structure — GitHub Actions, trunk-based, CCTs as mandatory gate | Platform Arch + Enterprise Arch |
| ADR-014 | Secret Management — `.env` dev / GitHub Secrets CI / Azure Key Vault cloud | Security Arch + Platform Arch |
| ADR-015 | Temporal Deployment — self-hosted dev/QA; Temporal Cloud UAT/prod | Platform Arch + Enterprise Arch |

---

## Next Planned Work

### Immediate (Next Session)

1. **Sprint 001 Execution** — Constitutional Analyst produces knowledge claims in `knowledge/claims/` (IB-001, Gate G2)
2. **`architecture/reference/`** — C4 container/component detail specs for each service
3. **Data Architecture** — Constitutional Audit Ledger schema, RLS design, three-ledger model
4. **`.github/workflows/`** — CI/CD pipeline implementation (GitHub Actions, per ADR-013)
5. **`infrastructure/keycloak/`** — Keycloak realm export JSON (per ADR-008)

---

## Open Questions Requiring Founder Input

None currently open.

---

## Docker Compose Services (Current Design)

```
postgres          — PostgreSQL 16 + pgvector (port 5432)
keycloak          — Identity broker (port 8443)
ollama            — Local LLM for dev (port 11434)
temporal          — Workflow orchestration (port 7233)
temporal-ui       — Temporal dashboard (port 8080)
jaeger            — Distributed tracing (port 16686)
business-api      — Business Platform .NET (port 5001)
constitutional-engine — Constitutional Engine .NET (port 5002, internal)
professional-runtime  — Professional Runtime Python (port 5003)
ai-runtime        — AI Runtime Python (port 5004, internal)
web               — Next.js PWA (port 3000)
```

`docker compose up` → full stack running locally.

---

## Repository Structure (Current)

```
CONSTITUTION.md       — Constitutional law v1.2
GENESIS.md            — Engineering operating system (Parts 01-04)
ORGANIZATION.md       — Constitutional organization (10 offices)
INSTITUTIONAL_BACKLOG.md — Work queue (IB-001 to IB-005)
BOOTSTRAP.md          — Agent onboarding protocol
README.md             — Institutional state
RED_TEAM.md           — Constitutional audit (11 attacks, 0 failures)
.github/copilot-instructions.md — Copilot auto-inject
architecture/
  100k/README.md      — System context + solution layers
  32k/README.md       — Service architecture + API design
simulation/           — Constitutional Discovery Cases 001-003
standards/            — Professional standards (5 offices)
work-contracts/       — Sprint contracts + operational discoveries
blockers/             — Constitutional blockers
knowledge/            — Claims (empty — Gate G2 not yet run)
adr/                  — Architecture Decision Records (empty — pending)
```

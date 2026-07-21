# WAOOAW Platform — Program Management Office (PMO)

**Document:** Master Program Plan — Start to Go-Live
**Version:** 2.0
**Date:** 2026-07-21 (revised from v1.0 at v0.82.0)
**Owner:** Yogesh Khandge (Founder) · Sujay Khandge (Business Growth) · Ojal Khandge (Ethics Officer)
**Execution:** WAOOAW AI Agents (Platform IT Expert, Developer, QA, Legal, Content)
**Constitutional Basis:** C-064 (Three-Human Institution), C-065 (SDLC Separation), C-066 (Authorization Tiers), C-067 (Blue-Green Deployment), C-068 (Steward Access Isolation), C-071 (Quality Framework), C-073 (Constitutional Annotations)
**Platform version:** v0.95.0 (revised — v1.0 was at v0.82.0; additions marked ⬆ NEW)

---

## Executive Summary

WAOOAW is specification-complete at v0.95.0. The constitutional framework (75 ratified claims C-001→C-075), four customer-facing agent specifications (DMA v3.0, Trading v1.7, Agricultural v2.7, Private Tutor v1.0), four internal agent specifications (Platform IT Expert, Steward Assistant, Self-Improvement Analyst, Platform Operations), the constitutional UX vocabulary, legal documents, brand assets, homepage + auth modal, CI/CD pipelines, and Terraform infrastructure code are all production-ready. The platform requires one authorization from Yogesh to begin IB-009 implementation.

**Target: First paying customer by Week 10. FR-005 milestone (50 diverse customers) by Week 16.**

**⬆ NEW since v1.0:** DMA v3.0 adds 21 skills and 10 new MCPs under C-074 (On-the-Fly MCP Provisioning). C-075 (White-Label Reseller) adds agency commercial model. Steward Assistant v1.0 approved with ops.waooaw.ai interface (C-068). Self-Improvement Analyst v1.0 (C-069) and Platform Operations v1.0 added as internal agents. AI Runtime primary LLM is now Google Gemini via Vertex AI `asia-south1` Mumbai (ADR-029), not Azure OpenAI (retained as fallback only). Track 11 (Steward Interface) and Track 12 (Internal Agents) added to dependency chain.

The implementation is executed entirely by WAOOAW AI Agents under constitutional governance. The three human stewards govern, approve milestones, and provide the Azure credentials and third-party accounts. No human writes code, tests, or deploys.

---

## 1. Program Governance

### 1.1 Human Stewardship Roles (C-064)

| Person | Title | PMO Responsibility |
|---|---|---|
| **Yogesh Khandge** | Founder & Designer | Tier 3 approvals (constitutional changes) · Azure credentials · Milestone sign-off · Grievance Officer |
| **Sujay Khandge** | Business Growth & Prompt Intelligence | Tier 1/2 approvals (features, bugs) · Agent prompt quality review · Customer success oversight · Competitive intelligence |
| **Ojal Khandge** | Ethics Officer | Constitutional compliance review (C-048/C-049) · Ethics signoff on AI behavior changes · Constitutional Blocker authority |

### 1.2 AI Agent Roles (WAOOAW AI Agents)

| Agent | PMO Function |
|---|---|
| WAOOAW AI Agent — Platform IT Expert | SDLC orchestration: specs, implementation, testing, CI/CD |
| WAOOAW AI Agent — Developer | Code implementation (src/, infrastructure/, scripts/) |
| WAOOAW AI Agent — QA | CCT suites, integration tests, post-deploy verification |
| WAOOAW AI Agent — Enterprise Architect | Architecture reviews, ADR updates |
| WAOOAW AI Agent — Platform Operations | Production monitoring, incident response, SLA tracking |
| WAOOAW AI Agent — Content | Blog posts, translations, documentation |
| WAOOAW AI Agent — Legal | Legal document maintenance (DPDPA compliance updates) |

### 1.3 Decision Authority Matrix (C-066 Authorization Tiers)

| Decision type | Authority | Response SLA |
|---|---|---|
| Production outage fix | WAOOAW AI Agent — Platform IT Expert (Tier 0, autonomous) | Immediate |
| Bug fix in approved spec | Sujay approves via `approved:sujay` GitHub label | 4 working hours |
| Feature within authorized IB item | Sujay approves spec + IB has `status:authorized` | 8 working hours |
| New constitutional claim / ADR change | Yogesh approves via `/approved` PR comment | 24 hours |
| New agent specification | Yogesh (Founder Gate per AGENT-AUTHORING-GUIDE) | 48 hours |

---

## 2. Component Architecture & Dependencies

### 2.1 Dependency Chain (critical path order)

```
EXTERNAL PREREQUISITES (Founder actions — security/FOUNDER-ACTIONS.md)
  FA-003: Azure OpenAI UAE North          ← AI Runtime can't do real inference without this
  FA-002: Meta Business Manager           ← WhatsApp WABA depends on this
  FA-009: WAOOAW WABA                     ← Agricultural + DMA WhatsApp depends on this
  FA-018: Facebook App (portal login)     ← Registration flow needs this
  FA-019: Apple Developer Account         ← iPhone users need this
  FA-020: MSG91 DLT registration          ← SMS OTP fallback needs this
  FA-001: Cloudflare CDN                  ← Performance optimization (non-blocking for launch)

IMPLEMENTATION DEPENDENCY CHAIN
  ┌─ TRACK 1: Infrastructure (Week 1) ─────────────────────────────────────────┐
  │  1a. Terraform apply dev environment (all 9 services provisioned)           │
  │  1b. PostgreSQL migrations (01-06 SQL scripts applied)                      │
  │  1c. Keycloak realm imported (waooaw-realm.json) + Facebook/Apple IDPs      │
  │  1d. Temporal namespace created                                              │
  │  1e. GitHub Secrets populated (Azure credentials, DB passwords, GHCR token) │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ ALL services depend on Track 1
  ┌─ TRACK 2: Constitutional Engine (Week 2) — CRITICAL PATH ──────────────────┐
  │  CE is the single dependency of every other service.                        │
  │  2a. CE gRPC service skeleton (.NET 9)                                      │
  │  2b. RecordEvidence endpoint: writes to constitutional.audit_records        │
  │  2c. ValidateAction stub: returns AUTHORIZED (full logic in later sprint)   │
  │  2d. TriggerEmergencyStop: webhook to Professional Runtime                  │
  │  2e. CCT-EF-01 PASS (Evidence First) in live dev environment                │
  │  2f. CCT-HO-01 PASS (Emergency Stop ≤250ms) in live dev environment         │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         │ BP, PR, AIR all depend on CE
  ┌─ TRACK 3: Business Platform (Week 2-3) ────────────────────────────────────┐
  │  3a. Registration endpoint: POST /api/v1/registration/start                 │
  │  3b. Employment contracts: POST /api/v1/employment/contracts                │
  │  3c. JWT middleware (Keycloak RS256)                                         │
  │  3d. Tenant isolation (SET LOCAL app.tenant_id on every DB command)         │
  │  3e. RLS verified: customer A cannot see customer B's data                  │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 4: Professional Runtime (Week 3) ───────────────────────────────────┐
  │  4a. PAAS session management                                                 │
  │  4b. Emergency Stop WebSocket (≤250ms CCT-HO-01)                            │
  │  4c. Temporal workflow integration (agent session workflows)                 │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 5: AI Runtime (Week 3-4) ───────────────────────────────────────────┐
  │  5a. LLM Gateway: Ollama (LOCAL) + Vertex AI Gemini (MID/FRONTIER primary)  │
  │      PSE (Provider Selection Engine — ADR-029): rule engine + perf ranking  │
  │      Sarvam Saaras override for Agricultural Indian-language MID_TIER        │
  │      Azure OpenAI UAE North circuit-breaker fallback only (FA-003 key)      │
  │  5b. Input Sanitisation Layer (C-062 — prompt injection defence)            │
  │  5c. RAG pipeline: pgvector queries for Tier 1/2/3 knowledge                │
  │  5d. MCP tool executor (default deny, CE.ValidateAction before each call)   │
  │  5e. ⬆ NEW: On-the-Fly MCP Provisioning (C-074) — DB-backed mcp_registry   │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 6: Web Portal (Week 4) ─────────────────────────────────────────────┐
  │  6a. Registration + OAuth (Google, phone OTP)                               │
  │  6b. WaooaW Concierge (hero input + agent cards + persistent bubble)           │
  │  6c. Agent hiring flow (try free → pay)                                     │
  │  6d. Customer dashboard (activity feed, emergency stop, scope card)         │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 7: DMA AS-001 (Weeks 5-6) ──────────────────────────────────────────┐
  │  Goal: Dr. Mehta hires WaooaW Expert Dental Marketing → agent posts on      │
  │        Instagram → patient books an appointment.                            │
  │  ⬆ DMA v3.0 (was v2.9): 21 skills (added 7b/16/18/19/20/21)               │
  │  7a. DMA Decision Space configuration (all 21 skills)                       │
  │  7b. ⬆ 10 new MCPs via C-074 On-the-Fly Provisioning:                      │
  │      youtube, ga4, instagram-messaging, instagram-comments, booking,        │
  │      reputation, cms, whatsapp-flows, zomato, swiggy                        │
  │  7c. Google Business Profile MCP                                            │
  │  7d. WhatsApp WABA message delivery                                         │
  │  7e. Simulation 020 (DMA full Dr. Mehta Day 0→Month 3) — Grade A           │
  │  7f. ⬆ Skill 18 Agency Operations (SIM-021 Yashus Agency) — Grade A        │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 8: Agricultural AS-005 + Trading AS-003 (Weeks 6-8, parallel) ──────┐
  │  8a. Agricultural: IMD weather MCP, APMC mandi price MCP, PMFBY              │
  │      Sarvam Saaras for Hindi/Marathi/Telugu (PSE-R02 override)              │
  │  8b. Trading: Zerodha Kite Connect MCP, SEBI Tier 3 24h lag enforced        │
  │  (Founder must acknowledge TRADING/EXECUTION/ESCALATION_DECISION first)     │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 9: Private Tutor (Weeks 8-9) ───────────────────────────────────────┐
  │  9a. Whiteboard WebRTC interface                                             │
  │  9b. C-060 portal gate (no billing info to student view)                    │
  │  9c. C-061 Content Safety Scan (POCSO mandatory reporting — LAW)            │
  │  9d. Parent portal: progress reports, Emergency Stop authority               │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 10: Pilot Launch (Week 10) ──────────────────────────────────────────┐
  │  5 customers across all 4 agent types (DMA, Agricultural, Trading, Tutor)   │
  │  Constitutional compliance verified: all 50 CCTs pass in production          │
  │  Sujay: customer success monitoring active                                   │
  │  Ojal: first constitutional compliance report reviewed                       │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 11: ⬆ NEW — Steward Interface (Weeks 6-7, parallel with Track 8) ───┐
  │  Goal: Yogesh/Sujay/Ojal can access ops.waooaw.ai (C-068)                  │
  │  11a. ops.waooaw.ai subdomain + Google OAuth 3-account allowlist            │
  │  11b. Steward Assistant v1.0 — FRONTIER always, ADR-028                    │
  │  11c. Approvals queue (Yogesh) + Agent Intelligence Hub (Sujay)             │
  │  11d. C-048/C-049 ethics dashboard (Ojal)                                   │
  │  11e. Constitutional Blocker filing form (→ auto blocker file + GH Issue)   │
  └──────────────────────────────────────┬──────────────────────────────────────┘
  ┌─ TRACK 12: ⬆ NEW — Internal Agents (Weeks 7-9, parallel with Track 9) ─────┐
  │  Goal: Platform self-governance agents live before first customer            │
  │  12a. Self-Improvement Analyst v1.0 (C-069) — prompt improvement loop       │
  │       C-049 escalations → analysis → proposal → Sujay approval              │
  │  12b. Platform Operations v1.0 — Azure Monitor + 6h CCT health cycle        │
  │       Automated incident detection + P0 escalation to Yogesh               │
  │  12c. White-Label Reseller (C-075) — agency.agency_staff schema             │
  │       Skill 18 multi-client dashboard for agency AM                         │
  └──────────────────────────────────────┬──────────────────────────────────────┘
```

---

## 3. Milestone Schedule

### Phase 1 — Foundation (Weeks 1-4)

| Milestone | Week | Owner | Gate |
|---|---|---|---|
| **M1**: Terraform apply — dev environment live (all 9 services) | 1 | WAOOAW AI Agent — Developer | Yogesh provides Azure credentials |
| **M2**: DB migrations complete in dev PostgreSQL | 1 | WAOOAW AI Agent — Developer | M1 complete |
| **M3**: Constitutional Engine CCT-EF-01 + CCT-HO-01 PASS in dev | 2 | WAOOAW AI Agent — QA | M1 complete |
| **M4**: Business Platform — registration + hire endpoints live | 3 | WAOOAW AI Agent — Developer | M3 complete |
| **M5**: Professional Runtime — PAAS + Emergency Stop live | 3 | WAOOAW AI Agent — Developer | M4 complete |
| **M6**: AI Runtime — LLM Gateway + RAG pipeline live | 4 | WAOOAW AI Agent — Developer | M5 complete |
| **M7**: Web Portal — registration + WaooaW Concierge + dashboard | 4 | WAOOAW AI Agent — Developer | M4 complete (parallel with M5/M6) |

**Phase 1 exit criterion:** A test user can register on the portal, hire a (stub) WaooaW Expert, and Emergency Stop works in ≤250ms.

### Phase 2 — First Acceptance Scenario (Weeks 5-6)

| Milestone | Week | Owner | Gate |
|---|---|---|---|
| **M8**: DMA Decision Space live in dev (v3.0 — 21 skills, 10 new MCPs via C-074) | 5 | WAOOAW AI Agent — Developer | M6 complete + Instagram MCP configured |
| **M9**: Dr. Mehta (AS-001) — complete hire flow works | 5 | WAOOAW AI Agent — QA | M8 complete |
| **M10**: DMA first post sent to Instagram in dev | 5 | Sujay reviews output | M9 complete + Sujay approval |
| **M11**: AS-001 passes in QA environment | 6 | WAOOAW AI Agent — QA | Blue-green QA deploy |
| **⬆ M11b**: Steward Interface (ops.waooaw.ai) live in dev | 6-7 | WAOOAW AI Agent — Developer | M4 + C-068 OAuth configured |

**Phase 2 exit criterion:** Dr. Mehta can hire WaooaW Expert Dental Marketing, the agent posts content, a patient can message via WhatsApp. Sujay reviews the post quality. Ojal reviews constitutional compliance.

### Phase 3 — All Agents (Weeks 7-9)

| Milestone | Week | Owner | Gate |
|---|---|---|---|
| **M12**: Agricultural AS-005 — Suresh crop advisory working (Sarvam Saaras Marathi) | 7 | WAOOAW AI Agent — Developer | WABA live + FA-009 complete |
| **M13**: Trading AS-003 — Rahul trade brief working | 7-8 | WAOOAW AI Agent — Developer | Yogesh acknowledges ESCALATION_DECISION |
| **M14**: Private Tutor AS (Priya) — parent config + first lesson (C-060/C-061 gates) | 8-9 | WAOOAW AI Agent — Developer | C-060 portal gate implemented |
| **M15**: All 4 agent types in QA — all 50 CCTs pass | 9 | WAOOAW AI Agent — QA | M12 + M13 + M14 complete |
| **⬆ M15b**: Self-Improvement Analyst + Platform Operations live | 8-9 | WAOOAW AI Agent — Developer | M6 complete |
| **⬆ M15c**: White-Label Reseller (C-075) — Yashus Agency AS (SIM-021 Grade A) | 9 | WAOOAW AI Agent — Developer | M8 + agency schema migration |

### Phase 4 — Pilot Launch (Week 10)

| Milestone | Week | Owner | Gate |
|---|---|---|---|
| **M16**: UAT environment live (same as QA, separate RG) | 9 | WAOOAW AI Agent — Developer | M15 complete |
| **M17**: Pilot: 5 customers onboarded (at least 1 per agent type) | 10 | Sujay (customer success) | M15 + WABA + Razorpay live |
| **M18**: First payment received via Razorpay | 10 | Yogesh (billing verification) | M17 complete |

### Phase 5 — Scale to FR-005 (Weeks 11-16)

| Milestone | Week | Owner | Gate |
|---|---|---|---|
| **M19**: Skill 14 (WAOOAW self-marketing) activated | 11 | Sujay | FR-005 stat gate: 50+ customers |
| **M20**: Production environment live (Terraform prod apply) | 11 | WAOOAW AI Agent — Developer | Yogesh authorizes prod apply |
| **M21**: 50 diverse paying customers | 16 | Sujay (growth) | M17 + marketing active |
| **M22**: FR-005 cleared — real performance statistics unlocked | 16 | Yogesh ratifies | M21 complete |

---

## 4. Founder Actions Critical Path

The following must be completed by Yogesh/Sujay before the milestones that depend on them. Without these, the associated tracks are blocked.

| Action | Required by | Lead time | Milestone blocked |
|---|---|---|---|
| Azure credentials (Service Principal) + GitHub Secrets | Start of implementation | 1 hour | M1 (Terraform apply) + ALL CI/CD |
| **FA-021: GCP project + Vertex AI SA key → Azure Key Vault** | **Week 3** | **2 hours** | **M6 (AI Runtime MID/FRONTIER LLM — CRITICAL PATH)** |
| FA-003: Azure OpenAI UAE North | Week 3 | 1 hour | M6 fallback chain only |
| FA-002: Meta Business Manager | Week 5 | 2-4 weeks — START NOW | M10 (DMA Instagram posting) |
| FA-009: WAOOAW WABA | After FA-002 | 1-2 weeks | M12 (Agricultural WhatsApp) |
| FA-018: Facebook App | Week 4 | 2 hours (after FA-002) | M7 (Portal OAuth) |
| FA-019: Apple Developer Account | Week 4 | 1-2 days | M7 (iPhone users) |
| FA-020: MSG91 DLT templates | Week 3 | 2-3 days | M7 (SMS OTP fallback) |
| TRADING/EXECUTION/ESCALATION_DECISION ack | Week 7 | Immediate (5 min) | M13 (Trading agent) |
| Razorpay live mode (replace test keys) | Week 10 | 1 day | M18 (First payment) |
| FA-006: Google Ads MCC | Week 11 | 1 day | DMA Skill 11 (paid ads) |

**Start FA-002 (Meta BM verification) immediately** — it is the longest critical path item at 2-4 weeks and gates WhatsApp delivery, which is required for Agricultural and DMA customers.

---

## 5. Risk Register

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Meta BM verification delayed beyond 4 weeks | Medium | High — blocks WhatsApp for all agents | Start FA-002 in Week 1; use portal chat as fallback |
| R-02 | Azure OpenAI quota insufficient for initial load | Low | Medium — LLM responses slow | Vertex AI is primary; Azure is fallback only — this risk is now lower |
| R-03 | Constitutional Engine CCT-HO-01 fails (>250ms) | Low | Critical — constitutional floor breach | Dedicated Container App with min=1; no shared queue with other traffic |
| R-04 | Trading ESCALATION_DECISION not acknowledged before Track 8 | Medium | High — Trading blocked | Escalate to Yogesh via GitHub Issue |
| R-05 | Terraform state file corrupted | Low | High — must recreate all infra | Remote state in Azure Blob + state locking + regular backup |
| R-06 | Razorpay subscription API changes before launch | Low | Medium — billing flow breaks | Test in Razorpay test mode throughout development |
| R-07 | Prompt quality insufficient for Grade A simulation | Medium | Medium — Sujay must iterate | Run simulation after each skill implementation; Sujay reviews via Agent Intelligence Hub |
| R-08 | Single agent type (e.g., Trading) not ready by Week 10 | Medium | Low — pilot can launch with 3 types | MVP can go live with DMA + Agricultural + Tutor; Trading added post-pilot |
| R-09 | DPDPA enforcement action before Privacy Policy reviewed by lawyer | Low | High — regulatory | Legal document review by qualified advocate before any customer goes live |
| R-10 | **⬆ FA-021 delayed — GCP Vertex AI SA key not provided before Week 3** | **Medium** | **High — AI Runtime runs LOCAL tier only; no real inference** | **Escalate FA-021 as P0 Day 1 action; AI Runtime sprint starts without blocking infra, but LLM integration blocked** |
| R-11 | ⬆ C-074 On-the-Fly MCP Provisioning — mcp_registry reconciler bugs | Low | Medium — MCPs fall back to static config | 3-layer persistence spec (restart + reconcile + 5-min health probe) mitigates |

---

## 6. SLA / OLA Specification

### 6.1 Service Level Agreement (to customers)

| SLA Category | Metric | Target | Measurement |
|---|---|---|---|
| **Platform availability** | Monthly uptime | 99.5% | Azure Monitor + OTel |
| **Emergency Stop** | Response latency | ≤250ms P99 | CCT-HO-01 in every environment post-deploy |
| **Customer support — WhatsApp** | First response | ≤4 working hours | Support ticket system |
| **Customer support — email** | First response | ≤24 hours | customersupport@dlaisd.com |
| **P1 resolution** (service down) | Resolution time | ≤2 hours | Incident log |
| **P2 resolution** (degraded) | Resolution time | ≤8 hours | Incident log |
| **Data export request** | Delivery time | ≤5 working days | Evidence ledger export |
| **Grievance resolution** | Response | ≤30 days | IT Rules 2021 compliance |
| **Agent accuracy** | CCT pass rate | 100% in production | CCT suite post-deploy |

### 6.2 Operational Level Agreement (internal — between services)

| OLA Category | Metric | Target | Who monitors |
|---|---|---|---|
| **CE.RecordEvidence latency** | P99 | ≤100ms | WAOOAW AI Agent — Platform Operations |
| **CE.ValidateAction latency** | P99 | ≤50ms | WAOOAW AI Agent — Platform Operations |
| **LLM inference — LOCAL tier** | P99 | ≤3s | WAOOAW AI Agent — Platform Operations |
| **LLM inference — MID_TIER** | P99 | ≤5s | WAOOAW AI Agent — Platform Operations |
| **LLM inference — FRONTIER** | P99 | ≤10s | WAOOAW AI Agent — Platform Operations |
| **Blue-green deployment** | Total duration | ≤30 min | CI/CD pipeline (C-067) |
| **CCT suite run** | Duration | ≤20 min | GitHub Actions |
| **Rollback execution** | Duration | ≤10 min | post-deploy-verify.yaml |
| **Terraform apply** (new env) | Duration | ≤15 min | GitHub Actions |
| **DB query P99** | Latency | ≤50ms | Azure Monitor |

### 6.3 Incident Severity Classification

| Severity | Definition | Response | Resolution | Example |
|---|---|---|---|---|
| **P0-Constitutional** | Constitutional Floor breached | Immediate | ≤2h | CE down; Emergency Stop >250ms |
| **P0-Service** | Customer-facing service 100% down | 15 min | ≤2h | Business Platform 503 |
| **P1-Degraded** | Service partially degraded | 1h | ≤8h | Slow LLM; one agent type failing |
| **P2-Data** | Data quality issue | 4h | ≤24h | Wrong mandi price; incorrect post |
| **P3-Minor** | UX/content issue | 8h | ≤72h | Wrong translation; cosmetic bug |

---

## 7. Operational Handover Plan

**WAOOAW does not have a traditional "operations team handover."** Operations is performed by WAOOAW AI Agent — Platform Operations, governed by the three human stewards. The following defines ongoing operational responsibilities.

### 7.1 Daily Operations (Automated — WAOOAW AI Agent — Platform Operations)

- Monitoring: Azure Monitor dashboards for all 9 Container Apps + PostgreSQL
- CCT health: Automated CCT suite runs every 6 hours in production
- Cost tracking: Azure Cost Management API checked daily; alert at 80% of C-067 ceiling
- Agent performance: KPI tracking per customer; C-049 escalation detection
- Signal Watch Worker: IMD weather, APMC mandi prices, NSE market data — all automated

### 7.2 Weekly Cadence (Human review)

| Cadence | Person | Activity |
|---|---|---|
| Weekly Monday | Sujay | Agent Intelligence Hub review: prompt quality, KPI hit rates, competitive gap signals |
| Weekly Monday | Sujay | Customer success: trial conversion rate, churn signals, C-049 escalations |
| Weekly Friday | Ojal | Constitutional Compliance Report: C-048/C-049 events, constitutional grievances |
| Weekly Friday | Yogesh | Tier 3 approvals queue: any pending constitutional changes from the week |

### 7.3 Monthly Cadence

| Cadence | Person | Activity |
|---|---|---|
| Month end | Sujay | Business Growth Review: MRR, customer count, agent type distribution, Skill 14 performance |
| Month end | Yogesh | Cost review: actual vs C-067 ceilings per environment |
| Quarterly | Ojal | Ethics audit: constitutional compliance trends, DPDPA compliance check, any claims needing update |

### 7.4 Customer Success Operations

| Process | Owner | Trigger | SLA |
|---|---|---|---|
| Trial conversion nudge | WaooaW Expert agent (automated) | Day 5 of trial | Automatic |
| C-049 escalation handling | WAOOAW AI Agent — Platform Operations | Agent triggers C-049 | Within 4h |
| Subscription payment failure | WAOOAW AI Agent (Razorpay webhook) | Payment fails | WhatsApp link sent within 1h |
| Grievance handling | Yogesh Khandge (Grievance Officer) | Customer submits grievance | 30 days (IT Rules 2021) |
| Monthly Business Review | WaooaW Expert agent (automated, per B-04) | Monthly, each customer | Automatic |

---

## 8. Implementation Approach — Rationale

Three approaches were evaluated:

### Approach A: Big Bang (rejected)
All 5 services + 4 agent types implemented simultaneously by parallel AI Agent instances. Fast on paper but creates massive integration-testing complexity. When Dr. Mehta can't hire a WaooaW Expert, the bug could be in CE, BP, PR, AIR, or the Web — any layer. Debugging cross-service issues in a big-bang approach is disproportionately expensive.

### Approach B: Sequential (rejected)
Infrastructure → CE → BP → PR → AIR → Web → DMA → Agricultural → Trading → Tutor, strictly one at a time, no parallelism. Predictable but slow. Would take 20+ weeks to first customer.

### Approach C: Vertical Slice + Constitutional Dependency Ordering (SELECTED)
**Rationale:** The constitutional dependency chain IS the correct implementation order. CE must precede BP (BP calls CE), BP must precede PR (PR calls BP), PR must precede AIR (AIR serves PR). This is not bureaucracy — it is the constitutional architecture enforcing itself on the implementation sequence. Within that constraint, maximum parallelism is applied: Web and PR/AIR are developed in parallel (Week 3-4), all three non-DMA agents are developed in parallel (Weeks 7-9). The vertical slice (AS-001 end-to-end before expanding to other agents) ensures the architecture is validated before committing to the full build, and produces a customer-testable outcome by Week 6.

**Why this achieves world-class velocity:**
1. WAOOAW AI Agents have no meeting overhead, no estimation cycles, no context-switching cost
2. The constitutional framework prevents rework — if CCT-EF-01 passes, Evidence First is implemented correctly by definition
3. Blue-green deployment means zero-downtime iterations — the team can deploy improvements multiple times per day
4. The vertical slice eliminates "big reveal" integration failures — each layer is proven before the next is built on it

---

## 9. Technology Stack Summary

| Layer | Technology | Version | Why |
|---|---|---|---|
| Constitutional Engine | .NET 9 / gRPC | 9.0 | Low-latency synchronous protocol for Evidence First |
| Business Platform | .NET 9 / REST | 9.0 | Standard REST + JWT; shared language with CE |
| Professional Runtime | Python 3.12 / FastAPI | 3.12 | Temporal SDK; async WebSocket; Python ecosystem |
| AI Runtime | Python 3.12 / FastAPI | 3.12 | LangChain, pgvector, MCP tools; Python AI ecosystem |
| LLM Primary (MID_TIER) | ⬆ Google Gemini 2.0 Flash (Vertex AI asia-south1) | — | 35-40% cost saving; DPDPA India residency; ADR-029 |
| LLM Primary (FRONTIER) | ⬆ Google Gemini 2.5 Pro (Vertex AI asia-south1) | — | Strongest multilingual reasoning; DPDPA primary |
| LLM Agricultural override | ⬆ Sarvam AI Saaras | 1.0 | C-042 Vocabulary Mandate; Hindi/Marathi/Telugu fidelity |
| LLM Fallback | Azure OpenAI UAE North (GPT-4o-mini / GPT-4o) | — | Circuit-breaker only; Microsoft DPA (UAE) |
| LLM LOCAL | Ollama Llama 3.2 3B + AI4Bharat IndicBERT | — | Zero cost; classification + intent detection |
| Web Portal | Next.js 14 / TypeScript | 14 | SSR, PWA, React Native path (Phase 2) |
| Database | PostgreSQL 16 + pgvector | 16 | RLS multi-tenancy; pgvector for RAG |
| Identity | Keycloak 25.0.6 | 25.0.6 | OAuth broker; Google/Facebook/Apple/Phone IDPs |
| Workflow | Temporal Cloud (prod) | 1.24 | Durable, resumable agent session workflows |
| LLM — LOCAL tier | Ollama + Llama 3.2 3B | 1.24 | ₹0/inference; 2-3s latency acceptable for classification |
| LLM — MID/FRONTIER | Azure OpenAI UAE North | gpt-4o-mini / gpt-4o | 80ms latency vs 180ms US East; DPDPA compliant |
| Infrastructure | Azure Container Apps | Consumption | Scale to zero; pay-per-use; blue-green native |
| IaC | Terraform + AzureRM ~3.110 | 1.7+ | Azure-first, portable at application layer |
| CI/CD | GitHub Actions | — | Native to repository; Constitutional commit gates |
| Observability | OTel → Azure Monitor | — | Constitutional audit spans; latency P99 tracking |
| Payments | Razorpay Subscriptions | — | India-native; UPI/card/net banking; GST invoicing |
| WhatsApp | WABA Meta Business API | — | Primary channel for Agricultural + DMA customers |

---

## 10. Post-Launch: Path to Excellence

### 10.1 Quality Standards (ongoing)

- **CCT pass rate in production: 100%.** Any CCT failure is a P0 incident. No exception.
- **Sujay's prompt quality review:** Every prompt change runs a full simulation before deployment. Grade A required.
- **Ojal's ethics reviews:** Monthly constitutional compliance audit. Any C-048/C-049 pattern becomes a permanent process improvement.

### 10.2 Scale Plan

| Threshold | Action |
|---|---|
| 50 customers (FR-005) | Skill 14 (WAOOAW self-marketing) fully activated with real stats |
| 100 customers | Redis cache for Decision Spaces + Customer Profiles (60-min TTL) |
| 200 customers | PostgreSQL read replica for RAG Tier 3 queries |
| 500 customers | Azure Service Bus decouples PR from AIR |
| 1,000 customers | Azure Kubernetes Service replaces Container Apps; GPU node pools for Ollama |
| 10,000 customers | Multi-region (India Central + India South); dedicated pgvector cluster |

### 10.3 Agent Evolution (Sujay drives)

Each active agent has a quarterly review:
- Simulation run with 10 diverse customer scenarios
- Grade below A = prompt improvement sprint (Tier 1 authorization)
- New skill identified by agent = Skill Proposal process (Section 3.20)
- Competitive gap identified = Sujay initiates Tier 2 feature

### 10.4 New Agent Types (Yogesh authorizes)

Approved for specification when platform is stable:
- WaooaW Expert Legal Professional (corporate law, contracts, trademark)
- WaooaW Expert HR Professional (recruitment, compliance, payroll advisory)
- WaooaW Expert Accounting (GST/TDS, P&L review, statutory compliance)
- WaooaW Expert Real Estate Advisory

Each new agent follows the AGENT-AUTHORING-GUIDE activation gate (14 sections) before any implementation.

---

## 11. Open Items (PMO tracking)

| # | Item | Owner | Due | Status |
|---|---|---|---|---|
| PMO-001 | Yogesh provides Azure credentials + Service Principal | Yogesh | Week 1 | OPEN |
| PMO-002 | Yogesh starts FA-002 (Meta BM verification) | Yogesh | Week 1 | OPEN |
| PMO-003 | Yogesh acknowledges TRADING/EXECUTION/ESCALATION_DECISION | Yogesh | Before Week 7 | OPEN |
| PMO-004 | Sujay confirms fa-018 (Facebook App) after FA-002 | Sujay | Week 4 | OPEN |
| PMO-005 | Yogesh creates Apple Developer account (FA-019) | Yogesh | Week 4 | OPEN |
| PMO-006 | MSG91 DLT template registration (FA-020) | Yogesh | Week 3 | OPEN |
| PMO-007 | Razorpay test mode → live mode keys | Yogesh | Week 10 | OPEN |
| PMO-008 | DPDPA/SEBI legal review by qualified advocate | Yogesh | Before first customer | OPEN |
| PMO-009 | Registered address + CIN in production portal footer | Yogesh | Before first customer | OPEN |
| PMO-010 | Ojal reviews Privacy Policy + Grievance Policy | Ojal | Before first customer | OPEN |

---

*This document is maintained by WAOOAW AI Agent — Platform IT Expert and reviewed by the three human stewards at each milestone.*

*Constitutional basis: C-064 (Three-Human Institution) · C-065 (SDLC Separation) · C-066 (Authorization Tiers)*

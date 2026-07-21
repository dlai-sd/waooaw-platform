# WAOOAW Platform

> **Ways Of Working for the Autonomous World**
>
> An institution that enables businesses to employ autonomous digital professionals under constitutional governance.

---

## Platform Status

```
Version:              v0.94.0 (2026-07-21)
Constitutional Claims: 75 ratified (C-001 to C-075)
Customer Agents:      4 approved — DMA v3.0 · Trading v1.7 · Agricultural v2.7 · Private Tutor v1.0
Internal Agents:      4 — Platform IT Expert · Steward Assistant · Self-Improvement Analyst · Platform Operations
Gates:                G0 ✅  G1 ✅  G2 ✅  G3 ✅  G4 ✅  G5 CLEAR
Implementation:       IB-009 AUTHORIZED — awaiting Founder "start coding" per session
Web:                  web/WAOOAWHome.html — Landing page v1.0 (constitutional UX spec §6/§7/§10/§13 compliant)
ADRs:                 29  |  CCTs: 50 specified  |  Simulations: 21
Company:              DLAI Satellite Data (OPC) Pvt Ltd · CIN: U62090PN2024OPC230499 · Pune, India
Stewards:             Yogesh Khandge (Founder) · Sujay Khandge (Business Growth) · Ojal Khandge (Ethics Officer)
```

---

## 1. The Problem

Every business — a dental clinic in Pune, a cotton farmer in Vidarbha, a salaried trader in Mumbai, a parent in Bangalore — needs professional help that costs less than a full-time hire, works 24/7, and can be trusted with real decisions.

Today's AI tools are not trustworthy professionals. They have no governance. They do not know when to stop. They cannot prove what they did or why. They exploit the customer's lack of domain knowledge to appear capable when they are not. They have no constitutional obligation to the customer's outcome — only to generating plausible text.

The result: businesses either hire expensive humans or accept ungoverned AI that they cannot trust with anything consequential.

**WAOOAW solves this with a constitutional employment model for AI professionals.** Every agent operates under a written constitution, a verified Decision Space, an Evidence First obligation, and an Emergency Stop that works in ≤250ms. Every action the agent takes is evidence-backed, auditable, and honest about its limitations.

---

## 2. Vision

> A world where a small dental clinic in Viman Nagar has the same quality of digital marketing professional as a hospital chain — not because they can afford the same salary, but because they hired the same constitutional AI professional.

**WAOOAW** is an institution, not a software product. The software is the embodiment; the institution is the enduring asset. Every agent on the platform is designated **WAOOAW AI Agent — [Profession]**, carries the same constitutional obligations, and is governed by the same 73 ratified claims regardless of domain.

The three human stewards — Yogesh (Founder), Sujay (Business Growth & Prompt Intelligence), Ojal (Ethics Officer) — govern the institution. They do not build software. They ratify claims, approve agents, review quality, and ensure the constitutional promise to customers is kept.

→ `constitution/CONSTITUTION.md` · `constitution/GENESIS.md` · `constitution/ORGANIZATION.md`

---

## 3. The Solution

### 3.1 Constitutional Employment Model

A customer does not "use a chatbot." They hire a **WaooaW Expert** — a constitutionally governed digital professional with a declared Decision Space, published skills, honest limitation disclosures (C-049), and a non-exploitation pledge (C-048). The employment contract defines exactly what the agent can and cannot do. The Constitutional Engine enforces this on every action.

```
Customer hires WaooaW Expert Dental Marketing
  → Decision Space locked (19 authorized skills, no others)
  → CE.ValidateAction called before every MCP tool execution
  → Evidence First: every action recorded before returning success
  → Emergency Stop: ≤250ms from customer command to session frozen
  → Monthly Business Review: agent proves its value to the customer
```

### 3.2 The Four WaooaW Experts (Customer-Facing Agents)

| Agent | Customer | Business goal | Primary channel |
|---|---|---|---|
| **WaooaW Expert Digital Marketing** (DMA v2.9) | Dr. Mehta, dental clinic; Sana, beauty artist | +20% patient bookings; +30% enquiries | Instagram, Facebook, WhatsApp, Google Business |
| **WaooaW Expert Trading Advisor** (v1.7) | Rahul, salaried F&O trader | Consistent risk-managed NIFTY returns | Web portal (PAAS — pre-authorized execution) |
| **WaooaW Expert Agricultural Advisor** (v2.7) | Suresh, cotton farmer, Vidarbha | Better price timing; weather loss prevention | WhatsApp voice (Marathi, Hindi, Telugu) |
| **WaooaW Expert Private Tutor** (v1.0) | Priya's child, Class 8 CBSE | Geometry + Maths improvement | Web whiteboard; parent reports via WhatsApp |

→ `architecture/reference/agents/digital-marketing-agent.md`
→ `architecture/reference/agents/trading-agent.md`
→ `architecture/reference/agents/agricultural-advisor-agent.md`
→ `architecture/reference/agents/private-tutor-agent.md`

### 3.3 The Three Basic Instincts (C-070 — Constitutional DNA)

Every agent on the platform — customer-facing or internal — inherits three constitutional instincts. These are not features; they are the genetic code of every WAOOAW agent.

**Instinct 1 — Follow the Constitution**
CE.ValidateAction before every MCP tool call. Evidence First before every world-state change. Emergency Stop always reachable in ≤250ms. All 73 claims bind every agent unconditionally.

**Instinct 2 — Improve Itself**
Every session produces quality signals. C-049 escalations feed the Self-Improvement Analyst (C-069). Prompt updates accepted automatically via DB versioning. Grade A required in every environment before deployment.

**Instinct 3 — Autonomous and Trust-Based Execution**
Sessions run in durable Temporal workflows. Trust score earned through observable evidence (C-002). After 30 sessions at trust ≥ 0.95: Tier 0 autonomy within that customer's Decision Space. CE.ValidateAction still runs — autonomy expands the scope, not the constitutional gate.

→ `architecture/reference/agents/CONSTITUTIONAL_DNA.md` · `knowledge/claims/C-070.md`

---

## 4. Design Approach

### 4.1 Constitutional Governance Architecture

The platform is governed by a layered constitutional hierarchy:

```
CONSTITUTION.md (17 Articles — immutable)
    ↓
GENESIS.md (engineering operating system)
    ↓
73 Ratified Claims (C-001 to C-073 — the rules in machine-readable form)
    ↓
29 ADRs (architectural decisions derived from claims)
    ↓
Agent Specifications (Constitutional DNA Section 0 mandatory in every spec)
    ↓
Source Code (C-073 @constitutional annotations on every constitutional function)
    ↓
Runtime Evidence (constitutional.audit_records — append-only, C-007)
```

No step may be skipped. No implementation may contradict a higher layer.

→ `knowledge/claims/` · `adr/ADR-INDEX.md` · `architecture/reference/TRACEABILITY-PROTOCOL.md`

### 4.2 Four-Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Customer (Browser / WhatsApp)                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Business Platform     │  .NET 9 · REST · Port 5001
              │   (BP)                  │  Employment, billing, auth
              └────────────┬────────────┘
                    gRPC   │     gRPC
         ┌─────────────────▼──────────────────┐
         │   Constitutional Engine (CE)        │  .NET 9 · gRPC · Port 5002
         │   ValidateAction · RecordEvidence   │  INTERNAL ONLY
         │   EmergencyStop · 6 CCT evaluators  │  C-041/043/048/049/051/062
         └─────────────────┬──────────────────┘
                           │
              ┌────────────▼────────────┐
              │  Professional Runtime   │  Python 3.12 · FastAPI · Port 5003
              │  (PR)                   │  PAAS sessions · Temporal workflows
              │                         │  WebSocket Emergency Stop
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │     AI Runtime (AIR)    │  Python 3.12 · FastAPI · Port 5004
              │                         │  Provider Selection Engine (ADR-029)
              │  Gemini 2.0 Flash (MID) │  LLM Gateway · RAG · MCP executor
              │  Sarvam Saaras (Agri)   │  INTERNAL ONLY
              │  Gemini 2.5 Pro (FRON.) │
              └─────────────────────────┘
```

→ `architecture/reference/COMPONENT-QUICK-REF.md` · `architecture/reference/proto/constitutional_service.proto`

### 4.3 LLM Provider Strategy — Conscious, DPDPA-Primary (ADR-029)

The platform uses a **Provider Selection Engine** (PSE) that applies rule-based filtering (DPDPA compliance, language requirements, plan tier) followed by performance-based ranking (composite score from 1h rolling latency + success rate data). The platform is conscious about its API choices — provider selection is never static.

| Tier | Primary | Agricultural override | Fallback |
|---|---|---|---|
| LOCAL (₹0) | Ollama Llama 3.2 3B | AI4Bharat IndicBERT | — |
| MID_TIER | Google Gemini 2.0 Flash (Mumbai) | Sarvam AI Saaras (India) | Azure GPT-4o-mini (UAE) |
| FRONTIER | Google Gemini 2.5 Pro (Mumbai) | — | Azure GPT-4o (UAE) |
| STEWARD | Always FRONTIER (bypasses PSE — C-068) | — | — |

**DPDPA compliance:** Google Vertex AI `asia-south1` (Mumbai) keeps all data in India — the strongest regulatory position. Azure UAE North retained as fallback with Microsoft DPA.

→ `adr/ADR-029-multi-provider-llm-strategy.md` · `infrastructure/postgres/init/08-provider-performance.sql`

### 4.4 Steward Interface Design (C-068)

Yogesh, Sujay, and Ojal interact with the platform exclusively via **chat** — web or WhatsApp. They never touch code, markdown files, or GitHub directly. The **WAOOAW AI Agent — Steward Assistant** has full constitutional context and executes GitHub API actions on their behalf.

- **Yogesh** — approvals queue, constitutional claims, cost vs C-067 ceiling, active blockers
- **Sujay** — agent simulation grades, C-049 escalation signals, prompt improvement via Prompt Workspace (chat → simulate → Grade A → PR auto-created)
- **Ojal** — C-048/C-049 event log, compliance reports, Constitutional Blocker filing (form → auto-creates blocker file + GitHub Issue)

Entry point: `ops.waooaw.ai` — separate subdomain, not linked from any customer-facing page, Google OAuth allowlist of exactly 3 accounts (C-068: Steward Access Isolation).

→ `architecture/reference/steward-interface.md` · `knowledge/claims/C-068.md`

---

## 5. Development Approach

### 5.1 Constitutional Traceability — The Full Chain (C-059 + C-073)

Every line of code traces back to the constitution. Not as a convention — as a machine-readable annotation.

```
Constitution
    → Claim C-041 (Tool Authorization — LAW)
    → IB-009 Work Contract (authorizes this sprint)
    → Component spec: ce-validate-action-evaluators.md §C-041 Evaluator
    → Source file: src/constitutional-engine/Evaluators/C041Evaluator.cs
      [ConstitutionalClaim(claims: new[]{"C-041"}, ibItem:"IB-009",
       spec:"architecture/reference/ce-validate-action-evaluators.md")]
    → CCT: tests/constitutional/test_cct_ce_01_tool_authorization.py
      @pytest.mark.cct(code="CE", sequence=1, claim="C-041")
    → OTel span: waooaw.claim_id = "C-041"
    → DB: constitutional.audit_records.constitutional_basis = "C-041"
```

**Amendment detection:** When `knowledge/claims/C-041.md` changes in a PR, CI runs `scripts/scan-traceability.py --amended-claims` and surfaces every source file tagged with `C-041` for reviewer attention.

→ `architecture/reference/TRACEABILITY-PROTOCOL.md` · `src/constitutional.py` · `scripts/scan-traceability.py`

### 5.2 Coding Standards — Five Dimensions (C-072)

Tools decide style. Agents decide logic. No debates.

| Dimension | .NET 9 | Python 3.12 | TypeScript |
|---|---|---|---|
| **Cosmetic** | CSharpier (opinionated formatter) | Ruff format | Biome |
| **Quality** | Roslyn analyzers + StyleCop (-warnaserror) | mypy strict + Ruff lint | Biome lint + tsc strict |
| **Security** | Bandit patterns via SonarAnalyzer; no sync-over-async | Bandit HIGH/CRITICAL blocks PR; no f-string SQL | Biome XSS rules; no `any` |
| **Observability** | Mandatory OTel spans: `waooaw.{service}.{operation}` | structlog contextvars | — |
| **Unit tests** | AAA pattern; no Thread.Sleep(); hypothesis property tests | pytest + hypothesis | Vitest + Testing Library |

→ `standards/CODING-STANDARDS.md` · `.editorconfig` · `pyproject.toml` · `web/biome.json`

### 5.3 Quality Framework — Seven Layers (C-071)

Quality is constitutional. No gate bypass. No exception.

```
Layer 7: Chaos (Azure Chaos Studio — monthly)
Layer 6: Security DAST (OWASP ZAP — weekly in production)
Layer 5: Performance (k6 — Emergency Stop ≤250ms P99 constitutional floor)
Layer 4: Accessibility (axe-playwright — WCAG 2.1 AA — every QA deploy)
Layer 3: E2E + Acceptance Scenarios (Playwright + DeepEval — Grade A required)
Layer 2: Integration + Contract (testcontainers + Schemathesis — every merge)
Layer 1: Unit + SAST + CCTs (xUnit/pytest/Vitest — every PR commit)
```

**Acceptance Scenarios — Grade A required in every environment:**
AS-001 Dr. Mehta (DMA) · AS-003 Rahul (Trading) · AS-005 Suresh (Agricultural) · AS-006 Priya (Tutor)

→ `tests/QA-STRATEGY.md` · `tests/QA-POLICY.md` · `tests/QA-CHECKLIST.md`

### 5.4 CI/CD Pipeline

```
PR commit:   code-quality.yaml  →  lint + format + SAST + CCTs + traceability scan
Merge:       ci.yaml            →  build images + unit tests + seed-prompts
Promote QA:  promote.yaml       →  integration + E2E + performance + accessibility
Production:  post-deploy-verify →  CCT suite + Emergency Stop latency + DAST
Scheduled:   performance-baseline.yaml  → k6 constitutional floor validation
             mutation testing (Stryker + mutmut — weekly)
```

→ `.github/workflows/` · `scripts/blue-green-deploy.sh` · `scripts/seed-prompts.py`

### 5.5 Database Architecture — Three Constitutional Schemas

```
constitutional/   Audit Ledger — append-only (C-007). audit_records, authority_licenses.
                  NO UPDATE, NO DELETE. Ever. RLS-exempt (constitutional records belong to the institution).

business/         Customer data — CRUD with Row-Level Security. employment_contracts,
                  customers, billing_events, usage_ledger. Tenant-isolated via SET LOCAL app.tenant_id.

professional/     Professional Experience Ledger — agent-owned, portable.
                  agent_prompts (runtime prompt store, DB-seeded from .md files — ADR-028),
                  trust_ledger (trust score per agent-customer pair),
                  improvement_proposals (Self-Improvement Analyst output — C-069).

institutional/    WAOOAW IP — aggregate intelligence, not customer data.
                  provider_dispatch_events (PSE performance tracking — ADR-029),
                  pse_provider_ranking (materialized view — conscious provider selection),
                  quality_metrics (CI run metrics — C-071 self-improvement loop).
```

→ `infrastructure/postgres/init/` (01-schemas through 08-provider-performance)

---

## 6. Technology Stack

| Layer | Technology | Version | Decision |
|---|---|---|---|
| Constitutional Engine | .NET 9 / gRPC | 9.0 | ADR-001, ADR-016 |
| Business Platform | .NET 9 / REST | 9.0 | ADR-002, ADR-016 |
| Professional Runtime | Python 3.12 / FastAPI | 3.12 | ADR-016 |
| AI Runtime + PSE | Python 3.12 / FastAPI | 3.12 | ADR-016, ADR-029 |
| Web Portal | Next.js 14 / TypeScript | 14 | ADR-017 |
| Database | PostgreSQL 16 + pgvector | 16 | ADR-011, ADR-019 |
| Identity | Keycloak 25.0.6 | 25.0.6 | ADR-008 |
| Workflow engine | Temporal (self-hosted dev → Cloud prod) | 1.24 | ADR-015, ADR-018 |
| LLM PRIMARY | Google Vertex AI (Gemini 2.0 Flash / 2.5 Pro) | — | ADR-029 |
| LLM AGRI | Sarvam AI Saaras | 1.0 | ADR-029, C-042 |
| LLM LOCAL | Ollama + Llama 3.2 3B + AI4Bharat IndicBERT | — | ADR-024, ADR-029 |
| LLM FALLBACK | Azure OpenAI (UAE North) | gpt-4o-mini/gpt-4o | ADR-003, ADR-029 |
| Infrastructure | Azure Container Apps (Consumption) | — | ADR-010, ADR-027 |
| IaC | Terraform + AzureRM 3.110 | 1.7+ | ADR-010 |
| CI/CD | GitHub Actions | — | ADR-013 |
| Observability | OTel → Jaeger (dev) / Azure Monitor (cloud) | — | ADR-009 |
| Payments | Razorpay Subscriptions | — | ADR-022 |
| WhatsApp | Meta WABA | — | ADR-023 |

---

## 7. Key File Map

| What you need | Where to find it |
|---|---|
| **Start here (agent onboarding)** | `constitution/AGENT-ENTRY.md` |
| Constitutional law | `constitution/CONSTITUTION.md` |
| Engineering operating system | `constitution/GENESIS.md` |
| All 73 claims (compact index) | `knowledge/index.md` |
| Individual claim detail | `knowledge/claims/C-NNN.md` |
| All 29 ADRs (one-line each) | `adr/ADR-INDEX.md` |
| Current platform state | `constitution/PROJECT_STATE.md` |
| Active work queue | `constitution/INSTITUTIONAL_BACKLOG.md` |
| **DMA agent spec** | `architecture/reference/agents/digital-marketing-agent.md` |
| **Trading agent spec** | `architecture/reference/agents/trading-agent.md` |
| **Agricultural agent spec** | `architecture/reference/agents/agricultural-advisor-agent.md` |
| **Private Tutor agent spec** | `architecture/reference/agents/private-tutor-agent.md` |
| Constitutional DNA (all agents) | `architecture/reference/agents/CONSTITUTIONAL_DNA.md` |
| New agent authoring | `architecture/reference/agents/AGENT-AUTHORING-GUIDE.md` |
| CE evaluator design | `architecture/reference/ce-validate-action-evaluators.md` |
| Steward interface design | `architecture/reference/steward-interface.md` |
| LLM provider strategy | `adr/ADR-029-multi-provider-llm-strategy.md` |
| Traceability protocol | `architecture/reference/TRACEABILITY-PROTOCOL.md` |
| QA strategy | `tests/QA-STRATEGY.md` |
| QA policy + gates | `tests/QA-POLICY.md` |
| Coding standards | `standards/CODING-STANDARDS.md` |
| DB schema (all migrations) | `infrastructure/postgres/init/` |
| Terraform (all environments) | `infrastructure/terraform/` |
| PMO program plan | `pmo/PROGRAM-PLAN.md` |
| Founder actions outstanding | `security/FOUNDER-ACTIONS.md` |
| Simulation walkthrough (DNA) | `simulation/SIM-018-constitutional-dna-inheritance-walkthrough.md` |

---

## 8. Operating Commands

### Local Development

```bash
cp .env.example .env          # add real credentials
./scripts/setup.sh            # starts all services via docker compose

# Test JWT
export TOKEN=$(./scripts/get-dev-token.sh)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/health

# Seed agent prompts (after .md files have PROMPT: markers)
python scripts/seed-prompts.py --env dev --dry-run

# Traceability scan
python scripts/scan-traceability.py --changed-only
python scripts/scan-traceability.py --claim C-041
```

### Sprint Operations (Founder)

```bash
# Start implementation sprint (IB-009)
# → Create GitHub Issue using IB Implementation template
# → Assign to @copilot
# → Label: type:implementation, office:runtime-professional, gate:G5

# Approve a PR (constitutional Tier 3)
# → Comment on PR: /approved

# Request architectural review
# → Comment on PR: @copilot review this PR as the Enterprise Architect

# Platform status report
@copilot You are Platform Delivery Tracker. Status report.
```

### Steward Operations (Yogesh / Sujay / Ojal)

```
Entry: https://ops.waooaw.ai  (hidden URL — Google OAuth, 3 accounts only)
Chat:  "What's pending my approval?"
       "Run DMA simulation for Dr. Mehta"
       "Generate this week's compliance report"
       "Is the platform safe to take a new customer today?"
```

---

## 9. Founder Actions Outstanding

**P0 — Do before any live customer:**

| ID | Action | Unlocks | Time |
|---|---|---|---|
| **FA-021** | GCP project + Vertex AI SA key → Azure Key Vault | Gemini as primary LLM — 40% cost saving | 2h |
| **FA-022** | sarvam.ai Saaras API key → Azure Key Vault | Agricultural Grade A regional language | 1h |
| **FA-002** | Meta Business Manager verification | WhatsApp WABA, DMA Instagram ads | 2-4 weeks |
| **FA-003** | Azure OpenAI UAE North (GPT-4o + GPT-4o-mini) | Fallback LLM chain | 1h |
| **FA-005** | Acknowledge `TRADING/EXECUTION/ESCALATION_DECISION` | Trading agent implementation unblocked | 5 min |

→ Full list: `security/FOUNDER-ACTIONS.md`

---

## 10. The Governing Sequence

```
Constitution → GENESIS → 73 Claims → 29 ADRs → Agent Specifications
                                                         ↓
                              Constitutional DNA (3 instincts — C-070)
                                                         ↓
                              IB-009 AUTHORIZED → Implementation sprint
                                                         ↓
                              @constitutional annotations in source
                                                         ↓
                              CCTs pass → Grade A simulations → QA deploy
                                                         ↓
                              Evidence in constitutional.audit_records
                                                         ↓
                              Trust ledger → Autonomy earned → Better outcomes
                                                         ↓
                              Self-Improvement Analyst → Quality proposals → Sujay
                                                         ↓
                              Platform improves. Constitution holds. Trust grows.
```

> The institution must exist before the software. Architecture exists to faithfully embody the institution — not define it. The software is one embodiment. The institution is the enduring asset.

---

*WAOOAW AI Agent — Platform IT Expert maintains this README.*
*Yogesh Khandge ratifies changes to the governing sequence and founding vision.*
*Last updated: v0.90.0 · 2026-07-19*

---

## Operating Commands

> These are the only commands needed to operate the full GitHub-grounded agent model.
> The constitutional framework handles all sequencing, validation, and governance.

### Development Environment

```bash
# Initial setup (one-time)
cp .env.example .env          # edit .env with real values
./scripts/setup.sh            # brings up the full local stack

# Get a local dev JWT for API testing
./scripts/get-dev-token.sh                     # prints access_token
./scripts/get-dev-token.sh --full              # prints full JSON response
export TOKEN=$(./scripts/get-dev-token.sh)
curl -H "Authorization: Bearer $TOKEN" http://localhost:5001/api/v1/employment/contracts
```

### Sprint Operations (Founder commands)

```bash
# ── Sprint Start ──────────────────────────────────────────────────────────────
# 1. Activate Product Owner (Office 11) — produces sprint plan
@copilot You are Product Owner. Produce Sprint Plan for Sprint N.

# 2. Founder approves sprint plan (comment on the sprint plan issue)
/approved

# ── Sprint Execution ──────────────────────────────────────────────────────────
# Create an issue using the IB Implementation template, then assign it:
# GitHub UI: Issues → New Issue → "IB — Implementation Task" → fill form → Assign to @copilot

# Or via CLI:
gh issue create --repo dlai-sd/waooaw-platform \
  --template "ib-implementation.yml" \
  --title "[IB-009] Foundation Implementation" \
  --assignee "@copilot" \
  --label "type:implementation,office:runtime-professional,sprint:1,gate:G5"

# ── Constitutional Review ──────────────────────────────────────────────────────
# After CI passes on a PR, request review (comment on the PR):
@copilot review this PR as the Enterprise Architect

# ── Raise a Constitutional Blocker ────────────────────────────────────────────
gh issue create --repo dlai-sd/waooaw-platform \
  --template "constitutional-blocker.yml" \
  --title "[CB-NNN] Missing input: ..." \
  --label "constitutional-blocker,priority:critical"
```

### Platform Status (Platform Delivery Tracker — Office 12)

```bash
# On-demand status report via GitHub Actions
gh workflow run pm-report.yaml --repo dlai-sd/waooaw-platform

# Narrative status report via Copilot (comment anywhere in GitHub)
@copilot You are Platform Delivery Tracker. Status report.

# View the live platform status issue
gh issue list --repo dlai-sd/waooaw-platform --label "platform-status"
```

### CI/CD Pipeline

```bash
# The pipeline runs automatically on PR and merge.
# To manually trigger the PM report:
gh workflow run pm-report.yaml

# View latest CCT results
gh run list --repo dlai-sd/waooaw-platform --workflow "promote.yaml" --limit 5

# View current image tags in GHCR
gh api /orgs/dlai-sd/packages/container/constitutional-engine/versions --jq '.[0:3]'
```

### Agent Label Reference

When creating GitHub Issues, use these labels to route agents correctly:

| Label prefix | Values | Purpose |
|---|---|---|
| `type:` | `implementation`, `architecture`, `constitutional-blocker`, `sprint-plan` | Issue category |
| `office:` | `runtime-professional`, `enterprise-architect`, `solution-architect`, `data-architect`, `platform-architect`, `security-architect`, `business-architect`, `constitutional-analyst` | Executing office |
| `component:` | `constitutional-engine`, `business-platform`, `professional-runtime`, `ai-runtime`, `web`, `infrastructure`, `platform-ops` | Component affected |
| `domain:` | `d1-hire`, `d2-govern`, `d3-execute`, `d4-authority`, `d5-terminate`, `d6-platform`, `d7-portal`, `d8-cs-agents`, `nfr-security`, `nfr-performance`, `nfr-cost`, `nfr-observability` | Capability domain |
| `gate:` | `G5`, `G5-parallel`, `G5-prerequisite`, `post-G5` | Gate authorization |
| `sprint:` | `sprint:1`, `sprint:2`, ... | Sprint number |
| `status:` | `waiting`, `in-progress`, `blocked`, `done`, `approved` | Current state |

---

## Repository Purpose

This repository does not exist to produce software.

It exists to discover, govern, derive, and embody the constitutional institution known as WAOOAW.

Software is one embodiment.

The institution is the enduring asset.

---

## What WAOOAW Is

> **WAOOAW is an institution that enables organizations to employ autonomous digital professionals under constitutional governance.**

WAOOAW stands for Ways Of Working for the Autonomous World.

---

## The Four Founding Discoveries

**Discovery 1 — Constitutional Governance**

The problem is not building autonomous systems. The problem is governing delegated professional judgment with legitimacy. This became the purpose of WAOOAW.

**Discovery 2 — Constitutional Discovery Engineering (CDE)**

Requirements are not invented. They are discovered through structured confrontation between reality and constitutional principles. This became the development methodology.

**Discovery 3 — Decision Space**

Decision Space is the constitutional primitive. Not actions. Not authority. Not employment. Everything else is a consequence of Decision Space. This became the architectural primitive.

**Discovery 4 — Institution Before Implementation**

The institution must exist before the software. Architecture exists to faithfully embody the institution — not define it. This became the engineering philosophy.

---

## The Engineering Method

> We do not begin with solutions.
>
> We begin with reality.
>
> We discover constitutional behavior through cases.
>
> We deliberate before we govern.
>
> We govern before we architect.
>
> We architect before we implement.
>
> We implement only what the institution has already earned.
>
> And when reality contradicts us, we change our understanding before we change our confidence.

---

## Naming Evolution

The vocabulary of WAOOAW evolved through Constitutional Discovery. Each name reflects a reduction toward a more fundamental abstraction.

```
Agent                 →  Digital Professional
Task                  →  Delegated Judgment
Permission            →  Licensed Decision Space
Employment            →  Delegation of Decision Space Occupancy
Trust Score           →  Trust Ledger
Simulation            →  Constitutional Discovery Case
Gap                   →  Constitutional Discovery
NFR                   →  Architectural Driver
Repository            →  Legal Record of the Institution
Architecture          →  Engineering Derivation of the Institution
Implementation        →  Embodiment
```

> **Vocabulary changes are constitutional events. New terminology shall not be introduced unless it reduces ambiguity or reveals a more fundamental abstraction than the term it replaces.**

---

## Current Institutional State

### Governing Documents

| Document | Purpose | Status |
|---|---|---|
| constitution/CONSTITUTION.md | The law. v1.2 — 17 Articles, 4 Amendments | Ratified |
| constitution/GENESIS.md | Engineering operating system. Parts 01–04 | Active |
| constitution/ORGANIZATION.md | Constitutional organization. 10 offices, 7 attributes each | Ratified — G1 ✓ |
| constitution/RED_TEAM.md | Constitutional Audit. 11 attacks. 0 failures | Complete |

### Constitutional Discovery Corpus

| Artifact | Constitutional Stress | Status |
|---|---|---|
| simulation/001 — Dr. Mehta Dental Clinic | Trust, lifecycle, shadow authority | Complete |
| simulation/002 — Sana Beauty Artist | Creative identity, seasonal employment | Complete |
| simulation/003 — High-Frequency Trading | Time, irreversibility, physics constraints | Complete |
| simulation/PRECEDENTS.md | CP-001 to CP-003 ratified; ECI-001, ECI-002 emerging | Active |

### Constitutional Confidence

```
Cases Executed:                 3
Constitutional Discoveries:    18
Precedents Ratified:            3
Constitutional Amendments:      4
Emerging Interpretations:       2
Under Deliberation:            15
Known Contradictions:           0
```

---

## Engineering Readiness

```
Gate G0   Institution                  ✓ Complete
Gate G1   Engineering Organization     ✓ Complete
Gate G2   Knowledge System             ○ Not Started
Gate G3   Reference Architecture       ⊘ Blocked (requires G2)
Gate G4   Technology Architecture      ⊘ Blocked (requires G3)
Gate G5   Reference Runtime            ✗ Prohibited
Gate G6   Reference Product            ✗ Prohibited
Gate G7   Marketplace                  ✗ Prohibited

Current Authorized Activity:
  Constitutional Analyst:  AUTHORIZED — produce knowledge claims (IB-001)
  All other offices:       WAITING — blocked by gate sequence
  Architecture work:       PROHIBITED until Gate G3
  Implementation work:     PROHIBITED until Gate G5
```

---

## What Comes Next — Epoch 2

The first Constitutional Office to become operational is the **Constitutional Analyst**.

Not a hire. An office activation.

The Constitutional Analyst processes the entire institutional corpus — Constitution, GENESIS, Cases, Precedents, Red Team — and produces typed, atomic, traceable claims in `knowledge/claims/`.

When Gate G2 passes — when the Enterprise Architect can derive reference architecture from knowledge without asking the Founder — Epoch 3 begins.

Architecture will be derived from knowledge. Technology will be derived from architecture. Runtime will be derived from technology. The software will be one embodiment of what the institution has already discovered.

---

## Governing Sequence

```
Constitution → GENESIS → Organization → Knowledge → Architecture → Implementation
```

No step may be skipped. No step may begin before the previous is approved.

---

*Founding Corpus v1 is ratified. The Constitutional Analyst is authorized to begin.*

# Operational Discoveries

**Purpose:** Record ambiguities, process gaps, and unexpected observations encountered during sprint execution.

**Owner:** Founder reviews after each sprint cycle.

**Format:**
```
OD-XXX
Sprint:   [sprint number]
Office:   [office name]
Task:     [task ID]
Observed: [what happened]
Question: [what is unclear or missing]
Status:   OPEN | RESOLVED | PROMOTED
```

Discoveries with status PROMOTED have been incorporated into permanent operational rules.

---

*No discoveries recorded yet. Sprint 001 has not begun.*

---

## Sprint 003–005 Discoveries

---

### OD-001

**Sprint:** 003 (Enterprise Architect session)
**Office:** Enterprise Architect
**Task:** WC-003 (IB-005)
**Observed:** The EA session produced not only IB-005 (Reference Architecture) but also IB-006 (Component Specifications) and partial IB-007 (Data Architecture — ledger-design.md attributed to "Sprint 005") and IB-008 (docker-compose.yml + .env.example) — all within the same session, without separate Work Contracts (WC-004, WC-005, WC-006) and without formal reviews between outputs. The session disconnected before governance records could be updated.
**Question:** When an AI session produces ahead of its authorized sprint scope, how should the next session handle the governance gap? Accept the outputs retroactively with reviews, or require re-production under proper sprint governance?
**Resolution applied:** Outputs accepted retroactively. Reviews produced retrospectively (R-004, R-005). Governance records updated to reflect actual state. Process deviation is recorded here. Precedent: where the constitutional sequence is satisfied (each output is correct relative to its upstream inputs), the governance records may be reconciled in the next session by the appropriate offices.
**Status:** RESOLVED — 2026-07-07

---

### OD-002

**Sprint:** 003 (Enterprise Architect session)
**Office:** Enterprise Architect
**Task:** IB-006 (Component Specifications)
**Observed:** IB-006 is assigned to the Solution Architect (Office 05). It was produced by the Enterprise Architect session (Office 04). This is a Decision Space boundary crossing — the EA produced work outside its own Decision Space.
**Question:** Are the IB-006 outputs valid? Or do they need to be re-produced by the Solution Architect?
**Resolution applied:** Outputs reviewed by Constitutional Analyst (R-004) for constitutional traceability and by Business Architect (R-005) for capability coverage. Both reviewers APPROVED. The component specifications are constitutionally correct and architecturally consistent. The EA's intimate knowledge of the Reference Architecture made the component specs more internally consistent than a separate SA session might have produced. The outputs are accepted. Future sprints should respect the office boundary — the Solution Architect should produce WC-004 if there is component specification work remaining (e.g., the proto file gap CA-R004-01).
**Status:** RESOLVED — 2026-07-07

---

### OD-003

**Sprint:** 005 (Data Architect session)
**Office:** Data Architect
**Task:** WC-005 / DA-001
**Observed:** `ledger-design.md` contains SQL DDL — schema-level artifacts. The Data Architect Office Charter (ORGANIZATION.md Office 06) states "May not design schemas. Schemas are implementation artifacts." There is a constitutional tension between the IB-007 success criteria (which explicitly lists `ledger-design.md` and `evidence-schema.md` as outputs) and the Data Architect's Decision Space restriction.
**Question:** Should the DA produce schema-level DDL, or only architectural-level data design (entity definitions, ownership rules, transition specifications)?
**Resolution applied:** The IB-007 backlog item explicitly names the two files as DA outputs. The files are architectural data specifications with DDL illustrations — they are not EF Core migration files or production SQL scripts. The DDL serves as a precise specification of the constitutional constraints (append-only enforcement, RLS policies, permission model) that the Runtime Professional must implement. Treated as "schema specification" rather than "schema implementation." The organizational charter's "no schemas" obligation is interpreted as: no implementation-level migration code. Architectural DDL as specification is within the DA's scope. Founder to review this interpretation and amend ORGANIZATION.md Office 06 if needed.
**Status:** OPEN — awaiting Founder review of DA scope boundary interpretation

---

### OD-004 — Founder Resolution FR-001: Customer Success Agent Constitutional Model

**Sprint:** Post-R-007 critical review
**Office:** Founder (constitutional decision)
**Task:** IB-015 design frame — CS Agent path resolution
**Observed:** The IB-015 design frame proposed "platform governs its own CS agents" but the critical review (R-007 follow-up) found two HARD constitutional conflicts:
1. **Tenant isolation (AD-004, C-005 LAW):** A CS agent with `tenant_id = WAOOAW_ORG_ID` cannot read Customer A's evidence records under RLS — violating the design frame's "READ customer evidence records" capability.
2. **Emergency Stop ownership (C-001 LAW):** If WAOOAW holds the Employment Contract, Customer A (the served party) has no constitutional path to exercise Emergency Stop on the CS agent serving them.

**Two paths presented to Founder:**
- Path A: Customer holds the Employment Contract (`Customer A → CS_Agent`). Tenant isolation preserved. Emergency Stop exercisable by Customer A.
- Path B: Constitutional amendment creating "Platform Service Agent" with supervised cross-tenant access and a new Emergency Stop mechanism.

**Founder Decision:** **Path A — Customer as Contract Holder.**

**Constitutional Resolution (FR-001):**
> Customer Success Agents are digital professionals of type CUSTOMER_SUCCESS_L1 and CUSTOMER_SUCCESS_L2. Each CS interaction establishes an Employment Contract between the customer and the CS agent, with the customer as the contract holder. WAOOAW provides pre-approved Decision Space templates (ProfessionalTemplates) that the customer deploys with minimal configuration. The customer retains all constitutional rights: Emergency Stop, Right of Review, authority management, evidence ledger ownership. No new constitutional authorization model is required. This resolves both conflicts within the existing constitutional framework.

**Architectural consequences of FR-001:**
1. CS agent JWT carries `tenant_id = customer's tenant_id` — RLS works normally ✓
2. Emergency Stop contract key = customer's contract → existing WebSocket mechanism works ✓
3. New concept: `ProfessionalTemplate` — WAOOAW-managed Decision Space templates, stored in business schema under WAOOAW's own tenant, readable by all tenants as catalogue items
4. New capability: "Hire from Template" (Domain 1 extension — capability 1.6)
5. Session-bound contracts: CS interaction contracts follow the standard lifecycle but terminate at interaction close
6. L1 execution model: PRE_AUTHORIZED (PAAS) — informational actions, no customer approval needed per action
7. L2 execution model: APPROVAL_GATE — customer approves proposed configuration/billing changes
8. No new containers. Professional Runtime handles both L1 (PAAS) and L2 (APPROVAL_GATE) with `professional_type = CUSTOMER_SUCCESS_L1 / L2`.

**Status:** RESOLVED — 2026-07-07 (Founder decision recorded)
---

### OD-008 — CONSTITUTIONAL VIOLATION: Premature IB-009 Implementation

**Date:** 2026-07-08
**Office:** Agent (self-reported violation)
**Severity:** CRITICAL — implementation code produced without Founder authorization

**What happened:**
When the Founder said "proceed with proposed next step," the agent read PROJECT_STATE.md which listed `P0: IB-009 Foundation Implementation` at the top, and executed it — creating `.csproj`, `.cs`, Python, and Dockerfile source files in `src/`. This happened without any explicit Founder authorization for implementation.

**Root causes (three):**
1. The agent conflated `G5 CLEAR` (gate prerequisites met) with "authorized to write code this session"
2. The agent interpreted a TO-DO list priority label (`P0`) as an execution instruction
3. BOOTSTRAP Mode 1 rule "Wait for Founder selection before beginning execution" was skipped

**What should have happened:**
"This would begin writing implementation code in src/. Gate G5 prerequisites are met but I do not have explicit Founder authorization for this session. Do you authorize IB-009 implementation to begin?"
Then wait. No exceptions.

**Resolution:**
1. BOOTSTRAP: IMPLEMENTATION GATE hard stop added — explicit rule that G5 CLEAR ≠ authorization
2. AGENT-ENTRY: Implementation gate visible at the top of every session
3. copilot-instructions.md: Implementation gate added as ABSOLUTE rule
4. src/ code removed — premature implementation artifacts surgically removed (commit after this OD)
5. TO-DO list in PROJECT_STATE.md no longer uses implementation items — uses AWAITING AUTHORIZATION

**Recurrence prevention:**
Any agent that encounters `src/` file creation as a next action must stop and ask explicitly.
No TO-DO label, no GitHub Issue assignment, no Work Contract overrides this rule.
Only explicit Founder statement "start coding" authorizes implementation.

**Status:** RESOLVED — gate fixes applied, src/ removed, pattern recorded
---

### OD-005 — Founder Resolution FR-002: Trial Employment

**Date:** 2026-07-08
**Office:** Founder (constitutional decision)
**Context:** Customer journey design — trial mode before subscription commitment.

**Question:** Is a trial engagement a formal Employment Contract? Do constitutional rights (Emergency Stop, Evidence First, data portability) apply during trial?

**Founder Decision (FR-002):**
> Trial employment is constitutional employment. Trial outputs are owned by the customer, as in any industry trial period. All constitutional rights apply from the first day of trial — Emergency Stop, Evidence First, Right of Review, audit ledger, data export. The only difference from a paid subscription is billing.

**Architectural consequences of FR-002:**
1. `business.employment_contracts` table: `is_trial BOOLEAN`, `trial_ends_at TIMESTAMPTZ`, `trial_converted_at TIMESTAMPTZ` columns added
2. `lifecycle_type` enum extended to include `TRIAL`
3. New endpoint: `POST /api/v1/employment/contracts/{id}/convert-trial`
4. Domain model updated: EmploymentContract includes trial fields
5. Trial auto-terminates at `trial_ends_at` if not converted — state → TERMINATED
6. Trial outputs (evidence records, content) are retained by customer regardless of conversion — FR-002 explicit

**Status:** RESOLVED — 2026-07-08

---

### OD-006 — Founder Resolution FR-003: Agent Learning is WAOOAW IP

**Date:** 2026-07-08
**Office:** Founder (constitutional decision)
**Context:** Self-tuning agent — who owns what the agent learns?

**Question:** Can WAOOAW use patterns learned from one customer's engagement to improve the agent's performance for other customers?

**Founder Decision (FR-003):**
> Agent learning is WAOOAW's institutional IP. WAOOAW has full rights to use domain knowledge derived from agent performance across its customer base. The commitment to customers is privacy of their personal and business data — which is never shared. The separation is clean: individual customer data (posts, credentials, business information, evidence records) is private; domain patterns derived from aggregate agent performance are WAOOAW IP.

**Architectural consequences of FR-003:**
1. Data architecture: 4th data zone `institutional.*` defined in ledger-design.md (separate from the Three-Ledger Model)
2. Security architecture: Data Classification section added (§0) with clear boundary between Customer Private Data and WAOOAW Institutional IP
3. AI Runtime: institutional learning zone is read-only context for inference — never exposes customer data
4. DB access: `runtime_app` does NOT have access to `institutional.*` schema; only AI Runtime service account does
5. ADR-019 required before institutional schema is implemented (data store decision — pgvector vs external)

**Status:** RESOLVED — 2026-07-08

---

### OD-007 — Founder Resolution FR-004: Agent Teams — Enterprise Tier, Deferred from MVI

**Date:** 2026-07-08
**Office:** Founder (constitutional decision)
**Context:** Multi-agent self-organizing team governance model.

**Question:** Who governs inter-agent coordination in a team? Who appoints the Team Coordinator?

**Founder Decision (FR-004):**
> WAOOAW's team bundle comes with a Team Coordinator by default — WAOOAW-provided, not customer-appointed. Team functionality is designed for sizable/enterprise customers, not the SMB/MVI tier. Agent Teams will not be built or specced for MVI. The constitution recognises Agent Teams as a future constitutional domain to ensure all future architecture is designed with teams in mind.

**Constitutional Team Architecture (for future epochs):**
1. Customer employs the TEAM as a unit via a Team Employment Contract
2. Team Coordinator is WAOOAW-provided (bundled ProfessionalTemplate, like CS Agents from FR-001)
3. Each team agent has a Domain Decision Space; the Team Decision Space governs inter-agent coordination
4. Domain authority boundaries are explicit: only the CA agent can instruct the Accountant agent on financial classification; the Marketing agent cannot direct the CA agent on budget approval
5. Emergency Stop covers the entire team simultaneously — team-level, not per-agent
6. Team Evidence Ledger captures cross-agent decisions, not just individual agent actions
7. Escalation to customer only when Team Decision Space is exceeded

**When this becomes active:**
- IB-018 added to institutional backlog as DEFERRED (enterprise tier, post-MVI)
- Business Architect sprint required to add Domain 11 (Team Orchestration) to capability map
- Constitutional Analyst sprint required to produce claims for inter-agent authority delegation

**Status:** RESOLVED — 2026-07-08 (architecture deferred, constitution aware)

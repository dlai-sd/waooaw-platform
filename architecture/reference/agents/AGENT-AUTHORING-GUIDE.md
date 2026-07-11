# Agent Authoring Guide

**Authority:** GENESIS Part 05 — Agent Definition Protocol
**Date:** 2026-07-09 (v2.0 — gate-enforced template replacing guide-only template)
**Purpose:** Mandatory template for every new Digital Professional type on WAOOAW. This is a GATE, not a guide. An agent spec that is incomplete in any section cannot be activated.

**GATE vs GUIDE distinction:**
- A guide: follow if you remember to. Partial compliance passes.
- A gate: every section is binary (present and complete, or absent). Missing any section = BLOCKED. An automated agent can verify this gate by querying the repository.

Before any implementation sprint for a new agent type begins, ALL sections of this template must exist, be complete, and have passed EA review and Founder approval.

---

## When to Create a New Agent Specification

Create a new agent specification when:
- A new professional domain is being added to the platform (e.g., Legal Professional, HR Professional)
- A new variant of an existing domain is substantially different (e.g., B2B Digital Marketing vs B2C)
- A new Acceptance Scenario is being implemented that isn't covered by an existing agent type

---

## Agent Specification Structure

Copy this template. Fill every section. Leave no section blank.

---

```
# [Agent Name] Specification
# e.g., "Digital Marketing Professional — Healthcare"

## 1. Agent Identity

Domain:             [field of expertise — e.g., Digital Marketing: Healthcare]
Sub-domain:         [specialization — e.g., Dental Practice, Beauty & Aesthetics, Fitness]
Persona tone:       [how the agent communicates — always: expert + consultant + partner]
Expertise claim:    [what the agent knows deeply — e.g., Indian dental patient behavior,
                    Instagram healthcare content, local SEO for medical practices in India]
Professional type:  [professional_type enum value — e.g., DIGITAL_MARKETING_HEALTHCARE_DENTAL]

## 2. Target Customer Personas

| Persona | Business | Location | Goal |
|---|---|---|---|
| [Name] | [Business type] | [City] | [Business outcome] |

Acceptance Scenarios satisfied: [AS-001, AS-002, etc.]

## 3. Skill Catalogue

For each Skill, complete ALL sub-sections. No partial specifications.

---

### Skill N: [Skill Name]

**Skill type:** [SKILL_TYPE_ENUM — e.g., INSTAGRAM_CONTENT_MARKETING]
**Business KPI:** [measurable outcome — e.g., "Instagram-driven appointment enquiries per month"]
**Execution model:** [APPROVAL_GATE / PRE_AUTHORIZED]

**Decision Space:**
- Authorized: [what this skill can do without asking]
- Prohibited: [what this skill may NEVER do — constitutional and business constraints]
- Always-ask: [what requires customer approval before executing]

**RAG Sources:**
| Tier | Knowledge | Description |
|---|---|---|
| 1 — Domain | [category] | [what is retrieved and why] |
| 2 — Customer | [category] | [what per-customer context is needed] |
| 3 — Platform | [category] | [what aggregate patterns are relevant] |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure mode |
|---|---|---|---|---|
| [name] | [mcp-server-name] | [tool.action] | [Decision Space entry that authorizes it] | DEGRADABLE / REQUIRED |

**Constitutional constraints:**
- [what this skill must NEVER do regardless of customer authorization]

---

## 4. Onboarding Conversation Flow

The conversational flow through which a customer configures this professional type.
Must complete in ≤ 15 minutes (AD-013). Questions are in business language (DP-011).

```
AI: "[Opening question — establish business context]"
Customer: [expected response type]

AI: "[Goal-setting question — business KPI targets]"
Customer: [expected response type]

AI: "[Credential question — what access the agent needs]"
Customer: [expected response type]

AI: "[Schedule question — when/how often]"
Customer: [expected response type]

AI: "[Confirmation — presents proposed configuration in business language]"
Customer: approves / requests adjustment

OUTCOME: Complete DecisionSpaceInput JSON derived from conversation
```

## 5. Professional Template Definition

```
ProfessionalTemplate {
  name:               "[Display name for catalogue]"
  description:        "[One sentence: what this professional does for which customer]"
  professional_type:  "[PROFESSIONAL_TYPE_ENUM]"
  lifecycle_type:     "PERMANENT"  // or SESSION_BOUND for short engagements
  decision_space_template: {
    execution_model: [APPROVAL_GATE / PRE_AUTHORIZED]
    professional_type: "[PROFESSIONAL_TYPE_ENUM]"
    authorized_actions: [
      { actionType: "...", description: "...", parameters: {} },
    ]
    prohibited_actions: [
      { actionType: "...", description: "..." },
    ]
    always_ask_actions: [
      { actionType: "...", description: "..." },
    ]
  }
  is_published: true
}
```

## 6. New MCP Servers Required

List every MCP server this agent requires that is not already in `architecture/reference/containers.md`. If no new servers are needed, write "None — all required MCP servers already in platform inventory."

| MCP Server | Data Source | Status | Built by |
|---|---|---|---|
| `[server-name]-mcp` | [API / dataset] | New / Extend existing | WAOOAW-built / Third-party |

For each new server: confirm it is added to `containers.md` MCP Integration Layer inventory and `docker-compose.yml` stubs (Section 9 Architecture Chain Update Checklist).

## 7. Learning Loop

**Customer feedback signals captured:**
- [what the agent learns from customer approvals/rejections]

**Domain knowledge contribution (Tier 1 + Tier 3):**
- [what patterns flow to WAOOAW IP after anonymization]

**Customer context learning (Tier 2):**
- [what stays private to the customer]

## 8. Unit Economics

**Why required:** An agent spec without pricing is not investment-ready for Founder approval. Include realistic estimates — not aspirational ones.

```
| Model | Customer pays | WAOOAW receives | Path to scale |
|---|---|---|---|
| [direct subscription] | ₹/month | ₹/month | [payment method, distribution] |
| [bundle/B2B] | ₹0 | ₹/unit/month | [B2B partner, volume] |
| [government/institutional] | ₹0 | ₹/unit/month | [contract structure] |

Infrastructure cost: ~₹X/customer/month at [N] active customers
Minimum viable margin: ₹Y/customer/month. Achievable at [N] customers.
```

## 9. Constitutional Checklist

Before submitting for EA review, confirm:
- [ ] Every Skill has a measurable business KPI (C-037)
- [ ] Every MCP tool call has a Decision Space authorization entry (C-041)
- [ ] Every prohibited action explicitly protects a constitutional principle
- [ ] The onboarding flow is completable in ≤ 15 minutes in business language (AD-013, C-039)
- [ ] At least one Acceptance Scenario is cited
- [ ] RAG Tier 1 and Tier 2 sources are explicitly separated (FR-003)
- [ ] No prohibited action violates a Constitutional Floor (Emergency Stop, Evidence First, Audit Ledger)
- [ ] **Learning from R011-01 / R012-01: any real-world authorization the agent needs from the customer (image consent, broker API access, platform credentials) must be an always-ask action type that creates a constitutional evidence record. An assumed authorization is a constitutional gap.**
- [ ] **C-042 check: if your agent serves customers with limited technical or digital literacy — farmers, healthcare workers, artisans — the Vocabulary Mandate applies. Add a Vocabulary Translation Layer to every Skill. No technical data surfaced to customer. All outputs actionable in their vocabulary.**
- [ ] **C-048 check (Information Non-Exploitation): does any Skill use the agent's information advantage against the customer's interests — steering them toward higher-tier plans they don't need, continuing execution of a known-failing strategy, or optimising for platform metrics at the expense of customer outcomes? If yes → redesign the Skill. C-048 violations cannot be fixed in the Decision Space — they require redesigning the Skill's objective.**
- [ ] **C-049 check (Honest Limitation Disclosure): does every Self-Governance Diagnosis reasoning step include a C-049 check — "Can I deliver this customer's goal with my current capabilities? If not, do I say so explicitly?" The Self-Governance Escalation (Section 3.14.4) must include `c049_honest_assessment` in its output schema.**
- [ ] **C-050 check (Strategic Cognition): does Section 3.15 exist in this spec? Are both SKILL_ACTIVATION_PLAN and PERFORMANCE_ASSESSMENT prompts catalogued? Are trigger events declared in the Professional Template? An agent without strategic cognition is a schedule, not a professional.**

## 9b. Section 3.15 — Strategic Cognition Standard (MANDATORY — every agent)

> **Why required (C-050):** Skill execution without strategic oversight is not professional judgment. Every agent must reason about its entire skill portfolio at key lifecycle points — not just execute skills on their individual heartbeats. This section is gate-enforced (Activation Gate Section 10). Missing this section = GATE BLOCKED.

---

### 3.15.1 Strategic Cognition Model

The agent's strategic cognition operates at two levels:

| Level | Prompt type | Question answered | When invoked |
|---|---|---|---|
| **Planning** | `SKILL_ACTIVATION_PLAN` | "Given what I know about this customer, which skills should I activate, in what order, and why?" | After initial profiling/onboarding data is ready |
| **Assessment** | `PERFORMANCE_ASSESSMENT` | "Given what's happened, is my current skill configuration achieving the customer's goal? What must change?" | Periodic review cadence + on material deviation |

Both prompts are constitutional artifacts (C-045, C-050). Both outputs are Reasoning Traces (C-047, AD-008). Both feed into the self-governance escalation (Section 3.14.4) when the assessment concludes the strategy must change.

---

### 3.15.2 Trigger Events (MANDATORY — declare in Professional Template)

Specify the exact trigger events for each prompt. At minimum, three event types are required:

| Event type | Trigger condition | Prompt invoked |
|---|---|---|
| **POST_ONBOARDING** | Customer profile reaches `MINIMUM_VIABLE` status | `SKILL_ACTIVATION_PLAN` |
| **PERIODIC_REVIEW** | Regular cadence (weekly / monthly / seasonal — per agent type) | `PERFORMANCE_ASSESSMENT` |
| **DEVIATION_ALERT** | Any skill's KPI pace < 60% of target at mid-period | `PERFORMANCE_ASSESSMENT` (immediate, not waiting for cadence) |

Agent-specific additional triggers (e.g., "market regime change" for Trading, "harvest approaching" for Agricultural) may be declared.

---

### 3.15.3 Required Output Schema Fields

Both prompts must include these fields in their output schemas. These are gate requirements — not implementation details.

**SKILL_ACTIVATION_PLAN must include:**
```
strategic_reasoning_chain:  "Full reasoning from customer context → skill selection → sequence"
skill_activation_sequence:  [{skill_id, rationale, dependency, requires_approval}]
skills_deferred:            [{skill_id, reason, revisit_trigger}]
portfolio_readiness:        "READY_TO_EXECUTE | NEEDS_CUSTOMER_INPUT | BLOCKED"
c050_strategic_intent:      "Plain statement of the professional strategy — why this sequence serves the customer's goal"
c048_check:                 "Does this plan serve the customer's goal or WAOOAW's revenue? Must state 'customer goal' explicitly"
c049_honest_assessment:     "CAN_DELIVER_WITH_THIS_PLAN | CANNOT_DELIVER_MUST_DISCLOSE"
constitutional_basis:       "C-050; C-036; C-037; [others]"
```

**PERFORMANCE_ASSESSMENT must include:**
```
strategic_reasoning_chain:  "Full assessment of portfolio performance → diagnosis → strategic recommendation"
portfolio_health:           "HEALTHY | UNDERPERFORMING | MISALIGNED | CRITICALLY_FAILING"
skill_assessment:           [{skill_id, contributing: bool, kpi_trend, diagnosis}]
strategic_recommendation:   "CONTINUE | ADJUST_SKILL_MIX | ESCALATE | STOP_AND_DISCLOSE"
proposed_adjustments:       [{action: ACTIVATE|DEACTIVATE|UPDATE, skill_id, rationale}]
c049_honest_assessment:     "CAN_DELIVER_WITH_ADJUSTMENTS | CANNOT_DELIVER_MUST_DISCLOSE"
customer_narrative:         "Plain language summary of the strategic picture for customer"
constitutional_basis:       "C-050; C-037; C-048; C-049; DP-019"
```

---

### 3.15.4 Relationship to Section 3.14 (Skill Runtime Config)

Section 3.14 governs **how individual skills run** (approval mode, cadence, budget).  
Section 3.15 governs **why skills run** and **whether they should run at all**.

These are distinct and both mandatory. Section 3.15 sits above Section 3.14: the SKILL_ACTIVATION_PLAN determines which skills the Section 3.14 runtime config applies to.

---

### 3.15.5 Professional Template Declaration

The Professional Template must include a `strategic_cognition` block:

```yaml
strategic_cognition:
  skill_activation_plan_prompt: "{AGENT}/STRATEGIC/SKILL_ACTIVATION_PLAN"
  performance_assessment_prompt: "{AGENT}/STRATEGIC/PERFORMANCE_ASSESSMENT"
  trigger_events:
    - type: "POST_ONBOARDING"
      condition: "customer_profile.status == MINIMUM_VIABLE"
      prompt: "SKILL_ACTIVATION_PLAN"
    - type: "PERIODIC_REVIEW"
      condition: "[cadence — e.g., monthly_day_1, weekly_monday_0800]"
      prompt: "PERFORMANCE_ASSESSMENT"
    - type: "DEVIATION_ALERT"
      condition: "any_skill_kpi_pace < 0.60 at mid_period"
      prompt: "PERFORMANCE_ASSESSMENT"
  strategic_state_table: "business.agent_strategic_state"  # SQL table for persisting plan
```

## 9c. Section 3.16 — Token Economy Standard (MANDATORY — every agent)

> **Why required (C-051):** Every agent must declare its UsageUnit definitions, model tier assignments per prompt, and customer-facing budget communication strategy. An agent spec without a Token Economy section cannot be economically deployed. This section is gate-enforced (Activation Gate Section 11).

---

### 3.16.1 UsageUnit Definitions (MANDATORY)

Every agent must define the UsageUnit types that translate its internal token budget into customer-meaningful service units. UsageUnits are what the customer sees in the portal widget and in WhatsApp messages — never tokens.

```yaml
usage_units:
  - unit_type: "[UNIT_ID — e.g., ADVISORY_DAY, CONTENT_CREATION]"
    label: "[Display name in customer language]"
    label_local: "[Display name in agent's primary language — e.g., Marathi for agricultural]"
    token_output_equivalent: [approximate output tokens per unit]
    monthly_included:
      tier_1: [quantity at lowest tier]
      tier_2: [quantity at mid tier]
      tier_3: [quantity at highest tier]
    rollover_pct: [0-50 — % of unused units that roll to next month]
    emergency_exempt: [true/false — can this unit be used even at 0 remaining?]
```

**Emergency exemption rule:** Any unit that covers a constitutional obligation (Evidence First, Emergency Stop, constitutional disaster alert) MUST have `emergency_exempt: true`. The budget cannot block constitutional floors.

---

### 3.16.2 Model Tier Assignment (MANDATORY — per prompt)

The Prompt Catalogue section of this spec must include a `minimum_model_tier` column:

| Prompt ID | Step | Type | `minimum_model_tier` |
|---|---|---|---|
| `AGENT/SKILL/PROMPT_ID` | description | BREAKING/BEHAVIOURAL/PHRASING_ONLY | FRONTIER/MID_TIER/LOCAL/FREE_BATCH |

**Assignment rules:**
- `BREAKING`: Always `FRONTIER` — constitutional decisions cannot have degraded reasoning
- `BEHAVIOURAL` (complex): `FRONTIER` for first-time runs (onboarding, first plan, first seasonal recommendation); `MID_TIER` for routine repetitions
- `BEHAVIOURAL` (routine): `MID_TIER` — daily heartbeats, check-ins, reports, content variants
- `PHRASING_ONLY`: `LOCAL` — vocabulary translation, formatting, acknowledgment generation
- `CLASSIFICATION`: Always `LOCAL` — Message Classification Gate is invariant at LOCAL tier
- `USAGE_SUMMARY`: Always `MID_TIER` — communicating budget status is BEHAVIOURAL quality

---

### 3.16.3 Message Classification Strategy

Declare the classification categories relevant to this agent and the path for each:

```yaml
message_classification:
  categories:
    - category: "[CATEGORY_NAME]"
      examples: ["example phrase 1", "example phrase 2"]
      path: "ZERO_COST | LOW_COST | STANDARD | PREMIUM | EMERGENCY"
      response_type: "TEMPLATE | CACHE | MCP_DIRECT | LLM_DISPATCH | CE_EMERGENCY"
  estimated_zero_cost_pct: [X%]  # What % of messages expected to hit ZERO_COST path
```

---

### 3.16.4 Customer Budget Communication

Declare how the agent communicates remaining budget to the customer:

```yaml
budget_communication:
  thresholds:
    - remaining_pct: 30
      message_template: "[What the agent says at 30% remaining, in customer language]"
      channel: "[WHATSAPP | PORTAL | PUSH]"
    - remaining_pct: 10
      message_template: "[What the agent says at 10% remaining]"
      channel: "[WHATSAPP | PORTAL | PUSH]"
  period_reset_message: "[What the agent says at start of new billing period]"
  emergency_override_message: "[What the agent says when serving exempt advisory despite 0 units]"
```

**Emergency override message example (agricultural):**
> "Suresh dada, I know we've used all your advisory days, but this weather alert is too important to delay. No charge for this."

---

## 9d. Section 3.17 — Off-Topic Boundary Standard (MANDATORY — every agent)

> **Why required (C-036, C-037, C-048):** A Digital Professional has a defined mandate — its Skills are constitutional units (C-036). Engaging with requests outside that mandate wastes the customer's UsageUnit budget (C-048 violation), undermines professional identity, and delivers zero business value (C-037 violation). Every agent must declare its professional boundary and the graceful redirection strategy it uses when customers venture outside it.

---

### 3.17.1 Off-Topic Classification Categories (in addition to Token Economy categories)

The Message Classification Gate classifies off-topic messages into three categories. Each requires a different deflection strategy:

| Category | Definition | Agent response |
|---|---|---|
| `SOCIAL_CHATTER` | Small talk, personal questions, unrelated life topics | Warm acknowledgment + immediate specific monitoring hook |
| `ADJACENT_PROFESSIONAL` | Topic in the customer's business domain but outside this agent's skills | Empathetic boundary + WAOOAW cross-referral if applicable + monitoring hook |
| `OFF_TOPIC_MISUSE` | Using the agent as a general AI assistant or outside its professional mandate | Clear professional scope statement + most urgent active monitoring hook |

---

### 3.17.2 The `off_topic_redirect_hooks` Declaration (MANDATORY)

Every agent spec must declare exactly 5 redirect hooks — real-time data signals the agent continuously monitors that can be deployed as pivot points in any deflection response. These are **pre-fetched from live data at each conversation start**, not LLM-generated at deflection time.

```yaml
off_topic_redirect_hooks:
  - hook_id: "[identifier]"
    data_source: "[DB table / MCP tool that feeds this hook]"
    hook_template: "[How this hook is phrased in a redirect — 1 sentence, specific]"
    urgency: "HIGH|MEDIUM|LOW"  # HIGH hooks are used first
```

The Off-Topic Redirect prompt receives the TOP hook by urgency as its redirect anchor. Multiple hooks ensure variety across the 3-attempt graduation.

---

### 3.17.3 `adjacent_professional_routing` Declaration (MANDATORY if other agent types exist)

If another WAOOAW professional type handles topics the customer may ask about, declare the routing here. This turns off-topic deflection into a cross-discovery moment.

```yaml
adjacent_professional_routing:
  - topic_category: "[topic this agent cannot handle]"
    waooaw_professional_type: "[professional_type that CAN handle it — null if none]"
    referral_message_template: "[How to refer warmly in 1 sentence]"
```

**Example (DMA agent):**
```yaml
adjacent_professional_routing:
  - topic_category: "tax_gst_compliance"
    waooaw_professional_type: "ACCOUNTING_PROFESSIONAL"  # Not yet built — say "coming soon"
    referral_message_template: "GST advice is outside my area — WAOOAW's Accounting Professional handles that."
  - topic_category: "hiring_hr"
    waooaw_professional_type: "HR_PROFESSIONAL"
    referral_message_template: "Hiring advice isn't my focus — that's the HR Professional's territory."
```

---

### 3.17.4 Constitutional Checklist Addition

- [ ] **C-036/C-037/C-048 check (Off-Topic Boundary): Section 3.17 exists. 5 redirect hooks declared with data sources. `adjacent_professional_routing` declared. Off-Topic Redirect prompt exists in Prompt Catalogue (`{AGENT}/BOUNDARY/OFF_TOPIC_REDIRECT`). The 3-attempt graduated pattern is declared in agent spec.**

---

## 10. Review and Approval

Reviewer: Enterprise Architect
Approval: Founder

Review creates: `reviews/R-NNN-sprint-N-agent-{name}-ea-review.md`

---

## 11. Architecture Chain Update Checklist (MANDATORY — every agent create/update)

> **Why this exists:** v0.12.0 simulation run revealed that two new agent specs left 9 architecture layers inconsistent — capabilities, drivers, principles, containers, component specs, data schema, and infra were not updated alongside the agent spec. This checklist is the fix. It is **not optional**. Apply it every time an agent spec is created or meaningfully updated.

### 11.1 — For every new agent spec

| Layer | File | What to update | Skip condition |
|---|---|---|---|
| Capabilities | `knowledge/business-capabilities.md` | Add a new Domain section with one capability per major Skill | Never skip |
| Drivers | `knowledge/architectural-drivers.md` | Add an AD entry if the agent introduces a new HARD non-functional constraint | Skip only if no new constraint |
| Principles | `knowledge/design-principles.md` | Add a DP entry if the agent requires a new structural engineering pattern | Skip only if pattern already defined |
| Containers | `architecture/reference/containers.md` | Add any new MCP servers to the MCP Integration Layer server inventory table | Skip if no new MCP servers |
| MCP Tool Catalogue | `architecture/reference/mcp-tool-catalogues.md` | Add full tool signature spec for every new MCP server (request, response, authorization, failure mode) | Skip if no new MCP servers — but if MCP server is referenced in spec without a catalogue entry, this is a GATE BLOCKER |
| Prompt Catalogue | `architecture/reference/prompts/` | Create prompt file for agent type; add every prompt to agent_prompt_versions seed data; update README index | NEVER skip — missing approved prompt = INFERENCE_BLOCKED at runtime (C-045, AD-018) |
| Component spec | `architecture/reference/components/ai-runtime.md` | Add/expand any component behavior the agent requires (new processing pipelines, new RAG tiers, new VTL behavior) | Skip if no new AI Runtime behavior |
| Data schema | `infrastructure/postgres/init/03-enums-and-tables.sql` | Add any tables the agent needs (profiles, session records, progressive state, logs) | Skip if no new tables |
| RLS policies | `infrastructure/postgres/init/04-rls-policies.sql` | Add RLS policies and GRANT statements for every new table | NEVER skip — new table without RLS = AD-004 violation |
| Docker Compose | `docker-compose.yml` | Add env URL + stub service for each new MCP server; add to ai-runtime env block | Skip if MCP server already exists |
| GENESIS | `constitution/GENESIS.md` | Add agent to Ratified Professional Types table | NEVER skip |
| Capability map | `architecture/reference/capability-to-container-map.md` | Add all new capabilities with owning container and supporting containers | Never skip |
| AGENT-ENTRY | `constitution/AGENT-ENTRY.md` | Update approved agent list and routing table | Never skip |
| ADR | `adr/` | Create an ADR if the agent introduces a new architectural decision | Skip if no new architectural decision |
| Project State | `constitution/PROJECT_STATE.md` | Update version, agents table, and WORK MENU | Never skip |
| README | `README.md` | Update version number | Never skip |

### 11.2 — For agent updates (existing spec amended)

Apply only the layers affected by the change type. Every change type has a MINIMUM required update set — below the minimum is a GATE BLOCKER.

| Change type | Minimum required updates | Additional if applicable |
|---|---|---|
| **New Skill added** | Capabilities (+sub-capability), Prompt Catalogue (+prompts for new skill), MCP Catalogue (+tool signatures if new MCP), Containers (+MCP if new), Docker Compose (+stub if new), Data Schema (+tables if new), RLS (+policies if new tables), Capability map (+new capability) | AI Runtime (+pipeline if new), ADR (+if new architectural decision) |
| **New MCP tool added** | Containers (+MCP inventory), MCP Catalogue (+tool signature), Docker Compose (+stub + env URL) | AI Runtime (+if new tool class), ADR (+if new external service type) |
| **New prompt added/changed** | Prompt Catalogue (+new prompt in file + seed data + README index), SQL (+seed row in agent_prompt_versions) | BEHAVIOURAL: EA review required. BREAKING: Founder approval required. |
| **New constitutional constraint** | Claims (+new claim if novel), Principles (+new DP if new structural pattern), Agent spec checklist | EA review required regardless |
| **New always-ask action** | Agent spec only — Decision Space updated | Constitutional Checklist re-verify |
| **New RAG source** | AI Runtime (+pipeline description if new tier), Data Schema (+table if new data type) | |
| **Vocabulary Mandate added** | AI Runtime component (+VTL section), AD-015 referenced, Docker (+whatsapp-voice-mcp confirmed), C-042 in constitutional basis | |
| **Skill removed** | Capabilities (comment out sub-capability — never delete), Data Schema (comment out table — never drop), Billing events continue | |
| **Version bump (bug fix / phrasing)** | Agent spec version table only | |

### 11.3 — Agent Update Summary Block

Every PR that creates or updates an agent spec **must include** this summary block in the PR body:

```
## Agent Architecture Chain Update

| Layer | File | Change | Skipped (reason) |
|---|---|---|---|
| Capabilities | business-capabilities.md | [describe] | — |
| Drivers | architectural-drivers.md | [describe] | — |
| Principles | design-principles.md | [describe] | — |
| Containers | containers.md | [describe] | — |
| Component spec | ai-runtime.md | [describe] | — |
| Data schema | 03-enums-and-tables.sql | [describe] | — |
| Docker Compose | docker-compose.yml | [describe] | — |
| GENESIS | GENESIS.md | [describe] | — |
| AGENT-ENTRY | AGENT-ENTRY.md | [describe] | — |
```

An EA review that does not find this block in the PR is automatically a CHANGE REQUEST (missing architectural due diligence).

---

## 12. Agent Version History Convention

Each agent spec file carries a version table at the bottom. Update it with every change:

```markdown
## Version History

| Version | Date | Author (Office) | Change |
|---|---|---|---|
| 1.0 | YYYY-MM-DD | [Office] | Initial draft |
| 1.1 | YYYY-MM-DD | [Office] | [what changed] |
```

---

## 13. Capability-to-Container Map Update

After every new agent spec, verify `architecture/reference/capability-to-container-map.md` includes the new capabilities. If it doesn't, add them. Domain-level capabilities must map to their owning container (typically AI Runtime for execution, Business Platform for lifecycle, Constitutional Engine for evidence).

---

## 14. Agent Activation Gate (BINARY — must PASS before agent can be activated)

This gate is verified by the EA reviewer before issuing APPROVED verdict. Each item is PASS or FAIL — no partial credit.

```
SECTION 1 — SPEC COMPLETENESS
[ ] 1.1  Agent Identity: domain, professional_type, persona, expertise claim — all present
[ ] 1.2  Target Personas: at least 1 Acceptance Scenario cited and ratified in GENESIS
[ ] 1.3  Constitutional Basis: every claim cited is in RATIFIED status (not DRAFT)
[ ] 1.4  Every Skill has: Decision Space (Authorized/Prohibited/Always-ask), RAG Sources, MCP Tools,
         Business KPI, Constitutional Constraints — NO section left blank

SECTION 2 — PROMPT GATE (C-045, AD-018)
[ ] 2.1  A Prompt Catalogue section exists in the agent spec listing every LLM inference point
[ ] 2.2  Every listed prompt has a corresponding file entry in architecture/reference/prompts/
[ ] 2.3  Every listed prompt has an active row in institutional.agent_prompt_versions (seeded in SQL)
[ ] 2.4  No LLM call exists in any pipeline spec that is NOT listed in the Prompt Catalogue
         FAIL condition: "LLM generates X" in pipeline spec without a matching prompt ID → GATE BLOCKED

SECTION 3 — MCP GATE (C-041)
[ ] 3.1  Every MCP server referenced in the spec is in architecture/reference/containers.md inventory
[ ] 3.2  Every MCP server has a tool signature in architecture/reference/mcp-tool-catalogues.md
[ ] 3.3  Every MCP server has a docker-compose.yml stub service with health check
[ ] 3.4  Every MCP server has its env URL in the ai-runtime environment block in docker-compose.yml
         FAIL condition: MCP server name in spec → not in containers.md → GATE BLOCKED

SECTION 4 — SKILL RUNTIME GATE (DP-014, DP-015, C-044)
[ ] 4.1  Skill Runtime Configuration Standard (Section 3.14 equivalent) exists in the spec
[ ] 4.2  Default approval_mode declared for each skill
[ ] 4.3  synthetic_approval_confidence_threshold declared (can be N/A if CUSTOMER_APPROVAL only)
[ ] 4.4  goal_miss_escalation_months declared
[ ] 4.5  delivery_channels declared
[ ] 4.6  monthly_llm_budget declared per skill or per phase

SECTION 5 — EXECUTION LOOP GATE (C-047, AD-019)
[ ] 5.1  Heartbeat schedule declared for each skill (when does the agent wake up per skill?)
[ ] 5.2  Session start trigger declared for PAAS-execution agents (who starts the session?)
[ ] 5.3  Agent execution loop pattern: reasoning-first activity pattern referenced

SECTION 6 — DATA GATE (AD-004)
[ ] 6.1  Every new SQL table has an RLS policy in 04-rls-policies.sql
[ ] 6.2  Every new SQL table has a GRANT statement for the appropriate DB role
[ ] 6.3  No tenant-scoped table is missing a tenant_id or organisation_id discriminator

SECTION 7 — CONSTITUTIONAL GATE
[ ] 7.1  Every Skill's KPI is measurable (what data source produces the measurement?) (C-037)
[ ] 7.2  C-042 check: if agent serves low-literacy customers → Vocabulary Translation Layer present
[ ] 7.3  C-043 check: if agent manages financial spend → budget ceiling is a Constitutional Floor
[ ] 7.4  C-044 check: if agent uses Synthetic Approval → confidence gate + minimum history declared
[ ] 7.5  C-045 check: all prompts approved and seeded (Section 2 gate above)
[ ] 7.6  C-046 check: if agent is platform-internal → operates under the same constitutional governance
[ ] 7.7  C-047 check: agent reasons first, code executes second — no code-determined actions
[ ] 7.8  C-048 check: no Skill uses the agent's information advantage against the customer's interests
[ ] 7.9  C-049 check: Self-Governance Diagnosis prompt includes c049_honest_assessment field; STOP_AND_DISCLOSE is a valid recommended_option

SECTION 8 — ARCHITECTURE CHAIN GATE (Section 11 checklist completed)
[ ] 8.1  Capabilities domain added to knowledge/business-capabilities.md
[ ] 8.2  New drivers/principles added to knowledge/ if applicable
[ ] 8.3  All new MCP servers in containers.md and docker-compose.yml
[ ] 8.4  Capability-to-container map updated
[ ] 8.5  GENESIS Ratified Professional Types table updated
[ ] 8.6  README.md version number updated
[ ] 8.7  PROJECT_STATE.md updated

SECTION 9 — REVIEW GATE
[ ] 9.1  EA Review record exists in reviews/ with APPROVED verdict
[ ] 9.2  Founder approval recorded in agent spec Section 10 (Review and Approval)
[ ] 9.3  All P0 and P1 findings from EA review resolved before activation

SECTION 10 — COGNITION GATE (C-050, AD-021, DP-019)
[ ] 10.1  Section 3.15 (Strategic Cognition Standard) exists in the spec
[ ] 10.2  A SKILL_ACTIVATION_PLAN prompt is catalogued in the Prompt Catalogue section
[ ] 10.3  SKILL_ACTIVATION_PLAN output schema includes: strategic_reasoning_chain,
          skill_activation_sequence, c050_strategic_intent, c048_check, c049_honest_assessment
[ ] 10.4  A PERFORMANCE_ASSESSMENT prompt is catalogued in the Prompt Catalogue section
[ ] 10.5  PERFORMANCE_ASSESSMENT output schema includes: portfolio_health, skill_assessment,
          strategic_recommendation, c049_honest_assessment, customer_narrative
[ ] 10.6  Professional Template declares strategic_cognition block with trigger_events
          (minimum: POST_ONBOARDING, PERIODIC_REVIEW, DEVIATION_ALERT)
[ ] 10.7  C-050 check is present in the Constitutional Checklist section
[ ] 10.8  Both prompts have active rows in institutional.agent_prompt_versions
          FAIL condition: prompts declared in spec but not seeded in SQL → GATE BLOCKED

SECTION 11 — TOKEN ECONOMY GATE (C-051, AD-022, AD-023, DP-020)
[ ] 11.1  Section 3.16 (Token Economy Standard) exists in the spec
[ ] 11.2  UsageUnit definitions declared (at least 1 unit type per subscription tier)
[ ] 11.3  Every unit with constitutional coverage (emergency alerts, Evidence First actions)
          has emergency_exempt: true
[ ] 11.4  Prompt Catalogue includes minimum_model_tier column for every prompt
          FAIL condition: any prompt without a declared tier → GATE BLOCKED
[ ] 11.5  No PHRASING_ONLY or CLASSIFICATION prompt assigned tier above LOCAL
          (over-routing wastes resource — AD-022 violation, DP-020 violation)
[ ] 11.6  No BREAKING prompt assigned tier below FRONTIER
          (under-routing is quality compromise — C-045 violation)
[ ] 11.7  Message classification categories declared with estimated zero_cost_pct
[ ] 11.8  Customer budget communication strategy declared (30%, 10% thresholds)
[ ] 11.9  Usage Summary prompt exists (USAGE_SUMMARY type) in the Prompt Catalogue
[ ] 11.10 C-051 check is present in the Constitutional Checklist section
[ ] 11.11 minimum_model_tier column added to all seed rows in 03-enums-and-tables.sql
          FAIL condition: seeded prompts without minimum_model_tier → GATE BLOCKED

OVERALL GATE RESULT:
  All 11 sections PASS → AGENT MAY BE ACTIVATED
  Any section FAIL → CONSTITUTIONAL BLOCKER → raise blocker in blockers/ → agent NOT activated
```

---

## 15. Agent Update Template

When updating an existing agent spec, identify the change type first. Then follow ONLY the update path for that type.

### Type 1 — New Skill

Steps (in order):
1. Add Skill to Section 3 (Skill Catalogue) — complete all sub-sections
2. Add prompts for new skill to Prompt Catalogue (Section X) + prompt file + SQL seed
3. Add new MCP servers to containers.md + docker-compose + MCP Catalogue
4. Add new SQL tables + RLS
5. Add new capabilities to business-capabilities.md + capability-to-container-map
6. Update Professional Template (Section 7) — add new authorized_actions
7. Update Constitutional Checklist — re-verify all items
8. Run EA review — request CHANGE_TYPE=NEW_SKILL review
9. Update GENESIS if the skill introduces a new execution model or domain first
10. Bump spec version (MINOR: e.g., 1.0.0 → 1.1.0)

Gate check: Sections 1-8 of the Activation Gate above

### Type 2 — New or Updated Prompt

Steps (in order):
1. Add/update prompt in `architecture/reference/prompts/{agent}-prompts.md`
2. Determine change type: PHRASING_ONLY | BEHAVIOURAL | BREAKING
3. If PHRASING_ONLY: standard PR review → merge → update SQL seed version to ACTIVE
4. If BEHAVIOURAL: EA review required → merge after APPROVED → update SQL seed
5. If BREAKING: EA review + Founder approval required → same as Decision Space amendment
6. Insert new row in `agent_prompt_versions` (do NOT update existing active row — create new version)
7. Set `is_active = TRUE` on new version, `is_active = FALSE` on old version (atomic swap)
8. Bump spec version (PATCH for PHRASING_ONLY, MINOR for BEHAVIOURAL/BREAKING)

Gate check: Section 2 of the Activation Gate above

### Type 3 — New MCP Server or Tool

Steps (in order):
1. Add MCP server to `architecture/reference/containers.md` MCP inventory
2. Add full tool signature to `architecture/reference/mcp-tool-catalogues.md`
3. Add stub service to `docker-compose.yml` (env URL + service definition)
4. Add tool reference to the relevant Skill's MCP Tools table in the spec
5. Add CE.ValidateAction authorization requirement to the tool spec
6. If new external service type: create ADR
7. Standard PR review is sufficient (unless the tool introduces new authorization patterns → EA review)
8. Bump spec version (PATCH)

Gate check: Section 3 of the Activation Gate above

### Type 4 — New Constitutional Constraint or Claim

Steps (in order):
1. Write the new claim in `knowledge/claims/C-NNN.md`
2. Add to agent spec constitutional basis
3. Check if claim requires new AD (HARD driver) or DP (structural principle)
4. Update agent spec affected Skills (prohibited_actions, always_ask_actions, or constitutional_constraints)
5. Full EA review + Founder approval required
6. If claim changes what the agent CAN do: re-run the full Activation Gate
7. Bump spec version (MINOR)

Gate check: Full Activation Gate

### Type 5 — Persona or Domain Extension

Steps (in order):
1. Add new persona to Section 2 (Target Customer Personas)
2. Add domain to `business_domain_taxonomy` SQL seed data
3. Check Tier 1 RAG — does new domain need new domain knowledge entries?
4. Check prompts — do any prompts have domain-specific hardcoded content that now needs to generalize?
5. Update agent spec unit economics if domain changes the business model
6. EA review required (persona changes affect what the agent claims to know)
7. Bump spec version (MINOR)

Gate check: Sections 1, 2, 7 of the Activation Gate

---

## 16. Retroactive Compliance Check

All existing agent specs must be checked against the full Activation Gate. Any gate failures become P1 work items before the implementation sprint begins.

**Current compliance status (as of v0.32.0):**

| Agent | Gate Section | Status | Notes |
|---|---|---|---|
| DMA v2.1 | Sections 1–10 | ✓ PASS | R-014 + R-017 + R-018 EA reviews |
| DMA v2.1 | Section 11 (Token Economy Gate) | ⚠ PARTIAL | Section 3.16 + UsageUnits + min_model_tier needed (v0.32.0 sprint) |
| Trading v1.4 | Sections 1–10 | ✓ PASS | R-012 + R-017 + R-018 EA reviews |
| Trading v1.4 | Section 11 (Token Economy Gate) | ⚠ PARTIAL | Section 3.16 + UsageUnits + min_model_tier needed (v0.32.0 sprint) |
| Agricultural v2.3 | Sections 1–10 | ✓ PASS | R-013 + R-015 + R-017 + R-018 EA reviews |
| Agricultural v2.3 | Section 11 (Token Economy Gate) | ⚠ PARTIAL | Section 3.16 + UsageUnits + min_model_tier needed (v0.32.0 sprint) |

**Section 11 (Token Economy Gate) is a new gate introduced in v0.32.0 (C-051). All three agents need the v0.32.0 sprint:**
- Add Section 3.16 Token Economy Standard to each spec
- Declare UsageUnit types and monthly allocations per subscription tier
- Add `minimum_model_tier` to every Prompt Catalogue entry
- Add Message Classification categories + estimated zero-cost %
- Add customer budget communication thresholds
- Add Usage Summary prompt to each agent's Prompt Catalogue
- Add C-051 to each Constitutional Checklist
- SQL: `minimum_model_tier` column + seed rows + `customer_usage_units` table

These are P1 items before the IB-009 implementation sprint begins. Section 11 gate must pass for all three agents before implementation.

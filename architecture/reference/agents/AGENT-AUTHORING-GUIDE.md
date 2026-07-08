# Agent Authoring Guide

**Authority:** GENESIS Part 05 — Agent Definition Protocol
**Date:** 2026-07-08
**Purpose:** Template and instructions for specifying a new Digital Professional type on WAOOAW.

Before any implementation sprint for a new agent type begins, a complete Agent Specification must exist in this directory and be reviewed by the Enterprise Architect and approved by the Founder.

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
| Component spec | `architecture/reference/components/ai-runtime.md` | Add/expand any component behavior the agent requires (new processing pipelines, new RAG tiers, new VTL behavior) | Skip if no new AI Runtime behavior |
| Data schema | `infrastructure/postgres/init/03-enums-and-tables.sql` | Add any tables the agent needs (progressive state, profiles, logs) | Skip if no new tables |
| Docker Compose | `docker-compose.yml` | Add a stub service for each new MCP server | Skip if MCP server already exists |
| GENESIS | `constitution/GENESIS.md` | Verify agent's acceptance scenario (AS-XXX) is listed in Part 04 | Add if missing |
| AGENT-ENTRY | `constitution/AGENT-ENTRY.md` | Update approved agent list and routing table | Never skip |
| ADR | `adr/` | Create an ADR if the agent introduces a new architectural decision (e.g., new external service type, new protocol) | Skip if no new architectural decision |

### 11.2 — For agent updates (existing spec amended)

Apply only the layers affected by the change:

| Change type | Layers to update |
|---|---|
| New Skill added | Capabilities (add sub-capability), Data (new RAG tables if needed), Containers (new MCP server if needed), docker-compose (new stub if needed) |
| New MCP tool added | Containers (MCP inventory table), docker-compose (stub), ai-runtime.md (if new tool class) |
| New always-ask action | Constitutional Checklist re-verify; no layer update usually needed |
| New RAG source | ai-runtime.md (pipeline description), data schema (new table if new data type) |
| New constitutional constraint | Claims (if new claim), Principles (if new structural pattern), Checklist item 9.3 |
| Vocabulary Mandate added | AI Runtime component (VTL section), AD-015 referenced, Docker (whatsapp-voice-mcp confirmed) |
| Skill removed | Capabilities (remove sub-capability), data schema comment the table (never drop), billing events continue |

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

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

## 6. Learning Loop

**Customer feedback signals captured:**
- [what the agent learns from customer approvals/rejections]

**Domain knowledge contribution (Tier 1 + Tier 3):**
- [what patterns flow to WAOOAW IP after anonymization]

**Customer context learning (Tier 2):**
- [what stays private to the customer]

## 7. Constitutional Checklist

Before submitting for EA review, confirm:
- [ ] Every Skill has a measurable business KPI (C-037)
- [ ] Every MCP tool call has a Decision Space authorization entry (C-041)
- [ ] Every prohibited action explicitly protects a constitutional principle
- [ ] The onboarding flow is completable in ≤ 15 minutes in business language (AD-013, C-039)
- [ ] At least one Acceptance Scenario is cited
- [ ] RAG Tier 1 and Tier 2 sources are explicitly separated (FR-003)
- [ ] No prohibited action violates a Constitutional Floor (Emergency Stop, Evidence First, Audit Ledger)
- [ ] **Learning from R011-01 / R012-01: any real-world authorization the agent needs from the customer (image consent, broker API access, platform credentials) must be an always-ask action type that creates a constitutional evidence record. An assumed authorization is a constitutional gap.**

## 8. Review and Approval

Reviewer: Enterprise Architect
Approval: Founder

Review creates: `reviews/R-NNN-sprint-N-agent-{name}-ea-review.md`
```

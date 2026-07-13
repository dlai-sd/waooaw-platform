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
- [ ] **C-052 check (Context Fidelity, Isolation, Uniqueness): (a) FIDELITY — is Context Bootstrap Protocol declared? Does the spec specify that session state, Decision Space, and performance history are loaded before every session? Does the spec prohibit ungrounded historical assertions? (b) ISOLATION — is Tier 3 24-hour write lag declared? For PAAS Trading: is SEBI cross-customer contamination prohibition documented? (c) UNIQUENESS — for content-generating agents: is Creative Fingerprint declared and Creative Fingerprint Enforcer (M-3) invoked before content generation? For advisory agents with shared recommendations: is Agricultural Timing Stagger (M-4) declared?**
- [ ] **C-053 check (Signal Intelligence): is Section 3.18 present? If agent operates in a time-sensitive domain (weather, market, operational), are signal feeds declared? Are all CRITICAL-class signal types marked `emergency_exempt: true`? Is a PROACTIVE_ALERT prompt in the Prompt Catalogue? If NOT applicable, is `signal_intelligence: NOT_APPLICABLE` stated with a reason?**
- [ ] **C-054 check (Skill Intelligence Routing): for multi-skill agents, is Section 3.19 present? Does every Skill have a `skill_capability_manifest` block with ≥ 5 intent_signatures and ≥ 1 collaboration affinity? Is `skill_gap_signalling` declared? Is a SKILL_INTENT_ROUTER prompt (LOCAL tier) in the Prompt Catalogue? If single-skill, is `skill_intelligence_router: NOT_APPLICABLE` stated?**

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
- [ ] **C-055 check (Campaign Coherence): if agent creates multi-post, multi-platform content, Section 3.21 exists. Campaign Brief structure declared with all required fields. SCR 5-check criteria declared with thresholds. Platform Intelligence research declared. Content Approval Modes (POST_APPROVAL, CAMPAIGN_APPROVAL, CAMPAIGN_AUTO) declared with upgrade criteria. MASTER_THEME_PROPOSAL prompt in Prompt Catalogue (FRONTIER/BREAKING). If NOT applicable, `campaign_theme_engine: NOT_APPLICABLE` stated with reason.**

---

## 9h. Section 3.21 — Campaign Theme Engine Standard (MANDATORY for multi-post, multi-platform content agents)

> **Why required (C-055):** A Digital Marketing Professional who creates posts without a campaign strategy is a content factory, not a professional. C-055 makes campaign-coherent content a constitutional obligation. Section 3.21 is gate-enforced (Activation Gate Section 14). Missing this section in a multi-post content agent = GATE BLOCKED.

**Multi-post content test (applies this section if TRUE):**
- Does this agent create more than 3 content pieces per month across one or more platforms?
- If YES → Section 3.21 is MANDATORY.
- If NO → write `campaign_theme_engine: NOT_APPLICABLE` and state the reason.

---

### 3.21.1 Platform Intelligence Declaration (MANDATORY)

The agent must research and recommend a platform mix before any campaign is designed:

```yaml
platform_intelligence:
  research_skill: "[Skill that performs platform research — typically Market Research / Skill 0]"
  research_prompt: "{AGENT}/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH"
  research_cadence: "ONBOARDING + QUARTERLY_REFRESH"
  research_signals:
    - "competitor platform presence and engagement rates"
    - "target audience demographics per platform (domain-specific)"
    - "platform-content fit for business domain"
    - "customer's existing platform accounts and follower count"
  output_fields:
    recommended_platforms:
      - platform: "[INSTAGRAM | YOUTUBE | LINKEDIN | X | FACEBOOK | WHATSAPP | GBP | PINTEREST | THREADS]"
        recommendation: "ACTIVE | ADVISORY | NOT_RELEVANT"
        rationale: "[One sentence: why this platform is / isn't right for this customer]"
        evidence: "[Competitor signals, demographic data that supports the recommendation]"
  platform_mix_approval: "CUSTOMER_APPROVED — customer confirms their platform mix before any campaign"
```

---

### 3.21.2 Campaign Theme Cascade Structure (MANDATORY)

Declare the three-level content hierarchy this agent will produce:

```yaml
campaign_theme_cascade:
  level_1_campaign:
    required_fields:
      - master_theme          # "Dental Preventive Care Series" — the campaign headline
      - campaign_window       # ISO 8601 date range — e.g., "2026-10-01/2026-10-31"
      - target_outcome        # Business outcome in customer language — "+15 preventive bookings"
      - target_audience       # Specific description of who this campaign reaches
      - platform_mix          # From Platform Intelligence, customer-approved
      - content_cadence       # {platform: frequency} for each active platform
      - theme_sequence        # [{week_number, sub_theme, narrative_hook, emotional_target}]
    approval_required: true   # Customer must approve Level 1 before any Level 2 is generated

  level_2_weekly_theme:
    required_fields:
      - week_number
      - sub_theme             # "Prevention is cheaper than cure"
      - narrative_hook        # "Cost anxiety reduction — ₹500 checkup vs ₹15,000 root canal"
      - emotional_target      # "Relief + motivation to book now"
      - platform_execution_notes  # Any platform-specific notes for this week's content
    generated_by: "{AGENT}/CAMPAIGN/WEEKLY_THEME_CASCADE"
    approval_required: false  # Generated automatically from approved Level 1

  level_3_content_variant:
    required_fields:
      - platform
      - week_number
      - content_body          # Platform-specific content (caption, image_prompt, CTA, etc.)
      - audio_script          # Voice script for YOUTUBE_SHORT, INSTAGRAM_REEL, WHATSAPP_VOICE
      - scheduled_at          # When this piece is scheduled to publish
    generated_by: "{AGENT}/CAMPAIGN/PLATFORM_CONTENT_VARIANT"
    scr_required: true        # Every Level 3 content MUST pass SCR before publish
```

---

### 3.21.3 Platform Content Variant Formats (MANDATORY — declare per active platform)

For each platform in the customer's approved platform mix, declare the content format the agent produces:

```yaml
platform_content_formats:
  - platform: "INSTAGRAM_POST"
    content_fields: ["caption (≤2200 chars)", "image_prompt (for image-generation-mcp)", "hashtags (≤30)", "cta_text", "alt_text"]
    audio: false
    image: true
    publishing_mcp: "instagram-mcp"

  - platform: "INSTAGRAM_REEL"
    content_fields: ["voice_script (60–90 second)", "visual_storyboard (scene-by-scene)", "caption (≤2200 chars)", "hashtags"]
    audio: true
    image: true
    publishing_mcp: "instagram-mcp"

  - platform: "YOUTUBE_SHORT"
    content_fields: ["voice_script (≤60 seconds)", "visual_storyboard", "title (≤100 chars)", "description (≤5000 chars)", "tags"]
    audio: true
    image: true
    publishing_mcp: "youtube-mcp"

  - platform: "LINKEDIN_POST"
    content_fields: ["post_text (≤3000 chars, professional tone)", "image_prompt (optional)", "hashtags (≤5)", "cta_text"]
    audio: false
    image: true
    publishing_mcp: "linkedin-mcp"

  - platform: "X_POST"
    content_fields: ["tweet_text (≤280 chars)", "thread_continuation (optional)", "image_prompt (optional)"]
    audio: false
    image: true
    publishing_mcp: "x-mcp"

  - platform: "GBP_POST"
    content_fields: ["post_text (≤1500 chars)", "cta_button_type (BOOK/CALL/LEARN_MORE)", "image_prompt"]
    audio: false
    image: true
    publishing_mcp: "google-business-mcp"

  - platform: "WHATSAPP_BROADCAST"
    content_fields: ["message_text (≤1024 chars, conversational tone)", "cta_link"]
    audio: false
    image: false
    publishing_mcp: "whatsapp-business-mcp"

  - platform: "PINTEREST_PIN"
    content_fields: ["pin_title (≤100 chars)", "pin_description (≤500 chars)", "image_prompt", "destination_link"]
    audio: false
    image: true
    publishing_mcp: "pinterest-mcp"
```

---

### 3.21.4 Synthetic Content Reviewer (SCR) Declaration (MANDATORY)

The SCR is the 5-check quality gate that enables auto-posting. Declare the review criteria and thresholds:

```yaml
synthetic_content_review:
  enabled_for_modes: ["CAMPAIGN_APPROVAL", "CAMPAIGN_AUTO"]
  not_applicable_for_modes: ["POST_APPROVAL"]

  checks:
    - check_id: "SCR_1_THEME_FIDELITY"
      description: "Does this content serve the declared weekly sub-theme and advance the master campaign narrative?"
      method: "Semantic similarity between content and sub_theme + narrative_hook embeddings"
      pass_threshold: 0.80
      model_tier: "LOCAL"
      fail_action: "REGENERATE_WITH_THEME_ANCHOR"

    - check_id: "SCR_2_BRAND_VOICE"
      description: "Is this content in the customer's established brand voice (Creative Fingerprint)?"
      method: "Cosine similarity to brand_voice_embedding (business.customer_creative_fingerprints)"
      pass_threshold: 0.75
      model_tier: "LOCAL"
      fail_action: "REGENERATE_WITH_VOICE_CONSTRAINT"

    - check_id: "SCR_3_COMPLIANCE"
      description: "Does this content comply with platform policies and domain advertising regulations?"
      method: "Rule-based check against known prohibitions (RAG Tier 1: advertising standards)"
      pass_threshold: "ZERO_VIOLATIONS"
      model_tier: "LOCAL"
      fail_action: "FLAG_SPECIFIC_VIOLATION → ROUTE_TO_CUSTOMER"
      # Compliance failures ALWAYS route to customer — never regenerate silently

    - check_id: "SCR_4_UNIQUENESS"
      description: "Is this content differentiated from competitors and from own recent posts?"
      method: "Similarity to competitor_exclusion_embedding < 0.75 AND own_content_30_days < 0.85"
      pass_threshold: "SEE_THRESHOLDS"
      model_tier: "LOCAL"
      fail_action: "REGENERATE_WITH_DIVERSITY_CONSTRAINT"

    - check_id: "SCR_5_QUALITY"
      description: "Is this content professionally produced? Would the customer be proud to post it?"
      method: "LLM quality assessment across: grammar, CTA clarity, emotional resonance, visual-copy alignment"
      pass_threshold: 0.80
      model_tier: "MID_TIER"
      fail_action: "REGENERATE_WITH_QUALITY_BRIEF"

  max_regeneration_attempts: 2  # If 2 regenerations still fail SCR → route to customer
  evidence_record: true         # Every SCR run creates a business.scr_review_records entry
  scr_review_prompt: "{AGENT}/CAMPAIGN/SCR_QUALITY_CHECK"  # for Check 5 only; others are LOCAL
```

---

### 3.21.5 Content Approval Modes (MANDATORY — extend Section 3.14.1 for content skills)

```yaml
content_approval_modes:
  POST_APPROVAL:
    description: "Customer approves every individual content piece before publish"
    upgrade_criteria: "3 months with ≥ 90% approval rate + customer requests upgrade"
    customer_touchpoints: "Every piece of content"
    scr_enabled: false  # SCR runs but results are advisory — customer always the final gate

  CAMPAIGN_APPROVAL:
    description: "Customer approves Campaign Brief + weekly themes. Content that passes SCR auto-publishes."
    upgrade_criteria: "3 months in POST_APPROVAL at ≥ 90% + customer explicitly requests"
    customer_touchpoints: "1 per campaign (brief approval) + weekly digest + SCR failures"
    scr_enabled: true
    scr_failure_routing: "ALWAYS_TO_CUSTOMER — no silent rejection"
    weekly_digest: true  # Customer receives weekly summary of what published + performance

  CAMPAIGN_AUTO:
    description: "Customer approves Campaign Brief only. SCR handles content review. Weekly digest is the only touchpoint."
    upgrade_criteria: "3 months in CAMPAIGN_APPROVAL with <5% SCR failure rate + customer explicitly requests"
    customer_touchpoints: "1 per campaign + weekly digest"
    scr_enabled: true
    max_auto_posts_per_week: 10  # Safety cap — beyond this, route to customer regardless
    downgrade_trigger: "SCR failure rate > 15% in any 30-day period → propose downgrade to CAMPAIGN_APPROVAL"
```

---

### 3.21.6 Campaign Digest (MANDATORY for CAMPAIGN_APPROVAL and CAMPAIGN_AUTO)

Every week, the agent sends a campaign digest that tells the customer:
1. What published this week (and where)
2. How it performed (platform metrics in business language)
3. What's planned for next week (preview of Level 2 sub-theme + 1 sample content piece)
4. Any decisions needed (SCR failures awaiting approval, budget nearing threshold)

```yaml
campaign_digest:
  cadence: "WEEKLY — Monday morning, before next week's content begins"
  delivery_channels: ["PORTAL", "WHATSAPP_TEXT (if opted in)", "EMAIL"]
  prompt: "{AGENT}/CAMPAIGN/CAMPAIGN_DIGEST"
  model_tier: "MID_TIER"
  structure:
    - "THIS_WEEK: What published, on which platforms, how it performed"
    - "NEXT_WEEK_PREVIEW: Sub-theme + 1 sample content piece for customer visibility"
    - "ACTION_NEEDED: SCR failures (if any) + budget status"
    - "CAMPAIGN_HEALTH: Are we on track for the campaign's target outcome?"
```

---

### 3.21.7 Constitutional Checklist Addition

- [ ] **C-055 check (Campaign Coherence): Section 3.21 exists OR `campaign_theme_engine: NOT_APPLICABLE` stated. If applicable: Platform Intelligence declared. Campaign Theme Cascade structure declared (all 3 levels). SCR 5-check criteria declared with thresholds and model tiers. Content Approval Modes declared (POST_APPROVAL → CAMPAIGN_APPROVAL → CAMPAIGN_AUTO) with upgrade criteria. Campaign Digest declared. All campaign prompts in Prompt Catalogue (MASTER_THEME_PROPOSAL as FRONTIER/BREAKING). Campaign tables referenced (content_campaigns, campaign_weekly_themes, campaign_content_items, scr_review_records).**

---

## 9e. Section 3.18 — Signal Intelligence Layer (MANDATORY for time-sensitive domain agents)

> **Why required (C-053):** An agent that waits for a customer to ask about a risk that the agent already knows about has failed its professional duty. Signal Intelligence is not a feature — it is a constitutional obligation for any agent where external signals (weather, market, operational) can materially affect customer outcomes. Missing this section in a time-sensitive agent is a GATE BLOCKER.

**Time-sensitive domain test (applies this section if TRUE):**
- Does this agent operate in a domain where external events (weather, prices, regulations, platform changes) can cause material harm or benefit to the customer within hours if unaddressed?
- If YES → Section 3.18 is MANDATORY.
- If NO (e.g., HR Professional, Legal Professional) → write `signal_intelligence: NOT_APPLICABLE` and state the reason.

---

### 3.18.1 Signal Feeds Declaration (MANDATORY)

Declare every external signal feed the agent must continuously monitor:

```yaml
signal_intelligence:
  signal_feeds:
    - feed_id: "[SIGNAL_FEED_ID — e.g., WEATHER_DISTRICT]"
      mcp_server: "[mcp-server-name]"
      tool_call: "[tool.method_name]"
      poll_cadence: "[ISO 8601 duration — e.g., PT15M for every 15 minutes]"
      relevance_dimension: "[What customer state makes this signal relevant — e.g., crop.stage_day + farm.district]"
      materiality_classifier: "[Rule or LOCAL model that scores 0.0–1.0 — describe the logic]"
```

---

### 3.18.2 Signal Types and Urgency Classes (MANDATORY)

Declare every named signal type this agent can detect. Each must be mapped to an URGENCY_CLASS with a specific triggering rule:

```yaml
  signal_types:
    - signal_type: "[SIGNAL_TYPE_ID — e.g., WEATHER_HAIL_RISK]"
      feed_id: "[references signal_feeds above]"
      skill_id: "[which active Skill handles this signal]"
      urgency_class_rule: "[explicit condition for CRITICAL/HIGH/ADVISORY — e.g., hail_probability > 0.6 AND stage_day > 60 → CRITICAL]"
      urgency_class: "CRITICAL | HIGH | ADVISORY"
      emergency_exempt: true | false   # CRITICAL signals MUST be true
      channel: "[WHATSAPP_VOICE | WHATSAPP_TEXT | PORTAL | PUSH | ALL]"
      trai_outside_window_behavior: "HSM_TEMPLATE_ONLY | DEFER | IMMEDIATE"
        # IMMEDIATE only for URGENCY_CLASS=CRITICAL
      evidence_action_type: "[CAL action type for evidence record — e.g., PROACTIVE_SIGNAL_ALERT]"
```

**URGENCY_CLASS definitions (non-negotiable):**
| Class | Materiality score | Delivery | Budget | TRAI window |
|---|---|---|---|---|
| `CRITICAL` | ≥ 0.90 | Immediate | `emergency_exempt: true` — budget cannot block | Override with HSM; CRITICAL is a constitutional obligation |
| `HIGH` | 0.70–0.89 | Within 1 hour | Costs 1 UsageUnit | Within window: send. Outside: HSM template only |
| `ADVISORY` | 0.50–0.69 | Next heartbeat bundle | No extra cost | Bundled with scheduled message |

---

### 3.18.3 Proactive Communication Prompts (MANDATORY)

At minimum one prompt must exist for proactive signal delivery. Add to Prompt Catalogue:

| Prompt ID | Type | Tier | Description |
|---|---|---|---|
| `{AGENT}/SIGNAL/PROACTIVE_ALERT` | `BEHAVIOURAL` | `MID_TIER` | Converts raw signal event into customer-vocabulary alert with actionable guidance |
| `{AGENT}/SIGNAL/ADVISORY_BUNDLE` | `BEHAVIOURAL` | `MID_TIER` | Bundles multiple ADVISORY-class signals into a single coherent brief |

**CRITICAL signal prompts** may not be downgraded below MID_TIER — constitutional communications require professional quality reasoning.

---

### 3.18.4 HSM Pre-Approved Templates (MANDATORY if agent sends WhatsApp)

For each signal type that requires out-of-TRAI-window delivery, declare the HSM template content. These must be submitted to Meta for pre-approval before the agent can communicate outside the 24-hour service window.

```yaml
  hsm_templates:
    - signal_type: "[SIGNAL_TYPE_ID]"
      template_name: "[Meta HSM template name]"
      template_text: "[Exact text in customer's language — no variables except {{1}}=customer name]"
      meta_approval_status: "PENDING | APPROVED | REJECTED"
```

---

### 3.18.5 Constitutional Checklist Addition

- [ ] **C-053 check (Signal Intelligence): Section 3.18 exists OR `signal_intelligence: NOT_APPLICABLE` with reason stated. If applicable: all signal feeds declared with poll cadence. All signal types declared with explicit urgency_class_rule. All CRITICAL signals have `emergency_exempt: true`. All CRITICAL signals have `whatsapp_template_category: UTILITY` (CRITICAL signals are service obligations, not marketing — MARKETING template for a constitutional alert = C-053 violation). Multi-signal bundling rule declared or inherits platform default. PROACTIVE_ALERT prompt exists in Prompt Catalogue. Evidence action type declared for each signal type. HSM templates declared for any out-of-window signals.**

---

## 9f. Section 3.19 — Skill Intelligence Router Standard (MANDATORY for all multi-skill agents)

> **Why required (C-054):** An agent with more than one Skill that forces its customer to select the right Skill is not a digital professional — it is a labelled menu. Skill routing is a professional obligation. Every multi-skill agent must declare a Skill Capability Manifest (SCM) for each Skill so the Skill Intelligence Router (SIR) can serve any customer request to the correct Skill(s) at LOCAL tier cost. Missing SCMs are a GATE BLOCKER.

**Multi-skill test (applies this section if TRUE):**
- Does this agent expose more than one Skill to customers? If YES → Section 3.19 is MANDATORY for every Skill.
- Single-skill agents write `skill_intelligence_router: NOT_APPLICABLE` and state the reason.

---

### 3.19.1 Skill Capability Manifest (MANDATORY per Skill)

Every Skill section must include a `skill_capability_manifest` block. Add it immediately after the Skill's introductory table (after Business KPI, Execution model lines):

```yaml
skill_capability_manifest:
  skill_id: "[SKILL_TYPE — e.g., INSTAGRAM_MARKETING]"
  version: "1.0"

  intent_signatures:
    # Minimum 5 natural-language phrases that characterise what customers ask for this Skill
    - "[phrase 1]"
    - "[phrase 2]"
    - "[phrase 3]"
    - "[phrase 4]"
    - "[phrase 5]"

  servable_request_types:
    "[REQUEST_TYPE_ID]": "[Description of what this skill can do for this request type]"

  unservable_request_types:
    # Explicit routing exclusions — what this skill CANNOT do and where to send it
    - intent: "[what customer asks that this skill cannot serve]"
      routes_to_skill: "[SKILL_TYPE_ID of the skill that can serve it, or null]"

  input_requirements:
    required:
      - "[Data or Skill output that MUST exist for this Skill to execute]"
    optional:
      - "[Data or Skill output that improves output quality but does not block execution]"

  output_contributions:
    - type: "[OUTPUT_TYPE_ID — what this skill produces]"
      used_by:
        - "[SKILL_TYPE_ID of skills that consume this output]"

  collaboration_affinities:
    # At least 1 affinity required unless the Skill operates fully independently (must justify)
    - with_skill: "[SKILL_TYPE_ID]"
      relationship: "UPSTREAM | DOWNSTREAM | BIDIRECTIONAL"
      benefit: "[One sentence: what the collaboration achieves that solo execution cannot]"
```

---

### 3.19.2 Skill Gap Signalling (MANDATORY)

When the SIR cannot route a customer request to any active Skill (gap_detected = true), the agent must:

1. Acknowledge the request empathetically and state the professional boundary
2. Emit a `SKILL_GAP_SIGNAL` to the Platform Operations Agent with:
   - `unserviced_intent` — what the customer asked for
   - `frequency_in_30_days` — how many times this intent has been unserved
   - `similar_gap_across_customers` — platform-level count (Tier 3, anonymised)
3. If a WAOOAW adjacent professional type exists for the intent → apply `adjacent_professional_routing` (Section 3.17.3)

This gap signal is the evidence chain for the Agent Skill Proposal Governance Loop (Section 3.20).

```yaml
skill_gap_signalling:
  gap_signal_threshold_days: 30          # Emit signal after this many days of repeated gaps
  gap_frequency_min: 3                   # Minimum occurrences before emitting a gap signal
  cross_customer_threshold: 5            # Escalate to PO review when ≥ N customers hit same gap
  evidence_table: "institutional.skill_gap_signals"
```

---

### 3.19.3 Skill Collaboration Orchestration (MANDATORY for multi-skill requests)

When the SIR identifies a multi-skill request (primary_skill + contributing_skills), the Skill Collaboration Orchestrator (SCO) executes:

```
SCO execution order for multi-skill request:
  1. Identify dependency chain from Skill Dependency Graph
     (UPSTREAM skills execute first; DOWNSTREAM skills receive their outputs)
  2. For each Skill in dependency order:
     a. Load Skill-specific RAG context (Tier 1 + Tier 2 for this Skill)
     b. CE.ValidateAction for the Skill's contribution to the combined request
     c. Execute Skill reasoning step
     d. Pass output to downstream Skills' input_requirements
  3. Combine outputs into single coherent response
  4. Single combined approval request covers all contributing Skills
     (customer approves the whole, not each step separately)
  5. Evidence record created per Skill contribution — the combined request
     produces N evidence records, one per contributing Skill
```

---

### 3.19.4 Constitutional Checklist Addition

- [ ] **C-054 check (Skill Intelligence Routing): Section 3.19 exists OR `skill_intelligence_router: NOT_APPLICABLE` with reason. If applicable: every Skill has a `skill_capability_manifest` block. Each manifest has minimum 5 intent_signatures. Each manifest declares `collaboration_affinities` (or justifies empty). `skill_gap_signalling` block declared. `{AGENT}/SKILL/SKILL_INTENT_ROUTER` prompt exists in Prompt Catalogue (LOCAL tier). Skill gap signal mechanism connects to institutional.skill_gap_signals table.**

---

## 9g. Section 3.20 — Agent Skill Proposal Governance Loop (MANDATORY platform standard)

> **Why required:** When agents consistently encounter customer requests they cannot serve (C-054 gap signal), the platform needs a constitutional pathway from signal → business case → Founder decision → new Skill. Without this pathway, unserved intents are invisible. With it, the platform evolves organically from customer need.

---

### 3.20.1 The Governance Loop

```
STAGE 1 — SIGNAL ACCUMULATION (AI Runtime / Platform Operations Agent)
  SIR emits SKILL_GAP_SIGNAL for each unserved intent
  institutional.skill_gap_signals accumulates signals
  Platform Operations Agent monitors: when gap_frequency_in_30_days ≥ 3
  AND similar_gap_across_customers ≥ 5 → escalate to STAGE 2

STAGE 2 — PRODUCT OWNER REVIEW (Office 11 — Product Owner)
  Platform Operations Agent raises a `type:skill-proposal` GitHub Issue
  Issue body: unserviced_intent, frequency data, affected customers (count only — no names),
              adjacent_professional_type if applicable, suggested skill domain
  Product Owner reads issue → deep review:
    - Is this a genuine new Skill need or a training/prompt gap?
    - Does a WAOOAW adjacent professional already cover this?
    - What are the constitutional dependencies (new claim needed? new MCP server?)
    - What is the business case (pricing impact, customer segment size)?
    - What are the risks (constitutional, regulatory, technical)?
  Product Owner produces: SKILL_PROPOSAL document (see template below)

STAGE 3 — FOUNDER DECISION (GitHub Issue — type:skill-proposal, label:awaiting:founder-approval)
  Product Owner posts SKILL_PROPOSAL to GitHub Issue
  Adds label: `awaiting:founder-approval`
  Founder reviews and decides:
    APPROVE → add label `status:approved`, assign to Business Architect office
    DEFER   → add label `status:deferred`, comment with condition for re-evaluation
    REJECT  → add label `status:rejected`, close issue with reason

STAGE 4 — SKILL IMPLEMENTATION (Standard Section 15 Type 1 flow)
  On Founder APPROVE: Business Architect creates `type:agent-update, update-type:new-skill` issue
  Standard Section 15 Type 1 execution (Architecture Chain Update checklist applies)
  EA Review → Founder approval → merged to main → agent version bumped
```

---

### 3.20.2 SKILL_PROPOSAL Template (Product Owner produces this)

```markdown
## Skill Proposal: [Proposed Skill Name]

**Agent:** [Agent professional_type]
**Proposed Skill Domain:** [e.g., Invoice Generation, Contract Review]
**Signal Evidence:** [N gap events in last 30 days across M customers]
**Sample Unserviced Intents:** (anonymised)
  - "[Intent phrase 1]"
  - "[Intent phrase 2]"

**Product Owner Assessment:**
  - Genuine gap? [YES/NO + reasoning]
  - Adjacent professional covers it? [YES/NO + which one]
  - Constitutional dependencies: [new claims needed? new MCP servers?]
  - Regulatory considerations: [any applicable regulations]
  - Estimated customer segment: [N customers would benefit]
  - Pricing impact: [current tier covers it? or requires tier extension?]

**Risk Assessment:**
  - Constitutional risks: [list]
  - Technical risks: [list]
  - Regulatory risks: [list]

**Proposed Mitigation:** [best option with mitigation plan]

**PO Recommendation:** APPROVE_FOR_SPEC | NEEDS_MORE_DATA | REJECT
**Confidence:** [X%]
```

---

### 3.20.3 Constitutional Checklist Addition

- [ ] **Section 3.20 is a platform standard — it is not declared per-agent. The `institutional.skill_gap_signals` table and `type:skill-proposal` GitHub Issue template must exist before any agent with SIR active is deployed.**

---

## 9i. Section 3.23 — Agent Interview Mode (MANDATORY — every agent)

> **Why required:** WAOOAW's primary customer acquisition channel is the agent demonstrating its own expertise before the customer commits. Every agent must define how a prospective customer can "interview" it — have a live, uninstructed conversation — on WhatsApp or the WAOOAW portal. The agent IS the marketing. This section is gate-enforced (Activation Gate Section 15). Missing this section = GATE BLOCKED.

---

### 3.23.1 The Interview Mode Concept

Before any customer hires an agent, they can talk to it for up to 15 minutes in Demo Mode. No Employment Contract. No persistent memory. No MCP API costs. The agent uses synthetic/example data to demonstrate its capabilities.

This is the most powerful form of marketing: **the product demonstrates itself**.

**Two available channels — every agent must support both:**

```yaml
interview_channels:
  WHATSAPP:
    entry_point: "User messages WAOOAW's main WhatsApp number"
    routing: "Platform routing agent asks: 'Which professional would you like to meet?'
              [menu of available agents]"
    demo_duration_max: 15 minutes
    session_type: DEMO_MODE
    
  PORTAL:
    entry_point: "waooaw.com/meet/[agent-slug] — individual landing page per agent"
    ui_requirements:
      - Agent persona visual (avatar or illustrated character — NOT a real person photo)
      - 3 sample output cards (what this agent produced for an example customer)
      - "Start Interview" button → opens demo session
      - Agent's expertise shown BEFORE the conversation starts
    demo_duration_max: 15 minutes
    session_type: DEMO_MODE
```

---

### 3.23.2 Demo Mode Constraints (All Agents)

```yaml
demo_mode_rules:
  
  PERMITTED:
    - Demonstrate expertise using synthetic/example data
    - Show the agent's full persona (tone, language, personality)
    - Respond to prospect's real questions about their specific situation
    - Show sample outputs (reports, recommendations, content) using anonymised examples
    - Ask the prospect qualifying questions that build engagement
    
  PROHIBITED:
    - Creating any Employment Contract or customer record
    - Making MCP API calls that have per-call costs (exception: read-only free APIs)
    - Building persistent memory across demo sessions
    - Accessing real customer data from any existing customer
    - Claiming specific results that the prospect's business will achieve
    - Extending the demo beyond 15 minutes without explicit prospect request
    
  ALWAYS_HONEST:
    disclosure: "In Demo Mode, the agent must be transparent when using synthetic data:
                 'Main tumhe ek example scenario mein dikhata hoon — yeh ek real customer 
                  ka data nahi hai, but yahi main tumhare business ke liye karunga.'"
    constitutional_basis: C-049 (Honest Limitation Disclosure)
    
  CONVERSION:
    trigger: "Natural conversation close — agent senses prospect is interested"
    NOT: Hard sell or pressure tactics
    YES: "Yeh aapko kaisa laga? Agar aap chahte hain ki main aapke business ke liye 
          kaam karna shuru karun — trial session ek click mein shuru hota hai."
    constitutional_basis: C-048 (Non-Exploitation — never pressure a prospect)
```

---

### 3.23.3 Per-Agent Interview Script Declaration

Each agent spec must declare its Interview Mode behaviour in a `Section 3.23` block:

```yaml
interview_mode_spec:
  agent_slug: [url-friendly name — e.g., dma, tutor, agri-advisor]
  portal_tagline: [one sentence — what this agent does for the customer]
  
  opening_hook:
    whatsapp_opener: [first message the agent sends — 1-2 sentences that demonstrate expertise]
    portal_opener: [slightly richer — shows confidence and personality from message 1]
    
  demonstration_scenarios:  # 2-3 scenarios that show peak capability
    - scenario_name: [e.g., "Market Research Demo"]
      synthetic_data_used: [e.g., "Example dental clinic in Pune"]
      what_prospect_sees: [what the agent produces in this scenario]
      
  sample_outputs:  # 3 cards shown on portal landing page before interview starts
    - title: [e.g., "October Campaign — Dr. Mehta's Dental Clinic"]
      description: [1-2 lines of what was produced]
      visual: [image or illustrated summary — not a real customer screenshot]
      
  conversion_cta:
    whatsapp: [text of the conversion message at end of demo]
    portal: [button text + short description]
    
  mcp_calls_allowed_in_demo:  # Only read-only, free APIs
    - [list of MCPs that can be called — typically none for cost reasons]
    - default: [] (no external MCP calls in demo — use synthetic data)
```

---

### 3.23.4 DMA Interview Mode Example

```yaml
interview_mode_spec:
  agent_slug: dma
  portal_tagline: "The digital marketing professional your business deserves. ₹1,499/month."
  
  opening_hook:
    whatsapp_opener: |
      "Namaste! Main WAOOAW ka Digital Marketing Professional hoon.
       Batao — aapka business kya hai aur city kahan hai? 
       Main 2 minute mein aapke competitors ka analysis karke dikhata hoon."
    portal_opener: |
      "Hello! I'm WAOOAW's Digital Marketing Professional — I work for local businesses 
       across India the way a senior agency account manager would, but at ₹1,499/month.
       Tell me about your business — I'll show you exactly what I'd do for you in the first 30 days."
      
  demonstration_scenarios:
    - scenario_name: "Competitor Intelligence Demo"
      synthetic_data_used: "Example dental clinic, Pune (anonymised, representative)"
      what_prospect_sees: |
        Agent researches (simulated): competitor Instagram activity, GBP review gap,
        Meta ad library presence. Delivers: "Your top competitor has 94 GBP reviews — 
        you have 47. That gap costs you 5-8 patients/month. Here's exactly how I'd close it."
        
    - scenario_name: "First Month Plan"
      what_prospect_sees: |
        Agent produces a 4-week content calendar outline + 2 sample Instagram captions
        + one ad brief for their business type — all using their stated business info.
        
  sample_outputs_portal:
    - title: "Review gap closed: 47 → 94 Google reviews in 4 months"
      description: "Dental clinic, Pune — GBP review generation campaign"
    - title: "October campaign: +18 bookings vs target of 15"
      description: "Healthcare campaign — Instagram + WhatsApp + GBP"
    - title: "₹3,800 revenue per ₹1,000 ad spend (ROAS 3.8×)"
      description: "Meta + Google paid campaign for beauty studio, Mumbai"
      
  conversion_cta:
    whatsapp: "Aapke business ke liye yahi sab main karonga — aur bhi. 
               Trial session mein mile? Ek message mein shuru hota hai."
    portal: "Start my free trial →"
```

---

### 3.23.5 Agricultural Advisor Interview Mode Example

```yaml
interview_mode_spec:
  agent_slug: agri-advisor
  portal_tagline: "Your farming advisor. Crop planning, market timing, government schemes. WhatsApp pe."
  
  opening_hook:
    whatsapp_opener: |
      "Namaskar! Main WAOOAW ka Krishi Salahkar hoon.
       Aapki kaunsi fasal hai aur kaunse district mein aapki zameen hai?
       Main aaj ke mandi bhav aur next season ke liye ek suggestion dungi."
       
  demonstration_scenarios:
    - scenario_name: "Mandi Price Alert Demo"
      synthetic_data_used: "Example cotton farmer, Nagpur (representative)"
      what_prospect_sees: "Live-style price update: 'Nagpur mandi mein today soybean ₹3,820/q 
                           hai. Agar aapka target ₹4,000 hai — main alert kar dunga exact waqt pe.'"
    - scenario_name: "Crop Planning Demo"
      what_prospect_sees: "8-dimension analysis for prospect's stated crop + land + water, 
                           including one non-traditional option with market linkage info."
                           
  conversion_cta:
    whatsapp: "Trial ke liye: apna naam, zameen ka size, aur district batao — 
               ek hafte free mein dekho main kaise kaam karta hoon."
```

---

### 3.23.6 Private Tutor Interview Mode Example

```yaml
interview_mode_spec:
  agent_slug: tutor
  portal_tagline: "The teacher your child deserves — available every day, remembers every session."
  
  opening_hook:
    portal_opener: |
      "Hello! I'm a WAOOAW Private Tutor. I can be configured to your child's exact needs —
       board, class, subjects, language, teaching style.
       Tell me about your child — I'll show you how I'd teach them."
    whatsapp_opener: |
      "Namaste! Main WAOOAW ka Private Tutor hoon.
       Aapke bache ki class kya hai aur kaunsa subject sabse zyada help chahiye?"
       
  demonstration_scenarios:
    - scenario_name: "Discovery Session Demo (Maths)"
      what_prospect_sees: |
        Agent delivers a 5-minute Discovery Session on Quadratic Equations using 
        the Al-Khwarizmi story. Parent sees: teacher personality, story-based approach,
        whiteboard usage (portal only), and how it would feel for their child.
    - scenario_name: "Parent Report Preview"
      what_prospect_sees: |
        Sample weekly progress report: what was covered, what was strong, 
        what to watch, one dinner-table question. Parent sees the reporting they'd get.
        
  sample_outputs_portal:
    - title: "Priya talked about Emmy Noether for 5 minutes at dinner"
      description: "Class 9, Maths — Discovery Session changed how she sees the subject"
    - title: "Arjun's algebra score: 44% → 78% in 6 weeks"
      description: "Class 8, CBSE — targeted weak area sessions"
    - title: "Riya's parent report: 'For the first time, she's excited about Science'"
      description: "Class 6, ICSE — story-based teaching approach"
      
  conversion_cta:
    portal: "Try one free session →"
    whatsapp: "Ek free session mein Sunita Ma'am se milein? Batao kab chalega."
```

---

### 3.23.7 Constitutional Checklist Addition

- [ ] **Section 3.23 (Interview Mode) exists in the agent spec with all required sub-sections**
- [ ] **Demo Mode constraints documented: no Employment Contract, no persistent memory, synthetic data only**
- [ ] **Conversion CTA does not use pressure or urgency language (C-048 Non-Exploitation)**
- [ ] **Demo session disclosure present: agent tells prospect when using synthetic/example data (C-049)**
- [ ] **Portal landing page sample outputs use anonymised/fictional customer examples — not real customer data**

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

SECTION 12 — SIGNAL INTELLIGENCE GATE (C-053) — for time-sensitive domain agents
[ ] 12.1  Section 3.18 exists in the spec OR `signal_intelligence: NOT_APPLICABLE` with reason stated
[ ] 12.2  (If applicable) At least one signal_feed declared with poll_cadence
[ ] 12.3  (If applicable) Every URGENCY_CLASS=CRITICAL signal type has emergency_exempt: true
          FAIL condition: CRITICAL signal without emergency_exempt → C-001 + C-053 violation
[ ] 12.4  (If applicable) PROACTIVE_ALERT prompt in Prompt Catalogue (MID_TIER minimum)
[ ] 12.5  (If applicable) Evidence action_type declared for each signal_type
[ ] 12.6  (If applicable) HSM templates declared for any out-of-TRAI-window signals
[ ] 12.7  C-053 check present in Constitutional Checklist section

SECTION 13 — SKILL INTELLIGENCE ROUTING GATE (C-054) — for multi-skill agents
[ ] 13.1  Section 3.19 exists in the spec OR `skill_intelligence_router: NOT_APPLICABLE` with reason
[ ] 13.2  (If applicable) Every Skill has a `skill_capability_manifest` block
          FAIL condition: any Skill missing SCM → GATE BLOCKED
[ ] 13.3  (If applicable) Each SCM has minimum 5 intent_signatures
[ ] 13.4  (If applicable) Each SCM declares collaboration_affinities OR justifies empty (rare)
[ ] 13.5  (If applicable) skill_gap_signalling block declared with threshold and table reference
[ ] 13.6  (If applicable) SKILL_INTENT_ROUTER prompt exists in Prompt Catalogue (LOCAL tier)
          FAIL condition: no router prompt → SIR cannot operate → GATE BLOCKED
[ ] 13.7  C-054 check present in Constitutional Checklist section

SECTION 14 — CAMPAIGN THEME ENGINE GATE (C-055) — for multi-post, multi-platform content agents
[ ] 14.1  Section 3.21 exists in the spec OR `campaign_theme_engine: NOT_APPLICABLE` with reason
[ ] 14.2  (If applicable) Platform Intelligence declared with research_signals + output_fields
[ ] 14.3  (If applicable) Campaign Theme Cascade structure declared (all 3 levels with required_fields)
[ ] 14.4  (If applicable) SCR 5-check criteria declared with pass_threshold and model_tier per check
          FAIL condition: SCR declared without individual check thresholds → GATE BLOCKED
[ ] 14.5  (If applicable) SCR Check 3 (Compliance) fail_action = ROUTE_TO_CUSTOMER (never silent)
          FAIL condition: any compliance failure routed to auto-regeneration → C-055 violation
[ ] 14.6  (If applicable) Content Approval Modes declared (POST_APPROVAL, CAMPAIGN_APPROVAL, CAMPAIGN_AUTO)
[ ] 14.7  (If applicable) Upgrade criteria declared for each mode transition
[ ] 14.8  (If applicable) Campaign Digest declared (cadence, channels, prompt)
[ ] 14.9  (If applicable) All campaign prompts in Prompt Catalogue:
          MASTER_THEME_PROPOSAL (FRONTIER, BREAKING)
          WEEKLY_THEME_CASCADE (MID_TIER, BEHAVIOURAL)
          PLATFORM_CONTENT_VARIANT (MID_TIER, BEHAVIOURAL)
          SCR_QUALITY_CHECK (MID_TIER, BEHAVIOURAL — Check 5 only)
          CAMPAIGN_DIGEST (MID_TIER, BEHAVIOURAL)
          FAIL condition: any of these missing → GATE BLOCKED
[ ] 14.10 C-055 check present in Constitutional Checklist section

SECTION 15 — INTERVIEW MODE GATE (MANDATORY — every agent)
[ ] 15.1  Section 3.23 (Agent Interview Mode) exists in the agent spec
[ ] 15.2  agent_slug declared (used for portal URL: waooaw.com/meet/[agent-slug])
[ ] 15.3  portal_tagline declared (one sentence, shown before the conversation starts)
[ ] 15.4  opening_hook declared for both WHATSAPP and PORTAL channels
[ ] 15.5  At least 2 demonstration_scenarios declared with synthetic_data_used noted
[ ] 15.6  3 sample_outputs declared for portal landing page
[ ] 15.7  conversion_cta declared for both channels (no pressure language — C-048)
[ ] 15.8  Demo Mode constraints documented: no Employment Contract, no persistent memory
[ ] 15.9  Disclosure statement present: agent tells prospect when using synthetic data (C-049)
[ ] 15.10 mcp_calls_allowed_in_demo declared (default: [] — no paid MCP calls in demo)
          FAIL condition: Section 3.23 absent → agent cannot be marketed → GATE BLOCKED
          FAIL condition: conversion_cta uses urgency or pressure language → C-048 violation

OVERALL GATE RESULT:
  All 15 sections PASS → AGENT MAY BE ACTIVATED
  Any section FAIL → CONSTITUTIONAL BLOCKER → raise blocker in blockers/ → agent NOT activated
```
[ ] 12.1  Section 3.18 exists in the spec OR `signal_intelligence: NOT_APPLICABLE` with reason stated
[ ] 12.2  (If applicable) At least one signal_feed declared with poll_cadence
[ ] 12.3  (If applicable) Every URGENCY_CLASS=CRITICAL signal type has emergency_exempt: true
          FAIL condition: CRITICAL signal without emergency_exempt → C-001 + C-053 violation
[ ] 12.4  (If applicable) PROACTIVE_ALERT prompt in Prompt Catalogue (MID_TIER minimum)
[ ] 12.5  (If applicable) Evidence action_type declared for each signal_type
[ ] 12.6  (If applicable) HSM templates declared for any out-of-TRAI-window signals
[ ] 12.7  C-053 check present in Constitutional Checklist section

SECTION 13 — SKILL INTELLIGENCE ROUTING GATE (C-054) — for multi-skill agents
[ ] 13.1  Section 3.19 exists in the spec OR `skill_intelligence_router: NOT_APPLICABLE` with reason
[ ] 13.2  (If applicable) Every Skill has a `skill_capability_manifest` block
          FAIL condition: any Skill missing SCM → GATE BLOCKED
[ ] 13.3  (If applicable) Each SCM has minimum 5 intent_signatures
[ ] 13.4  (If applicable) Each SCM declares collaboration_affinities OR justifies empty (rare)
[ ] 13.5  (If applicable) skill_gap_signalling block declared with threshold and table reference
[ ] 13.6  (If applicable) SKILL_INTENT_ROUTER prompt exists in Prompt Catalogue (LOCAL tier)
          FAIL condition: no router prompt → SIR cannot operate → GATE BLOCKED
[ ] 13.7  C-054 check present in Constitutional Checklist section

OVERALL GATE RESULT:
  All 13 sections PASS → AGENT MAY BE ACTIVATED
=======
SECTION 14 — CAMPAIGN THEME ENGINE GATE (C-055) — for multi-post, multi-platform content agents
[ ] 14.1  Section 3.21 exists in the spec OR `campaign_theme_engine: NOT_APPLICABLE` with reason
[ ] 14.2  (If applicable) Platform Intelligence declared with research_signals + output_fields
[ ] 14.3  (If applicable) Campaign Theme Cascade structure declared (all 3 levels with required_fields)
[ ] 14.4  (If applicable) SCR 5-check criteria declared with pass_threshold and model_tier per check
          FAIL condition: SCR declared without individual check thresholds → GATE BLOCKED
[ ] 14.5  (If applicable) SCR Check 3 (Compliance) fail_action = ROUTE_TO_CUSTOMER (never silent)
          FAIL condition: any compliance failure routed to auto-regeneration → C-055 violation
[ ] 14.6  (If applicable) Content Approval Modes declared (POST_APPROVAL, CAMPAIGN_APPROVAL, CAMPAIGN_AUTO)
[ ] 14.7  (If applicable) Upgrade criteria declared for each mode transition
[ ] 14.8  (If applicable) Campaign Digest declared (cadence, channels, prompt)
[ ] 14.9  (If applicable) All campaign prompts in Prompt Catalogue:
          MASTER_THEME_PROPOSAL (FRONTIER, BREAKING)
          WEEKLY_THEME_CASCADE (MID_TIER, BEHAVIOURAL)
          PLATFORM_CONTENT_VARIANT (MID_TIER, BEHAVIOURAL)
          SCR_QUALITY_CHECK (MID_TIER, BEHAVIOURAL — Check 5 only)
          CAMPAIGN_DIGEST (MID_TIER, BEHAVIOURAL)
          FAIL condition: any of these missing → GATE BLOCKED
[ ] 14.10 C-055 check present in Constitutional Checklist section

OVERALL GATE RESULT:
  All 14 sections PASS → AGENT MAY BE ACTIVATED
>>>>>>> 699f049 (constitutional(dma): C-055 Campaign Theme Engine + SCR + Platform Intelligence (DMA v2.5, v0.39.0))
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

**Current compliance status (as of v0.61.0):**

| Agent | Gate Section | Status | Notes |
|---|---|---|---|
| DMA v2.9 | Sections 1–14 | ✓ PASS | Multiple EA reviews through R-018 |
| DMA v2.9 | **Section 15 (Interview Mode Gate)** | ⚠ NEEDED | Section 3.23 must be added — see backlog below |
| Trading v1.7 | Sections 1–14 | ✓ PASS | |
| Trading v1.7 | **Section 15 (Interview Mode Gate)** | ⚠ NEEDED | Section 3.23 must be added |
| Agricultural v2.7 | Sections 1–14 | ✓ PASS | |
| Agricultural v2.7 | **Section 15 (Interview Mode Gate)** | ⚠ NEEDED | Section 3.23 must be added |
| Private Tutor v1.0 | Sections 1–14 | ✓ PASS | Simulation 018 validated |
| Private Tutor v1.0 | **Section 15 (Interview Mode Gate)** | ⚠ NEEDED | Section 3.23 template exists in AGENT-AUTHORING-GUIDE 9i; to be added to spec |

**Section 15 (Interview Mode Gate) added in v0.61.0. Backlog for all existing agents:**

```
For each existing agent (DMA / Trading / Agricultural / Private Tutor):
  Add Section 3.23 to the agent spec with:
    - agent_slug
    - portal_tagline
    - opening_hook (WhatsApp + Portal)
    - 2-3 demonstration_scenarios with synthetic_data_used
    - 3 sample_outputs for portal landing page
    - conversion_cta (both channels, no pressure language)
    - mcp_calls_allowed_in_demo: [] (default — no paid MCP calls)

Platform work required alongside specs:
  - waooaw.com/meet/[agent-slug] landing pages (Next.js 14 — existing web component)
  - WAOOAW WhatsApp routing agent (selects which professional to demo)
  - Demo Mode session type in AI Runtime (no Employment Contract, 15-min limit, no persistence)
  - Portal landing page with sample output cards (per agent)
```

These are P1 items before the IB-009 implementation sprint begins. Section 11 gate must pass for all three agents before implementation.

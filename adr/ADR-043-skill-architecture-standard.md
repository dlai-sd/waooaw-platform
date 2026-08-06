# ADR-043 — Skill Architecture Standard

**Status:** Accepted  
**Date:** 2026-08-06  
**Authority:** C-031 (No significant architectural decision without an ADR — LAW); C-036 (Skills are constitutional units)  
**Deciders:** Yogesh Khandge (Founder), Enterprise Architect (INST-004)  
**Related:** ADR-020 (MCP — tool connectivity), ADR-035 (Platform Agent Contract Standard), ADR-042 (Provider Registry — skills declare required providers)

---

## Context

WAOOAW agents are described in agent specification files that declare their tools, constraints, and capabilities. As of 2026-08-06, "capability" is expressed as a flat list of authorized MCP tools inside an agent spec. This creates three structural problems:

**Problem 1 — Capability is coupled to agent identity.** If the Digital Marketing Agent gains a new ability (say, YouTube publishing), the agent spec must be edited and an ADR-type amendment must go through the full agent lifecycle gate. A platform-level concept for packaged, versioned capability units does not exist.

**Problem 2 — No catalog of capabilities customers can choose from.** Hiring an agent requires reading specification documentation. There is no discoverable catalog that says "here are the capabilities you can give this agent, here is what each one costs, here is the Intent Crystallizer prompt it uses." The Skill Registry gap makes the hiring UX opaque.

**Problem 3 — Capability versioning is undefined.** ADR-035 (Platform Agent Contract Standard) governs agent spec versioning, but there is no versioning for the capability units within an agent. If a skill implementation changes (new tool added, Intent Crystallizer prompt improved), there is no mechanism for agents pinned to the old version to remain on it while new hires adopt the new version.

The Founder strategy session on 2026-08-06 identified Skill Architecture as Layer 4 of the platform — currently 0% built — and the first new platform component requiring an ADR before any sprint begins.

---

## Constitutional Basis

| Claim | Application |
|---|---|
| **C-031** | This ADR records the Skill Architecture decision — required before any implementation sprint |
| **C-036** | "Skills are constitutional units" — Skill Catalog + Skill Versioning is the structural realisation of C-036 |
| **C-041** | Tool authorization is governed by Decision Space — Skill definition declares the tool set; agent's Decision Space is derived from its skill assignment |
| **C-032** | Implementation may not create architecture — Skill Catalog design lives here, not in a WC |
| **ADR-035** | Agent Contract Standard — Employment Contract `skills[]` section formalised by this ADR |

---

## Decision

### 1. Skill Definition Standard

A **Skill** is the smallest independently testable, independently versionable unit of agent capability. A skill declaration contains:

```yaml
skill_id: content_publish
version: "1.2.0"
display_name: "Content Publishing"
description: "Publish approved content to connected social platforms on behalf of the customer."

# Tools this skill authorises (maps to C-041 authorized_tools)
tools:
  - meta.post_content
  - meta.post_story
  - youtube.upload_video
  - instagram.post_reel

# Providers this skill requires (maps to ADR-042 Provider Registry)
required_providers:
  - meta
  - google

# Default DCM category for all tool calls declared in this skill
default_dcm_category: DETERMINISTIC_REQUIRED    # publishing is irreversible

# Intent Crystallizer configuration (optional — skills that produce structured intent before acting)
intent_crystallizer:
  enabled: true
  prompt_template: "skills/content_publish/crystallizer_v1.md"
  requires_customer_approval: true
  locked_artifact_schema: "schemas/campaign_brief_v2.json"

# Default autonomy level (maps to DCM dial — customer may tighten, never loosen without amendment)
default_autonomy_level: APPROVAL_REQUIRED

# Constitutional Compliance Tests that must pass before skill is published to registry
cct_suite:
  - CCT-SKILL-CP-01   # Intent Crystallizer produces locked brief before first publish
  - CCT-SKILL-CP-02   # Publishing blocked without locked_artifact in session context
  - CCT-SKILL-CP-03   # CE.ValidateAction called for every publish action

# What billing event this skill's execution maps to (for WBE metering)
billing_event: SKILL_TOOL_CALL
```

### 2. Skill Catalog — Owned by Business Platform

The Skill Catalog is a **Postgres table in the Business Platform instance**, not a new service.

**Rationale:** The Skill Catalog is business configuration data. Business Platform already owns the Employment Contract, provider configs, and billing profiles. Adding a skill catalog is an extension of BP's existing domain — not a new bounded context. Running a fifth service for a catalog of YAML rows would be over-engineering.

**Schema (BP Postgres table `skills`):**

```sql
CREATE TABLE skills (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id        VARCHAR(64) NOT NULL,
  version         VARCHAR(32) NOT NULL,           -- semver: "1.2.0"
  display_name    VARCHAR(128) NOT NULL,
  definition      JSONB NOT NULL,                 -- full skill YAML as JSON
  cct_suite       TEXT[] NOT NULL,                -- CCT IDs that must pass
  status          VARCHAR(32) NOT NULL DEFAULT 'DRAFT',  -- DRAFT | PUBLISHED | DEPRECATED
  published_at    TIMESTAMPTZ,
  deprecated_at   TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (skill_id, version)
);
```

**BP API endpoints for Skill Catalog:**
- `GET /api/v1/skills` — list published skills
- `GET /api/v1/skills/{skill_id}` — latest published version
- `GET /api/v1/skills/{skill_id}/{version}` — specific pinned version
- `POST /api/v1/skills` — (internal, Founder-authorized) publish new skill or version

### 3. Skill Runtime — Co-located in Professional Runtime

The Skill Runtime is **in-process within Professional Runtime**, not a standalone service.

**Rationale:** Skill execution happens inside a PAAS session (ADR-005). The PAAS session is the unit of agent task execution, owned by PR. Skill resolution (fetching the skill manifest, loading the Intent Crystallizer prompt, setting the autonomy level for the session) is a session-open-time operation — it runs inside the Temporal activity that initialises the session. Adding a separate Skill Runtime service would require a synchronous call inside every session open, adding a network hop to the critical path and creating a new failure domain with no governance benefit.

**Skill resolution at session open (in PR):**

```
PAASSessionWorkflow.Open(contract_id, task_request)
        │
        ▼
1. Fetch Employment Contract from BP
   → contract.skills = ["content_publish@1.2.0", "ad_campaign_manager@1.0.0"]
        │
        ▼
2. For each skill: GET /api/v1/skills/{skill_id}/{version} from BP Skill Catalog
   → returns full skill manifest (tools, providers, DCM category, crystallizer config)
        │
        ▼
3. Merge tool sets → session_ctx.authorized_tools (sent to CE.ValidateAction on every call)
4. Load crystallizer prompts → session_ctx.crystallizers[skill_id]
5. Set autonomy levels → session_ctx.autonomy_dial[skill_id]
        │
        ▼
Session is now capability-complete and constitutionally bounded.
```

**Result:** 4+1 service mesh preserved (CE, BP, PR, AIR + oauth-vault). No 6th service. Skill execution is a session concern, not a service concern.

### 4. Skill Assignment in the Employment Contract

**ADR-035 Employment Contract `skills[]` section is formalised by this ADR.**

Employment Contract JSON gains a `skills` array:

```json
{
  "contract_id": "con_xxxx",
  "agent_type": "digital-marketing-professional",
  "tenant_id": "ten_xxxx",
  "skills": [
    { "skill_id": "content_publish", "version": "1.2.0", "assigned_at": "2026-08-06T09:00:00Z" },
    { "skill_id": "ad_campaign_manager", "version": "1.0.0", "assigned_at": "2026-08-06T09:00:00Z" }
  ],
  "autonomy_overrides": {
    "content_publish": "APPROVAL_REQUIRED"
  }
}
```

**Skill amendment rules:**
- Adding a skill = Employment Contract amendment (requires customer consent, new CE evidence record)
- Removing a skill = Employment Contract amendment (customer consent, CE evidence record)
- Upgrading a skill version = Employment Contract amendment (customer sees changelog, accepts or stays on pinned version)
- Customer may tighten autonomy level per skill; may never loosen beyond the skill's `default_autonomy_level`

### 5. Skill Versioning

| Rule | Detail |
|---|---|
| Version is pinned at assignment | Agent stays on `content_publish@1.2.0` until customer accepts an upgrade |
| Minor upgrades (1.2.x) are non-breaking | Tool set unchanged, prompt improvements only; auto-offer in Performance Report |
| Major upgrades (2.0.0) are breaking | New tools or removed tools; require explicit customer consent and contract amendment |
| Deprecated skills | Status = DEPRECATED; new assignments rejected; existing agents receive 90-day warning via WhatsApp (ADR-023) |
| EA must produce a Skill Migration Note with every major version bump | Documents what changed and which agent specs must be re-tested |

### 6. Intent Crystallizer — Generic Pattern

The Intent Crystallizer is a **per-skill, configurable structured-intent approval pattern**. It is not a standalone component — it is a configuration block in the skill definition that PR reads at session open and enforces at execution time.

**How it works (using content_publish as example):**
1. Customer or agent initiates a publishing intent
2. PR's session executor invokes the crystallizer prompt template for `content_publish`
3. Crystallizer produces a `CampaignBrief` (structured JSON artifact per `locked_artifact_schema`)
4. Campaign Brief is presented to the customer via the approval-gate mechanism (PR → BP → customer notification)
5. Customer approves → Brief is locked (hash stored in CE evidence record)
6. Subsequent publishing actions in this session must reference the locked Brief — CTG enforces this by checking `session_ctx.locked_artifacts["content_publish"]` before calling any tool in the skill's tool set
7. No locked Brief = publishing blocked = `MCPToolError(CONSTITUTIONAL_BLOCKED, "Intent crystallization required")`

This is the same pattern for every skill that has `intent_crystallizer.enabled = true`. The Theme Creator for DMA is the first instantiation — it is not DMA-specific code; it is the Crystallizer pattern configured with DMA's prompt template.

---

## Rejected Alternatives

**A — Standalone Skill Service (`src/skill-engine/`):** Skills are execution context, not a runtime boundary. Skill resolution is a session-open-time lookup from BP catalog. A dedicated service adds a network hop on every session open, introduces a new failure domain, and provides no architectural benefit. Rejected — skills are in PR (runtime) and BP (catalog).

**B — Skills as flat tool lists in agent spec (current state):** Does not support versioning, does not produce a customer-discoverable catalog, couples capability to agent identity. Rejected — superceded by this ADR.

**C — Intent Crystallizer as a global service:** Every skill has a different crystallizer prompt and schema. Centralising would require a plugin architecture that adds more complexity than keeping it as a per-skill configuration block in PR's session executor. Rejected.

---

## Implementation Prerequisites

Before any WC opens for Skill Architecture implementation:
1. ✅ ADR-043 merged (this document)
2. ✅ ADR-042 merged (Provider Registry — skills declare required providers)
3. ⏳ BP migration adds `skills` table
4. ⏳ Employment Contract JSON schema updated with `skills[]` array
5. ⏳ PR session open activity updated to resolve and load skill manifests
6. ⏳ CCT-SKILL-CP-01/02/03 written before first Skill sprint WC is opened

*First skill to implement: `content_publish@1.0.0` as part of DMA agent enablement sprint.*

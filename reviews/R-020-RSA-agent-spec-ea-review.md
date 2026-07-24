# EA Review — Reasoning Sprint Analyst Agent Specification

**Review ID:** R-020
**Date:** 2026-07-24
**Reviewer Office:** Enterprise Architect
**Spec reviewed:** `architecture/reference/agents/reasoning-sprint-analyst-agent.md` v1.1
**Review type:** New internal agent — AGENT-AUTHORING-GUIDE activation gate
**Constitutional basis:** C-066 (Authorization Tiers), C-059 (Traceability), C-070 (DNA Inheritance)

---

## Verdict: REQUEST CHANGES → APPROVED (same session)

Initial review identified 3 gate blockers. All 3 were resolved within this review session and
the spec updated to v1.2. Re-review confirms PASS. Final verdict: **APPROVED for DRAFT status.**
Founder ratification required before RATIFIED and implementation sprint can begin.

---

## Gate Blocker 1 — Section 0 Constitutional DNA MISSING (CRITICAL)

**Finding:** The spec declares `Inherits: CONSTITUTIONAL_DNA v1.0` in the header but has no
Section 0 body. Per AGENT-AUTHORING-GUIDE v3.0: "No agent spec may pass EA review without it."

**Resolution:** Section 0 added to spec (see v1.2). Contains:
- Instinct 1 parameters: CE.ValidateAction triggers, Evidence First obligations, DENY conditions
- Instinct 2 parameters: acceptance scenario, quality signal type, C-049 triggers
- Instinct 3 parameters: trust tier, pre-authorized actions list, actions that always require CE

**Gate check:** ✅ PASS after fix

---

## Gate Blocker 2 — Prompt Catalogue MISSING (Section 2 Gate)

**Finding:** §11 describes a `call_llm_with_reasoning()` function calling Claude with extended
thinking. This is an LLM inference point. Per Activation Gate Section 2.1-2.4, every LLM call
must be registered in a Prompt Catalogue. No catalogue existed.

**Resolution:** Minimal Prompt Catalogue section added to spec (see v1.2). Prompt ID:
`RSA/REASONING/DIAGNOSIS`. Model tier declared (FRONTIER). Since the RSA is a pipeline agent
with no `institutional.agent_prompt_versions` DB table yet, the prompt is registered in the
spec only — the SQL seeding is a WC-018+ implementation concern.

**Gate check:** ✅ PASS after fix (spec-level registration; DB seeding deferred to implementation sprint)

---

## Gate Blocker 3 — Acceptance Scenario MISSING (Section 1.2 Gate)

**Finding:** No acceptance scenario cited. Activation Gate 1.2 requires at least 1 AS.

**Resolution:** AS-RSA-001 defined inline (pipeline agents reference their own scenario format,
not customer-facing AS-NNN from GENESIS). Added to spec §12.

**Gate check:** ✅ PASS after fix

---

## Non-Blocking Findings (noted, not blocking)

**NB-1 — Architecture Chain Update not required:**
The RSA is a pipeline agent that reads existing artifacts and writes to existing surfaces
(GitHub, sprint branch). No new MCP servers, no new DB tables, no new containers.
Architecture Chain Update (Section 11) scope: minimal — only the workflow YAML reference
in §10 must be implemented in the execution sprint.

**NB-2 — DB table for improvement_proposals:**
The RSA outputs Level 1 code commits and Level 2 spec PRs. No new DB tables required.
The `reasoning-output.json` artifact is transient (workflow artifact, not persisted to DB).
This is correct for the pipeline context.

**NB-3 — MCP Gate N/A:**
The RSA does not call any MCP tools. It uses the GitHub CLI (`gh`), the Anthropic API directly,
and the `git` CLI. None of these require MCP registration. MCP Gate items 3.1–3.4 are N/A.

**NB-4 — Skill Runtime Gate N/A for pipeline agents:**
The RSA is event-triggered (after sprint failure) not schedule-triggered. Heartbeat cadence
declared as "event-driven (sprint failure)" which satisfies Section 5.1 for pipeline agents.

---

## Activation Gate Summary (post-fix)

```
SECTION 1 — SPEC COMPLETENESS
[✅] 1.1  Agent Identity: present in §1
[✅] 1.2  Acceptance Scenario: AS-RSA-001 defined in §12
[✅] 1.3  Constitutional Basis: C-069, C-070, C-083, C-084, C-085, C-023, C-066 all RATIFIED
[✅] 1.4  Decision Space: §5 complete with authorized + prohibited actions

SECTION 2 — PROMPT GATE
[✅] 2.1  Prompt Catalogue: §13 added — RSA/REASONING/DIAGNOSIS registered
[N/A] 2.3  DB seeding: deferred to implementation sprint (no agent_prompt_versions table yet)
[✅] 2.4  No unregistered LLM calls: extended thinking call in §11 is registered in §13

SECTION 3 — MCP GATE
[N/A] All MCP items: RSA uses direct APIs (Anthropic, GitHub CLI) — no MCP servers

SECTION 4 — SKILL RUNTIME GATE
[N/A] Customer-facing skill config not applicable; event-trigger pattern declared instead

SECTION 0 — CONSTITUTIONAL DNA
[✅] Section 0 present with Instinct 1/2/3 agent-specific parameters

OVERALL GATE STATUS: PASS
```

---

## EA Authorization

This review authorizes the spec to advance from DRAFT to **DRAFT (EA reviewed)**. Implementation
sprint requires Founder ratification to begin.

**Recommended Founder action:** Review §0 (DNA inheritance) and §5 (Decision Space) specifically —
these define what the agent can do autonomously. The Level 1 autonomous code commits and Level 2
autonomous spec PRs are the most significant authority grants.

---
*Enterprise Architect review — 2026-07-24 · See spec v1.2 for all changes*

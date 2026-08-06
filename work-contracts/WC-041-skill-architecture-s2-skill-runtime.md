# Work Contract 041 — Skill Architecture Sprint 2: Skill Runtime in Professional Runtime

**Office:** Platform IT Expert (INST-010)  
**Sprint:** WC-041  
**Backlog Item:** IB-011 — Skill Architecture (pending Founder ratification)  
**Sprint Track:** Track DIFFERENTIAL — extends existing PAAS session open activity  
**Gate:** G5 CLEAR  
**Reviewer:** Enterprise Architect (INST-004)  
**Constitutional Basis:** C-031 (ADR-043 — satisfied), C-036 (Skills are constitutional units — Skill Runtime is the execution-time enforcer), C-041 (tool authorization derived from skill assignment at session open)  
**Authorization:** Founder must authorize — *"Authorize WC-041"*

**Depends on:** WC-040 DONE (Skill Catalog API must exist for runtime to resolve manifests)  
**Blocks:** DMA agent sprint — no DMA implementation until Skill Runtime is functional  
**Service scope:** Professional Runtime (Python FastAPI, `src/professional-runtime/`)

---

## Sprint Goal

The PAAS session open activity in Professional Runtime is extended to resolve skill manifests from the BP Skill Catalog at session-open time. The session context gains `authorized_tools`, `crystallizers`, and `autonomy_dial` derived from the agent's assigned skills. The Intent Crystallizer executes for skills that require it before any tool calls in the session proceed.

After this sprint, an agent with `skills: [content_publish@1.0.0]` opens a PAAS session that:
- Has `authorized_tools = [meta.post_content, meta.post_story, youtube.upload_video, ...]` — derived from the skill definition
- Requires Intent Crystallization (locked Campaign Brief) before any publish tool call is permitted
- Blocks any tool call not in `authorized_tools` (constitutionally governed by C-041)

---

## Tasks

| task_id | scope | model_hint | status |
|---|---|---|---|
| WC041-01 | `src/professional-runtime/skill_resolver.py` — `SkillResolver` class. `async resolve_skills(contract_id: str, skills: list[SkillAssignment]) → SessionSkillContext`. For each skill assignment: calls `GET /api/v1/skills/{skill_id}/{version}` on BP; parses skill definition JSONB; builds `SessionSkillContext` containing: `authorized_tools: set[str]` (union of all skills' tool sets), `crystallizer_configs: dict[skill_id, CrystallizerConfig]`, `autonomy_levels: dict[skill_id, str]`, `required_providers: set[str]`. On unknown/unavailable skill: raise `SkillResolutionError(skill_id, version)` — session fails to open. | `reasoning` | pending |
| WC041-02 | `src/professional-runtime/session_executor.py` (or PAAS session activity, whichever owns session init) — call `SkillResolver.resolve_skills()` at session open. Attach resolved `SessionSkillContext` to session state. Any tool call from the LLM during the session is validated against `session_ctx.authorized_tools` BEFORE calling CTG — if not in authorized set: raise `C041ToolAuthorizationError`, session paused, CE evidence record written (DENIED). | `reasoning` | pending |
| WC041-03 | `src/professional-runtime/intent_crystallizer.py` — `IntentCrystallizer` class. `async crystallize(skill_id: str, config: CrystallizerConfig, session_ctx: SessionSkillContext) → LockedArtifact`. Builds prompt from `config.prompt_template`, sends to AIR (via CTG if external), returns structured JSON per `config.locked_artifact_schema`. Presents artifact to customer via approval-gate mechanism (existing PR approval flow). On customer approval: stores `LockedArtifact` in session state; writes CE evidence record `action_type=APPROVAL`. Any tool call in `config.tool_set` without a corresponding `LockedArtifact` in session state → `CrystallizerRequiredError` → MCPToolError(CONSTITUTIONAL_BLOCKED). | `reasoning` | pending |
| WC041-04 | PAAS session state extended — `session_state.py` or equivalent: add `locked_artifacts: dict[skill_id, LockedArtifact]`, `crystallization_complete: dict[skill_id, bool]`. These are persisted in Temporal workflow state so crystallization survives session restart. | `auto` | pending |
| WC041-05 | Tests — `tests/professional-runtime/test_skill_runtime.py`: CCT-SKILL-CP-01 (session with `content_publish@1.0.0` — crystallizer called before first publish tool; mock BP skill API + mock crystallizer approval flow); CCT-SKILL-CP-02 (tool call in skill's tool set without locked artifact → MCPToolError CONSTITUTIONAL_BLOCKED); CCT-SKILL-CP-03 (CE.ValidateAction called for every tool call with tool_name matching skill's declared tools — mock CE, assert called with correct tool_name + dcm_category from skill definition); CCT-SKILL-UNKNOWN-01 (session open with unknown skill → SkillResolutionError → session fails to open, no tool calls permitted). | `auto` | pending |

---

## Required Inputs

| Input | File |
|---|---|
| ADR-043 Skill Architecture spec | `adr/ADR-043-skill-architecture-standard.md` |
| content_publish@1.0.0 skill definition | `knowledge/skills/content_publish_v1.0.0.yaml` (from WC-040) |
| Existing PAAS session code | `src/professional-runtime/` |
| Existing PR test setup | `tests/professional-runtime/conftest.py` |
| CTG library (for crystallizer LLM call routing) | `src/trust-layer/ctg/` (from WC-039) |

---

## Definition of Done

- [ ] `SkillResolver` resolves skill manifests from BP Skill Catalog at session open
- [ ] `SessionSkillContext.authorized_tools` gates all tool calls before CTG (C-041 enforcement)
- [ ] `IntentCrystallizer` executes for skills with `intent_crystallizer.enabled = true`
- [ ] `LockedArtifact` persisted in Temporal session state — survives restart
- [ ] CCT-SKILL-CP-01: crystallizer called before first publish tool in `content_publish` skill
- [ ] CCT-SKILL-CP-02: tool call without locked artifact → MCPToolError CONSTITUTIONAL_BLOCKED
- [ ] CCT-SKILL-CP-03: CE.ValidateAction called with correct dcm_category for every tool call
- [ ] CCT-SKILL-UNKNOWN-01: session fails to open on unresolvable skill
- [ ] All existing PR tests (CCT-PR-01) still passing
- [ ] `ruff` clean, `pytest` clean
- [ ] VERSION bumped, CHANGELOG, PROJECT_STATE updated

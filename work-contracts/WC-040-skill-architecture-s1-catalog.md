# Work Contract 040 — Skill Architecture Sprint 1: Skill Catalog + Employment Contract Amendment

**Office:** Platform IT Expert (INST-010)  
**Sprint:** WC-040  
**Backlog Item:** IB-011 — Skill Architecture (pending Founder ratification)  
**Sprint Track:** Track GREENFIELD (new BP table + API) + Track DIFFERENTIAL (Employment Contract extension)  
**Gate:** G5 CLEAR  
**Reviewer:** Enterprise Architect (INST-004)  
**Constitutional Basis:** C-031 (ADR-043 required — satisfied), C-036 (Skills are constitutional units), C-041 (tool authorization derived from skill assignment)  
**Authorization:** Founder must authorize — *"Authorize WC-040"*

**Depends on:** ADR-043 merged (✅ `b934481`)  
**Blocks:** WC-041 — Skill Runtime needs Skill Catalog API before it can resolve manifests  
**Parallel with:** WC-037/038/039 — trust layer and skill catalog are independent tracks  
**Service scope:** Business Platform (.NET 9)

---

## Sprint Goal

Business Platform gains a Skill Catalog (Postgres table + REST API) and the Employment Contract JSON schema is extended with a `skills[]` array. The hiring flow validates that all declared skills exist at the pinned version in the catalog before a contract is created.

After this sprint, the first skill definition file `content_publish@1.0.0` is published to the catalog and available for resolution by WC-041's Skill Runtime.

---

## Tasks

| task_id | scope | model_hint | status |
|---|---|---|---|
| WC040-01 | BP migration — `skills` table per ADR-043 §2 schema. Fields: `id`, `skill_id`, `version` (semver), `display_name`, `definition` (JSONB — full skill YAML as JSON), `cct_suite` (TEXT[]), `status` (DRAFT/PUBLISHED/DEPRECATED), `published_at`, `deprecated_at`, `created_at`. Unique constraint on `(skill_id, version)`. | `reasoning` | pending |
| WC040-02 | BP API — `GET /api/v1/skills` (list published skills — public, customer JWT), `GET /api/v1/skills/{skill_id}` (latest published version), `GET /api/v1/skills/{skill_id}/{version}` (pinned version — used by Skill Runtime), `POST /api/v1/skills` (publish new skill/version — Founder role only). | `auto` | pending |
| WC040-03 | Employment Contract JSON schema extended with `skills[]` array per ADR-043 §4. Each entry: `{ skill_id, version, assigned_at }`. BP `EmployAgent` endpoint validates every declared skill exists at pinned version via Skill Catalog lookup — if not found: 422 `SKILL_NOT_FOUND`. BP `AmendContract` endpoint handles adding/removing skills (requires CE evidence record for each amendment). | `reasoning` | pending |
| WC040-04 | Seed data — `content_publish` skill definition file at `knowledge/skills/content_publish_v1.0.0.yaml`. Fields per ADR-043 §1 standard: `skill_id`, `version`, `display_name`, `tools[]`, `required_providers[]`, `default_dcm_category`, `intent_crystallizer` config, `default_autonomy_level`, `cct_suite[]`, `billing_event`. Publish to catalog via migration seed (status=PUBLISHED). | `auto` | pending |
| WC040-05 | Skill amendment audit — when `AmendContract` adds or removes a skill, BP calls `CE.ValidateAction` with `action_type = SKILL_AMENDMENT`, writes evidence record. Customer's Employment Contract `skills[]` is updated only after CE returns ALLOW. | `reasoning` | pending |
| WC040-06 | Tests — `tests/business-platform.Tests/Skills/CCT_SKILL_CAT_01_UnknownSkillRejectedTests.cs`: attempt to hire agent with `skills: [{ skill_id: "nonexistent", version: "1.0.0" }]` → 422 SKILL_NOT_FOUND. `CCT_SKILL_VER_01_VersionPinTests.cs`: publish skill@1.0.0 and @2.0.0; hire with @1.0.0 pinned; resolve via API → returns @1.0.0 definition, not @2.0.0. `CCT_SKILL_AMEND_01_AuditTests.cs`: add skill via AmendContract → CE evidence record written with action_type=SKILL_AMENDMENT. | `auto` | pending |

---

## Required Inputs

| Input | File |
|---|---|
| ADR-043 Skill Architecture spec | `adr/ADR-043-skill-architecture-standard.md` |
| Existing BP Employment Contract model | `src/business-platform/` (existing contracts for reference) |
| ADR-035 Agent Contract Standard | `adr/ADR-035-platform-agent-contract-standard.md` |

---

## Definition of Done

- [ ] `skills` table migrated in BP with `content_publish@1.0.0` seeded (status=PUBLISHED)
- [ ] Skill catalog API functional: GET list, GET pinned version, POST (Founder-gated)
- [ ] `EmployAgent` rejects unknown/unpublished skills with 422 SKILL_NOT_FOUND
- [ ] `AmendContract` writes CE evidence record for every skill add/remove
- [ ] `knowledge/skills/content_publish_v1.0.0.yaml` committed — first platform skill definition
- [ ] CCT-SKILL-CAT-01, CCT-SKILL-VER-01, CCT-SKILL-AMEND-01 pass
- [ ] All existing BP tests passing (no regression — hire/trial/amendment flows unbroken)
- [ ] `dotnet build` clean on BP
- [ ] VERSION bumped, CHANGELOG, PROJECT_STATE updated

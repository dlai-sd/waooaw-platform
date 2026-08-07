# Enterprise Architect Review — R-023
## Sprint: WC-040 — Skill Architecture Sprint 1 (Skill Catalog)
**Reviewer Office:** Enterprise Architect (INST-004)  
**Review Date:** 2025-07-15  
**Constitutional Basis:** ADR-043, ADR-042, C-023, C-036, C-066, C-076  
**Verdict:** APPROVED WITH REQUIRED FIXES (all fixes applied before commit)

---

## 1. Deliverables Reviewed

| Deliverable | File | Status |
|---|---|---|
| Skill Catalog SQL migration | `infrastructure/postgres/init/17-skill-catalog.sql` | Reviewed |
| EF Core DbContext | `src/business-platform/Infrastructure/SkillCatalogDbContext.cs` | Reviewed |
| Skill Catalog API | `src/business-platform/Controllers/SkillsController.cs` | Reviewed |
| Employment Manager amendments | `src/business-platform/Controllers/CustomersController.cs` | Reviewed |
| Skill definition YAML | `knowledge/skills/content_publish_v1.0.0.yaml` | Reviewed |
| CCT-SKILL-CAT-01 | `tests/business-platform.Tests/Skills/CCT_SKILL_CAT_01_*` | Reviewed |
| CCT-SKILL-VER-01 | `tests/business-platform.Tests/Skills/CCT_SKILL_VER_01_*` | Reviewed |
| CCT-SKILL-AMEND-01 | `tests/business-platform.Tests/Skills/CCT_SKILL_AMEND_01_*` | Reviewed |
| PSE router CTG fail-fast | `src/ai-runtime/pse/router.py` | Reviewed |

---

## 2. Gap Register

### GAP-001 — CRITICAL: SQL grants to non-existent roles `bp_ro` / `bp_app`
**File:** `17-skill-catalog.sql`  
**Lines:** 37–38  
**Evidence:**  
```sql
-- DEFECT: bp_ro and bp_app do not exist
GRANT SELECT ON business.skills TO bp_ro;
GRANT SELECT, INSERT, UPDATE ON business.skills TO bp_app;
```
`02-users-and-permissions.sh` defines `runtime_app` (SELECT) and `business_app` (full CRUD). PostgreSQL would abort the init script with `ERROR: role "bp_ro" does not exist`, preventing DB initialization entirely.

**Fix applied:**
```sql
GRANT SELECT ON business.skills TO runtime_app;
GRANT SELECT, INSERT, UPDATE ON business.skills TO business_app;
```
**Constitutional basis:** ADR-043 §2 — Skill Catalog is a business schema table; `business_app` is the schema owner.

---

### GAP-002 — CRITICAL: `GetPinnedSkillAsync` rejects DEPRECATED skills — breaks existing agent sessions
**File:** `SkillsController.cs`  
**Endpoint:** `GET /api/v1/skills/{skillId}/{version}`  
**Evidence:**  
```csharp
// DEFECT: DEPRECATED skills return 404 — breaks ADR-043 §5
s => s.SkillId == skillId && s.Version == version && s.Status == "PUBLISHED"
```
ADR-043 §5 states: "A deprecated skill's existing contract assignments remain valid." The Professional Runtime calls this endpoint at session open to load the skill definition. If the skill has been deprecated, the PR receives 404 and cannot start the session, causing an agent availability outage for any customer whose contract references the deprecated version.

**Fix applied:** Query extended to include `DEPRECATED` status on the pinned-version endpoint only. The `GetLatestSkillAsync` (hiring UX) remains PUBLISHED-only so new hires are not directed to deprecated versions.
```csharp
s => s.SkillId == skillId && s.Version == version
  && (s.Status == "PUBLISHED" || s.Status == "DEPRECATED")
```
**Test added:** `CCT_SKILL_VER_01` Test 5 — `GetPinnedVersion_Deprecated_Returns200`  
**Constitutional basis:** ADR-043 §5, C-036

---

### GAP-003 — SIGNIFICANT: `ToResponse` swallows `JsonException` silently
**File:** `SkillsController.cs`  
**Evidence:**  
```csharp
// DEFECT: bare catch hides data corruption silently
catch
{
    def = JsonDocument.Parse("{}").RootElement;
}
```
A corrupted `Definition` column (invalid JSON) would silently return `{}` to callers — including the Professional Runtime loading a skill at session open — with no log trail. This violates C-059 (constitutional traceability) and hides data integrity violations.

**Fix applied:** Changed to `catch (JsonException ex)` with `_logger.LogError`. Method changed from `static` to instance to access `_logger`.
```csharp
catch (JsonException ex)
{
    _logger.LogError(ex,
        "SkillEntry Definition is not valid JSON — returning empty object. SkillId={SkillId} Version={Version}",
        s.SkillId, s.Version);
    def = JsonDocument.Parse("{}").RootElement;
}
```
**Constitutional basis:** C-059

---

### GAP-004 — SIGNIFICANT: `SkillAssignment` missing `AssignedAt` per ADR-043 §4
**File:** `CustomersController.cs`  
**Evidence:**  
```csharp
// DEFECT: ADR-043 §4 specifies { skill_id, version, assigned_at }
public sealed record SkillAssignment(string SkillId, string Version);
```
ADR-043 §4 defines the Employment Contract skills[] array schema as `{ skill_id, version, assigned_at }`. Without `assigned_at`, the Skill Runtime has no timestamped audit record of when each skill was assigned — required for compliance and billing event tracing.

**Fix applied:**
```csharp
public sealed record SkillAssignment(
    string SkillId,
    string Version,
    DateTimeOffset AssignedAt = default);
```
`HireAgentAsync` response now populates `AssignedAt = proRataBillingStartDate` for each returned skill assignment. The `= default` default value maintains backward compatibility for existing test callers that pass only 2 positional arguments.  
**Constitutional basis:** ADR-043 §4

---

## 3. Items Verified (No Defect)

| Item | Finding |
|---|---|
| `SkillCatalogDbContext` EF model | Correct. `HasColumnType("jsonb")` and `HasColumnType("text[]")` match SQL DDL. UNIQUE index on `(SkillId, Version)` matches SQL constraint. |
| `HireAgentAsync` C-036 pre-condition gate | Correct. Skills[] validated against catalog BEFORE CE call. This is config pre-validation (read-only), not a state change — C-023 not violated. |
| `AmendContractAsync` C-023 compliance | Correct. CE.ValidateAction called before any state mutation. Response includes `ce_evidence_basis`. |
| `ActionParameters` JSON in CE calls | Correct. `SkillId` and `Version` included in SKILL_AMENDMENT parameters for CE evidence record. |
| CCT-SKILL-CAT-01 (3 tests) | Pass. Unknown skill_id → 422, wrong version → 422, no skills[] → reaches CE (503). |
| CCT-SKILL-VER-01 (4 tests + 1 new) | Pass. Version pinning deterministic. Deprecated version resolvable (new Test 5). |
| CCT-SKILL-AMEND-01 (4 tests) | Pass. ADD known skill reaches CE (503 proxy). ADD unknown → 422 before CE. REMOVE → CE (503). |
| SQL RLS policy (SELECT PUBLISHED) | Correct for a platform catalog (no tenant_id column). `business_app` is schema owner → bypasses RLS for writes by default. |
| `content_publish_v1.0.0.yaml` | Conforms to ADR-043 §1 schema: skill_id, version, tools[], required_providers[], cct_suite[]. |
| PSE router CTG fail-fast (GAP-002) | Correct. `IMPLEMENTATION` phase check prevents ungoverned LLM dispatch (C-041). |
| C-066 Founder role check | Correct. `User.FindFirst("role") ?? User.FindFirst("roles")` handles both claim shapes. |

---

## 4. Architectural Notes (No Fix Required)

### AN-001: `ContractId = "platform"` in SKILL_PUBLISH CE call
`PublishSkillAsync` passes `ContractId = "platform"` to CE.ValidateAction. There is no Employment Contract with id "platform" — this is a platform-level administrative action. CE will write an evidence record linked to this pseudo-contract. This is an accepted pattern for platform management operations but should be formalized as a named constant and documented in ADR-043 as the "Platform Catalog Management Contract."

**Recommendation:** In a future sprint, define `urn:waooaw:platform:skill-catalog` as the canonical platform contract ID for CE evidence records, and add it to ADR-043 §6.

### AN-002: Legacy `SkillId` field in `HireAgentRequest` is unvalidated
`HireAgentRequest` has both a legacy `SkillId` string (pre-WC-040) and the new `Skills[]` array. The legacy field is not validated against the Skill Catalog. While existing callers depend on it, this creates a partial C-036 guarantee: a caller can hire an agent with an unknown `SkillId` if they do not also populate `Skills[]`.

**Recommendation:** In a future sprint, migrate all callers to `Skills[]` and deprecate the legacy `SkillId` field.

---

## 5. Test Coverage

**Before fixes:** 44 tests — BP 44/44  
**After fixes:** 45 tests — BP 45/45  
**New test:** `CCT_SKILL_VER_01` Test 5 (`GetPinnedVersion_Deprecated_Returns200`)  
**C-076 (≥90% coverage):** MAINTAINED

---

## 6. Review Decision

**APPROVED.** All critical and significant gaps have been identified, fixed, and verified.  
All 45 BP tests pass. No regressions introduced.

Fixes applied in this review session are included in the same commit as the review file.

**Reviewer:** Enterprise Architect (INST-004)  
**Reviewed sprint output from:** Platform IT Expert (INST-010) / WC-040

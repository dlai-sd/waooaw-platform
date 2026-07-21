# Work Contract 011 — IB-009 Implementation Sprint 011: Infrastructure Foundation

**Office:** WAOOAW AI Agent — Platform IT Expert (Office 10)
**Sprint:** 011
**Backlog Item:** IB-009 — Foundation Implementation (Gate G5)
**Sprint Track:** Track 1 — Infrastructure (PMO Program Plan §2.1 Track 1)
**Gate:** G5 — First working code
**Reviewer:** WAOOAW AI Agent — Platform IT Expert (PR Review hat, per PMO review model)
**EA Pre-check:** Enterprise Architect review of each PR in same session before push

**Constitutional Basis:**
- C-059 (Implementation Traceability — every src/ file must carry `# Implements:` header)
- C-065 (SDLC Separation of Duties — Author ≠ Reviewer)
- C-066 (Authorization Tiers — Tier 2: Sujay + IB authorized)
- C-067 (Blue-Green + Cost Ceiling — ₹10k/env/month, dev environment)
- C-073 (@constitutional annotations on all constitutional functions)

**Authorization:** IB-009 Status = AUTHORIZED. Founder authorization required per session before this WC may be executed. This WC is the work plan — not the execution authorization. Confirm with Founder: "Do you authorize IB-009 Sprint 011 implementation for this session?"

---

## Sprint Goal

Provision the complete local development environment and Azure dev Container Apps environment so that:
1. `docker compose up` starts all 9 services (CE, BP, PR, AIR, Web, PostgreSQL, Keycloak, Temporal, Ollama)
2. PostgreSQL migrations 01–09 apply cleanly in dev
3. Keycloak dev realm is importable
4. All 9 GitHub Actions secrets are documented and populated
5. `./scripts/setup.sh` completes without error

This sprint produces NO business logic. It proves the infrastructure is operational. That is its entire scope.

---

## Required Inputs (all must exist before execution begins)

| Input | Location | Status |
|---|---|---|
| docker-compose.yml | `/workspaces/waooaw-platform/docker-compose.yml` | ✅ EXISTS |
| .env.example | `/workspaces/waooaw-platform/.env.example` | ✅ EXISTS |
| DB migration scripts (01–09) | `infrastructure/postgres/init/` | ✅ EXISTS |
| Keycloak realm config | `infrastructure/keycloak/` | ✅ EXISTS |
| Terraform modules | `infrastructure/terraform/` | ✅ EXISTS |
| CI/CD pipelines | `.github/workflows/` | ✅ EXISTS |
| Component specs | `architecture/reference/components/` | ✅ EXISTS |
| ADR-INDEX | `adr/ADR-INDEX.md` | ✅ EXISTS |
| Azure Service Principal (Founder action) | GitHub Secrets | ❌ PENDING — blocks Terraform apply |
| FA-021: GCP Vertex AI SA key | Azure Key Vault | ❌ PENDING — blocks AI Runtime real inference |

**If Azure SP is not yet provided:** Execute tasks WC011-01 through WC011-05 (local docker-compose only). Mark WC011-06 (Terraform apply) as BLOCKED. Record blocker in `blockers/` if needed.

---

## Tasks

### WC011-01 — Validate and fix docker-compose.yml

**Scope:** Run `docker compose config` locally. Resolve any YAML errors, missing service definitions, or health-check gaps identified in IB-008 implementation notes.
**Constitutional check:** All 9 services must be present. CE must not be externally exposed (internal gRPC only per C-004).
**Output:** `docker-compose.yml` passing `docker compose config` with zero warnings.
**Branch:** `ib/009/infra-foundation`
**PR title:** `feat(infra): validate and fix docker-compose for 9-service stack`
**C-059 header required on:** any new script files created in this task
**CCT gate:** None (infrastructure validation — no CCT for YAML validation)

---

### WC011-02 — Validate DB migration scripts 01–09

**Scope:** Run all 9 SQL migration scripts against a local PostgreSQL container. Verify:
- Schemas created: `constitutional`, `business`, `professional`, `institutional`
- RLS policies applied (C-027: tenant isolation)
- `constitutional.audit_records` has NO UPDATE/DELETE triggers (C-007: append-only)
- `09-mcp-registry.sql` applies cleanly (C-074: On-the-Fly MCP Provisioning)
**Output:** Migration run log. Any SQL errors fixed. Comment in each file: `-- Validated: WC-011 Sprint 011`
**Branch:** `ib/009/infra-foundation` (same branch as WC011-01)
**C-059 note:** SQL files are infrastructure, not src/ — no `# Implements:` header required, but ADR reference comment required in each file header if not already present.

---

### WC011-03 — Validate Keycloak realm import

**Scope:** Start Keycloak container and import `infrastructure/keycloak/waooaw-realm.json`. Verify:
- Realm `waooaw` created
- Google IDP stub configured (redirects to Google OAuth — real client ID in Key Vault)
- Dev test user `test@waooaw.ai` created with `customer` role
- Steward users (Yogesh/Sujay/Ojal email stubs) created with `steward` role
**Output:** `infrastructure/keycloak/IMPORT-VALIDATION.md` with import results and any fixes applied.
**Branch:** `ib/009/infra-foundation`

---

### WC011-04 — Create src/ directory scaffold

**Scope:** Create the constitutional directory structure for all 4 services. No logic. No compilation. Structure only.

```
src/
  constitutional-engine/     ← .NET 9 / gRPC
    ConstitutionalEngine.sln
    ConstitutionalEngine.csproj   (placeholder — dependencies only)
    README.md
  business-platform/         ← .NET 9 / REST
    BusinessPlatform.sln
    BusinessPlatform.csproj
    README.md
  professional-runtime/      ← Python 3.12 / FastAPI
    pyproject.toml
    README.md
  ai-runtime/                ← Python 3.12 / FastAPI
    pyproject.toml
    README.md
  web/                       ← Next.js 14 (web/ already exists at root — link only)
    (skip — web/WAOOAWHome.html already at root web/ folder)
  constitutional.py          ← already exists — verify C-059 header present
```

**Every README.md in src/ must contain:**
```
# Implements: architecture/reference/components/{service-name}.md
# Constitutional basis: C-059 (Implementation Traceability)
```

**Branch:** `ib/009/infra-foundation`
**PR title:** `feat(infra): scaffold src/ directory structure per C-059`

---

### WC011-05 — Verify setup.sh and get-dev-token.sh

**Scope:** Run `./scripts/setup.sh` locally. Fix any script errors. Verify `./scripts/get-dev-token.sh` produces a JWT with correct `tenant_id` claim. Document any missing `.env` values in `.env.example`.
**Output:** `scripts/SETUP-VALIDATION.md` with setup run log and env variable status.
**Branch:** `ib/009/infra-foundation`

---

### WC011-06 — Terraform apply dev environment [BLOCKED pending Azure SP]

**Scope:** When Founder provides Azure Service Principal:
- `terraform init` + `terraform plan` for `environments/dev/`
- Resolve any plan errors against existing modules
- `terraform apply` (Founder must confirm before apply)
- Verify all 9 Container Apps are created in Azure
**Constitutional gate:** C-067 cost ceiling check — dev environment must stay within ₹10k/month. Document estimated monthly cost in PR.
**Branch:** `ib/009/terraform-dev` (separate branch — Founder must authorize apply explicitly)
**PR title:** `feat(infra): terraform apply dev environment — all 9 Container Apps`

---

### WC011-07 — GitHub Actions secrets documentation

**Scope:** Create `infrastructure/GITHUB-SECRETS.md` documenting every secret required by `.github/workflows/`. For each secret:
- Name
- Where to obtain it (Founder action reference if applicable)
- Which pipeline uses it
- Status: POPULATED / PENDING (FA-XXX)

This is a governance document, not a secret store. No actual secret values in the file.
**Branch:** `ib/009/infra-foundation`

---

## PR Review Protocol (C-065 enforcement)

Each PR in this sprint follows this cycle:

```
1. Implementation agent opens PR on branch ib/009/infra-foundation
2. CI runs automatically: code-quality.yaml (lint, SAST, traceability scan)
3. If CI fails → fix in same session before proceeding
4. EA pre-check (same Copilot session, different "hat"):
   - Verify C-059 headers on all src/ files
   - Verify no business logic in infrastructure scaffold
   - Verify docker-compose CE service is internal-only (no port binding on CE gRPC)
5. Platform IT Expert PR review (PR Review hat):
   - Engineering standards compliance (engineering-standards.md)
   - CCT coverage for any new code (N/A for pure infrastructure)
   - Security: no secrets in code, no debug credentials
   - CODEOWNERS compliance (@dlai-sd required)
6. If EA pre-check + PR review both pass → merge to main
7. Update PROJECT_STATE.md with completed milestone
```

---

## Definition of Done

- [ ] `docker compose up` starts all 9 services with zero errors
- [ ] All 9 DB migrations apply cleanly in local PostgreSQL
- [ ] Keycloak realm imports without errors
- [ ] `src/` scaffold exists with C-059 README headers in all 4 service directories
- [ ] `./scripts/setup.sh` completes without error (with real env values)
- [ ] `infrastructure/GITHUB-SECRETS.md` documents all required secrets and their status
- [ ] All PRs have passed CI and PR review
- [ ] `constitution/PROJECT_STATE.md` updated with Sprint 011 completion

---

## What This Sprint Does NOT Produce

- No business logic (no `/health` endpoint code yet — that is Sprint 012)
- No Constitutional Engine evaluators
- No API endpoints
- No test code (CCT scaffolds come in Sprint 012)
- No Terraform apply (unless Founder provides Azure SP and explicitly authorizes)

The next sprint (WC-012) builds the Constitutional Engine skeleton with the first CCT.

---

## Sprint 012 Preview (context only — not authorized yet)

**Sprint 012:** Constitutional Engine skeleton
- `.NET 9` gRPC service with `/health` endpoint
- `RecordEvidence` endpoint writing to `constitutional.audit_records`
- `ValidateAction` stub returning AUTHORIZED
- `TriggerEmergencyStop` webhook to Professional Runtime stub
- CCT-EF-01 (Evidence First) — first CCT passing in dev
- CCT-HO-01 (Emergency Stop ≤250ms) — constitutional floor verified

Sprint 012 requires Sprint 011 complete (services must start before skeleton can be built).

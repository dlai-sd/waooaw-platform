# PROJECT_STATE.md

**Last Updated:** 2026-07-07

**Session Reference:** v0.5.0 Baseline + Sprint 1 Simulation

## Current Status

| Item | Status |
|---|---|
| Architecture phase | ✅ COMPLETE |
| Phase 2 Readiness (IB-017) | ✅ COMPLETE |
| GitHub Operating Model | ✅ COMPLETE — v0.5.0 |
| IB-009 Foundation Implementation | AUTHORIZED — next sprint |
| Sprint 1 simulation | See below |

---

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| Issue templates (.github/ISSUE_TEMPLATE/) | ✓ DONE |
| CODEOWNERS | ✓ DONE |
| PR template | ✓ DONE |
| PM report workflow | ✓ DONE |
| Project automation workflow | ✓ DONE |
| copilot-instructions.md updated | ✓ DONE |
| ORGANIZATION.md Office 12 added | ✓ DONE |
| README operating commands | ✓ DONE |
| Commit + push | ✓ DONE |

---

## GitHub Operating Model — Implemented

This session delivered the full GitHub-grounded autonomous agent operating model.

**Artifacts produced:**

| Artifact | Purpose |
|---|---|
| `.github/ISSUE_TEMPLATE/ib-implementation.yml` | Structured IB issue form: IB ID, office, sprint, gate, components, domain, success criteria |
| `.github/ISSUE_TEMPLATE/ib-architecture.yml` | Architecture IB form |
| `.github/ISSUE_TEMPLATE/constitutional-blocker.yml` | CB form with blocker type, resolution path |
| `.github/ISSUE_TEMPLATE/sprint-plan-approval.yml` | Sprint plan approval with `/approved` activation pattern |
| `.github/ISSUE_TEMPLATE/config.yml` | Template chooser with backlog link |
| `.github/pull_request_template.md` | PR body: IB reference, constitutional basis, CCT coverage, spec compliance checklist |
| `.github/CODEOWNERS` | Founder (@dlai-sd) as required reviewer on all paths |
| `.github/workflows/pm-report.yaml` | Scheduled + event-driven delivery matrix report (Office 12) |
| `.github/workflows/project-automation.yaml` | Auto-label on agent assignment, blocker propagation, sprint activation on `/approved` |
| `.github/copilot-instructions.md` | Updated with GitHub issue mode, PR review mode, PM mode, branch/commit conventions |
| `constitution/ORGANIZATION.md` | Office 12 — Platform Delivery Tracker added |
| `README.md` | Operating commands section: dev env, sprint operations, status, CI/CD, label reference |

**Five operating patterns (bare minimum invocations):**
1. Sprint start: `@copilot You are Product Owner. Produce Sprint Plan for Sprint N.`
2. Sprint execution: assign GitHub Issue to `@copilot`
3. PR review: `@copilot review this PR as the Enterprise Architect`
4. Status report: `@copilot You are Platform Delivery Tracker. Status report.`
5. Sprint approval: comment `/approved` on the sprint plan issue

---

**Previous Session Reference:** Coding Agent Readiness Fixes + v0.4.0 Baseline

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| Postgres init .sh fix + TEMPORAL_DB_PASSWORD | ✓ DONE |
| buf.yaml + Dockerfile templates | ✓ DONE |
| docker-compose CE healthcheck fix | ✓ DONE |
| EF Core migration bootstrap + SET LOCAL docs | ✓ DONE |
| Keycloak dev JWT + .env.example | ✓ DONE |
| README version + v0.4.0 tag + commit | ✓ DONE |

---

## v0.4.0 Baseline Summary

Version 0.4.0 marks the completion of the full Architecture + Phase 2 Readiness phase.
The coding agent can begin IB-009 with all 7 identified confidence gaps resolved.

**Seven fixes applied this session:**
1. Postgres init: `.sql` → `.sh` (bash script, proper env var interpolation); `TEMPORAL_DB_PASSWORD` added to `.env.example`
2. Proto toolchain: `buf.yaml` + `buf.gen.yaml` in `architecture/reference/proto/`
3. Dockerfile templates: `.NET 9`, `Python 3.12`, `Next.js` in `architecture/reference/dockerfiles/`
4. docker-compose CE healthcheck: `grpc_health_probe` → `nc -z localhost 5002` (dev); web service healthcheck added
5. EF Core migration bootstrap: empty initial migration technique documented in engineering-standards.md §9
6. `SET LOCAL` interceptor: `TenantDbCommandInterceptor` pseudocode in CE + BP component specs; JWT middleware pipeline order specified
7. Dev JWT: `waooaw-dev-client` added to Keycloak realm; dev user seeded; `scripts/get-dev-token.sh` created; `DEV_TEST_USER/PASSWORD` in `.env.example`

---

**Previous Session Reference:** IB-017 Phase 2 Readiness Sprint

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| IB-017 added to backlog | ✓ DONE |
| WC-010 created (PA + EA joint sprint) | ✓ DONE |
| Engineering Quality Standards (IB-011) | ✓ DONE |
| CCT Framework specification | ✓ DONE |
| CI/CD workflows (.github/workflows/) | ✓ DONE |
| Infrastructure postgres init SQL | ✓ DONE |
| Keycloak realm JSON | ✓ DONE |
| Temporal dynamic config | ✓ DONE |
| Bootstrap script + directory structure | ✓ DONE |
| Governance close + commit | IN PROGRESS |

---

**Previous Session Reference:** FR-001 (CS Agent Path A) + IB-014/015/016 design frames

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| FR-001 recorded (Path A decision) | ✓ DONE |
| IB-014 corrected + added to backlog | ✓ DONE |
| IB-015 Path A added to backlog | ✓ DONE |
| IB-016 corrected + added to backlog | ✓ DONE |
| Governance close + commit | ✓ DONE |

---

## Current State Summary

| Item | Status |
|---|---|
| Architecture Phase (G1–G4) | ✓ COMPLETE |
| Gate G5 | ✓ CLEAR — all prerequisites met |
| Phase 2 Readiness (IB-017) | ✓ COMPLETE |
| IB-009 Foundation Implementation | **READY TO BEGIN** |

---

## Phase 2 Readiness — What Was Produced (IB-017)

**Engineering governance (IB-011 — EA):**
- `architecture/reference/engineering-standards.md` — Runtime Professional's Decision Space specification: coding standards, coverage targets, security gates, CCT mandate, OTel metric names
- `tests/constitutional/README.md` — CCT framework: 12 CCTs defined (EF-01/02, HO-01/02, AL-01/02, MT-01/02, PAAS-01, RU-01), failure procedure, template

**CI/CD pipeline (PA):**
- `.github/workflows/ci.yaml` — PR pipeline: build all 5 images, unit tests (.NET + Python + TypeScript), OpenAPI/proto lint, SAST (CodeQL), Trivy image scan, secret detection
- `.github/workflows/promote.yaml` — Merge pipeline: dev deploy, integration tests, CCTs (mandatory gate), promote to :qa on CCT pass

**Infrastructure initialization (PA):**
- `infrastructure/postgres/init/01-schemas.sql` — three constitutional schema zones
- `infrastructure/postgres/init/02-users-and-permissions.sql` — constitutional_app/business_app/runtime_app/temporal with precise grants per ledger-design.md
- `infrastructure/postgres/init/03-enums-and-tables.sql` — all enums and tables including action_instance_id, paas_sessions (GAP-004), creative_standard_embeddings (GAP-005), professional_templates (IB-015)
- `infrastructure/postgres/init/04-rls-policies.sql` — tenant isolation RLS on all tenant-scoped tables
- `infrastructure/postgres/init/05-append-only-rules.sql` — PostgreSQL RULE enforcement (belt-and-suspenders on C-007)
- `infrastructure/keycloak/waooaw-realm.json` — realm with tenant_id claim mapper, waooaw-web + waooaw-platform clients, Google IDP, 15-min token expiry
- `infrastructure/temporal/dynamicconfig.yaml` — Temporal dev configuration with PAAS-suitable 24h workflow timeout

**Dev bootstrap (PA):**
- `scripts/setup.sh` — one-command: .env → validate dirs → `docker compose up` → health checks → smoke tests
- `tests/unit/`, `tests/integration/`, `src/` directories created (GENESIS repository structure contract)

---

## Next Session — IB-009 (Runtime Professional)

**The Runtime Professional may now begin.** The development environment is governed.

Pre-flight checklist (carry forward from prior sessions):
- R006-01: `TEMPORAL_DB_PASSWORD` to `.env.example` — now handled in `02-users-and-permissions.sql` and `.env.example` needs the var
- R006-02: Healthcheck on `web` service — add to `docker-compose.yml` in IB-009
- R009: CE Container App — `ingress: internal` in Azure config
- R010-01: Produce `emergency-stop-ws.md` (WebSocket frame spec)

The Runtime Professional reads `architecture/reference/engineering-standards.md` as their Professional Standard BEFORE writing the first line of code.

---

**Previous Session Reference:** R-007 Gap Closure — EA (ADR-016/017/018) + Security Architect + Solution Architect (OpenAPI)

## IN-PROGRESS CHECKPOINT

| Milestone | Status |
|---|---|
| IB-010/012/013 added to backlog | ✓ DONE |
| WC-007 created (EA — ADR-016/017/018 + Emergency Stop fan-out) | ✓ DONE |
| ADR-016 language selection | ✓ DONE |
| ADR-017 web framework | ✓ DONE |
| ADR-018 Emergency Stop Temporal signal | ✓ DONE |
| Component specs updated (CE + PR — Emergency Stop fan-out) | ✓ DONE |
| WC-008 created (Security Architect) | ✓ DONE |
| Security Architecture + Threat Model produced | ✓ DONE |
| WC-009 created (Solution Architect — OpenAPI) | ✓ DONE |
| business-platform.openapi.yaml produced | ✓ DONE |
| professional-runtime.openapi.yaml produced | ✓ DONE |
| Governance records closed + Gate G5 authorized | ✓ DONE |

---

## Current State Summary

| Item | Status |
|---|---|
| Gate G2 | ✓ PASSED |
| Gate G3 | ✓ PASSED |
| Gate G4 | ✓ PASSED |
| Gate G5 | ✓ CLEAR — all R-007 P0 gaps closed |
| Architecture Phase | COMPLETE |
| Implementation | AUTHORIZED — Runtime Professional may begin IB-009 |

---

## Completed This Session

**EA Sprint 007 (IB-013) — R-008 APPROVED:**
- ADR-016: .NET 9 for CE/BP, Python 3.12 for PR/AI Runtime — rationale, alternatives, version pins
- ADR-017: Next.js 14 TypeScript PWA (Phase 1) → React Native (Phase 2)
- ADR-018: Emergency Stop Temporal signal routing — resolves GAP-003 (R-007)
- professional-runtime.md updated: PAAS session explicitly as PAASSessionWorkflow with EmergencyStop signal handler
- constitutional-engine.md updated: Temporal client dependency added (narrow, for signal routing only)

**Security Architecture Sprint 008 (IB-010) — R-009 APPROVED:**
- architecture/reference/security/threat-model.md — full STRIDE analysis, 6 threat actors, 30+ threats
- architecture/reference/security/security-architecture.md — network topology, JWT spec, secret management, OWASP Top 10, security CCTs
- GAP-006a from R-007 resolved

**Solution Architect Sprint 009 (IB-012) — R-010 APPROVED:**
- architecture/reference/api-specs/business-platform.openapi.yaml — 16 endpoints, all domain schemas
- architecture/reference/api-specs/professional-runtime.openapi.yaml — Emergency Stop, PAAS sessions, internal API
- ADR-002 (spec-first) now fulfilled
- GAP-002 from R-007 resolved

---

## R-007 Gap Closure Summary

| Gap | Severity | Resolution |
|---|---|---|
| GAP-001: Missing tech stack ADRs | HIGH | ✓ ADR-016, ADR-017 produced |
| GAP-002: OpenAPI specs missing | HIGH | ✓ Both specs produced (IB-012) |
| GAP-003: Emergency Stop fan-out | HIGH | ✓ ADR-018 — Temporal signal routing |
| GAP-006a: Security Architecture | HIGH | ✓ IB-010 complete (threat model + security arch) |
| GAP-004: PAAS session table | MEDIUM | Partially addressed — PAASSession schema in OpenAPI; `paas_sessions` DB table is IB-009 |
| GAP-005: pgvector embeddings | MEDIUM | Deferred to AI Architect sprint (IB-011 scope) |
| GAP-006b: AI Architecture | MEDIUM | Deferred (IB-011 scope) |

---

## Next Session — IB-009 (Runtime Professional)

**Authorized office: Runtime Professional (WC-010)**

Pre-flight checklist (from all reviews this session):
- R006-01: Add `TEMPORAL_DB_PASSWORD` to `.env.example`; create dedicated `temporal` DB user in postgres init scripts
- R006-02: Add healthcheck to `web` service in `docker-compose.yml`
- R006-03: Confirm AI Runtime pgvector access (`runtime_app` needs SELECT on embeddings table)
- R009 finding: CE Container App must have `ingress: internal` set
- R010-01: Produce `emergency-stop-ws.md` (WebSocket frame format, reconnection, heartbeat)

IB-009 success gate: `docker compose up` starts all services; each passes healthcheck; first CCT (Evidence First) passes; Runtime Universality skeleton test passes.

## IN-PROGRESS CHECKPOINT (update as work completes — prevents session-timeout loss)

| Milestone | Status |
|---|---|
| WC-006 created (Platform Architect) | ✓ DONE |
| R-006 (EA review of IB-008) | ✓ DONE — APPROVED |
| IB-008 DONE + backlog updated | ✓ DONE |
| Proto file produced (CA-R004-01) | ✓ DONE — constitutional_service.proto |
| Gate G4 formally closed | ✓ DONE — 2026-07-07 |

---

---

## Current State Summary

| Item | Status |
|---|---|
| Epoch 0 — Institution | ✓ Complete |
| Epoch 1 — Engineering Organization | ✓ Complete (Gate G1 passed) |
| Epoch 2 — Knowledge System | ✓ Complete (Gate G2 passed) |
| Gate G2 | ✓ PASSED — 2026-07-07 |
| Gate G3 | ✓ PASSED — 2026-07-07 |
| Gate G4 | ✓ PASSED — 2026-07-07 |
| Gate G5 | AUTHORIZED — IB-009 may begin |
| Implementation | AUTHORIZED — Runtime Professional may produce code |

---

## Last Completed Work (This Session — WC-006 + SA proto)

### Sprint 006 (Platform Architect — WC-006)
- WC-006 created
- docker-compose.yml and .env.example reviewed against component specs and all ADRs
- R-006 produced: EA review of IB-008 — **APPROVED**
- Three IB-009 implementation notes raised (R006-01 Temporal DB user, R006-02 web healthcheck, R006-03 AI Runtime pgvector access)
- IB-008 marked **DONE**

### Solution Architect — CA-R004-01 (proto file)
- `architecture/reference/proto/constitutional_service.proto` produced
- Complete gRPC interface specification for Constitutional Engine:
  - `RecordEvidence` — Evidence First Enforcer
  - `ValidateAction` — PAAS Boundary Validator
  - `GrantAuthorityLicense` / `RevokeAuthorityLicense` — Authority License Manager
  - `EvaluatePolicy` — Policy Evaluator
  - `TriggerEmergencyStop` — Emergency Stop Handler
- All message types defined with field-level constitutional basis notes
- Tenant ID via gRPC metadata (not request field) — specified in file header
- Latency budget targets documented per AD-001, AD-005

### Gate G4 Formally Closed
- All G4 items DONE: IB-005, IB-006, IB-007, IB-008, proto file
- README updated: Gate G4 PASSED, Gate G5 AUTHORIZED
- Implementation now constitutionally authorized

- R-004 produced: Constitutional Analyst review of WC-003 (Reference Architecture + Component Specs) — **APPROVED**
- R-005 produced: Business Architect review of WC-003 — **APPROVED** (all 26 capabilities verified)
- IB-005 marked DONE — Gate G3 confirmed passed
- IB-006 marked DONE — component specs accepted (proto file gap CA-R004-01 noted, required before Gate G5)

### Sprint 005 Executed (Data Architect — WC-005)

- WC-005 created: Data Architect Sprint 005 (IB-007)
- `architecture/reference/data/evidence-schema.md` produced — **complete evidence state machine specification**:
  - ABANDONED state added to evidence_state enum
  - action_instance_id column specified (missing from ledger-design.md — critical gap closed)
  - Approval-Gate vs PAAS execution model variants fully specified
  - Emergency Stop evidence record sequence specified (two-record pattern: stop event + ABANDONED records)
  - Scope-boundary confirmation event record pattern specified
  - State transition table: all valid and prohibited transitions with constitutional basis
  - constitutional_basis field format specification
  - DB enforcement approach: Constitutional Engine application-layer state machine validation
- IB-007 marked DONE

### Governance Records Updated

- `constitution/INSTITUTIONAL_BACKLOG.md` — IB-005, IB-006, IB-007 DONE; IB-008 IN_PROGRESS; index updated
- `README.md` — Gate G3 PASSED, Gate G4 IN_PROGRESS, Epoch 3 Architecture, authorized offices updated

---

## Gate G4 Remaining Work

| Item | Status | What remains |
|---|---|---|
| IB-008 — Infrastructure / Docker Compose | IN_PROGRESS | `docker-compose.yml` + `.env.example` exist (produced in prior session). Need: WC-006 (Platform Architect) created, formal review R-006 produced, IB-008 marked DONE. |
| Proto file (CA-R004-01) | OUTSTANDING | `architecture/reference/proto/constitutional_service.proto` must be produced before Gate G5. Assigned to Solution Architect scope. |

Gate G4 formally passes when IB-008 is reviewed (R-006) and `docker-compose.yml` is validated against the data architecture and component specs.

---

## Next Session Work

**IB-009 is authorized. Runtime Professional may begin foundation implementation.**

All architecture is complete. The following G5-parallel items exist and will be executed alongside IB-009:
- IB-014: Customer Portal Domain 7 + 2 API addenda (Business Architect + SA)
- IB-015: CS Agents Domain 8 Path A (Business Architect + Runtime Professional)
- IB-016: Platform Operations Architecture (Platform Architect)

Pre-flight checklist for IB-009 (from all prior reviews):
- R006-01: `TEMPORAL_DB_PASSWORD` to `.env.example`; dedicated `temporal` DB user in postgres init scripts
- R006-02: Healthcheck on `web` service in `docker-compose.yml`
- R006-03: `runtime_app` pgvector SELECT permission for AI Runtime embeddings
- R009: CE Container App must have `ingress: internal` set in Azure config
- R010-01: Produce `emergency-stop-ws.md` (WebSocket frame spec, reconnection, heartbeat)

Per R-007 — the following must be produced before the Runtime Professional starts implementation:

| Priority | Action | Office |
|---|---|---|
| P0 | ADR-016 — language selection (.NET 9 / Python 3.12) | Enterprise Architect |
| P0 | ADR-017 — web framework (Next.js / TypeScript) | Enterprise Architect |
| P0 | `architecture/reference/api-specs/business-platform.openapi.yaml` | Solution Architect |
| P0 | `architecture/reference/api-specs/professional-runtime.openapi.yaml` | Solution Architect |
| P0 | Emergency Stop fan-out mechanism specified (Temporal signal approach) | Enterprise Architect |
| P0 | Security Architecture sprint — threat model, network topology, JWT spec | Security Architect |
| P1 | `paas_sessions` table in data architecture | Data Architect |
| P1 | pgvector embeddings table for Creative Standard Profiles | AI / Data Architect |
| P1 | DP-011 — Constitutional Observability principle | Business Architect |

**Recommended next session:** Enterprise Architect — produce ADR-016, ADR-017, and Emergency Stop fan-out specification. This unblocks Security Architect and OpenAPI specs.

---

## Architecture Decisions Summary

| Decision | Choice |
|---|---|
| Deployment target | Azure India Central (Pune) |
| MVI scenarios | All 3: Dental Marketing, Beauty Artist, NIFTY Trading |
| Services | 4: Business Platform (.NET 9), Constitutional Engine (.NET 9), Professional Runtime (Python), AI Runtime (Python) |
| Workflow orchestration | Temporal (self-hosted dev → Temporal Cloud prod) |
| No Kafka | PostgreSQL event tables + Temporal queuing at MVI scale |
| No API gateway | Container Apps ingress handles routing at MVI scale |
| Mobile | Next.js PWA (Phase 1) → React Native (Phase 2) |
| Identity | Keycloak as OAuth broker — Google default, expandable |
| Observability | OpenTelemetry → Jaeger (dev) → Azure Monitor (cloud) |
| Database | PostgreSQL Flex + pgvector + Row-Level Security for multi-tenancy |
| JWT propagation | Customer JWT → gRPC metadata → PostgreSQL SET LOCAL → AI context |
| Testing | Zero manual, image promotion, Constitutional Compliance Tests |
| Cost | Dev ~INR 5-6k/month, each non-prod env within INR 10k limit |
| Evidence state machine | Append-only event records; state transitions = new INSERTs; action_instance_id groups events |
| Emergency Stop evidence | Two-record pattern: stop event record + ABANDONED records for in-flight actions |


---

## Current State Summary

| Item | Status |
|---|---|
| Epoch 0 — Institution | ✓ Complete |
| Epoch 1 — Engineering Organization | ✓ Complete (Gate G1 passed) |
| Epoch 2 — Knowledge System | ✓ Sprint 001 complete — IB-001 DONE |
| Gate G2 | ✓ PASSED — 2026-07-07 |
| Amendment A-005 | ✓ Ratified — Creative Identity as Protected Right |
| Gate G3 | Not Started — IB-002, IB-003, IB-004 now authorized |
| Gate G4+ | Blocked |
| Implementation | Constitutionally prohibited until Gate G5 |

---

## Last Completed Work

Architecture phase initiated by Founder (acting as Chief Architect):

- `architecture/100k/README.md` v0.5 — Full system context, solution layers, Docker Compose design, mobile strategy, service decomposition, Temporal orchestration, CI/CD philosophy, cost breakdown
- `architecture/32k/README.md` — Service communication, JWT propagation, API design, scaling strategy, 9 pending ADRs

Engineering governance additions to GENESIS:
- Engineering Quality Mandate (zero manual testing, image promotion pipeline)
- Constitutional Compliance Tests (WAOOAW-specific test category)
- Operations Discovery Rule

Agent infrastructure:
- `.github/copilot-instructions.md` — Copilot auto-inject entry point
- `BOOTSTRAP.md` — Updated with context and role-ask
- `standards/` — 5 professional standards

---

## Architecture Decisions Made (This Session)

| Decision | Choice |
|---|---|
| Deployment target | Azure India Central (Pune) |
| MVI scenarios | All 3: Dental Marketing, Beauty Artist, NIFTY Trading |
| Services | 4: Business Platform (.NET), Constitutional Engine (.NET), Professional Runtime (Python), AI Runtime (Python) |
| Workflow orchestration | Temporal (self-hosted dev → Temporal Cloud prod) |
| No Kafka | PostgreSQL event tables + Temporal queuing at MVI scale |
| No API gateway | Container Apps ingress handles routing at MVI scale |
| Mobile | Next.js PWA (Phase 1) → React Native (Phase 2) |
| Identity | Keycloak as OAuth broker — Google default, expandable |
| Observability | OpenTelemetry → Jaeger (dev) → Azure Monitor (cloud) |
| Database | PostgreSQL Flex + pgvector + Row-Level Security for multi-tenancy |
| JWT propagation | Customer JWT → gRPC metadata → PostgreSQL SET LOCAL → AI context |
| Testing | Zero manual, image promotion, Constitutional Compliance Tests |
| Cost | Dev ~INR 5-6k/month, each non-prod env within INR 10k limit |

---

## Completed Work (This Session)

### ADR Set Complete — 15 ADRs Formally Ratified (commit 4ec4248)

**ADR-001–009 gaps fixed:**
- ADR-001: Proto file ownership + versioning rule added
- ADR-002: Toolchain named (openapi-generator, Spectral, schemathesis)
- ADR-003: `active_contracts` removed from JWT (stale-session authorization risk)
- ADR-004: JWT transport secured — Authorization header only, never query params (OWASP A02)
- ADR-005: Replica failure recovery path added for PAAS sessions
- ADR-006: ASP.NET Core built-in rate limiting added as per-tenant backstop (zero infra cost)
- ADR-007: Concrete cloud portability escape hatch for mTLS documented
- ADR-008: Keycloak version pinning + upgrade protocol added
- ADR-009: Alert routing targets defined (P0: constitutional violations; P1: PAAS latency)

**ADR-010–015 — New ADRs ratified:**

| ADR | Decision | Roles |
|---|---|---|
| ADR-010 | Cloud Portability Posture — Azure-first, named escape hatches per Azure dependency | Enterprise Arch + Platform Arch |
| ADR-011 | Database Migration Strategy — EF Core Migrations; Audit Ledger: no destructive migrations | Data Arch + Platform Arch |
| ADR-012 | Container Image Registry — GHCR (free, cloud-agnostic, GitHub Actions native) | Platform Arch + Enterprise Arch |
| ADR-013 | CI/CD Pipeline Structure — GitHub Actions, trunk-based, CCTs as mandatory gate | Platform Arch + Enterprise Arch |
| ADR-014 | Secret Management — `.env` dev / GitHub Secrets CI / Azure Key Vault cloud | Security Arch + Platform Arch |
| ADR-015 | Temporal Deployment — self-hosted dev/QA; Temporal Cloud UAT/prod | Platform Arch + Enterprise Arch |

---

## Next Planned Work

### Immediate (Next Session)

1. **Sprint 001 Execution** — Constitutional Analyst produces knowledge claims in `knowledge/claims/` (IB-001, Gate G2)
2. **`architecture/reference/`** — C4 container/component detail specs for each service
3. **Data Architecture** — Constitutional Audit Ledger schema, RLS design, three-ledger model
4. **`.github/workflows/`** — CI/CD pipeline implementation (GitHub Actions, per ADR-013)
5. **`infrastructure/keycloak/`** — Keycloak realm export JSON (per ADR-008)

---

## Open Questions Requiring Founder Input

None currently open.

---

## Docker Compose Services (Current Design)

```
postgres          — PostgreSQL 16 + pgvector (port 5432)
keycloak          — Identity broker (port 8443)
ollama            — Local LLM for dev (port 11434)
temporal          — Workflow orchestration (port 7233)
temporal-ui       — Temporal dashboard (port 8080)
jaeger            — Distributed tracing (port 16686)
business-api      — Business Platform .NET (port 5001)
constitutional-engine — Constitutional Engine .NET (port 5002, internal)
professional-runtime  — Professional Runtime Python (port 5003)
ai-runtime        — AI Runtime Python (port 5004, internal)
web               — Next.js PWA (port 3000)
```

`docker compose up` → full stack running locally.

---

## Repository Structure (Current)

```
CONSTITUTION.md       — Constitutional law v1.2
GENESIS.md            — Engineering operating system (Parts 01-04)
ORGANIZATION.md       — Constitutional organization (10 offices)
INSTITUTIONAL_BACKLOG.md — Work queue (IB-001 to IB-005)
BOOTSTRAP.md          — Agent onboarding protocol
README.md             — Institutional state
RED_TEAM.md           — Constitutional audit (11 attacks, 0 failures)
.github/copilot-instructions.md — Copilot auto-inject
architecture/
  100k/README.md      — System context + solution layers
  32k/README.md       — Service architecture + API design
simulation/           — Constitutional Discovery Cases 001-003
standards/            — Professional standards (5 offices)
work-contracts/       — Sprint contracts + operational discoveries
blockers/             — Constitutional blockers
knowledge/            — Claims (empty — Gate G2 not yet run)
adr/                  — Architecture Decision Records (empty — pending)
```

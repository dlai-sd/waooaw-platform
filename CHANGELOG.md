# Changelog

All notable changes to the WAOOAW Platform are documented here.
This file is auto-generated from conventional commits. Do not edit manually.

Format: [Conventional Commits](https://www.conventionalcommits.org/) —
types: `feat` | `fix` | `constitutional` | `cct` | `chore` | `refactor` | `security` | `docs`

---

## [0.10.0] — 2026-07-08

### Implementation (IB-009 Foundation)
- `src/constitutional-engine/`: .NET 9 gRPC service skeleton
  - ConstitutionalServiceImpl: RecordEvidence (writes to DB), ValidateAction stub, TriggerEmergencyStop
  - Evidence First enforced: write confirmed before returning OK; gRPC INTERNAL on failure
  - State transition validation (evidence-schema.md)
  - ConstitutionalDbContext with EvidenceRecord + AuthorityLicense entities
  - Dockerfile (multi-stage, non-root, grpc_health_probe)
- `src/business-platform/`: .NET 9 REST service skeleton
  - POST /api/v1/employment/contracts — Evidence First: CE called BEFORE SaveChangesAsync
  - GET /api/v1/employment/contracts/{id}
  - GET /health
  - TenantDbCommandInterceptor: SET LOCAL app.tenant_id on every DB command
  - JWT middleware: RS256, algorithm enforcement, tenant_id extraction
  - BusinessDbContext with EmploymentContract entity
  - Dockerfile (multi-stage, non-root)
- `src/professional-runtime/`: Python FastAPI skeleton
  - GET /health
  - WSS /ws/emergency-stop (stub — READY frame, PING/PONG, EmergencyStop stub)
  - POST /api/v1/paas/sessions (stub)
  - Dockerfile + pyproject.toml
- `src/ai-runtime/`: Python FastAPI skeleton
  - GET /health
  - POST /api/v1/inference (stub with C-041 enforcement placeholder)
  - POST /api/v1/tools/execute (MCP stub — default deny enforced)
  - Dockerfile + pyproject.toml
- `tests/constitutional/bp/test_cct_ef_01.py`: CCT-EF-01 Evidence First pattern tests
  - EF01_a/b: CE called before SaveChanges, failure path exists
  - EF01_c: action_instance_id present
  - EF01_d: constitutional_basis provided (AD-008)

### Reviews
- R-011: EA review of digital-marketing-agent.md — APPROVED WITH NOTE (patient consent mechanism)

### Data Architecture
- `01-schemas.sql`: institutional schema added (ADR-019, FR-003)
- `03-enums-and-tables.sql`: domain_knowledge + platform_intelligence tables (institutional schema)

---

## [0.9.0] — 2026-07-08

### Constitutional (new claims + GENESIS Part 05)
- C-040: Domain specialization as constitutional obligation (LAW)
- C-041: Every MCP tool call governed by Decision Space (LAW)
- GENESIS Part 05: Agent Definition Protocol — mandatory specification before any new agent implementation
  - RAG Specification Standard (three-tier: Domain / Customer / Platform Intelligence)
  - MCP Tool Specification Standard (default deny, C-041 enforcement)
  - Learning Loop Standard (FR-003 boundary at inference signal boundary)

### Architecture (new ADRs + agent infrastructure)
- ADR-019: RAG Architecture — three-tier, pgvector in `institutional` schema at MVI
- ADR-020: MCP Integration Pattern — AI Runtime as MCP client, CE.ValidateAction before every tool call
- ADR-INDEX.md: updated to 20 ADRs
- AI Runtime component spec: RAG pipeline + MCP client sections added

### Agent Specifications (new directory)
- `architecture/reference/agents/AGENT-AUTHORING-GUIDE.md` — reusable template for new agent types
- `architecture/reference/agents/digital-marketing-agent.md` — first complete agent specification
  - 7 Skills: Content Strategy, Instagram, Facebook, Google Business, WhatsApp, Video, Analytics
  - RAG sources per skill (Tier 1/2/3)
  - MCP tools per skill with authorization + failure mode
  - 15-minute onboarding conversation flow
  - ProfessionalTemplate definition (dental + beauty variants)
  - Full constitutional checklist

---

## [0.8.0] — 2026-07-08

### Constitutional (new claims)
- C-036: Skills as first-class constitutional units (C-036 LAW)
- C-037: Business outcome KPIs as primary performance measure (C-037 LAW)
- C-038: Pro-rata billing as constitutional right (C-038 LAW)
- C-039: Conversational configuration as constitutional obligation (C-039 CONFIRMED)

### Knowledge (Business Architect)
- `knowledge/business-capabilities.md`: 16 new capabilities across D1/D2/D3/D4/D5/D6 + new D9 Commercial
- `knowledge/architectural-drivers.md`: AD-012 (Business KPI Primacy), AD-013 (Conversational Config), AD-014 (Pro-Rata Billing)
- `knowledge/design-principles.md`: DP-011 (Business Outcome First), DP-012 (Skill Granularity in Governance)

### Architecture (EA/SA/DA percolation)
- `architecture/reference/domain-model.md`: Skill entity, SubscriptionBillingEvent entity
- `architecture/reference/components/business-platform.md`: Skill Manager, Performance Monitor, Subscription Manager components
- `architecture/reference/components/ai-runtime.md`: Conversational Configuration Engine component
- `architecture/reference/api-specs/business-platform.openapi.yaml`: Skills, Performance, Billing, Conversational Config endpoints + schemas

### Data Architecture
- `03-enums-and-tables.sql`: skill_state enum, billing_event_type enum, professional_skills table, skill_performance_records table, subscription_billing_events table (append-only)

---

## [0.7.0] — 2026-07-08

### Constitutional (Founder Resolutions)
- FR-002: Trial = full constitutional employment from day one; trial outputs owned by customer
- FR-003: Agent learning is WAOOAW institutional IP; customer data is private and never shared
- FR-004: Agent Teams — enterprise tier, WAOOAW-provided Team Coordinator, deferred from MVI

### Architecture (gaps bridged by simulation)
- `architecture/reference/domain-model.md`: EmploymentContract `isTrial`, `trialEndsAt`, `trialConvertedAt`
- `infrastructure/postgres/init/03-enums-and-tables.sql`: trial columns on `business.employment_contracts`
- `architecture/reference/api-specs/business-platform.openapi.yaml`: trial fields + `POST /convert-trial` endpoint
- `architecture/reference/data/ledger-design.md`: Institutional Learning Zone (FR-003 fourth data zone)
- `architecture/reference/security/security-architecture.md`: Data Classification table §0 (FR-003)

### Backlog
- IB-018: Agent Teams — Constitutional Team Architecture (enterprise, post-MVI, DEFERRED)

---

## [0.6.0] — 2026-07-07

### Added
- Agent efficiency index layer: `constitution/AGENT-ENTRY.md`, `adr/ADR-INDEX.md`, `architecture/reference/COMPONENT-QUICK-REF.md`
- Office Quick-Start cards (50 lines vs 880): `.github/agent-context/office-*.md`
- GitHub labels: 67 labels created on repository (type/office/component/domain/gate/sprint/status)
- `scripts/setup-github-labels.sh` — reproducible label creation
- `architecture/reference/api-specs/emergency-stop-ws.md` — WebSocket frame spec, reconnection, heartbeat
- `ARCHITECTURE.md` and `CHANGELOG.md` at repository root (GENESIS mandate)
- `commitlint.config.js` — enforces conventional commits including `constitutional` type
- BOOTSTRAP Step 3 + 5 updated to route through indices (60-70% token reduction per session)

### Fixed
- CB-001 (simulation): `ABANDONED` enum was already in business-platform.openapi.yaml ✓
- CB-002 (simulation): CE gRPC Health service already specified in component spec ✓

---

## [0.5.0] — 2026-07-07

### Added
- GitHub-grounded operating model: 4 issue templates, CODEOWNERS, PR template
- `.github/workflows/pm-report.yaml` — Platform Delivery Tracker (Office 12) automated reporting
- `.github/workflows/project-automation.yaml` — issue lifecycle automation
- `.github/copilot-instructions.md` updated with GitHub sprint mode, PM role, branch/commit conventions
- `constitution/ORGANIZATION.md`: Office 12 — Platform Delivery Tracker
- `README.md`: Operating Commands section (5 bare-minimum invocations)
- Sprint 1 simulation: 5 components, 2 CCTs proven, 2 Constitutional Blockers surfaced correctly

---

## [0.4.0] — 2026-07-07

### Added (coding agent readiness — 7 fixes)
- `infrastructure/postgres/init/02-users-and-permissions.sh` (bash, proper env var interpolation)
- `architecture/reference/proto/buf.yaml` + `buf.gen.yaml` (proto toolchain)
- Dockerfile templates: `.NET 9`, `Python 3.12`, `Next.js 14`
- `docker-compose.yml` CE healthcheck: TCP check for dev; web service healthcheck
- Engineering-standards §9: EF Core empty initial migration technique
- Engineering-standards §10: `TenantDbCommandInterceptor` pseudocode
- Engineering-standards §11: Dev JWT via `waooaw-dev-client`
- `infrastructure/keycloak/waooaw-realm.json`: dev user + `waooaw-dev-client`
- `scripts/get-dev-token.sh`

---

## [0.3.0] — 2026-07-07

### Added (R-007 P0 gap closure)
- ADR-016: .NET 9 / Python 3.12 language selection
- ADR-017: Next.js 14 TypeScript web framework
- ADR-018: Emergency Stop Temporal signal routing (GAP-003 resolution)
- `architecture/reference/security/`: threat model (STRIDE) + security architecture
- `architecture/reference/api-specs/`: business-platform.openapi.yaml + professional-runtime.openapi.yaml
- IB-017 Phase 2 Readiness: CI/CD pipelines, CCT framework, postgres init SQL, Keycloak realm

---

## [0.2.0] — 2026-07-07

### Added (Architecture phase)
- 35 ratified constitutional claims (C-001 to C-035) — Gate G2 PASSED
- Business Capability Map (26 capabilities), Architectural Drivers (11), Design Principles (10) — Gate G3 PASSED
- Complete Reference Architecture: context, containers, domain model, 4 component specs — Gate G4 PASSED
- Data architecture: three-ledger design, evidence state machine with ABANDONED state
- 15 ADRs (ADR-001 through ADR-015)
- Security architecture, OpenAPI specs, proto contract — Gate G5 CLEAR

---

## [0.1.0] — 2026-07-06

### Added (Institution foundation)
- `constitution/CONSTITUTION.md` v1.2 (17 Articles, 4 Amendments)
- `constitution/GENESIS.md` Parts 01–04 + Engineering Quality Mandate
- `constitution/ORGANIZATION.md` (11 offices, 7 attributes, Operating Protocol)
- `constitution/BOOTSTRAP.md` + `.github/copilot-instructions.md`
- `standards/` (5 professional standards)
- `simulation/` (3 cases, PRECEDENTS.md, ECI-001, ECI-002)
- `constitution/RED_TEAM.md` (11 attacks, 0 constitutional failures)

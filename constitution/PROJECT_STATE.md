# PROJECT_STATE.md

**Last Updated:** 2026-07-07

**Session Reference:** Architecture Phase — Data Architect session (WC-005)

---

## Current State Summary

| Item | Status |
|---|---|
| Epoch 0 — Institution | ✓ Complete |
| Epoch 1 — Engineering Organization | ✓ Complete (Gate G1 passed) |
| Epoch 2 — Knowledge System | ✓ Sprint 001 complete — IB-001 DONE |
| Gate G2 | ✓ PASSED — 2026-07-07 |
| Amendment A-005 | ✓ Ratified — Creative Identity as Protected Right |
| Gate G3 | ✓ PASSED — 2026-07-07 (R-004 CA APPROVED, R-005 BA APPROVED) |
| Gate G4 | IN PROGRESS — IB-005 DONE, IB-006 DONE, IB-007 DONE, IB-008 IN_PROGRESS |
| Gate G5 | Not Started |
| Implementation | Constitutionally prohibited until Gate G5 |

---

## Last Completed Work (This Session)

### Sprint 003 Formally Closed (Enterprise Architect + concurrent IB-006)

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

1. **Platform Architect — WC-006**: Formally close IB-008 — produce R-006 review of docker-compose.yml + .env.example against data architecture and component specs
2. **Solution Architect — proto file**: Produce `architecture/reference/proto/constitutional_service.proto` (CA-R004-01 finding)
3. **Pass Gate G4** — update README.md, PROJECT_STATE.md, declare Gate G5 authorized
4. **Runtime Professional — WC-007**: Begin IB-009 foundation implementation skeleton

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

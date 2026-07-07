# PROJECT_STATE.md

**Last Updated:** 2026-07-07

**Session Reference:** Architecture Phase — Chief Architect session

---

## Current State Summary

| Item | Status |
|---|---|
| Epoch 0 — Institution | ✓ Complete |
| Epoch 1 — Engineering Organization | ✓ Complete (Gate G1 passed) |
| Epoch 2 — Knowledge System | Sprint 001 authorized, not yet executed |
| Architecture Phase | In progress (parallel to Epoch 2) |
| Gate G2 | Not started |
| Gate G3+ | Blocked |
| Implementation | Constitutionally prohibited |

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

### ADRs — Formally Ratified (commit 881a616)

| ADR | Decision | Roles |
|---|---|---|
| ADR-001 | gRPC for Constitutional Engine | Enterprise Arch + Solution Arch |
| ADR-002 | OpenAPI spec-first | Solution Arch + Enterprise Arch |
| ADR-003 | JWT claims + multi-tenancy anchor | Security Arch + Enterprise Arch |
| ADR-004 | Emergency Stop — Azure SignalR | Solution Arch + Security Arch |
| ADR-005 | PAAS session isolation — session-affinity | Enterprise Arch + Solution Arch |
| ADR-006 | Rate limiting deferred to Epoch 6 | Platform Arch + Business Arch |
| ADR-007 | gRPC mTLS — Container Apps managed certs | Security Arch + Platform Arch |
| ADR-008 | Keycloak as OAuth federation broker | Security Arch + Solution Arch |
| ADR-009 | OpenTelemetry + Jaeger/Azure Monitor | Platform Arch + Enterprise Arch |

---

## Next Planned Work

### Immediate (Next Session)

1. **Sprint 001 Execution** — Constitutional Analyst produces knowledge claims in `knowledge/claims/` (IB-001, Gate G2)
2. **architecture/reference/** — C4 container/component detail specs for each service (Founder decision: sprint vs reference first)
3. **Data Architecture** — Constitutional Audit Ledger schema, RLS design, three-ledger model
4. **Deployment Architecture** — Terraform modules per environment, GitHub Actions pipeline

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

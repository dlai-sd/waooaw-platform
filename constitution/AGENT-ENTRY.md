# WAOOAW Agent Entry Point

**Read this file first. It routes you to exactly what you need. Do not scan the full repository.**

---

## ⛔ IMPLEMENTATION GATE — READ BEFORE ANYTHING ELSE

```
If your next action involves creating files in src/, writing runnable code,
or producing build artifacts:

STOP. DO NOT PROCEED.

"G5 CLEAR" or "Implementation AUTHORIZED" in README means gate prerequisites
are met. It does NOT authorize THIS session's implementation sprint.

A TO-DO list, a GitHub Issue, or a Work Contract is NOT authorization.

You must ask: "This would begin writing implementation code.
Do you explicitly authorize IB-009 implementation for this session?"

Wait for explicit Founder confirmation. No exceptions.
```

---

## Current Platform State (updated each session)

```
Version:   0.39.0 | Gate: G5 CLEAR | Epoch: 1 — Employment
Authorized: Runtime Professional (IB-009 — Foundation Implementation — NOT YET STARTED)
Implementation: AWAITING FOUNDER AUTHORIZATION | Architecture: COMPLETE
Activation Gate: 14 sections (extended v0.39.0: +Section 14 Campaign Theme Engine Gate)
```

**Open Constitutional Blockers:** None

**Active Founder Resolutions:** FR-001 (CS Agents) · FR-002 (Trial) · FR-003 (Learning IP) · FR-004 (Teams — deferred) · **FR-005 (Skill 14 — WAOOAW Self-Marketing AUTHORIZED 2026-07-12: ₹5,000/month budget, 50+ diverse customer threshold before performance stats)**

**Note for implementation sprint:** TRADING/EXECUTION/ESCALATION_DECISION is BREAKING type — Founder must acknowledge before Trading agent implementation begins.

**Approved Agent Specifications (GENESIS Part 05):**
- Digital Marketing Agent (Healthcare + Beauty) v2.5 — APPROVED. R-014 + R-015. 58 active prompts. Activation Gate 14/14 PASS (v0.39.0). Sections 3.18+3.19+3.21 added. Campaign Theme Engine + Platform Intelligence + SCR operational.
- Trading Agent (FO + Crypto) v1.7 — APPROVED. R-012 + R-017 + R-018. Full Activation Gate 11/11 PASS. **P1 before IB-009: Sections 3.18+3.19 (SIL/SIR) not yet added to Trading spec.**
- Agricultural Advisory Agent (India Small Farmers) v2.6 — APPROVED. R-013 + R-015 + R-017 + R-018. Full Activation Gate 11/11 PASS. Sections 4.13+4.18 (SIL+SIR) added (v0.35.0–v0.36.0). Gate 12+13 status: PASS.

**New in v0.35.0–v0.38.0:**
- C-053: Signal Sensing Obligation (LAW) — all time-sensitive agents must run Signal Watch Loops
- C-054: Skill Intelligence Routing (LAW) — multi-skill agents must route requests via SIR
- AD-026: Signal Watch Workflow Pattern; AD-027: Skill Capability Manifest Standard
- DP-022: Proactive Intelligence Primacy; DP-023: Skill Network Intelligence
- AGENT-AUTHORING-GUIDE Sections 3.18 (SIL), 3.19 (SIR), 3.20 (Skill Proposal Governance Loop)
- Skill Dependency Register: architecture/reference/skill-dependency-register.md
- ADR-021 Section 7: oauth-vault Azure Key Vault backing confirmed
- type:skill-proposal GitHub Issue template added

**Deferred:** OD-003 (DA scope) · AI Architect sprint (GAP-006b) · IB-018 (Agent Teams — enterprise, post-MVI)

---

## Office Routing — Read ONLY what your office needs

| Office | Read | Skip entirely |
|---|---|---|
| **Runtime Professional** | This file + your Work Contract + [COMPONENT-QUICK-REF.md](../architecture/reference/COMPONENT-QUICK-REF.md) + [ADR-INDEX.md](ADR-INDEX.md) + [engineering-standards.md](../architecture/reference/engineering-standards.md) | Full ORGANIZATION.md, full ADRs, knowledge/claims/, simulation/ |
| **Enterprise Architect** | This file + your WC + [ADR-INDEX.md](ADR-INDEX.md) + knowledge/index.md + knowledge/business-capabilities.md + architectural-drivers.md + design-principles.md | Full individual ADRs (use index), ORGANIZATION.md, simulation/, src/ |
| **Solution Architect** | This file + your WC + [ADR-INDEX.md](ADR-INDEX.md) + [COMPONENT-QUICK-REF.md](../architecture/reference/COMPONENT-QUICK-REF.md) + architecture/reference/ (all) | knowledge/claims/, simulation/, ORGANIZATION.md in full, src/ |
| **Data Architect** | This file + your WC + [COMPONENT-QUICK-REF.md](../architecture/reference/COMPONENT-QUICK-REF.md) + architecture/reference/data/ + ADR-011, ADR-003 full | Other ADRs (use index), ORGANIZATION.md, simulation/ |
| **Platform Architect** | This file + your WC + [ADR-INDEX.md](ADR-INDEX.md) + architecture/reference/security/ + docker-compose.yml | knowledge/claims/, ORGANIZATION.md, simulation/ |
| **Security Architect** | This file + your WC + architecture/reference/security/ (all) + ADR-003, ADR-007, ADR-008 full + [ADR-INDEX.md](ADR-INDEX.md) | knowledge/claims/, simulation/, src/ |
| **Business Architect** | This file + your WC + knowledge/claims/ (all) + knowledge/confidence-register.md + knowledge/index.md + GENESIS Part 01 | simulation/ (cases), architecture/, src/, ORGANIZATION.md in full |
| **Constitutional Analyst** | This file + your WC + CONSTITUTION.md + GENESIS.md + simulation/PRECEDENTS.md + simulation/ (cases) + RED_TEAM.md | architecture/, src/, knowledge/ (you produce it) |
| **Product Owner** | This file + INSTITUTIONAL_BACKLOG.md + PROJECT_STATE.md + ORGANIZATION.md (all office charters) | architecture/, src/, knowledge/claims/, simulation/ |
| **Platform Delivery Tracker** | This file + INSTITUTIONAL_BACKLOG.md + PROJECT_STATE.md + GitHub Issues via API | Everything else — read-only observational role |

---

## Key File Map (where things live)

```
Architecture
  Context / Containers / Domain model   architecture/reference/{context,containers,domain-model}.md
  Component specs (4 services)          architecture/reference/components/{service-name}.md
  API contracts (REST)                  architecture/reference/api-specs/{service}.openapi.yaml
  API contract (gRPC)                   architecture/reference/proto/constitutional_service.proto
  Data architecture                     architecture/reference/data/{ledger-design,evidence-schema}.md
  Security architecture                 architecture/reference/security/{security-architecture,threat-model}.md
  Dockerfile templates                  architecture/reference/dockerfiles/Dockerfile.{dotnet-service,python-service,nextjs-web}
  Engineering standards                 architecture/reference/engineering-standards.md
  ADR quick reference                   adr/ADR-INDEX.md           ← read this before individual ADRs
  Individual ADRs                       adr/ADR-NNN-*.md

Constitutional
  Backlog + gate status                 constitution/INSTITUTIONAL_BACKLOG.md
  Session state                         constitution/PROJECT_STATE.md
  Bootstrap protocol                    constitution/BOOTSTRAP.md
  Office charters                       constitution/ORGANIZATION.md
  Quick-start cards (per office)        .github/agent-context/office-{name}.md  ← use INSTEAD of full ORGANIZATION.md

Implementation
  Source code (coming)                  src/{service-name}/
  Constitutional compliance tests       tests/constitutional/README.md + tests/constitutional/{service}/
  Infrastructure init                   infrastructure/postgres/init/*.sql, /keycloak/, /temporal/
  Dev environment                       docker-compose.yml + .env.example
  Bootstrap script                      scripts/setup.sh
  Dev JWT script                        scripts/get-dev-token.sh

GitHub Operations
  Issue templates                       .github/ISSUE_TEMPLATE/
  PR template                           .github/pull_request_template.md
  CI/CD pipelines                       .github/workflows/{ci,promote,pm-report,project-automation}.yaml
```

---

## The Three Facts Every Agent Must Know

**Fact 1 — Constitutional Engine is gRPC only, never exposed externally.**
All services call CE via gRPC. CE does not expose REST. CE is internal-only.

**Fact 2 — Evidence First is not optional.**
Every governance event must call CE.RecordEvidence() and receive OK before the calling service returns success. CCT-EF-01 and CCT-EF-02 verify this in every environment.

**Fact 3 — tenant_id comes from JWT, never from request body.**
The JWT middleware extracts tenant_id and stores it in HttpContext. The EF Core interceptor calls `SET LOCAL app.tenant_id` before every query. PostgreSQL RLS enforces isolation from there. An agent that accepts tenant_id from a request body has created a security vulnerability.

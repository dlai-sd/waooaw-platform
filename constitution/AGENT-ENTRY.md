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
Version:    0.96.0  |  Gate: G5 CLEAR  |  Epoch: 1 — Employment
Last update: 2026-07-21 — Full autonomy model: C-066 Tier 2A, BOOTSTRAP amendment, autonomous-sprint.yaml
Implementation: AUTONOMOUS — autonomous-sprint.yaml fires every 2h (C-066 Tier 2A + C-070 Third Instinct)
Human Override: AUTONOMOUS_HALT: true in PROJECT_STATE.md SPRINT_STATE_MACHINE (C-001)
Constitutional Claims: C-001 to C-075 (75 RATIFIED)
Agents (customer): DMA v3.0 | Trading v1.7 | Agricultural Advisor v2.7 | Private Tutor v1.0
Agents (internal): Platform IT Expert v1.0 | Steward Assistant v1.0 | Self-Improvement Analyst v1.0 | Platform Operations v1.0
CCTs: 50 specified | ADRs: 29 | Security: Audit-ready | Infra: Cloud-optimized + Blue-Green
Web: web/WAOOAWHome.html — Landing page v1.0 + Auth modal (Google/WhatsApp/email, Figma-style)
Three Humans: Yogesh Khandge (Founder) · Sujay Khandge (Business Growth) · Ojal Khandge (Ethics Officer)
Company: DLAI Satellite Data (OPC) Pvt Ltd | CIN: U62090PN2024OPC230499 | GSTIN: 27AAKCD8188R1ZH
```

**Open Constitutional Blockers:** None

**Active Founder Resolutions:**
- FR-001 (CS Agents) · FR-002 (Trial) · FR-003 (Learning IP) · FR-004 (Teams — deferred)
- **FR-005 (Skill 14 WAOOAW Self-Marketing — AUTHORIZED: ₹5k/month, 50+ diverse customers)**

**CRITICAL before Trading implementation:** `TRADING/EXECUTION/ESCALATION_DECISION` is BREAKING — Founder must acknowledge before Trading sprint begins.

**Approved Agent Specifications (GENESIS Part 05):**
- **DMA v3.0** — APPROVED. 21 skills (incl. Skill 7b/16/18/19/20/21). 10 new MCPs (C-074). Sims 019/020/021 Grade A.
- **Trading v1.7** — APPROVED. ⚠️ ESCALATION_DECISION pending Founder ack. Sim 013 Grade A.
- **Agricultural Advisor v2.7** — APPROVED. WhatsApp primary (ADR-023). Sim 014 Grade A.
- **Private Tutor v1.0** — APPROVED. C-060 minor protection. Web whiteboard. Sim 018.
- **Platform IT Expert v1.0** — APPROVED. Internal SDLC agent. C-065/C-066. 11 SDLC skills.
- **Steward Assistant v1.0** — APPROVED. ops.waooaw.ai entry (C-068). Always FRONTIER (ADR-028).
- **Self-Improvement Analyst v1.0** — APPROVED. C-069. Prompt improvement pipeline.
- **Platform Operations v1.0** — APPROVED. Monitoring, incident response, SLA tracking.

**Key constitutional claims C-068 → C-075:**
- C-068: Steward Access Isolation (ops.waooaw.ai, 3-account OAuth allowlist)
- C-069: Platform Self-Improvement (Self-Improvement Analyst loop)
- C-070: Constitutional DNA (3 instincts — inherited by every agent)
- C-071: Quality Framework (7 layers — Layer 1 CCTs through Layer 7 Chaos)
- C-072: Coding Standards (5 dimensions per language)
- C-073: Constitutional Annotations (@constitutional in source, CCT-TR-01)
- C-074: On-the-Fly MCP Provisioning (09-mcp-registry.sql, no deployment cycles)
- C-075: White-Label Reseller (agency commercial model, 10-reseller-agency.sql)

**Claims C-059 → C-067 (previously new, now ratified):**
- C-059: Implementation Traceability | C-060: Minor Student Protection (LAW) | C-061: Content Safety (LAW)
- C-062: AI Security (OWASP LLM Top 10) | C-063: Data Minimisation | C-064: Three-Human Institution
- C-065: SDLC Separation of Duties | C-066: Authorization Tiers | C-067: Blue-Green + Cost Ceiling

**Founder Actions Outstanding (P0):** See `security/FOUNDER-ACTIONS.md` — FA-001 to FA-021+
- **FA-021** (GCP Vertex AI SA key) — CRITICAL PATH: AI Runtime MID_TIER/FRONTIER cannot function without this
- **FA-002** (Meta BM verification) — START NOW: 2-4 week lead time for WhatsApp/DMA
- **FA-005** (Trading ESCALATION_DECISION ack) — 5 min, unblocks Trading sprint
- **Azure SP + GitHub Secrets** — blocks ALL CI/CD from running

---

## Office Routing — Read ONLY what your office needs

| Office / Agent | Read | Skip entirely |
|---|---|---|
| **Runtime Professional** | This file + Work Contract + [COMPONENT-QUICK-REF.md](../architecture/reference/COMPONENT-QUICK-REF.md) + [ADR-INDEX.md](ADR-INDEX.md) + engineering-standards.md | Full ORGANIZATION.md, full ADRs, knowledge/claims/, simulation/ |
| **Enterprise Architect** | This file + WC + [ADR-INDEX.md](ADR-INDEX.md) + knowledge/index.md + architectural-drivers.md + design-principles.md | Full individual ADRs, ORGANIZATION.md, simulation/, src/ |
| **Solution Architect** | This file + WC + [ADR-INDEX.md](ADR-INDEX.md) + [COMPONENT-QUICK-REF.md](../architecture/reference/COMPONENT-QUICK-REF.md) + architecture/reference/ (all) | knowledge/claims/, simulation/, ORGANIZATION.md in full |
| **Data Architect** | This file + WC + [COMPONENT-QUICK-REF.md](../architecture/reference/COMPONENT-QUICK-REF.md) + architecture/reference/data/ + ADR-011, ADR-003 | Other ADRs, ORGANIZATION.md, simulation/ |
| **Platform Architect** | This file + WC + [ADR-INDEX.md](ADR-INDEX.md) + architecture/reference/security/ + docker-compose.yml + ADR-027 | knowledge/claims/, ORGANIZATION.md, simulation/ |
| **Security Architect** | This file + WC + architecture/reference/security/ + ADR-003, ADR-007, ADR-008, ADR-014 full + [ADR-INDEX.md](ADR-INDEX.md) | knowledge/claims/, simulation/, src/ |
| **Business Architect** | This file + WC + knowledge/claims/ (all) + knowledge/index.md + knowledge/confidence-register.md + GENESIS Part 01 | simulation/ (cases), architecture/, src/, ORGANIZATION.md in full |
| **Constitutional Analyst** | This file + WC + CONSTITUTION.md + GENESIS.md + simulation/PRECEDENTS.md + simulation/ (cases) + RED_TEAM.md | architecture/, src/, knowledge/ (you produce it) |
| **Product Owner** | This file + INSTITUTIONAL_BACKLOG.md + PROJECT_STATE.md + ORGANIZATION.md (office charters) | architecture/, src/, knowledge/claims/, simulation/ |
| **Platform Delivery Tracker** | This file + INSTITUTIONAL_BACKLOG.md + PROJECT_STATE.md + GitHub Issues | Everything else — read-only |
| **WAOOAW AI Agent — Platform IT Expert** | This file + platform-it-expert-agent.md + C-065.md + C-066.md + C-067.md + [ADR-INDEX.md](ADR-INDEX.md) + .github/workflows/ | knowledge/claims/ (except C-059/C-065/C-066/C-067), simulation/, legal/ |
| **WAOOAW AI Agent — Legal** | This file + legal/ (all 5 documents) + knowledge/claims/C-060.md + C-061.md + C-063.md | architecture/, src/, simulation/, agent specs |
| **Program Management Office** | This file + pmo/PROGRAM-PLAN.md + constitution/PROJECT_STATE.md + constitution/INSTITUTIONAL_BACKLOG.md + work-contracts/ (active WCs only) + security/FOUNDER-ACTIONS.md | architecture/ (detailed), src/, knowledge/claims/, simulation/, constitution/CONSTITUTION.md full |
| **Operations Management / Customer Success** | This file + standards/INCIDENT-MANAGEMENT-POLICY.md + standards/CHANGE-MANAGEMENT-POLICY.md + standards/RELEASE-MANAGEMENT-POLICY.md + pmo/PROGRAM-PLAN.md §6 (SLA/OLA) + constitution/PROJECT_STATE.md | architecture/, src/, knowledge/claims/, simulation/ — read operational artefacts only |

---

## Key File Map (where things live)

```
Architecture
  Context / Containers / Domain model   architecture/reference/{context,containers,domain-model}.md
  Component specs (4 services)          architecture/reference/components/{service-name}.md
  Agent specs (customer + internal)     architecture/reference/agents/{agent-name}-agent.md
  API contracts (REST)                  architecture/reference/api-specs/{service}.openapi.yaml
  API contract (gRPC)                   architecture/reference/proto/constitutional_service.proto
  Data architecture                     architecture/reference/data/{ledger-design,evidence-schema}.md
  Security architecture                 architecture/reference/security/{security-architecture,threat-model}.md
  Prompt library                        architecture/reference/prompts/
  Skill dependency register             architecture/reference/skill-dependency-register.md
  Component quick-reference             architecture/reference/COMPONENT-QUICK-REF.md
  ADR quick reference                   adr/ADR-INDEX.md  ← read this before individual ADRs
  Individual ADRs                       adr/ADR-NNN-*.md  (ADR-001 to ADR-029)
  Engineering standards                 architecture/reference/engineering-standards.md

UX & Brand
  Constitutional UX Vocabulary (spec)   architecture/reference/ux/constitutional-ux-vocabulary.md
  Suresh portal walkthrough             architecture/reference/ux/suresh-portal-walkthrough.md
  Brand assets (logos, preview)         architecture/reference/ux/brand/
  Logo dark-bg conversion script        scripts/convert-logos-dark.py

Legal
  Privacy Policy (DPDPA 2023)           legal/privacy-policy.md
  Terms of Service                      legal/terms-of-service.md
  Refund Policy                         legal/refund-policy.md
  Cookie Policy                         legal/cookie-policy.md
  Grievance Policy                      legal/grievance-policy.md

Constitutional
  Backlog + gate status                 constitution/INSTITUTIONAL_BACKLOG.md
  Session state                         constitution/PROJECT_STATE.md  ← read for full briefing
  Bootstrap protocol                    constitution/BOOTSTRAP.md
  Office charters + C-064 naming        constitution/ORGANIZATION.md
  Quick-start cards (per office)        .github/agent-context/office-{name}.md

Knowledge
  All constitutional claims (75)        knowledge/claims/C-001.md through C-075.md
  Claim index + summary                 knowledge/index.md
  Architectural drivers (AD-001–028)    knowledge/architectural-drivers.md
  Design principles (DP-001–025)        knowledge/design-principles.md
  Confidence register                   knowledge/confidence-register.md
  Business capabilities                 knowledge/business-capabilities.md

Steward Interface
  Steward web entry point (C-068)       ops.waooaw.ai (hidden URL — Google OAuth, 3 accounts)
  Steward agent spec                    architecture/reference/agents/steward-assistant-agent.md
  Steward interface design              architecture/reference/steward-interface.md

Operations & Standards
  PMO program plan                      pmo/PROGRAM-PLAN.md
  Incident Management Policy            standards/INCIDENT-MANAGEMENT-POLICY.md  (pending — ITSM)
  Change Management Policy              standards/CHANGE-MANAGEMENT-POLICY.md    (pending — ITSM)
  Release Management Policy             standards/RELEASE-MANAGEMENT-POLICY.md   (pending — ITSM)

Implementation (src/ not yet built — IB-009 awaiting authorization)
  Source code (coming)                  src/{service-name}/
  CCT framework                         tests/constitutional/README.md + tests/constitutional/{service}/
  Infrastructure init                   infrastructure/postgres/init/*.sql
  Keycloak realm                        infrastructure/keycloak/
  Container Apps scaling                infrastructure/container-apps/scaling-rules.yaml
  Dev environment                       docker-compose.yml + .env.example
  Blue-green deployment script          scripts/blue-green-deploy.sh
  Dev JWT script                        scripts/get-dev-token.sh

GitHub Operations
  Issue templates                       .github/ISSUE_TEMPLATE/
  PR template                           .github/pull_request_template.md
  CI pipeline                           .github/workflows/ci.yaml  (C-059 gate + CodeQL + OWASP)
  Promote + deploy                      .github/workflows/promote.yaml  (blue-green + cost gate)
  Emergency halt check                  .github/workflows/emergency-halt-check.yaml  (C-001 for pipelines)
  Post-deploy verification              .github/workflows/post-deploy-verify.yaml  (C-065 + auto-rollback)
  CODEOWNERS                            .github/CODEOWNERS  (all paths require @dlai-sd)

Security
  Founder action list                   security/FOUNDER-ACTIONS.md  (FA-001 to FA-021+)
  Security headers                      security/SECURITY-HEADERS.md
```

---

## The Three Facts Every Agent Must Know

**Fact 1 — Constitutional Engine is gRPC only, never exposed externally.**
All services call CE via gRPC. CE does not expose REST. CE is internal-only.

**Fact 2 — Evidence First is not optional.**
Every governance event must call CE.RecordEvidence() and receive OK before the calling service returns success. CCT-EF-01 and CCT-EF-02 verify this in every environment.

**Fact 3 — tenant_id comes from JWT, never from request body.**
The JWT middleware extracts tenant_id and stores it in HttpContext. The EF Core interceptor calls `SET LOCAL app.tenant_id` before every query. PostgreSQL RLS enforces isolation from there. An agent that accepts tenant_id from a request body has created a security vulnerability.

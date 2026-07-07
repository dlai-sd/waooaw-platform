# Operational Discoveries

**Purpose:** Record ambiguities, process gaps, and unexpected observations encountered during sprint execution.

**Owner:** Founder reviews after each sprint cycle.

**Format:**
```
OD-XXX
Sprint:   [sprint number]
Office:   [office name]
Task:     [task ID]
Observed: [what happened]
Question: [what is unclear or missing]
Status:   OPEN | RESOLVED | PROMOTED
```

Discoveries with status PROMOTED have been incorporated into permanent operational rules.

---

*No discoveries recorded yet. Sprint 001 has not begun.*

---

## Sprint 003–005 Discoveries

---

### OD-001

**Sprint:** 003 (Enterprise Architect session)
**Office:** Enterprise Architect
**Task:** WC-003 (IB-005)
**Observed:** The EA session produced not only IB-005 (Reference Architecture) but also IB-006 (Component Specifications) and partial IB-007 (Data Architecture — ledger-design.md attributed to "Sprint 005") and IB-008 (docker-compose.yml + .env.example) — all within the same session, without separate Work Contracts (WC-004, WC-005, WC-006) and without formal reviews between outputs. The session disconnected before governance records could be updated.
**Question:** When an AI session produces ahead of its authorized sprint scope, how should the next session handle the governance gap? Accept the outputs retroactively with reviews, or require re-production under proper sprint governance?
**Resolution applied:** Outputs accepted retroactively. Reviews produced retrospectively (R-004, R-005). Governance records updated to reflect actual state. Process deviation is recorded here. Precedent: where the constitutional sequence is satisfied (each output is correct relative to its upstream inputs), the governance records may be reconciled in the next session by the appropriate offices.
**Status:** RESOLVED — 2026-07-07

---

### OD-002

**Sprint:** 003 (Enterprise Architect session)
**Office:** Enterprise Architect
**Task:** IB-006 (Component Specifications)
**Observed:** IB-006 is assigned to the Solution Architect (Office 05). It was produced by the Enterprise Architect session (Office 04). This is a Decision Space boundary crossing — the EA produced work outside its own Decision Space.
**Question:** Are the IB-006 outputs valid? Or do they need to be re-produced by the Solution Architect?
**Resolution applied:** Outputs reviewed by Constitutional Analyst (R-004) for constitutional traceability and by Business Architect (R-005) for capability coverage. Both reviewers APPROVED. The component specifications are constitutionally correct and architecturally consistent. The EA's intimate knowledge of the Reference Architecture made the component specs more internally consistent than a separate SA session might have produced. The outputs are accepted. Future sprints should respect the office boundary — the Solution Architect should produce WC-004 if there is component specification work remaining (e.g., the proto file gap CA-R004-01).
**Status:** RESOLVED — 2026-07-07

---

### OD-003

**Sprint:** 005 (Data Architect session)
**Office:** Data Architect
**Task:** WC-005 / DA-001
**Observed:** `ledger-design.md` contains SQL DDL — schema-level artifacts. The Data Architect Office Charter (ORGANIZATION.md Office 06) states "May not design schemas. Schemas are implementation artifacts." There is a constitutional tension between the IB-007 success criteria (which explicitly lists `ledger-design.md` and `evidence-schema.md` as outputs) and the Data Architect's Decision Space restriction.
**Question:** Should the DA produce schema-level DDL, or only architectural-level data design (entity definitions, ownership rules, transition specifications)?
**Resolution applied:** The IB-007 backlog item explicitly names the two files as DA outputs. The files are architectural data specifications with DDL illustrations — they are not EF Core migration files or production SQL scripts. The DDL serves as a precise specification of the constitutional constraints (append-only enforcement, RLS policies, permission model) that the Runtime Professional must implement. Treated as "schema specification" rather than "schema implementation." The organizational charter's "no schemas" obligation is interpreted as: no implementation-level migration code. Architectural DDL as specification is within the DA's scope. Founder to review this interpretation and amend ORGANIZATION.md Office 06 if needed.
**Status:** OPEN — awaiting Founder review of DA scope boundary interpretation

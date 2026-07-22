# AGENTS.md — src/ Implementation Context
# FinOps Pattern 2: Nested AGENTS.md for scoped context (directory-level charter)
# Read by GitHub Copilot when working inside src/ directory or any subdirectory.
# constitutional_basis: C-059 (Traceability), C-065 (SDLC), C-073 (Annotations), C-076 (Coverage)

## Your Role Here
You are WAOOAW AI Agent — Platform IT Expert.
You are implementing platform services under constitutional governance.

## Do NOT Read (reduces token cost)
- constitution/CONSTITUTION.md or GENESIS.md (Class 1 — immutable, not implementation context)
- constitution/ORGANIZATION.md (880 lines — use .github/agent-context/ office files instead)
- simulation/, reviews/, blockers/, pmo/, legal/ (not relevant to src/ work)
- adr/ADR-001.md through ADR-029.md individually (use adr/ADR-INDEX.md — 29 lines total)

## Read Instead (minimal effective context)
1. constitution/AGENT-ENTRY.md — current state, gate, authorized claims
2. adr/ADR-INDEX.md — all 29 ADRs summarized
3. sprint-context/index.json — CURRENT TASK ONLY: spec files + relevant claims

## Constitutional Rules for All src/ Code

### Every file header (C-059 + C-073):
```python
# Implements: architecture/reference/components/{service}.md §{section}
# Constitutional basis: C-059 (Implementation Traceability)
# ib_item: IB-009
```

### Coverage obligation (C-076):
- Every new function/method MUST have at least one unit test
- Service-level coverage must stay ≥90% (all languages)
- Run `pytest --cov --cov-fail-under=90` before opening any PR

### No unapproved dependencies (C-032):
- Do not add packages not in approved architecture/reference specs
- If a gap requires a new dependency → STOP → raise Constitutional Blocker

### Emergency Stop is sacred (C-001, C-024):
- Any code touching Emergency Stop path must maintain ≤250ms P99
- No blocking I/O on Emergency Stop code path — ever

## Service Subdirectories
Each subdirectory has its own AGENTS.md with service-specific context.
Load it; do not reload this file again for service-specific work.

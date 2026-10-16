# R-148 - Enterprise Architecture Review

## Review Control

| Field | Value |
|---|---|
| Pull request | #520 |
| Office | Enterprise Architect (INST-005) |
| Initial reviewed head | `93ba109fae10b674ee8088622a521d187645767f` |
| Initial disposition | `CHANGES_REQUIRED` |
| Re-review candidate | Work Component `1.1.0-candidate.1` |
| Final disposition | `PENDING SAME-OFFICE RE-REVIEW` |

## Scope

Review of the Demo/UAT persistent-state lifecycle architecture and Platform IT Expert Work Component
for enterprise coherence, ADR compliance, reversibility and institutional authority boundaries.

## Initial Findings And Repair Disposition

| Finding | Required correction | Candidate repair |
|---|---|---|
| ADR-010 reversibility was asserted but not executable | Pin provider escape/exit contracts for Flexible Server, ACA/PgBouncer, Key Vault, private DNS/networking, Monitor and Terraform state | Work Component Section 9.3 adds a dependency-by-dependency reversibility matrix, proof, owner and stop condition |
| Entra-first bootstrap left the password transition ambiguous | Define exact two-plan sequence and failure gates | Section 7.2 requires Entra-only Plan A, bounded bootstrap transaction, reviewed Plan B compatibility enablement and bootstrap-access removal |
| PST-WC00-14 did not separate authorship, acceptance and evidence | Add accountable owner, acceptance authority and independent evidence owner | Section 17 adds all three columns and states that author evidence cannot substitute for acceptance or independent verification |

## Constitutional Boundaries

- FA-055 accepts the architecture but does not authorize implementation, provider mutation,
  deployment, Production action, approval or merge.
- ADR-010 exits are separately authorized migrations, never automatic fallbacks.
- The Founder retains acceptance, provider-action and merge authority where the Work Component says
  so.

## Re-review Requirement

The Enterprise Architect must verify that every initial finding is closed without introducing a
new service, provider or unapproved institutional authority. Only that same-office re-review may
replace the pending final disposition.

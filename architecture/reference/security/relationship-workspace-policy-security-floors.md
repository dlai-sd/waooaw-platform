# GOAL-005 WC-034 F4 Amendment 5 Order 1 - Security Policy Floors (INST-007)

## G-10 Contribution Attestation

| Attestation field | Value |
|---|---|
| institution_id | INST-007 |
| goal_id | GOAL-005 |
| record_id | CR-GOAL-005-INST-007-06 |
| record_type | Contribution Record |
| produced_at | 2026-08-11T01:29:30+00:00 |
| authorization_id | GOA-GOAL-005-INST-007-06 |
| acceptance_id | ACC-GOAL-005-INST-007-06 |
| acceptance_timestamp | 2026-08-11T01:27:41+00:00 |
| contribution_scope | Define non-weakenable assurance, acknowledgement, export, privacy, authority, lifecycle, and degraded-state floors for each policy option in F4-POL-01 through F4-POL-06 |
| decision_boundary | Security-floor analysis only. No policy selection. |

## Scope And Grounding

This security-floor contribution is grounded only in:

- accepted F4 security contract C1-C5 in CR-GOAL-005-INST-007-05;
- ADR-046 accepted workload identity and service authentication boundary;
- Product policy option table in CR-GOAL-005-INST-011-07;
- GOAL-005 execution plan Amendment 5, including Order 1 GOA and acceptance records;
- R-068 (CR-GOAL-005-INST-002-09) readiness conditions;
- LR-GOAL-005-INST-007-01 lineage requirement for this Order 1 contribution.

This record does not invent or select policy outcomes. It does not introduce new time windows, status codes, retention durations, technical mechanisms, or Founder ownership of technical design.

## Non-Weakenable Floors Across All Six Policies

1. Assurance and typed acknowledgement floors from C1-C5 are minimums and cannot be weakened.
2. Export and privacy controls are fail-closed when sensitivity, recipient, purpose, completeness, or redaction authority is unresolved.
3. Authenticated internal-owner command safeguards must preserve exact caller identity, audience, delegated purpose, and relationship-bound authorization.
4. Authority and lifecycle actions remain separately governed; ordinary approval cannot silently grant or expand authority.
5. Stale, unknown, partial, unavailable, or unresolved owner state cannot be presented as completed success.
6. Anti-enumeration is mandatory before authorization; inaccessible and non-existent remain privacy-indistinguishable.
7. Minimisation applies to logs, metrics, traces, URLs, browser state, and public error surfaces.
8. Customer rights and Emergency Stop remain independent and preserved.

## Policy Floors And Prohibited Options

### F4-POL-01 - Material acknowledgement classes

- accepted floor:
  - no materially consequential approval or rejection may execute without the required typed acknowledgement floor for that consequence class;
  - acknowledgement remains single-consequence, bound to actor, relationship, purpose, and current authoritative versions;
  - a missing materiality decision keeps affected commands blocked.
- prohibited options:
  - enabling materially consequential approval/rejection without an approved acknowledgement policy;
  - reusing generic approval, stale acknowledgement, or unchecked UI confirmation as equivalent typed acknowledgement;
  - exposing authorization details as existence or role oracles.

### F4-POL-02 - Evidence export self-service boundaries

- accepted floor:
  - ordinary authorized evidence inspection rights remain preserved;
  - export requires authorized recipient, purpose, sensitivity handling, completeness disclosure, and approved redaction behavior;
  - unresolved export policy remains unavailable with privacy-safe handling.
- prohibited options:
  - treating possession of a link or identifier as export authority;
  - disclosing recipient or sensitivity details through denial behavior;
  - permitting export when recipient/purpose/redaction/completeness controls are unresolved.

### F4-POL-03 - Allowance threshold and budget ceiling treatment

- accepted floor:
  - consequential commercial commands require exact owner route, actor, and purpose binding;
  - no automatic paid addition is permitted;
  - BP must not recompute WBE truth and must preserve authoritative owner meaning;
  - unresolved commercial continuation paths return privacy-safe denial and remain fail-closed;
  - Emergency Stop remains independent of allowance and budget treatment.
- prohibited options:
  - auto-enabling purchase/increase/continuation on threshold or ceiling contact;
  - replacing owner-authoritative commercial state with BP-derived approximations;
  - using degraded commercial state to claim success for unresolved consequential work.

### F4-POL-04 - Customer self-service authority changes

- accepted floor:
  - authority grant, expansion, restoration, narrowing, suspension, and revocation remain distinct authority-governed commands;
  - required assurance and typed acknowledgement floors apply where C1-C5 classify them;
  - if authority ownership, consequence, or version is unresolved, the change is denied fail-closed.
- prohibited options:
  - inferring authority expansion from tenant ownership, prior approval, or relationship membership;
  - allowing self-service authority expansion without explicit owner-approved policy;
  - collapsing authority change into ordinary approval flow.

### F4-POL-05 - Lifecycle policy (pause/resume/renew/terminate)

- accepted floor:
  - lifecycle commands preserve distinct consequence treatment for pause/resume/renew/terminate;
  - required assurance and typed acknowledgement floors apply per C1-C5 for consequential lifecycle actions;
  - unresolved lifecycle-commercial-evidence coupling remains blocked or unavailable;
  - Emergency Stop remains independently reachable regardless of lifecycle command availability.
- prohibited options:
  - presenting unresolved lifecycle consequences as executable customer actions;
  - allowing lifecycle success claims when owner state is stale, unknown, partial, or unavailable;
  - coupling Stop availability to lifecycle, billing, or export completion.

### F4-POL-06 - Permissible action in stale/unknown/partial/unavailable state

- accepted floor:
  - only still-authoritative facts may be presented as actionable context;
  - affected consequential commands are withheld while owner state is unresolved;
  - unknown and partial outcomes remain explicitly unresolved until owner-authoritative reconciliation;
  - anti-fabrication and privacy-safe denial remain mandatory.
- prohibited options:
  - treating request acceptance, transport success, or technical completion as business success;
  - allowing consequential commands to proceed on unresolved owner state;
  - leaking owner availability, tenant, relationship, or private-route details through degraded-state responses.

## Gate And Authority Statement

FA-036 is satisfied for current-session implementation authorization status, but this contribution does not authorize implementation start, policy selection, G-F4-10 closure, G-F4-12 closure, or G-F4-13 deployment. Amendment 5 order and policy gates remain in force exactly as recorded.

## Learning Record (GEOM G-05)

| field | value |
|---|---|
| institution_id | INST-007 |
| goal_id | GOAL-005 |
| record_id | LR-GOAL-005-INST-007-01 |
| record_type | Learning Record |
| improvement_signal | Security-floor-first framing across all six Founder policy IDs prevents implicit defaults and blocks weakened assurance/export/degraded-state behavior before policy decisions are recorded. |
| constitutional_discovery | no |
| evolution_triggered | no |
| produced_at | 2026-08-11T01:29:30+00:00 |

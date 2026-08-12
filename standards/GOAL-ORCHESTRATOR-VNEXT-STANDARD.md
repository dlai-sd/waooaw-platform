# Goal Orchestrator Operating Model vNext Standard

**Owner:** Goal Orchestrator (INST-013)
**Reviewer:** Constitutional Analyst (INST-002)
**Authority:** GEOM Stage G-4 Materiality and Contribution Envelope rule
**Status:** PROPOSED BY WC-070; inactive until independent review and Founder ratification
**Version:** 1.1.0-proposed

## 1. Purpose And Invariants

This standard converts the ratified vNext materiality model into deterministic routing controls.
It reduces repeated context and review while preserving required decisions, evidence, owner
accountability, independence, and Founder control.

The following invariants override all cost or speed targets:

- Uncertainty classifies upward.
- Missing evidence remains missing; budget exhaustion never means completion.
- INST-013 coordinates work but does not decide another Institution's Decision Space.
- No reuse decision changes producer attribution, approval status, or immutable evidence.
- No model route removes a required owner, protected verdict, or Founder-reserved decision.
- No primary executor may review or approve its own material contribution.
- Every repair, classification, reuse decision, escalation, and budget transition is auditable.

## 2. Contribution Necessity Gate

Before creating a new institutional context, INST-013 evaluates the requested outcome in order:

| Outcome | Required finding | Routing |
|---|---|---|
| `REUSE` | Approved evidence already resolves the decision and passes the Contribution Reuse Test | Cite the pinned evidence; create no new contributor context |
| `M1_CONTINUE` | The same accountable owner can finish within the accepted envelope and active Participation Window without changing material meaning | Continue in the owner context; create no new GOA or institutional context |
| `M2_CONTRIBUTE` | A new material decision, changed owner Decision Space, changed boundary, or failed reuse test requires an owner contribution | Create one complete Contribution Envelope and one owner context |
| `M3_DECIDE` | A protected verdict, constitutional interpretation, authority change, immutable evidence decision, production action, or Founder-reserved action is required | Route to the protected authority; work remains stopped pending verdict |

**Binding rule:** No new material decision, no new agent context. Absence of a prior record is not
by itself proof that a new material decision is required; INST-013 must identify the unresolved
decision and its owning Decision Space.

## 3. Contribution Reuse Test

Reuse is valid only when one record contains all fields below and every check passes:

| Field | Requirement |
|---|---|
| `reuse_record_id` | Unique auditable record ID |
| `source_record_id` | Prior approved Contribution, Review, or Clearance Record |
| `source_commit` and `sha256` | Immutable source pin |
| `producer` and `decision_owner` | Original attribution and owning Decision Space |
| `approved_scope` | Scope and acceptance meaning actually reviewed |
| `target_scope` | Current decision the evidence is proposed to resolve |
| `version_compatibility` | Relevant constitutional, policy, architecture, data, security, and package versions |
| `assumptions` | Material assumptions on which the prior result depends |
| `changed_facts` | Facts changed since approval, including explicit `none found` evidence |
| `applicability` | `APPLICABLE`, `PARTIALLY_APPLICABLE`, or `NOT_APPLICABLE` with rationale |
| `validated_by` and `validated_at` | Accountable classifier and timestamp |

`PARTIALLY_APPLICABLE` reuses only explicitly mapped conclusions. All uncovered decisions route
separately. Missing hash, owner, approval, assumption, version, or changed-fact evidence makes the
record `NOT_APPLICABLE`; uncertainty cannot be treated as reuse.

## 4. Materiality Challenge

Every M0 or M1 classification must answer `no` to each challenge below:

1. Does this change policy, behavior, architecture, data/security rules, acceptance meaning,
   dependency assumptions, package boundaries, constitutional weight, authority, or risk?
2. Does it require judgment reserved to another Decision Space?
3. Does it alter approved or immutable evidence, producer attribution, or an independent verdict?
4. Is the accountable owner, accepted envelope, package baseline, or Participation Window changed?
5. Could a reasonable reviewer reach a different outcome from facts not already fixed by the
   accepted package?

Any `yes` is at least M2 unless GEOM explicitly classifies it as M3. An unsupported or ambiguous
answer classifies upward. INST-002 spot-checks at least 25 percent of M0/M1 records at Goal closure,
weighted toward high-impact avoided contexts.

## 5. Completeness Ledger

Every Work Contract or Work Component has one machine-checkable ledger before execution begins.
Each row contains:

| Field | Allowed value or evidence |
|---|---|
| `obligation_id` | Stable requirement, task, acceptance scenario, evidence item, or gate ID |
| `owner` | One accountable Institution or protected authority |
| `materiality` | M0, M1, M2, or M3 |
| `required_evidence` | Record type and minimum content |
| `dependencies` | Direct prerequisite IDs |
| `status` | `PENDING`, `SATISFIED`, `BLOCKED`, `NOT_APPLICABLE` |
| `evidence_ref` | Pinned evidence ID/hash when satisfied |
| `validation` | Deterministic check or independent verdict required |

Completion is valid only when every row is `SATISFIED` or has an independently defensible
`NOT_APPLICABLE` determination, all blocking dependencies are resolved, and required protected
verdicts exist. A budget transition cannot modify obligation status.

## 6. Dependency Impact Report

Every M2 or M3 change, and every repair that escapes its accepted envelope, records:

- changed records and hashes;
- changed decisions and assumptions;
- direct dependants;
- indirect dependants reached through those direct dependencies;
- unaffected dependants with rationale;
- required owner re-contribution or re-review;
- baseline and delta hashes; and
- unresolved or conflicting impacts.

Delta review is prohibited without this report. An initial baseline receives complete required
review. Later review may examine only a delta when the baseline is approved and hash-pinned, the
dependency report is complete, and no constitutional, authority, package-boundary, or acceptance
change invalidates the baseline.

## 7. Model And Validation Router

Model choice follows the cheapest capable route, never the cheapest available route:

| Work | Default route | Escalation |
|---|---|---|
| M0 transformation or validation | Deterministic parser, schema, linter, diff, hash, or test; no LLM when a deterministic tool can decide | Tool failure or semantic ambiguity routes upward |
| Straightforward M1 continuation | Smallest model demonstrated capable for the artifact type, one initial call and one bounded repair loop | Failed validation, contradictory evidence, or second repair routes to a stronger model/owner |
| Bounded M2 contribution | Capable non-frontier model only when the Decision Space, inputs, schema, and acceptance are explicit | Ambiguity, cross-domain conflict, high consequence, or failed repair routes to frontier capability |
| Ambiguous M2 or any M3 reasoning | Frontier-capable model and required human/institutional protected authority | No model substitutes for the authority's verdict |

All generated outputs pass deterministic checks before review dispatch. Model output never
self-attests capability. INST-013 records model class, reason, validation result, repair count,
and escalation result without exposing secrets or private chain-of-thought.

## 8. Budget And Stop Semantics

Each Execution Plan declares context, handoff, token/cost, elapsed-time, and repair-loop budgets.
Targets are planning controls, not constitutional completion criteria.

| State | Meaning | Required action |
|---|---|---|
| `WITHIN_BUDGET` | Actual use remains below the consolidation threshold | Continue under the accepted envelope |
| `STOP_AND_CONSOLIDATE` | Actual or forecast use reaches 80 percent, repeated context appears, or repair loops approach their limit | Stop dispatch; deduplicate evidence, reuse valid baselines, combine remaining owner questions, and recalculate |
| `REPLAN_REQUIRED` | Forecast exceeds 100 percent, handoff reserve is consumed, validation repeatedly fails, or package assumptions changed | Stop new contexts; amend scope/budget/routing through the proper authority |

No budget state waives an obligation or authorizes completion. A Founder decision is required
before exceeding a Founder-set monetary ceiling. Sensitive provider prices may remain outside the
public record, but thresholds, actual-versus-budget status, and decision evidence remain auditable.

## 9. Execution Record

INST-013 maintains one compact execution record per Work Component containing:

- accepted Contribution Envelope and accountable executor;
- Contribution Necessity Gate decisions and reuse records;
- Completeness Ledger and Dependency Impact Reports;
- baseline/delta hashes and deterministic validation results;
- model routes, escalations, and bounded repairs;
- budget state and actual versus planned contexts/handoffs/cost band;
- protected verdicts and unresolved blockers; and
- closure metrics: elapsed time, rework causes, escaped defects, and lessons.

Stable constitutional and office context is version-pinned and cached by reference. A context
cache hit is valid only when its source versions and hashes still match the current package.

## 10. Initial Adoption And Review

The first use on a specification Work Contract and the first use on an implementation Work
Contract receive full independent review. After an approved baseline exists, incremental review
may be used under Section 6. CA sampling prioritizes avoided high-risk contexts, repeated reuse,
budget-triggered consolidation, and cheap-model escalations. Any quality regression suspends the
affected optimization until reviewed and corrected.
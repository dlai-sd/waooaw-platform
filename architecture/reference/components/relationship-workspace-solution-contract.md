# WC-034 F4 Relationship Workspace Solution Contract

## Attestation

| Field | Value |
|---|---|
| Institution | INST-005 — Solution Architect |
| Goal | GOAL-005 |
| Work Contract | WC-034 F4 |
| Contribution ID | CR-GOAL-005-INST-005-04 |
| Date | 2026-08-10 |
| Status | COMPLETE |
| Contribution boundary | Solution-level BP public and BP-internal contracts, interaction sequencing, versioning, errors, idempotency, reconciliation, generated-client boundary, acceptance trace, and gate evidence; no OpenAPI modification, data schema, implementation, deployment, provider activation, or F5-F8 decision |

## Post-Authorization Re-attestation

| Attestation field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-005-05 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T13:44:57+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-005-03 |
| `acceptance_record` | ACC-GOAL-005-INST-005-03 |
| Re-attests | CR-GOAL-005-INST-005-04 candidate solution contract |
| Gate contribution | G-F4-03 — Solution API contracts |
| Order 3 decision | RE-ATTESTED — G-F4-03 contribution evidence SATISFIED within INST-005 Decision Space |
| Authority boundary | Solution contracts only; no DMA evidence, G-F4-09, canonical OpenAPI edit, generated client, source, test, migration, implementation, deployment, F5-F8, self-review, or integrated-review authority |

After `GOA-GOAL-005-INST-005-03` was issued and `ACC-GOAL-005-INST-005-03` was recorded at `2026-08-10T13:41:01+00:00`, INST-005 independently re-opened this candidate against Amendment 3 `GEP-GOAL-005-INST-013-04`, R-062 / `CR-GOAL-005-INST-002-05`, the published Order 1 records `CR-GOAL-005-INST-003-04` and `CR-GOAL-005-INST-011-05`, and the published Order 2 records `CR-GOAL-005-INST-004-08`, `CR-GOAL-005-INST-006-04`, and `CR-GOAL-005-INST-007-05`. Repository search found no Contribution Record identifier collision for `CR-GOAL-005-INST-005-05`.

INST-005 adopts Sections 1-14 without substantive amendment and confirms that they satisfy the Amendment 3 evidence specification for G-F4-03: public and internal contract families; BP, WBE, PR, domain-adapter, and CE ownership-preserving sequences; generated-client boundaries; versions and freshness; actor, tenant, and relationship authorization; idempotency and expected-version controls; privacy-safe errors; and deterministic partial, unknown, and reconciliation semantics. Historical gate-state statements in the adopted candidate describe its pre-authorization state; this re-attestation is the controlling post-acceptance contribution decision for G-F4-03 only.

This record does not close G-F4-07 or G-F4-08; their separate logical owner acceptances are `CR-GOAL-005-INST-005-06` and `CR-GOAL-005-INST-005-07`. It does not supply DMA domain evidence or close G-F4-09, specify G-F4-10 compatibility evidence, perform G-F4-11 review, or resolve any Founder policy. Fresh INST-004 review remains required before the Order 3 package can be treated as independently accepted.

## 1. Purpose And Ownership

This contract decomposes the approved F4 business meanings and Enterprise Architecture ownership into implementable service contracts. It introduces no deployable component and does not alter the reference architecture.

Business Platform (BP) remains the only ordinary public facade. It owns the relationship-governance projection, customer command outcome, stable **Needs your attention** order, public reconciliation state, and customer-safe error contract. The web application reads and commands only through the generated BP public client.

WAOOAW Billing Engine (WBE) remains authoritative for allowance and billing actuals, remaining allowance, ceilings, forecasts, threshold states, assumptions, validity, pacing choices, and commercial consequences. Professional Runtime (PR) remains authoritative for internal professional execution facts. Professional/domain adapters remain authoritative for approved domain outcome meaning. Constitutional Engine (CE) remains authoritative for constitutional validation, authority licensing, and constitutional evidence. BP composes these truths without recalculating, ranking, or transferring their ownership.

### 1.1 Non-Negotiable Boundaries

1. Every public F4 request terminates at BP, except the existing dedicated Emergency Stop transport, which F4 does not change.
2. The browser must not call PR, WBE, CE, a domain adapter, the Constitutional Audit Ledger, the Customer Evidence Ledger, or any billing ledger.
3. The browser must not rank, score, filter into authority, personalize, aggregate, or secondarily sort **Needs your attention**.
4. BP must not recreate WBE actuals, forecasts, thresholds, pricing, allowance balances, or commercial consequences.
5. PR facts and domain contributions are not customer truth until BP validates and incorporates them into its relationship projection.
6. Capability is not authority; plan is not approval; approval is not scope confirmation; completed work is not a result; forecast is not actual; pending evidence is not recorded evidence.
7. Every operation is bound to the authenticated tenant and one authorized Employment Relationship. `tenantId` is never a public path, query, header supplied by web code, or request field.
8. An absent or unapproved owner contract produces an explicit `UNAVAILABLE` or `BLOCKED` capability. No layer may compensate with private calls, local defaults, mock success, or technical telemetry.

## 2. Contract Families And Proposed Public Paths

The following paths and schema names are the normative Solution Architecture proposal for a later Business Platform OpenAPI update. They are not added to OpenAPI by this contribution.

All paths use the existing relationship root:

`/api/v1/employment/relationships/{relationshipId}/workspace`

The aggregate read is the initial-load and full-reconciliation contract. Family reads allow independent refresh after a source-specific stale or unavailable outcome without forcing unrelated sources to fail.

| Operation ID | Method and proposed path | Response schema | Contract purpose |
|---|---|---|---|
| `getRelationshipWorkspace` | `GET /api/v1/employment/relationships/{relationshipId}/workspace` | `RelationshipWorkspaceV1` | Return one complete authorized relationship context and all selected F4 families as a consistency-marked snapshot |
| `getRelationshipWorkspaceChanges` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/changes?afterCursor=` | `RelationshipWorkspaceChangePageV1` | Reconcile BP-confirmed changes after a prior opaque workspace cursor |
| `getRelationshipPlan` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/plan` | `RelationshipPlanV1` | Read Plan, goals, Priority Work, dependencies, timing, review points, and authoritative commands |
| `getRelationshipAttention` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/attention` | `RelationshipAttentionPageV1` | Read the complete qualifying attention list in exact BP-owned order and stable tie sequence |
| `getRelationshipWork` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/work` | `RelationshipWorkPageV1` | Read work, deliverables, schedules, approvals, effects, evidence states, and available commands |
| `getRelationshipResults` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/results` | `RelationshipResultsV1` | Read BP-owned business-outcome projection with approved domain meaning and attribution limits |
| `getRelationshipUsageBudget` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/usage-budget` | `RelationshipUsageBudgetV1` | Relay WBE-owned actual, allowance, ceiling, forecast, threshold, assumption, validity, and consequence meanings |
| `getRelationshipRightsControls` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/rights-controls` | `RelationshipRightsControlsV1` | Read current scope, authority, lifecycle, rights, evidence access, assurance needs, and Stop reachability |
| `submitRelationshipCommand` | `POST /api/v1/employment/relationships/{relationshipId}/workspace/commands` | `RelationshipCommandReceiptV1` | Submit or replay one typed relationship-governance command |
| `getRelationshipCommand` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/commands/{commandId}` | `RelationshipCommandOutcomeV1` | Reconcile a pending, partial, or unknown command to an authoritative outcome |
| `listRelationshipEvidence` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/evidence` | `RelationshipEvidencePageV1` | Read BP-authorized evidence summaries without exposing a ledger |
| `getRelationshipEvidence` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/evidence/{evidenceId}` | `RelationshipEvidenceDetailV1` | Read one permitted evidence projection and its completeness/limitation state |
| `requestRelationshipEvidenceExport` | `POST /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports` | `RelationshipEvidenceExportReceiptV1` | Request or replay an assurance-checked evidence export |
| `getRelationshipEvidenceExport` | `GET /api/v1/employment/relationships/{relationshipId}/workspace/evidence-exports/{exportId}` | `RelationshipEvidenceExportOutcomeV1` | Reconcile export preparation and obtain a time-bounded BP-mediated result when authorized |

No public operation accepts a generic destination URL, service name, ledger query, rank, score, WBE customer identifier, PR execution identifier, CE contract identifier, provider identifier, or raw evidence-store location.

## 3. Public Read Contracts

### 3.1 Common Envelope

Every public F4 read schema includes `schemaVersion`, `relationshipId`, `workspaceVersion`, `authoritativeCursor`, `producedAt`, `lastAuthoritativelyConfirmedAt`, and `currencyState`.

`currencyState` is one of `CURRENT`, `STALE`, `UNKNOWN`, `UNAVAILABLE`, or `BLOCKED`. It includes `validUntil` when known, `reasonCode`, a customer-language `effect`, and an optional accountable `recoveryAction`. `STALE` and `UNKNOWN` data must not authorize a consequential command. `UNAVAILABLE` and `BLOCKED` must not be omitted if omission would imply that no capability or concern exists.

Every family is a `RelationshipWorkspaceSectionV1` with:

- `sectionType`, `sectionVersion`, `currencyState`, and source provenance;
- `items` or the section-specific projection;
- `emptyMeaning` when current and genuinely empty;
- `availableCommands`, each referencing only `submitRelationshipCommand` and a typed command kind;
- `sourceProjectionVersions` naming BP plus any incorporated WBE, PR, domain, authority, lifecycle, or evidence projection version;
- no private URL, internal service name, ledger coordinates, provider telemetry, tokens, or raw technical cost.

The aggregate `RelationshipWorkspaceV1` is a BP-owned composition, not a distributed transaction claim. Its `snapshotState` is `CONSISTENT`, `PARTIAL`, `STALE`, or `UNKNOWN`. Each section independently states its currency and source versions. A current BP section may coexist with an unavailable WBE section; BP must not fail or relabel unrelated truth when partial projection is safe.

### 3.2 Relationship Context

`RelationshipContextV1` contains the professional customer label and identifier, Employment Relationship identifier, lifecycle state, current goal summary/reference, rights/control availability, relationship authority/scope versions, workspace currency, and allowed relationship-switch navigation reference.

Switching relationships always obtains a fresh `getRelationshipWorkspace` response after server authorization. No prior relationship draft, cursor, link, authority, budget, evidence, attention order, selected item, or command availability may be carried into the new context. Public IDs and cursors are opaque and grant no authority.

### 3.3 Plan, Goals, Priority Work, Work, Deliverables, And Results

`RelationshipPlanV1` contains `planId`, plan owner, state, intended effect, timing, dependencies, review point, goals, and Priority Work. `RelationshipGoalV1` names the business outcome, owner, baseline, measure, review period, attribution boundary, state, and valid commands. `RelationshipWorkItemV1` and `RelationshipDeliverableV1` each state owner, current business state, expected or observed effect, evidence status, limitations, and available commands.

`RelationshipResultsV1` contains `BusinessOutcomeResultV1` items. Each item includes the customer-language outcome, baseline, measure, review period, observed value or bounded qualitative assessment, evidence summaries, attribution basis, attribution limitations, uncertainty, accountable domain source, and review commands. `TechnicalMetricV1` may appear only as explicitly labelled supporting diagnosis; it must never occupy the business outcome or achieved-state fields.

All consequential Plan, Goal, Work, Deliverable, Approval, Schedule, and Result items implement `GovernedRelationshipItemV1`:

- `itemId`, `itemType`, `schemaVersion`, `owner`, `state`, `effect`, and `evidenceStatus`;
- `relationshipId`, `itemVersion`, and `sourceSequence`;
- `availableCommands`, or an explicit no-action reason;
- currency, provenance, and limitation fields;
- optional `attentionItemId` only when BP has qualified the item for attention.

### 3.4 Authoritative Needs Your Attention

`RelationshipAttentionPageV1` contains `items`, `authoritativeCursor`, and `nextCursor`. Each `RelationshipAttentionItemV1` contains an opaque `attentionItemId`, `sourceItemReference`, reason, customer consequence, required action or acknowledgement, due meaning, owner, materiality, validity, and typed command references.

Order in the response array is the complete authoritative order for that page. Each item carries an opaque `authoritativeSequence`; it is not a score and must not be displayed as one. Pagination preserves global order. Equal-priority relative order remains stable across snapshot, refresh, reconnect, and device until BP changes it or an item ceases to qualify.

The public contract exposes no rank-writing, reorder, sort, score, priority-weight, dismiss-as-unimportant, or personalization operation. Query parameters for sort/order/filter are prohibited. Web may visually group nothing that changes sequence or apparent authority. Informational updates that do not require a customer response are excluded by BP, not filtered by the browser.

### 3.5 Usage And Budget Relay

`RelationshipUsageBudgetV1` contains WBE-supplied `actuals`, `allowances`, `budget`, `forecast`, `thresholds`, `pacingChoices`, and `commercialConsequences`. Each value includes its customer-understandable unit, period, observed/produced time, validity, WBE projection version, and currency state.

- `UsageActualV1` is observed use, never forecast.
- `AllowanceV1` states allocated, consumed, remaining, renewal meaning, and boundary consequence in customer units.
- `BudgetCeilingV1` states the agreed financial ceiling and current authoritative state; it does not grant work authority.
- `UsageForecastV1` is a range with assumptions, uncertainty, period, and validity; it is never an actual charge.
- `UsageThresholdV1` states the WBE-owned threshold state and typed customer consequence.
- `UsagePacingChoiceV1` is an owner-supplied choice, not a BP optimization.

BP may map internal opaque WBE resource references to relationship-scoped public IDs, but must not recompute a value, convert provider cost into customer allowance, infer a threshold, alter a forecast, or soften a commercial consequence.

### 3.6 Rights, Scope, Authority, Lifecycle, And Evidence

`RelationshipRightsControlsV1` keeps `rights`, `scope`, `authority`, `lifecycle`, `approvalRules`, `boundaryConfirmationRules`, `evidenceAccess`, and `emergencyStop` independently understandable.

`RelationshipScopeV1` and `RelationshipAuthorityV1` carry distinct versions and states. Capability references may explain what the professional can do but never appear as granted authority. `RelationshipLifecycleV1` uses `EVALUATION`, `ACTIVE`, `SUSPENDED`, or `TERMINATED` and includes typed billing, allowance, schedule, evidence, and re-entry consequences supplied by their owners.

`RelationshipEvidenceSummaryV1` and `RelationshipEvidenceDetailV1` expose subject, action/state, accountable producer, period, CE-confirmed evidence status, completeness, sensitivity category, redaction/limitation, dispute/supersession meaning, and permitted actions. They contain BP-mediated content or an opaque BP retrieval reference, never ledger coordinates. `RECORDED` requires authoritative CE confirmation and a confirmed evidence reference. `PENDING`, `FAILED`, `UNKNOWN`, `STALE`, `DISPUTED`, and `UNAVAILABLE` remain distinct.

Emergency Stop remains reachable through the existing dedicated contract. F4 may expose its availability and current relationship context but must not route Stop through `submitRelationshipCommand`, couple it to workspace refresh, or delay it on WBE, PR projection, domain adapter, or evidence-read availability.

## 4. Public Command Contract

### 4.1 Request And Command Families

`SubmitRelationshipCommandRequestV1` contains:

- `schemaVersion`, `commandKind`, `subjectType`, `subjectId`, and `purpose`;
- `expectedWorkspaceVersion`, `expectedSubjectVersion`, and all command-specific expected authority, scope, lifecycle, assurance, evidence, or WBE projection versions;
- command-specific `payload` using a generated discriminated union;
- `typedAcknowledgement` only where the approved consequence policy requires it;
- no tenant identifier, private service identifier, rank, inferred authority, or arbitrary callback URL.

The request requires the standard `Idempotency-Key` header. The generated union must support these operation families without a free-form command name:

| Command kinds | Required semantic distinction |
|---|---|
| `REVIEW_PLAN`, `AGREE_PLAN`, `REQUEST_PLAN_CHANGE`, `CANCEL_PLAN` | Proposed/agreed/current/cancelled plan states remain distinct from authority, affected work, relationship lifecycle, and work completion; cancellation names its consequence and does not imply that related work or the relationship was terminated |
| `DEFINE_GOAL`, `CONFIRM_GOAL`, `CONFIRM_BASELINE`, `AMEND_GOAL`, `REPLACE_GOAL`, `RETIRE_GOAL` | Goal version, baseline, measure, review period, attribution boundary, and affected work are explicit; baseline confirmation is a distinct version-checked result/goal acknowledgement and does not confirm achieved outcome or attribution |
| `APPROVE_ITEM`, `REJECT_ITEM` | Exact subject, consequence, expiry, downstream dependency, and assurance policy are checked |
| `CONFIRM_SCOPE_BOUNDARY`, `REJECT_SCOPE_BOUNDARY` | Separate command kind, assurance, acknowledgement, evidence action type, and outcome from approval |
| `PAUSE_WORK`, `RESUME_WORK`, `PROVIDE_WORK_INPUT` | Work state changes do not silently alter lifecycle, authority, or budget |
| `ACCEPT_DELIVERABLE`, `REJECT_DELIVERABLE`, `REQUEST_DELIVERABLE_REVISION` | Acceptance is not inferred from read, preview, download, or transport success |
| `CONFIRM_SCHEDULE`, `RESCHEDULE`, `CANCEL_SCHEDULE`, `ACKNOWLEDGE_SCHEDULE_CHANGE` | Timing and consequence are versioned and owner-approved |
| `PAUSE_RELATIONSHIP`, `RESUME_RELATIONSHIP`, `RENEW_RELATIONSHIP`, `TERMINATE_RELATIONSHIP` | Lifecycle and commercial outcomes remain independently authoritative |
| `GRANT_AUTHORITY`, `CONSTRAIN_AUTHORITY`, `SUSPEND_AUTHORITY`, `REVOKE_AUTHORITY`, `RESTORE_AUTHORITY` | Licensed owner, exact authority, scope, duration, ceiling, stop condition, assurance, and acknowledgement are mandatory |
| `CHANGE_BUDGET_CEILING`, `CHANGE_PACING`, `REQUEST_ALLOWANCE_ADDITION` | WBE owns validation and resulting commercial truth; BP owns public relationship effect |
| `DISPUTE_RESULT`, `ACKNOWLEDGE_RESULT_LIMITATION` | Attribution challenge is a result dispute; neither command rewrites evidence or manufactures attribution |

Evidence inspection is a read, not a command. Evidence export uses the dedicated export resource because preparation may be asynchronous and sensitivity/recipient policy differs from relationship mutation.

The selected Product labels map to generated union variants as follows. These mappings are normative and must not be replaced by a free-form or generic agreement command:

| Product label | Required generated command kind |
|---|---|
| **Cancel plan** | `CANCEL_PLAN` for the exact current plan and expected plan/workspace versions |
| **Confirm baseline** | `CONFIRM_BASELINE` for the exact goal/result baseline and expected goal, result, and evidence versions |
| **Challenge attribution** | `DISPUTE_RESULT` for the exact result and attribution basis being challenged |
| **Request goal change** | `AMEND_GOAL` when the current goal identity continues with versioned changes; `REPLACE_GOAL` when the current goal is superseded by a distinct goal. The authoritative projection must expose exactly one applicable kind for the current subject and state. |

### 4.2 Receipt And Outcome

`RelationshipCommandReceiptV1` returns `commandId`, `commandKind`, `relationshipId`, `status`, `acceptedAt`, `idempotencyReplay`, `correlationId`, and reconciliation links restricted to BP paths.

`status` is one of:

- `COMPLETED`: all required authoritative owners and Evidence First obligations confirmed the represented outcome;
- `PENDING`: BP durably accepted responsibility but one or more required authoritative outcomes remain in progress;
- `PARTIAL`: at least one owner committed and another required outcome did not confirm; compensation/reconciliation ownership is explicit;
- `UNKNOWN`: BP cannot establish whether a required owner committed; no success is shown and blind replay is prohibited;
- `REJECTED`: the command was authoritatively denied with no represented success;
- `CONFLICT`: expected versions are stale or the subject changed; authoritative reconciliation is required;
- `BLOCKED`: an owner contract, assurance, authority, lifecycle, Stop, or constitutional prerequisite prevents execution.

`RelationshipCommandOutcomeV1` adds per-owner `steps`, resulting public versions, evidence state/reference, typed effect, unresolved owner, next reconciliation action, and `resolvedAt`. Internal URLs, stack traces, private IDs, and ledger coordinates are prohibited.

HTTP `202` means BP accepted durable reconciliation responsibility, not that the business command succeeded. HTTP `200` may represent a replayed or synchronously completed authoritative outcome. A timeout, disconnected browser, accepted internal request, PR event, WBE transport response, or pending CE record never means success.

### 4.3 Idempotency And Concurrency

BP binds idempotency to authenticated actor, tenant, relationship, operation family, `Idempotency-Key`, canonical request hash, and initial expected versions.

1. Same binding, key, and canonical hash returns the original command ID and latest authoritative outcome.
2. Reuse with a different hash returns `RELATIONSHIP_IDEMPOTENCY_CONFLICT` and performs no new owner call.
3. BP propagates a derived owner-scoped idempotency identity to WBE, PR, and domain adapters. It propagates one stable `action_instance_id` to CE evidence transitions. Public keys are not used as private authorization.
4. `expectedWorkspaceVersion` and subject/source versions prevent blind overwrite. A mismatch returns `RELATIONSHIP_STATE_CONFLICT` with a fresh reconciliation cursor or snapshot link.
5. Retrying an `UNKNOWN` or `PARTIAL` command first queries recorded owner outcomes using the existing command ID. BP must not issue a second semantic mutation until the first outcome is authoritatively resolved or the owner contract explicitly proves no commit.
6. A completed terminal outcome is replayed. A changed customer intent requires a new key and, where applicable, a new assurance decision.

## 5. Internal Owner Contracts

All internal contracts are service-authenticated, tenant- and relationship-bound, semantically versioned, and inaccessible from the browser. Internal tenant context comes from the authenticated BP service assertion or approved transport metadata, not from an untrusted body field. Names below are conceptual interface names and proposed REST paths for later owner specifications/OpenAPI artifacts.

### 5.1 BP To WBE

| Operation | Proposed internal path | Request/response |
|---|---|---|
| `getRelationshipCommercialProjection` | `GET /internal/v1/relationships/{relationshipId}/commercial-projection` | `WbeRelationshipCommercialProjectionV1` |
| `submitRelationshipCommercialCommand` | `POST /internal/v1/relationships/{relationshipId}/commercial-commands` | `WbeCommercialCommandRequestV1` to `WbeCommercialCommandReceiptV1` |
| `getRelationshipCommercialCommand` | `GET /internal/v1/relationships/{relationshipId}/commercial-commands/{commandId}` | `WbeCommercialCommandOutcomeV1` |

The projection includes customer-language units, actuals, remaining allowance, ceilings, forecast ranges, assumptions, threshold states, pacing choices, consequences, `projectionVersion`, `producedAt`, `validUntil`, and currency state. It does not expose provider procurement cost, Thread Catalog internals, platform margin, raw wallet/ledger rows, or WBE operational controls to the public projection.

WBE commands cover only owner-approved ceiling, pacing, allowance addition, and lifecycle commercial effects. WBE validates commercial state and returns `COMPLETED`, `PENDING`, `REJECTED`, `CONFLICT`, `UNKNOWN`, or `UNAVAILABLE` plus an opaque owner outcome ID. BP must relay, not reinterpret, the commercial effect.

### 5.2 BP To PR

| Operation | Proposed internal path | Request/response |
|---|---|---|
| `getRelationshipExecutionProjection` | `GET /api/v1/internal/relationships/{relationshipId}/workspace-execution` | `PrRelationshipExecutionProjectionV1` |
| `submitRelationshipExecutionControl` | `POST /api/v1/internal/relationships/{relationshipId}/workspace-controls` | `PrRelationshipExecutionControlRequestV1` to `PrRelationshipExecutionControlReceiptV1` |
| `getRelationshipExecutionControl` | `GET /api/v1/internal/relationships/{relationshipId}/workspace-controls/{controlId}` | `PrRelationshipExecutionControlOutcomeV1` |

PR supplies work/execution facts: professional owner, internal work correlation, scheduled/active/paused/blocked/completed/cancelled/failed/unknown execution state, observed timestamps, partial/Stop state, supported evidence references, and `projectionVersion`. It must not supply public approval, authority, rights, lifecycle, result attribution, attention order, or WBE meaning.

PR controls are limited to BP-authorized work pause/resume/input propagation where the owning work contract permits them. PR does not implement relationship lifecycle or Emergency Stop through this interface. Stop remains the dedicated preemptive path.

### 5.3 BP To Professional/Domain Adapter

| Operation | Conceptual interface | Request/response |
|---|---|---|
| `getDomainOutcomeProjection` | `RelationshipOutcomeAdapterV1.GetProjection` | `DomainOutcomeProjectionRequestV1` to `DomainOutcomeProjectionV1` |
| `validateDomainGoalChange` | `RelationshipOutcomeAdapterV1.ValidateGoalChange` | `DomainGoalChangeRequestV1` to `DomainGoalChangeAssessmentV1` |
| `getDomainCommandOutcome` | `RelationshipOutcomeAdapterV1.GetCommandOutcome` | owner command reference to `DomainCommandOutcomeV1` |

The transport and deployable placement remain owned by each selected professional/domain contract; this Solution contract does not create a generic public service. Every adapter contribution includes adapter major/minor version, relationship and goal binding, accountable domain owner, baseline, measure, review period, observed assessment, evidence references, attribution basis/limits, uncertainty, missing inputs, validity, and optional attention candidate.

BP validates ownership, relationship/goal binding, schema support, evidence reference form, and completeness. BP alone decides public incorporation, business state, available commands, and attention qualification/order. The adapter cannot grant authority, approve work, change lifecycle, record constitutional evidence, calculate WBE truth, or expose a browser endpoint.

### 5.4 BP To CE

BP uses existing CE gRPC contracts; F4 creates no REST CE surface.

- `ValidateAction` or `EvaluatePolicy` checks the current relationship, subject, Decision Space, authority/scope/lifecycle versions, consequence class, and approved assurance context before governed mutation.
- `RecordEvidence` uses one stable `action_instance_id` for proposal, awaiting approval, approved/rejected, executed, or abandoned transitions. `CONFIRM_SCOPE_BOUNDARY` records `SCOPE_BOUNDARY_CONFIRMATION` with the distinct acknowledgement fields.
- `GrantAuthorityLicense` and `RevokeAuthorityLicense` remain the authority-change contracts; BP does not emulate authority licensing in its business store.
- `TriggerEmergencyStop` remains outside ordinary F4 command sequencing.

No BP public response may state approved, boundary confirmed, authority changed, lifecycle consequence completed, evidence recorded, or another constitutionally governed success before the required CE confirmation. CE unavailability fails closed for writes with `CONSTITUTIONAL_ENGINE_UNAVAILABLE`; unaffected reads may return with accurate evidence/constitutional currency state.

## 6. Interaction Sequences

### 6.1 Aggregate Workspace Read

1. Web calls `getRelationshipWorkspace` through the generated BP client.
2. BP authenticates the session and authorizes actor, tenant, role, and relationship before reading any protected source.
3. BP reads its relationship-governance projection and owner-version registry.
4. BP obtains or validates the current WBE commercial projection, PR execution projection, and selected domain adapter projection through internal contracts. Owner calls may run independently, but no result crosses relationship boundaries.
5. BP validates supported major versions, binding, provenance, freshness, and correlation. It incorporates only valid owner meanings.
6. BP qualifies and orders **Needs your attention**. WBE/domain candidates are inputs only; their source priority never becomes public order automatically.
7. BP returns `CONSISTENT`, `PARTIAL`, `STALE`, or `UNKNOWN`, with each section's source versions and currency. Web presents the array order and meanings exactly.

An unavailable WBE projection makes Usage & budget unavailable and may make affected lifecycle or work commands blocked; it does not erase current Plan or rights. An unsupported PR/domain major version makes only dependent projections unavailable/unknown and prohibits dependent consequential commands. BP never fills a missing section from cached browser content.

### 6.2 Approval Or Rejection

1. Web submits `APPROVE_ITEM` or `REJECT_ITEM` with the exact subject, expected versions, purpose, assurance material, and idempotency key.
2. BP authorizes the decision owner and verifies subject state, expiry, consequence, lifecycle, scope, authority, and required assurance.
3. BP records/validates the proposed constitutional action through CE as required.
4. BP commits the BP-owned approval decision only after the required CE confirmation and invokes PR, WBE, or domain follow-up only when the approved subject contract requires it.
5. BP records the final required evidence state and publishes a completed outcome only after all owners required for the represented effect confirm.
6. If downstream effect remains pending, BP returns `PENDING`; approval of the stated next step may be recorded while work completion remains separately pending.

Approval grants only the named next step. It never confirms scope, expands authority, accepts a deliverable, or proves a result unless those are the exact separately governed subject and command.

### 6.3 Distinct Scope-Boundary Confirmation

1. Web can offer `CONFIRM_SCOPE_BOUNDARY` only from a BP projection that names the boundary, exclusions, affected relationship, duration, downstream action, consequence class, current assurance requirement, and expected scope version.
2. Web submits the exact boundary reference and typed acknowledgement using the distinct generated request variant.
3. BP verifies current assurance and licensed boundary owner, then calls CE with `SCOPE_BOUNDARY_CONFIRMATION`; it must not translate the request into ordinary approval.
4. BP updates its scope projection only after CE confirms the distinct evidence record.
5. BP returns the new scope version, effective meaning, evidence reference, and any separately pending authority/work effect.

Any stale assurance, changed boundary, changed consequence, or expired proposal returns conflict/assurance-required with zero confirmation.

### 6.4 Lifecycle Or Authority Change With WBE Effect

1. BP validates actor, current relationship/lifecycle/authority/scope versions, typed consequence, assurance, and idempotency.
2. BP obtains a WBE commercial consequence quote/projection identified by a version; it does not calculate one.
3. BP performs required CE policy/authority/evidence calls and starts the idempotent owner sequence.
4. BP applies or records the BP governance transition only according to the approved transition choreography, then commands WBE and PR using derived owner idempotency identities.
5. BP returns `COMPLETED` only when the lifecycle/authority state, required CE evidence, and represented commercial/execution effects are all authoritative.
6. If one owner commits and another is unknown or fails, BP returns `PARTIAL` or `UNKNOWN`, freezes incompatible follow-up commands, identifies the reconciliation owner, and polls owner outcomes before compensation or completion.

Automatic rollback is prohibited unless every owner contract defines it as valid and evidence-preserving. A compensation is a new evidenced transition, never deletion or rewriting of prior truth.

### 6.5 Evidence Read And Export

1. BP authorizes the actor, relationship, role, subject, sensitivity, and permitted evidence scope.
2. BP uses CE/evidence-reader internal authority to obtain a customer-safe projection; web never receives ledger access or a reusable private locator.
3. Inspection returns recorded/pending/unavailable/completeness meaning without implying outcome success.
4. Export request includes subject/period, intended recipient or use, requested scope, expected evidence version, assurance/acknowledgement where required, and idempotency key.
5. BP records required constitutional evidence and prepares or delegates the export under the approved security policy.
6. `202` means export responsibility accepted. Only `COMPLETED` yields a time-bounded BP-mediated retrieval result with completeness, redaction, sensitivity, recipient/use, and limitation statement.

Failed, partial, expired, or unknown exports do not return a file link presented as authoritative. Export retry reconciles the original `exportId` and idempotency outcome.

### 6.6 Usage Or Budget Choice

1. Web submits a generated budget/pacing/allowance command to BP with expected relationship, authority, lifecycle, and WBE projection versions.
2. BP verifies the licensed actor and obtains any CE validation required by financial authority or scope.
3. BP invokes WBE with a derived idempotency identity. WBE validates and owns the commercial outcome.
4. BP incorporates the WBE outcome into relationship governance and records required evidence before reporting represented success.
5. A changed WBE version returns conflict and a fresh Usage & budget projection. BP never re-prices or retries against new assumptions without customer review.

## 7. Failure, Partial, And Unknown Semantics

Public errors use RFC 9457 `RelationshipWorkspaceProblemDetailV1` with `type`, `title`, `status`, stable `code`, `correlationId`, `relationshipId` only when safe, `reconciliationRequired`, and optional BP-only reconciliation link. Errors never echo acknowledgement text, evidence payload, tenant identity, internal URL/ID, provider detail, WBE ledger state, PR trace, CE rationale not approved for customers, or resource existence across an authorization boundary.

| HTTP | Code | Required public behavior |
|---|---|---|
| 400 | `RELATIONSHIP_REQUEST_INVALID` | Reject malformed input, unsupported minor usage, or invalid command payload without owner calls |
| 401 | `RELATIONSHIP_SESSION_REQUIRED` | Hide protected state and re-authenticate |
| 403 | `RELATIONSHIP_ASSURANCE_REQUIRED` | State the required assurance action without exposing protected owner data |
| 404 | `RELATIONSHIP_WORKSPACE_NOT_ACCESSIBLE` | Normalize missing, cross-tenant, wrong-role, and inaccessible relationship outcomes |
| 409 | `RELATIONSHIP_STATE_CONFLICT` | Reconcile current snapshot/subject/source versions before a new decision |
| 409 | `RELATIONSHIP_IDEMPOTENCY_CONFLICT` | Preserve the original outcome; perform zero new mutation |
| 409 | `RELATIONSHIP_COMMAND_UNRESOLVED` | Query the existing command outcome; do not issue a blind duplicate |
| 410 | `RELATIONSHIP_CURSOR_EXPIRED` | Fetch a complete authorized workspace snapshot |
| 410 | `RELATIONSHIP_COMMAND_EXPIRED` | Proposal/approval/boundary/export validity ended; obtain a fresh projection |
| 422 | `RELATIONSHIP_COMMAND_NOT_ALLOWED` | Command is not authoritative for current subject/lifecycle/authority state |
| 423 | `RELATIONSHIP_STOPPED` | Stop is active; ordinary F4 command cannot release it |
| 424 | `RELATIONSHIP_OWNER_DEPENDENCY_FAILED` | Required owner definitively rejected/failed; no represented success |
| 429 | `RELATIONSHIP_RATE_LIMITED` | Preserve command identity and honor `Retry-After` |
| 503 | `RELATIONSHIP_PROJECTION_UNAVAILABLE` | Return unavailable/partial semantics; do not substitute cached or inferred truth |
| 503 | `RELATIONSHIP_OWNER_UNAVAILABLE` | Dependent command remains blocked or unresolved with reconciliation ownership |
| 503 | `CONSTITUTIONAL_ENGINE_UNAVAILABLE` | Fail closed for writes; never claim governed success |
| 503 | `RELATIONSHIP_SCHEMA_UNSUPPORTED` | Halt dependent composition/command on unknown owner major version |

Transport failure before BP durable acceptance permits the client to repeat the exact request with the exact idempotency key. Transport failure after possible acceptance requires `getRelationshipCommand` or export-outcome reconciliation. BP's inability to distinguish commit from non-commit is `UNKNOWN`, not failure and not success.

`PARTIAL` is allowed only when the contract names each committed and unresolved owner outcome. It must disable commands that could compound the inconsistency. `UNKNOWN` withholds consequential state and names the accountable reconciliation path. Neither state may be hidden behind a generic success response.

## 8. Version And Compatibility Contract

Public F4 schemas begin at semantic schema version `1.0`. Proposed BP OpenAPI version after incorporating F4 must be selected by the BP owner as a backward-compatible increment from the current `1.2.0`; this contribution does not edit or release that specification.

| Change | Compatibility rule |
|---|---|
| Add optional field, currency reason, or non-command item type | Minor-compatible; generated consumer ignores unknown optional fields while preserving authoritative order |
| Add command kind | Requires a generated discriminated-union variant and owner-approved operation semantics; web cannot invoke an unknown kind |
| Remove/rename field, change meaning/type, change required state semantics, or change ordering interpretation | New major schema version with explicit coexistence/migration window |
| Unknown public major version | Render honest unsupported/unavailable state; execute no command |
| Unknown internal owner major version | BP excludes dependent truth, marks it unavailable/unknown, and blocks dependent commands |
| Unknown optional field in supported major | Ignore without recomputation or local inference |

Every owner projection declares `schemaVersion`, `projectionVersion`, production/observation time, validity, and supported reconciliation behavior. BP records the source versions used for every public snapshot and command outcome. A source version is evidence of composition, not authority for the browser.

## 9. Generated-Client Surface

The later BP OpenAPI update must generate one dependency-closed TypeScript `RelationshipWorkspaceApi` using the repository-pinned OpenAPI Generator and strict TypeScript without manual patches.

The generated public client must expose only these F4 operation families:

- aggregate and incremental workspace reads;
- Plan, attention, Work, Results, Usage & budget, and Rights & control reads;
- one typed relationship command submission plus command-outcome reconciliation;
- BP-mediated evidence list/detail and export request/outcome.

All command payloads must be generated discriminated unions; `Record<string, unknown>`, arbitrary endpoint fields, generic action URLs, or stringly typed service routing are prohibited. Generated models must preserve schema version, source currency, item owner/state/effect/evidence, authoritative array order, expected versions, idempotency header, and partial/unknown outcomes.

The generated client and any web server wrapper must contain no:

- PR base URL or ordinary PR operation;
- WBE base URL, wallet/bucket/customer ID, internal pricing/meter/procurement/reconciliation operation, or ledger locator;
- CE host, gRPC-web surface, CE RPC, constitutional metadata header, or audit-ledger operation;
- Customer Evidence Ledger or billing-ledger query;
- model-provider URL, API key, token/provider-cost field, or ranking endpoint;
- `tenantId` request field;
- attention sort, rank, score, weight, reorder, personalization, or cross-relationship aggregate operation.

The existing Emergency Stop client remains separately governed and is not generated from the F4 BP paths.

## 10. Required Later OpenAPI And Owner Tasks

This contribution deliberately does not modify OpenAPI. The following are later-owner gate tasks:

1. **BP owner:** accept sole public facade and relationship-governance ownership; add the proposed public F4 paths, tags, parameters, schemas, response components, idempotency header, security, and RFC 9457 errors to `business-platform.openapi.yaml`.
2. **BP owner:** confirm aggregate snapshot composition, stable attention ordering, expected-version handling, command-state persistence, and owner reconciliation responsibilities.
3. **WBE owner:** publish and approve the internal relationship commercial projection/command contract, compatibility, freshness, customer-language units, and outcome reconciliation. Existing customer-ID bucket/meter APIs are not a browser or BP F4 substitute.
4. **PR owner:** add or approve the BP-only relationship execution projection/control contracts as `x-internal`, with service authentication and no public browser ingress.
5. **Selected professional/domain owners:** publish adapter-conformant outcome contracts, supported versions, evidence/attribution rules, uncertainty, validity, and candidate-attention semantics.
6. **CE/BP owners:** confirm existing gRPC coverage for each selected consequence and identify any required CE contract change through its own approved architecture process; no REST CE endpoint may be introduced.
7. **INST-005 with BP owner:** run OpenAPI parse/reference/operation-ID validation, pinned generator validation, two-run deterministic generation, strict TypeScript compile, and forbidden-surface scan with no manual patch.
8. **Independent reviewers through INST-013:** review the integrated Solution, Data, Security, Product, BP, WBE, and selected domain-owner package before implementation selection.

Until each owner accepts its contract, the dependent public section or command remains `BLOCKED` or `UNAVAILABLE`. This document closes the INST-005 design contribution to G-F4-03; it does not unilaterally close owner gates G-F4-07 through G-F4-10.

## 11. F4 Acceptance Mapping

| Acceptance ID | Contract evidence | Required later executable evidence |
|---|---|---|
| UX-CONV-06 | `GovernedRelationshipItemV1`, Plan/Goal/Work/Deliverable/Approval/Decision command unions, and required owner/state/effect/evidence/action fields | Generated-client fixtures prove every selected item type answers the four customer questions and exposes only authoritative commands |
| UX-CONV-07 | Every path, cursor, item, command, source version, export, and idempotency binding is tenant/relationship authorized; relationship switch requires a complete fresh snapshot | Cross-relationship browser and API scenarios show zero draft, link, authority, budget, evidence, attention, item, or command carry-over |
| UX-CONV-08 | `RelationshipAttentionPageV1` has exact BP array order, opaque stable sequence, no sort/rank/filter/reorder operations, and BP-only qualification | Repeated refresh, pagination, reconnect, and device scenarios preserve server order and stable ties; generated-client scan finds no ranking surface |
| CCT-UX-BOUNDARY-01 | `CONFIRM_SCOPE_BOUNDARY` is a distinct union variant, assurance/version check, typed acknowledgement, CE action, evidence outcome, and error path | Ordinary approval cannot satisfy or expand scope; stale assurance/version causes zero confirmation |
| CCT-UX-RIGHTS-01 | `RelationshipRightsControlsV1` independently exposes rights, scope, authority, lifecycle, evidence access/export, and unchanged Emergency Stop reachability | Each included lifecycle state has reachable customer-language rights and controls, including degraded owner states |
| CCT-UX-EF-01 | Evidence states are structural; CE-confirmed `RECORDED` is required before recorded/governed success; command/export sequences preserve pending first | Failure and delayed-confirmation scenarios show `PENDING` before `RECORDED` and zero fabricated evidence success |
| UX-SHELL-06 | Missing owner/schema/authority produces `UNAVAILABLE` or `BLOCKED`; no private route, fallback calculation, or mock success is permitted | Contract and browser scenarios show honest blocked states for every absent selected-release dependency |

## 12. Gate Evidence And State

| Gate | Evidence supplied or required | State after CR-GOAL-005-INST-005-04 |
|---|---|---|
| G-F4-03 — Solution API contracts | Sections 2-9 define concrete BP public and BP-WBE/PR/domain/CE internal contracts, request/response/error/version/idempotency/reconciliation semantics, sequences, generated-client boundary, and private-route prohibitions | **CONTRIBUTION COMPLETE** — subject to independent integrated review and owner acceptance; no OpenAPI changed |
| G-F4-07 — BP owner contract | BP must accept the paths/schemas, sole public facade, relationship projection, stable attention ordering, command authority, partial/unknown ownership, and reconciliation obligations in Sections 1-7 and publish the OpenAPI update | **BLOCKED pending BP owner acceptance and canonical OpenAPI contract** |
| G-F4-08 — WBE owner contract | WBE must approve `WbeRelationshipCommercialProjectionV1`, command/outcome contracts, customer-language meanings, compatibility/freshness, and no-recomputation rule | **BLOCKED pending WBE owner-approved internal contract** |
| G-F4-09 — Domain-owner contracts | Every selected release profession/domain must approve `RelationshipOutcomeAdapterV1`-conformant meanings, evidence, attribution, uncertainty, attention candidates, and compatibility | **BLOCKED pending selected domain-owner contracts** |
| G-F4-10 — Generated-client compatibility | BP OpenAPI must validate/generate deterministically with strict TypeScript and expose all required operations with zero PR/WBE/CE/ledger/provider/ranking/tenant-authority surface | **BLOCKED until G-F4-07 closes and executable generator evidence passes** |

### 12.1 Required Gate Evidence Package

For G-F4-07 through G-F4-10 closure, the later owners must provide:

- signed/attested BP, WBE, and selected domain contract acceptance records;
- canonical BP OpenAPI diff with local-reference and operation-ID validation;
- approved internal WBE and PR contract artifacts and adapter compatibility records;
- generated `RelationshipWorkspaceApi` operation/model inventory;
- deterministic generation hash from two clean runs and strict TypeScript compile result;
- forbidden-surface scan proving no private PR/WBE/CE/ledger/provider URL or operation, no `tenantId` authority field, and no ranking/reorder surface;
- fixture or contract evidence for success, conflict, stale, unavailable, blocked, partial, unknown, CE-unavailable, and owner-version-unsupported outcomes;
- trace from every acceptance ID above to generated operations/schemas and later executable scenarios.

Architecture completion is not implementation authorization. G-F4-11 independent review, G-F4-12 implementation authorization, and G-F4-13 deployment authorization remain separate and blocked. F5-F8 remain outside this contribution.

## 13. Definition Of Done

- BP public and BP-internal operation families are concrete at Solution scope.
- Relationship context, Plan/goals/Priority Work/work/deliverables/results, authoritative attention, approvals, boundary confirmation, lifecycle/authority, evidence read/export, and Usage & budget relay have named request/response contracts.
- Version, idempotency, expected-version conflict, reconciliation, failure, partial, and unknown behavior are deterministic.
- BP-WBE, BP-PR, BP-domain adapter, and BP-CE sequences preserve each owner's truth.
- The browser uses generated BP contracts only and has no private service, ledger, provider, tenant-authority, or ranking surface.
- Every F4 acceptance ID and G-F4-03/G-F4-07 through G-F4-10 evidence obligation is mapped.
- Required later OpenAPI and owner tasks are explicit; no OpenAPI, implementation, test, governance state, assurance log, commit, push, runner, provider, deployment, or F5-F8 artifact is produced.

## 14. Controlling Inputs

- `goals/GOAL-005-f4-business-contribution.md` — CR-GOAL-005-INST-003-03
- `architecture/reference/components/relationship-workspace.md` — CR-GOAL-005-INST-004-07
- `work-contracts/WC-034-goal005-webportal-founder-admin.md` — F4 scope and authorization boundary
- `architecture/reference/ux/wc-034-implementation-decomposition.md` — F4 acceptance and dependency boundary
- `architecture/reference/components/conversation-core.md` — established BP public, PR internal, version, idempotency, and reconciliation conventions
- ADR-001, ADR-002, ADR-003, ADR-017, ADR-031, ADR-034, and ADR-035
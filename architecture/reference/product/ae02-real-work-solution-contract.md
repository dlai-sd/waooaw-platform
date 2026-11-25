# AE-02 Real Work Solution Contract (WC-170 data contracts)

**Status:** GROOMED CANDIDATE. Accepted when the Founder merges the WC-170 grooming pull request. No code is authorized by this document.
**Work Contract:** [WC-170](../../../work-contracts/WC-170-real-agent-work-end-to-end.md)
**Program:** GOAL-005, Roadmap Iteration 3, milestone M3
**Closes (specification only):** PG-17, PG-18, PG-19, PG-20, PG-21, PG-22, PG-23
**Constitutional basis:** C-001, C-005, C-007, C-023, C-049, C-059, C-063, C-065, C-088, C-089
**Reuses without change:** ADR-043 (Intent Crystallizer and `LockedArtifact`), ADR-046 (workload identity), ADR-026 (WAOOAW-managed paid accounts), WC-114 solution contract (conversational employment aggregate), WC-115 implementation, WC-116 (DMA Skills 0, 1, 2), WC-117 (content production and publication), WC-118 (paid demand, lead handling).

## 1. Purpose and ownership

WC-170 proves that a professional does real, approved, reconciled work for a customer. It adds no new owner. Each data contract below names the one owner that stores it and the one place the customer reads it.

| Concern | Sole owner | Rule |
|---|---|---|
| Public API and customer projection | Business Platform (BP) | The web calls generated BP clients only; BP maps every error |
| Execution coordination, durable external intent, ambiguous-outcome reconciliation | Professional Runtime (PR) | No public lifecycle authority |
| Approval, scope and consequence validation, append-only evidence | Constitutional Engine (CE) | Validation precedes every consequential action; Emergency Stop stays independent |
| Entitlement, wallet, reservation, charge, spend | Billing Engine (WBE) | The only commercial authority |
| Model calls | AI Runtime (AIR/PSE) | Proposal only; model output is never authority |
| Domain meaning, constraints, isolation, outcome interpretation | The agent's domain adapter | Generic contracts only; no platform schema or branch is agent-specific |

**Platform-led rule (Founder, 2026-11-24).** Every capability here is stated agent-neutrally and proved by DMA. A change that exists only for DMA does not enter a shared owner; it stops and goes to the Founder.

## 2. Activation contract (precondition of everything below)

| Item | Current fact (read from the repository, 2026-11-25) | Contract |
|---|---|---|
| Employment protocol gate | `EmploymentProtocol:Enabled` is `false` in `appsettings.json`; Demo does not set it; the web workspace shows "Conversational employment is not available" | Demo sets `EmploymentProtocol__Enabled=true` and `EmploymentProtocol__GateId=conversational-employment-candidate-v1` through the environment settings path in a Founder-authorized change. `RollbackEpoch` is set, never reused, and raised to roll back |
| Rollback | Epoch field exists and is validated (`>= 0`) | Raising the epoch makes in-flight commands resolve to a closed blocked outcome with evidence; no history is rewritten |
| Conversation | Backend `Wc120Conversation__Enabled=true` and `VisitorConversation__Mode=V2` on Demo; the web `WC120_CONVERSATION_ENABLED` switch is separate and off | The web switch is turned on by the Founder's decision (WC170-R003); the four conversation tables are granted by WC169-R003 |
| Agent admission | The DMA agent is admitted and offered on the Marketplace | The compatibility start operation binds the exact admitted inventory and protocol version; a mismatch fails closed |
| Model credential | Providers screen holds no AI key yet | At least one AIR provider key is saved by the Founder after step-up; AIR reports provider status without revealing the value |
| Provider mode | Meta development mode; sandbox payment and test assets | Real money and real customers stay out of scope until Iteration 5 |

## 3. Data contracts

### DC-1 Domain vocabulary resolution (PG-17)

| Field | Definition |
|---|---|
| Source | The agent manifest `experience.vocabularyRef` (`contractRef`, `contractVersion`, `contractDigest`) points at a versioned vocabulary document. For DMA the build must confirm the exact vocabulary section the reference names (the reference currently points at `digital-marketing-agent.md#3.22`); if that section is not the vocabulary, the build repairs the reference through the owning contract before any resolution code, and records the repair |
| Business domain | A tenant-scoped, customer-confirmed business-domain selector (for example "dental clinic" or "fitness studio") chosen during the profile step. Resolution input is the pair (vocabulary version, business-domain selector); the selector is data, never a code branch |
| Resolution | The shared runtime resolves `{DVE.TOKEN}` references in prompts, plan text and customer copy from the vocabulary version bound to the admitted agent version. The digest in the manifest must equal the digest of the loaded vocabulary or resolution fails closed |
| Unknown token | Rendered as a named gap and recorded as a limitation. It never renders as an empty string or as a guess |
| Isolation | Two agents with different vocabularies resolve the same token to different text with no `if agent` branch in the shared code |
| Evidence | Each resolution that reaches a customer carries vocabulary version and digest |

Proof of "no domain branching" is a conformance scenario with a second profession fixture (Trading or Tutor, already used by WC-116 R019) resolving a different vocabulary through the same code path, plus two businesses served by the same agent version resolving different domain wording from their selectors.

### DC-2 Locked artifact projection (PG-18, AE-02-S02 and S03)

| Field | Definition |
|---|---|
| Artifact | The Intent Crystallizer's `LockedArtifact` (ADR-043): `skill_id`, `artifact_type`, `content`, `approval_evidence_id`. That type has no version, digest or status and may carry stub approval evidence. The build adds a version lifecycle (version number, content digest, status, supersedes link) as an owner-side record beside it, and the lock transition is allowed only with a genuine, non-stub approval evidence id from the approval gate (DC-3); a stub is refused |
| Bootstrap | Artifact-binding applies to steps that act on the customer's behalf or change customer-visible state. The first steps that create an artifact (profile confirmation, observation, scoring that feeds the maturity report) run under the agent's admitted skill and plan version, and produce the artifact as their output; they are not circular |
| Customer projection | BP exposes a read model of the artifact that controls execution: `artifactId`, `artifactType`, `version`, `digest`, `status` (DRAFT, PROPOSED, LOCKED, SUPERSEDED), `lockedAt`, `approvalEvidenceId`, `supersedesArtifactId`, `plainLanguageSummary`, `limitations[]` |
| Immutability | A locked artifact is never edited. A change creates a successor version; the successor never inherits approval (WC117-R015, WC118-R015) |
| Execution binding | Every consequential execution step names the `artifactId` and `digest` it runs under. A step whose artifact is not LOCKED, or whose digest differs, is refused by CE before dispatch |
| DMA instances | Profile (PROFILE_CONFIRMATION), maturity report (MATURITY_REPORT), campaign brief (CAMPAIGN_BRIEF), content calendar (CONTENT_CALENDAR) |

### DC-3 Decision steps: approval and scope-boundary confirmation (PG-19, AE-02-S03 and S04)

Two distinct customer decisions, never merged into one button, one record or one label:

| Decision | Question to the customer | Command (existing or new) | Evidence record |
|---|---|---|---|
| Approval | "Do you approve this exact version?" | `ACCEPT_PLAN_VERSION` (existing, accepts a plan version); a closed `ACCEPT_ARTIFACT_VERSION` (new) for a brief, calendar or draft | `APPROVAL` bound to artifact id and digest |
| Scope-boundary confirmation | "Is it within what this agent may do for you, and who may do it?" | A closed command `CONFIRM_SCOPE_BOUNDARY` (new, closed discriminator in `submitEmploymentCommand`) | `SCOPE_CONFIRMATION` bound to the Decision Space version (PG-07) **and** to the artifact id and digest it covers |

Both commands carry `relationshipId`, expected version, artifact id and digest, and an idempotency key. Only the customer owner or a delegate the Decision Space names may issue them; the owner check is done by BP before the command reaches CE, and CE re-checks.

A consequential step runs only when both records exist for the exact artifact version. The screen shows the two steps separately, in order, each with its own state.

### DC-4 Execution status and action timeline (PG-20, AE-02-S04 and S05)

One append-only event stream per relationship, owned by PR for execution and projected by BP.

| Field | Definition |
|---|---|
| `eventId`, `relationshipId`, `tenantId` | Identity and isolation; every read is tenant-scoped |
| `workItemId`, `workItemType` | DMA types from the manifest (`PROFILE_CONFIRMATION`, `PUBLIC_PRESENCE_OBSERVATION`, `MATURITY_DIMENSION_SCORING`, `MATURITY_REPORT`, `PRIORITY_RECOMMENDATION`, `CAMPAIGN_BRIEF`, `CONTENT_CALENDAR`, content and publication items) |
| `state` | `PROPOSED`, `APPROVED`, `EXECUTING`, `COMPLETED`, `FAILED`, `HALTED` (closed set of six). An unknown outcome is not a seventh state: it is `FAILED` or `EXECUTING` with `reasonCode=UNKNOWN_OUTCOME`, shown with its own plain sentence |
| `artifactId`, `artifactDigest` | The locked artifact the step runs under |
| `evidenceRefs[]` | CE evidence ids, provider references (as references only), no secret or token |
| `occurredAt`, `sequence` | Monotonic per relationship; replay and reorder resolve to one logical event |
| `reasonCode` | Closed list for FAILED and HALTED (for example `EMERGENCY_STOP`, `PROVIDER_REJECTED`, `UNKNOWN_OUTCOME`) |

Rules: the stream is append-only. Reconciliation appends a new event (same `workItemId`, higher `sequence`) and the projection shows the latest state per work item; no event is rewritten. An unknown outcome is reconciled, never retried blindly (degradation profile `OUTCOME_UNKNOWN`). Emergency Stop fences dispatch: once the stop is recorded, PR refuses new dispatch for that relationship before it calls any provider (checked at dispatch, not only at render). If a provider call was already sent, its late result is recorded as evidence with `reasonCode=EMERGENCY_STOP`, shown as halted-then-reconciled, never as resumed or successful work (`EMERGENCY_STOP: SUPPRESS_LATE_SUCCESS`); the stop check is bounded by one dispatch attempt and has its own test. The customer sees the stream as a timeline with one plain sentence per event.

### DC-5 Outcome trace (PG-21, AE-02-S05)

| Field | Definition |
|---|---|
| `outcomeClaimId`, `measureId` | For example "4 posts published this month", with the manifest `measureId` |
| `claimText`, `value`, `unit`, `asOf` | What the customer reads |
| `derivation` | `INDEPENDENT` (computed by the owner from records, never by the agent) or `AGENT_STATED`; `AGENT_STATED` is labelled as such and cannot be shown as a business result (`independentDerivationRequired: true`) |
| `workItemIds[]`, `evidenceIds[]` | The trace. Selecting a claim lists the work items and the evidence behind it |
| `limitations[]` | Coverage, freshness and attribution limits, carried from the measure |

A claim needs both at least one work item and at least one evidence id; missing either, it is not displayed as an outcome. Activity counts such as "4 posts published" are shown under activity with their trace; a business outcome (qualified enquiry, confirmed visit, conversion) is shown only when a measurable source exists, otherwise the slot reads "not measurable yet" and the test fixture asserts that wording. `activityIsNotCustomerOutcome: true` applies: counts of tasks done are activity, not outcome.

### DC-6 External-spend authorization and reconciliation (PG-22, C-088, C-089)

Sandbox and test mode only in WC-170; real provider spend is Iteration 5 (WC-172). `AD_BOOST` stays UNAVAILABLE until the Founder decides otherwise.

| Record | Owner | Content |
|---|---|---|
| `SpendAuthorization` | WBE | `authorizationId`, `relationshipId`, `artifactId`, `artifactDigest`, `ceiling`, `currency`, `fundingAccount` (PLATFORM or CUSTOMER), `window`, `status`; created only after approval and scope confirmation exist for the exact artifact version |
| `SpendReservation` and `SpendCharge` | WBE | Reservation before dispatch, charge after verified provider evidence |
| `ProviderSpendObservation` | PR | Provider-reported spend as an observation with provider reference |
| `ReconciliationResult` | WBE | `MATCHED`, `WITHIN_TOLERANCE`, `DISCREPANCY`; a `DISCREPANCY` blocks new spend for that relationship until resolved |

Enforcement: the ceiling is checked and the reservation written in one atomic wallet operation (existing WBE wallet operations; no second ledger), keyed by `authorizationId` plus work item id, so a replay returns the same reservation and two concurrent dispatches cannot exceed the ceiling. An uncertain reservation (dispatch outcome unknown) stays reserved and is settled by reconciliation, never released blindly. Every row carries tenant, relationship and work item ids.

Funding rule (R009): platform-owned work is funded from the platform account, hired work from the customer's; a work item with no funding account does not run. Every rupee is authorized (an authorization row), attributable (relationship, artifact, work item) and reconcilable (a result row).

### DC-7 Monitor projection (PG-23)

Business measures lead; technical metrics support. The agent manifest already declares `experience.monitor.tiles` (for example `PROFILE_COVERAGE_TILE`, `MATURITY_EVIDENCE_TILE`, `PRIORITY_PROGRESS_TILE`, plan review and calendar tiles) with `measureId`, `blockType` and `audiences`. The web does not render them today.

| Field | Definition |
|---|---|
| Tile | `tileId`, `measureId`, `blockType` (METRIC, STATUS, ...), `value`, `unit`, `asOf`, `freshnessSeconds`, `stale` (bool), `limitations[]` |
| Order | Customer outcome tiles first, professional-performance tiles second, technical telemetry only behind a "details" control |
| Audience | `customer_owner`, `delegate`, `steward`, as declared; a tile the audience may not see is absent, not blank |
| Staleness | A tile older than its `freshnessSeconds` shows as stale, never as a current number |

## 4. Non-goals and stop conditions

- No real ad spend, no real customer, no real payment, no activation outside Demo (Iteration 5 owns real money). Approved test assets are allowed: the Meta development test assets and the AI provider the Founder configures on Providers.
- No new owner and no second source of truth for transcript, relationship, plan or phase (WC115-R006).
- No change to the shared kernel that only DMA needs (stop and ask the Founder).
- No customer-facing claim without a trace (DC-5).

## 5. Traceability

| Contract | Gap | Story (AE-02) | WC-170 requirements |
|---|---|---|---|
| Section 2 | prerequisite | all | R001, R002, R003 |
| DC-1 | PG-17 | S02 | R004 |
| DC-2 | PG-18 | S02, S03 | R005 |
| DC-3 | PG-19 | S03, S04 | R006 |
| DC-4 | PG-20 | S04, S05 | R007 |
| DC-5 | PG-21 | S05 | R008 |
| DC-6 | PG-22 | S04, S05 | R009 |
| DC-7 | PG-23 | S02, S05 | R011 |
| Emergency Stop (C-001) | PG-20 | S05 | R010 |
| Proof and coverage | PG-17 to PG-23 | S01 to S05 | R012, R013 |

Requirement ids are `WC170-R001` to `WC170-R013`, defined in the Canonical Requirement Index of WC-170.

# WC-114 - Conversational Employment Solution Contract

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-10-07 continuous working session |
| Status | SUPERSEDING CANDIDATE 2 - FOUNDER REVIEW PENDING - IMPLEMENTATION AND PROTOCOL ACTIVATION UNAUTHORIZED |
| Baseline | `origin/main` at `592c7478f51685b702ffecabb0e82b4ad6def52d` |
| Delivery unit | One bounded, non-implementation Solution Architecture repair package |
| Parent authority | WC-113 §11.1; ADR-051; Conversational Employment Workspace 1.0-candidate |
| Constitutional basis | C-001, C-003, C-005, C-007, C-023, C-026, C-030, C-034-C-039, C-041-C-044, C-048-C-049, C-051, C-059, C-063, C-070, C-079, C-088 and C-094 |
| Implementation scope | None |

## 1. Objective

Produce the concrete, versioned solution contract required by WC-113 §11.1 for the existing Business
Platform, Conversation Core, Relationship Workspace, Professional Runtime, Constitutional Engine,
WBE, AI Runtime, web and domain-adapter boundaries.

The superseding package must define operation families, wire schemas, state machines, interaction sequences,
idempotency, reconciliation, errors, generated-client boundaries, observability, rollback and the
closed Data, Security, AI and Product controls required by WC-115. It must preserve the ten
Founder-accepted WC-113 guardrails verbatim, repair the six WC-115 Section 7.5 findings and must not
activate the protocol.

## 2. Authority And Scope

### 2.1 In scope

- bind the accepted enterprise boundary to existing deployables and existing canonical contracts;
- define the minimum additive BP public, BP private compatibility-scan, WBE eligibility, AIR
  proposal-only and generic domain-adapter wire slices;
- bind existing Conversation Core, Relationship Workspace, PR, CE and WBE operations without
  duplicating or transferring their authority;
- define exact states, transitions, sequence preconditions, idempotency identities, ambiguous-outcome
  reconciliation, stable errors and telemetry;
- define generated-client ownership and prohibit browser/private-owner coupling;
- define compatibility, rollout and rollback constraints without changing a mandatory protocol
  version;
- define implementation-ready acceptance oracles and downstream handoff constraints; and
- define one machine-readable specialist profile from the Founder-directed privacy-first,
  fail-closed, data-minimised, Stop-preserving and default-off boundary;
- perform author review, repository validation, exact-head PR preparation and Founder handoff.

### 2.2 Out of scope

- any change under `src/` or `web/`;
- runnable implementation, generated clients, generated server stubs, migrations, tests, workflows,
  deployment, cloud resources, providers, secrets, DNS, customer traffic or production state;
- a new deployable service, database schema, prompt body, model policy body or visual design;
- amendment of ADR-051, WC-113 policy, the C-034 lifecycle or any business capability;
- creation of an Institutional Backlog item;
- Agent Base Specification or Platform-Agent Contract version activation;
- agent conformance claims, customer readiness claims, self-approval or merge.

### 2.3 Ten protected Founder guardrails

The following rules are copied from WC-113 and are controlling inputs, not Solution Architecture
decisions:

1. Partial readiness: permit ready Skills to operate only when dependencies, billing and Decision
   Space are independently bounded; otherwise keep affected Skills locked.
2. Trial operations: simulated or non-consequential read-only/advisory work only unless a separate
   trial policy explicitly authorizes a real action.
3. Material goal change: relock affected work and require plan impact review and renewed agreement.
4. Deferred dependencies: permit `READY_WITH_DEFERRED_ITEMS` only when every deferred item names
   blocked Skills and cannot weaken a mandatory gate.
5. Plan acknowledgement: explicit acceptance for initial plan, material goal/budget/authority/calendar
   changes and irreversible consequences.
6. Performance failure: require diagnosis and customer-visible corrective proposal after two
   consecutive missed review periods unless the domain requires a shorter threshold.
7. Billing exhaustion: preserve constitutional and read-only review paths; block unfunded
   consequential work according to WBE-owned consequence.
8. Calendar authority: permit rescheduling only inside an explicitly agreed tolerance window.
9. Credential loss: block only affected Skills when isolation is proven; otherwise fail closed for
   dependent work.
10. Mandatory readiness override: no override for constitutional, safety, evidence, tenant,
    authority or financial gates.

## 3. Required Inputs

| Input | Required state | Status |
|---|---|---|
| WC-113 §11.1 | Founder-directed handoff | PRESENT |
| ADR-051 | Merged enterprise decision package; activation still prohibited | PRESENT |
| Conversational Employment Workspace 1.0-candidate | Merged reference package | PRESENT |
| Conversation Core contract | Approved/current | PRESENT |
| Relationship Workspace contracts and canonical APIs | Approved/current | PRESENT |
| BP, PR, CE, AIR and WBE component specifications | Current | PRESENT |
| ADR-001, ADR-002, ADR-003, ADR-009, ADR-017, ADR-031, ADR-035 | Current | PRESENT |
| Repository PR template and process-control manifest | Current | PRESENT |

No implementation input is required or authorized.

## 4. Required Outputs

1. `work-contracts/WC-114-conversational-employment-solution-contract.md`
2. `work-contracts/WC-114-requirements.yaml`
3. `architecture/reference/components/conversational-employment-solution-contract.md`
4. `architecture/reference/api-specs/conversational-employment-business-platform.openapi.yaml`
5. `architecture/reference/api-specs/conversational-employment-ai-runtime.openapi.yaml`
6. `architecture/reference/api-specs/conversational-employment-wbe.openapi.yaml`
7. `architecture/reference/api-specs/conversational-employment-domain-adapter.openapi.yaml`
8. `architecture/reference/api-specs/conversational-employment-compatibility-scan.openapi.yaml`
9. `architecture/reference/api-specs/conversational-employment-negative-fixtures.yaml`
10. `architecture/reference/api-specs/conversational-employment-specialist-profiles.yaml`
11. compact routing updates to `SPRINT-REGISTRY.md`
12. template-compliant PR body and a new PR for Founder review

## 5. Delivery Plan

| Stage | Output | Acceptance oracle |
|---|---|---|
| SA-01 | Obligation and reuse ledger | Every WC-113 boundary and guardrail maps to an owner and contract |
| SA-02 | Operation and schema package | Every cross-boundary call has a versioned operation and closed schema |
| SA-03 | State and sequence package | Every success, partial, stale, blocked, unknown and failure path is explicit |
| SA-04 | Reliability and operability package | Idempotency, reconciliation, telemetry, rollout and rollback are deterministic |
| SA-04A | Universal conformance package | Complete agent manifest, exact-inventory compatibility scan and CEW-FIT trace have closed acceptance oracles |
| SA-05 | Downstream handoffs | Data, Security, AI and Product constraints identify decisions still owned downstream |
| SA-06 | Validation and author review | All checks pass and every finding is repaired |
| SA-07 | Founder handoff | Exact-head PR is open without approval, merge or activation |

## 6. Definition Of Done

WC-114 is complete only when:

- one versioned solution contract covers all nine named boundaries without creating a new deployable;
- the five additive candidate OpenAPI documents are syntactically valid OpenAPI 3.1 and have no
  unresolved local references;
- the all-agent manifest carries every mandatory WC-113 induction, planning, operations, profile,
  adapter and scenario-evidence declaration;
- the BP private compatibility scan binds one exact offered-agent inventory and fails closed on
  partial, stale, unknown, mixed-major, unresolved or missing evidence;
- AIR proposal acceptance and reconciliation retain exact relationship, contribution, agent,
  manifest, semantic-catalogue and canonical request-digest identity;
- the common phase projection carries every WC-113 customer-facing field and mechanically prohibits
  completion of the continuous Operations phase;
- every reused PR, CE and WBE operation is pinned to an exact existing contract and compatibility
  expectation;
- all state machines define legal transitions and terminal or reconciliation behavior;
- every mutation binds actor, tenant, relationship, operation family, idempotency key, canonical
  payload hash and expected authoritative versions;
- external intent and observed outcome remain distinct and blind retry is prohibited;
- public and private error vocabularies are stable, privacy-safe and fail closed;
- generated BP clients are the only ordinary web integration, and private clients stay service-owned;
- observability distinguishes availability, gate health, blocked state, stale source,
  reconciliation, provider failure, agent performance and business outcomes;
- rollback retains append-only plan/evidence history and never rolls back constitutional evidence;
- all ten protected guardrails are traced without reinterpretation;
- CEW-FIT-01 through CEW-FIT-18 map to an owner, contract rule and executable implementation oracle;
- specification-negative fixtures cover manifest incompleteness, missing scenario evidence,
  fail-open compatibility, lost AIR identity, Operations completion and incomplete phase projection;
- Data, Security, AI and Product handoff constraints leave no Solution Architecture decision gap;
- the specialist profile fixes every value required by WC-115 R077-R108 and remains disabled by
  default without deployment or customer activation authority;
- calendar, authentication, command/replay, AIR provenance/state, Stop fitness and mixed-major
  fixtures contain the six WC-115 Section 7.5 repairs;
- the requirement ledger declares implementation evidence `NOT_APPLICABLE`;
- no `src/`, `web/`, implementation, activation, self-approval or merge occurs; and
- author review and repository prechecks pass on the exact pushed commit before the PR is opened.

## 7. Stop Conditions

Stop and report a blocker if:

- any operation requires a new deployable or changes an approved owner boundary;
- a wire contract requires an unresolved Founder policy, business capability or ADR;
- a generic schema requires a DMA-, Trading- or Tutor-specific field;
- an existing canonical contract cannot preserve a required semantic without an upstream decision;
- a downstream office would have to infer an owner, state transition, error, compatibility rule or
  protected guardrail;
- validation finds an unresolved reference, contradictory state, authority bypass or ambiguous
  success; or
- PR preparation cannot bind author review to the exact remote head.

## 8. Rollback And Reversibility

This Work Contract changes architecture and contract documentation only. Before Founder acceptance,
rollback removes the WC-114 package and its compact registry row. After acceptance, a later
Solution Architecture contract must supersede this package, preserve decision traceability and name
wire-compatibility and migration consequences.

No runtime rollback is performed because no runtime behavior is changed. Any later implementation
must keep the prior mandatory employment protocol available until exact-version all-agent
conformance and rollback evidence pass. Append-only plans, commands and constitutional evidence are
never deleted by rollback.

## 9. Authorization Boundary

Founder authorization in this session covers architecture/specification authoring, validation,
commits, push and PR submission only. It does not authorize implementation, generated artifacts,
protocol activation, deployment, PR approval or merge.

## 10. Author Review

### 10.1 Findings and repairs

| Lens | Finding | Repair | Result |
|---|---|---|---|
| Contract clarity | Spectral reported missing contact and operation descriptions | Added contact and exact operation descriptions to every candidate contract | RESOLVED |
| Wire correctness | `EmploymentCommandOutcomeV1` combined `allOf` with a closed child schema that could reject inherited receipt fields | Replaced the conflicting closure with JSON Schema 2020-12 `unevaluatedProperties: false` | RESOLVED |
| Protected trial policy | `TRIAL_ADVISORY` was named in prose but absent from the public wire model | Added operation mode, allowed operation classes and a schema condition prohibiting consequential trial classes | RESOLVED |
| Partial readiness | WBE `1.1.0` exposes a string consequence but no exact Skill-scoped eligibility shape | Added the bounded WBE eligibility candidate while retaining WBE ownership and the existing command family | RESOLVED |
| Version compatibility | Candidate BP used a string Decision Space version while the active CE and conversation contracts use an integer | Aligned `expectedDecisionSpaceVersion` to integer `minimum: 1` | RESOLVED |
| Command ambiguity | Protected commands did not mechanically require their command-specific version, acknowledgement or payload fields | Added conditional schema requirements for deferral, patch application, plan review/acceptance, material change, rescheduling and corrective acknowledgement | RESOLVED |
| Universal conformance | The manifest omitted readiness, calendar, material-change, adapter/profile, degradation and exact scenario-evidence declarations | Expanded the manifest into closed induction, planning, operations and conformance objects with immutable contract references | RESOLVED |
| Activation safety | Compatibility scanning had no owner, operation family, result schema or fail-closed activation oracle | Added the private BP compatibility-scan candidate on the existing BP deployable with exact-inventory binding and closed findings | RESOLVED |
| AIR provenance | Reconciled proposals did not retain relationship, contribution, agent or semantic-catalogue identity | Bound request, receipt and result to the same immutable identities and canonical request digest | RESOLVED |
| Continuous operations | The generic phase status allowed Operations to serialize as `COMPLETE` | Added phase-specific schema/state constraints and a negative fixture prohibiting Operations completion | RESOLVED |
| Common phase interface | The phase resource omitted required goal/plan, blocker, dependency, milestone, calendar, evidence, limitation and next-action fields | Expanded the closed phase projection to the complete universal WC-113 shape | RESOLVED |
| Fitness traceability | The solution package did not map CEW-FIT-01 through CEW-FIT-18 | Added owner/contract/oracle traceability, eleven schema-negative fixtures and one non-enumeration policy fixture | RESOLVED |
| Repair author review | The first repair pass still flattened completed/in-progress/pending groups and omitted explicit agent/prompt/tool/DCM bindings | Added required grouped phase collections and immutable governance references | RESOLVED |
| Compatibility proof | The first scan schema did not mechanically require evidence and rollback safety for aggregate eligibility | Made per-agent PASS require exact evidence and aggregate eligibility require complete inventory, all-agent PASS and rollback safety | RESOLVED |
| WC-115 specialist closure | The implementation contract required exact data, security, freshness, Stop, AI, product-truth and rollback values that candidate.1 deferred | Added one machine-readable, privacy-first, fail-closed specialist profile bound to existing owners and constitutional controls | RESOLVED |
| Calendar correctness | Candidate.1 could not prove local/instant consistency or daylight-saving ambiguity | Required IANA zone, local value, UTC instant, offset, fold, tzdb version and versioned tolerance policy | RESOLVED |
| Authentication ownership | Candidate.1 forced unauthenticated requests into the employment error vocabulary | Reused the canonical BP `IdentityUnauthorized` response by reference | RESOLVED |
| Command and replay closure | Conditional fields still allowed non-applicable command fields and terminal replay returned only a receipt | Replaced the command with nine closed discriminated schemas and made terminal replay return complete owner/evidence/version outcome | RESOLVED |
| AIR control closure | Candidate.1 allowed caller-selected path prefixes and incomplete prompt/model provenance | Added immutable catalogue/prompt/model references with digests and a closed state-dependent result union | RESOLVED |
| Stop fitness | CEW-FIT-12 described a rule but did not provide degraded aggregate fixtures | Added four aggregate workspace setups requiring `operations.stopReachable=true` | RESOLVED |
| Mixed-major safety | CEW-NEG-010 validated one agent schema rather than aggregate behavior | Added two offered agents with different mandatory majors, aggregate failure, zero activation mutation and zero side effects | RESOLVED |
| Stop authority | The first specialist profile draft added employer and Founder actors beyond the existing PR contract | Restricted the profile to the existing customer actor; any actor expansion requires a separate upstream decision | RESOLVED |

### 10.2 Review result

| Review lens | Result |
|---|---|
| WC-113 §11.1 scope and nine named boundaries | PASS |
| Universal all-agent conformance and compatibility boundary | PASS |
| Ten Founder-accepted guardrails preserved without reinterpretation | PASS |
| Requirements, five interfaces, states, sequences and failure modes | PASS |
| Authority, security boundary and privacy-safe errors | PASS |
| Idempotency, reconciliation, observability and reversibility | PASS |
| Data/Security/AI/Product profile closure | PASS |
| No implementation, activation, `src/` or `web/` change | PASS |
| Implementation-readiness test | PASS |

### 10.3 Validation evidence

| Check | Result |
|---|---|
| Requirement ledger validation in repository Docker runner | PASS - WC-114 and WC-115 digests valid |
| YAML parse and `$ref` closure for candidate OpenAPI 3.1 contracts and specialist profile | PASS - five APIs and profile |
| Closed command, calendar, authentication and AIR contract assertions | PASS |
| CEW-FIT-12 and CEW-NEG-010 fixture validation | PASS |
| Catalog-controlled repository `spec-lint` | PASS - canonical inventory plus all five candidate contracts; 67 pre-existing canonical warnings, zero errors |
| OpenAPI Generator `7.17.0` validation for all five candidate contracts | PASS - catalog-owned nested-Docker runner |
| Candidate-specific Stoplight Spectral `6.15.0` validation | PASS - catalog-owned nested-Docker runner |
| `git diff --check` | PASS |

Package author review is **PASS**. CB-013 is resolved by the catalogued changed-contract validation
route and successful candidate execution. Exact pushed-head PR author review remains separately
required by the repository PR preparation control.

# Agent Runtime Adapter Contract v1 - Executable Delivery Plan

**Office:** Solution Architect (INST-005)
**Work Contract:** WC-080
**Status:** AUTHOR-REVIEWED SOLUTION PLAN CANDIDATE - FOUNDER REVIEW; IMPLEMENTATION REQUIRES SEPARATE SESSION AUTHORIZATION
**Reference architecture:** `architecture/foundation-consolidated-assessment-2026-08-29.md` Section 4.7
**Admission dependency:** WC-079 and merged PR 381
**Delivery unit:** One versioned internal runtime adapter contract, reference adapter, conformance kit,
and Professional Runtime integration proving two dissimilar admitted professionals
**Constitutional basis:** C-001, C-002, C-003, C-005, C-007, C-023, C-025, C-026, C-032, C-035,
C-036, C-037, C-049, C-059, C-063, C-065, C-071, C-076, C-079, C-080, C-094
**Architectural decisions:** ADR-001, ADR-002, ADR-003, ADR-005, ADR-015, ADR-018, ADR-031,
ADR-035, ADR-046; a new accepted adapter transport/isolation ADR is required before implementation

## 1. Objective

Define and deliver **Agent Runtime Adapter Contract v1** so Professional Runtime can invoke, control,
stop, and observe every admitted WAOOAW professional through one deterministic, versioned internal
interface. The contract must let professional implementations specialize skill inputs, outputs, and
domain behavior without inventing private lifecycle, authorization, identity, evidence, error,
idempotency, or Emergency Stop semantics.

The first release must prove that the materially different Digital Marketing and Trading fixtures
used by WC-079 can be admitted, launched as isolated immutable artifacts, configured, asked to plan,
executed, queried, cancelled, stopped, resumed under fresh authority, and reconciled through the same
adapter contract. Web and WhatsApp must continue to use Business Platform employment APIs; neither
channel may call an adapter directly.

The plan is self-contained for a future implementation executor. It does not itself authorize source,
deployment, provider activation, customer traffic, spend, UAT, Production, PR approval, or merge.

## 2. Required Outcome

```text
ADMITTED PROFESSIONAL VERSION
  -> PROFESSIONAL RUNTIME AUTHORIZES EXACT WORK
  -> PROFESSIONAL RUNTIME RESOLVES ONE PINNED ADAPTER ARTIFACT
  -> ADAPTER EXECUTES DOMAIN-SPECIFIC SKILL
  -> PROFESSIONAL RUNTIME VALIDATES FACTS AND EVIDENCE REFERENCES
  -> BUSINESS PLATFORM PROJECTS CUSTOMER-SAFE EMPLOYMENT STATE
```

The following boundaries are fixed:

| Boundary | Owner | Required responsibility | Prohibited responsibility |
|---|---|---|---|
| Agent Admission Contract | Business Platform with CE decisions | Certify exact professional version, contract digest, artifact, compatibility, and readiness | Invoke work or let an agent admit itself |
| Agent Runtime Adapter Contract | Professional Runtime | Internal execution port, adapter lifecycle, invocation state, cancellation, Stop propagation, and result validation | Public/customer API, admission approval, customer lifecycle, or constitutional authority |
| Platform-Agent Contract | Agent specification under ADR-035 | Asynchronous platform signals and declared degradation behavior | Substitute for request/response execution semantics |
| Agent Employment Experience Contract | Business Platform | Trial, hire, rights, contract, payment, activation, review, pause, stop, termination, and channel continuity | Domain execution or private agent onboarding |
| Constitutional decisions and evidence | Constitutional Engine | Validate governed actions and commit constitutional evidence | Execute professional work |
| Domain behavior | Admitted adapter artifact | Implement admitted Skill Definitions within supplied authority | Expand Decision Space, forge evidence, or reinterpret platform state |

No new public service or standalone Agent Adapter platform service is introduced. The adapter is a
private port behind Professional Runtime. Version 1 supports one isolated WAOOAW-managed runtime
deployment per admitted professional artifact. A shared multi-artifact host or externally hosted
third-party adapter is out of scope until a later accepted architecture decision.

## 3. Entry Gates And Required Inputs

Implementation may start only when every row is present, current, non-contradictory, and linked from
the implementation Work Contract.

| Input or authority | Required state | Validation |
|---|---|---|
| This plan | Founder accepted | Exact accepted path and commit recorded |
| Section 4.7 foundation assessment | Enterprise Architecture accepted | Adapter boundary and isolation direction unchanged |
| WC-079 / PR 381 | Founder accepted and merged | Admission schema, lifecycle, fixtures, and activation guard available on implementation base |
| Agent Employment Experience Contract | Accepted foundation | Customer rights and lifecycle remain platform-owned |
| ADR-035 and PAC schemas | Accepted/current | Signals remain compatible and distinct from adapter commands |
| New adapter transport/isolation ADR | Accepted | Transport, identity, isolation, discovery, deadlines, event delivery, and version negotiation fixed |
| Professional Runtime component spec | Accepted amendment | Adapter client/host responsibilities and failure handling defined |
| Professional Runtime OpenAPI | Accepted versioned change | BP-to-PR control remains canonical and adapter stays private |
| Adapter contract schemas | INST-005 accepted | Envelopes, operations, states, errors, and compatibility are exact |
| Security contract | Security owner accepted | Workload identity, least privilege, network policy, replay defense, secret and data handling fixed |
| Data/evidence contract | Data and constitutional owners accepted | Invocation lineage, retention, evidence references, and append-only boundaries fixed |
| Implementation Work Contract | Founder assigned and authorized for the session | Exact issue, tier, branch, files, tests, environments, and stops named |

If any input is missing or implementation would require a new semantic decision, stop and return a
specification gap. The executor must not infer architecture from test fixtures or current source.

### 3.1 Owner Handoff Before Platform IT Execution

The following work occurs before the Platform IT Expert receives implementation authority. Platform
IT verifies these outputs but does not author, approve, or repair their policy:

| Owner | Required accepted output |
|---|---|
| Enterprise Architecture / Founder | ADR accepting or rejecting the proposed HTTP/JSON isolation profile in Section 5.3.1 |
| Solution Architecture | Canonical OpenAPI 3.1 contract, JSON Schemas, Professional Runtime component amendment, compatibility matrix, and spec-to-test map |
| Security Architecture | Workload identity, route grant, network/egress, secret, threat, anti-replay, and privacy contract |
| Data Architecture | Temporal/PostgreSQL ownership, invocation lineage, indexes, RLS, retention, erasure, and migration/rollback contract |
| Constitutional owner | Action/evidence ordering, Stop/resume authority, fail-safe behavior, and CCT mapping |
| Founder | Accepted specification package, assigned implementation Work Contract, issue/tier labels, and explicit session authorization |

After all rows are accepted, the implementation issue must include exact paths, accepted commit IDs,
schema versions, CCT IDs, branch name, environment boundary, qualification command, and the two
fixture identities. A missing attachment is a specification blocker, not an ARA implementation task.

### 3.2 Platform IT Expert Skill Binding

The implementation Work Contract must direct Platform IT Expert Skills 1-8 and 11-17 as follows:

| Skill | Required application |
|---|---|
| 1-4 | Freeze issue specification, verify authorization, create the assigned branch, and implement only accepted contracts |
| 5-6 | Add deterministic tests and run pinned static, dependency, secret, and image security checks |
| 7-8 | Prepare one Founder-ready PR and use the repository CI order without bypass or blind reruns |
| 11 | Update only owning specifications/evidence required by verified behavior; no parallel summary documents |
| 12-15 | Reuse hash-tagged images, propagate references rather than secrets, capture failure state first, and validate structured contracts |
| 16 | Apply repository observability practice if active in the accepted agent version; do not invent telemetry policy |
| 17 | Execute governed Docker qualification and immutable evidence packaging without provider or environment mutation |

## 4. Scope

### 4.1 In Scope

- Versioned adapter protocol and compatibility policy.
- Private Professional Runtime-to-adapter operations: `describe`, `health`, `configure`, `plan`,
  `execute`, `status`, `cancel`, `emergencyStop`, `resume`, and `result`.
- Platform-constructed invocation envelope and authenticated workload context.
- Deterministic adapter state machine, idempotency, deadlines, cancellation, Stop, and replay.
- Typed domain extension points referencing admitted Skill Definition schemas by version and digest.
- One reference adapter SDK/base implementation matching the repository's selected language/runtime.
- Adapter discovery and exact immutable artifact binding for one artifact per isolated deployment.
- Admission readiness extension for adapter protocol and conformance evidence.
- Professional Runtime adapter client, orchestration, validation, and failure mapping.
- Digital Marketing and Trading fixture adapters using the same generic contract.
- Contract, component, security, integration, constitutional, and compatibility tests.
- One Docker qualification command that directly emits final evidence JSON.
- Complete Founder-ready, unmerged PR after all local pre-push gates pass.

### 4.2 Out Of Scope

- A new public API, customer-facing adapter endpoint, or standalone adapter service.
- Web, WhatsApp, mobile, payment, hiring, or employment lifecycle redesign.
- New professional skills, prompts, prices, providers, tools, or customer configuration policy.
- Agent self-admission, self-activation, authority expansion, evidence acceptance, or lifecycle control.
- Shared multi-artifact hosting, arbitrary plug-in loading in one process, marketplace distribution,
  or remote third-party adapter hosting.
- UAT, Production, customer traffic, provider credential issuance, environment activation, or spend.
- Changes to Class 1 constitutional documents or accepted reference architecture outside the explicit
  adapter amendment.

## 5. Contract Model

### 5.1 Adapter Identity And Descriptor

`describe` returns an immutable `AdapterDescriptorV1` containing:

- `protocolVersion` and supported compatible minor range;
- `professionalTypeId`, `professionalVersion`, and `artifactDigest`;
- `admissionContentDigest` and admitted PAC version/digest;
- supported Skill IDs and versions;
- input, output, configuration, goal, schedule, and result schema versions/digests;
- execution model support: `APPROVAL_GATE`, `PRE_AUTHORIZED`, or both as admitted;
- capabilities: planning, streaming, cancellation, Stop acknowledgement, resume, and result replay;
- maximum request size, supported content types, deadline limits, and health contract version.

Descriptor values must match the platform-owned admission snapshot exactly. A mismatch is
`ADAPTER_BINDING_MISMATCH`; Professional Runtime must not configure or execute the adapter.

### 5.2 Platform-Constructed Envelope

Every operation except unauthenticated container liveness receives an `AdapterInvocationEnvelopeV1`.
Professional Runtime constructs it from authenticated and admitted platform state. The adapter never
supplies these values as trusted facts.

| Field | Rule |
|---|---|
| `schemaVersion` | Exact adapter envelope major/minor |
| `tenantRef` | Opaque runtime-scoped tenant reference from authenticated workload context; never customer input |
| `relationshipId` | Exact Employment Relationship; required for customer work |
| `professionalTypeId` / `professionalVersion` | Must match descriptor and ACTIVE admission snapshot |
| `skillId` / `skillVersion` | Must match one admitted Skill Definition |
| `admissionContentDigest` / `artifactDigest` | Exact immutable activation binding |
| `customerContractDigest` | Exact accepted employment contract binding |
| `decisionSpaceVersion` | Exact active scope version; stale versions fail closed |
| `configurationRevision` / `goalRevision` | Exact effective customer records; nullable only where admitted operation permits |
| `invocationId` | Platform-generated UUID for one logical invocation |
| `idempotencyKey` / `payloadDigest` | Same key and digest replay prior outcome; divergent reuse fails |
| `ceDecisionRef` / `evidenceContextRef` | Opaque platform references; not evidence content or proof of final success |
| `deadline` | Absolute UTC deadline; expiry prevents new consequential dispatch |
| `traceparent` / `correlationId` | Structured observability without customer payload or secrets |
| `mode` | `TRIAL`, `LIVE`, or `PLANNING`; adapter cannot promote mode |

Domain payloads are separate typed fields validated against the admitted schema digest. Unknown major
versions fail closed. Unknown optional fields within a supported minor may be ignored only where the
compatibility policy explicitly permits it.

### 5.3 Operations

| Operation | Input | Success meaning | Mandatory denial/failure behavior |
|---|---|---|---|
| `describe` | Workload identity and optional negotiation range | Immutable descriptor returned | No descriptor synthesis from environment guesses |
| `health` | Workload identity for readiness; container probe for liveness | Process/runtime readiness only | Must not claim admission, provider, CE, billing, or customer readiness |
| `configure` | Envelope plus configuration/goal references and payload | Exact revisions validated/applied or prior outcome replayed | No relationship mutation, authority change, or unadmitted schema |
| `plan` | Envelope plus admitted planning input | Non-consequential proposal returned | No external side effect or LIVE promotion |
| `execute` | Envelope plus exact authorized skill input | Durable invocation accepted or terminal prior outcome replayed | No dispatch when Stop active, deadline expired, CE unavailable, scope stale, or binding mismatched |
| `status` | Envelope plus invocation identity | Current deterministic state returned | Cross-tenant/relationship lookup normalized and denied |
| `cancel` | Envelope plus invocation identity and reason category | Cancellation accepted or terminal outcome replayed | Preserve partial facts and evidence; do not release Stop |
| `emergencyStop` | Relationship-scoped stop envelope and stop evidence context | Affected work halted and attributable acknowledgement returned | Must remain available independently of ordinary execution dependencies |
| `resume` | New envelope with fresh same-tenant authority linked to stop evidence | New execution eligibility acknowledged | Never infer authorization from recovery or prior session state |
| `result` | Envelope plus invocation identity | Typed terminal/partial facts and evidence references returned | Adapter result is not platform or constitutional acceptance |

The transport ADR must accept the Section 5.3.1 profile before implementation. The implementation
must not expose adapter operations through the public Professional Runtime server and must not choose
an alternative listener, protocol, or route. If the ADR rejects the profile, this plan returns to
architecture revision before Platform IT receives the Work Contract.

### 5.3.1 Proposed Fixed Wire Profile For ADR Acceptance

To prevent Platform IT from choosing transport during implementation, this plan proposes one profile
for the required ADR to accept or return before source work:

- OpenAPI 3.1, HTTP/1.1, UTF-8 JSON, and RFC 9457 problem details over a private container-app/service
  endpoint; no public ingress, browser CORS, customer token, or provider callback ingress;
- short-lived audience-bound service JWT plus environment workload identity under ADR-046; production
  transport protection and mTLS behavior follow the accepted security contract;
- synchronous control responses with `202` only after Temporal accepts durable responsibility;
- ordered Server-Sent Events for optional result streaming from adapter to Professional Runtime;
- `Idempotency-Key`, `X-Correlation-ID`, W3C `traceparent`, absolute deadline, protocol version, and
  payload digest on every mutation;
- one adapter deployment and immutable OCI digest per admitted professional version in v1.

The proposed private operations are:

| Method and path | Operation | Required success |
|---|---|---|
| `GET /internal/v1/descriptor` | `describe` | `200 AdapterDescriptorV1` |
| `GET /health/live` | process liveness | `200` only when process loop is alive; no dependency claim |
| `GET /internal/v1/health/ready` | `health` | `200 AdapterHealthV1`; `503` when adapter cannot accept work |
| `POST /internal/v1/configurations:validate` | `configure` | `200 ConfigurationValidationV1`; validation does not become BP configuration truth |
| `POST /internal/v1/plans` | `plan` | `200 AdapterPlanV1`; no external side effect |
| `POST /internal/v1/invocations` | `execute` | `202 AdapterInvocationV1` or `200` replay |
| `GET /internal/v1/invocations/{invocationId}` | `status` | `200 AdapterInvocationV1` |
| `GET /internal/v1/invocations/{invocationId}/events` | stream | `200 text/event-stream` with monotonic events |
| `POST /internal/v1/invocations/{invocationId}:cancel` | `cancel` | `202` accepted or `200` terminal replay |
| `POST /internal/v1/relationships/{relationshipId}:emergency-stop` | `emergencyStop` | `200 AdapterStopAcknowledgementV1` after local halt |
| `POST /internal/v1/relationships/{relationshipId}:resume` | `resume` | `200 AdapterResumeAcknowledgementV1` after fresh authority validation |
| `GET /internal/v1/invocations/{invocationId}/result` | `result` | `200 AdapterResultV1`; `202` while non-terminal |

The ADR may reject this profile, but Platform IT cannot substitute another transport. Rejection sends
the package back to Enterprise and Solution Architecture for revision and Founder acceptance.

### 5.4 State Machine

```text
RECEIVED -> VALIDATING -> ACCEPTED -> RUNNING
RUNNING -> SUCCEEDED | FAILED | PARTIAL | CANCEL_REQUESTED | STOP_REQUESTED
CANCEL_REQUESTED -> CANCELLED | PARTIAL | FAILED
STOP_REQUESTED -> STOPPED | PARTIAL | FAILED
```

Rules:

- `ACCEPTED` means durable execution responsibility, not successful work or constitutional evidence.
- Only a valid transition may advance state; state version uses optimistic concurrency.
- Terminal outcomes are immutable and replayable.
- Timeout or transport loss is `UNKNOWN` to the caller until `status` reconciliation; it is never
  treated as success and never creates a second invocation.
- `emergencyStop` preempts planning, configuration, execution, streaming, and ordinary cancellation.
- Recovery does not resume work. `resume` requires a new invocation context and explicit authority.
- Adapter-local storage is ephemeral execution state. Platform truth and constitutional evidence
  remain in their owning services.

### 5.4.1 Durable State Ownership And Transaction Boundaries

| State | Authoritative owner | Durability rule |
|---|---|---|
| Admission, professional/skill version, customer contract, configuration and goal revisions | Business Platform PostgreSQL | Adapter receives exact references and validated payloads; it never writes owner records |
| Constitutional decision and evidence | Constitutional Engine ledger | CE record/decision reference exists before consequential dispatch or success projection |
| Invocation workflow, retry, cancellation, Stop signal, and unknown-outcome reconciliation | Professional Runtime Temporal workflow | Workflow ID derives from immutable invocation identity; Temporal acceptance precedes `202` |
| Queryable execution projection and idempotency outcome | Professional Runtime approved PostgreSQL schema | Additive, tenant-isolated, RLS-protected, optimistic state version; exact schema requires Data acceptance |
| Adapter working state | Isolated adapter memory/ephemeral volume | Reconstructable from the PR envelope and workflow; never sole durable truth |
| Customer-visible result and timeline | Business Platform projection | BP validates PR facts before customer projection; adapter output is never public truth directly |

There is no cross-service transaction. Professional Runtime atomically stores the idempotency
identity, canonical payload digest, initial invocation projection, and an outbox record in its
approved PostgreSQL schema. The outbox dispatcher starts a Temporal workflow whose deterministic
workflow ID is derived from the invocation ID, then records dispatch acknowledgement. Replayed outbox
delivery reaches the same workflow ID. Reconciliation may recover one prior outcome; it may not
manufacture authorization, evidence, result acceptance, or a new invocation identity.

Emergency Stop confirmation to the customer must not wait for adapter health. Professional Runtime
halts/terminates the affected workflow and adapter workload locally, records or buffers evidence under
ADR-031, and returns the existing Stop confirmation within the constitutional SLO. Adapter
acknowledgement is reconciled as execution evidence and cannot delay or negate the platform Stop.

### 5.5 Result And Event Contract

`AdapterResultV1` contains invocation identity, schema version, state, completion reason, typed output
blocks, cost/usage facts, tool/provider facts, evidence references, warnings, timestamps, and output
payload digest. It excludes customer bearer tokens, raw provider credentials, internal policy detail,
prompt/reasoning traces, tenant identifiers, and claims of constitutional success.

For streaming work, events are ordered by monotonic sequence and contain stable event ID, invocation
ID, event schema version, event type, partial flag, timestamp, payload digest, and typed payload.
Professional Runtime validates and persists/relays accepted facts. Unknown major event versions halt
projection and produce `ADAPTER_SCHEMA_UNSUPPORTED`; they never become customer-visible truth.

### 5.6 Error Contract

All errors have a stable code, correlation ID, retry classification, and privacy-safe detail. They do
not echo payloads, tenant identity, credentials, prompts, policy internals, or another relationship's
existence.

| Class | Required stable codes |
|---|---|
| Request | `ADAPTER_REQUEST_INVALID`, `ADAPTER_SCHEMA_UNSUPPORTED`, `ADAPTER_DEADLINE_EXPIRED` |
| Identity and scope | `ADAPTER_UNAUTHORIZED`, `ADAPTER_NOT_ACCESSIBLE`, `ADAPTER_BINDING_MISMATCH`, `ADAPTER_DECISION_SPACE_STALE` |
| Replay and state | `ADAPTER_IDEMPOTENCY_CONFLICT`, `ADAPTER_STATE_CONFLICT`, `ADAPTER_RESULT_UNRESOLVED` |
| Constitutional safety | `ADAPTER_CONSTITUTIONAL_UNAVAILABLE`, `ADAPTER_EXECUTION_DENIED`, `ADAPTER_STOPPED`, `ADAPTER_RESUME_DENIED` |
| Runtime | `ADAPTER_UNAVAILABLE`, `ADAPTER_PROVIDER_UNAVAILABLE`, `ADAPTER_INTERNAL_FAILURE` |

Only explicitly classified transient infrastructure failures are retryable. Constitutional denial,
binding mismatch, schema incompatibility, stale authority, idempotency conflict, and deterministic
adapter failure are not retryable without a changed authorized input.

## 6. Security, Isolation, And Operability

1. Professional Runtime is the only adapter caller. Browser, mobile, WhatsApp, Business Platform,
   AI Runtime, providers, and customer credentials cannot directly invoke adapter operations.
2. Caller and adapter authenticate with environment-specific workload identities and exact audience,
   operation, professional version, artifact digest, relationship scope, purpose, and expiry.
3. Customer bearer tokens and provider credentials are never forwarded as adapter authority.
4. Each admitted artifact runs in an isolated deployment with least-privilege network routes,
   read-only image, non-root identity, bounded CPU/memory, ephemeral writable storage, and no Docker
   socket or host filesystem access.
5. Tools/providers are reachable only through admitted, governed routes. Undeclared egress is denied.
6. Secrets arrive only as approved secret references and workload-bound retrieval; descriptors,
   results, logs, evidence, and qualification artifacts contain no secret values.
7. Stop has a dedicated bounded path and does not wait for model, provider, billing, or ordinary
   adapter health. The end-to-end constitutional Stop SLO remains at most 250 ms.
8. CE unavailability halts consequential adapter execution. Local stop still executes and its
   attributable record is buffered under ADR-031 rules.
9. Structured telemetry includes operation, protocol version, professional and skill opaque IDs,
   invocation/correlation IDs, state, latency, retry classification, and digest prefixes. It excludes
   customer payload, prompts, PII, credentials, and full security-sensitive artifacts.
10. Rollback selects a prior still-supported ACTIVE professional version and exact artifact digest.
    It never edits an ACTIVE admission, rewrites evidence, or silently migrates relationships.

## 7. Canonical Artifacts To Produce Or Amend

The accepted implementation Work Contract must freeze exact filenames. The expected owning artifacts
are:

| Artifact | Required change |
|---|---|
| `adr/ADR-NNN-agent-runtime-adapter-contract.md` | Transport, isolation, discovery, identity, invocation, streaming, and compatibility decision |
| `architecture/reference/components/professional-runtime.md` | Adapter gateway, resolver, lifecycle, Stop, reconciliation, and dependency responsibilities |
| `architecture/reference/api-specs/professional-runtime.openapi.yaml` | BP-to-PR fields and results required to bind exact adapter execution; no public adapter exposure |
| `architecture/reference/api-specs/agent-runtime-adapter-v1.openapi.yaml` | Private normative HTTP/JSON adapter wire contract after ADR acceptance |
| `architecture/reference/api-specs/schemas/agent-runtime-adapter-v1.schema.json` | Shared descriptor, envelope, operation, state, event, result, and error schemas |
| `architecture/reference/api-specs/schemas/agent-admission-contract-v1.schema.json` | Versioned adapter declaration and conformance-evidence reference, using compatible evolution rules |
| `infrastructure/workload-identity/registry.yaml` | Exact PR-to-adapter route grants only |
| `src/professional-runtime/` | Generic adapter gateway/client, descriptor verifier, resolver, orchestration, Stop, and result validation |
| `src/agent-adapters/runtime_contract/` | Language-neutral schema assets and Python reference adapter base; not a public platform service |
| `src/agent-adapters/digital_marketing/` | Digital Marketing fixture adapter package using only admitted domain contracts |
| `src/agent-adapters/trading/` | Trading fixture adapter package using only admitted domain contracts |
| `tests/fixtures/agent-runtime-adapter/` | Frozen descriptor, envelope, result, error, and cross-language golden vectors |
| `tests/contract/` | Schema, version, golden vector, compatibility, and generated drift tests |
| `tests/professional-runtime/` | Gateway, binding, state, idempotency, Stop, reconciliation, and failure tests |
| `tests/constitutional/` | Evidence First, Human Override, CE unavailable, and Decision Space tests |
| `scripts/qualify_agent_runtime_adapter_v1.sh` | One Docker-only final qualification and evidence producer |

No source path is authorized by this list. Before implementation, the Work Contract must verify the
accepted spec exists and explicitly authorize each runnable path under C-059.

## 8. Ordered Delivery Components

Do not split this delivery into intermediate PRs. Internal increments remain incomplete until the
whole adapter component, conformance evidence, and Founder-ready PR are complete.

| ID | Engineering action | Completion evidence |
|---|---|---|
| ARA-00 | Re-read authority, verify every Section 3.1 owner artifact is accepted, verify merged WC-079 state and actual repository gates, and create only the assigned branch. Copy frozen paths, versions, CCTs, commands, and stops into the implementation issue. | Every input resolves to an accepted path/commit; missing policy stops execution |
| ARA-01 | Run a no-mutation baseline of canonical schema/Compose rendering and one deliberately invalid adapter fixture to prove the validator is active. Do not repair architecture in this step. | Baseline result and existing unrelated failures are recorded before source change |
| ARA-02 | Implement the accepted admission declaration/readiness extension with adapter protocol, artifact/isolation profile, and conformance digest while preserving immutable WC-079 identity and lifecycle. | Valid fixture passes; missing, forged, stale, mismatched, and unsupported declarations fail deterministically |
| ARA-03 | Implement generic reference adapter descriptor, envelope validation, state machine, idempotency, deadlines, status, cancellation, Stop, resume, results, and privacy-safe errors. | Endpoint-focused examples cover every operation and principal negative path |
| ARA-04 | Implement Professional Runtime adapter gateway, exact descriptor/admission/artifact verification, durable orchestration, result/event validation, unknown-outcome reconciliation, and error mapping. | No professional-type branch exists; no dispatch precedes all guards |
| ARA-05 | Add workload identity, private routing, network isolation, resource bounds, secret references, observability, liveness/readiness, and environment-parameterized Compose/release configuration for demo, uat, and prod. | Direct non-PR access and undeclared egress are denied; config renders for all environments |
| ARA-06 | Implement Digital Marketing and Trading fixture adapters using the same base contract and only admitted domain schemas/configuration. | Both descriptors and all common operations pass without private platform lifecycle logic |
| ARA-07 | Integrate generic execution with existing conversation, approval-gate, PAAS, and Emergency Stop paths without changing BP public ownership. | Web/WhatsApp projections remain channel-neutral; Stop and cancellation remain distinct |
| ARA-08 | Add contract, unit, integration, security, compatibility, CCT, rollback, recovery, and performance tests. Do not run heavyweight Docker validation per small edit. | Test inventory maps every acceptance condition and failure path to a deterministic test |
| ARA-09 | Run one consolidated development validation: Docker preflight, Compose check, one smoke per changed service, then endpoint-focused and changed-slice tests. Repair evidenced failures and rerun only the failed focused slice. | Focused campaign passes; logs and resource evidence classify any retry |
| ARA-10 | Finalize intended commits, ensure clean HEAD, prune only disposable Docker artifacts if needed, calculate hashes, build qualified images once, and run the complete qualification command once. | Evidence JSON reports PASS against exact HEAD, image IDs, and report hashes |
| ARA-11 | Perform complete author review, bind review metadata to exact HEAD, validate repository commit/authorization/author-review gates and prepared PR body, then push once and open one unmerged PR. | Hosted checks pass and PR is ready for Founder review; no self-approval or merge |

## 9. Test And Acceptance Plan

### 9.1 Development Validation Policy

Docker testing is batched to avoid repeated environment startup and image rebuild cost. A developer
may use editor diagnostics and deterministic contract inspection while implementing ARA-02 through
ARA-08, but all executable tests remain Docker-only. After those implementation slices are complete,
ARA-09 runs one consolidated focused Docker campaign:

1. Check Docker daemon, Compose, free space, active containers, images, builders, and volumes.
2. Run `docker compose config --quiet` before builds or service startup.
3. Start each changed service once and run one health/contract smoke test per service.
4. Run endpoint-focused examples for all adapter operations and critical negative cases.
5. Run only changed-service contract, unit, integration, security, and CCT slices.
6. Capture logs and resource state before cleanup or any retry.
7. Retry unchanged code once only when evidence demonstrates daemon, network, registry, or capacity
   failure. Never retry deterministic contract, test, lint, coverage, build, or security failures.
8. Repair code/configuration defects and rerun only the failed focused slice.

Do not run full coverage, production builds, SBOM, Trivy, Gitleaks, or the complete deterministic
campaign during ARA-02 through ARA-09. Those run once in ARA-10 against finalized commits and reused
qualified images.

### 9.2 Endpoint-Focused Examples

The focused campaign must prove at minimum:

- exact `describe` negotiation and descriptor/admission/artifact match;
- `health` cannot claim admission or constitutional readiness;
- configuration replay and divergent-key conflict;
- planning causes no provider/tool side effect;
- execution accepts exact valid bindings and rejects each mismatched envelope field;
- unknown execution outcome reconciles by invocation ID without duplicate dispatch;
- status is tenant/relationship isolated and privacy-normalized;
- cancellation preserves partial output/evidence and does not release Stop;
- Emergency Stop preempts all active operations and meets its bounded acknowledgement behavior;
- resume fails without fresh authority linked to stop evidence;
- result/event schema, ordering, digest, and evidence-reference validation;
- CE unavailable, stale Decision Space, expired deadline, suspended admission, unavailable adapter,
  unsupported major, and provider failure all fail with the correct stable semantics;
- Digital Marketing and Trading pass through the same generic gateway with no type switch;
- Web and WhatsApp inputs resolve to the same employment, admission, configuration, and adapter identity.

### 9.3 Coverage And Quality Thresholds

- New/touched adapter and Professional Runtime logic: at least 90% line coverage and 80% branch
  coverage, unless a stricter repository gate controls.
- Every operation, state transition, stable error, authority denial, replay rule, schema compatibility
  rule, and Stop path has deterministic positive and negative coverage.
- Existing repository global thresholds may not be lowered, excluded, or baselined away.
- Emergency Stop retains the constitutional at-most-250-ms end-to-end requirement under normal and CE
  unavailable scenarios.
- No fixture, mock, LLM output, or transport success is accepted as evidence of admission,
  authorization, execution success, or customer outcome.

## 10. Docker Qualification And Cost Control

### 10.1 Preflight And Safe Capacity Recovery

The qualification script must first record:

```sh
docker version
docker compose version
docker system df
docker system df -v
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}'
docker volume ls
docker compose config --quiet
```

If free capacity is insufficient, preserve the before-state and remove only disposable artifacts:

```sh
docker image prune --force
docker builder prune --force --filter 'until=24h'
```

Never run `docker system prune`, `docker volume prune`, broad container pruning, or remove running,
pinned, evidence-bearing, database, or user-named images, containers, networks, or volumes. If safe
cleanup is insufficient, stop with a capacity blocker.

### 10.2 Immutable Image Identity And Reuse

The qualification command computes deterministic sorted input inventories:

```text
SOURCE_HASH = first 12 lowercase hex of SHA-256 over tracked adapter/PR source, tests, and schemas
CONFIG_HASH = first 12 lowercase hex of SHA-256 over normalized Compose, Dockerfiles, locks, workflows,
              workload grants, qualification script, and pinned tool configuration
IMAGE_TAG   = ara-v1-${SOURCE_HASH}-${CONFIG_HASH}
```

Build each changed service and test image once after final commits. Record image name, tag, image ID,
digest, platform, and build input hashes. Reuse the exact image IDs for smoke confirmation, focused
guard, complete tests, coverage, production build inspection, conformance campaign, SBOM, Trivy, and
evidence assembly. A relevant input change invalidates qualification and requires new final commits,
new hashes, one new image set, and a fresh complete run.

### 10.3 Evidence-First Failure Handling

Before cleanup or retry, capture:

```sh
docker compose ps --all
docker compose logs --no-color --timestamps <changed-service>
docker inspect <container-or-image>
docker stats --no-stream
docker system df
```

Record command, exit code, timestamps, image ID, and one classification: code/configuration,
assertion, schema/contract, security, capacity, daemon/network, registry, or external dependency.
Retry unchanged code once only for evidenced infrastructure failure. Deterministic failure requires a
repair, a focused rerun, finalized commits again, and then one fresh complete qualification.

### 10.4 One Final Qualification Command

Implementation must add:

```sh
./scripts/qualify_agent_runtime_adapter_v1.sh \
  --output test-results/agent-runtime-adapter-v1/qualification.json
```

The host shell may orchestrate only Docker/Compose, git, `jq`, and hashing utilities. All language
runtimes, tests, lint, schema validation, generators, coverage, builds, SBOM, and scanners execute in
repository-pinned containers. The command fails closed and writes evidence from observed command
results; it never writes a fabricated PASS after a failure.

In order, it performs:

1. Authority/input and clean finalized-HEAD checks.
2. Docker capacity/state capture, safe disposable cleanup if needed, and Compose rendering for demo,
   uat, and prod without mutating an environment.
3. Source/config inventory hashing and one build of every qualified image.
4. One smoke per changed service and a bounded endpoint-focused guard using the same images.
5. Full affected unit, contract, integration, workload identity, isolation, compatibility, migration
   if applicable, and constitutional test suites.
6. Full coverage and threshold enforcement.
7. Production builds/compilation and generated artifact drift checks.
8. Deterministic two-professional conformance campaign covering all operations, lifecycle, failures,
   Stop, cancellation, replay, rollback, and channel invariance.
9. SBOM generation from every exact qualified image.
10. Trivy HIGH/CRITICAL image and configuration scanning using repository-pinned policy/version.
11. Gitleaks history/diff scanning using repository-pinned policy/version.
12. Actual repository gates, including OpenAPI/proto/schema/YAML validation, generated drift,
    `scripts/gap_scanner.py`, C-059 commit checks, C-066 authorization checks,
    `scripts/validate_author_review.py`, and current workflow-defined authorization checks through
    their approved execution paths.
13. Evidence JSON assembly, schema validation, redaction check, and final PASS/FAIL derivation.

Evidence JSON contains at minimum plan/WC/issue identity, result, exact 40-character HEAD and base,
source/config hashes, image names/tags/IDs/digests, preflight/cleanup state, Compose environments,
smokes, endpoint examples, tests/counts, coverage, builds, fixture campaign, performance, authorization
denials, compatibility, Stop, rollback/recovery, SBOM paths/hashes, Trivy/Gitleaks report hashes, gate
commands/tool versions/exit codes, failure classifications, start/end times, and redaction result.
`PASS` is impossible unless every mandatory result binds to the same HEAD and image IDs.

### 10.5 Exact Repository Gate Command Forms

The executor must re-read the scripts and workflow pins at ARA-00 because repository truth may evolve.
At the current plan revision, the qualification command invokes these forms inside the appropriate
repository test image unless the command is explicitly host orchestration:

```sh
# Fast configuration and focused Python checks
docker compose config --quiet
docker compose --profile test-python run --rm test-runner-python \
  pytest tests/contract/ tests/professional-runtime/ tests/constitutional/ -v
docker compose --profile test-python run --rm test-runner-python \
  ruff check src/professional-runtime src/agent-adapters tests/contract tests/professional-runtime
docker compose --profile test-python run --rm test-runner-python \
  mypy src/professional-runtime src/agent-adapters

# PAC and repository contract drift
docker compose --profile test-python run --rm test-runner-python \
  python scripts/gap_scanner.py --report

# OpenAPI lint using the version pinned by .github/workflows/ci.yaml
docker run --rm -v "$PWD:/workspace" -w /workspace node:20 \
  npx --yes @stoplight/spectral-cli@6.15.0 lint --fail-severity error \
  architecture/reference/api-specs/business-platform.openapi.yaml \
  architecture/reference/api-specs/professional-runtime.openapi.yaml \
  architecture/reference/api-specs/agent-runtime-adapter-v1.openapi.yaml

# C-059 and C-065 body/HEAD validation in the repository Python test image
docker compose --profile test-python run --rm test-runner-python \
  python scripts/validate_c059.py --pr-body-file /workspace/test-results/agent-runtime-adapter-v1/pr-body.md \
  --base "$BASE_SHA" --head "$HEAD_SHA"
docker compose --profile test-python run --rm test-runner-python \
  python scripts/validate_author_review.py \
  --pr-body-file /workspace/test-results/agent-runtime-adapter-v1/pr-body.md --head "$HEAD_SHA"
```

The qualification script resolves `BASE_SHA` and `HEAD_SHA`, records every tool/image version, and
uses repository-pinned Trivy, Gitleaks, SBOM, language build, and coverage commands discovered from
the current workflows. It fails if a required tool is unpinned; it does not silently install `latest`.

At this plan revision, `scripts/pr_guard.py` is not present on `main` and is not a required gate.
After qualification PASS and actual author review, write the four checked author-review statements,
exact 40-character `Reviewed Commit`, and `Author Review Result: PASS` into the prepared PR body.
Re-run `validate_c059.py` and `validate_author_review.py` in the Docker test image against the same
base, HEAD, and body. The hosted C-059, C-065, and C-066 jobs remain authoritative after PR creation.
If a local PR guard is later merged, ARA-00 may add it only as an additional current repository gate;
it cannot replace these validators or become an unpinned external dependency.

## 11. LLM And Token-Cost Optimization

The delivery uses deterministic tools for truth and minimizes LLM context and retries:

1. Load only the accepted adapter plan/ADR, task-owning component/API sections, touched files, and
   nearest tests. Do not repeatedly load full agent specifications, claims, ADRs, logs, or generated clients.
2. Resolve symbols and existing patterns with targeted repository search before requesting model
   generation. Reuse accepted schemas, error shapes, workload identity, and orchestration helpers.
3. Group related edits by one delivery component. Do not invoke an LLM to diagnose every small edit.
4. Cache planning context by accepted-spec commit and source/config hash. Re-send only changed snippets,
   failed paths, and the local schema/test needed to repair an evidenced failure.
5. Use deterministic schema validation, contract examples, compiler output, test failures, and scanner
   reports as the diagnosis source. LLM opinion cannot convert FAIL, UNKNOWN, or UNAVAILABLE to PASS.
6. Use the least-cost approved model that can complete a bounded code/document task. Reserve frontier
   reasoning for architecture ambiguity, cross-service contract conflict, or security-critical repair.
7. Record optional development LLM model, prompt/template version, input/output tokens, cost, cache hit,
   retry reason, and affected component in qualification evidence without recording sensitive prompts.
8. Permit one model retry only for evidenced transport/provider failure with the same bounded request.
   A valid but incorrect result is repaired from deterministic feedback, not blindly regenerated.
9. Build images once and run heavyweight validation once. Docker environment faults are diagnosed from
   captured evidence before spending model tokens on source changes.

## 12. Commit, Review, Push, And PR Sequence

Use the branch and commit identity assigned by the implementation Work Contract. Never push to
`main`, self-approve, or self-merge.

1. Complete ARA-00 through ARA-08 and the consolidated focused campaign in ARA-09.
2. Repair all focused findings and rerun only affected focused checks.
3. Finalize the intended conventional commits. Every commit carries required `IB:`, `Constitutional:`,
  and any Work Contract-required CCT metadata under the repository's actual C-059 validator format;
  do not rely on a field not enforced by the current scripts.
4. Confirm clean HEAD and calculate final source/config hashes.
5. Run the complete qualification command once against finalized commits.
6. Make no source, schema, config, test, Dockerfile, workflow, tool, or qualification-script change
   after PASS. Any such change invalidates the evidence.
7. Prepare the PR body from `.github/pull_request_template.md` with objective, exact scope, acceptance
   matrix, spec-code traceability, qualification evidence path/hash, image IDs, tests, coverage, SBOM,
   Trivy, Gitleaks, rollback, unresolved risks, and Founder-only merge statement.
8. Perform mandatory author review of the complete diff and evidence against this plan, the accepted
   Work Contract, all acceptance conditions, security, compatibility, failure handling, operability,
   and rollback. Repair every finding; unresolved findings block PASS.
9. Bind the four completed author-review checks, exact 40-character `Reviewed Commit`, and PASS result
  in `test-results/agent-runtime-adapter-v1/pr-body.md` to the qualified HEAD.
10. Validate the prepared PR body and commit range with `scripts/validate_c059.py` and
   `scripts/validate_author_review.py` using the exact Docker forms in Section 10.5; run current
   authorization and all other actual pinned pre-push gates. Qualification evidence and review
   metadata must bind the same HEAD.
11. Push once, open one unmerged PR, and verify one-time hosted status snapshots. Do not watch/retry
    workflows blindly. If a hosted deterministic gate fails, diagnose, repair, refinalize commits,
    rerun affected focused checks and complete qualification, rebind review metadata, and push once more.
12. Mark the PR ready for Founder review only when every required hosted check succeeds and no review
    finding or blocker remains. Request Founder review and merge; do not approve or merge it.

The controlling delivery sequence is:

```text
DOCKER PREFLIGHT -> CONSOLIDATED FOCUSED TESTS -> FINAL COMMIT HISTORY
-> ONE COMPLETE QUALIFICATION -> PR METADATA VALIDATION -> PUSH ONCE
-> HOSTED PRE-CHECK SUCCESS -> FOUNDER REVIEW
```

## 13. Acceptance Matrix

| ID | Acceptance condition |
|---|---|
| ARA-ACC-01 | One versioned adapter contract supports all admitted professional types without professional-specific Professional Runtime branches |
| ARA-ACC-02 | Adapter remains private behind Professional Runtime and creates no new public or customer lifecycle service |
| ARA-ACC-03 | Descriptor and every invocation bind exact professional, skill, admission, artifact, contract, Decision Space, configuration, goal, tenant, and relationship context |
| ARA-ACC-04 | Only authenticated Professional Runtime workload identity can invoke adapter operations |
| ARA-ACC-05 | `describe`, `health`, `configure`, `plan`, `execute`, `status`, `cancel`, `emergencyStop`, `resume`, and `result` have deterministic meanings and stable errors |
| ARA-ACC-06 | Same idempotency key and payload replay one outcome; divergent reuse causes zero mutation or duplicate execution |
| ARA-ACC-07 | Timeout and transport loss reconcile to one invocation and never report or infer success |
| ARA-ACC-08 | Emergency Stop preempts all work, remains available during ordinary dependency failure, and never auto-resumes |
| ARA-ACC-09 | CE unavailable, stale Decision Space, expired authority, suspended admission, and binding mismatch fail before consequential dispatch |
| ARA-ACC-10 | Adapter outputs are execution facts; BP and CE retain customer projection and constitutional acceptance authority |
| ARA-ACC-11 | Domain schemas may specialize by admitted skill while envelope, lifecycle, errors, evidence references, and compatibility remain common |
| ARA-ACC-12 | Digital Marketing and Trading fixtures pass the same conformance suite without private admission, hiring, billing, or lifecycle logic |
| ARA-ACC-13 | Web and WhatsApp employment inputs resolve to the same adapter identity and execution semantics without direct adapter access |
| ARA-ACC-14 | One isolated immutable artifact deployment is used per admitted professional version; artifact substitution and undeclared egress fail |
| ARA-ACC-15 | Logs, errors, events, results, and evidence exclude secrets, tokens, prompts, PII, tenant leakage, and unsafe internals |
| ARA-ACC-16 | Version negotiation, supported minor evolution, unknown major rejection, rollback, suspension, and revocation are deterministic |
| ARA-ACC-17 | Focused tests are consolidated; full coverage, builds, SBOM, Trivy, Gitleaks, and full conformance run once after final commits |
| ARA-ACC-18 | Qualified images are hash-tagged, built once, and reused across tests, coverage, scans, and evidence capture |
| ARA-ACC-19 | Failure handling captures logs/resource state first and permits one unchanged retry only for evidenced infrastructure failure |
| ARA-ACC-20 | The Docker qualification command directly emits schema-valid evidence bound to exact HEAD and image IDs |
| ARA-ACC-21 | Repository actual gate scripts and pinned tools pass before push; author review and PR body bind the qualified HEAD |
| ARA-ACC-22 | One unmerged PR is opened and ready for Founder review; author neither approves nor merges it |

## 14. Rollback And Compatibility

- Adapter protocol uses semantic versioning. Additive optional fields may be minor-compatible only
  after producer and consumer behavior is specified and tested. Removed, renamed, retyped, reordered,
  or meaning-changing fields/states require a new major and explicit coexistence window.
- Admission binds the supported adapter protocol and conformance digest. An ACTIVE professional cannot
  change adapter major, artifact, descriptor identity, or schema digest in place.
- Rollback selects a previously admitted, still-supported professional version and exact artifact.
  Existing invocation/evidence history is retained and remains attributable.
- Suspension or revocation blocks new configuration/execution immediately. Active work follows the
  accepted stop/suspension policy and cannot silently continue, migrate, or claim success.
- Unknown outcomes reconcile by immutable invocation and idempotency identity before any retry.
- Database or durable-state changes, if later approved, must be additive, tenant-isolated,
  migration-tested, and rollback-safe. Constitutional evidence is never deleted or rewritten.
- Build once and promote the same accepted digests through separately authorized demo, uat, and prod
  gates. This plan authorizes no environment mutation.

## 15. Stops

- Stop before runnable implementation without Founder acceptance, an assigned Work Contract, and
  explicit current-session implementation authorization.
- Stop if WC-079 / PR 381 is not accepted and merged or its final contract differs materially from
  the assumptions in this plan.
- Stop if the adapter transport/isolation ADR or owner security/data/constitutional contracts are
  missing, stale, or contradictory.
- Stop rather than create a public adapter API, a new standalone platform service, a shared arbitrary
  plug-in host, or a remote third-party execution path.
- Stop rather than allow direct browser/channel access, agent self-admission, self-activation,
  Decision Space expansion, evidence forgery, lifecycle control, or automatic resume.
- Stop rather than trust request-body tenant/authority fields, customer tokens, LLM output, fixture
  claims, health status, or transport success as authorization or evidence.
- Stop when binding, schema, identity, admission, artifact, contract, scope, deadline, Stop, CE, or
  readiness state is unknown, stale, mismatched, unavailable, or unsupported.
- Stop rather than run host language tests, virtual environments, host package installs, unpinned
  scanners, or destructive Docker cleanup.
- Stop on deterministic test, contract, lint, coverage, build, security, or gate failure. Never hide a
  failure through retries, exclusions, threshold reductions, baseline replacement, or fabricated evidence.
- Stop if evidence, images, commits, author review, and PR metadata do not bind the same final HEAD.
- Never deploy, activate providers, create customer traffic, approve, merge, or claim customer proof
  under this plan.

## 16. Definition Of Done

Agent Runtime Adapter Contract v1 is complete only when:

- The Founder has accepted the adapter ADR and complete owner-approved specification package.
- The versioned private adapter wire/schema contract and compatibility policy are canonical.
- Admission readiness binds exact adapter protocol, artifact/isolation profile, and conformance evidence.
- Professional Runtime invokes adapters through one generic gateway with no professional-type logic.
- The reference adapter implements every v1 operation, state, replay, failure, Stop, resume, result,
  event, and privacy rule.
- Digital Marketing and Trading fixtures pass the same deterministic conformance suite.
- Exact admission, artifact, customer contract, Decision Space, configuration, goal, tenant, and
  relationship bindings fail closed on every mismatch or stale state.
- Workload identity, private routing, isolation, least privilege, secret handling, data minimization,
  observability, rollback, suspension, and revocation tests pass.
- Web and WhatsApp remain channel projections of one platform-owned employment relationship and do
  not contain private adapter lifecycle logic.
- One consolidated focused Docker campaign passes after implementation slices complete.
- Final commits are fixed before one complete qualification run.
- Full tests, coverage, production builds, deterministic conformance, SBOM, Trivy, Gitleaks, generated
  drift, constitutional checks, and actual repository gates pass against reused hash-tagged images.
- The qualification command directly emits valid PASS evidence bound to the exact final HEAD and image IDs.
- Mandatory author review has no unresolved finding and is bound to that same HEAD.
- Commit, authorization, author-review, and prepared PR metadata gates pass before push.
- One unmerged PR is pushed once, all required hosted pre-checks pass, and it is ready for Founder
  review and merge without self-approval or self-merge.

## 17. Author Review

**Result:** PASS - solution plan candidate; Founder acceptance and implementation authorization remain
separate gates.

INST-005 reviewed this complete plan against Section 4.7, the WC-079 plan pattern, Agent Employment
Experience boundaries, ADR-035/PAC separation, Professional Runtime universality, existing PAAS and
conversation execution contracts, Evidence First, Human Override, fail-safe CE behavior, workload
identity, privacy, compatibility, operability, rollback, Docker-only execution, cost controls, and the
requested PR completion sequence.

The review confirmed that admission certification is not duplicated, no new public or standalone
service is introduced, customer channels remain outside the adapter, authority is platform-constructed,
domain variation is confined to admitted schemas, Stop and cancellation remain distinct, one-artifact
isolation avoids premature shared-host architecture, validation is batched without weakening final
evidence, actual repository gates are discovered before push, and PR readiness remains separate from
Founder approval and merge. No unresolved in-scope plan finding remains.

| Author-review finding | Repair made in this revision |
|---|---|
| Transport selection was deferred to the implementation executor | Added one exact proposed HTTP/JSON/OpenAPI/SSE profile and route table; ADR rejection returns to architecture rather than Platform IT substitution |
| Canonical source and wire artifact paths contained alternatives | Fixed the OpenAPI, shared adapter, two fixture adapter, and golden-vector paths |
| Durable invocation, idempotency, and Stop transaction ownership was incomplete | Added authoritative state owners, Temporal/PostgreSQL boundaries, reconciliation, and non-blocking platform Stop behavior |
| Architecture acceptance work appeared inside Platform IT delivery tasks | Moved owner outputs to explicit preconditions and changed ARA-00/01 to verification and baseline only |
| Platform IT skills were not mapped to plan responsibilities | Added Skills 1-8 and 11-17 binding with exact obligations and escalation boundaries |
| Gate scripts were named without executable current-main commands | Added current Docker forms for `validate_c059.py` and `validate_author_review.py`; removed reliance on absent `pr_guard.py` |
| Commit metadata text overclaimed a fixed `CCTs-added` enforcement rule | Bound commit metadata to the repository's current C-059 validator and Work Contract instead of inventing enforcement |
# DMA Thin Vertical Slice And Agent Image Proof - Executable Delivery Plan

**Office:** Solution Architect (INST-005)
**Work Contract:** WC-089
**Status:** OWNER-REVIEWED PLAN - SECURITY PASS; FOUNDER ACCEPTANCE PENDING; IMPLEMENTATION UNAUTHORIZED
**Concept:** `architecture/dma-agent-image-concept.md`
**Delivery unit:** One real DMA image version serving isolated customer instances through Skills 0/1/2
**Reference architecture:** exact-six platform release tuple plus private admitted adapter workload images outside that tuple
**Dependencies:** WC-079, WC-080, WC-087 and WC-088 merged; ADR-035 and ADR-049 accepted
**Constitutional basis:** C-001, C-023, C-026, C-035, C-049, C-059, C-065, C-071, C-079

## 1. Objective

Deliver one bounded Digital Marketing Agent release that proves the approved type-image/customer-
instance model without changing WAOOAW's six-image platform boundary. One immutable admitted DMA
professional version and OCI digest serves multiple customer-specific trial or hired instances. Each
instance retains its own tenant, relationship, `agentInstanceId`, contract, mode, goals, configuration,
Skill versions, Decision Space, evidence, usage, work and lifecycle.

Release 1 implements only:

1. `CUSTOMER_PROFILING` - customer-confirmed minimum profile;
2. `MARKET_RESEARCH` - source-cited maturity report and needs heat map; and
3. `CONTENT_STRATEGY` - customer-approved campaign brief and 30-day content calendar.

The implementation must close reusable image identity, instance binding, work/result, usage, Stop,
readiness, isolation, compatibility and qualification gaps. It must not make shared platform code
understand DMA semantics or introduce a new service.

## 2. Required Outcome And Boundaries

```text
CUSTOMER EMPLOYMENT RELATIONSHIP + IMMUTABLE AGENT INSTANCE
  -> BP AUTHORIZES EXACT SKILL WORK
  -> CE RECORDS REQUIRED DECISION/EVIDENCE
  -> PR RESOLVES EXACT ADMITTED DMA IMAGE DIGEST
  -> DMA EXECUTES ONE TYPED SKILL WITHOUT PLATFORM AUTHORITY
  -> PR VALIDATES RESULT, USAGE, STOP AND EVIDENCE REFERENCES
  -> BP PROJECTS CUSTOMER-SAFE PROGRESS, APPROVAL AND RESULT
  -> WBE ATTRIBUTES OBSERVED USAGE TO THE EXACT INSTANCE/INVOCATION
```

| Boundary | Required owner | Fixed rule |
|---|---|---|
| Customer lifecycle and truth | Business Platform | Trial/hire, instance, Skill state, goals, approvals and results remain platform-owned |
| Authority and evidence | Constitutional Engine | Consequential work follows Evidence First; adapter output is never constitutional acceptance |
| Runtime lifecycle | Professional Runtime | One generic WC-080 gateway; no professional-type switch |
| Domain behavior | DMA image | Interpret only admitted Skill schemas; no admission, identity, billing or lifecycle mutation |
| AI/tool access | AI Runtime and CTG | DMA declares need; platform authorizes and dispatches; no direct agent Internet/provider route |
| Credential custody | oauth-vault | Release 1 carries no customer provider credential |
| Usage/economics | WBE | Reserve/attribute platform-observed usage; adapter cannot set price or debit truth |

## 3. Entry Gates And Owner Inputs

Implementation is blocked until every row is accepted and bound by exact path, version and commit.

| Input | Required state | Executor validation |
|---|---|---|
| Concept and this plan | Founder accepted | Exact commit and unchanged Skills 0/1/2 scope |
| WC-079/080/087/088 | Merged | Admission, adapter, instance and Skill decisions available on implementation base |
| ADR-035 and ADR-049 | Accepted/current | PAC remains signals; adapter remains private with one isolated deployment per admitted type + version + digest tuple |
| Solution contracts | INST-005 accepted | Skill schemas, work/result contract and instance binding deterministic |
| Enterprise review | INST-004 accepted or findings recorded | Six-image boundary and no-new-service decision preserved |
| Security contract | INST-007 PASS - 2026-09-10 | Image trust, workload/tenant/instance/mode binding, anti-replay, egress, secret, privacy, abuse and Stop controls fixed; implementation replaces registry/configuration/test drift with the exact ADR-049 audience without alias or fallback |
| Data contract | INST-006 accepted | Ownership, lineage, retention, erasure and isolation shapes fixed |
| Implementation Work Contract | Founder authorized in session | Exact branch, paths, tests, CCTs, environments and command named |

### 3.1 Readiness Gap Register

| Gap | Required closure | Owner | State |
|---|---|---|---|
| DMA-GAP-01 Canonical Skill coordinates | Freeze IDs, SemVer and schema digests for Skills 0/1/2; reject fixture aliases without explicit mapping | Solution Architecture | OPEN |
| DMA-GAP-02 Agent instance binding | Add immutable `agentInstanceId` to every customer-scoped adapter operation, signed delegation, replay scope and result lineage | Solution + Security | OPEN |
| DMA-GAP-03 Running-image proof | Verify trusted signature and provenance attestation and bind source commit, build identity, SBOM, conformance evidence, admission, resolved deployment and runtime-reported OCI digest; replace fixture digests and reject tags or unverifiable/mismatched links | Enterprise + Security + Platform | OPEN |
| DMA-GAP-04 Work and result contract | Freeze assignment, progress, approval, partial, terminal result, review and stable failure semantics, including immutable event/result lineage and optimistic concurrency | Solution Architecture | OPEN |
| DMA-GAP-05 Skill data ownership | Apply Section 5.7 ownership, revision, lineage, retention, erasure and legal-hold obligations to profile, research source/report, strategy and approval contracts | Data Architecture | DATA CONTRACT FIXED - implementation artifacts remain gated |
| DMA-GAP-06 Usage attribution | Freeze immutable reservation and observed-usage facts for tenant/relationship/instance/Skill/work/invocation with idempotent reconciliation | Solution + WBE owner | OPEN |
| DMA-GAP-07 Tool and egress route | Release 1 public research uses purpose-bound governed platform tools only; inherit WC-080 default-deny ingress/egress and metadata denial; define degraded behavior and source evidence | Security + AI owners | OPEN |
| DMA-GAP-08 Stop under real work | Prove active and queued DMA work halts, emits no late result and needs fresh-authority future invocation | Solution + Constitutional owner | OPEN |
| DMA-GAP-09 Resource and failure isolation | Apply WC-080's accepted request-size, replica, execution, queue, filesystem and runtime-hardening limits; prove limit-plus-one denial and Stop reserved capacity without choosing infrastructure here | Security + Platform owners | OPEN |
| DMA-GAP-10 Additive Skill release | Define compatibility, old-instance continuity and rollback for a later Skill/image version | Solution + Enterprise | OPEN |
| DMA-GAP-11 Adapter audience consistency | Apply ADR-049 to the existing distinct versioned adapter IDs: DMA is `urn:waooaw:service:agent-runtime-adapter:digital-marketing-local-service:3.1.0` and trading is `urn:waooaw:service:agent-runtime-adapter:trading-fo-crypto:1.8.0`; replace registry/configuration/test drift synchronously without alias or fallback; keep professional version and OCI digest as separate admission bindings | Enterprise + Security + Platform | ARCHITECTURE RECONCILED; SECURITY PASS - Founder authorized 2026-09-10; implementation repair not executed |

## 4. Scope

### 4.1 In Scope

- One DMA professional type/version and immutable admitted image digest.
- Skills 0, 1 and 2 only, with typed versioned input, output, configuration and result contracts.
- `agentInstanceId` binding across BP, PR and private adapter operations.
- Customer-safe assignment, progress, approval, partial result, terminal result and review projection.
- Platform-governed AI/tool calls, source citation and deterministic degradation.
- WBE reservation/usage attribution including zero-priced trial use; no pricing redesign.
- Image identity/attestation verification through existing admission and activation ownership.
- Real cancellation and Emergency Stop under queued and active DMA work.
- Liveness/readiness, privacy-safe telemetry, bounded execution and failure isolation.
- Two-tenant/two-instance conformance and one same-tenant/two-instance proof.
- Additive later-Skill compatibility demonstration using a contract fixture, not a fourth real Skill.
- Docker-only focused and final qualification with exact image/commit evidence.

### 4.2 Out Of Scope

- Skill 1b or Skills 3 onward, including GBP optimization and content publishing.
- Customer provider OAuth, social login, authenticated Google/Meta data or direct provider writes.
- Paid advertisements, spend, checkout, subscription, refund or wallet-policy changes.
- Production, customer traffic, provider activation, DNS or environment mutation.
- One image/container per customer, shared multi-professional host or third-party remote adapter.
- New platform service, framework, database technology or reference-architecture redesign.
- New business capability, DMA persona rewrite, broad prompt redesign or quality-learning system.

## 5. Contract Model

### 5.1 DMA Package And Existing Descriptor Binding

The WC-080 `AdapterDescriptorV1` remains common and is not extended with a DMA-specific lifecycle or
transport contract. Existing common descriptor fields and the WC-079 admission snapshot bind:

PAC coordinates are admission compatibility metadata only; the adapter does not become a PAC signal
consumer or gain a platform-signal channel under ADR-035.

- exact professional type/version and OCI digest;
- verified signature, provenance attestation, source commit, build identity and SBOM evidence;
- exact adapter protocol and PAC versions;
- exact Skill 0/1/2 IDs, SemVer and input/output/configuration/result schema digests;
- supported execution models and honest degradation modes;
- declared AI/tool capabilities by Skill and purpose;
- no-direct-egress and no-customer-provider-secret declarations;
- resource profile identifier and conformance evidence digest.

The descriptor reports facts; admission and activation decide whether those facts are accepted. Before
readiness or execution, PR verifies the trusted signature/attestation chain and equality among the
attested artifact, admission snapshot, activation resolution, descriptor and runtime-reported OCI
digest. A mutable tag, missing proof, untrusted issuer or mismatch fails closed; a descriptor claim
alone is not running-image proof.

### 5.2 Customer-Scoped Invocation Binding

Every customer-scoped operation must bind the WC-080 envelope plus `agentInstanceId`. Equality is
required across authenticated platform state, Employment Relationship, signed PR delegation,
invocation envelope, active admission and result lineage. Customer payloads cannot supply trusted
identity. The delegation also binds trial/live mode and inherits WC-080's single-use `jti`, 60-second
maximum lifetime, replay retention and fresh-delegation retry rules. Replay scope includes caller,
audience, operation, tenant, relationship, agent instance, mode, invocation, payload digest and
idempotency identity. A missing, stale, replayed or mismatched binding fails before domain parsing and
cannot disclose whether the protected tenant, relationship, instance or invocation exists.

### 5.3 Skill Contracts

| Skill | Required input shape | Required output shape | Authority transition |
|---|---|---|---|
| Customer Profiling | Existing registration reference, current confirmed/inferred/missing fields, account-mode answer and expected revision | Proposed field changes, provenance, confidence class, missing fields and confirmation summary | Only explicit customer confirmation may produce authoritative profile revision |
| Market Research | Confirmed minimum profile reference, public research targets, allowed sources, deadline and prior partial state | Cited observations, unavailable sources, maturity dimensions, score rationale, needs heat map, limitations and report digest | Report remains proposed until customer review; named competitor display needs confirmation |
| Content Strategy | Confirmed profile, reviewed research report, approved platform mix constraints and strategy horizon | Campaign brief, outcome hypothesis, audience, platform recommendations, 30-day calendar, claims/evidence and approval summary | No content generation/publishing until customer approves the brief; Release 1 stops at approved plan |

Unknown fields do not become facts. Every output distinguishes observation, inference, proposal,
customer-confirmed fact and unavailable information. Model text is never accepted as a source.

### 5.3.1 Skill Record Ownership And Revision

- BP owns durable customer-facing profile, research report, strategy and customer decision records.
  DMA outputs are proposed invocation results and cannot mutate those records directly.
- Profile observations and inferences retain provenance and confidence separately from confirmed
  fields. Confirmation creates a new immutable profile revision; it does not rewrite prior proposals.
- Research source records retain source reference, retrieval/observation time, claim linkage and
  availability status. Citations resolve claims to source records. Partial reports are durable,
  explicitly non-terminal results and are never silently promoted to reviewed reports.
- Strategy drafts bind exact confirmed-profile and reviewed-report revisions. Approve, reject and
  revise decisions append customer-attributed decision records; approval does not rewrite the draft.
- Every customer record is authorized under the authoritative
  `tenantId + relationshipId + agentInstanceId` scope and has an opaque immutable record identity plus
  revision/version. Tenant,
  relationship and instance values are binding dimensions, not a customer-selectable composite key.

### 5.4 Work Lifecycle

```text
ASSIGNED -> PLANNING -> RUNNING -> AWAITING_CUSTOMER
AWAITING_CUSTOMER -> RUNNING | REJECTED | CANCELLED
RUNNING -> PARTIAL | SUCCEEDED | FAILED | CANCELLED | STOPPED
```

- `ASSIGNED` means BP authorized a bounded work item, not execution authority.
- PR obtains exact CE authority and durable invocation responsibility before dispatch.
- `AWAITING_CUSTOMER` carries no automatic approval and pauses consequential continuation.
- Partial output preserves cited facts and limitations but is not silently promoted to success.
- Terminal facts are immutable and replayable by invocation identity.
- Explicit Emergency Stop dominates every ordinary state and remains latched.
- Work events append under one stable work-item identity and expected revision. Each invocation binds
  the work item, logical command/idempotency identity, attempt, exact input revisions and predecessor
  invocation when applicable. Progress and partial events never replace a terminal result; accepted
  terminal results are immutable, and late or conflicting terminal outcomes are rejected and retained
  only as reconciliation evidence under the owning policy.

### 5.5 Usage And Cost Facts

Before a cost-bearing AI/tool dispatch, the platform obtains a WBE reservation or an explicit
zero-priced trial allowance. After execution, platform-observed usage records carry tenant,
relationship, `agentInstanceId`, professional/Skill versions, invocation, provider/tool class,
quantity, unit, reservation reference, observed timestamp and evidence reference. Adapter estimates
may be diagnostic only; they cannot debit, price or settle.

Reservation and observed-usage facts are WBE-owned immutable records. They also reference the stable
work item and logical idempotency identity so retry and unknown-outcome reconciliation can reuse or
close the original reservation and cannot create duplicate attribution. Corrections append a linked
adjustment/reconciliation fact; they do not overwrite observed history.

### 5.7 Data Lineage, Lifecycle And Evidence Boundaries

1. Durable lineage connects customer record revision -> work item -> invocation/attempt -> exact
  input revisions -> partial or terminal result -> customer decision, plus CE evidence and WBE
  reservation/usage references. Cross-owner links use opaque identifiers, versions and digests; no
  owner copies another owner's authoritative payload as its own truth.
2. CE evidence and qualification/audit proof contain minimum attribution, classifications, opaque
  references and payload/proof digests. Customer profile, research, strategy, prompts, citations and
  report bodies remain in the owning customer-data boundary and are not duplicated into evidence.
3. BP defines retention and erasure disposition for customer payload records and source/citation
  content. Erasure propagates to eligible projections and ephemeral copies while preserving scoped
  tombstones, non-reversible digests and minimum immutable ledger attribution required by accepted
  policy. A legal hold records scope, authority and release, suspends eligible destruction, and does
  not broaden access or create a new payload owner.
4. CE evidence, immutable work/result events and WBE reservation/usage facts follow their owning
  retention rules and are not rewritten by customer erasure. References to erased payload resolve to
  an erased/tombstoned state rather than resurrecting content or breaking lineage.
5. Repeated commands and invocations reconcile by owner-scoped idempotency identity. Revision-bearing
  writes require the expected prior revision; stale or concurrent confirmation, approval, result or
  reconciliation attempts fail deterministically or return the already-recorded outcome.
6. Contract and record versions coexist for the supported window. Readers preserve historical
  meaning and reject unsupported majors; migrations are additive, restartable, tenant-isolated and
  auditable, with pre/post invariants and no in-place reinterpretation of immutable events/results.
  Rollback restores compatible readers/writers or an already admitted tuple; it never reverses a
  committed migration by deleting history. Incompatible durable changes require a forward fix or a
  separately governed compensating migration under ADR-011.

### 5.6 Errors And Degradation

Reuse WC-080 stable adapter errors. DMA domain errors add only versioned detail codes under the common
problem shape: `DMA_PROFILE_INCOMPLETE`, `DMA_SOURCE_UNAVAILABLE`, `DMA_SOURCE_NOT_ALLOWED`,
`DMA_CITATION_INVALID`, `DMA_RESEARCH_PARTIAL`, `DMA_STRATEGY_INPUT_STALE`, and
`DMA_CUSTOMER_CONFIRMATION_REQUIRED`. Degradable research returns explicit unavailable sources and
limitations. Required profile persistence, authority, instance binding, evidence, reservation and
approval failures stop the operation. Public and cross-scope denials expose only a stable normalized
class, correlation reference and safe retry/reconciliation guidance; they reveal no protected
existence, identity, topology, policy, digest, provider or credential detail.

## 6. Security, Privacy And Isolation Requirements

1. Only Professional Runtime invokes DMA through ADR-049 private mTLS identity, exact registered
  audience and route grants. Unknown identities, audiences, routes and contract majors fail closed.
2. Signed authority binds issuer/subject, `jti`, operation, method/route, environment, tenant,
  relationship, agent instance, trial/live mode, professional/Skill versions, artifact/admission,
  payload digest, invocation, deadline, purpose, Decision Space and idempotency identity.
3. DMA has no customer bearer token, customer/provider secret value, platform database credential or
  direct CE/WBE access. Customer secrets remain customer data; any future provider secret remains in
  oauth-vault and is usable only by its admitted workload/purpose route. Release 1 requests no such secret.
4. Ingress and egress inherit WC-080 Section 6.1 deny-by-default semantics in every qualified
  rendering. Only PR and the local liveness probe may ingress; only environment DNS, approved OTLP
  and explicitly admitted purpose-bound governed tool destinations may egress. Metadata, host,
  database, CE-ledger, sibling workload, Docker socket, wildcard and direct Internet routes fail.
5. Profile, research and strategy payloads remain erasable customer data. Constitutional evidence and
  qualification proof carry only opaque references, digests, classifications and minimum attribution,
  never customer content, prompts, PII or a duplicate proof payload.
6. Logs, traces, metrics, errors and scan/qualification output contain bounded operation/state,
  opaque correlation/invocation references, latency, retry/deny class and digest prefixes only; they
  exclude customer content, prompts, raw URLs or headers, tenant/relationship/instance identifiers,
  credentials, signatures, attestations and full digests. Labels cannot contain protected high-cardinality data.
7. Instance-local mutable state is ephemeral, erased between invocations and cannot be reused across
  customers, relationships, instances, modes or replicas.
8. Stop has reserved capacity, bypasses ordinary queues and provider/tool dependencies, and is tested
  within the constitutional SLO during CPU/memory pressure, full execution and request queues,
  provider/tool outage, CE outage and adapter unavailability. No late result publishes; explicit Stop
  remains latched and resume requires fresh authority.
9. WC-080 Section 6.1's accepted limits apply: 32 KiB aggregate headers; 1 MiB
  configure/plan/execute bodies; 64 KiB cancel/Stop/resume bodies; JSON depth 32; 256 KiB strings;
  10,000 array items; 64 KiB SSE events; 1 MiB other responses; and per replica 2 vCPU, 2 GiB memory,
  1 GiB ephemeral storage, 128 processes, 1,024 files, 32 in-flight requests, four executions and
  queue depth 32. Limit-plus-one fails before domain work. Runtime remains non-root, read-only,
  capability-dropped, no-new-privileges and runtime-default seccomp with no host namespaces/devices
  or executable writable mounts. This plan inherits accepted limits; it does not choose infrastructure.
10. Every cross-tenant, cross-relationship, cross-instance and cross-mode denial is privacy-normalized,
   produces zero mutation/tool use/evidence/usage, and is covered by deterministic negative tests.
11. Trial authority cannot be replayed or promoted into live work. Trial and live state, delegation,
   queues, idempotency and usage remain mode-bound; Release 1 trial and live execution both prohibit
   provider credentials, external publication and spend.
12. Final qualification generates an SBOM and runs pinned secret, dependency, SAST, license,
   configuration and OCI image scans. Accepted repository thresholds block PASS; findings are not
   waived, hidden by retries or reduced by changing policy in this Work Contract.

## 7. Canonical Artifacts Expected From Implementation

The implementation issue must freeze exact paths after reconciling repository truth. Expected owners:

| Artifact class | Required content |
|---|---|
| DMA package manifest/schema | Professional/image identity, exact three Skills, schema digests, tools, resource profile and conformance reference |
| Skill schemas/golden vectors | Valid, boundary and invalid examples for each input/output/result |
| Agent adapter OpenAPI/schema | Add instance binding and package references without DMA-specific common lifecycle fields |
| Business Platform API | Work assignment/projection and approval fields required by the customer journey |
| Professional Runtime API/component | Generic instance-bound dispatch, progress, result, usage and Stop integration |
| DMA adapter package | Real Skill 0/1/2 behavior only |
| WBE integration contract | Reservation/allowance and immutable observed-usage attribution |
| Workload registry/policy | Exact PR-to-DMA route and governed tool routes; no wildcard egress |
| Tests/fixtures | Two tenants, three instances, partial provider failure, replay, saturation and later-Skill compatibility |
| Qualification script | One Docker-only evidence producer for WC-089 |

This planning list authorizes no runnable path. The implementation Work Contract must perform the
C-059 existence/approval check and enumerate every source/configuration path after Founder authority.

### 7.1 Current Repository Anchors And Fixture Reality

These are current anchors, not permission to edit them. The implementation issue must bind their
exact base commit and replace every `TO FREEZE` entry with an owner-accepted path before authorization.
An executor must not choose a missing contract, fixture shape or persistence path during implementation.

| Slice | Current repository anchor | Reality the implementation issue must preserve or close |
|---|---|---|
| Exact-six plus admitted workloads | `docker-compose.yml`; `architecture/reference/components/manifest/` | The `agent-runtime-adapter` profile currently declares both DMA and trading adapter workloads. Both remain outside the exact-six release tuple. WC-089 may explicitly build/start DMA only and must assert that enabling the profile does not change exact-six membership, promotion or rollback evidence; trading is unchanged and is not a WC-089 deliverable. |
| Common adapter contract | `architecture/reference/api-specs/agent-runtime-adapter-v1.openapi.yaml`; `architecture/reference/api-specs/schemas/agent-runtime-adapter-v1.schema.json`; `src/agent-adapters/runtime_contract/`; `src/professional-runtime/adapter_gateway.py` | `AdapterInvocationEnvelopeV1` has no `agentInstanceId`; the OpenAPI remains PR-only and generic. |
| DMA fixture | `src/agent-adapters/digital_marketing/adapter.py`; `tests/fixtures/agent-admission/digital-marketing-local-service-v3.1.0.json` | The handler returns one generic `CAMPAIGN_PLAN`; digests are placeholders; only `LOCAL_CAMPAIGN_MANAGEMENT` and `LOCAL_CONTENT_PLANNING` are declared. `tests/fixtures/agent-runtime-adapter/` does not exist. |
| Adapter/PR tests | `tests/contract/test_agent_runtime_adapter_contract.py`; `tests/professional-runtime/test_agent_runtime_adapter.py`; `tests/constitutional/test_agent_runtime_adapter_cct.py` | Existing tests prove WC-080 common lifecycle and invalid admission behavior, not Skills 0/1/2, instance binding, two DMA versions or customer work. |
| BP instance and workspace | `src/business-platform/Services/EmploymentRelationshipService.cs`; `src/business-platform/Controllers/RelationshipWorkspaceController.cs`; `tests/business-platform.Tests/EmploymentRelationshipServiceTests.cs`; `tests/business-platform.Tests/RelationshipWorkspaceControllerTests.cs`; `architecture/reference/api-specs/business-platform.openapi.yaml` | BP already creates `AgentInstanceId` and exposes relationship workspace patterns. DMA work/profile/research/strategy records and owner-accepted persistence/migration paths are `TO FREEZE`; they may not be inferred from controller shape. |
| WBE | `src/billing-engine/wallet/`; `src/billing-engine/meter/`; `src/billing-engine/reconciliation/`; `src/billing-engine/relationship_workspace.py`; matching `tests/billing-engine/` tests | Reservation and usage primitives exist, but the owner-accepted instance/Skill/work/invocation attribution contract and any additive persistence path are `TO FREEZE`. Adapter output is not a billing fact. |
| Web and generated client | `web/components/relationships/RelationshipWorkspace.tsx`; `web/components/relationships/RelationshipWorkspace.test.tsx`; `web/lib/api/generated/`; `web/scripts/generate-api.sh` | Generate once only after the BP OpenAPI is stable, then test and commit the generated drift as one component. Do not hand-edit generated files or regenerate after every backend edit. |
| Identity and qualification | `infrastructure/workload-identity/registry.yaml`; `scripts/qualify_agent_runtime_adapter_v1.sh`; `scripts/prepare_pr_body.py`; `.github/workflows/ci.yaml` | WC-080 qualification is a reusable pattern, not WC-089 proof. The ADR-049 audience is reconciled; implementation must update registry, configuration and tests synchronously and prove old or wrong audiences fail without alias or fallback. The WC-089 qualification script does not yet exist and is created only after authorization. |

Missing fixtures to freeze before implementation are: canonical Skill 0/1/2 schemas and valid,
boundary and invalid golden vectors; two tenants with three instances including same-tenant separation;
slow/queued work and Stop sentinels; governed-tool timeout, 429, invalid-source and partial-result
vectors; replay and stale-revision vectors; privacy-redaction sentinels; and two supported DMA admission
snapshots for additive compatibility and rollback. The second snapshot may declare a non-executable
future Skill contract, but no fourth Skill handler or domain output is permitted.

## 8. Ordered Work Components

Every component is mandatory. The executor updates progress after each focused check but avoids full
Docker rebuilds until the specified campaign.

### 8.1 Implementation Edit And Check Ledger

The implementation issue must copy this ledger, replace `TO FREEZE`, and name exact test selectors.
All language runtimes, generators, tests and scanners run through Compose or pinned `docker run` tools;
host commands are limited to Git, hashing and read-only Docker inspection. Reuse the existing
`test-runner-python`, `test-runner-dotnet` and `test-runner-ts` images and their caches. Rebuild only
when a Dockerfile, lock/requirements input or copied image source changes.

| Component | Bounded edit set | Cheapest disconfirming Docker check before the next edit |
|---|---|---|
| DMA-00 | No runnable edit; freeze Section 7.1 paths, owner inputs, commits and fixtures | Compose render; existing contract smoke; `pytest tests/contract/test_agent_runtime_adapter_contract.py -q` in `test-runner-python` with one copied invalid admission fixture |
| DMA-01 | Common descriptor/admission schema only where owner-approved; DMA package contract and frozen golden fixtures; DMA descriptor fixture | Focused JSON Schema/admission/descriptor tests in `test-runner-python`; no service stack and no rebuild unless adapter image inputs changed |
| DMA-02 | Common envelope/OpenAPI, runtime contract and `adapter_gateway.py`; nearest contract/PR/CCT tests | Focused `tests/contract/test_agent_runtime_adapter_contract.py`, `tests/professional-runtime/test_agent_runtime_adapter.py` and named instance-binding CCT selectors in `test-runner-python` |
| DMA-03..05 | `src/agent-adapters/digital_marketing/` plus owner-frozen Skill contract/fixture paths; BP-owned write paths only after Data-owned paths are frozen | Per-Skill deterministic contract/unit fixtures first; then named BP stale/revision selectors in `test-runner-dotnet`; no AI/provider call until deterministic checks pass |
| DMA-06 | `RelationshipWorkspaceController`, owner-frozen BP work service/model path, BP OpenAPI, relationship workspace component/test and generated client | Named `RelationshipWorkspaceControllerTests` filter in `test-runner-dotnet`; after OpenAPI stabilizes, run `pnpm generate:api`, generated-drift check and the single relationship workspace Jest file once in `test-runner-ts` |
| DMA-07 | Owner-frozen CE/PR/WBE integration paths; existing wallet, meter, reconciliation and relationship-workspace tests | Named WBE reservation/usage/replay selectors in `test-runner-python`, followed by only the cross-service invariant slice |
| DMA-08 | Existing adapter/runtime Stop paths plus frozen slow, queue, limit and redaction fixtures | Named adapter/PR Stop and limit selectors first; one reused-image DMA service campaign only after unit/contract checks pass |
| DMA-09 | Admission/compatibility contracts and two frozen DMA admission snapshots; no future-Skill implementation | Contract compatibility selectors in `test-runner-python`; start no provider and rebuild no unrelated platform image |
| DMA-10 | `scripts/qualify_dma_thin_vertical_slice.sh` focused campaign path and schema-valid report | One consolidated focused campaign using the already built image IDs; capture evidence before repair or retry |
| DMA-11 | Final qualification/report, mandatory PR metadata and only required existing governance evidence | One final Docker-only qualification against finalized HEAD, then the post-push PR sequence in Section 12 |

If a named image/profile, path, selector or fixture is absent at DMA-00, stop and amend the implementation
issue; do not substitute a broad suite or create a convenient path. For a failure, preserve the command,
exit code, first causal error, Compose process state, bounded service logs and image IDs. Repair only the
owning component and rerun its focused check. One unchanged retry is permitted only after evidence shows
an infrastructure transport failure; a second failure or any deterministic failure is not retried.

### DMA-00 - Authority And Baseline Freeze

**Objective:** Verify accepted architecture, exact implementation authority, clean baseline, current
contracts, fixture limitations and all frozen paths before source mutation.

**Actions:** Record base/head, issue, accepted commits, scope, Skill IDs/versions, existing tests and
known unrelated failures. Prove the current DMA handler is a generic fixture and the conformance gate
can reject an invalid descriptor.

**Definition of Done:** Every Section 3 gate resolves; implementation authorization is explicit;
baseline and one negative validator result are captured; unresolved owner decision stops work.

**AI token optimization:** Load only this plan, accepted owner repairs, current DMA adapter/common
contract and nearest tests. Cache exact versions/hashes; do not reread the full DMA specification.

**Docker testing:** `docker compose config --quiet`, one existing adapter contract smoke and one
deliberately invalid fixture. No build if unchanged qualified images match inputs.

### DMA-01 - Package, Skill And Image Identity Contracts

**Objective:** Make one admitted DMA package machine-verifiable and eliminate placeholder identity.

**Actions:** Add package/Skill contracts and golden vectors; bind exact OCI digest, attestation/SBOM
references and conformance digest; add deterministic mismatch and unsupported-version failures.

**Definition of Done:** Trusted signature and provenance attest source commit/build identity; SBOM,
conformance, admission, resolved deployment, descriptor and runtime OCI digest agree; changed image,
untrusted or missing proof, tag substitution, Skill schema or version fails before readiness/execution;
no fixture alias is ambiguous.

**AI token optimization:** Generate schemas from one frozen field matrix, then use validators and
golden vectors for repairs. Do not ask a model to compare large YAML/JSON outputs.

**Docker testing:** Schema/golden-vector contract slice plus image-label/digest fixture checks in the
pinned test image; no full service stack.

### DMA-02 - Instance-Bound Generic Runtime Path

**Objective:** Carry immutable `agentInstanceId` through the existing generic adapter path without
professional-specific runtime logic.

**Actions:** Extend common contracts and signed delegation; derive instance from authoritative
relationship state; validate equality at PR and adapter; preserve replay and privacy-safe denial.

**Definition of Done:** Valid instance dispatch succeeds; missing, customer-supplied, stale, replayed,
cross-mode, cross-relationship and cross-tenant instance bindings fail before domain work with zero
protected existence disclosure or mutation; no DMA switch exists in PR.

**AI token optimization:** Reuse WC-087 identity and WC-080 envelope patterns. Search symbols once,
edit the owning contract path, and use compiler/schema failures instead of broad code rereads.

**Docker testing:** Focused common-contract, gateway, workload-identity and two-instance negative tests.

### DMA-03 - Skill 0 Customer Profiling

**Objective:** Produce a customer-confirmable profile without converting inference into fact.

**Actions:** Implement typed progressive profile logic, provenance classes, account-mode first rule,
minimum completeness, correction and confirmation proposal. Platform persists only confirmed revision.

**Definition of Done:** Registration fields are not re-asked; six required fields and account mode
are handled; inferred/missing/confirmed states remain distinct; concurrent/stale confirmation fails;
cross-instance data is invisible.

**AI token optimization:** Use deterministic conversation fixtures and structured outputs. Evaluate
only failed fixture deltas; reserve LLM quality review for the small customer-facing summary corpus.

**Docker testing:** DMA unit/contract tests, BP confirmation integration, replay/stale/cross-instance
tests, and one bounded conversation fixture.

### DMA-04 - Skill 1 Market Research

**Objective:** Produce a source-cited maturity report with deterministic partial/degraded behavior.

**Actions:** Implement admitted public research intents through AI Runtime/CTG, source capture,
observation/inference separation, maturity calculation, needs heat map, partial completion and review.

**Definition of Done:** Every factual claim resolves to source/date; forbidden/private sources fail;
provider failure yields explicit partial output; retries do not duplicate tool use or usage; no direct
DMA egress exists.

**AI token optimization:** Use frozen provider simulators and deterministic scoring fixtures for most
tests. Run a tiny approved LLM evaluation corpus once after deterministic contracts pass.

**Docker testing:** Tool-route contract tests, no-egress proof, provider timeout/429/invalid-source
fixtures, citation checks, idempotency and concurrent-customer load slice.

### DMA-05 - Skill 2 Content Strategy

**Objective:** Convert confirmed profile and reviewed research into an approval-gated 30-day strategy.

**Actions:** Implement campaign brief and calendar generation, stale-input checks, claim evidence,
platform recommendation rationale and customer approval proposal. Stop before content production.

**Definition of Done:** Exact upstream revisions are bound; draft cannot trigger publishing; customer
approve/reject/revise is replay-safe; domain-prohibited or unsupported claims fail; output is useful
under the frozen acceptance scenario.

**AI token optimization:** Separate deterministic structure/compliance checks from one bounded quality
evaluation set. Reuse approved prompt templates and send only structured profile/research summaries.

**Docker testing:** Skill contract/unit tests, stale revision, approval replay, prohibited claims,
no-side-effect assertion and bounded output-quality fixture.

### DMA-06 - Customer Work Journey And Projection

**Objective:** Join assignment, progress, approval, result and review through platform-owned APIs.

**Actions:** Add canonical work-item projection to the relationship workspace; map PR facts without
exposing adapter topology; handle loading, partial, unavailable, rejected, failed and stopped states.

**Definition of Done:** Customer can run Profile -> Research -> Strategy and approve required records;
refresh/reconnect reconciles one work item; another relationship cannot view or mutate it; adapter is
never browser-accessible.

**AI token optimization:** Reuse WC-088 command/projection/client patterns. Regenerate clients once
after OpenAPI stabilizes; avoid repeated generated-file analysis.

**Docker testing:** BP/PR integration, OpenAPI/generated drift, focused web tests and one browser-level
journey using deterministic providers; no full browser matrix during development.

### DMA-07 - Evidence, Usage And Billing Attribution

**Objective:** Make every governed action and consumed resource attributable without giving DMA
authority over evidence or money.

**Actions:** Enforce decision-before-dispatch; record source/tool/result/approval lineage; reserve or
allow zero-priced trial use before cost; reconcile platform-observed usage after execution.

**Definition of Done:** Every invocation maps to tenant, relationship, instance, Skill and work item;
replay produces no duplicate evidence/reservation/debit; adapter estimates cannot settle; CE/WBE
unavailability follows fail-safe semantics.

**AI token optimization:** Use ledger counts, hashes and invariant queries as truth. Provide a model
only the failing invariant and nearest owning code, never full ledgers or logs.

**Docker testing:** CE/WBE/BP/PR integration with success, zero-price trial, reserve denial, replay,
partial, reconciliation, cross-instance and outage tests.

### DMA-08 - Stop, Cancellation, Readiness And Isolation

**Objective:** Prove real DMA work is controllable and one customer cannot harm another.

**Actions:** Add interruptible slow fixtures, reserved Stop path, queued/active cancellation, late-
result rejection, readiness detail, WC-080 limit and limit-plus-one fixtures, trial/live separation,
default-deny network proofs and privacy-safe telemetry/redaction sentinels.

**Definition of Done:** Explicit Stop is effective within the constitutional SLO under active work,
queue saturation and dependency failure; no late publish occurs; resume needs fresh authority;
stopping/failing one instance does not stop another.

**AI token optimization:** Analyze compact latency percentiles and failure summaries, not raw traces.
Capture one representative trace only for a failed invariant.

**Docker testing:** Saturation, timeout, crash/restart, queue, Stop/cancel distinction, CE outage,
resource observation, denied egress and two-instance survival campaign.

### DMA-09 - Compatibility And Fast Skill Addition Proof

**Objective:** Prove later Skills are agent-package additions, not platform redesigns.

**Actions:** Add a non-executable future-Skill contract fixture; validate additive compatible minor,
breaking major rejection, old-instance continuity, supersession and restoration of an already
admitted tuple for relationships already pinned to it. Any relationship or accepted Skill version
change remains a BP-owned governed selection/update under WC-087/088, never adapter rollback.

**Definition of Done:** Existing instances remain pinned; new admitted package can declare an additive
Skill without common lifecycle changes; unsupported schemas fail; rollback selects an already admitted
digest and preserves history.

**AI token optimization:** Use generated compatibility matrices and schema diffs. No implementation of
the future Skill and no model-generated speculative domain behavior.

**Docker testing:** Contract compatibility and two-version conformance fixtures using reused images;
no provider or environment deployment.

### DMA-10 - Consolidated Focused Qualification

**Objective:** Validate the complete changed slice once before final commits.

**Actions:** Run Compose render, changed-service smokes, component tests, three-Skill journey,
two-tenant/two-instance scenario, Stop, usage, security and compatibility checks. Capture evidence
before any retry and repair only causal failures.

**Definition of Done:** Every focused acceptance condition passes; failures are classified; unchanged
retry occurs at most once and only for evidenced infrastructure failure.

**AI token optimization:** One filtered failure report per command; deduplicate compiler/test errors;
never paste full successful logs or repeatedly rebuild unchanged images.

**Docker testing:** One consolidated campaign using image/cache reuse. Full coverage, SBOM and scanners
remain deferred to DMA-11.

### DMA-11 - Final Qualification, Review And PR

**Objective:** Produce immutable evidence and one Founder-ready unmerged PR.

**Actions:** Finalize commits; hash inputs; build once; run full affected tests, coverage, production
builds, conformance, security scans and repository gates; push exact HEAD; perform author review and
prepare commit-bound PR metadata.

**Definition of Done:** Section 16 is complete; qualification PASS binds exact HEAD/image IDs/report
hashes; no unresolved review finding; hosted prechecks pass; PR is ready for Founder review and is not
self-approved or merged.

**AI token optimization:** No model involvement in PASS derivation. Use deterministic evidence; invoke
reasoning only for a bounded causal failure or review conflict. Do not poll CI.

**Docker testing:** One final Docker-only command in Section 10 using the same qualified images for all
tests, coverage, builds, SBOM and scans.

## 9. Test And Acceptance Strategy

### 9.1 Acceptance Scenarios

| ID | Scenario |
|---|---|
| DMA-AS-01 | Single-location customer completes Profile -> Research -> Strategy and approves outputs |
| DMA-AS-02 | Two tenants use the same DMA digest concurrently with no identity, data, evidence or usage crossover |
| DMA-AS-03 | One tenant hires two DMA instances; goals, profiles, work, usage and Stop remain separate |
| DMA-AS-04 | Research provider partially fails; customer receives cited partial report and honest limitation |
| DMA-AS-05 | Duplicate request replays one result with no duplicate tool call, evidence or usage |
| DMA-AS-06 | Emergency Stop during active research halts before late result publication and leaves another instance running |
| DMA-AS-07 | New image/schema mismatch fails before work; prior admitted digest remains available |
| DMA-AS-08 | Future additive Skill fixture passes admission compatibility without platform lifecycle changes |

### 9.2 Coverage And Quality

- New/touched executable logic: at least 90% line and 80% branch coverage unless stricter gates apply.
- Every identity/binding field, state transition, denial, replay, partial result, Stop, usage and
  compatibility rule has deterministic positive and negative coverage.
- Skill quality evaluation is bounded to approved fixtures and cannot override contract/security FAIL.
- Global thresholds, exclusions and constitutional SLOs may not be weakened.

## 10. Docker Qualification And Cost Control

### 10.1 Development Campaign

Run lightweight diagnostics and schema checks after each component. Build changed images at the first
component requiring execution, then reuse them until relevant inputs change. Batch integration at
DMA-10. Do not run full coverage, production builds, SBOM or scanners per component.

### 10.2 Final Command

Implementation adds one command with a frozen output path:

```sh
./scripts/qualify_dma_thin_vertical_slice.sh \
  --output test-results/dma-thin-vertical-slice/qualification.json
```

The script orchestrates Docker/Compose and deterministic host git/hash tools only. Language runtimes,
schema validation, tests, generators, builds, coverage and scanners run in pinned containers. It:

1. verifies authority metadata, clean finalized HEAD and frozen tracked-input inventory;
2. records Docker/Compose versions, capacity and running state;
3. renders applicable environment configuration without deployment;
4. computes sorted path/content and normalized configuration hashes;
5. builds each changed image once and records ID/digest/platform;
6. runs smokes and the complete affected unit/contract/integration/CCT suites;
7. runs DMA-AS-01 through DMA-AS-08 and coverage thresholds;
8. validates OpenAPI/schema/generated drift and production builds;
9. generates SBOM and runs pinned image/configuration/secret scanners;
10. verifies implementation-authorization evidence and that required C-059/C-065 validators and PR
  template inputs exist, without claiming a remote-SHA or hosted PR gate before push;
11. emits redacted schema-valid PASS/FAIL evidence bound to exact HEAD and image IDs.

No `docker system prune`, volume prune, broad container deletion, unpinned `latest` tool or host
package installation is permitted. Capture logs, inspect and resource state before cleanup/retry.

## 11. AI Token And Time Optimization

1. Freeze architecture, Skill schemas, acceptance fixtures and paths before implementation.
2. Maintain a compact implementation context card: accepted commits, component, touched paths,
   nearest tests, current failure and next check. Do not repeatedly load full plans/specifications.
3. Work one DMA component at a time and validate immediately with its cheapest Docker check.
4. Use targeted search/symbol references; avoid broad repository inventories after DMA-00.
5. Generate OpenAPI clients once after contracts stabilize; never review generated files one by one.
6. Prefer schema validators, compiler diagnostics, invariant queries and filtered test output over LLM
   interpretation. A model cannot turn UNKNOWN or FAIL into PASS.
7. Use low-cost models for bounded mechanical edits and fixture generation. Reserve frontier reasoning
   for cross-service contract conflict, security boundary or unexplained deterministic failure.
8. Cache by plan commit, source hash and config hash. Send only changed snippets and the causal error.
9. One unchanged retry is allowed only for evidenced infrastructure/provider transport failure.
10. Batch Docker integration once at DMA-10 and full qualification once at DMA-11. Reuse exact images.
11. Record model/task category, token count, cache hit and retry reason without retaining sensitive prompts.
12. Stop scope drift immediately; a fourth Skill or new platform service returns to architecture.

## 12. Commit, Review And PR Sequence

Use the implementation branch and metadata assigned after authorization. Recommended milestones:

1. `agent(contract): bind DMA package skills and instance identity`
2. `feat(agent): implement DMA profile research and strategy`
3. `constitutional(agent): integrate evidence usage and stop controls`
4. `cct(agent): qualify DMA thin vertical slice`
5. `docs(governance): record WC-089 qualification`

Run focused validation after each milestone. The exact sequence is:

1. close every Section 3 owner input, record current-session authorization and pass DMA-00 before any
  runnable edit;
2. finalize commits, perform author review against the complete local diff, and run final qualification
  against that clean exact HEAD;
3. push the qualified HEAD once;
4. populate `.github/pull_request_template.md`, then run
  `python scripts/prepare_pr_body.py --body-file /tmp/pr-body.md --base origin/main`; this requires the
  pushed remote SHA and binds C-059 metadata and the C-065 author-review evidence to it;
5. open one PR from that exact prepared file, then allow hosted C-059/C-065 checks to evaluate the same
  SHA. Do not poll CI, self-approve or merge.

Any relevant post-qualification or post-preparation change invalidates the evidence and returns to
step 2. A failed local or hosted gate remains FAIL; capture its bounded evidence and do not rewrite the
PR body after opening it to manufacture PASS.

## 13. Acceptance Matrix

| ID | Acceptance condition |
|---|---|
| DMA-ACC-01 | Six-image platform boundary is unchanged; DMA is a private admitted image behind PR |
| DMA-ACC-02 | One image/version serves isolated customer instances; no per-customer image semantics |
| DMA-ACC-03 | Trusted provenance binds source/build, SBOM, conformance, admission, descriptor, resolved deployment and running OCI digest exactly; tag or proof substitution fails closed |
| DMA-ACC-04 | Every customer operation and replay scope binds tenant, relationship, immutable `agentInstanceId`, mode, invocation and payload |
| DMA-ACC-05 | Skills 0/1/2 use canonical versioned contracts; no fourth Skill is implemented |
| DMA-ACC-06 | Profile confirmation never promotes unconfirmed inference to fact |
| DMA-ACC-07 | Research claims are cited and provider failure produces honest partial output |
| DMA-ACC-08 | Strategy is useful, binds current inputs and cannot publish content |
| DMA-ACC-09 | Customer work progress, approval, result and review remain BP-owned |
| DMA-ACC-10 | PR remains generic and adapter remains unreachable from customer channels |
| DMA-ACC-11 | AI/tool dispatch is purpose-bound and governed; default-deny ingress/egress blocks metadata, wildcard and direct provider/Internet authority |
| DMA-ACC-12 | Evidence, reservation and usage references reconcile idempotently and are attributed to the correct tenant, relationship, instance, work item and invocation without payload duplication |
| DMA-ACC-13 | Stop halts active/queued work within the constitutional SLO and blocks late publication |
| DMA-ACC-14 | Two tenants and two same-tenant instances remain isolated under concurrency and failure |
| DMA-ACC-15 | Readiness, errors, logs, traces, proof and scan output are truthful, privacy-normalized, payload-minimized and credential-free |
| DMA-ACC-16 | WC-080 request/resource/concurrency/queue limits, limit-plus-one denial and Stop reserved capacity preserve another customer's work |
| DMA-ACC-17 | Additive later-Skill fixture requires no new platform service or lifecycle branch |
| DMA-ACC-18 | Prior admitted digest remains usable for pinned instances and rollback |
| DMA-ACC-19 | Focused Docker tests are batched; one final qualification reuses exact images |
| DMA-ACC-20 | Qualification evidence binds exact HEAD, image IDs, tests, scans and report hashes |
| DMA-ACC-21 | Author review and PR metadata bind the pushed qualified HEAD |
| DMA-ACC-22 | One unmerged PR is ready for Founder review without self-approval or merge |
| DMA-ACC-23 | Profile observations/inferences/confirmations, research sources/citations/partials, strategy drafts/decisions and work/results preserve owner, revision, lineage and concurrency semantics |
| DMA-ACC-24 | Retention, erasure and legal hold preserve proof/payload separation and minimum immutable attribution without content resurrection |
| DMA-ACC-25 | Supported record/contract versions coexist; additive migration and rollback obligations satisfy ADR-011 without rewriting immutable history |

## 14. Compatibility And Rollback

- Any behavior, dependency, schema digest or image content change produces a new immutable image digest
  and follows WC-079 admission compatibility treatment; no active admission record is edited in place.
- Existing relationships retain their exact admitted professional version and accepted Skill versions
  unless BP records a governed WC-087/088-compatible selection or update. Adapter deployment or
  rollback never silently rebinds a relationship or changes its immutable `agentInstanceId`.
- Additive optional contract fields require tested minor compatibility. Meaning changes require a new
  major and coexistence window.
- Rollback resolves a previously admitted supported digest; it never rewrites invocation, evidence,
  usage, profile or customer acceptance history.
- Durable contract migration follows ADR-011: additive and backward-compatible expansion first,
  coexistence through the supported read/write window, invariant verification before retirement, and
  forward repair for committed data. Physical schema and implementation technology remain an
  implementation decision outside this plan.
- Unknown outcomes reconcile by existing invocation/idempotency identity before retry.
- Durable changes, if separately approved, are additive, tenant-isolated and forward-fixed.

## 15. Stops

- Stop before runnable implementation without Founder acceptance and explicit current-session authority.
- Stop on any open or contradictory Section 3 owner input.
- Stop until the workload identity registry, configuration and tests synchronously use the reconciled
  ADR-049 audiences; do not add an alias, fallback or implementation-selected value.
- Stop rather than add a fourth Skill, provider write, paid-ad path, customer credential or Production traffic.
- Stop rather than add a service, per-customer image, shared arbitrary host or DMA branch in PR.
- Stop rather than trust customer/model/adapter identity, authority, evidence, price or acceptance claims.
- Stop on missing/stale instance, admission, digest, schema, contract, Decision Space, approval,
  reservation, evidence, deadline, readiness or Stop state.
- Stop rather than expose PII/secrets in logs, traces, evidence or qualification artifacts.
- Stop on deterministic test, contract, coverage, build, security or gate failure; never hide it by retry.
- Stop rather than use host runtimes, unpinned tools, destructive Docker cleanup or fabricated evidence.
- Stop if final commits, images, qualification, review and PR metadata do not bind one exact HEAD.

## 16. Definition Of Done

WC-089 is complete only when:

- Founder accepted concept and owner-reviewed plan are bound to implementation authority.
- One admitted DMA type/version image has real, non-placeholder artifact/conformance identity.
- Skills 0/1/2 have canonical typed contracts and real domain behavior.
- Every invocation binds exact tenant, relationship, instance, versions, artifact, authority and work.
- Profile, research and strategy complete the customer journey with required confirmations.
- BP, CE, PR, AIR/CTG, oauth-vault and WBE boundaries remain intact and domain-neutral.
- Evidence, usage, replay, partial result, cancellation and Stop invariants pass.
- Two tenants and multiple instances remain isolated under concurrent work and failure.
- A future additive Skill contract proves the fast iteration path without platform redesign.
- One consolidated focused Docker campaign passes.
- One final Docker-only qualification passes against finalized commits and reused image IDs.
- Coverage, builds, contract drift, SBOM, security scans and repository gates pass.
- Complete author review has no unresolved finding and binds the pushed qualified HEAD.
- One unmerged PR is ready for Founder review; no self-approval or merge occurs.

## 17. Author And Institutional Review Record

**Author review:** PASS - 2026-09-10. The complete planning package was checked before and after the
institutional repairs against WC-080's structure, the accepted exact-six and adapter boundaries,
Skills 0/1/2 scope, component-to-acceptance traceability, implementation authority, registry
arithmetic, path references, Markdown integrity, ASCII policy and diff integrity. The final audit
found no structural or semantic defect. The audience issue was resolved through the authorized
Enterprise decision and subsequent Security PASS; remaining implementation inputs are not unresolved
author-review findings.

The Founder requested one edit-and-repair pass by Enterprise Architecture, Security, and Data after
Solution Architecture author review, followed by one Platform IT Expert implementability pass. Each
pass is bounded to its Decision Space. Compatible repairs are integrated directly; conflicts,
authority gaps or reference-architecture changes are recorded as blockers rather than silently fixed.

| Review | Status | Findings and repairs |
|---|---|---|
| Solution Architecture author review | PASS | Confirmed every DMA-00 through DMA-11 component has an objective, actions, Definition of Done, AI token optimization and Docker testing approach; no repair required |
| Enterprise Architecture | PASS | Preserved the exact-six platform release tuple, ADR-035 signal-only PAC role and ADR-049 type + version + digest deployment boundary; clarified that DMA is a private admitted workload, not a seventh service; bound instance/version evolution and rollback to WC-079/087/088 without silent relationship migration. Founder-authorized reconciliation on 2026-09-10 classified the registry namespace as conformance drift and fixed the canonical versioned audiences as `urn:waooaw:service:agent-runtime-adapter:digital-marketing-local-service:3.1.0` and `urn:waooaw:service:agent-runtime-adapter:trading-fo-crypto:1.8.0`; version and artifact digest remain independent admission bindings; no ADR change required. |
| Security | PASS | INST-007 confirmed the reconciled exact versioned audiences, synchronized registry/configuration/test replacement, independent professional-version and OCI-digest binding, and fail-closed denial of old or wrong audiences without alias or fallback. The complete planning contract also fixes least privilege, instance/mode and anti-replay binding, secret and egress separation, privacy-safe evidence and telemetry, saturation-safe Stop, resource limits, provenance, scans, trial/live isolation and executable negative-test obligations. The current registry drift remains an implementation entry gate, not an unresolved planning decision or executable proof. |
| Data Architecture | PASS | INST-006 clarified BP-owned customer records versus DMA proposals; separated observations/inferences/confirmations, sources/citations/partials and strategy drafts/decisions; fixed scoped keys, revisions, concurrency, work/invocation/result lineage, WBE attribution, evidence-reference versus payload/proof ownership, retention/erasure/legal hold, immutable facts, version coexistence and ADR-011 migration/rollback obligations. No physical schema or implementation technology selected. |
| Platform IT Expert implementability | BLOCKED | INST-010 froze current adapter, PR, BP, WBE, web, fixture, Compose and qualification anchors; added component-sized edit/check boundaries, missing-fixture requirements, generated-client timing, image/cache reuse, bounded failure/retry evidence and the correct authorization -> qualification -> push -> C-059/C-065 -> PR sequence. The audience decision is reconciled but its registry/configuration/test repair is an unexecuted implementation input; Section 3 owner inputs and `TO FREEZE` contract/persistence/test paths remain open; current fixtures have placeholder digests, legacy Skill aliases, no runtime fixture directory and no second DMA version needed to prove rollback. No implementation or Founder acceptance is claimed. |

# Work Contract 079 - Agent Admission Contract Implementation Plan

**Office:** Enterprise Architect (INST-004)
**Future executor:** Platform IT Expert (INST-010), Skills 1-8, 11-15, and 17
**Assigned by:** Founder instruction, 2026-08-30
**Status:** FOUNDER ACCEPTANCE CANDIDATE - CONSOLIDATED IMPLEMENTATION SPECIFICATION; IMPLEMENTATION NOT AUTHORIZED
**Delivery unit:** Versioned Agent Admission Contract, admission lifecycle, deterministic conformance, and activation gate
**Constitutional basis:** C-001, C-002, C-003, C-007, C-023, C-032, C-034, C-036, C-037, C-038, C-039, C-041, C-048, C-049, C-059, C-063, C-065, C-070, C-071, C-076, C-077, C-079, C-080, C-083, C-084, C-085, C-088, C-094, C-099
**Architectural decisions:** ADR-001, ADR-002, ADR-003, ADR-011, ADR-013, ADR-014, ADR-015, ADR-020, ADR-022, ADR-023, ADR-031, ADR-034, ADR-035, ADR-040, ADR-043, ADR-044

## Objective

Create one versioned, machine-readable Agent Admission Contract that determines whether an exact
WAOOAW professional version is eligible to be offered for trial or hire and activated for customer
employment. WAOOAW must present only professional versions whose immutable admission package has
passed every required authoring, constitutional, skill, billing, provider, runtime, security, and
environment conformance gate.

The admitted professional becomes the reusable product foundation for the later customer journey:

```text
HIRE OR TRIAL -> UNDERSTAND CUSTOMER -> CONFIGURE AND TUNE
-> ACCEPT CUSTOMER EMPLOYMENT CONTRACT -> ACTIVATE
-> AUTONOMOUS OPERATION -> REVIEW AND TUNE
```

WC-079 governs professional-version admission, not the complete customer journey. It must make the
professional's skill and configuration contracts available to the existing platform-owned employment
journey without allowing an agent to approve, admit, activate, or silently change itself.

The implementation handoff must be executable without requiring INST-010 to invent lifecycle states,
authority boundaries, API meanings, persistence semantics, validation rules, evidence shape, Docker
workflow, test scope, compatibility policy, or release gates.

## Founder Intent Fixed By This Contract

1. WAOOAW presents only agents that have completed Agent Admission Contract compliance.
2. A professional version contains one or more declared Skill Definitions.
3. Each customer Skill Instance may have zero or more versioned Configuration Revisions, Goal
   Revisions, Schedule Rules, and Performance Review Windows.
4. Zero goals are permitted while drafting, interviewing, or configuring. Before activation, every
   skill requires at least one measurable business goal unless its admitted Skill Definition carries
   an explicitly approved non-goal operational-purpose exemption.
5. Thirty days is the default performance and customer contract review window. It is not a universal
   skill execution frequency. Execution remains skill-specific, bounded, or event-driven.
6. An agent may discover requirements, populate its draft admission package, run deterministic
   validation, read findings, and submit corrected revisions.
7. An agent may not approve, admit, publish, activate, suspend, supersede, or retire itself. These are
   independently authorized platform transitions and fail closed.
8. Agent Admission is a logical lifecycle capability over existing platform boundaries. WC-079 does
   not create a standalone Agent Admission microservice.
9. Web and WhatsApp later consume the same admitted professional and skill contracts through the
   platform-owned employment journey. No agent may implement a private hiring or activation flow.

## Authority And Scope

This Work Contract authorizes plan creation only. It does not authorize architecture mutation,
canonical API or data-contract changes, application source, migrations, generated clients,
dependency installation, image publication, provider activation, environment mutation, deployment,
spend, customer traffic, UAT, Production, PR approval, or merge.

Before implementation, the exact logical design, wire contracts, persistence contract, security
policy, and constitutional readiness must be produced or amended by their owning institutions and
accepted under an explicit Founder-authorized specification Work Contract. After those gates and
separate explicit Founder implementation authorization, INST-010 may implement only the approved
contracts and the tasks AA-00 through AA-13 below.

### In Scope

- Immutable professional identity and version admission.
- Versioned machine-readable Agent Admission Contract schema.
- Professional identity, compliance declaration, Skill Manifest, and Activation Evidence sections.
- Deterministic validation and structured remediation findings.
- Draft, validating, remediation-required, review-ready, approved, active, suspended, superseded,
  retired, and rejected lifecycle semantics.
- Professional-to-skill and skill-to-configuration/goal/schedule/review cardinalities.
- Compatibility between Agent Authoring Guide, Constitutional DNA, Agent Base Spec, Platform-Agent
  Contract, Agent Billing Profile, Decision Consequence Map, provider requirements, and runtime.
- Business Platform catalogue/admission ownership, Constitutional Engine transition validation and
  evidence, Professional Runtime activation enforcement, WBE billing readiness, and provider/environment
  readiness projections.
- Public catalogue suppression for every version that is not ACTIVE and currently compatible.
- Docker-only implementation and one reusable-image final qualification command.

### Out Of Scope

- The complete Web or WhatsApp customer onboarding experience and Employment Journey Orchestrator.
- Customer discovery dialogue, customer-specific configuration content, contract presentation UI,
  payment UI, customer activation UI, autonomous skill execution, or periodic tuning UX.
- New professional skills, prompts, personas, prices, providers, MCP tools, or billing products.
- Changes to Constitutional DNA, Agent Base Spec, Agent Authoring Guide, PAC, or constitutional claims
  except through their separately authorized owner process.
- Provider account creation, credential issuance, live provider calls, or production activation.
- A new deployable service, queue, model provider, workflow engine, identity authority, or ledger.
- UAT, Production, customer traffic, or customer-proof claims.

## Required Inputs And Pre-Implementation Gates

| Input | Required state | Purpose |
|---|---|---|
| `architecture/foundation-consolidated-assessment-2026-08-29.md` Objective B | Founder accepted for this scope | Admission boundary, cardinalities, cadence, and freeze criteria |
| `architecture/reference/agents/AGENT-AUTHORING-GUIDE.md` | Current approved gate | Professional specification completeness and activation prerequisites |
| `architecture/reference/agents/AGENT-BASE-SPEC.md` | APPROVED and current | Universal platform-aware agent behavior |
| `architecture/reference/agents/CONSTITUTIONAL_DNA.md` | RATIFIED and current | Universal constitutional inheritance |
| `adr/ADR-035-platform-agent-contract-standard.md` and current PAC schemas | Accepted and current | Platform/agent compatibility and signal declarations |
| `architecture/reference/product/agent-employment-experience-contract.md` | v1.0-foundation contributed; Founder acceptance required before implementation | Uniform customer rights and employment journey boundary |
| `architecture/reference/components/business-platform.md` | Accepted/current | Catalogue, admission state, employment, and skill ownership |
| `architecture/reference/components/constitutional-engine.md` | Accepted/current | Governed transition validation and immutable evidence |
| `architecture/reference/components/professional-runtime.md` | Accepted/current | Runtime activation and execution rejection boundary |
| `architecture/reference/api-specs/business-platform.openapi.yaml` | Canonical | Existing relationship, contract, skill, and activation API truth |
| `adr/ADR-INDEX.md` | Re-read before specification and implementation | Current accepted architecture decisions |
| `constitution/PROJECT_STATE.md` | Re-read at every authority boundary | Current gate, phase, blocker, and environment authority |

Mandatory specification gates before INST-010 source work:

1. INST-004 publishes and receives Founder acceptance for the logical admission lifecycle, ownership,
   compatibility, and domain-model delta described by WC-079.
2. Founder acceptance of this consolidated specification accepts the INST-003 capability outcome and
  exact representative fixtures defined below without creating a second professional product model.
3. Founder acceptance of this consolidated specification accepts the INST-005 REST/internal
  operations, errors, idempotency, generated-client boundary, and compatibility rules below. The
  canonical OpenAPI must be changed spec-first before source implementation; ADR-002 controls.
4. Founder acceptance of this consolidated specification accepts the INST-006 persistence, keys,
  constraints, indexes, RLS, retention, supersession, migration, and rollback contract below.
  ADR-011 controls.
5. Founder acceptance of this consolidated specification accepts the INST-007 threat model,
  service authorization, separation, integrity, minimization, and denial-disclosure rules below.
6. Founder acceptance of this consolidated specification accepts the INST-002 rule-to-claim/CCT
  matrix and confirms that Evidence First, Human Override, and Decision Space cannot be bypassed.
7. The Founder accepts the specification package and explicitly authorizes WC-079 implementation for
   the current session. G5 CLEAR alone is not implementation authority.
8. The Agent Employment Experience Contract v1.0-foundation must have an attributable Founder
  acceptance record before implementation. Its contributed status is sufficient for planning only.

### Consolidated Institutional Handoff

This planning PR resolves the cross-institution decisions needed to make the later specification
package mechanical. It does not substitute for Founder acceptance or authorize source work.

| Owner | Decision fixed by this plan | Required implementation-issue attachment |
|---|---|---|
| INST-003 Business Architect | Admission certifies reusable professional versions; it does not create a second product or customer-employment model | Accepted capability outcome and the two named representative professional fixtures |
| INST-004 Enterprise Architect | Lifecycle, ownership, digest boundaries, compatibility, readiness reconciliation, and no-new-service rule below | Accepted WC-079 revision and architecture fitness result |
| INST-005 Solution Architect | REST/internal operations implement the logical meanings below, use the canonical digest contract, and expose typed idempotent errors | Versioned OpenAPI/internal contract diff and generated-client inventory |
| INST-006 Data Architect | Submitted revisions and evidence are append-only; tenant isolation, keys, concurrency, retention, and supersession are enforced in the approved additive migration | Migration specification, rollback, RLS matrix, indexes, and concurrency tests |
| INST-007 Security Architect | Submitter/approver separation, service authorization, anti-enumeration, integrity, minimization, and denial disclosure are mandatory | Threat model and caller-operation authorization matrix |
| INST-002 Constitutional Analyst | Every consequential transition remains Evidence First, Human Override reachable, and inside the actor's Decision Space | Rule-to-claim/CCT matrix and constitutional acceptance record |
| INST-010 Platform IT Expert | Implementation follows only the accepted attachments and repository-owned paths | Skill 1 implementation-spec comment with IB/issue, tier, branch, exact files, commands, CCTs, and fixture versions |

This WC is the single consolidated owner specification. The implementation issue attaches its
Founder-accepted commit rather than creating parallel owner documents. It must name that commit,
acceptance evidence, exact source/test paths, commands, CCTs, tier, and branch. INST-010 must record a
specification gap and stop if the accepted commit, AEEC acceptance, or any required implementation
binding is absent or contradictory; AA-00 may inventory accepted details but may not create policy.

### Frozen Capability Outcome And Representative Fixtures

Admission certifies a reusable professional type/version for the existing employment product. It
does not create a second product, customer journey, price, provider, or agent-specific activation
path. Qualification uses these exact professional specifications at the Founder-accepted WC commit:

| Fixture role | Professional identity | Frozen specification | Required proof |
|---|---|---|---|
| Current multi-skill customer professional | `DIGITAL_MARKETING_LOCAL_SERVICE` v3.1 | `architecture/reference/agents/digital-marketing-agent.md` | Multiple skills pass one shared schema and validator |
| Materially different professional | `TRADING_FO_CRYPTO` v1.8 | `architecture/reference/agents/trading-agent.md` | Different cadence, risk, and provider posture pass the same shared rules |

The implementation issue records the SHA-256 digest of both files and the exact accepted Git commit.
Substitution requires a new accepted WC revision; INST-010 may not select an alternate fixture.

### Frozen Implementation Surfaces

| Contract | Required repository surface |
|---|---|
| Canonical public/internal REST contract | `architecture/reference/api-specs/business-platform.openapi.yaml` |
| Business Platform owner contract | `architecture/reference/components/business-platform.md` |
| Additive database migration | `infrastructure/postgres/init/25-agent-admission.sql` |
| BP implementation | `src/business-platform/Controllers/`, `Services/`, `Infrastructure/EmploymentRelationshipDbContext.cs`, `Program.cs` |
| CE contract and implementation | Existing constitutional gRPC contract and CE service; no public REST surface |
| PR activation guard | Existing Professional Runtime internal activation boundary |
| Generated Web client | `web/scripts/generate-api.sh` and `web/lib/api/generated/`; include the `Professionals` tag |
| Qualification command | `scripts/wc079_qualify.sh` and ignored `test-results/wc079/` evidence |

The public `Professionals` projection is anonymous by design and returns only public-safe ACTIVE,
current, compatible, environment-offerable records. Every admission management operation is
authenticated and platform-owned; none is browser-public.

## Component And Ownership Determination

WC-079 introduces no new deployable component. It adds one logical capability across existing
boundaries:

| Concern | Authoritative owner | Required behavior |
|---|---|---|
| Admission aggregate, catalogue eligibility, professional and skill versions | Business Platform | Own current lifecycle projection and expose only approved public/customer-safe data |
| Constitutional transition decision and evidence | Constitutional Engine | Validate governed transitions and record evidence before success |
| Runtime compatibility and activation enforcement | Professional Runtime | Reject an unadmitted, suspended, superseded, digest-mismatched, or incompatible version |
| Billing readiness | WBE | Confirm current Agent Billing Profile, skill cost mapping, and activation eligibility without granting admission |
| Provider/tool readiness | Existing provider and MCP registries | Return environment-specific readiness without exposing credentials or granting authority |
| Specification conformance | Deterministic admission validator | Validate immutable inputs and emit structured findings; never approve |
| Human/institutional approval | Founder or explicitly authorized platform authority | Approve the exact contract version and digest; no self-approval |

The validator is deterministic application logic, not an LLM judge. It may explain a stable finding
using predefined customer/developer-safe text, but model opinion cannot turn a failed rule into PASS.

## Agent Admission Contract

### Contract Identity And Immutability

Every submitted package has:

- `contractSchemaVersion` using semantic versioning;
- immutable `professionalTypeId` and `professionalVersion`;
- canonical admission-content digest and canonicalization profile;
- exact agent specification path/version/digest;
- artifact digest and build provenance when an implementation exists;
- submitter identity, owner identity, created/submitted timestamps, and predecessor;
- lifecycle state and append-only transition/evidence references.

Drafts may change. Submission freezes an exact revision. Any material correction creates a new
revision and digest. Approval binds to that exact revision and digest. An ACTIVE version cannot be
mutated in place; change requires a new professional version or compatible contract revision under
the accepted compatibility rules.

The submitter-controlled `admissionContent` contains Professional Identity, Compliance Declaration,
and Skill Manifest only. Activation Evidence is platform-owned append-only evidence and is never
accepted from the submitter as truth. `admissionContentDigest` is SHA-256 over UTF-8 JSON Canonicalization
Scheme (RFC 8785) bytes and is encoded as `sha256:` plus 64 lowercase hexadecimal characters. The
digest includes `contractSchemaVersion` and every field in `admissionContent`; it excludes lifecycle
projection, findings, readiness observations, approvals, timestamps assigned by the platform, and
evidence references. Cross-language golden vectors, including Unicode, numbers, object-key ordering,
empty values, and arrays, are part of the INST-005 contract.

Each governed decision additionally binds an immutable `evidenceSetDigest`, calculated with the same
profile over evidence-reference records sorted lexicographically by `evidenceType`, `evidenceRef`,
`subjectDigest`, `policyVersion`, then `observedAt` in normalized UTC RFC 3339 form. Duplicate sort-key
tuples are invalid. Approval binds the exact admission-content digest and evidence-set digest. Later
readiness or lifecycle evidence appends a new evidence set and never changes the approved admission
content.

### Four Required Sections

1. **Professional Identity** - immutable professional type/version, owner, supported languages and
   channels, agent specification and AVD references/digests, lifecycle status, and predecessor.
2. **Compliance Declaration** - Constitutional DNA and Base Spec versions, Decision Space schema,
   DCM, Evidence First operations, Emergency Stop behavior, CCT set, data classes, retention,
   security posture, PAC version, and limitation/degradation behavior.
3. **Skill Manifest** - one or more Skill Definitions with capability, business KPI, inputs/outputs,
   Decision Space subset, tools/providers, constitutional actions, configuration schema, goal schema,
   schedule policy, review policy, cost units, trial behavior, degradation, and compatibility.
4. **Activation Evidence** - approved specification references, deterministic conformance results,
   security/constitutional acceptance, environment/runtime/provider/billing readiness, immutable
   artifact digest, approval record, activation date, suspension reason, and superseded version.

### Cardinalities

```text
ProfessionalType 1 -> many ProfessionalVersions
ProfessionalVersion 1 -> many SkillDefinitions
EmploymentRelationship 1 -> many SkillInstances
SkillInstance 0 -> many ConfigurationRevisions
SkillInstance 0 -> many GoalRevisions
SkillInstance 0 -> many ScheduleRules
SkillInstance 0 -> many PerformanceReviewWindows
```

Configuration, goals, schedules, and review windows are versioned records with effective time,
source, actor, reason, compatibility, and evidence linkage. Mutable JSON may be a validated extension
payload or projection; it is not the sole history or authority.

### Cadence Semantics

| Concept | Admission rule |
|---|---|
| Skill execution schedule | Declared by Skill Definition; customer-adjustable only within admitted bounds |
| Event-driven trigger | No calendar default; only declared governed events may trigger it |
| Performance review window | Defaults to 30 days unless an approved safer domain cadence overrides it |
| Customer contract review | Defaults to 30 days and may change only where admitted policy permits |

## Admission Lifecycle

```text
DRAFT -> VALIDATING
VALIDATING -> REMEDIATION_REQUIRED | VALIDATED
REMEDIATION_REQUIRED -> DRAFT
VALIDATED -> DRAFT | READY_FOR_REVIEW
READY_FOR_REVIEW -> APPROVED | REJECTED
REJECTED -> DRAFT
APPROVED -> ACTIVE
ACTIVE -> SUSPENDED | SUPERSEDED | RETIRED
SUSPENDED -> ACTIVE | SUPERSEDED | RETIRED
```

Rules:

- Only the draft owner may create a revision, validate, read findings, and submit.
- Validation success creates VALIDATED for the exact revision and digest. Any draft edit creates a
  new revision in DRAFT and invalidates the prior validation for submission purposes.
- `submitAgentAdmission` is the only VALIDATED -> READY_FOR_REVIEW transition. It freezes the exact
  revision/digest. REJECTED -> DRAFT creates a successor draft revision and preserves the rejected
  submission and evidence; it never reopens or mutates the rejected revision.
- Approval and activation require an independently authorized actor and exact digest binding.
- ACTIVE requires APPROVED plus current billing, runtime, provider/environment, artifact, and
  constitutional readiness. Unknown or unavailable is never PASS.
- Every readiness assertion contains `assertionType`, `subjectDigest`, `environment`, `status`,
  `sourceAuthority`, `observedAt`, `validUntil`, `policyVersion`, and `evidenceRef`. PASS is usable only
  before `validUntil`, for the exact subject digest and environment. Missing, expired, stale-policy,
  mismatched, unavailable, or UNKNOWN assertions fail closed.
- Business Platform owns the admission transition coordinator. It obtains the CE decision and
  Evidence First reference before committing a consequential projection, persists the idempotency
  key and decision reference atomically with that projection, and publishes an outbox event. There is
  no cross-service database transaction. Reconciliation replays by idempotency key and exact digest;
  it may converge projections but may not manufacture approval or evidence.
- Suspension is immediate when a mandatory compatibility, constitutional, security, billing, or
  provider assertion is revoked, expires, becomes unavailable, or is replaced by an incompatible
  policy. The owning readiness source emits the change; Business Platform reconciles it through CE
  and suppresses new offer/activation immediately. Existing customer consequences follow approved
  employment contracts; admission suspension does not silently terminate relationships.
- Supersession names the successor and migration/compatibility policy. Old evidence remains.
- Every consequential transition is idempotent, attributable, and Evidence First.

### Evidence First Transition Ordering

For submit, approve, reject, activate, suspend, supersede, and retire, Business Platform must:

1. authenticate and authorize the actor, including separation of duties;
2. validate lifecycle state and exact revision, content, artifact, evidence-set, and policy digests;
3. obtain the CE decision and immutable evidence reference for the exact intent;
4. atomically persist the local projection, idempotency outcome, CE reference, and outbox row;
5. return success only after step 4 commits, then publish the outbox event.

Failure in steps 1-4 produces no governed success projection. Reconciliation may replay the same
idempotency key and digest, but cannot manufacture approval, activation, or evidence. Human Override
and Emergency Stop remain reachable independently of admission state, rate limits, and dependency
degradation. CE unavailability fails every admission consequential write closed and cannot delay or
disable Emergency Stop behavior.

## Logical API Capability

ADR-002 remains controlling. These exact meanings and paths must be added to the canonical OpenAPI
before source implementation:

| Operation | Method and path | Caller | Success |
|---|---|---|---|
| Create draft | `POST /api/v1/professionals/{type}/versions/{version}/admission/drafts` | Owner delegate or admission operator | `201`, identical replay `200` |
| Put revision | `PUT /api/v1/professionals/{type}/versions/{version}/admission/drafts/{draftId}/revisions/{revision}` | Draft owner | `200` |
| Validate | `POST /api/v1/professionals/{type}/versions/{version}/admission/drafts/{draftId}/validations` | Draft owner or validator operator | `202`, identical replay `200` |
| Read findings | `GET /api/v1/professionals/{type}/versions/{version}/admission/drafts/{draftId}/validations/{validationId}/findings` | Draft owner or reviewer | `200` |
| Submit | `POST /api/v1/professionals/{type}/versions/{version}/admission/submissions` | Draft owner | `201`, identical replay `200` |
| Approve | `POST /api/v1/professionals/{type}/versions/{version}/admission/approvals` | Independent approver | `200` |
| Reject | `POST /api/v1/professionals/{type}/versions/{version}/admission/rejections` | Independent approver | `200` |
| Activate | `POST /api/v1/professionals/{type}/versions/{version}/admission/activations` | Platform activation authority | `200` |
| Suspend | `POST /api/v1/professionals/{type}/versions/{version}/admission/suspensions` | Constitutional or operational authority | `200` |
| Supersede | `POST /api/v1/professionals/{type}/versions/{version}/admission/supersessions` | Compatibility authority | `200` |
| Retire | `POST /api/v1/professionals/{type}/versions/{version}/admission/retirements` | Retirement authority | `200` |
| Offerable versions | `GET /api/v1/professionals/offerable-versions` | Anonymous/customer | `200` public-safe collection |

Every mutating operation requires `Idempotency-Key`. The same key, actor, tenant, operation, subject,
and canonical request hash replays the prior outcome; the same key with any different binding returns
`409 ADMISSION_IDEMPOTENCY_CONFLICT` with no mutation. Stale aggregate versions return
`409 ADMISSION_STATE_CONFLICT`; policy/readiness locks return `423 ADMISSION_TRANSITION_BLOCKED`;
dependency failure returns `503 ADMISSION_UNAVAILABLE`. Invalid requests use `400`, unauthenticated
requests `401`, and authenticated but unauthorized operation families `403` only before a resource
identifier is resolved.

All errors use RFC 9457 with stable `code` and `correlationId`. For an authenticated caller, absent,
inaccessible, and cross-tenant identified resources all return the same `404 ADMISSION_NOT_FOUND`
shape, headers, and timing envelope. Step-up, conflict, or policy details are disclosed only after
resource authorization. Errors, findings, logs, and traces exclude reviewer identity, evidence IDs,
artifact coordinates, credentials, prompts, customer payloads, storage paths, and policy internals.
Authorization precedence is deterministic: an invalid or absent token returns `401`; an authenticated
caller invoking an operation family it can never perform returns `403` only when no admission resource
identifier is present; once any type, version, draft, validation, or admission identifier is present,
failed role, ownership, tenant, or existence resolution returns normalized `404`. An authorized caller
that resolves the resource may then receive `409`, `423`, or step-up detail.

OpenAPI remains at `/api/v1`; a breaking wire change requires `/api/v2` and a coexistence window.
`contractSchemaVersion` follows semantic versioning: a supported minor may add explicitly optional
fields only after validator deployment; unsupported higher minor or major fails AAV-002; required,
typed, removed, renamed, or meaning-changing fields require a new major. Unknown fields within an
exact supported version fail validation. The Web generator adds the `Professionals` tag so public
offerability uses the canonical generated client; admission management clients remain internal.

No public caller supplies tenant authority, approval identity, evidence IDs, readiness outcomes, or
lifecycle state as trusted facts. Public catalogue reads never expose internal findings, artifact
coordinates, credentials, security details, or reviewer identity beyond approved public provenance.

### Admission Authorization Matrix

Caller identity, tenant, role, and assurance come only from validated server context. Evaluation
order is authentication, tenant membership, ownership or institutional entitlement, lifecycle
precondition, operation assurance, separation of duties, and digest binding. Ambiguity fails closed.

| Operation family | Allowed principal | Mandatory denial |
|---|---|---|
| Create/revise/validate/submit | Exact professional owner delegate; validation also permits platform validator | Public/customer, non-owner, submitted-revision mutation |
| Read findings | Exact owner delegate or assigned reviewer | Cross-tenant, unrelated reviewer, public caller |
| Approve/reject | Founder or explicitly delegated independent admission approver with step-up MFA | Submitter, owner delegate, agent subject, missing step-up |
| Activate | Internal platform activation authority with step-up MFA | Submitter, owner, public/customer, stale readiness |
| Suspend | Internal constitutional or operations authority with step-up MFA | Agent subject, public/customer, insufficient authority |
| Supersede/retire | Internal lifecycle authority with step-up MFA | Agent subject, public/customer, missing migration/retirement policy |
| Offerable read | Anonymous/customer | Internal fields or any non-offerable version |

The submitter subject may never approve, reject, activate, suspend, supersede, or retire the same
professional version. Denial telemetry contains only correlation ID, pseudonymous actor hash,
operation family, result code, policy version, and timestamp.

## Persistence And Migration Contract

Migration 25 is additive and creates no new service, schema, or shared ledger:

| Table | Purpose | Primary and unique keys | Mutation policy |
|---|---|---|---|
| `business.agent_admissions` | Current aggregate projection | UUID PK; unique tenant/type/version; optimistic `state_version` | Guarded compare-and-swap projection only |
| `business.agent_admission_revisions` | Exact contract revisions | UUID PK; unique admission/revision and admission/content digest | Append-only |
| `business.agent_admission_validations` | Deterministic attempts | UUID PK; unique admission/revision/profile/idempotency key | Append-only |
| `business.agent_admission_findings` | Stable findings | UUID PK; unique validation/rule/path | Append-only |
| `business.agent_admission_assertions` | Readiness observations | UUID PK; unique admission/type/environment/subject/policy/observed time | Append-only; newer rows supersede logically |
| `business.agent_admission_transitions` | Lifecycle and CE evidence links | UUID PK; unique admission/from/to/correlation | Append-only |
| `business.agent_admission_idempotency` | Replay outcomes | UUID PK; unique admission/operation/key | Insert then one terminal outcome update |
| `business.agent_admission_outbox` | Existing BP outbox-pattern extension | UUID PK; unique transition and scope hash | Event immutable; publication metadata update only |

All tables carry non-null `tenant_id`; `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`
are mandatory. Every `SELECT`, `INSERT`, `UPDATE`, and permitted dispatcher operation has explicit
`USING` and `WITH CHECK` policies using
`tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid`. `business_app` receives
only operation-required DML. Background reconciliation and outbox dispatch set the exact tenant
context per transaction and use a constrained non-bypass role; no application or dispatcher role has
`BYPASSRLS`. Digest checks require `sha256:` plus 64 lowercase hex characters. Assertion status and
finding severity are constrained enums; assertion `valid_until` must be after `observed_at`. Foreign
keys include tenant identity and cannot cross tenants.

Aggregate transitions compare `expectedStateVersion` and increment exactly once in the same
transaction as idempotency outcome, CE reference, and outbox insert. A stale version returns
`ADMISSION_STATE_CONFLICT`. Revisions, findings, transitions, and evidence links are retained as
lineage and cannot be hard-deleted. Assertion expiry is logical. Migration rollback before use drops
only newly created empty tables in reverse dependency order; after any admission record exists,
rollback is application-version selection and forward repair, never data deletion or rewrite.

Legacy employment and skill endpoints retain `minItems: 1` goal behavior. Zero goals are permitted
only in admission drafts/configuration; activation applies AAV-011 and fails unless every skill has a
measurable goal or exact admitted non-goal exemption. No legacy endpoint changes semantics silently.

## Deterministic Conformance Rules

The validator must use stable rule IDs and fail closed. At minimum it verifies:

- current Agent Authoring Guide sections and prerequisite references are complete;
- Constitutional DNA and current Agent Base Spec versions are declared and compatible;
- PAC schema/version and every required platform signal handler are complete;
- Agent Billing Profile exists and every active Skill Definition has cost attribution;
- at least one Skill Definition exists and every skill has a business KPI and Decision Space subset;
- every external tool/provider is declared, default denied, and mapped to CE.ValidateAction;
- each consequential decision appears in the DCM and deterministic-required decisions have an
  independent verification method;
- configuration, goal, schedule, review, trial, degradation, data, retention, and Emergency Stop
  schemas are present and internally consistent;
- required CCTs and conformance results bind to the same specification/artifact digests;
- runtime, environment, billing, provider, and artifact compatibility are current and supported;
- no submitter can satisfy an independent approval rule and no approval can target a floating version.

Finding shape must include `ruleId`, `severity`, `contractPath`, `constitutionalBasis`,
`expected`, `observedCategory`, `remediation`, and `blocking`. It must exclude secrets, customer
payload, prompt text, credentials, unsafe filesystem paths, and raw scanner output.

### Stable Rule Catalogue

Rule IDs are permanent. A changed meaning receives a new ID; retired IDs remain reserved. INST-002
owns constitutional bases, INST-007 owns security classifications, INST-005 owns wire representation,
and INST-004 approves semantic changes.

| Rule ID | Blocking requirement |
|---|---|
| AAV-001 | Required contract sections and fields are complete |
| AAV-002 | Declared schema version is supported under the negotiated compatibility policy |
| AAV-003 | Admission content canonicalizes and matches the supplied digest and immutable identity |
| AAV-004 | Authoring Guide, specification, AVD, DNA, and Base Spec references are exact and compatible |
| AAV-005 | PAC version and required signal handlers are complete and compatible |
| AAV-006 | At least one Skill Definition exists with KPI, Decision Space, and admitted schemas |
| AAV-007 | Tools/providers are declared, default denied, and mapped to governed action validation |
| AAV-008 | Billing profile and every active skill cost mapping are current and digest-bound |
| AAV-009 | DCM, Evidence First operations, independent checks, CCTs, and artifact digests align |
| AAV-010 | Configuration, goal, cadence, review, trial, degradation, data, retention, and stop policies are consistent |
| AAV-011 | Activation goals exist, or each exception has an admitted non-goal exemption record |
| AAV-012 | Runtime, environment, provider, billing, artifact, and constitutional assertions are exact, current, and available |
| AAV-013 | Submitter, approver, and transition actors satisfy separation of duties and Decision Space |
| AAV-014 | Approval and transition evidence bind exact content, evidence-set, artifact, actor, and policy digests |

A non-goal exemption is part of the admitted Skill Definition and contains `exemptionId`, purpose,
scope, measurable operational outcome, approving authority, constitutional acceptance reference,
effective period, and revocation conditions. It cannot be introduced during customer configuration
or supplied by the agent as an asserted approval.

### Threat Model And Integrity Controls

| Threat | Mandatory control | Proof |
|---|---|---|
| Forged approval or activation actor | Validated identity, operation entitlement, step-up, CE decision | `CCT-SEC-06`, `CCT-SEC-09` |
| Payload mutation or divergent replay | Server RFC 8785 digest, immutable submission, bound idempotency hash | `CCT-TR-13`, `BP-ADM-IDEMP-001..006` |
| Approval repudiation | Append-only actor, authority, digest, policy, time, and CE evidence tuple | `CCT-EF-05` |
| Identifier enumeration | Normalized not-accessible response and minimized telemetry | `CCT-SEC-07`, `CCT-MT-03` |
| Validation abuse or findings scraping | Per-actor throttling after auth; idempotent replay; no internal disclosure | `CCT-SEC-08` |
| Agent self-admission | Submitter/approver constraint and CE-enforced operation authority | `CCT-EF-06` |
| Stale readiness activation | Exact subject/environment/policy/freshness checks | `CCT-TR-15` |
| CE outage bypass | Fail-safe halt with no local success projection | `CCT-CE-AVAIL-02`, `CCT-EF-07` |

Content and evidence digests are recomputed server-side for every consequential transition. The
minimization allowlist for findings is the declared finding shape; denial telemetry uses only the
fields named in the authorization matrix. No retry can convert unknown, unavailable, stale, or
mismatched readiness into PASS without a new authoritative assertion.

### Rule-To-Claim And CCT Matrix

| Rule | Constitutional basis | Mandatory proof |
|---|---|---|
| AAV-001 | C-088, C-094 | `CCT-TR-11` |
| AAV-002 | C-059 | `CCT-TR-12` |
| AAV-003 | C-059, C-063 | `CCT-TR-13` |
| AAV-004 | C-070, C-094 | `CCT-TR-14` |
| AAV-005 | C-041, C-094 | `CCT-TR-15` |
| AAV-006 | C-036, C-037 | `CCT-TR-16` |
| AAV-007 | C-003, C-041 | `CCT-SEC-06` |
| AAV-008 | C-038, C-088 | `CCT-TR-17` |
| AAV-009 | C-023, C-059, C-099 | `CCT-EF-04` |
| AAV-010 | C-001, C-049, C-079 | `CCT-HO-03` |
| AAV-011 | C-037, C-049 | `CCT-TR-18` |
| AAV-012 | C-063, C-079 | `CCT-CE-AVAIL-02` |
| AAV-013 | C-003, C-065 | `CCT-SEC-09` |
| AAV-014 | C-023, C-059, C-063 | `CCT-EF-05` |

The implementation reserves `CCT-EF-04..07`, `CCT-SEC-06..09`, `CCT-MT-03`, `CCT-TR-11..18`,
`CCT-HO-03`, and `CCT-CE-AVAIL-02` for WC-079. It also implements operation authorization
`BP-ADM-AUTH-001..012`, idempotency `BP-ADM-IDEMP-001..006`, denial
`BP-ADM-DENIAL-001..005`, CE transitions `CE-ADM-TRANS-001..008`, and runtime guards
`PR-ADM-GUARD-001..006`. A proof ID reused across rows must contain separately asserted cases for
every mapped rule and threat; one passing assertion cannot satisfy multiple obligations implicitly.
Each test must fail against its named breach; execution alone is not proof.

## LLM And Token-Cost Controls

Admission truth is deterministic. Schema validation, compatibility, digests, rule evaluation,
catalogue eligibility, tests, scans, and evidence generation require no live LLM call.

- INST-010 uses repository search/indexes and the smallest task-owning context; do not repeatedly load
  full agent specifications, claims, ADRs, logs, or generated reports when a named section or index
  answers the task.
- Group related implementation edits and run focused deterministic checks at task boundaries rather
  than asking an LLM to diagnose every small edit.
- Validator findings are stable machine output. Do not use an LLM to reinterpret PASS/FAIL.
- If an admitted agent uses an LLM to help populate or explain its draft, the model output remains
  untrusted draft input and must pass the same deterministic schema and conformance rules.
- Cache optional draft assistance by normalized contract/schema/source hash. Never regenerate
  unchanged sections.
- Use the least-cost approved model that meets the bounded drafting task, send only failed paths and
  required local schema fragments, enforce a hard token/cost ceiling, and record model/prompt version,
  token totals, cost, cache hits, and retry reason.
- No autonomous retry follows a valid model response. One retry is permitted only for evidenced
  transport/provider failure using the same bounded request.
- Runtime validation and activation remain available without model-provider access.

## Platform IT Expert Skill Direction

After exact implementation authorization, INST-010 must apply:

| Skill | Required use in WC-079 |
|---|---|
| Skill 1 | Convert accepted WC-079 tasks and rule IDs into the implementation issue/spec trace |
| Skill 2 | Verify current-session implementation authority before any runnable change |
| Skill 3 | Establish the approved feature branch and preserve unrelated work |
| Skill 4 | Implement only accepted contracts; raise a spec gap rather than invent behavior |
| Skill 5 | Add focused unit, contract, integration, and constitutional tests |
| Skill 6 | Run pinned static, dependency, secret, and image security gates at qualification |
| Skill 7 | Prepare the Founder-ready PR with exact evidence and no self-approval/merge |
| Skill 8 | Use repository CI/gate order and observe results without bypass or repeated blind reruns |
| Skill 11 | Update only owning documentation required by verified contract changes |
| Skill 12 | Build and reuse hash-tagged Docker images; rebuild only when hashed inputs change |
| Skill 13 | Propagate only approved non-secret configuration and secret references |
| Skill 14 | Capture container logs/resource state before cleanup or retry and classify failures |
| Skill 15 | Validate OpenAPI, Compose, workflow, and structured contract YAML through pinned paths |
| Skill 17 | Execute deterministic Docker qualification, supply-chain scans, evidence, and rollback checks |

Skill availability is capability, not authority. This direction does not permit INST-010 to modify
architecture, invent API/data contracts, activate a provider, deploy, approve, or merge.

## Ordered Work Components

| Task | Scope and required output | Focused development check |
|---|---|---|
| AA-00 | Re-read current authority and accepted owner attachments; copy their frozen rule IDs, touched services, generated boundaries, exact test inventory, IB/issue, tier, and branch into the Skill 1 implementation spec. | Every attachment resolves to its accepted version; Compose config plus one deliberately invalid contract fixture proves validator activation |
| AA-01 | Publish/consume approved admission lifecycle, ownership, compatibility, and domain-model specifications. | Architecture fitness check finds no new deployable component or ambiguous owner |
| AA-02 | Add the canonical Agent Admission Contract JSON Schema/OpenAPI schemas and compatibility fixtures. | Valid minimal multi-skill package passes; missing/unknown/incompatible fields fail |
| AA-03 | Implement BP admission aggregate, immutable revisions, lifecycle projection, idempotency, RLS, and catalogue eligibility using the approved migration. | BP smoke plus focused lifecycle, digest, replay, RLS, and offerability tests |
| AA-04 | Implement deterministic authoring, DNA, Base Spec, PAC, ABP, DCM, skill, schema, CCT, and compatibility validators. | Endpoint-focused examples for each stable rule family and multi-finding output |
| AA-05 | Implement CE validation/evidence for submit, approve, reject, activate, suspend, supersede, and retire. | CE smoke plus allowed/prohibited transition and Evidence First tests |
| AA-06 | Implement WBE billing-readiness and provider/environment readiness projections without transferring admission authority. | Focused current/stale/unknown/unavailable/mismatch examples |
| AA-07 | Implement PR activation guard binding professional version, admission digest, artifact digest, runtime version, and customer contract. | PR smoke plus unadmitted/suspended/superseded/mismatched fail-closed tests |
| AA-08 | Implement approved public/internal generated clients and public-safe offerable-professional projection. | Only ACTIVE/current versions appear; internal findings and credentials never appear |
| AA-09 | Prove agent self-preparation without self-admission: create, revise, validate, remediate, and submit are allowed; approve/activate/lifecycle authority is denied. | Authorization matrix and adversarial caller tests |
| AA-10 | Prove the exact two professional type/version fixtures selected in the accepted INST-003 attachment: one current multi-skill customer professional and one materially different professional. | Same schema/rules pass both; agent-specific private admission logic is absent |
| AA-11 | Prove employment handoff compatibility for Web and WhatsApp projections without implementing the journey UI. | Channel-neutral fixtures produce the same admitted identity and skill schemas |
| AA-12 | Run focused regression for touched services and actual repository gate scripts; repair evidenced defects only. | Changed-service suites, generated drift, OpenAPI/YAML, traceability, and commit gates pass |
| AA-13 | Finalize commits, build reusable hash-tagged images once, run one complete qualification, bind evidence and author-review metadata to HEAD, validate both gates, and push once. | `wc079-qualification.json` reports PASS against exact HEAD and image IDs |

Do not run Docker tests after every small edit. During AA-00 through AA-12, run one smoke for each
changed service and endpoint-, rule-, or contract-focused tests at bounded task completion. Run full
coverage, complete builds, SBOM, Trivy, Gitleaks, and the deterministic multi-service campaign once
during AA-13. If a code defect is repaired, rerun the failed focused gate; perform one final clean
qualification only after commits are finalized again.

## Docker-Only Execution And Qualification Protocol

### Absolute Environment Rule

All Python, .NET, Node, schema, test, build, coverage, SBOM, Trivy, and Gitleaks execution must use
the repository's Docker/Compose test runners or accepted pinned containers. Virtual environments,
host `pip`, host Python tests, host Node package tests, and ad hoc host-installed scanners are
prohibited. Repository shell/git commands may orchestrate Docker and validate commit state.

### 1. Docker Preflight And Safe Capacity Recovery

Before any test or build:

```sh
docker version
docker compose version
docker system df
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}'
docker compose config --quiet
```

If capacity is inadequate, capture `docker system df -v` first. Remove only disposable artifacts:

```sh
docker image prune --force
docker builder prune --force --filter 'until=24h'
```

Never use `docker system prune`, `docker volume prune`, broad container pruning, or remove a running,
pinned, evidence, database, or user-named image/container/volume. Record before/after capacity. If
safe cleanup is insufficient, stop with a capacity blocker.

### 2. Quick Configuration And Smoke

Start with `docker compose config --quiet`. Build only changed services and their existing test
runners. Run exactly one service-owned health or contract smoke per changed service before broader
focused checks. A smoke proves startup, dependency wiring, health, and one minimal admission request;
it does not replace tests or trigger the full campaign.

### 3. Immutable Local Image Identity And Reuse

Calculate a deterministic sorted inventory and normalization algorithm in the qualification script:

```text
SOURCE_HASH = first 12 hex of SHA-256 over tracked WC-079 implementation inputs
CONFIG_HASH = first 12 hex of SHA-256 over normalized Compose, locks, schemas, and pinned tool inputs
IMAGE_TAG   = wc079-${SOURCE_HASH}-${CONFIG_HASH}
```

Build each changed service/test image once for final qualification. Record image ID and digest and
reuse those exact images across smoke, focused guard, full tests, coverage, build inspection, SBOM,
Trivy, Gitleaks context, and evidence assembly. No gate may rebuild an image. A relevant source,
schema, lock, Dockerfile, Compose, workflow, or tool-version change invalidates the hash and requires
one new final image set.

### 4. Evidence-First Failure And Retry Rule

Before cleanup or retry, capture:

```sh
docker compose ps --all
docker compose logs --no-color --timestamps <changed-service>
docker inspect <container>
docker system df
```

Record exit code and classify code/configuration, assertion, security, capacity, daemon/network,
registry, or external dependency failure. Retry unchanged code once only when logs and resource state
demonstrate infrastructure failure. Never retry a deterministic test, lint, build, contract, schema,
or scan failure. Repair the same slice and run its focused gate.

### 5. Focused Development And Final Campaign

During development, use endpoint-focused examples for draft creation, revision, validate/findings,
submit, unauthorized approval/activation, authorized transitions, offerability, and PR activation
guard. Use targeted tests for each changed service and reserve the complete deterministic campaign
for final qualification.

INST-010 must add one Docker-based repository command:

```sh
./scripts/wc079_qualify.sh --output test-results/wc079/wc079-qualification.json
```

The command may use host POSIX shell, Docker/Compose, git, and jq only for orchestration. It must run
repository-pinned tools, fail closed, redact secrets/customer data, and produce evidence JSON directly
from observed successful runs. In order it performs:

1. Docker capacity/state capture, safe disposable cleanup when necessary, and Compose validation.
2. Source/config hash calculation and one build of each reusable qualified image.
3. One smoke per changed service and focused endpoint/rule examples as a fast guard.
4. Full changed-service unit, contract, integration, migration, RLS, generated-client, and CCT suites.
5. Full coverage with repository constitutional thresholds, including at least 90% line coverage for
   new/touched logic where the controlling gate requires it.
6. Production builds/compilation for every changed service from the exact qualified images.
7. Deterministic two-professional admission, lifecycle, authorization, compatibility, channel-handoff,
   and fail-closed campaign.
8. SBOM generation from each exact qualified service image.
9. Trivy HIGH/CRITICAL image scanning using the pinned repository policy/version.
10. Gitleaks repository history/diff scanning using the pinned repository policy/version.
11. Repository actual gates, including generated drift, OpenAPI/schema/YAML, C-059 traceability,
    commit format, `scripts/gap_scanner.py`, `scripts/validate_author_review.py`, and
    `scripts/pr_guard.py` through their accepted Docker/CI execution paths.
12. Evidence JSON assembly and schema validation.

Evidence contains at minimum WC ID, result, exact 40-character HEAD, source/config hashes, image
names/tags/IDs/digests, Docker before/cleanup/after, smokes, focused examples, tests/counts, coverage,
builds, two-professional campaign, authorization denials, compatibility/fail-closed outcomes, SBOM
paths/hashes, Trivy and Gitleaks report hashes, repository gate commands/versions/exit codes, start/end
times, and redacted failure classification. `PASS` is impossible unless every mandatory result passed
against the recorded HEAD and image IDs.

Generated qualification reports remain under ignored `test-results/` or CI artifact storage. They
are not committed after qualification because changing HEAD invalidates the binding.

### 6. Commit, Evidence, PR, And Push Order

1. Complete implementation and focused repairs.
2. Finalize all intended commits with repository-conforming subject and mandatory traceability body.
3. Run the one complete WC-079 qualification against finalized HEAD.
4. Make no source/config/schema/tool change after qualification.
5. Prepare the PR body locally from the repository template with exact evidence path/hash, image IDs,
   coverage, SBOM, Trivy, Gitleaks, rollback, and findings.
6. Perform mandatory author review against the complete diff and exact qualification results.
7. Bind review metadata to the full HEAD with the repository-approved `pr_guard.py finalize-review`
   path.
8. Validate the prepared PR body with `validate_author_review.py` and validate commits with
  `pr_guard.py pre-push` through repository-approved paths. For a new remote branch, the guard's
  documented no-open-PR result validates commits only and is not evidence that C-065 PR metadata passed.
9. Push the finalized implementation HEAD once, open the unmerged PR using the already validated body,
  and require the PR/CI C-065 guard to validate the server-side body against the same HEAD. Do not
  claim final gate PASS until that post-open check succeeds. Any later commit requires fresh
  qualification, review binding, push, and PR validation.

## Acceptance Matrix

| ID | Acceptance condition |
|---|---|
| AA-ACC-01 | One versioned machine-readable Agent Admission Contract joins all required existing contracts without creating a parallel agent model or new service |
| AA-ACC-02 | Only ACTIVE, current, compatible, environment-offerable professional versions appear in public/customer catalogue projections |
| AA-ACC-03 | Professional version has one or more Skill Definitions with KPI, Decision Space, tools/providers, schemas, cost, cadence, trial, and degradation declarations |
| AA-ACC-04 | Skill Instance supports zero-to-many versioned configuration, goal, schedule, and review records with effective time and evidence lineage |
| AA-ACC-05 | Zero goals are accepted in draft/configuration and rejected at activation unless an exact admitted operational-purpose exemption applies |
| AA-ACC-06 | Thirty days defaults review cadence only; execution schedules remain skill-specific or event-driven |
| AA-ACC-07 | Agent owner can create, revise, validate, remediate, and submit but cannot approve, activate, suspend, supersede, retire, or forge readiness/evidence |
| AA-ACC-08 | Validation is deterministic, uses stable rule IDs, reports all safe findings, and cannot be overridden by LLM output |
| AA-ACC-09 | Every approval and lifecycle transition binds an immutable revision, contract digest, artifact digest where applicable, actor, authority, and evidence |
| AA-ACC-10 | Unknown, stale, unavailable, mismatched, unapproved, or unadmitted dependencies fail closed and never appear as PASS/ACTIVE |
| AA-ACC-11 | PR rejects unadmitted, suspended, superseded, artifact-mismatched, or runtime-incompatible activation |
| AA-ACC-12 | One current multi-skill professional and one materially different professional pass the same contract and tests without private admission logic |
| AA-ACC-13 | Web and WhatsApp handoff fixtures expose the same admitted identity and skill schemas without duplicating lifecycle authority |
| AA-ACC-14 | RLS, service authorization, idempotency, replay, concurrency, anti-enumeration, data minimization, and secret isolation pass |
| AA-ACC-15 | Consequential transitions satisfy Evidence First; Emergency Stop and existing customer rights remain unchanged and reachable |
| AA-ACC-16 | Runtime admission validation requires no LLM/provider availability and optional draft assistance cannot determine PASS |
| AA-ACC-17 | Focused checks are used during development; full coverage/build/SBOM/Trivy/Gitleaks execute once in final qualification |
| AA-ACC-18 | One Docker qualification command emits schema-valid PASS evidence bound to final HEAD and reused hash-tagged image IDs |
| AA-ACC-19 | Local repository gates and pinned tools pass before one push; after PR creation, server-side C-065 metadata validation passes against the same 40-character HEAD before final PASS |

## Rollback And Compatibility

- Admission schema uses semantic versioning and explicit negotiation. Within an exact supported schema
  version, unknown fields fail. Additive optional fields may enter a new minor version only after the
  corresponding validator is deployed; an older validator rejects that higher minor with AAV-002
  rather than reporting each field as unknown. Removed, renamed, retyped, or meaning-changing fields
  require a new major with an explicit support window. No forward-compatibility inference is allowed.
- ACTIVE professional versions are immutable. Rollback selects a prior still-supported admitted
  version and exact artifact digest; it never edits the failed version in place.
- Suspension prevents new trial/hire and activation immediately. Existing relationship treatment is
  governed explicitly and is not silently terminated or migrated.
- Catalogue projection can suppress a version independently of deleting its records. Admission and
  evidence records remain attributable and append-only.
- Database change is additive, migration-tested, tenant-isolated, and rollback-safe. Constitutional
  evidence is never deleted or rewritten.
- Build once and promote the same accepted digests only through separately authorized environment
  gates. WC-079 authorizes no deployment or provider activation.

## Stops

- Stop before any runnable implementation without explicit Founder authorization for WC-079 in the
  current session.
- Stop if any required owner specification or acceptance is missing, stale, contradictory, or would
  require INST-010 to invent architecture, API, data, security, constitutional, or product policy.
- Stop rather than create a new deployable Admission service without a separately accepted ADR and
  component decision.
- Stop rather than let an agent approve, activate, suspend, supersede, retire, or alter its own
  admission rules, validators, findings, evidence, or lifecycle authority.
- Stop rather than offer a non-ACTIVE, stale, incompatible, unprofiled, digest-mismatched, or
  environment-unready professional version.
- Stop rather than treat an LLM answer, agent assertion, transport success, test fixture, or provider
  capability as admission evidence.
- Stop rather than conflate 30-day review cadence with skill execution frequency.
- Stop rather than require a goal during draft/interview or activate a goal-less skill without an
  exact approved exemption.
- Stop rather than run a virtual environment, host test/package runtime, ad hoc scanner, or unpinned
  tool.
- Stop if safe Docker cleanup cannot provide capacity; never delete persistent volumes or protected
  artifacts to force qualification.
- Stop on deterministic test, contract, build, coverage, or security failure; never hide it through
  blind retry, exclusion, threshold reduction, baseline replacement, or fabricated evidence.
- Stop if qualification evidence, images, hashes, tool versions, author review, or PR metadata do not
  bind the same final HEAD.
- Never self-approve, self-merge, push directly to `main`, activate providers, mutate environments,
  deploy, or claim customer proof under WC-079.

## Definition Of Done

- The Agent Admission Contract is approved as the single machine-readable admission package joining
  the existing authoring, constitutional, PAC, billing, provider, runtime, and employment foundations.
- Exact owner-approved logical, API, persistence, security, constitutional, compatibility, evidence,
  and migration contracts exist before implementation begins.
- Tasks AA-00 through AA-13 and AA-ACC-01 through AA-ACC-19 are traceable through specifications,
  source, tests, evidence, commits, and PR metadata.
- WAOOAW catalogue and activation boundaries accept only exact ACTIVE professional versions whose
  current admission revision, artifact, runtime, billing, provider/environment, and constitutional
  gates pass.
- Agents can prepare and remediate their own package but cannot change the rules or perform any
  independent admission or activation transition.
- One multi-skill customer professional and one materially different professional pass the same
  deterministic contract, including rejection, suspension, supersession, and incompatibility paths.
- Skill cardinalities and version history support customer-specific configuration, goals, schedules,
  and reviews; 30 days is preserved as default review rather than execution frequency.
- Web and WhatsApp can consume one channel-neutral admitted professional/skill foundation for the
  future employment journey without agent-specific hiring logic.
- No runtime admission decision depends on an LLM. Development LLM use is bounded, minimal-context,
  cached, measured, and never accepted without deterministic gates.
- Docker execution uses preflight and safe cleanup, one smoke per changed service, focused development
  checks, reusable hash-tagged images, evidence-first failure diagnosis, and one final campaign.
- Final coverage, builds, SBOM, Trivy, Gitleaks, repository gates, qualification evidence, author
  review, and unmerged PR all bind the same final 40-character HEAD. Founder retains approval and
  merge authority.

## Author Review

**Result:** PASS - targeted consolidated institutional repair complete; Founder acceptance of this
exact commit, AEEC acceptance, implementation-issue binding, and current-session implementation
authorization remain separately gated.

| Review perspective | Result | Resolution |
|---|---|---|
| INST-003 Business Architect | PASS | Reusable admission outcome fixed; DMA v3.1 and Trading v1.8 frozen; no second product model |
| INST-004 Enterprise Architect | PASS | Existing BP/CE/PR/WBE ownership retained; no new service; compatibility decisions closed |
| INST-005 Solution Architect | PASS | Exact paths, callers, responses, errors, idempotency, versioning, and generated-client boundary fixed |
| INST-006 Data Architect | PASS | Migration 25 tables, keys, RLS, concurrency, retention, outbox, and rollback fixed |
| INST-007 Security Architect | PASS | Authorization matrix, step-up, separation, anti-enumeration, threat controls, and minimization fixed |
| INST-002 Constitutional Analyst | PASS | AAV-to-claim/CCT mapping, Evidence First ordering, fail-safe halt, and Human Override fixed |
| INST-010 Platform IT Expert | PASS | Frozen surfaces and test IDs make implementation mechanical after remaining acceptance gates |

INST-004 reviewed this complete Work Contract against the Founder instruction, Objective B of the
consolidated foundation assessment, the ratified claim index, ADR index, Agent Authoring Guide,
Constitutional DNA, Agent Base Spec, Platform-Agent Contract direction, Agent Employment Experience
Contract, and existing BP/CE/PR/WBE ownership boundaries.

The review checked requirements coverage, professional-versus-customer onboarding separation,
anti-self-approval controls, lifecycle completeness, cardinality and cadence semantics, immutable
version/digest binding, deterministic validation, catalogue suppression, service ownership, fail-safe
activation, channel neutrality, compatibility and rollback, LLM token minimization, Docker-only
execution, safe disk recovery, focused development checks, image reuse, evidence-first retry, one
final qualification, repository gate discovery, final-commit ordering, evidence/PR binding, and all
constitutional stops.

Findings repaired in this contract include ambiguous fixture choice, pending AEEC status disclosure,
missing exact wire and generated-client boundaries, absent persistence/RLS/concurrency details,
underspecified actor authority and anti-enumeration, missing threat and AAV/CCT traceability, ambiguity
between self-preparation and self-admission, customer-journey overlap, accidental creation of a new
service, conflation of review and execution cadence, mutable admission state, model-based PASS,
repeated heavyweight Docker validation, unsafe cleanup, blind retries, and stale qualification
evidence. No unresolved technical or policy choice was found in the targeted review of this plan.
Founder acceptance, AEEC acceptance, implementation binding, and current-session authority remain
open gates; author review is not institutional approval and does not close them.
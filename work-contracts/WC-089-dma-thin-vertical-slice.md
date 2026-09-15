# Work Contract 089 - DMA Thin Vertical Slice And Agent Image Proof

**Office:** Solution Architect (INST-005), then Platform IT Expert (INST-010) only after implementation authorization
**Assigned by:** Founder instruction, 2026-09-10
**Status:** FOUNDER ACCEPTED - IMPLEMENTATION AND LOCAL CANDIDATE BUILD AUTHORIZED FOR 2026-09-15 SESSION; PROVIDER/CLOUD/DEPLOYMENT PROHIBITED
**Design direction:** Founder instruction, 2026-09-15 - first product/image release remains Release 1; requirements/specification revisions are independent
**Implementation issue:** GitHub Issue #437 on branch `ib/089/dma-release-1`
**Delivery unit:** One admitted DMA Release 1 image (`professionalVersion: 1.0.0`), customer-specific instances, Skills 0/1/2, generic hosting closures, conformance, qualification and Founder-ready PR
**Concept:** `architecture/dma-agent-image-concept.md`
**Controlling plan:** `architecture/dma-thin-vertical-slice-execution-plan.md`
**Predecessors:** WC-079, WC-080, WC-087 and WC-088 merged
**Constitutional basis:** C-001, C-023, C-026, C-035, C-049, C-059, C-065, C-071, C-079

## Authority And Scope

The Founder accepted the revised plan and authorized repository implementation plus local candidate
image build in the 2026-09-15 session. Authority is bound to Issue #437, Release 1 / version `1.0.0`,
the named branch, paths, tests, fixtures and local Docker qualification. It does not authorize
provider access, expenditure, cloud/environment mutation, deployment, DNS, customer traffic, UAT,
Production, PR approval or merge.

The implementing Platform IT Expert must validate every controlling-plan entry gate before touching
runnable paths. This session's explicit authority satisfies the per-session authorization gate only
for Issue #437; a Work Contract identifier, accepted plan, issue, label, or clear platform gate does
not authorize a later session.

The controlling plan is normative for responsibilities, interfaces, data shapes, ordered components,
tests, Docker qualification, token optimization, stops, review and Definition of Done. An executor
must stop on a missing or contradictory contract rather than invent policy or expand DMA scope.

This Work Contract controls the product/image release identity, lifecycle semantics, inherited
governance, constitutional behavior, customer experience and completion boundary. The concept
controls type-image/customer-instance architecture. The controlling plan decomposes implementation.
The accepted reference architecture and ADRs control platform boundaries. If these sources conflict,
implementation stops and returns to Solution Architecture; the executor must not choose a convenient
interpretation.

## Objective

Establish the first reusable WAOOAW method for developing, governing, admitting, employing, inducting,
operating, improving and replacing a customer-facing digital professional. Prove the method with one
real Digital Marketing Agent Release 1 image and a bounded Profile -> Research -> Strategy journey.
The outcome is not merely a working DMA adapter. It is an executable institutional pattern that later
agents can reuse without redefining constitutional inheritance, employment lifecycle, image trust,
customer-instance isolation, platform ownership, operational gates or release governance.

Release 1 must prove all of the following as one coherent customer outcome:

1. an approved professional definition can be groomed into fixed machine-readable Skill, PAC,
   runtime, data, security, evidence, billing and customer-experience contracts;
2. Founder approval fixes the product release before any image for that release is built;
3. one immutable admitted image can serve multiple isolated trial and hired agent instances without
   becoming a customer identity or containing customer state;
4. after trial start or paid activation, a customer can Onboard, complete agent-led Induct, verify
   goals, receive governed business outcomes and reach Operations through the Customer Portal;
5. every action inherits WAOOAW's constitutional DNA and Agent Base Spec, uses the Platform-Agent
   Contract, and remains within the accepted Employment Contract and Decision Space;
6. BP, CE, PR, AIR/CTG, oauth-vault and WBE remain authoritative for their existing platform concerns,
   while the DMA image owns only admitted domain behavior; and
7. failure, replay, concurrency, Stop, upgrade and rollback preserve truth, isolation, evidence and
   prior admitted relationships.

Close only reusable hosting gaps required by this journey so later Skills and professional types can
be admitted through additive releases rather than shared-platform redesign. The DMA adapter remains a
private workload outside the exact-six platform release tuple, not a seventh platform service.

## Product, Specification And Image Version Contract

Version axes are independent and must be persisted, displayed and validated as distinct fields:

| Axis | WC-089 fixed value or rule | Authority and meaning |
|---|---|---|
| Professional product release | `releaseSequence: 1` | Founder-governed ordinal for the first customer-operable DMA release |
| Professional version | `professionalVersion: 1.0.0` | Immutable catalogue/admission coordinate for Release 1 |
| DMA requirements/specification revision | Current referenced gate-pass input is `3.1`; repository status records version-specific Founder approval only through `3.0` | Design maturity of `digital-marketing-agent.md`; the exact mapped revision requires Founder acceptance and does not set the product/image version |
| Image identity | OCI digest produced only after approval and authorized build | Immutable executable artifact identity; tags are never authority |
| Skill versions | Independently admitted SemVer for Skills 0/1/2 | Skill contract and behavior compatibility; never inferred from professional or spec version |
| PAC/base-spec/schema versions | Independently declared compatibility coordinates | Platform signal and mandatory behavior compatibility |
| Prompt identity | Exact approved prompt version/SHA per inference | Behavioral provenance; prompt promotion does not silently re-version the image |

The Release 1 mapping is therefore: one Founder-approved professional release `1.0.0` may implement
DMA requirements/specification revision `3.1`. The implementation issue must freeze the exact spec
commit and every subordinate contract version. It must not derive `professionalVersion` from the spec
heading, adapter audience, mutable tag, branch, package version or prior fixture.

No agent image may be built, published, signed, admitted, activated or presented as a new release until
the Founder approves that exact professional release for build in a current authority record. Founder
acceptance of this planning package does not itself authorize a build. After approval, source,
dependency, executable behavior, package manifest or included Skill changes produce a new candidate
digest and invalidate prior candidate evidence. No active admission, image, digest, relationship or
accepted Skill binding is changed in place. A later professional version or Release 2 requires a new
Founder decision; an implementation agent must never bump it autonomously.

The candidate-image builder must fail closed before its first build operation unless it receives and
validates the exact Founder release approval and current-session build authorization for Release 1,
`professionalVersion: 1.0.0`, mapped specification commit, source HEAD, builder identity and permitted
environment. Provenance must record both authority references and prove `buildStartedAt` is later than
their effective times. Missing, expired, mismatched or replayed authority produces no local image,
registry artifact, signature, provenance statement, SBOM, admission draft mutation or success claim.

## Dual Lifecycle Contract

### A. Professional Type And Release Lifecycle

WC-089 composes governed design/build checkpoints with WC-079's canonical BP-owned admission
lifecycle. It does not create a second lifecycle aggregate or new service.

```text
DESIGN DRAFT -> GROOMED -> OWNER REVIEWED -> FOUNDER RELEASE APPROVED
FOUNDER RELEASE APPROVED -> CURRENT-SESSION BUILD AUTHORIZED -> CANDIDATE EVIDENCE COMPLETE
                         -> WC-079 ADMISSION DRAFT

WC-079 canonical admission lifecycle:
DRAFT -> VALIDATING -> REMEDIATION_REQUIRED | VALIDATED
REMEDIATION_REQUIRED -> DRAFT
VALIDATED -> DRAFT | READY_FOR_REVIEW
READY_FOR_REVIEW -> APPROVED | REJECTED
REJECTED -> DRAFT
APPROVED -> ACTIVE
ACTIVE -> SUSPENDED | SUPERSEDED | RETIRED
SUSPENDED -> ACTIVE | SUPERSEDED | RETIRED
```

| Checkpoint or state family | Authoritative owner | Required immutable or versioned evidence |
|---|---|---|
| Design draft and grooming | Owning architecture artifacts under assigned Work Contract | Exact revisions, requirements, dependency/risk register, simulations and acceptance matrix |
| Owner review | Each authorized reviewing office within its Decision Space | Findings, repairs, unresolved blockers, reviewed commit and no claim of Founder approval |
| Founder release approval | Founder | Exact professional type, Release 1 / `1.0.0`, mapped specification revision/commit, allowed build purpose and explicit boundary |
| Current-session build authorization | Founder/session authority boundary | Exact branch/HEAD, paths, builder, environment, versions, fixtures, tests and qualification command |
| Candidate evidence | Authorized builder and deterministic qualification | Authority refs/times, source/build identity, OCI digest, signature, provenance, SBOM, schemas, conformance and scans |
| Admission lifecycle | Business Platform under WC-079, with CE decision/evidence | Canonical admission revision/state, content/artifact/evidence-set digests, actor, authority, readiness and append-only transitions |
| Runtime activation enforcement | Professional Runtime from BP activation registry | Exact environment + type + professional version + artifact digest resolution and fail-closed compatibility |

`BUILT`, `CONFORMANCE_PASS` and `ACTIVATABLE` are evidence/readiness descriptions, not additional
admission states. `GROOMED` and `OWNER REVIEWED` are document-governance checkpoints, not customer or
runtime states. Only BP may coordinate WC-079 admission transitions; the DMA image, browser, builder,
submitter and reviewing offices cannot approve or activate themselves.

No checkpoint or canonical state may be skipped or inferred from another. A failed design/build check
returns to its owning checkpoint. A failed admission transition follows WC-079 exactly. Evidence from
another version, digest, environment, tenant, relationship or instance cannot promote this release.

### B. Customer Employment And Operational Lifecycle

Trial start or paid activation establishes or continues one BP-owned Employment Relationship and one
immutable `agentInstanceId`. The customer-facing lifecycle after that entry is:

```text
Onboard -> Induct -> Goal Verification -> Business Outcomes -> Operations
```

- `Onboard` is a two-minute preference step: customer-approved professional display name, presentation,
  chat appearance and timestamp/visibility choices. It never changes image behavior, authority,
  professional version, Skill version, contract, goal, billing or lifecycle truth.
- `Induct` is an agent-led conversation, not a form. The DMA introduces its admitted Skills and limits,
  learns business identity, domain vocabulary, audience, priorities, constraints, approved channels
  and baseline, distinguishes observed/inferred/missing/confirmed information, and obtains explicit
  confirmation. Skill 0 supplies the typed profiling behavior, but BP owns confirmed context and
  correction lineage.
- `Goal Verification` turns the confirmed profile and bounded customer intent into explicit goals.
  Every goal binds a declared Skill, measure definition, review frequency, Decision Space, budget,
  stop condition and customer verification. The agent asks only what is necessary and never invents a
  target, baseline, attribution rule or authority.
- `Business Outcomes` presents Skill 1's reviewed, cited research and Skill 2's approval-gated strategy
  as customer-facing outcomes with provenance, limitations and attribution boundaries. Agent
  performance and external business results remain distinct; no conversion or revenue is guaranteed.
- `Operations` unlocks only from BP-owned eligibility after all required goals and configuration are
  current and verified. Browser state, DMA output, image readiness, payment alone or model confidence
  cannot unlock it. Material goal/configuration/contract changes relock affected work for reassessment.

Trial and hired instances use the same constitutional protections and instance isolation. Trial mode
remains explicit, zero-priced/zero-cost where required, cannot perform consequential external action,
and cannot silently become paid or live. Paid activation cannot reuse trial authority. Pause, Emergency
Stop, resume and termination remain governed Employment Relationship transitions, not adapter states.

## Contract Inheritance And Ownership

Every invocation must resolve and prove this complete contract stack before domain parsing or work:

1. ratified Constitution and `CONSTITUTIONAL_DNA v2.0`;
2. current `AGENT-BASE-SPEC` and ADR-035 Platform-Agent Contract compatibility;
3. Founder-approved DMA professional release and exact mapped specification commit;
4. admitted professional, image, Skill, prompt, schema and runtime-adapter versions/digests;
5. BP-owned Employment Relationship, accepted Employment Contract, trial/live mode and immutable
   `agentInstanceId`;
6. current customer configuration, verified goals, Decision Space, budget, approvals and Stop state;
7. PR-issued single-use invocation authority and CE/WBE preconditions.

Missing, stale, incompatible, unsupported or contradictory layers fail closed. Capability and trust
never create authority. Customer/model/adapter payloads cannot assert trusted tenant, relationship,
instance, contract, version, price, approval, evidence or operational eligibility.

| Owner | Authoritative responsibility | Explicit prohibition |
|---|---|---|
| Business Platform | Relationship, instance, contract, configuration, goals, customer decisions, lifecycle, work and portal truth | DMA execution, constitutional acceptance or billing settlement |
| Constitutional Engine | Decision consequence enforcement, authority validation, Evidence First and Stop evidence | Domain execution, customer payload ownership or price |
| Professional Runtime | Durable invocation, adapter resolution, deadlines, replay, cancellation, Stop and result validation | DMA branches, customer truth or silent relationship rebinding |
| AI Runtime / CTG | Approved prompt/model routing, PII handling and purpose-bound governed tools | Employment identity, authority, evidence acceptance or direct customer billing |
| oauth-vault | Scoped provider credential custody and retrieval evidence | Customer workflow, domain decisions or credential disclosure to the portal |
| WBE | Reservation, zero-priced trial allowance, metering, attribution and reconciliation facts | Customer identity payload, professional execution or authority decisions |
| DMA Release 1 image | Admitted Skill 0/1/2 domain interpretation and typed proposed results | Durable customer truth, lifecycle mutation, admission, billing, evidence acceptance, direct provider authority or portal access |
| Customer Portal | Relationship-scoped presentation and typed BP commands | Browser-owned lifecycle, ranking, authority, version selection, billing calculation or adapter access |

## Governance, Instinct And Constitutional Compliance

All three constitutional instincts apply to every Release 1 path, including onboarding and reads that
lead to later action. Domain configuration may specialize vocabulary and thresholds but cannot weaken
the inherited obligations.

### Instinct 1 - Follow The Constitution

- Classify every consequential decision through the DMA Decision Consequence Map before execution.
  Undeclared decision types block; complexity or model confidence never lowers consequence category.
- Call CE.ValidateAction before every governed tool/action and commit Evidence First before observable
  state change, data write or customer-visible output where the constitutional contract requires it.
  CE unavailability halts consequential work while
  preserving honest read-only/advisory behavior.
- Keep Emergency Stop reachable and effective within the constitutional SLO during induction, queued
  work, active AI/tool work, customer approval wait, retry, saturation and dependency failure. Stop is
  latched; resume requires fresh same-tenant authority.
- Enforce C-049 honest limitation for missing data, partial research, uncertainty, unavailable tools,
  degraded services and out-of-scope requests. Do not bill known-undeliverable work.
- Enforce Decision Space, consent, purpose, budget, data minimization, tenant/instance isolation and
  no external publication/provider write in Release 1.

### Instinct 2 - Improve Itself Without Self-Authorizing

- Record privacy-minimized quality signals for every Skill outcome: delivered, partial, escalated,
  failed, stopped, customer-corrected and customer-rejected.
- Preserve exact prompt SHA, professional/Skill versions, input revisions, provider/tool route and
  outcome evidence so quality changes are attributable rather than anecdotal.
- Use acceptance simulations and aggregate signals to propose prompt, Skill, contract or platform
  improvements. The running agent may not alter its image, version, Skill contract, Decision Space,
  prompt promotion or constitutional rules.
- Prompt-only improvements follow prompt governance. Behavior/dependency/Skill/package changes require
  the applicable agent update flow, conformance, Founder approval and a new admitted release/digest.

### Instinct 3 - Earned Autonomous And Trust-Based Execution

- New customer instances begin at the inherited conservative trust tier. Autonomy is earned from
  relationship-specific evidence and remains bounded by that customer's current Decision Space.
- CE validation, Evidence First, Stop, budget and platform ownership apply at every trust tier.
- Release 1 ends at an approved strategy and performs no external publication, scheduling, provider
  write or ad spend, even if another DMA specification section describes future Tier 0 behavior.
- Trust, capability, image admission and customer authority are separate dimensions. Success in one
  tenant or instance cannot raise another instance's authority or combine their learning payloads.

### Required Alignment Evidence

Implementation must produce a machine-checkable trace matrix from every WC-089 acceptance condition
to constitutional claims, AEEC clauses, base-spec/PAC duties, component owner, contract/schema field,
test/CCT, exact source commit and exact image digest. A narrative assertion, model evaluation or passing
happy-path browser test cannot substitute for a missing deterministic contract or constitutional gate.

## Required Inputs

- Founder-accepted concept and controlling plan bound to exact commits.
- Merged WC-079 admission, WC-080 adapter, WC-087 instance and WC-088 Skill journey foundations.
- Current accepted ADR-035 and ADR-049 boundaries.
- Accepted Enterprise, Data, Security and Platform implementability review results for this revised
  Release 1 mapping, recorded in controlling-plan Section 17 without treating author review as approval.
- Implementation issue freezing branch, paths, contract versions, CCTs, fixtures, environments and
  qualification command.
- Explicit Founder implementation authorization in the implementing session.

The implementation issue must additionally freeze `releaseSequence: 1`,
`professionalVersion: 1.0.0`, DMA specification revision and commit, Skill/PAC/base/schema/prompt
versions, canonical adapter audience, admission snapshot, candidate-build policy, lifecycle-to-portal
mapping, trace matrix, scenario fixtures and the exact negative selectors. Any `TO FREEZE`, placeholder,
legacy alias, unapproved version or contradictory owner contract keeps DMA-00 blocked.

## Mandatory Proactive Simulations

The following are release gates, not optional demonstrations:

| Scenario | Required proof |
|---|---|
| Release rejected before approval | Builder denies before execution; no local image, registry artifact, signature, provenance, SBOM, admission mutation or version change exists |
| Spec `3.1` mapped to product `1.0.0` | Both coordinates remain distinct through catalogue, admission, descriptor, runtime, evidence and portal projection |
| Interrupted Induct | Resume continues one relationship/instance with confirmed revisions and no duplicate questions or invented facts |
| Stale or concurrent confirmation | Old profile/goal/strategy revision conflicts with zero overwrite or cross-instance disclosure |
| Trial to paid activation | New authority and billing state are explicit; trial delegation, allowance and mode cannot be replayed into live work |
| Two tenants on one digest | Concurrent Profile -> Research -> Strategy has zero data, evidence, usage, cache, prompt-context or Stop crossover |
| Two instances in one tenant | Goals, configuration, work, approvals, usage, trust and Stop remain instance-specific |
| Partial research failure | Cited partial result names unavailable sources and limitations; no unsupported success or duplicate charge/tool call |
| CE, AIR, WBE or tool outage | Each component follows its declared fail-safe/degradation contract and customer disclosure without authority expansion |
| Stop under active/saturated work | Queued and running work halt within SLO; late result is rejected; unrelated instance continues; resume needs fresh authority |
| Material goal/configuration amendment | Affected Operations work relocks and is reassessed without erasing prior decisions or evidence |
| Erasure and legal hold | Eligible payload is removed/tombstoned without resurrecting content or rewriting minimum immutable attribution |
| Old/new admitted release coexistence | Existing instance remains pinned; unsupported mappings fail; rollback selects an already admitted digest without rebinding |
| Portal refresh/channel handoff | BP reconstructs one authoritative lifecycle/work state; browser or channel storage cannot create authority or lose Stop access |

## Definition Of Done

WC-089 implementation is complete only when every condition below and controlling-plan Section 16
passes against the same finalized source HEAD and image digest:

### Release And Governance

- Founder acceptance binds Release 1 / `professionalVersion: 1.0.0` to the exact DMA specification
  revision and owner-reviewed contract set before build authorization.
- The image is built only after explicit current-session implementation authority; source, build,
  authority references/times, signature, provenance, SBOM, conformance, admission, activation
  resolution, descriptor and runtime digest form one verifiable chain. A tag or descriptor assertion
  is insufficient, and a pre-authority build cannot qualify retroactively.
- No image/version/admission is changed in place, no per-customer image exists, and no seventh platform
  service or DMA-specific branch is introduced into shared platform services.
- The complete contract stack and constitutional trace matrix are machine-validated with no missing,
  placeholder, stale, incompatible or contradictory coordinate.

### Customer Lifecycle And Product Outcome

- Two tenants and two same-tenant instances complete Onboard -> Induct -> Goal Verification ->
  Business Outcomes -> Operations using one admitted Release 1 digest with strict separation.
- Onboard changes presentation preferences only; Induct produces explicitly confirmed BP-owned context
  and correction lineage; Operations remains locked until required goals are current and verified.
- Real Skills 0/1/2 complete Profile -> cited Research -> approval-gated Strategy with no fourth Skill,
  external publication, provider credential, paid advertising or Production traffic.
- Trial/hire, mode transition, pause, Stop, resume, material amendment, reassessment and termination
  preserve AEEC rights, relationship identity, authority, billing and evidence semantics.
- Customer Portal truth is reconstructed from BP and exposes lifecycle, work, approval, outcome,
  limitation, usage and Stop without exposing adapter topology or inventing authority.

### Constitutional, Data, Security And Resilience

- Instinct 1 evidence proves DCM classification, CE validation, Evidence First, honest limitation,
  fail-safe behavior, consent/Decision Space enforcement and Stop under real active work.
- Instinct 2 evidence proves version-bound quality signals and governed improvement proposals without
  self-modifying image, version, prompt, Skill, authority or policy.
- Instinct 3 evidence proves relationship-specific earned autonomy without bypassing constitutional
  gates or transferring trust/authority between customers or instances.
- BP/CE/PR/AIR-CTG/oauth-vault/WBE/DMA ownership, revision, lineage, retention, erasure, legal hold,
  immutable facts, idempotency, replay, usage attribution and version coexistence invariants pass.
- Every mandatory proactive simulation passes deterministically or blocks release; model quality cannot
  override a contract, security, privacy, constitutional or isolation failure.

### Engineering Qualification And Handoff

- Focused checks follow every bounded component; one consolidated Docker campaign and one final
  Docker-only qualification reuse exact image IDs and bind tests, CCTs, coverage, builds, OpenAPI/schema
  drift, generated clients, SBOM, scans, privacy checks and report hashes to exact HEAD/digest.
- Author review covers correctness, constitutional alignment, security, privacy, compatibility,
  failure handling, operability and rollback, with every manageable finding repaired and rerun.
- One unmerged PR is prepared from exact pushed-head C-059/C-065 evidence for Founder review. No
  self-approval, self-merge, deployment, provider acceptance or Production claim occurs.

Section 17 of the controlling plan must retain Security PASS before implementation authorization and
record any new review finding caused by this revision. The implementation contract must preserve the
Data Architecture ownership, revision, lineage, retention/erasure/legal-hold, immutability,
coexistence and migration obligations already recorded there. This design review does not claim
Founder acceptance, image approval, implementation authority or operational acceptance.

## Stops

All controlling-plan Section 15 stops apply. In particular: no runnable work without explicit
current-session authorization; no fourth Skill; no external publication, customer provider credential,
paid advertising, Production traffic, new microservice, per-customer image, platform DMA branch,
destructive Docker cleanup, test weakening, self-approval or self-merge.

Also stop on an unapproved image release/version change; spec/product/image/Skill/PAC/prompt coordinate
conflation; build before Founder approval; skipped lifecycle stage; browser/model/adapter-created
operational eligibility; silent trial-to-live promotion; unconfirmed profile fact; unverified goal;
cross-instance trust or memory; unsupported old/new version mapping; or evidence from another digest,
environment, tenant, relationship or instance.

## Plan Author Review

**Result:** PASS - 2026-09-15. Solution Architecture re-read the complete revised contract against the
Founder direction, accepted admission/runtime/customer contracts, objective, scope, lifecycle,
constitutional inheritance, simulations, Definition of Done and Stops. Author review found and
repaired the parallel-lifecycle ambiguity, stale `3.1.0` audience conclusion, missing checkpoint
ownership/evidence and prose-only pre-build gate. The requested Enterprise, Security, Data and Platform
IT review/repair results are recorded in controlling-plan Section 17. Founder acceptance, image/build
approval, implementation authority, deployment and operational acceptance remain separate decisions.

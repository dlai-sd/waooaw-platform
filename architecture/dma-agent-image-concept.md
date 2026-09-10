# DMA Agent Image And Customer Instance Concept

**Office:** Solution Architect (INST-005)
**Date:** 2026-09-10
**Status:** OWNER-REVIEWED CONCEPT - SECURITY PASS; FOUNDER ACCEPTANCE PENDING
**Work Contract:** WC-089
**Reference architecture:** six WAOOAW platform application images plus admitted agent images
**Constitutional basis:** C-001, C-023, C-026, C-035, C-049, C-059, C-065, C-071, C-079

## 1. Decision In Plain English

WAOOAW remains a stable governed platform of six application images. Each professional type and
version is packaged as one separately admitted immutable image. The image is reusable executable
behavior; it is not a customer, employment, subscription, trial, or durable agent identity.

The admitted professional image is an Agent Runtime Adapter workload artifact outside the exact-six
platform release tuple. It neither becomes a seventh platform application image nor changes the
membership, promotion, or rollback semantics of that tuple.

Each customer trial or hire creates a separate platform-owned Employment Relationship and immutable
`agentInstanceId`. That instance binds the customer, tenant, contract, goals, selected Skill versions,
configuration, Decision Space, trial or live mode, evidence, usage, and lifecycle. Many customer
instances may safely use replicas of the same admitted image digest, but no state may cross between
instances.

```text
SIX GOVERNED PLATFORM IMAGES
  + one admitted DMA type/version image and digest
      + customer A trial instance (relationship A, agent instance A)
      + customer B hired instance (relationship B, agent instance B)
      + customer C hired instance (relationship C, agent instance C)
```

This is a type-image / customer-instance model, not one container per customer and not one image that
contains many professional types.

## 2. Why DMA Is The Reference Agent

Digital Marketing is broad enough to expose the platform's hardest reusable boundaries: progressive
customer configuration, public research, long-running work, AI and tool use, approval gates, evidence,
cost attribution, provider credentials, external side effects, cancellation, Emergency Stop, and
frequent Skill evolution. If WAOOAW hosts a bounded DMA journey cleanly, less demanding professional
types should reuse the same package and runtime contracts with smaller domain payloads.

DMA breadth is also the principal delivery risk. WC-089 therefore proves only one coherent outcome:

```text
Skill 0 CUSTOMER_PROFILING
  -> Skill 1 MARKET_RESEARCH
  -> Skill 2 CONTENT_STRATEGY
```

The customer confirms a business profile, receives an evidence-cited maturity assessment, and
approves a bounded content strategy/calendar. Release 1 does not publish content, connect social
accounts, spend money, manage advertisements, or carry Production traffic.

## 3. Fixed Architectural Boundaries

| Boundary | Owner | Owns | Must not own |
|---|---|---|---|
| Employment, trial, hire and customer projection | Business Platform | Relationship, `agentInstanceId`, contract, mode, goals, Skill decisions and customer-visible state | Domain execution or adapter process state |
| Constitutional authority and evidence | Constitutional Engine | Decision, Evidence First, Stop evidence and policy evaluation | DMA work execution |
| Work orchestration | Professional Runtime | Durable invocation, adapter resolution, deadlines, replay, cancellation, Stop and result validation | DMA-specific branches or customer truth |
| AI and governed tools | AI Runtime and CTG | Model/provider routing and authorized tool dispatch | Employment lifecycle or agent identity |
| Provider credentials | oauth-vault | Scoped credential custody and retrieval evidence | Customer workflow or DMA domain decisions |
| Usage and economics | WBE | Reservation, metering, attribution and reconciliation facts | Professional execution or customer authority |
| DMA domain behavior | Admitted DMA image | Skill 0/1/2 logic and admitted domain input/output interpretation | Admission, identity, billing truth, evidence acceptance or platform lifecycle |

No seventh shared platform service is introduced. DMA is an admitted workload behind Professional
Runtime's private Agent Runtime Adapter port established by WC-080 and ADR-049. Its isolated
deployment is resolved by the exact `professionalTypeId + professionalVersion + artifactDigest`
tuple; it is not a new platform service or a customer-owned deployment.

Business Platform owns the durable customer records and revisions for confirmed profile, reviewed
research, approved strategy, work projection and customer decisions. The DMA image may return typed
observations, inferences, citations, partial reports and draft strategies, but these remain proposed
invocation results until BP records the applicable confirmation, review or approval. PR owns durable
invocation and result lineage; WBE owns reservation and observed-usage facts; CE owns constitutional
evidence. Evidence stores references and digests rather than duplicate customer payloads or proof
content.

## 4. Image, Replica And Instance Semantics

| Concept | Cardinality | Identity | State rule |
|---|---|---|---|
| Professional type | One logical DMA definition | `professionalTypeId` | Version-independent catalogue identity |
| Professional version | One immutable admitted release | type + SemVer + admission digest | Never changed in place |
| Image | One exact OCI artifact in each active admission snapshot | immutable OCI digest, verified signature and provenance attestation | Build identity, source commit, SBOM, conformance evidence, admission and the runtime-reported digest must form one verifiable chain; tags are never authority |
| Adapter deployment | One isolated deployment per admitted type + version + digest tuple | activation-registry binding + distinct workload identity | Outside the exact-six platform release tuple; never shared across artifacts |
| Replica | Zero or more runtime copies within one adapter deployment | workload identity + deployment identity | Ephemeral and interchangeable; never a customer identity |
| Agent instance | One per customer Employment Relationship | immutable `agentInstanceId` | Customer-specific durable boundary |
| Invocation | One logical work attempt | `invocationId` + idempotency identity | Replayable; never duplicated on ambiguity |

An adapter replica receives no durable customer store and no reusable customer or provider credential.
Every request is platform-constructed and binds tenant, relationship, agent instance, professional and
Skill versions, admitted and running image digest, contract, Decision Space, configuration, goal,
trial or live mode, evidence context, deadline, invocation, single-use delegation identity, payload
digest and idempotency identity. A retry uses fresh short-lived delegation and can only reconcile the
same prior outcome; it cannot repeat semantic work or cross an instance or mode boundary.

The adapter audience follows accepted ADR-049 exactly. The existing versioned adapter IDs remain the
distinct deployment identifiers, so the canonical audiences are
`urn:waooaw:service:agent-runtime-adapter:digital-marketing-local-service:3.1.0` and
`urn:waooaw:service:agent-runtime-adapter:trading-fo-crypto:1.8.0`. The workload registry's shorter
`urn:waooaw:adapter:*` namespace is conformance drift to repair synchronously in implementation
configuration and tests. No alias or fallback is permitted. Professional version and OCI artifact
digest remain independently verified admission and activation bindings; audience replaces neither.

## 5. Release 1 Skills

| Skill | Outcome | Why now | Explicit boundary |
|---|---|---|---|
| Skill 0 - Customer Profiling | Customer-confirmed minimum business profile | Proves conversational configuration, correction, private data and authoritative confirmation | No inferred field becomes fact without confirmation |
| Skill 1 - Market Research and Maturity Scoring | Source-cited maturity report and needs heat map | Proves degradable tools, parallel/long work, evidence, partial results and honest limitations | Public information only; no authenticated provider data |
| Skill 2 - Content Strategy and Calendar | Customer-approved campaign brief and 30-day calendar | Produces useful work and proves approval gating without external publication | No content publishing, scheduling or provider write |

Skill IDs and versions must be canonical platform catalogue coordinates. The existing fixture names
`LOCAL_CAMPAIGN_MANAGEMENT` and `LOCAL_CONTENT_PLANNING` are not accepted substitutes unless the
catalogue explicitly maps them through a versioned compatibility record.

## 6. Required Platform Closures

| Area | Current position | WC-089 closure |
|---|---|---|
| Adapter lifecycle | WC-080 contract and reference implementation exist | Use unchanged common lifecycle; no DMA-only runtime operation |
| DMA behavior | Current adapter returns a generic draft fixture | Implement typed Skill 0/1/2 behavior and deterministic domain failures |
| Instance binding | WC-087 owns immutable `agentInstanceId`; adapter envelope omits it | Add platform-constructed instance binding and mismatch denial |
| Image trust | Descriptor has digest fields; fixture values are placeholders | Verify signature and provenance attestation against the trusted issuer and bind source commit, build identity, SBOM, conformance evidence, admission, resolved deployment and runtime-reported OCI digest; any mismatch or unverifiable link fails closed before readiness or execution |
| Skill contracts | Detailed prose exists in the DMA specification | Publish bounded machine-readable input/output/configuration/result contracts for only Skills 0/1/2 |
| Work journey | Runtime and workspace foundations exist separately | Join assignment, progress, approval, result, evidence and review through canonical platform ownership |
| Billing | WBE exists; adapter result model can carry usage facts | Reserve before costly dispatch and attribute observed usage to tenant, relationship, instance, Skill and invocation, including zero-priced trial usage |
| Secrets and tools | oauth-vault and CTG exist | Release 1 uses no customer provider credential and no direct Internet access from DMA; customer secrets cannot enter platform/provider custody, provider secrets remain vault-held and workload-scoped, and tools remain purpose-bound governed platform routes |
| Stop | Adapter operation exists | Prove actual slow Skill work halts and cannot publish a late result or resume without fresh authority |
| Readiness | Process and generic readiness routes exist | Readiness reports exact admitted Skill/schema readiness without claiming customer, provider, CE or billing readiness |
| Isolation | Read-only and capability-dropped Compose fixture exists | Inherit WC-080's accepted resource, queue, request-size and hardening limits; prove tenant/instance and trial/live separation, default-deny ingress/egress, denied metadata/undeclared routes, privacy-safe telemetry and failure containment |
| Upgrade/rollback | WC-079 admission and WC-087/088 relationship/Skill version rules exist | Keep supported admitted tuples available; new artifacts follow admission compatibility rules; BP never silently rebinds a relationship, instance or accepted Skill version |

All durable customer and lineage records are scoped by authoritative
`tenantId + relationshipId + agentInstanceId` binding and carry their own immutable record identity
and revision/version. Profile,
research and strategy records bind exact upstream revisions; work, invocation, result, evidence and
usage references remain traceable without making one subsystem's payload another subsystem's truth.
Idempotent retries reconcile the same logical command or invocation, while stale or conflicting
revisions fail rather than overwrite. Customer payloads follow the owning BP retention and erasure
policy; legal hold suspends eligible destruction without converting payload into constitutional
evidence. Immutable audit, event, terminal-result and usage facts retain only the minimum lawful
attribution and tombstone/digest references when customer payload is erased.

## 7. Success Test

The concept is proven when two customers can trial the same DMA image version concurrently, complete
Skills 0/1/2 with distinct profiles and outputs, stop one instance without affecting the other, replay
requests without duplicate work or usage, and observe evidence and usage attributed to the correct
instance. The platform must then validate a non-executable additive future-Skill contract fixture
without adding a new platform service, changing shared runtime lifecycle semantics, expanding the
exact-six release tuple, or redeploying an unrelated platform image.

## 8. Non-Goals

- Production activation, customer traffic, DNS, provider activation or expenditure.
- Skills other than 0, 1 and 2.
- GBP, Instagram, WhatsApp, Meta, Google Ads or other authenticated provider writes.
- Paid advertising, wallet funding, checkout, refunds or subscription redesign.
- One container or image per customer instance.
- Shared multi-professional process hosting or remote third-party agent hosting.
- DMA-specific branches in Professional Runtime, Constitutional Engine, WBE or identity services.
- New microservices, new business capabilities or changes to the six-image reference architecture.

## 9. Consequences

This approach deliberately pays the cost of image identity, instance binding, metering, Stop,
isolation and compatibility in the first DMA slice. That cost is justified only if those controls are
generic and become the repeatable admission path for later DMA skills and other professionals.

The first slice is not a lightweight mock. It is a small real product outcome running through the
full governed path. Conversely, it is not permission to implement the rest of DMA. Any requirement
that cannot be traced to Skills 0/1/2 or a reusable hosting prerequisite returns to architecture.

# Professional Operating Envelope Work Component

**Document type:** Solution Architecture component contract and reusable new-agent template
**Office:** Solution Architect (INST-005)
**Status:** PROPOSED - FOUNDER REQUESTED; CONTRIBUTIONS RECORDED; FOUNDER APPROVAL REQUIRED
**Proving case:** Digital Marketing Professional Release 1 (`DIGITAL_MARKETING_LOCAL_SERVICE`, `1.0.0`)
**Scope:** Customer Profiling, Market Research and Content Strategy only
**Constitutional basis:** C-001, C-002, C-023, C-035-C-038, C-041, C-043, C-048,
C-049, C-051, C-059, C-063, C-070, C-088-C-091, C-094 and C-099
**Architecture basis:** ADR-020, ADR-029, ADR-034, ADR-035, ADR-042, ADR-049, WC-079,
WC-080, WC-087, WC-088, WC-089 and WC-095

## 1. Goal

Establish the **Professional Operating Envelope** as the mandatory platform-agent boundary for every
new WAOOAW Digital Professional. WAOOAW supplies governed employment, authority, resources,
channels, evidence, usage, status and Stop capabilities; the admitted agent image owns the
profession and exercises judgment inside that environment.

## 2. Objectives

1. Make package economics, resource enforcement, governance, channels and observability reusable.
2. Draw a testable ownership boundary between WAOOAW and agent images.
3. Make the boundary a binary new-agent authoring and activation gate.
4. Identify common component, interface, data, prompt, security and platform work.
5. Close DMA Release 1 gaps for Profiling, Research and Strategy only.
6. Bind customer transparency to the Customer Portal UI Coherence component.

## 3. Constitutional Pass

| Obligation | Required boundary |
|---|---|
| C-001 | Emergency Stop is platform-owned, immediate and allowance-exempt. |
| C-002/C-023 | Authority, reservation and evidence precede consequential success; agent output is not platform acceptance. |
| C-035 | Every profession uses the same BP, CE, PR, AIR, CTG, WBE and channel code without type branches. |
| C-036/C-037 | Skills, KPIs and professional reasoning remain domain declarations bound to platform governance. |
| C-038/C-090 | Pause, termination, pro-rata treatment and grandfather pricing remain platform-owned. |
| C-041/C-043 | External tools are default-denied; package allowance never implies spend authority. |
| C-048/C-049 | Agents may optimize resources but must disclose inability, depletion and quality constraints. |
| C-051 | Customer and agent receive current allowance, use, forecast and exhaustion truth. |
| C-059/C-063 | End-to-end attribution is resolvable without leaking protected customer or prompt data. |
| C-070 | Every agent inherits Evidence First, governed tools, honest limitation, quality evidence and Stop. |
| C-088-C-091 | Authorized ABP and bundles reference active Thread Catalog entries, pass margin floor and preserve price. |
| C-094/C-099 | Every package mode inherits governance; consequence calibration remains explicit. |

**Determination:** constitutionally aligned as a proposed component, subject to the mandatory
conditions in this document. No new claim or immutable constitutional amendment is created.

## 4. Ownership Boundary

### 4.1 WAOOAW Owns

- admission, offerability, identity, consent, employment, contract and immutable agent instance;
- trial, subscription, payment, renewal, pause, resume and termination truth;
- package, ABP, Thread Catalog, price floor, wallet, reservation, settlement and reconciliation;
- Decision Space custody, CE decisions, evidence commitment and Emergency Stop;
- provider dispatch, credentials, egress, Web/WhatsApp transport and delivery evidence;
- customer-safe lifecycle, work, commercial, usage and limitation projections; and
- generic isolation, retry, idempotency, observability and degradation mechanics.

### 4.2 Agent Image Owns

- admitted vocabulary, Skills, KPIs, domain schemas and induction questions;
- professional diagnosis, strategy and choice among admitted Skills;
- recommendations for allocating available package resources to customer Goals;
- governed domain prompts, quality criteria, limitations and explanations; and
- typed proposed results returned through the generic adapter.

### 4.3 Agent Image Never Owns

Customer or contract authority, package price or balance, settlement, provider credentials,
unrestricted egress, approval, evidence acceptance, Stop state, lifecycle transitions, browser
eligibility, or private implementations of platform governance and billing.

## 5. Requirements

### 5.1 Canonical Envelope

Before work, BP resolves one immutable, expiring snapshot binding tenant, relationship, actor,
`agentInstanceId`, contract/mode, exact professional/admission/image/runtime coordinates, Skill,
prompt, goal, context, Decision Space, consequence, approval, Stop, ABP, bundle, billing period,
resource-state references, work/invocation identities, channels, data class and degradation policy.
PR rejects missing, stale, superseded, incompatible, stopped or mismatched envelopes before domain
payload parsing. Browser and agent image cannot create or widen one.

### 5.2 Resource Lifecycle

```text
resolve envelope -> map capability to active Thread Catalog entry
-> authorize action -> reserve bounded resource -> dispatch through AIR/CTG
-> record observed use/cost -> settle or release -> commit evidence
-> refresh projection -> signal agent/customer
```

Unknown mapping, inactive ABP/bundle/thread, absent bucket, unavailable WBE, insufficient allowance,
reconciliation halt or stale authority fails closed before provider dispatch. Stop and mandatory
constitutional disclosure remain available when ordinary allowance is empty.

### 5.3 Common Interfaces

| Interface | Owner -> consumer | Contract |
|---|---|---|
| `ResolveProfessionalOperatingEnvelope` | BP -> PR/Portal | Current immutable authority/package references, expiry, blockers and next action. |
| `ResolveCapabilityCost` | WBE -> PR/AIR/CTG | Versioned capability to active Thread Catalog entry and bounded estimate. |
| `ReserveEnvelopeResource` | WBE -> runtime | Atomic reservation bound to tenant, relationship, instance, Skill, work and invocation. |
| `SettleEnvelopeResource` | WBE -> runtime | Idempotent observed-use recording, consume/release and reconciliation lineage. |
| `ValidateEnvelopeAction` | CE/CTG -> runtime | Separate authority, consequence, spend and reservation validation. |
| `PublishEnvelopeSignal` | platform -> PR/channels | Typed, revised and deduplicated facts that never grant authority. |
| `GetEnvelopeProjection` | BP/WBE -> portal/channels | Current package, actual use, allowance, forecast, limits and commands. |
| `ReportProfessionalResult` | adapter -> PR/BP | Typed proposal/result, observations, limitations and evidence references. |

Signals include package active, allowance threshold, exhaustion forecast/exhausted, provider
degraded, subscription renewed/paused, action denied, reassessment required and Emergency Stopped.

### 5.4 Common Technical Work

| Owner/component | Required build or change |
|---|---|
| Agent Authoring/Admission | Gate exact professional/Skill IDs, prompts, ABP, bundles, capabilities and Thread Catalog closure. |
| BP | Compose envelope; bind package at activation; expose blockers and next action. |
| WBE Bundle/Wallet | Seed authorized bundles; provision buckets; enforce canonical reservation/settlement. |
| WBE Meter/Procurement | Consume provider facts; correct period math; reconcile reservation, cost and projection. |
| CE/CTG | Keep authority separate from entitlement; require reservation for cost-generating calls. |
| AIR | Map prompt/capability, reserve before dispatch, capture actual use and settle every terminal path. |
| PR | Verify envelope, propagate coordinates, cancel on Stop and reject agent-owned platform truth. |
| PAC/signals | Carry state revisions and effective time without becoming authority. |
| Web/WhatsApp | Render one server projection and record truthful alert delivery/fallback. |
| Portal UI | Apply Customer Portal UI Coherence to workspace, package transparency and commands. |
| Observability | Correlate contract -> instance -> Skill -> work -> decision -> reservation -> dispatch -> cost -> result. |

No new deployable service is justified.

### 5.5 Data And Database Requirements

Data Architecture must fix ownership, immutability, revision lineage, three-ledger placement,
retention/erasure/legal hold, tenant isolation and RLS for envelope snapshots, professional mapping,
bundle activation, period entitlements, reservations, observed-use settlement, usage/cost attribution,
signals and projections. Runtime Implementation then derives canonical migrations. PostgreSQL tests
must initialize repository schema; handcrafted schemas and SQLite cannot prove compatibility, RLS or grants.

### 5.6 Prompt Requirements

Each new agent declares every inference point with approved prompt ID/version/digest, minimum model
tier, Skill, capability/Thread mapping, reservation basis, package-signal triggers and honest
degradation. Unused resource classes are explicitly `NOT_APPLICABLE`. Shared prompts carry
constitutional/envelope context and output shape; professional diagnosis stays in domain prompts.
Prompts never enforce authority, entitlement, settlement or evidence.

### 5.7 Security Contribution

Use least-privilege workload grants. Treat customer-supplied identities as untrusted. Bind
reservations to caller, audience, tenant, relationship, instance, Skill, work, invocation,
capability, amount, expiry and idempotency. Retries/cancellation cannot double-consume or evade
settlement. Deny direct adapter egress and credentials. Block paid dispatch when WBE or authority is
unavailable while preserving Stop. Keep prompt/customer content out of usage and alert telemetry.

### 5.8 Platform Contribution

Preserve service boundaries and approved technologies. Add only narrow grants, configuration,
readiness dependencies, bounded settlement/alert retry and privacy-safe observability. Qualify exact
Docker images in CI and exact deployed revisions separately; local or aggregate checks do not prove
Production readiness.

## 6. DMA Release 1 Gap Register

Content generation, publishing, provider OAuth, ads and campaign spend are intentionally excluded.

| Priority | Gap | Required closure |
|---|---|---|
| P0 | `DIGITAL_MARKETING_LOCAL_SERVICE` vs `dma_v3` identity drift | One admission-owned canonical mapping; reject unknown aliases. |
| P0 | No active authorized DMA bundle seed; price vocabulary conflicts | Founder authorizes exact Release 1 bundle/version/rations/price; seed once. |
| P0 | Paid activation does not prove bundle bucket provisioning | Bind bundle and atomically seed every entitlement; test returned buckets. |
| P0 | Wallet service conflicts with canonical reservation columns/no-delete rule | Reconcile contract/schema; prove reserve, settle, expiry and replay in PostgreSQL. |
| P0 | AIR dispatch bypasses WBE reservation and actual-use settlement | Add generic WBE lifecycle around success, failure, timeout and cancellation. |
| P0 | CTG validates CE authority but not package entitlement | Require reservation for cost-generating tools without replacing CE. |
| P0 | Skill `costUnits` are unresolved counters unused by runtime | Map versioned capabilities to active Thread Catalog coordinates/estimates. |
| P1 | Meter queries drift from schema and percentage denominator is mutable | Align canonical contracts; use stable period allocation for consumption. |
| P1 | WhatsApp alert notifier raises `NotImplementedError` | Use governed channel interface, delivery evidence, bounded retry and Web fallback. |
| P1 | Commercial projection/commands are process-local placeholders | Derive durable, fresh projection and idempotent commands from WBE truth. |
| P1 | No narrow AIR/CTG/PR -> WBE workload grants | Add reviewed reservation/settlement routes and configuration. |
| P1 | Prompt economics do not reach dispatch/cost ledger | Propagate prompt/tier through envelope, reservation, dispatch and cost facts. |
| P1 | Portal does not prove package/use/forecast/limitations end to end | Integrate common projection through Customer Portal UI Coherence. |
| P1 | SQLite/minimal PostgreSQL tests mask canonical drift | Add canonical-schema activation, bucket, dispatch, alert and projection tests. |
| P2 | Marketplace Growth Engine INR 2,499 conflicts with proposed Starter near INR 4,000 | Keep unavailable until Founder-authorized name/version/price is consistent. |

The existing DMA adapter is correctly narrow: it produces typed profile, cited research and strategy
proposals without publishing or taking customer authority.

## 7. Delivery And Office Pass

| Work package | Owner | Output |
|---|---|---|
| POE-01 | Solution Architect | Versioned envelope, cost, reservation, settlement, signal and projection contracts. |
| POE-02 | Enterprise Architect | No-new-service placement, boundaries and runtime-universality confirmation. |
| POE-03 | Security + Data Architects | Threat/identity, ownership, lineage, ledger, retention and migration requirements. |
| POE-04 | Platform Architect | Grants, topology, observability, resilience and environment qualification. |
| POE-05 | Runtime Implementation | Common BP/WBE/CE/CTG/AIR/PR/PAC/channel work under separate authorization. |
| POE-06 | Runtime Implementation | DMA Skills 0/1/2 mappings, prompts, package binding and exact-image tests. |
| POE-07 | Runtime Implementation | Customer projection through Customer Portal UI Coherence. |

The Founder requested one contribution-and-repair pass from Enterprise, Security, Data and Platform
Architecture. Sections 5.5-5.8 record and incorporate those contributions. Because one continuous
authoring context synthesized them, they are not independent protected approvals. Founder approval,
implementation authorization, deployment and merge remain reserved.

## 8. Definition Of Done

1. Founder accepts the name, boundary and no-new-service placement.
2. Agent Authoring Guide makes the envelope mandatory for every new professional.
3. All eight interfaces have approved versioned inputs, outputs, failures, idempotency and evidence.
4. Data, Security, Enterprise and Platform blockers are repaired and accepted.
5. One canonical DMA identifier resolves admission, BP, WBE, PR and adapter records.
6. One authorized DMA Release 1 bundle is active and consistently presented.
7. Activation/renewal provision exact bundle buckets from canonical data.
8. Paid AIR/CTG calls reserve before dispatch and settle observed use on every terminal path.
9. CE authority and WBE entitlement remain separate mandatory gates.
10. Agent/customer receive truthful threshold, forecast, exhausted, unavailable, paused and Stop state.
11. Portal satisfies Customer Portal UI Coherence for envelope information and actions.
12. DMA Skills 0/1/2 pass exact-image and multi-tenant/instance isolation without later Skills.
13. Canonical PostgreSQL proves schema, RLS, grants, activation, wallet, meter and projection.
14. Trace evidence resolves employment through result/cost without protected content in telemetry.
15. Author review and checks pass; only the Founder approves and merges the PR.

## 9. Explicit Exclusions

No content/image/video generation, publishing, social writes, ads, new DMA Skills, new service,
professional-type runtime branch, invented price/ration, or claim that allowance grants spend/action
authority. This document authorizes no code, migration, build, cloud mutation or deployment.

## 10. Change Control

After Founder acceptance, new agents may specialize domain Skills, prompts, schemas and package
declarations but may not fork or weaken the platform envelope. Exceptions require architecture and
constitutional review.
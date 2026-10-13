# WC-121 Platform Architect Disposition

## Record

| Field | Value |
|---|---|
| Institution | INST-009 — Platform Architect, Office 09 |
| Review | Founder-requested single-pass review-and-repair |
| Scope | WC-121 solution contract, implementation Work Contract, requirement-evidence ledger, and directly applicable accepted deployment/readiness contracts |
| Date | 2026-10-13 |
| Enterprise requirements | Reviewed and intentionally unchanged |
| Data and Security dispositions | Reviewed and intentionally unchanged |
| Authority | Platform architecture/specification only; no implementation, provider, cloud, deployment, traffic, activation, approval, commit, or merge authority |
| Disposition | **BLOCKED on external numeric, recovery, provider, and protected-authority decisions** |

## Platform Decision Space

This review covers cloud and service topology, runtime configuration, secret references, provider
boundary, health/readiness, observability, SLO integration, capacity/backpressure, immutable
promotion, migration/deployment/rollback sequencing, disaster-recovery integration, feature
activation, and platform evidence. It does not select Product targets, provider feasibility,
retention policy, live identities, cloud authority, traffic authority, activation authority, or
Founder decisions and does not inspect or authorize implementation.

## Findings and exact repairs

| Finding | Platform risk | Exact repair |
|---|---|---|
| CEW same-image parity did not bind the capability to existing release workloads. | An implementer could add an eighth service, ingress, queue, store, or provider bridge and break exact-seven promotion. | CSA-CEW-001 CEW-SD-014 and 13.5 place CEW only in existing Web, BP, Conversation/adapter, owner, and evidence workloads and prohibit topology expansion. |
| Capability state, environment configuration, and authority gates were not a closed-world machine contract. | Environment-name branching, stale authority, configuration drift, or deployment health could silently activate behavior. | Sections 13.6 and 13.11 define digest-bound manifest/catalog/capability records, fail-closed states, non-transitive gates, and an explicit post-deployment activation record. |
| Protected sender/recipient/provider and platform secrets lacked CEW-specific runtime-reference rules. | Values could enter images, Terraform/state, workflows, telemetry, or evidence, or one credential could cross purposes. | Section 13.6 binds purpose-separated secret references to the accepted catalog and per-workload managed identity, prohibits value-bearing artifacts, and limits readiness to metadata proof. |
| Provider and internal service/network boundaries were implicit. | Provider delivery could become BP authority, callbacks could bypass verification, or CEW could expose new public/network paths. | Section 13.5 fixes public/private edges, verified channel-neutral callback admission, environment isolation, and provider-versus-owner truth. |
| Liveness, startup, traffic readiness, and optional feature readiness were conflated. | Probes could cause effects, route traffic before migration/Stop/evidence readiness, or make unrelated reads unavailable. | Section 13.7 separates all probe classes, prohibits external/consequential probe effects, and makes mandatory dependency, digest, migration, Stop, and evidence checks traffic gates. |
| Existing latency metrics did not form a complete SLO and alert contract. | Customer, provider, evidence, identity, saturation, drift, or Stop failure could be aggregated or unowned. | Section 13.8 defines separate SLIs, required alert classes, redacted tuple-bound telemetry, owners/runbooks/evidence, and blocks activation until numeric targets and routing are accepted and tested. |
| Capacity and overload semantics were absent. | Unbounded queues/retries or overload could drop accepted work, duplicate owner effects, delay Stop, or fabricate success. | Section 13.7 requires a frozen workload envelope, soft/hard limits, bounded queues/concurrency, typed rejection, durable idempotent retry, poison quarantine, saturation evidence, and bounded recovery. |
| Exact-image evidence did not fully define immutable release promotion. | A qualified image could be rebuilt, retagged, reconfigured without binding, or promoted with incompatible schema. | Sections 13.9-13.10 bind CEW to the signed exact-seven tuple plus configuration/catalog/dependency/schema/evidence digests and prohibit rebuild, retag, or mutation. |
| Data migration stages were not tied to traffic and revision sequencing. | Partial backfill or incompatibility could receive traffic, and rollback could require destructive schema action. | Section 13.9 requires preflight, expand, backfill, verify, zero-traffic revision qualification, independent verification, authorized switch, and separately authorized later contraction. |
| Rollback and DR semantics were data/security-correct but not integrated with deployment mechanics. | Rollback could rebuild, revive authority, erase effects, or treat compute health as recovery. | Section 13.10 defines previous-qualified-tuple traffic rollback, reconciliation/non-resurrection evidence, UAT isolated PITR/restore qualification, and separately authorized Production recovery. |
| Live Demo deployment did not require a distinct inactive-to-active transition and complete platform evidence. | Deployment or credential presence could imply traffic/activation, and provider delivery could be confused with owner success. | Sections 13.11-13.12 and WC-121 Components 08-09 require `READY_INACTIVE`, separate deployment/traffic/activation records, bounded audience/window/spend, provider/owner truth separation, alert/capacity/rollback evidence, and deactivation proof. |
| Platform obligations were not independently tracked in the evidence ledger. | Broad parity or provider requirements could pass without topology, readiness, capacity, promotion, or DR proof. | WC-121 adds `WC121-R021`; the ledger adds a direct blocked platform qualification with specific Docker-owned oracle plans. |

## External dependencies and mandatory stops

1. **Service objectives and load:** Product/Platform/Founder acceptance is required for numeric
   availability target, error budget, evaluation and paging windows, queue-age limits,
   qualification load, workload forecast, and bounded recovery objective. Existing Section 12.2
   latency budgets remain unchanged.
2. **Recovery decisions:** Numeric RPO, RTO, backup retention, regional-copy policy, recovery
   environment, incident owner, and recovery-execution authority remain unresolved. Their absence
   blocks deployment acceptance and live activation.
3. **Provider feasibility:** Same sender/recipient use remains blocked under CSA-CEW-001 13.4 until
   binding provider confirmation, a separately authorized bounded probe, or a distinct
   Founder-authorized recipient exists.
4. **Live operating bounds:** Incident owner, spend ceiling, test window, bounded recipient set,
   alert routing, provider account authority, and credential-use authority require explicit
   acceptance.
5. **Package acceptance and implementation:** Founder acceptance of candidate `1.0.0-candidate.5`,
   Docker-only validation, pinned digests, impact analysis, and explicit current-session
   implementation authorization remain open.
6. **Protected actions:** Provider mutation, cloud mutation, deployment, external traffic,
   activation, PR approval, and merge remain independent and blocked unless each is separately
   authorized. No gate implies another.

## Evidence required before Platform PASS

- Existing-workload map and scans proving no deployable, ingress, queue, store, or release-member
  expansion.
- Schema/digest validation for environment manifest, secret catalog, capability records, signed
  exact-seven release tuple, dependencies, and migration compatibility.
- Liveness/startup/traffic/feature-readiness failure matrix with no external or consequential probe
  effects.
- Accepted capacity envelope with load, saturation, bounded queue/retry/quarantine, Stop precedence,
  and post-overload recovery evidence.
- Accepted SLO/error-budget inputs and tested alert ownership, routing, runbooks, and redacted
  release/configuration correlation.
- Expand/backfill/verify/cutover qualification, zero-traffic failure behavior, immutable promotion,
  and previous-qualified-tuple rollback with reconciliation.
- UAT encrypted PITR to an isolated target proving tenant/RLS, evidence linkage, current-key access,
  non-resurrection, accepted RPO/RTO, and previous-image readability.
- Separate provider, credential, cloud, deployment, bounded-traffic, activation, approval, and merge
  attestations where applicable.
- For live Demo only: Section 13.4 feasibility closure, exact Component 08 digest, `READY_INACTIVE`
  start, bounded live scenario, provider-versus-owner/evidence separation, rollback, and
  deactivation-at-expiry proof without protected values.

## Disposition

**BLOCKED.** All Platform-owned specification gaps identified in this pass are repaired. Enterprise
requirements and the Data and Security dispositions are unchanged. WC-121 remains blocked from
implementation acceptance and live Demo activation until the external numeric SLO/capacity,
recovery, provider-feasibility, operating-bound, package-acceptance, and separately protected
authority decisions above are accepted and evidenced. This disposition authorizes no implementation
or external action.

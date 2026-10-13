# WC-121 Security Architect Disposition

## Record

| Field | Value |
|---|---|
| Institution | INST-007 — Security Architect, Office 07 |
| Review | Founder-requested single bounded write-enabled specification review |
| Scope | WC-121 solution contract, additive API, implementation Work Contract, and requirement-evidence ledger |
| Date | 2026-10-13 |
| Enterprise requirements | Reviewed and intentionally unchanged |
| Data disposition | Reviewed and intentionally unchanged |
| Authority | Security architecture/specification only; no implementation, provider, cloud, deployment, traffic, activation, approval, commit, or merge authority |
| Disposition | **BLOCKED on external security dependencies and all existing acceptance/authority gates** |

## Security Decision Space

This review covers threat boundaries, identity, authentication, assurance, authorization,
tenant/object isolation, session and CSRF controls, focus and safe-return integrity, replay and
abuse resistance, WhatsApp ingress/media security, workload identity, secrets, encryption,
redaction, Stop precedence, operation separation, revocation, and rollback. It does not select
product, Legal, provider, Platform, recovery, retention, or Founder policy and does not inspect or
authorize implementation.

## Findings and exact repairs

| Finding | Security risk | Exact repair |
|---|---|---|
| The candidate needed one explicit CEW trust-boundary and threat model rather than relying on inherited controls by implication. | Browser, provider, workload, owner, reconciler, export, or telemetry edges could become unreviewed trust shortcuts. | CSA-CEW-001 Sections 11.1-11.2 enumerate every CEW trust boundary, required threat case, independent customer/workload proof, current membership/role/object authorization, privacy-safe denial, and forced tenant isolation. |
| Authentication success, identifier possession, or a JWT tenant/role claim could be misread as current relationship authority. | IDOR, confused-deputy, cross-tenant, stale-role, and operator/service privilege crossover. | CSA-CEW-001 11.2 requires raw-proof validation at every receiver, actor-keyed current membership, relationship/participant/object/purpose/version authorization on every path, authorization-before-disclosure, and no service/operator customer authority. WC-121 9.1-9.2 makes the edge matrix and adversarial proofs mandatory. |
| Authenticated wire responses did not normatively preserve anti-enumeration and cache controls. | `403`/conflict/expiry/version differences or browser/shared caching could disclose protected resource existence and state. | Candidate `1.0.0-candidate.4` requires `Cache-Control: no-store` on every authenticated success and reusable error, normalizes inaccessible/absent resources to one `404` family, and permits assurance, entitlement, conflict, expiry, validation, and version detail only after resource authorization. CSA-CEW-001 11.2 and WC-121 Section 7 bind the same rule. |
| Browser continuity required explicit defenses against ambient authority and unsafe redirects. | CSRF, login CSRF, fixation, stale assurance, account-switch leakage, open redirect, and automatic replay of a pending mutation. | CSA-CEW-001 11.3 fixes host-only secure server sessions, rotation/revocation, session-bound CSRF plus Origin/Fetch-Metadata validation, state/nonce/PKCE, and opaque single-use 15-minute safe-return references restricted to server-allowlisted relative destinations. Step-up reauthorizes but never auto-executes. |
| Focus references needed a complete cryptographic and lifecycle contract. | Token tamper, theft, URL/telemetry leakage, cross-context replay, stale authority, and key-rotation resurrection. | CSA-CEW-001 10.8 and 11.4 require type/audience separation, canonical authenticated integrity, at least 128 bits of unpredictability, body-only transport, maximum 15-minute non-extendable expiry, current binding/authority/Stop recheck, atomic single use for continuation/command-bearing focus, fingerprint-only observability, bounded key overlap, and invalidation on logout, switch, unlink, revocation, Stop, termination, deletion, correction, or supersession. |
| Admission replay protection required abuse behavior beyond ordinary idempotency. | High-cardinality key exhaustion, divergent retries, races, limiter/cache/process failure, and replay-record eviction could mint duplicates. | CSA-CEW-001 10.6 and 11.5 bind actor/tenant/purpose/key plus canonical digest before effects, durable original outcomes, conflict with zero effects, concurrency arbitration, owner uniqueness, bounded reservation/polling quotas, security signals, and replay protection that survives limiter, cache, restart, rollback, and clock failure. |
| WhatsApp ingress freshness language could have weakened the accepted Meta five-minute floor when the wire contract was incomplete. | Valid-signature stale replay, parser differentials, duplicate dispatch, sender substitution, resource exhaustion, and unsafe media use. | CSA-CEW-001 11.6 now requires bounded raw bytes before parsing, constant-time signature verification over exact bytes, the accepted Meta freshness proof within five minutes, pre-dispatch event/message reservation, Phone Identity plus current relationship authority, per-source/phone/tenant/session/operation abuse controls, and default-deny media quarantine. Missing accepted freshness proof blocks activation; local receipt time is not a substitute. WC-121 9.2 tests stale/future proof without a “where supported” exception. |
| Internal encrypted transport alone was insufficient as service authority. | Workload impersonation, lateral movement, callback/reconciler/export privilege crossover, and customer-context substitution. | CSA-CEW-001 11.7 requires mutually authenticated allowlisted workload identity, independent audience/caller/operation/purpose and delegated-context checks, original customer-proof validation where required, and distinct least-privilege identities for online, callback, reconciler, migration, restore, and export work. |
| Secret, encryption, and observability controls needed purpose and failure semantics. | Credential reuse, fallback to revoked keys, plaintext backup/export/quarantine, protected-value exfiltration, and attacker payloads becoming evidence. | CSA-CEW-001 11.7-11.8 requires authorized secret references, purpose-separated keys, versioned rotation/revocation with bounded overlap, encryption for every hop and protected store, fail-closed key dependency, deny-by-default telemetry, pre-serialization and collector redaction, bounded cardinality, seeded canaries, and opaque decision evidence only. |
| Stop and destructive/session actions required race and effect separation, not presentation labels alone. | Ordinary queues/rate limits could suppress cessation; logout, end-session, unlink, terminate, delete, Stop, or release could cross-trigger. | CSA-CEW-001 11.9 makes Stop win before every non-Stop governed commit and across admission, focus, handoff, session end, commands, reconciliation, and provider delivery. Each destructive/session operation has a distinct operation ID, idempotency purpose, assurance, owner, evidence type, effect, and recovery; ordinary flow cannot release Stop. |
| Rollback and restore needed explicit non-resurrection rules. | Revoked sessions, roles, links, tokens, workload credentials, secrets, ingress, or provider authority could return after rollback. | CSA-CEW-001 11.10 and WC-121 Sections 9 and 14 prohibit security-state resurrection, require revocation propagation through caches/queues/projections/background work, preserve Stop/read/reconciliation/data-right paths during disablement, and stop implementation when an accepted control or non-resurrection proof is absent. `WC121-R020` independently tracks the complete security qualification. |

## External dependencies and mandatory stops

1. **Exact accepted contracts:** Identity assurance, Stop/release, Meta signature/freshness,
   Phone Identity, workload identity, key custody/rotation, encryption, telemetry retention,
   media safety/consent, rate capacity, and recovery controls must remain accepted and compatible
   for the exact implementation candidate. Any missing or conflicting contract stops its component.
2. **WhatsApp freshness:** Callback activation is blocked unless the accepted inbound wire contract
   supplies the accepted Meta freshness proof within the five-minute window, or an authorized
   amendment defines an equivalent replay-resistant proof. This review does not invent a provider
   field or waive the floor.
3. **Policy owners:** Materiality, role entitlement, stronger factor, Stop release composition,
   retention, legal hold, export recipient/redaction, commercial treatment, and provider terms
   remain with their authorized owners. Unknown policy fails closed.
4. **Recovery:** Numeric RPO/RTO, backup retention, regional-copy policy, recovery environment, and
   restore authority remain blocked on the Platform/Founder decisions recorded by the Data
   disposition.
5. **Candidate acceptance:** Founder acceptance of exact candidate `1.0.0-candidate.4` and the
   requirement-ledger digests remains open. INST-007 does not accept it on the Founder’s behalf.
6. **Implementation and protected actions:** No implementation, generated artifact, provider/cloud
   mutation, deployment, external traffic, activation, PR approval, commit, or merge is authorized.

## Required security evidence before PASS

- Complete WC-121 9.1 edge/control matrix with no absent owner, policy, enforcement, or oracle.
- Deterministic WC-121 9.2 adversarial suite on the exact contract, image, and configuration.
- Cross-tenant/object/session/focus denial equivalence, forced isolation, and confused-deputy proof.
- Session, CSRF, login-CSRF, switch/logout, safe-return, focus, and admission replay/abuse proof.
- Exact-raw-byte Meta signature and five-minute freshness, deduplication, acknowledgement race,
  payload/decompression/media quarantine, and unknown-sender proof.
- Workload audience/operation/purpose, secret/key rotation and revocation, encrypted
  store/backup/export, and seeded application/collector redaction proof.
- Stop race/outage/restart and independent release proof for every governed path.
- Distinct logout, revoke, end-session, switch, unlink, terminate, delete, Stop, and release effects.
- Rollback/restore proof that no revoked authority, credential, binding, ingress, traffic, effect,
  or protected payload is resurrected.

## Disposition

**BLOCKED.** The Security-owned specification gaps found in this review are repaired in candidate
`1.0.0-candidate.4`, and the Enterprise requirements and Data Architect disposition are unchanged.
Security PASS remains blocked until the exact external contracts and owner policies are accepted,
the callback freshness dependency is closed, the direct security evidence above passes, and every
existing acceptance and authority gate is satisfied. No Legal or Founder decision is inferred.

# R-146 — Conversation Engine And WhatsApp Security Architecture Review

**Reviewer:** Security Architect (INST-007)  
**Review type:** Founder-requested, single-pass institutional architecture review  
**Date:** 2026-10-12  
**Package commit:** `f5bb9e49`  
**Verdict:** **CHANGES REQUIRED**

## 1. Scope

This review evaluates whether the proposed Conversation Engine and WhatsApp enterprise architecture
provides sufficient security direction for the Chief Solution Architect to proceed without inventing
security controls. The review covers identity and assurance, webhook challenge and raw-body HMAC,
replay and deduplication, environment isolation, secrets and workload authority, media safety,
templates and service-window enforcement, prompt and context injection, tenant isolation, Emergency
Stop, privacy-safe observability, failure behavior, and rollback.

The review does not authorize implementation, provider activation, credentials, deployment, traffic,
ADR acceptance, or merge. It does not assess source code.

## 2. Evidence Read

- Compact Security Architect office card: `constitution/INSTITUTION-REGISTRY.md`, INST-007 only.
- Committed diff `f5bb9e49`, comprising ADR index, capability/container/context/domain references,
  ADR-052, ADR-053, and the controlling enterprise architecture package.
- `architecture/reference/components/conversation-engine-whatsapp-enterprise-architecture.md`.
- `adr/ADR-052-channel-neutral-conversation-context-policy.md`.
- `adr/ADR-053-whatsapp-environment-isolation-transport.md`.
- Directly cited security decisions used to test preservation of existing controls:
  ADR-003 (current authoritative tenant binding and RLS), ADR-014 (secret management), ADR-023
  (WhatsApp phone identity), ADR-031 (fail-safe halt and Stop during CE unavailability), and ADR-046
  (workload identity and service authentication).

## 3. Findings

### BLOCKING

No BLOCKING finding is raised. The package keeps provider, persistence, media, DNS, and Production
activation stopped in Sections 2.2 and 24, so the identified omissions do not create an immediate
authorized exposure.

### HIGH

#### HIGH-01 — Phone identity, tenant resolution, and assurance are not deterministic enough

**Package references:** Sections 7, 8.3, 12.2, 12.6, 14.2, 15, and 17 (`CE-FIT-02`,
`CE-FIT-08`, `CE-FIT-12`).

The package correctly states that phone possession is low assurance, changing channel cannot upgrade
assurance, a phone cannot attach an existing relationship, tenant identity is server-derived, and
critical operations require stronger assurance. It does not define the fail-closed resolution result
for zero, one, or multiple active bindings across tenant, relationship, participant, recipient
phone-number ID, provider app, and environment. It also does not map protected operation families to
assurance tiers, assurance freshness, step-up expiry, number reassignment, revocation, or ambiguous
binding behavior. A Solution Architect would have to invent both tenant-selection and action-tier
policy, risking cross-tenant attachment or assurance downgrade.

**Required remediation:**

1. Add a deterministic resolution contract keyed by the signed provider event, environment, app/WABA
   authority, recipient phone-number ID, and protected participant proof.
2. Require zero, inactive, revoked, reassigned, duplicate, or ambiguous bindings to deny with one
   normalized non-enumerating response and zero relationship mutation.
3. Prohibit automatic attachment or tenant creation from a phone reference alone.
4. Add an operation-family-to-tier matrix, with required freshness, confirmation binding, step-up
   expiry, and portal-only actions; preserve Tier 4 for Stop release.
5. Add adversarial tests for cross-tenant phone reuse, number reassignment, ambiguous relationships,
   stale step-up, and recipient-number/environment mismatch.

#### HIGH-02 — Webhook acknowledgement and replay controls leave a loss/duplication decision open

**Package references:** Sections 12.1, 12.2, 15 (`Provider Event Dedup`), 16, and 17
(`CE-FIT-09`).

Raw-byte HMAC-before-parse, environment binding, freshness, schema validation, and durable event-ID
deduplication are sound requirements. However, the package does not define when a valid callback may
receive success, the atomic relationship between dedup claim and durable acceptance, the dedup key
scope, or how freshness interacts with legitimate delayed Meta retries. It also leaves dedup TTL
without a minimum tied to the provider retry horizon. Returning success before durable acceptance can
lose messages; returning failure after mutation or expiring dedup too early can duplicate actions.

GET verification also needs an explicit rule that only the expected subscribe mode plus an exact,
environment-bound verify token may cause the challenge to be echoed. POST verification needs explicit
header-algorithm parsing, constant-time digest comparison, and assurance that no middleware
normalization/decompression changes the signed bytes.

**Required remediation:**

1. Define the compound dedup key and an atomic state machine such as
   `CLAIMED -> DURABLY_ACCEPTED -> OUTCOME_RECORDED`, including concurrent first delivery.
2. Permit callback success only after durable acceptance or retrieval of a previously durable
   outcome; otherwise return the provider-approved retryable failure.
3. Define freshness/skew and delayed-retry treatment separately; never discard an authentic,
   previously accepted retry merely because its provider timestamp is old.
4. Set dedup retention no shorter than the documented retry/reconciliation horizon and preserve it
   through callback rollback.
5. Specify exact GET challenge predicates and constant-time raw-body POST verification, body-size
   rejection, and safe response classes without reflecting attacker input.

#### HIGH-03 — Secret custody and workload authority are listed as assets, not an access contract

**Package references:** Sections 7, 13.2–13.5, 14.1–14.2, 21, and 24.

Environment-separated Key Vaults, secrets, provider identities, deployment authority, and dark
Production are appropriate. The package does not state which exact workload identity may read the
verify token, HMAC app secret, outbound access authority, media retrieval authority, or callback
configuration authority; nor does it separate read, rotate, revoke, and deploy privileges. Rotation
overlap, cache lifetime, emergency revocation, compromise response, and audit requirements are also
undefined. ADR-014 storage and ADR-046 workload authentication do not themselves create this
WhatsApp-specific least-privilege matrix.

**Required remediation:**

1. Add an environment-specific workload/secret/operation matrix using exact workload identity and
   audience, with separate provider-adapter runtime and deployment/configuration authorities.
2. Keep verify token, HMAC app secret, outbound token, media authority, and deployment authority
   distinct; prohibit a shared catch-all credential.
3. Define managed-identity Key Vault access, in-memory/cache bounds, no secret propagation to PR/AIR,
   access audit, rotation overlap, revocation, and fail-closed behavior when secret state is unknown.
4. State that rollback can restore configuration but can never restore a revoked, expired, leaked,
   wrong-environment, or superseded credential.
5. Add negative evidence for wrong workload, audience, environment, secret version, and revoked
   authority.

#### HIGH-04 — Emergency Stop ingress and CE-unavailable behavior are not fully bound to WhatsApp

**Package references:** Sections 8.3, 12.6, 14.2, 16, and 17 (`CE-FIT-13`).

The package correctly makes Stop highest-precedence, universal across channels, and portal-only to
release. It says CE unavailability fails safe and Stop remains executable, but does not require the
WhatsApp adapter to recognize and durably hand off an authenticated Stop before ordinary
professional queuing, nor does it bind the WhatsApp path to ADR-031's local Stop evidence buffer and
latched recovery behavior. A generic free-text classifier or asynchronous professional execution
must not become the security boundary for Stop.

**Required remediation:**

1. Define a typed, authenticated WhatsApp Stop command path ahead of context/model execution, with
   idempotent relationship-scoped latching and no model interpretation dependency.
2. Bind CE-unavailable handling explicitly to ADR-031: execute the halt, record in the protected
   local buffer, acknowledge honestly, flush on recovery, and never auto-release.
3. Define ambiguity behavior for conversational uses of the word “stop” without weakening the
   explicit Stop command.
4. Extend `CE-FIT-13` to cover CE outage, duplicate delivery, simultaneous channels, adapter restart,
   and release attempts through WhatsApp.

### MEDIUM

#### MEDIUM-01 — Prompt-injection separation lacks an enforceable assembly contract

**Package references:** Sections 8.1–8.4, 9.1, 10.1–10.2, 14.2, and 21.

Server-resolved context, registered hints, versioned policy, typed proposals, and authoritative commit
owners are strong boundaries. The injection control addresses customer and media content but does not
explicitly cover retrieved research, tool/MCP output, quoted history, provider metadata, or derived
summaries. Nor does it require structural separation of trusted instructions from untrusted content
or independent authorization of model-proposed tool/command calls.

**Required remediation:** Require provenance and sensitivity on every assembled segment; treat all
customer, provider, media, research, retrieval, tool, transcript, and summary content as untrusted
data; structurally separate it from institutional/policy instructions; reject instruction-like data
from policy fields; and independently authorize every typed tool or command proposal against current
context, source versions, Decision Space, and assurance. Add adversarial indirect-injection and
cross-segment contamination tests.

#### MEDIUM-02 — Media quarantine is sound but the trust boundary and unsafe-format policy are open

**Package references:** Sections 12.5, 14.1–14.2, 16, 17 (`CE-FIT-11`), and 24.

The package properly requires server retrieval, hard bounds, quarantine, scan-before-use, erasable
storage, and fail-safe unavailability. Supported types and sizes are intentionally blocked pending an
owner decision. The design still needs to state that declared MIME type and filename are untrusted,
that active/archive formats are denied unless explicitly approved, and which workload may move an
object from quarantine to clean storage.

**Required remediation:** Add signature/content sniffing, decompression and parser-resource limits,
deny-by-default format policy, isolated scanner identity and storage permissions, immutable scan
verdict/version lineage, timeout/error quarantine, and deletion/retention behavior for rejected
payloads. Keep media activation blocked until the Section 24 owner decision is recorded.

#### MEDIUM-03 — Service-window and template enforcement lacks authoritative time and revocation rules

**Package references:** Sections 12.3–12.4, 14.2, 16, and 17 (`CE-FIT-10`).

Exact template/version/locale/schema/environment binding and fail-closed dispatch are adequate.
However, the package does not identify the authoritative event that opens the service window, the
trusted clock and boundary-race rule, or how opt-out/revocation immediately invalidates already
queued dispatch.

**Required remediation:** Define the qualifying inbound event, server-side trusted time, inclusive
boundary semantics, queue-time and send-time revalidation, immediate consent/opt-out revocation, and
reconciliation for dispatch whose window or template approval changes between queue and provider
submission.

#### MEDIUM-04 — Privacy-safe telemetry does not cover exception, trace propagation, access, or retention

**Package references:** Sections 14.3, 17 (`CE-FIT-14`), and 18.

Opaque metrics and the prohibited-data list are appropriate, but sensitive values can still escape
through framework exception bodies, request capture, trace baggage, dead-letter payloads, scanner
diagnostics, and high-cardinality labels. “Unapproved logs” also leaves the approval boundary
undefined.

**Required remediation:** Prohibit payloads, headers, signatures, phone proofs, tenant/relationship
identifiers, provider references, prompts, transcripts, and media metadata from ordinary logs,
metrics, traces, baggage, exception responses, and dead-letter diagnostics. Define the separately
authorized protected diagnostic/evidence path, RBAC, retention, deletion/legal-hold behavior,
sampling rules, and automated leakage tests across failure paths.

### LOW

No independent LOW finding is raised.

## 4. Controls Found Adequate At Enterprise Level

Subject to the findings above, the package establishes sound enterprise boundaries for:

- dedicated Demo/UAT/Production numbers, callbacks, state, media, telemetry, templates, and
  deployment authority with no cross-environment runtime fallback;
- raw-body signature validation before parsing and source IP explicitly excluded as authentication;
- canonical delivery, execution, customer decision, and constitutional evidence as independent
  states;
- exact template binding and fail-closed provider dispatch;
- server-resolved context and non-client-writeable tenant, authority, prompt, and policy fields;
- tenant RLS and normalized inaccessible responses;
- media quarantine and scan-before-reasoning;
- Stop precedence and portal-only release;
- honest unresolved/failure states rather than optimistic success; and
- rollback that preserves canonical messages, decisions, evidence, and environment identity.

## 5. Verdict

**CHANGES REQUIRED.**

The enterprise direction is materially strong and no immediate activation is authorized, but the
Chief Solution Architect cannot yet proceed without inventing security controls for phone-to-tenant
resolution and assurance, durable webhook acknowledgement/replay semantics, provider-secret workload
authority, and WhatsApp Emergency Stop behavior. Resolve all HIGH findings in the controlling package
before Solution Architecture decomposition. MEDIUM findings may be resolved in the controlling
package or in an explicitly prerequisite Security Architecture contribution, but they must be closed
before the affected solution contract is accepted or implementation begins.

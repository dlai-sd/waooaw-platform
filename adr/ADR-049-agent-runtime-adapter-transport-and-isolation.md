# ADR-049: Agent Runtime Adapter Transport and Isolation

**Status:** ACCEPTED - FOUNDER, 2026-08-31
**Date:** 2026-08-31
**Decision owner:** Enterprise Architecture (INST-004)
**Work Contract:** WC-080 / ARA-GAP-01
**Constitutional basis:** C-001, C-002, C-003, C-005, C-007, C-023, C-025, C-026, C-032, C-035, C-036, C-037, C-049, C-059, C-063, C-065, C-071, C-076, C-079, C-080, C-094
**Preserved decisions:** ADR-002, ADR-003, ADR-005, ADR-015, ADR-018, ADR-031, ADR-035, ADR-046
**Controlling plan:** `architecture/agent-runtime-adapter-contract-v1-execution-plan.md`

## Context

WC-079 established admission and immutable artifact binding but not the private wire contract through
which Professional Runtime invokes an admitted implementation. The Agent Runtime Adapter is a private
execution port owned by Professional Runtime. It is not a public service, customer API, provider
callback target, Platform-Agent Contract signal consumer, or substitute for constitutional authority.

## Decision

Agent Runtime Adapter v1 uses OpenAPI 3.1, HTTP/1.1, UTF-8 JSON,
RFC 9457 problem details, and optional Server-Sent Events. Professional Runtime is the sole ordinary
caller.

### Discovery And Binding

Professional Runtime resolves an adapter only from the platform activation registry using
`environment + professionalTypeId + professionalVersion + artifactDigest`. The registry returns the
private endpoint, fixed HTTPS port `8443`, expected workload URI SAN, exact audience, admitted protocol
range, and immutable OCI digest. Caller-supplied URLs, DNS scanning, hostname synthesis, public service
discovery, descriptor guessing, and fallback to another artifact are prohibited.

The resolved deployment, presented identity, descriptor, and OCI digest must match the ACTIVE
admission snapshot before configuration or execution.

### Identity And Transport Protection

Every protected route uses mTLS under ADR-046 in development, CI, Demo, UAT, and Production. TLS 1.3
is preferred and TLS 1.2 is the minimum. Plain HTTP, opportunistic TLS, authentication-disabled local
modes, public ingress, browser CORS, and cross-environment trust are prohibited.

The caller identity is `spiffe://waooaw.<environment>/workload/professional-runtime`. Each adapter has
a distinct identity `spiffe://waooaw.<environment>/workload/agent-runtime-adapter/<adapter-id>` and
audience `urn:waooaw:service:agent-runtime-adapter:<adapter-id>`. Wildcard identities and an
all-adapters audience are prohibited.

Each request also carries a PR-signed asymmetric service JWT bound to the mTLS caller, target audience,
environment, operation, method and route, tenant and relationship scope, professional and Skill
versions, artifact and admission digests, invocation ID, payload digest, deadline, and unique `jti`.
Its lifetime is at most 60 seconds and never exceeds the request deadline. It is not a customer token,
CE permit, or independent bearer authority.

Unauthenticated liveness is available only to the local orchestrator on a non-routable probe listener
and exposes process-loop state only.

### Deadlines

Every protected call carries an absolute UTC RFC 3339 deadline with millisecond precision. PR applies
the shortest of the caller deadline, operation maximum, and remaining Temporal activity deadline.

| Operation | Maximum wire deadline |
|---|---:|
| Descriptor, readiness, status, result | 2 seconds |
| Configuration validation | 5 seconds |
| Plan | 30 seconds |
| Execute acceptance | 5 seconds |
| Cancel or resume acknowledgement | 2 seconds |
| SSE establishment | 2 seconds |
| Adapter Emergency Stop acknowledgement | 100 milliseconds |

The Stop allocation is within, and does not enlarge, the constitutional 250 ms end-to-end limit.
Deadline expiry prevents new consequential dispatch. Work that outlives a request proceeds only under
the already accepted PR Temporal workflow.

### Version Negotiation

PR supplies the admitted inclusive minimum and exclusive maximum protocol versions. The adapter
selects the highest mutually supported minor within the admitted major and returns the exact selected
version. That version is pinned for the invocation and every later status, cancel, result, and event
call. There is no silent downgrade, cross-major negotiation, or fallback to an unadmitted version.
No compatible version returns the canonical unsupported-schema error.

### Streaming

SSE is adapter-to-PR only. Sequence is scoped to one invocation, starts at one, and increases by one.
The SSE `id` is the decimal sequence. Duplicate IDs must carry the same digest. PR reconnects with
`Last-Event-ID` and fresh workload authority; the adapter replays strictly after that sequence.
An unavailable cursor returns the canonical expired-cursor error, after which PR reconciles through
status and result without inferring missing events. Heartbeats are comments and carry no authority.

### Deployment Isolation

Version 1 deploys one isolated WAOOAW-managed adapter for each admitted
`professionalTypeId + professionalVersion + artifactDigest` tuple. Replicas may scale only that one
immutable digest. Demo, UAT, and Production use separate identity, trust, registry, configuration,
secrets, policy, and runtime state while promoting the same qualified digest.

Each deployment is non-root, read-only, capability-dropped, resource-bounded, and denied host
filesystem, Docker socket, privileged mode, sibling workload access, and undeclared egress. Working
state is ephemeral and reconstructable from PR-owned state. Shared multi-artifact hosts and remotely
hosted adapters require a later accepted ADR.

### Failure Behavior

mTLS failure closes the connection without protected detail. Authenticated failures use privacy-safe
RFC 9457 responses and stable codes. Transport loss or deadline after dispatch produces an `UNKNOWN`
caller outcome, never success or permission to create a second invocation. PR reconciles with the same
invocation ID, idempotency key, payload digest, and pinned version before retry.

Only classified transient transport failures are retryable within the original deadline.
Authentication, authorization, binding, schema, stale authority, idempotency, constitutional denial,
and deterministic adapter failures require changed authorized input. No failure permits plaintext,
public routing, artifact or environment fallback, cached authority, or optimistic success.

CE unavailability follows ADR-031: no new consequential work is dispatched and local Stop remains
executable. Adapter unavailability cannot delay or negate the platform Stop.

## Consequences

This decision creates no public endpoint or standalone platform service. It requires environment-
specific registry, PKI, network policy, deployment, and conformance evidence. HTTP/1.1 and SSE are
sufficient for v1 but do not authorize bidirectional streaming. Dedicated deployments cost more than
shared hosting but preserve identity, artifact, network, and failure boundaries.

## Required Evidence

Qualification must prove deterministic registry resolution; positive and negative mTLS/JWT binding;
every deadline and reconciliation rule; compatible-minor and unsupported-major behavior; SSE ordering,
reconnect, expiry, and fallback reconciliation; one-artifact isolation; default-deny ingress/egress;
resource limits; replica and transport failure; CE outage; and Stop during adapter unavailability.
Demo, UAT, and Production renderings must preserve the same semantics with environment-specific trust.

## Founder Decision

The Founder accepted ADR-049 on 2026-08-31. Acceptance fixes the transport and isolation decision but
does not itself authorize implementation, deployment, provider access, expenditure, customer traffic,
PR approval, or merge.

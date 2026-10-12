# ADR-052 - Channel-Neutral Conversation Context And Policy

**Status:** Proposed - Founder review required
**Date:** 2026-10-12
**Decision owner:** Enterprise Architecture (INST-004)
**Authorization:** Founder-authorized bounded architecture assignment, 2026-10-12
**Constitutional basis:** C-002, C-003, C-023, C-030, C-034-C-039, C-042, C-049, C-050, C-052,
C-059, C-063, C-079, C-094
**Capabilities:** 1.5 Onboard Digital Professional; 1.7 Configure Agent via Conversation; 4.5 Set And
Update Skill Goals; 6.1 Authenticate And Authorize Customers; 6.2 Isolate Tenant Data
**Drivers:** AD-004, AD-013, AD-015, AD-025
**Preserved decisions:** ADR-002, ADR-003, ADR-017, ADR-019, ADR-023, ADR-024, ADR-031, ADR-035,
ADR-040, ADR-044, ADR-046, ADR-049, ADR-051
**Acceptance dependency:** ADR-051 must be accepted first or accepted simultaneously without changing
its one-relationship/one-conversation ownership
**Controlling architecture:**
`architecture/reference/components/conversation-engine-whatsapp-enterprise-architecture.md`

## Context

WAOOAW has one durable Conversation Core and one Conversational Employment Workspace per Employment
Relationship. It also has web conversation, omnichannel continuity, browser voice, and WhatsApp phone
identity. It does not yet have one enterprise decision for selecting semantic interaction context or
composing professional conversation style consistently across web, WhatsApp, and future mobile.

Allowing each screen, channel, agent, or prompt to define context independently would fragment
history, permit context injection, produce contradictory recommendations, and force mobile to
reimplement business semantics.

## Decision

WAOOAW adopts a server-resolved, versioned **Interaction Context** and a layered, versioned
**Conversation Policy** over the existing relationship Conversation Core.

1. Each Employment Relationship retains one durable professional conversation and canonical message
   sequence across channels.
2. Business Platform remains the only ordinary public conversation facade and authoritative context
   projection owner.
3. Effective context is resolved from authenticated identity, relationship state, pending protected
   intent, customer selection, source versions, continuity checkpoint, message intent, channel
   capability, and a registered client hint.
4. Clients may supply a bounded context key and opaque subject reference. They may not supply tenant,
   authority, system prompt, free-form context, policy content, or model configuration.
5. Conversation Policy composes institutional, professional, interaction-purpose, customer,
   vocabulary, locale/accessibility, and channel-rendering layers.
6. Conversation/model output proposes typed changes. Authoritative owners validate and commit.
7. Canonical history remains distinct from bounded model working context. Summaries and retrieval are
   derived, versioned, attributable, and replaceable.
8. Every professional execution binds exact context, policy, Decision Space, and applicable source
   versions.
9. Material source changes stale affected context before further consequential execution.
10. No new deployable service is created. BP, PR, AIR, CE, WBE, Phone Identity, storage, and channel
    clients retain their existing boundaries.
11. Every assembled context segment carries provenance and sensitivity; all customer, provider,
    media, research, retrieval, tool, transcript and summary content is untrusted data structurally
    separated from accepted policy.
12. Canonical message append, sequence allocation, idempotency reservation and outbox publication
    share one BP-owned transaction; facts and summaries retain reproducible lineage.

## Alternatives Considered

| Alternative | Decision |
|---|---|
| Let each screen select a prompt and context | Rejected: untrusted presentation would control professional reasoning and authority |
| Maintain separate web, WhatsApp, and mobile conversations | Rejected: fragments history and violates ADR-051 continuity |
| Let the model infer all context from transcript | Rejected: non-deterministic, stale, injection-prone, and unauditable |
| Store the full history in every model request | Rejected: unnecessary cost, latency, privacy exposure, and context-window coupling |
| Create a standalone Conversation Engine service | Rejected: no capability requires a new deployable; existing BP/PR/AIR ownership is sufficient |
| Put all style rules in agent prompts | Rejected: channel and universal institutional behavior would drift across agents |
| Use one global customer memory across agents | Rejected: violates relationship purpose and risks unauthorized context contamination |
| Extend existing Conversation Core with context/policy contracts | Accepted: minimum structure preserving delivered ownership and continuity |

## Consequences

### Positive

- Web, WhatsApp, and future mobile share history, context semantics, and professional behavior.
- Context changes are attributable and resistant to client or prompt injection.
- Agent-specific professional behavior remains possible without duplicating universal policy.
- Research, inference, customer confirmation, and authoritative facts can remain distinct.
- Mobile can reuse generated BP contracts when separately authorized.

### Negative

- Context and policy versions add contract, persistence, and compatibility obligations.
- Channel rendering must prove semantic equivalence rather than merely display the same text.
- Existing agent prompts require conformance analysis before policy activation.
- Stale source versions create additional reassessment states visible to customers.

## Risks And Controls

| Risk | Control |
|---|---|
| Context key becomes an authority token | Server validation against identity, relationship, commands, and source versions |
| Policy layers conflict | Deterministic precedence with constitutional safety first |
| Summaries distort history | Attributable derived artifact; canonical messages remain authoritative |
| Repeated interrogation harms experience | Research-before-question and known-fact repetition fitness checks |
| Style becomes manipulative | Prohibit generic praise, pressure, hidden failure, and engagement without purpose |
| Simultaneous channels double-commit | Canonical idempotency and source-version conflict handling |
| Cross-agent leakage | Relationship-scoped context and explicit authorized sharing only |

## Fitness And Evidence

Acceptance requires CE-FIT-01 through CE-FIT-08, CE-FIT-13 through CE-FIT-15, exact-version contract
tests, agent policy conformance, adversarial context-injection tests, cross-channel semantic
equivalence, source-version staleness, and privacy-safe observability.

## Reversibility

Before activation this ADR may be rejected without runtime migration. After activation, the prior
supported context/policy version remains available for a bounded rollback window. Rollback blocks
new-version-only commands but does not rewrite messages, accepted decisions, or evidence. Derived
summaries and checkpoints can be rebuilt from referenced authoritative inputs.

## Implementation Boundary

This ADR authorizes no endpoint, schema, prompt, source file, dependency, model, provider,
deployment, mobile application, customer traffic, PR approval, or merge. Detailed Solution, Data,
Security, AI, Product, Platform, Runtime, and Test contracts require separate authority.

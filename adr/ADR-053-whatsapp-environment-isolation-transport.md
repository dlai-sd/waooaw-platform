# ADR-053 - WhatsApp Environment Isolation And Transport Boundary

**Status:** Proposed - Founder review required
**Date:** 2026-10-12
**Decision owner:** Enterprise Architecture (INST-004)
**Authorization:** Founder-authorized bounded architecture assignment, 2026-10-12
**Constitutional basis:** C-001, C-003, C-023, C-032, C-039, C-042, C-049, C-059, C-063, C-066,
C-067, C-079, C-086
**Capabilities:** 1.7 Configure Agent via Conversation; 6.1 Authenticate And Authorize Customers;
6.2 Isolate Tenant Data; 6.4 Observe Platform Health; 6.7 Implement Governed Cloud Delivery
**Drivers:** AD-004, AD-013, AD-015
**Preserved decisions:** ADR-003, ADR-008, ADR-009, ADR-010, ADR-014, ADR-017, ADR-023, ADR-031,
ADR-046, ADR-047, ADR-051, ADR-052
**Acceptance dependency:** Environment isolation can be accepted independently; channel-neutral
context, history and voice semantics require accepted ADR-052
**Controlling architecture:**
`architecture/reference/components/conversation-engine-whatsapp-enterprise-architecture.md`

## Context

WAOOAW has accepted WhatsApp phone identity and implemented channel continuity, but live provider
activation, environment number allocation, callback topology, outbound delivery, media transport, and
deployment isolation require one explicit decision. The Founder has selected dedicated Demo and UAT
numbers and will purchase a separate Production number, preferably ending in the telephone-keypad
digits for `WAOOAW`.

Using one provider identity or callback authority across environments would permit credential,
message, deduplication, media, telemetry, and customer-state contamination. Treating a static IP as
webhook authentication would also weaken Meta signature controls.

## Decision

1. Demo, UAT, and Production each use a dedicated WhatsApp number and provider phone-number identity.
2. Repository-safe bindings identify Demo by display suffix `3575`, UAT by suffix `2344`, and
   Production as pending with preferred suffix `926629`. Exact E.164 values and provider IDs are
   protected environment configuration.
3. Each environment has a distinct HTTPS callback hostname, TLS binding, app/WABA authority, verify
   token, app secret/access authority, Key Vault scope, deduplication namespace, media store,
   conversation data, telemetry, templates, and deployment authority.
4. UAT uses stable Azure environment ingress and DNS. Meta receives an HTTPS hostname callback, not a
   raw IP. Demo may be short-lived but must disable callback acceptance before teardown.
5. Webhook GET challenge verification and POST raw-body HMAC validation are mandatory and
   environment-bound. Source IP is not authentication.
6. Inbound provider events are normalized before Conversation Core acceptance. Outbound dispatch is
   created only from canonical BP messages or typed command outcomes.
7. Provider acceptance, delivery, read, professional execution, customer decision, and
   constitutional evidence are independent states.
8. Outside the applicable service window, outbound messaging requires an exact approved template,
   locale, variable schema, purpose, and opt-in evidence.
9. Media retrieval is server-side, authenticated, short-lived, scanned, bounded, and stored only in
   the approved erasable payload boundary. Provider URLs and tokens are never public or durable.
10. WhatsApp voice reuses existing BP/PR/AIR voice orchestration and joins the same canonical
    conversation after required review/confirmation.
11. No runtime fallback may cross Demo, UAT, or Production.
12. Stable outbound egress is added only if an authorized external dependency requires allow-listing;
    it is not implied by static inbound ingress.

## Alternatives Considered

| Alternative | Decision |
|---|---|
| One number for all environments | Rejected: provider identity and customer traffic can cross boundaries |
| Demo and UAT share credentials but use different URLs | Rejected: credential compromise and provider-event routing remain shared |
| Authenticate Meta by allow-listed source IP only | Rejected: does not preserve required message integrity; HMAC remains mandatory |
| Configure Meta with a raw Azure IP | Rejected: prevents normal TLS hostname identity and controlled ingress migration |
| Let clients download provider media | Rejected: exposes provider authority and bypasses server safety controls |
| Treat webhook 200 or provider read as professional success | Rejected: transport cannot prove execution, decision, or evidence |
| Build a separate WhatsApp conversation service | Rejected: duplicates BP conversation authority |
| Isolated number, callback, secrets, state, and storage per environment | Accepted: minimum structure preventing cross-environment trust and data drift |

## Consequences

### Positive

- Demo experimentation cannot silently reach UAT or Production state.
- UAT has a stable URL and ingress while preserving DNS/TLS migration.
- Production remains dark until number purchase and separate Founder authority.
- Provider retries and statuses reconcile without duplicate professional actions.
- WhatsApp text, media, and voice converge on the same conversation semantics.

### Negative

- Three numbers and isolated provider configuration increase cost and operations.
- Templates and number/app bindings require environment-specific qualification.
- Demo teardown needs provider-aware cleanup rather than only deleting Azure revisions.
- Media and delivery-status handling add storage, scanning, retention, and monitoring obligations.

## Risks And Controls

| Risk | Control |
|---|---|
| Wrong environment phone/app calls callback | Bind provider phone-number ID, app authority, hostname, and secret scope |
| Static IP is mistaken for trust | HMAC, freshness, deduplication, schema validation remain mandatory |
| Callback teardown loses messages | Disable acceptance, expose explicit unavailable state, then remove revision |
| Provider retry duplicates action | Environment/provider-event dedup plus canonical idempotency |
| Template/version drift | Exact approved template/locale/schema configuration and fail-closed dispatch |
| Media malware or token leakage | Server retrieval, quarantine, scan, redaction, bounded retention |
| Number migration loses consent/history | Explicit migration plan, customer communication, opt-in/template continuity, rollback |
| Production activated accidentally | Separate authority, secret scope, DNS/provider gates, dark default |

## Primary References

- Meta WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api
- Meta webhook endpoint verification:
  https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/create-webhook-endpoint
- Meta webhook security: https://developers.facebook.com/docs/graph-api/webhooks/securing
- Meta messages/media: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages
- Microsoft Azure Container Apps networking:
  https://learn.microsoft.com/en-us/azure/container-apps/networking
- Microsoft custom domains and certificates:
  https://learn.microsoft.com/en-us/azure/container-apps/custom-domains-certificates

## Fitness And Evidence

Acceptance requires CE-FIT-09 through CE-FIT-16, exact environment rendering, negative
cross-environment tests, valid/invalid challenge and HMAC tests, replay/dedup tests, service-window
and template matrices, media safety/erasure tests, provider status reconciliation, Demo teardown,
UAT stable-host proof, and Production-dark proof.

## Reversibility

An environment may move ingress or hostname through controlled DNS and callback rebinding while
retaining environment identity and proving no cross-environment fallback. Number migration requires
a separately authorized provider migration plan. Rollback restores the prior callback/number binding
without rewriting conversation, opt-in, delivery, or evidence records.

## Implementation Boundary

This ADR authorizes no number purchase, Meta app/WABA mutation, provider registration, credential,
template, Azure resource, DNS record, workflow change, source file, deployment, customer traffic,
Production activation, PR approval, or merge.

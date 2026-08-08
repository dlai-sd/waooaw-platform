# AE-01 Security and Consent Contract

**Producing Institution:** INST-007 — Security Architect
**Authorization:** GOA-GOAL-005-INST-007-02
**Status:** D-06 CONTRIBUTED — implementation-neutral
**Applies to:** WC-057 through WC-060

## Authentication Assurance

ADR-023 controls WhatsApp identity:

| Action | Minimum assurance | Failure behavior |
|---|---|---|
| Discovery, disclosure, interview, context proposal, simulated trial | Tier 1 phone identity or authenticated web | Reduce to public/non-sensitive capability if identity uncertain |
| Configuration confirmation and material budget proposal | Tier 2 explicit confirmatory reply; Tier 3 MPIN where financial threshold applies | Deny mutation; preserve draft |
| New Employment Contract acceptance | Tier 4 Keycloak-authenticated web portal | WhatsApp supplies 15-minute single-use deep link only |
| Payment authorization | Tier 4 portal plus Razorpay-hosted checkout | No card/payment secret in WAOOAW UI or chat |
| Emergency Stop | Current authenticated relationship participant; Stop is fail-safe and available at low assurance when relationship can be resolved | Halt; uncertainty never delays Stop |
| Emergency Stop release | Tier 4 portal, authorized same-tenant `EMPLOYER` role, fresh authentication, explicit release confirmation | Remain stopped |

The deep link is random, one-time, relationship/action bound, expires in 15 minutes, and cannot itself authenticate or authorize. It resumes only after Keycloak authentication and server-side participant-role verification.

## Payment Consent

The portal displays contract version/hash, exact INR amount, GST, subscription terms, ad-spend treatment, refund/cancellation terms, and provider-hosted payment action. Customer explicitly selects “Proceed to Razorpay”; BP records a payment-authorization proposal evidence event. Razorpay captures payment credentials and returns signed webhook evidence. Contract acceptance and payment authorization are separate. Dispute/refund uses existing WBE records and exposes order, payment, invoice, refund/chargeback, and status evidence without secrets.

## Participant and Stop Release

Any authenticated participant may request Stop when the relationship is resolvable; fail-safe Stop takes priority. Release is limited to an active same-tenant participant bound as `EMPLOYER`, not merely the stopper, evaluator, relationship manager, channel possessor, or platform operator. Release requires portal reauthentication, display of originating Stop reason/time/scope, explicit “Release Emergency Stop,” and evidence linked to the original Stop correlation. No conversational “resume,” reconnect, timeout, retry, or session token refresh can release it.

For AE-01, Stop scope includes evaluation/trial PAAS sessions, configuration, contract presentation, activation workflow, and channel handoff for the single Employment Relationship. AE-02 consequential execution Stop fan-out is inherited from the same relationship invariant but implemented and proven in AE-02, not WC-060.

## Takeover and Handoff Controls

- Meta HMAC, ±5-minute timestamp, and message-ID deduplication precede WhatsApp processing.
- Internal phone JWT is 30 minutes, server-issued, tenant scoped, and never sent to the customer.
- Unknown or changed phone may create a new evaluation relationship but cannot attach to an existing one.
- Existing-relationship phone attach requires Tier-4 portal authentication by an active `EMPLOYER`, presentation of hashed phone identity, explicit approval, a 15-minute request expiry, and fresh Meta validation on the next message.
- Shared-device/SIM takeover cannot perform Tier-4 actions; security events, three failed MPIN attempts, and repeated attach attempts lock/escalate per ADR-023.
- Handoff target reauthenticates and verifies current role/authority; assurance downgrade reduces allowed actions.

## Evidence Reader Access Matrix

| Caller | Scope |
|---|---|
| Evaluator | Own relationship disclosures, trial/configuration evidence, limitations, Stop |
| Employer | Full customer-visible relationship timeline, contract/payment/activation, charges, handoffs, Stop/release |
| Relationship Manager | Timeline except restricted payment/personal payload unless separately authorized |
| Other tenant/relationship | No existence disclosure |
| Platform operator | No customer API access; constitutional audit path only under separate authority |

The API returns proof metadata and authorized payload references. It excludes credentials, raw prompts, policy internals, another tenant's data, internal threat signals, and erased payload. Export uses short-lived authenticated download and records evidence.

## Interview and Trial Input Safety

Customer input is untrusted data. Existing PII/injection controls run before inference. System, constitutional, professional, and trial policies are isolated from user content. Answer tags are server-controlled. Public evidence must include source and retrieval time. Unsupported claims become `INFERENCE` or `LIMITATION`; prohibited or unsafe requests are refused. Generated/supplied media passes C-061 safety and consent gates before any demonstration artifact is retained.

## Required Security Tests

HMAC failure; stale/replayed webhook; forged tenant/relationship hint; phone attach without portal proof; expired deep link; MPIN lockout; contract/payment attempted from WhatsApp; takeover after SIM change; confused deputy; downgrade; cross-tenant Evidence Reader query; Stop under degraded connectivity; release by wrong role/channel/reconnect; prompt injection; user-forged evidence tag; and export-link replay all deterministically deny or fail safe with attributable evidence.
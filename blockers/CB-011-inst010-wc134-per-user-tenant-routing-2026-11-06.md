# CB-011 — WC-134 WhatsApp Guest Journey and Account Binding

**Office:** Platform IT Expert (INST-010)
**Work Contract:** WC-134
**State:** JOURNEY CLARIFIED — Founder direction recorded; guest Conversation API and Identity OTP binding remain open

## Blocking condition

The prior WC-134 framing treated an unknown WhatsApp sender as a provisional Identity participant
and described the interaction as registration/onboarding. That conflicts with the Founder-confirmed
product boundary: WhatsApp must allow guest discovery and approved agent preview without WAOOAW
account registration, while Trial/Hire requires the web portal's Identity-owned account and
registration flow. A sender-bound guest session is not a customer identity, account, tenant,
membership, or relationship.

The shared Conversation layer currently exposes relationship-scoped canonical conversations. The
additive guest discovery/preview scope, safe portal handoff, and Identity-owned OTP channel-binding
contract are not yet specified end-to-end. The earlier `PhoneOnboardingIdentity` flow risked
presenting guest exploration as registration; WC-134 now moves first-contact records into the
Business Platform guest-session store.
The implementation must close the guest-session API and owner contracts before public admission is
enabled. Tenant RLS, sender participant scope, and recipient binding still apply; account/relationship
data additionally requires current Identity session and membership authorization.

## Evidence

- [WC-134 journey and acceptance matrix](../work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md)
  records the Founder direction and the explicit R001-R005 boundaries.
- [Customer Engagement Workspace requirements](../architecture/reference/components/customer-engagement-workspace-enterprise-requirements.md)
  distinguish guest discovery, portal registration, channel binding, and relationship conversation.
- [CSA-CEWA-008](../architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md)
  specifies tuple resolution, reassignment, environment/tenant/relationship binding, and no
  automatic relationship attachment.
- [WhatsAppCapabilityGate.cs](../src/business-platform/Services/WhatsAppCapabilityGate.cs) requires
  the single activation tenant and recipient binding.
- [WhatsAppTenantExecutionScope.cs](../src/business-platform/Services/WhatsAppTenantExecutionScope.cs)
  and the outbox worker scope background work to that same tenant.
- [channel-neutral-conversation-business-platform.openapi.yaml](../architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml)
  currently defines relationship conversation operations, not the required guest-session API.
- [Customer Portal Solution Contract](../architecture/reference/components/customer-portal-solution-contract.md)
  requires login for Marketplace detail while explicitly not requiring completed customer
  registration or workspace membership.

## Resolution recorded for WC-134

The Founder clarified the required journey in the current conversation:

- Web Marketplace detail requires login but not completed customer registration or membership.
- A voluntary WhatsApp sender may browse offerings and use an approved, bounded agent preview
  without a WAOOAW account. First contact creates no customer Identity/account, customer tenant,
  membership, relationship, or employment.
- Trial/Hire continues through the web portal's Identity-owned login/registration flow. Mobile is
  optional for portal registration.
- An authenticated, sufficiently assured portal user may bind WhatsApp using a short-lived,
  purpose-bound OTP that Identity consumes. OTP proves control of that channel only; it is not
  account login, membership, or employment authority and must never enter conversation history.
- Web, WhatsApp, and future mobile reuse BP-owned Conversation and Marketplace semantics. A guest
  session and a canonical relationship conversation remain distinct; history is not copied.

This is the WC-134 execution direction, not a general architecture decision or permission to alter
other products/environments. Existing relationship-only Conversation contracts do not yet define
guest discovery or OTP handoff; close those additive owner/API contracts before enabling public
traffic.

### Budget and operations gaps

- The only recorded traffic authority is the own-number pilot: 30 minutes, ten combined inbound and
  outbound messages, INR 10, and no other customers. It cannot be extrapolated to public Demo.
- The Founder has approved a public-beta target: 10 combined messages per guest per 24 hours, at
  most 100 new guest sessions per day, INR 500/day combined messaging/model cost, and service hours
  09:00-21:00 IST. This target does not yet include a measured per-minute/concurrency ceiling, and
  actual provider/model unit pricing is unverified. Prove these controls and actual cost enforcement
  before activation; do not treat target approval as live authority.
- The prior alert estimate of about INR 314.25/month covers one conservatively costed one-minute log
  rule and one monitored series only; tax, ingestion, other rules, and complete integrated monitoring
  are excluded. It is not approved spend.
- No alert route has verified human receipt: the recorded push success was not received by the
  Founder, and the email attempt had no recipient. WC-134 needs a working, acknowledged receiver and
  accountable incident owner before activation.

This direction is bound to the WC-134 record and ledger for the bounded Demo implementation. Any
broader architecture change must still follow its own approval path. Actual pricing, per-minute and
concurrency caps, alert receipt, and all protected live-action approvals remain unresolved and
fail-closed.

## Founder-approved public-beta target policy — 2026-11-06

The Founder approved this target for implementation and qualification: any voluntary inbound sender
may browse offerings and use a bounded, text-only agent preview without registration; no marketing
campaigns; maximum 10 combined messages per guest per 24 hours; maximum 100 new guest sessions per
day; maximum INR 500/day combined WhatsApp and model cost; published service hours 09:00-21:00 IST.
At a message, session, or spend limit, stop AI processing and return a clear response.

This is not approval to deploy, enable public messaging, incur spend, or run live acceptance. Actual
provider/model pricing must be verified, per-minute/concurrency protections and the hard spend
ceiling proven, all owner/API and operational gates closed, and the exact candidate/window separately
approved before public traffic.

## Work state

WC-134 implementation work is on `ib/134/whatsapp-demo-complete-rollout` from `origin/main` at
`8cf1e38b`. The current branch adds AES-GCM-protected sender routing and a Business Platform
guest-session table, with an idempotent migration from legacy provisional sender records. Focused
.NET checks pass, including real-PostgreSQL sender isolation and migration replay, but these results
do not qualify the complete guest journey. Shared guest Conversation/API and approved agent preview,
portal registration/OTP binding, public controls, provider verification and alert receipt remain
open. This is not exact-image, cloud, or live-provider acceptance. Public traffic remains blocked
by those release gates.

## Founder-requested focused architecture review — 2026-11-06

**Office:** Solution Architect (INST-005)
**Request:** Decide whether INST-010 can continue R001/R002 within the agreed guest boundary, and
identify the minimum missing Conversation and Identity contracts.
**Disposition:** PROCEED WITH BOUNDARY.

- **R001/R002:** Continue implementation within the existing boundary: one dedicated Demo service
  tenant, sender-scoped guests, no customer account or relationship on first contact, and tenant
  plus sender isolation. Do not mark the stories complete until their end-to-end owner/API and
  isolation acceptance passes.
- **R004:** Business Platform Conversation owns guest-session state and shared discovery/approved
  preview semantics. WhatsApp owns transport/rendering only; it must not create a separate assistant
  or transcript store. Any portal handoff may retain explicit intent and opaque references, not copy
  conversation history. The current relationship-only API does not yet define this additive guest
  contract; the Conversation owner must specify and accept it before integration.
- **R005:** Identity remains the owner of the authenticated Web-to-WhatsApp channel-binding flow,
  including a purpose-bound, short-lived, single-use OTP that proves channel possession only. It
  grants no account, membership, or relationship authority, and the OTP is not conversation content.

This review authorizes no provider access, deployment, public activation, live traffic, or spend.

## Founder registration amendment — 2026-11-06

The Founder subsequently authorized making a verified WhatsApp number mandatory during web
registration. This supersedes the earlier optional-mobile statement above. A registrant explicitly
requests a single-use authentication code; number recognition does not replace account login,
membership, assurance, or authenticated channel linking.

Required registration state, destination-bound challenges, serialized confirmation, one-minute
resend cooldown, five-guess expiry, and both completion-path checks are implemented. Regression
cases are authored; execution remains deferred until all WC-134 stories are implemented. Compilation
in the pinned Docker .NET runner passes with zero warnings/errors, and the web type-check passes.
These are compilation results, not executable acceptance or live delivery evidence.

The Meta-side prerequisite is an approved **Authentication** template using a **Copy code** button,
the security disclaimer, and a 15-minute expiry warning. The proposed name is
`waooaw_registration_otp`; the final approved name and exact language code must be verified before
configuration. The existing Marketing template must not be used for authentication. No token or
secret is requested through chat.

Production authentication-template dispatch, its protected activation/cost controls, and inbound
verified-registration recognition remain open. No provider send, live configuration, or deployment
was performed by this amendment.

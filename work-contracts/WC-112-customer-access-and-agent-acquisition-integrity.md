# WC-112 - Customer Access And Agent Acquisition Integrity

## Record Control

| Field | Value |
|---|---|
| Authoring office | Platform IT Expert (INST-010) |
| Assigned by | Founder instruction in the 2026-10-06 continuous working session |
| Status | DRAFT EVOLVING WORK CONTRACT - FROZEN COMPONENT IMPLEMENTATION AUTHORIZED 2026-10-06 - DOWNSTREAM CONFLICTED REQUIREMENTS BLOCKED |
| Frozen components | Login / Registration / Logout / Switch Account and common Trial / Hire entry and confirmation experience FOUNDER FROZEN 2026-10-06; downstream employment, activation and exception mechanics remain in requirements analysis |
| Baseline | `origin/main` at `a7d3c2cbd7348624ae6c03698adc4f3e5987f553` |
| Live evidence boundary | Read-only Azure Demo inspection on 2026-10-06; no mutation, deployment, DNS, spend, provider configuration or acceptance |
| Delivery unit | One bounded cross-component customer-access and agent-acquisition integrity component |
| Implementing office | Platform IT Expert (INST-010), only after explicit current-session implementation authorization |
| Constitutional basis | C-023, C-032, C-041, C-049, C-059, C-063, C-065, C-071, C-076, C-077, C-088, C-090 |

## 1. Objective

**Overall objective:** deliver one resilient, industry-standard and constitutionally governed
customer journey from anonymous access through authenticated/registered identity, Trial or Hire
commitment, commercial satisfaction and truthful My Agents handoff, with server-owned state,
idempotent recovery, observable evidence and mandatory anti-drift gates that prevent later changes
from silently weakening the experience.

The objective contains two customer outcomes:

1. Login, standalone or intent-triggered Registration, Logout, relogin and Switch Account work
   predictably without identity or tenant leakage.
2. Trial or Hire uses a common contract/checkout experience, server-owned pricing and coupon truth,
   correct Razorpay or zero-payable behavior, resilient fulfillment and an authoritative My Agents
   outcome.

The implementation replaces implicit coordination through UI booleans, redirects and sequential
browser callbacks with guarded state machines and versioned API contracts. It repairs the recorded
defects without redesigning WAOOAW's accepted identity, commercial, employment, payment or cloud
architecture. Completion means the journeys work as complete customer outcomes, not merely that
individual endpoints or components pass in isolation.

The Founder-frozen customer-access and common Trial/Hire confirmation components in Sections 5.1
and 5.2 are immediately normative for future design and implementation planning, but do not
authorize implementation in this session. After
Founder acceptance and resolution of the remaining requirement gaps in Section 3.4, changes to an
owning surface must prove compatibility with the canonical transition tables and executable journey
gates. A later Work Contract may extend these workflows but
may not silently alter states, transitions, invariants, API semantics, customer copy or handoff
behavior.

## 2. Authority And Scope

This Work Contract authoring session is authorized to:

- inspect `origin/main` source and tests;
- perform read-only inspection of the current Azure Demo deployment, revisions, logs and traces;
- compare observed behavior with accepted WAOOAW contracts and current official industry guidance;
- record defects, gaps, requirements, acceptance evidence and implementation boundaries; and
- create this Work Contract and register it as awaiting Founder confirmation.

Founder authority granted on 2026-10-06 permits implementation of the frozen Sections 5.1 and 5.2
and their directly required supporting changes after the contract author review and exact source
baseline are complete. This authority does **not** resolve the conflicted downstream requirements in
Section 3.4 or authorize:

- Azure or Razorpay mutation, deployment, DNS, spend, secret access or customer traffic;
- real-provider acceptance, destructive testing or use of production customer data;
- a new identity provider, payment provider, service, dependency or architecture;
- self-approval, self-merge or a claim that the two journeys are accepted.

Live Demo qualification, real Google login and real Razorpay payment require separately stated
provider and financial authority, exact test identities, amount ceiling, rollback boundary and
acceptance owner.

## 3. Evidence Baseline

### 3.1 Live Demo deployment

Read-only Azure inspection on 2026-10-06 found the active Demo customer-flow revisions healthy and
receiving all traffic:

| Component | Active revision |
|---|---|
| Web | `ca-demo-web--0000059` |
| Business Platform | `ca-demo-business-platform--0000054` |
| Billing Engine | `ca-demo-billing-engine--0000057` |
| Keycloak | `ca-demo-keycloak--0000011` |
| Identity edge | `ca-demo-identity-edge--0000003` |

Healthy infrastructure does not prove a successful customer journey.

### 3.2 Observed defects and gaps

| ID | Flow | Evidence | Defect or gap | Required disposition |
|---|---|---|---|---|
| WC112-D01 | Login/account switch | Demo Keycloak logs, 2026-10-06 09:05-09:06 UTC | Google broker login failed with `different_user_authenticated`, HTTP 500, missing authentication-session context and missing `BROKERED_CONTEXT`. | One guarded account-switch/login transition must clear or preserve each session layer in an explicit order and recover without a Keycloak error page. |
| WC112-D02 | Session continuity | Demo Keycloak logs, 2026-10-06 03:06 UTC | A refresh token was rejected because its Keycloak session was no longer active. | Browser, NextAuth, Keycloak and WAOOAW session expiry must converge on one customer-safe reauthentication state. |
| WC112-D03 | Login/register | `web/lib/auth-transition.ts`, `AuthJourney.tsx`, `RegistrationFlow.tsx` | Auth "state" is split between React booleans, best-effort `sessionStorage` telemetry and server callbacks. Missing browser telemetry silently becomes no transition evidence. | Define one versioned transition schema with guarded events, correlation and server-authoritative outcome evidence. |
| WC112-D04 | Logout | `web/app/api/auth/keycloak-logout/route.ts` | `LOGOUT_COMPLETION/SUCCEEDED` is recorded before the browser reaches and completes Keycloak RP-initiated logout. The fallback can clear only the local NextAuth session. | Distinguish requested, local-cleared, WAOOAW-revoked, IdP-logout-pending, completed and partially failed outcomes. Never record completion before the IdP result is known. |
| WC112-D05 | Login/register | NextAuth provider commands and registration flow | Login, registration, account linking, account switching and return-target preservation have overlapping but separate redirect logic. | One shared API/UI contract must define intent, safe return target, provider selection, registration handoff and retry behavior. |
| WC112-D06 | Trial/Hire | `/api/acquisition/continue` and `/api/acquisition/hire-checkout` | Trial and Hire use separate browser orchestrators and inconsistent intent representation while sharing downstream relationship behavior. | Use one acquisition aggregate and canonical event vocabulary with intent-specific guarded branches. |
| WC112-D07 | Hire/payment/handoff | Hire checkout route and Billing Engine | After payment capture, the browser sequentially creates the relationship, binds payment and creates a My Agents selection. A bind failure returns `503` and asks the customer to retry the same request. | A durable saga/outbox must own captured-payment-to-portal completion. Browser loss or retry must not strand payment or duplicate employment. |
| WC112-D08 | Razorpay | Browser confirmation plus `/webhooks/razorpay` | Browser confirmation and webhook delivery can arrive in either order. Existing signature, provider-fetch and idempotency checks are useful but no single documented transition table governs both paths. | Both inputs must feed one idempotent payment state machine with ordering, replay and conflict rules. |
| WC112-D09 | Coupon | Hire preview, pre-Hire checkout and Promotions service | Pre-Hire applies a validated coupon to price and stores the code, but the traced Hire path does not call the atomic `apply_discount` redemption operation. Usage limits can therefore remain unconsumed. | Reserve and consume coupon capacity atomically with checkout outcome; release only under explicit expiry/cancellation rules. |
| WC112-D10 | Observability | Demo Log Analytics, prior 24 hours | Acquisition-specific query returned Business Platform SQL activity but no Web/Billing `trial.continue`, `hire.checkout`, outcome or handoff trace marker. | Emit one privacy-safe correlation and state-transition envelope across Web, BP, Billing and portal handoff. |
| WC112-D11 | Regression control | WC-083 through WC-110 history | Repeated local repairs changed adjacent stages and introduced new defects because tests proved components or snapshots rather than the complete customer outcome. | Add immutable end-to-end journey gates and require them for every changed owning or dependent surface. |

### 3.3 Accepted strengths to preserve

- Safe same-origin return-target handling.
- Authorization Code/OIDC provider integration through Keycloak and NextAuth.
- Access-token expiry checks and fail-closed refresh behavior.
- Server-side commercial calculation and coupon eligibility validation.
- Server-side Razorpay order creation.
- Server-side payment-signature verification and provider status/amount/currency verification.
- Signed webhook verification and replay-aware persistence.
- Idempotency keys for acquisition and payment commands.
- Authoritative relationship membership and My Agents selection handles.
- No client-side activation from an unverified payment result.

### 3.4 Constitutional path and requirement gaps

The governing WAOOAW path is not an ordinary sign-up and e-commerce checkout:

```text
Public discovery
  -> Keycloak-brokered authenticated visitor
  -> explicit Register, Trial or Hire intent (entry rule requires Founder resolution below)
  -> durable account and membership
  -> one durable pre-employment Acquisition Intent for exact customer + Agent + Version + mode
  -> rights, capability, limitations, Trust, Authority, evidence, Stop and price disclosure
  -> optional bounded non-consequential Trial
  -> outcome, Skill, Decision Space, budget, review cadence and Stop configuration
  -> exact versioned Employment Contract proposal and explicit same-tenant acceptance
  -> server-owned commercial quote and optional promotion
  -> provider-hosted payment or independently evidenced zero-price satisfaction
  -> create exactly one Employment Relationship only when Trial confirmation or Hire completion succeeds
  -> Evidence First exactly-once activation
  -> My Agents handoff
  -> Onboard -> Induct -> Goal Verification -> Business Outcomes -> Operations
```

The following records trace requirement gaps or conflicts in the current constitutional chain.
WC112-RG01 is resolved by the Founder-frozen access contract; unresolved entries must not be decided
by code or agent preference.

| ID | Requirement gap or conflict | Conflicting or incomplete authority | Required Founder disposition |
|---|---|---|---|
| WC112-RG01 | **RESOLVED 2026-10-06:** registration entry previously differed across contracts. | Standalone Register and Trial/Hire-triggered Registration are both valid. Login alone never registers. | Supersede the narrower Customer Portal wording; after registration, continue to the ordinary portal or resume the exact initiating Trial/Hire intent. |
| WC112-RG02 | **RESOLVED 2026-10-06:** Employment Relationship creation timing previously conflicted. | Earlier AEEC/WC-059/WC-095 material required a relationship before commerce, while WC107-R013 and the Founder-settled customer experience require completion first. | A durable Acquisition Intent, not an Employment Relationship, carries the exact customer + Agent + Version + mode through Registration, contract, Trial/Hire and retries. Create the relationship only when Trial confirmation or Hire completion succeeds; then expose it in My Agents. This WC-112 disposition supersedes relationship-first sequencing for this flow. |
| WC112-RG03 | **RESOLVED 2026-10-06:** contract/payment ordering previously conflicted with relationship timing. | The exact contract must precede payment, but no relationship exists until successful completion. | Bind versioned Employment Contract presentation and checkbox acceptance to the Acquisition Intent; payment or zero-price satisfaction may begin only afterward. Transfer the immutable acceptance reference into the relationship created at successful completion. |
| WC112-RG04 | Consent concepts are collapsed in recent journey requirements. | WC107-R010 uses one Terms/Privacy consent for Trial/Hire, while AEEC/WC-059 distinguish rights disclosure, Trial consent, Employment Contract acceptance, scope-boundary confirmation and payment proceed intent. | Define the exact consent ledger, sequence, expiry and re-consent triggers without dark patterns or duplicate clicks. |
| WC112-RG05 | No single lifecycle vocabulary has declared precedence. | AEEC, BP relationship states, evaluation workflow states, WC-095 readiness stages, WBE payment states and WC-107 journey outcomes overlap; WC-095 explicitly says architecture must reopen if enums disagree. | Ratify one layered state model and supersession map before implementation. |
| WC112-RG06 | **RESOLVED 2026-10-06:** Trial eligibility identity was underspecified. | Earlier acquisition rules used customer + agent type. | Enforce at most one Trial per customer + exact Agent + Version; default duration is 14 days with an authorized Agent + Version override. |
| WC112-RG07 | **PARTIALLY RESOLVED 2026-10-06:** coupon authority is settled; lifecycle details require implementation closure. | WC-095 permits a customer-entered code only under a public-promotion policy. | Only the Founder may create, activate, suspend or revoke coupons. Bind each coupon to exact Agent + Version, percentage and validity; implement standard bounded reservation, release, max-use, stacking and reversal rules without silent charge fallback. |
| WC112-RG08 | Post-logout completion authority is incomplete. | The identity contract requires RP-initiated logout but does not define whether an allowlisted post-logout callback, back-channel logout, provider response or bounded local proof authoritatively completes the WAOOAW logout state. | Select the completion evidence and partial-failure customer behavior. |
| WC112-RG09 | Captured-payment unresolved obligations have no time or remedy policy. | Existing contracts require durable reconciliation but do not set customer notification, escalation, refund/void, support ownership or maximum unresolved duration. | Define the paid-customer protection SLA and remedy authority. |
| WC112-RG10 | Refund, dispute and chargeback effects on employment are not closed. | WC-059 requires dispute/refund evidence, but no current contract fully maps refund, reversal, chargeback and failed settlement to subscription, activation and relationship states. | Define financial reversal states, customer rights, service continuation/suspension and evidence requirements. |
| WC112-RG11 | Pre-active relationships lack a complete My Agents projection. | My Agents defines lifecycle/resume truth, but the customer-visible behavior for declined, checkout-cancelled, payment-unresolved, activation-unresolved and contract-expired relationships is not fully specified. | Define retention, visibility, next action and dismissal/archive semantics for every pre-active terminal or unresolved state. |
| WC112-RG12 | Consequence classification is not explicit for the journey. | C-099 requires independent verification for financial and constitutional commitments, but the journey has no DCM mapping for registration completion, contract acceptance, coupon consumption, payment capture, activation and handoff. | Ratify the journey DCM and independent verifier for each deterministic-required transition. |

### 3.5 Intentional WAOOAW differentiators - not gaps

| WAOOAW choice | Difference from common industry flow | Why it is retained |
|---|---|---|
| Authenticated visitor before customer registration | Many products create an account immediately after social login. | Login remains non-mutating; the customer can inspect professionals before accepting employment or commercial consequences. |
| Durable Acquisition Intent before relationship formation | Typical commerce relies on a browser checkout session or creates the service relationship early. | One server-owned intent preserves exact customer, Agent + Version, mode, contract, quote and retry identity without representing employment before Trial/Hire succeeds. |
| Trial is a governed billing mode | Typical trials are anonymous feature access or payment-card funnels. | Trial carries rights, metering, evidence, explicit limits and non-consequential authority without silently becoming paid. |
| Hire is constitutional employment, not a purchase button | Typical marketplaces treat checkout acceptance as sufficient. | WAOOAW separates disclosure, Decision Space, contract, payment and authority activation. |
| Payment does not activate the professional | Typical SaaS unlocks immediately after capture. | Activation requires exact contract, payment, authority and Evidence First; uncertainty remains pre-active. |
| Capability, Trust and Authority remain independent | Typical products infer permission from plan, role or model capability. | WAOOAW licenses authority through evidence and never substitutes capability or trust. |
| Three ledgers remain separate | Typical products centralize operational, customer and audit history. | Constitutional ownership, RLS and evidentiary independence prevent platform or agent self-certification. |
| Emergency Stop and immediate pro-rata termination are constitutional rights | Typical subscriptions impose billing periods or cancellation windows. | Human override and non-exploitation outrank commercial convenience. |
| Operations is locked behind verified goals and mandate | Typical onboarding unlocks product operation after payment. | Onboard, Induct, Goal Verification and Business Outcomes establish governed purpose before autonomous work. |
| Zero-price Demo uses real commercial truth without a fake payment | Typical demos bypass commerce or fabricate successful provider events. | The same quote/consent/activation contract applies, while no bank, Razorpay or payment method is falsely represented. |

## 4. Industry Practice Baseline

Implementation must remain consistent with:

- [IETF OAuth 2.0 for Browser-Based Applications](https://www.rfc-editor.org/info/rfc10017) and
  [OAuth 2.0 Security Best Current Practice](https://www.rfc-editor.org/info/rfc9700):
  Authorization Code with PKCE, exact redirect handling, transaction-bound `state`, minimum browser
  token exposure and no implicit flow.
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html) and
  [RP-Initiated Logout](https://openid.net/specs/openid-connect-rpinitiated-1_0.html):
  issuer/audience/nonce validation, explicit session
  termination and registered post-logout redirect behavior.
- [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html),
  [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
  and [OAuth](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html) guidance:
  session rotation, fixation prevention,
  secure/HTTP-only/SameSite cookies, bounded retries, generic customer-safe errors and reauthentication
  after assurance loss.
- [Razorpay Standard Checkout guidance](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/):
  server-created Orders, server-side signature verification,
  webhook verification, idempotent event processing, captured-payment confirmation and no fulfillment
  from a browser callback alone.
- Reliable transaction patterns: durable saga/process manager, transactional outbox/inbox,
  idempotent consumers, explicit compensation/reconciliation and observable terminal outcomes.
- Accessible transactional UX: clear progress, disabled duplicate submission, preserved intent,
  recoverable failure, keyboard/focus continuity, responsive layout and no false success.

External guidance constrains implementation quality. It does not authorize a new provider, service,
dependency, cloud action or architecture.

## 5. Customer Journey State Machines

Sections 5.1 and 5.2 are Founder frozen. Section 5.3 remains a synthesis candidate pending
resolution of the remaining constitutional-chain conflicts and the upstream authority chain.

### 5.1 Founder-frozen customer access state machine

Login authenticates but never registers. Registration is available as a standalone entry and is
also required when an authenticated unregistered customer selects Trial or Hire. Registration
completion preserves the initiating destination. The server, not browser state, owns registration
status.

| State | Permitted events | Result |
|---|---|---|
| `ANONYMOUS` | `LOGIN_REQUESTED`, `REGISTER_REQUESTED` | Create correlation, bind an allowlisted return target and registration/ordinary-login intent, then move to `BROKER_REDIRECT_PENDING`. |
| `BROKER_REDIRECT_PENDING` | `BROKER_REDIRECTED`, `BROKER_CANCELLED`, `BROKER_FAILED` | Move to callback pending or a recoverable anonymous failure. |
| `BROKER_CALLBACK_PENDING` | `CALLBACK_VERIFIED_UNREGISTERED`, `CALLBACK_VERIFIED_REGISTERED`, `LINK_REQUIRED`, `CALLBACK_REJECTED` | Establish a rotated authenticated session, resolve registration status from server truth, require an explicit account-link decision or fail closed. |
| `AUTHENTICATED_UNREGISTERED` | `BASIC_FEATURE_USED`, `REGISTER_SELECTED`, `TRIAL_SELECTED`, `HIRE_SELECTED`, `ACCOUNT_SWITCH_REQUESTED`, `LOGOUT_REQUESTED` | Allow only the frozen basic-feature boundary. Standalone Register or Trial/Hire begins the same registration state machine with the exact continuation purpose. |
| `REGISTRATION_REQUIRED` | `REGISTRATION_STARTED`, `RETURN_TO_PORTAL`, `LOGOUT_REQUESTED` | Begin/resume idempotent registration, return to authenticated basic features or terminate the session. |
| `REGISTRATION_IN_PROGRESS` | `REGISTRATION_SAVED`, `VERIFICATION_REQUIRED`, `REGISTRATION_COMPLETED`, `REGISTRATION_CANCELLED` | Preserve authoritative draft/version; completion creates/reuses one customer account, membership and binding, then continues to the ordinary portal or exact Trial/Hire intent. |
| `AUTHENTICATED_REGISTERED` | `REGISTER_SELECTED`, `SESSION_REFRESHED`, `SESSION_EXPIRED`, `TRIAL_SELECTED`, `HIRE_SELECTED`, `ACCOUNT_SWITCH_REQUESTED`, `LOGOUT_REQUESTED` | Reuse registration without duplication, provide registered-customer options, resume safe intent or enter an explicit session-termination sequence. |
| `ACCOUNT_SWITCH_PENDING` | `PROTECTED_STATE_CLEARED`, `PRIOR_SESSION_REVOKED`, `IDP_ACCOUNT_CHOOSER_STARTED`, `NEW_BROKER_CALLBACK_VERIFIED`, `SWITCH_FAILED` | End/isolate the prior customer first, force explicit account selection and never transfer tenant, intent, coupon, relationship, cache or portal data. |
| `LOGOUT_PENDING` | `PROTECTED_STATE_CLEARED`, `WAOOAW_REVOKED`, `IDP_LOGOUT_REDIRECTED`, `IDP_LOGOUT_CONFIRMED`, `LOGOUT_PARTIAL_FAILURE` | Revoke WAOOAW access immediately, clear protected cookies/cache/history-restorable state, complete RP-initiated IdP logout or expose a truthful partial outcome that cannot silently restore protected access. |
| `ACCESS_FAILED` | `RETRY`, `RETURN_ANONYMOUS` | Retry only the failed transition with preserved safe intent. |

Illegal, stale, duplicate or identity-mismatched events return a typed conflict and do not mutate
state. Provider cancellation is not an internal error. Account-link and different-user cases receive
an explicit customer decision surface rather than a generic Keycloak 500 page.

### 5.2 Founder-frozen common Trial/Hire entry and confirmation

Trial and Hire use the same customer journey structure and the same WAOOAW checkout presentation.
Their financial effects remain distinct. Both require Login, Registration when needed, eligibility
validation and explicit acceptance of the exact applicable Employment Contract through a URL and
unchecked checkbox.

```text
Marketplace or My Agents Trial
  -> select exact Agent + Version and Trial or Hire mode
  -> Login / Registration when needed
  -> validate Agent + Version and customer eligibility
  -> present exact Employment Contract URL
  -> explicit checkbox acceptance
  -> common WAOOAW checkout interface
       -> Trial: 14-day free mode; coupon and payment methods visible read-only; no provider call
       -> Hire payable: coupon applied server-side; Razorpay methods enabled; hosted checkout
       -> Hire zero-payable: discount shown; Razorpay methods visible read-only; no provider call
  -> truthful authoritative completion
  -> My Agents mode `Trial` or `Hire`
```

| Mode | Frozen checkout behavior | Institutional outcome |
|---|---|---|
| Trial | Highlight `Free Trial - 14 days` by default; authorized exact Agent + Version configuration may change duration. Show coupon as `Not applicable during Trial` and Razorpay method families read-only/disabled. | Do not reserve/consume a coupon, create a Razorpay order, load actionable hosted Checkout or fabricate payment. Confirm one Trial entitlement per customer + exact Agent + Version and show `Trial` in My Agents. |
| Hire, payable | Allow a customer coupon; validate and apply it server-side to the exact Agent + Version offer; show authoritative itemization and enable supported Razorpay methods. | Invoke Razorpay-hosted Checkout for the server-created payable order and continue only from independently verified payment truth. |
| Hire, zero-payable | Show the same itemization and Razorpay method families read-only/disabled, including list price, coupon, discount and `Amount due: INR 0`. | Do not create a Razorpay order or fabricate payment. Record distinct zero-price commercial satisfaction and continue through the same activation boundary. |

Trial never silently converts to Hire or paid service. Expiry is customer-visible in My Agents.
Hire may start directly from Marketplace or from an existing Trial for the same Agent + Version.

### 5.3 Draft downstream Trial/Hire acquisition state machine

| State | Permitted events | Result |
|---|---|---|
| `OFFER_DISCOVERED` | `TRIAL_SELECTED`, `HIRE_SELECTED`, `NOT_NOW`, `EXIT` | Freeze professional/admission/version, disclosure revision and customer intent without creating commercial commitment. |
| `IDENTITY_REQUIRED` | `IDENTITY_CONFIRMED`, `REGISTRATION_COMPLETED` | Resume the exact frozen intent without browser-owned identity or commercial truth. |
| `ACQUISITION_INTENT_HELD` | `RIGHTS_DISCLOSED`, `DECLINED`, `EXPIRED`, `STOPPED` | Persist/reuse one durable server-owned Acquisition Intent for exact customer + Agent + Version + mode; no Employment Relationship exists yet. |
| `RIGHTS_DISCLOSED` | `TRIAL_CONTRACT_REQUESTED`, `CONFIGURATION_STARTED`, `NOT_NOW`, `EXIT` | Prove plain-language rights, capability, limitations, Trust, Authority, evidence posture, Stop and price consequences before Trial or commitment. |
| `TRIAL_ACTIVE` | `TRIAL_EXPIRED`, `HIRE_SELECTED`, `STOPPED` | Preserve Trial evidence and relationship identity; never silently convert or execute live consequential authority. |
| `CONFIGURING` | `HIRE_CONTRACT_REQUESTED`, `CONFIGURATION_REVISED`, `NOT_NOW` | Confirm Hire outcome, Skills, Decision Space, budget, review cadence and Stop conditions. |
| `CONTRACT_PROPOSED` | `TRIAL_CONTRACT_ACCEPTED`, `HIRE_CONTRACT_ACCEPTED`, `CONTRACT_REJECTED`, `CONTRACT_EXPIRED`, `CONTRACT_REVISED` | Accept only the exact mode/version/hash through fresh authorized same-tenant intent and distinct scope confirmation. |
| `CONTRACT_ACCEPTED` | `CONFIRMATION_REQUESTED`, `NOT_NOW` | Permit the Founder-frozen common confirmation interface only for the exact current accepted contract. |
| `CHECKOUT_PREVIEWED` | `TRIAL_CONFIRMED`, `COUPON_SUBMITTED`, `HIRE_CHECKOUT_ACCEPTED`, `OFFER_REFRESH_REQUIRED` | Render the mode-specific frozen behavior and recalculate all applicable price, tax, discount, renewal and cancellation consequences on the server. |
| `TRIAL_STARTING` | `TRIAL_STARTED`, `TRIAL_REJECTED` | Idempotently allocate the governed non-consequential Trial mode and create exactly one Trial relationship without coupon or payment-provider mutation. |
| `COUPON_RESERVED` | `ORDER_REQUESTED`, `ZERO_PRICE_CONFIRMED`, `RESERVATION_EXPIRED` | Bind bounded coupon capacity to customer and checkout intent. |
| `ORDER_CREATING` | `ORDER_CREATED`, `ORDER_UNRESOLVED` | Persist intent before the provider call and reconcile uncertain provider outcomes. |
| `PAYMENT_PENDING` | `BROWSER_CONFIRMATION_RECEIVED`, `WEBHOOK_RECEIVED`, `PAYMENT_FAILED`, `PAYMENT_EXPIRED` | Feed either provider signal into one idempotent payment verifier. |
| `COMMERCIAL_SATISFIED` | `RELATIONSHIP_REQUESTED` | Persist independently verified captured/zero-price evidence; create exactly one Hire relationship from the Acquisition Intent and immutable contract acceptance. |
| `ACTIVATION_PENDING` | `ACTIVATED`, `ACTIVATION_RETRYABLE_FAILURE`, `ACTIVATION_TERMINAL_HOLD` | Validate tenant + newly created relationship + accepted contract + activation-eligible commercial outcome, commit constitutional evidence, then activate exactly once. |
| `EMPLOYMENT_ACTIVE` | `PORTAL_HANDOFF_REQUESTED`, `PAUSED`, `SUSPENDED`, `TERMINATED` | Preserve the active relationship, authority snapshot, billing projection and immediate Stop/termination rights. |
| `PORTAL_HANDOFF_PENDING` | `SELECTION_CREATED`, `SELECTION_RECREATED` | Produce a bounded My Agents handoff handle for the authoritative relationship. |
| `MY_AGENT_READY` | `PORTAL_OPENED`, `ONBOARD_STARTED`, `INDUCT_STARTED` | Land on `/professionals/mine`, focus the exact relationship and show truthful lifecycle, Trial/Hire, payment, activation and next authorized readiness stage. |
| `ACQUISITION_RECONCILING` | `RETRY_DUE`, `RECONCILED`, `MANUAL_REVIEW_REQUIRED` | Continue without asking the customer to repeat a captured payment. |
| `ACQUISITION_FAILED` | `RETRY_SAFE`, `RETURN_TO_OFFER` | Retry only pre-consequence or explicitly idempotent operations. |

`COMMERCIAL_SATISFIED` creates a durable institutional obligation: exactly one relationship must be
created and eventually activate or expose a reviewable paid-customer exception. It may never silently
return the customer to checkout, create another relationship, or represent payment as authority.

## 6. Canonical Requirement Index

| ID | Normative outcome |
|---|---|
| WC112-R001 | Publish one versioned machine-readable transition contract for each state machine, including states, events, guards, effects, terminal outcomes and illegal-transition responses. |
| WC112-R002 | Generate or centrally reuse state/event types so Web, BP, Billing, tests and telemetry cannot define incompatible vocabularies. |
| WC112-R003 | Bind every journey to one privacy-safe correlation ID propagated across browser, NextAuth/Keycloak edge, Web API, BP, Billing and My Agents handoff. |
| WC112-R004 | Login and registration use Authorization Code/OIDC with PKCE, exact registered redirects, transaction-bound state/nonce and safe same-origin return targets. |
| WC112-R005 | Account switching revokes or isolates the prior local, WAOOAW and Keycloak session before accepting the new broker identity; different-user and link-required outcomes receive explicit UI. |
| WC112-R006 | Registration create/update/verify/complete/cancel commands are idempotent, version guarded and resumable without duplicate accounts or lost acquisition intent. |
| WC112-R007 | Logout records requested, local-cleared, WAOOAW-revoked, IdP-pending and completed/partial-failure outcomes separately; completion cannot precede IdP logout confirmation. |
| WC112-R008 | Expired or rejected refresh tokens clear protected state once and route to a reauthentication surface that preserves only a safe return target. |
| WC112-R009 | Trial and Hire share one acquisition aggregate, event vocabulary, offer identity and handoff contract while retaining intent-specific guards. |
| WC112-R010 | Server responses, not browser state, own professional version, disclosure, terms, list price, tax, discount, payable amount, currency and payment readiness. |
| WC112-R011 | Coupon validation, bounded reservation, atomic consumption and release are customer/checkout bound, concurrency safe, idempotent and enforce max-use and discount caps. |
| WC112-R012 | Razorpay Orders are created server-side after durable checkout intent persistence and use an immutable receipt/reference bound to the internal checkout. |
| WC112-R013 | Browser confirmation and verified Razorpay webhooks feed the same idempotent payment transition; signature, order, payment, amount, currency and captured status must match. |
| WC112-R014 | Duplicate, delayed, reordered and conflicting provider events cannot duplicate payment, coupon consumption, the existing relationship identity, activation or portal handoff. |
| WC112-R015 | A durable saga/process manager and outbox/inbox carry independently verified commercial satisfaction through evidence commitment, activation and My Agents handoff for the existing relationship without depending on the browser remaining open. |
| WC112-R016 | Retryable post-payment failures enter reconciliation with bounded backoff and operator-visible evidence; terminal failures stop and retain the paid-customer obligation. |
| WC112-R017 | Trial completion and successful/zero-price Hire produce exactly one authoritative relationship and a bounded selection handle for `/professionals/mine`. |
| WC112-R018 | My Agents focuses the exact new relationship and displays authoritative mode, lifecycle, setup, payment/Trial status and next action without implying activation that has not completed. |
| WC112-R019 | UI surfaces expose clear progress, cancellation, retry and truthful failure; prevent duplicate submit; preserve keyboard/focus/RTL/mobile behavior; and never show success before the terminal server state. |
| WC112-R020 | Structured logs and traces record correlation, state, event, prior/new state, result, reason code, component, duration and immutable identities without tokens, secrets, provider payloads or unnecessary PII. |
| WC112-R021 | Dashboard queries distinguish login, registration, logout, Trial, checkout, coupon, payment, relationship, reconciliation and portal-handoff conversion/failure rates. |
| WC112-R022 | Contract tests reject unknown states/events, illegal transitions, stale versions, unsafe redirects, identity mismatch, price drift, coupon overuse and payment replay. |
| WC112-R023 | Docker journey tests cover all happy paths and each observed defect, including Google different-user, broker-context loss, stale refresh, logout partial failure, coupon concurrency, webhook-before-browser, browser-before-webhook, browser loss after capture, bind retry and handoff recreation. |
| WC112-R024 | One immutable-candidate browser matrix covers Chromium, Firefox and WebKit at desktop and 360px mobile with accessibility checks and exact customer-visible outcomes. |
| WC112-R025 | CI impact selection makes the WC-112 contract and journey gates mandatory for every owning/dependent auth, acquisition, pricing, payment, relationship, activation, portal or deployment change; no snapshot-only substitute is accepted. |
| WC112-R026 | Post-deployment verification uses synthetic identities and bounded provider authority, proves end-to-end correlation and rollback, and records Demo acceptance separately from local qualification. |
| WC112-R027 | No implementation is complete until all pre-existing WC112-D01 through WC112-D11 dispositions have direct executable evidence and no new unresolved journey defect remains. |
| WC112-R028 | The final contract records Founder disposition for WC112-RG01 through WC112-RG12 and a precedence/supersession map; unresolved requirement conflict blocks implementation. |
| WC112-R029 | One durable server-owned Acquisition Intent is minted/reused after registered customer Trial/Hire selection and binds customer + exact Agent + Version + mode, disclosure, contract, quote and retry identity; exactly one Employment Relationship is created only on successful Trial confirmation or Hire completion. |
| WC112-R030 | Before Trial or commitment, the customer sees rights, Skills/capability, limitations, Trust, Authority, evidence posture, Emergency Stop, price/resource consequences and immediate termination rights in plain language. |
| WC112-R031 | Capability, Trust and Authority remain distinct in API, UI and state; payment, plan, role, Trial success or model capability cannot grant professional authority. |
| WC112-R032 | Trial is an explicit, bounded, metered free mode with a Founder-authorized Billing Profile, predictable zero-cost substitutions, at most one Trial per customer + exact Agent + Version, a 14-day default with authorized version-specific override, preserved customer rights and no consequential external action. |
| WC112-R033 | Hire configuration confirms outcome, Skills, Decision Space, budget ceiling, review cadence and Stop conditions before contract proposal. |
| WC112-R034 | Employment Contract acceptance binds exact version/hash, authorized same-tenant actor, fresh assurance, separate scope-boundary confirmation and committed evidence; Trial/Terms/Privacy/payment consent cannot substitute. |
| WC112-R035 | Checkout and zero-price commercial satisfaction cannot begin before WC112-R034 passes; price, tax, discount, renewal, cancellation/refund and resource consequences remain inspectable and exportable. |
| WC112-R036 | Hire completion creates one relationship from tenant + Acquisition Intent + exact accepted contract + activation-eligible commercial outcome; activation uses that immutable tuple with DCM-required independent verification and C-023 evidence committed before `ACTIVE` success. |
| WC112-R037 | CE/evidence unavailability permits Login and authorized read-only exploration but fail-safe halts registration completion, contract acceptance, payment commitment, activation and other CE-gated mutations without false processing UI. |
| WC112-R038 | Trial, contract, payment and activation preserve the separate Professional Experience, Customer Evidence and Constitutional Audit ledgers with tenant RLS and no self-benefiting evidence as sole proof. |
| WC112-R039 | Immediate Stop, pause, resume and termination remain visible and reachable from Trial/My Agents; billing effects are pro-rata from the constitutional event and committed evidence is retained. |
| WC112-R040 | My Agents truthfully projects pre-active, Trial, active, paused, suspended, terminated and unresolved states; Operations remains locked until Goal Verification and mandate eligibility pass. |
| WC112-R041 | Provider availability is independently gated: an enabled provider must pass redirect, callback, registration continuation, returning login, sign-out, repeat-login, failure and rollback; otherwise it is disabled, not partly released. |
| WC112-R042 | Login establishes an authenticated identity without creating customer registration, membership, Employment Relationship or commercial state. |
| WC112-R043 | Standalone Register and Trial/Hire-triggered Registration use one idempotent registration state machine; the latter resumes the exact server-held initiating intent after completion. |
| WC112-R044 | Server truth classifies every verified identity as authenticated-unregistered or authenticated-registered; relogin restores that classification and never forces an existing registered customer through registration again. |
| WC112-R045 | Authenticated-unregistered customers receive only the frozen non-consequential basic-feature boundary; registered-only capabilities fail with a typed registration-required outcome rather than an authorization error. |
| WC112-R046 | Logout revokes WAOOAW access immediately, clears protected cookies/cache/history-restorable state, performs RP-initiated IdP logout and reports completed versus partial provider logout truthfully. |
| WC112-R047 | Switch Account terminates or isolates the prior session before forcing the provider account chooser; no tenant, registration draft, Trial/Hire intent, coupon, relationship, cache or My Agents state crosses identities. |
| WC112-R048 | WC112-R004 through R008 and R041 through R047 are mandatory constitutional-compliance gates for every future identity implementation, provider enablement, release qualification and change-impact test selection. |
| WC112-R049 | Trial and Hire share one WAOOAW confirmation/checkout interface after Login, Registration when needed, exact Agent + Version eligibility and mode-bound Employment Contract acceptance. |
| WC112-R050 | Trial and Hire both require the customer to open the exact applicable Employment Contract URL and affirm an initially unchecked acceptance control; acceptance records customer, tenant, Agent + Version, mode, contract version/hash and time. |
| WC112-R051 | The Trial confirmation interface prominently states `Free Trial - 14 days` by default, the authorized effective duration, zero amount due, no payment required and no silent paid conversion. |
| WC112-R052 | Trial displays coupon and Razorpay method families read-only/disabled for experience consistency; it never validates, reserves or consumes a coupon, creates a Razorpay order, loads actionable hosted Checkout or fabricates payment evidence. |
| WC112-R053 | Successful Trial confirmation creates/reuses exactly one entitlement for customer + exact Agent + Version and makes the authoritative My Agents entry visible with mode `Trial`. |
| WC112-R054 | Trial expiry never initiates payment or Hire and is displayed truthfully as `Expired` in My Agents until a separately authorized customer action changes the lifecycle. |
| WC112-R055 | Hire may begin directly from the exact Marketplace Agent + Version or from its existing Trial; Trial-to-Hire preserves customer, Agent + Version, evidence and continuity without using Trial consent as Hire contract or payment consent. |
| WC112-R056 | Hire coupons are Founder-governed and bind exact Agent + Version, percentage, validity interval and additional approved eligibility/use rules; the browser supplies only the entered code and never price or authority. |
| WC112-R057 | A positive Hire amount enables supported Razorpay methods and invokes hosted Checkout only for a server-created order bound to the accepted contract and authoritative quote. |
| WC112-R058 | A zero-payable Hire shows the same itemization and Razorpay method families read-only/disabled but creates no Razorpay order and fabricates no provider event; WBE records distinct independently verifiable zero-price satisfaction. |
| WC112-R059 | WC112-R049 through R058 are mandatory constitutional-compliance gates for every future Trial/Hire UI, API, Billing, contract, My Agents and change-impact implementation. |

## 7. Required Inputs And Gates

| Input or gate | Status | Effect |
|---|---|---|
| Founder authorization for frozen Sections 5.1 and 5.2 | `SATISFIED 2026-10-06` | Local source and test implementation may begin after baseline closure. |
| Founder disposition of WC112-RG02 through WC112-RG12 | `OPEN` | Blocks only downstream relationship, activation and exception behavior whose outcome depends on those conflicts. |
| Accepted identity, acquisition, employment, billing/payment, promotions and Customer Portal contracts | `AVAILABLE WITH CONFLICTS RECORDED` | Frozen requirements control their bounded surfaces; no agent may infer an unresolved precedence. |
| Exact current `origin/main` and safe authorized branch/worktree | `SATISFIED` | `a7d3c2cbd7348624ae6c03698adc4f3e5987f553` on isolated branch `wc/112-customer-journey-integrity` at `/workspaces/waooaw-wc112`; unrelated original-worktree changes remain untouched. |
| Named synthetic identities and data rules | `REQUIRED BEFORE EXECUTABLE TESTING` | Tests must not use production/customer data. |
| Razorpay test-mode authority and bounded credentials | `NOT AUTHORIZED` | Provider-backed qualification remains excluded; local emulation may be implemented and tested. |
| Demo deployment/customer-traffic authority | `NOT AUTHORIZED` | No deployment or live acceptance. |
| Existing API schemas, generated clients, test catalog, Docker runners and telemetry schema | `REQUIRED INPUTS` | Reuse and amend accepted mechanisms; do not create parallel contracts. |

Any missing or conflicting input blocks the affected phase. Local fixtures cannot be represented as
real Google, Razorpay or Demo acceptance.

## 8. Required Outputs

1. Canonical human-readable and machine-readable transition contracts.
2. Versioned APIs and generated clients for guarded commands and typed outcomes.
3. Durable auth and acquisition process managers using existing accepted components.
4. Atomic coupon reservation/consumption and payment inbox/outbox reconciliation.
5. Industry-standard responsive and accessible UI states for both journeys.
6. Cross-component structured telemetry and bounded operational queries.
7. Focused, integration, journey, security, accessibility and deployed-synthetic evidence.
8. Updated existing architecture/component records only where implementation changes their contract.
9. Exact-head author review and Founder-ready PR; no self-approval or merge.

## 9. Strategic Delivery Plan

| Chunk | Requirements | Outcome | Main surfaces | Executable evidence | Dependencies |
|---|---|---|---|---|---|
| A - Constitutional closure and baseline | R001-R003, R020, R022, R028-R031, R038 | Founder-resolved precedence, shared transition schema, relationship identity, disclosure and correlation envelope | Existing identity/employment/acquisition specs, OpenAPI, telemetry contracts | Requirement-conflict closure, schema validation, illegal-transition and correlation tests | Founder dispositions |
| B - Founder-frozen customer access | R004-R008, R019, R023-R025, R037, R041-R048 | Stable Login/Register/Logout, relogin, account switch, registration continuity and provider gating | Web auth, NextAuth/Keycloak integration, BP identity/session APIs | Docker auth contract/unit/integration tests and three-browser journeys | Frozen contract; A supplies shared schema/evidence |
| C - Founder-frozen Trial/Hire confirmation and commercial intent | R009-R012, R019, R022-R025, R029-R035, R038-R039, R049-R059 | Durable relationship analysis plus frozen governed Trial/Hire entry, contract, common checkout experience, pricing and coupon behavior | Marketplace/acquisition Web APIs, BP employment, CE, Billing trial/promotions/payment | Rights/disclosure, Trial, contract, common-checkout, price/coupon concurrency and idempotency suites | Frozen confirmation contract; A for unresolved relationship/authority closure |
| D - Payment, activation and durable fulfillment | R013-R018, R023-R025, R036-R040 | Order-to-evidence-to-activation-to-My Agents saga | Billing payment/webhook, BP relationship/activation, CE, Web handoff | Reordered/duplicate/lost-browser/CE-failure/reconciliation journeys | C |
| E - Qualification and anti-drift lock | R020-R027, R041 | Complete observable customer outcomes and mandatory anti-drift gates | Test catalog, CI impact map, telemetry, deployment verification | Full immutable-candidate Docker/browser matrix; separately authorized Demo checks | B-D |

### 9.1 Mandatory implementation and testing order

The implementing agent must follow this order without substitution:

1. Complete the exact-main baseline, source ownership map, state/API contracts and user-story test
   design.
2. Complete **all authorized source implementation and all corresponding test-case creation across
   every work component**. Tests are authored with the implementation but are not executed through
   Docker during this phase.
3. Perform a source-completeness author review: requirement trace, generated-client impact, migration
   safety, security/privacy, accessibility, observability and absence of placeholder behavior.
4. Only after every authorized implementation story and test case is marked `IMPLEMENTED`, begin
   Docker-based testing.
5. Run Docker validation from smallest falsifying suites to cross-component and browser journeys,
   repairing failures without weakening assertions, skipping tests or lowering thresholds.
6. Rebuild affected immutable candidates after repairs and rerun every invalidated gate before
   closeout.

No early Docker success may substitute for incomplete implementation. No source-complete claim may
substitute for Docker evidence.

### 9.2 WAOOAW best-in-class engineering standard

Implementation must:

- establish contract/API/state ownership before UI orchestration and regenerate clients from the
  accepted source;
- keep identity, tenant, price, coupon, payment, relationship and lifecycle truth server-owned;
- use strict types, typed failures, idempotency, optimistic/concurrency guards, durable inbox/outbox
  or accepted equivalent, RLS and privacy-safe evidence;
- preserve accessibility, responsive behavior, keyboard/focus continuity and truthful progress/error
  presentation;
- reuse accepted components and repository patterns rather than adding parallel services, facades,
  stores or business logic;
- preserve backward compatibility or use an explicit reversible migration/compatibility boundary;
- include focused, integration, concurrency, security, accessibility, browser and cross-service
  journey tests for every changed behavior;
- surface failures explicitly and never use silent fallback, browser-owned success, fabricated
  provider evidence, skipped assertions or reduced quality thresholds;
- keep code, generated contracts, tests, telemetry and customer copy synchronized; and
- finish with exact-head author review, immutable evidence and Founder review without self-merge.

### 9.3 Persistent user-story progress ledger

This table is the repository-persistent restart point. The implementing agent updates it whenever a
story changes state and before any interruption. `IMPLEMENTED` means source and test cases are
complete but Docker evidence has not yet run. `PASS` requires recorded Docker evidence.

| Story | Customer outcome | Requirements | Status | Implementation/evidence reference | Exact next action |
|---|---|---|---|---|---|
| WC112-US-A01 | Login creates authenticated-unregistered or authenticated-registered server truth without implicit registration. | R004, R008, R042, R044-R045 | `IMPLEMENTED` | `web/app/(application)/layout.tsx`; layout test authored; Docker not started | Retain for post-implementation Docker validation. |
| WC112-US-A02 | Standalone and Trial/Hire-triggered Registration share one resumable, idempotent flow. | R006, R043-R045 | `IMPLEMENTED` | Server-owned identity-bound Acquisition Intent persistence plus exact safe Registration return and automatic marketplace continuation tests authored; Docker not started | Retain for post-implementation Docker validation. |
| WC112-US-A03 | Logout, relogin and browser-history behavior terminate and restore the correct identity safely. | R007-R008, R041, R044, R046 | `BLOCKED` | Premature `LOGOUT_COMPLETION` removed and route regression test authored; authoritative completion remains blocked by WC112-RG08 | Founder must select authoritative provider-return completion evidence and partial-failure behavior. |
| WC112-US-A04 | Switch Account cannot transfer protected state and forces explicit provider account selection. | R005, R047 | `IMPLEMENTED` | `SignOutCommand.tsx`; component tests authored; explicit provider selection replaces Google hard-code | Retain for post-implementation Docker validation. |
| WC112-US-T01 | Trial and Hire share Registration, mode-bound Employment Contract acceptance and one checkout shell. | R009-R010, R019, R034-R035, R049-R050 | `IMPLEMENTED` | Exact Agent + Version contract projection URL, content hash, durable intent acceptance, immutable relationship transfer and common checkout tests authored; Docker not started | Retain for contract/API/component/accessibility Docker validation. |
| WC112-US-T02 | One free 14-day default Trial per customer + Agent + Version uses read-only coupon/payment presentation and no provider mutation. | R032, R051-R053 | `IMPLEMENTED` | Read-only checkout UI, exact-version WBE policy, Founder-authorized duration override, owner-first completion and no-relationship-on-owner-failure tests authored; Docker not started | Retain for focused concurrency and BP/WBE/PR Docker validation. |
| WC112-US-T03 | Confirmed Trial and expiry project truthfully into My Agents without automatic Hire. | R017-R018, R040, R053-R054 | `IMPLEMENTED` | Trial completion creates the bounded My Agents selection; My Agents renders acquisition mode and authoritative Trial status; elapsed ACTIVE entitlement projects/persists `EXPIRED`; no conversion path is invoked; Docker not started | Retain for expiry and browser handoff validation. |
| WC112-US-H01 | Founder-governed coupon produces one authoritative, concurrency-safe Hire quote. | R010-R011, R056 | `IMPLEMENTED` | Exact Agent + Version validation, bounded reservation/expiry/cancellation release and bind-time single-consumption source/tests authored; Docker not started | Retain for focused PostgreSQL concurrency validation. |
| WC112-US-H02 | Positive-payable Hire uses one server-created Razorpay order and independently verified outcome. | R012-R016, R057 | `IMPLEMENTED` | Durable pre-Hire order, provider signature plus fetched amount/currency/capture verification, webhook/replay paths, stable correlation and browser-loss retry tests authored; Docker not started | Retain for provider-emulator, reordered-event and browser validation. |
| WC112-US-H03 | Zero-payable Hire retains the checkout experience without provider mutation or fabricated payment. | R015, R035-R036, R058 | `IMPLEMENTED` | Common disabled Razorpay presentation, distinct `FULLY_DISCOUNTED` persistence, no-order branch, coupon single consumption and My Agents handoff tests authored; Docker not started | Retain for negative-provider-call and browser validation. |
| WC112-US-H04 | Completion and recoverable failure produce one truthful My Agents outcome without duplicate payment or employment. | R014-R018, R036, R040 | `BLOCKED` | WC112-RG04-RG05 and RG09-RG12 | Resolve downstream lifecycle, activation and paid-customer exception authority. |
| WC112-US-Q01 | All journeys are observable and protected from future drift by mandatory impact-selected gates. | R001-R003, R020-R027, R048, R059 | `IMPLEMENTED` | Versioned machine-readable state contract, stable acquisition correlation, transition-specific telemetry correction and service/component/API/concurrency test cases authored; Docker not started | Retain for generated-contract, telemetry, privacy and impact-selected Docker gates. |

## 10. Definition Of Done

Checkboxes may be changed to `[x]` only after the evidence column names an immutable commit, test
artifact or Founder decision that directly proves the row.

| Done | Completion obligation | Required evidence |
|---|---|---|
| [ ] | Every authorized user story is `IMPLEMENTED`; no placeholder, TODO, disabled assertion or known source gap remains. | Exact commit plus story-to-files/test-cases trace. |
| [ ] | All required test cases across all work components were created before Docker testing began. | Test inventory and timestamped/exact-commit implementation checkpoint. |
| [ ] | Every applicable WC112 requirement is `PASS`; blocked requirements name the unresolved Founder decision and cannot be represented as complete. | Requirement-to-test/evidence ledger. |
| [ ] | Every WC112-D01 through D11 defect has a direct tested disposition. | Defect-to-test and outcome matrix. |
| [ ] | Login, standalone Registration, Trial/Hire-triggered Registration, Logout, relogin and Switch Account pass service and browser journeys. | Focused Docker results plus Chromium, Firefox and WebKit artifacts. |
| [ ] | Authenticated-unregistered and authenticated-registered customers receive the correct isolated portal behavior with no cross-account state. | Identity/session integration and account-switch evidence. |
| [ ] | Trial and Hire require exact mode-bound Employment Contract acceptance and use the common checkout experience. | Contract/API, component, accessibility and browser evidence. |
| [ ] | Trial proves one entitlement per customer + Agent + Version, effective duration, read-only coupon/payment presentation, no provider mutation and truthful My Agents Trial/Expired status. | Concurrency, Billing/BP integration and browser evidence. |
| [ ] | Hire coupon quote/reservation/consumption is server-owned, Founder-governed, concurrency safe and exact Agent + Version bound. | Billing database/integration/concurrency evidence. |
| [ ] | Positive-payable Hire proves server-created order, signature/provider reconciliation, replay safety and no duplicate charge. | Billing provider-emulator and reordered-event evidence. |
| [ ] | Zero-payable Hire proves identical checkout presentation, disabled payment controls, no Razorpay order/event and distinct zero-price satisfaction. | API, persistence, negative-provider-call and browser evidence. |
| [ ] | Captured or zero-price commercial satisfaction survives browser loss and retryable downstream failure without duplicate charge, coupon use, relationship or handoff. | Saga/reconciliation fault-injection evidence. |
| [ ] | Illegal, stale, duplicate, identity-conflicting, tenant-conflicting and price-drift transitions fail without unauthorized mutation. | Contract, security, RLS and concurrency evidence. |
| [ ] | Logs/traces provide privacy-safe cross-service correlation and state transitions without tokens, secrets, provider payloads or unnecessary PII. | Telemetry assertions and secret/privacy scans. |
| [ ] | Focused Docker suites pass before affected integrated suites; all invalidated suites rerun after repairs. | Exact commands, results and immutable artifacts. |
| [ ] | Three-browser desktop/360px, keyboard, focus, RTL, zoom and accessibility gates pass with no critical violation. | Browser matrix and accessibility reports. |
| [ ] | No CRITICAL/HIGH security finding, secret disclosure, migration hazard, generated-contract drift or quality-threshold reduction remains. | Security/static/schema/migration reports and author review. |
| [ ] | Rollback preserves payment, coupon, relationship, evidence and reconciliation obligations without two active authorities. | Rollback/fault-recovery evidence. |
| [ ] | Exact-head author review finds no unresolved correctness, security, constitutional-compliance or customer-experience defect. | Author-review section bound to exact commit. |
| [ ] | Founder reviews and merges the PR; separately authorized Demo/provider checks and customer acceptance remain accurately distinguished. | PR/merge reference and, when authorized, Demo acceptance evidence. |

## 11. Stop Conditions

Stop and retain evidence if work requires:

- architecture invention or a new provider/service/dependency;
- real provider access, payment, refund, Azure mutation, deployment, DNS or spend without exact current
  authority;
- customer or Production data;
- weakening PKCE, redirect, session, signature, amount, coupon, idempotency, authorization, security,
  quality, accessibility or coverage controls;
- treating a browser callback, local fixture, component test or healthy revision as end-to-end success;
- deleting failed-attempt, reconciliation or payment-obligation evidence;
- manual database repair as the normal customer path;
- an ambiguous state transition or conflicting user change; or
- two reproducible infrastructure failures.

## 12. Rollback And Recovery

- Preserve current accepted API versions until the new transition contract is qualified.
- Gate new behavior behind one reversible compatibility boundary; do not run two payment authorities.
- Never roll back or discard a verified payment, consumed coupon, relationship or audit event.
- A software rollback must leave durable reconciliation workers able to finish or explicitly hold
  in-flight obligations.
- Rollback evidence includes exact candidate, state counts, unresolved obligations, customer-safe
  recovery action and proof that no duplicate charge, coupon use or relationship was created.

## 13. Founder Decisions Required

1. Resolve remaining WC112-RG04, RG05 and RG08 through RG12 and approve the complete authority
   precedence/supersession map; WC112-RG01-RG03 and RG06 are closed, while RG07 has settled Founder
   authority and implementation-owned lifecycle closure.
2. Confirm the amended WC-112 as the governing Work Contract.
3. Approve the resulting downstream state-machine boundary after the frozen components.
4. Define later real Google and Razorpay test authority, identities, amount ceiling and acceptance
   window.
5. Accept the completed customer experience only after immutable-candidate evidence and a Founder-run
   journey.

## 14. Work Contract Author Review

Author review performed by INST-010 on 2026-10-06 before source implementation.

| Finding | Disposition |
|---|---|
| The objective named two flows but did not define the single end-to-end institutional outcome. | Repaired in Section 1 with one measurable overall objective and two subordinate customer outcomes. |
| The delivery plan required per-chunk evidence before later implementation, conflicting with the Founder-mandated implementation-first order. | Repaired in Section 9.1: all authorized source and test-case creation precedes Docker execution. |
| The prior Definition of Done was prose that could be claimed without durable per-item status. | Replaced with the evidence-bearing checkbox table in Section 10. |
| No repository-persistent restart point existed for a connection interruption. | Added the user-story ledger in Section 9.3 with status, references and exact next action. |
| “Best in class” was not operationally measurable. | Converted to explicit contract, type-safety, server-truth, security, accessibility, compatibility, test and evidence obligations in Section 9.2. |
| Frozen components and unresolved downstream authority could be confused as one implementation authorization. | Record Control, Sections 2 and 7 now authorize frozen work while blocking conflict-dependent downstream behavior. |
| Trial/Hire consistency could accidentally cause Trial coupon or Razorpay mutation. | R051-R054 and Section 5.2 explicitly require read-only presentation and negative provider/coupon effects. |
| Zero-price Hire could be falsely reported as a provider payment. | R058 requires no provider order/event and a distinct independently verifiable zero-price outcome. |
| Future agents could bypass these decisions as UI-only preferences. | R048 and R059 make the frozen contracts mandatory constitutional-compliance and change-impact gates. |
| Mainline application pages supported authenticated-unregistered views, but the shared layout redirected to Registration before they could render. | Repaired in the authorized source slice; an authored layout test proves the basic shell receives no membership projection. Docker execution remains deferred by Section 9.1. |
| Mainline Logout emitted `LOGOUT_COMPLETION` before redirecting to Keycloak. | Removed the false completion event and authored a regression assertion; authoritative provider-return completion remains WC112-RG08 work. |
| Mainline Switch Account hard-coded Google after revocation. | Repaired to clear/revoke the prior session and return to explicit Login provider selection; provider commands enforce account selection where supported. |
| Trial/Hire-triggered Registration had no server-held continuation, and the current Hire path collected payment before exact contract acceptance. | Implemented an identity-bound Acquisition Intent, exact Agent + Version Employment Contract projection/hash/acceptance, safe Registration resume and immutable relationship transfer before checkout completion. |
| Implementation review found a completed Acquisition Intent could be rebound when the same external subject selected a different customer workspace. | Added tenant and participant conflict rejection before replay or mutation, with a regression test proving the original relationship remains isolated. |
| `DEMO100` was bound to legacy shorthand `DMA`, while the admitted marketplace identifier is `DIGITAL_MARKETING_LOCAL_SERVICE`; the legacy coupon column was also too narrow. | Expanded the governed identifier column, bound `DEMO100` to the canonical Professional + Version, enabled the Founder-approved 100% cap only in local/Demo/UAT configuration and added direct validation. |
| The persisted Employment Contract URI omitted `disclosureRevision`, so replaying the exact stored URI could return Not Found. | Added the disclosure revision to both pre-Registration and registered intent URIs and asserted the immutable URI binding. |
| A generic Marketplace card displayed Hire coupon/payment controls before the customer chose Trial, contradicting the common mode-specific checkout contract. | Added an explicit Trial/Hire mode-selection state; Trial now enters a checkout with read-only coupon and Razorpay controls before acceptance. |
| Coupon and Trial eligibility checks were database-unique but did not serialize concurrent capacity decisions into deterministic customer outcomes. | Added PostgreSQL coupon row locking, stable reservation expiry, deterministic Trial unique-conflict handling and real concurrent PostgreSQL tests. |

**Author-review result:** contract review and implementation author review are complete for the
authorized slice. Focused Docker evidence passes Business Platform 42 tests, Billing/Trial 108 tests,
Web 87 tests, Hire preview 2 tests, PostgreSQL Trial concurrency 3 tests, PostgreSQL coupon concurrency
1 test, Business Platform PostgreSQL integration 1 test, TypeScript quality, fresh database
initialization/grants and migrations 48-52 replay. Trial owner failure no longer creates an Employment
Relationship; Hire creates one only after captured or zero-price commercial satisfaction. A03 remains
blocked by RG08; H04 and behavior dependent on RG04-RG05 or RG09-RG12 remain blocked and cannot be
represented as implemented or complete. The next action is the full Docker commit gate; the Founder
directed that no separate qualification run is required before the PR.

# WC-034 F2 Identity and Registration Contract

**Document type:** Canonical Component, API, Data, Error, and Integration Contract
**Owning office:** INST-005 — Solution Architect
**Security consultation:** INST-007 — CONCUR WITH BLOCKERS, 2026-08-09
**Work Contract:** WC-034 / IB-014 / F2 only
**Status:** WC-077 ACCEPTED FOR IMPLEMENTATION 2026-08-29; ENVIRONMENT GATES REMAIN INDEPENDENT
**Canonical API:** `architecture/reference/api-specs/business-platform.openapi.yaml`
**Normative parents:** ADR-002, ADR-003, ADR-008, ADR-017, ADR-023, `ae01-security-contract.md`, `hybrid-application-shell.md`, `hybrid-ui-acceptance-contract.md`
**Explicit exclusions:** F3–F8, active Employment Relationship creation, payment, private endpoints, application code, deployment

**WC-085 controlling repair (2026-09-09):** EA INST-004, bounded Solution authorship under
current Founder standing edit authority, not INST-005/INST-007 concurrence or a general review.
ADR-003's customer lookup amendment and ADR-008 Amendment 3 now control. Section 5.0 below
supersedes Sections 5.1-5.4 in full; those sections are historical publication/recovery design.
Sections 8.4, 11.1 and 14.1 are reconciled below. No Java, runtime Keycloak writer, publication
state machine, app JWT or new service. C-032 is explicitly amended; C-026 RLS remains mandatory.
The old Sections 15-16 re-review workflow does not request a new review for this bounded repair;
parent implementation proceeds under standing authority, with physical Data and evidence gates.

**Earlier WC-085 amendment (superseded where stated above):** INST-005 authors Sections 5.1-5.4, 8.4,
11.1, and 14.1 under the Founder's contract-repair assignment. These specify the Google-only
provisioning behavior, not implementation completion or Data/Security concurrence. They supersede
earlier text only for completion, recovery, and session entry. The private operations below are
logical BP adapters to existing Keycloak interfaces, not new services or browser/public endpoints.
CB-009 remains OPEN for the exact physical Data and Security decisions in Section 5.4.
Facebook/email activation remains deferred for WC-085. No ADR, infrastructure, or deployment
authority is changed.

## 1. Outcome and Invariants

F2 lets a person register with confirmed email, enter and explore without mandatory mobile verification, sign in through an approved Keycloak-brokered path, progressively verify mobile before a consequential action, link an existing WhatsApp identity to the web account without duplication, and safely resume the authorized application context.

The following invariants are mandatory:

1. Keycloak is the only web credential authority. WAOOAW applications never verify passwords or call Google, Meta, or Apple identity APIs directly.
2. ADR-023 is the authority for Meta-verified WhatsApp identity. A WhatsApp session token is not a Keycloak session and cannot become one without a Keycloak round trip.
3. A complete basic customer account requires confirmed email. Mobile verification is optional during registration and must be completed before hiring, WhatsApp connection, payment, recovery activation, sensitive account changes, or another server-classified consequential action.
4. Registration collects no more than display name, confirmed email, optional verified mobile, business name, business domain, and confirmed language preference. Language is presentation preference, not an additional identity field.
5. Registration does not create an Employment Relationship, contract, payment intent, professional authority, or trial entitlement.
6. Duplicate detection is server-side and proof-gated. No public operation answers whether an arbitrary email or mobile exists.
7. For WC-085, tenant identity is BP-minted and sourced only from current authoritative membership keyed by validated Keycloak issuer/subject. A JWT tenant claim, request body, query, URL, browser store, header or provider callback cannot select it. Other identity paths retain their separate contracts.
8. Every retryable mutation uses an idempotency key and canonical request hash. Same key and same hash replays the prior outcome; same key and different hash returns `IDENTITY_IDEMPOTENCY_CONFLICT` with zero mutation.
9. Errors are privacy-safe and anti-enumerating. They contain no email, mobile, tenant, provider token, one-time code, account-existence fact, or relationship identifier.
10. No authenticated payload, token, verification proof, or protected draft is stored by the service worker.

## 2. Component Ownership

| Boundary | Owns | Must not own |
|---|---|---|
| **Keycloak** | Web credential verification; Google, approved Meta, Apple, and approved email fallback flows; provider subject binding; MFA/authentication flow; session and assurance claims | Customer account truth; tenant minting; WhatsApp identity; duplicate resolution; return-target authorization; application drafts |
| **Identity Boundary** | Registration workflow; normalized identity keys; verified-email/mobile status; deterministic candidate resolution; link challenge and proof; account-switch cleanup policy; identity idempotency ledger | Provider passwords; raw provider tokens; Employment Relationships; professional authority; customer-facing private API |
| **Phone Identity Service** | ADR-023 webhook validation; Meta phone proof; message replay protection; short-lived internal WhatsApp session; fresh post-link Meta confirmation | Keycloak sessions; web credentials; arbitrary phone-number claims from a browser; Employment Relationships |
| **Business Platform** | Sole public F2 REST facade; authenticated/pre-account orchestration; tenant/account minting; authorization and assurance enforcement; privacy-safe errors; audit correlation | Credential verification; browser-only authorization; direct identity-provider integration; professional execution |
| **Next.js web application** | Dedicated login/register/verify/link/error routes; server-owned Keycloak session exchange; safe return-target resolution; generated BP client use; non-secret draft preservation and cleanup | Hand-written identity endpoints; credential verification; duplicate decisions; tenant derivation; provider tokens in client code; private BP/PR/WBE URLs |

The Identity Boundary is a logical Business Platform component, not a separately exposed service. ADR-023 Phone Identity Service remains a separate internal component. No new internet-facing container or private browser endpoint is introduced.

### 2.1 Customer role and institutional separation

Customer eligibility and organization authority are distinct:

- the accepted customer realm base role `customer` permits account entry only;
- current organization roles come from durable membership; WC-085 provisions only initial `OWNER`, ignoring JWT `waooaw_roles` as authority;
- Business Platform resolves command authority from current account, membership, contract, and policy
  state on every request; customer eligibility is never sufficient for a consequential command;
- `waooaw-operator` is not a customer organization role and grants no customer command authority;
- steward and other institutional sessions are outside WC-077 and use their separately approved
  realm/client and command contracts. They are never merged into a customer JWT.

Within this component, `VIEWER` may read authorized customer projections, `MANAGER` may additionally
approve routine actions explicitly assigned to managers, and `OWNER` may perform owner-only account,
contract, hiring, authority, and channel-link decisions. Emergency Stop activation remains available
under its controlling contract and must not be delayed by ordinary role or step-up processing.

## 3. Approved Authentication Paths

| Path | Contract | F2 disposition |
|---|---|---|
| Google | Keycloak-brokered OIDC; request `openid profile email`; accept email only when the brokered claim is verified | READY subject to environment configuration evidence |
| Meta/Facebook | Keycloak-brokered OIDC; login app limited to basic login information (`email` and `public_profile`); separate app and credentials from DMA Business OAuth | DEMO ACTIVATION AUTHORIZED by WC-090; other environments remain blocked |
| Apple | Keycloak-brokered Sign in with Apple; stable provider subject is the binding key; accept a confirmed Apple private-relay email without requiring disclosure of the underlying mailbox | POLICY APPROVED by FA-035; ACTIVATION BLOCKED by G-F2-14 |
| Email fallback | Keycloak-owned email flow with confirmed email; no password or email proof enters BP or Next.js application code | READY subject to Keycloak flow evidence |
| WhatsApp native | ADR-023 Meta webhook identity; complete account remains pending until email is confirmed; mobile proof is already satisfied for later consequential actions while possession remains current | READY for contract; environment proof separately gated |

Google, Facebook, Apple, and email fallback must be designed as one `Continue with...` experience for new and returning customers. Provider activation is independent: an unavailable provider is not displayed as active until its setup and customer-safety evidence passes. Microsoft remains a compatible future Keycloak provider but is not required to close WC-034 F2.

### Meta separation rule

The customer-login Meta application and the DMA Business Manager OAuth application are separate security principals with separate client IDs, secrets, redirect URIs, consent text, and scopes. The login application must never request page, advertisement, post, contact, WhatsApp Business management, publishing, or business-activity permissions. FA-035 resolves the Founder policy decision; INST-004 must still reconcile ADR-008 before implementation begins.

### 3.1 Keycloak token and broker-identity contract

Business Platform accepts customer web/mobile tokens only when all of these conditions pass:

| Claim or validation | Contract |
|---|---|
| `iss` | Exact environment customer-realm issuer from the reviewed identity environment manifest |
| `aud` | Contains the exact Business Platform audience `waooaw-platform`; no web-client or other-service audience substitutes |
| signature/JWKS | Valid signature from the issuer's configured JWKS; unknown key refresh is bounded and fails closed |
| `sub` | Non-empty Keycloak subject; combined with Keycloak issuer for the actor/session key |
| `tenant_id` | WC-085: not required and not authority; current actor-keyed membership supplies the tenant |
| `roles` | Contains base customer eligibility; it is not organization command authority |
| `waooaw_roles` | WC-085: ignored as authority; current initial membership must be ACTIVE OWNER |
| `email_verified` | Boolean; required for `AAL2_ACCOUNT`, never inferred from a plain email claim |
| `auth_time` | Required for freshness; token issue or refresh time does not replace authentication time |
| `auth_path` | `PORTAL` or `MOBILE` for Keycloak sessions; `WHATSAPP` exists only in the internal ADR-023 session |
| broker identity | WC-085: signed stock `idp` alias plus exact-subject stock federated-identity GET at completion, per ADR-008 Amendment 3; never an invented stable-subject mapper/note or raw upstream token |

Provider binding stores the normalized provider alias and stable upstream subject as the durable
login-method key. The Keycloak issuer plus Keycloak subject remains the WAOOAW actor key. Email is a
verified contact/candidate-resolution signal and never a provider-binding key. Google uses its stable
OIDC subject, Facebook uses the stable subject returned by the isolated customer-login application,
and Apple uses its stable Sign in with Apple subject; Business Platform does not invent upstream
issuer URLs or parse provider tokens.

Rejected tokens use `401 IDENTITY_SESSION_REQUIRED`. A valid token without current account
membership, eligibility, or required assurance uses a privacy-safe `403` without revealing another account
or policy internals. Institutional-realm, wrong-environment, wrong-audience, expired, not-yet-valid,
unsigned, altered, or untrusted-key tokens are rejected before any claim is consumed.

## 4. Assurance Contract

### 4.1 Assurance levels

| Level | Evidence | Permitted F2 use |
|---|---|---|
| `AAL1_CHANNEL` | Current ADR-023 Meta-verified phone session or basic authenticated web session | Discovery and non-sensitive registration continuation only |
| `AAL2_ACCOUNT` | Keycloak portal session plus confirmed email | Routine authenticated entry, exploration, and non-consequential account use |
| `AAL3_FRESH` | Keycloak portal authentication completed within the action's server-declared freshness window and every server-required factor, including verified mobile when required, satisfied | Hiring, WhatsApp connection, payment initiation, recovery activation, sensitive account changes, existing-account link approval, account deletion initiation, authority expansion, contract acceptance, and other consequential commands |
| `AAL4_PAYMENT` | `AAL3_FRESH` plus provider-hosted payment authorization | Payment only; outside F2 implementation |

`AAL3_FRESH` means authentication age no greater than five minutes at command receipt. A command may require an even stronger factor through Keycloak policy. The server returns a `StepUpRequired` contract containing an opaque intent ID and required assurance; it does not expose policy internals.

Keycloak access tokens expire after 15 minutes and refresh eligibility after eight hours, as fixed by ADR-008. Token refresh does not satisfy freshness. WhatsApp internal session tokens expire after 30 minutes. Step-up intents and account-link challenges expire after 15 minutes, are single-use, and are bound to actor subject, intended command, and safe return target.

### 4.2 High-risk behavior

- Insufficient assurance returns `403 IDENTITY_STEP_UP_REQUIRED` with an opaque step-up intent.
- The attempted command is not executed and no business mutation occurs.
- Non-secret draft and server-authorized relationship context may survive; protected content is hidden immediately.
- Completion resumes only the bound command and safe target after server revalidation.
- A command classified as consequential returns step-up until mobile is verified; basic account entry and exploration never require mobile.
- Contract acceptance, payment, Emergency Stop release, and authority expansion remain owned by their later component contracts; F2 supplies only the reusable step-up mechanism.
- Emergency Stop activation is never delayed by F2 step-up.

## 5. Registration State Machine

```text
STARTED
  -> FEDERATED_IDENTITY_ACCEPTED | CREDENTIAL_IDENTITY_ACCEPTED | WHATSAPP_IDENTITY_ACCEPTED
  -> EMAIL_VERIFICATION_REQUIRED
  -> DUPLICATE_RESOLUTION_REQUIRED | PROFILE_COMPLETION_REQUIRED
  -> READY_TO_COMPLETE
  -> COMPLETED

Any nonterminal state -> EXPIRED | CANCELLED
```

`READY_TO_COMPLETE` requires the approved minimum profile, confirmed language, and confirmed email. Mobile may be verified during registration but is not a completion gate. `COMPLETED` atomically mints or reuses one customer account and tenant anchor. It never mints an Employment Relationship.

For WC-085, the single atomic BP commit in Section 5.0 establishes `COMPLETED` and its replay result.
No Keycloak publication or distributed transaction is required.

Provider claims are hints until validated through the Keycloak-brokered server session. A confirmed email claim, including an Apple private-relay email, may satisfy email verification. Mobile claims from Google, Meta, or Apple login do not satisfy ADR-023 mobile verification unless the approved Keycloak authentication flow provides a separately verified mobile proof. The stable provider issuer-and-subject binding, never email alone, identifies a login method.

### 5.0 Current WC-085 Completion And Membership Contract

The exact current parent contract is
[WC-085 identity decision](../product/wc085-identity-architecture-decision.md).
Only Google web start/read/profile/complete, providers, session and non-consequential entry are
enabled in the first slice. Other customer operations deny at server entry until separately adopted;
do not infer enabled authority from public schema, UI hints or OWNER. No automatic trial/payment,
subscription/employment, multi-workspace selector, role-management or additional login-method flow.

| Existing public operation | Current authority and result; shapes unchanged |
|---|---|
| `startIdentityRegistration` | Validated exact actor; returning active binding reuses the same account/tenant, never latest registration or email. A different actor matching an existing stable Google key is unresolved recovery, not automatic rebinding. |
| `getIdentityRegistration` | Actor-scoped observational read. Before commit existing pending states apply; after commit `COMPLETED` / `CONTINUE_TO_DEFAULT_TARGET`. Foreign/absent/inactive actor access is normalized `404`. |
| `completeIdentityRegistration` | Verified Google session/email, stored minimum profile/language, fresh authentication and exact server-read broker proof. In ONE PostgreSQL transaction persist/reuse account, canonical organisation, initial ACTIVE OWNER membership, actor/login/proof, registration association, fixed outcome, existing idempotency result and required evidence. Only then `200 IdentityCompletion`; no token/tenant response or extra body. |
| `getIdentitySession` | SAME still-valid Keycloak token is sufficient; resolve current membership by exact issuer/subject, return existing account reference/current roles/capabilities. No signed tenant anchor, publication status or refresh prerequisite. No membership gives privacy-safe `403`; lookup failure gives `503`, never fallback. |

Serialize competing completions on actor/provider/registration and enforce unique actor and stable
provider keys. Same key/hash replays its immutable result after access checks; different hash is
`409 IDENTITY_IDEMPOTENCY_CONFLICT` with no writes. Other keys reuse the durable association and
original outcome. Keep successful registration/account association beyond request-key/draft expiry;
no new intent table. Failed DB transaction rolls back ALL account/retry/evidence writes. A lost commit
response is unknown until actor-scoped read/retry; never compensate by deleting or reminting.
Network proof reads happen before the transaction; unavailable proof is the existing retryable `503`.
No postcommit remote step, publication intent/outbox/revisions/acknowledgements or scheduler remains.

Private broker adapter: ADR-008 Amendment 3 fixes the stock `view-users` credential, exact-user GET
and federated-identity GET, signed Google session alias and stable upstream `userId`. No runtime
Keycloak writer/admin composite, public proxy or custom Java. Returning unchanged actor entry uses
current membership; it does not call Admin REST on every protected request.

Private membership adapter: `identity.resolve_customer_membership()` on EXISTING PostgreSQL;
no arguments, read-only, zero/one `{account_id uuid, tenant_id uuid, membership_id uuid, roles text[]}`.
Each BP/CE/PR/WBE/AI receiver validates the raw caller JWT and allowed peer service independently,
sets transaction-local issuer/subject with tenant context empty, resolves via its own restricted DB
identity, then sets both tenant GUCs and checks its own resource/participant/action under C-026 RLS.
ADR-003 defines exact authentication, grants and fail-closed semantics; no BP HTTP tenant assertion,
cross-ledger SELECT or new service. Disabled/unadopted operations deny, including jobs and WSS effects.

Stable issuer/subject fixtures may qualify initial completion and return. Recreated-subject recovery
is disabled pending proof/atomic retirement/old-session denial and retained-ID concurrency evidence.
Preserve stable Google proof but do not silently reset, relink or change Keycloak persistence.
No fake historical proof from email, shared tenant or old account-only registration is admissible.

One bounded INST-006 follow-on remains: physical mapping of the reduced records, atomic transaction
and nonrecursive actor-scoped lookup/RLS/grants in the Data amendment. No Security/general review
loop or new Founder technical decision is requested; implementation and evidence are not claimed.

### 5.1 Historical Publication Design - Superseded By Section 5.0

Capability: basic customer registration and authenticated entry under ADR-003/ADR-008 and
WC-085 Sections 17.1-17.2. BP alone mints account and tenant UUIDs. One independently registering
Google identity receives one account, one distinct initial tenant, and an active `OWNER` membership.
Reusing the same proven login identity reuses those bindings; neither a new registration nor a new
idempotency key creates another tenant. This grants no employment, payment, subscription, or spend
authority. Multiple-organization selection is not introduced.

| Existing operation | Inputs and authoritative behavior | Output and retry |
|---|---|---|
| `startIdentityRegistration` | Existing language/profile-independent request, idempotency key, and validated pre-account session. Derive issuer, subject, broker identity and verified-email fact server-side. Resolve the exact active actor binding first, then the proven stable login-method binding; never select by email. | Existing registration projection and start status. A returning binding resumes its original provisioning operation or a caller-bound continuation of the same account/tenant. New keys do not mint accounts. Unbound callers follow existing profile/duplicate resolution. |
| `getIdentityRegistration` | Existing registration ID plus exact validated actor binding. Read only; do not publish on GET. | Pending commit/publication projects `READY_TO_COMPLETE` / `COMPLETE_REGISTRATION`; acknowledged publication projects `COMPLETED` / `CONTINUE_TO_DEFAULT_TARGET`. No internal provisioning fields or tenant ID are added. Foreign, retired-actor, or absent registration uses normalized `404 IDENTITY_RESOURCE_NOT_ACCESSIBLE`. |
| `completeIdentityRegistration` | Existing registration ID, idempotency key, canonical semantic request hash, and actor-bound session; no new request body. Require verified email, minimum profile/language, unresolved-duplicate absence, live binding, and current account/tenant/membership eligibility. | `200 IdentityCompletion` only after the BP commit and verified publication. Until then, `503 IDENTITY_DEPENDENCY_UNAVAILABLE` with `retryAfterSeconds`; existing `409` conflict/duplicate and `422` verification errors remain. The response contains no tenant ID or token. |
| `getIdentitySession` | Validated renewed post-account JWT with `tenant_id`, issuer/subject, base role and organization roles. Load the bound account and current membership within the claim-selected tenant; never discover a replacement tenant for this request. | Existing session projection only if actor, account, tenant and current membership agree. Missing tenant or inactive/mismatched authority fails closed under Sections 3.1/7.1. No latest-registration, shared-tenant or email fallback. |

Completion has two durable stages, with internal states that do not extend public enums:

1. `BP_COMMITTED`: atomically persist or reuse account, tenant, active initial membership,
  proven login-method/actor binding, registration association, immutable completion intent and
  idempotency reservation, and required evidence. The intent fixes account/tenant IDs, original
  `ACCOUNT_CREATED` or `ACCOUNT_REUSED` outcome and intended publication revision. If the transaction
  fails, none of these writes commits and no Keycloak write is attempted. Preserve the repaired
  single-transaction account/idempotency guarantee; do not reinstate separate account and retry saves.
2. `PUBLISHED`: after Section 5.2 read-back confirms the committed binding, atomically acknowledge
  publication and persist `COMPLETED` plus the successful replay body. Return that stored body.
  `defaultTarget` remains a server-authorized target identifier, not permission to enter it.

Serialize competing completions on the durable actor/login binding and registration, not only the
request key. Identical contenders converge on the same intent; divergent identity claims enter
duplicate resolution without mutation. A caller retry after commit resumes publication, never mints
again. Pending `503` responses are not terminal replay results: the same key/hash may later yield
the fixed `200` result. Different hash always returns `409 IDENTITY_IDEMPOTENCY_CONFLICT`.
Different keys reuse the same committed binding; successful same-key replay preserves the original
outcome/body, subject to current actor/resource access checks. A removed membership never regains
access through replay. Inaccessible completion resources use the existing normalized `404`.

Precommit expired/cancelled registrations cannot complete (`404` inaccessible); committed intents
survive registration expiry and the 24-hour request-key retention window. Resume through a fresh
actor-bound registration using the same proven login identity, without a new tenant. Profile and
proof mutations cannot change a committed completion snapshot. No expiry job may delete a pending
intent or its bindings as ordinary abandoned registration data.

### 5.2 Private committed-binding publication and recovery

These are BP-owned logical service operations, not additions to the public OpenAPI. Use the
existing customer realm and stock Keycloak interfaces; no custom provider, new worker service,
infrastructure, realm-admin credential reuse, or direct Google call is authorized.

| Operation | Input | Output / failure semantics |
|---|---|---|
| `readBrokerBinding` | Validated customer issuer, Keycloak subject, signed allowlisted broker alias, correlation ID; no browser-selected user or email search | Read stock `GET /admin/realms/{realm}/users/{subject}/federated-identity` for that exact authenticated subject. Match exactly one configured alias and return its stable upstream subject and alias-specific provider trust namespace. WC-090 permits `google` and `facebook` in Demo only; unconfigured aliases and cross-alias bindings fail closed. Missing/ambiguous/conflicting proof is unresolved; do not bind, mint or relink. This server-verified broker record may supply the normalized broker identity required by Section 3.1 when stock token mappers cannot expose it; it does not supply tenant authority to protected requests. |
| `publishCommittedBinding` | Durable provisioning intent ID, expected revision, correlation ID. Reload committed BP data; caller does not supply attributes. | Target exact bound customer-realm user via stock `GET` / `PUT /admin/realms/{realm}/users/{subject}`. Publish only BP-owned `tenant_id`, `waooaw_roles`, and `org_name` user attributes from the committed tenant/membership/profile. Existing reviewed mappers emit like-named JWT claims; any emitted `organisation_id` must equal `tenant_id`. Read back the exact values before returning `APPLIED` or `ALREADY_APPLIED`. |
| `reconcileCommittedBinding` | Intent ID, expected revision, correlation ID from completion retry or BP's existing execution lifecycle | Read current BP binding/eligibility and actual Keycloak values first. Equal values acknowledge; missing or older BP-owned values on the same proven user are idempotently repaired. Return `RETRYABLE_UNAVAILABLE`, `BINDING_CONFLICT`, or `INELIGIBLE` otherwise. No tenant minting, credential changes, or browser-selected target. |

Publication does not set realm roles, credentials, broker links, assurance, email verification,
plan/subscription attributes or institutional authority. Preserve unrelated user attributes on the
stock user update. Serialize BP-owned publications per actor and fence obsolete revisions at BP;
an older retry must never overwrite a newer desired binding. Re-read eligibility and revision before
acknowledgement. Current DB membership checks deny access even if a stale token or remote write
exists. Unexpected foreign tenant attributes or changed broker binding produce `BINDING_CONFLICT`,
not an overwrite or automatic merge.

Network timeout, Keycloak outage/429/5xx, or read-back uncertainty leaves `BP_COMMITTED` and returns
the existing public `503`; use a bounded request attempt and advertise a retry delay. If the remote
write succeeded but its response or BP acknowledgement was lost, the next attempt reads and
acknowledges it without duplicate effects. Publication authentication/permission failure is not a
reason to escalate privileges: keep pending, emit privacy-safe operator evidence, and block readiness.
`BINDING_CONFLICT` maps to `409 DUPLICATE_RESOLUTION_REQUIRED`; `INELIGIBLE` maps to normalized `404`.
Unbound/missing recreated Keycloak users remain unavailable until Section 5.3 continuity is resolved.
Never compensate a publication outage by deleting the committed customer or minting another tenant.
GET is observational; retries of existing start/complete operations provide customer-driven recovery
even without a background facility. Do not introduce a scheduler merely to close this contract.

### 5.3 Stock disposable Keycloak continuity

Stable login identity is the configured provider trust namespace plus broker alias plus upstream
subject, not email and not the disposable Keycloak UUID. Ordinary return with the same live actor
reuses its account/tenant; absent claims require the existing registration continuation, publication
and renewal, not a protected-request tenant lookup. If a token has a wrong/nonmatching tenant,
deny protected entry; never silently substitute one from BP.

When Keycloak is recreated but BP survives, a newly validated configured-provider login may recover the same
login-method binding only after `readBrokerBinding` proves exactly the stored provider namespace,
alias and upstream subject. Require fresh Keycloak authentication under the five-minute window
without treating that alone as `AAL3_FRESH`. Atomically retire the old actor binding, bind the new
issuer/subject to the same account/tenant/membership and durable login method, and create a new
publication revision. Old actor sessions and actor-bound challenges cannot operate afterward.
Both actor uniqueness and login-method uniqueness must hold under concurrent recovery. A new
provider namespace, ambiguous match, absent historical subject proof, email equality alone, or
conflicting current actor binding cannot use this path; return unresolved duplicate/recovery state.
This is re-establishing the same proven login method, not attaching an additional login method.

Bounded fallback for disposable Demo: if stock Keycloak cannot supply the approved proof or narrow
publication permissions, qualification remains blocked. A joint reset is permissible only for the
two explicitly approved synthetic test customers, with an enumerated Data-owned dependency set,
Founder-approved destructive scope, and no retained customer, ledger, job, billing, file or AI state
that could become orphaned or reachable from new tenants. Reset Keycloak plus the corresponding BP
and downstream synthetic identity/data set together; invalidate sessions and discard test drafts.
New IDs after that reset are a new fixture generation, not evidence of returning-account continuity.
Never reset BP implicitly on Keycloak startup, erase real customer state, or claim a reset proves
preserved-data recovery. This contract does not execute or authorize a destructive reset.

### 5.4 Exact remaining Data and Security decisions

INST-005 has authored the operation/state/data-shape semantics above. No further general owner
review chain is requested. CB-009 stays OPEN until the following two bounded authorship decisions
are recorded against this revision; implementation and real Google evidence remain distinct gates.

| Office | One bounded authoring decision required | Acceptance floor |
|---|---|---|
| Data Architect | Map Section 8.4 to existing account/tenant/membership ownership and physical schema: keys/FKs, uniqueness, transaction/locking and revision fencing, actor-scoped pre-account access versus tenant RLS, recovery retention, and additive legacy migration/backfill or approved synthetic reset dependency set. | Actual application-role rollback, concurrency, cross-tenant and pooled-connection tests; no RLS bypass or fabricated historical provider binding. Existing account-only records retain IDs only with proven ownership; unresolved rows deny protected entry. Existing images that can create account-only completions must not serve the qualified journey after activation. |
| Security Architect | Specify the exact stock-Keycloak service principal, credential acquisition/reference, permitted user/broker read and attribute-write endpoints, realm/user/attribute scope, user-profile edit restrictions, trusted broker proof/namespace, mapper configuration, session validation and retired-actor controls. | Demonstrate denied cross-realm, credential/role/broker-link/unrelated-attribute mutation and user/browser edits. Do not grant broad `realm-admin` or assume `manage-users` is attribute-scoped. If the pinned stock release cannot enforce the required narrow grants, record the concrete permission conflict and block publication; no silent privilege expansion, custom plugin or new proxy service. |

No change to ADR-003 or ADR-008 is needed for these logical operations. The stock Admin API's
actual permission granularity remains a concrete unresolved constraint, not an asserted capability.
Security must establish whether it can meet the above boundary; a joint data reset does not solve
insufficient publication permissions.

## 6. Deterministic Duplicate Resolution and Linking

### 6.1 Normalized keys

- Email match key: canonicalized mailbox value transformed to a keyed, versioned HMAC. Provider-specific alias rewriting is prohibited.
- Mobile match key: canonical E.164 number transformed to a separate keyed, versioned HMAC.
- Raw email and mobile are encrypted customer payload. Match keys are never returned to the browser, URLs, logs, analytics, or telemetry.
- Provider subject key: configured provider trust namespace plus broker alias plus stable upstream
  subject (Sections 3.1/5.3). Actor key is separately Keycloak issuer plus Keycloak subject. Neither
  key is an email address or an upstream provider token.

### 6.2 Resolution matrix

Resolution runs only after the caller proves control of the identity being attached. Matching email is a candidate signal, never sufficient authority to link accounts.

| Verified match result | Deterministic outcome |
|---|---|
| No account matches either key | Continue profile completion and mint one account on completion |
| Both keys resolve to the same account | Reuse that account; bind the new Keycloak subject if not already bound |
| One key resolves to one account and the other is unused | Require `AAL3_FRESH`, explicit link approval, then attach the unused identity |
| Email and mobile resolve to different accounts | Return `DUPLICATE_RESOLUTION_REQUIRED`; freeze automatic completion; require authenticated recovery for both accounts or named support adjudication; never auto-merge |
| Provider subject is already bound to another account | Return `DUPLICATE_RESOLUTION_REQUIRED`; no rebinding or existence detail |
| Verified WhatsApp identity resolves to an existing account | Issue a single-use link challenge; do not mint another customer |

There is no `/duplicate-check` endpoint. The public contract exposes only the next required registration action after proof. This keeps duplicate resolution deterministic without creating an account-enumeration oracle.

### 6.3 WhatsApp-to-web linking

1. The portal actor holds a valid Keycloak session and completes `AAL3_FRESH` step-up.
2. BP starts a link challenge using an opaque verified-mobile proof or a server-selected pending WhatsApp identity. The browser never submits a raw mobile as authority.
3. BP returns an opaque challenge ID, masked destination, expiry, and next action.
4. The customer explicitly approves the link in the portal.
5. The next inbound WhatsApp message is freshly validated by ADR-023 HMAC, timestamp, and message-ID replay controls and confirms the challenge.
6. The Identity Boundary atomically binds the Keycloak subject and WhatsApp identity to one account, records correlation, invalidates the challenge, and returns the existing account.

Changed or unknown phone possession may begin a separate evaluation path but cannot attach to an existing account. Automatic account merge is prohibited.

### 6.4 Login-method linking and removal

Adding Google, Facebook, Apple, or email fallback to an existing account requires `AAL3_FRESH`, proof of the current account, and proof of the new login method. The same email on two providers never auto-links them. Responses and timing do not reveal whether the new method is already attached elsewhere. Removing a login method requires fresh authentication and is denied when it would leave the customer without at least one usable login or recovery path.

## 7. Canonical Public API

The normative HTTP details and generated models are in `business-platform.openapi.yaml`. All mutation operations require `Idempotency-Key`; same-key replay behavior is uniform.

| Operation | Purpose | Authentication |
|---|---|---|
| `GET /api/v1/identity/providers` | Return the ordered Google, Facebook, Apple, and email choices with environment readiness; disabled choices disclose only a generic unavailable reason | Anonymous; configuration projection only |
| `GET /api/v1/identity/session` | Return the caller's opaque account reference, assurance, current customer roles/capabilities, authentication path, and next required action | Post-account Keycloak bearer with `AAL2_ACCOUNT` |
| `POST /api/v1/identity/registrations` | Start or replay web registration from a Keycloak broker session | Pre-account Keycloak bearer; provider path is derived from the server session |
| `GET /api/v1/identity/registrations/{registrationId}` | Read the caller-bound registration projection | Same actor-bound pre-account session |
| `PUT /api/v1/identity/registrations/{registrationId}/profile` | Set only approved minimum profile fields | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/email-verifications` | Start or replay an email challenge when no verified broker claim exists | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/email-verifications/confirm` | Confirm an opaque challenge with a one-time code | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/mobile-verifications` | Optionally start or replay approved mobile proof during registration | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/mobile-verifications/confirm` | Confirm optional OTP/mobile proof during registration | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/complete` | Resolve duplicate state and atomically mint or reuse one account | Confirmed email required; mobile optional |
| `POST /api/v1/identity/mobile-verifications` | Start or replay progressive mobile proof for an authenticated account | Portal session; returned challenge discloses no account-existence fact |
| `POST /api/v1/identity/mobile-verifications/confirm` | Confirm progressive mobile proof before a consequential action | Same authenticated account; idempotent and proof-gated |
| `POST /api/v1/identity/account-links` | Start or replay a WhatsApp-to-web link challenge | `AAL3_FRESH` portal session |
| `POST /api/v1/identity/account-links/{linkId}/approve` | Record explicit portal approval | Same `AAL3_FRESH` actor |
| `GET /api/v1/identity/account-links/{linkId}` | Read caller-bound link status after fresh Meta confirmation | Same portal actor |

No API accepts `tenantId`, raw provider access token, password, upstream provider authorization code, relationship ID, or return URL in a request body. Keycloak protocol endpoints and callbacks remain Keycloak/Next.js session-boundary concerns and are not re-exposed as BP convenience endpoints.

### 7.1 Identity endpoint authorization matrix

| Operations | Required context | Role and assurance |
|---|---|---|
| provider readiness | Anonymous | No role; static reviewed environment projection only |
| registration read/mutations | Actor-bound pre-account Keycloak token | `AAL1_CHANNEL`; no tenant claim required; all resources bound to issuer and subject |
| session projection and authenticated mobile-verification start/confirm | Post-account Keycloak token and current membership | Any current customer organization role; `AAL2_ACCOUNT` |
| account-link start/approve/read | Post-account Keycloak token and current membership | `OWNER`; `AAL3_FRESH` and verified mobile |

Authorization is deny-by-default. Business Platform validates the token, derives tenant, activates
RLS, loads current membership and command policy, and then checks assurance. The session projection's
`capabilities` are server-derived current values, not copied from JWT claims. A stale or removed role
cannot retain authority until token expiry. Identity operations never grant institutional authority.

### 7.2 Phone Identity internal adapter

The separate ADR-023 Phone Identity Service owns the public Meta webhook verification boundary and
calls the logical Identity Boundary through a private authenticated adapter. The adapter accepts only
an opaque proof record containing a keyed phone HMAC, Meta message ID, proof time, proof expiry,
`AAL1_CHANNEL`, and correlation ID. It does not accept a browser-supplied phone number, raw webhook,
Meta token, or Phone Identity session token as public authority.

The adapter returns one of `CONTINUE_REGISTRATION`, `ACCOUNT_LINK_CONFIRMATION_REQUIRED`,
`ACCOUNT_LINKED`, `DUPLICATE_RESOLUTION_REQUIRED`, or `NO_CHANGE`, with opaque registration/link/account
references and the next action. Same message ID and same proof replay the prior outcome; conflicting
reuse fails unresolved. Invalid HMAC, stale timestamp, unknown signer, expired proof, ambiguous
identity, suspended account, database failure, or evidence failure performs no account/link mutation.
Transient failure returns an internal unavailable result so Meta retry remains safe. The internal
30-minute session never crosses to web/mobile and cannot be exchanged for a Keycloak token.

### 7.3 Environment configuration and reconciliation contract

One strict schema controls Demo, UAT, and Production. Each reviewed manifest contains:

- environment and schema version;
- public web, API, and identity origins;
- exact customer-realm issuer, audience, JWKS URI, realm name, token lifetimes, and clock skew;
- separate web and mobile public-client IDs, exact redirect and post-logout URI arrays, allowed web
  origins, PKCE requirement, and permitted scopes;
- ordered provider IDs, enabled state, broker alias, exact permitted scopes, secret-reference names,
  and accepted readiness-evidence references;
- identity-edge image/policy references, Keycloak image/normalized-realm references, cookie policy,
  Phone Identity internal audience, and channel enablement;
- no institutional client values in this customer identity manifest.

Unknown fields, duplicate provider aliases, literal secret-like values, wildcard redirects, HTTP
outside local Docker, callback hosts outside the named environment, issuer/JWKS mismatch, missing
secret references, unapproved scope, enabled provider without accepted readiness, or an unpinned
dependency fails validation. Demo/UAT/Production values are separate; promotion copies schema and
allowlisted non-secret meaning only, never hostnames, identities, state coordinates, credentials, or
secret values. Keycloak is reconciled from normalized version-controlled inputs; unreviewed console
drift blocks readiness.

### 7.4 Release, compatibility, and rollback contract

`architecture/reference/pipeline/identity-dependency-manifest.md` is the normative signed dependency
manifest. Keycloak image plus normalized realm digest and identity-edge image plus route-policy digest
are dependency members bound to, but not members of, the exact-six application tuple. Schema changes
are additive and previous-image compatible; destructive down-migrations are prohibited. Rollback
selects the immediately previous qualified application, dependency, configuration, and schema-compatible
tuple without rebuild, retag, secret copying, data downgrade, or destructive migration.

## 8. Canonical Data Contracts

### 8.1 Registration projection

`IdentityRegistration` contains only:

- opaque `registrationId`;
- state and `nextAction`;
- approved authentication path and provider label;
- booleans for verified email and verified mobile;
- masked email and mobile display values when present;
- non-secret profile completion values;
- duplicate-resolution state without account-existence detail;
- expiry and last-update timestamps.

It excludes tenant ID, internal account ID before completion, match keys, provider subject, tokens, codes, assurance policy internals, and another account's attributes.

### 8.2 Completion outcome

`IdentityCompletion` contains `outcome` (`ACCOUNT_CREATED` or `ACCOUNT_REUSED`), opaque account reference for the authenticated server session, `assuranceLevel`, and `defaultTarget`. The client must render the same success treatment for both outcomes.

### 8.3 Verification and link proof

Verification challenges expose only opaque ID, purpose, masked destination, expiry, resend time, and state. Link challenges additionally expose required assurance and next action. One-time codes, provider tokens, raw phone, HMAC match keys, and internal security events are never returned.

### 8.4 Private provisioning data shapes (WC-085)

These are logical records, not table/column definitions or migration authorization. All identifiers
below are private except the existing public registration/account references.

| Shape | Required facts and invariants |
|---|---|
| Customer account | BP account UUID, active/inactive status; registration is workflow history, not account truth. |
| Tenant | BP tenant UUID, organization display name, active/inactive status; never a shared Demo constant. |
| Membership | Account UUID, tenant UUID, current role and active/inactive status; one initial active `OWNER` binding per independently created tenant. No publication revision. |
| Login-method binding | Configured provider trust namespace, broker alias, stable upstream subject, account UUID, proof provenance and active/retired status; one stable login key cannot own two accounts. |
| Actor binding and proof | Exact Keycloak issuer/subject, login-method and account references, active/retired status, proof source/time/authentication time/trust-config digest; one actor cannot map to multiple accounts. Retired IDs cannot be recycled. No separate proof table required. |
| Existing completed registration | Durable actor/account association, immutable outcome and accepted profile snapshot; no separate completion intent/state table. Survives draft/key expiry. |
| Existing idempotency ledger and evidence | Exact actor issuer/subject, family/key/hash, registration association and terminal HTTP/body result in the SAME completion transaction, with minimal append-only event. Retain replay at least 24 hours; permanent actor/login uniqueness prevents reminting after expiry. |

Actor recovery is a future gate and cannot use old actor-scoped request keys as authority.
Historical registration `AccountId` alone is
insufficient proof for migration: do not infer tenant membership from a shared mapper, email match,
last-updated registration, or browser state. Data owns the physical translation and privacy-safe
retention; Section 5.0 and the Data amendment define the bounded physical author follow-on.

## 9. Error Contract

Every F2 error uses RFC 9457 `IdentityProblemDetail` with stable `code`, HTTP `status`, opaque `correlationId`, optional `retryAfterSeconds`, and optional opaque `stepUpIntentId`. `detail` is safe display text and never carries existence or policy internals.

| HTTP | Code | Meaning and required behavior |
|---|---|---|
| 400 | `IDENTITY_REQUEST_INVALID` | Malformed or unsupported input; no secret echoed |
| 401 | `IDENTITY_SESSION_REQUIRED` | Missing, invalid, or expired actor session; protected content hidden |
| 403 | `IDENTITY_STEP_UP_REQUIRED` | Stronger/fresher Keycloak assurance required; bound intent supplied |
| 403 | `IDENTITY_ACTION_DENIED` | Caller cannot perform operation; no account existence disclosed |
| 409 | `IDENTITY_IDEMPOTENCY_CONFLICT` | Same key with a different canonical request hash; zero mutation |
| 409 | `DUPLICATE_RESOLUTION_REQUIRED` | Automatic completion/linking is unsafe; no conflicting account detail |
| 410 | `IDENTITY_CHALLENGE_EXPIRED` | Challenge cannot be reused; restarting does not disclose existence |
| 404 | `IDENTITY_RESOURCE_NOT_ACCESSIBLE` | Resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class |
| 422 | `IDENTITY_VERIFICATION_REQUIRED` | Confirmed email, required mobile proof for a consequential action, or another required factor remains incomplete |
| 429 | `IDENTITY_RATE_LIMITED` | Retry delay supplied; response remains normalized |
| 503 | `IDENTITY_DEPENDENCY_UNAVAILABLE` | Keycloak, channel proof, or evidence dependency unavailable; outcome remains unresolved |

Existing and non-existing email/mobile inputs produce the same accepted challenge response shape, status, and externally observable timing class. Invalid, expired, already-used, and non-existent verification codes produce the same normalized failure. Rate limits apply per opaque registration, normalized identity key, and abuse context without exposing which threshold fired.

Cross-tenant and inaccessible identity resources use the same `404` not-accessible response shape. They do not use a distinguishable `403` that reveals existence.

## 10. Idempotency, Retry, and Failure Semantics

- `Idempotency-Key` is a client-generated UUID, scoped to authenticated/pre-account actor plus operation family, retained for at least 24 hours.
- Canonical request hash excludes transport metadata but includes every semantic input.
- Successful and accepted asynchronous outcomes are replayable with their original status and body.
- A timeout or disconnected browser remains `UNKNOWN`; the web reads registration/link status before retrying.
- Verification resend under the same key returns the existing active challenge. A new key before `resendAfter` returns `IDENTITY_RATE_LIMITED`.
- Dependency failure never produces a false successful completion, link, or consumed proof. Failure
  before the atomic BP completion commit mints nothing; after an uncertain commit response,
  actor-scoped read/retry resolves the committed result. There is no pending publication state.
- Concurrent completion commands serialize on normalized identity keys. One commits; identical contenders replay; divergent contenders enter duplicate resolution.
- ADR-023 message-ID deduplication remains 24 hours and precedes link confirmation.

## 11. Session, Return Target, Sign-Out, and Account Switch

### 11.1 WC-085 completion-to-session handoff

**Current contract:** completion commits membership, not new token claims. Use the SAME still-valid
Keycloak token with `getIdentitySession`; require the returned account reference to match the
server-held completion account and unchanged originating issuer/subject before protected navigation.
Normal expiry refresh/one PKCE round trip, token validation, no-store/CSRF and switch cleanup remain;
never refresh just to acquire tenant/role claims. Failed session lookup does not undo the committed
account. Existing public shapes stay unchanged; adopt BP membership resolution and web handoff
together. Old account-only writers cannot serve the qualified journey. Unadopted downstream paths
deny until their independent receiver checks are implemented.

**Historical handoff below is superseded in full:** its mandatory renewal, claim-selected tenant,
replacement mapper and tenantless-token rejection are NOT requirements of the current slice.

Completion `200` or a `COMPLETED` registration is not a refreshed session. If resuming from a
registration GET without an account reference, call the existing idempotent completion operation
to obtain it. The Next.js server session boundary retains that opaque expected account reference
and originating issuer/subject, then performs one Keycloak refresh-token exchange when a valid
server-managed refresh token is available. The existing auth callback retains only an access token;
implementation must add renewal/token replacement within the existing auth/session boundary or
use the OIDC round trip below, not assume refresh already exists. It validates the new
token under Section 3.1 before replacing server token state; no browser-supplied tenant/account/role
or application-minted access token is permitted. `assuranceLevel` in the completion response cannot
upgrade the old token. Access/refresh tokens stay within the existing server-session boundary.

If refresh is expired, rejected, or still lacks a valid tenant/role, use one normal Keycloak OIDC
authorization-code/PKCE round trip with server-held state/nonce and the existing callback. There is
no unbounded refresh/redirect loop. If still unresolved, stay outside protected routes with a
retryable sign-in/registration failure; do not navigate to `/home` or fetch protected data.
Changed issuer/subject during this completion handoff cancels it and uses clean account-switch
handling; recreated-actor recovery must first establish a fresh Section 5.3 continuation.

With the renewed JWT, call existing `GET /api/v1/identity/session`. BP must compare its claim-selected
tenant and issuer/subject against active durable account/membership state and return the existing
account reference, current roles and capabilities. The Next.js server requires that reference to
equal the completion continuation's expected reference before resolving `defaultTarget`. Failure,
mismatch, or revoked membership clears protected state and denies entry; no fallback tenant lookup.
`GET /registrations` next action `CONTINUE_TO_DEFAULT_TARGET` means perform this handoff, not skip it.
Transient post-publication session failure does not roll back or recreate the BP customer.

Existing OpenAPI request/response shapes, status codes and enums remain unchanged; no new endpoint
is needed. Older clients can parse the responses but cannot qualify by navigating immediately after
completion. Activate the repaired BP, web handoff and replacement mapper together under existing
release gates, and do not roll back to an account-only writer/shared mapper against qualified data.
An older tenantless token fails closed even after a successful completion replay.

### Safe return target

The server stores a target identifier, not an arbitrary URL. Allowed targets are named application routes whose authorization is rechecked after authentication. External origins, protocol-relative values, encoded origin changes, credential-bearing URLs, Founder routes without a Founder claim, inaccessible relationships, and stale link targets are rejected. Rejection falls back to the configured default start view.

### Session expiry

Protected content is removed immediately. Non-secret drafts may remain encrypted and namespaced to account plus relationship, but are not rendered until the same account and relationship are reauthorized. One-time codes, passwords, tokens, verification proofs, and link approvals never persist.

### Sign-out and account switch

Sign-out clears the server session, browser memory, query cache, relationship cache, protected drafts according to policy, pending verification/link state, optimistic state, and account-scoped storage. Account switch performs the same cleanup before Keycloak `prompt=select_account`. Static assets and public locale/theme preferences may remain. A post-switch sentinel test must prove no prior-account text, identifiers, requests, drafts, or cache entries remain.

## 12. Privacy, Telemetry, and Tenant Isolation

- URLs and telemetry contain no email, mobile, token, code, tenant ID, provider subject, relationship ID, or evidence payload.
- Logs use opaque registration/link IDs and correlation IDs. Security analytics receive classified events, not raw identity values.
- The service worker caches static assets only. Identity API, auth callback, authenticated HTML, RSC, and protected payload responses use `no-store` and are excluded from runtime caches.
- Before account completion, access is actor-scoped. After completion, WC-085 derives tenant only from current membership keyed by validated issuer/subject; each resource owner independently resolves and enforces it through RLS.
- Provider callbacks bind to server-held state, nonce, PKCE verifier, and intended authentication transaction. Browser parameters cannot choose provider identity, tenant, or account.
- ADR-023 WhatsApp continuation invokes the logical Identity Boundary through an internal server-to-server adapter. The Phone Identity Service token is never issued to a browser and cannot self-upgrade to a Keycloak session. Web continuation requires a Keycloak round trip and proof-gated binding.

## 13. UX Acceptance Mapping

| Acceptance ID | Contract evidence |
|---|---|
| `UX-SHELL-02` | Server validates Keycloak session, tenant, participant, and relationship authorization before protected render; pre-account routes expose no relationship data |
| `UX-SHELL-04` | Named, server-owned return targets; origin and authorization revalidation; safe fallback |
| `UX-AUTH-01` | Login/register switch preserves locale and non-secret profile values only; codes, passwords, proofs, and tokens are cleared |
| `UX-AUTH-02` | Federated email accepted only from validated Keycloak session with verified claim |
| `UX-AUTH-03` | Missing/unverified provider email moves to separate challenge; completion remains blocked |
| `UX-AUTH-04` | Verified proof-gated resolution matrix and link challenge reuse the existing account; no duplicate-check endpoint |
| `UX-AUTH-05` | `IDENTITY_STEP_UP_REQUIRED`, five-minute freshness, bound intent, and safe context restoration |
| `UX-AUTH-06` | Immediate protected-content removal; same-account reauthorization before non-secret draft render |
| `UX-PRIV-01` | Prohibited URL, log, telemetry, and cache fields; opaque correlation only |
| `UX-PWA-04` | Full account-scoped cleanup plus post-switch sentinel evidence |

## 14. Required Contract and Security Evidence

1. Canonical OpenAPI validates as OpenAPI 3.1 and generates a strict TypeScript client without manual patches.
2. Generated operations contain no `tenantId` request property and no private service URL.
3. Google, Facebook, Apple private-relay email, email fallback, WhatsApp-first completion, existing-account link, split-account conflict, and same-key replay fixtures conform to the schemas.
4. Anti-enumeration tests compare status, shape, and timing class for existing/non-existing email and mobile.
5. Cross-tenant access, forged provider claims, forged return targets, expired/replayed challenge, divergent idempotency replay, assurance downgrade, stale session, and account-switch residue deterministically deny or fail unresolved.
6. Meta scope-separation evidence is mandatory before Facebook activation; Apple private-relay, stable-subject, and key-rotation evidence is mandatory before Apple activation.
7. UX-SHELL-02, UX-SHELL-04, UX-AUTH-01 through UX-AUTH-06, UX-PRIV-01, and UX-PWA-04 pass in the proportional F8 evidence for F2.

### 14.1 WC-085 provisioning acceptance checks

**Current acceptance overrides the historical table below:** run the first two-identity real-PG
check in the current WC-085 decision, including atomic account/retry rollback, concurrent retries,
tenantless-token entry, cross-tenant API/RLS denial and pooled-context isolation. Test the stock
reader's effective read scope and denied writes, actual Google session alias/subject proof, ordinary
same-actor return and account-switch cleanup. Recreated-actor recovery is NOT enabled or claimed.
Every subsequently enabled CE/PR/WBE/AI surface needs independent raw-JWT, trusted-channel, lookup
and resource-denial evidence. Disabled surfaces stay DEFERRED/DISABLED, not PASS. Existing API shapes
remain. No publication/build/renewal-claim tests from the historical table are current requirements.
Documentation checks do not establish runtime, Google, cloud or Production proof.

**Historical table, superseded by the current acceptance above:**

Run local executable checks in Docker before real Google qualification. These are required fixtures,
not claims that the amendment or previous account-only tests have passed them.

| Check | Required observable result |
|---|---|
| Two customers | Two distinct synthetic Google broker identities create different account/tenant IDs and one active initial `OWNER` membership each. Then two approved real Google test accounts independently qualify only after implementation/release gates. No shared mapper or auth-only substitute. |
| Atomicity and races | Fail the BP transaction at binding, evidence, intent and request-result persistence boundaries: no partial customer and no Keycloak call before commit. Concurrent same/different-key completion for one proven identity converges on one account/tenant/membership; different-hash key reuse gives conflict and zero mutation. Preserve the existing PostgreSQL account/idempotency rollback regression. |
| Publication recovery | Fail before write, after remote write/before response, and after read-back/before BP acknowledgement. Observe pending `503`, no false `COMPLETED`, then same-key recovery to the fixed `200` without new IDs. Exercise concurrent reconciliation, obsolete revision, denied publication privileges, foreign attributes, and Keycloak outage. |
| Replay and expiry | Resume after browser disconnect, registration expiry and request-key expiry with fresh proof. No duplicate tenant; precommit expiry cannot complete. Replayed success cannot bypass removed membership, actor retirement, or an inaccessible registration. |
| Token and browser handoff | Old/pre-account token cannot access protected API; completed registration alone cannot navigate into protected content. Renewed token must carry the committed tenant and pass the session/account comparison. Cover refresh without claims, refresh rejection, bounded OIDC fallback, wrong account, sign-out and switching with no prior-customer residue. |
| Returning/recreated actor | Same provider subject with changed email retains IDs. Same email with different subject cannot relink. Recreated Keycloak actor with exact proven stable subject reuses IDs and retires old authority, including concurrent attempts; missing proof fails unresolved. A separately approved joint synthetic reset is labelled a reset, never preserved-data continuity. |
| API and database denial | Swapped account/resource IDs, wrong/missing tenant, removed membership and reused pooled connections deny reads/writes using actual application DB roles, not superuser or RLS-bypass substitutes. Pre-account binding access is actor-scoped and cannot read arbitrary tenant rows. |
| Downstream enabled surfaces | Exercise WC-085 Section 17.2: billing/invoices/payments, agents/relationships, files/conversations/retrieval/caches, AI context, jobs/callbacks and all three ledgers. Carry trusted JWT-derived tenant/resource provenance, then check current authorization before reads/effects; body/header/resource IDs cannot replace it. Disabled families must be unreachable through UI, direct API and background work and recorded `DEFERRED/DISABLED`, never `PASS`. This is not authority to implement deferred feature families. |
| Contract compatibility | Existing completion/session/registration schemas and generated clients parse outcomes unchanged. No new tenant request input, public endpoint or completion enum. Privacy-safe errors contain no broker, tenant, token, credential or other-account detail. Old account-only writers/shared mappers cannot serve the qualified release. |

Evidence must identify exact images/configuration/schema and test fixture generation. Documentation,
local mocks, or disposable-Keycloak reconstruction alone cannot establish real Google enforcement,
platform-wide isolation, Founder acceptance, or Production readiness.

## 15. F2 Dependency Gate Table

| Gate | Dependency | Status | Owner | Missing artifact or evidence |
|---|---|---|---|---|
| `G-F2-01` | F1 experience foundation merged and approved | **READY** | INST-010 / INST-004 | None — R-052 approved and PR #246 merged |
| `G-F2-02` | ADR-008 provider policy reconciled with FA-035 | **READY — ADR-008 Amendment 1 complete (v3, 2026-08-09)** | INST-004 Enterprise Architect | None — Amendment 1 records one provider-agnostic experience, confirmed-email completion, progressive mobile verification, provider-subject binding, proof-of-control linking, non-enumerating behavior, Facebook scope isolation, and provider-specific activation gates |
| `G-F2-03` | Meta login environment prerequisites | **BLOCKED** | Founder | FA-002 Meta Business Manager verification and FA-018 login app credentials/configuration evidence |
| `G-F2-04` | Google broker path | **READY** | Keycloak/identity implementation owner | Contract fixed; environment-specific provider proof is an implementation acceptance item |
| `G-F2-05` | Approved credential path with second factor | **READY** | Keycloak/identity implementation owner | Contract fixed; realm-flow evidence required during implementation |
| `G-F2-06` | Confirmed email and progressive mobile policy | **READY** | Founder / INST-004 | FA-035 and this contract; mobile gates consequential actions, not basic entry |
| `G-F2-07` | WhatsApp identity, linking, takeover, and assurance rules | **READY** | INST-007 / ADR-023 owner | AE-01 security contract, ADR-023, and this proof-gated link contract present |
| `G-F2-08` | Canonical BP public API and generated TypeScript compatibility | **READY** | INST-005 / BP specification owner | This contract plus canonical OpenAPI F2 operations; executable generation proof remains implementation entry evidence |
| `G-F2-09` | Tenant, idempotency, retry, anti-enumeration, and privacy-safe error contracts | **READY** | INST-005 with INST-007 concurrence | This contract and canonical OpenAPI schemas present |
| `G-F2-10` | C-095 component/skeleton determination | **READY** | INST-005 / INST-004 | Identity Boundary is a logical BP component; no new deployable component; OpenAPI is the implementation skeleton |
| `G-F2-11` | F2 implementation authorization | **READY** | Founder | FA-031 and FA-034 apply when all local entry gates pass |
| `G-F2-12` | Independent architecture review | **BLOCKED** | INST-004 Enterprise Architect | Independent review record for this F2 package |
| `G-F2-13` | Deployment authorization | **BLOCKED** | Founder / release authority | Deployment authorization and release evidence; explicitly outside WC-034 F2 grooming |
| `G-F2-14` | Apple login environment prerequisites | **BLOCKED** | Founder | FA-019 Apple Developer account, Service ID, private key, relay-domain configuration, and provider acceptance evidence |

### Gate conclusion

The F2 contract package is ready for independent re-review after R-055 remediation and the ADR-008 Amendment 1. F2 implementation remains **BLOCKED** by `G-F2-12` (independent architecture re-review). Facebook activation additionally remains blocked by `G-F2-03`; Apple activation remains blocked by `G-F2-14`. Deployment remains blocked independently and is not requested by this package.

## 16. Review Request

INST-004 must review this component contract, the F2 additions to `business-platform.openapi.yaml`, and the WC-034/decomposition status updates for consistency with the reference architecture, ADR-002/003/008/017/023, ownership boundaries, and generated-client compatibility. Approval does not resolve `G-F2-02`, authorize deployment, or extend scope into F3–F8.
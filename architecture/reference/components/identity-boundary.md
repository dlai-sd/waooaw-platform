# WC-034 F2 Identity and Registration Contract

**Document type:** Canonical Component, API, Data, Error, and Integration Contract  
**Owning office:** INST-005 — Solution Architect  
**Security consultation:** INST-007 — CONCUR WITH BLOCKERS, 2026-08-09  
**Work Contract:** WC-034 / IB-014 / F2 only  
**Status:** REVIEW CANDIDATE — IMPLEMENTATION BLOCKED BY GATE TABLE  
**Canonical API:** `architecture/reference/api-specs/business-platform.openapi.yaml`  
**Normative parents:** ADR-002, ADR-003, ADR-008, ADR-017, ADR-023, `ae01-security-contract.md`, `hybrid-application-shell.md`, `hybrid-ui-acceptance-contract.md`  
**Explicit exclusions:** F3–F8, active Employment Relationship creation, payment, private endpoints, application code, deployment

## 1. Outcome and Invariants

F2 lets a person register, verify mandatory email and mobile identities, sign in through an approved Keycloak-brokered path, link an existing WhatsApp identity to the web account without duplication, and safely resume the authorized application context.

The following invariants are mandatory:

1. Keycloak is the only web credential authority. WAOOAW applications never verify passwords or call Google or Meta identity APIs directly.
2. ADR-023 is the authority for Meta-verified WhatsApp identity. A WhatsApp session token is not a Keycloak session and cannot become one without a Keycloak round trip.
3. A complete customer account requires both verified email and verified mobile. Provider identity alone is insufficient when either claim is absent or unverified.
4. Registration collects no more than display name, verified email, verified mobile, business name, business domain, and confirmed language preference. Language is presentation preference, not an additional identity field.
5. Registration does not create an Employment Relationship, contract, payment intent, professional authority, or trial entitlement.
6. Duplicate detection is server-side and proof-gated. No public operation answers whether an arbitrary email or mobile exists.
7. Tenant identity is server-minted and later sourced only from a validated session claim. It is never accepted from a request body, query, URL, browser store, or provider callback parameter.
8. Every retryable mutation uses an idempotency key and canonical request hash. Same key and same hash replays the prior outcome; same key and different hash returns `IDENTITY_IDEMPOTENCY_CONFLICT` with zero mutation.
9. Errors are privacy-safe and anti-enumerating. They contain no email, mobile, tenant, provider token, one-time code, account-existence fact, or relationship identifier.
10. No authenticated payload, token, verification proof, or protected draft is stored by the service worker.

## 2. Component Ownership

| Boundary | Owns | Must not own |
|---|---|---|
| **Keycloak** | Web credential verification; Google, approved Meta, and approved credential flows; provider subject binding; MFA/authentication flow; session and assurance claims | Customer account truth; tenant minting; WhatsApp identity; duplicate resolution; return-target authorization; application drafts |
| **Identity Boundary** | Registration workflow; normalized identity keys; verified-email/mobile status; deterministic candidate resolution; link challenge and proof; account-switch cleanup policy; identity idempotency ledger | Provider passwords; raw provider tokens; Employment Relationships; professional authority; customer-facing private API |
| **Phone Identity Service** | ADR-023 webhook validation; Meta phone proof; message replay protection; short-lived internal WhatsApp session; fresh post-link Meta confirmation | Keycloak sessions; web credentials; arbitrary phone-number claims from a browser; Employment Relationships |
| **Business Platform** | Sole public F2 REST facade; authenticated/pre-account orchestration; tenant/account minting; authorization and assurance enforcement; privacy-safe errors; audit correlation | Credential verification; browser-only authorization; direct identity-provider integration; professional execution |
| **Next.js web application** | Dedicated login/register/verify/link/error routes; server-owned Keycloak session exchange; safe return-target resolution; generated BP client use; non-secret draft preservation and cleanup | Hand-written identity endpoints; credential verification; duplicate decisions; tenant derivation; provider tokens in client code; private BP/PR/WBE URLs |

The Identity Boundary is a logical Business Platform component, not a separately exposed service. ADR-023 Phone Identity Service remains a separate internal component. No new internet-facing container or private browser endpoint is introduced.

## 3. Approved Authentication Paths

| Path | Contract | F2 disposition |
|---|---|---|
| Google | Keycloak-brokered OIDC; request `openid profile email`; accept email only when the brokered claim is verified | READY subject to environment configuration evidence |
| Meta/Facebook | Keycloak-brokered OIDC; login app limited to `openid` equivalent, `email`, and `public_profile`; separate app and credentials from DMA Business OAuth | CONTRACT READY; ACTIVATION BLOCKED by G-F2-02 and G-F2-03 |
| Approved credentials | Keycloak-owned credential flow with verified email and approved second factor; no password enters BP or Next.js application code | READY subject to Keycloak flow evidence |
| WhatsApp native | ADR-023 Meta webhook identity; complete account remains pending until mandatory email is verified | READY for contract; environment proof separately gated |

Microsoft and Apple remain compatible Keycloak providers under ADR-008 but are not required to implement or close WC-034 F2. Adding either is Keycloak configuration plus provider-specific acceptance evidence, not a new BP API.

### Meta separation rule

The customer-login Meta application and the DMA Business Manager OAuth application are separate security principals with separate client IDs, secrets, redirect URIs, consent text, and scopes. The login application must never request page, ads, WhatsApp Business management, or publishing permissions. This rule does not resolve ADR-008 v2's Meta deferral; G-F2-02 remains blocked until INST-004 records the controlling reconciliation.

## 4. Assurance Contract

### 4.1 Assurance levels

| Level | Evidence | Permitted F2 use |
|---|---|---|
| `AAL1_CHANNEL` | Current ADR-023 Meta-verified phone session or basic authenticated web session | Discovery and non-sensitive registration continuation only |
| `AAL2_ACCOUNT` | Keycloak portal session plus mandatory email and mobile verification complete | Routine authenticated application access |
| `AAL3_FRESH` | Keycloak portal authentication completed within the action's server-declared freshness window and required factor satisfied | Existing-account link approval, account recovery, account deletion initiation, authority expansion, contract acceptance, and other high-risk commands |
| `AAL4_PAYMENT` | `AAL3_FRESH` plus provider-hosted payment authorization | Payment only; outside F2 implementation |

`AAL3_FRESH` means authentication age no greater than five minutes at command receipt. A command may require an even stronger factor through Keycloak policy. The server returns a `StepUpRequired` contract containing an opaque intent ID and required assurance; it does not expose policy internals.

Keycloak access tokens expire after 15 minutes and refresh eligibility after eight hours, as fixed by ADR-008. Token refresh does not satisfy freshness. WhatsApp internal session tokens expire after 30 minutes. Step-up intents and account-link challenges expire after 15 minutes, are single-use, and are bound to actor subject, intended command, and safe return target.

### 4.2 High-risk behavior

- Insufficient assurance returns `403 IDENTITY_STEP_UP_REQUIRED` with an opaque step-up intent.
- The attempted command is not executed and no business mutation occurs.
- Non-secret draft and server-authorized relationship context may survive; protected content is hidden immediately.
- Completion resumes only the bound command and safe target after server revalidation.
- Contract acceptance, payment, Emergency Stop release, and authority expansion remain owned by their later component contracts; F2 supplies only the reusable step-up mechanism.
- Emergency Stop activation is never delayed by F2 step-up.

## 5. Registration State Machine

```text
STARTED
  -> FEDERATED_IDENTITY_ACCEPTED | CREDENTIAL_IDENTITY_ACCEPTED | WHATSAPP_IDENTITY_ACCEPTED
  -> EMAIL_VERIFICATION_REQUIRED
  -> MOBILE_VERIFICATION_REQUIRED
  -> DUPLICATE_RESOLUTION_REQUIRED | PROFILE_COMPLETION_REQUIRED
  -> READY_TO_COMPLETE
  -> COMPLETED

Any nonterminal state -> EXPIRED | CANCELLED
```

The order of email and mobile verification may vary by channel. `READY_TO_COMPLETE` requires all five approved registration details plus confirmed language and valid verified proofs. `COMPLETED` atomically mints or reuses one customer account and tenant anchor. It never mints an Employment Relationship.

Provider claims are hints until validated through the Keycloak-brokered server session. A verified email claim may satisfy email verification. Mobile claims from Google or Meta login do not satisfy ADR-023 mobile verification unless the approved Keycloak authentication flow provides a separately verified mobile proof.

## 6. Deterministic Duplicate Resolution and Linking

### 6.1 Normalized keys

- Email match key: canonicalized mailbox value transformed to a keyed, versioned HMAC. Provider-specific alias rewriting is prohibited.
- Mobile match key: canonical E.164 number transformed to a separate keyed, versioned HMAC.
- Raw email and mobile are encrypted customer payload. Match keys are never returned to the browser, URLs, logs, analytics, or telemetry.
- Provider subject key: Keycloak issuer plus broker subject, never the upstream provider token.

### 6.2 Resolution matrix

Resolution runs only after the caller proves control of the relevant email or mobile.

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

## 7. Canonical Public API

The normative HTTP details and generated models are in `business-platform.openapi.yaml`. All mutation operations require `Idempotency-Key`; same-key replay behavior is uniform.

| Operation | Purpose | Authentication |
|---|---|---|
| `POST /api/v1/identity/registrations` | Start or replay registration from a Keycloak broker session or ADR-023 continuation proof | Pre-account Keycloak bearer or approved channel continuation proof |
| `GET /api/v1/identity/registrations/{registrationId}` | Read the caller-bound registration projection | Same actor-bound pre-account session |
| `PUT /api/v1/identity/registrations/{registrationId}/profile` | Set only approved minimum profile fields | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/email-verifications` | Start or replay an email challenge when no verified broker claim exists | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/email-verifications/confirm` | Confirm an opaque challenge with a one-time code | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/mobile-verifications` | Start or replay approved mobile proof | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/mobile-verifications/confirm` | Confirm OTP/mobile proof | Same actor-bound pre-account session |
| `POST /api/v1/identity/registrations/{registrationId}/complete` | Resolve duplicate state and atomically mint or reuse one account | Verified email and mobile required |
| `POST /api/v1/identity/account-links` | Start or replay a WhatsApp-to-web link challenge | `AAL3_FRESH` portal session |
| `POST /api/v1/identity/account-links/{linkId}/approve` | Record explicit portal approval | Same `AAL3_FRESH` actor |
| `GET /api/v1/identity/account-links/{linkId}` | Read caller-bound link status after fresh Meta confirmation | Same portal actor |

No API accepts `tenantId`, raw provider access token, password, upstream provider authorization code, relationship ID, or return URL in a request body. Keycloak protocol endpoints and callbacks remain Keycloak/Next.js session-boundary concerns and are not re-exposed as BP convenience endpoints.

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
| 422 | `IDENTITY_VERIFICATION_REQUIRED` | Mandatory verified email or mobile remains incomplete |
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
- Dependency failure never completes registration, links accounts, consumes a challenge as success, or mints a tenant.
- Concurrent completion commands serialize on normalized identity keys. One commits; identical contenders replay; divergent contenders enter duplicate resolution.
- ADR-023 message-ID deduplication remains 24 hours and precedes link confirmation.

## 11. Session, Return Target, Sign-Out, and Account Switch

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
- Before account completion, access is scoped to an actor-bound pre-account context. After completion, `tenant_id` is read only from the validated session claim and enforced through BP tenant isolation.
- Provider callbacks bind to server-held state, nonce, PKCE verifier, and intended authentication transaction. Browser parameters cannot choose tenant or account.

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
3. Google verified/unverified email, credential verification, WhatsApp-first completion, existing-account link, split-account conflict, and same-key replay fixtures conform to the schemas.
4. Anti-enumeration tests compare status, shape, and timing class for existing/non-existing email and mobile.
5. Cross-tenant access, forged provider claims, forged return targets, expired/replayed challenge, divergent idempotency replay, assurance downgrade, stale session, and account-switch residue deterministically deny or fail unresolved.
6. Meta scope-separation evidence is mandatory only when the Meta path gate becomes READY.
7. UX-SHELL-02, UX-SHELL-04, UX-AUTH-01 through UX-AUTH-06, UX-PRIV-01, and UX-PWA-04 pass in the proportional F8 evidence for F2.

## 15. F2 Dependency Gate Table

| Gate | Dependency | Status | Owner | Missing artifact or evidence |
|---|---|---|---|---|
| `G-F2-01` | F1 experience foundation merged and approved | **READY** | INST-010 / INST-004 | None — R-052 approved and PR #246 merged |
| `G-F2-02` | ADR-008 Meta deferral reconciled with Founder-approved F2 scope and FA-018 | **BLOCKED** | INST-004 Enterprise Architect, with Founder decision if policy changes | ADR-008 corrigendum/amendment naming Meta login disposition and OAuth-app separation |
| `G-F2-03` | Meta login environment prerequisites | **BLOCKED** | Founder | FA-002 Meta Business Manager verification and FA-018 login app credentials/configuration evidence |
| `G-F2-04` | Google broker path | **READY** | Keycloak/identity implementation owner | Contract fixed; environment-specific provider proof is an implementation acceptance item |
| `G-F2-05` | Approved credential path with second factor | **READY** | Keycloak/identity implementation owner | Contract fixed; realm-flow evidence required during implementation |
| `G-F2-06` | Mandatory verified email and mobile policy | **READY** | Founder / INST-004 | Founder decision and shell contract present |
| `G-F2-07` | WhatsApp identity, linking, takeover, and assurance rules | **READY** | INST-007 / ADR-023 owner | AE-01 security contract, ADR-023, and this proof-gated link contract present |
| `G-F2-08` | Canonical BP public API and generated TypeScript compatibility | **READY** | INST-005 / BP specification owner | This contract plus canonical OpenAPI F2 operations; executable generation proof remains implementation entry evidence |
| `G-F2-09` | Tenant, idempotency, retry, anti-enumeration, and privacy-safe error contracts | **READY** | INST-005 with INST-007 concurrence | This contract and canonical OpenAPI schemas present |
| `G-F2-10` | C-095 component/skeleton determination | **READY** | INST-005 / INST-004 | Identity Boundary is a logical BP component; no new deployable component; OpenAPI is the implementation skeleton |
| `G-F2-11` | F2 implementation authorization | **READY** | Founder | FA-031 and FA-034 apply when all local entry gates pass |
| `G-F2-12` | Independent architecture review | **BLOCKED** | INST-004 Enterprise Architect | Independent review record for this F2 package |
| `G-F2-13` | Deployment authorization | **BLOCKED** | Founder / release authority | Deployment authorization and release evidence; explicitly outside WC-034 F2 grooming |

### Gate conclusion

The F2 contract package is implementation-ready for independent review. F2 implementation remains **BLOCKED** by `G-F2-02` and `G-F2-12`. Meta activation additionally remains blocked by `G-F2-03`. Deployment remains blocked independently and is not requested by this package.

## 16. Review Request

INST-004 must review this component contract, the F2 additions to `business-platform.openapi.yaml`, and the WC-034/decomposition status updates for consistency with the reference architecture, ADR-002/003/008/017/023, ownership boundaries, and generated-client compatibility. Approval does not resolve `G-F2-02`, authorize deployment, or extend scope into F3–F8.
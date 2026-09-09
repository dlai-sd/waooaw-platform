# WC-085 - WC-084 Remediation And Evidence Closure

**Office:** Chief Solution Architect (INST-005)
**Implementation executor:** Platform IT Expert (INST-010), Skills 4 and 16 for application code;
Skill 17 only for separately authorized environment configuration, deployment, and qualification
**Assigned by:** Founder instruction, 2026-09-09
**Status:** PLAN CANDIDATE; RUNNABLE IMPLEMENTATION, PROVIDER ACTIVATION, AND DEPLOYMENT NOT AUTHORIZED
**Predecessor:** WC-084 Authentication Readiness And Customer Portal Delivery Plan
**Delivery baseline:** PR #407 merge `3496d11d9aff53cb86ab9730d36f9c9f6c2c8907`, deployed by
workflow run `34257700855` on 2026-09-08
**Normative parents:** `work-contracts/WC-084-auth-readiness-and-customer-portal-plan.md`,
`work-contracts/WC-084-capability-ledger.md`,
`architecture/reference/components/identity-boundary.md`,
`architecture/reference/components/customer-portal-solution-contract.md`,
`architecture/reference/ux/hybrid-application-shell.md`,
`architecture/reference/ux/hybrid-ui-acceptance-contract.md`,
`architecture/reference/ux/hybrid-visual-system-contract.md`
**Architecture decisions:** ADR-002, ADR-003, ADR-008, ADR-014, ADR-017, ADR-023, ADR-034
**Constitutional basis:** C-001, C-002, C-023, C-026, C-032, C-049, C-059, C-063,
C-065, C-071, C-076, C-080

## 1. Objective And Correction

Close every unproven, partial, blocked, or omitted WC-084 outcome without treating merged code,
passing CI, deployment success, provider fixtures, or truthful unavailability as proof of customer
completion. WC-085 is a remediation and evidence-closure contract. It does not replace or weaken
WC-084.

The deployed baseline contains substantial Customer Portal code, but WC-084 was incorrectly reported
as complete. The exact deployed baseline still has a full-page App Router loading view, history-based
auth dismissal, disabled Google and Facebook providers, no real Demo provider proof, no reproduced
and repaired Chrome landing/catalogue defect, no customer goal-verification command, and no complete
customer-global Billing projection. WC-085 keeps each condition open until its own executable and
human acceptance evidence passes.

No WC-084 story is accepted merely because this plan labels its baseline `DELIVERED_CANDIDATE`.
Every story must satisfy its Section 12 completion gate on one final implementation HEAD, and every
evidence reference must be included in the final unmerged PR.

## 2. Scope And Baseline Truth

### 2.1 Requirement Classes

| Class | WC-085 disposition |
|---|---|
| Omitted defect repair | Implement and qualify auth loading, direct dismissal, compact geometry, and the reproduced Chrome defect |
| Provider activation | Complete Google, Facebook, and email independently; keep a provider disabled until its complete gate passes |
| Partial portal capability | Complete Marketplace trial/hire, Billing, profile/security, navigation, lifecycle, goals, outcomes, and Operations contracts and UI |
| Delivered candidate | Preserve My Agents, conversation, voice, Alerts, shell, safe states, and generated-client boundaries, then prove them on the final deployed candidate |
| Evidence/process defect | Replace broad completion claims with story-level evidence, final-HEAD binding, substantive review, and explicit blocked status |

### 2.2 WC-084 Story Carry-Forward Ledger

`DELIVERED_CANDIDATE` means implementation exists but WC-085 still requires regression and release
evidence. `PARTIAL` means required behavior or evidence is incomplete. `OPEN` means the controlling
repair was not implemented. `BLOCKED` names an external or owner-contract prerequisite.

| Story | Baseline | WC-085 closure obligation |
|---|---|---|
| SP-01 Compact authentication | `OPEN` | Implement and prove initial login/register geometry at required viewport, zoom, locale, direction, and theme states |
| SP-02 Provider identity | `PARTIAL` | Preserve correct provider marks and truthful state; prove focus, contrast, zoom, RTL, theme, and disabled explanations |
| SP-03 Google access | `OPEN` | Complete authorized Google setup and real Demo new/returning customer journeys |
| SP-04 Facebook access | `BLOCKED` by FA-002/FA-018 | Complete Founder prerequisites, isolated login app, authorized setup, and real Demo journeys |
| SP-05 Email access | `PARTIAL` | Prove real Demo registration, delivery, verification, login, return, sign-out, and repeat login |
| SP-06 Truthful readiness | `PARTIAL` | Reconcile manifest, Keycloak, secret references, endpoint reachability, UI projection, failure telemetry, and rollback |
| SP-07 Stable loading | `OPEN` | Replace auth full-page loading with a stable, dismissible, accessible in-modal loading/error shell |
| SP-08 Direct dismissal | `OPEN` | Capture the public origin once and dismiss any login/register switch depth directly to it |
| SP-09 Browser integrity | `OPEN` | Reproduce the reported Chrome defect, repair its owning CSS/layout, and pass the complete browser geometry matrix |
| SP-10 My Agents | `DELIVERED_CANDIDATE` | Prove authorized list, selection, resume target, empty/error states, and real authenticated entry |
| SP-11 Text conversation | `DELIVERED_CANDIDATE` | Prove draft/send/retry/reconcile/partial/evidence behavior from the Customer Portal |
| SP-12 Voice conversation | `DELIVERED_CANDIDATE` | Prove capture/review/correct/cancel/send, permission/offline failure, text fallback, and Stop behavior |
| SP-13 Marketplace | `PARTIAL` | Complete owner-approved, idempotent trial/hire continuation or explicitly defer the command and release no false affordance |
| SP-14 Alerts | `DELIVERED_CANDIDATE` | Prove server order, stable destination, and separation of read/acknowledge from approval |
| SP-15 Billing | `BLOCKED` by owner contract | Add the BP-mediated customer-global WBE projection and portal UI; no browser-derived monetary truth |
| SP-16 Profile and settings | `PARTIAL` | Complete organization, login-method, security, assurance, and account-switch semantics and persistence |
| SP-17 Navigation | `PARTIAL` | Prove mobile bottom navigation and account drawer, including a truthful Billing destination and deterministic sign-out |
| SP-18 Themes and accessibility | `PARTIAL` | Pass keyboard, screen reader, axe, reduced motion, zoom, RTL, language, safe-area, and theme matrices |
| SP-19 Shared channel APIs | `PARTIAL` | Close the capability ledger and prove generated BP clients plus explicit WhatsApp/future-mobile mappings |
| SP-20 Safe degradation | `PARTIAL` | Prove distinct loading, empty, offline, unavailable, stale, conflict, partial, and error behavior without false success |
| SP-21 Human override | `DELIVERED_CANDIDATE` | Prove Emergency Stop remains visible, reachable, and operational across all owned states and failures |
| SP-22 Frozen public experience | `OPEN` evidence | Bind before/after visual evidence and confirm only authorized auth/defect repairs changed public routes |
| SP-23 Two-minute onboarding | `PARTIAL` | Complete Onboard/Induct behavior and record timed usability plus domain-adaptive induction evidence |
| SP-24 Universal goals | `BLOCKED` by owner contract | Add typed customer verification/amendment semantics and prove every active goal has skill, measure, frequency, and verification |
| SP-25 Outcome traceability | `PARTIAL` | Complete customer UI and prove outcome-to-goal/skill/evidence traceability without guarantees |
| SP-26 Goal-gated operations | `BLOCKED` by goal-verification contract | Prove server-owned lock/unlock, amendment reassessment, and preserved historical evidence |

## 3. Authority And Entry Gates

### 3.1 Decision Space

| Boundary | Accountable authority | Required output before dependent implementation |
|---|---|---|
| Product composition and customer language | Product Owner (INST-011) | Initial-release inclusion/defer decisions and customer-visible semantics |
| Public APIs and component integration | Solution Architect (INST-005) with named owners | Accepted OpenAPI/components, errors, state transitions, and generated-client impact |
| Provenance, ordering, freshness, retention, correction | Data Architect (INST-006) | Accepted data semantics for new goal, outcome, Billing, profile, and provider evidence |
| Assurance, authorization, privacy, secrets, callback and failure controls | Security Architect (INST-007) | Accepted security contract and threat/failure tests |
| Reference-architecture conformance | Enterprise Architect (INST-004) | Review of changed architecture contracts; no product or implementation substitution |
| Application implementation | Platform IT Expert (INST-010), Skills 4 and 16 | Source and focused tests only after explicit current-session Founder authorization |
| Demo provider/cloud mutation and qualification | Platform IT Expert (INST-010), Skill 17 | Only the exact separately authorized provider, environment, secret reference, deployment, and proof |
| Credentials, external registrations, activation, plan/visual/PR acceptance, merge | Founder | Explicit decisions remain separate and cannot be inferred |

### 3.2 Mandatory Entry Checklist

Implementation may begin only after the Founder accepts WC-085 and explicitly authorizes WC-085
implementation for that session. Provider configuration or cloud mutation additionally requires an
exact provider/environment authorization. The executor records `PASS`, `BLOCKED`, or `NOT_APPLICABLE`
for each item; silence is not `PASS`.

| Gate | Required condition |
|---|---|
| Baseline | PR #407 merge, deployed revision, image digest, and current Demo revision are recorded |
| Plan | Founder accepts WC-085 scope, story ledger, defer decisions, and visual review points |
| Implementation | Founder explicitly authorizes runnable WC-085 implementation for the current session |
| Provider mutation | Founder separately names Google, Facebook, and/or email, Demo, secret destination, activation, and test authority; authority for one provider does not cover another |
| Google inputs | Google project/consent/client ownership, exact callbacks, secret references, test identities, and policy URLs are ready |
| Facebook inputs | FA-002 and FA-018 are complete; isolated login app, exact callbacks, scopes, secret references, and test identities are ready |
| Email inputs | Demo sender/domain/delivery, template, realm flow, test mailbox, and expiry/retry behavior are ready |
| Goal contract | Product, BP, professional, Data, Security, and INST-005 accept typed customer verification and reassessment semantics |
| Billing contract | WBE, BP, Product, Data, Security, and INST-005 accept the customer-global summary and unavailable semantics |
| Browser baseline | Founder-provided screenshot/context and deterministic Chrome reproduction are recorded before CSS repair |
| Test environment | Repository-approved Docker runners, browser projects, and sanitized evidence destinations are available |

## 4. Google And Facebook Completion Contract

### 4.1 Founder-Side Actions

The Founder never sends secrets through chat, commits them, or places them in PR evidence. Secrets
are entered directly into the approved secret store. Exact callback URIs are derived from the
deployed Demo Keycloak issuer and recorded as non-secret evidence before provider-console changes.

| Provider | Founder action | Founder completion evidence |
|---|---|---|
| Google | Select/own the Google Cloud project; configure OAuth consent, support/privacy/domain details; create the Web OAuth client; register exact Demo Keycloak callback URI; enter client ID/secret into the approved secret store; provide approved test identities; authorize Demo activation and test | Redacted console export/screenshots, callback list, consent status, secret version/reference only, test-account custody record, and explicit Demo authorization |
| Facebook | Complete FA-002 Meta Business verification; complete FA-018 by creating a dedicated WAOOAW customer-login app separate from DMA Business OAuth; enable Facebook Login with only `email` and `public_profile`; register the exact Demo Keycloak callback URI and domains; enter app ID/secret into the approved secret store; add approved tester identities; authorize Demo activation and test | FA-002/FA-018 completion record, redacted app/settings evidence, scope and callback list, secret version/reference only, tester-role record, and explicit Demo authorization |
| Email | Own or approve the Demo sender/domain and customer-facing template; complete any DNS or mailbox-provider verification that only the account owner can perform; enter delivery credentials directly into the approved secret store; provide an approved non-customer test mailbox; authorize Demo delivery and test | Redacted sender/domain verification, approved template revision, secret version/reference only, test-mailbox custody record, expiry/retry policy acceptance, and explicit Demo authorization |

Founder actions are non-delegable account-owner decisions. INST-010 may derive and present non-secret
callback/DNS values, validate references, and execute only a separately authorized configuration or
qualification step; INST-010 must not create an external account in the Founder's name, receive a
credential through chat or a committed file, copy a secret into evidence, or infer activation authority.
One provider's authorization, credential, or passing journey grants no authority or evidence to another.

### 4.2 Executor Configuration And Proof

For each provider independently, the authorized executor must:

1. validate the reviewed environment manifest and exact secret-reference names before mutation;
2. configure only the Keycloak broker for that provider; application code never handles provider
   credentials or calls provider identity APIs;
3. configure approved scopes, sync mode, trust rules, and stable-subject/email-verification mappers;
4. verify the public broker endpoint and provider authorization endpoint from the deployed web and
   Keycloak runtime boundaries without logging authorization codes, tokens, or PII;
5. reconcile actual Keycloak state, secret references, and the Demo provider projection;
6. run new-customer registration, returning login, safe return to `/home`, sign-out, repeat login,
   account-collision/privacy behavior, denied consent, callback failure, unreachable endpoint, and
   rollback tests using approved non-production identities;
7. enable the provider in Demo only after all provider-specific checks pass; otherwise restore the
   disabled manifest and broker state and record the accountable blocker.

The dependency order is independent for each provider: Founder-owned external prerequisite and
secret-store entry -> reviewed non-secret manifest/realm diff -> focused schema and realm validation
-> separately authorized Demo reconciliation -> deployed endpoint check -> real new/returning/failure
journeys -> enable decision. Email follows the same order using sender/domain, Keycloak email flow,
delivery, verification, expiry, and retry evidence rather than an OAuth callback. A blocked provider
stops at its first unmet dependency and remains disabled; it does not stop qualification of another
provider whose own chain is complete.

Provider fixtures, unit tests, a visible button, a successful redirect start, or a green deployment
do not satisfy real provider proof. Google passing does not satisfy Facebook, and vice versa.

### 4.3 Provider Evidence Schema

The final PR must contain a sanitized record for each `GOOGLE`, `FACEBOOK`, and `EMAIL` provider:

| Field | Required value |
|---|---|
| Environment and revision | `demo`, deployed revision, image digest, Keycloak revision |
| Authorization | Founder action/authorization reference |
| External prerequisites | Named prerequisite with `PASS` or accountable `BLOCKED` |
| Callback | Exact non-secret registered callback URI and observed callback host |
| Secret binding | Secret name/reference and version only; never the value |
| Reconciliation | Manifest state, Keycloak broker state, UI projection, and endpoint reachability agree |
| Journeys | Registration, login, return, sign-out, repeat login, denial, failure, and rollback results |
| Privacy/security | Scope list, stable subject mapping, no enumeration, no token/PII leakage |
| Decision | `ENABLED` only when all rows pass; otherwise `DISABLED` with blocker |

## 5. Authentication And Browser Repair Contract

### 5.1 Stable Modal And Navigation

- Add a route-local auth loading boundary that renders inside the same reserved dialog shell; the
  global `web/app/loading.tsx` must not own intercepted auth loading.
- Keep modal width and minimum height stable across loading, login, registration choice, bounded
  provider error, and switching. Initial choice screens fit at 1366x768 without dialog scrolling.
- Loading is announced, finite, reduced-motion aware, and cannot block Close, Escape, backdrop
  dismissal, or Emergency Stop.
- Capture one sanitized same-origin public origin when the intercepted journey begins. Login and
  registration switches carry or replace that origin without adding dismissal depth.
- One dismissal from every modal state navigates directly to the captured origin. Direct `/login`
  and `/register` remain refresh-safe standalone routes and use a safe default when no origin exists.
- Reject external, protocol-relative, auth-loop, protected-without-session, and malformed return
  targets. Preserve query/fragment only when permitted by the safe-return contract.
- Restore focus to the invoking control when it still exists; otherwise focus the public page's
  deterministic fallback target.

### 5.2 Chrome And Cross-Browser Repair

Before changing CSS, record the exact route, Chrome version, operating system, viewport, zoom,
locale, direction, theme, font readiness, screenshot, DOM geometry, and console/network errors that
reproduce the Founder-reported landing/catalogue distortion. Identify the owning layout rule. Do not
approve a speculative broad restyle.

After the smallest owning repair, test public landing/catalogue, auth modal and standalone routes,
authenticated shell, My Agents, Marketplace, Alerts, Billing, Profile, Settings, and relationship
workspace in Chromium Chrome/Edge-equivalent, Firefox, and WebKit Safari-equivalent at 360x800,
768x1024, 1366x768, and 1440x900. Cover 100%, 125%, and 200% zoom/reflow where supported, English
and Urdu, LTR and RTL, light and dark themes, keyboard, reduced motion, font-ready/font-delayed,
loading, and error states.

Executable geometry assertions must reject horizontal document overflow, clipped content,
incoherent overlap, destructive word wrapping, unreachable controls, undersized catalogue cards,
modal scroll on initial auth choice, fixed-navigation collision, and unsafe mobile insets.
Screenshots are supporting evidence, not the sole gate.

## 6. Portal Capability Closure

### 6.1 Owner-Contract Repairs Before UI

The WC-084 portal contract and canonical BP OpenAPI already decide the read paths listed below.
The capability ledger subsequently proved two owner gaps and one identity-command gap. The following
amendments are the complete architecture decision for WC-085; INST-010 implements them but does not
choose alternate paths, command kinds, assurance, state, or fallback semantics.

| Capability | Exact contract and behavior | Accountable acceptance | Blocking rule and first falsifiable contract check |
|---|---|---|---|
| Goal verification | Amend existing `POST /api/v1/employment/relationships/{relationshipId}/workspace/commands` (`submitRelationshipCommand`) by adding `VerifyGoalPayloadV1 { kind: VERIFY_GOAL, goalId, goalVersion, verificationDecision: VERIFIED \| CHANGES_REQUESTED, correctionReason? }` to the canonical `kind` discriminator union. `correctionReason` is required and length-bounded for `CHANGES_REQUESTED` and absent for `VERIFIED`. The existing envelope requires `schemaVersion`, `expectedWorkspaceVersion`, `expectedSubjectVersion`, and `Idempotency-Key`. BP derives tenant, actor, relationship participation, current role/capability, and time; requires `AAL3_FRESH`; validates that `goalVersion` is the current immutable version with declared skill, measure, and frequency; records an append-only decision event and returns the existing command receipt. `VERIFIED` may enable reassessment; `CHANGES_REQUESTED` keeps Operations locked and creates no amended goal by itself. Same key/hash replays, changed hash conflicts, stale versions conflict, and timeout remains unresolved until command/read reconciliation. `AMEND_GOAL` and `REPLACE_GOAL` never verify. A material amendment changes the new version to `REQUIRES_RENEWAL` and triggers reassessment without rewriting prior verification or correction history. | Product, BP and professional owners define eligibility meaning; Data owns lineage/retention; Security owns authorization/assurance/privacy; INST-005 accepts the component and OpenAPI amendment. | Stop Goal/Operations UI mutation until component contract, OpenAPI discriminator/schema, generated client, and negative/idempotency/conflict tests agree. First check: schema fixtures prove `VERIFY_GOAL` uses canonical `kind`, requires both expected versions and the exact goal version, and is absent from amend/replace effects. |
| Operations reassessment | Preserve `GET /api/v1/employment/relationships/{relationshipId}/workspace/operations` (`getRelationshipOperations`) as sole portal eligibility truth. It returns `LOCKED`, `ELIGIBLE`, `ACTIVE`, `PAUSED`, or `BLOCKED`, required/verified goal versions, reason, affected work/outcome references, reassessment state, freshness, and history reference. Verification may unlock only after authoritative command completion; material amend/replace immediately removes eligibility until renewed verification, preserves active/pending work as explicitly paused or blocked, and never deletes outcome/evidence history. | Product, BP/professional, Data, Security, and INST-005. | Stop Operations integration when any state transition or affected-work consequence is unspecified. First check: state-transition contract test proves amend-after-verification cannot remain `ELIGIBLE` and old history remains readable. |
| Billing summary | Retain public `GET /api/v1/billing/summary` (`getBillingPortalSummary`) and add WBE internal owner operation `getCustomerBillingPortalProjection` returning `WbeCustomerBillingPortalProjectionV1` before implementing its adapter. The service-authenticated, tenant-derived projection is customer-global and returns schema/projection version, `producedAt`, `validUntil`, freshness, preference, allowance allocation/use/remaining/reset, forecast range/horizon/assumptions, invoices, payment state, and typed consequences. Every family carries `sourceSystem`, `sourceRecordVersion`, `asOf`, and optional `correctionOf`; invoices are ordered by `issuedAt` descending then stable invoice reference, and allowance families by owner-defined resource order then stable resource key. BP may compose only owner-attributed families and must preserve `CURRENT`, `STALE`, `PARTIAL`, `UNKNOWN`, `UNAVAILABLE`, and `BLOCKED`; `PARTIAL` names each missing or stale family and its last authoritative time. Absent owner truth is never zero or empty success. The browser never calculates, calls WBE, substitutes one relationship, or exposes provider/ledger details. | WBE owner accepts internal semantics; BP owner accepts relay/composition; Product accepts customer language; Data accepts provenance/freshness; Security accepts service authorization/minimization; INST-005 accepts public compatibility. | Stop Billing adapter/UI until the WBE owner contract and implementation supply every mandatory family and BP contract tests prove provenance and unavailable behavior. First check: a missing payment/allowance family produces typed `PARTIAL`/`UNAVAILABLE`, never a complete `200` projection with invented values. |
| Marketplace continuation | Preserve `GET /api/v1/professionals/marketplace` (`browseMarketplaceProfessionals`) and its server-owned `nextAuthorizedAction`. Continuation uses only existing `getProfessionalDisclosure`, `startEmploymentRelationshipTrial`, `getRelationshipContractJourney`, `acceptEmploymentContract`, `createRelationshipOnboardingOrder`, and `startPaidRelationshipActivation`. `nextAuthorizedAction` supplies the exact operation kind, opaque server-issued subject/version/intent references, expiry, required assurance, and named safe target; it contains no arbitrary URL. The portal submits only those references and idempotency keys, revalidates safe return and offerability, and never constructs eligibility, price, operation order, or identifiers. | Product and BP lifecycle owners with INST-005; Security for assurance and return-target controls. | Do not render an enabled trial/hire command unless the projection supplies an unexpired executable authorized continuation. First check: absent, expired, inaccessible, replayed, or version-stale `nextAuthorizedAction` yields no command and no relationship mutation. |
| Profile/security | Preserve `get/updateCustomerProfile`, `get/updateCustomerSettings`, and `listCustomerLoginMethods`. Before add/remove UI, amend the identity contract and OpenAPI with: `POST /api/v1/identity/login-methods/{provider}/link-intents` (`createLoginMethodLinkIntent`) using `Idempotency-Key` and `If-Match` login-method version plus `CreateLoginMethodLinkIntentRequestV1 { safeTargetId }`, returning `IdentityActionIntentV1`; `DELETE /api/v1/identity/login-methods/{loginMethodId}` (`removeCustomerLoginMethod`) using `Idempotency-Key` and `If-Match`, returning `IdentityMutationReceiptV1`; and `POST /api/v1/identity/security-action-intents` (`createIdentitySecurityActionIntent`) using `Idempotency-Key` and `If-Match` profile version plus `CreateIdentitySecurityActionIntentRequestV1 { actionKind, safeTargetId }`, returning `IdentityActionIntentV1`. `actionKind` is exactly `CHANGE_CREDENTIAL`, `CONFIGURE_MFA`, or `RECOVERY_REVIEW`. All three require current membership, `AAL3_FRESH`, proof through Keycloak, single-use expiring opaque intents where applicable, approved named safe targets, and server enforcement that at least one usable login or recovery path remains. They reuse privacy-safe identity errors for session required, step-up, denied, inaccessible, idempotency/version conflict, and dependency unavailable; no provider subject or account-existence fact is exposed. Account switch uses Keycloak `prompt=select_account` only after the identity-boundary cleanup contract completes; no BP account-switch command is invented. | Identity and BP owners, Product, Data, Security, and INST-005. | Stop each absent command independently; reads/settings may proceed without false controls. First check: removing the last usable method and stale/freshness-deficient mutations deny with zero state change and no account-existence disclosure. |
| Cross-channel mapping | The final capability ledger records operation/path, owner, request/response state, errors, generated client, web presentation, WhatsApp continuation/unsupported reason, and future-mobile mapping. Goal verification, Marketplace, Billing, profile/security, outcomes, and Operations use the same BP semantics; channel adapters may alter transport/presentation only. | INST-005 with each capability owner; Security and Data for channel-specific minimization/provenance. | Stop dependent UI when a released operation lacks a generated client or explicit three-channel mapping. First check: deterministic ledger validation rejects missing owner, operation, state/error, or channel cell and bundle/network inspection rejects private endpoints. |

OpenAPI changes precede endpoint and UI changes. Generated clients, server adapters, fixtures, and
consumers move in the same bounded slice. Each changed operation defines authorization, tenant
derivation, assurance, idempotency, version/conflict, freshness, audit/evidence, privacy-safe errors,
and unavailable behavior.

#### 6.1.1 Product Semantics And Initial-Release Boundary

- WC-085 initial release includes all SP-01 through SP-26 and the real Demo Google, Facebook, and
  email journeys. Browse-only Marketplace, truthfully unavailable Billing, or disabled providers
  may be shown during development, but none completes its story or permits a blanket release-complete
  claim. Only an explicit Founder scope amendment can remove a story or provider from WC-085.
- Goal states use `Needs your review`, `Verified`, or `Changes requested`. Operations says
  `Locked until required goals are verified` and names the affected goals without implying that a
  browser action itself unlocked work. An amended material goal returns to `Needs your review`.
- Marketplace shows Trial or Hire only for the exact executable `nextAuthorizedAction`. Browse and
  detail remain usable when continuation is absent; no disabled command suggests that clicking could
  succeed. Billing absent owner truth reads `Billing information temporarily unavailable`; partial
  truth identifies the unavailable family and its as-of time without displaying zero as a fallback.
- Anonymous provider choices use `Not available yet` for an unmet activation prerequisite and
  `Temporarily unavailable` for a reconciled provider or readiness dependency failure. They never
  name account existence, secret state, internal provider policy, or another tenant. Authenticated
  denied actions use the accepted privacy-safe identity error and a next action, not provider detail.
- Profile and security reads remain available when an independent mutation is blocked. Link, remove,
  credential, MFA, recovery, and account-switch controls appear only when their server projection
  supplies current capability, version, assurance next action, and an approved safe target.

#### 6.1.2 Data Semantics And Evidence Lineage

- Every mutable projection carries `schemaVersion`, owner `subjectVersion`, `asOf`, `producedAt`,
  `validUntil` where freshness expires, `freshness`, `sourceSystem`, and an opaque `historyRef` or
  `evidenceRef`. Server order is authoritative and deterministic with a stable tie-breaker; clients
  do not re-rank Goals, Operations history, invoices, login methods, or provider evidence.
- Goal verification, change requests, amendments, replacements, reassessments, and affected-work
  consequences are append-only events linked by relationship, goal ID, immutable goal version,
  prior event/version, actor, command receipt, and evidence reference. Correction appends a
  superseding event; it never overwrites a prior customer decision or outcome/evidence record.
- Billing preserves per-family WBE provenance and correction lineage through BP. A mixed-age response
  is `PARTIAL` unless every mandatory family is authoritative for the declared validity window.
  `UNKNOWN` means command/result reconciliation is unresolved, `UNAVAILABLE` means owner truth could
  not be obtained, and `BLOCKED` means policy forbids the projection; none is serialized as empty or
  zero success.
- Identity intents and receipts record opaque actor/account scope, operation, canonical request hash,
  source and resulting version, state, issue/consume/expiry times, safe-target identifier, and audit
  reference. Provider evidence records environment, provider alias, manifest/realm revisions,
  secret reference/version only, journey class, result, observed time, and correction/supersession;
  it excludes credentials, tokens, authorization codes, raw provider subjects, email, and customer PII.
- Identity idempotency records retain the accepted minimum of 24 hours. Exact billing, identity audit,
  and provider-evidence retention/deletion periods require an accepted legal/privacy retention
  schedule not present in the bounded authority set. Until the Founder accepts that named schedule,
  schema and append-only capture may proceed, destructive purge and Production evidence-retention
  configuration remain blocked; no reviewer invents a duration.

#### 6.1.3 Security Controls And Failure Tests

- Each provider uses an environment-specific Keycloak broker alias, client, secret reference, exact
  callback allowlist, and least-privilege scopes. Wildcards, cross-environment callbacks, HTTP outside
  local Docker, shared Facebook login/DMA credentials, and direct application-provider calls fail
  closed. Callback handling binds a server-held, single-use transaction to state, nonce, PKCE S256
  verifier, provider, initiating session, safe target, and expiry; mismatch, replay, or unsolicited
  callback performs zero identity mutation.
- Provider binding uses stable upstream provider subject plus normalized broker/provider identity;
  verified email is contact and candidate-resolution evidence only. Unverified email is ignored for
  completion/linking, same-email methods never auto-link, and changed email never rebinds a method.
  Link/remove/security actions preserve normalized response status, body shape, and timing class for
  existing, absent, inaccessible, cross-tenant, and already-linked targets.
- `AAL3_FRESH` means Keycloak authentication age no greater than five minutes at command receipt;
  token refresh does not renew it. Link and security intents are opaque, single-use, actor/account/
  operation/safe-target bound, expire within 15 minutes, and are reauthorized at consumption.
  Removing the final usable login or recovery path, stale `If-Match`, stale capability, or changed
  membership returns zero mutation.
- Authenticated HTML, RSC, API, identity, Goal, Operations, Billing, Marketplace, and provider
  responses are `no-store`, excluded from service-worker caches, and removed on sign-out/account
  switch. URLs, browser storage, logs, traces, analytics, and evidence exclude tokens, codes, PKCE
  verifiers, secrets, raw provider subjects, email/mobile, tenant IDs, and protected payloads.
- Required negative tests cover cross-tenant access, wrong issuer/audience/environment, excess scope,
  state/nonce/PKCE mismatch, callback replay, stable-subject/email collision, enumeration timing,
  stale AAL3, last-method removal, intent reuse/expiry, unsafe return, cache/storage residue, log/PII
  scanning, dependency outage, idempotency conflict, rollback, and concurrent mutation. Provider
  rollback disables broker and manifest projection, revokes pending transactions/intents, preserves
  established account bindings and audit history, and proves the UI fails closed.

#### 6.1.4 Component-Contract Concurrence

- Existing canonical BP operations are `submitRelationshipCommand`, `getRelationshipOperations`,
  `getBillingPortalSummary`, `browseMarketplaceProfessionals`, `getCustomerProfile`,
  `updateCustomerProfile`, `getCustomerSettings`, `updateCustomerSettings`, and
  `listCustomerLoginMethods`, plus the six Marketplace continuation operation IDs named above.
  WC-085 extends these surfaces additively and does not rename or bypass them.
- `VerifyGoalPayloadV1` joins the existing `kind`-discriminated relationship-command union and returns
  the existing command receipt. The Operations read remains the only eligibility projection and must
  expose required/current verified goal versions, reason, reassessment state, affected references,
  freshness, and history reference without a second mutation family.
- `getCustomerBillingPortalProjection` is a new private WBE owner operation, not a browser or public
  BP operation. Its accepted WBE schema and service-authenticated implementation must exist before BP
  adapts `getBillingPortalSummary`; relationship billing endpoints cannot substitute for it.
- The three identity operations in the Profile/security row are new public BP operations. Link and
  security-intent creation return `202 IdentityActionIntentV1` with `intentId`, `state`, `expiresAt`,
  `requiredAssurance`, and `safeTargetId`; remove returns `200 IdentityMutationReceiptV1` with
  `receiptId`, `outcome`, `previousVersion`, `resultingVersion`, and `completedAt`. `provider` is an
  allowlisted configured provider alias, `safeTargetId` is a server-approved named target rather than
  a URL, `If-Match` is mandatory, and all mutations use `Idempotency-Key`. The intent read/consume
  continuation remains Keycloak-bound; no provider callback or credential is exposed as a BP body.
- S1 remains blocked until WBE, BP, professional, Identity, Product, Data, Security, and INST-005
  accept the amended component/OpenAPI schemas and generated-client fixtures. This concurrence makes
  the shapes implementable; it is not implementation, provider activation, deployment, or acceptance.

### 6.2 Delivered-Candidate Requalification

My Agents, text conversation, voice, Alerts, shell navigation, safe states, Emergency Stop, and
generated-client/private-endpoint boundaries are not rewritten without a failing gate. They are
requalified from a real authenticated Customer Portal entry on the final candidate. A regression is
repaired in its owning slice and rerun before broader work proceeds.

## 7. Ordered Implementation Slices

| Slice | Work | Entry | Exit evidence |
|---|---|---|---|
| 0. Baseline | Bind PR #407, deployed revision/images, current provider states, screenshots, and all SP statuses | WC-085 accepted | Baseline ledger with every story explicitly classified |
| 1. Contract closure | Goal/Operations, Billing, Marketplace, Profile/security, and channel mappings | Named owners available | Accepted contracts, OpenAPI diff, capability ledger, generated-client no-drift |
| 2. Auth UX | Compact geometry, in-modal loading/error, explicit origin/dismissal, safe returns/focus | Auth design boundaries accepted | Focused component/navigation/geometry/accessibility tests |
| 3. Browser defect | Reproduce and repair the reported Chrome defect | Reproduction evidence exists | Before/after geometry and cross-browser focused checks |
| 4. Email qualification | Complete real Demo email path | Sender/domain/test mailbox and mutation authority | Sanitized full-journey provider record |
| 5. Google qualification | Configure and prove Google independently | Founder Google inputs and exact Demo authority | Sanitized full-journey provider record or disabled blocker |
| 6. Facebook qualification | Configure and prove Facebook independently | FA-002/FA-018 and exact Demo authority | Sanitized full-journey provider record or disabled blocker |
| 7. Portal gaps | Implement generated-client-backed Goal, Operations, Billing, Marketplace, Profile/security, and navigation closure | Slice 1 accepted | Focused contract/component/API/browser evidence |
| 8. Regression | Requalify all 26 stories, authorization, privacy, cache, accessibility, and Emergency Stop | Slices 2-7 assembled | Complete story matrix with no unsupported pass |
| 9. Final qualification | Build once, deploy only if authorized, run final Docker and real Demo campaigns, review visuals | Final code frozen | One HEAD-bound evidence bundle and unmerged PR |

After the first substantive edit in a slice, run the cheapest Dockerized behavior-scoped check that
can falsify it. Do not open another implementation slice until that focused check passes or changes
the owning hypothesis. Run broad Docker/browser campaigns only at assembled boundaries.

### 7.1 Per-Story Execution Controls

Section 12 defines the pass assertion. This ledger makes authority, dependency, first falsifiable
check, rollback/stop, and evidence explicit for every baseline disposition. `S0` through `S9` refer
to the ordered slices above. Every evidence reference resolves inside the Section 9 bundle.

| Story | Authority and exact behavior | Order and first falsifiable check | Rollback / stop and final evidence |
|---|---|---|---|
| SP-01 | Product/Founder visual boundary; INST-010 implements Section 5.1 geometry only | S2; initial login/register at 1366x768 has no modal scroll | Revert auth CSS independently; stop on frozen-route drift; auth geometry in browser matrix |
| SP-02 | Identity/Product own truthful provider labels; Security owns focus/contrast/privacy | S2 after provider projection contract; automated mark/state/a11y matrix | Restore prior reviewed marks/state projection; stop on misleading availability; visual/a11y matrix |
| SP-03 | Founder owns Google account, secret entry, activation/test authority; Identity/Security own broker contract | S5 after Google chain in Section 4; real Demo new and returning journey | Disable Google in realm and manifest; stop at first unmet provider gate; Google readiness record |
| SP-04 | Founder owns FA-002/FA-018, secret entry, activation/test authority; isolated Meta login policy is fixed | S6 after FA-002/FA-018; real Demo journey with only `email public_profile` | Disable Facebook in realm and manifest; stop on scope/app mixing; Facebook readiness record |
| SP-05 | Founder owns sender/domain, secret entry, mailbox and Demo authority; Keycloak owns credential/email flow | S4 after email chain; real delivery plus expiry/retry/verification journey | Disable email projection/flow without deleting accounts; stop on delivery or secret gap; email readiness record |
| SP-06 | Identity/Security/Skill 17 reconcile manifest, secret reference, Keycloak, endpoint and UI per provider | S4-S6 independently; injected layer mismatch fails closed and emits sanitized telemetry | Restore last reviewed disabled state; stop on any disagreement; provider reconciliation/fault records |
| SP-07 | INST-005 Section 5.1 route-local boundary; INST-010 implements | S2; delayed route keeps stable modal and all dismiss controls operational | Restore prior auth route boundary; stop on full-page loading or trapped input; timing/CLS/a11y evidence |
| SP-08 | Identity safe-return contract and INST-005 state machine; INST-010 implements | S2; switch repeatedly then each one-action dismissal reaches captured origin | Revert explicit-origin change; stop on external/auth-loop target; navigation state-machine evidence |
| SP-09 | Founder supplies defect context; INST-010 repairs only reproduced owning rule | S3 after recorded reproduction; geometry assertion fails before and passes after | Revert owning CSS rule; stop if unreproduced or broad restyle required; reproduction/browser bundle |
| SP-10 | BP/relationship owner supplies authorized collection/resume target; browser only renders it | S7 after S1; cross-tenant and empty/error focused tests | Disable route/slice, preserve server truth; stop on browser resume inference; BP auth and browser evidence |
| SP-11 | Reuse WC-060 conversation contract unchanged | S8 requalification after S7; accepted transport cannot render completed processing | Revert portal adapter only; stop on contract drift/private call; conversation contract/browser evidence |
| SP-12 | Reuse WC-062 voice contract unchanged; Security owns consent/retention | S8; permission denial and offline preserve complete text fallback and Stop | Disable voice control, retain text; stop on unproven consent/erasure; voice/failure evidence |
| SP-13 | Product/BP own Section 6.1 Marketplace continuation; Security owns assurance/safe return | S7 after S1; absent/expired server action yields no trial/hire mutation | Disable only unavailable command; stop on inferred ID/offerability; contract/negative/browser evidence |
| SP-14 | BP/Data own server order/cursor; read/ack are feed-only commands | S8 requalification; acknowledge cannot mutate underlying approval/action | Disable feed mutation, keep truthful read; stop on ordering/semantic drift; API/interaction evidence |
| SP-15 | WBE/BP/Product/Data/Security/INST-005 own Section 6.1 summary contract | S7 after accepted S1 WBE addition; missing owner family cannot appear as complete data | Billing remains typed unavailable; stop on relationship/browser substitute; WBE/BP/network/browser evidence |
| SP-16 | Identity/BP/Product/Data/Security/INST-005 own Section 6.1 profile/security operations | S7 after accepted S1 identity amendment; last-login removal and stale assurance deny | Hide only unimplemented commands, retain reads; stop on browser account truth; identity/assurance/browser evidence |
| SP-17 | Product/Founder own navigation composition; Identity owns sign-out cleanup | S7 after truthful Billing/profile destinations; account-switch sentinel finds no prior-account residue | Revert shell navigation independently; stop on dead destination or residue; mobile/storage evidence |
| SP-18 | Product visual boundary and Security accessibility/privacy requirements | S8 after assembled owned routes; axe/keyboard/screen-reader/zoom/RTL matrix | Stop release and revert offending route change; accessibility/localization matrix |
| SP-19 | INST-005 and capability owners own Section 6.1 channel mappings/generated BP boundary | S1 before dependent UI, recheck S8; generation zero-diff plus private-endpoint scan | Revert contract/client slice together; stop on missing mapping/private call; capability ledger/generation/network evidence |
| SP-20 | Each capability owner defines typed safe states; browser never promotes uncertainty | S8; injected offline/stale/conflict/partial cases remain distinct | Disable affected command/route; stop on false success; fault-injection/browser state matrix |
| SP-21 | Constitutional Emergency Stop contract is invariant; INST-010 preserves it | S8; latency/reachability tests during every named degraded state | Revert offending shell/slice; stop entire release on unreachable Stop; interaction/failure/latency evidence |
| SP-22 | Founder owns frozen-public visual acceptance; INST-005 defines repair boundary | S0 baseline then S3/S9 diff; unauthorized pixels/routes fail | Revert out-of-bound visual changes; stop pending Founder decision; visual diff and acceptance reference |
| SP-23 | Product owns Onboard/Induct semantics; relationship/conversation owners supply server truth | S7 after S1; timed flow plus correction/continuation test | Disable incomplete lifecycle entry, preserve conversation; stop on browser lifecycle invention; usability/induction evidence |
| SP-24 | Product/BP/professional/Data/Security/INST-005 own `VERIFY_GOAL` contract | S1 then S7; schema/idempotency/version/history tests precede UI | No verification control and Operations stays locked; stop until contract accepted; contract/state/browser evidence |
| SP-25 | Product/BP/professional/Data own canonical outcome traceability and attribution limits | S7 after S1; fixture missing skill/goal/measure/evidence is rejected or partial | Disable outcome view, preserve history; stop on guarantee/browser derivation; API/evidence/browser review |
| SP-26 | Product/BP/professional/Data/Security own server eligibility and reassessment | S1 -> S7 after SP-24; verified-to-amended transition relocks without history loss | Keep Operations locked; stop on client unlock or destructive reassessment; eligibility/conflict/history evidence |

## 8. Test And Evidence Contract

All executable tests, linters, type checks, schema validation, generation, builds, browser checks,
scans, and qualification run in repository-approved Docker services under C-080. No host virtual
environment or host dependency installation is evidence.

Required evidence includes:

- strict TypeScript, production build, lint, focused component/API tests, and at least 90% changed
  interactive line coverage;
- Business Platform tests, OpenAPI validation, pinned generated-client regeneration with zero diff,
  and owner-contract negative/idempotency/conflict tests;
- real Demo provider journeys and sanitized reconciliation records for email, Google, and Facebook;
- browser geometry, interaction, accessibility, locale/direction/theme/zoom, loading/failure, and
  frozen-public-route before/after evidence;
- authenticated route denial, `no-store`, service-worker exclusion, CSRF/state/nonce/PKCE behavior,
  safe-return abuse, secret scan, token/PII log scan, and private-endpoint bundle/network inspection;
- offline, stale, partial, unavailable, conflict, replay, account switching, sign-out cleanup, and
  Emergency Stop failure-path evidence;
- SBOM, vulnerability scan, image digest, deployed revision, and substantive Founder visual review.

## 9. Final PR Evidence Bundle

The final implementation PR is not ready for Founder review unless it contains or links to immutable,
sanitized artifacts for the exact final HEAD. At minimum it includes:

| Artifact | Required content |
|---|---|
| `test-results/wc085/baseline.md` | PR #407/deployment binding, reported defects, initial provider states, and before evidence |
| `test-results/wc085/story-gates.md` | SP-01 through SP-26: result, command/journey, artifact, SHA, owner, and blocker if not passed |
| `test-results/wc085/provider-readiness.json` | Section 4.3 records for Google, Facebook, and email with no secrets or customer PII |
| `test-results/wc085/browser-matrix.md` | Browser/viewport/zoom/locale/direction/theme matrix plus geometry and accessibility results |
| `test-results/wc085/api-capability-ledger.md` | Final operation, owner, disposition, generated client, channel mapping, and approval for every capability |
| `test-results/wc085/final-evidence.md` | Commands, Docker image IDs, results, scans, final HEAD, deployed revision/images, and known limitations |
| PR body | Story checklist linked to the artifacts; explicit authorization boundaries; no blanket completion sentence |

Every `PASS` must identify reproducible evidence. `BLOCKED`, `DEFERRED`, `NOT_RUN`, fixture-only,
and local-only results are not completion. If any required story is not `PASS`, the PR title/body and
status must say `PARTIAL` or `BLOCKED`, and WC-085 remains incomplete.

Contract fixtures, mocks, CI, a successful image build, and a deployment workflow are supporting
evidence only. SP-03 through SP-06 require the exact authorized Demo deployment and real provider or
delivery boundary. SP-09 through SP-26 require browser/API qualification against the exact deployed
Demo revision wherever the assertion crosses a runtime, identity, service, persistence, browser, or
integration boundary. If Demo deployment is not authorized, those rows remain `NOT_RUN` or `BLOCKED`;
local or CI evidence cannot promote them to `PASS`. Pure schema/static assertions may bind to final
HEAD, but they do not complete a story whose gate also names deployed behavior or Founder review.

## 10. Rollback And Release Boundary

- Auth repairs are independently reversible without deleting customer identity or provider data.
- Each provider has independent enable and rollback operations. Rollback disables both Keycloak
  broker exposure and the reviewed manifest projection, then verifies the UI fails closed.
- Provider credential rotation or rollback never requires application-source changes.
- Portal contract changes are additive and version-compatible unless a separately accepted breaking
  migration exists. Generated clients and consumers move together.
- Build once and promote the same accepted digest. Plan acceptance, implementation authorization,
  provider mutation, Demo deployment, Demo proof, UAT, Production, customer traffic, PR approval,
  and merge are separate decisions.
- At least one real, fully qualified provider path is mandatory before the authenticated Customer
  Portal can be called customer-accessible. WC-085 requires all three named WC-084 provider paths to
  pass unless the Founder explicitly amends scope; truthful disablement alone does not complete a
  provider story.

## 11. Stops

Stop the affected slice rather than improvise when:

- current-session implementation or exact provider/environment mutation authority is absent;
- a Founder credential, external registration, callback, consent, test identity, or secret-store
  action is missing;
- an owner-approved Goal, Operations, Billing, Marketplace, Profile, or Security contract is absent;
- a provider only redirects but does not complete registration/login/return/sign-out/repeat/failure;
- an enabled provider disagrees across manifest, Keycloak, endpoint, or UI projection;
- tests would use real customer data, expose secrets/PII/tokens, or call Production;
- the Chrome defect cannot be reproduced and the proposed change would speculate or restyle broadly;
- public visual changes exceed the frozen repair boundary;
- browser logic would infer tenant, eligibility, verification, billing, outcome, or success;
- a private PR, WBE, CE, ledger, or provider endpoint would reach the browser;
- a deterministic failure is bypassed, retried without change, hidden by baseline replacement, or
  converted into a known limitation while its story is marked complete;
- final evidence is not bound to one code HEAD and, when deployment is required, its exact deployed
  revision and image digests;
- self-approval, self-merge, direct `main` push, unapproved cloud spend, UAT, Production, or customer
  traffic is proposed.

## 12. Definition Of Done - Story Gates

WC-085 is complete only when every row below is `PASS` on the same final implementation HEAD and its
evidence is present in the final unmerged PR. Founder-approved scope removal requires an explicit
amendment; it cannot be represented as a passing test.

| Story | Completion gate | Mandatory final-PR evidence |
|---|---|---|
| SP-01 | Initial login and registration choices fit at 1366x768 without dialog scroll and reflow at mobile/200% | Auth geometry results and screenshots |
| SP-02 | Google, Facebook, Apple, and email marks, labels, states, focus, contrast, RTL, themes, and zoom pass | Visual/a11y matrix |
| SP-03 | Real Demo Google new registration and returning login reach safe intended targets; sign-out/repeat/failure/rollback pass | Google readiness record and redacted journey evidence |
| SP-04 | Real Demo Facebook isolated-login-app registration/login/return/sign-out/repeat/failure/rollback pass with only approved scopes | Facebook readiness record and redacted journey evidence |
| SP-05 | Real Demo email registration, delivery, expiry/retry, verification, login, return, sign-out, and repeat login pass | Email readiness record and redacted delivery/journey evidence |
| SP-06 | Manifest, secret reference, Keycloak, endpoint, and UI agree; outages fail closed and are observable without secret/PII leakage | Reconciliation and fault-test records |
| SP-07 | All intercepted auth loading/error states stay in a stable modal and remain dismissible, accessible, and reduced-motion safe | Route timing, layout-shift, interaction, and a11y evidence |
| SP-08 | One Close/Escape/backdrop action after any login/register switch returns directly to the captured safe public origin | Navigation state-machine tests |
| SP-09 | Reported Chrome defect has before/after proof and every required browser geometry case has zero prohibited layout failure | Reproduction bundle and browser matrix |
| SP-10 | Authenticated customer sees only authorized relationships and can select/resume the server-owned target with truthful empty/error states | BP authorization plus portal browser evidence |
| SP-11 | Portal text draft/send/retry/reconcile/partial/evidence states pass without transport being presented as completion | Conversation contract and browser evidence |
| SP-12 | Voice capture/pause/review/correct/cancel/send and permission/offline/text-fallback/Stop paths pass | Voice browser and failure evidence |
| SP-13 | Browse/detail plus eligible trial and hire continuation execute through approved idempotent BP operations; unavailable actions are not offered | Marketplace contract, negative, and browser evidence |
| SP-14 | Alerts preserve server order and stable destinations; read/acknowledge never approves or completes the underlying action | Alert API and interaction evidence |
| SP-15 | Portal displays owner-approved BP-mediated customer-global WBE allowance, forecast, assumptions, invoices, payment, consequences, partial/unavailable states with no browser calculation | WBE/BP contract, network, and browser evidence |
| SP-16 | Profile, organization, locale/theme/channels, login methods, security actions, step-up, account switch, and persistence pass owner contracts | Identity/Profile API, assurance, and browser evidence |
| SP-17 | Mobile bottom bar and account drawer expose all required destinations; Billing is truthful; sign-out cleanup is deterministic | Mobile interaction and storage-cleanup evidence |
| SP-18 | Keyboard, screen reader, axe, reduced motion, zoom, RTL, approved languages, safe areas, and light/dark themes pass owned routes | Accessibility and localization matrix |
| SP-19 | Every released capability uses generated BP clients and records semantically equivalent web, WhatsApp, and future-mobile mappings; browser has no private endpoint | Generated-client diff, capability ledger, bundle/network inspection |
| SP-20 | Loading, empty, offline, unavailable, stale, conflict, partial, and error states are distinguishable and no uncertain result is shown as success | Fault-injection and browser state matrix |
| SP-21 | Emergency Stop is visible, keyboard reachable, operational, and within its SLA during navigation, loading, modal, chat, voice, offline, and dependency degradation | Interaction, failure, and latency evidence |
| SP-22 | Public-route before/after review shows only authorized auth and reproduced-defect repairs, with substantive Founder visual acceptance | Frozen-route visual diff and Founder acceptance reference |
| SP-23 | Onboard contains the accepted lightweight fields, completes within the two-minute target, and continues to concise domain-adaptive Induct with confirmation/correction | Timed usability and induction interaction evidence |
| SP-24 | Every active goal traces to declared skill, measure, frequency, explicit customer verification, amendment/version history, and renewal through typed BP commands | Goal contract, state-transition, and browser evidence |
| SP-25 | Every outcome traces to skill, verified goal, measure, cadence, status, evidence, correction, and attribution limits, separating agent performance from external results | Outcome API, evidence, and browser review |
| SP-26 | Operations is server-locked before required verification, unlocks only from owner truth, and goal amendment reassesses dependent work/outcomes without erasing history | Eligibility, amendment, conflict, and history evidence |

### 12.1 Final Release Gates

In addition to all 26 story rows:

1. all Section 9 evidence artifacts exist, contain no secret or customer PII, and reference the same
   final HEAD;
2. final Docker build, tests, browser matrix, generated-client check, SBOM, vulnerability scan,
   secret scan, and author review pass;
3. when Demo deployment is authorized, deployed revision and image digests match the reviewed HEAD,
   and real provider/portal journeys run against that deployment;
4. Solution Architect author review and Platform IT Expert implementability review have no open P0
   or P1 finding;
5. any required targeted owner review is complete in edit mode, its plan repairs are incorporated,
   and the reviewer records no unresolved implementation decision;
6. the PR remains unmerged for Founder review and does not claim completion when any row is blocked,
   deferred, not run, fixture-only, or bound to another revision.

The acceptance key is `(final HEAD, immutable image digest set, Demo revision)` for every
deployment-dependent row. A later code, configuration, realm, secret-reference, or image change
invalidates affected evidence and requires focused requalification. Workflow success without this
key, or evidence captured from the PR #407 baseline, cannot satisfy the WC-085 final gate.

## 13. Solution Architect Author Review

**Status:** PASS - INST-005 author review completed 2026-09-09. This is plan/architecture acceptance
only. It does not approve implementation, provider configuration or activation, cloud mutation,
deployment, the final implementation PR, or merge.

P0/P1 findings repaired in this pass:

1. Added the missing independent email Founder/executor chain and made all external account, secret
  entry, activation, and test decisions non-delegable and non-secret-bearing.
2. Replaced generic owner-gap language with exact operation and state decisions: `VERIFY_GOAL` on
  `submitRelationshipCommand`, server-owned Operations reassessment, WBE
  `getCustomerBillingPortalProjection` behind `getBillingPortalSummary`, fixed Marketplace
  continuation, and explicit identity login-method/security-intent amendments.
3. Added Section 7.1 so every `OPEN`, `PARTIAL`, `BLOCKED`, and `DELIVERED_CANDIDATE` story names its
  authority, dependency order, first falsifiable check, rollback/stop, and final-PR evidence.
4. Prohibited fixture-only, local-only, CI-only, build-only, and deployment-workflow-only completion;
  deployment-dependent acceptance now binds final HEAD, immutable image digests, and exact Demo
  revision and is invalidated by later code/configuration/realm/reference changes.

Remaining prerequisites are external execution gates, not plan gaps: Founder acceptance and fresh
implementation authorization; separate provider/environment mutation authority; Google external
inputs; FA-002/FA-018 and Facebook inputs; email sender/domain/test-mailbox inputs; WBE owner
acceptance and implementation of the customer-global projection; owner acceptance of the goal and
identity contract amendments; authorized Demo deployment/qualification; and substantive Founder
visual acceptance. A missing prerequisite keeps only its dependent row/slice blocked and cannot be
self-approved by INST-005 or INST-010.

Deterministic author checks: exact set equality and single occurrence of `SP-01` through `SP-26` in
Sections 2.2 and 12; no placeholder markers; no obvious embedded credential assignment/value; Markdown
table/heading inspection; and `git diff --check`. These checks validate the plan document only and are
not implementation or activation evidence.

## 14. Platform IT Expert Implementability Review

**Status:** PASS WITH EXTERNAL ENTRY GATES - INST-010 implementability review completed 2026-09-09.
The plan is executable without implementation invention after each named owner/Founder entry gate
passes. This review authorizes no runnable code, provider/cloud mutation, deployment, PR approval,
or merge.

One P1 implementability finding was repaired: Section 7 named behavior and evidence but did not name
the repository anchors, Docker command families, expected pass signals, or per-slice evidence
destinations required by this section. The matrix below supplies those controls. Paths are starting
anchors, not permission for broad refactoring; the executor confirms the nearest owning test before
each first edit.

| Slice | Verdict | Owning anchors and allowed mutation | Validation | Control and evidence |
|---|---|---|---|---|
| S0 Baseline | `YES` after plan acceptance | **Anchors:** `work-contracts/WC-084-capability-ledger.md`, `infrastructure/identity-config/environments/demo.json`; read-only Git/GitHub/deployed-state inspection only. | **Command:** no product executable before capture; Section 9 schema validation runs later in the Docker qualification. **Expected:** every SHA, revision, image, provider state, defect, and story has an attributable value. | **Evidence:** `test-results/wc085/baseline.md`. **Rollback:** none, read-only. **Stop:** unbound revision/image or unsafely redacted evidence. |
| S1 Contract closure | `BLOCKED` pending named owner acceptance | **Anchors:** `architecture/reference/api-specs/business-platform.openapi.yaml`, `architecture/reference/components/customer-portal-solution-contract.md`, `architecture/reference/components/identity-boundary.md`, `src/business-platform/Controllers/`, `src/business-platform/Services/`, `src/billing-engine/`, `web/lib/api/generated/`, `tests/business-platform.Tests/`, `tests/billing-engine/`. | **Command:** `docker compose --profile test-dotnet run --rm test-runner-dotnet dotnet test tests/business-platform.Tests/business-platform.Tests.csproj`; `docker compose --profile test-python run --rm test-runner-python pytest tests/billing-engine -q`; generated-client check in `test-runner-ts`. **Expected:** focused tests pass and regeneration has zero diff. | **Evidence:** `test-results/wc085/api-capability-ledger.md`. **Rollback:** revert contract, client, adapter, and tests together. **Stop:** owner rejection, schema drift, missing channel cell, or invented fallback. |
| S2 Auth UX | `YES` after implementation authority | **Anchors:** `web/components/auth/AuthDialog.tsx`, `web/app/@authModal/`, `web/app/(auth)/`, `web/app/loading.tsx`, `web/components/auth/`, `web/lib/safe-return.ts`, `web/app/globals.css`, `web/tests/e2e/wc083-auth-dialog.spec.ts`. | **Command:** `docker compose --profile test-ts run --rm -v "$PWD:/workspace" test-runner-ts sh -lc 'cd /workspace/web && pnpm test -- --runInBand components/auth lib/safe-return.test.ts'`, then focused auth Playwright. **Expected:** component pass, stable geometry, safe return, and one-action dismissal. | **Evidence:** auth rows in `test-results/wc085/browser-matrix.md`. **Rollback:** revert auth route/CSS/state-machine slice. **Stop:** full-page loading, unsafe return, trapped input, focus loss, or frozen-route drift. |
| S3 Browser defect | `BLOCKED` until deterministic reproduction | **Anchors:** `web/app/(public)/page.tsx`, `web/app/(public)/professionals/`, `web/components/public/`, `web/app/globals.css`, `web/tests/e2e/wc083-screenshots.spec.ts`; mutate only the reproduced owner. | **Command:** WC-083 screenshot/browser command family plus focused WC-085 Chromium reproduction in `test-runner-ts`. **Expected:** pre-fix geometry assertion fails, smallest repair passes, then Firefox and WebKit pass. | **Evidence:** reproduction and before/after rows in `test-results/wc085/browser-matrix.md`. **Rollback:** revert owning CSS/layout change. **Stop:** unreproduced defect or unapproved visual change. |
| S4 Email qualification | `BLOCKED` pending Founder email inputs and exact Demo authority | **Anchors:** `infrastructure/keycloak/waooaw-realm.json`, `infrastructure/identity-config/environments/demo.json`, `tests/identity-foundation/`, `tests/business-platform.Tests/Identity/`; secret values remain outside Git. | **Command:** Identity Foundation pytest in `test-runner-python`, focused Identity provider tests in `test-runner-dotnet`, then authorized deployment workflow and real mailbox journey. **Expected:** reconciliation and every Section 4.3 email journey pass. | **Evidence:** Email object in `test-results/wc085/provider-readiness.json`. **Rollback:** restore reviewed disabled flow/projection without deleting accounts. **Stop:** sender, delivery, mailbox, secret, authorization, or journey failure. |
| S5 Google qualification | `BLOCKED` pending Founder Google inputs and exact Demo authority | **Anchors:** `infrastructure/keycloak/waooaw-realm.json`, `infrastructure/identity-config/environments/demo.json`, `tests/identity-foundation/`, `tests/business-platform.Tests/Identity/`; no direct application-provider integration. | **Command:** same identity Python/.NET Docker checks, then authorized deployment workflow and real Google journeys. **Expected:** manifest/realm/UI/endpoint agreement and every Google journey pass. | **Evidence:** Google object in `test-results/wc085/provider-readiness.json`. **Rollback:** disable broker and manifest projection. **Stop:** callback, consent, mapper, secret, authorization, privacy, or journey failure. |
| S6 Facebook qualification | `BLOCKED` pending FA-002, FA-018, Founder inputs, and exact Demo authority | **Anchors:** `infrastructure/keycloak/waooaw-realm.json`, `infrastructure/identity-config/environments/demo.json`, `tests/identity-foundation/`, `tests/business-platform.Tests/Identity/`; DMA OAuth remains untouched. | **Command:** same identity Python/.NET Docker checks, then authorized deployment workflow and real Facebook journeys. **Expected:** only approved login scopes, full reconciliation, and every Facebook journey pass. | **Evidence:** Facebook object in `test-results/wc085/provider-readiness.json`. **Rollback:** disable broker and manifest projection. **Stop:** app mixing, excess scope, callback, mapper, secret, authorization, privacy, or journey failure. |
| S7 Portal gaps | `BLOCKED` by S1 | **Anchors:** S1 contracts plus `web/app/(authenticated)/`, `web/components/relationships/`, `web/components/portal/`, `web/app/api/`, `web/tests/e2e/wc084-customer-portal.spec.ts`. | **Command:** focused BP `.NET`, Billing `pytest`, and web Jest commands from S1/S2, followed by WC-085 portal Playwright in `test-runner-ts`. **Expected:** contract negative/idempotency/version tests and every changed interaction pass with the coverage gate. | **Evidence:** story rows in `test-results/wc085/story-gates.md`. **Rollback:** revert each vertical contract/client/server/UI slice together. **Stop:** missing owner truth, private call, browser inference, or false enabled command. |
| S8 Regression | `YES` after S2-S7 assembled | **Anchors:** all WC-084/WC-085 source and tests; mutate production code only when a focused failure identifies its owner. | **Command:** Dockerized full BP, Billing, Jest/coverage, and Playwright matrices. **Expected:** all 26 evidence rows populated with no unsupported `PASS`, changed interactive line coverage at least 90%, and no private endpoint. | **Evidence:** `test-results/wc085/story-gates.md`, `test-results/wc085/browser-matrix.md`, `test-results/wc085/api-capability-ledger.md`. **Rollback:** repair only the failing slice. **Stop:** rerun focused owner check before returning to this matrix. |
| S9 Final qualification | `BLOCKED` until final code freeze and exact deployment authority | **Anchors:** future `scripts/wc085_qualify.sh` following `scripts/wc083_qualify.sh`, Section 9 evidence, and PR body; no feature mutation during assembly. | **Command:** `./scripts/wc085_qualify.sh --output test-results/wc085/final-evidence.json`; it delegates executable work to pinned Docker runners. **Expected:** build, tests, coverage, browser, generation, SBOM, Trivy, gitleaks, story/provider counts, and final-HEAD assertions pass. | **Evidence:** complete Section 9 bundle. **Rollback:** invalidate and rerun affected evidence after any relevant change. **Stop:** any story not `PASS`. |

Repository verification confirmed the merged canonical OpenAPI already owns
`getCustomerProfile`, `updateCustomerProfile`, `getCustomerSettings`, `updateCustomerSettings`,
`listCustomerLoginMethods`, `browseMarketplaceProfessionals`, `getBillingPortalSummary`,
`getRelationshipOperations`, and `submitRelationshipCommand`. WC-085 amends these accepted surfaces
or adds only the explicitly named owner operation and identity commands in Section 6.1; INST-010 does
not choose alternate endpoint names or semantics.

Remaining blockers are authority or owner acceptance gates, not executor ambiguity: Founder
provider inputs and mutation/deployment authority; deterministic Chrome reproduction; and Product,
BP, professional, WBE, Identity, Data, Security, and INST-005 acceptance of the exact Section 6.1
contract amendments. Because these amendments decide consequential verification, billing,
authentication, privacy, provenance, and failure behavior, they require one targeted edit-mode owner
review before implementation. That review must repair this plan directly and may not delegate an
unresolved decision to INST-010.

## 15. Targeted Owner Review And Repair

**Review date:** 2026-09-09
**Mode and scope:** Single-pass targeted edit-mode institutional owner review of WC-085 only, using
WC-084, its capability ledger, the Customer Portal and Identity contracts, relevant canonical BP
OpenAPI surfaces, and ADR-003/008/014/034. This review did not implement code, configure a provider
or cloud resource, deploy, accept external evidence, or grant Founder acceptance.

| Decision space | Separate disposition | Findings repaired | Remaining external prerequisites and blocks |
|---|---|---|---|
| Product Owner (INST-011) | **CONCUR - PLAN SEMANTICS REPAIRED** | Fixed initial-release completeness across all 26 stories and all three WC-085 provider journeys; defined Goal review/change wording, Operations lock wording, browse-only Marketplace behavior, Billing partial/unavailable language, provider disabled/failure language, and capability-gated profile/security controls. | Founder plan acceptance and any explicit scope amendment remain Founder decisions. Missing provider proof, Billing owner truth, Marketplace continuation, identity mutation, Goal verification, or Founder visual acceptance keeps its story blocked and prevents a complete-release claim. |
| Data Architect (INST-006) | **CONCUR WITH RETENTION BLOCK** | Added owner/source/version/time fields, deterministic order, immutable Goal/history lineage, Billing family provenance and correction, typed partial/unknown/unavailable/blocked meaning, identity intent/receipt lineage, sanitized provider evidence, and append-only correction rules. | The bounded accepted authority contains no legal/privacy retention schedule for billing, identity audit, or provider evidence. Founder must accept a named schedule before destructive purge or Production retention configuration; those actions remain blocked. The accepted identity idempotency minimum remains 24 hours. |
| Security Architect (INST-007) | **CONCUR - ACTIVATION AND EXECUTION BLOCKED** | Added provider/environment isolation, exact callbacks/scopes, state/nonce/PKCE S256 binding, stable-subject and verified-email rules, non-enumeration timing, five-minute AAL3 freshness, 15-minute single-use intents, safe targets, last-login invariant, no-store/cache/log/PII controls, rollback behavior, and abuse/failure tests. | External provider accounts, credentials/secret versions, FA-002/FA-018, sender/domain/test mailbox, exact Demo mutation/test authority, and runtime security evidence are not present. Each provider remains disabled until its independent gate passes. |
| BP/WBE/Identity/professional component owners | **CONCUR ON PROPOSED SHAPES - S1 BLOCKED PENDING FORMAL ACCEPTANCE** | Corrected `VERIFY_GOAL` to the canonical `kind` discriminator; defined verify/change-request effects and Operations reassessment; pinned every existing Marketplace continuation operation ID; completed WBE customer-global projection boundaries; and specified identity intent/removal methods, headers, responses, lifecycles, errors, and safe-target constraints without browser inference. | Canonical OpenAPI and owner contracts do not yet contain the new Goal discriminator, private WBE projection, or three identity operations. Their named owners plus INST-005 must formally accept the amendments before implementation; generated clients and contract fixtures must then agree. |

**Overall status:** **OWNER-REPAIRED PLAN; BLOCKED BEFORE IMPLEMENTATION AND EXTERNAL
QUALIFICATION.** No reviewed concern requires INST-010 to invent customer semantics, data lineage,
security policy, or component shapes. S1 remains blocked by formal named-owner acceptance; provider
activation and Demo qualification remain blocked by their independent Founder/external gates; exact
Production retention configuration remains blocked by the named schedule decision. External provider
accounts, credentials, runnable implementation, deployment, final evidence, Founder visual/plan/PR
acceptance, merge, and WC-085 completion are not claimed.
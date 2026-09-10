# WC-085 - WC-084 Remediation And Evidence Closure

**Office:** Chief Solution Architect (INST-005)
**Implementation executor:** Platform IT Expert (INST-010), Skills 4 and 16 for application code;
Skill 17 only for separately authorized environment configuration, deployment, and qualification
**Assigned by:** Founder instruction, 2026-09-09
**Status:** PARTIAL; Founder narrowed the current task on 2026-09-09 to handover preparation,
Java-experiment deletion, and safe parking on draft PR #409. No further feature implementation.
**Start here:** [WC-085 handover](WC-085-handover.md); Section 18 controls continuation and overrides
historical execution instructions below. A new session needs its own explicit authorization.
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

### Current-Session Execution Amendment

The Founder authorized WC-085 implementation and the following additional Demo requirement on
2026-09-09. Execute independently with deterministic, token-efficient tooling; do not dispatch
additional institutional reviewers without a Founder request. Use Docker for all application,
infrastructure, and test execution. Virtual environments are prohibited. Batch Docker qualification
at complete story milestones, with focused editor/static checks between small edits.

Demo users may be discarded when Keycloak is replaced. Every fresh Demo deployment must nevertheless
recreate the realm, application client, Google provider, and default customer role; load Google
credentials through environment-specific Key Vault references; and configure the stable public issuer
and registered OAuth callback automatically. Verify a redirect to Google after deployment. A returning
Google user must be able to recreate their local account without administrator changes. Persistent
Keycloak storage and a custom secret importer are outside this amendment. Credentials must not be
embedded in images, Git, Terraform values, or evidence. This requirement supplements SP-03 and SP-06;
it does not replace real provider-journey acceptance or authorize unrelated environments.

Creative UI decisions remain within the accepted WAOOAW visual contracts and frozen public-route
boundary. Delivery uses the staged PR and Demo acceptance sequence below; every PR records all story
statuses and attributable evidence. Blocked or unexecuted gates must never be reported as passing.

### Plan Gap-Closure Amendment - 2026-09-09

**Authority:** Founder instruction in the current conversation to bridge the reviewed plan gaps.
This amendment controls conflicting execution, sequencing, review, and evidence wording below.
It authorizes this plan repair only. It grants no new implementation, provider, cloud, expenditure,
customer-traffic, approval, or merge authority and does not supply missing owner acceptance.
Sections 13-15 retain their dated review records; their historical verdicts are not fresh acceptance
of this amendment or proof that their outstanding prerequisites have been satisfied.

#### Delivery And Acceptance Sequence

1. Submit an unmerged **engineering candidate PR** after applicable local Docker checks, author
  review, and the repository's commit-bound pre-PR checks pass. Include all 26 story statuses and
  label the PR `PARTIAL` while any full story gate remains open. Deployed checks may be `NOT_RUN`
  with their named dependency; they are not prerequisites for reviewing the engineering candidate.
2. The Founder decides whether to merge that bounded candidate. Merge establishes a code baseline,
  not provider activation, Demo acceptance, WC-085 completion, or permission to deploy.
3. With separate current authority for the exact environment, provider operations, and tests, use
  the existing deployment entry point and successful exact-current-main release. Do not add a
  branch-deployment bypass. Promote its immutable image digests without rebuilding for acceptance.
  If current main has advanced, qualify the newly selected release; do not attach old evidence to it.
4. Run the real Demo journeys and applicable failure, privacy, geometry, and Stop checks against that
  deployment. A failed gate leaves the story open. Any repair follows another unmerged engineering
  PR, Founder merge, and authorized deployment, then focused requalification of affected evidence.
5. Submit an unmerged **acceptance-evidence PR** containing the final story matrix and immutable
  release evidence. This PR may be documentation-only and have a different HEAD from the deployed
  code. Founder review, visual acceptance, and merge remain protected decisions. Declare WC-085
  complete only when every required story passes; an evidence PR with open gates remains `PARTIAL`.

The deployment acceptance key is `(release code SHA, immutable image digest set, Demo revision)`.
Bind the reviewed configuration digest, Keycloak revision/realm digest, provider secret references
and versions, and dependency evidence to that key where applicable. Record the evidence PR HEAD
separately. Evidence-only commits do not require rebuilding unchanged application images. A code,
configuration, realm, secret-reference, image, or relevant dependency change invalidates affected
results and requires requalification; pure documentation changes do not invalidate runtime proof.
All completed stories must apply to the final accepted release tuple, not a mixture of deployments.

#### First Usable Milestone And Prerequisite Handling

The first usable milestone is one real Demo authentication path into the authorized Customer Portal:
new registration, returning login, safe return, sign-out, repeat login, and truthful authorized or
empty portal entry. Prioritize Google reconstruction and qualification under its separately recorded
authority when its prerequisites are ready. If it is blocked, qualify another independently ready,
authorized provider. This milestone is not full WC-085 acceptance and grants no public customer traffic.

Preserve all SP-01 through SP-26 and Google, Facebook, and email in scope. No blocked feature becomes
complete through a disabled control or a scope inference. Only a Founder scope amendment removes it.
S0 captures the baseline; S2/S3 and independently ready provider chains may proceed without S1 closure.
Within S1/S7, accept and implement each coherent owner-contract slice independently; do not hold an
accepted Billing slice for an unrelated Identity decision, or vice versa. S8/S9 assemble completed
slices and retain every remaining gate explicitly. Slice numbers express dependencies, not a global
serial queue that makes one blocked provider stop all progress.

Use the existing capability/story ledgers as the prerequisite register, not another tracking document.
Each open dependency records: affected stories, exact missing decision/input, accountable owner,
authority or acceptance reference, current status, next authorized action, and the check that closes
it. Reuse Sections 6.1 and 15's exact proposed shapes and recorded concurrences; request only the
outstanding formal acceptance or decision. Do not repeat the full plan review or invoke additional
institutions without a Founder request. Missing acceptance blocks only its dependent implementation.

Provider qualification may temporarily enable the broker for approved test identities only when
that exact Demo test configuration is authorized. General provider availability stays disabled until
the complete provider gate passes. Record this controlled test state separately from customer-ready
availability; never mark a provider ready merely to make the qualification journey possible. If the
approved configuration cannot isolate the qualification audience, stop for a decision rather than
invent an access mechanism. Failure restores the reviewed disabled state and preserves account history.

#### Validation Cadence And Offline Stop

After a substantive change, use the cheapest relevant editor/static check before further edits.
Run focused Docker behavior tests at a complete behavior/story milestone before moving to another
implementation slice; use an earlier focused Docker test when needed to resolve a concrete behavior
uncertainty. Broad Docker/browser campaigns run at assembled boundaries, not after each small edit.
Editor checks guide iteration but do not substitute for the Docker evidence required by Section 8.
Perform author review and required executable gates; any additional institutional review requires an
explicit Founder request. Existing owner acceptance remains necessary and cannot be self-issued.

For SP-21, distinguish reachable transport from complete client disconnection. With a reachable Stop
channel, measure the existing end-to-end SLA to confirmed runtime halt, including the named degraded
states. During complete disconnection, keep Stop visible and keyboard reachable, identify delivery as
unconfirmed, and never display local acknowledgement, queued intent, or elapsed time as remote halt.
On reconnection, use the existing authenticated Stop/status contract to reconcile the actual outcome;
do not claim success or invent automatic replay semantics. Test browser offline separately from CE,
identity, ordinary API, and adapter outages because their effects on the Stop channel differ.

Any runtime watchdog or disconnect-triggered halt must come from an already accepted owner contract
and have independent runtime evidence. This amendment creates neither such a mechanism nor a waiver
of the constitutional Stop SLA. If the accepted contract requires a remote halt guarantee during total
disconnection that the implementation cannot prove, SP-21 remains `BLOCKED` pending the named Stop
owner and Founder decision. UI accessibility and honest uncertainty alone do not complete SP-21.

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
Every story must satisfy its Section 12 completion gate on the final accepted release tuple, and every
evidence reference must be included in the final unmerged acceptance-evidence PR.

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
7. enable general provider availability in Demo only after all provider-specific checks pass; otherwise restore the
   disabled manifest and broker state and record the accountable blocker.

The dependency order is independent for each provider: Founder-owned external prerequisite and
secret-store entry -> reviewed non-secret manifest/realm diff -> focused schema and realm validation
-> separately authorized Demo reconciliation and isolated test enablement -> deployed endpoint check
-> real new/returning/failure journeys -> general enable decision. Email follows the same order using sender/domain, Keycloak email flow,
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
| 1. Contract closure | Goal/Operations, Billing, Marketplace, Profile/security, and channel mappings, each as a bounded owner slice | Relevant named-owner acceptance; unrelated pending slices do not block | Accepted contracts, OpenAPI diff, capability ledger, generated-client no-drift |
| 2. Auth UX | Compact geometry, in-modal loading/error, explicit origin/dismissal, safe returns/focus | Auth design boundaries accepted | Focused component/navigation/geometry/accessibility tests |
| 3. Browser defect | Reproduce and repair the reported Chrome defect | Reproduction evidence exists | Before/after geometry and cross-browser focused checks |
| 4. Email qualification | Complete real Demo email path | Sender/domain/test mailbox and mutation authority | Sanitized full-journey provider record |
| 5. Google qualification | Configure and prove Google independently | Founder Google inputs and exact Demo authority | Sanitized full-journey provider record or disabled blocker |
| 6. Facebook qualification | Configure and prove Facebook independently | FA-002/FA-018 and exact Demo authority | Sanitized full-journey provider record or disabled blocker |
| 7. Portal gaps | Implement generated-client-backed Goal, Operations, Billing, Marketplace, Profile/security, and navigation closure | Corresponding Slice 1 contract accepted | Focused contract/component/API/browser evidence |
| 8. Regression | Requalify all 26 stories, authorization, privacy, cache, accessibility, and Emergency Stop | Slices 2-7 assembled | Complete story matrix with no unsupported pass |
| 9. Final qualification | Submit engineering candidate; after Founder merge and separate deployment authority, qualify the immutable current-main release and submit acceptance evidence | Section 1 staged delivery gates; final release tuple fixed | Release-bound evidence bundle and unmerged acceptance-evidence PR; open stories remain PARTIAL |

Apply the Section 1 amendment's validation cadence: cheap editor/static feedback between small edits,
focused Docker behavior qualification at a complete milestone before opening another implementation
slice, and broad Docker/browser campaigns only at assembled boundaries. Run an earlier focused Docker
check when a concrete uncertainty requires it; do not repeat broad qualification for every edit.

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

The engineering candidate PR requires attributable local evidence and explicit remaining gates, not
pre-merge Demo proof. The final acceptance-evidence PR contains or links to immutable, sanitized
artifacts for the accepted release tuple under Section 1. At minimum the bundle includes:

| Artifact | Required content |
|---|---|
| `test-results/wc085/baseline.md` | PR #407/deployment binding, reported defects, initial provider states, and before evidence |
| `test-results/wc085/story-gates.md` | SP-01 through SP-26: result, command/journey, artifact, release SHA, owner, and blocker if not passed |
| `test-results/wc085/provider-readiness.json` | Section 4.3 records for Google, Facebook, and email with no secrets or customer PII |
| `test-results/wc085/browser-matrix.md` | Browser/viewport/zoom/locale/direction/theme matrix plus geometry and accessibility results |
| `test-results/wc085/api-capability-ledger.md` | Final operation, owner, disposition, generated client, channel mapping, and approval for every capability |
| `test-results/wc085/final-evidence.md` | Commands, Docker image IDs, results, scans, release code SHA, configuration/dependency bindings, deployed revision/images, separate evidence PR HEAD, and known limitations |
| PR body | Story checklist linked to the artifacts; explicit authorization boundaries; no blanket completion sentence |

Every `PASS` must identify reproducible evidence. `BLOCKED`, `DEFERRED`, `NOT_RUN`, fixture-only,
and local-only results are not completion. If any required story is not `PASS`, the PR title/body and
status must say `PARTIAL` or `BLOCKED`, and WC-085 remains incomplete.

Contract fixtures, mocks, CI, a successful image build, and a deployment workflow are supporting
evidence only. SP-03 through SP-06 require the exact authorized Demo deployment and real provider or
delivery boundary. SP-09 through SP-26 require browser/API qualification against the exact deployed
Demo revision wherever the assertion crosses a runtime, identity, service, persistence, browser, or
integration boundary. If Demo deployment is not authorized, those rows remain `NOT_RUN` or `BLOCKED`;
local or CI evidence cannot promote them to `PASS`. Pure schema/static assertions bind to the reviewed
code SHA, but they do not complete a story whose gate also names deployed behavior or Founder review.

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
- final evidence is not bound to the accepted release code SHA and, when deployment is required, its
  exact deployed revision and image digests; an evidence-only PR HEAD is recorded separately;
- self-approval, self-merge, direct `main` push, unapproved cloud spend, UAT, Production, or customer
  traffic is proposed.

## 12. Definition Of Done - Story Gates

WC-085 is complete only when every row below is `PASS` for the same final accepted release tuple and
its evidence is present in the unmerged acceptance-evidence PR. Founder-approved scope removal requires an explicit
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
| SP-21 | Emergency Stop is visible and keyboard reachable in all named states; reachable-channel halt meets its SLA; total disconnection never reports unconfirmed delivery as a halt and is reconciled under Section 1's offline contract; any required but unproven runtime disconnect guarantee remains blocked | Interaction, transport-specific failure, confirmed runtime halt/latency, and reconciliation evidence |
| SP-22 | Public-route before/after review shows only authorized auth and reproduced-defect repairs, with substantive Founder visual acceptance | Frozen-route visual diff and Founder acceptance reference |
| SP-23 | Onboard contains the accepted lightweight fields, completes within the two-minute target, and continues to concise domain-adaptive Induct with confirmation/correction | Timed usability and induction interaction evidence |
| SP-24 | Every active goal traces to declared skill, measure, frequency, explicit customer verification, amendment/version history, and renewal through typed BP commands | Goal contract, state-transition, and browser evidence |
| SP-25 | Every outcome traces to skill, verified goal, measure, cadence, status, evidence, correction, and attribution limits, separating agent performance from external results | Outcome API, evidence, and browser review |
| SP-26 | Operations is server-locked before required verification, unlocks only from owner truth, and goal amendment reassesses dependent work/outcomes without erasing history | Eligibility, amendment, conflict, and history evidence |

### 12.1 Final Release Gates

In addition to all 26 story rows:

1. all Section 9 evidence artifacts exist, contain no secret or customer PII, and reference the same
  accepted release tuple, with the evidence PR HEAD recorded separately;
2. final Docker build, tests, browser matrix, generated-client check, SBOM, vulnerability scan,
   secret scan, and author review pass;
3. separately authorized Demo deployment follows Founder merge of the engineering candidate;
  revision and image digests match the selected current-main release code SHA, and real provider/portal
  journeys pass against that deployment; absent authority or evidence keeps completion blocked;
4. the assigned executor's author review has no unresolved P0 or P1 finding; Sections 13-15 are
  historical plan reviews, not a requirement to dispatch those offices again;
5. required formal owner acceptances are recorded for changed contracts and no implementation
  decision remains unresolved; additional institutional review occurs only on explicit Founder request;
6. the PR remains unmerged for Founder review and does not claim completion when any row is blocked,
   deferred, not run, fixture-only, or bound to another revision.

The acceptance key and evidence invalidation rules are defined in the Section 1 amendment. Workflow
success without that key, or evidence captured from the PR #407 baseline, cannot satisfy the WC-085
final gate. Evidence-only PR commits do not change the deployed release identity.

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

## 16. Google-First Execution Decision - 2026-09-09

The Founder explicitly renewed current-session implementation authorization and authorized preparation
of the consolidated owner-decision packet below. Facebook FA-002/FA-018 and email sender/test-mailbox
prerequisites are not ready. Execute and prove Google first; do not implement or activate Facebook or
email until the Founder resumes those provider phases after Google proof. Keep their Demo choices
disabled and record SP-04/SP-05 as `DEFERRED_BY_FOUNDER`, never `PASS`.

This is a sequencing decision, not removal of stories from WC-085. All 26 stories remain in the final
scope; the first Google milestone and its engineering PR remain partial WC-085 delivery. Existing
Google reconstruction authority and secret references are reused. No new cloud deployment, provider
account change, expenditure, customer traffic, or merge authority is inferred from code authorization.
Request the exact next Demo action before it blocks qualification; do not repeat credential requests
whose non-secret bindings are already recorded. Secrets never pass through chat or this document.

## 17. Consolidated Outstanding Owner-Decision Packet

**Status:** D-GOAL was ACCEPTED by the Founder on 2026-09-10; D-BILLING and D-IDENTITY remain
PREPARED FOR DECISION, NOT ACCEPTED;
D-TENANT has Founder-authorized scope as recorded in Sections 17.1-17.2, not completed enforcement
or acceptance of an unspecified interface. No additional reviewer was invoked. Sections 6.1
and 15 supply the proposed semantics and existing concurrences; this packet identifies only the
remaining formal owner acceptances. Approval to prepare it is not approval of the contracts.

| Decision | Proposed contract to accept without reopening settled design | Required acceptance and closing check | Affected stories |
|---|---|---|---|
| D-GOAL | **ACCEPTED — Founder, 2026-09-10.** Section 6.1 `VerifyGoalPayloadV1` on `submitRelationshipCommand`, exact immutable goal version, both expected versions, idempotency, `AAL3_FRESH`, append-only decisions, and server-owned Operations reassessment after material amendment. The payload uses the existing canonical `commandKind` discriminator; this is the established wire name described as `kind` in the proposal. `AMEND_GOAL` and `REPLACE_GOAL` do not verify. | Founder acceptance binds the BP/professional owner and INST-005 decision to this Section 6.1 revision with its recorded Product/Data/Security concurrence. Generated-client and negative/state-transition fixtures must prove change-request, stale/conflicting verification, relock, and preserved history. | SP-24, SP-25, SP-26 |
| D-BILLING | Section 6.1 private WBE `getCustomerBillingPortalProjection` with all mandatory allowance, forecast, invoice, payment, consequence, and per-family provenance/freshness fields; BP relays through existing `getBillingPortalSummary`. No relationship substitute or browser-derived money. | WBE/BP owners and INST-005 formally accept the private/public contract revisions with recorded Product/Data/Security concurrence. Missing owner families must produce typed partial/unavailable results rather than zero or complete success. | SP-15 and its SP-17 destination |
| D-IDENTITY | Section 6.1 link-intent, remove-method, and security-action-intent operations with exact methods, headers, response types, Keycloak proof, fresh assurance, single-use expiry, safe-target binding, and last-usable-method protection. | Identity/BP owners and INST-005 formally accept the component/OpenAPI revisions with recorded Product/Data/Security concurrence. Negative fixtures must prove no mutation for stale assurance/version, cross-account access, replay, or removal of the last usable path. | SP-16 and account-switch/sign-out dependencies in SP-17 |

For each decision, record `ACCEPTED`, `CHANGES_REQUIRED`, or `DEFERRED`, the accountable authority,
exact accepted revision/reference, and any bounded correction. Until that record exists, dependent
implementation remains blocked. Existing reads, Google authentication, and independent accepted
contracts may proceed. Do not bypass ownership by treating this packet as a new API specification.
The Founder may request the named-owner reviews explicitly; none is dispatched automatically.

The legal/privacy retention schedule identified in Section 15 remains a separate gate for destructive
purge and Production retention configuration, neither of which belongs to this Google-first delivery.
Google acceptance does not require adding these three new command/projection families: the first
portal entry uses existing authorized reads and truthful empty/unavailable states. It must not expose
enabled Goal, Billing, or Identity mutations whose owner contracts or runtime implementations are absent.

### 17.1 Customer Isolation Prerequisite And Deployment Authority

**Current execution override - 2026-09-09:** the Founder mandated the established C#/Python/JS
stack and instructed execution. Current EA/Solution and Data amendments supersede the historical
tenant-publication and Java decisions below. Standard Keycloak authenticates; BP provisions the
workspace in C# and resolves current membership from the validated issuer/subject. ADR-003 now
explicitly permits that customer-path lookup with independent downstream checks and database RLS.
No runtime Keycloak writer or custom Java component is part of the replacement path.
The contract-authoring gap is resolved; local backend, real-host and web checks pass as recorded in
`test-results/wc085/final-evidence.md`. Real Google, restored-identity continuity, downstream adoption,
browser switching and release gates remain open. Unadapted customer endpoints fail closed. This is
a partial engineering milestone, not any full WC-085 story PASS or deployment authorization.

The Founder subsequently selected **complete customer tenant provisioning before real Google
qualification**, rejecting authentication-only proof in the shared synthetic tenant as the first
acceptance milestone. The Founder also authorized Google-only Demo deployment and qualification
after Founder review/merge and required cost/security gates, using existing Key Vault references,
with no DNS, UAT, or Production changes. This conditional authorization does not waive provisioning,
approved test-account consent, or the immutable release/deployment gates.

**D-TENANT: FOUNDER-AUTHORIZED; EXACT PROVISIONING CONTRACT AND ENFORCEMENT EVIDENCE PENDING.**
On 2026-09-09 the Founder authorized D-TENANT and a lightweight constitutional-enforcement
documentation pass for necessary ADR/claim updates, following clarification that customer isolation
includes billing and all downstream services, not only BP/Identity. This accepts the isolation-first
scope below; it does not certify implementation or assign additional constitutional offices.
The accepted Identity contract Sections 1, 2, 3.1,
and 5 require BP-minted tenant/account truth and a later Keycloak-signed tenant claim. The current
`IdentityService.CompleteRegistrationAsync` only stores an account UUID on the registration;
`IdentityRegistrationRecord` has no tenant anchor; the web completion path navigates to `/home`
without obtaining a new tenant-bearing token. Demo currently hardcodes one synthetic tenant in its
realm mapper. These implementation facts do not satisfy independent customer provisioning.

Authorized completion requirements; exact service/schema/permission revisions remain to be recorded:

- BP/Identity/Data define the durable account, tenant, initial membership, and issuer/subject binding;
  uniqueness and transaction boundaries prevent concurrent/retried completion from creating duplicates.
- BP remains the only tenant-minting authority. Keycloak receives only committed, server-owned tenant
  and membership attributes through a private least-privilege provisioning interface. Security and
  INST-005 must accept its exact credential scope, endpoint permissions, and trusted attribute rules;
  browsers and users cannot edit those attributes. Do not reuse a broad administrator credential.
- Owners define partial-failure/outage/retry reconciliation between the BP transaction and Keycloak
  attribute publication. A pending publication must not return a false completed portal-ready outcome;
  use an accepted existing response or formally amend the schema before implementation.
- Identity/Web owners define the Keycloak session-renewal handoff and post-renewal checks without
  minting application tokens or injecting a browser-supplied tenant. Returning login must recover the
  same authorized tenant; account switching must remove the prior account's protected state.
- Owners define identity continuity when disposable Demo Keycloak subjects are recreated while BP
  data survives, or a bounded synthetic-data reset when both are disposable. Email equality alone must
  never relink accounts. This decision must respect the approved no-persistent-Keycloak constraint.
- Qualification must use two distinct approved Google test identities and prove distinct tenant
  claims/memberships, same-account retry/return stability, cross-tenant denial at API and database,
  no pre-account protected access, and failure/recovery without duplicate tenants or false completion.
  Remove the shared Demo tenant mapper only with the replacement path qualified.

Required contract closure: record one exact provisioning and recovery revision within the applicable
BP/Identity, Data, Security, and INST-005 authority boundaries, including existing schema/API compatibility
and downstream owner obligations in Section 17.2. No new office or reviewer has been invoked. Founder
scope authorization is recorded here; this packet is not itself a new service interface, schema, or
permission grant. Dependent implementation remains pending that exact contract; real-account
deployment/qualification remains pending implementation, evidence, merge, and release gates. Other
already accepted local engineering may proceed. Do not replace the missing handoff with a per-request
tenant lookup, a random Keycloak mapper, or a shared tenant, which would bypass the accepted boundary.

### 17.2 Lightweight Constitutional Enforcement Pass - 2026-09-09

**Subsequent authorized boundary repairs:** the Founder authorized required-office repair calls
with edit authority, while retaining routine implementation with INST-010. Solution authored the
Identity Boundary amendment; Data authored `architecture/reference/product/wc085-identity-provisioning-data-contract.md`;
Security authored `architecture/reference/security/wc085-identity-publication-security-contract.md`
and tested the pinned stock Keycloak permissions; EA authored
`architecture/reference/product/wc085-identity-architecture-decision.md` for the one resulting conflict.
These are completed authorship calls, not another review chain or unprovided Founder approval.
CB-009 consolidates their outcomes and supersedes earlier pending-office wording in Section 17.1.
Publication remains blocked because tested writer grants also permit credential/broker changes.
Separately authorized administrative publication would change unattended onboarding; retaining
autonomy requires an explicitly authorized credential-enforcement architecture change. Neither is
implicitly approved by office delegation. No broader BP credential, real Google acceptance, or
deployed tenant-isolation proof is claimed.

**Decision:** tenant provisioning starts in BP/Identity; customer isolation is a platform-wide
obligation. One signed tenant claim is an identity anchor, not sufficient authorization for every
resource or command. Current membership, relationship, assurance, and Decision Space checks remain
required by their owning contracts. Registration creates no payment, employment, or spend authority.

**ADR assessment:** ADR-003 already explicitly covers billing and requires isolation at API, service,
and database layers, including trusted tenant propagation. The Identity Boundary Sections 1.7, 2,
3.1, and 5 already assign tenant minting to BP and credentials to Keycloak. ADR-034 retains WBE's
billing ownership. No new ADR is required merely to implement these existing boundaries. Exact
provisioning, reconciliation, and renewal details belong in the owning component/API/data contracts.
If closure changes an accepted architectural choice, record that bounded delta for EA-authorized
ADR amendment before implementing it; INST-010 does not create or amend an ADR under this authority.

**Claim assessment:** no new constitutional claim or change to an existing claim's normative statement
is justified by this gap. It is missing implementation/evidence of existing obligations. The following
mapping records required evidence, not a claim-status upgrade:

| Existing authority | D-TENANT enforcement obligation | Required evidence |
|---|---|---|
| ADR-003; Identity Boundary Sections 1.7, 2, 3.1, 5 | BP creates durable tenant/account/membership truth; only validated Keycloak claims supply the customer-session tenant; current resource authority is checked separately. | Two-account provisioning, retry/concurrency, publication failure/recovery, renewed session, and returning-account stability. |
| C-026; ADR-003 | Preserve three-ledger ownership and database isolation; tenant isolation does not replace stakeholder/schema separation. | Cross-tenant reads and writes denied using actual application DB roles; missing/wrong tenant and pooled-connection reuse fail closed; no superuser/RLS-bypass test substitute. |
| C-052; C-062 | Customer execution history and reasoning remain isolated; every inference context is scoped to one organization. | Cross-customer conversation, retrieval, memory, and inference-context denial, including reused workers/caches. |
| C-023 | Record required constitutional evidence before governed effects; never present a pending or failed provisioning step as completed. | Correlated, privacy-safe evidence for provisioning/recovery and governed commands; no tokens, secrets, or another customer's data in customer-visible errors/evidence. |

**Downstream acceptance checklist:** apply each row to the actual enabled Google-first journey.
For a deferred surface, prove it cannot be reached through UI, direct API, or background execution;
record `DEFERRED/DISABLED`, never `PASS`. An enabled surface without evidence blocks qualification.

| Surface and accountable implementation boundary | Required isolation check |
|---|---|
| BP/Identity and Web session | Two approved Google identities receive distinct tenants; guessed account/resource IDs cannot cross the boundary; pre-account sessions cannot read protected data; switch/sign-out removes prior protected state. |
| WBE and BP billing facade | Customer-global means across the authenticated customer's relationships, never across customers. Invoices, allowances, payment history, forecasts, and payment effects use authoritative tenant/resource ownership. Reject swapped invoice/payment/customer IDs. Bind authenticated provider webhooks to server-owned payment/customer records, not caller-selected tenants; duplicate events cannot duplicate effects. D-BILLING's separate projection decision is not implicitly accepted. |
| CE, professional runtime, and AI runtime | Propagate trusted tenant context and independently enforce resource/relationship authority at service boundaries. Missing or mismatched context denies before execution, ledger mutation, inference, or spend. A tenant claim never expands Decision Space. |
| Conversations, files, retrieval, and caches | Authorize reads, writes, downloads, search, and retrieval to the same tenant and permitted relationship; object paths, signed links, cache keys, and model context cannot expose another customer's content. |
| Jobs, queues, callbacks, and retries | Preserve authenticated server-established tenant/resource provenance across asynchronous work; reject missing/mismatched context and recheck applicable current authority before effects. Retried work cannot execute for a different tenant. |
| Databases, ledgers, and operational access | Prove tenant-scoped reads/writes under deployed application privileges and preserve ledger separation. Privileged maintenance/support paths need separately authorized, auditable access, not a customer-session bypass. |

**Proof boundary:** configuration binding, callback tests, and disposable Keycloak reconstruction
already recorded in milestone evidence do not prove any untested checklist row. Bind qualification
to the exact release/configuration identity under Section 1; no platform-wide security/privacy or
Production-readiness claim follows from this documentation pass. Facebook/email remain deferred,
and existing no-DNS/UAT/Production-change limits remain in force.

## 18. Controlling Handover And Execution Packages - 2026-09-09

### 18.1 Authority, Architecture And Cost Controls

This section supersedes conflicting execution instructions in Sections 1 and 17, not the 26 story
acceptance gates. Historical publication/Java paragraphs are records, not work to execute. The Founder
authorized handover preparation and parking only; the sole new code change in this parking step is
deleting the rejected Java experiment. Existing C#/web/infra work is preserved, not extended.
No feature, deployment, secret, spending, merge, or new institutional review is authorized by parking.

The next executor occupies **Platform IT Expert INST-010**, using Skills 4/16 for application work and
Skill 17 only for separately authorized environment work. Bootstrap once in that new session only
after explicit Founder authorization. Declare Decision Space and obligations; obtain explicit
current-session implementation authorization and a selected package before runnable edits. The
handover prompt does not grant either by itself. Do not repeat bootstrap after compaction.

Fixed architecture: stock Keycloak authenticates; C# BP atomically provisions account, canonical
organisation/tenant and initial OWNER membership. Current membership comes from validated `(iss, sub)`
and `identity.resolve_customer_membership()`, not a tenant claim, browser input or latest registration.
ADR-003's customer-path amendment and ADR-008 Amendment 3 control. Use the CURRENT portions of the
identity architecture, data and security contracts. No custom Keycloak provider, Java, runtime account
writer, new token issuer, new membership service, email-only relinking, shared customer tenant, or
silent reset. Preserve ledger separation and independent downstream authorization. Data's reduced
physical mapping is authored; do not repeat its historical authoring request.

Use one primary implementer. Do not invoke delegates, offices or reviewers unless the Founder
explicitly requests them. Any authorized implementation delegate must explicitly occupy INST-010,
load its compact office guidance and selected skill, and receive exact files, scope, stack, Docker
commands, acceptance/stop criteria and a prohibition on further delegation. Parent retains ownership.
Escalate an exact undecided boundary, not a general request for another architecture review.

Start with the named file/symbol and its nearest test. State one local hypothesis and one falsifying
check; edit only the selected package. Run the focused Docker check immediately after a substantive
edit, before opening another slice. Retry only on changed evidence; at most two local repair attempts
after the initial failure, then report the first causal error, attempts, and required decision.
Do not change runners or expand suites to search for a passing result. Broad checks run at assembled
milestones and required publication gates, not after every small edit. Keep raw output in local
artifacts; report command, runner ID, counts, first causal failure and limitation. Never call build-only
output a test pass. VSTest is the normal xUnit execution platform inside Docker, not a host-test tool.

### 18.2 Saved Implementation Map And Evidence Limits

Paths below are repository-relative. Read only the selected row's files and controlling contract;
this table is a routing map, not permission to scan the whole repository.

| Surface | Exact implementation and test anchors | Current truth |
|---|---|---|
| Storage and provisioning | `infrastructure/postgres/init/29-customer-workspace-provisioning.sql`; `src/business-platform/Infrastructure/IdentityDbContext.cs`; `src/business-platform/Services/CustomerWorkspaceProvisioningService.cs` (`CompleteAsync`, `ResolveAsync`, `ResolveInTransactionAsync`); `tests/business-platform.Tests/Identity/CustomerWorkspaceProvisioningPostgresTests.cs` | Four new identity tables, canonical organisations, atomic completion/replay, proof and current membership. 43 local real-PostgreSQL cases; not a full init-chain or deployed migration proof. |
| Broker proof and journey | `src/business-platform/Services/GoogleWorkspaceProofAdapter.cs` (`IdentityBrokerReadOptions`, `ValidateActor`, `ReadAsync`); `src/business-platform/Services/CustomerIdentityJourneyService.cs`; `src/business-platform/Services/IdentityService.cs`; `tests/business-platform.Tests/Identity/GoogleWorkspaceProofAdapterTests.cs` | Exact-subject read-only broker proof; synthetic HTTP/JWT tests. Actual stock reader/TLS/claim mapping not qualified. |
| HTTP authorization | `src/business-platform/Controllers/IdentityController.cs`; `src/business-platform/Infrastructure/CustomerMembershipMiddleware.cs`; `src/business-platform/Program.cs`; `tests/business-platform.Tests/Identity/CustomerIdentityJourneyHttpPostgresTests.cs`; `tests/business-platform.Tests/Identity/CustomerIdentityProgramHostTests.cs` | Registration start/read/profile/complete and session adapted. Unsupported customer routes deny. Eleven real Program-host cases passed separately. Legacy direct-call tests do not prove public fallback is allowed. |
| Web handoff | `web/app/api/identity/registration/route.ts`; `web/components/auth/RegistrationFlow.tsx`; `web/app/api/wc084-portal-boundaries.test.ts`; `web/components/auth/RegistrationFlow.test.tsx` | Same server-held token resolves session after completion; exact account and expiry required before navigation. Timeouts/cancellation covered; complete cross-tab switching not proven. |
| Demo configuration | `infrastructure/identity-config/environments/demo.json`; `infrastructure/terraform/phase2/modules/workload/identity.tf`; `infrastructure/terraform/phase2/modules/workload/main.tf`; `src/business-platform/Services/IdentityEnvironmentOptions.cs` | Origin/client/callback and manifest bindings repaired locally. Provider readiness disabled; shared synthetic mapper still requires coordinated replacement. No cloud mutation. |
| Reconstruction evidence | `scripts/run_wc085_google_reconstruction.sh`; `scripts/verify_google_deployment.py`; `tests/identity-foundation/test_wc085_google_reconstruction.py`; `tests/pipeline/test_wc085_google_deployment.py` | Two fresh pinned stock Keycloak fixtures passed before final C# integration. Not real Google or final restored-account proof. |

Latest existing-stack evidence: 203 backend identity tests passed, then 11 additional Program-host
tests passed separately; 81 web tests in 12 suites and TypeScript passed. These are pre-parking local
milestones, not one combined 214-test execution, final-commit CI, image qualification or real Google.
The earlier 229-web/30-browser/513-Python/build/scan evidence belongs to the earlier freeze recorded
in `test-results/wc085/final-evidence.md`; it must not be attributed to the current application source.
Historical Java failures do not describe a currently failing C# test. The old rollback fixture needed
new nullable registration AND idempotency columns; that failure was repaired. Preserve the distinction.

### 18.3 Ordered Remaining Packages

Execute H1 first after authorization. H2 follows H1; H3 and H4 follow their named prerequisites.
H5 is the assembled engineering gate; H6 is post-merge, separately authorized deployment/acceptance.
H7-H9 preserve the remaining WC-085 obligations without turning missing contracts into invented code.
Each package updates the existing story/evidence ledgers, not another status system.

| Package / stories | Inputs, exact next work and output | First check, exit and stop |
|---|---|---|
| H1 Full-schema compatibility / SP-03,06,19,20 | CURRENT `architecture/reference/product/wc085-identity-provisioning-data-contract.md`; migration 29, `IdentityDbContext`, provisioning PG fixture above. Rehearse the entire approved PostgreSQL init chain and migration on retained legacy rows using disposable Docker DBs. Keep four identity tables and existing organisations/events/idempotency; no publication tables or fabricated legacy proof. Record role grants, upgrade compatibility and non-destructive rollback/recovery. | Start with `CustomerWorkspaceProvisioningPostgresTests`; then full-chain rehearsal under actual restricted service roles, not only the fixture's selected init 03/20/29 fragments. Two customers, retry/concurrency, commit failure, inactive/legacy denial and pooled-context isolation must pass. Known migration 13 reference to `institutional.billing_profiles(customer_id)` conflicts with migration 12's agent-type shape: report exact first failure; do not repair unrelated billing schema without bounded approval. H1 cannot pass while the selected deployment chain fails. |
| H2 Stock reader and Demo configuration / SP-03,06 | `GoogleWorkspaceProofAdapter`, `Program`, Demo manifest and workload Terraform; ADR-008 Amendment 3 and CURRENT security contract. Bind the exact options in Section 18.4, actual stock reader permissions, signed Google `idp`, verified email, `auth_time`, audience/client and lifetimes. Reuse existing Google vault refs; no reader secret through chat or Git. Local fixture first; actual environment mutation requires separate authority. | Run adapter and Program-host tests, then the pinned stock Keycloak fixture against the final adapter over valid private HTTPS. Prove two allowed GETs; account/password/broker/role writes denied; reader lifetime <=60s and no refresh token. Wrong issuer/audience/client, extra roles, expired/future proof, bad TLS/host, redirects and unavailable dependencies fail closed. Realm-wide read scope is a known residual, not per-user ACL. Missing credential reference/TLS/mapper contract blocks activation, not permission escalation. |
| H3 Membership adoption and usable portal / SP-10 through26 as enabled | Start `CustomerMembershipMiddleware`, `Program`, existing `TenantIsolationMiddleware` and the first enabled controller, normally `src/business-platform/Controllers/EmploymentRelationshipsController.cs`; use `tests/business-platform.Tests/EmploymentRelationshipsControllerTests.cs` and `Infrastructure/CCT_MT01_TenantIsolationTests.cs`. Controlling exact downstream protocol: `wc085-identity-architecture-decision.md` / Exact Internal Membership Operation. Enable one accepted read at a time; profile/settings are separate from registration profile. Follow only that operation's actual call site into CE/PR/AIR/WBE. | First show the current deny, then two validated actors get only their own result. Every enabled receiver independently validates original bearer + allowed mTLS caller/operation and resolves membership with its own DB identity; set both tenant GUCs from resolution. Swapped headers/resource IDs, revocation and lookup outage deny before result/effect. No bypass by merely adding a route attribute or forwarding BP's tenant header. Unadopted REST/gRPC/WSS, files, retrieval, caches, jobs/callbacks and ledgers must be unreachable, not just hidden in UI. Record enabled/disabled operation matrix against Section 17.2. Exact unresolved service call-site details are bounded local inspection, not license for a platform rewrite. |
| H4 Returning/recreated identity and browser cleanup / SP-03,16,17,20 | CURRENT identity decision / First Slice Defaults And Continuity Gate; provisioning `CompleteAsync`, broker adapter, registration route/flow and `web/tests/e2e/wc084-customer-portal.spec.ts`. Stable issuer/subject must reuse IDs. Preserve account/member/proof history. Test same browser, second tab, expired session, switch during pending response, sign-out and repeated login. | First prove same subject returns same account/tenant and a different actor matching stable Google key fails unresolved, never creates/relinks by email. Recreated-actor recovery needs exact accepted retirement/rebinding and old-session denial rules before mutation; if still unspecified, report that boundary for Founder-authorized owner decision. No silent reset or persistent-Keycloak addition. Browser sentinels must find no previous protected state or stale navigation after switch/sign-out. Unresolved recovery keeps fresh-deployment continuity open. |
| H5 Assemble engineering candidate / all affected stories | H1-H4 evidence; existing Section 8 gates and `test-results/wc085/{story-gates.md,final-evidence.md,api-capability-ledger.md}`. Keep draft #409 PARTIAL. Build candidate images, run applicable focused and assembled regression, generated-client no-drift, security/PII scans, changed-interaction coverage and required pre-PR checks. | No old image or old coverage attributed to new source. No full story PASS without its complete Section 12 evidence. Use one fixed code/config image set; record limitations. Founder review/merge is required and does not itself activate Google. |
| H6 Google-only Demo qualification / SP-03,06 and enabled portal | Founder merge + successful exact-current-main release, named Demo/Google/test-identity authority, H1-H5 and approved callbacks/secret refs. Use `.github/workflows/deploy.yaml`; no branch-deploy bypass. Remove the shared synthetic tenant mapper only in the qualified replacement configuration. Facebook/email remain disabled. | Two approved real Google identities create distinct accounts/tenants, complete profile, enter authorized/empty portal, return, sign out and repeat. Prove cross-tenant denial, recovery, rollback, consent/denial and dependency failure. Record release SHA, immutable image set, Demo revision and configuration/realm/secret-reference versions. Synthetic redirect/reconstruction is not acceptance. Stop on any authority, cost, input or isolation gap; no DNS/UAT/Production change. |
| H7 Auth/browser regression / SP-01,02,07,08,09,18,22 | Existing auth repair and `web/tests/e2e/wc085-auth.spec.ts`; Section 5 and browser matrix. Preserve implemented modal geometry/loading/dismissal; do not rewrite working UI. Founder Chrome reproduction context remains an input. | Reproduce the reported Chrome defect before any CSS repair, then owning-rule fix with before/after evidence. Run configured browser projects, viewport/zoom/theme/locale/RTL/accessibility/focus states and frozen-public comparison. No broad restyling; missing reproduction/visual acceptance stays open. |
| H8 Owner-gated portal gaps / SP-13,15,16,19,23,24,25,26 | D-GOAL/D-BILLING/D-IDENTITY in Section 17 remain PREPARED, not accepted. Reuse Section 6.1 exact operation/schema/idempotency/assurance/lineage semantics; canonical `architecture/reference/api-specs/business-platform.openapi.yaml`, `wbe-relationship-workspace.openapi.yaml`, and WC-084 capability ledger are entry anchors. | Select only one accepted contract family. OpenAPI and generated clients precede adapter/UI. Goal amendment relocks, missing billing family is partial/unavailable not zero, last-method removal denies, absent marketplace continuation causes no mutation. Obtain exact outstanding acceptance; no general review chain. Do not fill missing owner decisions with implementation assumptions. |
| H9 Remaining acceptance / SP-04,05 and all26 | Founder resumes Facebook/email separately with Section 4 inputs. Requalify delivered candidates under Section 6.2, browser/Stop/degradation under Sections 7.1/8/12, including timed onboarding and cross-channel mappings. | Facebook/email remain DEFERRED_BY_FOUNDER until resumed, never PASS. Stop offline is unconfirmed until actual authoritative reconciliation, not local acknowledgement. Final acceptance evidence uses one release tuple; submit unmerged evidence PR. WC-085 is complete only when every required gate and Founder acceptance passes. |

### 18.4 Exact Runtime Bindings And Bounded Docker Commands

`IdentityBrokerReadOptions.SectionName` is `IdentityBrokerRead`. Required environment keys are
`IdentityBrokerRead__Enabled`, `__ActorIssuer`, `__PrivateOrigin`, `__AllowedPrivateHosts__0`,
`__ClientId`, `__ClientSecret`, `__ProviderNamespace`, `__TrustConfigDigest` (each abbreviated key uses
the same `IdentityBrokerRead` prefix). `ClientId` is exactly `waooaw-bp-identity-reader`.
Actor issuer is HTTPS with exact `/realms/waooaw`; private origin is allowlisted HTTPS origin `/`;
trust digest is 64 lowercase hexadecimal characters of the accepted trust configuration, not an
invented constant. Provider namespace must be the accepted stable provider identity. The secret is a
vault-backed runtime reference. These bindings are currently NOT qualified in Demo. HMAC uses the
existing `Identity:Hmac` options in `Program.cs`; inspect that options class before binding, do not
guess its field names or introduce another key system.

Existing non-secret coordinates: vault `kv-waooaw-demo`, refs `google-client-id` and
`google-client-secret`; Google callback
`https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io/realms/waooaw/broker/google/endpoint`;
web origin `https://ca-demo-web.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io`;
BP origin `https://ca-demo-business-platform.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io`.
Web callback is `/api/auth/callback/keycloak-google`. Do not substitute the generic callback.

The following runner IDs exist in this container at handover. IDs pin local images, not registry
availability; another machine must use the approved Compose runner build and record its resulting ID.
Do not silently pull a new SDK/browser version. Commands run from `/workspaces/waooaw-wc085`.

```bash
# H1 baseline; select a single test class for a local defect before this namespace gate.
docker run --rm --network host \
  -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:$PWD" -w "$PWD" \
  -e TESTCONTAINERS_HOST_OVERRIDE=127.0.0.1 --entrypoint dotnet \
  sha256:31b4fc3008a0df7285cf42e177b7fe652cb208c0b4ae9902171e0753bacfa598 \
  test tests/business-platform.Tests/business-platform.Tests.csproj \
  -p:RestoreForce=true -p:IsTestProject=true \
  --filter 'FullyQualifiedName~Waooaw.BusinessPlatform.Tests.Identity' \
  --logger 'console;verbosity=minimal'

# H4 focused route/component boundary; this is not the full previous 81-test selection.
docker run --rm -v "$PWD:$PWD" -w "$PWD/web" --entrypoint pnpm \
  sha256:c59b212476b4da92ffd9dd502235afa4dc5a733d32ad1e03402bfb80cf426f3c \
  exec jest --runInBand --runTestsByPath app/api/wc084-portal-boundaries.test.ts \
  components/auth/RegistrationFlow.test.tsx
docker run --rm -v "$PWD:$PWD" -w "$PWD/web" --entrypoint pnpm \
  sha256:c59b212476b4da92ffd9dd502235afa4dc5a733d32ad1e03402bfb80cf426f3c \
  exec tsc --noEmit --incremental false --pretty false

# H2 local configuration regression; does not contact real Google.
docker run --rm -v "$PWD:$PWD" -w "$PWD" --entrypoint pytest \
  sha256:5a833b51dcbb5da88ac473b849ec32656cce0611d731fca361ab7abfe82f3866 \
  tests/pipeline/test_goal006_terraform_foundations.py \
  tests/pipeline/test_wc085_google_deployment.py \
  tests/identity-foundation/test_identity_artifacts.py -q
```

Web commands require the existing installed workspace dependencies; if missing, install from the
lockfile inside the approved runner, never on host. Full-chain migration, actual reader TLS,
cross-service, recovery and real-Google checks do not yet have complete executable coverage: their
first deliverable is the selected package's focused test/rehearsal, not an assertion they already pass.
Reconstruction wrapper requires Docker socket and Terraform fixture prerequisites recorded in the
existing evidence. Do not run it simply to rediscover its inputs.

### 18.5 Publication And Resumption Contract

Continue in `/workspaces/waooaw-wc085`, branch `ib/085/remediation`, existing draft
https://github.com/dlai-sd/waooaw-platform/pull/409. The editor's original worktree is on
`ib/083/auth-dialog` and has unrelated Founder work: do not switch, clean or stage it.
Pre-parking committed HEAD was `bff1bc7cd68252534071ec847be221b021cfdf5f`. The parking commit is
discoverable through the PR's head and commit-bound Author Review; do not hardcode a self-referential
commit SHA into the same commit. Preserve generated local logs/build caches outside the staged set.

Stage only this WC-085 continuation, authorized architecture records, handover and checkpoint.
Do not modify immutable Constitution/Genesis. Review diff, evidence limitations and secret scan;
commit conventionally with WC-085 traceability, push only this branch, and run the existing
`scripts/prepare_pr_body.py --body-file /tmp/pr-body.md --base origin/main` inside Docker after the
final push. The preparer requires local HEAD = remote branch HEAD and runs the applicable real-container
runtime lifecycle gate. Submit that exact prepared body to draft #409; do not bypass a failure or
claim that gate proves BP signup or Google. No new PR, ready-for-review transition, self-approval or
merge. Any new commit requires refreshing the prepared body/evidence.

The next session verifies branch/HEAD/status against #409, loads this section and CURRENT contracts,
then executes the Founder-selected package only. Do not rerun all old suites before any work, repeat
settled architecture selection, restore Java, or read historical records as active instructions.
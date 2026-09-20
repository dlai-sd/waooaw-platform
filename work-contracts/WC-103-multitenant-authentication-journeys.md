# WC-103 - Multi-Tenant Authentication Journeys

## Record Control

| Field | Value |
|---|---|
| Authoring office | Solution Architect (INST-005) |
| Assigned by | Founder instruction in the 2026-09-20 continuous working conversation |
| GitHub issue | #458 |
| Status | IMPLEMENTATION-READY SPECIFICATION - IMPLEMENTATION NOT AUTHORIZED |
| Delivery shape | One atomic authentication quality work component; partial journey closure is not completion |
| Baseline | `origin/main` at `502f70b5`; WC-083, WC-090, WC-092, WC-093, WC-094, WC-098 and WC-099 |
| Governing architecture | `architecture/reference/components/identity-boundary.md`; `architecture/reference/ux/hybrid-application-shell.md` |
| Security contract | `architecture/reference/security/identity-session-security-contract.md` |
| Data contract | `architecture/reference/data/identity-security-data-contract.md` |
| Constitutional basis | C-001, C-002, C-005, C-007, C-023, C-026, C-027, C-048, C-049, C-059, C-063, C-100; ADR-003, ADR-008 |
| Review mode | Founder-requested one-pass Security Architect and Data Architect edit review |

## 1. Objective

Deliver one coherent, privacy-safe authentication boundary for a multi-tenant SaaS customer journey:
authenticate first, explore without account creation, register only when consequential value requires
it, preserve the selected Trial or Hire intent, and make logout terminate all WAOOAW and Keycloak
session state so the next visit starts unauthenticated and the next social login requires account
selection. Every identity attempt observed by WAOOAW must produce privacy-safe forensic evidence,
while constitutional decisions retain separate Evidence First records.

This contract consolidates the remaining authentication obligations into one requirement-to-defect-
journey-to-evidence ledger. A passing aggregate suite, provider redirect, local fixture, or merged
source change cannot substitute for a missing journey acceptance result.

## 2. Authority And Scope

The Solution Architect may specify component responsibilities, interfaces, state transitions,
failure semantics, evidence requirements and implementation acceptance. This document authorizes
only architecture and Work Contract documentation. It does not authorize `src/` or `web/` changes,
database migrations, generated clients, provider-console changes, secrets, cloud mutation,
deployment, customer traffic, Production action, approval or merge.

Before implementation begins, the Founder must explicitly answer the repository implementation-gate
question for WC-103 in the implementing session. Environment and real-provider execution require
separate current authority. Apple and standalone email activation remain independent gates; their
journeys may be implemented dark and tested synthetically without being projected as available.

## 3. Required Inputs

| Input | Required state | Use |
|---|---|---|
| Identity Boundary | PRESENT | Credential ownership, actor binding, registration, session, logout and isolation |
| Hybrid Application Shell | PRESENT | Visitor, Marketplace, Trial/Hire continuation and route-backed auth UX |
| ADR-003 | ACCEPTED | JWT validation and tenant isolation |
| ADR-008 | ACCEPTED | Keycloak broker and provider-neutral authentication decision |
| WC-083/WC-092/WC-093 | MERGED | Modal, safe-return, accessibility and customer-language baseline |
| WC-090/WC-094 | MERGED WITH RESIDUAL ACCEPTANCE | Google/Facebook broker, logout and readiness baseline |
| WC-098 | MERGED | Broker-verified email, actor continuity and registration recovery |
| WC-099 | LOCAL QUALIFICATION; ACTUAL-CLOUD JOURNEY OPEN | Fresh Google selection and integrated customer journey evidence |
| Issue #458 | OPEN | PR and delivery traceability |

## 4. Defect Register

| Defect | Evidence-backed gap | Impact | Severity |
|---|---|---|---|
| AUTH-D01 | Real Google and Facebook callback-to-portal journeys lack exact-release Demo acceptance | Authentication can appear ready without proving customer success | Critical |
| AUTH-D02 | Explicit logout cleanup is merged, but real provider account selection remains locally proven only | Previous account can be silently reused on a shared browser | Critical |
| AUTH-D03 | No complete durable event taxonomy covers all WAOOAW-observed identity attempts | Incident reconstruction and abuse investigation are incomplete | Critical |
| AUTH-D04 | No customer-facing active-session inventory or single/all-session revocation contract is complete | Customers cannot inspect or terminate remote WAOOAW sessions | High |
| AUTH-D05 | Apple policy exists but prerequisites, key rotation, relay handling and acceptance remain blocked | Apple users lack a usable path | High |
| AUTH-D06 | Standalone email is architected but runtime, recovery, abuse and journey evidence are absent | Customers without social login lack a proven fallback | High |
| AUTH-D07 | Refresh rotation, revocation and stale-token denial are not proven across every enabled receiver | A revoked or stale identity may survive at a downstream boundary | High |
| AUTH-D08 | Demo has privacy-safe logs but no complete distributed authentication trace | First causal failures remain expensive or ambiguous to diagnose | High |
| AUTH-D09 | Provider availability can be inferred from configuration before complete journey readiness | An unusable provider may be presented as available | High |
| AUTH-D10 | Revisit-after-logout lacks one explicit no-silent-reauth acceptance invariant across navigation, history and cache | Protected state may appear without a new customer action | High |
| AUTH-D11 | Provider cancellation, failure and missing-email paths are specified across multiple contracts but lack one release-level matrix | Recovery behavior can drift between providers | Medium |
| AUTH-D12 | Operational identity events and Constitutional Audit Ledger events lack one explicit separation and failure policy | Over-collection, ledger merging or Evidence First ambiguity | High |

## 5. Target Authentication Journeys

1. **First social login:** User selects Google, Facebook, or Apple, reviews shared information,
   authenticates with the provider, and enters WAOOAW as a visitor.
2. **Visitor exploration:** Authenticated visitor explores available professionals and services
   without creating a customer account.
3. **Progressive registration:** When the visitor starts Trial or Hire, WAOOAW collects only missing
   essentials, creates the account, and resumes the selected journey.
4. **Returning customer:** User authenticates and lands directly on the appropriate Customer Portal view.
5. **Standalone email:** User verifies their email through Keycloak and follows the same visitor or
   registration journey as social-login users.
6. **Logout:** WAOOAW immediately destroys its application, Keycloak, browser-storage, cache, and
   protected-session state and returns to the public page.
7. **Return after logout:** Revisiting WAOOAW always displays Login/Register and never silently restores
   the previous WAOOAW session.
8. **Social login after logout:** The provider displays account selection so WAOOAW cannot silently
   reuse the previous customer's account.
9. **Account switch:** WAOOAW wipes the current customer context before allowing another provider
   account to be selected.
10. **Session expiry:** Protected content disappears immediately and the user must authenticate again
    before anything is restored.
11. **Provider cancellation:** Cancelling Google, Facebook, or Apple returns the user safely to the
    Login/Register modal without creating an account.
12. **Provider failure:** WAOOAW shows a clear retry option without exposing technical details or
    leaving disabled controls.
13. **Missing provider email:** WAOOAW requests separate email verification before registration can complete.
14. **Existing email with another provider:** WAOOAW requires fresh proof before linking accounts and
    never links them using email alone.
15. **Sensitive action:** Payment, hiring, recovery, account linking, or authority changes require
    recent stronger authentication.
16. **Session management:** Customer can view active WAOOAW sessions and revoke one session or all sessions.
17. **Forensic audit:** Every WAOOAW-observed login, registration, logout, refresh, denial, account-switch,
    and revocation attempt creates a privacy-safe database audit event.

## 6. Stories And Acceptance

| Story | Customer outcome | Defects | Journeys | Definition of Done |
|---|---|---|---|---|
| AUTH-S01 | New social user authenticates without automatic registration | D01, D09, D11 | 1, 2, 11, 12 | Each enabled provider completes disclosure, broker callback, visitor session, cancellation and bounded failure on one exact candidate; no account/membership is created |
| AUTH-S02 | Visitor converts through Trial or Hire without restarting | D01, D11 | 3, 13 | Missing minimum fields are collected once; verified provider email is reused; completion creates exactly one account/tenant/membership and resumes the exact intent |
| AUTH-S03 | Returning customer enters the correct portal context | D01, D07 | 4 | Existing issuer/subject resolves current membership; safe target is reauthorized; wrong, inactive or absent membership denies without fallback |
| AUTH-S04 | Customer can use standalone verified email | D06, D11 | 5, 13 | Keycloak owns credential and recovery flows; enumeration and abuse controls pass; visitor and registration outcomes match social paths |
| AUTH-S05 | Logout has immediate and durable customer meaning | D02, D10 | 6, 7 | Server, NextAuth, Keycloak, WAOOAW cookies/storage/cache/protected drafts are cleared; `/`, history, refresh and protected direct routes remain unauthenticated |
| AUTH-S06 | Next social login cannot silently reuse the prior customer | D02 | 8, 9 | Next explicit provider launch carries account-selection intent; stale sensitive continuation also requires fresh authentication; no prior-customer residue appears |
| AUTH-S07 | Expired or revoked sessions fail closed everywhere | D07 | 10, 16 | Expiry removes protected content; refresh rotation/reuse denial and single/all-session revocation invalidate every enabled receiver within the accepted bound |
| AUTH-S08 | Provider recovery is consistent and truthful | D09, D11 | 11, 12, 13 | Cancel, unavailable, timeout, callback failure and missing verified email produce distinct safe states with retry/restart and no false availability |
| AUTH-S09 | Login methods cannot be linked by email coincidence | D07, D11 | 14 | Existing-account proof, new-method proof and fresh assurance are required; same email alone never links or reveals account existence |
| AUTH-S10 | Consequential identity actions require current assurance | D07, D12 | 15 | Server validates `auth_time`, required factors, actor, membership, tenant, intent and action; success waits for required constitutional evidence |
| AUTH-S11 | Customer controls active WAOOAW sessions | D04, D07 | 16 | Session list shows privacy-safe device/session facts; revoke-one preserves others; revoke-all ends all WAOOAW sessions; both are replay-safe and audited |
| AUTH-S12 | Investigators can reconstruct identity attempts without collecting secrets | D03, D08, D12 | 17 | Append-only operational events cover the required taxonomy with correlation and reason codes; constitutional decisions remain separate; retention, RLS and failure policy pass |
| AUTH-S13 | Apple can be activated without changing application semantics | D05, D09, D11 | 1, 3, 4, 8, 11-14 | Stable Apple subject, private-relay email, key rotation, transfer/revocation and provider acceptance pass before availability is projected |

## 7. Component Responsibilities

| Component | Required responsibility | Prohibited behavior |
|---|---|---|
| Web Application / NextAuth boundary | Route-backed modal, disclosure, safe target, server-held token lifecycle, complete browser cleanup, no-silent-reauth and session controls | Provider token in browser JS, tenant derivation, iframe embedding of provider pages, local account truth |
| Keycloak | Sole web credential authority, provider brokering, account-selection/freshness controls, RP-initiated logout, session/revocation authority | Customer tenant minting, email-only account linking, provider readiness claims without usable flow |
| Identity Edge | Exact public OIDC routes and bounded privacy-safe access telemetry | Credential verification, request query logging, customer authorization decisions |
| Business Platform Identity Boundary | Actor/membership resolution, progressive registration, assurance and authorization, provider projection, audit correlation | Password handling, raw provider tokens, browser-selected tenant/account, direct provider APIs |
| PostgreSQL identity-security event store | Append-only operational identity events, retention, restricted access and correlation | Constitutional/customer ledger merging, raw credentials/tokens/PII, mutable event history |
| Constitutional Engine / Audit Ledger | Evidence First for consequential identity and authorization decisions | General-purpose access-log ingestion or operational-event substitution |
| Every enabled downstream receiver | Validate raw JWT and trusted peer, resolve current membership, set transaction-local tenant, authorize resource/action | Trust forwarded tenant headers, stale role claims or BP authorization as a substitute for local checks |

## 8. Forensic Event Contract

Every identity attempt observed by WAOOAW records an opaque event ID and correlation ID, UTC time,
environment, event type, provider class, outcome, stable reason code, assurance class and privacy-safe
actor/session reference when known. Required types are authentication start, provider handoff,
callback success/failure, session establishment, registration start/completion/failure, refresh
success/failure, authorization denial, logout request/completion/failure, account switch, session
expiry and single/all-session revocation.

The operational store and Constitutional Audit Ledger remain separate under C-005. They may share an
opaque correlation ID. Passwords, OTPs, authorization codes, access/refresh/ID tokens, PKCE material,
raw provider subjects, raw email/mobile, tenant/relationship IDs, URI/query, remote address, referrer
and user agent are prohibited. Logout erases revocable session state but never committed evidence.

Operational-event failure is visible and fails closed for session establishment, registration
completion, linking, revocation and authorization decisions. A provider action that never reaches a
WAOOAW boundary is not claimed as observed. Constitutional decisions continue to require confirmed
C-023 evidence before success.

## 9. Constitutional Compliance Matrix

| Obligation | Stories | Required proof |
|---|---|---|
| C-001 human override | S05-S07, S11 | Immediate logout, no silent restoration, single/all-session revocation |
| C-002 observable trust | S12 | Durable identity-event taxonomy and complete correlation |
| C-005 ledger separation | S10, S12 | Separate operational and constitutional schemas, roles and retention |
| C-007/C-027 immutability | S05, S12 | Database denial of update/delete/truncate on committed events/evidence |
| C-023 Evidence First | S02, S09-S12 | Consequential success cannot precede confirmed constitutional evidence |
| C-026 tenant isolation | S01-S03, S06-S11 | Actor-bound pre-account access, current membership and database RLS |
| C-048/C-049 truthful treatment | S01, S04, S08, S13 | Honest provider state, disclosure, cancellation and recoverable limitations |
| C-063 minimization | S01, S02, S08, S12, S13 | Minimum fields and forbidden-data scan of events/logs/artifacts |
| C-100 credentialed-origin restriction | S01, S04-S08, S13 | Exact origin, callback and logout allowlists; no wildcard credentials |

## 10. Requirement-To-Evidence Ledger

| Requirement | Story / journey | Evidence class | Required executable evidence |
|---|---|---|---|
| WC103-R001 | S01 / J1-J2 | Local Docker + actual provider | Clean-profile Google/Facebook callback-to-visitor journeys; Apple dark until gated |
| WC103-R002 | S02 / J3, J13 | PostgreSQL integration + browser | New visitor Trial and Hire each create one account/tenant/membership and resume intent |
| WC103-R003 | S03 / J4 | Integration + browser | Returning identity reaches correct portal; inactive/wrong membership denies |
| WC103-R004 | S04 / J5 | Security integration + browser | Verified-email, recovery, enumeration and rate-limit matrix |
| WC103-R005 | S05 / J6-J7 | Unit + browser + exact release | Logout cleanup sentinel; history/refresh/direct-route no-silent-reauth matrix |
| WC103-R006 | S06 / J8-J9 | Browser + actual provider | Account-selection intent and second-account journey with zero prior residue |
| WC103-R007 | S07 / J10, J16 | Integration + exact release | Expiry, rotation, replay, revoke-one/all and downstream stale-token denial |
| WC103-R008 | S08 / J11-J13 | Provider-neutral browser matrix | Cancel, unavailable, timeout, callback failure and unverified-email outcomes |
| WC103-R009 | S09 / J14 | Hostile integration | Same-email/different-subject denial, fresh dual proof and anti-enumeration |
| WC103-R010 | S10 / J15 | CCT + integration | Freshness, factor, bound-intent, membership/RLS and Evidence First checks |
| WC103-R011 | S11 / J16 | PostgreSQL + browser | Session inventory authorization, privacy projection, idempotent revoke-one/all |
| WC103-R012 | S12 / J17 | PostgreSQL + security | Event taxonomy, append-only controls, RLS, retention, redaction and failure injection |
| WC103-R013 | S13 / J1, J3-J4, J8, J11-J14 | Synthetic + actual Apple | Stable subject, private relay, key rotation, transfer/revocation and acceptance |
| WC103-R014 | All | Contract/static | No token/PII leakage, no browser tenant authority, exact allowlists and generated-client consistency |
| WC103-R015 | All | Actual cloud | One exact immutable Demo candidate completes the enabled-provider journey matrix |

## 11. Definition Of Done

WC-103 is complete only when:

1. WC103-R001 through WC103-R015 each have an exact result of `PASS`, `BLOCKED`, `DEFERRED` or
   `NOT_APPLICABLE`, with only unavailable-provider activation rows permitted to remain `DEFERRED`.
2. Every enabled Target Authentication Journey has direct evidence on one exact immutable candidate;
   aggregate counts and redirects alone are insufficient.
3. Google and Facebook pass real-account Demo journeys. Apple and standalone email are either fully
   accepted or truthfully unavailable; synthetic proof does not authorize projection as available.
4. Logout, revisit, history, refresh, direct-route, account selection and second-account isolation pass
   on supported desktop/mobile browsers with no protected-state residue.
5. JWT expiry, refresh rotation, token reuse, revocation and current membership/RLS denial pass at
   every enabled receiver; disabled receivers remain unreachable and are not marked passing.
6. The operational identity-event schema, append-only controls, access roles, retention, redaction,
   correlation and failure behavior pass Data and Security acceptance.
7. Consequential identity and authorization decisions satisfy Evidence First without merging the
   operational store, Customer Evidence Ledger or Constitutional Audit Ledger.
8. Accessibility, localization, RTL, 200% text, reduced motion, popup-blocked/redirect fallback and
   provider cancellation/failure states pass without trapping the customer.
9. Exact-source, image, configuration, migration and provider evidence is bound to the candidate;
   local, synthetic, actual-cloud and untested evidence classes remain distinct.
10. Author review finds no unresolved correctness, security, privacy, data, operability, rollback,
    constitutional or traceability finding; Founder review and merge remain separate.

## 12. Implementation Sequence

1. Freeze this contract and the Identity Boundary amendments through Founder review.
2. Implement the operational identity-event data contract and database controls before event writers.
3. Complete logout/no-silent-reauth and active-session lifecycle controls.
4. Complete provider-neutral recovery, progressive registration and email path.
5. Prove JWT/tenant enforcement across enabled receivers.
6. Qualify Google/Facebook against one exact Demo candidate; keep Apple/email dark until their gates pass.
7. Run the full requirement ledger, author review and PR preparation against final pushed HEAD.

Each implementation step requires explicit current-session Founder authorization. This ordering is a
delivery dependency, not authorization to write code or mutate an environment.

## 13. Rollback And Failure Policy

Rollback restores the prior application and identity configuration as one exact release tuple while
preserving committed identity, membership, idempotency, operational security events and constitutional
evidence. Rollback must not re-enable silent reauthentication, weaken RLS, accept stale tokens, expose
an unqualified provider, or delete audit history. A partial identity migration, inaccessible evidence
store, ambiguous account binding, provider-secret exposure or failed tenant-isolation check blocks
release and requires restoration of the last qualified tuple.

## 14. Stops

Stop rather than proceed when implementation would require direct provider calls from WAOOAW
applications, provider pages in an iframe, browser-held provider tokens, email-only account linking,
browser-selected tenant/account, mutable audit history, ledger merging, logging forbidden identity
data, provider availability without complete readiness, weakened JWT/RLS validation, Production or
customer traffic without authority, self-approval or self-merge.

## 15. Review And Handoff

The Founder requested one single-pass Security Architect and Data Architect edit review. Each office
may repair manageable gaps directly in this contract and the controlling Identity Boundary, then must
record its findings and disposition here. No repeat institutional pass is implied. After those repairs,
the Solution Architect performs final author review and submits the documentation PR to the Founder.

### 15.1 Security Architect One-Pass Review

**Findings repaired:** explicit session rotation/fixation controls; logout/revocation CSRF and race
ordering; popup/redirect boundary; stale-token denial; privacy-safe abuse telemetry; browser-cache
restoration; provider and exact-release evidence limits.

**Disposition:** PASS AT SPEC. No new identity provider, protocol or security technology decision is
introduced. Runtime and actual-provider proof remain implementation gates.

### 15.2 Data Architect One-Pass Review

**Findings repaired:** explicit operational event ownership; separation from all three ledgers;
logical event/session schemas; append-only/idempotency controls; revocation ordering; RLS and
connection-pool isolation; retention, legal hold, backup and export behavior.

**Disposition:** PASS AT SPEC. Physical implementation remains unauthorized and must follow the data
contract without inventing a mutable log or cross-ledger join.

### 15.3 Solution Architect Final Author Review

The complete specification was reviewed against the Founder objective, all 17 Target Authentication
Journeys, AUTH-D01 through AUTH-D12, WC103-R001 through WC103-R015, the controlling identity
architecture, constitutional obligations, Security/Data findings, failure modes, operability,
rollback and evidence classes. The stale ADR-003 index summary was corrected to the accepted WC-085
membership-authority amendment. No requirement lacks an owner or direct acceptance class, no new
technology decision requires an ADR, and no implementation or environment action is authorized.

**Disposition:** PASS AT SPEC - READY FOR FOUNDER REVIEW.
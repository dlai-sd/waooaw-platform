# WC-085 Identity Architecture Decision

**Current decision (amended by WC-090 on 2026-09-10): STOCK KEYCLOAK + BP MEMBERSHIP, ready for bounded implementation.**
**Author:** EA INST-004 under standing required-office edit authority, bounded Solution repair;
not Security/Data concurrence or an independent institutional review. Bootstrap remains completed.
The latest Founder C#/Python/JS-only constraint supersedes the earlier custom-Java selection.
[ADR-003](../../../adr/ADR-003-jwt-claims-multi-tenancy.md) and
[ADR-008 Amendment 3](../../../adr/ADR-008-keycloak-identity-broker.md) are the controlling author
amendments under C-032. C-026 RLS and institutional/ledger separation remain mandatory.

## Current Implementable Contract

1. Stock Keycloak verifies an explicitly configured broker; the existing ASP.NET bearer scheme validates RS256/JWKS, exact
   environment issuer, audience containing `waooaw-platform`, allowlisted customer web/mobile `azp`,
   subject, expiry/not-before/issued-at (30-second skew), `auth_time`, signed allowlisted `idp` and base
   customer eligibility. WC-090 adds `facebook` beside `google` in Demo only, with a fixed
   provider-specific namespace and trust digest. Service accounts, institutional roles/clients and other provider
   paths do not qualify. Web `azp` is the existing `waooaw-web` client; mobile is disabled for the first slice.
   A configured client not explicitly enabled cannot qualify via a permissive audience match.
2. BP alone holds `waooaw-bp-identity-reader` credentials with stock `view-users`, never writes
   Keycloak. The exact two Admin GETs, field minimization, secret references and stock alias mapper
   are fixed in ADR-008 Amendment 3. Preserve exact broker `userId`; no invented stable note, raw
   provider token, email-only linking or browser proof. Read scope is realm-wide metadata, not a
   per-user ACL; no BP listing/search endpoint. Read/permission failure is unavailable, not escalation.
3. Completion validates verified email, minimum stored profile/language, five-minute authentication
   age and fresh exact broker proof BEFORE opening its DB transaction. Proof must still be at most
   five minutes old when the transaction commits. No network operation inside/after that transaction
   is needed to complete signup. Atomically write or reuse account, canonical organisation
   (`organisation.id = tenant_id`), initial ACTIVE OWNER membership, active actor, stable login key,
   minimal proof provenance, completed registration, existing idempotency result and required evidence.
   No intent/outbox/publication/revision/acknowledgement, billing mapping, wallet or new worker.
4. Serialize on exact actor and provider identity as well as registration; DB uniqueness is final
   authority. Same key/hash replays the committed status/body after current access checks; different
   hash is `409 IDENTITY_IDEMPOTENCY_CONFLICT` without mutation. Other keys/registrations for that
   same active identity reuse its original account/tenant. Persist the immutable completion outcome
   with the existing durable registration association; request-key expiry cannot permit reminting.
   Any commit failure rolls back account AND retry/evidence records. Lost commit response is resolved
   by lookup/retry, not compensation. A removed membership cannot regain access by completion replay.
5. The web server calls existing `GET /api/v1/identity/session` with the SAME still-valid caller token
   and compares its returned opaque account reference with the completed account before navigation.
   No tenant-claim refresh prerequisite. Normal expired-token refresh or one PKCE round trip remains
   bounded and server-owned; changed issuer/subject cancels the handoff. Session/cache/draft cleanup,
   CSRF, HTTP-only cookies and `no-store` remain. `defaultTarget`, `capabilities` and UI hints are not
   authorization. Every operation independently enforces its server policy.
6. Each protected request resolves current membership from validated `(iss, sub)` through the exact
   read-only storage contract below. Ignore JWT/browser tenant and organisation-role claims as
   authority. No latest-registration fallback, shared tenant, JWT minting or application auth framework.

### Exact Internal Membership Operation

`identity.resolve_customer_membership()` is a zero-argument, read-only operation on the existing
PostgreSQL identity store. It returns zero/one typed row `{ account_id: uuid, tenant_id: uuid,
membership_id: uuid, roles: text[] }`; this slice allows exactly one active initial OWNER workspace.
It uses the calling service's transaction-local validated `app.identity_issuer`/`app.identity_subject`,
and checks live actor, login binding, account, organisation and membership. Inactive/absent means no
row; multiple matches are an invariant failure. No tenant input, arbitrary subject lookup, provider
proof output, cross-ledger data, positive cache, writes or grants of organisational role management.

Grant only EXECUTE to the existing BP/CE/PR/WBE/AI service database identities; never share BP login.
Function owner is nonowner, NOLOGIN/NOBYPASSRLS, read-only on the minimum identity/organisation
columns with actor-scoped FORCE RLS, fixed search path and no PUBLIC execution/schema creation.
Data supplies the exact nonrecursive policies/DDL. There is NO new HTTP membership endpoint/service.
On each receiver: authenticate allowed peer by mTLS AND independently validate the original raw
Keycloak bearer in `authorization`; resolve using its own DB identity; set both tenant GUCs from the
result; check its own resource/participant/action/assurance policy under tenant RLS. Supplied
`x-tenant-id`/`x-account-id` mismatch denies; a matching header is not proof. A compromised forwarding
service cannot select another tenant with a header; BP remains the trusted account/membership writer,
not the credential issuer or arbiter of CE/PR/WBE/AI resource permissions.

Use existing service certificate identities and explicit caller/operation allowlists, not private
network location or TLS alone. No new caller/operation pair is enabled by this document. Lookup
outage fails `503` with no protected result/effect; missing authority denies `403`, resource ownership
failure uses normalized `404`. Local resource mutations must recheck current membership within their
authorization transaction; cross-service reads are not a distributed revocation lock. No assertion
of instantaneous cancellation of already authorized work is made; existing revocation/Emergency Stop
controls remain additional. Unadopted services/operations are disabled, not permitted by a BP verdict.

### First Slice Defaults And Continuity Gate

Enable only configured Google and, under WC-090 in Demo, Facebook web registration
start/read/profile/complete, provider readiness, session
projection and the non-consequential shell needed for entry. Confirmed email and profile/language
are mandatory; mobile is not. Persist only initial OWNER membership, no multi-workspace selection,
MANAGER/VIEWER creation, payment/trial/subscription/employment or inferred commercial capabilities.
Deny unsupported customer mutations and unadopted downstream REST/gRPC/WSS, jobs/callbacks/background
effects at server entry, not only UI. Existing separately authorized institutional and Emergency Stop
activation paths are not reclassified or disabled. Consequential commands remain denied until their
own authority, mobile/freshness and resource controls are implemented; API hints cannot enable them.

Same issuer/subject returns to the same IDs. A different actor with a matching stable provider key
returns non-enumerating unresolved recovery, never automatic rebinding or a new account. Preserve
proof now. Future recovery must demonstrate current configured-provider session proof plus historical broker key,
nonrecycled actors, locked retirement/rebinding, old-session denial and unchanged durable IDs under
concurrency. No implicit reset or persistent-Keycloak change. Initial fixtures keep the realm and
subjects stable; fixture identities must be labelled synthetic, not real Google or reconstruction proof.

### Small Data Author Delta And First Check

The architecture is selected; no further technical choice or general reviewer chain is requested.
The ONLY remaining physical authoring request is to INST-006: map the reduced records, one atomic
completion transaction and read-only function in the
[Data amendment](wc085-identity-provisioning-data-contract.md) onto existing EF/Npgsql storage,
with exact uniqueness/FKs, actor-scoped lookup RLS/function privileges and tenant RLS. Supply an
additive legacy-safe migration decision; do not fabricate old provider proof, apply a reset, build a
publication subsystem or redesign billing/ledgers. This is Data authorship, not a review or delegate.
Parent may proceed under standing implementation authority while that physical mapping is completed;
activation waits for it and executable proof. No code is written by this docs-only call.

**First discriminating parent check:** real PostgreSQL, restricted app roles, stable stock-Keycloak
fixture and two independently validated synthetic subjects with explicitly synthetic broker records.
Complete each through BP, assert two durable accounts/organisations and OWNER memberships, then use
the same tenantless tokens to obtain each own session. Swap registration/resource IDs and forge tenant
headers/claims: cross-tenant read/write must deny at API AND actual RLS. No substitute in-memory DB,
superuser assertion or administrator-populated membership. Inject one failure before final commit to
prove account + idempotency rollback, then retry/race and assert one result per identity. A later
enabled CE/PR/WBE/AI operation must additionally prove its own raw-token validation, independent lookup,
channel authentication and foreign-resource denial. Disabled families are DEFERRED/DISABLED, not PASS.

**Evidence status:** documentation authoring only; no tests, build, cloud, source deletion, commits,
pushes or recovery executed. Real Google consent/session mapper proof and deployment acceptance remain
future gates; CB-009 stays open for physical/implementation/evidence closure, not an architecture choice.

## Superseded Decision Record - Not Implementation Instructions

The ENTIRE remaining record below is historical. Its Java approval, publication protocol, Data table
requirements, renewal requirement, qualification plan and recommendation are superseded by the current
contract above. The Java source and dedicated probe were deleted during Founder-authorized handover.
Historical Security evidence is retained, not adopted as an implementation instruction.

**Office:** INST-004, Enterprise Architect; bounded decision authorship, 2026-09-09.
**Authority:** Founder's current CB-009 repair assignment with edit authority. Continuous-session
bootstrap remains valid. No delegation, additional office invocation or review is requested.
**Resolution: in-process Keycloak publication extension SELECTED; architecture AUTHORED.**
**Updated authority:** Founder subsequently answered yes to changing how signup connects to login
so signup stays automatic without extra credential powers. This supersedes the earlier stock-only/
operator-gated disposition. It does not authorize deployment or spending.

## 1. Decision And Authority

Select the attribute-only `RealmResourceProvider` in the existing Keycloak process, approved by
[ADR-008 Amendment 2](../../../adr/ADR-008-keycloak-identity-broker.md). BP owns durable account,
tenant and membership truth; Keycloak alone owns credentials, broker associations and signed tokens.
Customers complete ordinary Google consent/profile entry; publication and renewal are automatic,
without an operator approving each signup. Temporary failure stays retryable, not falsely completed.

Decision Space: this bounded cross-component protocol and necessary Java SPI dependency.
Obligations: C-032 authority separation, C-026 RLS, C-059 truthful evidence, ADR-003 signed tenant
isolation and ADR-014 secret custody. The compact EA card was read; its general discovery/reviewer
cycle is not invoked under this assignment. No bootstrap rerun or delegation occurs.

The conventional SaaS pattern is external identity proof, app-owned membership, trusted signed
tenant claims and independent current resource authorization. Neither social login nor `OWNER`
alone grants consequential permissions. This is not a regulatory compliance attestation.

## 2. Reason And Bounded Supersession

Security's existing local 25.0.6 probes found that `manage-users` and preview group `manage-members`
also allow credential/broker/unrelated-attribute changes. Both remain rejected. A signed backchannel
mapper would add token-time integration and custom claim logic; this endpoint reuses durable
attributes and stock renewal. No new service, callback, database credential in Keycloak or worker
is needed. Java is new to the .NET/Python app stack and is not described as configuration-only.

This supersedes only the stock-only/no-plugin channel constraint and rejected writer/read selection
in [Identity Boundary](../components/identity-boundary.md) 5.2-5.4,
[Security](../security/wc085-identity-publication-security-contract.md) Sections 1-2/7 and the stock-
transport wording in [Data](wc085-identity-provisioning-data-contract.md) Section 6. Their credential
denials, immutable actor payload, broker proof, eligibility, RLS, public operations and session
controls remain. The old operator-gated recommendation is superseded. Other offices' files are
unchanged; concurrence is not invented. ADR-003 needs no amendment. Subscription publication
is outside this endpoint's authority.

## 3. Exact Private API

Base: allowlisted internal TLS Keycloak origin plus
`/realms/waooaw/waooaw-identity-publication/v1`. The public ingress must not expose these routes;
provider authentication remains mandatory independently of networking. No new public registration
API, CORS access, redirect or caller-selected host/realm. Decode subject once as one path segment;
reject malformed/oversize identifiers. Select only enabled local customer users, never service
accounts, administrators or institutional identities. Missing/conflicting broker state denies.

| Method/path | Request and response |
|---|---|
| `GET /users/{subject}/broker-binding` | No body/query selector. Return only `actorIssuer`, `actorSubject`, `enabled`, `eligible`, configured `providerNamespace`, `brokerAlias`, exact opaque `providerSubject` and nonsecret `trustConfigDigest`. No email, username, credentials or upstream tokens. Namespace/digest derive from reviewed server config, not request input. |
| `POST /users/{subject}/publication` | Strict object: `actorIssuer`, `intentId` UUID, `revision` positive bigint decimal string, `membershipRevision` likewise, `payloadDigest` lowercase SHA-256 hex, `providerNamespace`, `brokerAlias`, `providerSubject`, `trustConfigDigest`, and `attributes`. Correlation UUID is a header, not authority. Attributes contain exactly `tenant_id` canonical UUID string, `waooaw_roles` nonempty distinct sorted array restricted to OWNER/MANAGER/VIEWER, and `org_name` committed nonempty display name, at most 200 characters. No other user fields. Return 200 with `APPLIED` or `ALREADY_APPLIED` and the stored publication representation. |
| `GET /users/{subject}/publication` | Return the stored envelope plus ACTUAL three owned attributes and `UNPUBLISHED` or `PUBLISHED`. Recheck current broker association. A marker alone is not proof of publication or BP acknowledgement. Never mutate on GET. |

POST issuer must equal the configured realm issuer; subject comes from the bound durable actor.
BP selects proof-read targets only from the validated customer actor, never browser email/subject.
After commit it reloads through actor-scoped `identity.read_publication`. Keycloak compares the
envelope namespace/alias/upstream subject/digest against its configured trust and actual federated
association. No relinking or identity creation is an endpoint capability.

Authenticate EVERY route with Keycloak-native bearer validation, not decode-only JWT parsing:
RS256, exact issuer, audience exactly `waooaw-identity-publication`, `azp` exactly
`waooaw-bp-identity-publisher`, scope containing exact token `wc085:identity-publication`, and `sub`
equal to that enabled client's enabled service account. Validate expiration/not-before/issued-at,
maximum 60-second lifetime and configured revocation/not-before state. Use standard client
credentials with the existing separate secret; no refresh/offline/customer grant. Attach the
dedicated audience/scope only to this client. No realm-management roles or admin composites,
including `view-users`; native admin reads MUST deny as well as writes. Reject customer tokens
and a different machine client with similar claims.

Return 400 for malformed input, 401 for invalid authentication, 403 for insufficient client/scope,
normalized 404 for absent/ineligible targets, 409 for binding/immutable-state conflict and 503 for
dependency/lock failure. Authenticate before lookup, with no existence disclosure to unauthenticated
requests. Reject unknown fields and duplicate JSON keys; cap body at 16 KiB and use bounded lock/
HTTP timeouts. Responses are no-store. BP retains public 409/404/503 mappings and never escalates
credentials on 401/403. Provider missing/version-incompatible at startup fails readiness, not fallback.

### Publication Integrity And Concurrency

Persist one provider-private `waooaw_publication_record` attribute containing the immutable envelope
alongside the three fields in ONE server transaction. Protect it from user/profile/broker editing
and all token mappers; input attributes can never include it. It is replay metadata, not another
source of tenant truth. Compare typed fields AND actual attributes, not only the submitted digest.
`payloadDigest` is the exact opaque stored Data digest, not proof of commit or a digest recomputed
using unspecified cross-language JSON serialization.

Lock the local user row with `PESSIMISTIC_WRITE` through pinned `JpaConnectionProvider` and
`UserEntity` in the request's Keycloak transaction before fresh storage reads/mutation. Use storage/
cache APIs that preserve lock lifetime and invalidate cached users on commit; direct SQL writes to
attribute tables are prohibited. First publication requires all three owned fields AND marker to
be absent. Exact envelope AND actual fields return `ALREADY_APPLIED`. Any difference, partial field,
unmarked seeded state, changed proof or different revision conflicts without mutation. Write only
the three fields and marker. Concurrent first writes yield one immutable winner, never merged data
or two successful different payloads. Lock failure rolls back; in-memory locks/BP leases are not
remote serialization. Recheck broker proof inside the locked transaction, not a cached earlier read.

Data's one immutable payload per actor remains: this is not a general name/role synchronization API.
An old request arriving after timeout can at most install that same actor's initial snapshot.
BP refuses acknowledgement if actor/membership/revision is now ineligible. Recovery uses a DIFFERENT
nonrecycled actor and incremented intent revision with fixed account/tenant/membership IDs. Same-user
revision advancement is rejected. No distributed transaction or zero-stale-claims promise is made;
current resource authorization denies revoked authority immediately.

BP keeps Data's publication advisory lock, reads back actual fields AND broker proof, and rechecks
active actor/account/organisation/login/membership and desired revision in the short acknowledgement
transaction. Only then append acknowledgement/result and report completion. A timeout resumes the
same intent; never mint another tenant or compensate by deletion. Then use Security's one refresh/
one PKCE fallback and expected-account session check. Missing/wrong claims are never upgraded by
BP lookup. Customer A's pending completion must not overwrite customer B's newer session.

### Explicit Trust Limit

The machine client has population-wide access to these minimal routes, not per-customer authority.
It does not independently prove a DB transaction. BP loads committed immutable data; Keycloak
enforces field limits and identity integrity. A stolen publication credential could poison an
initial business-attribute publication or cause denial of service, but must not reset credentials,
relink Google, mint a customer session or grant realm roles. DB actor/tenant/membership checks must
reject forged access. Do not describe this as independent database attestation or omit its limited
business-publication compromise risk.

## 4. Exact Contract Deltas For The Parent

These are implementation inputs, not another general review or office invocation. Apply under
existing bounded EDIT/parent authority; no Data schema redesign is requested.

| Owning boundary | Required delta; retained floor |
|---|---|
| Security Sections 1-2, 6-7 | Replace stock GET/PUT and `view-users` with the three extension routes, zero admin roles, explicit audience/scope/service-account validation, protected replay metadata and internal-only exposure. Retain secret custody, rotation, TLS, Google trust/session proof, profile protection and Sections 3-5 renewal/continuity controls. Change the stock-only conflict disposition to selected-extension qualification pending, not a security PASS. Add stolen-publisher negative tests including DB denial of forged allowed attributes. |
| Solution Identity Boundary 5.2-5.4, 14.1 | Replace adapter transport and superseded no-plugin/founder-choice wording. Reconcile by identical immutable replay, never overwriting older/foreign values on the same actor. Retain public OpenAPI, BP_COMMITTED/PUBLISHED, customer-driven retry, 5.3 continuity and 11.1 handoff. Add extension availability, conflict, denial and lock/cache tests to 14.1. No new browser API or worker. |
| Data Sections 6-7 | Replace stock-transport wording. Extend private `read_publication` result with referenced proof/login's `provider_issuer`, `broker_alias`, `provider_subject`, `trust_config_digest`, alongside existing actor/attributes/digest/membership revision. Resolve from the intent's exact proof/login under the same current-actor/RLS checks; no arbitrary lookup, new table, DB principal or callback. Preserve immutable actor publication, reconstruction revision and post-read-back acknowledgement. |

Define the replay metadata profile attribute as admin-view/edit only, non-user-required and never
mapped to claims; publisher Admin API calls still deny. BP and Keycloak use the same reviewed
namespace/digest inputs, never browser data. The broker-binding response does not replace the stock
signed `idp` session-note proof. BP alone authorizes current resources and rejects machine tokens.

## 5. Build, Cheap Check And Qualification

ADR-008 explicitly approves Java 21, Maven 3.9.9, provided Keycloak 25.0.6 dependencies, private/JPA
coupling and the reproducible Docker build. This adds Java maintenance, a custom image supply chain,
request validation, transaction/cache tests and upgrade gates. It avoids a new service/custom token
issuer, but is neither trivial nor already tested.

Repository evidence: workload `main.tf` and reconstruction script use the ADR image digest; ADR-016
specifies .NET/Python services. Targeted lookup found no retained SPI source/JAR in the external
Security probe. No upstream source was fetched or extension code executed here. Version-tagged
verification anchors for the parent, not claims of inspected implementations:

- [RealmResourceProvider, 25.0.6](https://github.com/keycloak/keycloak/blob/25.0.6/server-spi-private/src/main/java/org/keycloak/services/resource/RealmResourceProvider.java).
- [Native bearer authentication, 25.0.6](https://github.com/keycloak/keycloak/blob/25.0.6/services/src/main/java/org/keycloak/services/managers/AppAuthManager.java).
- [JPA connection provider, 25.0.6](https://github.com/keycloak/keycloak/blob/25.0.6/model/jpa/src/main/java/org/keycloak/connections/jpa/JpaConnectionProvider.java).
- [Local user entity, 25.0.6](https://github.com/keycloak/keycloak/blob/25.0.6/model/jpa/src/main/java/org/keycloak/models/jpa/entities/UserEntity.java).

**Falsifiable hypothesis:** the pinned native endpoint can publish an eligible actor's immutable
allowed attributes with a zero-admin client while the same credential cannot mutate credentials,
broker proof or unrelated data. **Next executable check:** isolated Docker build/start of the minimal
provider on the exact pin, then one positive publication/read-back and one native Admin API password-
reset denial with the SAME publisher token. Compile/start/auth failure or successful native reset
falsifies that implementation; repair this slice, never add admin roles.

Required focused gates after that first check:

1. Missing/forged/expired token, wrong issuer/audience/scope/client, customer/machine mismatch,
   cross-realm target, invalid field/role and user/profile edits deny. Representative native Admin
   APIs ALL deny: user read/list, password, required actions, email verification, broker mutation,
   founder/realm-role grants, impersonation, groups, client/realm config and unrelated/subscription
   fields. Assert effective roles and direct endpoint outcomes, not configuration alone.
2. Concurrent identical/conflicting publication across two Keycloak instances sharing the selected
   database; lock timeout, rollback, stale cache, lost response, marker tamper, foreign seeded tenant
   and changed Google association. No partial write or conflicting success. Unsupported storage denies.
3. Actual BP-role PostgreSQL rollback/uniqueness/RLS/pooled-context tests, forged business attributes
   using the stolen-publisher model, retired actor denial, read-back/ack failures and recovery preserving
   durable IDs. Check that role claims cannot exceed current DB membership authority.
4. Stock mapper issuance, web OIDC renewal and account-switch isolation; later authorized two-real-
   Google-customer registration and returning/recreated entry with independent tenants. Synthetic
   fixtures do not prove Google authentication, deployment readiness or actual-cloud behavior.

## 6. Readiness And Limits

**Architecture selected and dependency approved; ready for parent implementation under standing
authority.** Incorporate the exact deltas in that bounded implementation, not another option selection
or perpetual stock-only gate. Implementation, image build, permission/concurrency/isolation proof and
real Google acceptance are pending. Builder digest, exact private API compatibility and lock/cache
behavior must be established by the build/focused tests. Failure blocks qualification, never relaxes
credential separation. The compatibility pin does not establish current version security support.

[CB-009](../../../blockers/CB-009-wc085-tenant-provisioning-contract-2026-09-09.md) remains open for
implementation/evidence closure; lack of authority to change architecture is superseded. Security's
historical stock results stay valid, not relabelled as extension results. This call changes only
ADR-008 and this note. No runnable files, artifacts, other office contracts, blocker/project-state
records, commits, pushes, secrets, cloud operations or delegation are included.
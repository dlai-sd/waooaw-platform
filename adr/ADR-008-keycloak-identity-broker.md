# ADR-008: Identity — Keycloak as OAuth Federation Broker

**Status:** Accepted - v5 (2026-09-09: stock Keycloak and BP membership; Amendment 3 controls WC-085)
**Date:** 2026-07-07 | **Last Updated:** 2026-09-09
**Roles Applied:** Security Architect (identity management) + Solution Architect (integration patterns)
**Constitutional Basis:** GENESIS Design Principles — Configuration over Code; Constitution Article IX (Customer Rights — right to identity continuity)

---

## Context

WAOOAW customers (dental clinics, beauty artists, traders, enterprises) need to authenticate. They expect social login (Google, Facebook, Apple) in addition to email/password. Multiple OAuth providers are required today and more will be added.

The question is: does each service integrate directly with each OAuth provider, or is there a federation layer?

## Decision

**Keycloak as the identity broker. Google is the default social provider. The application never talks directly to any OAuth provider.**

```
Customer: "Continue with Google"
  ↓
Customer Browser → Keycloak login page (auth.waooaw.com)
  ↓
Keycloak → Google OAuth (federation)
  ↓
Customer authenticates with Google
  ↓
Google → Keycloak (verified identity)
  ↓
Keycloak → Customer Browser (Keycloak JWT)
  ↓
Customer Browser → WAOOAW API (Bearer: Keycloak JWT)
```

Application services only ever see Keycloak JWTs. The OAuth provider used is irrelevant to the application.

**Provider rollout (all Keycloak configuration only, zero code changes):**
- Phase 1 (MVI): Google + email fallback
- Phase 2: Facebook and Apple — designed under Amendment 1; activated independently when FA-002/FA-018 (Facebook) and FA-019 (Apple) prerequisites are satisfied
- Phase 3 (future): Microsoft/Outlook — bank branch and corporate segment

_Note: Amendment 1 (see below) supersedes the Phase 2/Phase 3 ordering for Facebook and Apple and records the FA-035 provider policy._

**Keycloak setup:**
- Self-hosted in Docker container (dev)
- Self-hosted in Azure Container App (cloud, same Container Apps environment)
- Realm: `waooaw`
- Client: `waooaw-platform`

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Direct OAuth per provider in each service | Each new provider requires code changes in Business Platform and Professional Runtime. Violates Configuration over Code. |
| Auth0 | Expensive at scale (per-user pricing). Vendor lock-in. Keycloak is open-source and self-hostable. |
| Azure AD B2C | Per-authentication pricing (~$0.0016/auth after 50k free). At 10,000 monthly active users = ~$16/month. Acceptable but creates Azure dependency. Keycloak preferred. |
| Clerk | Developer-friendly but vendor lock-in. No self-hosting option. |

## Consequences

**Benefits:**
- Adding a new OAuth provider = Keycloak admin configuration only (5 minutes)
- Application code is provider-agnostic from day one
- Keycloak is self-hostable — no per-auth pricing at any scale

**Trade-offs:**
- Keycloak requires operational management (updates, realm backup)
- Keycloak in Container Apps adds ~256MB RAM overhead
- In dev: Keycloak requires configuration on first run (realm setup via import)

**Operational note:**
- Keycloak realm configuration exported as JSON and version-controlled in `infrastructure/keycloak/`
- Container startup imports realm automatically — no manual configuration
- **Version pin:** Docker image pinned to a specific Keycloak minor version (e.g., `quay.io/keycloak/keycloak:25.0.6`). Floating `:latest` is prohibited — Keycloak has had breaking realm schema changes between major versions
- **Upgrade process:** Test upgrade in dev, export updated realm JSON, commit, promote through environments. Never upgrade directly in cloud without dev validation.
- **Realm backup:** Automated daily export of realm configuration included in platform backup job (see ADR-014 for secret management, including Keycloak client secrets)

---

## Identity Provider Expansion Strategy (v2 — 2026-07-13)

### Customer segments and their IDPs

| Customer segment | Primary IDP | Notes |
|---|---|---|
| Dental / beauty / fitness / retail | Google | 70-80% of Indian smartphone users; Android dominant |
| Bank branch managers | **Microsoft** | SBI, HDFC, Axis, ICICI run on Microsoft 365 |
| Insurance advisors (corporate) | **Microsoft** | LIC, Bajaj Allianz, ICICI Pru — Microsoft shops |
| Builders / professional services | Google or Microsoft | Mixed |
| Parents (Private Tutor) | Google + **Apple** | iOS ~20% India premium segment |
| Farmers / rural | **None** | WhatsApp phone-as-identity (ADR-023) |
| Trading customers | Google | Tech-forward audience |

### IDP Priority Decisions

| IDP | Priority | Decision | Reason |
|---|---|---|---|
| **Google OAuth 2.0** | P0 — Live | ✅ Implemented | 70-80% coverage. Default. |
| **Microsoft (Azure AD OIDC)** | **P1 — Phase 2** | ✅ Implement before banking segment | Bank branches, insurance, corporate professionals cannot use personal Google for business tools. Without this, the high-value B2B banking segment (DMA Skill 11) is blocked. Config: `login.microsoftonline.com/common/v2.0` — supports personal + corporate AAD in one endpoint. |
| **Apple Sign In** | P1 — Designed; BLOCKED by FA-019 | ⚠️ See Amendment 1 | App Store rules §4.8 and parent segment (Private Tutor ~25-30% iOS urban India) require Apple Sign In. FA-035 approves design now; activation gated on FA-019 Apple Developer account, Service ID, private key, and relay-domain configuration. |
| **LinkedIn** | P2 — Phase 3 | Defer | Useful for professional B2B segment. LinkedIn OAuth has been historically restrictive. Implement when B2B segment is proven. |
| **Facebook / Meta** | P2 — Designed; BLOCKED by FA-002/FA-018 | ⚠️ See Amendment 1 | FA-035 approves Facebook login with scope isolation; see Amendment 1 for isolation rules. Activation gated on FA-002 Meta Business Manager verification and FA-018 login app credentials. The identity boundary problem is resolved by mandatory scope and app separation — the login app and DMA Business OAuth are separate security principals. |

### Why Microsoft is P1 (not P2)

Corporate customers (bank branches, insurance advisors, builders with teams) cannot use personal Google accounts for a business procurement tool. This is corporate policy, not preference. Without Microsoft SSO, WAOOAW is locked out of every Indian bank's branch marketing budget — our highest CPL segment with highest LTV.

### Why Apple is P1 (conditional)

Not optional for App Store. Required by Apple's own rules. The Private Tutor parent segment has significant iOS penetration. Zero additional code — Keycloak configuration only.

---

## Authentication and Authorization Architecture (v2 — 2026-07-13)

### Three Authentication Paths

```
PATH 1 — Web/Portal (Keycloak OAuth)
  Customer → Keycloak → IDP (Google / Microsoft / Apple / LinkedIn)
  → JWT (15-min access + 8-hour refresh) → API → RLS (tenant_id)

PATH 2 — WhatsApp (Phone Identity — ADR-023)
  WhatsApp message → Meta webhook → Phone Identity Service
  → Session token (30 min) → RLS (organisation_id)
  High-risk actions: MPIN challenge tier (see ADR-023 v2)

PATH 3 — Service-to-Service (mTLS — ADR-007)
  Service A → mutual TLS → Service B
  CE gRPC: service certificates, not user JWTs
```

### Role-Based Authorization Within an Organisation

An organisation may have multiple users (owner + receptionist, trader + assistant). Roles are Keycloak realm roles embedded in the JWT:

```yaml
OWNER:    Full Decision Space authority. Can amend Employment Contract.
          Can Emergency Stop. Can approve any agent action.
MANAGER:  Can approve routine agent actions. Cannot amend contract.
          Cannot Emergency Stop.
VIEWER:   Read-only. Can see reports. Cannot approve or act.
```

JWT claim: `"waooaw_roles": ["OWNER"]`

Constitutional Engine validates: C-003 (authority must be licensed to the specific role). An MANAGER approval for a high-risk financial action is denied at the CE level regardless of what the Business Platform allows.

### JWT Claims Standard (extends ADR-003)

```yaml
sub:              Keycloak user UUID
tenant_id:        Multi-tenancy anchor (ADR-003)
organisation_id:  Session-scoped organisation
waooaw_roles:     [OWNER | MANAGER | VIEWER]
auth_path:        PORTAL | WHATSAPP | SERVICE
idp:              GOOGLE | MICROSOFT | APPLE | LINKEDIN | PHONE
exp / iss:        Standard JWT fields
```

The `auth_path` claim is consumed by the Constitutional Engine: a `WHATSAPP` session cannot approve HIGH-RISK actions unless the MPIN challenge has been completed in this session window (see ADR-023 v2).

---

## Amendment 1 — FA-035 Customer Identity Policy Reconciliation (v3 — 2026-08-09)

**Authority:** FA-035 — Founder Yogesh Khandge, 2026-08-09
**Supersedes:** IDP Priority Decisions table rows for Facebook/Meta and Apple in v2; Phase 2/Phase 3 provider rollout ordering in the Decision section
**This amendment does NOT authorize:** implementation of any F2 or F3–F8 component, any provider activation, deployment to any environment, merge of any pull request, or any independent architecture review

### One Provider-Agnostic Customer Experience

FA-035 establishes that WAOOAW presents one unified customer experience offering `Continue with Google`, `Continue with Facebook`, `Continue with Apple`, and email-fallback options to new and returning customers. The experience is provider-agnostic: the application shell renders the same registration and sign-in flows regardless of which provider the customer selects. Keycloak remains the sole web credential authority; WAOOAW applications never call Google, Meta, or Apple identity APIs directly.

An unavailable provider is not displayed as active. The display set expands as each provider's activation evidence is accepted. All four providers are designed under this amendment; activation is independent and gated on provider-specific prerequisites.

### Customer Account Completion

Registration requires confirmed email before account completion. A customer may enter and explore without confirming mobile. Mobile verification is progressive: it must not block basic account entry or exploration, but is required before hiring, WhatsApp connection, payment initiation, recovery activation, sensitive account changes, or another server-classified consequential action.

### Provider Issuer/Subject Binding

The provider issuer and provider subject together are the binding key for a login method. Email address alone is not sufficient to identify a binding. A confirmed email from one provider does not automatically link to another login method that shares the same address. The stable provider subject is the durable key; email is an auxiliary claim that may change.

### Proof-of-Control Account Linking

Separate login methods may reconnect to one WAOOAW account only after a live proof-of-control challenge for the new method. The challenge is single-use, short-lived, bound to actor subject and intended command, and produces no account-existence disclosure at any step. Automatic email-only linking is prohibited.

### Non-Enumerating Behavior

No public operation discloses whether an email address, mobile number, tenant identifier, or provider subject is already registered. All identity error responses use stable non-enumerating codes. No response body, HTTP status differential, or timing variation reveals an account-existence fact.

### Facebook Login Scope Isolation

The Meta application used for Keycloak-brokered customer login is a separate security principal from the Meta Business Manager application used by the DMA agent (ADR-026). The customer-login Meta application:

- requests only `email` and `public_profile` scopes (basic login information);
- must never request page management, advertisement, post, contact, WhatsApp Business management, publishing, business-activity, DMA Business OAuth, or any other business or marketing permission;
- uses separate client ID, client secret, redirect URI, consent text, and app registration from the DMA Business OAuth application.

Customer-login Meta credentials and DMA Business OAuth credentials must not be shared, aliased, or combined under any configuration.

### Provider-Specific Activation Gates

Providers are enabled in Keycloak configuration only after their activation prerequisites are satisfied. This amendment records approved policy for all four providers; it does not satisfy or waive any activation gate.

| Provider | Activation status | Blocking prerequisites |
|---|---|---|
| Google | READY subject to environment configuration evidence | None |
| Email fallback | READY subject to Keycloak flow evidence | None |
| Facebook / Meta | **BLOCKED** | FA-002 — Meta Business Manager verification; FA-018 — customer-login app credentials and configuration evidence |
| Apple | **BLOCKED** | FA-019 — Apple Developer account, Service ID, private key, relay-domain configuration, and provider acceptance evidence |

Facebook activation remains gated on FA-002 and FA-018. Apple activation remains gated on FA-019. This amendment records the Founder-approved policy; activation requires separate completion of the named prerequisites.

### Authorization Boundary

This amendment records the Founder-approved customer identity policy (FA-035). It does not authorize implementation of any F2 or F3–F8 component; activate any identity provider; authorize deployment to any environment; authorize merge of any pull request; or constitute an independent architecture review of the WC-034 F2 identity and registration contract package. The independent architecture re-review (gate `G-F2-12`) must be performed in a separate context under C-065 before F2 implementation begins.

---

## Amendment 2 - WC-085 Unattended Tenant Publication (v4 - 2026-09-09; SUPERSEDED)

**Historical only:** Amendment 3 supersedes this entire Java/publication selection, its dependency
approval and its assertion that ADR-003 remains unchanged. Retained source/Java is not deleted or
authorized for use by this record. Do not implement, build or deploy Amendment 2.

**Decision author:** INST-004 Enterprise Architect, bounded EDIT authority, not a review.
**Authority:** Founder explicitly approved changing how signup connects to login so signup stays
automatic without granting extra credential powers. This supersedes the stock-Keycloak-only
constraint for WC-085, not credential separation. No deployment, provider activation, cloud
operation, spending, merge or general office review is authorized by this amendment.
**Traceability:** Customer Account Completion and Provider Issuer/Subject Binding in Amendment 1;
C-032 office/authority separation, C-026 database enforcement, C-059 evidence and ADR-003 signed
tenant isolation. Existing parent implementation authority remains distinct from this docs-only call.

### Selected Design And SaaS Boundary

Add one narrow Java `RealmResourceProvider` extension to the existing Keycloak process and build
a derived Keycloak image. BP publishes only committed initial tenant/membership attributes through
this endpoint. Keycloak retains credentials, Google broker links, sessions, signing keys and token
issuance. Stock attribute mappers and OIDC renewal remain. No new service, BP-issued customer JWT,
custom token grant, direct Google API, shared tenant, browser-selected tenant or approval per signup.

This follows the conventional SaaS separation: external identity proof through Keycloak, application-
owned accounts/organisations/membership, a trusted signed tenant claim, and independent current
actor/membership/resource authorization within that tenant. A JWT is not current membership truth.
ADR-003 is unchanged: current authorization may restrict the signed anchor, never replace it with
a tenant found by lookup or supplied by the browser. This is not a regulatory compliance certification.

For WC-085, `waooaw_roles` is the BP-owned protected membership attribute, not grants of Keycloak
realm roles. It grants no institutional, employment, payment or consequential authority. This
specializes the v2 organisation-role description; other authentication paths remain unchanged.

### Credential And Mutation Contract

The [WC-085 decision note](../architecture/reference/product/wc085-identity-architecture-decision.md)
specifies the normative private wire contract. Register `waooaw-identity-publication` in realm
`waooaw`, with exact-subject broker-proof GET, publication GET and initial-publication POST only.
No generic user representation, search/list, credential, broker mutation or role API is exposed.
Mutate only `tenant_id`, `waooaw_roles`, `org_name` and provider-private replay metadata.

Use reserved confidential client `waooaw-bp-identity-publisher`, its separate environment secret,
and standard `client_credentials`. On every route require native Keycloak RS256 token validation,
exact configured issuer, audience exactly `waooaw-identity-publication`, authorized party exactly
that client, scope `wc085:identity-publication`, and subject equal to its enabled service account.
Validate times, revocation/not-before state and maximum 60-second lifetime. Attach the dedicated
audience/scope only to that client. Disable interactive/direct grants, offline access and unneeded
scopes; do not attach customer claim mappers or a customer API audience. No new JWT grant is invented.

Assign ZERO realm-management roles, including no `view-users`, `manage-users`, fine-grained group
management, impersonation or inherited admin composites. Proof reads move to the extension; ALL
stock Admin REST APIs, including user reads/listing, must deny this same credential. Never inject
bootstrap/operator credentials into BP or the provider. Retain Security's TLS, secret rotation,
token custody and private-origin rules. The public ingress must not expose extension routes.
The privileged in-process provider enforces authentication and field limits, not BP code alone.

BP submits only the exact immutable payload loaded through its actor-scoped Data routine after
commit. Keycloak receives no BP database credentials or callback endpoint. The publication credential
can assert these business attributes across eligible customers; it does not independently attest
a database commit. It must not control identity proof, credentials or institutional roles. Current
DB authorization denies forged tenant/membership access. This limited publication-compromise risk
is explicit, not a claim of per-customer machine credentials or independent transaction verification.

### Identity, Replay And Concurrency

Compare the exact realm issuer/subject and eligible local customer with the configured Google
association and committed proof. Preserve opaque upstream subjects; email cannot establish identity.
BP separately requires the signed current broker-session claim and fresh reconstruction proof.

Permit one immutable initial payload per nonrecycled actor key. Store replay metadata and the three
fields in one Keycloak transaction. Serialize using a database pessimistic lock on the local user
row, read fresh storage under the lock, and invalidate caches correctly on commit. Exact replay
returns `ALREADY_APPLIED`; differing intent/revision/proof/digest/payload conflicts without mutation.
Unmarked preexisting owned attributes also conflict. No last-writer-wins or mutable sync is approved.

Retain Data's BP publication lock and current eligibility/revision checks. BP must read back actual
fields AND broker proof before acknowledgement. Reconstruction binds a different nonrecycled actor
to the same proven Google identity and durable BP account/tenant. A late write to a retired actor
cannot authorize it; DB checks deny it. Revocation never waits for publication. No distributed
transaction or guarantee of zero stale claims is claimed.

### Explicit Dependency And Build Approval

Approve Java **21** solely for this in-process extension; ADR-016's .NET/Python service choices
remain. Pin Keycloak **25.0.6**, runtime base
`quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2`.
Compile against `org.keycloak:keycloak-core`, `keycloak-server-spi`, `keycloak-server-spi-private`,
`keycloak-services` and `keycloak-model-jpa`, all **25.0.6**, provided scope. Private/JPA dependencies
are explicitly approved for native bearer authentication and local-user locking. They are pinned
internal dependencies, not promises of stable public APIs.

Use Maven **3.9.9**, compiler plugin **3.13.0** with release 21, JAR plugin **3.4.2**, Surefire
**3.5.2**. Parent must resolve/record an immutable Java 21 builder-image digest and exact JDK patch
before qualification; none is invented here. Pin remaining plugins/test dependencies and artifact
checksums; prohibit snapshots/ranges. Build entirely in Docker; register the provider factory through
`META-INF/services`, copy the thin JAR into `/opt/keycloak/providers/`, and run `kc.sh build` on the
pinned server with explicit database/feature settings. Do not bundle Keycloak/Jakarta libraries.
Use a fixed source-derived output timestamp and two clean builds to verify identical JAR checksums;
record final image digest/provenance rather than assume identical OCI bytes.

Target `RealmResourceProvider`/`RealmResourceProviderFactory`, native
`AppAuthManager.BearerTokenAuthenticator` and `JpaConnectionProvider`/`UserEntity` pessimistic locking
from 25.0.6. This design is for local JPA users only. Verify transaction lock lifetime, rollback and
cache coherence against the selected database, including concurrent server instances. No custom
table, distributed lock service or preview fine-grained feature is selected. Unsupported storage
must fail closed. The existing process avoids another service but adds trusted Java code, image
supply-chain work and exact-version upgrade/permission regression tests.

### Authoring And Qualification Status

Repository image pins and ADR-016 establish the baseline; prior Security Docker evidence rejects
the stock writers. This authorship did not fetch upstream source, compile a provider or test its
security. API/build/locking compatibility is required executable evidence, not a reported PASS.
The 25.0.6 compatibility pin is not an assertion of current vendor security support or lack of CVEs.

**Architecture AUTHORED and SELECTED.** The stock-only scope obstacle is superseded. Parent can
implement under standing authority, incorporating the exact contract deltas in the decision note.
Implementation and qualification remain pending; CB-009 is not closed. No deployment or real Google
acceptance is claimed. No further Founder technical selection or general review loop is required
for this covered decision. Historical authority limits in Amendment 1 do not negate this new scope.

---

## Amendment 3 - Stock Broker And BP Membership (v5 - 2026-09-09)

**Author/authority:** EA INST-004, bounded Solution repair under the current Founder C#/Python/JS-only
direction and standing edit authority. This C-032 author amendment supersedes Amendment 2 in full
and v2 customer tenant/organisation-role claim requirements for WC-085. It explicitly depends on
the changed per-request lookup rule in ADR-003's controlling amendment, not the original rule.
No new language, dependency, auth framework, service or JWT issuer is approved. Reuse stock pinned
Keycloak, ASP.NET authentication, existing EF/Npgsql and JS server-session code. No custom Java,
SPI, derived provider image, runtime Keycloak writer or publication endpoint is part of this slice.

Stock Keycloak verifies Google and signs customer identity. BP commits account, organisation,
initial OWNER membership, actor/provider binding, proof provenance and existing registration/retry
result in ONE PostgreSQL transaction. Completion is final at that commit: no publication intent,
outbox, revision, acknowledgement or post-commit remote mutation. Current actor-keyed membership,
not token tenant/role attributes, supplies authorization under ADR-003 and C-026 RLS.

### Proven Stock Broker Read

Select the stock exact-user and federated-identity GETs already recorded in
[Security Section 8](../architecture/reference/security/wc085-identity-publication-security-contract.md).
Use a dedicated confidential client `waooaw-bp-identity-reader`, `client_credentials`, only the
`realm-management` role `view-users` explicitly assigned and scoped, maximum 60-second token,
no interactive/direct/offline grants. The environment-local
`IdentityBrokerRead__ClientSecret` references `bp-identity-reader-client-secret`, injected ONLY
into BP per ADR-014; `IdentityBrokerRead__ClientId` is the literal reader ID. No administrator,
publisher, web or broker credential reuse. No `manage-users`, `query-users`, write grant or
administrative composite. `view-users` DOES permit realm-wide user metadata/list reads: this
bounded read exposure is explicitly accepted, not described as per-user Keycloak enforcement.
BP provides no listing/search or arbitrary-subject proxy and retains no generic user representation.

From the exact validated caller subject, over configured private TLS with no redirects, read only
`GET /admin/realms/waooaw/users/{subject}` (enabled, non-service-account eligibility) and
`GET /admin/realms/waooaw/users/{subject}/federated-identity`. Encode subject as one path segment;
no browser subject/host/realm selector. Require exactly one configured `google` record and retain
its exact opaque `userId` with configured trust namespace/alias as stable broker identity.
No email match, upstream-token retrieval or invented stable-subject session note. Require the
stock signed `idp` session claim using `oidc-usersessionmodel-note-mapper` and note
`identity_provider=google` to distinguish current broker login from an old linked record; this
is the ALIAS, not the upstream subject. Missing current-session alias, verified email, `auth_time`
or broker proof fails closed. Existing local evidence covers reads/denied writes, not a real Google
session or that mapper's issuance in the configured web flow; those remain executable gates.

Ordinary return with the SAME validated issuer/subject reuses the membership without broker GET
on each protected request. First completion requires the two reads, fresh authentication at most
five minutes old, and unchanged reviewed trust configuration. Disable automatic email-only linking
and self-service broker relinking for this bounded Google path; do not enable other login paths.
The role `customer` permits only customer-scheme eligibility; it never grants institutional roles.

### Continuity And Delivery Limits

Retain stable Google proof now, but a new Keycloak subject matching that proof does NOT silently
rebind or mint a second account. Return the existing non-enumerating recovery/duplicate outcome.
Recreated-realm recovery is a FUTURE gate: accepted proof of current Google authentication, historical
binding, nonrecycled actor IDs, atomic retirement/rebinding, old-session denial and retained IDs
under concurrent recovery must be qualified before enabling it. No reset, persistent-Keycloak
change or migration of identity namespaces is authorized here. Stable local fixtures can qualify
the initial slice, but cannot prove Google consent or preserved-data reconstruction.

Tenant claim mappers/shared constants are unnecessary for this path and must not supply authority.
Completion can use the SAME still-valid Keycloak token for `getIdentitySession`; no refresh solely
to obtain tenant claims. Normal expiry/PKCE and account-switch protections remain. Initial OWNER
grants entry/exploration only, no automatic employment, payment, trial, subscription or entitlement.

**Current recommendation: ready for bounded parent implementation under standing authority.**
Physical Data translation is the one small follow-on authorship item specified in the decision
note; no new general review or Founder option selection. Implementation/real-PG/Google evidence
remains pending; CB-009 is not closed. This call is docs-only and does not authorize deployment.


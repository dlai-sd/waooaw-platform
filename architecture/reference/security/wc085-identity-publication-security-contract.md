# WC-085 Identity Publication Security Contract

## Controlling Architecture Amendment - 2026-09-09

**Author:** EA INST-004, bounded Solution repair under standing Founder edit authority; not a new
INST-007 review/concurrence. ADR-003's controlling amendment and ADR-008 Amendment 3 explicitly
change the customer authorization boundary under C-032. **Publication is superseded, not cleared.**
The stock write-denial findings in Section 8 remain valid historical evidence; no extra credential
powers are accepted. This is no longer an implementation blocker requiring a Java publisher.

The following replaces Sections 1-7 wherever they require publication, tenant/role JWT authority,
post-publication renewal or automatic recreated-actor recovery:

- Select ONLY stock Keycloak 25.0.6 exact-subject user/federated-identity GETs and read-only
	`view-users`, as evidenced in Section 8. Use dedicated `waooaw-bp-identity-reader` client,
	`IdentityBrokerRead__ClientId`, `IdentityBrokerRead__ClientSecret` referencing environment-local
	`bp-identity-reader-client-secret`. Retain Section 1's private TLS, no redirects, scope minimization,
	client-credentials/60-second token, secret rotation and BP-only custody. Do not reuse an existing
	publisher credential that may have write grants. Effective permission denials need qualification
	for this reader's final configuration; historical probes are not evidence for a new deployment.
- `view-users` is realm-wide user metadata access including listing, not caller-only ACL. Accept
	that explicit read exposure within BP's binding responsibility; expose only the two exact-subject
	adapters internally and never a browser/search/list proxy. No `manage-users`, `query-users`,
	realm-admin/composites, fine-grained write workaround, upstream-token read or Java extension.
- Retain Section 4's exact Google `userId`, configured namespace/digest and stock signed
	`identity_provider` -> `idp` ALIAS mapper. No stable upstream-subject note is invented. Initial
	completion requires both exact live broker record and validated current Google session with
	verified email and authentication at most five minutes old. Missing proof denies; token issue or
	refresh time is not authentication time. Disable self-service relinking/other login paths for the
	first slice. New-subject continuity is deferred and fails unresolved, never email-linked or reset.
- Keycloak writes and tenant/role/plan publication mappers are not required. Ignore all such token
	attributes as authorization sources; remove shared-tenant authority from the activated customer
	path. Retain user-profile protections against accidental reuse and generic unmanaged attributes.
	Tenantless customer tokens remain valid identity proof after completion, not a substitute for
	membership. The same unexpired token may call session; refresh is only normal session lifecycle.
- BP validates and resolves exact `(iss, sub)` to authoritative active membership. CE, PR, WBE and
	AI independently validate ORIGINAL raw caller JWT plus allowed service peer/operation over mTLS,
	call the read-only identity DB operation with their OWN restricted service login, and check their
	own resources and constitutional permissions under RLS. No trust in arbitrary BP tenant headers,
	decoded claims or BP's allow decision; no cross-ledger SELECT grant. ADR-003 fixes the exact
	shared audience/customer-client validation and DTO/storage interface. C-026 remains mandatory.
- Preserve server-only token storage, no-store/CSRF/session cleanup, expected-account comparison,
	expiry and account-switch cancellation. Preserve 15-minute access/eight-hour refresh maximum,
	zero-reuse rotation and five-minute consequential freshness. Initial OWNER means account entry,
	not institutional authority, mobile proof, payment, trial or subscription. Server policies deny
	unsupported actions irrespective of API capability hints. Unadopted service/job/callback paths
	fail closed; existing independently authorized Emergency Stop activation is not disabled.

CB-009 remains open for physical Data mapping and implementation/evidence, not a pending stack
selection or general Security review. Initial synthetic stable-fixture PostgreSQL tests cannot prove
real Google authentication, mapper issuance, recovery, cloud ingress or Production readiness.
No tests were run here. The
[current decision](../product/wc085-identity-architecture-decision.md) fixes the first delivery check.

## Historical Publication Contract And Evidence

Sections 1-7 below are historical where superseded above. Section 8 remains historical local evidence,
with its stated limits; it is not upgraded to PASS for the replacement design.

**Author:** INST-007, Security Architect, 2026-09-09.
**Authority:** Founder-assigned CB-009 boundary repair with edit authority; continuous-session
bootstrap remains valid. No additional office invocation or review is represented.
**Disposition:** Security contract authored; **publication NOT CLEARED**. The stock write
permission conflict in Section 7 blocks dependent provisioning implementation and qualification.
Read, proof, profile, and session decisions below are normative, not claims of deployed controls.

This is the bounded WC-085 supplement to [security-architecture.md](security-architecture.md).
It specializes [Identity Boundary](../components/identity-boundary.md) Sections 5.1-5.4, 8.4,
11.1 and 14.1 without changing their authority floor. ADR-003, ADR-008 and ADR-014 continue to
control tenant claims, broker ownership and secrets. The authentication, participant verification,
takeover and payment-consent controls in [AE-01](../product/ae01-security-contract.md) remain
independent: initial customer `OWNER` membership grants no employment, institutional, payment or
Emergency Stop release authority. Data's physical mapping is separately owned; this file does
not invent its schema or claim Data concurrence.

## 1. Principal, Transport And Credentials

The customer realm is exactly `waooaw`, with its exact environment issuer from the reviewed
manifest. Neither `master` nor an institutional realm is a customer-realm substitute.

Reserve confidential OIDC client `waooaw-bp-identity-publisher`, service accounts enabled,
`publicClient=false`, `standardFlowEnabled=false`, `implicitFlowEnabled=false`,
`directAccessGrantsEnabled=false`, `fullScopeAllowed=false`. Disable optional/default scopes
unneeded for machine access, including `offline_access`; use explicit role scope mappings.
This principal is not `waooaw-web`, `waooaw-platform`, `admin-cli`, the bootstrap administrator,
an operator, or a customer. It cannot authenticate a customer or become a customer session.
Set the client `attributes["access.token.lifespan"]` override to `"60"`.

Runtime configuration contract: `IdentityPublication__ClientId` has the above literal client ID;
`IdentityPublication__ClientSecret` references environment-local secret
`bp-identity-publisher-client-secret`. Per ADR-014, use a git-ignored local secret, encrypted CI
environment secret, or Key Vault secret reference injected only into BP. Use a distinct random
secret per environment, never the web, broker, bootstrap or realm administrator credential.
Rotate at least every 90 days and immediately on suspected exposure, revoke old credentials,
and keep machine access tokens in BP memory only with a maximum configured lifespan of 60 seconds.
Do not request offline or refresh tokens; renew machine access by client credentials.

Acquire tokens by server-only `POST /realms/waooaw/protocol/openid-connect/token`, with
`grant_type=client_credentials` and confidential-client authentication. Administrative operations
use the separately configured, allowlisted private Keycloak origin and TLS with certificate
verification. The public issuer remains the JWT issuer even when BP uses an internal connection.
Do not derive hosts, realms, redirects or URL paths from caller input; URL-encode the validated
subject as one path segment. No browser access to administrative paths or credentials. Do not
follow administrative HTTP redirects. Existing private topology is required; no new service,
proxy, plugin, public route or persistent-Keycloak redesign is selected here.

**Grant decision:** no production write grant is selected or authorized. For broker/user read-only
work, the stock minimal realm-management role is `view-users`, explicitly assigned both to the
service-account user and the client's scope mappings. It is realm-wide user read, not caller-only
read; do not add `query-users`, `manage-users`, `manage-realm`, `manage-clients`, `impersonation`,
`realm-admin`, or broad composites merely to obtain these direct reads. Validate effective token
roles, not only the client configuration. This read-only role must not be presented as a working
publisher. Direct reads, realm-wide listing and write denials were verified in Section 8.

Realm-wide read access is acceptable within BP's existing realm-wide registration/binding
responsibility, conditional on server-only credential handling, exact-subject adapter selection,
no user-search/list interface, minimized retention and redacted security evidence. It remains a
credential-compromise exposure of realm user/binding metadata, not a per-customer Keycloak ACL.

## 2. Exact Operations And Attribute Ownership

| Logical operation | Stock HTTP interface | Selection and effect |
|---|---|---|
| Read broker binding | `GET /admin/realms/waooaw/users/{subject}/federated-identity` | Exact subject from validated customer JWT, then current actor binding; no email or username search. Return one configured Google binding only. |
| Read publication state | `GET /admin/realms/waooaw/users/{subject}` | Same actor, reloaded from the durable intent for publication/retry. Accept only enabled eligible customer users. |
| Publish committed state | `PUT /admin/realms/waooaw/users/{subject}` | **Blocked pending Section 7 resolution.** Intended payload is the attributes object only, merging preserved attributes with committed `tenant_id`, `waooaw_roles`, `org_name`. No caller-supplied representation. |
| Verify publication | Repeat both reads | Match the stable broker key and exact owned attribute arrays; reread current BP eligibility/revision before acknowledging. A `204` alone is not acknowledgement. |

BP owns these publication fields across its legitimately provisioned customer population:
`tenant_id` is a single canonical UUID; `waooaw_roles` is the distinct current membership set
restricted to `OWNER`, `MANAGER`, `VIEWER`; `org_name` is the committed organization display name.
Initial independent Google customers receive distinct BP-minted tenants and one active `OWNER`
membership each. No tenant, account, subject or role selection comes from browser parameters.
The private adapter must not expose a generic user-update operation.

Publication cannot create/delete/disable users, set credentials or required actions, verify email,
edit broker links, map realm/client roles, impersonate, manage groups, edit profile policy/mappers,
write plan/subscription/institutional attributes, or edit unrelated profile data. Those are actual
prohibited capabilities under the current component contract, not just omitted application calls.
Read-modify-write must preserve unrelated attributes, but it is not a Keycloak attribute ACL or
atomic compare-and-swap. Serialize all BP publishers per actor, fence obsolete intent revisions,
and stop on a foreign tenant, changed broker binding or unexpected owned values. Out-of-band
writers must not concurrently edit BP-owned fields. Current DB checks deny stale/revoked authority
even if a remote write completed after a local failure; never mint a replacement tenant on retry.

## 3. Protected Profile And Token Configuration

On stock 25.0.6, configure managed user-profile attributes for `tenant_id`, `waooaw_roles`, and
`org_name`, with `permissions.view=["admin"]` and `permissions.edit=["admin"]`. Only
`waooaw_roles` is multivalued. Disable unmanaged attributes: omit/null `unmanagedAttributePolicy`
in this release; literal `"DISABLED"` was rejected in the local probe. No user/self-registration,
Account Console, update-profile action, identity-provider attribute mapper or submitted form may
set these protected fields. Do not make them user-required fields. Preserve the existing reviewed
email/profile definitions; validate cardinality, UUID syntax and allowed roles again in BP.

These profile permissions distinguish customer users from administrators; they do **not**
distinguish BP's administrator from other administrators or restrict it to these attributes.

Replace the shared Demo constant with stock `oidc-usermodel-attribute-mapper` mappings on every
approved customer client that issues BP tokens:

| User attribute | Claim | Mapper configuration |
|---|---|---|
| `tenant_id` | `tenant_id` | `user.attribute=tenant_id`, String, `multivalued=false` |
| `waooaw_roles` | `waooaw_roles` | `user.attribute=waooaw_roles`, String, `multivalued=true` |
| `org_name` | `org_name` | `user.attribute=org_name`, String, `multivalued=false` |

Use `access.token.claim=true`; emit the same values in ID tokens only where the reviewed server
session needs them. Disable UserInfo emission unless needed. If `organisation_id` is emitted,
map the same `tenant_id` attribute, never an independently editable value. Absent tenant attributes
produce no tenant claim, not a default. Keep the audience mapper for `waooaw-platform`; expose
base customer eligibility through the reviewed realm-role mapper and normalize it at BP as in
Identity Section 3.1. Organization roles are attributes backed by DB membership, not newly assigned
realm roles. No hardcoded tenant or mutable user attribute may supply authentication assurance.

## 4. Trusted Google Proof And Continuity

Use exact configured broker alias `google`; normalize only that reviewed alias to the application's
Google enum. The upstream subject is the nonempty opaque `userId` returned by the stock federated
identity record, preserved case-sensitively without trimming, lowercasing or deriving it from email.
`userName`, email, display name, caller `idp` hints and user attributes are not stable proof.

Assign immutable environment-local trust namespace `urn:waooaw:identity:demo:google:customer-login:v1`
for this Demo configuration; other environments require distinct configured namespaces. It is an
opaque binding namespace, not an invented Google issuer URL. Preserve it across a disposable
Keycloak reconstruction only when the same approved provider trust configuration is restored.
Changing it is an identity migration, not an automatic match.

A linked broker record proves a stored association, not which provider authenticated the current
session. Require a Keycloak-signed broker-session alias: stock
`oidc-usersessionmodel-note-mapper`, `user.session.note=identity_provider`, `claim.name=idp`,
`jsonType.label=String`, `access.token.claim=true`. Require exact `google` plus the server-read
binding for WC-085 Google acceptance. Never use an editable user-attribute mapper for that claim.
Missing/ambiguous/conflicting session or binding proof fails unresolved; do not infer Google merely
because the realm has a Google provider. Preserve `storeToken=false`, `trustEmail=false`, approved
first-broker-login proof controls and verified-email validation. No upstream token retrieval API,
email-only automatic linking, password grant or local-account fallback qualifies this journey.

For a recreated actor, require fresh Keycloak authentication no older than five minutes and exact
namespace/alias/upstream-subject match to historical durable proof. Atomically retire the old
issuer/subject and bind the new one through Data's concurrency protocol, preserving account,
tenant and membership IDs. Retired actors and their challenges/replay keys deny on every BP entry;
do not trust a still-valid old JWT. Recovery does not grant `AAL3_FRESH` by itself or additional
login methods. Missing historical proof stays unresolved even if email matches. No shared tenant,
implicit reset, or regenerated account is a continuity substitute.

## 5. Renewal And Entry

Follow Identity Section 11.1: completion success stores the expected account and originating
issuer/subject in the server-owned continuation, not browser authority. After verified publication,
perform at most one server-held refresh-token exchange. Use refresh rotation with zero reuse,
15-minute access tokens, and an eight-hour SSO/refresh maximum for WC-085. This specializes the
older general 24-hour refresh sentence in the security architecture; refresh never resets
`auth_time` or establishes fresh authentication. Serialize refresh per server session so parallel
requests cannot race rotated tokens.

Validate signature/RS256, exact issuer, audience, expiry/not-before, subject, authentication time,
broker proof, tenant UUID, base customer role and organization-role shape before replacing server
session state. Reject machine tokens as customer tokens. Missing refreshed claims or rejected
refresh permit one authorization-code/PKCE round trip with server-held state, nonce and verifier.
Use fresh authentication when required; `prompt=select_account` alone is not freshness evidence.
Never loop or upgrade the old token using a BP tenant lookup.

Changed issuer/subject cancels this completion handoff and invokes clean account-switch handling.
With the renewed JWT, BP's existing identity-session operation must validate the active actor,
account and membership in the claim-selected tenant and return the exact expected account before
protected navigation. Wrong tenant/account, removed membership, stale/replayed continuation or
retired actor denies. DB authority is current and can only restrict the JWT anchor, not replace it.
Use the existing privacy-safe 401/403/404/409/503 outcomes in Identity Sections 5 and 9.

Server-only token storage, `no-store` responses, secure HTTP-only session cookies, CSRF protection,
and full protected cache/draft/challenge cleanup on logout or switch are mandatory. Customer A's
pending refresh/completion must not replace customer B's newer session. AE-01 consequential
authorization, mobile/factor proof and participant checks remain additional requirements.

## 6. Application Boundary And Residual Risk Decision

An application allowlist and durable intent validation are appropriate controls for BP's assigned
tenant/membership publication across all customer users. Realm-wide reach within that population
is not inherently an unauthorized new business authority, and must never be described as
Keycloak-enforced "only the authenticated user". Such controls limit bugs and confused-deputy
requests; they do not constrain an attacker holding the service credential.

Here, stock write grants additionally control credentials and trusted broker associations; broad
`manage-users` also granted `founder` in the actual fixture. This is outside tenant/membership
ownership, compromises the proof source used for continuity, and can expand authority beyond
customer entry. Private networking, short machine-token TTL, code allowlists, audit events and
DB checks do not turn those privileges into denied operations or preserve independent credential
authority after compromise. **Security does not accept these extra capabilities as residual risk
under the current contract.** Never substitute bootstrap/admin credentials on 401/403.

## 7. One Concrete Remaining Conflict

Identity Section 5.4 requires stock-enforced denial of credential, role, broker-link and unrelated
attribute mutation while Section 5.2 requires a stock user `PUT`. Keycloak 25.0.6's `manage-users`
does not provide that separation. Its stock preview fine-grained group `manage-members` permission
restricts the target population and realm-role mapping, but still allows password reset, broker-link
replacement and unrelated admin-editable attributes for permitted users. User-profile `admin`
permissions cannot distinguish attribute ownership among these administrators.

Therefore no tested stock write configuration satisfies the accepted floor. Keep publication
pending/unavailable and qualification blocked; neither broad `manage-users` nor fine-grained
`manage-members` is an approved deployment choice. The latter also needs group-enrollment authority
for future broker users and preview-feature approval; it is not an unattended provisioning solution.

Accepting an application-only restriction in place of these explicit Keycloak denials would change
the accepted credential/broker authority and component security floor. It requires an explicit
Founder/EA authority decision and contract amendment, not an implementer's interpretation or another
general review. No such approval is claimed or requested through delegation here. A joint fixture
reset does not resolve this permission conflict. Security's publication portion of CB-009 remains
open on this single issue; overall closure also requires Data and implementation evidence.

## 8. Local Evidence And Limits

The external synthetic probe is `/workspaces/waooaw-operations/wc085-security-probe/probe.sh`.
It reuses realm generation from `scripts/run_wc085_google_reconstruction.sh`: Terraform console
on the current workload module with the existing synthetic tfvars, repository mounted read-only.
The local variant disables Google, removes imported users, and uses an internal Docker network
with no published ports. Plain HTTP and password grants exist only in the isolated fixture.
The setup administrator is never used for candidate-principal assertions.

Pinned images:
- Keycloak: `quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2` (server reports `25.0.6`).
- Shell/curl/jq runner: `mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa` (no Azure CLI command used).
- Terraform: `hashicorp/terraform@sha256:18f9986038bbaf02cf49db9c09261c778161c51dcc7fb7e355ae8938459428cd` (`1.9.8` harness image).

| Candidate-token probe | `manage-users` | Group `manage-members`, no `manage-users` |
|---|---|---|
| Read selected user and exact synthetic broker binding | 200 / 200 | 200 / 200 |
| Publish tenant/membership and verify read-back | 204 / 200 | 204 / 200 |
| Publish second user outside selected group | 204 | 403 |
| Write unrelated admin-only attribute | 204 | 204 |
| Reset selected user's password | 204 | 204 |
| Delete / replace selected user's Google binding | 204 / 204 | 204 / 204 |
| Grant `founder` realm role | 204 | 403 |
| Self-grant `realm-admin` | 403 | 403 |
| Read `master` users; edit realm; edit client | 403 / 403 / 403 | 403 / 403 / 403 |

`results-broad.jsonl` and `results-fgap.jsonl` in that external directory record completed assertions.
The fine-grained run used `--features=admin-fine-grained-authz`; no production feature enablement
is authorized. Setup mistakes were corrected before the reported completed runs: disabled unmanaged
attributes require omitted policy, and this version exposes group rather than individual-user
management-permission configuration.

The additional external `session-profile.sh` probe removes the fine-grained grant and assigns only
`view-users` to the same principal and explicit client scope. Its completed
`results-session-profile.jsonl` records:

| Check | Observed result |
|---|---|
| Read user / broker binding / list users with `view-users` | 200 / 200 / 200; listing demonstrates the actual realm-wide read breadth |
| Publish / password reset / broker deletion / cross-realm read with that token | 403 / 403 / 403 / 403 |
| Ordinary customer changes own display name via Account REST API | 204, changed value confirmed |
| Same customer submits protected attributes before and after publication | 400 with `error-user-attribute-read-only`; protected values remain absent or unchanged on administrator read-back |
| Synthetic password login before publication | No tenant or broker-session `idp` claim; this login cannot qualify as Google proof |
| Refresh after fixture-admin seeds attributes | New access token has exact tenant and `OWNER` array, same subject, and still no Google `idp` claim |
| Reuse old rotated refresh token | 400 `invalid_grant` |
| Authentication time in this password-grant fixture | `NOT_PROVEN`: token omitted `auth_time`; do not treat two absent values as preserved freshness |

The refresh check uses an explicitly synthetic direct-grant client and administrator-seeded fields,
not an authorized BP publisher or the customer web OIDC flow. Account REST calls use a real synthetic
customer bearer token; they are not a browser UI test. The unmanaged field in the rejected mixed
request stayed absent, but an independent unmanaged-only request was not tested. The completed
fixture checks the protected-profile operation before replay, because replay invalidates the session.

Commands executed for the completed probes, with `RUNNER` set to the pinned shell image above,
`PROBE=/workspaces/waooaw-operations/wc085-security-probe`, and the named fixture already started:

```sh
docker run --rm --network wc085-security-proof -v "$PROBE:/probe" \
	--entrypoint /bin/bash "$RUNNER" /probe/probe.sh
docker run --rm --network wc085-security-proof -e PROBE_MODE=fgap -v "$PROBE:/probe" \
	--entrypoint /bin/bash "$RUNNER" \
	-c '/bin/bash /probe/probe.sh && /bin/bash /probe/session-profile.sh'
```

The first run used default stock features. The second used a fresh stock container with the
fine-grained feature enabled, synthetic bootstrap credentials and `start-dev --db=dev-file
--http-port=8080`. These commands reset only their disposable local `waooaw` fixture realm.
Probe artifacts remain outside the repository; the local test container/network are removed at close.

This proves stock local permission conflict, protected Account API attributes and synthetic refresh
behavior, not actual Google authentication, signed Google broker-session note issuance, `auth_time`
preservation, customer web OIDC renewal, BP recovery, database isolation, browser account switching,
deployed private networking, or two-real-customer acceptance. Those unexecuted controls are normative,
not PASS. The two approved real Google identities still require future manual consent and independent
tenant acceptance after applicable gates; no real identity was used in these fixtures.
No cloud/provider mutation, secret fetch, real credentials, commits or pushes occurred. No Demo/public
provider was enabled. No other office's contract or implementation file was edited.
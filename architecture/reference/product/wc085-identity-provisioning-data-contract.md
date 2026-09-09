# WC-085 Identity Provisioning Physical Data Contract

## CURRENT Data Contract - 2026-09-09

**Author: Data Architect INST-006. Status: DATA AUTHORSHIP COMPLETED; implementation and runtime
proof pending.** Founder standing bounded edit authority; bootstrap remains complete. Decision
Space: physical schema, constraints, transaction and database privileges for the selected stock
Keycloak + C# BP design. Obligations: C-005 ledger separation, C-007 append-only evidence, C-026
RLS, C-032 authorship and C-059 truthful evidence. No other office invocation, runtime change,
SQL file, reset, cloud action, commit or push is authorized by this document.

The [current EA decision](wc085-identity-architecture-decision.md) controls the interface and
eligibility policy. **Only this CURRENT section is the active physical contract. Everything after
the Historical Boundary is retained history, including the earlier EA request and Data tables.**
There is no Keycloak attribute synchronization, publication subsystem, recovery outbox, Java
dependency, new service or new database password in this slice. No commercial records are created.

### 1. Source Mapping And Physical Types

Read anchors: [init 03](../../../infrastructure/postgres/init/03-enums-and-tables.sql),
[init 20](../../../infrastructure/postgres/init/20-identity-boundary.sql),
[database roles](../../../infrastructure/postgres/init/02-users-and-permissions.sh),
[WBE grants](../../../infrastructure/postgres/init/12-billing-engine.sql),
[IdentityDbContext](../../../src/business-platform/Infrastructure/IdentityDbContext.cs) and
[IdentityService](../../../src/business-platform/Services/IdentityService.cs).
The existing registration has `ActorSubject`, nullable `ProviderIssuer` and nullable `AccountId`,
but no durable account, actor issuer or stable upstream subject. The comment on ProviderIssuer
is not proof that it contains either missing fact. Preserve that field; do not reinterpret it.

Create exactly four tables: `identity.accounts`, `identity.login_methods`,
`identity.actor_bindings`, `identity.memberships`. Reuse `business.organisations`,
`identity.registrations`, `identity.idempotency_ledger` and `identity.registration_events`.
No separate proof archive, billing binding, completion request/result, intent, publication,
acknowledgement, revision or event/outbox table is required, now or as a future migration dependency.

In the tables below, columns are NOT NULL unless `?` is shown; IDs are `uuid`, timestamps are
`timestamptz`, `created_at` defaults to `now()`. BP generates random UUIDs; PostgreSQL records time.
Every FK is `ON DELETE RESTRICT`. Mark the cycle FKs explicitly identified below
`DEFERRABLE INITIALLY DEFERRED`; other FKs are immediate. Index referencing columns unless covered
by a listed unique index. New identity-key columns use `varchar(256) COLLATE "C"`,
`CHECK (octet_length(column) > 0)` and exact case-sensitive comparison, not citext/lower/trim.
Alias is `varchar(40) COLLATE "C"`, likewise nonempty. Reject overlength, NUL and malformed input;
never truncate. Issuer is the exact validated configured Keycloak issuer. Provider namespace is
the exact configured Google trust namespace, not a browser string or normalized email domain.
Preserve opaque `sub` and broker `userId` exactly; no issuer URL rewriting or subject case folding.

| Physical object | Exact columns, keys and constraints |
|---|---|
| `business.organisations` additive columns | `identity_managed boolean DEFAULT false`; `identity_status varchar(24) DEFAULT 'LEGACY_UNVERIFIED'` CHECK in LEGACY_UNVERIFIED/ACTIVE/INACTIVE. CHECK `NOT identity_managed OR (id = tenant_id AND identity_status IN ('ACTIVE','INACTIVE'))`. Existing `id` PK and `tenant_id` UNIQUE remain. New managed rows set both IDs to the same new tenant UUID, managed=true, status=ACTIVE. Preserve existing rows and defaults. |
| `identity.accounts` | `account_id` PK; `initial_tenant_id` UNIQUE FK organisations(tenant_id), deferred; `origin_registration_id` UNIQUE FK registrations(registration_id), deferred; `status varchar(16)` CHECK in ACTIVE/INACTIVE; `created_at`. CHECK `account_id <> initial_tenant_id`. UNIQUE `(account_id, initial_tenant_id)`. |
| `identity.login_methods` | `login_method_id` PK; `provider_issuer` (configured namespace); `broker_alias`; `provider_subject`; `account_id` FK accounts, deferred; `status varchar(16)` CHECK in ACTIVE/RETIRED; `created_at`. UNIQUE `(provider_issuer, broker_alias, provider_subject)` across ALL history; UNIQUE `(login_method_id, account_id)`. Only the configured Google namespace/alias is accepted by BP. |
| `identity.actor_bindings` | `actor_binding_id` PK; `actor_issuer`; `actor_subject`; `login_method_id`; `account_id`; `status varchar(16)` CHECK in ACTIVE/RETIRED; `proof_source varchar(32)` CHECK = 'KEYCLOAK_FEDERATED_IDENTITY'; `verified_at`; `auth_time`; `trust_config_digest varchar(64)` CHECK `~ '^[0-9a-f]{64}$'`; `correlation_id uuid`; `created_at`. FK `(login_method_id, account_id)` to login_methods, deferred. UNIQUE `(actor_issuer, actor_subject)` across ALL history; UNIQUE `(actor_binding_id, account_id, actor_issuer, actor_subject)`; partial UNIQUE `(login_method_id) WHERE status = 'ACTIVE'`. CHECK `auth_time <= verified_at + interval '30 seconds'`. Proof columns are never nullable. |
| `identity.memberships` | `membership_id` PK; `account_id` UNIQUE; `tenant_id`; `roles text[]` CHECK `roles = ARRAY['OWNER']::text[]`; `status varchar(16)` CHECK in ACTIVE/INACTIVE; `created_at`. FK `(account_id, tenant_id)` to accounts(account_id, initial_tenant_id). UNIQUE `(membership_id, account_id, tenant_id)`. Exactly one initial workspace, not a general role model. |

`organisations.name` receives the accepted nonempty business name (existing registration max 160,
organisation max 200). Preserve accepted business-domain text (max 100) in the profile snapshot;
write the existing max-50 `business_domain` only for an exact accepted taxonomy code, otherwise NULL.
Do not truncate or create taxonomy. Account and tenant UUIDs are distinct. No `identity.tenants`,
shared Demo tenant, payment, wallet, subscription, trial or billing projection is created. Existing
billing IDs and institutional/professional ledgers are neither remapped nor joined by the resolver.

### 2. Additive EF Model And Legacy Gate

| Existing model/table | Additive mapping |
|---|---|
| `IdentityRegistrationRecord` / registrations | `string? ActorIssuer -> actor_issuer`; `Guid? ActorBindingId -> actor_binding_id`; `Guid? OriginRegistrationId -> origin_registration_id` FK registrations; `DateTimeOffset? CompletedAt -> completed_at`; `string? CompletionOutcome -> completion_outcome varchar(24)` CHECK in ACCOUNT_CREATED/ACCOUNT_REUSED; `string? CompletionProfileSnapshot -> completion_profile_snapshot jsonb` CHECK object; `int? CompletionStatusCode -> completion_status_code integer` CHECK = 200; `string? CompletionResponseBody -> completion_response_body text`. Keep existing AccountId/ActorSubject/ProviderIssuer. UNIQUE `(registration_id, actor_issuer, actor_subject)`; deferred composite FK `(actor_binding_id, account_id, actor_issuer, actor_subject)` to actor_bindings. |
| `IdentityIdempotencyEntry` / idempotency_ledger | `string? ActorIssuer -> actor_issuer`; `Guid? RegistrationId -> registration_id`. Composite FK `(registration_id, actor_issuer, actor_subject)` to registrations, deferred. Replace `idempotency_ledger_actor_key_op_unique` and EF's subject-only unique index with UNIQUE `(actor_issuer, actor_subject, idempotency_key, operation_family)`. Keep status/body/hash/expiry storage and exact existing operation family `CompleteRegistration`. |
| registration_events (add EF entity `IdentityRegistrationEventRecord`) | Add `string? ActorIssuer -> actor_issuer`; composite FK `(registration_id, actor_issuer, actor_subject)` to registrations, deferred. Map existing event ID, subject, type, from/to state, correlation and occurred-at fields. Reuse append-only `RegistrationCompleted` evidence with `to_state = 'Completed'`; no raw proof payload. |
| New EF entities | `IdentityAccountRecord`, `IdentityLoginMethodRecord`, `IdentityActorBindingRecord`, `IdentityMembershipRecord` map one-to-one to section 1, explicit snake_case columns, string states, Guid IDs, DateTimeOffset times and `string[] Roles` as `text[]`. Map canonical organisation to `business.organisations`, not the default identity schema; reuse an existing mapping if present. No EF-owned duplicate organisation table. |

Add `actor_issuer` nullable in physical storage and C# so retained legacy rows remain representable.
For registrations/events/idempotency add `CHECK (actor_issuer IS NOT NULL) NOT VALID`: existing
rows remain, but PostgreSQL checks EVERY new insert/update. Add nonempty checks and issuer/subject
`COLLATE "C"` to active key/index expressions (alter the existing subject column's collation without
rewriting its values). New workflow writes require both exact values; no subject-only API lookup.
For completion, add the following NOT VALID checks to preserve unverified old Completed records:

```sql
CHECK (state <> 'Completed' OR (
  actor_issuer IS NOT NULL AND actor_binding_id IS NOT NULL AND account_id IS NOT NULL
  AND origin_registration_id IS NOT NULL AND completed_at IS NOT NULL
  AND completion_outcome IS NOT NULL AND completion_profile_snapshot IS NOT NULL
  AND completion_status_code IS NOT NULL AND completion_response_body IS NOT NULL
));
CHECK (operation_family <> 'CompleteRegistration' OR (
  registration_id IS NOT NULL AND status_code = 200 AND response_body IS NOT NULL
));
```

The second check belongs to idempotency_ledger. Its noncompletion families retain their present
contract. Completion key is canonical lowercase UUID text; hash is lowercase 64-hex SHA-256 of
operation, registration ID and semantic input. Validate those shapes for new completion entries.
Add a completion-only CHECK `expires_at >= created_at + interval '24 hours'` (NOT VALID for
retained legacy entries); keep the existing 25-hour default. Expiry is cleanup eligibility, not
authority to change the durable identity or immutable completion result.
CHECK permits SQL NULL unless explicitly excluded; the nonnull terms above are mandatory.

The original completed registration is the durable association and replay anchor:
`accounts.origin_registration_id = registrations.registration_id = origin_registration_id`.
All subsequent registrations for that actor refer to this root and copy its exact account, binding,
outcome, status, serialized response and accepted profile snapshot. Do not convert ACCOUNT_CREATED
to ACCOUNT_REUSED on retry, replace the original profile, or derive authority from response metadata.
Snapshot keys: displayName, businessName, businessDomain, languagePreference, emailVerified=true
and mobileVerified boolean. No email/phone address, OTP, token or raw broker response. The successful
association and original response outlive draft/retry-key expiry under existing privacy rules;
never purge a referenced successful registration as an expired draft.

Legacy actor-only/unknown-issuer records have no RLS-visible authority and cannot complete or replay.
Do not infer ActorIssuer from ProviderIssuer, split a compound ActorSubject heuristically, invent a
Google subject, fabricate proof, or silently turn historical AccountId into an account/tenant.
No automatic backfill: verified historical import/recovery remains separately gated. Existing
unmanaged organisations remain LEGACY_UNVERIFIED. Old rows are retained, not deleted to satisfy keys.
Composite nullable FKs intentionally leave them quarantined; the new-write checks close that path
for new records. Gate the first slice before admitting traffic during migration.

Verification challenges, account links and portal preferences do not establish initial membership.
Their APIs remain disabled in this slice; no completion write to them is required. Before enabling
one, add nullable `ActorIssuer`, enforce the same new-write/legacy gate, and replace subject-only
lookups/uniqueness with issuer+subject (plus tenant where already present). This is not a dependency
on implementing phone/link/preferences or billing now. Session must use the resolver, not those tables.

### 3. Nonrecursive RLS And Roles

Existing principals: BP `business_app`, CE `constitutional_app`, PR/AI `runtime_app`, WBE `wbe_app`.
PR/AI currently share the runtime principal in the repository; this contract does not invent distinct
logins or claim database separation between them. Preserve each service's existing credential path
and ledger grants. Never give another service BP credentials. Enable a receiving operation only
after its own channel/token/lookup/resource checks qualify.

Use the existing migration administrator as schema/table owner, not an application login. Transfer
`business` schema ownership away from `business_app` (init 02 currently gives it ownership), revoke
CREATE on `business`, `identity` and `public` from PUBLIC and app roles, and ensure no app role owns
the touched tables/functions or inherits an owner, SUPERUSER, BYPASSRLS or CREATEROLE grant. Retain
USAGE. Revoke old table-wide grants on the touched objects before granting the following minimum
column grants; a column REVOKE alone does not undo table-wide grants. This does not transfer ledger
ownership to BP identity or grant cross-ledger writes. No change to database passwords is needed.

Create only one additional **NOLOGIN owner role**, `identity_resolver_owner`, with NOSUPERUSER,
NOBYPASSRLS, NOCREATEDB, NOCREATEROLE and NOREPLICATION. No app may be its member/SET ROLE to it.
It owns only the resolver function, not a table/schema, and has USAGE on identity/business.
Migration administrator may temporarily grant schema CREATE to transfer function ownership, then
must revoke it in the same migration; final owner has no CREATE or write grants.

| Principal | Explicit grants on this slice |
|---|---|
| business_app | SELECT, INSERT on the four new tables; no UPDATE/DELETE/TRUNCATE. SELECT, INSERT on registrations, registration_events, idempotency_ledger; UPDATE only mutable workflow/profile/verification and completion columns of registrations, not registration_id/actor_issuer/actor_subject/created_at. No evidence/idempotency UPDATE/DELETE/TRUNCATE. On organisations, SELECT plus INSERT only `(id,tenant_id,name,business_domain,identity_managed,identity_status)` for this slice; no update/delete of managed identity columns. Preserve unrelated approved organisation operations only with separately bounded grants/policies, never blanket CRUD restoring these privileges. |
| identity_resolver_owner | SELECT only actor_bindings `(actor_issuer,actor_subject,account_id,login_method_id,status)`; login_methods `(login_method_id,account_id,status)`; accounts `(account_id,initial_tenant_id,status)`; memberships `(membership_id,account_id,tenant_id,roles,status)`; organisations `(tenant_id,identity_managed,identity_status)`. No proof, profile, workflow, retry, contact or ledger access. |
| business_app, constitutional_app, runtime_app, wbe_app | USAGE identity and EXECUTE only on the resolver as cross-service identity access. Other than BP's explicit authoring grants above, no new direct identity-table grants. Existing own-ledger grants remain. |

The exact BP registration UPDATE column grant is `(state, email_verified, display_name,
business_name, business_domain, language_preference, account_id, actor_binding_id,
origin_registration_id, completed_at, completion_outcome, completion_profile_snapshot,
completion_status_code, completion_response_body, updated_at)`. Provider/authentication metadata
is supplied on INSERT from the trusted initial proof, not rewritten by profile/completion. Existing
phone/link/other-provider writers are not enabled by this grant. Registration INSERT still requires
RLS actor context and the new-write checks; the trigger freezes all completed fields.

All four new tables, registrations, events, idempotency and organisations use ENABLE and FORCE RLS.
Define exact policy predicates below by substituting the target row/column names, not by creating
helper functions. `I = NULLIF(current_setting('app.identity_issuer', true), '') COLLATE "C"` and
`S = NULLIF(current_setting('app.identity_subject', true), '') COLLATE "C"` are notation only.
Every issuer/subject equality uses C collation. No policy invokes the resolver on its own input tables.

| Table and role | SELECT predicate; INSERT WITH CHECK for business_app where granted |
|---|---|
| actor_bindings, BP + resolver owner | `actor_issuer = I AND actor_subject = S`. Retired history stays actor-visible but never authorizes. |
| login_methods, BP + resolver owner | EXISTS actor_bindings with matching current actor, account_id and login_method_id. |
| accounts, BP + resolver owner | EXISTS actor_bindings with matching current actor and account_id. |
| memberships, BP + resolver owner | EXISTS actor_bindings with matching current actor and account_id. Composite FK fixes tenant to initial account. |
| registrations, registration_events, idempotency_ledger, BP only | `actor_issuer = I AND actor_subject = S`; registrations UPDATE uses the same USING AND WITH CHECK. Legacy NULL issuer is denied. |
| organisations, resolver owner only | EXISTS accounts with initial_tenant_id = target tenant_id. Account RLS reduces this to the current actor. No tenant GUC needed. |
| organisations, BP bootstrap SELECT/INSERT only | `identity_managed AND id = tenant_id AND EXISTS (SELECT 1 FROM identity.accounts AS own_account WHERE own_account.initial_tenant_id = organisations.tenant_id)`. Account RLS binds actor; insert checks identity_status = 'ACTIVE'. This branch is allowed only with BOTH tenant GUCs empty. |

The dependency graph is organisation -> account -> actor; login/membership -> actor. Actor policy
is a direct GUC equality with no subquery. It is nonrecursive even during bootstrap. BP inserts
actor FIRST, login SECOND, account THIRD, organisation FOURTH, membership FIFTH; the specified
deferred FKs allow the transient cycle without disabling constraints/RLS. No bootstrap GUC is a
global bypass, and no unbound organisation insert is allowed. Missing actor context denies even
when a client guesses a tenant. BP may see its own incomplete cohort inside this transaction only.

For normal protected resources use a permissive command policy AND an `AS RESTRICTIVE` tenant
policy for the actual resource roles, with BOTH USING and WITH CHECK requiring:
`tenant_id = NULLIF(current_setting('app.tenant_id',true),'')::uuid AND
tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid`.
Invalid UUID context errors/denies; absent/empty denies. Existing init 04/20 permissive policies
must not OR around this restriction. On organisations give BP an explicit restrictive predicate
`normal_tenant_and_live_actor OR bounded_bootstrap_predicate_above`; the ordinary tenant restriction
for CE/runtime/WBE has no bootstrap branch. Resolver owner is subject to its actor policy, not
these app-role tenant policies, so it works before tenant resolution. BP normal organisation access
additionally requires managed ACTIVE organisation plus live account, actor, login and OWNER membership
using direct EXISTS along the graph above, never a resolver call on organisations.

Other BP protected tables can use EXISTS over the resolver result for active membership in addition
to restrictive tenant RLS; they are not resolver input tables, so this creates no cycle. Add these
policies only to enabled resources. Disabled consequential families remain denied at server entry,
not activated by grants or a tenant UUID. Do not rewrite all ledgers/billing as part of this slice.

### 4. Exact Read-Only Function And Context Boundary

This is the sole public-to-services database operation; no completion stored procedure is needed.
The following is documentation SQL, not an applied migration. Its owner/grants are mandatory:

```sql
CREATE FUNCTION identity.resolve_customer_membership()
RETURNS TABLE (account_id uuid, tenant_id uuid, membership_id uuid, roles text[])
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = pg_catalog
SET row_security = on
AS $function$
DECLARE
  resolved record;
BEGIN
  IF NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') IS NULL
     OR NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') IS NULL THEN
    RETURN;
  END IF;
  BEGIN
    SELECT account.account_id, account.initial_tenant_id AS tenant_id,
         membership.membership_id, membership.roles
      INTO STRICT resolved
      FROM identity.actor_bindings AS actor
      JOIN identity.login_methods AS login
      ON login.login_method_id = actor.login_method_id
       AND login.account_id = actor.account_id
      JOIN identity.accounts AS account ON account.account_id = actor.account_id
      JOIN business.organisations AS organisation
      ON organisation.tenant_id = account.initial_tenant_id
      JOIN identity.memberships AS membership
      ON membership.account_id = account.account_id
       AND membership.tenant_id = account.initial_tenant_id
     WHERE actor.actor_issuer =
         NULLIF(pg_catalog.current_setting('app.identity_issuer', true), '') COLLATE "C"
       AND actor.actor_subject =
         NULLIF(pg_catalog.current_setting('app.identity_subject', true), '') COLLATE "C"
       AND actor.status = 'ACTIVE' AND login.status = 'ACTIVE'
       AND account.status = 'ACTIVE' AND organisation.identity_managed
       AND organisation.identity_status = 'ACTIVE'
       AND membership.status = 'ACTIVE' AND membership.roles = ARRAY['OWNER']::text[];
  EXCEPTION
    WHEN no_data_found THEN RETURN;
    WHEN too_many_rows THEN
      RAISE EXCEPTION 'customer membership invariant failed' USING ERRCODE = '23514';
  END;
  RETURN QUERY SELECT resolved.account_id, resolved.tenant_id,
            resolved.membership_id, resolved.roles;
END;
$function$;
ALTER FUNCTION identity.resolve_customer_membership() OWNER TO identity_resolver_owner;
REVOKE ALL ON FUNCTION identity.resolve_customer_membership() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.resolve_customer_membership()
  TO business_app, constitutional_app, runtime_app, wbe_app;
```

Set migration-owner default function privileges to revoke PUBLIC EXECUTE, and explicitly revoke
PUBLIC on every created function. Grant creation/ownership administratively, never via application
SQL. Fixed catalog-only search_path, qualified tables, no dynamic SQL, no caller-supplied identifiers
and no temp-object lookup prevent object substitution. No LIMIT 1, newest-registration fallback,
tenant parameter, positive membership cache, proof output or organisational-role writes.

Each receiving service validates the ORIGINAL raw Keycloak bearer independently, with EA's issuer,
signature, audience, enabled azp, lifetime, subject, auth_time, Google idp and customer checks.
Authenticate the allowed forwarding peer/operation by existing mTLS identity as well. Do not trust
an arbitrary BP tenant/account header, a decoded JWT or private network placement. Header mismatch
denies; header equality confers nothing. JWT tenant/organisation-role claims are not authority.

Start a transaction on the service's own existing DB connection. Set transaction-local context
using parameterized `SELECT pg_catalog.set_config('app.identity_issuer', $1, true),
pg_catalog.set_config('app.identity_subject', $2, true),
pg_catalog.set_config('app.tenant_id', '', true),
pg_catalog.set_config('app.current_tenant_id', '', true)`; this is the parameter-safe equivalent of
SET LOCAL. Execute the resolver; set BOTH tenant settings transaction-locally from its result, then
apply the service's own resource/action/participant/assurance policy. Missing membership -> 403;
foreign resource -> normalized 404; DB outage/invariant failure -> fail closed without effects
(dependency unavailable -> 503). Local mutations re-resolve in their authorization transaction;
there is no distributed revocation lock or instantaneous cancellation promise.

**Trust limit:** PostgreSQL does NOT authenticate JWTs. Custom GUCs are settable by these trusted
application connections; no PostgreSQL policy can stop a compromised holder of that connection
from supplying another subject. Actor context cannot come from request-supplied issuer/subject or
tenant headers: only the receiving service's validated principal, through one typed interceptor.
Parameterized SQL and no user SQL/identifier/SET ROLE path protect against ordinary injection;
arbitrary SQL execution or stolen DB credentials defeats this context trust boundary. BP also
remains the trusted identity/proof writer and could forge its own writes if compromised. Other
receivers independently validate bearer and peer and never accept BP's membership verdict. The
read-only function owner limits data/operation exposure, not authenticates a subject or proof.
No claim of resistance to a fully compromised BP/database connection is made.

Always overwrite all four settings on entry, even before pre-account work; rollback/commit ends
their local lifetime. Keep Npgsql pool reset enabled (no `No Reset On Close=true`), clear any
application session-level context, and test connection reuse after exceptions as well as success.
Never configure session-level identity/tenant defaults or trust inherited pooled state.

### 5. Atomic Completion, Proof And Concurrency

1. BP validates current eligible Google web session, verified email, stored minimum profile/language
   and authentication age <= five minutes. Use stock private read-only Keycloak view-users with
   the two Admin GETs specified by EA/ADR-008; select the authenticated subject only and require
   its exact configured Google alias and broker `userId`. No email-only linking, search/list
   endpoint, client-supplied proof or permission escalation. Keep the namespace/alias/subject,
   verified_at/auth_time/config digest and correlation only. Read failure or missing/conflicting
   proof cannot return success. Network reads precede the database transaction.
2. Begin ONE EF/Npgsql READ COMMITTED transaction. All contexts use the same DbConnection and
   `UseTransaction`, not independently committed SaveChanges. Compute signed big-endian int64
   from the first eight SHA-256 bytes of compact UTF-8 JSON arrays
   `["wc085-actor",issuer,subject]` and `["wc085-provider",namespace,alias,subject]`.
   Sort/deduplicate these signed values and acquire parameterized `pg_advisory_xact_lock(bigint)`
   in that order; hash collisions only serialize unrelated work. Then SELECT the actor-owned
   registration FOR UPDATE. Every completion, including a different registration/key, uses this
   same lock order. Bound lock/statement/transaction timeouts; no network call inside the transaction.
3. Re-read registration, current actor/login/account/membership and the actor+family+key ledger
   under locks. Check exact actor issuer/subject, Google tuple, active status and completion eligibility.
   Same key/different hash -> 409 IDENTITY_IDEMPOTENCY_CONFLICT with zero mutation. Exact key/hash
   replays only after current proof/access checks; missing/removed/inactive membership never succeeds.
   Pre-account expired/cancelled/foreign registration denies. Completed associations do not expire
   merely because draft expires_at or idempotency expiry elapsed. Retired keys remain reserved.
4. If neither binding exists, mint distinct account/tenant IDs and an OWNER membership, inserting
   in section 3 order with nonnull proof. Set origin registration to itself and persist fixed
   profile/outcome/status/body. If the same active actor and exact Google key already exist,
   reuse account/tenant/membership and load accounts.origin_registration_id; copy its fixed
   completion tuple into the caller-owned registration. Never let a concurrent profile overwrite
   the winner. A different actor with an existing provider key returns unresolved recovery with
   no new account; it may be hidden by RLS, but full-history uniqueness still rejects its insert.
5. Mark the caller registration Completed and append its RegistrationCompleted event plus its
   existing idempotency-ledger terminal 200 response in the SAME transaction. Do not store a
   pending 503 result. Before commit, verify fresh request proof and auth age still within five
   minutes and full cohort/status/tuple equality (section 6). Force deferred constraints immediate
   after all writes. If proof ages out, roll back and reprove; never refresh proof inside the transaction.
   Commit immediately with bounded timeout. Return success only after successful commit.
6. On 40001 serialization, 40P01 deadlock or competing-key 23505, roll back the WHOLE unit, clear
   EF tracking, then retry at most three total attempts with the same keys and unexpired proof.
   Re-read under locks; an invisible conflicting provider/actor key yields non-enumerating unresolved
   recovery, not an insert loop or a new identity. Do not retry unrelated FK/check errors as races.
   Exhaustion -> retryable unavailable. Commit failure rolls back account AND retry/evidence.
   Unknown commit outcome/lost response -> fresh lookup/retry, never compensation or another tenant.

The existing operation family is `CompleteRegistration`; do not rename it to the public operationId.
Uniqueness survives ledger expiry through actor/provider keys and the retained origin registration.
Do not use ON CONFLICT DO UPDATE to relink keys or a fresh key to evade a conflict. Phone verification
is not required for this basic Google OWNER account and confers no payment/employment entitlement.

### 6. Integrity Enforcement Without A Routine Framework

Use ordinary EF DML and the native keys/checks/FKs above. Application grants make all four new
records insert-only in this slice; no retirement/reactivation/rebinding routine is introduced.
The migration administrator's ability to change data is not customer authority. Recovery and
ordinary future status-management writers require separately bounded grants/evidence; do not
expose them as completion options now. No hundreds of per-table CRUD routines are needed.

Two small trigger functions are required in addition to the resolver; both are SECURITY INVOKER,
fixed `search_path = pg_catalog`, qualified static SQL, no PUBLIC EXECUTE and no application
direct EXECUTE grant. Migration owner creates their triggers; they run under BP's RLS/grants.
Exact definitions follow as documentation-only SQL. No SQL file is created or executed.

```sql
CREATE FUNCTION identity.guard_registration_identity() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $guard$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF OLD.state = 'Completed' OR
       ROW(NEW.registration_id, NEW.actor_issuer, NEW.actor_subject, NEW.created_at)
       IS DISTINCT FROM
       ROW(OLD.registration_id, OLD.actor_issuer, OLD.actor_subject, OLD.created_at) THEN
      RAISE EXCEPTION 'immutable registration identity' USING ERRCODE = '23514';
    END IF;
  END IF;
  IF NEW.state <> 'Completed' AND
     (NEW.account_id IS NOT NULL OR NEW.actor_binding_id IS NOT NULL
    OR NEW.origin_registration_id IS NOT NULL OR NEW.completed_at IS NOT NULL
    OR NEW.completion_outcome IS NOT NULL OR NEW.completion_profile_snapshot IS NOT NULL
    OR NEW.completion_status_code IS NOT NULL OR NEW.completion_response_body IS NOT NULL) THEN
    RAISE EXCEPTION 'incomplete association' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$guard$;
CREATE TRIGGER guard_registration_identity
BEFORE INSERT OR UPDATE ON identity.registrations
FOR EACH ROW EXECUTE FUNCTION identity.guard_registration_identity();

CREATE FUNCTION identity.assert_completed_cohort() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $cohort$
DECLARE
  target_registration uuid;
  registration_row identity.registrations%ROWTYPE;
  root_row identity.registrations%ROWTYPE;
  cohort record;
BEGIN
  IF TG_TABLE_NAME = 'accounts' THEN
    target_registration := NEW.origin_registration_id;
  ELSIF TG_TABLE_NAME = 'idempotency_ledger' THEN
    IF NEW.operation_family <> 'CompleteRegistration' THEN RETURN NULL; END IF;
    target_registration := NEW.registration_id;
  ELSE
    target_registration := NEW.registration_id;
  END IF;
  SELECT registration.* INTO STRICT registration_row
    FROM identity.registrations AS registration
   WHERE registration.registration_id = target_registration;
  IF TG_TABLE_NAME = 'registrations' AND registration_row.state <> 'Completed' THEN
    RETURN NULL;
  END IF;
  IF registration_row.state <> 'Completed' THEN
    RAISE EXCEPTION 'completion invariant failed' USING ERRCODE = '23514';
  END IF;
  SELECT account.origin_registration_id, actor.verified_at, actor.auth_time
    INTO STRICT cohort
    FROM identity.accounts AS account
    JOIN identity.actor_bindings AS actor ON actor.account_id = account.account_id
    JOIN identity.login_methods AS login
    ON login.login_method_id = actor.login_method_id AND login.account_id = account.account_id
    JOIN identity.memberships AS membership
    ON membership.account_id = account.account_id AND membership.tenant_id = account.initial_tenant_id
    JOIN business.organisations AS organisation ON organisation.tenant_id = account.initial_tenant_id
   WHERE account.account_id = registration_row.account_id
     AND actor.actor_binding_id = registration_row.actor_binding_id
     AND actor.actor_issuer = registration_row.actor_issuer COLLATE "C"
     AND actor.actor_subject = registration_row.actor_subject COLLATE "C"
     AND actor.status = 'ACTIVE' AND login.status = 'ACTIVE' AND account.status = 'ACTIVE'
     AND organisation.identity_managed AND organisation.id = organisation.tenant_id
     AND organisation.identity_status = 'ACTIVE' AND membership.status = 'ACTIVE'
     AND membership.roles = ARRAY['OWNER']::text[];
  SELECT registration.* INTO STRICT root_row FROM identity.registrations AS registration
   WHERE registration.registration_id = cohort.origin_registration_id;
  IF root_row.state <> 'Completed'
     OR root_row.origin_registration_id IS DISTINCT FROM root_row.registration_id
     OR registration_row.origin_registration_id IS DISTINCT FROM root_row.registration_id
     OR ROW(registration_row.actor_issuer, registration_row.actor_subject,
        registration_row.actor_binding_id, registration_row.account_id,
        registration_row.completion_outcome, registration_row.completion_status_code,
        registration_row.completion_response_body, registration_row.completion_profile_snapshot)
      IS DISTINCT FROM ROW(root_row.actor_issuer, root_row.actor_subject,
        root_row.actor_binding_id, root_row.account_id,
        root_row.completion_outcome, root_row.completion_status_code,
        root_row.completion_response_body, root_row.completion_profile_snapshot)
     OR root_row.email_verified IS DISTINCT FROM true
     OR root_row.authentication_path <> 'Google'
     OR NULLIF(btrim(root_row.display_name), '') IS NULL
     OR NULLIF(btrim(root_row.business_name), '') IS NULL
     OR NULLIF(btrim(root_row.business_domain), '') IS NULL
     OR NULLIF(btrim(root_row.language_preference), '') IS NULL
     OR root_row.completion_profile_snapshot IS DISTINCT FROM jsonb_build_object(
        'displayName', root_row.display_name, 'businessName', root_row.business_name,
        'businessDomain', root_row.business_domain, 'languagePreference', root_row.language_preference,
        'emailVerified', true, 'mobileVerified', root_row.mobile_verified) THEN
    RAISE EXCEPTION 'completion invariant failed' USING ERRCODE = '23514';
  END IF;
  IF TG_TABLE_NAME = 'accounts' THEN
    IF NEW.account_id IS DISTINCT FROM registration_row.account_id
       OR cohort.verified_at < clock_timestamp() - interval '5 minutes'
       OR cohort.auth_time < clock_timestamp() - interval '5 minutes'
       OR cohort.verified_at > clock_timestamp() + interval '30 seconds'
       OR cohort.auth_time > clock_timestamp() + interval '30 seconds' THEN
      RAISE EXCEPTION 'completion proof invalid' USING ERRCODE = '23514';
    END IF;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM identity.registration_events AS event
     WHERE event.registration_id = target_registration
       AND event.actor_issuer = registration_row.actor_issuer COLLATE "C"
       AND event.actor_subject = registration_row.actor_subject COLLATE "C"
       AND event.event_type = 'RegistrationCompleted' AND event.to_state = 'Completed'
  ) OR NOT EXISTS (
    SELECT 1 FROM identity.idempotency_ledger AS entry
     WHERE entry.registration_id = target_registration
       AND entry.actor_issuer = registration_row.actor_issuer COLLATE "C"
       AND entry.actor_subject = registration_row.actor_subject COLLATE "C"
       AND entry.operation_family = 'CompleteRegistration'
       AND entry.status_code = root_row.completion_status_code
       AND entry.response_body = root_row.completion_response_body
  ) THEN
    RAISE EXCEPTION 'completion evidence missing' USING ERRCODE = '23514';
  END IF;
  IF TG_TABLE_NAME = 'idempotency_ledger' THEN
    IF NEW.status_code IS DISTINCT FROM root_row.completion_status_code
       OR NEW.response_body IS DISTINCT FROM root_row.completion_response_body
       OR NEW.actor_issuer IS DISTINCT FROM registration_row.actor_issuer
       OR NEW.actor_subject IS DISTINCT FROM registration_row.actor_subject
       OR NEW.idempotency_key !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       OR NEW.canonical_hash !~ '^[0-9a-f]{64}$' THEN
      RAISE EXCEPTION 'completion replay invariant failed' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NULL;
EXCEPTION
  WHEN no_data_found OR too_many_rows THEN
    RAISE EXCEPTION 'completion invariant failed' USING ERRCODE = '23514';
END;
$cohort$;
CREATE CONSTRAINT TRIGGER account_completed_cohort
AFTER INSERT ON identity.accounts DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION identity.assert_completed_cohort();
CREATE CONSTRAINT TRIGGER registration_completed_cohort
AFTER INSERT OR UPDATE ON identity.registrations DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION identity.assert_completed_cohort();
CREATE CONSTRAINT TRIGGER replay_completed_cohort
AFTER INSERT ON identity.idempotency_ledger DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION identity.assert_completed_cohort();
REVOKE ALL ON FUNCTION identity.guard_registration_identity() FROM PUBLIC;
REVOKE ALL ON FUNCTION identity.assert_completed_cohort() FROM PUBLIC;
```

Nonnull proof source/digest and composite identity FKs are native constraints from sections 1-2,
not inferred by the trigger. BP additionally validates the existing language allowlist and exact
configured Google namespace/alias; PostgreSQL does not verify broker provenance. Returning completion
validates fresh request proof in BP; initial proof timestamps are immutable historical evidence.
The deferred cohort triggers run on creation/transition/replay insertion, not on later membership
reads after retry expiry. Expired-key cleanup must therefore not remove an entry being inserted in
the completion transaction. Existing append-only retention authority is unchanged.

All success paths enforce these assertions in BP before serialization; constraint failure rolls
back, never reports completion. No app UPDATE/DELETE on events/ledger is granted. Reconcile any
pre-existing permissive grants/rules on the touched tables, without adding a CRUD routine framework.

### 7. Parent Handoff And Evidence Boundary

Apply one additive migration and matching EF model update, replace subject-only service inputs with
the validated actor pair, and use the existing completion transaction with the reduced records above.
Extend [the first PG completion test](../../../tests/business-platform.Tests/Identity/IdentityCompletionPostgresTests.cs):
its current init-20-only subject-only fixture/`completion_app` test cannot prove this contract.
Load the canonical organisation and new migration, run service DML as actual restricted `business_app`
and resolver grants as actual other roles, never an administrator-populated account/membership.

First bounded check: two synthetic stable stock-Keycloak identities, independently validated
tenantless tokens and explicitly synthetic read-only broker proofs, complete through BP into distinct
accounts/organisations/OWNER memberships; same tokens resolve their own sessions and account references.
In the same focused slice assert missing/null/expired proof and legacy actor-only completion deny;
case-distinct issuer/subjects are not merged; forged tenant context and swapped registrations/resources
deny under API and actual RLS. Empty tenant bootstrap works only for the actor's own cohort. Probe
resolver-owner and other-role table/write/schema/SET ROLE denials and no recursive RLS error.

Inject a failure before commit to prove account/organisation/membership/registration/event/idempotency
rollback; retry, race two registrations/keys for the same identity and race two actors for one Google
key. Expect one durable cohort, immutable winning snapshot and fail-closed recovery for the other
actor. Check exact-key replay/hash conflict, retry expiry, membership inactivity and pooled-context
reset after success/failure. Sequential test reads by a superuser are observation only, not RLS proof.

Data authorship is complete now. This edit supplies implementation input, NOT executed SQL, passing
PG tests, Security concurrence, real Google consent, restored-identity recovery, deployment approval,
CB-009 closure or Founder acceptance. Same-actor return is supported; restored/different-actor
recovery remains fail closed behind its own gate, without reset or persistence authority. No further
office call is requested absent an actual new architecture conflict. Disabled downstream/commercial
families remain DEFERRED/DISABLED; do not expand the first service-completion check into all billing.

## Historical Boundary - All Remaining Content Is Superseded

The remainder is retained verbatim as historical rationale, not current migration or routine
requirements. In particular its publication/recovery objects and pending-author request are inactive.

## Historical EA Delta - 2026-09-09

**Author:** EA INST-004, bounded Solution repair under standing Founder authority; NOT a physical
Data decision or Data concurrence. ADR-003 customer membership amendment and ADR-008 Amendment 3
supersede the publication design. **All original Sections 1-10 below are historical physical design,
not implementation requirements.** Their publication tables/routines and JWT-selected tenant rules
must not be carried forward. Preserve the history and existing code; no schema/source deletion or
reset is authorized. C-026 RLS, C-032 explicit author amendment and separate ledger ownership remain.

### Minimal Replacement, No Publication Subsystem

Map only these logical durable records onto existing storage, reusing existing workflow/retry/evidence
records. This is not authority to invent all the old tables or choose new physical names here.

| Retained logical record | Required facts |
|---|---|
| Account | Distinct BP account UUID, initial organisation/tenant reference, ACTIVE/INACTIVE; not merely registration history. |
| Existing canonical organisation | BP-generated UUID with organisation ID equal to tenant ID for new managed customers; name, accepted domain mapping and active state. Preserve existing organisation ownership and unverified legacy rows. |
| Initial membership | Stable membership ID, account/tenant relationship, ACTIVE/INACTIVE and exactly initial OWNER. One initial workspace only; no role-management API or publication revision. |
| Stable login key | Exact configured provider trust namespace, broker alias and opaque upstream subject, bound immutably to one account; unique across retained history, never email-derived. |
| Actor binding with minimal proof provenance | Exact Keycloak issuer/subject unique across history, account/login reference, ACTIVE/RETIRED, broker-read source, verified time, authentication time and trust-config digest. Store proof facts here or in existing restricted evidence, not a new raw-proof archive. |
| Existing registration, idempotency and append-only evidence | Durable successful actor/account association, fixed original completion outcome and accepted profile snapshot; issuer/subject/family/key/hash/status/body replay and minimal correlation event. Committed association outlives draft/retry-key expiry. |

Do NOT introduce `completion_intents`, `publication_revisions`, `provisioning_state`,
`publication_acknowledgements`, separate completion request/result tables, publication events/outbox
or publication locks/routines. Separate `broker_proofs` and `billing_customer_bindings` are not
required for this initial slice. Registration creates no billing/trial/wallet/subscription projection.
Existing billing IDs remain untouched; their paths stay disabled until their own mapping qualifies.
No generic multi-workspace/entitlement model is needed.

Completion is ONE existing EF/Npgsql transaction sharing the same connection across participating
contexts: lock/resolve actor + stable provider key + registration, validate uniqueness/current
eligibility, create/reuse the records above, set COMPLETED and save terminal idempotency/evidence,
then commit. Network proof reads precede it; no Keycloak operation occurs inside/after commit.
Exact-key/hash retry replays after authorization; hash conflict makes zero mutation. Different keys
reuse immutable original account/tenant/outcome. Unique keys survive replay retention expiry. Commit
failure rolls back everything; lost commit response is read/retry, not a durable pending publication.
No new completion database routine is mandated where the existing transaction can enforce this.

### Required Read-Only Storage Interface

Implement `identity.resolve_customer_membership()` (no arguments) on the existing database.
Private result is zero or one row: `account_id uuid`, `tenant_id uuid`, `membership_id uuid`,
`roles text[]`. Require exact transaction-local `app.identity_issuer` + `app.identity_subject`,
active actor/login/account/initial organisation/membership and one initial OWNER workspace.
Absent/inactive/retired returns no row; ambiguity fails invariant, never LIMIT 1/latest. The result
is current per request; no tenant input, persistent cache, proof output or cross-ledger join.

Grant only EXECUTE to each existing BP/CE/PR/WBE/AI DB service identity, not shared BP credentials
or direct identity-table access. SECURITY DEFINER owner must be a separate NOLOGIN, NOSUPERUSER,
NOBYPASSRLS non-table-owner with SELECT only on minimum binding/membership/account/organisation
columns, actor-scoped ENABLE/FORCE RLS, fixed `search_path`, no dynamic SQL/PUBLIC EXECUTE/schema
creation and no membership-write or ledger grants. Policies must not recursively call the same
lookup. Actor-scoped pre-account lookup intentionally works with tenant GUCs empty; it is not an
unrestricted cross-tenant read. JWT validation lives in each trusted receiving service, not in GUCs.

Protected resource transactions set BOTH `app.tenant_id` and `app.current_tenant_id` to the resolved
UUID, never a JWT/browser/BP-header tenant. Preserve restrictive C-026 tenant USING/WITH CHECK,
active actor/membership checks for BP protected data and nonowner/NOBYPASSRLS resource roles.
Overwrite/reset all context transaction-locally across pooled connections. Pre-account minting
must have a bounded write policy/routine, never a global RLS bypass or customer-selected tenant.
Other services retain only their own ledger grants plus this lookup; portable professional and
constitutional ledgers are not converted into BP identity tables.

### Exact Small Request To INST-006

Supply ONLY the physical delta for these records and existing transaction: reuse vs necessary
new tables/columns, uniqueness/FKs, actor/provider concurrency, nonrecursive lookup policies and
function/creation privileges, and additive migration/legacy quarantine. Remove the old publication
requirements from the active migration plan. Do not redesign ledgers/billing, add a service, invoke
a review chain, fabricate historical binding or authorize reset. Data owns this decision; EA does
not claim it has been authored. It is the remaining physical input before activation, not another
architecture option selection or a block on bounded parent implementation under standing authority.

Keep proof and successful associations durable without indefinite raw-token/contact retention;
existing privacy/retention rules apply. Same-actor return is initial scope. Different actor matching
an existing Google key denies unresolved; recovery/retirement mutation remains a future gate.
Initial real-PG check: two stable-fixture identities complete with distinct accounts/tenants/OWNER
memberships; same tenantless tokens enter own sessions; swapped resources and forged tenant context
deny using actual runtime roles. Include account+retry rollback, concurrency and pool reset. No test
or migration was run by this amendment; synthetic proof does not qualify Google or reconstruction.

## Historical Data Authoring Record - Superseded, Not The Active Schema

| Field | Decision |
|---|---|
| Owning office | INST-006 - Data Architect; authoring, not review |
| Authorization | Founder assignment, 2026-09-09: bounded CB-009 D-TENANT repair WITH EDIT AUTHORITY; continuous-session bootstrap and parent implementation authority remain valid |
| Status | AUTHORED - physical Data decision complete; implementation and executable qualification pending |
| Scope | First Google registration, returning entry, verified disposable-Keycloak continuity, and durable tenant isolation mapping; no new service or public API |
| Constitutional obligations | C-005 ledger separation; C-007 append-only evidence; C-026 database enforcement; C-032 office boundaries; C-059 traceability; C-080 Docker validation |
| Gate effect | Supplies the Data authorship decision requested by CB-009 and Identity Boundary 5.4/8.4. Does not close CB-009, Security permissions, runtime isolation, release, real Google qualification, Founder acceptance or merge |

This is the implementable physical translation of [Identity Boundary](../components/identity-boundary.md)
Sections 5.1-5.4, 8.4, 11.1 and 14.1, under the bounded assignment recorded in
[CB-009](../../../blockers/CB-009-wc085-tenant-provisioning-contract-2026-09-09.md).
Security owns trusted broker proof and stock-Keycloak permissions in
[Security Architecture](../security/security-architecture.md). This document does not assert
Security concurrence or authorize a reset. All definitions below are documentation, not an applied migration.

Applicable local guidance: the existing Data-owned Three-Ledger Design and
[Engineering Standards](../engineering-standards.md). Targeted lookup found no compact Data Architect
card in `.github/agent-context` or Data Architect standard in `standards`; no other office is invoked.

## 1. Existing Ownership And Physical Mapping

Observed implementation anchors:

- [IdentityDbContext](../../../src/business-platform/Infrastructure/IdentityDbContext.cs) and
  [migration 20](../../../infrastructure/postgres/init/20-identity-boundary.sql) hold workflow
  registrations, challenges, links and idempotency. A registration's nullable `account_id` is
  currently the only account record. `provider_issuer` is not a stored stable provider subject.
- [Three-Ledger Data Design](../data/ledger-design.md) names `business.organisations` as the
  canonical customer organisation and says tenant identity is organisation identity.
  [migration 03](../../../infrastructure/postgres/init/03-enums-and-tables.sql) physically has
  `id uuid PRIMARY KEY`, `tenant_id uuid NOT NULL UNIQUE`, `name varchar(200) NOT NULL`, optional
  `business_domain varchar(50)` and `created_at timestamptz NOT NULL`. It does not enforce `id = tenant_id`.
- [migration 04](../../../infrastructure/postgres/init/04-rls-policies.sql) uses `app.tenant_id`;
  identity migration 20 uses `app.current_tenant_id`. Both must receive the same validated JWT UUID
  on protected requests, transaction-locally; neither may be left over from a pooled connection.
- [billing migration 12](../../../infrastructure/postgres/init/12-billing-engine.sql) references
  `business.organisations(id)`, including unique `customer_wallets.organisation_id`.
  [acquisition migration 13](../../../infrastructure/postgres/init/13-customer-acquisition.sql)
  separately references `institutional.billing_profiles(customer_id)`. Neither is account truth.

**Decision:** no `identity.tenants`, second organisation table, shared Demo tenant, or tenant from a
registration request. BP generates two distinct random UUIDs: `account_id` and `tenant_id`.
Insert `business.organisations.id = business.organisations.tenant_id = tenant_id`. Persist
`identity.accounts.initial_tenant_id = tenant_id`. The initial account has one active OWNER membership.
Independent proven Google identities get distinct accounts and tenants. Existing phone/GST/reseller/
billing fields remain at their existing defaults; registration grants no commercial entitlement.

`business_domain` from registration is up to 100 characters, while organisation taxonomy is 50.
Preserve the accepted text in the immutable profile snapshot; leave the organisation taxonomy column
NULL unless it is an exact existing permitted taxonomy code. Do not truncate or invent a taxonomy entry.

## 2. Type And Constraint Conventions

The following table definitions specify all new columns. Every listed column is NOT NULL unless
marked `?`. IDs are `uuid`; times are UTC `timestamptz`; BP mints UUIDs, PostgreSQL supplies creation
timestamps. All FKs use `ON DELETE RESTRICT`, with no cascading identity deletion. Cross-record FKs
are `DEFERRABLE INITIALLY DEFERRED` where the initial atomic insert requires it. Text identity keys
use deterministic `COLLATE "C"`, exact comparison, nonempty checks and no case-folding of subjects.
All states have CHECK constraints restricting values to the enumerated values below.

Actor issuer/subject are separate `varchar(256)` columns, never an ambiguous concatenation. Provider
issuer is `varchar(256)`, broker alias `varchar(40)`, upstream subject `varchar(256)`. Reject overlength
proof rather than truncate. The provider issuer is the exact Security-approved configured trust
namespace representing the upstream issuer, not the Keycloak issuer or an invented URL. Namespace
changes cannot recover old bindings. Only configured Google is admitted in this slice.

All new tables reside in `identity` except the existing organisation extension. Do not use email,
HMAC email match keys, display name, registration recency, or a tenantless JWT to infer membership.

## 3. Accounts, Tenants, Membership And Proven Identity

| Table | Columns and constraints |
|---|---|
| `business.organisations` extension | `identity_status varchar(24) DEFAULT 'LEGACY_UNVERIFIED'` CHECK in `LEGACY_UNVERIFIED, ACTIVE, INACTIVE`; `identity_managed boolean DEFAULT false`. CHECK `NOT identity_managed OR id = tenant_id`. WC085 inserts set managed=true, status=ACTIVE. Add UNIQUE `(id, tenant_id)`. Existing nonidentity organisation uses are not silently reclassified. |
| `identity.accounts` | `account_id uuid PK`; `initial_tenant_id uuid UNIQUE` FK to `business.organisations(tenant_id)`; `status varchar(16)` in ACTIVE/INACTIVE; `created_at timestamptz DEFAULT now()`. CHECK account_id differs from initial_tenant_id; UNIQUE `(account_id, initial_tenant_id)`. No raw contact PII. |
| `identity.billing_customer_bindings` | `customer_id uuid PK`; `account_id uuid UNIQUE`; `tenant_id uuid UNIQUE`; `provenance varchar(24)` in NATIVE/VERIFIED_BACKFILL; `correlation_id uuid`; `created_at timestamptz DEFAULT now()`. Composite FK `(account_id, tenant_id)` to accounts; FK tenant_id to organisations(tenant_id). CHECK provenance differs from NATIVE or customer_id=tenant_id. Entire row append-only. New registrations insert customer_id=tenant_id; an existing different customer UUID may be retained only with verified historical ownership. No billing profile, wallet, subscription or trial is created. |
| `identity.memberships` | `membership_id uuid PK`; `account_id uuid`; `tenant_id uuid`; `roles text[]`; `status varchar(16)` in ACTIVE/INACTIVE; `revision bigint DEFAULT 1` CHECK >0; `created_at`, `updated_at timestamptz DEFAULT now()`. UNIQUE `(account_id, tenant_id)` and `(membership_id, account_id, tenant_id)`. Composite FK `(account_id, tenant_id)` to accounts `(account_id, initial_tenant_id)` fixes this journey to the initial organisation. FK tenant_id to organisations(tenant_id). CHECK roles is nonempty, has no NULLs, is a subset of OWNER/MANAGER/VIEWER; write operation canonicalizes distinct sorted values. Initial roles exactly `{OWNER}`. Every role/status change increments revision. |
| `identity.login_methods` | `login_method_id uuid PK`; `provider_issuer varchar(256)`; `broker_alias varchar(40)`; `provider_subject varchar(256)`; `account_id uuid` FK accounts; `status varchar(16)` in ACTIVE/RETIRED; `created_at timestamptz DEFAULT now()`. UNIQUE `(provider_issuer, broker_alias, provider_subject)` across ALL statuses, not a partial active index. UNIQUE `(login_method_id, account_id)`. Retired keys remain reserved to the original account. |
| `identity.actor_bindings` | `actor_binding_id uuid PK`; `actor_issuer varchar(256)`; `actor_subject varchar(256)`; `login_method_id uuid`; `account_id uuid`; `revision bigint` CHECK >0; `status varchar(16)` in ACTIVE/RETIRED; `created_at timestamptz DEFAULT now()`; `retired_at timestamptz?`. UNIQUE `(actor_issuer, actor_subject)` across all history; UNIQUE `(actor_binding_id, account_id, login_method_id)`; FK `(login_method_id, account_id)` to login_methods. Partial UNIQUE `(login_method_id) WHERE status = 'ACTIVE'`. CHECK retired_at is present exactly when RETIRED. Actor key/account/login reference and creation revision never change; retirement is one-way. |
| `identity.broker_proofs` | `proof_id uuid PK`; `login_method_id uuid`; `account_id uuid`; `actor_binding_id uuid`; `verified_at`, `auth_time timestamptz`; `trust_config_digest varchar(64)`; `source varchar(32)` fixed `KEYCLOAK_FEDERATED_IDENTITY`; `correlation_id uuid`; `created_at timestamptz DEFAULT now()`. Composite FKs to login_methods and actor_bindings above; digest is lowercase hex SHA-256 of nonsecret trust configuration. Append-only provenance that the exact server-authenticated actor's configured Google broker record was checked; not a raw token or browser assertion. |

An initial deferred constraint trigger requires every newly managed ACTIVE organisation to have its
account, billing-customer binding, active initial OWNER membership, active login, active actor and
initial proof by commit.
It runs only for initial creation, not later revocation: deactivation must always remain possible.
Immutable-column triggers prohibit retargeting accounts, login keys or memberships. Role/status
changes append evidence in the same transaction; applications have no direct rights to bypass them.
Additional memberships or login-method attachment require their own accepted flow, not this contract.

## 4. Durable Operation, Publication And Retry Records

| Table | Columns and constraints |
|---|---|
| `identity.completion_intents` | `intent_id uuid PK`; `origin_registration_id uuid UNIQUE` FK registrations; `account_id uuid UNIQUE`; `tenant_id uuid UNIQUE`; `membership_id uuid`; `login_method_id uuid UNIQUE`; `original_outcome varchar(24)` in ACCOUNT_CREATED/ACCOUNT_REUSED; `profile_snapshot jsonb` object; `success_body text`; `correlation_id uuid`; `created_at timestamptz DEFAULT now()`. Composite FKs `(account_id, tenant_id)` to accounts, `(membership_id, account_id, tenant_id)` to memberships, `(login_method_id, account_id)` to login_methods. UNIQUE `(intent_id, account_id, tenant_id)` and `(intent_id, account_id, login_method_id)`. Entire row append-only. |
| `identity.publication_revisions` | `intent_id uuid`; `revision bigint` CHECK >0; `actor_binding_id uuid`; `account_id uuid`; `login_method_id uuid`; `proof_id uuid` FK broker_proofs; `membership_revision bigint` CHECK >0; `attributes jsonb` object; `payload_digest varchar(64)` lowercase hex; `created_at timestamptz DEFAULT now()`. PK `(intent_id, revision)`; UNIQUE actor_binding_id within this initial-provisioning slice. Composite FKs to intent/account/login and actor/account/login. Entire row append-only. Deferred validation requires proof to reference this actor/login/account and membership revision to match the committed snapshot. |
| `identity.provisioning_state` | `intent_id uuid PK` FK completion_intents; `desired_revision bigint` CHECK >0; `state varchar(16)` in BP_COMMITTED/PUBLISHED; `acknowledged_revision bigint?`; `next_attempt_at timestamptz?`; `last_error varchar(32)?` in DEPENDENCY_UNAVAILABLE/BINDING_CONFLICT/INELIGIBLE; `updated_at timestamptz DEFAULT now()`. FK `(intent_id, desired_revision)` to publication_revisions; FK `(intent_id, acknowledged_revision)` to publication_acknowledgements. CHECK PUBLISHED implies acknowledged_revision=desired_revision and NOT NULL; BP_COMMITTED has NULL acknowledgement. |
| `identity.publication_acknowledgements` | `intent_id uuid`; `revision bigint`; `payload_digest varchar(64)`; `correlation_id uuid`; `observed_at timestamptz`; `created_at timestamptz DEFAULT now()`. PK `(intent_id, revision)` FK publication_revisions. Append-only; deferred validation checks digest against that revision. Only verified remote read-back can create it. |
| `identity.completion_requests` | `request_id uuid PK`; `actor_issuer varchar(256)`; `actor_subject varchar(256)`; `operation_family varchar(64)` fixed `completeIdentityRegistration`; `idempotency_key varchar(36)` canonical lowercase UUID text; `canonical_hash varchar(64)` lowercase hex SHA-256; `registration_id uuid` FK registrations; `intent_id uuid` FK completion_intents; `created_at timestamptz DEFAULT now()`; `expires_at timestamptz DEFAULT now()+25 hours`. UNIQUE `(actor_issuer, actor_subject, operation_family, idempotency_key)`. Append-only reservation; expires_at >= created_at+24 hours. |
| `identity.completion_results` | `request_id uuid PK` FK completion_requests; `intent_id uuid`; `publication_revision bigint`; `status_code integer` CHECK =200; `response_body text`; `created_at timestamptz DEFAULT now()`. FK `(intent_id, publication_revision)` to publication_acknowledgements. Append-only; deferred check request.intent_id equals result.intent_id and response_body equals intent.success_body byte-for-byte. No pending 503 result row. |
| `identity.provisioning_events` | `event_id uuid PK`; `intent_id uuid` FK completion_intents; `revision bigint` CHECK >0; `actor_binding_id uuid` FK actor_bindings; `event_type varchar(32)` in BP_COMMITTED/PUBLICATION_PENDING/PUBLISHED/ACTOR_RETIRED/ACTOR_BOUND/MEMBERSHIP_CHANGED/ACCESS_REVOKED; `correlation_id uuid`; `occurred_at timestamptz DEFAULT now()`. FK `(intent_id, revision)` to publication_revisions. Append-only; no arbitrary payload, subject, email or credential in events. |

`profile_snapshot` contains only displayName, businessName, businessDomain, languagePreference and
verified-email boolean from the accepted registration, plus optional verified-mobile boolean. No
email address, provider token, broker response or OTP. `success_body` is the serialized existing
IdentityCompletion response fixed at commit, including original outcome and opaque account reference;
it is not readable as successful completion before acknowledgement. Access/assurance is always
rechecked; replayed assurance metadata is never authority. Different request keys preserve the same
logical outcome/body. Return-target permission is revalidated, not embedded as a durable grant.

Publication attributes are exactly `tenant_id`, `waooaw_roles`, `org_name`, with tenant equal to the
intent tenant, initial roles from current membership, and name from the committed businessName.
Any emitted organisation_id must equal tenant_id. No role assignment, credential, billing or broker
mutation is encoded. JSON shape and equality checks are enforced by the restricted write routines.

Extend existing registrations with nullable `actor_issuer varchar(256)`, `intent_id uuid` FK intents,
`actor_binding_id uuid` FK actor_bindings and `legacy_disposition varchar(24)` DEFAULT 'UNVERIFIED'
in UNVERIFIED/NATIVE/VERIFIED_BACKFILL. New rows require actor_issuer and NATIVE; committed rows
require binding and intent and account_id matching that intent. Add composite UNIQUE
`(registration_id, actor_issuer, actor_subject)` and a composite FK from completion_requests.
An append-only association invariant prohibits changing committed account/intent/actor references.
Public registration state remains ReadyToComplete until the current publication is acknowledged.
Add actor_issuer to verification_challenges, registration_events, account_links, idempotency_ledger
and customer_portal_preferences; challenges for post-account use additionally carry nullable
`tenant_id uuid` FK organisations(tenant_id), required when registration_id is NULL. Legacy NULL
issuer rows are denied, not matched by subject alone. Existing actor-only uniqueness on the generic
idempotency ledger is replaced by issuer/subject/key/family uniqueness after legacy quarantine.

Retain `actor_subject` storage as observed for legacy rows; if it encoded issuer and subject together,
do not split it heuristically. New rows store the validated subject alone and the issuer separately.
Add FK account_links.tenant_id and customer_portal_preferences.tenant_id to organisations(tenant_id),
and replace preferences' actor/tenant uniqueness with `(actor_issuer, actor_subject, tenant_id)`.
Deferred validation checks every committed registration actor against actor_bindings and every proof's
actor/account/login against its publication row. It checks no identity-managed active association
points to an unmanaged/legacy organisation. Event actor must equal the referenced revision actor;
ACTOR_RETIRED references the retiring actor's old revision, ACTOR_BOUND the new revision.

State transition triggers permit desired_revision to increase only by one, backed by an inserted
immutable publication revision and retirement/new-binding evidence. They clear the current
acknowledgement on that transition. Otherwise desired_revision cannot change; acknowledgements are
only for that revision. Membership UPDATE must set revision=OLD.revision+1 and append its event in
the same transaction. Existing published evidence remains historical after retirement or revocation.

Completion uses the new reservation/result pair, not a second successful entry in the generic
idempotency_ledger. Other operations retain that ledger. The split preserves append-only evidence
without mutating a stored 503 into 200. Add indexes on each referencing FK and actor issuer/subject,
and `provisioning_state(next_attempt_at) WHERE state='BP_COMMITTED'`; none permits background tenant
enumeration by a customer DB role.

## 5. Exact Transaction And Concurrency Protocol

1. Validate Keycloak session and the Security-approved exact Google broker proof. Acquire proof for
   the authenticated subject only. Canonical hash includes operation, registration ID and semantic
   input, never transport IDs or a browser tenant. Before reservation, reject an inaccessible/expired
   uncommitted registration and validate the full minimum profile, verified email and duplicate state.
2. Begin one PostgreSQL transaction. Acquire transaction advisory locks for the exact actor key and
   stable provider tuple, sorting their signed 64-bit lock numbers globally to avoid lock-order cycles.
   Define each lock number as the first 8 bytes, signed big-endian, of SHA-256 of a UTF-8 JSON array:
   `["wc085-actor", issuer, subject]` or `["wc085-provider", issuer, alias, subject]`, serialized compactly.
   Hash collisions only over-serialize; uniqueness constraints, not hashes, establish identity.
   Then lock the registration and existing login/actor/intent/state/membership rows FOR UPDATE in that
   order. No network call occurs inside this initial BP commit transaction.
3. Check the actor-scoped request key before any mutation. Same key/different hash returns 409 with
   zero writes. Same key/hash resumes its intent only after current access checks. With a different
   key or registration, exact active actor and login must resolve to the same account. Conflicting
   actor/login ownership returns unresolved duplicate state with zero provisioning mutation.
4. If neither binding exists, mint one account/organisation/membership/billing-customer binding and persist login, actor,
   proof, immutable intent/success snapshot, publication revision 1, BP_COMMITTED state, registration
   association, request reservation and required evidence in this SAME transaction. If already bound,
   reuse its single intent and fixed IDs; attach a caller-owned continuation, never create a new tenant.
   A differing concurrent profile cannot overwrite the winner's committed snapshot. Divergent identity
   proof fails unresolved. An inactive account/login/tenant/membership denies rather than reactivates.
5. Commit once. Every DB write/evidence failure rolls the whole unit back; no Keycloak write precedes
   commit. All participating EF contexts must share this exact connection and transaction, not merely
   execute two SaveChanges calls. Data authorizes the narrowly scoped SQL locking, RLS context and
   guarded routine operations defined here under Engineering Standards section 1; no generic raw SQL.
6. Perform publication as section 6. On verified acknowledgement, atomically append acknowledgement,
   PUBLISHED event and request result, update provisioning state and the caller registration to
   Completed, and commit. Any failure leaves a recoverable BP_COMMITTED operation. A later caller-bound
   continuation can be marked Completed and get its own result against an already current acknowledgement.

Deadlock/serialization/unique violations abort the entire transaction before a bounded retry. Reload
the exact actor/provider binding under locks; do not treat a failed insert as permission to mint again.
The shared provider lock plus unique stable key serializes different actors claiming one Google login;
the actor lock serializes differing provider claims for one actor. Database constraints remain the final
defence when requests run in different BP instances. At most one concurrent recreated actor wins:
compare the expected prior active binding and revision; the loser must reauthenticate/reprove against
the current state, not automatically retire the winner using its earlier proof.

## 6. Publication Serialization, Recovery And Revocation

Use a dedicated connection with a session advisory lock in a separate lock namespace for the exact
target actor key. Derive the signed lock number as in section 5 with array tag `wc085-publication`.
All publishers use that lock, including completion retry; no automatic lease-expiry takeover. Reload
the desired revision, active actor, account/managed organisation, login and current membership before
the stock read/write/read-back. Revalidate the exact target's current Google broker binding through
Security's approved read; a changed/missing/ambiguous binding cannot be published from stale proof.
Network attempts are bounded; failure keeps BP_COMMITTED and returns
503 with retryAfterSeconds. GET never publishes. No worker service or scheduler is introduced.

After read-back, lock provisioning state, actor and membership in a short transaction and require
the same desired revision, actor, membership revision, active status and exact payload before appending
acknowledgement/result. A stale writer cannot acknowledge, change desired revision, mark Completed or
return a previously stored success without current authorization. An acknowledgement timeout is
recovered by remote read-back of the identical payload, not another account or blind compensation.

**Remote fencing limit:** a PostgreSQL lease/fencing counter cannot fence stock Keycloak PUT. A timed-out
HTTP request may still finish after the DB connection dies. Therefore each actor_binding_id has exactly
one immutable initial publication payload in WC085. Retrying that target can only resend identical
values. Revision increments for recreated-actor continuity target a DIFFERENT nonrecycled actor key;
old revisions cannot overwrite the new actor's attributes. Old actor sessions are denied by DB status,
even if an in-flight write reaches that retired Keycloak user. Do not reuse issuer/subject IDs for a
new Keycloak fixture generation. If the provider cannot uphold this, continuity remains unresolved.

Name edits, role changes or account reassignment cannot create a competing publication payload for
the same actor in this slice. Membership revocation is immediate DB authorization denial, regardless
of remote claims; it is never delayed for publication. Membership changes during pending publication
make that snapshot ineligible and prevent acknowledgement; no stale snapshot is silently rebased.
General mutable attribute synchronization would need remote conditional-write/serialization semantics
outside this initial Google journey. Do not claim lease-only fencing solves it.

Recreated Demo Keycloak continuity requires Security's fresh (at most five-minute auth age) validated
session plus current exact broker proof, and an existing historical proven login key. In one locked
transaction retire the old actor, append retirement evidence, create the new active actor and proof,
increment intent publication revision, append its immutable publication row, set BP_COMMITTED and
attach a NEW actor-owned registration/request. Preserve account/tenant/membership IDs and original
outcome. Reject old actor registrations, challenges, keys and successes. No old request keys are
transferred. Keycloak permission/proof failure leaves the operation unresolved, not reset or merged.

## 7. RLS And Privilege Contract

Enable AND FORCE RLS on every new table and on touched identity workflow tables and organisations.
Runtime principals are neither owners, superusers nor BYPASSRLS, cannot SET ROLE to a writer/owner,
and cannot create in any involved schema. Revoke PUBLIC table, sequence and routine privileges and
unsafe default privileges. Migration owner is separate from all runtime principals.
Grant schema USAGE on identity/business only to the principals requiring listed objects. UUID keys
need no sequences; do not add global sequence or schema CREATE grants. Grant identity_writer no
membership to BP or other service roles. Constraint-trigger execution uses the guarded owner context
with the same private-row scope, never a table owner that silently defeats FORCE RLS.

Use three privilege boundaries within the existing BP database, not new services:

| Principal | Exact permitted surface |
|---|---|
| Existing BP runtime login (`business_app` where deployed) | SELECT on actor-scoped registrations/challenges/generic idempotency and current actor binding; tenant-authorized SELECT on accounts, memberships, organisations and existing tenant resources. EXECUTE only on explicitly granted guarded identity routines below. No direct INSERT/UPDATE/DELETE/TRUNCATE on provisioning or evidence tables, no direct organisation INSERT for this journey; no unrestricted identity/admin role membership. Audit/revoke inherited broad grants as well as direct grants. |
| `identity_writer` NOLOGIN, NOSUPERUSER, NOBYPASSRLS, nonowner | Owns SECURITY DEFINER routines, not tables. SELECT/INSERT on the contract tables; column-scoped UPDATE only for allowed workflow transitions, one-way retirement, membership role/status/revision, organisation identity status and provisioning_state. No UPDATE/DELETE/TRUNCATE on billing_customer_bindings, intent, proof, publication, acknowledgement, request/result or event tables; no account/key/tenant retargeting. No privileges on ledgers, billing product tables, job, file or AI tables. |
| Migration/retention authority | Separate nonruntime execution identity. Applies constraints, backfill and approved retention only; never used by a web request or publication retry. No ordinary expiry job receives append-only evidence DELETE. |

Guarded DB routine contract (implemented in the existing database): `identity.commit_completion`,
`identity.bind_recreated_actor`, `identity.acknowledge_publication`, `identity.record_publication_failure`
and the existing workflow write equivalents. Parameters carry registration/request IDs, hashes and
server-verified proof/profile facts, never caller-selected account/tenant or arbitrary SQL/attributes.
These routines enforce sections 3-6 and generate/resolve account/tenant internally. No routine returns
tenant resource data to a pre-account caller. Publisher loads committed attributes through
`identity.read_publication(intent_id, expected_revision)` restricted to the authenticated current actor;
execution without actor context is denied. Customer-driven recovery suffices here.

Routine interfaces use the following exact database types. `proof` below is the composite type
`identity.verified_broker_input` with fields `provider_issuer varchar(256)`, `broker_alias varchar(40)`,
`provider_subject varchar(256)`, `verified_at timestamptz`, `auth_time timestamptz`,
`trust_config_digest varchar(64)`, `email_verified boolean`. It is a trusted BP adapter input, not an
OpenAPI type or a database-authenticated token. Issuer/subject always come from validated actor context.

| Routine | Inputs | Private result |
|---|---|---|
| commit_completion | registration_id uuid, idempotency_key varchar(36), canonical_hash varchar(64), proof identity.verified_broker_input, correlation_id uuid | request_id uuid, intent_id uuid, desired_revision bigint, state varchar(16), authorized terminal status integer?/body text?; profile loaded from locked registration, no arbitrary success-body argument |
| bind_recreated_actor | registration_id uuid, expected_old_actor_binding_id uuid, expected_revision bigint, proof identity.verified_broker_input, correlation_id uuid | intent_id uuid, desired_revision bigint; actor-owned continuation only; completion key reserved by subsequent commit_completion |
| read_publication | intent_id uuid, expected_revision bigint | exact active actor issuer/subject, attributes jsonb, payload_digest varchar(64), membership_revision bigint; no other caller's data |
| acknowledge_publication | request_id uuid, expected_revision bigint, observed_payload_digest varchar(64), observed_at timestamptz, correlation_id uuid | status integer=200, body text; request resolves intent, digest must equal the stored expected payload and the adapter's verified read-back |
| record_publication_failure | intent_id uuid, expected_revision bigint, error_code varchar(32), next_attempt_at timestamptz, correlation_id uuid | no payload; guarded pending-state update and evidence only |

The public response never contains these private IDs/attributes. The commit routine constructs the
existing response using the fixed accepted default target and stored profile, not caller-supplied JSON.
Recovery proof must be fresh at lock acquisition, and expected old actor/revision must still match.
Existing authorized membership/status commands must use guarded revision/evidence writes; these
provisioning routines do not grant customers a role-edit API.

Each SECURITY DEFINER routine has fixed `search_path = pg_catalog, identity, business`, fully qualified
objects, no dynamic SQL, no PUBLIC EXECUTE, no untrusted schema creation and no external input used as
a GUC tenant. Data grants only the listed routines to BP. The writer's RLS uses the private transaction
context described below; being SECURITY DEFINER does NOT disable RLS.

RLS predicates, with identical USING and WITH CHECK where writes exist:

- Actor context is `app.identity_issuer` and `app.identity_subject`, populated by BP exclusively from
  the validated token using parameterized transaction-local set_config. Missing/empty context denies.
  Registration/challenge/event/idempotency rows require both exact actor columns; retired actor keys
  deny. Pre-account challenges must additionally match their registration. Post-account challenges,
  links and preferences require actor AND tenant predicates and an active membership.
- An active actor may SELECT only its own actor binding; no direct grants expose login_methods,
  proofs, intents, publication payloads, requests/results or events as a cross-tenant search surface.
  Guarded replay routines return only the current actor's authorized response. Global provider-key
  resolution is private to commit/recovery routines after authenticated broker proof, never an email
  lookup or an API accepting arbitrary provider subjects.
- Protected tenant context requires BOTH `NULLIF(current_setting('app.tenant_id', true),'')::uuid`
  and the equivalent `app.current_tenant_id` to equal the row tenant. Missing/unequal values deny;
  malformed UUID aborts before data access. Organisation id and tenant_id must both equal the claim
  for identity-managed customers. Accounts use initial_tenant_id; memberships and tenant resources
  use their physical tenant discriminator. Existing permissive policies must be replaced or bounded
  by a restrictive policy; adding another permissive policy is not an AND restriction.
- BP's protected query also requires the exact active actor -> ACTIVE account -> ACTIVE managed
  organisation -> ACTIVE membership chain, membership tenant equal to the JWT tenant and roles valid
  for the requested resource. A narrow writer-owned boolean routine
  `identity.has_current_membership(claim_tenant uuid)` enforces the same chain for runtime RLS without
  recursive membership policies. It returns false unless argument equals both JWT-context settings;
  it returns no account/tenant identifiers. Its internal SELECT policies constrain actor and supplied
  claim tenant and do not recursively invoke that helper. Runtime policy uses this helper even for
  account/membership reads; no membership query derives a replacement tenant.
- Writer policies on binding/control tables permit only the exact actor/provider keys selected by a
  guarded routine; on tenant tables permit only internally resolved `app.identity_write_tenant` and
  `app.identity_write_account`. These private settings are transaction-local and reset after the
  routine. They are overwritten from locked verified data or newly minted IDs, never read as authority
  from runtime input. Runtime has no policy for this writer context and cannot assume identity_writer.
  Routine entry sets private context before queries and clears it on exit; failure rolls back.
- Deferred constraint triggers run at commit after routine exit. Their guarded trigger functions
  derive the minimum validation context from the triggering NEW/OLD keys, save/restore any prior
  private settings, and validate only those referenced rows. They do not depend on cleared routine
  context or obtain global RLS access. They cannot be invoked as customer-callable validation routines.
- RLS does not authenticate a bearer token or a client-set GUC. BP is the trusted DB client and must
  validate JWTs before setting context. Pre-account routines are narrowly scoped mint/recovery
  authority, not permission to set `app.tenant_id` from a lookup and execute tenant business queries.

Each request opens an explicit transaction, overwrites all actor/tenant settings (empty tenant on
pre-account paths), performs authorization and queries, then commits/rolls back. Transaction-local
settings and dedicated publication connections must not leak through pooling. Never use connection-
session SET for request authorization. A signed tenant claim remains mandatory on every protected
request; membership is current resource authorization, not a tenantless-session upgrade mechanism.

## 8. Billing And Full Isolation Mapping

The durable join is account.account_id -> account.initial_tenant_id -> organisations.tenant_id,
with organisations.id equal to that tenant UUID for managed customers. Billing wallet/invoice/payment
organisation references therefore use this organisation UUID, NOT account_id, Keycloak sub or an email.
For customer_id-based records, resolve `identity.billing_customer_bindings.customer_id` within the
JWT-selected tenant, require its account to equal the authenticated account, and then use the recorded
customer UUID. New customer_id equals organisation/tenant ID, not account_id. Existing distinct billing
customer IDs require the VERIFIED_BACKFILL mapping, never an email join. This table uses tenant RLS
and current membership like accounts; no actor-only read or arbitrary reverse-lookup API is granted.
`wbe_app` may SELECT the binding through the same trusted tenant/current-account context only for an
enabled authenticated billing path; it has no INSERT/UPDATE/DELETE permission. BP performs no billing
profile projection during registration. A narrowly authenticated billing service flow must carry
current account/tenant provenance, not select a customer row and manufacture that context.

**Observed architectural conflict:** migration 12 defines `institutional.billing_profiles` as an
agent catalogue (`agent_type varchar(50) PRIMARY KEY`), without customer_id. Migration 13 declares
trial/referral FKs to `institutional.billing_profiles(customer_id)`. That target does not exist in
these definitions. This contract does not invent a customer column on the institutional agent
catalogue or claim those FKs work. The explicit binding above resolves identity/customer ownership;
affected acquisition schema must be reconciled before enabling those features. This is not a reason
to block Google account/tenant provisioning or implement trial/billing projections in WC085.

All tenant-scoped resource rows and parent-child FKs must bind the same organisation/tenant; child
IDs alone cannot cross it. Internal calls/jobs/callbacks carry trusted originating tenant and resource
provenance, then recheck current access before effects. The same obligation applies to billing,
relationships/agents, files/conversations/retrieval/cache keys, AI context, jobs and all three ledgers.
Do not broaden the portable professional ledger into tenant-owned data or join ledgers to infer identity.
Enabled surfaces require actual two-customer denial tests; disabled families must be unreachable via
UI, direct API and background paths and labelled DEFERRED/DISABLED, not PASS. No projection feature
or employment/subscription/wallet creation is required by this identity commit.

## 9. Additive Migration And Conservative Legacy Disposition

Apply a new forward migration; never rewrite applied migration 20 or drop historical account UUIDs.
Sequence: inventory constraints/legacy rows under migration authority; create tables/roles/routines
and deny-by-default policies; add nullable workflow provenance columns; deploy gated new writers;
validate FKs/uniqueness/checks; enable the qualified path only after exact-image tests. Existing writer
images that create account-only completions must be fenced off before activation; rollback may
disable the journey but must not restore those writers or a shared mapper against qualified data.

Keep unproven account-only Completed registrations and existing replay rows as quarantined history:
`legacy_disposition=UNVERIFIED`, NULL intent/binding, no new membership and no successful new replay.
Do not fabricate provider_subject from ActorSubject, infer issuer from deployment defaults, or invent
tenant ownership from AccountId. Legacy account_id remains historical, not an FK to a fabricated
active account. New rows have a conditional checked association to accounts through their intent.
Expired old actor-only keys cannot revive a legacy completion.

Backfill may retain an account UUID ONLY when retained evidence proves that exact historical account
belongs to the exact stable provider tuple and a newly authenticated actor proves that same tuple
through the Security-approved broker path. Existing organisation linkage additionally requires
verified provenance and `id=tenant_id`; do not rewrite unrelated organisation IDs to force equality.
If the account genuinely never had a tenant and ownership is proven, mint one canonical organisation
once and atomically create the full binding/intent with ACCOUNT_REUSED. Conflicting accounts, shared
legacy tenants, missing proof or unknown dependent data remain UNVERIFIED and inaccessible pending
case-specific ownership resolution. A fresh proof plus email equality alone is insufficient.

An additive migration must not bulk mark old organisations ACTIVE or add an unvalidated global
id=tenant_id constraint. Only managed rows receive that equality constraint. No delete/reset is
selected or authorized: verified disposable-Keycloak relink is the normal retained-data path.

## 10. Retention And Required Parent Validation

Intents, binding keys, proofs, publication revisions/acknowledgements and provisioning events are
durable append-only or one-way-retirement records, independent of two-hour registration expiry and
25-hour request retention. Committed registration associations cannot be deleted by abandoned-draft
cleanup; FK RESTRICT makes this explicit. Runtime roles cannot update/delete/truncate append-only
records; DB triggers reject attempted mutation as well as privileges denying it. Historical state
changes are separate events, not edits to proof. Never log provider subjects, tenant IDs or snapshots.

Keep completion requests/results at least 25 hours and while publication is pending; ordinary
runtime cleanup cannot delete them. A separately authorized retention job may purge expired terminal
request/result pairs only together, preserving durable intent/binding/acknowledgement/evidence. Intent
uniqueness survives such purges. Profile snapshots and pseudonymous proof are restricted personal
data, not public logs; account-erasure/legal-retention handling must preserve required nonreassignable
keys and evidence under existing retention policy, not invent a new indefinite raw-PII archive.

Parent must run Docker-only checks against migrated PostgreSQL and actual restricted application
roles, identifying schema/image/fixture generation:

1. Account + retry atomicity regression, plus fault injection at organisation, membership, proof,
   intent, request and evidence writes: complete rollback and zero precommit Keycloak calls.
2. Concurrent same actor/provider with same/different registrations and keys: one account, one tenant,
   one membership, one intent; same-key hash conflict makes no mutation. Race recreated actors and
   differing provider claims; exactly one legitimate binding wins without evidence loss.
3. Outage/timeout before and after remote write/read-back/acknowledgement; fixed IDs/body, pending
   503 not cached as terminal, same-key recovery and expiry continuation. Stale actor/revision cannot
   acknowledge or overwrite a new actor target; membership removal blocks replay immediately.
4. Actual app-role RLS/privilege tests for missing/wrong/unequal tenant contexts, swapped IDs, foreign
   actor/provider probes, direct writes, SECURITY DEFINER abuse, append-only mutation and pooled
   connection reuse, including pre-account -> post-account -> different-customer transitions.
5. Verified Google same-subject/changed-email and recreated-actor continuity retain IDs; same-email/
   different-subject and legacy account-only/no-proof fixtures fail closed with no automatic relink.
6. Renewed signed JWT/session checks and every enabled downstream family's two-customer denial;
   legacy billing/customer references cannot bypass the durable mapping. Deferred features are denied.

Documentation checks are not those runtime proofs. The Data authoring gate is supplied by this
contract; Security's exact stock-Keycloak privilege boundary remains independently owned. No general
review or additional office invocation is requested. Parent combines this decision and executable
evidence without treating this file as Founder merge approval or platform readiness.
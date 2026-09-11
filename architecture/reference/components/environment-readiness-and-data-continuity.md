# Environment Readiness And Data Continuity Component

**Work Contract:** WC-091
**Owner:** Solution Architect (INST-005)
**Status:** OWNER-REVIEWED - CONDITIONAL PASS - EA AMENDMENT APPROVED - FOUNDER ACCEPTANCE BLOCKS I1 - IMPLEMENTATION UNAUTHORIZED
**Scope:** Runtime configuration, secret dependencies, identity match-key continuity, environment
data posture, deployment preflight, and independent readiness evidence

## 1. Component Responsibility

The Environment Readiness And Data Continuity component is a deployment-time contract spanning the
existing Business Platform, Keycloak, environment configuration, Key Vault, PostgreSQL, migration
job, deployment workflow, and independent verifier. It is not a seventh application service.

It owns these decisions:

1. the non-secret configuration schema for each environment;
2. the secret dependency catalog and its consumer bindings;
3. the identity match-key version and rotation contract;
4. the declared data durability posture of each environment;
5. preflight gates before mutation and traffic;
6. distinct configuration, provider, recovery, and acceptance evidence.

It does not own provider credentials, customer identity, constitutional evidence, database business
schemas, cloud authorization, or Production acceptance.

## 2. Architectural Invariants

- One reviewed environment manifest is the source of all non-secret public origins, issuer, callback,
  cookie, channel, and provider-enable configuration.
- One schema-versioned, machine-readable secret catalog is the closed-world source of required secret
  names, purpose, owner, generation mode, principal, consuming service, Key Vault reference, allowed
  operations, rotation class, and environment applicability. Undeclared secret dependencies fail.
- Secret values never appear in a manifest, plan, state, workflow input/output, log, artifact, or
  command argument.
- Every workload receives only its own secret references through its own managed identity and exact
  secret-level authorization.
- Missing or malformed required configuration keeps the affected revision unready before traffic.
- Database posture is explicit: Demo is disposable; UAT is persistent and recovery-qualified;
  Production is persistent, independently isolated, and activation-gated.
- Readiness evidence never upgrades configuration presence into provider or human acceptance.

## 3. Environment Contract

| Property | Demo - WC091-I1 | UAT - WC091-I2 | Dark Production - WC091-I3 |
|---|---|---|---|
| Data | Synthetic only; disposable database; reset on restart or revision replacement | Isolated persistent PostgreSQL | Isolated persistent PostgreSQL |
| Durability claim | None | Backup, PITR, isolated restore, restart continuity | Plan-only target: HA, PITR, RPO/RTO, rollback |
| Migration | Recreate/seed from approved synthetic fixtures | Expand-only, digest-pinned, before traffic | Same qualified migration contract as UAT |
| Temporal | Self-hosted Demo dependency may be disposable | Temporal Cloud under ADR-015 | Temporal Cloud under ADR-015 |
| Manifest | `demo.json`, schema-validated and runtime-consumed | `uat.json`, same renderer and validator | `prod.json`, same renderer and validator |
| Traffic | Founder/tester only under current Demo authority | Approved testers only | None until separate activation authority |
| Promotion | May restore Demo independently; no durability inference | Same immutable application digests after Demo acceptance | Same qualified tuple after separate authorization |
| Recovery proof | Deterministic reset and reseed | Backup, PITR, isolated restore and prior-revision compatibility | Plan-only gates reuse UAT evidence and define separately authorized Production proof |

The Demo row is a Founder-directed bounded variance from the previously accepted reference topology.
Enterprise Architecture amended `architecture/reference/pipeline/azure-deployment-topology.md` on
2026-09-11 to name this exact disposable ACA design and its no-durability consequences and recorded
EA approval. The Founder must still accept that exact amendment before WC091-I1 implementation.
Until Founder acceptance is recorded, the variance is not effective and I1 remains implementation-
blocked. This component does not authorize implementation, cloud mutation, or acceptance.

## 4. Environment Manifest

Each manifest contains only reviewed non-secret configuration:

- schema version and environment identity;
- public web, API, and identity origins;
- issuer, audience, JWKS URI, realm, token/session limits, and clock skew;
- exact client redirect, post-logout, and allowed-origin values;
- channels, cookie policy, identity-edge image and route policy;
- provider alias, scopes, enabled state, and non-secret readiness reference.

The renderer rejects unknown fields, environment mismatches, non-HTTPS cloud origins, origin/callback
inconsistency, enabled providers without catalog dependencies, duplicate aliases, and references to
another environment. Terraform and verification consume the same canonical rendered output and
record its digest.

Rendering is one deterministic operation over the environment manifest, secret catalog, signed
identity dependency manifest, and selected release tuple. The identity environment projection digest
is bound into the signed dependency manifest; the rendered output records the manifest schema/version,
catalog schema/version and digest, dependency-manifest digest, source commit, target environment, and
release digest. Preflight, Terraform, ACA revision configuration, startup checks, and the independent
verifier consume that same output. A consumer-specific hand-written mapping, stale catalog version,
unsigned dependency projection, unknown binding, or digest disagreement stops before mutation.

URLs are configuration, not secrets. Operators change them through reviewed manifest edits. External
provider consoles must contain the exact rendered callback before that provider can become ready.

## 5. Secret Dependency Catalog

The repository contains exactly one catalog artifact with a schema version and canonical digest. Its
environment applicability fields produce Demo, UAT, and Production projections; separate manually
maintained inventories are prohibited. Schema validation rejects unknown fields, duplicate logical
IDs or vault names in an environment, undeclared consumers, principals or operations, and a required
runtime secret with no catalog entry. Render, preflight, provisioning, RBAC generation, startup, and
verification consume the same canonical catalog digest.

Each catalog entry has this shape:

| Field | Meaning |
|---|---|
| `id` | Stable logical dependency identifier |
| `vaultSecretName` | Environment-local Key Vault secret name |
| `purpose` | One security purpose; no credential sharing across principals |
| `source` | `platform-generated`, `external-operator`, or `external-managed` |
| `consumers` | Exact service and environment-variable/secret-reference bindings |
| `environments` | Explicit Demo/UAT/Production applicability |
| `requiredWhen` | Deterministic condition, such as provider enabled |
| `rotationClass` | Rotation cadence, overlap, expiry, and emergency action |
| `validation` | Metadata checks only: existence, enabled state, expiry, and minimum form |
| `owner` | Accountable secret lifecycle owner |
| `principal` | One workload, bootstrap, provisioning, migration, verification, or operator principal |
| `allowedOperations` | Exact Key Vault data-plane operations required by that principal |
| `compromiseAction` | Disable/revoke, readiness hold, rotation, requalification, and evidence response |

The catalog must include separate entries for identity HMAC keys, Keycloak administration, each OIDC
client, Demo founder bootstrap, each provider client ID/secret, service authentication, database
dependency credentials where approved, and Temporal Cloud material where applicable. One value may
not serve Keycloak administration, OIDC client authentication, and founder bootstrap.

### 5.1 Provisioning

- `platform-generated`: an idempotent private seeder creates only absent material using a
  cryptographically secure generator, preserves existing versions, applies lifecycle metadata, and
  emits only secret name/version identifiers.
- `external-operator`: one bounded no-echo operator command writes standard input directly to the
  selected environment Key Vault. The value is never a command argument or intermediate file.
- `external-managed`: preflight validates the approved external reference and workload access without
  importing plaintext into deployment automation.

The no-echo operator path reads the value only from an echo-disabled interactive standard-input
stream inside the approved private provisioning boundary and writes it directly to Key Vault. It
must reject command arguments, environment variables, workflow inputs/outputs, shell tracing,
intermediate files, Terraform values/state, and retained plaintext. Success and failure output is
limited to logical ID, vault name, version identifier, and redacted status.

Provisioning, deployment, migration, application, and independent-verification identities are
separate principals. Catalog generation produces exact Key Vault references and least-privilege
role assignments; deployment authority alone grants no secret read, provisioning authority grants
only create/set and metadata operations for its declared entries, and a workload may get only the
versions referenced by its own bindings. Cross-environment and undeclared-secret access is denied
and tested.

## 6. Identity HMAC Key Ring

Identity match keys use a versioned key ring, not one unversioned shared key.

- Each key has a stable version identifier, lifecycle state, creation time, and retirement boundary.
- Exactly one version is `ACTIVE_WRITE`; bounded prior versions may be `READ_ONLY`.
- Email and mobile use separate keys or cryptographic domain separation with fixed labels. OTP or
  continuity signing must not reuse the match-key domain.
- Key bytes are environment-local Key Vault secret versions. PostgreSQL stores only key version,
  fixed domain, normalized-input algorithm version, match digest, lifecycle timestamps, and the
  identity-record association; it never stores key bytes or raw normalized contact values.
- Stored match-key records carry key version and domain in a uniqueness constraint that prevents one
  digest from ambiguously selecting multiple active identities within that domain/version.
- Lookup computes the active version first and retained read versions only within the bounded rotation
  window; ambiguous matches fail closed.
- Rotation first adds a new active-write version, then performs an idempotent migration/reindex with
  per-version counts, uniqueness/collision checks, resumable checkpoints, and old/new lookup parity,
  then retires the prior version only after continuity evidence passes. Retirement removes the old
  read path only after every retained record is migrated or explicitly quarantined.
- Emergency compromise disables the affected version and new identity writes, places lookup/link/
  merge operations that depend on it in a security hold, and requires a recorded recovery decision.
  Recovery uses a fresh version and the same collision/parity gates; it never treats email equality
  as proof, silently creates an unrelated identity, or auto-merges accounts.

The anonymous provider projection does not consume the HMAC key ring. Registration, verification,
linking, and identity lookup remain fail-closed when their required cryptographic configuration is
missing or invalid.

## 7. Runtime Dependency Isolation

Controllers and route handlers depend only on services used by that operation. In particular, the
anonymous identity-provider discovery/projection read path must not fail because the enclosing
controller eagerly constructs an unrelated registration, linking, lookup, or mutation service.
This separation does not make mutation crypto optional: identity mutation routes must validate their
full dependency set at startup/readiness and return no successful response without it.

Readiness has two layers:

1. process readiness proves the service can construct every enabled route dependency;
2. feature readiness reports each optional provider or channel independently.

A service is not traffic-ready when a mandatory route dependency is invalid. An optional provider is
truthfully unavailable without making unrelated public reads fail.

## 8. Data And Migration Contract

### 8.1 Demo Disposable Data

Subject to the Section 3 amendment gate, Demo uses a digest-pinned PostgreSQL container in ACA with
replica-scoped ephemeral `EmptyDir` storage only: no Azure Files, managed disk, Flexible Server,
backup, export, replica-external database endpoint, or retained database volume. The database is a
pinned dependency, not a seventh first-party release member. A deployment/revision replacement and
every database process start run a generation-fenced destructive initialize-and-seed operation
before traffic; application readiness requires the current generation ID and fixture digest. This
explicit startup reset closes the platform ambiguity that an ephemeral volume can survive a
container-only restart within one replica.

The approved synthetic fixture generation is one dependency set spanning application, Keycloak,
and self-hosted Temporal state. Partial preservation is prohibited: a reset failure or generation
mismatch keeps all affected routes at zero traffic. Verification proves two consecutive restart/
replacement cycles yield only the expected fixture IDs/counts and no prior generation is reachable.
The UI, API, evidence, and operator output must label Demo disposable and must not imply backup,
continuity, customer retention, or recovery. No real customer, irreplaceable acceptance data, or
constitutional evidence requiring retention enters this database.

### 8.2 UAT Persistent PostgreSQL

UAT introduces one isolated PostgreSQL boundary with separate databases and least-privilege roles for
application state, Keycloak, and approved dependencies. The implementation follows the accepted
Entra-first database bootstrap, Key Vault handoff, private networking, and additive migration rules.
It removes local PostgreSQL sidecars and proves:

- restart and revision continuity;
- schema migration before traffic;
- previous-release read compatibility and traffic-switch rollback;
- automated backup and point-in-time restore to an isolated target;
- restored record counts, tenant/RLS controls, and application smoke behavior;
- no Demo or Production identity, route, state, secret, or data access.

The role and ownership floor is:

| Principal | Required database authority | Prohibited authority |
|---|---|---|
| Entra bootstrap administrator | Create the environment databases, NOLOGIN owners, extensions, and bounded grants; hand off and stop | Application traffic, routine migration, or standing secret read |
| Digest-pinned EF migration job | DDL only in its owned application/constitutional schemas and migration history; additive migrations before traffic | Login reuse by workloads, database administration, destructive audit-ledger changes, or cross-database access |
| Application service roles | Separate LOGIN/NOBYPASSRLS roles with only required schema usage, DML, and exact ADR-003 function execution | Ownership, role creation, schema creation, BYPASSRLS, another service database, Keycloak, or Temporal |
| Keycloak and Temporal | Separate generated non-admin roles limited to their separate databases; direct PostgreSQL only where accepted | Application/constitutional schemas, shared credentials, or cross-environment access |
| Recovery verifier | Temporary isolated-restore connection with read/test grants needed for the approved checks | Source mutation, Production access, standing application use, or credential reuse |

The migration is a digest-pinned one-shot pre-traffic job using the accepted EF Core migration
artifacts under ADR-011. It acquires one environment migration lock, records before/after schema
watermarks and migration digest, and permits only expand/contract changes whose expand phase remains
readable by the immediately previous qualified release. Failure leaves the new revision at zero
traffic and does not run a destructive down-migration.

PITR qualification restores the selected point to a new isolated UAT restore server/database with
separate DNS and temporary verifier authority. It proves the restore point and recovery duration,
schema watermark, fixture/record counts, tenant and FORCE-RLS denial behavior, application smoke
behavior, and no route or credential to the source, Demo, or Production. The source is never mutated
to prove restore. Failed or incomplete proof blocks I2 and I3; cleanup of the restore target occurs
only after evidence retention is complete.

### 8.3 Dark Production

Production reuses the UAT-proven contract as its target, but WC091-I3 is limited to deterministic
offline rendering and plan-only gate specifications for sizing, HA, backup retention, RPO/RTO,
restore drill, monitoring, incident response, isolation, and cost. It does not create protected
GitHub environments, OIDC bindings, runners, state, Key Vault, DNS, PostgreSQL, or any other
Production resource, and it does not execute an apply, recovery drill, provider check, or traffic.
Those actions and Production acceptance require separate Founder authorization outside WC-091.

## 9. Deployment Gates

| Gate | Required proof | Failure behavior |
|---|---|---|
| Contract | Manifest and secret catalog validate; environment is permitted for requested execution | Stop before authentication or mutation |
| Secret metadata | Every conditionally required secret exists, is enabled, unexpired, and authorized to the exact consumer | Keep affected revision/provider unready; never print value |
| Render | Terraform/runtime/verifier inputs share one manifest digest and catalog version | Stop on drift or unknown binding |
| Data | Declared environment data posture and migration/reseed mechanism match the iteration | Stop before traffic |
| Identity | HMAC active/read versions and domains are valid for enabled mutation paths | Keep mutation routes unready |
| Provider configuration | Exact broker alias, scopes, callbacks, and enabled state agree | Mark only that provider unavailable |
| Recovery | Iteration-required reset, rollback, PITR, or restore evidence passes | Block promotion |
| Verification | Independent identity and evidence source verifies deployed revision/configuration tuple | Block traffic and acceptance |

Before authentication or cloud mutation, preflight also proves the requested iteration is authorized,
the Demo topology amendment is accepted when I1 is requested, the source commit is trusted, the
release/dependency/configuration/catalog digests are immutable and mutually bound, the exact GitHub
environment/OIDC subject and Azure subscription/resource group match, the private runner is qualified,
the plan contains no foreign-environment reference, and the cost/lease/rollback inputs are current.
Any unknown, stale, unavailable, or additional input is a hard failure, never a warning.

Under WC-091, every Production `apply`, control-plane creation or mutation, recovery execution, DNS
change, and traffic action is rejected unconditionally. I3 may run only after its own separate Founder
authorization and may emit only deterministic offline render results, expected-state control-plane
manifests, and plan-only gate results. Those gates must specify protected Production deployment,
verification, and acceptance environments; exact OIDC subjects; zero-capacity runners; isolated
state, Key Vault, network, DNS, PostgreSQL, and evidence boundaries; UAT-qualified recovery and
rollback for the exact tuple; cost limits; and cross-environment denial. A manifest flag, branch,
issue, Work Contract, environment name, prior acceptance, or successful plan cannot authorize any
mutation, provider claim, recovery execution, traffic, or acceptance.

## 10. Verification Model

Under C-080, all executable validation uses repository-defined Docker images and containers. Host
Python, `pip`, `pytest`, virtual environments/`venv`, and host dependency installation are prohibited;
documentation-only checks that need no runtime may use standard read-only shell and Git tools.

Verification records independent outcomes:

1. `CONFIGURATION_READY`: rendered values, secret metadata, RBAC, dependency construction, and
   deployed revision agree.
2. `PROVIDER_REDIRECT_READY`: the broker emits the expected provider redirect with exact callback,
   client identifier class, scopes, PKCE/state/nonce, and no secret disclosure.
3. `PROVIDER_LOGIN_ACCEPTED`: a separately authorized human completes login, registration,
   cancellation, repeat login, sign-out, and defined failure paths.
4. `DATA_CONTINUITY_READY`: the iteration-specific reset/reseed or persistence/recovery checks pass.

No outcome implies another. Missing evidence is `NOT_PROVEN`, never success.

## 11. Implementation Decomposition

| Order | Slice | Primary owner | Earliest iteration |
|---|---|---|---|
| 1 | Manifest schema, catalog schema, validators, and rendered contract tests | Platform IT Expert | I1 |
| 2 | Provider read-path dependency isolation and startup/readiness checks | Platform IT Expert | I1 |
| 3 | Versioned domain-separated HMAC key ring and migration-safe storage contract | Platform IT Expert under Data/Security acceptance | I1 |
| 4 | Idempotent private secret seeder and no-echo external-secret command | Platform IT Expert under Security acceptance | I1 |
| 5 | Demo disposable database, synthetic seed, reset evidence, and truthful UI/operator state | Platform IT Expert | I1 |
| 6 | Split verifier outcomes and run assembled-container/rendered-plan tests | Platform IT Expert with independent verification | I1 |
| 7 | UAT PostgreSQL, roles, private connectivity, migrations, rollback, backup/PITR and restore proof | Platform IT Expert under Data/Platform acceptance | I2 |
| 8 | UAT manifest/provider promotion and Temporal Cloud dependency | Platform IT Expert | I2 |
| 9 | Production control plane and dark readiness qualification | Platform IT Expert only under separate Founder authority | I3 |

Each slice receives an immediate focused executable check. Each iteration ends with one consolidated
Docker qualification and the applicable independent environment evidence. Source-string assertions
alone do not satisfy assembled runtime configuration, startup, migration, or recovery behavior.

## 12. Failure Modes And Rollback

| Failure | Required response |
|---|---|
| Missing HMAC key/version | Identity mutation routes remain unready; provider read route remains available |
| Compromised HMAC key/version | Enter security hold; disable affected writes and proof-dependent lookup/link/merge; rotate and requalify without automatic identity creation or merge |
| Secret catalog drift | Stop before apply; report logical IDs only |
| Seeder partial failure | Preserve existing versions; retry only missing idempotent operations; no regeneration of valid secrets |
| Manifest mismatch | Stop before mutation or traffic |
| Provider broker failure | Mark only that provider unavailable; do not claim acceptance |
| Demo database restart | Keep traffic at zero; destructively initialize the whole synthetic generation, reseed, and prove no prior generation is reachable |
| UAT migration failure | New revision gets zero traffic; preserve prior revision and database |
| UAT restore failure | Block I2 completion and all Production readiness |
| Rollback compatibility failure | Keep the current qualified revision; do not run a down-migration or restore an incompatible tuple |
| Production prerequisite absent | Reject apply and remain plan-only |

## 13. Owner Review Questions

The single combined edit-mode review must resolve:

- **Enterprise Architecture:** accept or repair the bounded Demo disposable-data exception and confirm
  that three iterations preserve the target topology and promotion sequence.
- **Data Architecture:** confirm HMAC version persistence, migration/reindex continuity, UAT database
  roles, additive migrations, PITR/restore proof, and no durable Demo-data claim.
- **Security Architecture:** confirm domain separation, key lifecycle, no-echo provisioning,
  credential separation, least privilege, compromise behavior, and evidence redaction.
- **Platform Architecture:** confirm ACA-supported Demo ephemeral storage, common manifest rendering,
  Key Vault references, PostgreSQL/Temporal handoff, preflight, rollback, and Production apply guard.

Reviewers repair bounded defects directly in this file and WC-091, then record one consolidated
disposition. They do not defer small wording, interface, validation, or ownership corrections to a
later office pass.

### 13.1 Consolidated Owner Review - 2026-09-11

| Decision space | Disposition | Basis and repaired finding |
|---|---|---|
| Chief Enterprise Architect | `APPROVED - FOUNDER ACCEPTANCE PENDING` | Three iterations preserve the required Demo -> UAT -> plan-only dark Production sequence. The canonical topology now specifies the exact disposable ACA database design, its reset behavior and its no-durability consequences; UAT remains the first persistent tier. |
| Data Architect | `CONCUR` | Sections 6 and 8 now make key-version/domain persistence, collision-safe rotation, role/owner separation, EF migration authority, prior-release compatibility, PITR, isolated restore, RLS, and cross-environment denial explicit and testable. |
| Security Architect | `CONCUR` | Sections 5, 6, 8, 9, and 12 now require domain-separated keys, per-principal credentials and Key Vault operations, no-echo/no-plaintext provisioning, redacted evidence, least privilege, compromise holds, and fail-closed recovery without silent identity creation or merge. |
| Platform Architect | `CONCUR - FOUNDER ACCEPTANCE PENDING` | Sections 4, 5, 8, 9, and 12 define one canonical render, ACA-feasible replica-local storage plus startup reset, Key Vault binding, UAT PostgreSQL/Temporal handoff, preflight, rollback, and a non-bypassable plan-only Production guard. Implementation remains blocked by Founder acceptance and separate session authority. |

**Overall status:** `CONDITIONAL PASS - EA AMENDMENT APPROVED - FOUNDER ACCEPTANCE REQUIRED - IMPLEMENTATION UNAUTHORIZED`.
All small/manageable owner findings identified in this combined call are repaired above. The sole
unresolved prerequisite is Founder acceptance of the exact Enterprise Architecture amendment.
This table is a combined owner disposition, not independent assurance, implementation, cloud
evidence, Production approval, or Founder acceptance.

## 14. Acceptance Mapping

| Requirement | Contract location |
|---|---|
| Restore Demo identity readiness | Sections 6, 7, 9 and 10 |
| Disposable Demo database | Sections 3 and 8.1 |
| Standard secret onboarding | Sections 4 and 5 |
| Safe URL onboarding | Section 4 |
| UAT PostgreSQL and recovery | Sections 8.2, 9 and 11 |
| Production PostgreSQL and readiness | Sections 8.3, 9 and 11 |
| Provider evidence separation | Section 10 |
| Small multi-owner repairs in one round | Section 13 |

## 15. Author Review

**Status:** PASS for the repaired planning contract. Focused validation completed on 2026-09-11:
`git diff --check` passed, and 30 relevant deployment/identity pipeline tests passed in the
repository-defined Docker Compose Python test runner. No host language runtime, virtual environment,
or host dependency installation was used. WC091-I1 remains blocked by Section 3, all implementation
requires explicit current-session Founder authority, and Production remains plan-only and separately
authorized.

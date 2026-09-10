# CB-009 - WC-085 Tenant Provisioning Contract Missing

| Field | Value |
|---|---|
| `institution_id` | `INST-010` |
| `record_id` | `CB-009` |
| `record_type` | Constitutional Blocker |
| `produced_at` | `2026-09-09` |
| Status | **Contract gap resolved for existing-stack path; delivery qualification remains OPEN** |
| Raised by | INST-010 - Platform IT Expert |
| Affected work | WC-085 D-TENANT; independent customer provisioning before Google qualification |
| Constitutional basis | C-032; ADR-003; Identity Boundary Sections 1.7, 2, 3.1, 5 |
| Resolution authority | Founder mandated existing stack; EA/Solution and Data authored the replacement contract |

## Authority Already Present

**Latest controlling update, 2026-09-09:** the Founder mandated C#/Python/JavaScript only and
directed execution. The current ADR-003/ADR-008 amendments and WC-085 architecture/data contracts
supersede the Java publication design: stock Keycloak authenticates; C# provisions accounts and
organisations; current database membership supplies customer tenant authority. No runtime Keycloak
writer, new token issuer, or Java extension is used by this replacement. Historical decisions below
are retained for traceability, not current implementation instructions.

The replacement backend has 203 passing identity tests including restricted-role PostgreSQL and
HTTP checks. A further 11 tests pass through the real Program host. Browser/server handoff has 81
passing focused web tests and a passing TypeScript check. These are local synthetic identity tests,
not real Google or release proof. The contract-authoring obstruction is resolved; keep delivery
qualification open for deployed read-only credentials/configuration, downstream service adoption,
browser account switching, returning/recreated identity, release gates and real Google acceptance.
No repeat implementation approval or general office review is requested. See final-evidence.md.

The Founder authorized implementation, D-TENANT's platform-wide isolation scope, autonomous
execution within constitutional limits, and required-office boundary repair calls with edit authority.
Google-only Demo qualification is conditionally authorized
after review/merge and required gates. None of these permissions is being requested again.

## Original Gap

The accepted Identity Boundary specifies BP-minted account/tenant truth and Keycloak-signed session
claims, but the implementation has only an account UUID on the registration. It lacks an accepted
durable tenant/membership binding, private Keycloak publication interface and privilege scope,
publication recovery protocol, and browser session-renewal handoff. C-032 prohibits INST-010 from
inventing these architectural contracts while implementing them.

## Original Required Resolution

Record one accepted component/API/data contract revision that specifies:

1. Durable account, tenant, membership, and stable identity keys; uniqueness, transaction, concurrency,
   migration, and existing-account compatibility rules.
2. Private Keycloak publication operations, exact least-privilege credentials and attribute ownership;
   committed-state reconciliation after partial failure with explicit API outcomes.
3. Session renewal and authoritative post-renewal checks; returning-account stability and disposable
   Keycloak continuity without email-only relinking or a shared tenant fallback.
4. Trusted downstream tenant propagation and resource authorization, including billing; executable
   two-customer denial/retry/recovery criteria under WC-085 Section 17.2.

This was contract authoring, not a request for another general review. Under the Founder's 2026-09-09
delegation authority, INST-005 authored the Solution amendment, Data and Security authored their
specific residual contracts, and EA addressed the tested privilege conflict. Their completed outcomes
are consolidated below. No additional review or office-assignment request remains.

## Current Consolidated Decision - 2026-09-09

| Boundary repair | Outcome and owning artifact |
|---|---|
| Solution, INST-005 | Completion, private publication/recovery, logical data and renewed-session contracts authored in [Identity Boundary](../architecture/reference/components/identity-boundary.md). Existing public API schemas remain unchanged. |
| Data, INST-006 | Physical ownership, constraints, concurrency, recovery and conservative legacy handling authored in [Data contract](../architecture/reference/product/wc085-identity-provisioning-data-contract.md). Data authorship is complete; no migration or runtime proof is claimed. |
| Security, INST-007 | [Security contract](../architecture/reference/security/wc085-identity-publication-security-contract.md) authored and stock Keycloak 25.0.6 permission probes executed locally. Read-only scope established; publication clearance refused because tested writers also mutate credentials/broker bindings. |
| Enterprise Architect, INST-004 | [Architecture decision](../architecture/reference/product/wc085-identity-architecture-decision.md) preserves the authority boundary and rejects silently broadening BP credentials. No further review requested. |

**Remaining blocker:** the tested stock user-update permissions cannot provide the required
credential-operation separation. `manage-users` permits password resets, broker replacement and
the fixture's institutional role grant. Fine-grained group management restricts users/role mapping
but still permits password resets, broker replacement and unrelated protected-field mutation.
Customer profile restrictions do not constrain a privileged publisher to its owned attributes.
The permission checks used synthetic local containers, not live Demo, real Google accounts or
customer traffic. Exact results and limits are in the Security artifact; no runtime writer is approved.

EA's decision-ready smallest alternative is separately authorized nonruntime administrative
publication, retaining BP read-only verification. It requires a Founder workflow/scope change and
operator action for each new/recreated identity; it does not meet unattended onboarding. If autonomy
remains mandatory, a separately authorized credential-enforcement architecture change is required.
Neither alternative has been authorized or implemented. Current scope remains fail-closed.

The Data call also found an existing migration-13 reference to `billing_profiles(customer_id)`
although migration 12 defines that table by `agent_type`. This is a separate affected-acquisition
activation dependency, not a reason to reopen D-TENANT authorship or alter billing pricing ownership.

Your implementation authorization and office-delegation authority remain valid. No repeat general
review, Founder implementation approval, or assignment request is needed. No code/schema/cloud
change, broad credential grant, provider activation, or real qualification occurred in these calls.

## INST-005 Authored Contract - 2026-09-09

Owning revision: `architecture/reference/components/identity-boundary.md`, WC-085 amendment,
Sections 5.1-5.4, 8.4, 11.1 and 14.1. This is an actual component/service/data-shape amendment under
the assigned Solution office, not fabricated Data/Security concurrence or real-world acceptance.

- Existing start/get/complete/session operations carry the behavior; OpenAPI already supports the
   success body and `503 IDENTITY_DEPENDENCY_UNAVAILABLE`. No new public endpoint/schema is required.
- BP commits the account, unique initial tenant/membership, stable login and actor bindings,
   completion intent/evidence and idempotency reservation atomically. Pending publication retains
   those IDs; success and its replay body are exposed only after verified publication acknowledgement.
- Exact logical private operations read the authenticated user's stock Keycloak federated binding,
   publish committed BP attributes to that same user, and reconcile partial failure through read-back.
   Pending retries recover without duplicate minting. Broad Admin credentials are not selected.
- Keycloak renewal plus existing BP session validation gates portal navigation. The JWT remains the
   tenant anchor; current membership/resource authorization remains a DB obligation. A tenant lookup
   cannot upgrade a tenantless token or substitute another tenant.
- Returning/recreated actor continuity requires the exact proven stable Google login-method key,
   never email. A jointly disposable synthetic reset is a separately approved fallback fixture path,
   not preserved-data recovery proof and not a remedy for insufficient publication permissions.
- Section 14.1 specifies focused rollback/race/publication/renewal/continuity and downstream isolation
   checks. The existing 122 identity-test result predates this contract and does not qualify its new
   provisioning semantics.

## Historical Residual Requests - Completed Above

1. **Data Architect:** physical mapping of Section 8.4 to authoritative account/tenant/membership
    storage, constraints, transaction and concurrency fencing, actor-scoped pre-account access versus
    tenant RLS, durable recovery retention, and additive legacy compatibility/backfill. Specify how
    account-only rows without historical provider proof remain inaccessible; alternatively enumerate
    the exact synthetic reset dependency set for Founder approval. Preserve the repaired rollback
    guarantee. Record the mapping against the Identity component Section 8.4 and the owning existing
    database schema/migration contract; do not substitute the relationship projection data contract
    for Identity persistence ownership.
2. **Security Architect:** author the exact stock-Keycloak principal/credential reference, endpoint
    and user/attribute permissions for Section 5.2, protected attribute/mappers and trusted broker proof,
    and session/retired-actor controls in `architecture/reference/security/security-architecture.md`,
    with the applicable `architecture/reference/product/ae01-security-contract.md` identity control
    cross-reference. Demonstrate narrow permissions on the pinned stock release. `manage-users` is
    not assumed to be attribute-scoped. If that release cannot enforce the required boundary, record
    the concrete architectural conflict; do not choose realm-admin, a custom plugin or a new service.

These two decisions were returned to the parent executor once. Their authorship is complete; the
Security permission conflict required the single bounded EA decision above. CB-009 remains open
for that scope decision and subsequent implementation/evidence, not missing office assignments.
No immutable document, ADR, physical schema, application or infrastructure is changed by this record.

## Bounded Progress And Gate Effect

- Existing-contract completion persistence was repaired: account state and retry record now share
  one save. All 122 identity tests passed, including real PostgreSQL rollback/retry under a restricted
  test application role. See `test-results/wc085/final-evidence.md`.
- Other accepted local engineering may proceed. Do not treat this blocker as a global work freeze.
- Independent tenant provisioning, real Google acceptance, and dependent deployment remain blocked.
  No cloud changes, schema invention, shared-tenant qualification, or expanded permissions are allowed
  as a substitute. No claim of completed isolation or Production readiness is made.
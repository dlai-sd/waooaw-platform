# GOAL-006 Release Promotion, Rollback, and Blue-Green Execution Plan

**Status:** Proposed execution plan
**Prepared:** 2026-08-28
**Canonical baseline:** `main` at `7211eb85d392363135bdfe60c1339fe0c256d85e`
**Execution target:** UAT proof now; Production-ready parameterization without Production provisioning or apply
**Owning office:** INST-010 Platform IT Expert, Skill 17

## 1. Objectives

Deliver the following three capabilities as one release-control component before building Production:

1. **Immutable image promotion:** promote the exact accepted six-image release tuple from Demo to UAT, and make the same mechanism reusable later for UAT to Production.
2. **Rollback:** restore UAT to its last independently accepted compatible tuple after a failed or operator-requested rollout, and make the same mechanism reusable later for Production.
3. **Progressive blue-green deployment:** deploy and verify Green before progressively moving UAT traffic from Blue to Green, with automatic rollback on a blocking signal; parameterize the process for later Production use.

The component is complete only when all three capabilities work together against the real UAT environment and produce immutable, correlated evidence. A workflow that merely copies tags, changes a revision, or documents manual commands does not satisfy the objective.

## 2. Scope and Safety Boundary

### In scope

- Exact-six release tuple: Constitutional Engine, Business Platform, Professional Runtime, AI Runtime, Web, and Billing Engine.
- Demo-to-UAT promotion of digest-pinned images and their supply-chain/qualification evidence.
- UAT Blue/Green revision creation, candidate-specific verification, staged traffic movement, acceptance, retirement, and rollback.
- Automatic rollback on failed Green readiness, failed verification, failed stage observation, stale/missing evidence, or traffic-state mismatch.
- Manual rollback to the recorded last compatible UAT tuple.
- Generic source/target environment contracts so the same implementation can later perform UAT-to-Production promotion and Production rollout/rollback.
- UAT durable-state separation required for meaningful rollback: private PostgreSQL, persistent Keycloak state, explicit schema migration, and revision-independent runtime credentials.
- Cohort-pinned service discovery so a Blue request cannot traverse Green dependencies and a Green request cannot traverse Blue dependencies during staged traffic.
- Revision-aware Azure Monitor observation and authenticated synthetic traffic sufficient to evaluate each approved stage.
- Local tests, offline simulation, Terraform validation, real Azure CLI proof in UAT, cost evidence, and final PR evidence.

### Out of scope for this execution

- Provisioning Production resources.
- Applying any Terraform or traffic mutation to Production.
- Promoting UAT data into Production.
- Rebuilding an image during promotion or rollback.
- Mutable image tags as deployment authority.
- Database down-migration or evidence rewriting.
- Product feature changes unrelated to release control.

### Hard safety rules

- Keep Production plan-only and fail closed on every apply, route, retire, or rollback operation until the Founder separately authorizes Production activation.
- Use the canonical private runner, OIDC identities, private state, cost controls, and cleanup path. Do not run cloud mutation from a GitHub-hosted runner.
- Do not weaken latest-release, attestation, C-059, C-065, C-066, cost, lease, independent-verification, or no-delete/no-replacement controls. Where rollback cannot use a latest-main rule, replace it with a narrower accepted-tuple authorization rule rather than removing the guard.
- Preserve UAT public access with application authentication/RBAC; do not introduce runner-IP or storage-public-access exceptions.
- Keep Blue available until Green is independently accepted. Retire or scale Blue to zero within the C-067 30-minute post-confirmation window.
- Never merge the delivery PR without Founder review.

## 3. Current Baseline

| Capability | Existing asset | Current state | Required change |
|---|---|---|---|
| Exact-six packaging | `scripts/goal006_registry_manifest.py`, CI release artifact | Digest-pinned six-member tuple with scan, SBOM, provenance, signature, source SHA, and run binding | Reuse as promotion payload; add environment acceptance/promotion lineage |
| Release verification | `scripts/goal006_release_verification.py` | Verifies immutable CI tuple | Extend validation to accepted source and target promotion records |
| Deployment entry | `.github/workflows/deploy.yaml` | Parameterized Demo/UAT/Prod plan/apply; selects successful CI artifact for latest `main` | Add explicit release-operation inputs or delegate to dedicated promote/rollout workflows; retain one canonical trusted entry boundary |
| Environment deployment | `.github/workflows/deploy-environment.yaml` | Private runner, OIDC, Terraform, cost/lease gates, Demo-to-UAT configuration initialization | Separate Green creation from accepted-traffic movement; consume authorized promotion record |
| Configuration promotion | Demo blob to UAT blob in `deploy-environment.yaml` | Create-only initialization with digest verification and new UAT lease | Bind reviewed configuration digest to the promoted image tuple and record lineage; generalize source/target rules without copying secrets |
| Container Apps revisions | `infrastructure/terraform/phase2/modules/workload/main.tf` | Exact-six apps use Multiple revision mode, but ingress sends 100% to latest revision | Create named Green at 0%; prevent Terraform from silently moving accepted traffic |
| Independent verification | `.github/workflows/post-deploy-verify.yaml` | Validates live inventory, latest healthy revisions, internal probes, URL, and exact-six tuple after apply | Target the Green revision directly before accepted traffic; evaluate every traffic stage and final state |
| Rollback | No canonical workflow/state record | No accepted-tuple rollback operation | Add last-compatible tuple, traffic restore, verification, and evidence workflow |
| Blue-green helper | `scripts/blue-green-deploy.sh` | Legacy imperative prototype with generic app names, mutable external assumptions, placeholder error rate, direct CLI, and no canonical evidence trust | Do not adopt as-is; replace with tested state/decision tooling integrated into canonical workflows |
| Production boundary | Prod runner is inactive; prior intent is plan-only | No Production live proof is in scope | Add explicit fail-closed Production mutation guard and test it |

### 3.1 Implementer review findings and bridged design

| Severity | Finding | Evidence | Bridged design |
|---|---|---|---|
| Critical | Current UAT data is revision-local | CE, BP, and Billing each embed a PostgreSQL sidecar; Billing embeds Redis; Keycloak uses `--db=dev-file` | Add WC-1A before release-control implementation: private PostgreSQL 16 consistency group, explicit migration job, persistent Keycloak DB, runtime roles, PITR proof; keep Redis explicitly transient |
| Critical | Equal percentages across six apps do not create a coherent release cohort | Runtime configuration calls stable service hostnames, so each internal hop may independently select Blue or Green | Give every revision deterministic cohort-pinned dependency endpoints and bootstrap the current accepted tuple as a pinned Blue anchor before any canary |
| High | Six Azure app updates cannot be transactionally atomic | Terraform/Azure may succeed for a subset before another app fails | Define acceptance as atomic in the operation ledger, implement cloud changes as a locked compensating saga, and restore the recorded pre-state on partial failure |
| High | Proposed additional manual workflows conflict with the current trusted-caller contract | `deploy-environment.yaml` and `post-deploy-verify.yaml` accept only `deploy.yaml@refs/heads/main` | Keep `deploy.yaml` as the sole manual dispatcher; make promotion, Green deployment, observation, rollback, and retirement reusable `workflow_call` implementations |
| High | Canary signals were named but not operationally sourced | UAT has Log Analytics; live Container Apps metrics expose `Requests`, status, restart, replica, CPU/memory dimensions; no evaluator exists | Add an explicit revision-metric collector/evaluator and authenticated synthetic-load job; use active-probe latency because platform `ResponseTime` lacks a revision dimension |
| Medium | Demo and UAT already run the same six digests | Live inventory comparison on 2026-08-28 returned equality | Record the first promotion as `NO_CHANGE` lineage only; require a later Demo-accepted changed tuple for changed-image proof, or label the exercise strictly as a revision/process drill |
| Medium | Inactive revision retention was unspecified | AzureRM 4.14.0 supports `max_inactive_revisions` | Set and test a retention floor sufficient for accepted Blue plus failed Green until terminal evidence and rollback expiry are complete |

## 4. Target Release-Control Model

### 4.1 Promotion is authorization, not image copying

The six images already live in GHCR under immutable digests. Promotion must not rebuild or retag them. It creates an immutable promotion record proving that:

- the source environment independently accepted the exact manifest and configuration digest;
- the live source inventory still matches all six manifest digests;
- CI qualification, signatures, attestations, scans, SBOMs, and provenance remain valid;
- the target environment is the immediate permitted successor (`demo -> uat`, later `uat -> prod`);
- migration/data compatibility and the rollback tuple are declared;
- the target configuration is derived without copying credentials or environment-specific access controls; and
- the actor, source evidence, target, operation ID, timestamps, and policy decision are recorded.

Use immutable operation records plus a conditional mutable pointer:

```text
release-control/<environment>/operations/<operation-id>/promotion.json
release-control/<environment>/operations/<operation-id>/events/000001-<state>-<digest>.json
release-control/<environment>/operations/<operation-id>/plans/<stage>-<digest>.json
release-control/<environment>/operations/<operation-id>/observations/<stage>-<digest>.json
release-control/<environment>/operations/<operation-id>/terminal.json
release-control/<environment>/accepted/current.json
release-control/<environment>/accepted/history/<operation-id>.json
```

Use one create-only block blob per event; do not concurrently append or overwrite a shared JSONL blob. Event ordinals are contiguous, and each event contains the predecessor event digest, canonical payload digest, operation ID, state, actor, timestamp, release manifest digest, six OCI references, reviewed configuration digest, schema/migration watermark, source acceptance evidence references, CI run/SHA, and GitHub attestation identity. Update `accepted/current.json` only with ETag compare-and-swap after independent acceptance. A pointer is never sufficient authority without its immutable referenced record. Retain accepted and last-compatible records plus referenced evidence while any environment or rollback window depends on them; 90-day GitHub artifacts are transport/cache, not durable authority.

### 4.2 State machine

Implement and validate the following transitions:

```text
REQUESTED
  -> AUTHORIZED
  -> PREFLIGHT_PASSED
  -> PLAN_APPROVED
  -> NO_CHANGE

PLAN_APPROVED
  -> GREEN_DEPLOYED
  -> GREEN_VERIFIED
  -> TRAFFIC_SHIFTING
  -> INDEPENDENTLY_CONFIRMED
  -> ACCEPTED
  -> BLUE_RETIRED
  -> CLOSED

GREEN_DEPLOYED | GREEN_VERIFIED | TRAFFIC_SHIFTING | INDEPENDENTLY_CONFIRMED
  -> ROLLING_BACK
  -> ROLLED_BACK

Any cloud mutation with partial or indeterminate state
  -> COMPENSATING
  -> ROLLED_BACK | FAILED_ROLLBACK

ROLLING_BACK -> FAILED_ROLLBACK
```

`NO_CHANGE`, `CLOSED`, `ROLLED_BACK`, and `FAILED_ROLLBACK` are terminal. Every transition must reject missing predecessors, repeated stage IDs, stale ETags, a different manifest/configuration tuple, unauthorized source/target pairs, and evidence loss. Retries append events under the same operation ID; they do not erase failed attempts.

### 4.3 Blue-green unit

Treat the exact-six manifest as one release unit. Deploy all six Green revisions before traffic progression. Do not independently accept a mixed release where only some services have moved to the new tuple.

Cloud mutation is a **compensating saga**, not a transaction. The operation ledger and accepted pointer are the atomic authority. Before each mutation, record all six app ETags/revisions/weights. After mutation, reconcile all six. If any app differs from the approved stage, restore the complete recorded pre-state and mark the attempted transition failed; never mark a partial cloud state accepted.

Each Blue and Green revision must be a coherent cohort. Use compact deterministic suffixes `b-<12 lowercase hex>` and `g-<12 lowercase hex>` derived from the accepted/operation record digest, reject collisions, and configure each revision's internal dependency URLs to revision-specific FQDNs of the same cohort. The initial current UAT tuple must first be recreated and independently accepted as a **Blue anchor** with pinned Blue dependency URLs; otherwise existing Blue revisions continue to call stable hostnames and can cross into Green during a canary.

For a public app, the revision FQDN is a qualification path that bypasses stable-host traffic weights. Add a Host-aware candidate ingress guard: requests whose Host is a revision FQDN require a short-lived verification token with exact environment, operation, revision, audience, and `release_verifier` claim; stable UAT Host requests retain normal application authentication/RBAC. Internal revision FQDNs remain reachable only inside the Container Apps environment. Never expose an unauthenticated candidate endpoint.

Keycloak, identity edge, verification jobs, and infrastructure dependencies are not release-manifest members. Change them only when the reviewed configuration/infrastructure plan requires it, and prove compatibility with both Blue and Green throughout the rollout window.

### 4.4 Traffic progression

Proposed initial UAT policy, subject to Founder approval before live execution:

| Stage | Green weight | Minimum observation | Blocking decision inputs |
|---|---:|---:|---|
| `BG-S0-PRIVATE` | 0% accepted public traffic | Until candidate verification completes | Revision readiness, exact-six digest inventory, internal health, auth/RBAC, CCT/security/journey checks |
| `BG-S1-CANARY` | 10% | 5 minutes | Required sample floor, HTTP/gRPC failures, latency, dependency/data health, Emergency Stop, Evidence First, cost |
| `BG-S2-EXPANSION` | 50% | 10 minutes | Same signals plus no regression from Blue baseline |
| `BG-SF-FINAL` | 100% | Until independent confirmation | Complete verification suite, traffic/revision reconciliation, confirmer verdict |

No stage advances on absent telemetry, insufficient samples, indeterminate verification, cost-gate failure, or traffic mismatch. Threshold values and minimum sample counts must be explicit configuration, validated as non-empty, and approved before the UAT live run. They must not be hard-coded as unconditional success.

Implement the stage evaluator from concrete sources:

- Azure Monitor `Requests`, filtered by `revisionName` and grouped by status code category, for request count and 5xx ratio;
- `RestartCount`, `Replicas`, `UsageNanoCores`, and `WorkingSetBytes`, filtered by `revisionName`, for runtime stability and saturation;
- authenticated synthetic journeys carrying operation/stage correlation IDs for sample generation and end-to-end latency;
- direct candidate health/CCT/Emergency Stop/Evidence First probes for constitutional and dependency signals; and
- cost query/forecast evidence already used by the private deployment path.

Do not use the Container Apps `ResponseTime` metric to compare Blue and Green because the live metric definition does not expose `revisionName`. Use correlated active-probe latency or application telemetry with an explicit revision dimension. Persist raw query responses, time bounds, filters, sample counts, computed values, thresholds, and decisions.

### 4.5 Rollback model

- **Before traffic:** deactivate failed Green; Blue remains at 100%.
- **During staged traffic:** restore all exact-six Blue revisions to 100% through the compensating saga, reconcile the complete routing state, then deactivate Green.
- **After Green acceptance but before Blue retirement:** restore the recorded Blue tuple and independently verify it.
- **After Blue retirement:** reactivate only the recorded last-compatible revisions if Azure retains them and they still match the immutable rollback tuple; otherwise redeploy the same accepted digests/configuration. Never rebuild.
- **Data incompatibility:** block before traffic. Restore application traffic only to a schema-compatible Blue tuple and follow a separately authorized forward-repair/recovery path; never perform an automatic schema down-migration.
- **Rollback failure:** mark `FAILED_ROLLBACK`, retain both revisions/evidence, raise the required incident/Constitutional Blocker, and stop automated mutation.

### 4.6 Canonical workflow graph and locking

Keep `.github/workflows/deploy.yaml` as the sole `workflow_dispatch` entrypoint. Extend its validated inputs with `operation`, `execution`, `source_environment`, `target_environment`, `operation_id`, `stage`, and `reason`; reject irrelevant or conflicting combinations before OIDC/cloud access.

| Operation | Reusable implementation | Release authority | Mutating identity |
|---|---|---|---|
| `forward` | `deploy-environment.yaml` | Latest successful `main` exact-six artifact | Existing environment deployment identity |
| `promote` | `promote-release.yaml` | Immutable source accepted record | Promotion/evidence writer; no workload mutation |
| `deploy-green` | `deploy-environment.yaml` candidate path | Target promotion record | Existing deployment identity |
| `advance` | `shift-traffic.yaml` | Prior stage plus approved next-stage record | Environment traffic identity |
| `rollback` | `rollback-environment.yaml` | Last-compatible accepted record | Environment rollback identity |
| `accept` | `accept-release.yaml` | Independent confirmer verdict plus final observation | Narrow release-state writer; no workload mutation |
| `retire` | `retire-revision.yaml` | Independently accepted Green record | Environment retirement identity |

Reusable workflows must have `workflow_call` only and assert the exact top-level caller `deploy.yaml@refs/heads/main` plus the operation they implement. All operations use repository-wide concurrency group `goal006-${target_environment}-release-control` with `cancel-in-progress: false`; operation storage additionally uses ETag compare-and-swap, and Terraform uses the existing remote-state lock. Do not use `secrets: inherit` unless a named secret is proven necessary; prefer OIDC and explicit least-privilege inputs.

### 4.7 Durable UAT state contract

Before Blue/Green proof, replace revision-local authoritative state with an environment-level UAT consistency group:

- private PostgreSQL Flexible Server 16 in a delegated UAT data subnet with private DNS, TLS, encrypted storage, seven-day PITR minimum, no public firewall rule, and no Production connectivity;
- one UAT database matching the repository's schema scripts, with separate least-privilege CE, BP, Billing, Keycloak, and migration roles; runtime containers never receive the administrator credential;
- credentials stored as environment Key Vault references and exposed only to the owning managed identities;
- an explicit one-shot migration Container Apps Job that applies the ordered `infrastructure/postgres/init/` bundle, records its bundle digest/schema watermark, and runs before Green creation;
- Keycloak 25.0.6 configured with `KC_DB=postgres` and its isolated schema so login/session state survives revisions; and
- Redis classified as transient and reconstructible. It may remain revision-local for this component only if Billing idempotency and authoritative lineage are proven PostgreSQL-backed; otherwise move it to a stable environment service before canary.

Migration preflight must prove additive Blue/Green compatibility, current schema watermark, backup/PITR restorable point, and no destructive/down migration. If current SQL scripts are not safely idempotent and ordered, add a migration ledger and checksums before applying them. Seed representative synthetic UAT data and record invariant queries that must pass before Green, after each stage, after rollback, and after final acceptance.

Current UAT sidecar state is ephemeral and is not a supported migration source. Before cutover, inventory any surviving records and classify them. With `GD-12`, freeze UAT writes, archive only non-secret diagnostic counts/checksums, initialize the durable database from reviewed schema plus approved synthetic fixtures, independently verify invariants, and then switch applications. If any current record is declared authoritative, stop and create a separate accepted export/import and reconciliation procedure; never silently discard or copy it.

## 5. Implementation Plan

Execute the following work components in order. Keep one implementation branch/PR through local qualification. Founder merge is required before canonical live proof; post-proof repository evidence follows `GD-11`. Internal commits are milestones, not separate delivery units.

### WC-1: Reconfirm authority and capture live baseline

1. In the new session, run the authorized BOOTSTRAP sequence and declare INST-010 Platform IT Expert, Skill 17.
2. Obtain explicit Founder implementation authorization before changing runnable code or workflows.
3. Branch from current `main` using the authorized IB/work-contract identifier; do not continue on a stale merged branch.
4. Confirm Azure tenant/subscription, UAT and runner resource groups, private state account, active OIDC identities, runner images, and environment protection rules.
5. Capture current UAT exact-six image digests, active revisions, traffic weights, revision mode, configuration ETag/digest, release CI run/SHA, verification artifacts, lease, and month-to-date/forecast cost.
6. Revalidate the known Demo source evidence before using it: successful `main` deployment run `33091901153`, release run `33089901937`, source SHA `10d7525ccca6fa0d7daa437da7e4630fb94bbeae`, manifest SHA-256 `692896d08153cd20bc22dbe517c7f574d23b633d5eab83885d027d73711245a3`, and retained apply/independent-verification/prestart/cleanup artifacts expiring 2026-11-25. Re-run `goal006_live_inventory.py`; the planning-time comparison passed for all six members on 2026-08-28.
7. From the private runner, read the Demo configuration blob and ETag, bind its digest to the retained release tuple, and persist the acceptance set into durable private release-control storage before relying on the 90-day GitHub artifacts.
8. Confirm the selected Terraform traffic model with a backend-initialized AzureRM 4.14.0 plan: named `template.revision_suffix` plus explicit `ingress.traffic_weight.revision_suffix` entries. Require zero replacement/deletion and exact Blue/Green weights.

**Exit:** Baseline evidence exists; no delete/replacement is present; source acceptance and target rollback tuple are known; the revision/traffic control mechanism is selected from evidence.

### WC-1A: Establish durable UAT state and recovery readiness

This component precedes promotion and traffic work because the existing revision-local databases cannot support meaningful continuity or rollback.

1. Extend the Phase 2 foundation with a UAT-only PostgreSQL Flexible Server 16, delegated data subnet, private DNS, TLS enforcement, encrypted storage, seven-day PITR minimum, backup redundancy selected by the approved cost/risk profile, and public access disabled.
2. Add the server/database/key-reference outputs needed by the workload without outputting credentials. Keep the server and recovery resources protected from lease cleanup and workload retirement.
3. Extend the existing private credential seeder to create separate migration, CE, BP, Billing, and Keycloak credentials in UAT Key Vault; runtime identities receive only their own secret reference.
4. Add a one-shot migration job using a pinned image and the ordered `infrastructure/postgres/init/` bundle. Produce a canonical bundle checksum, migration ledger, before/after schema watermark, and per-file result. Reject changed checksums, order gaps, destructive statements, and concurrent migration.
5. Remove PostgreSQL sidecars from CE, BP, and Billing. Point each service to its least-privilege UAT role through Key Vault-backed connection configuration. Verify RLS/session initialization and append-only protections against the shared consistency group.
6. Change Keycloak from `--db=dev-file` to PostgreSQL with an isolated schema/role. Verify login, refresh, revocation, and session continuity across a Keycloak revision restart.
7. Treat Redis as non-authoritative: prove Billing idempotency and lineage survive cache loss, then either retain revision-local Redis with an explicit flush/rebuild test or move it to a stable internal UAT cache if the proof fails.
8. Seed synthetic representative UAT records and capture invariant queries for CE evidence tails, BP tenant/RLS data, Billing idempotency/lineage, and Keycloak identity/session state.
9. Perform an isolated PITR restore drill, verify schema/data/evidence watermarks and key references, and record RPO/RTO. Do not reopen release progression on health checks alone.
10. Run a no-delete/no-replacement Terraform plan after adoption and a cost forecast including PostgreSQL dual-revision windows.

**Exit:** UAT authoritative state survives app revisions, migration is explicit and compatible, an isolated restore is proven, cache loss is non-authoritative, and all invariant queries pass.

### WC-2: Define release-operation schemas and validators

1. Add JSON schemas or strict Python model validation for promotion record, accepted environment record, operation event, traffic stage, observation result, rollback tuple, and terminal evidence summary.
2. Extend or add focused scripts under `scripts/` to:
   - validate source/target succession;
   - resolve and verify immutable CI artifacts and source acceptance;
   - construct and hash promotion records;
   - validate legal state transitions;
   - compare all six desired/live revision digests;
   - plan traffic transitions without mutation;
   - evaluate stage signals and fail closed;
   - plan rollback from the last-compatible tuple; and
   - reconcile final revision, traffic, evidence, and cost state.
3. Keep pure decision logic separate from Azure/GitHub shell orchestration so it can be unit tested offline.
4. Require operation IDs, manifest/config digests, predecessor digest, ETags, actor, environment, and evidence references on every mutation decision.
5. Add negative tests for mutable tags, rebuilt/substituted digests, skipped environments, stale source acceptance, stale ETags, missing telemetry, illegal transitions, mixed six-member tuples, unavailable Blue, and Production mutation.

**Exit:** Local validators deterministically accept valid fixtures and reject every unsafe/partial fixture before any cloud workflow is changed.

### WC-3: Implement immutable Demo-to-UAT promotion

1. Create `.github/workflows/promote-release.yaml` as a `workflow_call`-only implementation invoked by canonical `deploy.yaml@refs/heads/main`; it must have no manual dispatch.
2. Inputs: source environment, target environment, source acceptance operation ID, execution mode (`plan` or `apply`), and optional reason. Do not accept arbitrary image tags or free-form image lists.
3. Permit `demo -> uat`; encode `uat -> prod` but keep Production apply blocked. Reject same-environment, reverse, or skipped promotion.
4. Retrieve the source immutable acceptance record, exact-six manifest, attestations, and independent verification evidence. Verify content digests and GitHub identities before Azure access.
5. Read the live/retained source inventory and require exact equality with the manifest. If Demo is deactivated, require its signed terminal deactivation evidence and retained accepted tuple.
6. Derive target configuration from the reviewed source configuration through an allowlisted transform. Remove Demo-only IP restrictions and leases; never copy Key Vault secret values, identities, hostnames, state coordinates, or credentials.
7. Create the immutable UAT promotion operation record. Upload with create-only semantics, download through the private path, and verify the digest.
8. In plan mode, emit the complete proposed record and target diff without changing accepted pointers or workloads.
9. In apply mode, write only the authorized promotion record; do not move traffic or mark UAT accepted.
10. Compare source manifest/configuration digests with the target's accepted record. If equal, emit terminal `NO_CHANGE`, preserve lineage, and prohibit Green deployment from claiming changed-image proof. Planning-time evidence shows Demo and UAT currently have identical six-image tuples.
11. Publish 90-day GitHub artifacts and durable private evidence references.

**Exit:** A valid Demo-accepted exact-six tuple can be authorized for UAT without rebuilding/copying images, and every tamper/stale/unauthorized path fails closed.

### WC-4: Make Terraform candidate-safe

1. Parameterize the workload module with release operation ID/revision suffix and explicit accepted/candidate traffic intent.
2. Ensure a changed image tuple creates named Green revisions while Blue remains active at its prior accepted weight.
3. Remove `latest_revision = true, percentage = 100` as the implicit deployment behavior for exact-six apps.
4. Remove authoritative database sidecars per WC-1A; keep stable app names, ingress boundaries, managed identities, Key Vault references, permitted transient cache treatment, scale bounds, and no-replacement guarantees.
5. Make Terraform the sole declarative owner of accepted traffic weights. AzureRM 4.14.0 supports both named template revision suffixes and traffic weights keyed by revision suffix. Every stage supplies the immutable Blue suffix, Green suffix, and approved percentages; direct `az containerapp ingress traffic set` is diagnostic/emergency tooling only and must not be a second normal-path owner.
6. Apply each exact-six stage from one reviewed Terraform plan. Query Azure immediately afterward and reconcile every app's full revision-weight map to the approved stage before observing or advancing.
7. Use revision-specific FQDNs returned by Azure for candidate verification. Planning-time proof confirmed both public (`ca-uat-web--<suffix>.<domain>`) and internal (`ca-uat-constitutional-engine--<suffix>.internal.<domain>`) Green endpoints are available independently of the stable app FQDN.
8. Expose revision names, revision FQDNs, and desired traffic as private outputs consumed by verification; do not publish internal topology in public summaries. Labels may be human-readable aliases but are not release authority.
9. Generate each cohort's dependency URLs from deterministic revision suffixes. Green must call only Green CE/BP/AIR/Billing endpoints; the accepted Blue anchor must call only Blue endpoints. Keep Keycloak and identity edge stable and shared unless their reviewed input changes.
10. Set `max_inactive_revisions` high enough to retain accepted Blue and failed Green through rollback/evidence expiry; initial value `5`, blocked from reduction below `2`, with a pre-retirement inventory check.
11. Validate saved Terraform plan JSON against an operation allowlist: Green creation may update only exact-six templates/traffic; stage movement may update only exact-six ingress weights; rollback may update weights/activation; any other resource action blocks apply.
12. Run `terraform fmt`, `terraform init -backend=false`, `terraform validate`, and plan/no-delete/no-replacement assertions for Demo, UAT, and Production roots.

**Exit:** A UAT apply can create all six Green revisions at 0% accepted traffic, and a subsequent plan neither replaces apps nor silently moves traffic.

### WC-4A: Bootstrap the accepted Blue anchor

1. Resolve current UAT's accepted exact-six manifest, configuration, schema watermark, state generation, and revision inventory from retained verification run `33177257822` plus live evidence.
2. Create deterministic Blue suffixes and cohort-specific dependency URLs for all six apps using the same accepted digests. This is a same-digest anchoring operation, not image promotion.
3. Plan creation with current revisions at 100% and Blue-anchor revisions at 0%; enforce the WC-4 plan allowlist.
4. Apply on the private runner, verify all six Blue-anchor revisions directly, then move stable traffic to the anchor using the compensating-saga process.
5. Run authenticated journeys and all WC-1A state invariants before and after the move. Roll back to the captured pre-state if any invariant changes.
6. Independently accept the anchor and store it as UAT's initial `accepted/current.json` and `last_compatible` tuple. Retain the pre-anchor revisions until closure evidence is complete.

**Exit:** The accepted UAT Blue cohort is immutable, revision-pinned, state-compatible, independently verified, and safe to pair with a future Green cohort.

### WC-5: Add candidate-specific independent verification

1. Refactor `.github/workflows/post-deploy-verify.yaml` or add a narrowly scoped reusable verifier that accepts operation ID, manifest digest, and exact candidate revision map.
2. Verify Green by the exact revision FQDN map produced by WC-4 before public traffic. Do not equate `latestRevisionName`, a mutable label, or readiness alone with acceptance.
3. Validate all six digest references, readiness/health, Keycloak OIDC discovery/session behavior, application authentication/RBAC, internal service connectivity, Constitutional Engine health, Evidence First, Emergency Stop, Temporal idempotency, Billing lineage, and approved customer journeys applicable to the release.
4. Capture baseline and Green telemetry using revision dimensions. Telemetry absence is a failure.
5. Add an authenticated synthetic-load Container Apps Job that targets the stable public UAT URL, emits operation/stage correlation IDs, exercises approved customer journeys and auth/RBAC denials, and generates the approved sample floor without bypassing ingress or identity.
6. Add `scripts/goal006_release_observation.py` to collect/evaluate revision-filtered `Requests`, 5xx ratio, restart/replica/resource metrics, active-probe latency, constitutional probes, invariant queries, and cost. Require complete time windows and persist raw plus derived evidence.
7. Extend the verification identity with only Azure Monitor metrics read and Log Analytics query permissions at UAT scope; keep deployer and confirmer identities/jobs distinct and provide no app write authority.
8. Emit a signed/hashed candidate-verification record that authorizes only the next traffic stage.

**Exit:** Green can be proven independently at 0% accepted traffic; failures leave Blue untouched and produce complete evidence.

### WC-6: Implement progressive traffic controller

1. Add a reusable traffic workflow/controller with inputs limited to operation ID and approved next stage; resolve revisions and weights from immutable state rather than caller-provided arbitrary values.
2. Before every stage, verify current traffic equals the prior recorded state, the release/config tuple is unchanged, Green remains healthy, Emergency Stop is reachable, cost remains within bounds, and the stage approval is valid.
3. Capture all six pre-state ETags/revisions/weights, validate the saved Terraform plan allowlist, and apply under the environment/state lock. Immediately query Azure and require exact reconciliation.
4. Observe for the configured window and sample floor. Evaluate explicit technical, security, constitutional, journey, dependency/data, and cost thresholds.
5. Advance only one ordered stage at a time: `BG-S1-CANARY`, `BG-S2-EXPANSION`, `BG-SF-FINAL`.
6. On apply failure, partial/mixed routing, or a blocking/indeterminate observation, invoke the same rollback path using the recorded pre-state/Blue tuple. Do not continue on retry without a new linked decision event.
7. After final independent confirmation, invoke `accept-release.yaml` with the immutable confirmer verdict. Its release-state identity may create acceptance history and ETag-update `accepted/current.json` but cannot mutate workloads, roles, secrets, or Terraform state.
8. After acceptance, deactivate/scale Blue to zero within 30 minutes and verify cost/revision state.
9. Upload stage plans, before/after traffic, observations, decisions, CLI/API responses, and cost evidence under the operation ID.

**Exit:** UAT progresses 0 -> 10 -> 50 -> 100 only on passing evidence, with no mixed exact-six acceptance and no unobserved traffic mutation.

### WC-7: Implement automatic and manual rollback

1. Create `.github/workflows/rollback-environment.yaml` with a dedicated environment-bound rollback OIDC identity. Do not reuse the current control-plane identity, which has Contributor and RBAC Administrator across Demo/UAT/Prod, or the cleanup identity, which cannot route traffic.
2. Inputs: environment, failed/current operation ID, mode (`plan` or `apply`), and reason. Resolve the rollback tuple from immutable accepted history; do not accept arbitrary digests/revisions.
3. Keep Production apply blocked. Require `main`, an authorized actor, environment protection, current traffic ETag/state match, and an existing compatible Blue tuple.
4. Plan output must show current/candidate/rollback tuple, six revision changes, traffic changes, data compatibility, expected cost, and evidence destination.
5. Apply must restore all exact-six Blue weights as a compensating saga, query and reconcile traffic, run independent functional/auth/constitutional checks, then deactivate failed Green. Do not describe the cloud mutation itself as atomic.
6. Preserve the failed operation and append rollback events. Mark `ROLLED_BACK` only after independent verification; otherwise mark `FAILED_ROLLBACK` and stop.
7. Make the progressive controller call this same workflow/path for automatic rollback so manual and automatic behavior cannot diverge.
8. Provision a UAT-scoped custom role with `microsoft.app/containerapps/read`, `microsoft.app/containerapps/write`, `microsoft.app/containerapps/revisions/read`, `microsoft.app/containerapps/revisions/replicas/read`, `microsoft.app/containerapps/revisions/activate/action`, `microsoft.app/containerapps/revisions/deactivate/action`, `microsoft.app/locations/containerappoperationresults/read`, and `microsoft.app/locations/containerappoperationstatuses/read`. Add Reader at the UAT resource group and Storage Blob Data Contributor at the private release/state container only as required for Terraform refresh/state and evidence. Explicitly exclude resource delete, RBAC administration, secret listing, exec/debug/logstream, revision restart, registry push, and access outside UAT. Create the equivalent Production role definition/subject contract but no Production assignment or activation.
9. Add idempotency tests: re-running a completed rollback is a verified no-op; stale or conflicting runs fail closed.
10. Implement two compensation levels: first generate/apply a Terraform rollback plan after releasing/renewing the state lock; if Terraform cannot restore traffic, use the dedicated rollback identity with explicit Azure revision weights as emergency compensation, then import/refresh and require a zero-drift Terraform plan. Preserve both attempts in evidence.

**Exit:** Both automatic and authorized manual UAT rollback restore the exact recorded compatible tuple and prove the resulting traffic and functionality.

### WC-8: Offline and local qualification

1. Add focused unit tests for all release-operation decision scripts and schemas.
2. Extend pipeline contract tests to prove trusted callers, immutable checkouts/actions, environment choices, private runners, OIDC separation, permission ceilings, atomic ledger acceptance plus compensating cloud mutation, evidence retention, and Production mutation rejection.
3. Add an offline state-machine simulation covering:
   - successful promotion and 0/10/50/100 rollout;
   - Green startup failure at 0%;
   - verifier failure before traffic;
   - blocking canary signal and successful rollback;
   - missing telemetry and successful rollback;
   - partial traffic update and reconciliation failure;
   - manual rollback after final shift but before Blue retirement;
   - rollback failure terminal state;
   - stale ETag/concurrent operation rejection; and
   - every Production mutation path blocked.
4. Add cohort-routing tests proving every Blue dependency URL resolves to Blue and every Green dependency URL resolves to Green; reject stable internal service URLs inside cohort revisions.
5. Add state tests for migration checksum/order, destructive-statement rejection, Blue/Green schema compatibility, cache-loss idempotency, Keycloak session continuity, PITR invariants, and rollback data watermarks.
6. Add compensating-saga tests for failure after each of six app updates, emergency compensation, state refresh, and zero-drift reconciliation.
7. Run targeted tests first, then the full pipeline/GOAL-006 test suite and relevant service tests.
8. Run action lint/schema checks and Terraform format/validate/plan checks across Demo, UAT, and Production.

**Exit:** All local/offline tests pass with deterministic fixtures and no gate suppression.

### WC-9: Real UAT execution and rollback drills

Canonical live proof can run only after the implementation is merged to `main`; branch execution would violate the trusted-caller and latest-main controls. Do not mutate Production.

1. After Founder merges the implementation PR, require successful `ci.yaml` on the exact new `main` SHA and an unexpired exact-six release artifact.
2. Deploy that exact release to Demo through canonical `deploy.yaml`, independently verify it, and obtain `GD-03` acceptance. This produces the changed Demo-accepted tuple needed for actual image-promotion proof; if all six digests remain equal, record a process drill and do not claim changed-image proof.
3. Capture pre-run UAT baseline, cost, accepted Blue anchor, state/PITR watermarks, active revisions, and traffic.
4. Run Demo-to-UAT promotion in plan mode and inspect the full record/diff, then apply and verify immutable storage round-trip and evidence lineage.
5. Run UAT Green deployment at 0%; prove Blue remains at 100%, all six Green revisions exist with promoted digests, and every Green dependency endpoint is cohort-pinned.
6. Run candidate-specific verification, synthetic load, and all state/session/cache invariants.
7. **Automatic rollback drill:** progress to 10%, invoke an approved synthetic blocking observation (not a bad/rebuilt image), prove compensating restoration of Blue 100%, Green deactivation, independent verification, unchanged data watermarks, and `ROLLED_BACK` evidence.
8. Re-run from a new operation ID; progress 0 -> 10 -> 50 -> 100 with real observations and independent confirmation.
9. **Manual rollback drill:** before Blue retirement, invoke authorized manual rollback, prove exact-six Blue restoration, cohort routing, state/session continuity, and independent verification.
10. Execute the final successful rollout once more, independently accept Green, retire Blue within 30 minutes, and reconcile cost/state/evidence.
11. Run one post-operation Terraform plan and require no unintended traffic reset, replacement, deletion, migration, or state drift.
12. Verify UAT URL, authentication/RBAC, exact-six inventory, internal functions, lease, PITR, cleanup, durable operation records, and evidence retention.

**Exit:** UAT has live proof for promotion, progressive rollout, automatic rollback, manual rollback, final acceptance, Blue retirement, and post-run reconciliation.

### WC-10: Production reuse proof without Production build

1. Run all Production paths in offline simulation and Terraform/workflow plan-only mode.
2. Prove the source/target validator permits only `uat -> prod` for the future Production promotion.
3. Prove Production consumes the identical UAT-accepted manifest/configuration lineage and cannot rebuild/substitute images.
4. Prove Production apply, traffic shift, rollback apply, and retirement fail before Azure mutation while Production remains inactive.
5. Produce a future activation checklist covering Production runner activation, environment approvals, OIDC identities/RBAC, state/configuration, edge/DNS/certificates/WAF, observability thresholds, data/recovery acceptance, cost limits, and Founder authorization.

**Exit:** The implementation is environment-parameterized and Production-ready, but Production remains unprovisioned and unchanged.

### WC-11: Evidence, review, and final PR

1. Before live proof, record local tests, offline simulations, Terraform plans, role previews, expected cost, and author review in one implementation PR.
2. Run C-059, C-065, C-066, CodeQL-relevant tests, full affected suites, Terraform validation, and one-time PR status snapshots.
3. Commit at meaningful milestones using traceable conventional commits; push one branch and open the implementation PR using the repository template. Do not merge it; hand it to the Founder.
4. After Founder merge, execute WC-9 only from the exact successful `main` release and retain all raw/derived evidence in Actions artifacts plus durable private operation storage.
5. Publish workflow run IDs, release SHA, manifest/config/migration digests, operation IDs, revisions, traffic history, rollback timings, state watermarks, URLs, cost, and terminal states in the owning issue/Work Contract evidence record.
6. Update repository evidence and `constitution/PROJECT_STATE.md` only if the Work Contract/session-close rules require it. Because canonical proof occurs post-merge, such an update requires a separate evidence-only PR; never rewrite or weaken `main` trust to avoid that PR.
7. State explicitly that Production was not provisioned or mutated and attach the reproducible Production activation checklist.

**Exit:** Founder-merged implementation is proven through canonical `main`; immutable UAT evidence is complete; any required evidence-only PR remains unmerged for Founder review.

## 6. Expected File Surfaces

Prefer extending these existing owners and add new files only where responsibility is genuinely new:

- `.github/workflows/deploy.yaml`
- `.github/workflows/deploy-environment.yaml`
- `.github/workflows/post-deploy-verify.yaml`
- `.github/workflows/promote-release.yaml` (new reusable workflow, no manual dispatch)
- `.github/workflows/shift-traffic.yaml` (new reusable workflow, no manual dispatch)
- `.github/workflows/rollback-environment.yaml` (new reusable workflow, no manual dispatch)
- `.github/workflows/accept-release.yaml` (new reusable workflow, no manual dispatch)
- `.github/workflows/retire-revision.yaml` (new reusable workflow, no manual dispatch)
- `scripts/goal006_registry_manifest.py`
- `scripts/goal006_release_verification.py`
- `scripts/goal006_live_inventory.py`
- `scripts/goal006_release_operation.py` (new pure state/policy model)
- `scripts/goal006_traffic.py` (new pure planning/reconciliation logic)
- `scripts/goal006_release_observation.py` (new metric/probe evaluator)
- `scripts/goal006_migration_bundle.py` (new migration order/checksum/policy validator)
- `scripts/goal006_terraform_plan_policy.py` (new per-operation plan allowlist)
- `infrastructure/deployment-stacks/goal006-runner/prerequisites.bicep`
- `scripts/goal006_runner_prerequisites.py`
- `infrastructure/terraform/phase2/modules/foundation/main.tf`
- `infrastructure/terraform/phase2/modules/foundation/variables.tf`
- `infrastructure/terraform/phase2/modules/workload/main.tf`
- `infrastructure/terraform/phase2/modules/workload/variables.tf`
- `infrastructure/terraform/phase2/modules/workload/outputs.tf`
- `infrastructure/postgres/init/` migration bundle and ledger inputs
- `src/constitutional-engine/`, `src/business-platform/`, and `src/billing-engine/` database configuration where required for shared UAT PostgreSQL
- `web/`, `src/business-platform/`, and `src/professional-runtime/` candidate-Host verification guard surfaces for externally exposed revision FQDNs
- Demo/UAT/Production workload root variables and module calls
- UAT foundation root outputs/variables and Production plan-only contracts
- Focused tests under `tests/pipeline/`
- Focused migration/state/session tests under existing service test projects
- GOAL-006 evidence and required state records

Do not treat `scripts/blue-green-deploy.sh` as the production implementation. Retire it or reduce it to a tested wrapper only after the canonical controller replaces its responsibility and references are checked.

## 7. Definition of Done

All conditions below are mandatory:

- Demo-to-UAT promotion uses the same six OCI digests and verified supply-chain evidence; no image is rebuilt or authorized by mutable tag.
- Source acceptance, target promotion, configuration digest, migration compatibility, and rollback tuple are cryptographically linked.
- Green is created at 0% accepted traffic and verified by exact revision before canary.
- UAT traffic progresses through at least two partial stages before 100%, with approved windows, samples, thresholds, and immutable decisions.
- Missing or failed evidence automatically restores Blue and prevents acceptance.
- Automatic and manual rollback both restore the exact last-compatible six-member tuple and pass independent verification.
- Failed rollback cannot report success and leaves actionable retained evidence.
- Final acceptance is atomic for the exact-six tuple; mixed release acceptance is impossible.
- Cloud changes use recorded pre-state and compensating rollback; partial six-app mutation can never become accepted.
- Blue and Green dependency calls remain inside their own revision cohorts at every stage.
- UAT PostgreSQL, Keycloak state, migration watermarks, and constitutional/business/billing invariants survive Green creation, both rollback drills, final acceptance, and PITR restore.
- A same-digest promotion terminates as `NO_CHANGE` and is never reported as changed-image proof.
- Canary decisions contain revision-filtered raw metrics, authenticated synthetic samples, active-probe latency, thresholds, and deterministic calculations.
- Blue retirement meets the 30-minute rule and is reconciled with traffic and cost.
- Terraform remains convergent after traffic operations and proposes no unintended replacement/deletion/reset.
- Demo and UAT behavior is covered; all shared logic is parameterized for Production.
- Every Production mutation path remains blocked and no Production resource is created or changed.
- Local, offline, pipeline, security, Terraform, and real UAT validations pass.
- Implementation is merged only by the Founder before canonical live proof; any required post-proof evidence PR is left unmerged for Founder review.

## 8. Dependencies, Gaps, and Blocking Rules

### 8.1 Governance dependency list (Founder/user owned)

These items are intentionally separated from engineering execution. The Founder/user will resolve or provide them. Engineering should continue through all work that does not depend on an unresolved item and pause only at the stated blocking gate.

| ID | Governance dependency | Required decision/evidence | Becomes blocking at |
|---|---|---|---|
| `GD-01` | Current-session implementation authorization | Explicit response authorizing runnable code/workflow changes for the new session | Before the first implementation edit |
| `GD-02` | Work Contract and trace identifier | Authorized IB/Work Contract covering all three objectives and the UAT live drills | Before branch creation and milestone commits |
| `GD-03` | Demo source acceptance authority | Founder-recognized Demo acceptance record identifying the exact six-image tuple, reviewed configuration digest, and retained evidence | Before promotion apply in WC-3; plan/validator work may continue |
| `GD-04` | UAT rollout policy | Approval of stage weights, observation windows, minimum samples, automatic rollback thresholds, and accepted synthetic-failure drill | Before live canary traffic in WC-9; implementation and offline simulation may continue |
| `GD-05` | Independent confirmer and permission ceiling | Named confirmation authority plus acceptance of the read-only Azure verification identity/permissions, or an approved alternative that preserves deployer/confirmer separation | Before independently confirming Green in WC-5/WC-9 |
| `GD-06` | Migration and rollback compatibility authority | Accepted owner(s) and required evidence for schema/data compatibility, forward repair, PITR, Keycloak session handling, Temporal idempotency, and Billing lineage | Before any candidate with data/schema change reaches nonzero traffic |
| `GD-07` | UAT rollback-drill authority | Approval to deliberately trigger a synthetic blocking observation at canary and to perform the subsequent manual rollback drill | Before the two live rollback drills in WC-9 |
| `GD-08` | Production activation boundary | Continued confirmation that Production is plan-only, followed later by separate authorization for runner/resource activation and live UAT-to-Production promotion | Not blocking this plan; blocks every Production mutation |
| `GD-09` | Implementation PR review and merge | Founder review after local/offline qualification and author review; only the Founder merges so canonical `main` proof can begin | Before WC-9 live execution |
| `GD-10` | Durable UAT state and cost authorization | Approval to provision private PostgreSQL/PITR and migrate UAT from revision-local databases within an accepted cost ceiling | Before WC-1A cloud apply; design/tests/plans may continue |
| `GD-11` | Main-only proof and evidence publication model | Approval of the safe sequence: Founder merges implementation PR, canonical proof runs on `main`, and any required repository evidence uses a second evidence-only PR | Before merging the implementation PR |
| `GD-12` | Ephemeral UAT state disposition | Confirmation that current revision-local UAT data is disposable synthetic state and may be replaced by reviewed fixtures, or identification of authoritative records requiring an accepted migration | Before WC-1A database cutover |

Governance dependencies must be recorded by stable evidence such as an approved Work Contract, protected-environment decision, issue/PR comment, or accepted policy record. An informal assumption in workflow code is not sufficient.

### 8.2 Groomed engineering decisions (executor owned)

Planning-time research has resolved the implementation direction for every engineering gap. These are binding design inputs unless executable validation falsifies one; a falsified decision must be recorded with evidence before changing direction.

| ID | Settled engineering decision | Evidence and implementation consequence | Residual executable proof |
|---|---|---|---|
| `ED-01` | Use the retained Demo accepted tuple as the initial promotion source, then persist it in private release-control storage | Successful `main` deployment run `33091901153`; exact-six release run `33089901937`; artifacts retained through 2026-11-25; live Demo inventory passed the canonical validator; manifest digest recorded in WC-1 | Private-runner configuration digest/ETag read and storage round-trip |
| `ED-02` | Ordinary forward deployment retains latest-successful-`main` trust; promotion/rollback instead require an immutable source-accepted or last-compatible record | This permits older accepted rollback tuples without permitting caller-selected stale SHA/image inputs | Negative authorization fixtures and one rollback plan |
| `ED-03` | Terraform is the sole normal-path traffic-weight owner | AzureRM 4.14.0 source exposes named template revision suffix and traffic weights keyed by revision suffix; current live UAT is Multiple mode | Backend-initialized 0/100, 10/90, 50/50, 100/0 plans with no replacement/deletion |
| `ED-04` | Verify Green through exact revision FQDNs, not `latestRevisionName` or mutable labels | Live UAT exposes revision FQDNs for both public and internal apps; labels remain optional display aliases | Zero-traffic Green internal and external probes from the private verification path |
| `ED-05` | Refactor verification around an immutable operation ID plus exact six-revision map | Current latest-revision verifier cannot distinguish candidate readiness from acceptance | Candidate fixture tests and live 0% Green verification |
| `ED-06` | Store append-only hashed operation events plus ETag-guarded accepted pointers in the existing private storage boundary | Public access is disabled and Codespace access correctly fails; the private runner already has the storage path | Create-only event upload, digest download, concurrent ETag rejection, pointer recovery |
| `ED-07` | Create a dedicated UAT rollback OIDC identity and narrow custom role | Current control-plane identity is Contributor/RBAC Admin across all environments; cleanup identity is cleanup-only | Role assignment inspection plus authorized/forbidden action tests before rollback apply |
| `ED-08` | Replace the legacy shell script's responsibility with tested Python policy/state logic and canonical workflows | The script has placeholder telemetry and bypasses current trust/evidence controls | Reference scan, parity tests, then deletion or wrapper-only reduction |
| `ED-09` | Execute from a clean branch/worktree created from current `main` | Active `agent/update/platform-it-cloud-delivery` contains extensive unrelated/stale changes | Clean status and baseline SHA check before first edit |
| `ED-10` | Keep Production paths parameterized but mutation-disabled | Production resources/runner remain intentionally inactive and this component is UAT-first | Offline/plan tests proving all Production mutation paths fail before Azure writes |
| `ED-11` | Move UAT authoritative state out of app revisions before claiming rollback | Current CE/BP/Billing PostgreSQL and Keycloak `dev-file` state are revision-local; repository recovery contract requires PITR and data invariants | Private PostgreSQL/migration/Keycloak/PITR qualification in WC-1A |
| `ED-12` | Pin all service-to-service calls to deterministic Blue or Green cohort endpoints | Stable internal hostnames independently split each hop and can create mixed-version request paths | Blue-anchor and Green cohort routing tests plus live correlated journeys |
| `ED-13` | Treat six-app Azure mutation as a compensating saga; only ledger acceptance is atomic | Azure/Terraform cannot transactionally update six Container Apps | Per-app failure injection, complete pre-state restore, and zero-drift reconciliation |
| `ED-14` | Keep `deploy.yaml` as the sole manual entrypoint | Existing reusable workflows trust only canonical `deploy.yaml@refs/heads/main` | Operation/input matrix tests and shared environment concurrency proof |
| `ED-15` | Use revision-filtered Requests/runtime metrics plus authenticated synthetic probes | Live UAT exposes revision dimensions for Requests/restarts/resources but not ResponseTime | Raw metric query fixtures, sample-floor generation, and deterministic evaluator tests |
| `ED-16` | Store one create-only blob per state event | A shared appended JSONL blob is unsafe under concurrent jobs and weakens immutability | Concurrent writer rejection, ordinal/predecessor validation, and pointer recovery |
| `ED-17` | Guard direct public revision FQDNs with operation-bound verifier authorization | Revision FQDNs bypass stable-host traffic weights and are externally addressable for public apps | Unauthorized direct-host denial and authorized verifier/canary journey tests |
| `ED-18` | Treat equal source/target tuples as `NO_CHANGE` | Planning-time live comparison shows Demo and UAT currently run identical six digests | No-op promotion fixture and a later changed Demo-accepted tuple for image proof |
| `ED-19` | Separate independent confirmation from acceptance mutation | A read-only confirmer cannot safely update the accepted pointer | Immutable verdict plus narrow release-state writer identity and ETag update tests |
| `ED-20` | Reinitialize ephemeral UAT sidecar state unless explicitly classified authoritative | Revision-local stores have no durable migration guarantee and may already be lost after scale-to-zero | `GD-12`, freeze/inventory evidence, reviewed fixtures, and invariant comparison |

### 8.3 Residual technical validations, not planning gaps

The following checks remain because they require the implementation or private execution environment; they do not require more design grooming:

1. Terraform is not installed in the current planning container. Run exact AzureRM 4.14.0 plans on the pinned private runner and reject the design if any stage replaces/deletes an app or creates an unintended revision.
2. The state/configuration account has public access disabled, so its Demo configuration ETag/digest cannot and should not be read from this Codespace. Perform that read and durable acceptance persistence through the existing private runner.
3. Revision-specific FQDNs are proven to exist, but the new Green verification job must prove DNS/TLS/reachability from its final private execution context at 0% traffic.
4. The rollback custom role and OIDC subject do not yet exist. Provision and test them in UAT before live rollback; lack of assignment is an implementation task, not a reason to reuse Contributor.
5. The current Demo evidence is technically complete and live-inventory-compatible, but `GD-03` still determines whether the Founder recognizes it as the promotion authority.
6. The ordered SQL bundle exists, but its full idempotency/destructive-statement profile and service schema watermarks must be established by WC-1A before any shared UAT database apply.
7. Current revision-filtered UAT Requests queries return structurally valid series but may contain zero samples. The synthetic-load job must meet the approved sample floor before any stage can pass.

### 8.4 Required script contracts

All new Python tools use UTF-8 JSON input/output, canonical sorted-key hashing, no secret values, deterministic exit codes (`0` pass/result, `1` policy rejection, `2` malformed input), and write evidence only through an explicit `--output` path. Minimum interfaces:

```text
goal006_release_operation.py create|validate|transition|accept|terminal
  --environment --operation-id --record/--previous --manifest --configuration --output

goal006_traffic.py capture|plan|reconcile|rollback-plan
  --environment --operation --stage --accepted-record --live-inventory --output

goal006_release_observation.py collect|evaluate
  --environment --operation --stage --revision-map --policy --start --end --output

goal006_migration_bundle.py inventory|validate|watermark
  --root infrastructure/postgres/init --database-evidence --output

goal006_terraform_plan_policy.py validate
  --operation deploy-green|advance|rollback|retire --plan-json --revision-map --output
```

Shell/workflow code may invoke Azure/GitHub, but policy decisions must consume these structured results and require their success. Unit tests call Python functions directly; workflow tests assert exact CLI contracts.

### 8.5 Execution posture

No engineering design decision remains open, and no engineering gap prevents starting local implementation, offline qualification, Terraform changes, or UAT preflight. The executor should implement the settled decisions above and stop only if executable evidence falsifies one or a governance gate is reached.

The remaining likely live blockers are governance-owned: Demo acceptance authority (`GD-03`), approved UAT thresholds (`GD-04`), independent-confirmer authority (`GD-05`), data compatibility acceptance for a schema-changing tuple (`GD-06`), and rollback-drill authority (`GD-07`). Each has a fail-closed path and must not be bypassed.

No dependency requires Production to be built first. The UAT work is specifically intended to resolve the reusable release-control risks before Production cost and blast radius are introduced.

## 9. New-Session Handoff

The new session should begin with this exact operating sequence:

1. Read and complete the repository BOOTSTRAP sequence only after Founder authorization.
2. Occupy INST-010 Platform IT Expert, Skill 17, and load this plan plus the current canonical GOAL-006 deployment files listed in Section 6.
3. Ask: **"This would begin writing implementation code. Do you authorize this for the current session?"**
4. After explicit authorization, inspect current `main`, the selected Work Contract/IB item, the governance dependency register in Section 8.1, Azure identity/configuration prerequisites, and the UAT live baseline.
5. Execute WC-1, WC-1A, WC-2 through WC-4, WC-4A, and WC-5 through WC-8 on the implementation branch; open the implementation PR and wait only for the required Founder merge decision.
6. After Founder merge and successful exact-main CI, execute WC-9 and WC-10; complete WC-11 using the `GD-11` evidence publication model.
7. Stop only for a genuine constitutional blocker, missing source acceptance/rollback evidence, unsafe Terraform replacement/deletion, unapproved rollout thresholds, unavailable required authority, a falsified engineering decision, or a required Founder decision.
8. Keep Production plan-only and untouched throughout this component.

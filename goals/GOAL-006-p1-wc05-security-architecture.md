# GOAL-006 P1-WC05 Security Architecture And Threat Model

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-007 — Security Architect |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-007-01 |
| `record_type` | Contribution Record |
| `go_authorization` | GOA-GOAL-006-INST-007-01 |
| `acceptance_record` | ACC-GOAL-006-INST-007-01 |
| `work_component` | P1-WC05 — Security Architecture And Threat Model |
| `produced_at` | 2026-08-13T10:27:49Z |
| `source_commit` | `1a3c6b10b36f9f34c10ebfe1663509a9e7f8f153` |
| `status` | ACCEPTED — R-111 / CR-GOAL-006-INST-004-01 |
| Constitutional basis | Constitution Articles IX and X; AD-001 through AD-004 and AD-008 through AD-010; ADR-003, ADR-007, ADR-008, ADR-014 |
| Accepted dependencies | P1-WC01 through P1-WC04; CT-02; R-107 through R-110 |

## Authority And Evidence Boundary

GOA-GOAL-006-INST-007-01 authorizes security architecture for identity, OIDC, RBAC,
network boundaries, TLS, secret custody, supply-chain controls, break glass, threats, and
security testing. This contribution preserves PA-01 through PA-08 and the accepted component
topology. It does not decide data recovery, service sizing, cost, product behavior, or API shape.

It defines requirements, not deployed effectiveness. It grants no authority for implementation,
credentials, provider queries, cloud creation, DNS, deployment, production, Platform Operations
activation, PR approval, or merge. Residual risks are identified, not accepted. Phase 2 and Phase 3
remain separately gated.

| Classification | Meaning |
|---|---|
| `ACCEPTED_DESIGN` | Independently accepted predecessor decision preserved here. |
| `RECORDED_RESULT` | Result reported by an accepted record but not rerun here. |
| `DESIGN_REQUIREMENT` | Required control whose implementation remains unverified. |
| `UNVERIFIED` | No authorized live Azure, GitHub, GHCR, DNS, certificate, credential, or runtime query supports a current-state assertion. |
| `CONFLICT` | Records require explicit reconciliation before implementation. |

## Evidence And Reuse Ledger

| Evidence | Reviewed identity | Current persisted SHA-256 | Use |
|---|---|---|---|
| P1-WC01 inventory | Review hash `ae0eb22b9fddf98a3c255aa5fdf751453bbf1a8a470faa12796cee346959a9c5` | `0382d13b1ba9a7bd3c69eebc08a04542074ad0cfcb934ff15b2571cebcf06464` | `ACCEPTED_DESIGN` / `RECORDED_RESULT` |
| P1-WC02 outcomes | Review hash `808ede6a6e79a95070b647b5dceec5c2077ba6780a9901a042e47c4dfc048278` | `d107465140716d78fd6980c91e3a9fabb172b009a6a597c03b47e03dc03d43ab` | `ACCEPTED_DESIGN` |
| P1-WC03 platform architecture | Review hash `1bed5e13333b3b2b2c5b11a2ee1d13c903e12a0e4c815963c6d1a605b732b303` | `3c01b01a6bfd786ee717fa29544774853b98105c9ac7e88c5395b52da26b81da` | `ACCEPTED_DESIGN` |
| P1-WC04 component topology | Review hash `0ad00d789893f9d526a971edd6570e8da459733108a08eb68afb37de7052c914` | `6a1622c28bbf4853e0190cc6e24d8438f80e41a72b6fb3ffca21b0a636049b2a` | `ACCEPTED_DESIGN` |
| CT-02 scope decision | Review/current hash `25d40fa2d00a66b4e777955e324e2f7f5c7acffc729dcb958ea65e728fbb7bd2` | Same | `ACCEPTED_DESIGN` |
| ADR-009 / 010 / 012 / 013 / 014 / 027 | Hashes `566b0643…`, `90364de2…`, `0c058af0…`, `c34b5c3e…`, `2014c377…`, `eec39130…` | Verified at contribution time | Partial control reuse |
| ADR-003 / 007 / 008 | Accepted architecture; no hash pinned by predecessor records | Not newly asserted | Tenant identity, CE mTLS, Keycloak |
| Live platform state | No authorized query | N/A | `UNVERIFIED` |

Review hashes identify the exact content reviewed. Current hashes differ where acceptance metadata was
subsequently added; that metadata change does not rewrite the reviewed decision.

## Conflict Ledger

| ID | Conflict or accepted boundary | Security treatment |
|---|---|---|
| CF-01 | PA-01 through PA-08 are accepted. | Preserve environment isolation, durable foundations, OIDC, digest promotion, OTel, and safe JIT behavior. |
| CF-02 | Web, BP, and PR are public candidates; CE, AIR, data, Temporal, Redis, Ollama, and internal tools are private. | Preserve classes; Billing Engine is private. |
| CF-03 | Current Terraform exposes Keycloak; older design treats it as internal. | Customer login may use controlled ingress; admin, management, metrics, and direct container surfaces remain private. |
| CF-04 | ADR-014 documents CI client secrets; PA-03 requires OIDC. | PA-03 controls GOAL-006; long-lived Azure deployment credentials are prohibited. |
| CF-05 | Older fixed certificate/secret intervals conflict. | Use provider-managed certificate rotation and owner-approved secret policy; do not inherit an unsupported calendar. |
| CF-06 | Older material relies on forwarded customer JWTs for service auth. | Require workload authentication plus validated delegated context; customer JWT alone is insufficient. |
| CF-07 | ADR-007 requires ACA-managed CE peer mTLS. | No manual CE certificates, cert-manager, or mesh without a new accepted decision. |
| CF-08 | ADR-006 keeps tenant rate limits in applications; GOAL-006 requires WAF justification. | WAF at public edge; tenant-aware limits remain in BP/PR. |
| CF-09 | CT-01 port mismatch and CT-05 missing Temporal health declaration. | Future Phase 2 blockers; no Phase 1 runnable edit. |
| CF-10 | Live cloud/runtime state is unknown. | Deployment-effectiveness assertions remain `UNVERIFIED` until authorized qualification. |

## Security Architecture Decisions

### SA-01 — Environment And Identity Isolation

Demo, UAT, and Production require distinct Terraform state and apply identities, GitHub deployment
Environments and OIDC subjects, Azure deployment/runtime managed identities, vault boundaries,
Keycloak clients/configuration, service/provider credentials, certificate bindings, and access
evidence. Non-production authority cannot mutate Production, and Production credentials or customer
data cannot be copied down.

### SA-02 — Customer Identity And Authorization

Keycloak 25.0.6 remains the sole broker for web customer identity. Services validate asymmetric
signature, issuer, audience, time constraints, subject, and required tenant context. `tenant_id`
comes only from validated authentication context and is propagated to PostgreSQL RLS through
`SET LOCAL app.tenant_id`; request data never establishes tenant authority.

Claims are not complete authority. Consequential actions also resolve current relationship, role,
contract, lifecycle, scope, and Decision Space from authoritative stores. Authorization occurs before
existence or policy detail is disclosed.

### SA-03 — Keycloak Boundary

Only the approved customer authentication surface may traverse public ingress. Administration,
management, metrics, health detail, database access, and direct Container App endpoints remain
private. Administration requires separate strong operator identity, private access, least privilege,
time-bounded authority, and audit evidence. Realm/config changes are version-controlled and promoted
through environments. Recovery details remain P1-WC06/P1-WC09 dependencies.

### SA-04 — GitHub Actions To Azure OIDC

Every Azure deployment uses environment-specific GitHub Actions OIDC federation. Long-lived
`AZURE_CREDENTIALS_*`, Azure client secrets, reusable Azure-login PATs, and credentials in Terraform
variables are prohibited. Trust is restricted to GitHub's issuer, approved audience, WAOOAW
repository, exact deployment Environment, and approved ref/workflow constraints. Only the deployment
job receives `id-token: write`; untrusted pull-request and build/test jobs receive no Azure token.

### SA-05 — Least-Privilege RBAC

| Identity | Required authority | Prohibited |
|---|---|---|
| Build/test | Build and attest packages | Azure mutation; Production secrets |
| Environment plan | Read bounded state/config and plan | Apply, role assignment, secret values, cross-environment mutation |
| Environment apply | Mutate approved resources in one environment | Subscription Owner, cross-environment access, arbitrary delegation |
| Bootstrap | Create approved state/federation/security prerequisites | Routine deployment, application secrets, standing use |
| Runtime identity | Named workload dependencies and secret references | Control-plane deployment, state, other workload secrets |
| Identity admin | Bounded private Keycloak administration | Azure/state/unrelated-vault authority |
| Security observer | Read posture, logs, alerts, cert/access evidence | Mutation or secret-value retrieval |
| Operations candidate | None until independent acceptance and Founder activation | Assumed live authority |
| Break glass | JIT emergency scope under SA-13 | Routine automation or daily use |

Role-assignment authority is isolated from deployment authority. No identity receives `Owner` for
convenience.

### SA-06 — Service Authentication And Delegation

Network location is not authentication. BP and PR calls to CE require ACA-managed mTLS, approved
workload identity, audience, operation, and delegated actor/tenant context where applicable. CE
validates both workload and delegation. Every internal service uses distinct least-privilege identity
or credentials and independently validates caller, environment, audience, purpose, and operation.
Shared superuser credentials, shared service certificates, and cross-environment credentials are
prohibited. Browser access to private components is denied by network and application policy.

### SA-07 — Ingress, WAF, Rate Limits, And Emergency Stop

The logical path is managed public edge/WAF to environment ingress, then Web, approved BP/PR public
operations, and Keycloak login; all later hops are private and authenticated. Direct public Container
App endpoints are prevented once the edge is active.

WAF supplies exploit, protocol-anomaly, bot, and coarse source-abuse controls. Authenticated
actor/tenant limits remain in BP/PR. Emergency Stop is excluded from ordinary challenges, tenant
quotas, commercial limits, and rate limits. Its pre-warmed path remains available during API
saturation and control pressure. Any protocol-denial control on that path must prove it does not
breach the constitutional latency floor. Exact edge product and cost remain protected decisions.

### SA-08 — Private Communication And Egress

Non-public components use private discovery and ingress. Outbound access is default-deny and
allowlisted by workload and purpose: AIR to approved model/tool endpoints, Keycloak to activated
identity providers, deployment jobs to approved Azure/GitHub/GHCR/state/evidence endpoints, and
applications to named dependencies/providers. Caller-supplied destinations are prohibited. DNS/IP
revalidation, redirect controls, and private/link-local rejection prevent SSRF and DNS rebinding.

### SA-09 — Constitutional Engine mTLS

Cloud BP/PR-to-CE traffic uses ACA-managed peer mTLS under ADR-007. CE permits approved workloads and
operations only. Development's exception is not cloud evidence. Platform-managed rotation,
unauthorized-caller rejection, invalid-peer behavior, and recovery require qualification. CE auth or
response failure causes governed work to fail safe; plaintext fallback and bypass are prohibited.

### SA-10 — TLS, DNS, And Certificates

Public endpoints require managed TLS. The reference TLS 1.3 target must be validated against the
selected service; compatibility changes need Security review. Founder owns domains, hostnames, DNS,
and Production activation; INST-007 owns policy and validation; authorized Platform work owns IaC;
activated Operations owns renewal response. Private keys never enter GitHub secrets, Terraform
state, images, logs, or workstations. Managed renewal is monitored for issuance, chain, hostname,
issuer, rotation, and expiry failure. No hostname or DNS action is authorized here.

### SA-11 — Secrets, State, And Bootstrap

Each environment has isolated secret custody. Workloads use managed identity and Key Vault
references. Secret values are prohibited from Terraform inputs/state/plans/outputs/logs, source,
configuration, images, SBOMs, attestations, workflow artifacts/caches/summaries, public health,
errors, and telemetry.

Remote state requires environment separation, locking, encryption, version/recovery controls,
restricted networking, least-privilege RBAC, access logging, and no runtime access. Bootstrap uses a
separately authorized constrained OIDC identity, emits references only, hands off after deterministic
verification, and is then removed, disabled, or reduced. Rotation occurs on compromise, authority
change, provider/crypto requirement, or approved schedule, with prompt old-authority revocation.

### SA-12 — Supply Chain And Promotion

OCI digest is release identity. The manifest binds source commit, every component digest including
Billing Engine, trusted build identity, SBOM, provenance, signature, required scans, tests/CCTs,
reviewed configuration, and promotion/rollback history. Build once; promote the same digest.

Promotion fails closed for digest mismatch, invalid/missing signature/provenance/SBOM/scan evidence,
untrusted builder, failed CCT/security gate, policy-violating vulnerability, omitted member, or
secret/unreviewed authority in configuration. Rollback selects a qualified digest and compatible
configuration, never a rebuild or mutable tag. Exact open formats and tooling are Phase 2 choices.

### SA-13 — Break Glass

Break glass requires a declared incident, exact environment/resource/operation/reason/duration,
independent approval separate from execution under a Founder-approved matrix, fresh strong auth,
dedicated emergency identity, JIT least privilege, immutable evidence, full session/control-plane
logging, immediate alerting, automatic expiry, revocation/session invalidation, exposure-driven
rotation, and independent post-event review.

Where delay would violate a Constitutional Floor, a pre-authorized emergency path may perform only
the minimum stop or containment action. It cannot enable routine deployment, evidence deletion,
authority expansion, or unrestricted secret access. Exact Production approvers remain protected.

### SA-14 — OAuth Vault Under CT-02

**Decision: exclude OAuth Vault from the GOAL-006 baseline release.** MCP services and their external
OAuth integrations are excluded, and no accepted baseline caller requires OAuth Vault. Deploying an
unused credential service would add custody risk, cost, recovery burden, and attack surface.

ADR-021 remains controlling when a future authorized integration requires server-side token custody.
That change needs separate scope, callers, mTLS, encryption, tenant binding, refresh/revocation,
recovery, threat tests, cost, and manifest membership. Tokens may not fall back to BP, PR, AIR,
Terraform, GitHub secrets, browser storage, logs, or ordinary ungoverned secret locations. Billing
Engine remains mandatory, private, and authenticated.

## STRIDE Threat Register

| ID | Asset/boundary and threat | Required control | Detection and test | Residual risk / owner |
|---|---|---|---|---|
| TH-01 S | Browser/Keycloak identity forgery, replay, mis-linking | Full JWT validation, provider binding, short sessions, proof-of-control linking | Invalid algorithm/issuer/audience/time and linking abuse tests | Provider/Keycloak compromise; INST-007, then P1-WC09 activated identity operator |
| TH-02 S | Untrusted workflow obtains Azure token | Exact OIDC subject/audience/environment and deploy-only token | Negative federation and revocation matrix | Provider/control-plane compromise; INST-007 + INST-009 |
| TH-03 S/E | Service impersonation/confused deputy | mTLS, workload allowlist, audience/operation/delegation validation | Unauthorized workload, audience, tenant, purpose tests | Allowed workload compromise; INST-007 + P1-WC07 component owners |
| TH-04 T | Digest/manifest/SBOM/signature substitution | Digest promotion, attestations, trusted builder | Tamper and mutable-tag denial tests | Builder compromise; INST-007 + INST-009 + QA |
| TH-05 T/I | Terraform state tamper or secret leakage | Isolated locked state, RBAC, recovery, no secret values | Access, lock, recovery, leak tests | Privileged cloud compromise; INST-007/009/006 |
| TH-06 T/R | Evidence altered, deleted, omitted, or late | CE-only authority, append-only DB, Evidence First, fail safe | CCT-EF, UPDATE/DELETE denial, CE failure | Privileged DB/control plane; INST-005 CE owner + INST-007 + INST-002 |
| TH-07 I/E | Tenant/relationship substitution | JWT tenant anchor, authoritative relationship, RLS, anti-enumeration | Cross-tenant API/DB/cache/export/delegation tests | Mapper/RLS error; INST-007 + INST-006 + P1-WC07 component owners |
| TH-08 I | Secret leakage | Managed identity, per-secret access, references, scanning/redaction | Canary scans across state/image/log/artifact/health | Runtime/vault admin compromise; INST-007 + P1-WC07 workload owners |
| TH-09 I | Keycloak admin exposure | Private admin, strong auth, JIT, separate credentials | Reachability denial, role/session expiry | Zero-day/admin misuse; INST-007, then P1-WC09 activated identity operator |
| TH-10 I/E | AIR SSRF/exfiltration | Default-deny egress, revalidation, specific credentials | Private IP, redirect, rebinding, provider tests | Provider compromise; INST-007 + P1-WC07 AIR owner |
| TH-11 D | Public exploit/bot/resource abuse | WAF, source and tenant limits, scaling/cost controls | WAF, fairness, saturation, recovery | Provider-scale attack; INST-007 + INST-009 |
| TH-12 D | Stop delayed by controls or outage | Dedicated path, challenge/quota exclusion, capacity isolation | Stop under API/WAF/provider/CE pressure | External network outage; INST-007 + P1-WC07 PR/CE owners + P1-WC08 QA |
| TH-13 D | CE exhaustion | Private ingress, authenticated callers, per-caller controls, fail-safe halt | Unauthorized flood, dependency-loss, no-bypass | Shared dependency failure; INST-005 CE owner + INST-009 |
| TH-14 E | Cross-environment or excessive Azure RBAC | Separate scoped plan/apply/runtime identities | RBAC negative and cross-environment matrix | Tenant admin compromise; INST-007 + INST-009 |
| TH-15 E/R | Standing or repudiated break glass | Independent approval, JIT, logs, expiry, revocation/review | Invalid activation, over-scope, expiry/revocation | Approved actor abuse; Founder matrix + INST-007 |
| TH-16 T/I | DNS/certificate hijack or failed renewal | Founder DNS control, managed certs, monitoring | Unauthorized change, mismatch, expiry, rotation | Registrar/CA compromise; Founder + INST-007 + P1-WC09 activated operator |
| TH-17 T/E | Billing omitted/exposed or forged | Mandatory manifest, private ingress, authenticated delegation | Membership, public denial, purpose/version tests | Implementation unknown; INST-007 + P1-WC07 Billing owner |
| TH-18 E/I | Unneeded OAuth Vault or unsafe token fallback | Baseline exclusion and forbidden fallback | Manifest absence and secret-location tests | Future integration undesigned; INST-007 + separately authorized future integration owner |

## Constitutional Security Coverage

| Obligation | Architectural guarantee |
|---|---|
| Override and Emergency Stop | Independent pre-warmed path, free of ordinary auth step-up, WAF challenge, quota, commercial state, and provider dependency. |
| Evidence First | No governed success before durable CE evidence; timeout and invalid response fail safe. |
| Audit immutability | Database-layer append-only enforcement; incident, rollback, shutdown, and break glass cannot rewrite evidence. |
| Audit/appeal rights | Tenant-bound evidence access and privacy-safe denial correlation preserve independent review. |
| Data portability and export | Export is tenant-bound, authorized, integrity-verifiable, privacy-safe, and cannot silently omit constitutional evidence; P1-WC06 defines data mechanics and P1-WC08 proves isolation. |
| Immediate engagement termination | Termination revokes active sessions, delegated authority, scheduled work, and new governed execution without deleting evidence; P1-WC07 implements and P1-WC08 validates. |
| Professional identity continuity | Environment promotion, rollback, recovery, and identity-provider change cannot silently merge, replace, or reassign a professional identity; INST-007 defines identity binding and P1-WC08 validates continuity. |
| Continuing appeal availability | Security denial, halt, rollback, recovery, and account restriction preserve privacy-safe decision basis and evidence access for independent review; P1-WC09 defines operations and P1-WC08 validates. |
| Transparency of current authority | Authenticated actors can obtain a privacy-safe statement of their current role, scope, restrictions, and governing source; identity alone never implies authority. P1-WC07 implements and P1-WC08 validates. |
| Tenant/ledger isolation | JWT tenant anchor, authoritative relationships, RLS, environment separation, anti-enumeration. |
| Authority licensing | Identity never implies Decision Space or current role authority. |
| Floor enforcement | Middleware, network, identity, database, and pipeline gates, not endpoint convention. |
| Platform neutrality | Exceptions require independent approval and evidence; commercial pressure cannot bypass controls. |
| Conflict disclosure | CF-01 through CF-10 and all `UNVERIFIED` states are explicit. |
| Observability | Redacted security/constitutional telemetry binds environment, service, digest, and opaque correlation. |

## Security Test And CCT Matrix

| Test | Required proof | Gate effect |
|---|---|---|
| CCT-G006-SEC-01 | Unapproved repo/ref/fork/workflow/audience/environment gets no Azure token; no long-lived deployment credential exists. | Blocks Phase 2/3 |
| CCT-G006-SEC-02 | Plan/apply/runtime/observer/bootstrap/break-glass identities cannot exceed scope. | Blocks qualification |
| CCT-G006-SEC-03 | Every private component is unreachable publicly. | Blocks promotion |
| CCT-G006-SEC-04 | CE rejects invalid peer, workload, audience, operation, and delegation. | Blocks CE acceptance |
| CCT-G006-SEC-05 | Invalid JWT properties fail without enumeration. | Blocks public API |
| CCT-G006-SEC-06 | Tenant/relationship substitution reveals no rows, counts, timing, export, mutation, or success. | Blocks release |
| CCT-G006-SEC-07 | Keycloak login uses approved ingress; admin/management remain private. | Blocks identity acceptance |
| CCT-G006-SEC-08 | TLS hostname/chain/issuer/policy/renewal/rotation/alerts pass per approved hostname. | Blocks qualification |
| CCT-G006-SEC-09 | State, plans, logs, artifacts, images, SBOM, health, and telemetry contain no secrets; unauthorized access fails. | Blocks Phase 2 |
| CCT-G006-SEC-10 | Manifest signature, provenance, SBOM, scans, membership, and digest verify; tampering fails. | Blocks promotion |
| CCT-G006-SEC-11 | All environments and rollback use approved identical digests without rebuild. | Blocks UAT/Production |
| CCT-G006-SEC-12 | WAF/rate controls contain abuse without delaying Stop under saturation/failure. | Constitutional blocker |
| CCT-G006-SEC-13 | Egress denies private/link-local, redirect, rebinding, arbitrary URL/provider, and cross-environment credentials. | Blocks provider activation |
| CCT-G006-SEC-14 | Invalid break glass fails; valid elevation expires, revokes, records, and triggers review. | Blocks Production |
| CCT-G006-SEC-15 | Billing Engine is in manifest, private, and rejects unauthorized caller/purpose/version. | Blocks release |
| CCT-G006-SEC-16 | OAuth Vault and MCPs are absent; forbidden token locations are empty. | Blocks scope expansion |
| CCT-G006-SEC-17 | CT-01 repaired to the accepted CE endpoint/port with authenticated contract test. | Phase 2 blocker |
| CCT-G006-SEC-18 | CT-05 repaired with accepted Temporal health/dependency-loss behavior. | Phase 2 blocker |
| CCT-G006-SEC-19 | CE evidence failure prevents success; ledger UPDATE/DELETE denied. | Constitutional blocker |
| CCT-G006-SEC-20 | Cross-environment identity/state/vault/Keycloak/provider/DNS access denied. | Blocks qualification |
| CCT-G006-SEC-21 | Certificate, secret, OIDC, workload, and signing rotations preserve service and revoke old authority. | Blocks handover |
| CCT-G006-SEC-22 | Telemetry/errors contain no JWT, secret, raw protected identifier/payload, provider body, state URI, or topology detail. | Blocks observability |
| CCT-G006-SEC-23 | Tenant-authorized export is complete, integrity-verifiable, isolated, privacy-safe, and includes required constitutional evidence without cross-tenant disclosure. | Blocks portability acceptance; INST-006/P1-WC08 |
| CCT-G006-SEC-24 | Engagement termination revokes sessions, delegated authority, scheduled work, and new execution while retaining immutable evidence. | Constitutional release blocker; P1-WC07/P1-WC08 |
| CCT-G006-SEC-25 | Promotion, rollback, recovery, and identity-provider change preserve professional identity without merge, replacement, or reassignment. | Blocks identity/recovery acceptance; INST-007/P1-WC08 |
| CCT-G006-SEC-26 | Denial, halt, rollback, recovery, and account restriction retain privacy-safe decision basis and evidence access for continuing appeal. | Blocks operational handover; P1-WC08/P1-WC09 |
| CCT-G006-SEC-27 | An authenticated actor can retrieve current role, scope, restrictions, and governing source without secret or cross-tenant disclosure. | Blocks authority-transparency acceptance; P1-WC07/P1-WC08 |

P1-WC08 must consolidate identifiers and avoid duplicate execution while preserving every proof.

## Phase 2 Implementation Blockers

| Blocker | Required closure evidence |
|---|---|
| P1-R02 credential-secret Azure login | OIDC definitions, environment identities, RBAC/negative tests, old-credential revocation plan |
| P1-R03 / CT-06 secret-bearing Terraform/config | Key Vault references, leakage tests, distinct identities, plaintext removal |
| P1-R04 mutable promotion/no attestations | Signed digest manifest and tamper tests |
| P1-R06 / CT-03 / CT-04 absent boundaries | Public/private topology, WAF decision, CORS, private admin/internal reachability, denial tests |
| CT-01 CE port mismatch | Phase 2 repair and authenticated contract test |
| CT-05 Temporal health absent | Phase 2 health semantics and dependency-loss test |
| Billing absent from five-image release | Build, scan, attest, manifest, private deployment, integration proof |
| OAuth Vault conditional scope | Closed by SA-14 baseline exclusion; prove absence |
| State/bootstrap authority absent | Bootstrap/backend controls, handoff/revocation, lock/recovery tests |
| Delegation unverified | Workload, audience, purpose, operation, tenant/relationship/version negative tests |
| Break-glass authority matrix absent | Founder-approved matrix and expiry/revocation test |
| DNS/certificate config absent | Approved hostnames/authority/design/monitoring/qualification |
| Signing/vulnerability policy open | Approved formats, exception authority, retention, revocation |
| P1-R10 / CT-07 live state unknown | Authorized Phase 3 qualification; repository work cannot close it |

No blocker authorizes its own repair.

## Protected Decisions And Unknowns

Founder retains public hostnames and DNS change, cloud expenditure, Production promotion/activation,
Production OIDC approvers and break-glass matrix, protected residual-risk acceptance, Platform
Operations activation, Phase 2 authorization, PR approval, and merge. INST-009 recommends the edge
product and platform mechanism; INST-006 owns recovery/retention recommendations; INST-005 owns API
and component health semantics.

Live Azure identities/RBAC/network/vaults, GitHub Environments/OIDC/secrets, GHCR artifacts and
attestations, DNS/certificates, Keycloak realm/config/exposure, CE mTLS/delegation, and endpoint state
are `UNVERIFIED`. WAF product/cost, signing/SBOM formats, vulnerability exceptions, evidence
retention, break-glass actors/duration, numeric security SLOs, rotation schedules, and operational
response targets remain unresolved or downstream decisions. No live customer, provider, cloud-cost,
deployment, or Production-readiness proof exists here.

## Completeness Ledger

| Obligation | Status |
|---|---|
| Authority, evidence semantics, reuse, conflicts | COMPLETE FOR CONTRIBUTION |
| Identity, OIDC, RBAC, Keycloak, service auth, CE mTLS | COMPLETE AS DESIGN |
| Ingress, egress, private communication, WAF/rates, Stop | COMPLETE AT SECURITY BOUNDARY |
| TLS, DNS, certificates, secrets, state, bootstrap | COMPLETE AS DESIGN |
| Supply chain, break glass, OAuth Vault, Billing | COMPLETE AS DESIGN |
| Threat register and Constitutional Floor coverage | COMPLETE FOR P1-WC05 |
| Security/CCT matrix and implementation blockers | COMPLETE FOR P1-WC05 |
| Live implementation or Production readiness | NOT ESTABLISHED |
| Independent review and acceptance | NOT PERFORMED |

## Contribution Record

| Field | Value |
|---|---|
| Contribution | CR-GOAL-006-INST-007-01 |
| Materiality | M2 — specialist security architecture contribution |
| Decision | Complete at design level and submitted for independent review |
| Security verdict | DESIGN REQUIREMENTS DEFINED; IMPLEMENTATION AND LIVE EFFECTIVENESS UNVERIFIED |
| Residual risk | IDENTIFIED, NOT ACCEPTED |
| Implementation/cloud/DNS authority | NOT GRANTED |
| Self-review | NOT PERFORMED |
| Required review | Independent architecture coherence and Constitutional Floor validation |
| Downstream effect if accepted | Satisfies P1-WC05 dependency for P1-WC06 only; does not unblock Phase 2 or Phase 3 |

# WC-091 - Environment Readiness And Data Continuity

**Office:** Solution Architect (INST-005), with one combined owner review and repair round
**Assigned by:** Founder instruction, 2026-09-11
**Status:** OWNER-REVIEWED - CONDITIONAL PASS - EA AMENDMENT BLOCKS I1 - IMPLEMENTATION UNAUTHORIZED
**Delivery unit:** One environment-readiness component delivered through three independently gated iterations
**Controlling contract:** `architecture/reference/components/environment-readiness-and-data-continuity.md`
**Predecessors:** WC-076, WC-077, WC-085, WC-086 and WC-090
**Constitutional basis:** C-001, C-023, C-026, C-059, C-065, C-066, C-067, C-071, C-076, C-079, C-080

## Authority And Scope

WC-091 authorizes Solution Architecture planning, direct repair of small and manageable planning
findings, one combined edit-mode owner review, author validation, registry reconciliation, and one
planning PR for Founder review. It does not authorize runnable source, migration, Terraform,
workflow, secret, cloud, DNS, provider, customer-traffic, Production, approval, or merge changes.

Implementation requires a later Platform IT Expert session with explicit current-session Founder
authorization. Production remains plan-only and separately authorized. A Work Contract, accepted
plan, issue, label, clear platform gate, or merged planning PR is not implementation authorization.

## Objective

Restore truthful Demo identity and deployment readiness without pretending that disposable Demo data
is durable, then introduce persistent PostgreSQL and recovery in UAT, and only then qualify a dark
Production control plane. Replace scattered secret exceptions with one versioned environment
configuration and secret dependency contract shared by preflight, Terraform, workloads, and
independent verification.

## Iterations

### WC091-I1 - Disposable Demo Readiness

- Keep Demo data synthetic and disposable. The Demo database has no persistence, backup, restore,
  migration-continuity, or customer-data claim and resets on revision replacement or restart.
- Restore the anonymous identity-provider projection without constructing mutation-only cryptographic
  dependencies.
- Introduce a versioned, domain-separated identity HMAC key ring before any durable customer identity
  data exists.
- Define one machine-readable secret catalog and idempotent no-echo provisioning path for generated
  and externally supplied secrets.
- Separate configuration readiness, provider redirect readiness, and real-user acceptance evidence.
- Keep UAT, Production, DNS activation, and customer traffic out of scope.

### WC091-I2 - UAT Persistent Data And Promotion Qualification

- Provision isolated PostgreSQL for UAT with separate databases and least-privilege roles.
- Run expand-only migration before traffic and prove compatible rollback to the previous qualified
  release tuple.
- Prove backup, point-in-time recovery, isolated restore, data continuity across revision restart,
  and environment isolation.
- Consume the UAT identity manifest through the same validated runtime path as Demo.
- Split credentials by principal and purpose; qualify managed-identity and Key Vault bindings.
- Use Temporal Cloud under ADR-015 and remove UAT-local database sidecars.

### WC091-I3 - Dark Production Readiness

- Under separate Founder authorization for I3, produce deterministic plan-only specifications and
  gate results for the protected Production deployment, verification, and acceptance environments;
  do not create or mutate those environments or any Production resource.
- Plan the Production PostgreSQL sizing, HA, PITR, RPO/RTO, migration compatibility, rollback, and
  cross-environment denial controls without executing an apply, restore drill, or customer traffic.
- Render and validate the Production manifest through the common contract offline, proving exact
  configuration and release digests without runtime or provider-readiness claims.
- Keep Production apply, control-plane creation, DNS activation, traffic, recovery execution, and
  final acceptance separately Founder-reserved and outside WC-091.

## Required Inputs

| Input | Required state |
|---|---|
| WC-091 controlling component contract | Owner-reviewed and Founder-accepted exact revision |
| Demo disposable-data exception | Accepted amendment to `architecture/reference/pipeline/azure-deployment-topology.md` replacing Demo PostgreSQL Flexible Server with the exact WC091-I1 disposable ACA design; the amendment requires Enterprise Architecture authorship and Founder acceptance before I1 implementation |
| Identity HMAC lifecycle | Security and Data acceptance of key versions, domains, lookup continuity, and retirement |
| PostgreSQL contract | Data, Security, and Platform acceptance before WC091-I2 implementation |
| Environment control plane | Demo/UAT: protected GitHub environments, exact OIDC subjects, Key Vault, state, runner, DNS, cost, and denial evidence for the selected environment. Production: plan-only expected-state manifests and gate specifications; no resource creation or mutation under WC-091 |
| Provider credentials | Entered directly through the approved no-echo Key Vault path; never supplied through chat, Git, workflow input, Terraform state, logs, or artifacts |
| Implementation authority | Explicit Founder authorization in each implementing session |

## Definition Of Done

- [ ] The controlling contract has no unresolved owner finding or invented implementation behavior.
- [ ] WC091-I1 proves Demo configuration and identity readiness while describing Demo data as
      disposable and synthetic, never durable or production-like.
- [ ] WC091-I2 proves UAT persistence, migration, rollback, PITR, isolated restore, and manifest parity.
- [ ] WC091-I3 produces deterministic plan-only Production control-plane, PostgreSQL, recovery,
      isolation, and manifest gate results without resource creation, apply, DNS, traffic, provider,
      recovery-execution, or acceptance authority.
- [ ] Every required secret is declared once and all consumers, preflight checks, provisioning,
      Key Vault references, RBAC, startup checks, rotation, and verification derive from that catalog.
- [ ] HMAC rotation preserves lookup continuity through explicit active-write and retained-read
      versions with domain separation and bounded retirement.
- [ ] Configuration readiness, provider readiness, and human acceptance are distinct results.
- [ ] Docker and rendered-plan tests prove assembled behavior rather than only source strings. All
  executable validation runs in repository-defined containers; host Python, virtual environments,
  and host dependency installation are prohibited.
- [ ] One final-head-bound planning PR passes applicable repository checks and author review and is
      submitted for Founder review without self-approval or self-merge.

## Stops

Stop rather than proceed when:

- an implementation session lacks explicit Founder authorization;
- the Demo disposable-data decision lacks Enterprise Architecture disposition;
- a secret value would enter Git, chat, a command argument, Terraform input/state, workflow output,
  log, screenshot, or retained artifact;
- HMAC rotation could make an existing identity unresolvable or merge identity domains;
- UAT lacks persistent PostgreSQL, migration rollback, PITR, isolated restore, or environment denial;
- Production lacks its protected control plane or separate Founder authorization;
- a readiness check would infer provider acceptance from configuration or redirect health;
- a failed gate would be bypassed, weakened, or converted into a warning;
- PR approval, merge, direct `main` mutation, or customer traffic would be required.

## Combined Owner Review And Repair

One edit-mode review round must cover Enterprise Architecture, Data Architecture, Security
Architecture, and Platform Architecture. Reviewers repair bounded findings directly in this Work
Contract and its controlling contract. They return one consolidated disposition; they do not create
serial handoffs. A finding that changes constitutional policy, accepts Production risk, or expands
scope remains a Founder decision rather than a reviewer repair.

**Combined review date:** 2026-09-11

| Decision space | Disposition | Repaired result or external prerequisite |
|---|---|---|
| Chief Enterprise Architect | `CONCUR WITH BLOCKER` | Three iterations are appropriate: disposable synthetic Demo, persistent recovery-qualified UAT, then plan-only dark Production. The current accepted topology still mandates Demo PostgreSQL Flexible Server, so this review cannot make the variance effective. I1 is blocked until Enterprise Architecture amends that topology with the exact disposable ACA design and the Founder accepts the amendment. |
| Data Architect | `CONCUR` | The controlling contract now fixes HMAC key/version persistence, domain/version columns, collision-safe reindex, database/role separation, EF migration ownership, additive compatibility, PITR, isolated restore, RLS, and restore acceptance. No small Data finding remains delegated. |
| Security Architect | `CONCUR` | The controlling contract now fixes domain separation, per-principal credentials, catalog-derived least privilege, no-echo handling, redaction, version overlap, compromise holds, cross-environment denial, and fail-closed identity behavior. No small Security finding remains delegated. |
| Platform Architect | `CONCUR WITH EA PREREQUISITE` | The proposed I1 design is feasible on ACA using replica-scoped ephemeral storage plus deterministic startup reset/reseed; manifest/catalog rendering, Key Vault references, PostgreSQL/Temporal handoff, preflight, rollback, and plan-only Production rejection are specified. Platform implementation remains blocked by the EA/Founder topology-amendment gate and separate session authorization. |

**Overall review status:** `CONDITIONAL PASS - EXTERNAL EA/FOUNDER AMENDMENT REQUIRED - IMPLEMENTATION UNAUTHORIZED`.
The only unresolved item is the true external prerequisite above. It is not delegated to an
implementer and no implementation, cloud action, Production action, independent assurance, or
Founder approval is claimed by these dispositions.

## Plan Author Review

**Status:** PASS for the repaired planning artifacts. Focused validation completed on 2026-09-11:
`git diff --check` passed, and 30 relevant deployment/identity pipeline tests passed in the
repository-defined Docker Compose Python test runner. No host language runtime, virtual environment,
or host dependency installation was used. The plan remains implementation-unauthorized, WC091-I1
remains blocked by the accepted-topology amendment, and Production remains plan-only and separately
authorized.

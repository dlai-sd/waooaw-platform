# GOAL-006 P1-WC07 Implementation And Pipeline Feasibility

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-010 — Platform IT Expert |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-010-01 |
| `record_type` | Feasibility Contribution |
| `go_authorization` | GOA-GOAL-006-INST-010-01 |
| `acceptance_record` | ACC-GOAL-006-INST-010-01 |
| `work_component` | P1-WC07 — Implementation And Pipeline Feasibility |
| `evidence_date` | 2026-08-13 |
| `repository_observation_point` | Commit `9227bd9` |
| `status` | ACCEPTED — R-113 / CR-GOAL-006-INST-004-02 |
| `implementation_authority` | NOT GRANTED |

## Authority And Evidence Boundary

INST-010 may assess prerequisites, implementation decomposition, deterministic Docker validation,
and feasibility. It may not change architecture or runnable files, install dependencies, access
credentials/providers, query or mutate cloud state, change DNS, spend, deploy, act in Production,
accept risk, activate operations, approve, merge, or self-review.

`VERIFIED` means directly observed repository or recorded command evidence; `DECLARED` means an
accepted design/configuration requires it but it was not executed; `UNVERIFIED` requires later
deterministic or live proof; `CONFLICT` blocks implementation acceptance; `PROTECTED` remains with a
named authority. Repository presence is not operational effectiveness. Host pytest collection below
is diagnostic only and is not a C-080-compliant test run.

## Accepted Inputs

| Input | Acceptance anchor |
|---|---|
| P1-WC03 platform architecture | R-109; review hash `1bed5e13333b3b2b2c5b11a2ee1d13c903e12a0e4c815963c6d1a605b732b303` |
| P1-WC04 topology | R-110; review hash `0ad00d789893f9d526a971edd6570e8da459733108a08eb68afb37de7052c914` |
| CT-02 release scope | R-110; hash `25d40fa2d00a66b4e777955e324e2f7f5c7acffc729dcb958ea65e728fbb7bd2` |
| P1-WC05 security | R-111; review hash `fdcd3bfd5547e1217a66b68ff901ef611838a276d30a2471b3a7b59807172e3e` |
| P1-WC06 data/recovery | R-112; review hash `839370dcd54ca48bd89a8ccb7a859120f7911887c08ae06889f11541673d2691` |

Any material Phase 2 change requires a Dependency Impact Report and applicable owner re-review.
C-059 spec-first/co-commit traceability remains mandatory.

## Feasibility Verdict

**Phase 2 is CONDITIONALLY FEASIBLE.** The accepted design can be implemented with the selected
Docker, GitHub Actions, GHCR, Terraform/AzureRM, Azure Container Apps, PostgreSQL/pgvector,
Keycloak, Temporal, OTel, .NET, Python, and Next.js stack. No requirement inherently demands an
unavailable replacement architecture.

It is not implementation-ready because deterministic Docker test collection, Terraform tooling,
mandatory Billing image membership/build entries, Docker-first workflows, OIDC, immutable manifests,
real rollback, secret-safe Terraform, Demo/UAT roots, CT-01 and CT-03 through CT-06, security/data
controls, and protected Production decisions remain open. These are closure gates, not technical
impossibility.

## Toolchain And Prerequisites

| Capability | Evidence | Status / required closure |
|---|---|---|
| Docker | `29.3.0`; Compose config exits 0 | `VERIFIED`; pin build/runtime images |
| Compose secrets | Six required values default blank | `CONFLICT`; validation must fail closed without committing real credentials |
| Python | Host `3.12.1` | `VERIFIED`, not test authority; Docker-only tests |
| Test collection | 1,701 collected; exit 2: missing `grpc`, `KeyError: WC012-01` | `VERIFIED DIAGNOSTIC FAILURE`; repair pinned test image/declarations |
| Node/npm | `24.14.0` / `11.9.0`; web declares Node 20/pnpm | `VERIFIED/DECLARED`; choose authoritative pinned runner |
| .NET | Host SDK `10.0.200`; projects declare .NET 9 | Use pinned .NET 9 build runner |
| Terraform | CLI missing | `VERIFIED BLOCKER`; pin Terraform >=1.7 container and provider lock |
| GitHub/Git | gh `2.88.0`; git `2.53.0` | `VERIFIED` |
| Environment roots | dev/prod present; Demo/UAT absent | `VERIFIED GAP` |
| Build entries | Source Dockerfile observed only for excluded OAuth Vault | `VERIFIED GAP`; add approved mandatory build entries |
| Scanning | Gitleaks, CodeQL, Trivy/dependency scans declared | `DECLARED`; pin and include Billing |
| SBOM/signature/provenance | Required, not implemented | `UNVERIFIED GAP` |
| Rollback | Workflow success path exists while rollback is TODO | `CONFLICT`; implement same-digest/config rollback |
| Azure/GHCR/DNS/runtime | No authorized live query | `UNVERIFIED`; Phase 3 proof only |

Command-derived values are durably recorded in ER-GOAL-006-INST-010-01 with normalized evidence
SHA-256 `c01c6d4fb9877e8770ccd1938f8801c2d02faa4e1e91ae87719ac77a9ae041d4`.

Blank Compose variables observed: `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD`,
`WHATSAPP_WEBHOOK_SECRET`, `IDENTITY_HMAC_KEY`, `WHATSAPP_TENANT_TOKEN_KEY`, and
`BP_SERVICE_JWT_SECRET`.

## Implementation Surface Feasibility

### Workflows And Compose

Existing workflow primitives for CI matrices, scanning, coverage, contract checks, and environment
gates are reusable after replacing host Python execution with pinned Docker runners; adding Billing
to build, scan, manifest, promotion, rollback, and qualification; removing invalid `tag-qa`
dependency; replacing mutable tags and `AZURE_CREDENTIALS_DEV` with digest authority and OIDC; and
turning pending verification/rollback into fail-closed executable checks.

Compose can support deterministic integration, but needs an accepted baseline profile excluding
OAuth Vault/MCPs, CE endpoint `5002`, Temporal health/dependency semantics, PgBouncer transaction
routing, deterministic non-secret fixtures, and proof cloud compositions do not inherit host exposure.

### Terraform And Containers

Terraform is feasible after introducing bootstrap/foundation/workload/policy modules and separate
environment roots/state identities; removing secret values/tokens/passwords from variables, plans,
state, and outputs; using least-privilege named identities; deploying manifest digests; adding Billing;
enforcing private/public boundaries; and testing JIT leases, forbidden secrets/public ingress,
cross-environment references, destructive plans, mutable tags, and missing members.

Formatting, parsing, initialization, validation, policy, and plan-shape tests can run without cloud
credentials in a pinned container. Apply/effectiveness remain Phase 3.

Mandatory CE, BP, PR, AIR, Web, and Billing images need approved Dockerfiles, pinned base images,
non-root minimal runtime stages, separated runtime/test dependencies, declared ports and health
probes, secret/cache exclusion, and one signed digest per member. Omitted or additional baseline
members fail the release gate.

## Docker-First Validation Architecture

```text
source tree -> pinned dependency/static runners -> service image builds
            -> isolated Compose integration -> migration/recovery fixtures
            -> security/data proof suites -> digest manifest/SBOM/provenance/signature/scans
            -> same-digest promotion eligibility
```

No virtual environment, host pip install, or host pytest. Python dependencies install from locked
authoritative inputs into pinned images. .NET, Node/pnpm, Terraform, policy, scanning, and signing use
pinned containers/actions. Local and CI invoke the same images/scripts. Fixtures are synthetic and
offline. Every result binds commit, digest, config, tool versions, and test IDs. Zero tests, missing
dependencies, skipped constitutional proofs, mutable images, omitted members, warning-based passes,
or pending rollback fail closed.

| Plane | Permitted | Prohibited |
|---|---|---|
| Local | Docker lint/unit/contract/integration, Terraform validation/policy, synthetic recovery | Host Python tests, credentials/providers/DNS/cloud mutation/Production data |
| CI | Same gates; build/scan/attest/sign; manifest and plan review | Long-lived Azure credentials, self-approval, mutable authority, skipped proof |
| Phase 3 cloud | Authorized apply, OIDC/RBAC negatives, boundaries, restore/DR, TLS/WAF/load/promotion | Per-environment rebuild, bypass, unapproved spend/DNS/Production |

## Proposed Phase 2 Work Components

These require Phase 1 closure, approved WCs, explicit current-session Founder implementation
authorization, GOA/Acceptance, C-059 traceability, and independent review.

| WC | Owner and scope | Outputs/tests | Rollback/prohibitions | Size |
|---|---|---|---|---|
| P2-WC01 | INST-010: deterministic runners and dependencies | Locked stack runners, import/collection/zero-test/tool-version parity | Revert to last passing runner digest; no host Python/venv/unpinned/provider calls | L/high |
| P2-WC02 | INST-010; INST-005 confirms: component builds/contracts | Six images, Billing membership, Compose baseline, CT-01/05/06, health/auth/pool tests | Restore declarations only; no business redesign/OAuth/MCP/public CE | XL/high |
| P2-WC03 | INST-010; INST-009/007 own design: Terraform identity/network/secrets/JIT | Roots/modules, OIDC/RBAC, boundaries/state/lease controls and policy negatives | Version rollback only; no cloud apply/credentials/DNS/secret values | XL/very high |
| P2-WC04 | INST-010; INST-006/007 own design: data/recovery | Additive migration, synthetic PITR, evidence tail/lifecycle/export/hold tests | Isolated fixture/forward fix; no Production data/objective/key/destructive migration | XL/very high |
| P2-WC05 | INST-010; INST-007 policy, QA proof: supply chain | Six-member manifest, SBOM/provenance/signature/scans/tamper verification | Prior qualified manifest; no mutable authority/unsigned/omitted Billing/included OAuth/MCP | L/high |
| P2-WC06 | INST-010; INST-009/007 owners: promotion/rollback/halt/cost/recovery | OIDC workflows, saved plans, same-digest promotion/rollback, leases/halt/cost tests | Qualified compatible tuple; no Phase 2 Azure action/self-confirmation/TODO success | XL/very high |
| P2-WC07 | INST-010 test author; independent QA accepts: complete proof suite | All SEC-01..27 and DATA-01..28 executable/non-skipped with proof ledger | Revert test code without weakening; no drop/skip/xfail/self-validation | XL/very high |
| P2-WC08 | INST-010; independent review: evidence package | Traceability, impacts, manifests, proof/scan evidence, Phase 3 gaps, reproducible PR | Withdraw/revert unmerged branch; no self-review/merge/live claims | M/medium |

| WC | Direct dependencies |
|---|---|
| P2-WC01 | Accepted Phase 1 package and explicit implementation authorization |
| P2-WC02 | P2-WC01; accepted topology/security/data contracts |
| P2-WC03 | P2-WC01; accepted Platform and Security architecture; protected tool/policy decisions |
| P2-WC04 | P2-WC01, P2-WC02; accepted Data/Security architecture |
| P2-WC05 | P2-WC01, P2-WC02; accepted supply-chain policy choices |
| P2-WC06 | P2-WC03, P2-WC04, P2-WC05; accepted promotion/recovery policy choices |
| P2-WC07 | P2-WC01 through P2-WC06; independent QA assignment |
| P2-WC08 | Independently accepted outputs of P2-WC01 through P2-WC07 |

## Complete Proof Mapping

| Security proofs | Phase 2 implementation owner |
|---|---|
| SEC-01 | WC03/WC06: OIDC negative subjects and no long-lived credential |
| SEC-02 | WC03: identity scope matrix |
| SEC-03 | WC03: private components unreachable publicly |
| SEC-04–06 | WC02/WC04: CE peer/delegation, JWT, tenant/relationship negatives |
| SEC-07–08 | WC03/WC06: Keycloak boundary and TLS lifecycle |
| SEC-09 | WC01/WC03/WC05: no secrets across artifacts/surfaces |
| SEC-10–11 | WC05/WC06: manifest integrity and same-digest promotion/rollback |
| SEC-12–14 | WC02/WC03/WC06: Stop under controls, egress, break glass |
| SEC-15–16 | WC02/WC05: Billing mandatory; OAuth/MCP absent |
| SEC-17–18 | WC02: CT-01 CE endpoint and CT-05 Temporal health |
| SEC-19–22 | WC02/WC03/WC04/WC06: Evidence First, environment isolation, rotation, redaction |
| SEC-23–27 | WC02/WC04/WC06: export, termination, identity, appeal, authority transparency |

| Data proofs | Phase 2 implementation owner |
|---|---|
| DATA-01–03 | WC02/WC04: RLS, pool reset, relationship scope |
| DATA-04–05 | WC04: destructive denial and evidence recovery |
| DATA-06–07 | WC03/WC04: lower-environment data and anonymization |
| DATA-08–11 | WC04: PITR/evidence tail/Keycloak/Temporal |
| DATA-12–13 | WC02/WC04: Redis and vector reconstruction |
| DATA-14–16 | WC03/WC05/WC06: state, GHCR, immutable recovery tuple |
| DATA-17–21 | WC04: migrations, deletion, hold, lifecycle replay |
| DATA-22–23 | WC04/WC05: export and secret exclusion |
| DATA-24–26 | WC04/WC06: measured recovery, termination, identity continuity |
| DATA-27–28 | WC02/WC04/WC03: Billing lineage and telemetry isolation |

P2-WC07 enforces identifier-level selection and completeness for all 27 security and 28 data proofs;
grouping above does not merge or drop any proof obligation.

**Security proof ledger:** `SEC-01`, `SEC-02`, `SEC-03`, `SEC-04`, `SEC-05`, `SEC-06`,
`SEC-07`, `SEC-08`, `SEC-09`, `SEC-10`, `SEC-11`, `SEC-12`, `SEC-13`, `SEC-14`,
`SEC-15`, `SEC-16`, `SEC-17`, `SEC-18`, `SEC-19`, `SEC-20`, `SEC-21`, `SEC-22`,
`SEC-23`, `SEC-24`, `SEC-25`, `SEC-26`, `SEC-27`.

**Data proof ledger:** `DATA-01`, `DATA-02`, `DATA-03`, `DATA-04`, `DATA-05`, `DATA-06`,
`DATA-07`, `DATA-08`, `DATA-09`, `DATA-10`, `DATA-11`, `DATA-12`, `DATA-13`,
`DATA-14`, `DATA-15`, `DATA-16`, `DATA-17`, `DATA-18`, `DATA-19`, `DATA-20`,
`DATA-21`, `DATA-22`, `DATA-23`, `DATA-24`, `DATA-25`, `DATA-26`, `DATA-27`,
`DATA-28`.

## Conflict And Prerequisite Ledger

| ID | Conflict and closure |
|---|---|
| CT-01 | AIR/OAuth CE `7000` versus accepted `5002`; WC02 + SEC-17 |
| CT-02 | Five-image CI omits Billing and includes excluded scope; six-member manifest + SEC-15/16 |
| CT-03 | Host-exposed dependencies/MCPs; baseline profile + WC03 private policy |
| CT-04 | Public Keycloak without login/admin split; WC03 + SEC-07 |
| CT-05 | Missing Temporal health/dependency semantics; WC02 + SEC-18 |
| CT-06 | Password configuration/direct DB clients conflict with secrets/PgBouncer; WC02–04 |
| CT-07 | Live state unknown; only authorized Phase 3 qualification can close |
| PREREQ-01 | Diagnose and correct the missing `grpc` dependency and `WC012-01` lookup failure in authoritative declarations; Docker collection then exits 0 |
| PREREQ-02 | Pinned Terraform and AzureRM lock accepted |
| PREREQ-03 | Approved build entries for all six mandatory images |
| PREREQ-04 | SBOM/provenance/signature/vulnerability/retention/revocation policy accepted |
| PREREQ-05 | Phase 2 WCs and explicit implementation authorization exist |
| PREREQ-06 | Independent QA and implementation reviewer assigned |

## Dependency And Recovery Feasibility

Python uses authoritative locked root test dependencies in pinned images; imports validate before
collection. Runtime/test dependencies remain separate. Node uses committed pnpm lock; .NET uses a
pinned .NET 9 SDK and selected package lock; Terraform uses a pinned image and provider checksums.
Base images, actions, scanners, and signing tools pin immutable revisions. Updates carry build,
security, license, behavior, and rollback evidence.

Synthetic Docker fixtures can prove additive migrations, destructive denial, RLS/pool reset,
encrypted backup/PITR chain logic, evidence-tail fail-safe, Keycloak reconciliation, Temporal pause/
idempotency, Billing lineage, Redis/vector reconstruction, state recovery, immutable compatibility,
and lifecycle/export controls. Phase 2 cannot prove Azure backup effectiveness, Production restore
time, regional DR, live key recovery, actual RPO/RTO, or cost; these remain Phase 3.

## Closure Gates, Decisions, And Unknowns

| Gate | Required evidence |
|---|---|
| F-01 | Phase 1 clearance plus explicit Founder Phase 2 authorization and valid records |
| F-02 | Tool/supply-chain/vulnerability/retention/test-owner decisions accepted |
| F-03 | Pinned runners build; import/full Docker collection passes; no zero/missing tests |
| F-04 | Six images build non-root and pass health/secret checks |
| F-05 | CT-01 through CT-06 deterministic proofs pass; CT-07 remains Phase 3 |
| F-06 | Terraform format/validate/policy/fixture plans pass offline |
| F-07 | SEC-01..27 and DATA-01..28 executable, non-skipped, machine-accounted |
| F-08 | Independent QA/specialist review; INST-010 does not self-review |
| F-09 | Complete unmerged PR evidence; no cloud/DNS/deployment/Production action |

Unresolved choices include exact Terraform/AzureRM versions, .NET 9 container versus editor SDK,
Node 20 versus 24, Python locks, Billing build source, supply-chain formats/signing/retention,
vulnerability exception policy, IaC policy engine, state bootstrap tools, health timings, development
profiles for excluded services, and container-parity CodeQL execution.

Founder retains Phase 2/3 authorization, domains/DNS/cert activation, expenditure, Production region/
promotion/objectives/residual risk, OIDC/break-glass actors, Operations activation, PR approval, and
merge. Specialist owners retain their accepted Decision Spaces; QA retains qualification.

Unknowns include live cloud/GitHub/GHCR/DNS/cert/identity/backup/cost state, actual service builds,
post-repair test validity/pass count/coverage/performance/Stop latency/security/migration/recovery,
current vulnerabilities, Production load/provider/region behavior, numeric objectives, and drift.

## Completeness And Contribution Record

Toolchain, workflows, Compose, Terraform, container builds, Docker validation, local/CI/cloud
separation, eight Phase 2 proposals, all 55 proof mappings, supply chain, recovery, conflicts,
dependencies, closure gates, protected decisions, and unknowns are complete at feasibility level.
Implementation and live effectiveness are not established.

| Field | Value |
|---|---|
| Contribution | CR-GOAL-006-INST-010-01 |
| Decision | P1-WC07 feasibility contribution complete |
| Verdict | CONDITIONALLY FEASIBLE |
| Residual risk | IDENTIFIED, NOT ACCEPTED |
| Implementation/cloud/DNS/deployment/Production authority | NOT GRANTED |
| Self-review | NOT PERFORMED |
| Downstream effect if accepted | Satisfies P1-WC07 for P1-WC08 planning only |

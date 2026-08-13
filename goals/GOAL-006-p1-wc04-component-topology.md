# GOAL-006 P1-WC04 Deployable Component And Integration Topology

## Record Control

| Field | Value |
|---|---|
| `institution_id` | INST-005 |
| `goal_id` | GOAL-006 |
| `record_id` | CR-GOAL-006-INST-005-01 |
| `record_type` | Contribution Record |
| `go_authorization` | GOA-GOAL-006-INST-005-01 |
| `work_component` | P1-WC04 — Deployable Component And Integration Topology |
| `produced_at` | 2026-08-13T10:03:27Z |
| `source_commit` | `e9b76b61a96313c930394e5406efef067ee17975` |
| `status` | ACCEPTED — R-110 / CR-GOAL-006-INST-002-05 |

This document defines component placement and integration requirements from committed repository
evidence. It does not prove runtime behavior or decide P1-WC05 security controls, P1-WC06 data
recovery, cloud resources, DNS, implementation, deployment, or activation.

## Deployable Inventory

| Set | Components | Repository evidence | Topology treatment |
|---|---|---|---|
| Current five-image CI set | Constitutional Engine, Business Platform, Professional Runtime, AI Runtime, web | `.github/workflows/ci.yaml` | Required release-manifest members until an accepted scope change. |
| Additional source services | Billing Engine; Trust Layer/OAuth Vault | `src/billing-engine/`; `src/trust-layer/oauth_vault/`; Compose declarations | Billing Engine is mandatory per DR-GOAL-006-INST-011-01. OAuth Vault is conditional on P1-WC05. |
| Shared platform dependencies | PostgreSQL, PgBouncer, Keycloak, Temporal, Redis, OTel backend; Ollama where approved | `docker-compose.yml`; Terraform core module | Placement and lifecycle follow P1-WC03; security/data detail remains routed. |
| Development-only surfaces | test/sprint runners, Temporal UI, Jaeger UI, MCP stubs/tools | `docker-compose.yml` | Not automatically part of Demo/UAT/Production; each needs explicit owner, need, image, health, security, cost, and release decision. |

Repository presence is not live or production evidence. Billing Engine must be added through an
accepted manifest/CI/topology change. OAuth Vault remains conditional and MCP services excluded.

## Placement Contract

| Component class | Demo/UAT workload plane | Production workload plane | Foundation/interface requirement |
|---|---|---|---|
| Web and approved public APIs | Leased compute using approved digest/configuration | Minimum safe always-available compute | Public exposure enforcement decided by P1-WC05. |
| CE, AIR, internal APIs/tools | Leased only where approved health/startup allows | Capacity derived from accepted SLO/load evidence | Internal-only reachability; CE is never directly public. |
| Keycloak/Temporal/PgBouncer/Redis/Ollama | Lifecycle based on state, dependency and recovery classification | Capacity/availability based on accepted component SLOs | P1-WC05 identity/network controls and P1-WC06 state classification apply. |
| PostgreSQL and durable state | Not disposable with workload lease | Always protected | P1-WC06 owns isolation, backup, restore, retention, migration, RPO/RTO. |
| Telemetry backend/collectors | Available whenever monitored workload is active; evidence retained per policy | Available for production monitoring | P1-WC03 backend; P1-WC05 redaction; P1-WC09 response. |

## Cloud Boundary Mapping

Compose host-port mappings are development conveniences and are never copied into cloud topology.

| Component | Cloud exposure requirement | Egress/dependency requirement | P1-WC05/P1-WC06 enforcement input |
|---|---|---|---|
| Web | Public candidate | Approved public API and identity endpoints only | TLS/CORS/WAF/domain controls pending Security. |
| Business Platform | Public API candidate | CE, identity, data, Temporal and approved internal services | Public ingress/rate/TLS plus private dependencies pending Security/Data. |
| Professional Runtime | Public interaction candidate | CE, BP, AIR, identity, data and Temporal | Public protocol boundary and private dependencies pending Security. |
| CE | Internal only; no internet ingress | Data/telemetry and approved internal callers only | Private reachability, mTLS and caller identity pending Security. |
| AIR | Internal only | CE, data and approved providers/tools | Private reachability, egress allow-list and provider identity pending Security. |
| PostgreSQL/PgBouncer/Redis/Temporal/Ollama | Internal only; no public or host-port analogue | Only approved component callers | Network/data/auth/encryption controls pending Security/Data. |
| Keycloak | Split user/admin surfaces require Security decision; current external Terraform ingress is not accepted | Data plus approved identity providers/clients | P1-WC05 must define user endpoint, admin isolation, rate/TLS and trust boundaries. |
| Billing Engine | Mandatory release member; exposure remains internal unless P1-WC05 accepts another boundary | BP/AIR/data dependencies require P1-WC07 verification | P1-WC05/P1-WC06 review and promotion-manifest membership required. |
| OAuth Vault | No cloud exposure until P1-WC05 establishes it as the accepted credential component | None assumed | Conditional under DR-GOAL-006-INST-011-01. |
| MCP services | Excluded from GOAL-006 platform baseline | None assumed | Separate agent/feature authorization required. |

## Declared Ports And Protocols

| Component | Declared port/protocol | Evidence class | Boundary requirement / unresolved issue |
|---|---|---|---|
| Constitutional Engine | `5002`, gRPC/HTTP2 | Compose, Terraform, proto | Internal only. |
| Business Platform | `5001`, HTTP REST | Compose, Terraform, OpenAPI | Public API candidate; exact ingress/TLS/CORS decided by P1-WC05. |
| Professional Runtime | `5003`, HTTP REST/WebSocket | Compose, Terraform, OpenAPI/Emergency Stop contract | Public interaction candidate; exact exposure decided by P1-WC05. |
| AI Runtime | `5004`, HTTP API | Compose, Terraform, OpenAPI | Internal only. Compose points its CE address to `constitutional-engine:7000`, conflicting with CE `5002`; P1-WC07 must resolve before implementation acceptance. |
| Web | `3000`, HTTP | Compose/CI/Terraform | Public web candidate; exact exposure decided by P1-WC05. |
| OAuth Vault | `8130`, HTTP | Dockerfile/Compose | Cloud inclusion and callers remain OPEN. |
| Billing Engine | `8140`, HTTP | Compose/source | Cloud inclusion and API consumers remain OPEN. |
| PostgreSQL / PgBouncer | `5432` / `5433`, PostgreSQL protocol | Compose | Internal only; direct versus pooled clients require P1-WC06/07 verification. |
| Keycloak | `8080` internal declaration; external cloud ingress currently declared | Compose/Terraform | Identity endpoint/admin boundary is a P1-WC05 decision; current external Terraform declaration is not accepted security design. |
| Temporal | `7233`, Temporal gRPC | Compose/Terraform | Internal only. |
| Redis | `6379`, Redis protocol | Compose | Internal only; transient/durable classification pending P1-WC06. |
| Jaeger/OTLP | `4317` gRPC, `4318` HTTP, UI `16686` in Compose | Compose | Development backend/UI; cloud uses accepted OTel backend design. |
| Ollama | `11434`, HTTP | Compose/Terraform | Internal only; production inclusion/capacity remains evidence-dependent. |

## Declared Dependency Contracts

| Consumer | Declared dependency/configuration | Required contract before Phase 2 |
|---|---|---|
| Business Platform | CE, Temporal, Keycloak, PostgreSQL, OTel | Exact endpoint/protocol, auth context, timeout, health, failure and evidence behavior verified against source/API/proto. |
| Professional Runtime | CE, AIR, BP, Temporal, Keycloak JWKS, PostgreSQL, OTel | Emergency Stop path and fail-safe behavior verified; no invented polling/fallback. |
| AI Runtime | CE, BP, PostgreSQL, OTel and tool/provider integrations | Resolve CE port mismatch; enumerate only implemented callers/providers; define fail-safe degradation with owner approval. |
| Web | Business/customer APIs and identity flow | Runtime configuration contains environment endpoint references only; no baked URL/secret. |
| Keycloak / Temporal | Direct PostgreSQL declarations | P1-WC06 validates schema/isolation/recovery; P1-WC05 validates identity/admin boundary. |
| Application data clients | Current direct/pool declarations vary | P1-WC06/07 establish accepted direct-versus-PgBouncer matrix. |
| Billing Engine / OAuth Vault / MCP services | Compose/source relationships vary | P1-WC07 produces exact implemented dependency inventory before release inclusion. |

## Health And Startup Contract

Committed Compose probes are development declarations, not accepted cloud health contracts. Each
cloud deployable must provide:

- distinct startup, readiness, and liveness semantics where the runtime supports them;
- a readiness result that covers mandatory local dependencies without calling optional providers;
- bounded timeout/retry behavior and a fail-safe state;
- no secret, tenant data, or internal detail in probe responses;
- release digest/configuration identity in diagnostic evidence, not public health output;
- a dependency graph that prevents traffic before readiness but avoids permanent cyclic startup;
- QA-verifiable behavior for slow startup, dependency loss, recovery, and rollback.

Temporal has no Compose health check. Port-open checks for CE and HTTP `/health` declarations for
other services require P1-WC07 source verification before they become cloud acceptance criteria.

## Configuration And Promotion Contract

The image contains code/runtime only. The signed promotion manifest binds each approved component
to its OCI digest and evidence. Environment configuration supplies reviewed non-secret endpoints,
feature controls, and operational settings. Secret values are resolved through the P1-WC05-approved
identity/reference mechanism and never baked into images or passed as Terraform plaintext.

Adding/removing a release component changes the manifest schema and requires owner review, tests,
cost impact, rollback compatibility, and traceability. Demo, UAT, and Production deploy the same
component digests; environment differences are configuration only.

## Failure And Degradation Requirements

| Failure class | Required behavior | Owner follow-up |
|---|---|---|
| CE unavailable/invalid constitutional response | Affected governed action fails safe; no bypass or success claim. | INST-005 contract detail; INST-007 threat review; QA CCT. |
| Required datastore unavailable | Reject or pause unsafe mutation; preserve evidence and correlation; no fabricated success. | INST-006 recovery/data consistency; QA. |
| Identity/JWKS unavailable | No new unauthorized access; cached-material policy only if P1-WC05 approves it. | INST-007. |
| Optional AI/provider/tool unavailable | Degrade only through an approved capability/fallback contract; governed action remains subject to CE. | INST-005/008 and Product Owner; QA. |
| Telemetry backend unavailable | Business behavior follows approved policy, but evidence obligations must not be silently dropped. | INST-002/009; P1-WC09 response. |
| New digest unhealthy | Stop promotion and roll back to the previous qualified digest/configuration pair when rollback is proven safe. | INST-009 pipeline; QA evidence. |
| Dependency contract mismatch | Fail build/contract gate before deployment. | INST-010 implementation feasibility; QA. |

No numeric timeout, retry count, fallback, escalation time, or recovery objective is accepted in
P1-WC04. Those values require specialist evidence and qualification.

## Observability Contract

Every component must emit OTel-compatible service, dependency, error, saturation, startup,
readiness, release, and configuration-version signals with tenant-safe correlation. CE/PR/BP paths
must preserve constitutional evidence and Emergency Stop correlation. P1-WC05 defines redaction;
P1-WC06 defines data classifications; P1-WC09 defines alert response. Public telemetry endpoints
are prohibited unless explicitly approved by Security.

## Gaps And Conflicts

| ID | Gap/conflict | Routing | Effect |
|---|---|---|---|
| CT-01 | AIR uses CE port `7000` in Compose while CE is declared on `5002`. | INST-010 P1-WC07 with INST-005 confirmation | Blocks AIR/CE implementation acceptance. |
| CT-02 | Five-image CI excludes mandatory Billing Engine; OAuth Vault is conditional; MCPs are excluded. | DR-GOAL-006-INST-011-01; INST-005/007/010 | Billing manifest/CI integration and OAuth decision remain downstream work. |
| CT-03 | Compose exposes many dependency/MCP ports to the host; cloud inclusion/boundaries are undefined. | INST-005/007/009 | Blocks copying Compose topology into cloud. |
| CT-04 | Keycloak cloud ingress is externally enabled in current Terraform without accepted P1-WC05 boundary. | INST-007 | Blocks security acceptance of current Terraform. |
| CT-05 | Temporal lacks a declared Compose health check; cloud health semantics are not verified. | INST-005/010/QA | Blocks readiness acceptance. |
| CT-06 | Current password-bearing configuration and direct/pool DB clients conflict with accepted P1-WC03 boundaries. | INST-006/007/010 | Blocks implementation acceptance. |
| CT-07 | Live image, endpoint, DNS, provider, realm, and dependency state remains unknown. | Phase 3 authorized owners | No production/readiness claim permitted. |

CT-01 and CT-05 are implementation defects to be verified and repaired only under a future Phase 2
implementation GOA. Phase 1 records the required target contract and test; it does not modify source,
Compose, or Terraform. These defects block Phase 2 implementation acceptance, not acceptance of an
evidence-correct Phase 1 topology. CT-02 release scope is resolved by DR-GOAL-006-INST-011-01;
implementation and the conditional OAuth decision remain open.

## P1-R06 And P1-R10

P1-R06 is partially addressed by classifying public candidates and internal-only requirements. The
enforcement design remains P1-WC05. P1-R10 remains open: no GHCR, Azure, DNS, credential, provider,
or endpoint query was performed.

## Completeness And Routing

| Obligation | Status |
|---|---|
| Deployable/component inventory | COMPLETE for repository evidence; cloud release scope gaps explicit |
| Placement and public/internal requirements | COMPLETE at component-interface level; enforcement routed |
| Ports/protocols/dependencies | COMPLETE for declarations; CT-01 and unverified calls explicit |
| Health/startup/configuration/promotion contracts | COMPLETE as requirements; source/live proof pending |
| Failure/degradation/observability contracts | COMPLETE without invented numeric behavior |
| State/recovery | ROUTED to P1-WC06 |
| P1-R06/P1-R10 | PARTIAL/OPEN as stated |
| Phase 2/3 authority | NOT GRANTED |

Recommended next gate: independent review of CR-GOAL-006-INST-005-01. If accepted, P1-WC05 may
be routed to INST-007 using P1-WC01 through P1-WC04 as inputs. P1-WC06, implementation, cloud
action, DNS, production, and activation remain dependency-gated.

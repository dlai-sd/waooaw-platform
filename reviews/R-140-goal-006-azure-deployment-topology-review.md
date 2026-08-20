# R-140 - GOAL-006 Azure Deployment Topology Architecture Review

| Field | Value |
|---|---|
| Goal | GOAL-006 - Secure Autonomous Cloud Delivery Capability |
| Work Contract | WC-076 - GOAL-006 Phase 3 Execution |
| Reviewed baseline | `a4b22c7` - `architecture/reference/pipeline/azure-deployment-topology.md` |
| Enterprise Architecture | INST-004 - APPROVE WITH REQUIRED REPAIRS |
| Solution Architecture | INST-005 - APPROVE WITH REQUIRED REPAIRS |
| Consolidated verdict | **APPROVE AFTER RECORDED REPAIRS** |
| Review date | 2026-08-20 |

## Decision

The topology is derived from the accepted GOAL-006 platform, security, data, cost, and delivery decisions and is implementable without changing the Constitution. It establishes the authoritative cloud target before further Demo infrastructure mutation.

The review confirms:

- build-once exact-six promotion with separate signed dependency evidence;
- Demo, Founder acceptance, UAT, and pre-activation Production boundaries;
- isolated environment state, identity, network, data, secrets, DNS, and evidence;
- durable foundation and leased workload separation;
- private PostgreSQL, Keycloak, Temporal, Redis, and internal services;
- managed public identity and application ingress surfaces;
- pre-traffic qualification, ACA revision traffic switching, and schema-safe rollback;
- bounded cost and lease reconciliation with protected-state retention.

## Required Repairs And Closure

| Repair | Disposition |
|---|---|
| Define dark Production as the single Production environment before traffic activation | CLOSED in topology invariant 5 |
| Preserve exact-six while pinning identity edge, Keycloak, Temporal, and Redis | CLOSED through a separately signed dependency manifest |
| Define state, configuration, identity, database, dependency, verification, rollback, and lease interfaces | CLOSED in `Implementation Interface Gates` |
| Make required public and private probes fail closed before traffic shift | CLOSED in promotion step 4 |
| Bind rollback to previous qualified tuple and additive-schema compatibility | CLOSED in rollback contract |
| Route detailed CCTs, probes, role/RLS, configuration, and dependency versions to accountable offices | CLOSED through the interface ownership matrix |

## Governance Disposition

- **Constitution amendment:** Not required. The topology enforces existing constitutional floors and does not create new institutional authority.
- **ADR amendment/new ADR:** Not required for this recovery implementation. ADR-010, ADR-011, ADR-013, ADR-014, ADR-015, ADR-027, ADR-031, and ADR-046 already govern the selected cloud, migration, delivery, secret, workflow, cost, fail-safe, and identity strategies.
- **Future ADR trigger:** Required only if implementation changes a strategic decision, including replacing ACA, changing Temporal placement, permitting destructive migrations, changing exact-six authority, adding a Production edge before cost/origin-lock approval, or weakening environment identity/data isolation.
- **Founder-reserved boundary:** UAT remains blocked until explicit Founder Demo acceptance. Production customer traffic and final activation remain reserved.

## Implementation Gate

Proceed in dependency order: control plane, foundation, runtime dependencies, application plane and DNS/TLS, release mechanics, then promotion. No full Demo apply may occur until the first five slices pass a real Demo OIDC plan, cost gate, and independent executable review.

This review authorizes no self-merge, UAT action, Production apply, customer traffic, or expansion of FA-052/WC-076.

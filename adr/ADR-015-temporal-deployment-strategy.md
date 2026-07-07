# ADR-015: Temporal Workflow Orchestration Deployment Strategy

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Platform Architect (infrastructure lifecycle) + Enterprise Architect (cost and scaling strategy)
**Constitutional Basis:** Constitution Article III (Second Law — authority licensed through constitutional evidence; every employment workflow is an authorised act that must be orchestrated reliably); GENESIS Part 01 — Cost Constraint (INR 10,000/month per non-production environment); ADR-010 (Cloud Portability — Temporal is cloud-agnostic)

---

## Context

Temporal is the workflow orchestration engine for all long-running institutional processes: professional employment lifecycle, evidence collection workflows, contract approval chains, PAAS session management.

Temporal can be deployed in two modes:
1. **Self-hosted** — Temporal server running in Docker / Container Apps, backed by PostgreSQL
2. **Temporal Cloud** — managed Temporal-as-a-service (Temporal Technologies, Inc.)

The question is: which mode in which environment, and when does the switch occur?

## Decision

**Self-hosted Temporal in dev and QA (sharing the platform PostgreSQL). Temporal Cloud in UAT and production.**

The switch from self-hosted to Temporal Cloud occurs when the first UAT deployment is executed.

### Self-Hosted (Dev and QA)

```yaml
# docker-compose.yaml (dev)
temporal:
  image: temporalio/auto-setup:1.24
  environment:
    DB: postgresql
    DB_PORT: 5432
    POSTGRES_USER: temporal
    POSTGRES_PWD: ${TEMPORAL_DB_PASSWORD}
    POSTGRES_SEEDS: postgres
  depends_on: [postgres]

temporal-ui:
  image: temporalio/ui:2.26
  ports:
    - "8080:8080"
  environment:
    TEMPORAL_ADDRESS: temporal:7233
```

Self-hosted Temporal uses the same PostgreSQL instance as the platform (separate `temporal` database schema). This is acceptable in dev and QA where data loss is tolerable and cost must be minimised.

**Cost:** zero additional cost — Temporal runs in the same PostgreSQL Flexible Server.

### Temporal Cloud (UAT and Production)

```
Connection string: <namespace>.tmprl.cloud:7233
Authentication: mTLS with Temporal Cloud-issued client certificates (stored in Azure Key Vault per ADR-014)
Namespaces:
  waooaw-uat   — UAT environment
  waooaw-prod  — Production environment
```

**Why Temporal Cloud for UAT+prod:**
- Temporal's server HA (multi-node, replicated history shards) is complex to operate
- A failed Temporal server in production means no new workflows can be started (Emergency Stops still work — they are direct WebSocket calls, not Temporal workflows)
- Temporal Cloud provides 99.99% SLA and handles all operational burden
- Cost: ~$25/month per namespace at MVI workflow volumes (estimated 1,000-5,000 workflow executions/month)

### Migration Trigger

The switch happens at first UAT deployment. The `TEMPORAL_ADDRESS` environment variable is the only configuration that changes:

```
Dev/QA:   TEMPORAL_ADDRESS=temporal:7233  (self-hosted, Docker service name)
UAT/Prod: TEMPORAL_ADDRESS=waooaw-uat.tmprl.cloud:7233  (Temporal Cloud)
```

Workflow code is identical in both environments — Temporal's client SDK is unaware of whether the server is self-hosted or cloud-managed.

### Version Pinning

Self-hosted Temporal server version is pinned in Docker Compose (e.g., `temporalio/auto-setup:1.24`). Temporal Cloud server version is managed by Temporal Technologies. The Temporal Go/Java/Python/TypeScript SDK version must be compatible with the server version — this compatibility is documented in the Temporal release notes and enforced at build time.

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Temporal Cloud in all environments including dev | ~$25/month per namespace × 4 environments = ~$100/month. Exceeds INR 10k constraint for non-production. Also unnecessary — dev does not need Temporal SLA. |
| Self-hosted Temporal in all environments | Production-grade self-hosted Temporal requires multi-node deployment (Temporal Frontend, History, Matching, Worker services) plus PostgreSQL HA. Adds ~₹3,000-5,000/month and significant operational overhead. Not justified at MVI. |
| Cadence (Temporal predecessor) | Temporal is the actively maintained fork. No reason to use Cadence. |
| Apache Airflow | Designed for data pipelines (DAGs). Not designed for arbitrary long-running workflows with external signals (Temporal signals/queries are used for Emergency Stop integration). |

## Consequences

**Benefits:**
- Zero additional cost in dev and QA (self-hosted on existing PostgreSQL)
- Production-grade SLA in UAT and production without operational overhead
- Workflow code is environment-agnostic — one codebase, different connection strings
- Temporal Cloud is not Azure-specific — aligns with ADR-010 portability posture

**Trade-offs:**
- Dev/QA Temporal shares PostgreSQL — a heavy workflow load in QA could impact database performance for other services
- Temporal Cloud credentials (mTLS certs) have an expiry — must be tracked in ADR-014 secret rotation schedule
- Self-hosted and Temporal Cloud may have minor version differences — Temporal SDK compatibility matrix must be checked at each Temporal upgrade

**Temporal UI access:**
- Dev: `http://localhost:8080` (Temporal UI docker service)
- Cloud: `https://cloud.temporal.io` (Temporal Cloud console, requires Temporal Cloud account)

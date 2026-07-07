# ADR-010: Cloud Provider Portability Posture

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Enterprise Architect (platform-wide strategy) + Platform Architect (infrastructure decisions)
**Constitutional Basis:** Constitution Article VII (Doctrine of Institutional Independence — the institution must not be subject to capture by any external power, commercial or otherwise); GENESIS Part 01 — Cost Constraint; GENESIS Design Principles — Configuration over Code

---

## Context

All infrastructure decisions carry an implicit cloud portability assumption. Without an explicit posture, individual engineers will make different portability trade-offs, creating inconsistency. Some will choose maximum portability (at cost and complexity), others will choose managed services (at portability cost). Both can be wrong.

The institution needs one declared posture that all infrastructure decisions reference.

## Decision

**Azure-first. Portability at the application layer. Managed services are accepted where they are the lowest-cost option — with one named escape hatch per Azure-specific dependency.**

This is not "cloud-agnostic" (which is expensive and premature). This is "not permanently captive."

### Portability Layers

| Layer | Portability Posture | Reasoning |
|---|---|---|
| Application code | Fully portable | .NET and Python containers run identically on any OCI-compliant runtime |
| Protocols | Fully portable | gRPC (open standard), REST (open standard), WebSocket (open standard) |
| Database | Portable with connection string change | Standard PostgreSQL — AWS RDS, GCP Cloud SQL, self-hosted are equivalent |
| Observability | Portable with config variable change | OTel OTLP endpoint is the only config that changes (ADR-009) |
| Identity | Portable | Keycloak is self-hostable; no Azure identity dependency (ADR-008) |
| Workflow orchestration | Portable | Temporal is self-hostable or available via Temporal Cloud (not Azure-specific) |
| Container runtime | Portable with IaC rewrite | Container Apps → GCP Cloud Run / AWS App Runner / Kubernetes is a Terraform rewrite, zero app code change |
| Emergency Stop transport | **Azure-specific** | Azure SignalR (see escape hatch below) |
| Service mTLS | **Azure-specific** | Container Apps managed mTLS (see escape hatch below) |

### Named Escape Hatches

**Emergency Stop (Azure SignalR → self-hosted SignalR + Redis backplane):**
```
Current:    Professional Runtime → Azure SignalR Hub
Portable:   Professional Runtime → self-hosted ASP.NET Core SignalR Hub
             + Redis backplane for horizontal scaling (Redis is cloud-agnostic)
Migration:  Update docker-compose.yaml + Container Apps config
            No application code change (SignalR Hub interface is identical)
Cost delta: +~₹800/month for Redis cache in non-dev environments
```

**mTLS (Container Apps managed → gRPC TLS interceptor with cert files):**
```
Current:    Azure Container Apps environment auto-provisions and rotates mTLS certs
Portable:   gRPC TLS interceptor reads cert + key from mounted secret volume
             Certs issued by any CA (Let's Encrypt, internal CA, cloud provider CA)
Migration:  Mount cert secrets into containers, update gRPC server/client config
            No application code change (interceptor interface is identical)
```

### What We Deliberately Do Not Pursue

- **Multi-cloud active-active** — requires 3× infrastructure cost and engineering overhead with zero benefit at MVI
- **Provider-agnostic IaC** (e.g., Pulumi multi-cloud) — Terraform with Azure provider is sufficient; migration is a rewrite, not incremental
- **Abstracting managed services behind adapter interfaces** — adds indirection with no current value

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Full cloud-agnostic design | Increases MVI cost by 30-50% (replacing managed services with self-hosted equivalents). Requires solving problems that don't exist yet. Violates GENESIS Minimum Viable Institution principle. |
| Permanent Azure lock-in (no escape hatches) | Violates Constitution Article VII (Institutional Independence). The institution must retain the ability to move its operations. |
| AWS-first | Azure India Central (Pune) has better latency for Indian customers. Azure has better pricing for the specific services used at MVI scale. No technical reason to switch. |

## Consequences

**Benefits:**
- All engineers share the same portability mental model
- Every Azure-specific dependency has a documented escape hatch
- Application code change required for cloud migration: zero
- Infrastructure IaC rewrite required for cloud migration: yes (acceptable — this is infrastructure work, not business logic)

**Review trigger:**
This ADR should be revisited if:
- A constitutional review identifies that an Azure-specific dependency has no viable escape hatch
- Azure pricing changes make a component non-viable within the INR 10k/month constraint
- A customer requirement mandates deployment to a specific non-Azure cloud

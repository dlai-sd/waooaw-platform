# ADR-007: gRPC mTLS Certificate Management

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Security Architect (PKI and certificate management) + Platform Architect (infrastructure management)
**Constitutional Basis:** Constitution Article IX (Constitutional Floors — Security by Design); GENESIS Design Principles — Security by Design

---

## Context

Internal gRPC communication between services (Business Platform → Constitutional Engine, Professional Runtime → Constitutional Engine) must be mutually authenticated. Without mTLS, a compromised service or a network-internal attacker could call the Constitutional Engine directly and fabricate evidence records.

The question is: how do we manage TLS certificates for mTLS between services?

## Decision

**Azure Container Apps managed mTLS in cloud; plain gRPC (no TLS) in development Docker network.**

Azure Container Apps environments provide automatic peer-to-peer mTLS between services running in the same environment. Certificates are provisioned and rotated automatically by the platform. Zero operational overhead.

In development (Docker Compose): all services run on the same isolated Docker bridge network. The network is not reachable externally. Plain gRPC without TLS is acceptable in this trusted environment.

```
Cloud (Azure Container Apps):
  Business Platform ──(mTLS, auto-cert)──→ Constitutional Engine
  Professional Runtime ──(mTLS, auto-cert)──→ Constitutional Engine

Development (Docker):
  business-api:5001 ──(plain gRPC)──→ constitutional-engine:5002
  professional-runtime:5003 ──(plain gRPC)──→ constitutional-engine:5002
```

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Manual certificate management (openssl) | Certificate rotation risk. Operational burden. One expired certificate brings down inter-service communication. |
| Service mesh (Linkerd or Istio) | Significant operational complexity for 4-service platform. Linkerd adds ~200MB RAM per sidecar. Not justified at MVI. |
| No mTLS anywhere | Constitutionally unacceptable. The Constitutional Engine must only accept calls from authorized services. |
| HashiCorp Vault | Powerful but complex. Vault must be operated, backed up, and unsealed. Zero justification at MVI when Container Apps provides this for free. |

## Consequences

**Benefits:**
- Zero certificate management overhead (Azure handles it)
- Automatic rotation (no certificate expiry incidents)
- Service-to-service authentication without additional infrastructure

**Trade-offs:**
- Dev/cloud parity is slightly broken (mTLS in cloud, plain in dev)
- Integration tests in CI must account for no-mTLS environment
- If moving to a different cloud provider, managed mTLS solution changes

**Future:**
If the platform moves to Kubernetes, evaluate Linkerd for service mesh. At that scale, a service mesh becomes worth the operational overhead.

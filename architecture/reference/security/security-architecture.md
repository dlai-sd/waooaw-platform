# Security Architecture

**Produced by:** Security Architect (Sprint 008)
**Work Contract:** WC-008
**Date:** 2026-07-07
**Constitutional Basis:** Constitution Article IX (Constitutional Floors), Constitution Article X (Right of Review), C-001 (human override absolute), C-007 (ledger immutability), AD-009 (Observability by Default), ADR-007 (mTLS), ADR-008 (Keycloak), ADR-014 (Secret Management)

---

## 0. Data Classification (FR-003)

Every piece of data in the WAOOAW platform falls into one of four classifications. Security controls are calibrated per classification.

| Classification | Examples | Owner | Access | Portability |
|---|---|---|---|---|
| **Customer Private Data** | Employment contracts, evidence records, Decision Spaces, credentials, goals, content created | Customer | Customer only (RLS enforced) | Full — Article IX right of export |
| **Professional Experience** | Engagement summaries (hashed), capability demonstrations | Professional Identity | Professional + WAOOAW internal | Portable with professional identity |
| **Constitutional Audit** | All governance events — approvals, rejections, Emergency Stops, authority changes | Platform (immutable) | Customer read, no one writes except CE | Full — Article IX |
| **WAOOAW Institutional IP** | Domain learning patterns, skill performance models, aggregate anonymised insights | WAOOAW | Internal AI services only | Not portable — WAOOAW IP (FR-003) |

**The security rule:** A data access that crosses classification boundaries requires explicit constitutional authorization. Crossing the Customer Private ↔ Institutional IP boundary is prohibited in both directions — customer data never flows into institutional IP; institutional IP never exposes customer data.

---

## 1. Network Topology

### Public vs Internal Boundary

```
INTERNET
    │
    │  HTTPS (TLS 1.3)      WSS (TLS 1.3)
    │
┌───▼─────────────────────────────────────────────┐
│  Azure Container Apps Environment                │
│  (Azure-managed ingress — no customer-managed   │
│  API gateway at MVI per ADR-010)                │
│                                                  │
│  PUBLIC INGRESS:                                 │
│  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ Business Platform │  │ Professional Runtime  │ │
│  │ Port 5001 (REST)  │  │ Port 5003 (WSS)       │ │
│  │ api.waooaw.com    │  │ rt.waooaw.com         │ │
│  └──────────┬────────┘  └──────────┬────────────┘ │
│             │ gRPC (mTLS)          │ gRPC (mTLS)  │
│  INTERNAL ONLY (not reachable from internet):    │
│  ┌──────────▼────────────────────────────────┐  │
│  │  Constitutional Engine (Port 5002)         │  │
│  │  Internal Container Apps network only      │  │
│  └──────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────┐ │
│  │  AI Runtime (Port 5004)                    │ │
│  │  Internal only — called by PR only         │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │  PostgreSQL (Port 5432)                    │ │
│  │  Internal only — no public route           │ │
│  └────────────────────────────────────────────┘ │
│  ┌───────────────┐  ┌─────────────────────────┐ │
│  │  Keycloak     │  │  Temporal               │ │
│  │  Port 8443    │  │  Port 7233              │ │
│  │  Internal only│  │  Internal only          │ │
│  └───────────────┘  └─────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Enforcement mechanism:** Azure Container Apps environment — services that do not have `ingress: external` cannot be reached from the internet. CE and AI Runtime have `ingress: internal`. No NSG override required — the Container Apps environment is the network boundary.

**Admin access:** Keycloak admin portal, Temporal UI, Jaeger UI are accessible only via Azure Bastion session or private VPN. Never exposed to the internet.

---

## 2. Identity and Authentication

### JWT Validation Specification

Every request to Business Platform and Professional Runtime must pass JWT validation before reaching any controller. This is not optional and is not feature-flagged.

**Algorithm:** RS256 (asymmetric — Keycloak private key signs; services validate with Keycloak public key via JWKS endpoint)

**Token expiry:** 15 minutes access token. 24-hour refresh token with rotation (each use invalidates the current and issues a new refresh token).

**Required claims validation (in order — reject on any failure):**

```
1. Signature:  validate against Keycloak JWKS endpoint (cache JWKS for 5 minutes; 
               force-refresh on key-not-found)
2. Algorithm:  must be RS256 — reject any other algorithm (algorithm confusion attack prevention)
3. iss:        must equal Keycloak realm issuer URL (e.g., http://keycloak:8080/realms/waooaw)
4. aud:        must include "waooaw-platform"
5. exp:        must be in the future (clock skew tolerance: 30 seconds)
6. nbf:        if present, must be in the past
7. tenant_id:  must be present and a valid UUID format
               (Keycloak custom claim mapper adds this claim at login)
```

**Rejection behaviour:** Return 401 Unauthorized with RFC 9457 Problem Detail. Do not reveal which validation step failed (prevents enumeration of valid claims).

**gRPC propagation:**
Business Platform and Professional Runtime propagate the raw JWT Bearer token as gRPC metadata header `authorization: Bearer <token>` on every Constitutional Engine call. CE performs its own JWT validation on this token to extract `tenant_id` for the `x-tenant-id` metadata. This double-validation is intentional — it prevents a compromised BP from passing a different tenant_id to CE.

### Service-to-Service Authentication

| Route | Dev | Cloud |
|---|---|---|
| BP → CE | Plain gRPC (internal network only) | mTLS (ADR-007) |
| PR → CE | Plain gRPC (internal network only) | mTLS (ADR-007) |
| PR → AI Runtime | Plain HTTP (internal network only) | TLS 1.3 (internal) |
| All → PostgreSQL | Password auth (DB user credentials) | Password auth + Azure Private Endpoint |
| All → Temporal | Temporal SDK (no auth in dev) | Temporal Cloud mTLS |

mTLS certificates for cloud deployment are managed per ADR-007 — cloud provider certificates with 90-day rotation.

---

## 3. Secret Management

Per ADR-014:

| Environment | Mechanism | What is stored |
|---|---|---|
| Dev | `.env` file (git-ignored) | All credentials |
| CI | GitHub Actions encrypted secrets | GHCR PAT, test DB credentials |
| Cloud (Azure) | Azure Key Vault + Container Apps secret references | All production secrets |

**Azure Key Vault injection pattern:**

Container Apps reads secrets from Key Vault at startup via Key Vault references. The Container Apps managed identity has `Key Vault Secrets User` role on the Key Vault.

```
Container App environment variable:
  POSTGRES_PASSWORD = secretref:postgres-password

Container Apps resolves secretref at runtime via the managed identity.
The secret value is never in the container image or the Bicep template.
```

**Secret rotation policy:**
- DB passwords: rotated every 90 days, zero-downtime (new secret added before old removed, dual-valid period of 1 hour)
- LLM API keys: rotated every 30 days or immediately on suspected exposure
- Keycloak client secrets: rotated every 90 days
- mTLS certificates: auto-rotated by cert-manager (60-day certificates, 30-day renewal)

**Secret scanning:** `detect-secrets` pre-commit hook. GitHub Secret Scanning enabled on the repository. Any detected secret triggers immediate rotation procedure.

---

## 4. Data Security

### Encryption at Rest

- PostgreSQL data: Azure Disk Encryption (transparent, Azure-managed AES-256). No application-layer encryption required — the DB is not accessible from the internet and is protected by the Container Apps network boundary.
- Temporal workflow history: stored in PostgreSQL — covered by disk encryption above.
- Keycloak data: stored in PostgreSQL — same.

**Exception — Sensitive fields:** The `proposed_content` and `executed_content` fields in `evidence_records` may contain customer business content (marketing copy, trade parameters). These are stored as JSONB. No field-level encryption at MVI — the DB access controls and disk encryption are the protection layer. Field-level encryption added post-MVI if regulatory requirement (DPDP Act, India).

### Encryption in Transit

- All external traffic: TLS 1.3 minimum. TLS 1.2 is not accepted. Cipher suites: TLS_AES_128_GCM_SHA256, TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256.
- Internal gRPC (dev): TLS. Internal gRPC (cloud): mTLS.
- PostgreSQL connections: `sslmode=require` for all application users in cloud.

---

## 5. OWASP Top 10 Coverage

| OWASP | Risk | How WAOOAW addresses it |
|---|---|---|
| **A01 Broken Access Control** | HIGH | RLS at DB level (last line of defence). JWT `tenant_id` as the only authoritative source. Decision Space boundary validated by CE on every action. Authority levels enforced by CE (not application layer). |
| **A02 Cryptographic Failures** | HIGH | TLS 1.3 on all external traffic. RS256 JWT (asymmetric). AES-256 disk encryption. No sensitive data in logs. No credentials in container images. |
| **A03 Injection** | MEDIUM | EF Core with parameterized queries — no raw SQL concatenation. `sqlalchemy` with bound parameters in Python. ORM is the only DB access layer. Any raw SQL usage requires Security Architect approval. |
| **A04 Insecure Design** | HIGH | Constitutional model is the security design. Decision Space enforces authorized actions. Evidence First prevents action without audit. The threat model is part of the architecture (this document). |
| **A05 Security Misconfiguration** | MEDIUM | Hardened base images (`mcr.microsoft.com/dotnet/aspnet:9.0-alpine`, `python:3.12-slim`). No debug endpoints in production (ASPNETCORE_ENVIRONMENT ≠ Development). No Swagger UI in production. Health endpoints return no internal details. |
| **A06 Vulnerable Components** | HIGH | Dependabot auto-PRs for all dependency updates. Snyk scans on every PR. Critical/High CVEs block merge. SBOM generated at build. |
| **A07 Identification and Auth Failures** | HIGH | Keycloak manages auth (industry-grade identity). Short-lived tokens (15 min). Refresh token rotation. Algorithm validation prevents JWT confusion attacks. JWKS cached with force-refresh on key rotation. |
| **A08 Software/Data Integrity** | MEDIUM | GHCR image signing. Image promotion pipeline (one image, no rebuild). Migration validation in CI (ADR-011). Git commit signing enforced on main branch. |
| **A09 Logging and Monitoring Failures** | HIGH | OTel mandatory in all services. Constitutional violations produce P0 alerts. Centralized trace storage. Security events (auth failures, permission denials) produce structured OTel spans tagged as `constitutional.security.*`. |
| **A10 Server-Side Request Forgery** | MEDIUM | AI Runtime external API calls are via the Tool Registry. Tool Registry enforces an allowlist of approved external URLs from the Decision Space. No arbitrary URL fetching. Outbound DNS resolves via Azure DNS — no custom DNS that could be poisoned. |

---

## 6. Security in CI/CD Pipeline

All security gates are non-bypassable. No manual override permitted without a Founder Resolution citing the security exception.

| Gate | Tool | When | Blocks on |
|---|---|---|---|
| Secret scanning | `detect-secrets` + GitHub Secret Scanning | Every commit + PR | Any secret detected |
| SAST | GitHub Advanced Security (CodeQL) | Every PR | Any HIGH finding |
| Dependency scan | Dependabot + Snyk | Every PR + daily | Critical/High CVE unfixed >7 days |
| License compliance | FOSSA | Every PR | GPL/AGPL/SSPL in production dependency |
| Container image scan | Trivy | Every build | Critical CVE in base image |
| SBOM generation | Syft | Every build | Failed generation |
| API security (conformance) | Schemathesis | Every PR | Response violates OpenAPI spec |
| CCT — security category | Custom | Every PR + deploy | Any security CCT failure |

**Security Constitutional Compliance Tests (mandatory category):**
- CCT-SEC-01: Cross-tenant data isolation — Tenant A query must return zero Tenant B rows
- CCT-SEC-02: JWT algorithm enforcement — token with `alg: none` must be rejected
- CCT-SEC-03: Constitutional Engine not reachable from public internet — TCP connection to CE port from external IP must time out
- CCT-SEC-04: Evidence immutability — direct DB UPDATE on constitutional schema must be rejected
- CCT-SEC-05: Emergency Stop path reachability — Emergency Stop must succeed even when Business Platform REST API is rate-limited

---

## 7. Incident Response — Security Events

**P0 Security Incidents (immediate response — page on-call):**
- Cross-tenant data access detected (RLS failure or application bug)
- Constitutional Audit Ledger modification attempt
- Failed Emergency Stop (latency > 250ms or dropped)
- JWT forgery attempt (invalid signature on multiple requests from same IP)
- Credential detected in repository

**Incident response — what is NOT permitted:**
- Deleting evidence records to "clean up" incident artefacts (violates C-007)
- Disabling authentication temporarily to investigate (violates AD-004)
- Sharing customer evidence data externally without customer consent (violates Article IX)

All security incidents are recorded as OTel events tagged `constitutional.incident.*` — they are part of the constitutional audit trail, not separate from it.

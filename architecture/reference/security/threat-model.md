# Threat Model — WAOOAW Platform

**Produced by:** Security Architect (Sprint 008)
**Work Contract:** WC-008
**Date:** 2026-07-07
**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
**Constitutional Basis:** Constitution Article IX (Constitutional Floors — human override absolute, audit immutable); Constitution Article X (Right of Review); AD-009 (Observability by Default — security events are constitutional evidence)

---

## Assets Under Protection

| Asset | Sensitivity | Owner | Constitutional Status |
|---|---|---|---|
| Constitutional Audit Ledger | CRITICAL | Platform | Constitutional Floor — immutable, append-only (C-007) |
| Customer Decision Spaces | CRITICAL | Customer | Private contract configuration — breach enables unauthorized professional actions |
| Customer JWTs | HIGH | Customer | Authentication token — breach enables impersonation |
| PAAS Session State | HIGH | Customer | Trading session — breach enables unauthorized financial execution |
| Customer Evidence Data | HIGH | Customer | Private audit record — breach violates Article IX |
| LLM API Keys | HIGH | Platform | Cost and data exposure risk |
| Professional Experience Ledger | MEDIUM | Professional Identity | Privacy — portable, not tenant-scoped |
| Database Credentials | HIGH | Platform | Full DB access if leaked |
| Keycloak Admin Credentials | CRITICAL | Platform | Identity system root access |
| Temporal Workflow State | MEDIUM | Platform | Workflow data; breach could expose employment lifecycle events |

---

## Threat Actors

| Actor | Access Level | Motivation |
|---|---|---|
| **Unauthenticated external** | None | Financial gain, reconnaissance, DoS |
| **Authenticated customer (malicious)** | Own tenant only (JWT) | Access other tenants' data, manipulate own evidence |
| **Compromised service (lateral move)** | Internal network | Exfiltrate data, modify ledger, bypass Decision Space |
| **Malicious AI agent** | Decision Space execution | Exceed authorized Decision Space, exfiltrate customer data via LLM |
| **Insider (WAOOAW operator)** | Infrastructure access | Financial gain, sabotage |
| **Supply chain attacker** | Dependency injection | Code execution, secret exfiltration |

---

## STRIDE Analysis

### S — Spoofing

| Threat | Vector | Asset | Likelihood | Mitigation |
|---|---|---|---|---|
| **S-01** | JWT forgery: attacker crafts a JWT with a different `tenant_id` | Customer JWT | LOW (requires Keycloak private key) | JWT signature validation via Keycloak JWKS endpoint on every request. RS256 algorithm — asymmetric keys. Private key never leaves Keycloak. |
| **S-02** | Service impersonation: attacker poses as Constitutional Engine | gRPC internal | LOW (internal network) | mTLS on all service-to-service gRPC in cloud (ADR-007). Dev uses plain TLS; cloud uses mutual certificate auth. |
| **S-03** | Keycloak admin impersonation | Keycloak admin portal | MEDIUM | Keycloak admin port (8443) is not exposed publicly in cloud. Admin access via Azure Bastion or VPN only. |
| **S-04** | JWT replay attack: valid but expired token reused | Customer JWT | MEDIUM | Short-lived tokens (15-minute expiry enforced in Keycloak realm config). Refresh token rotation enabled — a refresh token can only be used once. |

### T — Tampering

| Threat | Vector | Asset | Likelihood | Mitigation |
|---|---|---|---|---|
| **T-01** | Constitutional Audit Ledger modification | Direct DB access | LOW (infra-level) | PostgreSQL RULE prevents UPDATE/DELETE. `constitutional_app` user has INSERT+SELECT only. DB credentials in Azure Key Vault. Disk encryption at rest (Azure managed). |
| **T-02** | Evidence record injection (forged evidence) | gRPC to Constitutional Engine | MEDIUM | CE validates `tenant_id` from gRPC metadata (sourced from customer JWT). A forged tenant_id requires a forged JWT (S-01 mitigated). CE never trusts caller-provided tenant_id in request body — metadata only. |
| **T-03** | Decision Space modification between validation and execution | In-memory PAAS state | LOW | Decision Space version checked on every CE ValidateAction call. Version mismatch → session halt (ADR-018 PAASSessionWorkflow). |
| **T-04** | Container image tampering in registry | GHCR | LOW | GitHub Actions builds images from source. Images signed with GitHub's signing key (GHCR attestation). No manual pushes to GHCR — only CI pipeline pushes. |
| **T-05** | Database migration tampering | EF Core migration files | LOW | Migrations are version-controlled. ADR-011: no destructive migrations on constitutional schema. CI validates migration against schema before applying. |

### R — Repudiation

| Threat | Vector | Asset | Likelihood | Mitigation |
|---|---|---|---|---|
| **R-01** | Customer denies approving an action | Approval workflow | MEDIUM | Every approval is a Constitutional Engine RecordEvidence call (state=APPROVED, constitutional_basis, recorded_at). The JWT identity of the approving user is recorded. Append-only — cannot be deleted. |
| **R-02** | Customer denies issuing Emergency Stop | Emergency Stop | LOW | Emergency Stop creates a EXECUTED evidence record with `stopped_by` (customer user ID from JWT). Append-only. |
| **R-03** | Platform denies receiving Emergency Stop | Emergency Stop | LOW | OTel trace captures the entire Emergency Stop path from WebSocket receipt to evidence confirmation. Trace ID is returned to customer. |
| **R-04** | Agent denies proposed action | Approval workflow | LOW | PROPOSED state record created before any action is submitted to customer for approval. Professional identity recorded. |

### I — Information Disclosure

| Threat | Vector | Asset | Likelihood | Mitigation |
|---|---|---|---|---|
| **I-01** | Cross-tenant data access via SQL | Customer Evidence | MEDIUM (without RLS) | PostgreSQL RLS enforced on all tenant-scoped tables. `SET LOCAL app.tenant_id` on every DB session from JWT. Row-level isolation is DB-enforced, not application-enforced. |
| **I-02** | Evidence data exposed via Business Platform API | Customer Evidence | MEDIUM (without auth) | JWT required on every Business Platform endpoint. `tenant_id` from JWT enforced at both application layer (middleware) and DB layer (RLS). |
| **I-03** | LLM provider leaks customer data | Inference requests | MEDIUM | Decision Space context is injected into system prompt — customer-specific data (business goals, prior decisions) is included. Mitigation: (a) Azure OpenAI within Azure tenant boundary; (b) Data Processing Agreement with LLM provider; (c) AI Runtime does not log prompt content by default; (d) OTel spans record action types but not content |
| **I-04** | Professional Experience Ledger cross-contamination | professional schema | LOW | Professional Experience Ledger uses `evidence_hash` (not raw evidence). No tenant_id on professional records — professional identity is platform-owned, not customer-owned (C-005). |
| **I-05** | Error messages expose internal details | API error responses | MEDIUM | Problem Detail RFC 9457 response format. Error messages never include stack traces in production. Internal error codes mapped to customer-facing messages by the API layer. |

### D — Denial of Service

| Threat | Vector | Asset | Likelihood | Mitigation |
|---|---|---|---|---|
| **D-01** | Emergency Stop path saturated | WebSocket | MEDIUM | Emergency Stop has a dedicated pre-warmed WebSocket connection — not shared with regular API traffic (DP-002). Container Apps WebSocket connections have separate scaling. Rate limiting does NOT apply to Emergency Stop path (DP-002 mandates it cannot be rate-limited). |
| **D-02** | Constitutional Engine overloaded | gRPC | HIGH (by design — CE is on every path) | CE scales horizontally (stateless — all state is in PostgreSQL). Container Apps scales CE replicas on CPU/request metrics. DB connection pool limits prevent DB overload. |
| **D-03** | API endpoint abuse (data scraping) | Business Platform REST | MEDIUM | ADR-006: ASP.NET Core rate limiting middleware. Per-tenant rate limits enforced at API layer. 429 responses for excess requests. |
| **D-04** | Temporal worker pool exhaustion | Temporal workflow execution | LOW | PAAS sessions are bounded by trading hours (ADR-005). Employment lifecycle workflows are infrequent. Temporal worker pool size is configured per environment. |
| **D-05** | LLM provider rate limit breach | AI Runtime | MEDIUM | AI Runtime has circuit breaker and exponential backoff. Tenant-level token budget tracked. Exceeding budget → ESCALATE response (Professional Runtime routes to customer for decision). |

### E — Elevation of Privilege

| Threat | Vector | Asset | Likelihood | Mitigation |
|---|---|---|---|---|
| **E-01** | AI agent exceeds Decision Space | LLM inference | MEDIUM | Decision Space injected into every LLM system prompt. Tool Registry validates every tool call against `authorizedActions`. CE ValidateAction enforces Decision Space at the API boundary — the LLM output is validated before execution, not just after. |
| **E-02** | Tenant A accesses Tenant B resources by manipulating request parameters | REST API | MEDIUM | `tenant_id` from JWT is the only authoritative source — URL parameters and request bodies claiming a different `tenant_id` are ignored. JWT `tenant_id` is set by Keycloak at login — not by the customer. |
| **E-03** | Professional Runtime calls CE with forged tenant_id | gRPC metadata | LOW | CE validates that the `x-tenant-id` gRPC metadata matches the JWT-derived tenant_id in the token passed by the calling service. Mismatches are rejected with PERMISSION_DENIED. |
| **E-04** | Authority expansion without evidence | Authority Manager | LOW | CE `GrantAuthorityLicense` requires `evidence_ids` (non-empty list). CE validates these IDs exist and belong to the correct contract. An expansion without evidence is rejected at the CE API layer. |
| **E-05** | Dependency supply chain attack | npm / NuGet / PyPI | MEDIUM | Dependabot monitors all dependencies. Snyk scans for CVEs. SBOM generated at build time. Only packages with verified publishers are used. |

---

## Constitutional Security Obligations

The following Constitutional Floors have direct security implications. They cannot be degraded by any security control:

| Floor | Implication | Security Requirement |
|---|---|---|
| Emergency Stop ≤250ms (C-001, AD-001) | Security controls on the Emergency Stop path must not add latency | Rate limiting MUST NOT apply to Emergency Stop WebSocket. mTLS handshake is pre-warmed. |
| Evidence immutability (C-007, AD-003) | No security incident may be used to justify evidence deletion | Incident response playbooks must not include "delete affected evidence records." |
| Audit trail completeness (C-023) | Security events are constitutional evidence | Security incidents (auth failures, permission denials, rate limit breaches) must produce OTel spans that are queryable as constitutional events. |
| Tenant isolation (C-005, AD-004) | A security breach affecting one tenant must not affect others | RLS is the last line of defence — it operates even if application-layer checks fail. |

---

## Security Findings Feeding Back to Architecture

1. **JWT claim validation must be explicit**: Business Platform middleware must validate: (a) `iss` = Keycloak issuer URL, (b) `aud` = waooaw-platform, (c) `exp` > now, (d) `tenant_id` claim present and UUID. Reject on any failure.
2. **CE gRPC metadata validation**: CE must extract `x-tenant-id` from metadata and cross-check against the JWT Bearer token in the same metadata. Both must match. See security-architecture.md for implementation pattern.
3. **AI Runtime tool allowlist must be in Decision Space**: The tool registry must refuse any tool not explicitly in `decision_space.authorized_tools`. Default deny. (C-003 applies — authority is a license, not a default.)
4. **No customer-provided tenant_id in request body**: All API endpoints must ignore `tenant_id` in request bodies. Tenant identification is from JWT only.

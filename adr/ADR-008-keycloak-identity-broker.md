# ADR-008: Identity — Keycloak as OAuth Federation Broker

**Status:** Accepted — v2 (2026-07-13: IDP expansion strategy + auth/authz tiering added)
**Date:** 2026-07-07 | **Last Updated:** 2026-07-13
**Roles Applied:** Security Architect (identity management) + Solution Architect (integration patterns)
**Constitutional Basis:** GENESIS Design Principles — Configuration over Code; Constitution Article IX (Customer Rights — right to identity continuity)

---

## Context

WAOOAW customers (dental clinics, beauty artists, traders, enterprises) need to authenticate. They expect social login (Google, Facebook, Apple) in addition to email/password. Multiple OAuth providers are required today and more will be added.

The question is: does each service integrate directly with each OAuth provider, or is there a federation layer?

## Decision

**Keycloak as the identity broker. Google is the default social provider. The application never talks directly to any OAuth provider.**

```
Customer: "Continue with Google"
  ↓
Customer Browser → Keycloak login page (auth.waooaw.com)
  ↓
Keycloak → Google OAuth (federation)
  ↓
Customer authenticates with Google
  ↓
Google → Keycloak (verified identity)
  ↓
Keycloak → Customer Browser (Keycloak JWT)
  ↓
Customer Browser → WAOOAW API (Bearer: Keycloak JWT)
```

Application services only ever see Keycloak JWTs. The OAuth provider used is irrelevant to the application.

**Provider rollout (all Keycloak configuration only, zero code changes):**
- Phase 1 (MVI): Google
- Phase 2: Facebook, Microsoft/Outlook
- Phase 3: Apple (requires Apple Developer account)

**Keycloak setup:**
- Self-hosted in Docker container (dev)
- Self-hosted in Azure Container App (cloud, same Container Apps environment)
- Realm: `waooaw`
- Client: `waooaw-platform`

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Direct OAuth per provider in each service | Each new provider requires code changes in Business Platform and Professional Runtime. Violates Configuration over Code. |
| Auth0 | Expensive at scale (per-user pricing). Vendor lock-in. Keycloak is open-source and self-hostable. |
| Azure AD B2C | Per-authentication pricing (~$0.0016/auth after 50k free). At 10,000 monthly active users = ~$16/month. Acceptable but creates Azure dependency. Keycloak preferred. |
| Clerk | Developer-friendly but vendor lock-in. No self-hosting option. |

## Consequences

**Benefits:**
- Adding a new OAuth provider = Keycloak admin configuration only (5 minutes)
- Application code is provider-agnostic from day one
- Keycloak is self-hostable — no per-auth pricing at any scale

**Trade-offs:**
- Keycloak requires operational management (updates, realm backup)
- Keycloak in Container Apps adds ~256MB RAM overhead
- In dev: Keycloak requires configuration on first run (realm setup via import)

**Operational note:**
- Keycloak realm configuration exported as JSON and version-controlled in `infrastructure/keycloak/`
- Container startup imports realm automatically — no manual configuration
- **Version pin:** Docker image pinned to a specific Keycloak minor version (e.g., `quay.io/keycloak/keycloak:25.0.6`). Floating `:latest` is prohibited — Keycloak has had breaking realm schema changes between major versions
- **Upgrade process:** Test upgrade in dev, export updated realm JSON, commit, promote through environments. Never upgrade directly in cloud without dev validation.
- **Realm backup:** Automated daily export of realm configuration included in platform backup job (see ADR-014 for secret management, including Keycloak client secrets)

---

## Identity Provider Expansion Strategy (v2 — 2026-07-13)

### Customer segments and their IDPs

| Customer segment | Primary IDP | Notes |
|---|---|---|
| Dental / beauty / fitness / retail | Google | 70-80% of Indian smartphone users; Android dominant |
| Bank branch managers | **Microsoft** | SBI, HDFC, Axis, ICICI run on Microsoft 365 |
| Insurance advisors (corporate) | **Microsoft** | LIC, Bajaj Allianz, ICICI Pru — Microsoft shops |
| Builders / professional services | Google or Microsoft | Mixed |
| Parents (Private Tutor) | Google + **Apple** | iOS ~20% India premium segment |
| Farmers / rural | **None** | WhatsApp phone-as-identity (ADR-023) |
| Trading customers | Google | Tech-forward audience |

### IDP Priority Decisions

| IDP | Priority | Decision | Reason |
|---|---|---|---|
| **Google OAuth 2.0** | P0 — Live | ✅ Implemented | 70-80% coverage. Default. |
| **Microsoft (Azure AD OIDC)** | **P1 — Phase 2** | ✅ Implement before banking segment | Bank branches, insurance, corporate professionals cannot use personal Google for business tools. Without this, the high-value B2B banking segment (DMA Skill 11) is blocked. Config: `login.microsoftonline.com/common/v2.0` — supports personal + corporate AAD in one endpoint. |
| **Apple Sign In** | **P1 — Required for iOS app** | ✅ Implement with iOS app | App Store rules §4.8: if ANY social login is offered, Apple Sign In MUST also be offered. Non-compliance = App Store rejection. Parent segment (Private Tutor) has ~25-30% iOS usage in urban India. |
| **LinkedIn** | P2 — Phase 3 | Defer | Useful for professional B2B segment. LinkedIn OAuth has been historically restrictive. Implement when B2B segment is proven. |
| **Facebook / Meta** | P3 — Explicitly deferred | ❌ Do not implement | Consumer-facing IDP; confusion with Meta Business Manager integration (ADR-026); DMA agent manages customer's Facebook Business Page — sharing the Facebook login IDP creates an identity boundary problem. Defer indefinitely. |

### Why Microsoft is P1 (not P2)

Corporate customers (bank branches, insurance advisors, builders with teams) cannot use personal Google accounts for a business procurement tool. This is corporate policy, not preference. Without Microsoft SSO, WAOOAW is locked out of every Indian bank's branch marketing budget — our highest CPL segment with highest LTV.

### Why Apple is P1 (conditional)

Not optional for App Store. Required by Apple's own rules. The Private Tutor parent segment has significant iOS penetration. Zero additional code — Keycloak configuration only.

---

## Authentication and Authorization Architecture (v2 — 2026-07-13)

### Three Authentication Paths

```
PATH 1 — Web/Portal (Keycloak OAuth)
  Customer → Keycloak → IDP (Google / Microsoft / Apple / LinkedIn)
  → JWT (15-min access + 8-hour refresh) → API → RLS (tenant_id)

PATH 2 — WhatsApp (Phone Identity — ADR-023)
  WhatsApp message → Meta webhook → Phone Identity Service
  → Session token (30 min) → RLS (organisation_id)
  High-risk actions: MPIN challenge tier (see ADR-023 v2)

PATH 3 — Service-to-Service (mTLS — ADR-007)
  Service A → mutual TLS → Service B
  CE gRPC: service certificates, not user JWTs
```

### Role-Based Authorization Within an Organisation

An organisation may have multiple users (owner + receptionist, trader + assistant). Roles are Keycloak realm roles embedded in the JWT:

```yaml
OWNER:    Full Decision Space authority. Can amend Employment Contract.
          Can Emergency Stop. Can approve any agent action.
MANAGER:  Can approve routine agent actions. Cannot amend contract.
          Cannot Emergency Stop.
VIEWER:   Read-only. Can see reports. Cannot approve or act.
```

JWT claim: `"waooaw_roles": ["OWNER"]`

Constitutional Engine validates: C-003 (authority must be licensed to the specific role). An MANAGER approval for a high-risk financial action is denied at the CE level regardless of what the Business Platform allows.

### JWT Claims Standard (extends ADR-003)

```yaml
sub:              Keycloak user UUID
tenant_id:        Multi-tenancy anchor (ADR-003)
organisation_id:  Session-scoped organisation
waooaw_roles:     [OWNER | MANAGER | VIEWER]
auth_path:        PORTAL | WHATSAPP | SERVICE
idp:              GOOGLE | MICROSOFT | APPLE | LINKEDIN | PHONE
exp / iss:        Standard JWT fields
```

The `auth_path` claim is consumed by the Constitutional Engine: a `WHATSAPP` session cannot approve HIGH-RISK actions unless the MPIN challenge has been completed in this session window (see ADR-023 v2).


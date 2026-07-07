# ADR-008: Identity — Keycloak as OAuth Federation Broker

**Status:** Accepted
**Date:** 2026-07-07
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

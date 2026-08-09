# ADR-008: Identity — Keycloak as OAuth Federation Broker

**Status:** Accepted — v3 (2026-08-09: FA-035 customer identity policy reconciliation; see Amendment 1)
**Date:** 2026-07-07 | **Last Updated:** 2026-08-09
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
- Phase 1 (MVI): Google + email fallback
- Phase 2: Facebook and Apple — designed under Amendment 1; activated independently when FA-002/FA-018 (Facebook) and FA-019 (Apple) prerequisites are satisfied
- Phase 3 (future): Microsoft/Outlook — bank branch and corporate segment

_Note: Amendment 1 (see below) supersedes the Phase 2/Phase 3 ordering for Facebook and Apple and records the FA-035 provider policy._

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
| **Apple Sign In** | P1 — Designed; BLOCKED by FA-019 | ⚠️ See Amendment 1 | App Store rules §4.8 and parent segment (Private Tutor ~25-30% iOS urban India) require Apple Sign In. FA-035 approves design now; activation gated on FA-019 Apple Developer account, Service ID, private key, and relay-domain configuration. |
| **LinkedIn** | P2 — Phase 3 | Defer | Useful for professional B2B segment. LinkedIn OAuth has been historically restrictive. Implement when B2B segment is proven. |
| **Facebook / Meta** | P2 — Designed; BLOCKED by FA-002/FA-018 | ⚠️ See Amendment 1 | FA-035 approves Facebook login with scope isolation; see Amendment 1 for isolation rules. Activation gated on FA-002 Meta Business Manager verification and FA-018 login app credentials. The identity boundary problem is resolved by mandatory scope and app separation — the login app and DMA Business OAuth are separate security principals. |

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

---

## Amendment 1 — FA-035 Customer Identity Policy Reconciliation (v3 — 2026-08-09)

**Authority:** FA-035 — Founder Yogesh Khandge, 2026-08-09
**Supersedes:** IDP Priority Decisions table rows for Facebook/Meta and Apple in v2; Phase 2/Phase 3 provider rollout ordering in the Decision section
**This amendment does NOT authorize:** implementation of any F2 or F3–F8 component, any provider activation, deployment to any environment, merge of any pull request, or any independent architecture review

### One Provider-Agnostic Customer Experience

FA-035 establishes that WAOOAW presents one unified customer experience offering `Continue with Google`, `Continue with Facebook`, `Continue with Apple`, and email-fallback options to new and returning customers. The experience is provider-agnostic: the application shell renders the same registration and sign-in flows regardless of which provider the customer selects. Keycloak remains the sole web credential authority; WAOOAW applications never call Google, Meta, or Apple identity APIs directly.

An unavailable provider is not displayed as active. The display set expands as each provider's activation evidence is accepted. All four providers are designed under this amendment; activation is independent and gated on provider-specific prerequisites.

### Customer Account Completion

Registration requires confirmed email before account completion. A customer may enter and explore without confirming mobile. Mobile verification is progressive: it must not block basic account entry or exploration, but is required before hiring, WhatsApp connection, payment initiation, recovery activation, sensitive account changes, or another server-classified consequential action.

### Provider Issuer/Subject Binding

The provider issuer and provider subject together are the binding key for a login method. Email address alone is not sufficient to identify a binding. A confirmed email from one provider does not automatically link to another login method that shares the same address. The stable provider subject is the durable key; email is an auxiliary claim that may change.

### Proof-of-Control Account Linking

Separate login methods may reconnect to one WAOOAW account only after a live proof-of-control challenge for the new method. The challenge is single-use, short-lived, bound to actor subject and intended command, and produces no account-existence disclosure at any step. Automatic email-only linking is prohibited.

### Non-Enumerating Behavior

No public operation discloses whether an email address, mobile number, tenant identifier, or provider subject is already registered. All identity error responses use stable non-enumerating codes. No response body, HTTP status differential, or timing variation reveals an account-existence fact.

### Facebook Login Scope Isolation

The Meta application used for Keycloak-brokered customer login is a separate security principal from the Meta Business Manager application used by the DMA agent (ADR-026). The customer-login Meta application:

- requests only `email` and `public_profile` scopes (basic login information);
- must never request page management, advertisement, post, contact, WhatsApp Business management, publishing, business-activity, DMA Business OAuth, or any other business or marketing permission;
- uses separate client ID, client secret, redirect URI, consent text, and app registration from the DMA Business OAuth application.

Customer-login Meta credentials and DMA Business OAuth credentials must not be shared, aliased, or combined under any configuration.

### Provider-Specific Activation Gates

Providers are enabled in Keycloak configuration only after their activation prerequisites are satisfied. This amendment records approved policy for all four providers; it does not satisfy or waive any activation gate.

| Provider | Activation status | Blocking prerequisites |
|---|---|---|
| Google | READY subject to environment configuration evidence | None |
| Email fallback | READY subject to Keycloak flow evidence | None |
| Facebook / Meta | **BLOCKED** | FA-002 — Meta Business Manager verification; FA-018 — customer-login app credentials and configuration evidence |
| Apple | **BLOCKED** | FA-019 — Apple Developer account, Service ID, private key, relay-domain configuration, and provider acceptance evidence |

Facebook activation remains gated on FA-002 and FA-018. Apple activation remains gated on FA-019. This amendment records the Founder-approved policy; activation requires separate completion of the named prerequisites.

### Authorization Boundary

This amendment records the Founder-approved customer identity policy (FA-035). It does not authorize implementation of any F2 or F3–F8 component; activate any identity provider; authorize deployment to any environment; authorize merge of any pull request; or constitute an independent architecture review of the WC-034 F2 identity and registration contract package. The independent architecture re-review (gate `G-F2-12`) must be performed in a separate context under C-065 before F2 implementation begins.


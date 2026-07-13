# ADR-002: OpenAPI Specification Strategy — Spec-First

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Solution Architect (API contract standards) + Enterprise Architect (platform-wide standard)
**Constitutional Basis:** GENESIS Part 02 — "Interfaces before implementations"; GENESIS Engineering Quality Mandate — "Every API traces to a business capability"

---

## Context

The WAOOAW platform exposes external APIs consumed by: web (Next.js), mobile (React Native / PWA), and future AI agents acting as customers. All four services produce or consume APIs. The question is whether the OpenAPI specification is written before the code (spec-first / contract-first) or generated from the code after the fact (code-first).

## Decision

**Spec-first (contract-first): OpenAPI 3.0 specifications are written and reviewed before implementation begins.**

Every endpoint in `src/*/api/` must have a corresponding entry in the OpenAPI spec before the implementation is coded. The spec is the source of truth. The implementation must conform to the spec — not the reverse.

OpenAPI specs live in: `architecture/reference/api-specs/`

Code generation tools may generate stubs from the spec, but the spec is never generated from code.

**Toolchain:**
- **Stub generation:** `openapi-generator-cli` — generates typed client SDKs for Next.js (TypeScript) and server stubs for .NET (NSwag) from the spec
- **Spec linting:** Spectral CLI (`@stoplight/spectral-cli`) — validates spec style and WAOOAW API conventions in CI
- **Contract conformance in CI:** `schemathesis` — runs property-based tests against a live service, verifying responses conform to the OpenAPI spec
- Specs live in `architecture/reference/api-specs/` — one file per service (e.g., `business-platform.openapi.yaml`)

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Code-first (generate spec from code) | Spec becomes an afterthought. When code changes, spec silently diverges. No independent review of API design before implementation effort is spent. Violates "Architecture before Implementation." |
| No OpenAPI at all | No contract for mobile clients, AI agents, or future third-party integrations. No automated contract testing. |

## Consequences

**Benefits:**
- API design is reviewable before a single line of implementation is written
- Client SDK generation from spec (Next.js, React Native) reduces implementation errors
- API contract tests (Pact or OpenAPI validation) can run against the spec independently
- AI Runtime Professional agents can read the spec to understand what endpoints exist

**Trade-offs:**
- Requires discipline: spec must be updated before implementation, not after
- Initial overhead to write specs before coding

**Enforcement:**
- Pull requests adding new endpoints must include the OpenAPI spec update
- CI pipeline validates that implementation responses conform to spec (automated)

---

## API Documentation Portal (v2 — 2026-07-13)

**Decision:** Add a `/api-docs` route to the Next.js web application that renders all WAOOAW OpenAPI specs through Redoc (lightweight, zero backend required). This is the "one-page view of all APIs" — zero additional infrastructure cost, no Azure API Management needed at MVI.

```
https://app.waooaw.com/api-docs
  → Redoc rendering of:
      architecture/reference/api-specs/business-platform.openapi.yaml
      architecture/reference/api-specs/professional-runtime.openapi.yaml
  → Authenticated route (OWNER/MANAGER roles only — not public)
  → Updated automatically when specs change in the repository
```

**Next.js implementation (no backend needed — static rendering from spec files):**
```typescript
// web/app/api-docs/page.tsx
// Uses: @redocly/react (embedded Redoc) OR Swagger UI React
// Spec files are bundled at build time from architecture/reference/api-specs/
// No separate documentation server needed
```

**Scope of the portal:**
| Spec | What it covers |
|---|---|
| business-platform.openapi.yaml | Employment lifecycle, marketplace, customer, billing APIs |
| professional-runtime.openapi.yaml | Agent execution, PAAS session, Emergency Stop APIs |
| Constitutional Engine (gRPC) | Proto contracts (linked from portal, not rendered inline) |

**What this replaces Azure API Management for (at MVI):**
- One-page API view: ✅ Redoc portal
- API documentation: ✅ OpenAPI specs (Redoc renders descriptions, examples, schemas)
- API versioning: ✅ URL versioning `/api/v1/` (see API Versioning Policy below)
- API change control: ✅ PR process + Spectral lint + buf breaking-change detection
- API analytics: ✅ OTel → Azure Monitor (ADR-009)

**Azure API Management remains deferred to Epoch 7** (third-party developer portal, API subscription keys, commercial API marketplace).

---

## API Versioning Policy (v2 — 2026-07-13)

All WAOOAW API endpoints use URL versioning:

```
/api/v1/organisations          — Employment lifecycle
/api/v1/agent/request          — Agent request submission
/api/v1/evidence/{id}          — Evidence record retrieval
/api/v1/whatsapp/webhook       — WhatsApp integration (not versioned — Meta controls this)
```

**Versioning rules:**
- **v1** is the only version until a breaking change is required
- A breaking change = new major version (v2); old version maintained for 6 months
- Non-breaking changes (new optional fields, new endpoints) stay in the current version
- Breaking change examples: removing a field, changing a field type, changing authentication

**buf `breaking` detection** (already in ci.yaml) catches gRPC breaking changes. Spectral rules catch REST breaking changes.

---

## Channel Adapter Pattern — API-Once Principle (v2 — 2026-07-13)

**The core design:** The Business Platform API is built once. Every channel (WhatsApp, web portal, mobile app, CLI) is an adapter that maps its input format to the same API calls.

```
Channel                 Adapter                     Business Platform API
──────────────────────────────────────────────────────────────────────────
WhatsApp message   →  WhatsApp webhook adapter  →  POST /api/v1/agent/request
Portal click       →  React/Next.js component   →  POST /api/v1/agent/request
Mobile app tap     →  React Native component    →  POST /api/v1/agent/request  (same)
CLI command        →  CLI tool (curl/httpie)     →  POST /api/v1/agent/request  (same)

WhatsApp approval  →  Webhook adapter            →  POST /api/v1/campaigns/{id}/approve
Portal approval    →  React component            →  POST /api/v1/campaigns/{id}/approve  (same)
```

**The agent never knows which channel was used.** The `auth_path` JWT claim (`WHATSAPP | PORTAL | MOBILE | CLI`) is metadata for the Constitutional Engine's risk tier decisions (ADR-023 v2), not for the agent's reasoning.

**Channel capabilities:**
| Feature | WhatsApp | Web Portal | Mobile App | CLI |
|---|---|---|---|---|
| Agent conversation | ✅ Primary | ✅ | ✅ | ✅ |
| Whiteboard (Tutor) | ❌ (image fallback) | ✅ | ✅ | ❌ |
| Progress reports | ✅ Voice + text | ✅ Full | ✅ Full | ✅ JSON |
| Emergency Stop | ✅ | ✅ | ✅ | ✅ |
| High-risk approvals | ✅ + MPIN | ✅ | ✅ | ❌ (portal redirect) |
| Demo/Interview mode | ✅ | ✅ | ✅ | ❌ |

**Implementation:** Each channel adapter is a thin layer in the Business Platform:
- `WhatsAppWebhookAdapter` — parses Meta webhook, maps to standard `AgentRequest` model
- `PortalController` — ASP.NET Core controller, standard REST
- `MobileController` — same as Portal (identical API, different auth header handling)
- Future CLI: scripts calling the REST API directly with Bearer token from `get-dev-token.sh`


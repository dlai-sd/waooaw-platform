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

# R-058 — WC-034 F2 Implementation Enterprise Architect Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `work_contract` | WC-034 / IB-014 / F2 Identity and Registration |
| `commits_reviewed` | `5d7bd0b` (Identity Boundary backend), `aa45053` (F2 web experience) |
| `architecture_review` | R-056 — APPROVED WITH NOTES |
| `record_id` | R-058 |
| `review_type` | Independent implementation architecture review under C-065 |
| `produced_at` | 2026-08-09 |
| **Decision** | **APPROVED WITH NOTES — CONDITIONS SATISFIED** |

## Independence Declaration

INST-004 did not author the reviewed implementation commits. The implementation was inspected in a fresh read-only review context against the approved Identity Boundary, canonical OpenAPI, ADR-008, ADR-023, WC-034 F2 decomposition, and F2 acceptance contract.

## Conformance Result

| Area | Result | Evidence |
|---|---|---|
| Canonical F2 operations | **PASS** | All 13 operations implemented in BP and generated `IdentityApi` |
| Provider boundary | **PASS** | Meta, Apple, and browser WhatsApp paths deny; Google/credential paths only |
| Actor and tenant isolation | **PASS** | Issuer + subject pre-account binding; tenant RLS on account links; normalized inaccessible response |
| Verification security | **PASS** | Cryptographic six-digit code, secret-backed HMAC, constant-time comparison, fail-closed dispatcher |
| Privacy and session boundary | **PASS** | Bearer token retained in encrypted server JWT only; no PII/code/token in URL or persistent browser storage |
| Idempotency and replay | **PASS** | Actor + operation family + key uniqueness; same-hash replay; divergent conflict |
| Web acceptance | **PASS** | Broker-gated registration, progressive verification, safe return target, expiry hiding, sign-out/account-switch cleanup |
| Scope boundary | **PASS** | No F3–F8, deployment, Facebook activation, or Apple activation |

## Review Conditions

### R058-01 — Profile request validation

**Status: RESOLVED**

`IdentityController.UpdateProfileAsync` now validates required values, OpenAPI maximum lengths, and the canonical locale pattern before reading idempotency state or invoking persistence. Four invalid-boundary cases assert `400 IDENTITY_REQUEST_INVALID`.

### R058-02 — Pre-account RLS rationale

**Status: RESOLVED**

Migration 20 now records why `identity.registrations` cannot use tenant RLS before account completion: the actor has no tenant. Every registration operation remains bound in the service to validated Keycloak issuer + subject; tenant RLS begins on post-account resources.

## Validation Evidence

| Gate | Result |
|---|---|
| Focused profile remediation | **PASS** — command chain completed before broader suites |
| Identity backend | **PASS** — 93/93 after remediation |
| Full Business Platform | **PASS** — 148/148 after remediation |
| Identity backend coverage | **PASS** — 97.26% unique source lines before four validation-only test cases |
| Web unit coverage | **PASS** — 52/52; 92.68% lines |
| Web static gates | **PASS** — TypeScript, lint, production build |
| F2 Chromium acceptance | **PASS** — 4/4 expanded and 360px; axe included |
| Existing Chromium acceptance | **PASS** — 24 passed, 3 intentional skips |
| Firefox/WebKit | **ENVIRONMENT BLOCKED** — pinned binaries installed; container lacks required shared libraries |

## Residual Activation Boundaries

1. `Identity:Hmac:Key` must be supplied from environment secret management; source contains no production secret.
2. Email/SMS delivery remains fail-closed until an approved environment dispatcher is configured.
3. The internal ADR-023 Phone Identity adapter must supply verified proof before WhatsApp account linking can activate.
4. Facebook and Apple activation, deployment, and F3–F8 remain separately gated and unauthorized.

## Decision

**APPROVED WITH NOTES — CONDITIONS SATISFIED.**

The WC-034 F2 implementation conforms to the approved architecture and is ready for pull-request constitutional review. This decision does not authorize deployment, provider activation beyond approved environment configuration, F3–F8 implementation, self-merge, or release.
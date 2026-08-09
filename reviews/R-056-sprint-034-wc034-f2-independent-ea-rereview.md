# R-056 — WC-034 F2 Independent Enterprise Architect Re-Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `work_contract` | WC-034 / IB-014 / F2 Identity and Registration |
| `pull_request_reviewed` | PR #248 |
| `commits_reviewed` | `4df595b` (INST-005 F2 remediation), `0b629c6` (INST-004 ADR-008 Amendment 1) |
| `prior_review` | R-055 — CHANGES REQUIRED (2026-08-09) |
| `security_consultation` | R-054 — CONCUR WITH BLOCKERS |
| `record_id` | R-056 |
| `review_type` | Independent architecture re-review under C-065 |
| `produced_at` | 2026-08-09 |
| **Decision** | **APPROVED WITH NOTES** |

## Independence Declaration

INST-004 did not author commits `4df595b` or `0b629c6` and did not modify any candidate architecture, API, or ADR contract to make them pass. This review is performed in a separate context under C-065 SDLC Separation of Duties.

## R-055 Required Corrections — Verification

### R055-01 — WhatsApp continuation is internal server-to-server (P0)

**Status: RESOLVED**

The `POST /api/v1/identity/registrations` operation description now explicitly states:
> "ADR-023 WhatsApp continuation uses an internal server-to-server Identity Boundary adapter, never this browser operation or a browser-held Phone Identity Service token."

The operation declares only `PreAccountBearerAuth: []` security — a Keycloak-issued, actor-bound registration JWT. No ADR-023 phone-identity security alternative is present and none is needed: the WhatsApp adapter is internal only. The `StartIdentityRegistrationRequest` schema contains only `languagePreference` with no phone proof or continuation token.

Component contract §2 confirms Phone Identity Service must not own "Keycloak sessions; web credentials; arbitrary phone-number claims from a browser." Component contract §12 adds: "ADR-023 WhatsApp continuation invokes the logical Identity Boundary through an internal server-to-server adapter. The Phone Identity Service token is never issued to a browser and cannot self-upgrade to a Keycloak session. Web continuation requires a Keycloak round trip and proof-gated binding."

No Phone Identity Service proof or token reaches the browser, is exposed as a public BP security scheme, or self-upgrades to a Keycloak session. Option B of the required correction is correctly implemented.

### R055-02 — Privacy-safe 400 responses and IDENTITY_RESOURCE_NOT_ACCESSIBLE (P0)

**Status: RESOLVED**

All 13 public F2 operations now declare `"400": { $ref: "#/components/responses/IdentityInvalidRequest" }`:

| # | Operation |
|---|---|
| 1 | `POST /api/v1/identity/registrations` |
| 2 | `GET /api/v1/identity/registrations/{registrationId}` |
| 3 | `PUT /api/v1/identity/registrations/{registrationId}/profile` |
| 4 | `POST /api/v1/identity/registrations/{registrationId}/email-verifications` |
| 5 | `POST /api/v1/identity/registrations/{registrationId}/email-verifications/confirm` |
| 6 | `POST /api/v1/identity/registrations/{registrationId}/mobile-verifications` |
| 7 | `POST /api/v1/identity/registrations/{registrationId}/mobile-verifications/confirm` |
| 8 | `POST /api/v1/identity/registrations/{registrationId}/complete` |
| 9 | `POST /api/v1/identity/account-links` |
| 10 | `POST /api/v1/identity/account-links/{linkId}/approve` |
| 11 | `GET /api/v1/identity/account-links/{linkId}` |
| 12 | `POST /api/v1/identity/mobile-verifications` |
| 13 | `POST /api/v1/identity/mobile-verifications/confirm` |

`IdentityProblemCode` enum now includes `IDENTITY_RESOURCE_NOT_ACCESSIBLE`. The `IdentityNotFound` response component description reads: "Identity resource is absent, inaccessible, or cross-tenant; one normalized shape and timing class prevents existence disclosure" and uses `IdentityProblemDetail` with `code: $ref IdentityProblemCode`. The component contract §9 error table lists HTTP 404 → `IDENTITY_RESOURCE_NOT_ACCESSIBLE`. Cross-tenant and inaccessible resources share one 404 shape and timing class; no distinguishable 403 leaks existence.

### R055-03 — Trailing whitespace (P1)

**Status: RESOLVED**

Command: `git diff --check origin/main...HEAD`
Result: empty output (exit 0) — no trailing whitespace on any changed line.

## Full F2 Conformance Assessment

### A. Identity Boundary, Ownership, and ADR-023 Adapter

| Check | Result | Evidence |
|---|---|---|
| WhatsApp continuation is internal adapter, not public operation | **PASS** | Operation description; `PreAccountBearerAuth` only; §12 adapter declaration |
| Phone Identity Service token never reaches browser or public API | **PASS** | §2 ownership "Must not own: ...arbitrary phone-number claims from a browser"; §12 |
| WhatsApp token cannot self-upgrade to Keycloak session | **PASS** | §12 explicit prohibition; Keycloak round trip required |
| Business Platform is sole public F2 REST facade | **PASS** | §2 ownership table; no second internet-facing container introduced |
| Keycloak is the only web credential authority | **PASS** | Invariant 1; all operations use `PreAccountBearerAuth` or `BearerAuth` |

### B. FA-035 Alignment

| FA-035 policy element | Contract evidence |
|---|---|
| Unified Google/Facebook/Apple/email fallback | ADR-008 Amendment 1 §One Provider-Agnostic Customer Experience; identity-boundary.md §3 all four providers listed |
| Confirmed-email completion | ADR-008 Amendment 1 §Customer Account Completion; identity-boundary.md Invariant 3, §5 READY_TO_COMPLETE requires confirmed email |
| Progressive mobile verification (not a registration blocker) | ADR-008 Amendment 1; identity-boundary.md §4 AAL3\_FRESH for consequential actions only; basic entry never requires mobile |
| Stable provider issuer/subject binding | ADR-008 Amendment 1 §Provider Issuer/Subject Binding; identity-boundary.md §6.1 provider subject key is issuer+broker subject |
| Proof-of-control account linking | ADR-008 Amendment 1 §Proof-of-Control Account Linking; identity-boundary.md §6 resolution matrix, §6.3 link challenge |
| No automatic email-only linking | ADR-008 Amendment 1 ("Automatic email-only linking is prohibited"); identity-boundary.md §6.1 ("Matching email is a candidate signal, never sufficient authority"), §6.4 |
| Non-enumerating behavior | ADR-008 Amendment 1 §Non-Enumerating Behavior; identity-boundary.md §6.2 (no /duplicate-check), §9 (stable codes), §10 (same timing class); OpenAPI IDENTITY\_RESOURCE\_NOT\_ACCESSIBLE |
| Facebook customer-login scope isolation | ADR-008 Amendment 1 §Facebook Login Scope Isolation; identity-boundary.md §3 Meta separation rule; separate client ID, secret, redirect URI, consent text |
| Independent provider activation gates | ADR-008 Amendment 1 activation gate table; identity-boundary.md §15 G-F2-03 BLOCKED/G-F2-14 BLOCKED; WC-034 F2 status |
| FA-035 in security/FOUNDER-ACTIONS.md | Completed actions table, correctly records all nine policy elements |

FA-035 is consistently reflected across `ADR-008-keycloak-identity-broker.md` (Amendment 1), `security/FOUNDER-ACTIONS.md`, `architecture/reference/components/identity-boundary.md`, `architecture/reference/api-specs/business-platform.openapi.yaml`, `architecture/reference/ux/wc-034-implementation-decomposition.md`, `work-contracts/WC-034-goal005-webportal-founder-admin.md`, and `constitution/PROJECT_STATE.md`.

### C. OpenAPI and Generated-Client Evidence

All validation executed using Docker only; no host Python or `.venv` used.

**Full-spec validation** (`openapitools/openapi-generator-cli:v7.17.0 validate`):
- Result: 28 errors — all are pre-existing dangling schema references for non-F2 paths (`/api/v1/billing/`, `/api/v1/digital-marketing/`, `/api/v1/approvals/`, `/api/v1/employment/skills/`, `/api/v1/payments/`)
- Zero errors on any `/api/v1/identity/` path or schema
- These dangling schemas are pre-existing and unrelated to the F2 surface (noted in prior session records for WC-057)

**F2-filtered spec generation** (`openapitools/openapi-generator-cli:v7.17.0 generate -g typescript-fetch`):
- 13 identity operations extracted into standalone spec
- Generation: succeeded — `IdentityApi.ts` produced, no generator errors
- `tenantId` parameter check in `IdentityApi.ts`: absent — no request parameter named `tenantId`

**Strict TypeScript compilation** (`node:22-alpine`, `typescript@5`, `--strict --noEmit --target ES2020 --lib DOM,ES2020`):
- Command: `npx tsc --strict --noEmit --target ES2020 --moduleResolution node --module commonjs --lib DOM,ES2020 apis/IdentityApi.ts models/index.ts runtime.ts`
- Result: Exit 0 — no TypeScript errors
- Note: DOM lib required for `typescript-fetch` generator output (fetch/Response/URLSearchParams browser types); this is the standard compilation environment for this generator

**Evidence conclusion:** The F2 surface generates and compiles cleanly. Pre-existing non-F2 dangling schemas are documented; they do not originate from this PR.

### D. Ownership, Assurance, Tenant, Idempotency, Session

| Area | Result | Evidence |
|---|---|---|
| Confirmed email before account completion | **PASS** | §1 Invariant 3; §5 READY_TO_COMPLETE; §9 IDENTITY_VERIFICATION_REQUIRED (422) |
| AAL3_FRESH ≤ 5 minutes for consequential actions | **PASS** | §4.1 assurance table; §4.2 bound step-up intent |
| Token refresh does not satisfy freshness | **PASS** | §4.1 explicit statement |
| Tenant never accepted from request body/query/URL | **PASS** | §1 Invariant 7; §12 privacy; no tenantId parameter in generated client |
| Same idempotency key + same hash = replay; different hash = IDENTITY_IDEMPOTENCY_CONFLICT | **PASS** | §1 Invariant 8; §10; operation responses |
| Cross-tenant 404 matches absent 404 (IDENTITY_RESOURCE_NOT_ACCESSIBLE) | **PASS** | §9 table; identity-boundary.md "Cross-tenant and inaccessible identity resources use the same 404 not-accessible response shape" |
| Sign-out clears server session, browser memory, protected drafts | **PASS** | §11 sign-out and account switch |
| Account switch sentinel test required | **PASS** | §11; UX-PWA-04 mapping (§13) |

### E. git diff --check R055-03 Verification

```
$ git diff --check origin/main...HEAD
[no output — exit 0]
```
PASS — no trailing whitespace on any line in the diff.

## G-F2 Gate Re-evaluation

| Gate | Status | Owner | Evidence / Missing |
|---|---|---|---|
| `G-F2-01` F1 foundation | **READY** | INST-010 / INST-004 | R-052 approved; PR #246 merged as `798c183` |
| `G-F2-02` ADR-008 FA-035 reconciliation | **READY** | INST-004 | ADR-008 v3 Amendment 1 complete; one provider-agnostic experience, confirmed-email, progressive mobile, provider-subject binding, proof-of-control linking, no email-only auto-linking, non-enumerating behavior, Facebook scope isolation, independent activation gates — all recorded |
| `G-F2-03` Meta environment prerequisites | **BLOCKED** | Founder | FA-002 (Meta BM verification) and FA-018 (login app credentials) — prerequisite Founder actions only; does NOT block architecture contract approval |
| `G-F2-04` Google broker path | **READY** | Keycloak/identity owner | Contract present; environment proof is implementation acceptance |
| `G-F2-05` Credential path with second factor | **READY** | Keycloak/identity owner | Contract present; realm-flow evidence required during implementation |
| `G-F2-06` Confirmed email and progressive mobile | **READY** | Founder / INST-004 | FA-035 and component contract present |
| `G-F2-07` WhatsApp identity and linking | **READY** | INST-007 / ADR-023 | Proof-gated link contract and ADR-023 present; R055-01 resolved |
| `G-F2-08` Canonical API and TypeScript compatibility | **READY** | INST-005 / BP owner | R055-01 and R055-02 resolved; generation and compilation pass (this review) |
| `G-F2-09` Tenant, retry, error contracts | **READY** | INST-005 + INST-007 | R055-02 resolved; complete error table in contract and OpenAPI |
| `G-F2-10` Component/skeleton determination | **READY** | INST-005 / INST-004 | Identity Boundary is logical BP component; no new deployable service; OpenAPI is implementation skeleton |
| `G-F2-11` F2 implementation authorization | **READY, NOT ACTIVATED** | Founder | FA-031 and FA-034 apply when all local entry gates pass |
| `G-F2-12` Independent architecture re-review | **CLOSED by this review** | INST-004 | R-056 APPROVED WITH NOTES |
| `G-F2-13` Deployment authorization | **BLOCKED** | Founder / release authority | Separate deployment authorization and release evidence; outside F2 grooming |
| `G-F2-14` Apple login environment prerequisites | **BLOCKED** | Founder | FA-019 (Apple Developer, Service ID, private key, relay-domain) — prerequisite Founder actions only; does NOT block architecture contract approval |

### Gate assessment note

Provider activation gates G-F2-03 (Facebook) and G-F2-14 (Apple) are correctly blocked. Neither gate blocks architecture contract approval — they block the activation of those specific providers in Keycloak configuration. The F2 architecture contract is approved for Google and email-fallback activation and designs Facebook/Apple correctly for later activation. Deployment gate G-F2-13 is independently blocked and is not requested by this package.

## ADR-008 Meta/Facebook Disposition

ADR-008 Amendment 1 (v3, 2026-08-09, FA-035) is a correctly authorized INST-004 amendment. It:
- records the Founder-approved one provider-agnostic experience;
- distinguishes the customer-login Meta application from the DMA Business Manager OAuth application with explicit scope, credential, and principal separation;
- keeps Facebook and Apple activation gated on FA-002/FA-018 and FA-019 respectively;
- explicitly states it does not authorize implementation, activation, deployment, or merge.

`G-F2-02` is now READY. This resolves the Founder blocker named in R-055. The Meta login scope-isolation rule in Amendment 1 is sufficient to approve the Facebook design for later activation; it does not activate Facebook.

## Scope and Exclusions (Retained)

This review covers:
- R-055 required corrections (R055-01 through R055-03)
- FA-035 alignment across all named documents
- ADR-008 Amendment 1 accuracy and authorization
- G-F2 gate re-evaluation

This review expressly does NOT authorize:
- F3 through F8 implementation
- Application code, private endpoints, Employment Relationships, payment behavior
- Facebook provider activation (blocked by G-F2-03 / FA-002 / FA-018)
- Apple provider activation (blocked by G-F2-14 / FA-019)
- Deployment to any environment
- Merge of PR #248
- WC-057 or WC-058 through WC-060

## Decision

**APPROVED WITH NOTES.**

The WC-034 F2 Identity and Registration architecture and API contract package is architecture-approved for implementation selection. All three R-055 required corrections are independently verified as resolved. FA-035 alignment is confirmed across all named documents. The G-F2-12 independent re-review checkpoint is closed by this record.

**F2 is architecture-approved for later implementation selection under FA-031 and FA-034** when remaining local entry gates pass (provider environment configuration for Google and email-fallback; G-F2-03 and G-F2-14 for Facebook and Apple respectively).

### Notes (non-blocking, for implementation awareness)

1. **Pre-existing non-F2 dangling schemas**: The full canonical `business-platform.openapi.yaml` contains 28 pre-existing dangling schema references for non-F2 service surfaces (`billing`, `digital-marketing`, `approvals`, `skills`, `payments`). These are not introduced by this PR and do not affect the F2 surface or generated-client correctness. They should be resolved when those service surfaces are specified and implemented.
2. **Provider activation gates remain independently blocked**: G-F2-03 (Facebook) and G-F2-14 (Apple) correctly require Founder-completed FA-002/FA-018 and FA-019 before those providers are enabled in Keycloak. This is architecture-intended behavior, not a gap.
3. **Deployment authorization is not requested and remains blocked**: G-F2-13 is independently gated and requires a separate Founder action.

### Next Constitutional Action

INST-010 may proceed with F2 implementation under FA-031 and FA-034 authority when Google and email-fallback provider environment configuration evidence is present. Facebook and Apple implementation may begin but activation requires G-F2-03 and G-F2-14 evidence respectively. Deployment authorization (G-F2-13) requires a separate Founder action. PR #248 may not be merged without Founder review.

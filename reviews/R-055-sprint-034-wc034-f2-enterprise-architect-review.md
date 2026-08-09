# R-055 — WC-034 F2 Enterprise Architect Review

| Field | Value |
|---|---|
| `institution_id` | INST-004 |
| `work_contract` | WC-034 / IB-014 / F2 Identity and Registration |
| `pull_request_reviewed` | PR #248 |
| `commits_reviewed` | `c36b438`, `054bfe8` |
| `security_consultation` | R-054 — CONCUR WITH BLOCKERS |
| `record_id` | R-055 |
| `review_type` | Independent architecture and contract review |
| `produced_at` | 2026-08-09 |
| Decision | **CHANGES REQUIRED** |

## Scope and Independence

INST-004 independently reviewed only WC-034 Phase B F2 Identity and Registration. This review does not assess or authorize F3–F8, application implementation, deployment, or merge. The reviewer did not author commits `c36b438` or `054bfe8` and did not modify the candidate component or API contracts.

## Conformance Summary

| Area | Result | Evidence |
|---|---|---|
| Keycloak, Identity Boundary, Phone Identity Service, BP, and Next.js ownership | **PASS** | Keycloak exclusively owns web credentials; the logical Identity Boundary owns registration and proof-gated resolution; Phone Identity Service owns ADR-023 webhook proof; BP is the sole public REST facade and tenant/account minter; Next.js owns routes, server-session exchange, safe targets, generated-client use, and cleanup presentation. |
| Mandatory verified email and mobile | **PASS** | Completion requires both proof flags; unverified provider claims lead to separate verification and `422 IDENTITY_VERIFICATION_REQUIRED`. |
| Deterministic, non-enumerating duplicate resolution | **PASS** | Resolution follows a proof-gated matrix, split-account matches never auto-merge, public duplicate lookup is prohibited, and created/reused outcomes have identical customer treatment. |
| Progressive assurance and fresh step-up | **PASS** | `AAL3_FRESH` is bounded to five minutes; refresh does not satisfy freshness; intents are opaque, bound, single-use, and revalidated before command resumption. |
| Tenant isolation, idempotency, retries, and privacy | **PASS WITH FINDING R055-02** | Tenant is server-minted and session-derived, every mutation has `Idempotency-Key`, unknown outcomes are reconciled before retry, and secrets/identity values are excluded from URLs, logs, telemetry, and caches. The canonical error response inventory is incomplete. |
| Safe return targets, session expiry, sign-out, and account switch | **PASS** | Targets are server-owned identifiers with origin/authorization revalidation; protected content hides immediately; account switch performs full account-scoped cleanup with sentinel evidence. |
| Canonical OpenAPI and generated TypeScript compatibility | **PASS WITH FINDINGS R055-01/R055-02** | Generator `7.17.0` produced the full client; generated `IdentityApi.ts` compiled under strict TypeScript and exposed no `tenantId`. The generated contract nevertheless omits one promised authentication path and required error outcomes. |
| Requested UX acceptance mapping | **PASS** | The package maps UX-SHELL-02, UX-SHELL-04, UX-AUTH-01 through UX-AUTH-06, UX-PRIV-01, and UX-PWA-04 to concrete contract evidence consistent with the parent acceptance definitions. |
| F2-only scope | **PASS** | The PR contains architecture, OpenAPI, review, Work Contract, and state records only. It creates no application code, private endpoint, deployment artifact, Employment Relationship, payment behavior, or F3–F8 contract. |

## Findings

### R055-01 — P0 — The canonical API cannot start the promised WhatsApp continuation path

The component contract states that `POST /api/v1/identity/registrations` accepts either a pre-account Keycloak bearer or an approved channel continuation proof, and `StartIdentityRegistrationRequest.authenticationPath` includes `WHATSAPP`. The canonical OpenAPI operation permits only `PreAccountBearerAuth`, whose scheme description explicitly requires a Keycloak-issued registration JWT. No ADR-023 continuation security scheme or documented internal-adapter alternative exists in the canonical API.

This leaves the WhatsApp-first registration/completion path promised by F2 and ADR-023 unrepresentable in generated clients and server contract enforcement.

**Required correction:** choose and specify one approved boundary: either add an explicit actor-bound ADR-023 continuation security alternative to the operation, or state that the WhatsApp adapter invokes the logical Identity Boundary internally and remove the public-operation continuation claim. The browser must never receive the internal Phone Identity Service token, and a WhatsApp token must not self-upgrade to a Keycloak session.

### R055-02 — P0 — The canonical privacy-safe error contract is not closed

The component contract requires stable privacy-safe codes for every F2 error, including `400 IDENTITY_REQUEST_INVALID`, and requires inaccessible or cross-tenant identity resources to use a normalized 404 response. All eleven identity operations omit a `400` response. Nine operations reference `IdentityNotFound`, but the required `IdentityProblemDetail.code` enum has no not-found/not-accessible value. `IDENTITY_ACTION_DENIED` is normatively assigned to HTTP 403 and cannot consistently represent the promised 404 outcome.

The OpenAPI therefore cannot express two outcomes required by the component contract, and generated clients cannot handle them deterministically.

**Required correction:** add the applicable privacy-safe `400` response to F2 operations and define a stable non-enumerating 404/not-accessible problem code in both the component error table and `IdentityProblemCode`. Preserve one response shape and timing class for absent, inaccessible, and cross-tenant resources.

### R055-03 — P1 — The submitted validation record overstates `git diff --check`

PR #248 reports `git diff --check: PASS`, but the independent command fails on seven trailing-whitespace lines in `architecture/reference/components/identity-boundary.md`.

**Required correction:** remove the whitespace errors and replace the claimed evidence only after `git diff --check origin/main...HEAD` passes.

## ADR-008 Meta/Facebook Disposition

ADR-008 v2 is accepted and explicitly says Facebook/Meta is indefinitely deferred and must not be implemented. FA-018 records a later intent to create a portal-login Facebook application, but it remains PENDING and depends on pending FA-002. Enabling Meta login changes accepted provider policy; INST-004 cannot infer Founder approval from a pending action item.

`G-F2-02` therefore remains a named **Founder blocker**. The Founder must decide whether Meta login enters F2. If approved, INST-004 may then draft an ADR-008 amendment that distinguishes the least-privilege customer-login application from DMA Business OAuth. Until that amendment is approved, Meta login must not be implemented or activated.

## Dependency Gate Validation

| Gate | Review status | Owner | Missing artifact or evidence |
|---|---|---|---|
| `G-F2-01` F1 foundation | **READY** | INST-010 / INST-004 | None — R-052 and merged PR #246 recorded |
| `G-F2-02` ADR-008 Meta disposition | **BLOCKED** | Founder decision; INST-004 drafts amendment after approval | Founder Meta-login disposition and approved ADR-008 amendment |
| `G-F2-03` Meta environment | **BLOCKED** | Founder | Completed FA-002 and FA-018 evidence |
| `G-F2-04` Google broker contract | **READY** | Keycloak/identity implementation owner | Environment proof remains implementation acceptance evidence |
| `G-F2-05` credential/second-factor contract | **READY** | Keycloak/identity implementation owner | Realm-flow proof remains implementation acceptance evidence |
| `G-F2-06` verified email/mobile policy | **READY** | Founder / INST-004 | None |
| `G-F2-07` WhatsApp identity and assurance rules | **READY** | INST-007 / ADR-023 owner | None at architecture level; R055-01 blocks canonical API closure |
| `G-F2-08` canonical BP API/client compatibility | **BLOCKED** | INST-005 / BP specification owner | Correct R055-01 and R055-02; regenerate and compile the F2 client |
| `G-F2-09` tenant/retry/error contracts | **BLOCKED** | INST-005 with INST-007 concurrence | Correct the canonical error outcomes in R055-02 |
| `G-F2-10` component/skeleton determination | **READY** | INST-005 / INST-004 | None — logical BP component; no new deployable service |
| `G-F2-11` conditional implementation authorization | **READY, NOT ACTIVATED** | Founder | Local entry gates must all pass before FA-031/FA-034 can be exercised for F2 |
| `G-F2-12` independent architecture review | **BLOCKED** | INST-004 | Remediation of R055-01 through R055-03 and independent confirmation |
| `G-F2-13` deployment authorization | **BLOCKED** | Founder / release authority | Separate deployment authorization and release evidence |

## Independent Validation

- PR delta: seven architecture/governance files; zero application or runtime source files.
- OpenAPI: 11 F2 operations; focused F2 references generate successfully.
- Pinned OpenAPI Generator `7.17.0`: full TypeScript client generated in the official container.
- Strict TypeScript: generated `IdentityApi.ts` compiled in the Docker test runner.
- Generated Identity API: no `tenantId` request parameter.
- Structural error/auth check: 0/11 operations declare `400`; registration declares only Keycloak `PreAccountBearerAuth`; no stable 404 identity problem code exists.
- `git diff --check origin/main...HEAD`: **FAIL** on seven changed lines.

## Decision

**CHANGES REQUIRED.**

The ownership, assurance, tenant, retry, privacy, session, PWA, and UX structures are directionally approved, but the canonical API does not yet represent the complete F2 authentication and error contract. F2 implementation remains blocked pending R055-01 through R055-03 remediation and independent confirmation. The ADR-008 Meta policy decision remains a Founder blocker. This review does not authorize implementation, F3–F8, deployment, or merge.
# Work Contract 057 — AE-01 Employment Journey Foundation

**Goal:** GOAL-005 — Agent Employment Experience Program
**Epic:** AE-01
**Office on execution:** Platform IT Expert (INST-010)
**Reviewer:** Enterprise Architect (INST-004)
**Status:** IMPLEMENTATION COMPLETE — INDEPENDENT REVIEW PENDING
**Authorization:** FA-030 — Founder authorized implementation on 2026-08-08: “Authorize implementation of WC-057.”
**Track:** DIFFERENTIAL — Business Platform persistence and API + GREENFIELD customer web shell
**Service scope:** Business Platform (.NET 9), PostgreSQL, Next.js customer interface, reference OpenAPI/manifest artifacts

## Sprint Goal

Establish one durable, tenant-scoped Employment Relationship aggregate and a real customer journey shell. Replace placeholder employment endpoints with persisted, versioned state and expose a channel-neutral API that later slices use without allowing channel sessions, contracts, payments, or conversations to become relationship identity.

## Dependencies

- D-07 GOAL-005 ratification and separate Founder implementation authorization.
- WC-037 Audit Sink, WC-040 Skill Catalog, WC-041 Skill Runtime: DONE.
- D-02 AEEC, D-03 identity/state model, D-04 continuity contract: accepted inputs.
- Migration slots 01 through 18 are immutable; this contract owns new slot 19.
- The D-06 Business, Solution, Data, and Security contracts listed under Required Inputs are normative. Implementation may not replace their keys, states, APIs, ownership, RLS, or assurance rules without a new architecture review.

## Tasks

| Task | Scope | Model hint | Status |
|---|---|---|---|
| WC057-01 | Apply the exact Migration 19 blueprint in the D-06 Data Contract: relationship, participant-role binding, state history, and idempotency tables; canonical first-mint key; RLS; correlation indexes and benchmark. Channel bindings belong to Migration 22. Do not modify migrations 01–18. | reasoning | complete |
| WC057-02 | Add EF Core models and `EmploymentRelationshipDbContext` under `src/business-platform/Infrastructure/`; register the JWT-derived tenant setting/interceptor. Model D-03 and the participant-role contract exactly; reject illegal transitions and append state history only after CE validation/evidence commitment. | reasoning | complete |
| WC057-03 | Route the existing contract and hire endpoints inventoried in the D-06 Solution Contract through one `EmploymentRelationshipService`. Preserve response compatibility through explicit adapters and deprecation headers; do not retain duplicate lifecycle logic. | reasoning | complete |
| WC057-04 | Implement the canonical relationship create/read/timeline endpoints in the D-06 Solution Contract and an internal transition endpoint restricted to service JWT. Every request resolves tenant and participant role from authenticated identity, never payload hints. | auto | complete |
| WC057-05 | Complete the WC-016 Next.js 14 App Router PWA under the component structure in the D-06 Solution Contract. Use Keycloak secure session handling and the generated OpenAPI client; implement responsive authenticated journey state, rights, and persistent Stop entry point with WCAG 2.1 AA, axe, Jest/Testing Library, Playwright, and changed-line coverage gates. | reasoning | complete — provisional UI shell |
| WC057-06 | Update BP component spec, BP manifest, canonical OpenAPI source, and C-059 headers. Generated Swagger/proto/build artifacts are regenerated, never hand-edited. | auto | complete |
| WC057-07 | Add CCTs and integration tests for relationship first mint/retry reuse, illegal transitions, tenant isolation, channel identity non-equivalence, evidence-before-success, and web authentication/state presentation. | auto | complete |

## Implementation Evidence

- Commits: `c5169cc` (relationship persistence/API foundation) and `e458e42` (compatibility adapters, OpenAPI-generated web client, and PWA shell).
- Business Platform: 55/55 tests passed; project build passed with six pre-existing tenant-interceptor nullability warnings.
- Web: 5/5 Jest tests passed; changed interactive components reached 93.75% line coverage against the 90% gate; lint, strict type checking, and production build passed.
- Browser acceptance: Playwright passed desktop Chromium and exact 360px mobile projects with an installable manifest, no horizontal overflow, and zero critical axe violations.
- Platform metadata: focused platform-state and blueprint checks passed 12 tests with one pre-existing manual-check skip.
- Migration 19 focused assertions passed duplicate-admission arbitration, append-only history, and cross-tenant invisibility. A full fresh database bootstrap remains blocked by the pre-existing Migration 03 enum/search-path defect and was not repaired under WC-057.

**UI decision boundary:** The Next.js relationship workspace is a provisional technical acceptance shell required by WC057-05. Its visual and product design has not been Founder-confirmed and remains subject to later review and adjustment without changing the canonical relationship API or constitutional controls.

## Required Inputs

`goals/GOAL-005-D03-identity-employment-state-model.md` · `goals/GOAL-005-D03-data-semantics.md` · `architecture/reference/product/agent-employment-experience-contract.md` · `architecture/reference/product/omnichannel-continuity-contract.md` · `architecture/reference/product/ae01-business-boundary-contract.md` · `architecture/reference/product/ae01-solution-contract.md` · `architecture/reference/product/ae01-relationship-data-contract.md` · `architecture/reference/product/ae01-security-contract.md` · `architecture/reference/components/business-platform.md` · `architecture/reference/api-specs/business-platform.openapi.yaml` · ADR-003 · ADR-017 · ADR-044 · WC-016.

## Constitutional Compliance Tests

| CCT | Assertion |
|---|---|
| CCT-AE01-REL-01 | Duplicate/retried first admission returns the same relationship identity |
| CCT-AE01-REL-02 | Conversation, contract, payment, participant, and channel IDs cannot substitute for relationship ID |
| CCT-AE01-STATE-01 | Every illegal D-03 transition is denied with zero mutation and attributable evidence |
| CCT-AE01-TENANT-01 | Another tenant cannot retrieve or mutate relationship state or timeline |
| CCT-AE01-EF-01 | No transition reports success unless constitutional evidence commits |
| CCT-AE01-WEB-01 | Authenticated customer sees correct trial/live state, rights, and Stop entry point on mobile and desktop |

## Definition of Done

- One persisted Employment Relationship aggregate owns lifecycle truth and reconstructable history.
- Existing public BP behavior remains compatible or has a documented versioned migration path.
- All BP queries use JWT-derived tenant context and PostgreSQL RLS.
- The customer web app builds and supports authenticated journey routing; static-only interface debt is removed.
- OpenAPI and BP manifest match executable endpoints.
- CCTs pass; BP build/tests, web build/tests, lint, migration application, and `git diff --check` are clean.
- VERSION, CHANGELOG, SPRINT-REGISTRY, PROJECT_STATE, and component maturity evidence are updated only after executable proof.

## Validation Commands

```bash
docker compose --profile test run --rm test-runner dotnet test tests/business-platform.Tests/
docker compose --profile test run --rm test-runner npm --prefix web test
docker compose --profile test run --rm test-runner npm --prefix web run build
docker compose --profile test-python run --rm test-runner-python pytest tests/platform/test_platform_state_sync.py -q
```

## Boundaries

No professional matching, trial orchestration, contract acceptance, payment, provider execution, or channel handoff is implemented here. FA-030 authorized WC-057 only; WC-058 through WC-060 remain separately gated and unauthorized.
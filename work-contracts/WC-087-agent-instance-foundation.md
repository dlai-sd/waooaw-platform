# WC-087 - Agent Instance And Multi-Agent Foundation

**Office:** Platform IT Expert (INST-010)
**Assigned by:** Founder instruction, 2026-09-10
**Status:** IMPLEMENTED - PR PENDING
**Branch:** `ib/087/agent-instance`
**Baseline:** `origin/main` at `44afa9f4402ca6b106014e71e323af7f9134f5e5`
**Predecessor:** WC-085 remediation merged through PR #409
**Constitutional basis:** C-023, C-026, C-032, C-059, C-065

## 1. Objective

Give every canonical employment relationship one immutable agent-instance identity. Bind that
instance to the exact admitted professional type and version while preserving `relationshipId` as
the customer-specific employment, authority, goals, skills, contract, billing, and evidence boundary.

The implementation must prove that one customer can create two relationships for the same
professional type without either relationship or agent instance colliding.

## 2. Founder Authority

The Founder authorized autonomous implementation on 2026-09-10 and accepted D-BILLING and
D-IDENTITY as prepared. This Work Contract covers only Delivery 1, Agent Instance and Multi-Agent
Foundation. The accepted billing and identity contracts remain separate bounded deliveries.

## 3. Binding Contract

- One `agentInstanceId` is minted when a new employment relationship is admitted.
- An idempotent replay of the same admission returns the existing relationship and instance.
- A distinct evaluation intent creates a distinct relationship and agent instance, including when
  the customer and professional type are the same.
- The instance records the exact admitted professional version. No default or inferred version may
  substitute for an admitted version.
- The agent-instance identity is immutable for the lifetime of the relationship.
- No two relationships can bind the same agent-instance identity, including across tenants.
- Professional Runtime receives the instance identity, professional type, and admitted version when
  starting the relationship's trial workflow.
- Existing `relationshipId` references and compatibility adapters remain valid.

## 4. Scope

1. Append-only PostgreSQL migration for the agent-instance binding and immutability constraints.
2. Business Platform entity, persistence, admission, projections, and OpenAPI changes.
3. Professional Runtime trial-start contract propagation and validation.
4. Generated client regeneration required by the OpenAPI change.
5. Focused unit, PostgreSQL integration, controller, and contract tests.

## 5. Exclusions And Reminders

- Delivery 2 owns the customer-facing catalogue, My Experts, relationship switching, and governed
  skill selection/update/accept/defer journey.
- D-BILLING is accepted but remains a separate delivery: WBE-owned customer-global projection, BP
  facade, portal destination, provenance/freshness, and typed partial/unavailable behavior.
- D-IDENTITY is accepted but remains a separate delivery: link-method, remove-method, and
  security-action intents with fresh assurance, replay protection, safe targets, and last-method
  protection.
- No Demo deployment, Production operation, DNS change, customer traffic, or merge is authorized by
  this Work Contract.

## 6. Success Criteria

| ID | Criterion |
|---|---|
| AI-01 | A new relationship receives a non-empty immutable `agentInstanceId`. |
| AI-02 | Admission replay returns the original relationship and agent instance. |
| AI-03 | One customer can admit two instances of the same professional type using distinct evaluation intents. |
| AI-04 | Each instance is bound to an explicitly admitted professional type and exact version. |
| AI-05 | Trial start sends the instance identity and admitted version to Professional Runtime. |
| AI-06 | Cross-tenant relationship lookup and duplicate global agent-instance binding are denied. |
| AI-07 | Existing canonical and compatibility relationship journeys remain compatible. |
| AI-08 | Focused tests and the applicable Docker qualification pass. |
| AI-09 | Applicable pre-PR checks pass before the PR is submitted for Founder review. |

## 7. Evidence Plan

- Run the cheapest focused service test immediately after the first implementation edit.
- Run focused PostgreSQL migration tests after the schema milestone.
- Run focused controller, OpenAPI, generated-client, and Professional Runtime contract tests after
  their owning slices.
- Batch broader Docker qualification after Delivery 1 is functionally complete.
- Record exact commands, outcomes, commit, and image evidence before opening the PR.

## 8. Stop Conditions

Stop and raise a blocker if the admitted professional version cannot be resolved without guessing,
if an existing relationship would be rebound to a different agent instance, if runtime owners require
a conflicting identity key, or if tenant isolation cannot be enforced at persistence and API layers.

## 9. Implementation Evidence

| Check | Result |
|---|---|
| Focused repaired PostgreSQL fixtures | 14 passed; warning-as-error build passed |
| Full Business Platform Docker qualification | 648 passed, 0 failed, 0 skipped; warning-as-error build passed |
| Business Platform coverage | 91.47% line, 80% branch |
| Professional Runtime relationship workspace | 7 passed |
| Web relationship workspace | 5 passed |
| Web TypeScript | `pnpm --dir web exec tsc --noEmit` passed with 0 errors |
| OpenAPI and admission contracts | 25 passed, 1 browser-boundary test deselected |
| Diff integrity | `git diff --check` passed |

The first full Business Platform qualification exited 1 because the isolated migration-30 and
customer-identity host fixtures stopped before the admission and agent-instance migrations. Both
fixtures now apply migrations 25 and 31. Their focused rerun passed 14/14, and the final full suite
passed 648/648.

The PostgreSQL evidence proves global instance uniqueness, immutable binding, active exact-version
admission validation through Npgsql, and stable identity backfill for legacy relationships. Service
and controller evidence proves same-customer same-type relationships receive distinct relationship
and agent-instance identities while exact admission replay preserves the original pair.

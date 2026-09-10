# WC-088 - Customer Multi-Agent And Skill Journey

**Office:** Platform IT Expert (INST-010)
**Assigned by:** Founder instruction, 2026-09-10
**Status:** ENGINEERING QUALIFIED - PR PENDING
**Branch:** `ib/088/customer-multi-agent-skill-journey`
**Baseline:** `origin/main` at `28f3e5e4e84f7878c38748454929b18c9dd92b98`
**Predecessor:** WC-087 merged through PR #411
**Constitutional basis:** C-023, C-026, C-049, C-059, C-065

## 1. Customer Outcome

A customer can browse admitted professionals, enter the existing evaluation/trial/hire journey,
see every authoritative employment relationship in My Experts, switch to one relationship, and
manage that relationship's proposed skills without mixing it with another agent.

## 2. Relationship Switching

Switching means choosing another item from the customer's authoritative relationship list and
navigating to that relationship's workspace. It changes only the viewed relationship; it does not
copy, merge, or mutate goals, skills, trial, contract, workspace, or agent-instance identity.

## 3. Governed Skill Decisions

- Skill configuration is owned by one `tenantId + relationshipId` boundary.
- `SELECT_SKILL` marks one applicable proposal as the customer's current selection.
- `ACCEPT_SKILL` accepts the exact selected/proposed skill ID and version.
- `DEFER_SKILL` defers the exact selected/proposed skill without granting authority.
- `UPDATE_SKILL` selects another existing applicable proposal; it does not mutate a skill version or
  the admitted professional version in place.
- Every command requires an Employer/Evaluator participant, fresh AAL3, expected workspace and skill
  versions, an idempotency key, and constitutional evidence before mutation.
- Replay returns the original receipt; changed reuse and stale versions fail closed.
- Skill acceptance does not itself grant tool authority, recalculate billing, or alter identity.

## 4. Scope

1. Replace the empty My Experts page with the canonical relationship collection.
2. Add relationship switching from My Experts and inside the selected workspace.
3. Expose relationship-local skill state in the authoritative workspace projection.
4. Add governed select, update, accept, and defer skill commands.
5. Update the OpenAPI contract and generated web client where required.
6. Prove two same-type agents retain separate skills, goals, trial, contract, and workspace views.

## 5. Exclusions

- D-BILLING implementation, repricing, payment, refund, or wallet mutation.
- D-IDENTITY link/remove/security-action implementation.
- New professional or skill publication and catalog-authoring workflows.
- Silent skill-version upgrades or copying configuration between relationships.
- Deployment, Production operation, DNS, customer traffic, approval, or merge.

## 6. Acceptance Criteria

| ID | Criterion |
|---|---|
| CJ-01 | My Experts renders the authenticated customer's canonical relationship list and honest empty/error states. |
| CJ-02 | Selecting an expert opens only that relationship's workspace. |
| CJ-03 | The workspace switcher lists only relationships authorized for the current customer. |
| CJ-04 | Skill select/update/accept/defer commands enforce role, fresh AAL3, version and idempotency gates. |
| CJ-05 | Command replay is stable; changed reuse, stale versions and cross-relationship IDs fail closed. |
| CJ-06 | Skill state and command outcomes are visible from the authoritative relationship workspace. |
| CJ-07 | Two same-type relationships retain different skills and unchanged distinct goals, trials, contracts, workspaces and agent-instance IDs. |
| CJ-08 | Existing catalog, evaluation, trial, contract and relationship journeys remain compatible. |
| CJ-09 | Focused and applicable Docker qualification and pre-PR checks pass. |

## 7. Evidence Plan

- Focused controller/service tests for each skill decision and denial path.
- Relationship-list and workspace web tests for non-empty, empty, error and switch behavior.
- A two-relationship integration proof covering skills, goals, trial, contract, workspace and
  immutable agent-instance identity.
- OpenAPI validation, generated-client check, TypeScript, full applicable Docker suite, diff check,
  author review and commit-bound pre-PR preparation.

## 8. Stop Conditions

Stop if a command would require inventing billing or identity semantics, if a skill cannot be tied to
an existing relationship proposal and exact version, if another relationship can be mutated by ID,
or if the canonical relationship list cannot enforce the current customer boundary.

## 9. Implementation Evidence

- My Experts reads the canonical authenticated relationship collection and renders populated,
  empty, signed-out, and unavailable states without inventing relationship data.
- Relationship switching is link navigation to the selected `relationshipId`; it performs no
  mutation and preserves each agent's immutable `agentInstanceId`.
- `SELECT_SKILL`, `UPDATE_SKILL`, `ACCEPT_SKILL`, and `DEFER_SKILL` use the existing governed
  workspace command boundary with participant role, fresh AAL3, exact workspace/subject versions,
  idempotency, and Evidence First authorization.
- Migration 32 stores append-only decisions under tenant RLS, permits the new `SELECTED` state,
  rejects cross-relationship configuration binding, and serializes concurrent replay to one
  decision and one constitutional evidence call.
- OpenAPI 1.10.0 and the generated TypeScript client expose the relationship evaluation projection,
  all four skill payloads, command submission/reconciliation, and exact skill subject versions.
- Two same-type relationships retain distinct agent IDs, goals, trials, contracts, skill states,
  and relationship-local projections after a governed decision changes only one relationship.

## 10. Qualification Evidence

| Check | Result |
|---|---|
| Business Platform Docker restore/build with warnings as errors | PASS - 0 warnings, 0 errors |
| Full Business Platform tests | PASS - 657/657 |
| Migration 32 PostgreSQL integration tests | PASS - 2/2 |
| Full web Jest suite | PASS - 281/281 across 43 suites |
| Web TypeScript | PASS |
| Next.js production build | PASS |
| Generated-client normalization | PASS twice; idempotent |
| Generated OpenAPI contract test | PASS - 4/4 |
| `git diff --check` | PASS |

D-BILLING, D-IDENTITY, deployment, Production operation, approval, and merge remain excluded.
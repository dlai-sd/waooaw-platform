# WC-106 - Unified Docker Build And Test Process

## Record Control

| Field | Value |
|---|---|
| Owning office | Chief Solution Architect (INST-005) |
| Implementation office | Platform IT Expert (INST-010), Skills 5, 6, 8, 12, 14 and 17 |
| Authorized by | Founder instruction and explicit implementation authorization in the 2026-09-28 working session |
| Status | IMPLEMENTATION AUTHORIZED - UNMERGED PR ONLY |
| Baseline | `f80e8850b267dd18a4e437d8f11365316b377851` |
| Parent controls | WC-100 through WC-104; ADR-050 |
| Delivery unit | One bounded process-control PR |

## Authority And Scope

The Founder authorized one uniform Docker build and test process for Work Component implementation,
local PR preparation, hosted PR prechecks, and post-merge CI. This Work Component extends the existing
catalog, immutable runner supply, BuildKit layers, evidence reuse and phase gates. It does not replace
those controls or activate selective hosted validation.

Authorized changes are limited to validation scripts, Docker/Compose runner contracts, GitHub workflow
or catalog wiring, Platform IT Expert operating instructions, focused executable tests, this Work
Component and its requirement ledger, and one unmerged PR. No application behavior, cloud provider,
deployment, DNS, Production, branch-protection, approval or merge action is authorized.

## Inputs

- WC-104 immutable runner supply, cache reuse, static-first ordering and evidence contracts.
- `validation/engineering-validation.yaml` as the canonical gate and runner catalog.
- `scripts/validation_control/catalog_execution.py` as the common catalog executor.
- `scripts/prepare_pr_body.py` and `scripts/precheck_orchestrator.py` as local PR preparation controls.
- `.github/workflows/ci.yaml`, `.github/workflows/code-quality.yaml` and reusable validation workflows.
- Founder-observed repeated failures involving read-only caches, missing or overwritten temporary
  outputs, stale images, Docker socket permissions and late evidence failures.

## Process Contract

Every authoritative Docker task MUST use this sequence:

1. **Static contract:** validate exact worktree/head, catalog, Compose graph, Dockerfiles, tools,
   resource floor and declared output destinations without exporting an image or running tests.
2. **Execution contract:** resolve the immutable runner, then launch that exact image with the exact
   user, source mount, Docker socket, cache/temp paths and output mount required by the selected gate.
   The probe MUST create, read, atomically replace and delete host-visible evidence and cache files.
3. **Phase-appropriate execution:** implementation runs focused changed-component gates; PR creation
   runs applicable static and focused gates plus one final required qualification; hosted PR executes
   authoritative applicable gates; main publishes or promotes immutable candidates and executes the
   non-waivable final inventory.
4. **Evidence publication:** write run-scoped output first, verify host visibility and ownership, then
   atomically publish the final manifest. Container-only or stale prior output cannot authorize PASS.
5. **Retry control:** an infrastructure or execution-contract failure receives a stable fingerprint.
   The same gate, runner, environment and fingerprint MUST NOT rerun until one bound input changes.

Direct `docker run`, `docker compose run`, language test commands or alternate scripts are diagnostic
only unless invoked by the catalog executor. They cannot produce authoritative PASS evidence.

## Canonical Requirements

| ID | Required observable behavior |
|---|---|
| WC106-R001 | All four delivery phases resolve commands, runners, mounts and outputs from one versioned catalog and executor. |
| WC106-R002 | Every costly gate is structurally dependent on a static contract and an exact-container execution contract. |
| WC106-R003 | The execution contract proves source readability plus host-visible temp, cache and evidence create/read/replace/delete behavior under the selected container user. |
| WC106-R004 | Docker-socket gates prove socket access from inside the exact runner before tests or emulation begin. |
| WC106-R005 | Pytest, coverage, NuGet, pnpm and gate evidence use declared writable container-local or run-scoped host paths; read-only source cannot receive correctness state. |
| WC106-R006 | Existing output from another run or commit is rejected or isolated; PASS is published atomically only after required artifacts are visible on the host. |
| WC106-R007 | Unchanged execution-contract or infrastructure failures are blocked from costly retry and identify the input that must change. |
| WC106-R008 | Implementation runs focused gates first and broad qualification only for the final candidate or an explicitly declared exceptional condition. |
| WC106-R009 | PR and main workflows consume existing immutable runner and application-image identities; equivalent candidates are promoted rather than rebuilt where trust permits. |
| WC106-R010 | Platform IT Expert instructions require the canonical process and prohibit invented authoritative Docker paths. |
| WC106-R011 | Negative tests inject missing mounts, read-only output/cache, wrong user, absent socket, stale artifacts, container-only output and unchanged retry attempts before costly-node execution. |
| WC106-R012 | Author review proves requirement coverage, security/isolation preservation, rollback and no weakening of WC-104 or authoritative hosted gates. |

## Phase Matrix

| Phase | Required depth | Prohibited behavior |
|---|---|---|
| Implementation | Static contract, exact-container contract, focused affected gate | Broad qualification after every edit; authoritative ad hoc commands |
| PR creation | Static and applicable focused gates, verified reuse, one final required qualification on committed head | Repeating unchanged successful gates; output outside run-scoped evidence |
| Hosted PR | Authoritative catalog selection and complete required PR evidence | Workflow-local command variants or independently built validation runners |
| Main / release | Same immutable identities, final non-waivable inventory, publish/promote and attest | Rebuilding an equivalent trusted candidate without recorded reason; weakening final gates |

## Definition Of Done

- `work-contracts/WC-106-requirements.yaml` has one independently testable row for every requirement.
- The reusable execution-contract module and exact-container probe are used by local and hosted catalog
  execution before every costly gate.
- Failure fingerprints prevent one unchanged environment defect from consuming another costly run.
- Platform IT Expert policy and policy tests require the canonical phase sequence and prohibit alternate
  authoritative Docker paths.
- Focused Docker tests cover every negative fixture in WC106-R011 and the final exact-head applicable
  qualification passes.
- Author review records correctness, failure ordering, mounts, ownership, caches, evidence, security,
  compatibility, rollback and WC-104 equivalence with no unresolved finding.
- One unmerged PR is submitted for Founder review. The author does not approve or merge it.

## Stop Conditions

Stop on any requirement to weaken a quality gate, trust a mutable image tag, make cache state evidence,
write correctness state into read-only source, silently retry an unchanged infrastructure failure,
change application behavior, add a dependency, mutate a provider, deploy, access customer data,
self-approve or self-merge. A required gate that cannot use the canonical executor remains blocked;
it is never replaced by an ad hoc PASS.

## Rollback

Revert the bounded WC-106 commit. Existing WC-104 runner supply, catalog commands, Docker layers,
hosted full-gate inventory and application behavior remain the rollback baseline. Generated run-scoped
evidence is non-authoritative after rollback and may be removed without deleting prior immutable
evidence.
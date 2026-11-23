# WC-166 - Foundation Plan Identity On A Cache Miss

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-166 |
| Office | Platform IT Expert (INST-010) |
| Initiative | IB-166 |
| Founder assignment | Current conversation, 2026-11-23: investigate the failed Environment Deployment run 45213486537 with a short RCA; then "you know RCA and you know waooaw's policy ... review it and let me know" (the author decides the fix) |
| Status | IMPLEMENTATION_AUTHORIZED. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` at `745970eb` (PR #631 merged) |
| Branch | `ib/166/plan-only-foundation-identity` |
| Decisions | `architecture/reference/pipeline/azure-deployment-topology.md` (no shared runner role above an environment Key Vault; the bootstrap identity is constrained) |
| Requirement ledger | [WC-166-requirements.yaml](./WC-166-requirements.yaml) |
| Constitutional basis | C-023, C-065, C-080 |

## Root Cause (run 45213486537, plan-only, `apply: false`)

- The foundation changed (acceptance vault and identity), so the foundation cache missed and the foundation plan ran.
- The two steps that switch to the environment deployment identity ("Resolve Plan B foundation mutation identity" and its Azure login) were gated on `inputs.apply`, so they were skipped.
- Terraform therefore refreshed the existing Key Vault keys and secrets as the constrained bootstrap identity (`waooaw-platform-bootstrap`, oid `77147af5-a32d-4151-b557-e719f319b55b`). Live role read: it holds Contributor and Role Based Access Control Administrator on `waooaw-demo-rg` and no role on `kv-waooaw-demo`, so every key and secret read returned `ForbiddenByRbac` and the plan failed.
- `TF_VAR_deployment_client_id` also fell back to the control-plane client id, so a plan-only plan differed from the apply plan.
- The last successful run (45133184632) used `apply: true`, switched identity, and planned successfully.

## Authority And Scope

### In scope

1. The two Plan B identity steps run whenever the foundation plan runs (`inputs.apply || cache_hit != 'true'`), still only when password authentication is enabled.
2. One regression test that ties both conditions to the plan step's own condition.

### Out of scope and prohibited

- Granting the bootstrap identity any Key Vault role (it would breach the topology rule); any change to the apply path, the cache, or Terraform; applying anything.

## Canonical Requirement Index

| ID | Obligation |
|---|---|
| WC166-R001 | A foundation plan that runs without apply (cache miss) runs as the environment deployment identity, and uses it as `deployment_client_id`, exactly as an apply plan does |
| WC166-R002 | The identity steps stay gated on password authentication and never run when the plan step is skipped (cache hit without apply) |

## Definition Of Done

1. The regression test fails on the previous workflow and passes on the fix; actionlint passes; the existing deployment workflow tests pass.
2. PR body prepared; author review recorded; Founder reviews and merges.
3. After merge, a plan-only Demo run is the live proof; it is not claimed here.

## Stop Conditions

- Any need to widen the bootstrap identity or to change apply behavior.

## Implementation Record

Evidence at the exact head is in the PR body. The plan step is read-only (state adoption is refused in plan mode by `scripts/goal006_execution_gate.py`), so running it as the deployment identity adds no mutation path. Not run: any workflow run against Azure.

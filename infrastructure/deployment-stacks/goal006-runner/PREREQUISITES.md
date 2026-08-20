# Runner Prerequisite Process

## Verified Environment State

State verified against Azure subscription `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84` on
2026-08-20. These are prerequisites only; no runner stack or workload capacity exists.

| Environment | Resource group | Prerequisites | Idempotency preview | Recurring cost at this stage |
|---|---|---|---|---|
| Demo | `waooaw-demo-runner-rg` | Applied and verified | Verified | INR 0 |
| UAT | `waooaw-uat-runner-rg` | Applied and verified | 7 `NoChange`; no create, modify, or delete | INR 0 |
| Production | `waooaw-prod-runner-rg` | Applied and verified | 7 `NoChange`; no create, modify, or delete | INR 0 |

Each environment has two environment-specific custom roles and resource-group-scoped
Contributor and RBAC Administrator assignments. All environments share the subscription-scoped
Deployment Stack Owner assignment and cumulative GOAL-006 INR 10,000 monthly budget. The budget is
an alert threshold, not committed spend.

Use one reviewed parameter file per environment. Demo, UAT, and Production run the same command; authorization and parameter review remain environment-specific.

Preview without mutation:

```bash
python scripts/goal006_runner_prerequisites.py \
  --environment demo \
  --subscription-id 2ed11839-6a0f-4eaa-bd94-44ca96ff5d84 \
  --template infrastructure/deployment-stacks/goal006-runner/prerequisites.bicep \
  --parameters infrastructure/deployment-stacks/goal006-runner/demo.prerequisites.parameters.json
```

After explicit authorization, append `--apply`. The command validates Azure's built-in role IDs, runs ARM validation and what-if, rejects deletes, applies the idempotent deployment, and verifies the resource group, cumulative budget, and exact bootstrap role scopes. Reviewed creates and in-place corrections are allowed and reported.

UAT and Production use separate reviewed parameter files and require environment-specific
authorization. The process creates environment-specific resource groups, custom roles, and RG
assignments. The cumulative GOAL-006 budget and subscription Deployment Stack Owner assignment are
shared and idempotent.

The next delivery sequence is defined in [RUNNER-PROMOTION.md](RUNNER-PROMOTION.md). Prerequisite
readiness does not authorize runner deployment, promotion, activation, traffic, or Production use.
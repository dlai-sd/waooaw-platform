# Runner Prerequisite Process

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

UAT and Production require separate reviewed parameter files and authorization. The process creates environment-specific resource groups, custom roles, and RG assignments. The cumulative GOAL-006 budget and subscription Deployment Stack Owner assignment are shared and idempotent.
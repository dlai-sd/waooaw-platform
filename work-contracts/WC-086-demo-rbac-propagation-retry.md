# WC-086 - Demo RBAC Propagation Retry

**Office:** Platform IT Expert (INST-010)
**Status:** IN PROGRESS
**Assigned by:** Founder instruction, 2026-09-10
**Scope:** Docker-only validation and the Demo deployment workflow path
**Predecessor:** WC-085

## Authority And Objective

The Founder authorized a bounded correction for workflow run 34435572652. The
Demo workload apply failed because Azure Container Apps could not yet read
`bp-identity-reader-client-secret` immediately after Terraform created its
Key Vault role assignment.

Add a bounded retry in the existing environment deployment workflow. Retry only
when the apply output identifies the known Azure Key Vault managed-identity
propagation error. Rebuild and policy-check the Terraform plan before each retry;
unrelated Terraform or Azure failures remain terminal.

## Inputs

- `.github/workflows/environment-deployment.yaml`
- `infrastructure/terraform/phase2/environments/demo/workload/`
- Evidence from workflow run 34435572652

## Definition Of Done

- The workflow retries the known propagation failure with a capped wait/backoff.
- Each retry regenerates and policy-checks a fresh workload plan.
- Non-matching failures do not retry; no cloud provider action is run locally.
- Docker-only YAML/static validation and focused regression evidence pass.
- A PR is prepared with the test evidence and this contract.

## Stops And Constraints

- No application code, Terraform permissions, secrets, DNS, Production, or live
  Azure mutation changes.
- Do not expose secret values or credentials in logs or evidence.
- Stop if the workflow behavior cannot be validated locally in Docker.
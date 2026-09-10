# WC-087 - Demo Identity Reader Secret Seeding

**Office:** Platform IT Expert (INST-010)
**Status:** IN PROGRESS
**Assigned by:** Founder instruction, 2026-09-10
**Scope:** Docker-only validation and the Demo deployment workflow path
**Predecessor:** WC-086

## Authority And Objective

The Founder authorized the correction exposed by workflow run 34439777912 and
reproduced locally. The Demo deployment references the dedicated Key Vault secret
`bp-identity-reader-client-secret`, but the deployment inventory and seeder only
cover the six base credentials.

Add the dedicated secret to the deployment-time inventory and seeder. Generate or
preserve its value only in Key Vault at deployment time. Do not modify images or
bake environment values into image configuration. Keep the existing WC-086
bounded RBAC retry as secondary protection.

## Inputs

- `.github/workflows/environment-deployment.yaml`
- `tests/pipeline/test_wc085_google_deployment.py`
- `infrastructure/terraform/phase2/modules/workload/google.tf`
- Evidence from workflow run 34439777912

## Definition Of Done

- Inventory and seeder include `bp-identity-reader-client-secret`.
- A focused Docker regression test fails against the old workflow and passes with
  the fix.
- Docker `actionlint` and the focused pipeline test pass.
- No application image, Terraform secret value, repository secret, or evidence
  contains the generated credential.
- A PR is prepared with local Docker evidence.

## Stops And Constraints

- No live Azure mutation, deployment dispatch, DNS, Production, or image rebuild.
- Preserve existing secret values when present; only create a missing secret.
- Do not expose secret values in logs or test evidence.
- Stop if local Docker validation cannot prove the inventory/seeder contract.

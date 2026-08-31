#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AZURE_CLI_IMAGE="mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa"
TERRAFORM_IMAGE="hashicorp/terraform:1.9.8"

cd "$REPO_ROOT"

echo "[1/4] Linting GitHub Actions workflows"
docker run --rm -v "$REPO_ROOT:/repo:ro" -w /repo rhysd/actionlint:1.7.7 \
  .github/workflows/ci.yaml \
  .github/workflows/deploy.yaml \
  .github/workflows/environment-deployment.yaml \
  .github/workflows/environment-deployment-verification.yaml \
  .github/workflows/workload-lease-reconciliation.yaml \
  .github/workflows/private-runner-infrastructure.yaml

echo "[2/4] Validating all GOAL-006 Terraform roots with Terraform 1.9.8"
docker run --rm \
  -v "$REPO_ROOT:/repo:ro" \
  --entrypoint /bin/sh \
  "$TERRAFORM_IMAGE" \
  -c '
    set -eu
    cp -R /repo/infrastructure/terraform/phase2 /tmp/phase2
    for environment in demo uat prod; do
      for root in foundation workload; do
        directory="/tmp/phase2/environments/$environment/$root"
        echo "  terraform validate: $environment/$root"
        terraform -chdir="$directory" init -backend=false -input=false -no-color >/dev/null
        terraform -chdir="$directory" validate -no-color
      done
    done
    mkdir /tmp/lease-plan
    cat > /tmp/lease-plan/main.tf <<EOF
module "lease" {
  source                  = "../phase2/modules/lifecycle"
  environment             = "demo"
  purpose                 = "local deployment rehearsal"
  manifest_digest         = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  owner_principal_id      = "rehearsal"
  expires_at              = "2099-01-01T00:00:00Z"
  issued_at               = "2026-01-01T00:00:00Z"
  lifecycle_state         = "ACTIVE"
  cost_centre             = "rehearsal"
  evidence_digest         = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  protected_foundation_id = "rehearsal"
}

resource "terraform_data" "member" {
  for_each = module.lease.workload_enabled ? toset(["web"]) : toset([])
  input    = each.key
}
EOF
    echo "  terraform plan: lease-controlled workload membership"
    terraform -chdir=/tmp/lease-plan init -backend=false -input=false -no-color >/dev/null
    terraform -chdir=/tmp/lease-plan plan -input=false -no-color -out=/tmp/lease-plan/lease.tfplan >/dev/null
  '

echo "[3/4] Probing the pinned Azure CLI seeder argument parser"
set +e
parser_output=$(docker run --rm "$AZURE_CLI_IMAGE" az containerapp job create \
  --name rehearsal \
  --resource-group rehearsal-rg \
  --environment rehearsal-env \
  --trigger-type Manual \
  --replica-timeout 600 \
  --replica-retry-limit 1 \
  --replica-completion-count 1 \
  --parallelism 1 \
  --image "$AZURE_CLI_IMAGE" \
  --mi-user-assigned /subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rehearsal-rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/rehearsal \
  --cpu 0.25 \
  --memory 0.5Gi \
  --env-vars AZURE_CLIENT_ID=rehearsal KEY_VAULT_NAME=rehearsal \
  --command /bin/sh \
  --args '["-c","exit 0"]' \
  --output none 2>&1)
parser_status=$?
set -e
if [[ $parser_status -eq 0 ]] || [[ "$parser_output" != *"Please run 'az login'"* ]] || [[ "$parser_output" == *"unrecognized arguments"* ]]; then
  printf '%s\n' "$parser_output" >&2
  echo "Pinned Azure CLI did not reach the expected authentication boundary" >&2
  exit 1
fi

echo "[4/4] Running the complete GOAL-006 pipeline suite"
docker compose --profile test-python run --rm test-runner-python \
  pytest tests/pipeline/test_goal006_*.py -q

echo "GOAL-006 local deployment rehearsal passed; no Azure login or mutation was attempted."
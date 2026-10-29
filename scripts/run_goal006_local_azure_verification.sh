#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AZURE_CLI_IMAGE=${WAOOAW_RUNNER_AZURE_IMAGE:-mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa}
PYTHON_IMAGE="python@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a"
CURL_IMAGE="curlimages/curl@sha256:94e9e444bcba979c2ea12e27ae39bee4cd10bc7041a472c4727a558e213744e6"
CONTAINERAPP_EXTENSION_VERSION="1.3.0b4"

phase_started=
start_phase() {
  phase_started=$(date +%s)
  echo "[azure-verification] phase=$1 event=STARTED"
}
complete_phase() {
  local duration
  duration=$(($(date +%s) - phase_started))
  printf -v "$2" '%s' "$duration"
  echo "[azure-verification] phase=$1 event=COMPLETED duration_seconds=$duration"
}
mkdir -p "$REPO_ROOT/test-results"
WORK_DIR=$(mktemp -d "$REPO_ROOT/test-results/goal006-local-azure.XXXXXX")
RUN_ID=${WORK_DIR##*.}
NETWORK="goal006-azure-verification-$RUN_ID"
EMULATOR="goal006-azure-emulator-$RUN_ID"
EVIDENCE_DIR="$WORK_DIR/evidence"
AZURE_CONFIG_DIR="$WORK_DIR/azure-config"

cleanup() {
  if test -n "${GOAL006_EVIDENCE_DIR:-}" && test -d "$EVIDENCE_DIR"; then
    mkdir -p "$GOAL006_EVIDENCE_DIR"
    cp -R "$EVIDENCE_DIR/." "$GOAL006_EVIDENCE_DIR/"
  fi
  docker rm -f "$EMULATOR" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

start_phase image-and-emulator
mkdir -p "$EVIDENCE_DIR" "$AZURE_CONFIG_DIR"
docker run --rm --user "$(id -u):$(id -g)" -v "$EVIDENCE_DIR:/evidence" \
  "$AZURE_CLI_IMAGE" openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj /CN=auth.demo.waooaw.com \
  -addext subjectAltName=DNS:auth.demo.waooaw.com,DNS:cp.demo.waooaw.com,DNS:api.demo.waooaw.com \
  -keyout /evidence/fixture.key -out /evidence/fixture.crt >/dev/null 2>&1
docker network create "$NETWORK" >/dev/null
docker run -d --rm \
  --name "$EMULATOR" \
  --network "$NETWORK" \
  --network-alias goal006-azure-emulator \
  --network-alias auth.demo.waooaw.com \
  --network-alias cp.demo.waooaw.com \
  --network-alias api.demo.waooaw.com \
  -e GOOGLE_FIXTURE_TLS=true \
  -e PYTHONPATH=/repo/scripts \
  -e EVIDENCE_DIR=/evidence \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$EVIDENCE_DIR:/evidence" \
  "$PYTHON_IMAGE" \
  python /repo/tests/fixtures/goal006_azure_emulator.py >/dev/null

for attempt in $(seq 1 20); do
  if docker run --rm --network "$NETWORK" "$CURL_IMAGE" \
    --fail --silent http://goal006-azure-emulator:8080/healthz >/dev/null; then
    break
  fi
  test "$attempt" != 20
done

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --network "$NETWORK" \
  -v "$AZURE_CONFIG_DIR:/azure-config" \
  -e HOME=/tmp \
  -e AZURE_CONFIG_DIR=/azure-config \
  -e AZURE_CORE_ONLY_SHOW_ERRORS=true \
  "$AZURE_CLI_IMAGE" \
  az cloud register \
    --name WAOOAWLocal \
    --endpoint-active-directory http://goal006-azure-emulator:8080 \
    --endpoint-resource-manager http://goal006-azure-emulator:8080 \
    --endpoint-active-directory-resource-id http://goal006-azure-emulator:8080/ \
    --skip-endpoint-discovery \
    --output none
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$AZURE_CONFIG_DIR:/azure-config" \
  -e HOME=/tmp \
  -e AZURE_CONFIG_DIR=/azure-config \
  -e AZURE_CORE_ONLY_SHOW_ERRORS=true \
  "$AZURE_CLI_IMAGE" \
  az cloud set --name WAOOAWLocal

cat > "$AZURE_CONFIG_DIR/azureProfile.json" <<'JSON'
{
  "subscriptions": [
    {
      "environmentName": "WAOOAWLocal",
      "homeTenantId": "00000000-0000-0000-0000-000000000007",
      "id": "00000000-0000-0000-0000-000000000006",
      "isDefault": true,
      "managedByTenants": [],
      "name": "GOAL-006 Local Emulator",
      "state": "Enabled",
      "tenantId": "00000000-0000-0000-0000-000000000007",
      "user": {"assignedIdentityInfo": "MSI", "name": "systemAssignedIdentity", "type": "servicePrincipal"}
    }
  ]
}
JSON

run_az() {
  docker run --rm \
    --user "$(id -u):$(id -g)" \
    --network "$NETWORK" \
    -w /evidence \
    -v "$AZURE_CONFIG_DIR:/azure-config" \
    -e HOME=/tmp \
    -e AZURE_CONFIG_DIR=/azure-config \
    -e AZURE_CORE_ONLY_SHOW_ERRORS=true \
    -e AZURE_POD_IDENTITY_AUTHORITY_HOST=http://goal006-azure-emulator:8080 \
    -v "$EVIDENCE_DIR:/evidence" \
    "$AZURE_CLI_IMAGE" az "$@"
}

complete_phase image-and-emulator image_and_emulator_seconds
start_phase extension-readiness
if [ -z "${WAOOAW_RUNNER_AZURE_IMAGE:-}" ]; then
  run_az extension add \
    --name containerapp \
    --version "$CONTAINERAPP_EXTENSION_VERSION" \
    --allow-preview true \
    --only-show-errors
fi
test "$(run_az extension show --name containerapp --query version -o tsv)" = "$CONTAINERAPP_EXTENSION_VERSION"
test "$(run_az account show --query id -o tsv)" = "00000000-0000-0000-0000-000000000006"
complete_phase extension-readiness extension_readiness_seconds
start_phase deployment-resume
for app in pgbouncer auth-redis keycloak identity-edge temporal web business-platform billing-engine \
  constitutional-engine professional-runtime ai-runtime dma; do
  touch "$EVIDENCE_DIR/stopped-ca-demo-$app"
done
run_readiness() {
  docker run --rm \
    --user "$(id -u):$(id -g)" \
    --network "$NETWORK" \
    -e HOME=/tmp \
    -e AZURE_CONFIG_DIR=/azure-config \
    -e AZURE_CORE_ONLY_SHOW_ERRORS=true \
    -e AZURE_POD_IDENTITY_AUTHORITY_HOST=http://goal006-azure-emulator:8080 \
    -v "$AZURE_CONFIG_DIR:/azure-config" \
    -v "$REPO_ROOT:/repo:ro" \
    -v "$EVIDENCE_DIR:/evidence" \
    "$AZURE_CLI_IMAGE" python3 /repo/scripts/goal006_activation_readiness.py \
      --resource-group waooaw-demo-rg --environment demo \
      --timeout-seconds 300 --interval-seconds 1 "$@"
}
if run_readiness --scope migration --timeout-seconds 0 --output /evidence/stopped-readiness.json; then
  echo "Read-only readiness passed for an operationally stopped PgBouncer" >&2
  exit 1
fi
run_readiness --scope migration --resume-stopped --output /evidence/migration-readiness.json
test "$(find "$EVIDENCE_DIR" -name 'resumed-*.json' | wc -l)" = 1
test -f "$EVIDENCE_DIR/stopped-ca-demo-web"
run_az containerapp job show -g waooaw-demo-rg -n job-demo-wc124-billing-migration \
  > "$EVIDENCE_DIR/billing-preflight-job.json"
docker run --rm --user "$(id -u):$(id -g)" \
  -v "$REPO_ROOT:/repo:ro" -v "$EVIDENCE_DIR:/evidence" \
  "$PYTHON_IMAGE" python /repo/scripts/wc124_pgbouncer_preflight_job.py \
    --job /evidence/billing-preflight-job.json --environment demo \
    --subscription-id 00000000-0000-0000-0000-000000000006 \
    --database-query --output /evidence/database-preflight-template.json
test "$(run_az containerapp job start -g waooaw-demo-rg -n job-demo-wc124-billing-migration \
  --yaml /evidence/database-preflight-template.json --query name -o tsv)" = job-demo-database-preflight-local-0001
jq -e --slurpfile expected "$EVIDENCE_DIR/database-preflight-template.json" \
  '.containers == $expected[0].containers' "$EVIDENCE_DIR/database-preflight-start-request.json" >/dev/null
run_readiness --scope dependencies --resume-stopped --output /evidence/dependency-readiness.json
test -f "$EVIDENCE_DIR/stopped-ca-demo-web"
run_readiness --scope all --resume-stopped --output /evidence/activation-readiness.json
test "$(find "$EVIDENCE_DIR" -name 'resumed-*.json' | wc -l)" = 12
run_readiness --scope all --resume-stopped --output /evidence/activation-readiness-replay.json
test "$(jq '.resumed_apps | length' "$EVIDENCE_DIR/activation-readiness-replay.json")" = 0
complete_phase deployment-resume deployment_resume_seconds
start_phase database-handoff-update
docker compose --profile test-python run --rm --no-deps test-runner-python \
  python -c '
from pathlib import Path
import yaml
workflow = yaml.safe_load(Path(".github/workflows/environment-deployment.yaml").read_text())
step = next(step for step in workflow["jobs"]["terraform"]["steps"]
            if step.get("name") == "Finalize WC-124 PostgreSQL authority handoff")
print(step["run"].split("actual_identities=", 1)[0])
' > "$EVIDENCE_DIR/wc124-handoff-update.sh"
(
  cd "$EVIDENCE_DIR"
  export TARGET_ENVIRONMENT=demo RESOURCE_GROUP=waooaw-demo-rg
  export KEY_VAULT_NAME=kv-waooaw-demo POSTGRESQL_SERVER_FQDN=postgres.example.invalid
  export BOOTSTRAP_CLIENT_ID=00000000-0000-0000-0000-000000000008
  export DATABASE_PROVISIONER_CLIENT_ID=00000000-0000-0000-0000-000000000009
  az() { run_az "$@"; }
  source ./wc124-handoff-update.sh
)
jq -e --slurpfile expected "$EVIDENCE_DIR/wc124-db-handoff-job-definition.json" '
  .properties.template.containers[0].args
    == $expected[0].properties.template.containers[0].args
  and .identity.type == $expected[0].identity.type
  and (.identity.userAssignedIdentities // $expected[0].identity.userAssignedIdentities)
    == $expected[0].identity.userAssignedIdentities
  and .properties.template.containers[0].image
    == $expected[0].properties.template.containers[0].image
  and .properties.configuration == $expected[0].properties.configuration
' "$EVIDENCE_DIR/handoff-update-request.json" > /dev/null
complete_phase database-handoff-update database_handoff_update_seconds
start_phase positive-deployment
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --network "$NETWORK" \
  -w /evidence \
  -e HOME=/tmp \
  -e AZURE_CONFIG_DIR=/azure-config \
  -e AZURE_CORE_ONLY_SHOW_ERRORS=true \
  -e AZURE_POD_IDENTITY_AUTHORITY_HOST=http://goal006-azure-emulator:8080 \
  -e PYTHONPATH=/repo/scripts \
  -e GOAL006_REVISION_READY_ATTEMPTS=4 \
  -e SSL_CERT_FILE=/evidence/fixture.crt \
  -e GOAL006_REVISION_READY_INTERVAL_SECONDS=0 \
  -v "$AZURE_CONFIG_DIR:/azure-config" \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$EVIDENCE_DIR:/evidence" \
  "$AZURE_CLI_IMAGE" \
  /bin/bash /repo/scripts/goal006_verify_deployment.sh \
    demo \
    /evidence/registry-release-manifest.json \
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    https://cp.demo.waooaw.com

test "$(jq -r '.functional_verification' "$EVIDENCE_DIR/deployment-verification.json")" = true
jq -e '.redirect_verified == true and .real_user_sign_in_verified == false and
  .keycloak_revision == "ca-demo-keycloak--0000002" and .release_sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' \
  "$EVIDENCE_DIR/google-deployment-verification.json" >/dev/null
jq -e '.redirect_verified == true and .real_user_sign_in_verified == false and
  .keycloak_revision == "ca-demo-keycloak--0000002" and .release_sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' \
  "$EVIDENCE_DIR/facebook-deployment-verification.json" >/dev/null
test "$(find "$EVIDENCE_DIR/revision-evidence" -name '*-revision.json' | wc -l)" = 12  # exact seven + keycloak, identity-edge, temporal, auth-redis, pgbouncer
for provider in google facebook; do
  jq -e '.provider_start_verified == true and
    .release_sha == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' \
    "$EVIDENCE_DIR/revision-evidence/$provider-web-provider-start.json" >/dev/null
done
grep -F 'http-probes: all required runtime probes passed' "$EVIDENCE_DIR/functional-http-probes.log" >/dev/null
grep -F 'constitutional-health: all required runtime probes passed' \
  "$EVIDENCE_DIR/functional-constitutional-health.log" >/dev/null
complete_phase positive-deployment positive_deployment_seconds

start_phase negative-deployment
mkdir -p "$EVIDENCE_DIR/unhealthy-revision"
cp "$EVIDENCE_DIR/registry-release-manifest.json" \
  "$EVIDENCE_DIR/unhealthy-revision/registry-release-manifest.json"
touch "$EVIDENCE_DIR/force-professional-runtime-unready"
set +e
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --network "$NETWORK" \
  -w /evidence/unhealthy-revision \
  -e HOME=/tmp \
  -e AZURE_CONFIG_DIR=/azure-config \
  -e AZURE_CORE_ONLY_SHOW_ERRORS=true \
  -e AZURE_POD_IDENTITY_AUTHORITY_HOST=http://goal006-azure-emulator:8080 \
  -e PYTHONPATH=/repo/scripts \
  -e GOAL006_REVISION_READY_ATTEMPTS=1 \
  -e GOAL006_REVISION_READY_INTERVAL_SECONDS=0 \
  -v "$AZURE_CONFIG_DIR:/azure-config" \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$EVIDENCE_DIR:/evidence" \
  "$AZURE_CLI_IMAGE" \
  /bin/bash /repo/scripts/goal006_verify_deployment.sh \
    demo \
    /evidence/unhealthy-revision/registry-release-manifest.json \
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    https://cp.demo.waooaw.com > "$EVIDENCE_DIR/unhealthy-revision/verifier.log" 2>&1
unhealthy_status=$?
set -e
rm "$EVIDENCE_DIR/force-professional-runtime-unready"
test "$unhealthy_status" -ne 0
grep -F 'Revision readiness timed out: app=ca-demo-professional-runtime' \
  "$EVIDENCE_DIR/unhealthy-revision/verifier.log" >/dev/null
if grep -F 'jq: error' "$EVIDENCE_DIR/unhealthy-revision/verifier.log" >/dev/null; then
  echo "Unhealthy-revision diagnostics crashed before timeout evidence" >&2
  exit 1
fi
if grep -F 'only json logs supported for system logs' \
  "$EVIDENCE_DIR/unhealthy-revision/revision-evidence/professional-runtime-system.log" >/dev/null; then
  echo "Unhealthy-revision diagnostics used an unsupported system-log format" >&2
  exit 1
fi
grep -F 'Console log capture skipped: revision container metadata unavailable' \
  "$EVIDENCE_DIR/unhealthy-revision/revision-evidence/professional-runtime-console.log" >/dev/null
test "$(jq -r '.properties.healthState' \
  "$EVIDENCE_DIR/unhealthy-revision/revision-evidence/professional-runtime-revision.json")" = Unhealthy
complete_phase negative-deployment negative_deployment_seconds

start_phase cleanup-broker
RUNNER_IMAGE="ghcr.io/dlai-sd/goal006-private-runner@sha256:$(printf 'f%.0s' $(seq 1 64))"
run_az containerapp job show \
  --resource-group waooaw-demo-runner-rg \
  --name goal006-demo-runner-cleanup-broker \
  --output json > "$EVIDENCE_DIR/cleanup-job.json"
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e PYTHONPATH=/repo/scripts \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$EVIDENCE_DIR:/evidence" \
  "$PYTHON_IMAGE" \
  python /repo/scripts/goal006_runner_execution.py cleanup \
    --job /evidence/cleanup-job.json \
    --expected-image "$RUNNER_IMAGE" \
    --run-id 33388459246 \
    --run-attempt 1 \
    --private-job-conclusion success \
    --output /evidence/cleanup-execution.json
cleanup_execution=$(run_az containerapp job start \
  --resource-group waooaw-demo-runner-rg \
  --name goal006-demo-runner-cleanup-broker \
  --yaml /evidence/cleanup-execution.json \
  --query name -o tsv)
test "$cleanup_execution" = "goal006-demo-runner-cleanup-local-0001"
test "$(run_az containerapp job execution show \
  --resource-group waooaw-demo-runner-rg \
  --name goal006-demo-runner-cleanup-broker \
  --job-execution-name "$cleanup_execution" \
  --query properties.status -o tsv)" = Succeeded
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -e PYTHONPATH=/repo/scripts \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$EVIDENCE_DIR:/evidence" \
  "$PYTHON_IMAGE" \
  python /repo/scripts/goal006_runner_execution.py pointer \
    --environment demo \
    --run-id 33388459246 \
    --run-attempt 1 \
    --private-job-conclusion success \
    --cleanup-execution-name "$cleanup_execution" \
    --evidence-container-url https://local.test/goal006-runner-evidence \
    --output /evidence/cleanup-record.json
test "$(run_az containerapp job execution list \
  --resource-group waooaw-demo-runner-rg \
  --name goal006-demo-runner-job \
  --query "[?properties.status=='Running' || properties.status=='Processing' || properties.status=='Waiting'] | length(@)" \
  -o tsv)" = 0
test "$(jq -r '.containers[0].args[0]' "$EVIDENCE_DIR/cleanup-start-request.json")" != "stale deployed lifecycle source"
grep -F 'def write_cleanup_evidence(' "$EVIDENCE_DIR/cleanup-start-request.json" >/dev/null
complete_phase cleanup-broker cleanup_broker_seconds

azure_cli_version=$(run_az version --query '"azure-cli"' -o tsv)
jq -n \
  --arg azure_cli_version "$azure_cli_version" \
  --arg azure_cli_image "$AZURE_CLI_IMAGE" \
  --arg containerapp_extension_version "$CONTAINERAPP_EXTENSION_VERSION" \
  --argjson image_and_emulator_seconds "$image_and_emulator_seconds" \
  --argjson extension_readiness_seconds "$extension_readiness_seconds" \
  --argjson deployment_resume_seconds "$deployment_resume_seconds" \
  --argjson database_handoff_update_seconds "$database_handoff_update_seconds" \
  --argjson positive_deployment_seconds "$positive_deployment_seconds" \
  --argjson negative_deployment_seconds "$negative_deployment_seconds" \
  --argjson cleanup_broker_seconds "$cleanup_broker_seconds" \
  --arg cleanup_request_sha256 "$(sha256sum "$EVIDENCE_DIR/cleanup-start-request.json" | cut -d' ' -f1)" \
  --argjson azure_requests "$(wc -l < "$EVIDENCE_DIR/azure-request-log.jsonl")" \
  --argjson revision_evidence "$(find "$EVIDENCE_DIR/revision-evidence" -name '*-revision.json' | wc -l)" \
  '{
    passed: true,
    azure_cli_version: $azure_cli_version,
    azure_cli_image: $azure_cli_image,
    containerapp_extension_version: $containerapp_extension_version,
    phase_timings_seconds: {
      image_and_emulator: $image_and_emulator_seconds,
      extension_readiness: $extension_readiness_seconds,
      deployment_resume: $deployment_resume_seconds,
      database_handoff_update: $database_handoff_update_seconds,
      positive_deployment: $positive_deployment_seconds,
      negative_deployment: $negative_deployment_seconds,
      cleanup_broker: $cleanup_broker_seconds
    },
    azure_requests: $azure_requests,
    revision_evidence: $revision_evidence,
    functional_verification: true,
    structured_database_handoff_update: true,
    deployment_stop_resume_verified: true,
    database_preflight_template_verified: true,
    unhealthy_revision_failure_proved: true,
    cleanup_stale_source_replaced: true,
    cleanup_request_sha256: $cleanup_request_sha256,
    zero_active_private_executions: true
  }' > "$EVIDENCE_DIR/local-runtime-summary.json"
echo "GOAL-006 Docker Azure CLI end-to-end deployment verification passed."
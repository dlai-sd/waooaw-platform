#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AZURE_CLI_IMAGE="mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa"
PYTHON_IMAGE="python@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a"
CURL_IMAGE="curlimages/curl@sha256:94e9e444bcba979c2ea12e27ae39bee4cd10bc7041a472c4727a558e213744e6"
CONTAINERAPP_EXTENSION_VERSION="1.3.0b4"
NETWORK="goal006-azure-verification-$$"
EMULATOR="goal006-azure-emulator-$$"
WORK_DIR=$(mktemp -d)
EVIDENCE_DIR="$WORK_DIR/evidence"
AZURE_CONFIG_DIR="$WORK_DIR/azure-config"

cleanup() {
  docker rm -f "$EMULATOR" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$EVIDENCE_DIR" "$AZURE_CONFIG_DIR"
docker network create "$NETWORK" >/dev/null
docker run -d --rm \
  --name "$EMULATOR" \
  --network "$NETWORK" \
  --network-alias goal006-azure-emulator \
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
    -v "$AZURE_CONFIG_DIR:/azure-config" \
    -e HOME=/tmp \
    -e AZURE_CONFIG_DIR=/azure-config \
    -e AZURE_POD_IDENTITY_AUTHORITY_HOST=http://goal006-azure-emulator:8080 \
    -v "$EVIDENCE_DIR:/evidence" \
    "$AZURE_CLI_IMAGE" az "$@"
}

run_az extension add \
  --name containerapp \
  --version "$CONTAINERAPP_EXTENSION_VERSION" \
  --allow-preview true \
  --only-show-errors
test "$(run_az account show --query id -o tsv)" = "00000000-0000-0000-0000-000000000006"
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --network "$NETWORK" \
  -w /evidence \
  -e HOME=/tmp \
  -e AZURE_CONFIG_DIR=/azure-config \
  -e AZURE_POD_IDENTITY_AUTHORITY_HOST=http://goal006-azure-emulator:8080 \
  -e PYTHONPATH=/repo/scripts \
  -e GOAL006_REVISION_READY_ATTEMPTS=4 \
  -e GOAL006_REVISION_READY_INTERVAL_SECONDS=0 \
  -v "$AZURE_CONFIG_DIR:/azure-config" \
  -v "$REPO_ROOT:/repo:ro" \
  -v "$EVIDENCE_DIR:/evidence" \
  "$AZURE_CLI_IMAGE" \
  /bin/bash /repo/scripts/goal006_verify_deployment.sh \
    demo \
    /evidence/registry-release-manifest.json \
    aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
    https://ca-demo-web.local.waooaw.test \
    203.0.113.10/32

test "$(jq -r '.functional_verification' "$EVIDENCE_DIR/deployment-verification.json")" = true
test "$(find "$EVIDENCE_DIR/revision-evidence" -name '*-revision.json' | wc -l)" = 9
grep -F 'http-probes: all required runtime probes passed' "$EVIDENCE_DIR/functional-http-probes.log" >/dev/null
grep -F 'constitutional-health: all required runtime probes passed' \
  "$EVIDENCE_DIR/functional-constitutional-health.log" >/dev/null

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
    https://ca-demo-web.local.waooaw.test \
    203.0.113.10/32 > "$EVIDENCE_DIR/unhealthy-revision/verifier.log" 2>&1
unhealthy_status=$?
set -e
rm "$EVIDENCE_DIR/force-professional-runtime-unready"
test "$unhealthy_status" -ne 0
grep -F 'Revision readiness timed out: app=ca-demo-professional-runtime' \
  "$EVIDENCE_DIR/unhealthy-revision/verifier.log" >/dev/null
test "$(jq -r '.properties.healthState' \
  "$EVIDENCE_DIR/unhealthy-revision/revision-evidence/professional-runtime-revision.json")" = Unhealthy

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

azure_cli_version=$(run_az version --query '"azure-cli"' -o tsv)
jq -n \
  --arg azure_cli_version "$azure_cli_version" \
  --arg azure_cli_image "$AZURE_CLI_IMAGE" \
  --arg containerapp_extension_version "$CONTAINERAPP_EXTENSION_VERSION" \
  --arg cleanup_request_sha256 "$(sha256sum "$EVIDENCE_DIR/cleanup-start-request.json" | cut -d' ' -f1)" \
  --argjson azure_requests "$(wc -l < "$EVIDENCE_DIR/azure-request-log.jsonl")" \
  --argjson revision_evidence "$(find "$EVIDENCE_DIR/revision-evidence" -name '*-revision.json' | wc -l)" \
  '{
    passed: true,
    azure_cli_version: $azure_cli_version,
    azure_cli_image: $azure_cli_image,
    containerapp_extension_version: $containerapp_extension_version,
    azure_requests: $azure_requests,
    revision_evidence: $revision_evidence,
    functional_verification: true,
    unhealthy_revision_failure_proved: true,
    cleanup_stale_source_replaced: true,
    cleanup_request_sha256: $cleanup_request_sha256,
    zero_active_private_executions: true
  }' > "$EVIDENCE_DIR/local-runtime-summary.json"
if test -n "${GOAL006_EVIDENCE_DIR:-}"; then
  mkdir -p "$GOAL006_EVIDENCE_DIR"
  cp -R "$EVIDENCE_DIR/." "$GOAL006_EVIDENCE_DIR/"
fi
echo "GOAL-006 Docker Azure CLI end-to-end deployment verification passed."
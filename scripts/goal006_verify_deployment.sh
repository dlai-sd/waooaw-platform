#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <environment> <manifest> <release-sha> <web-url> [expected-access-cidr]" >&2
  exit 2
}

test "$#" -ge 4 && test "$#" -le 5 || usage
TARGET_ENVIRONMENT=$1
MANIFEST=$2
RELEASE_SHA=$3
EXPECTED_WEB_URL=$4
EXPECTED_ACCESS_CIDR=${5:-}
RESOURCE_GROUP="waooaw-$TARGET_ENVIRONMENT-rg"
REVISION_READY_ATTEMPTS=${GOAL006_REVISION_READY_ATTEMPTS:-30}
REVISION_READY_INTERVAL_SECONDS=${GOAL006_REVISION_READY_INTERVAL_SECONDS:-10}

case "$TARGET_ENVIRONMENT" in demo|uat|prod) ;; *) usage ;; esac

az containerapp list --resource-group "$RESOURCE_GROUP" \
  --query '[].{name:name,image:properties.template.containers[0].image,provisioningState:properties.provisioningState}' \
  -o json > live-inventory.json
python3 "$(dirname "$0")/goal006_live_inventory.py" \
  --environment "$TARGET_ENVIRONMENT" \
  --manifest "$MANIFEST" \
  --inventory live-inventory.json

mkdir -p revision-evidence
temporal_app="ca-$TARGET_ENVIRONMENT-temporal"
jq -er --arg temporal "$temporal_app" \
  'sort_by(if .name == $temporal then 0 else 1 end) | .[].name' live-inventory.json |
  while IFS= read -r app_name; do
  app=${app_name#"ca-$TARGET_ENVIRONMENT-"}
  test "$app" != "$app_name"
  for attempt in $(seq 1 "$REVISION_READY_ATTEMPTS"); do
    az containerapp show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$app_name" \
      --query '{latestRevision:properties.latestRevisionName,latestReadyRevision:properties.latestReadyRevisionName}' \
      -o json > "revision-evidence/$app-app.json"
    latest_revision=$(jq -r '.latestRevision // empty' "revision-evidence/$app-app.json")
    latest_ready_revision=$(jq -r '.latestReadyRevision // empty' "revision-evidence/$app-app.json")
    if test -n "$latest_revision"; then
      az containerapp revision show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$app_name" \
        --revision "$latest_revision" \
        -o json > "revision-evidence/$app-revision.json"
    fi
    if test "$latest_revision" = "$latest_ready_revision" && jq -e \
      --arg app "$app_name" --arg temporal "$temporal_app" '
      .properties.active == true and
      .properties.provisioningState == "Provisioned" and
      .properties.healthState == "Healthy" and
      (if $app == $temporal then
        (.properties.replicas >= 1 and (.properties.runningState | startswith("Running")))
      else
        ((.properties.runningState | startswith("Running")) or .properties.runningState == "ScaledToZero")
      end)
    ' "revision-evidence/$app-revision.json" >/dev/null; then
      break
    fi
    echo "Revision not ready: app=$app_name attempt=$attempt/$REVISION_READY_ATTEMPTS latest=$latest_revision latest_ready=$latest_ready_revision" >&2
    if test "$attempt" = "$REVISION_READY_ATTEMPTS"; then
      cat "revision-evidence/$app-app.json" >&2
      test ! -f "revision-evidence/$app-revision.json" || cat "revision-evidence/$app-revision.json" >&2
      echo "Revision readiness timed out: app=$app_name" >&2
      exit 1
    fi
    sleep "$REVISION_READY_INTERVAL_SECONDS"
  done
done

job_name="job-$TARGET_ENVIRONMENT-deployment-verification"
az containerapp job show \
  --name "$job_name" \
  --resource-group "$RESOURCE_GROUP" \
  --output json > functional-job.json
jq -e '.properties.provisioningState == "Succeeded"' functional-job.json >/dev/null

execution_name=""
for attempt in $(seq 1 12); do
  execution_name=$(az containerapp job start \
    --name "$job_name" \
    --resource-group "$RESOURCE_GROUP" \
    --query name -o tsv) && break
  test "$attempt" != 12
  sleep 10
done
test -n "$execution_name"

capture_functional_evidence() {
  az containerapp job execution show \
    --name "$job_name" \
    --resource-group "$RESOURCE_GROUP" \
    --job-execution-name "$execution_name" \
    --output json > functional-verification.json
  for container in http-probes constitutional-health; do
    az containerapp job logs show \
      --name "$job_name" \
      --resource-group "$RESOURCE_GROUP" \
      --execution "$execution_name" \
      --container "$container" \
      --tail 200 \
      --format text > "functional-$container.log" 2>&1
    test -s "functional-$container.log"
  done
}

for attempt in $(seq 1 40); do
  az containerapp job execution show \
    --name "$job_name" \
    --resource-group "$RESOURCE_GROUP" \
    --job-execution-name "$execution_name" \
    --output json > functional-verification.json
  status=$(jq -r '.properties.status' functional-verification.json)
  case "$status" in
    Succeeded)
      capture_functional_evidence
      break
      ;;
    Failed|Stopped)
      capture_functional_evidence
      cat functional-http-probes.log >&2
      cat functional-constitutional-health.log >&2
      echo "Internal deployment verification failed with status: $status" >&2
      exit 1
      ;;
  esac
  if test "$attempt" = 40; then
    capture_functional_evidence
    cat functional-http-probes.log >&2
    cat functional-constitutional-health.log >&2
    echo "Internal deployment verification timed out with status: $status" >&2
    exit 1
  fi
  sleep 10
done

live_fqdn=$(az containerapp show --resource-group "$RESOURCE_GROUP" \
  --name "ca-$TARGET_ENVIRONMENT-web" --query properties.configuration.ingress.fqdn -o tsv)
test "$EXPECTED_WEB_URL" = "https://$live_fqdn"
if test -n "$EXPECTED_ACCESS_CIDR"; then
  live_access_cidr=$(az containerapp show --resource-group "$RESOURCE_GROUP" \
    --name "ca-$TARGET_ENVIRONMENT-web" \
    --query "properties.configuration.ingress.ipSecurityRestrictions[?name=='founder-review'].ipAddressRange | [0]" \
    -o tsv)
  test "$live_access_cidr" = "$EXPECTED_ACCESS_CIDR"
fi
jq -n \
  --arg environment "$TARGET_ENVIRONMENT" \
  --arg release_sha "$RELEASE_SHA" \
  --arg web_url "$EXPECTED_WEB_URL" \
  '{environment: $environment, release_sha: $release_sha, web_url: $web_url, exact_six_verified: true, dependencies_verified: true, revisions_verified: true, functional_verification: true}' \
  > deployment-verification.json
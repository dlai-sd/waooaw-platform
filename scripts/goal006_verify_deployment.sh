#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <environment> <manifest> <release-sha> <web-url>" >&2
  exit 2
}

test "$#" -eq 4 || usage
TARGET_ENVIRONMENT=$1
MANIFEST=$2
RELEASE_SHA=$3
EXPECTED_WEB_URL=$4
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

redact_revision_log() {
  sed -E \
    -e 's#(postgres(ql)?://[^:/[:space:]]+):[^@[:space:]]+@#\1:[REDACTED]@#g' \
    -e 's#([Bb]earer[[:space:]]+)[A-Za-z0-9._~+/-]+=*#\1[REDACTED]#g' \
    -e 's#((password|secret|token|authorization)[=:][[:space:]]*)[^,[:space:]]+#\1[REDACTED]#Ig'
}

capture_revision_failure_evidence() {
  local app_name=$1
  local app=$2
  local revision=$3
  local system_log="revision-evidence/$app-system.log"
  local containers

  if ! az containerapp logs show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$app_name" \
    --type system \
    --tail 200 \
    --format json 2>&1 | redact_revision_log > "$system_log"; then
    echo "System log capture failed for $app_name" >> "$system_log"
  fi

  test -n "$revision" || return
  containers=$(jq -r '.properties.template.containers[]?.name // empty' \
    "revision-evidence/$app-revision.json")
  if test -z "$containers"; then
    echo "Console log capture skipped: revision container metadata unavailable for $app_name" \
      > "revision-evidence/$app-console.log"
    return
  fi

  while IFS= read -r container; do
    console_log="revision-evidence/$app-$container-console.log"
    if ! az containerapp logs show \
      --resource-group "$RESOURCE_GROUP" \
      --name "$app_name" \
      --revision "$revision" \
      --container "$container" \
      --type console \
      --tail 200 \
      --format text 2>&1 | redact_revision_log > "$console_log"; then
      echo "Console log capture failed for $app_name/$container" >> "$console_log"
    fi
  done <<< "$containers"
}

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
      capture_revision_failure_evidence "$app_name" "$app" "$latest_revision"
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
if [[ "$TARGET_ENVIRONMENT" == "demo" ]]; then
  test "$EXPECTED_WEB_URL" = "https://cp.demo.waooaw.com"
  declare -A custom_domains=(
    [ca-demo-web]=cp.demo.waooaw.com
    [ca-demo-identity-edge]=auth.demo.waooaw.com
    [ca-demo-business-platform]=api.demo.waooaw.com
  )
  for app_name in "${!custom_domains[@]}"; do
    hostname=${custom_domains[$app_name]}
    az containerapp show --resource-group "$RESOURCE_GROUP" --name "$app_name" \
      --query properties.configuration.ingress.customDomains -o json \
      | jq -e --arg hostname "$hostname" \
        'any(.[]; .name == $hostname and .bindingType == "SniEnabled")' >/dev/null
  done
  for attempt in $(seq 1 60); do
    if curl --fail --silent --show-error --max-time 20 \
      "$EXPECTED_WEB_URL/privacy" \
      "$EXPECTED_WEB_URL/terms" \
      "$EXPECTED_WEB_URL/data-deletion" \
      "https://auth.demo.waooaw.com/realms/waooaw/.well-known/openid-configuration" \
      "https://api.demo.waooaw.com/health/ready" >/dev/null; then
      break
    fi
    test "$attempt" != 60 || {
      echo "Demo custom domains did not become HTTPS-ready" >&2
      exit 1
    }
    sleep 10
  done
  keycloak_revision=$(jq -r '.latestReadyRevision' revision-evidence/keycloak-app.json)
  python3 "$(dirname "$0")/verify_google_deployment.py" \
    --issuer "https://auth.demo.waooaw.com/realms/waooaw" \
    --web-url "$EXPECTED_WEB_URL" \
    --release-sha "$RELEASE_SHA" --keycloak-revision "$keycloak_revision" \
    --output google-deployment-verification.json
  python3 "$(dirname "$0")/verify_facebook_deployment.py" \
    --issuer "https://auth.demo.waooaw.com/realms/waooaw" \
    --web-url "$EXPECTED_WEB_URL" \
    --release-sha "$RELEASE_SHA" --keycloak-revision "$keycloak_revision" \
    --output facebook-deployment-verification.json
else
  test "$EXPECTED_WEB_URL" = "https://$live_fqdn"
fi
jq -n \
  --arg environment "$TARGET_ENVIRONMENT" \
  --arg release_sha "$RELEASE_SHA" \
  --arg web_url "$EXPECTED_WEB_URL" \
  '{environment: $environment, release_sha: $release_sha, web_url: $web_url, exact_seven_verified: true, dependencies_verified: true, revisions_verified: true, functional_verification: true}' \
  > deployment-verification.json
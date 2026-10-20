#!/usr/bin/env bash
set -euo pipefail

job=
container=
execution=
status=
attempt=
workspace=
resource_group=
prefix=

while [ "$#" -gt 0 ]; do
  case "$1" in
    --job) job=$2; shift 2 ;;
    --container) container=$2; shift 2 ;;
    --execution) execution=$2; shift 2 ;;
    --status) status=$2; shift 2 ;;
    --attempt) attempt=$2; shift 2 ;;
    --workspace) workspace=$2; shift 2 ;;
    --resource-group) resource_group=$2; shift 2 ;;
    --prefix) prefix=$2; shift 2 ;;
    *) echo "Unsupported argument: $1" >&2; exit 2 ;;
  esac
done

for value in "$job" "$container" "$execution" "$status" "$attempt" "$workspace" "$resource_group" "$prefix"; do
  test -n "$value"
done
grep -Eq '^[a-z0-9][a-z0-9-]{0,63}$' <<< "$execution"
case "$status" in
  Failed|Stopped|Succeeded) ;;
  *) echo "ACA execution status is not terminal: $status" >&2; exit 2 ;;
esac
case "$attempt" in
  1|2) ;;
  *) echo "ACA execution attempt is invalid: $attempt" >&2; exit 2 ;;
esac

az containerapp job execution show \
  --resource-group "$resource_group" \
  --name "$job" \
  --job-execution-name "$execution" \
  --output json > "${prefix}.execution.json"
az containerapp job logs show \
  --resource-group "$resource_group" \
  --name "$job" \
  --execution "$execution" \
  --container "$container" \
  --tail 100 \
  --format text > "${prefix}.log" 2>&1 || true

query="ContainerAppSystemLogs_CL | where TimeGenerated > ago(30m) | where ExecutionName_s == '$execution' | project TimeGenerated, ExecutionName_s, JobName_s, Reason_s, Log_s, ReplicaName_s | order by TimeGenerated asc"
for evidence_attempt in $(seq 1 6); do
  az monitor log-analytics query \
    --workspace "$workspace" \
    --analytics-query "$query" \
    --output json > "${prefix}.events.json"
  python3 scripts/goal006_aca_execution_evidence.py classify \
    --events "${prefix}.events.json" \
    --execution-name "$execution" \
    --status "$status" \
    --attempt "$attempt" \
    --output "${prefix}.classification.json"
  if [ "$status" = Succeeded ] || jq -e '.terminal_platform_failure or .application_code_started' \
    "${prefix}.classification.json" >/dev/null; then
    exit 0
  fi
  if [ "$evidence_attempt" = 6 ]; then
    echo "ACA terminal system events were not observable for $execution" >&2
    exit 1
  fi
  sleep 10
done

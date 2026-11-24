#!/usr/bin/env bash
# Implements: work-contracts/WC-168-operator-console-works-on-demo.md WC168-R011
# Constitutional basis: C-023 (evidence), C-049 (honest limits), C-065
#
# Waits until a Container App has no running replica, so a startup qualification that refuses a busy database pool does
# not race the previous copy's scale-down (Azure scales an idle app to zero only after its cooldown, about 5 minutes).
# It never treats an Azure error as "drained": a failed lookup stops the wait with a failure.
#
#   scripts/wait_for_replicas_drained.sh <app-name> <resource-group> [max-seconds=480] [interval-seconds=5]
set -euo pipefail

app="${1:?app name required}"
resource_group="${2:?resource group required}"
max_seconds="${3:-480}"
interval="${4:-5}"

started="$(date +%s)"
while true; do
  count="$(az containerapp replica list --name "$app" --resource-group "$resource_group" --query 'length(@)' --output tsv)"
  case "$count" in
    ''|*[!0-9]*) echo "Could not read the replica count of $app (got '${count}')." >&2; exit 1 ;;
  esac
  if [ "$count" = 0 ]; then
    echo "$app has no running replica."
    exit 0
  fi
  elapsed=$(( $(date +%s) - started ))
  if [ "$elapsed" -ge "$max_seconds" ]; then
    echo "$app still has $count replica(s) after ${elapsed}s; refusing to start the startup qualification over a busy pool." >&2
    exit 1
  fi
  echo "$app has $count replica(s); waiting (${elapsed}s of ${max_seconds}s)."
  sleep "$interval"
done

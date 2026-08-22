#!/usr/bin/env bash
set -euo pipefail

environment=${1:-demo}
case "$environment" in
  demo|uat|prod) ;;
  *) printf 'Environment must be demo, uat, or prod.\n' >&2; exit 64 ;;
esac

resource_group="waooaw-${environment}-runner-rg"
app_name="goal006-${environment}-runner-key-import"

scale_down() {
  az containerapp update \
    --resource-group "$resource_group" \
    --name "$app_name" \
    --min-replicas 0 \
    --max-replicas 1 \
    --output none \
    --only-show-errors || true
}
trap scale_down EXIT HUP INT TERM

az containerapp update \
  --resource-group "$resource_group" \
  --name "$app_name" \
  --min-replicas 1 \
  --max-replicas 1 \
  --output none \
  --only-show-errors

for attempt in $(seq 1 30); do
  replica=$(az containerapp replica list \
    --resource-group "$resource_group" \
    --name "$app_name" \
    --query '[0].name' \
    --output tsv \
    --only-show-errors)
  test -n "$replica" && break
  test "$attempt" != 30 || {
    printf 'Key importer did not become ready.\n' >&2
    exit 69
  }
  sleep 2
done

az containerapp exec \
  --resource-group "$resource_group" \
  --name "$app_name" \
  --container key-import \
  --replica "$replica" \
  --command /opt/waooaw/import-app-signing-material.sh

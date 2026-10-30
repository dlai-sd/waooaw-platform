#!/usr/bin/env bash
# Install the Azure CLI extensions pinned in infrastructure/runner/Dockerfile before any deployment
# step needs them. Runner images built before those pins rely on az's on-demand install, which
# fails silently when the extension index is unreachable and then reports
# "'logs' is misspelled or not recognized" (run 41042104645).
set -euo pipefail

dockerfile=${GOAL006_RUNNER_DOCKERFILE:-infrastructure/runner/Dockerfile}
attempts=${GOAL006_AZ_EXTENSION_ATTEMPTS:-4}
retry_delay=${GOAL006_AZ_EXTENSION_RETRY_SECONDS:-10}

log() {
  printf '[az-extensions] %s time=%s\n' "$*" "$(date -u +%FT%TZ)"
}

pin() {
  local value
  value=$(sed -n -E "s/^ARG $1=([^[:space:]]+)$/\1/p" "$dockerfile")
  if [ -z "$value" ]; then
    echo "::error title=Azure CLI extension pin missing::$1 is not declared in $dockerfile" >&2
    exit 1
  fi
  printf '%s' "$value"
}

ensure_extension() {
  local name=$1 version=$2 installed path attempt
  installed=$(az extension show --name "$name" --query version -o tsv 2>/dev/null || true)
  path=$(az extension show --name "$name" --query path -o tsv 2>/dev/null || true)
  # Some wheels (log-analytics 1.0.0b3) publish no version metadata; their dist-info name has it.
  if [ "$installed" = "$version" ] || { [ -n "$path" ] && [ -d "$path/${name//-/_}-$version.dist-info" ]; }; then
    log "extension=$name version=$version status=present"
    return 0
  fi
  for attempt in $(seq 1 "$attempts"); do
    if az extension add --name "$name" --version "$version" --upgrade --yes --only-show-errors; then
      log "extension=$name version=$version status=installed attempt=$attempt"
      return 0
    fi
    log "extension=$name version=$version status=retry attempt=$attempt/$attempts"
    [ "$attempt" -lt "$attempts" ] && sleep $((retry_delay * attempt))
  done
  echo "::error title=Azure CLI extension install failed::$name $version could not be installed after $attempts attempts" >&2
  exit 1
}

containerapp_version=$(pin AZ_CONTAINERAPP_EXTENSION_VERSION)
log_analytics_version=$(pin AZ_LOG_ANALYTICS_EXTENSION_VERSION)
ensure_extension containerapp "$containerapp_version"
ensure_extension log-analytics "$log_analytics_version"

# Fail here, not minutes later inside evidence capture, if the commands are still unavailable.
az containerapp job logs show --help > /dev/null
az monitor log-analytics query --help > /dev/null
log "status=ready"

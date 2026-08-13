#!/usr/bin/env bash
set -euo pipefail

readonly compose_file="docker-compose.release.yml"
readonly required_free_gb="${GOAL006_MIN_FREE_GB:-12}"
readonly release_members=(
  constitutional-engine
  business-platform
  professional-runtime
  ai-runtime
  web
  billing-engine
)
members=("${release_members[@]}")

if (( $# > 0 )); then
  members=("$@")
  for member in "${members[@]}"; do
    known_member=false
    for release_member in "${release_members[@]}"; do
      if [[ "$member" == "$release_member" ]]; then
        known_member=true
        break
      fi
    done
    if [[ "$known_member" != true ]]; then
      echo "Unknown release member: ${member}" >&2
      exit 2
    fi
  done
fi

available_gb() {
  df --output=avail -BG /workspaces | tail -1 | tr -dc '0-9'
}

cleanup_failed_build() {
  local status="$?"
  if [[ "$status" -ne 0 ]]; then
    docker image prune --force >/dev/null
    docker buildx prune --force --filter "until=1h" >/dev/null
  fi
  return "$status"
}
trap cleanup_failed_build EXIT

if (( $(available_gb) < required_free_gb )); then
  docker buildx prune --all --force
  docker image prune --force
fi

if (( $(available_gb) < required_free_gb )); then
  echo "Insufficient disk: $(available_gb)GB free; ${required_free_gb}GB required." >&2
  exit 1
fi

for member in "${members[@]}"; do
  if (( $(available_gb) < required_free_gb )); then
    docker buildx prune --all --force
    docker image prune --force
  fi
  if (( $(available_gb) < required_free_gb )); then
    echo "Insufficient disk before ${member}: $(available_gb)GB free." >&2
    exit 1
  fi
  POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-goal006-offline-build}" \
    KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-goal006-offline-build}" \
    WBE_OPS_AUTH_TOKEN="${WBE_OPS_AUTH_TOKEN:-goal006-offline-build}" \
    RAZORPAY_KEY_ID="${RAZORPAY_KEY_ID:-goal006-offline-build}" \
    RAZORPAY_KEY_SECRET="${RAZORPAY_KEY_SECRET:-goal006-offline-build}" \
    RAZORPAY_WEBHOOK_SECRET="${RAZORPAY_WEBHOOK_SECRET:-goal006-offline-build}" \
    BILLING_CONTRACT_ID="${BILLING_CONTRACT_ID:-goal006-offline-build}" \
    docker compose -f "$compose_file" build "$member"
  source_image="$(basename "$PWD")-${member}:latest"
  docker image tag "$source_image" "waooaw-${member}:phase2"
  docker image rm "$source_image" >/dev/null
  docker buildx prune --force --filter "until=1h" >/dev/null
  docker image prune --force >/dev/null
done
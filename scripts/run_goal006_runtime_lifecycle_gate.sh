#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 <evidence-json>" >&2
  exit 2
}

test "$#" = 1 || usage
EVIDENCE_JSON=$1
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON_IMAGE="python@sha256:b64631e04e4920160c50fbe8d8df828f7f35f06f425cb44aa09bca53e708a35a"
CURL_IMAGE="curlimages/curl@sha256:94e9e444bcba979c2ea12e27ae39bee4cd10bc7041a472c4727a558e213744e6"
TEMPORAL_IMAGE="temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"
POSTGRES_IMAGE="postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
NETWORK="goal006-runtime-lifecycle-$$"
RUNTIME="goal006-professional-runtime-$$"
CE_HEALTH="goal006-ce-health-$$"
POSTGRES="goal006-temporal-postgres-$$"
TEMPORAL="goal006-temporal-$$"
RUNTIME_IMAGE="goal006-professional-runtime-lifecycle:$(git -C "$REPO_ROOT" rev-parse --short=12 HEAD)"
WORK_DIR=$(mktemp -d)

cleanup() {
  docker rm -f "$RUNTIME" "$CE_HEALTH" "$TEMPORAL" "$POSTGRES" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$(dirname "$EVIDENCE_JSON")"
docker network create "$NETWORK" >/dev/null
docker build --quiet -t "$RUNTIME_IMAGE" -f "$REPO_ROOT/src/professional-runtime/Dockerfile" "$REPO_ROOT" >/dev/null
docker run -d --rm \
  --name "$CE_HEALTH" \
  --network "$NETWORK" \
  --network-alias ce-health \
  -v "$REPO_ROOT/tests/fixtures/grpc_health_server.py:/tmp/grpc_health_server.py:ro" \
  "$RUNTIME_IMAGE" python /tmp/grpc_health_server.py >/dev/null
docker run -d --rm \
  --name "$RUNTIME" \
  --network "$NETWORK" \
  --network-alias professional-runtime \
  -e BP_SERVICE_JWT_SECRET=goal006-local-lifecycle-secret \
  -e CONSTITUTIONAL_ENGINE_ADDRESS=ce-health:5002 \
  -e TEMPORAL_ADDRESS=temporal:7233 \
  -e TEMPORAL_NAMESPACE=default \
  -e TEMPORAL_STARTUP_ATTEMPTS=90 \
  -e TEMPORAL_STARTUP_INTERVAL_SECONDS=2 \
  "$RUNTIME_IMAGE" >/dev/null

initial_status=""
initial_body=""
for attempt in $(seq 1 30); do
  initial_status=$(docker run --rm --network "$NETWORK" "$CURL_IMAGE" \
    --silent --output /tmp/health.json --write-out '%{http_code}' \
    http://professional-runtime:5003/health || true)
  if test "$initial_status" = 503; then
    initial_body=$(docker run --rm --network "$NETWORK" "$CURL_IMAGE" \
      --silent http://professional-runtime:5003/health)
    break
  fi
done
test "$initial_status" = 503
test "$(jq -r '.temporalConnected' <<< "$initial_body")" = false

docker run -d --rm \
  --name "$POSTGRES" \
  --network "$NETWORK" \
  --network-alias postgres \
  -e POSTGRES_DB=temporal \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  "$POSTGRES_IMAGE" >/dev/null
for attempt in $(seq 1 30); do
  if docker exec "$POSTGRES" pg_isready -U postgres -d temporal >/dev/null 2>&1; then
    break
  fi
  test "$attempt" != 30
done
docker run -d --rm \
  --name "$TEMPORAL" \
  --network "$NETWORK" \
  --network-alias temporal \
  -e DB=postgres12 \
  -e DB_PORT=5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PWD=unused \
  -e POSTGRES_SEEDS=postgres \
  "$TEMPORAL_IMAGE" >/dev/null

ready_status=""
ready_body=""
for attempt in $(seq 1 90); do
  ready_status=$(docker run --rm --network "$NETWORK" "$CURL_IMAGE" \
    --silent --output /dev/null --write-out '%{http_code}' \
    http://professional-runtime:5003/health || true)
  if test "$ready_status" = 200; then
    ready_body=$(docker run --rm --network "$NETWORK" "$CURL_IMAGE" \
      --silent http://professional-runtime:5003/health)
    break
  fi
done
if test "$ready_status" != 200; then
  docker logs "$RUNTIME" >&2
  docker logs "$TEMPORAL" >&2
  exit 1
fi
test "$(jq -r '.temporalConnected' <<< "$ready_body")" = true
docker logs "$RUNTIME" > "$WORK_DIR/professional-runtime.log" 2>&1

jq -n \
  --arg schema "waooaw.goal006-runtime-lifecycle/v1" \
  --arg commit_sha "$(git -C "$REPO_ROOT" rev-parse HEAD)" \
  --arg runtime_image "$RUNTIME_IMAGE" \
  --arg temporal_image "$TEMPORAL_IMAGE" \
  --arg postgres_image "$POSTGRES_IMAGE" \
  --argjson initial_health "$initial_body" \
  --argjson recovered_health "$ready_body" \
  --arg log_sha256 "$(sha256sum "$WORK_DIR/professional-runtime.log" | cut -d' ' -f1)" \
  '{
    schema: $schema,
    passed: true,
    commit_sha: $commit_sha,
    runtime_image: $runtime_image,
    temporal_image: $temporal_image,
    postgres_image: $postgres_image,
    initial_http_status: 503,
    initial_health: $initial_health,
    recovered_http_status: 200,
    recovered_health: $recovered_health,
    professional_runtime_log_sha256: $log_sha256
  }' > "$EVIDENCE_JSON"

echo "GOAL-006 real-container runtime lifecycle gate passed: 503 -> 200"
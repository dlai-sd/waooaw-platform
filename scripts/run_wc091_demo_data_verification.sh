#!/bin/sh
# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §§8.1, 10
# Constitutional basis: C-023, C-059, C-080

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
IMAGE="postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
CONTAINER="wc091-demo-postgres-$$"
FIXTURE_DIGEST=$(sha256sum "$ROOT/infrastructure/identity-config/environments/demo.json" | cut -d ' ' -f 1)
GENERATION_ONE="sha256:$(printf '%s' "wc091-generation-one-$FIXTURE_DIGEST" | sha256sum | cut -d ' ' -f 1)"
GENERATION_TWO="sha256:$(printf '%s' "wc091-generation-two-$FIXTURE_DIGEST" | sha256sum | cut -d ' ' -f 1)"
OUTPUT=${1:-"$ROOT/test-results/wc091/i1-demo-data.json"}

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

wait_ready() {
  attempt=0
  while [ "$attempt" -lt 60 ]; do
    if docker exec "$CONTAINER" psql -U postgres -d waooaw -Atc "SELECT 1" >/dev/null 2>&1; then
      return 0
    fi
    attempt=$((attempt + 1))
  done
  echo "Demo PostgreSQL did not become ready" >&2
  return 1
}

start_generation() {
  generation=$1
  docker run -d --name "$CONTAINER" \
    --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=256m \
    -v "$ROOT/infrastructure/postgres/demo/reset-and-seed.sh:/wc091-reset-and-seed.sh:ro" \
    --entrypoint /bin/sh \
    -e POSTGRES_DB=waooaw \
    -e POSTGRES_HOST_AUTH_METHOD=trust \
    -e WC091_GENERATION_ID="$generation" \
    -e WC091_FIXTURE_DIGEST="$FIXTURE_DIGEST" \
    "$IMAGE" /wc091-reset-and-seed.sh >/dev/null
  wait_ready
}

assert_generation() {
  expected=$1
  actual=$(docker exec "$CONTAINER" psql -U postgres -d waooaw -Atc \
    "SELECT generation_id || ':' || fixture_digest FROM public.wc091_demo_generation;")
  [ "$actual" = "$expected:$FIXTURE_DIGEST" ]
}

start_generation "$GENERATION_ONE"
assert_generation "$GENERATION_ONE"
docker exec "$CONTAINER" psql -U postgres -d waooaw -c \
  "CREATE TABLE public.wc091_prior_generation_sentinel(value text);" >/dev/null
docker restart "$CONTAINER" >/dev/null
wait_ready
assert_generation "$GENERATION_ONE"
if docker exec "$CONTAINER" psql -U postgres -d waooaw -Atc \
  "SELECT to_regclass('public.wc091_prior_generation_sentinel');" | grep -q wc091_prior_generation_sentinel; then
  echo "prior Demo generation remained reachable after restart" >&2
  exit 1
fi

docker rm -f "$CONTAINER" >/dev/null
start_generation "$GENERATION_TWO"
assert_generation "$GENERATION_TWO"

mkdir -p "$(dirname -- "$OUTPUT")"
cat > "$OUTPUT" <<JSON
{
  "schemaVersion": "1.0",
  "workContract": "WC-091",
  "iteration": "I1",
  "result": "PASS",
  "databaseImage": "$IMAGE",
  "fixtureDigest": "$FIXTURE_DIGEST",
  "cycles": [
    {"generationId": "$GENERATION_ONE", "priorGenerationReachable": false},
    {"generationId": "$GENERATION_TWO", "priorGenerationReachable": false}
  ]
}
JSON
printf 'WC-091 Demo data verification PASS: %s\n' "$OUTPUT"
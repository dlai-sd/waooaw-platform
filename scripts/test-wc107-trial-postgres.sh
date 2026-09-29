#!/usr/bin/env bash
set -euo pipefail

container="wc107-trial-postgres-$RANDOM-$$"
network="${WAOOAW_DOCKER_NETWORK:-$(docker compose config --format json | jq -er '.networks.default.name')}"
image="postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run --rm -d --name "$container" --network "$network" \
    -e POSTGRES_PASSWORD=wc107 -e POSTGRES_DB=wc107 "$image" >/dev/null
until docker exec "$container" pg_isready -U postgres -d wc107 >/dev/null 2>&1; do :; done

docker compose --profile test run --rm --no-deps \
    -e WC107_POSTGRES_URL="postgresql://postgres:wc107@${container}:5432/wc107" \
    test-runner pytest tests/billing-engine/test_trial_postgres.py -q
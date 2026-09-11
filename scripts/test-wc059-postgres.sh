#!/usr/bin/env bash
set -euo pipefail

container="wc059-postgres-$RANDOM-$$"
network="${WAOOAW_DOCKER_NETWORK:-waooaw-dev}"
image="postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run --rm -d --name "$container" --network "$network" \
    -e POSTGRES_PASSWORD=wc059 -e POSTGRES_DB=wc059 "$image" >/dev/null
until docker exec "$container" pg_isready -U postgres -d wc059 >/dev/null 2>&1; do :; done

docker compose run --rm \
    -e WC059_POSTGRES_URL="postgresql://postgres:wc059@${container}:5432/wc059" \
    test-runner pytest tests/billing-engine/test_paid_activation_postgres.py -q
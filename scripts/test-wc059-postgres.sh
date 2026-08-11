#!/usr/bin/env bash
set -euo pipefail

container="wc059-postgres-$RANDOM-$$"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run --rm -d --name "$container" -e POSTGRES_PASSWORD=wc059 \
    -e POSTGRES_DB=wc059 -P postgres:16-alpine >/dev/null
until docker exec "$container" pg_isready -U postgres -d wc059 >/dev/null 2>&1; do :; done
port="$(docker port "$container" 5432/tcp | sed -n '1s/.*://p')"
export WC059_POSTGRES_URL="postgresql://postgres:wc059@127.0.0.1:${port}/wc059"

pytest tests/billing-engine/test_paid_activation_postgres.py -q
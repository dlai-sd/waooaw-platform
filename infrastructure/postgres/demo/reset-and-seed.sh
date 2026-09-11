#!/bin/sh
# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §8.1
# Constitutional basis: C-023, C-059, C-063

set -eu

generation_digest=${WC091_GENERATION_ID#sha256:}
if [ "${WC091_GENERATION_ID:-}" = "$generation_digest" ] \
  || [ "${#generation_digest}" -ne 64 ] \
  || printf '%s' "$generation_digest" | grep -q '[^0-9a-f]'; then
  echo "invalid WC091 generation identifier" >&2
  exit 64
fi
if [ "${#WC091_FIXTURE_DIGEST}" -ne 64 ] \
  || printf '%s' "$WC091_FIXTURE_DIGEST" | grep -q '[^0-9a-f]'; then
  echo "invalid WC091 fixture digest" >&2
  exit 64
fi

rm -rf "${PGDATA:?}"/*
cat > /docker-entrypoint-initdb.d/00-wc091-generation.sql <<SQL
CREATE TABLE IF NOT EXISTS public.wc091_demo_generation (
    generation_id TEXT PRIMARY KEY,
    fixture_digest TEXT NOT NULL
);
INSERT INTO public.wc091_demo_generation (generation_id, fixture_digest)
VALUES ('${WC091_GENERATION_ID}', '${WC091_FIXTURE_DIGEST}');
SQL

exec docker-entrypoint.sh postgres
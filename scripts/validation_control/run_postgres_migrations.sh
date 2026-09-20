#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
for file in infrastructure/postgres/init/*.sql; do
    psql "$DATABASE_URL" -f "$file"
done

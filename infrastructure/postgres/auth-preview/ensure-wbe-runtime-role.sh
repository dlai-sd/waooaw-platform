#!/bin/sh
set -eu

psql \
  -v ON_ERROR_STOP=1 \
  -v wbe_password="$POSTGRES_PASSWORD" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
ALTER ROLE wbe_app PASSWORD :'wbe_password';
SQL

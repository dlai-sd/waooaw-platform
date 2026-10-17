#!/usr/bin/env bash
set -euo pipefail

POSTGRES_IMAGE="postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
PGBOUNCER_IMAGE="docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"
suffix="${$}"
network="wc124-pgbouncer-${suffix}"
postgres_container="wc124-postgres-${suffix}"
pgbouncer_container="wc124-pgbouncer-${suffix}"
fixture_directory=$(mktemp -d "/tmp/wc124-pgbouncer-${suffix}.XXXXXX")

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    sleep 1
    docker logs "$pgbouncer_container" >&2 2>/dev/null || true
    docker logs "$postgres_container" >&2 2>/dev/null || true
  fi
  docker rm --force "$pgbouncer_container" >/dev/null 2>&1 || true
  docker rm --force "$postgres_container" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  rm -f \
    "$fixture_directory/ca.crt" \
    "$fixture_directory/ca.key" \
    "$fixture_directory/ca.srl" \
    "$fixture_directory/server.crt" \
    "$fixture_directory/server.csr" \
    "$fixture_directory/server.ext" \
    "$fixture_directory/server.key" \
    "$fixture_directory/userlist.txt" \
    "$fixture_directory/init.sql" \
    "$fixture_directory/postgres.log" \
    "$fixture_directory/pgbouncer.log"
  rmdir "$fixture_directory"
  return "$status"
}
trap cleanup EXIT

openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj "/CN=wc124-local-ca" \
  -keyout "$fixture_directory/ca.key" \
  -out "$fixture_directory/ca.crt" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes \
  -subj "/CN=postgres" \
  -keyout "$fixture_directory/server.key" \
  -out "$fixture_directory/server.csr" >/dev/null 2>&1
printf '%s\n' "subjectAltName=DNS:postgres" > "$fixture_directory/server.ext"
openssl x509 -req -days 1 \
  -in "$fixture_directory/server.csr" \
  -CA "$fixture_directory/ca.crt" \
  -CAkey "$fixture_directory/ca.key" \
  -CAcreateserial \
  -extfile "$fixture_directory/server.ext" \
  -out "$fixture_directory/server.crt" >/dev/null 2>&1
chmod 0644 "$fixture_directory/server.key"

cat > "$fixture_directory/init.sql" <<'SQL'
CREATE DATABASE waooaw_application;
CREATE DATABASE waooaw_keycloak;
CREATE DATABASE waooaw_temporal;
CREATE DATABASE waooaw_temporal_visibility;
CREATE ROLE pgbouncer_auth LOGIN PASSWORD 'pgbouncer-password' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE ce_runtime LOGIN PASSWORD 'ce-password' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE keycloak_runtime LOGIN PASSWORD 'keycloak-password' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE temporal_runtime LOGIN PASSWORD 'temporal-password' NOSUPERUSER NOBYPASSRLS;
SQL

docker network create "$network" >/dev/null
docker run --detach \
  --name "$postgres_container" \
  --network "$network" \
  --network-alias postgres \
  --env POSTGRES_PASSWORD=bootstrap-password \
  --volume "$fixture_directory:/fixture:ro" \
  "$POSTGRES_IMAGE" \
  bash -ec '
    mkdir -p /var/lib/postgresql/ssl
    cp /fixture/server.crt /fixture/server.key /fixture/ca.crt /var/lib/postgresql/ssl/
    chown -R postgres:postgres /var/lib/postgresql/ssl
    chmod 0600 /var/lib/postgresql/ssl/server.key
    cp /fixture/init.sql /docker-entrypoint-initdb.d/00-wc124-fixture.sql
    exec docker-entrypoint.sh postgres \
      -c ssl=on \
      -c ssl_cert_file=/var/lib/postgresql/ssl/server.crt \
      -c ssl_key_file=/var/lib/postgresql/ssl/server.key \
      -c ssl_ca_file=/var/lib/postgresql/ssl/ca.crt \
      -c password_encryption=scram-sha-256
  ' >/dev/null

for _ in $(seq 1 60); do
  docker logs "$postgres_container" >"$fixture_directory/postgres.log" 2>&1
  if grep -Fq "PostgreSQL init process complete; ready for start up." "$fixture_directory/postgres.log"; then
    break
  fi
  sleep 1
done
docker logs "$postgres_container" >"$fixture_directory/postgres.log" 2>&1
grep -Fq "PostgreSQL init process complete; ready for start up." "$fixture_directory/postgres.log"
for _ in $(seq 1 60); do
  if docker exec "$postgres_container" pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$postgres_container" pg_isready -U postgres >/dev/null

docker run --rm \
  --network "$network" \
  --env PGPASSWORD=pgbouncer-password \
  --env PGSSLMODE=verify-full \
  --env PGSSLROOTCERT=/certs/ca.crt \
  --volume "$fixture_directory/ca.crt:/certs/ca.crt:ro" \
  "$POSTGRES_IMAGE" \
  psql -v ON_ERROR_STOP=1 -h postgres -U pgbouncer_auth -d waooaw_application \
    -Atc "SELECT current_user" | grep -Fxq pgbouncer_auth
cat > "$fixture_directory/userlist.txt" <<'USERS'
"pgbouncer_auth" "pgbouncer-password"
"ce_runtime" "ce-password"
"keycloak_runtime" "keycloak-password"
"temporal_runtime" "temporal-password"
USERS

docker run --detach \
  --name "$pgbouncer_container" \
  --network "$network" \
  --network-alias pgbouncer \
  --env 'DATABASES=waooaw_temporal = host=postgres port=5432 pool_mode=session,waooaw_temporal_visibility = host=postgres port=5432 pool_mode=session,* = host=postgres port=5432' \
  --env PGBOUNCER_AUTH_TYPE=scram-sha-256 \
  --env PGBOUNCER_AUTH_FILE=/certs/userlist.txt \
  --env PGBOUNCER_POOL_MODE=transaction \
  --env PGBOUNCER_LISTEN_PORT=5432 \
  --env PGBOUNCER_DEFAULT_POOL_SIZE=1 \
  --env PGBOUNCER_RESERVE_POOL_SIZE=0 \
  --env PGBOUNCER_VERBOSE=2 \
  --env PGBOUNCER_SERVER_TLS_SSLMODE=verify-full \
  --env PGBOUNCER_SERVER_TLS_CA_FILE=/certs/ca.crt \
  --env 'PGBOUNCER_SERVER_RESET_QUERY=DISCARD ALL' \
  --env PGBOUNCER_SERVER_RESET_QUERY_ALWAYS=1 \
  --volume "$fixture_directory/ca.crt:/certs/ca.crt:ro" \
  --volume "$fixture_directory/userlist.txt:/certs/userlist.txt:ro" \
  "$PGBOUNCER_IMAGE" >/dev/null

for _ in $(seq 1 60); do
  docker logs "$pgbouncer_container" >"$fixture_directory/pgbouncer.log" 2>&1
  if grep -Fq "process up" "$fixture_directory/pgbouncer.log"; then
    break
  fi
  sleep 1
done
docker logs "$pgbouncer_container" >"$fixture_directory/pgbouncer.log" 2>&1
grep -Fq "server_tls_sslmode = verify-full" "$fixture_directory/pgbouncer.log"
docker exec "$pgbouncer_container" \
  grep -Fq "auth_file = /certs/userlist.txt" /etc/pgbouncer/pgbouncer.ini
docker exec "$pgbouncer_container" \
  grep -Fq "waooaw_temporal = host=postgres port=5432 pool_mode=session" /etc/pgbouncer/pgbouncer.ini

probe() {
  local database=$1
  local username=$2
  local password=$3
  docker run --rm \
    --network "$network" \
    --env "PGPASSWORD=$password" \
    "$POSTGRES_IMAGE" \
    psql -v ON_ERROR_STOP=1 -h pgbouncer -p 5432 -U "$username" -d "$database" \
      -Atc "SELECT current_database() || ':' || current_user"
}

test "$(probe waooaw_application ce_runtime ce-password)" = "waooaw_application:ce_runtime"
test "$(probe waooaw_keycloak keycloak_runtime keycloak-password)" = "waooaw_keycloak:keycloak_runtime"
test "$(probe waooaw_temporal temporal_runtime temporal-password)" = "waooaw_temporal:temporal_runtime"
test "$(probe waooaw_temporal_visibility temporal_runtime temporal-password)" = "waooaw_temporal_visibility:temporal_runtime"

if probe waooaw_application ce_runtime wrong-password >/dev/null 2>&1; then
  echo "PgBouncer accepted an invalid database credential" >&2
  exit 1
fi

docker run --rm \
  --network "$network" \
  --env PGPASSWORD=ce-password \
  "$POSTGRES_IMAGE" \
  psql -v ON_ERROR_STOP=1 -h pgbouncer -p 5432 -U ce_runtime -d waooaw_application \
    -c "SET search_path = pg_catalog" >/dev/null
test "$(
  docker run --rm \
    --network "$network" \
    --env PGPASSWORD=ce-password \
    "$POSTGRES_IMAGE" \
    psql -v ON_ERROR_STOP=1 -h pgbouncer -p 5432 -U ce_runtime -d waooaw_application \
      -Atc "SHOW search_path"
)" = '"$user", public'

echo "WC-124 PgBouncer multi-database SCRAM, TLS, denial, and reset contract passed."

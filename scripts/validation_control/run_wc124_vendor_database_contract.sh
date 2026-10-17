#!/usr/bin/env bash
set -euo pipefail

POSTGRES_IMAGE="postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
PGBOUNCER_IMAGE="docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"
KEYCLOAK_IMAGE="quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
TEMPORAL_IMAGE="temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"

suffix="${$}"
network="wc124-vendor-${suffix}"
postgres_container="wc124-vendor-postgres-${suffix}"
pgbouncer_container="wc124-vendor-pgbouncer-${suffix}"
keycloak_container="wc124-vendor-keycloak-${suffix}"
temporal_container="wc124-vendor-temporal-${suffix}"
fixture_directory=$(mktemp -d "/tmp/wc124-vendor-${suffix}.XXXXXX")

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    for container in "$keycloak_container" "$temporal_container" "$pgbouncer_container" "$postgres_container"; do
      docker logs "$container" >&2 2>/dev/null || true
    done
  fi
  docker rm --force \
    "$keycloak_container" \
    "$temporal_container" \
    "$pgbouncer_container" \
    "$postgres_container" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  find "$fixture_directory" -maxdepth 1 -type f -delete
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
CREATE DATABASE waooaw_keycloak;
CREATE DATABASE waooaw_temporal;
CREATE DATABASE waooaw_temporal_visibility;

CREATE ROLE keycloak_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE ROLE keycloak_migrator LOGIN PASSWORD 'keycloak-migration-password' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE keycloak_runtime LOGIN PASSWORD 'keycloak-runtime-password' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE temporal_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
CREATE ROLE temporal_migrator LOGIN PASSWORD 'temporal-migration-password' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE temporal_runtime LOGIN PASSWORD 'temporal-runtime-password' NOSUPERUSER NOBYPASSRLS;

GRANT keycloak_owner TO keycloak_migrator;
GRANT temporal_owner TO temporal_migrator;
ALTER ROLE keycloak_migrator IN DATABASE waooaw_keycloak SET role TO keycloak_owner;
ALTER ROLE temporal_migrator IN DATABASE waooaw_temporal SET role TO temporal_owner;
ALTER ROLE temporal_migrator IN DATABASE waooaw_temporal_visibility SET role TO temporal_owner;

REVOKE CONNECT ON DATABASE waooaw_keycloak FROM PUBLIC;
REVOKE CONNECT ON DATABASE waooaw_temporal FROM PUBLIC;
REVOKE CONNECT ON DATABASE waooaw_temporal_visibility FROM PUBLIC;
GRANT CONNECT ON DATABASE waooaw_keycloak TO keycloak_migrator, keycloak_runtime;
GRANT CONNECT ON DATABASE waooaw_temporal TO temporal_migrator, temporal_runtime;
GRANT CONNECT ON DATABASE waooaw_temporal_visibility TO temporal_migrator, temporal_runtime;

\connect waooaw_keycloak
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO keycloak_owner;
GRANT USAGE ON SCHEMA public TO keycloak_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE keycloak_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO keycloak_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE keycloak_owner IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO keycloak_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE keycloak_owner IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO keycloak_runtime;

\connect waooaw_temporal
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO temporal_owner;
GRANT USAGE ON SCHEMA public TO temporal_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE temporal_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO temporal_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE temporal_owner IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO temporal_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE temporal_owner IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO temporal_runtime;

\connect waooaw_temporal_visibility
CREATE EXTENSION IF NOT EXISTS btree_gin;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO temporal_owner;
GRANT USAGE ON SCHEMA public TO temporal_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE temporal_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO temporal_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE temporal_owner IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO temporal_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE temporal_owner IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO temporal_runtime;
SQL

cat > "$fixture_directory/userlist.txt" <<'USERS'
"keycloak_migrator" "keycloak-migration-password"
"keycloak_runtime" "keycloak-runtime-password"
"temporal_migrator" "temporal-migration-password"
"temporal_runtime" "temporal-runtime-password"
USERS

cat > "$fixture_directory/realm.json" <<'JSON'
{
  "realm": "wc124-contract",
  "enabled": true,
  "sslRequired": "none"
}
JSON

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
    cp /fixture/init.sql /docker-entrypoint-initdb.d/00-wc124-vendor.sql
    exec docker-entrypoint.sh postgres \
      -c ssl=on \
      -c ssl_cert_file=/var/lib/postgresql/ssl/server.crt \
      -c ssl_key_file=/var/lib/postgresql/ssl/server.key \
      -c ssl_ca_file=/var/lib/postgresql/ssl/ca.crt \
      -c password_encryption=scram-sha-256
  ' >/dev/null

for _ in $(seq 1 60); do
  if docker exec "$postgres_container" pg_isready -U postgres >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$postgres_container" pg_isready -U postgres >/dev/null

docker run --detach \
  --name "$pgbouncer_container" \
  --network "$network" \
  --network-alias pgbouncer \
  --env 'DATABASES=waooaw_temporal = host=postgres port=5432 pool_mode=session,waooaw_temporal_visibility = host=postgres port=5432 pool_mode=session,* = host=postgres port=5432' \
  --env PGBOUNCER_AUTH_TYPE=scram-sha-256 \
  --env PGBOUNCER_AUTH_FILE=/certs/userlist.txt \
  --env PGBOUNCER_POOL_MODE=transaction \
  --env PGBOUNCER_LISTEN_PORT=5432 \
  --env PGBOUNCER_SERVER_TLS_SSLMODE=verify-full \
  --env PGBOUNCER_SERVER_TLS_CA_FILE=/certs/ca.crt \
  --env 'PGBOUNCER_SERVER_RESET_QUERY=DISCARD ALL' \
  --env PGBOUNCER_SERVER_RESET_QUERY_ALWAYS=1 \
  --volume "$fixture_directory/ca.crt:/certs/ca.crt:ro" \
  --volume "$fixture_directory/userlist.txt:/certs/userlist.txt:ro" \
  "$PGBOUNCER_IMAGE" >/dev/null

for _ in $(seq 1 60); do
  if docker logs "$pgbouncer_container" 2>&1 | grep -Fq "process up"; then
    break
  fi
  sleep 1
done
docker logs "$pgbouncer_container" 2>&1 | grep -Fq "process up"

run_keycloak_migration() {
  docker run --rm \
    --network "$network" \
    --env KC_DB=postgres \
    --env KC_DB_URL_HOST=postgres \
    --env KC_DB_URL_PORT=5432 \
    --env KC_DB_URL_DATABASE=waooaw_keycloak \
    --env 'KC_DB_URL_PROPERTIES=?sslmode=verify-full&sslrootcert=/certs/ca.crt' \
    --env KC_DB_USERNAME=keycloak_migrator \
    --env KC_DB_PASSWORD=keycloak-migration-password \
    --env KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY=update \
    --env KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY=true \
    --volume "$fixture_directory/ca.crt:/certs/ca.crt:ro" \
    --volume "$fixture_directory/realm.json:/tmp/realm.json:ro" \
    --entrypoint /opt/keycloak/bin/kc.sh \
    "$KEYCLOAK_IMAGE" \
    import --file /tmp/realm.json --override true
}

run_temporal_migration() {
  docker run --rm \
    --network "$network" \
    --env SQL_PASSWORD=temporal-migration-password \
    --volume "$fixture_directory/ca.crt:/certs/ca.crt:ro" \
    --entrypoint /bin/bash \
    "$TEMPORAL_IMAGE" \
    -euo pipefail -c '
      migrate() {
        database="$1"
        schema_directory="$2"
        temporal-sql-tool \
          --plugin postgres12 \
          --endpoint postgres \
          --port 5432 \
          --user temporal_migrator \
          --database "$database" \
          --tls \
          --tls-ca-file /certs/ca.crt \
          --tls-server-name postgres \
          setup-schema --version 0.0
        temporal-sql-tool \
          --plugin postgres12 \
          --endpoint postgres \
          --port 5432 \
          --user temporal_migrator \
          --database "$database" \
          --tls \
          --tls-ca-file /certs/ca.crt \
          --tls-server-name postgres \
          update-schema --schema-dir "$schema_directory"
      }
      migrate waooaw_temporal /etc/temporal/schema/postgresql/v12/temporal/versioned
      migrate waooaw_temporal_visibility /etc/temporal/schema/postgresql/v12/visibility/versioned
    '
}

run_keycloak_migration
run_keycloak_migration
run_temporal_migration
run_temporal_migration

docker run --detach \
  --name "$keycloak_container" \
  --network "$network" \
  --network-alias keycloak \
  --env KC_DB=postgres \
  --env KC_DB_URL_HOST=pgbouncer \
  --env KC_DB_URL_PORT=5432 \
  --env KC_DB_URL_DATABASE=waooaw_keycloak \
  --env 'KC_DB_URL_PROPERTIES=?prepareThreshold=0' \
  --env KC_DB_USERNAME=keycloak_runtime \
  --env KC_DB_PASSWORD=keycloak-runtime-password \
  --env KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY=validate \
  --env KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY=false \
  "$KEYCLOAK_IMAGE" \
  start-dev --http-enabled=true --hostname-strict=false >/dev/null

for _ in $(seq 1 90); do
  if docker exec "$keycloak_container" /bin/bash -c '
    exec 3<>/dev/tcp/127.0.0.1/8080
    printf "GET /realms/wc124-contract/.well-known/openid-configuration HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3
    head -n 1 <&3 | grep -Eq "HTTP/1[.]1 (200|30[0-9])"
  ' >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker exec "$keycloak_container" /bin/bash -c '
  exec 3<>/dev/tcp/127.0.0.1/8080
  printf "GET /realms/wc124-contract/.well-known/openid-configuration HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3
  head -n 1 <&3 | grep -Eq "HTTP/1[.]1 (200|30[0-9])"
' >/dev/null

docker run --detach \
  --name "$temporal_container" \
  --network "$network" \
  --network-alias temporal \
  --env DB=postgres12 \
  --env DB_PORT=5432 \
  --env DBNAME=waooaw_temporal \
  --env VISIBILITY_DBNAME=waooaw_temporal_visibility \
  --env POSTGRES_USER=temporal_runtime \
  --env POSTGRES_PWD=temporal-runtime-password \
  --env POSTGRES_SEEDS=pgbouncer \
  --env SKIP_SCHEMA_SETUP=true \
  --env SKIP_DB_CREATE=true \
  --env SKIP_DEFAULT_NAMESPACE_CREATION=true \
  --env SKIP_ADD_CUSTOM_SEARCH_ATTRIBUTES=true \
  "$TEMPORAL_IMAGE" autosetup >/dev/null

for _ in $(seq 1 90); do
  if [ "$(docker inspect --format '{{.State.Running}}' "$temporal_container")" != true ]; then
    docker inspect --format 'Temporal exited: code={{.State.ExitCode}} error={{.State.Error}}' "$temporal_container" >&2
    docker logs "$temporal_container" >&2
    exit 1
  fi
  if docker exec -e TEMPORAL_ADDRESS=temporal:7233 "$temporal_container" \
    temporal operator cluster health 2>/dev/null | grep -Fq SERVING; then
    break
  fi
  sleep 2
done
docker exec -e TEMPORAL_ADDRESS=temporal:7233 "$temporal_container" \
  temporal operator cluster health | grep -Fq SERVING

for database_owner in \
  "waooaw_keycloak:keycloak_owner" \
  "waooaw_temporal:temporal_owner" \
  "waooaw_temporal_visibility:temporal_owner"; do
  database=${database_owner%%:*}
  expected_owner=${database_owner##*:}
  owners=$(docker exec -e PGPASSWORD=bootstrap-password "$postgres_container" \
    psql -At -U postgres -d "$database" \
      -c "SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname = 'public' ORDER BY tableowner")
  test "$owners" = "$expected_owner"
done

assert_runtime_denied_ddl() {
  database="$1"
  username="$2"
  password="$3"
  if docker run --rm \
    --network "$network" \
    --env "PGPASSWORD=$password" \
    "$POSTGRES_IMAGE" \
    psql -v ON_ERROR_STOP=1 -h pgbouncer -U "$username" -d "$database" \
      -c "CREATE TABLE public.runtime_must_not_create(id integer)" >/dev/null 2>&1; then
    echo "$username created DDL in $database" >&2
    exit 1
  fi
}

assert_runtime_denied_ddl waooaw_keycloak keycloak_runtime keycloak-runtime-password
assert_runtime_denied_ddl waooaw_temporal temporal_runtime temporal-runtime-password
assert_runtime_denied_ddl waooaw_temporal_visibility temporal_runtime temporal-runtime-password

echo "WC-124 vendor migrations, NOLOGIN ownership, runtime validation, and DDL denial passed."

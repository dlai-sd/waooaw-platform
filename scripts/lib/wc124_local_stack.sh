#!/usr/bin/env bash
# Shared local reproduction of the WC-124 Demo persistent PostgreSQL instance.
# There is no sidecar database: every component reaches one provisioned instance through a
# PgBouncer that authenticates each restricted role itself (SCRAM, transaction pooling), so
# identity and privilege defects surface locally instead of after a ten-minute Azure apply.
# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080

WC124_POSTGRES_IMAGE="pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
# Demo instance ceiling (foundation/main.tf max_connections; Azure Flexible Server reserves
# superuser_reserved_connections=10 and reserved_connections=5), so 25 slots serve ordinary roles.
WC124_PG_MAX_CONNECTIONS="${WC124_PG_MAX_CONNECTIONS:-40}"
WC124_PG_SUPERUSER_RESERVED="${WC124_PG_SUPERUSER_RESERVED:-10}"
WC124_PG_RESERVED="${WC124_PG_RESERVED:-5}"
WC124_PG_USABLE_CONNECTIONS=$((WC124_PG_MAX_CONNECTIONS - WC124_PG_SUPERUSER_RESERVED - WC124_PG_RESERVED))
WC124_PGBOUNCER_IMAGE="docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"
WC124_ROLE_PASSWORD="wc124-local-restricted-only"
WC124_STACK_CONTAINERS=()

wc124_stack_init() {
  WC124_RUN_ID="$1"
  WC124_NETWORK="$WC124_RUN_ID-net"
  WC124_WORKDIR="$(mktemp -d)"
  WC124_POSTGRES="$WC124_RUN_ID-postgres"
  WC124_PGBOUNCER="$WC124_RUN_ID-pgbouncer"
  trap wc124_stack_cleanup EXIT
  docker network create "$WC124_NETWORK" >/dev/null
}

wc124_stack_cleanup() {
  if [ "${WC124_KEEP_STACK:-0}" = 1 ]; then
    echo "WC124_KEEP_STACK=1: leaving $WC124_RUN_ID containers running on network $WC124_NETWORK" >&2
    return 0
  fi
  if [ "${#WC124_STACK_CONTAINERS[@]}" -gt 0 ]; then
    docker rm -f "${WC124_STACK_CONTAINERS[@]}" >/dev/null 2>&1 || true
  fi
  docker rm -f "$WC124_PGBOUNCER" "$WC124_POSTGRES" >/dev/null 2>&1 || true
  docker network rm "$WC124_NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WC124_WORKDIR"
}

wc124_track() {
  WC124_STACK_CONTAINERS+=("$@")
}

psql_admin() {
  docker exec -i "$WC124_POSTGRES" psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -At "$@"
}

psql_admin_db() {
  local database="$1"
  shift
  docker exec -i "$WC124_POSTGRES" psql -v ON_ERROR_STOP=1 -U waooaw -d "$database" -At "$@"
}

# Vendor databases on the same instance, provisioned exactly as scripts/wc124_db_provisioner.py
# provisions them for Demo (owner / migrator / runtime split).
wc124_provision_vendor_database() {
  local database="$1" owner="$2" migrator="$3" runtime="$4" extension_sql=""
  [ "$database" = waooaw_temporal_visibility ] && extension_sql="CREATE EXTENSION IF NOT EXISTS btree_gin;"
  psql_admin -c "CREATE DATABASE $database OWNER $owner" >/dev/null
  psql_admin -c "REVOKE CONNECT ON DATABASE $database FROM PUBLIC; GRANT CONNECT ON DATABASE $database TO $migrator, $runtime;" >/dev/null
  psql_admin_db "$database" >/dev/null <<EOF
$extension_sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO $owner;
GRANT $owner TO $migrator;
ALTER ROLE $migrator IN DATABASE $database SET role TO $owner;
GRANT USAGE ON SCHEMA public TO $runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE $owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO $runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE $owner IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO $runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE $owner IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO $runtime;
EOF
}

wc124_provision_temporal_databases() {
  local database
  for database in waooaw_temporal waooaw_temporal_visibility; do
    wc124_provision_vendor_database "$database" temporal_owner temporal_migrator temporal_runtime
  done
}

wc124_provision_keycloak_database() {
  wc124_provision_vendor_database waooaw_keycloak keycloak_owner keycloak_migrator keycloak_runtime
  # Keycloak connects to the instance directly (Demo does not route it through PgBouncer).
  psql_admin -c "ALTER ROLE keycloak_migrator PASSWORD '$WC124_ROLE_PASSWORD'; ALTER ROLE keycloak_runtime PASSWORD '$WC124_ROLE_PASSWORD';" >/dev/null
}

# Fresh instance with the complete governed bootstrap chain, exactly as the WC-124 provisioner
# applies it to the Demo instance.
wc124_start_postgres() {
  local root="$1"
  docker run -d --name "$WC124_POSTGRES" --network "$WC124_NETWORK" \
    -e POSTGRES_USER=waooaw -e POSTGRES_PASSWORD=waooaw-local-dev-only -e POSTGRES_DB=waooaw \
    -v "$root/infrastructure/postgres/init:/docker-entrypoint-initdb.d:ro" \
    "$WC124_POSTGRES_IMAGE" \
    -c max_connections="$WC124_PG_MAX_CONNECTIONS" \
    -c superuser_reserved_connections="$WC124_PG_SUPERUSER_RESERVED" \
    -c reserved_connections="$WC124_PG_RESERVED" >/dev/null
  for _ in $(seq 1 90); do
    if docker exec "$WC124_POSTGRES" sh -c 'test "$(head -n 1 /var/lib/postgresql/data/postmaster.pid 2>/dev/null)" = 1 && pg_isready -q -U waooaw -d waooaw'; then
      psql_admin -c 'SELECT 1' >/dev/null
      return 0
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' "$WC124_POSTGRES")" != true ]; then
      docker logs "$WC124_POSTGRES" | tail -40 >&2
      echo "bootstrap chain failed on a fresh database" >&2
      return 1
    fi
    sleep 1
  done
  echo "bootstrap chain did not become ready" >&2
  return 1
}

# Replay residual Demo Billing state captured by scripts/wc124_capture_demo_billing_state.sh.
# Prints the fixture label.
wc124_replay_billing_snapshot() {
  local snapshot="$1"
  if [ ! -f "$snapshot" ]; then
    echo "bootstrap-chain-only"
    return 0
  fi
  local ledger_owner schema_owner
  ledger_owner=$(jq -r '.relations[] | select(.relname == "waooaw_schema_migrations") | .owner' "$snapshot")
  schema_owner=$(jq -r '.schema[0].owner' "$snapshot")
  test "$schema_owner" = billing_owner
  jq -e '.memberships | any(.member == "billing_migrator" and .granted_role == "billing_owner")' "$snapshot" >/dev/null
  if [ -n "$ledger_owner" ]; then
    psql_admin >/dev/null <<EOF
SET ROLE $ledger_owner;
CREATE TABLE IF NOT EXISTS billing.waooaw_schema_migrations (
    migration_name text PRIMARY KEY,
    migration_sha256 char(64) NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
RESET ROLE;
EOF
    jq -r '.ledger_rows[] | "INSERT INTO billing.waooaw_schema_migrations (migration_name, migration_sha256) VALUES (\u0027\(.migration_name)\u0027, \u0027\(.migration_sha256)\u0027) ON CONFLICT DO NOTHING;"' "$snapshot" \
      | psql_admin >/dev/null
  fi
  echo "snapshot:$(jq -r '.execution' "$snapshot")"
}

# PgBouncer authenticates each listed role itself and connects upstream as that role
# (transaction pooling, as the Demo PgBouncer does). No administrative backend identity.
wc124_start_pgbouncer() {
  local role
  : > "$WC124_WORKDIR/userlist.txt"
  for role in "$@"; do
    psql_admin -c "ALTER ROLE $role PASSWORD '$WC124_ROLE_PASSWORD';" >/dev/null
    printf '"%s" "%s"\n' "$role" "$WC124_ROLE_PASSWORD" >> "$WC124_WORKDIR/userlist.txt"
  done
  # Database map mirrors the Demo PgBouncer: Temporal databases pool per session, all else per transaction.
  cat > "$WC124_WORKDIR/pgbouncer.ini" <<EOF
[databases]
waooaw_temporal = host=$WC124_POSTGRES port=5432 pool_mode=session
waooaw_temporal_visibility = host=$WC124_POSTGRES port=5432 pool_mode=session
* = host=$WC124_POSTGRES port=5432
[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
# Demo limits (workload/main.tf PGBOUNCER_* for environment == "demo").
max_client_conn = 40
default_pool_size = 8
reserve_pool_size = 2
ignore_startup_parameters = extra_float_digits
EOF
  chmod 644 "$WC124_WORKDIR/pgbouncer.ini" "$WC124_WORKDIR/userlist.txt"
  docker run -d --name "$WC124_PGBOUNCER" --network "$WC124_NETWORK" \
    -v "$WC124_WORKDIR/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini:ro" \
    -v "$WC124_WORKDIR/userlist.txt:/etc/pgbouncer/userlist.txt:ro" \
    --entrypoint /opt/pgbouncer/pgbouncer "$WC124_PGBOUNCER_IMAGE" /etc/pgbouncer/pgbouncer.ini >/dev/null
  sleep 2
  if [ "$(docker inspect -f '{{.State.Running}}' "$WC124_PGBOUNCER")" != true ]; then
    docker logs "$WC124_PGBOUNCER" >&2
    return 1
  fi
}

wc124_role_url() {
  echo "postgresql://$1:$WC124_ROLE_PASSWORD@$WC124_PGBOUNCER:5432/waooaw?sslmode=disable"
}

wc124_role_npgsql() {
  echo "Host=$WC124_PGBOUNCER;Port=5432;Database=waooaw;Username=$1;Password=$WC124_ROLE_PASSWORD;SSL Mode=Disable;Pooling=true"
}

# session_user observed on the PostgreSQL backend when connecting through PgBouncer as a role.
wc124_backend_identity() {
  docker run --rm --network "$WC124_NETWORK" -e PGPASSWORD="$WC124_ROLE_PASSWORD" "$WC124_POSTGRES_IMAGE" \
    psql -h "$WC124_PGBOUNCER" -p 5432 -U "$1" -d waooaw -At -c 'SELECT session_user'
}

#!/usr/bin/env bash
# Fast local qualification of the Demo "Billing migration through PgBouncer" step.
# Reproduces the Demo database state (bootstrap chain + residual state from a captured
# snapshot) and runs the exact Billing image as the restricted billing_migrator identity
# through a PgBouncer that authenticates per role (no admin backend identity).
# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SNAPSHOT="${WC124_DEMO_SNAPSHOT:-$ROOT/test-results/wc124/demo-billing-state.json}"
IMAGE="${WC124_BILLING_IMAGE:-}"
EVIDENCE_DIR="${WC124_EVIDENCE_DIR:-$ROOT/test-results/wc124/billing-migration-local}"
POSTGRES_IMAGE="pgvector/pgvector@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b"
PGBOUNCER_IMAGE="docker.io/pgbouncer/pgbouncer@sha256:e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"
MIGRATOR_PASSWORD="wc124-local-restricted-only"
RUN_ID="wc124bl$(date +%s)"
NETWORK="$RUN_ID-net"
WORKDIR="$(mktemp -d)"

cleanup() {
  docker rm -f "$RUN_ID-pgbouncer" "$RUN_ID-postgres" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$WORKDIR"
}
trap cleanup EXIT
mkdir -p "$EVIDENCE_DIR"

psql_admin() {
  docker exec -i "$RUN_ID-postgres" psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -At "$@"
}

if [ -z "$IMAGE" ]; then
  IMAGE="waooaw/billing-engine:$RUN_ID"
  docker build --quiet --file "$ROOT/src/billing-engine/Dockerfile" --tag "$IMAGE" "$ROOT" >/dev/null
fi
image_digest=$(docker image inspect "$IMAGE" --format '{{.Id}}')

docker network create "$NETWORK" >/dev/null
docker run -d --name "$RUN_ID-postgres" --network "$NETWORK" \
  -e POSTGRES_USER=waooaw -e POSTGRES_PASSWORD=waooaw-local-dev-only -e POSTGRES_DB=waooaw \
  -v "$ROOT/infrastructure/postgres/init:/docker-entrypoint-initdb.d:ro" \
  "$POSTGRES_IMAGE" >/dev/null
for _ in $(seq 1 90); do
  if docker exec "$RUN_ID-postgres" sh -c 'test "$(head -n 1 /var/lib/postgresql/data/postmaster.pid 2>/dev/null)" = 1 && pg_isready -q -U waooaw -d waooaw'; then
    break
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$RUN_ID-postgres")" != true ]; then
    docker logs "$RUN_ID-postgres" | tail -40 >&2
    echo "bootstrap chain failed on a fresh database" >&2
    exit 1
  fi
  sleep 1
done
psql_admin -c 'SELECT 1' >/dev/null

# Replay Demo residual state: the ledger created by an earlier runner revision under the
# login identity, and any migrations already recorded there.
psql_admin -c "ALTER ROLE billing_migrator PASSWORD '$MIGRATOR_PASSWORD';" >/dev/null >/dev/null
if [ -f "$SNAPSHOT" ]; then
  snapshot_ledger_owner=$(jq -r '.relations[] | select(.relname == "waooaw_schema_migrations") | .owner' "$SNAPSHOT")
  snapshot_schema_owner=$(jq -r '.schema[0].owner' "$SNAPSHOT")
  test "$snapshot_schema_owner" = billing_owner
  jq -e '.memberships | any(.member == "billing_migrator" and .granted_role == "billing_owner")' "$SNAPSHOT" >/dev/null
  if [ -n "$snapshot_ledger_owner" ]; then
    psql_admin >/dev/null <<EOF
SET ROLE $snapshot_ledger_owner;
CREATE TABLE IF NOT EXISTS billing.waooaw_schema_migrations (
    migration_name text PRIMARY KEY,
    migration_sha256 char(64) NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
RESET ROLE;
EOF
    jq -r '.ledger_rows[] | "INSERT INTO billing.waooaw_schema_migrations (migration_name, migration_sha256) VALUES (\u0027\(.migration_name)\u0027, \u0027\(.migration_sha256)\u0027) ON CONFLICT DO NOTHING;"' "$SNAPSHOT" \
      | psql_admin >/dev/null
  fi
  fixture_source="snapshot:$(jq -r '.execution' "$SNAPSHOT")"
else
  fixture_source="bootstrap-chain-only"
fi

# PgBouncer authenticates the client role itself and connects upstream as that role.
cat > "$WORKDIR/pgbouncer.ini" <<EOF
[databases]
waooaw = host=$RUN_ID-postgres port=5432 dbname=waooaw
[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5433
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 50
default_pool_size = 5
ignore_startup_parameters = extra_float_digits
EOF
printf '"billing_migrator" "%s"\n' "$MIGRATOR_PASSWORD" > "$WORKDIR/userlist.txt"
chmod 644 "$WORKDIR/pgbouncer.ini" "$WORKDIR/userlist.txt"
docker run -d --name "$RUN_ID-pgbouncer" --network "$NETWORK" \
  -v "$WORKDIR/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini:ro" \
  -v "$WORKDIR/userlist.txt:/etc/pgbouncer/userlist.txt:ro" \
  --entrypoint /opt/pgbouncer/pgbouncer "$PGBOUNCER_IMAGE" /etc/pgbouncer/pgbouncer.ini >/dev/null
sleep 2
test "$(docker inspect -f '{{.State.Running}}' "$RUN_ID-pgbouncer")" = true || { docker logs "$RUN_ID-pgbouncer" >&2; exit 1; }

run_migration() {
  docker run --rm --network "$NETWORK" \
    -e DATABASE_URL="postgresql://billing_migrator:$MIGRATOR_PASSWORD@$RUN_ID-pgbouncer:5433/waooaw" \
    -e MIGRATION_PATTERN=59-wc124-billing-authority.sql \
    -e MIGRATION_SCHEMA=billing \
    "$IMAGE" python migrate.py
}

run_migration > "$EVIDENCE_DIR/first-run.log" 2>&1 || { cat "$EVIDENCE_DIR/first-run.log" >&2; echo "first migration run failed" >&2; exit 1; }
run_migration > "$EVIDENCE_DIR/second-run.log" 2>&1 || { cat "$EVIDENCE_DIR/second-run.log" >&2; echo "idempotent rerun failed" >&2; exit 1; }

ledger_owner=$(psql_admin -c "SELECT pg_get_userbyid(relowner) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'billing' AND c.relname = 'waooaw_schema_migrations'")
ledger_entry=$(psql_admin -c "SELECT migration_sha256 FROM billing.waooaw_schema_migrations WHERE migration_name = '59-wc124-billing-authority.sql'")
expected_digest=$(sha256sum "$ROOT/infrastructure/postgres/init/59-wc124-billing-authority.sql" | cut -d' ' -f1)
foreign_owned=$(psql_admin -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'billing' AND c.relkind IN ('r','S') AND pg_get_userbyid(c.relowner) <> 'billing_owner'")
backend_identity=$(docker run --rm --network "$NETWORK" -e PGPASSWORD="$MIGRATOR_PASSWORD" "$POSTGRES_IMAGE" \
  psql -h "$RUN_ID-pgbouncer" -p 5433 -U billing_migrator -d waooaw -At -c 'SELECT session_user')

test "$ledger_owner" = billing_owner
test "$ledger_entry" = "$expected_digest"
test "$foreign_owned" = 0
test "$backend_identity" = billing_migrator

jq -n \
  --arg schema "waooaw.wc124-billing-migration-local/v1" \
  --arg image "$IMAGE" --arg image_id "$image_digest" --arg fixture "$fixture_source" \
  --arg ledger_owner "$ledger_owner" --arg digest "$ledger_entry" --arg backend "$backend_identity" \
  '{schema: $schema, image: $image, image_id: $image_id, fixture: $fixture, route: "pgbouncer-scram-per-role",
    login: "billing_migrator", backend_identity: $backend, ledger_owner: $ledger_owner,
    recorded_migration_sha256: $digest, idempotent_rerun: true, status: "passed"}' \
  | tee "$EVIDENCE_DIR/result.json"

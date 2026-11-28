#!/usr/bin/env bash
# Local qualification of the WC-177 database update path against fresh pinned pgvector instances.
#
# Replica of the Demo role model: a NON-superuser bootstrap principal applies the base chain with the
# real provisioner functions (ledger, REASSIGN OWNED, update principal), then the real apply program
# scripts/wc177_database_update.sh applies pending update-class files as database_updater through a
# local PgBouncer in transaction mode. It proves:
#   1. the plan chooses `update` for one new declared file and `full` for undeclared, unclassified and
#      changed-digest files;
#   2. zero pg_dump --schema-only drift between "full chain" and "base chain plus update";
#   3. the apply program refuses an undeclared, an unclassified and a changed-digest file and a tampered manifest;
#   4. a held conflicting lock fails in a bounded way and a clean retry succeeds, and a short lock is retried;
#   5. the update principal holds exactly bp_owner and wbe_owner and no bootstrap-owned objects remain.
# Evidence: test-results/wc124/init-chain-local/wc177-database-update-local.json
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/wc124_local_stack.sh
. "$ROOT/scripts/lib/wc124_local_stack.sh"

EVIDENCE_DIR="${WC177_EVIDENCE_DIR:-$ROOT/test-results/wc124/init-chain-local}"
DATABASE=waooaw_application
UPDATER_PASSWORD="wc177-local-updater-only"
mkdir -p "$EVIDENCE_DIR"

RUN_ID="wc177u$(date +%s)"
wc124_stack_init "$RUN_ID"
# Bind-mounted files must exist on the Docker host: keep the work directory under the repository (also when this
# script itself runs in a container that mounts the repository at the same path).
rm -rf "$WC124_WORKDIR"
WC124_WORKDIR="$ROOT/test-results/wc124/wc177-work-$RUN_ID"
mkdir -p "$WC124_WORKDIR"
FULL="$RUN_ID-full"
BASE="$RUN_ID-base"
WC124_PGBOUNCER="$RUN_ID-pgbouncer"
trap 'docker rm -f "$FULL" "$BASE" "$WC124_PGBOUNCER" >/dev/null 2>&1 || true; wc124_stack_cleanup' EXIT
WORK="$WC124_WORKDIR"

# Repository stand-in: the real init files plus the fixtures this qualification adds.
mkdir -p "$WORK/repo-base/infrastructure/postgres/init"
cp "$ROOT"/infrastructure/postgres/init/*.sql "$WORK/repo-base/infrastructure/postgres/init/"
INIT_BASE="$WORK/repo-base/infrastructure/postgres/init"
FIXTURE=99zzzzzzzz-wc177-zz-fixture.sql
LOCK_PROBE=99zzzzzzzz-wc177-zzz-lock-probe.sql

write_fixture() {
  cat > "$1/$FIXTURE" <<'EOF'
-- wc177-apply: update
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;
CREATE TABLE IF NOT EXISTS business.wc177_fixture_probe (
    probe_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    note text NOT NULL DEFAULT 'wc177'
);
GRANT SELECT ON business.wc177_fixture_probe TO business_app;
EOF
}

start_instance() {
  local name="$1"
  docker run -d --name "$name" --network "$WC124_NETWORK" \
    -e POSTGRES_USER=waooaw -e POSTGRES_PASSWORD=waooaw-local-dev-only -e POSTGRES_DB="$DATABASE" \
    "$WC124_POSTGRES_IMAGE" -c max_connections=60 >/dev/null
  for _ in $(seq 1 90); do
    if docker exec "$name" sh -c "test \"\$(head -n 1 /var/lib/postgresql/data/postmaster.pid 2>/dev/null)\" = 1 && pg_isready -q -U waooaw -d $DATABASE"; then
      break
    fi
    sleep 1
  done
  docker exec -i "$name" psql -v ON_ERROR_STOP=1 -q -U waooaw -d "$DATABASE" >/dev/null <<EOF
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE ROLE bootstrap_local LOGIN CREATEROLE CREATEDB NOSUPERUSER NOBYPASSRLS;
-- The Azure bootstrap principal belongs to azure_pg_admin and can use every role it creates; the replica gives
-- the same reach without superuser through createrole_self_grant (PostgreSQL 16).
ALTER ROLE bootstrap_local SET createrole_self_grant = 'set, inherit';
GRANT CONNECT, CREATE ON DATABASE $DATABASE TO bootstrap_local;
ALTER DATABASE $DATABASE OWNER TO bootstrap_local;
GRANT ALL ON SCHEMA public TO bootstrap_local;
EOF
}

# Runs the real provisioner functions (bootstrap SQL, ledger, init chain, update principal) as the
# non-superuser bootstrap principal; only the psql transport is substituted (docker exec).
provision() {
  local container="$1" init_dir="$2"
  WC177_CONTAINER="$container" WC177_INIT="$init_dir" WC177_DATABASE="$DATABASE" WC177_PASSWORD="$UPDATER_PASSWORD" \
  PYTHONPATH="$ROOT/scripts" python - <<'EOF'
import json
import os
import subprocess
from pathlib import Path

import wc124_db_provisioner as provisioner

container = os.environ["WC177_CONTAINER"]


def local_psql(_server, bootstrap, database, _token, sql, *, tuples_only=False):
    command = ["docker", "exec", "-i", container, "psql", "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "-q", "-U", bootstrap, "-d", database]
    if tuples_only:
        command += ["--tuples-only", "--no-align", "--field-separator=\t"]
    completed = subprocess.run(command, input=sql, capture_output=True, text=True, check=False)  # noqa: S603
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return completed.stdout


provisioner.psql = local_psql
init = Path(os.environ["WC177_INIT"])
bootstrap = "bootstrap_local"
application = os.environ["WC177_DATABASE"]
role_sql = (init / provisioner.PRINCIPAL_BOOTSTRAP_NAME).read_text(encoding="utf-8")
role_sql += f"\nALTER ROLE {provisioner.UPDATE_PRINCIPAL} PASSWORD {provisioner.sql_literal(os.environ['WC177_PASSWORD'])};"
local_psql("local", bootstrap, application, "none", role_sql)
files = provisioner.application_migration_files(init)
local_psql("local", bootstrap, application, "none", f"GRANT bp_owner TO {bootstrap};")
try:
    outcome = provisioner.apply_init_chain("local", bootstrap, "none", files)
finally:
    local_psql("local", bootstrap, application, "none", f"REVOKE bp_owner FROM {bootstrap};")
local_psql("local", bootstrap, application, "none", f"GRANT CONNECT ON DATABASE {application} TO {provisioner.UPDATE_PRINCIPAL};")
principal = provisioner.provision_update_principal("local", bootstrap, "none")
print(json.dumps({"files": len(files), "applied": len(outcome["applied"]), "update_principal": principal}))
EOF
}

dump_schema() {
  docker exec "$1" pg_dump -U waooaw -d "$DATABASE" --schema-only --no-owner --no-privileges \
    | grep -v '^--' | grep -v '^\\restrict\|^\\unrestrict'
}

psql_su() {
  local container="$1"
  shift
  docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U waooaw -d "$DATABASE" -At "$@"
}

# Real plan: the repository stand-in against a record of the applied base chain.
plan() {
  local repo="$1" output="$2" requested="${3:-auto}"
  mkdir -p "$output"
  WC177_REPO="$repo" WC177_OUT="$output" WC177_REQUESTED="$requested" WC177_BASE="$INIT_BASE" PYTHONPATH="$ROOT/scripts" python - <<'EOF'
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import wc143_database_chain_record as chain

base = Path(os.environ["WC177_BASE"]).parent.parent.parent
applied = chain.init_file_digests(base)
record = chain.create_record(
    environment="demo",
    fingerprint="f" * 64,
    live_facts={"environment": "demo"},
    provisioner_result={
        "schema": chain.PROVISIONER_RESULT_SCHEMA,
        "execution": "local",
        "database_reset": None,
        "identity_schema": {"status": "passed"},
        "update_principal": {"memberships": ["bp_owner", "wbe_owner"]},
    },
    provisioner_execution={"name": "local", "properties": {"status": "Succeeded"}},
    run_id="local",
    recorded_at=datetime.now(timezone.utc),
    applied_init_files=applied,
)
out = Path(os.environ["WC177_OUT"])
(out / "record.json").write_text(json.dumps(record), encoding="utf-8")
(out / "facts.json").write_text(json.dumps({"environment": "demo"}), encoding="utf-8")
(out / "transition.json").write_text(json.dumps({"state": "REVOKED"}), encoding="utf-8")
completed = subprocess.run(
    [
        sys.executable, str(Path(chain.__file__)), "evaluate",
        "--record", str(out / "record.json"), "--environment", "demo", "--fingerprint", "f" * 64,
        "--live-facts", str(out / "facts.json"), "--transition", str(out / "transition.json"),
        "--reset-requested", "false", "--database-path", os.environ["WC177_REQUESTED"],
        "--repository-root", os.environ["WC177_REPO"], "--output-directory", str(out),
    ],
    capture_output=True, text=True, check=False,
)  # noqa: S603
(out / "decision.json").write_text(completed.stdout, encoding="utf-8")
EOF
}

# Run the real apply program in the pinned image on the local network, through PgBouncer.
run_update() {
  local out="$1"
  shift
  docker run --rm --network "$WC124_NETWORK" \
    -e DATABASE_URL="postgresql://database_updater:$UPDATER_PASSWORD@$WC124_PGBOUNCER:5432/$DATABASE?sslmode=disable" \
    -e UPDATE_PAYLOAD_B64="$(cat "$out/wc177-database-update-payload.b64")" \
    -e UPDATE_MANIFEST="$(cat "$out/wc177-database-update-manifest.txt")" \
    -e UPDATE_MANIFEST_SHA256="$(jq -r '.manifest_sha256' "$out/decision.json")" \
    "$@" \
    -v "$ROOT/scripts/wc177_database_update.sh:/update.sh:ro" \
    "$WC124_POSTGRES_IMAGE" sh /update.sh
}

start_instance "$FULL"
start_instance "$BASE"

# Reference: the complete chain, fixture included, applied by the bootstrap principal.
mkdir -p "$WORK/repo-full/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-full/infrastructure/postgres/init/"
write_fixture "$WORK/repo-full/infrastructure/postgres/init"
provision "$FULL" "$WORK/repo-full/infrastructure/postgres/init" > "$WORK/full.json"

# Replica: base chain only, with the update principal created exactly as the full path creates it.
provision "$BASE" "$INIT_BASE" > "$WORK/base.json"
test "$(jq -r '.update_principal.memberships | join(",")' "$WORK/base.json")" = "bp_owner,wbe_owner"
if [ "$(jq -r '.update_principal.bootstrap_owned_objects_after' "$WORK/base.json")" != 0 ]; then
  echo "bootstrap-owned objects remain after REASSIGN OWNED:" >&2
  psql_su "$BASE" -c "SELECT 'class', n.nspname, c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relowner = 'bootstrap_local'::regrole UNION ALL SELECT 'proc', n.nspname, p.proname, p.prokind FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace WHERE p.proowner = 'bootstrap_local'::regrole UNION ALL SELECT 'schema', nspname, '', '' FROM pg_namespace WHERE nspowner = 'bootstrap_local'::regrole UNION ALL SELECT 'type', n.nspname, t.typname, t.typtype FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace WHERE t.typowner = 'bootstrap_local'::regrole" >&2
fi
test "$(jq -r '.update_principal.bootstrap_owned_objects_after' "$WORK/base.json")" = 0

# PgBouncer in transaction mode between the update principal and the replica.
printf '"database_updater" "%s"\n' "$UPDATER_PASSWORD" > "$WORK/userlist.txt"
cat > "$WORK/pgbouncer.ini" <<EOF
[databases]
* = host=$BASE port=5432
[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 20
default_pool_size = 2
ignore_startup_parameters = extra_float_digits
EOF
psql_su "$BASE" -c "ALTER ROLE database_updater PASSWORD '$UPDATER_PASSWORD'" >/dev/null
chmod 644 "$WORK/pgbouncer.ini" "$WORK/userlist.txt"
docker run -d --name "$WC124_PGBOUNCER" --network "$WC124_NETWORK" \
  -v "$WORK/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini:ro" -v "$WORK/userlist.txt:/etc/pgbouncer/userlist.txt:ro" \
  --entrypoint /opt/pgbouncer/pgbouncer "$WC124_PGBOUNCER_IMAGE" /etc/pgbouncer/pgbouncer.ini >/dev/null
sleep 2
if [ "$(docker inspect -f '{{.State.Running}}' "$WC124_PGBOUNCER")" != true ]; then
  docker logs "$WC124_PGBOUNCER" >&2
  echo "PgBouncer did not start" >&2
  exit 1
fi

# 1. Plan: one new declared file selects `update`; the same repository with no new file selects `reuse`.
plan "$WORK/repo-base" "$WORK/plan-reuse"
test "$(jq -r '.path' "$WORK/plan-reuse/decision.json")" = reuse
mkdir -p "$WORK/repo-update/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-update/infrastructure/postgres/init/"
write_fixture "$WORK/repo-update/infrastructure/postgres/init"
plan "$WORK/repo-update" "$WORK/plan-update"
test "$(jq -r '.path' "$WORK/plan-update/decision.json")" = update
test "$(jq -r '.added_files | join(",")' "$WORK/plan-update/decision.json")" = "$FIXTURE"

# 1b. Fail-closed plans: undeclared, unclassified, changed digest, forced full.
mkdir -p "$WORK/repo-undeclared/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-undeclared/infrastructure/postgres/init/"
tail -n +2 "$WORK/repo-update/infrastructure/postgres/init/$FIXTURE" > "$WORK/repo-undeclared/infrastructure/postgres/init/$FIXTURE"
plan "$WORK/repo-undeclared" "$WORK/plan-undeclared"
test "$(jq -r '.path' "$WORK/plan-undeclared/decision.json")" = full
mkdir -p "$WORK/repo-unclassified/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-unclassified/infrastructure/postgres/init/"
{ echo "-- wc177-apply: maybe"; tail -n +2 "$WORK/repo-update/infrastructure/postgres/init/$FIXTURE"; } > "$WORK/repo-unclassified/infrastructure/postgres/init/$FIXTURE"
plan "$WORK/repo-unclassified" "$WORK/plan-unclassified"
test "$(jq -r '.path' "$WORK/plan-unclassified/decision.json")" = full
mkdir -p "$WORK/repo-changed/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-changed/infrastructure/postgres/init/"
echo "-- changed after it was applied" >> "$WORK/repo-changed/infrastructure/postgres/init/01-schemas.sql"
plan "$WORK/repo-changed" "$WORK/plan-changed"
test "$(jq -r '.path' "$WORK/plan-changed/decision.json")" = full
plan "$WORK/repo-update" "$WORK/plan-forced" full
test "$(jq -r '.path' "$WORK/plan-forced/decision.json")" = full

# 2. Apply through PgBouncer as the update principal; every statement ran as an owner role.
run_update "$WORK/plan-update" > "$WORK/update-1.log"
result=$(grep -o 'WC177_UPDATE_RESULT {.*}' "$WORK/update-1.log" | sed 's/^WC177_UPDATE_RESULT //')
test "$(jq -r '.status' <<<"$result")" = passed
test "$(jq -r '.applied | join(",")' <<<"$result")" = "$FIXTURE"
test "$(jq -r '.login' <<<"$result")" = database_updater
test "$(jq -r '.memberships' <<<"$result")" = "bp_owner,wbe_owner"
test "$(psql_su "$BASE" -c "SELECT tableowner FROM pg_tables WHERE schemaname='business' AND tablename='wc177_fixture_probe'")" = bp_owner
test "$(psql_su "$FULL" -c "SELECT tableowner FROM pg_tables WHERE schemaname='business' AND tablename='wc177_fixture_probe'")" = bp_owner
# A second run applies nothing and still verifies.
run_update "$WORK/plan-update" > "$WORK/update-2.log"
second=$(grep -o 'WC177_UPDATE_RESULT {.*}' "$WORK/update-2.log" | sed 's/^WC177_UPDATE_RESULT //')
test "$(jq -r '.applied | length' <<<"$second")" = 0
test "$(jq -r '.skipped | join(",")' <<<"$second")" = "$FIXTURE"

# 3. Zero schema drift between the full chain and the base chain plus the update.
dump_schema "$FULL" > "$WORK/schema-full.sql"
dump_schema "$BASE" > "$WORK/schema-update.sql"
drift=$(diff "$WORK/schema-full.sql" "$WORK/schema-update.sql" | grep -c '^[<>]' || true)
test "$drift" = 0
test "$(psql_su "$FULL" -c "SELECT count(*) FROM wc124_provisioning.init_chain_ledger")" = "$(psql_su "$BASE" -c "SELECT count(*) FROM wc124_provisioning.init_chain_ledger")"

# 4. The apply program refuses what the plan would not send.
refused() {
  local label="$1" out="$2"
  shift 2
  if run_update "$out" "$@" > "$WORK/refused-$label.log" 2>&1; then
    echo "update was not refused: $label" >&2
    return 1
  fi
  grep -q 'WC177_UPDATE_REFUSED' "$WORK/refused-$label.log"
}
payload_for() {
  local repo="$1" out="$2" name="$3"
  mkdir -p "$out"
  WC177_REPO="$repo" WC177_OUT="$out" WC177_NAME="$name" PYTHONPATH="$ROOT/scripts" python - <<'EOF'
import hashlib
import json
import os
from pathlib import Path

import wc143_database_chain_record as chain

repo = Path(os.environ["WC177_REPO"])
out = Path(os.environ["WC177_OUT"])
payload, manifest = chain.update_payload(repo, [os.environ["WC177_NAME"]])
(out / "wc177-database-update-payload.b64").write_text(payload, encoding="utf-8")
(out / "wc177-database-update-manifest.txt").write_text(manifest, encoding="utf-8")
(out / "decision.json").write_text(json.dumps({"manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest()}), encoding="utf-8")
EOF
}
payload_for "$WORK/repo-undeclared" "$WORK/pl-undeclared" "$FIXTURE"
refused undeclared "$WORK/pl-undeclared"
payload_for "$WORK/repo-unclassified" "$WORK/pl-unclassified" "$FIXTURE"
refused unclassified "$WORK/pl-unclassified"
# Changed digest: same name as an applied file, different content.
mkdir -p "$WORK/repo-edited/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-edited/infrastructure/postgres/init/"
{ cat "$WORK/repo-update/infrastructure/postgres/init/$FIXTURE"; echo "COMMENT ON TABLE business.wc177_fixture_probe IS 'edited';"; } > "$WORK/repo-edited/infrastructure/postgres/init/$FIXTURE"
payload_for "$WORK/repo-edited" "$WORK/pl-edited" "$FIXTURE"
refused changed-digest "$WORK/pl-edited"
# Tampered manifest digest.
cp -r "$WORK/plan-update" "$WORK/pl-tampered"
jq '.manifest_sha256 = ("0" * 64)' "$WORK/pl-tampered/decision.json" > "$WORK/pl-tampered/decision.next" && mv "$WORK/pl-tampered/decision.next" "$WORK/pl-tampered/decision.json"
refused tampered-manifest "$WORK/pl-tampered"

# 5. Lock handling: a held conflicting lock fails in a bounded way; a clean retry succeeds; a short lock is retried.
mkdir -p "$WORK/repo-lock/infrastructure/postgres/init"
cp "$INIT_BASE"/*.sql "$WORK/repo-lock/infrastructure/postgres/init/"
cp "$WORK/repo-update/infrastructure/postgres/init/$FIXTURE" "$WORK/repo-lock/infrastructure/postgres/init/$FIXTURE"
cat > "$WORK/repo-lock/infrastructure/postgres/init/$LOCK_PROBE" <<'EOF'
-- wc177-apply: update
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;
ALTER TABLE business.wc177_fixture_probe ADD COLUMN IF NOT EXISTS lock_probe text;
EOF
payload_for "$WORK/repo-lock" "$WORK/pl-lock" "$LOCK_PROBE"
hold_lock() {
  docker exec -d "$BASE" psql -U waooaw -d "$DATABASE" -c "BEGIN; LOCK TABLE business.wc177_fixture_probe IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep($1); COMMIT;"
  sleep 1
}
hold_lock 9
if run_update "$WORK/pl-lock" -e UPDATE_LOCK_RETRIES=2 -e UPDATE_LOCK_PAUSE_SECONDS=1 > "$WORK/lock-fail.log" 2>&1; then
  echo "update succeeded while a conflicting lock was held" >&2
  exit 1
fi
grep -q 'WC177_UPDATE_LOCK_TIMEOUT' "$WORK/lock-fail.log"
grep -q 'WC177_UPDATE_FAILED' "$WORK/lock-fail.log"
test "$(psql_su "$BASE" -c "SELECT count(*) FROM wc124_provisioning.init_chain_ledger WHERE file_name = '$LOCK_PROBE'")" = 0
sleep 8
run_update "$WORK/pl-lock" > "$WORK/lock-retry-clean.log"
grep -q '"status":"passed"' "$WORK/lock-retry-clean.log"
test "$(psql_su "$BASE" -c "SELECT count(*) FROM wc124_provisioning.init_chain_ledger WHERE file_name = '$LOCK_PROBE'")" = 1
# Short lock: the first attempt times out, the retry applies. Use a fresh file name so the ledger is empty for it.
mv "$WORK/repo-lock/infrastructure/postgres/init/$LOCK_PROBE" "$WORK/repo-lock/infrastructure/postgres/init/99zzzzzzzz-wc177-zzzz-lock-retry.sql"
sed -i 's/lock_probe/lock_retry/' "$WORK/repo-lock/infrastructure/postgres/init/99zzzzzzzz-wc177-zzzz-lock-retry.sql"
payload_for "$WORK/repo-lock" "$WORK/pl-retry" 99zzzzzzzz-wc177-zzzz-lock-retry.sql
hold_lock 4
run_update "$WORK/pl-retry" -e UPDATE_LOCK_RETRIES=3 -e UPDATE_LOCK_PAUSE_SECONDS=1 > "$WORK/lock-retry.log" 2>&1
retry_result=$(grep -o 'WC177_UPDATE_RESULT {.*}' "$WORK/lock-retry.log" | sed 's/^WC177_UPDATE_RESULT //')
test "$(jq -r '.attempts' <<<"$retry_result")" -ge 2

# 6. No object is owned by a login role and the update principal stays within its class.
test "$(psql_su "$BASE" -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace JOIN pg_roles r ON r.oid = c.relowner WHERE r.rolcanlogin AND n.nspname NOT IN ('pg_catalog','information_schema','wc124_provisioning') AND n.nspname !~ '^pg_'")" = 0
test "$(psql_su "$BASE" -c "SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls OR rolinherit FROM pg_roles WHERE rolname = 'database_updater'")" = f

jq -n \
  --arg schema "waooaw.wc177-database-update-local/v1" --arg image "$WC124_POSTGRES_IMAGE" \
  --argjson full "$(cat "$WORK/full.json")" --argjson base "$(cat "$WORK/base.json")" \
  --argjson update "$result" --argjson second "$second" --argjson retry "$retry_result" \
  '{schema: $schema, postgres_image: $image, bootstrap: "non-superuser CREATEROLE principal",
    base_chain: $base, reference_chain: $full, update: $update, update_rerun: $second, lock_retry: $retry,
    plan: {reuse: "reuse", update: "update", undeclared: "full", unclassified: "full", changed_digest: "full", forced: "full"},
    schema_drift_lines_between_full_chain_and_base_plus_update: 0,
    refusals: ["undeclared", "unclassified", "changed-digest", "tampered-manifest"],
    lock: {bounded_failure: true, clean_retry: true, short_lock_retried: true},
    pgbouncer: "transaction pooling", status: "passed"}' \
  | tee "$EVIDENCE_DIR/wc177-database-update-local.json"

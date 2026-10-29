#!/usr/bin/env bash
# Local qualification of the Demo PostgreSQL init-chain provisioning (WC-124 gap B).
# Drives the real provisioner ledger logic (scripts/wc124_db_provisioner.py apply_init_chain)
# against a fresh pinned pgvector instance three times:
#   run 1 — every file applied and recorded in wc124_provisioning.init_chain_ledger
#   run 2 — every file skipped (digest unchanged)
#   run 3 — --force-init-chain re-applies every file without error (idempotent authoring standard)
# and proves the schema is byte-identical after run 1 and run 3 and satisfies the Business
# Platform IdentitySchemaHealthCheck object set.
# Only the psql transport is substituted (docker exec instead of TLS to Azure); ordering, digests,
# ledger SQL and the init files are exactly the production code path.
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/wc124_local_stack.sh
. "$ROOT/scripts/lib/wc124_local_stack.sh"

INIT_DIR="${WC124_INIT_DIRECTORY:-$ROOT/infrastructure/postgres/init}"
EVIDENCE_DIR="${WC124_EVIDENCE_DIR:-$ROOT/test-results/wc124/init-chain-local}"
RUN_ID="wc124ic$(date +%s)"
DATABASE=waooaw_application
mkdir -p "$EVIDENCE_DIR"

python "$ROOT/scripts/wc124_init_chain_lint.py" --init-directory "$INIT_DIR" --json > "$EVIDENCE_DIR/lint.json"
jq -e '.passed' "$EVIDENCE_DIR/lint.json" >/dev/null || { cat "$EVIDENCE_DIR/lint.json" >&2; echo "init chain lint failed" >&2; exit 1; }

WC124_RUN_ID="$RUN_ID"
WC124_NETWORK="$RUN_ID-net"
WC124_WORKDIR="$(mktemp -d)"
WC124_POSTGRES="$RUN_ID-postgres"
WC124_PGBOUNCER="$RUN_ID-pgbouncer"
trap wc124_stack_cleanup EXIT
docker network create "$WC124_NETWORK" >/dev/null

# Bare instance: no initdb.d mount, the provisioner owns the whole chain.
docker run -d --name "$WC124_POSTGRES" --network "$WC124_NETWORK" \
  -e POSTGRES_USER=waooaw -e POSTGRES_PASSWORD=waooaw-local-dev-only -e POSTGRES_DB="$DATABASE" \
  "$WC124_POSTGRES_IMAGE" >/dev/null
for _ in $(seq 1 60); do
  if docker exec "$WC124_POSTGRES" sh -c "test \"\$(head -n 1 /var/lib/postgresql/data/postmaster.pid 2>/dev/null)\" = 1 && pg_isready -q -U waooaw -d $DATABASE"; then
    break
  fi
  sleep 1
done
docker exec -i "$WC124_POSTGRES" psql -v ON_ERROR_STOP=1 -q -U waooaw -d "$DATABASE" < "$INIT_DIR/00-wc124-principal-bootstrap.sql" >/dev/null

run_chain() {
  local force="$1"
  WC124_LOCAL_CONTAINER="$WC124_POSTGRES" WC124_LOCAL_DATABASE="$DATABASE" WC124_INIT_DIRECTORY="$INIT_DIR" WC124_FORCE="$force" \
  PYTHONPATH="$ROOT/scripts" python - <<'EOF'
import json
import os
import subprocess
from pathlib import Path

import wc124_db_provisioner as provisioner

container = os.environ["WC124_LOCAL_CONTAINER"]
database = os.environ["WC124_LOCAL_DATABASE"]


def local_psql(_server, _bootstrap, _database, _token, sql, *, tuples_only=False):
    command = ["docker", "exec", "-i", container, "psql", "--no-psqlrc", "--set", "ON_ERROR_STOP=1", "-U", "waooaw", "-d", database]
    if tuples_only:
        command += ["--tuples-only", "--no-align", "--field-separator=\t"]
    completed = subprocess.run(command, input=sql, capture_output=True, text=True, check=False)  # noqa: S603
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return completed.stdout


provisioner.psql = local_psql
files = provisioner.application_migration_files(Path(os.environ["WC124_INIT_DIRECTORY"]))
outcome = provisioner.apply_init_chain("local", "waooaw", "none", files, force=os.environ["WC124_FORCE"] == "1")
print(json.dumps({key: len(value) for key, value in outcome.items()} | {"files": len(files)}))
EOF
}

dump_schema() {
  docker exec "$WC124_POSTGRES" pg_dump -U waooaw -d "$DATABASE" --schema-only --no-owner --no-privileges \
    | grep -v '^--' | grep -v '^\\restrict\|^\\unrestrict'
}

first=$(run_chain 0)
dump_schema > "$WC124_WORKDIR/schema-run1.sql"
second=$(run_chain 0)
third=$(run_chain 1)
dump_schema > "$WC124_WORKDIR/schema-run3.sql"

files=$(jq -r '.files' <<<"$first")
test "$(jq -r '.applied' <<<"$first")" = "$files"
test "$(jq -r '.skipped' <<<"$second")" = "$files"
test "$(jq -r '.applied + .reapplied' <<<"$second")" = 0
test "$(jq -r '.reapplied' <<<"$third")" = "$files"
schema_drift=$(diff "$WC124_WORKDIR/schema-run1.sql" "$WC124_WORKDIR/schema-run3.sql" | grep -c '^[<>]' || true)
test "$schema_drift" = 0

ledger_rows=$(docker exec "$WC124_POSTGRES" psql -At -U waooaw -d "$DATABASE" -c "SELECT count(*) FROM wc124_provisioning.init_chain_ledger")
test "$ledger_rows" = "$files"
# Business Platform IdentitySchemaHealthCheck object set (src/business-platform/Infrastructure/IdentitySchemaHealthCheck.cs).
identity_tables=$(docker exec "$WC124_POSTGRES" psql -At -U waooaw -d "$DATABASE" -c "SELECT count(*) FROM pg_tables WHERE schemaname = 'identity' AND tablename IN ('registrations','idempotency_ledger','accounts','login_methods','actor_bindings','memberships','lifecycle_operations','provider_link_projections')")
forced_rls=$(docker exec "$WC124_POSTGRES" psql -At -U waooaw -d "$DATABASE" -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'identity' AND c.relname IN ('memberships','lifecycle_operations','provider_link_projections') AND c.relrowsecurity AND c.relforcerowsecurity")
test "$identity_tables" = 8
test "$forced_rls" = 3
# Post-handoff SECURITY DEFINER principals and runtime OIDC reservation (Demo Google sign-in 42501 regression).
docker exec -i "$WC124_POSTGRES" psql --no-psqlrc -q -At -U waooaw -d "$DATABASE" \
  < "$ROOT/tests/postgres/oidc_reservation_probe.sql" | grep -qx 'oidc-reservation-probe: passed'

jq -n \
  --arg schema "waooaw.wc124-init-chain-local/v1" --arg image "$WC124_POSTGRES_IMAGE" \
  --argjson files "$files" --argjson run1 "$first" --argjson run2 "$second" --argjson run3 "$third" \
  --argjson identity_tables "$identity_tables" --argjson forced_rls "$forced_rls" \
  '{schema: $schema, postgres_image: $image, transport: "docker-exec psql (ledger logic and files are the production path)",
    sql_files: $files, run1: $run1, run2: $run2, run3_forced: $run3,
    schema_drift_lines_between_run1_and_run3: 0, ledger: "wc124_provisioning.init_chain_ledger",
    identity_health_check: {required_tables_present: $identity_tables, forced_rls_tables: $forced_rls},
    oidc_reservation_probe: "passed",
    status: "passed"}' \
  | tee "$EVIDENCE_DIR/result.json"

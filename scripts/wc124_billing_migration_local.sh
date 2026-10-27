#!/usr/bin/env bash
# Fast local qualification of the Demo "Billing migration through PgBouncer" step.
# Reproduces the Demo instance state (bootstrap chain + residual state from a captured
# snapshot) and runs the exact Billing image as the restricted billing_migrator identity
# through a PgBouncer that authenticates per role (no admin backend identity).
# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/wc124_local_stack.sh
. "$ROOT/scripts/lib/wc124_local_stack.sh"

SNAPSHOT="${WC124_DEMO_SNAPSHOT:-$ROOT/test-results/wc124/demo-billing-state.json}"
IMAGE="${WC124_BILLING_IMAGE:-}"
EVIDENCE_DIR="${WC124_EVIDENCE_DIR:-$ROOT/test-results/wc124/billing-migration-local}"
RUN_ID="wc124bl$(date +%s)"
mkdir -p "$EVIDENCE_DIR"

if [ -z "$IMAGE" ]; then
  IMAGE="waooaw/billing-engine:$RUN_ID"
  docker build --quiet --file "$ROOT/src/billing-engine/Dockerfile" --tag "$IMAGE" "$ROOT" >/dev/null
fi
image_digest=$(docker image inspect "$IMAGE" --format '{{.Id}}')

wc124_stack_init "$RUN_ID"
wc124_start_postgres "$ROOT"
fixture_source=$(wc124_replay_billing_snapshot "$SNAPSHOT")
wc124_start_pgbouncer billing_migrator

run_migration() {
  docker run --rm --network "$WC124_NETWORK" \
    -e DATABASE_URL="$(wc124_role_url billing_migrator)" \
    -e MIGRATION_PATTERN=59-wc124-billing-authority.sql \
    -e MIGRATION_SCHEMA=billing \
    "$IMAGE" python migrate.py
}

run_migration > "$EVIDENCE_DIR/first-run.log" 2>&1 || { cat "$EVIDENCE_DIR/first-run.log" >&2; echo "first migration run failed" >&2; exit 1; }
run_migration > "$EVIDENCE_DIR/second-run.log" 2>&1 || { cat "$EVIDENCE_DIR/second-run.log" >&2; echo "idempotent rerun failed" >&2; exit 1; }
# Demo run 39543680599: the ledger held the digest of an earlier revision of the same file. The
# migrator must re-apply the (idempotent) current file and converge the ledger, not refuse forever.
psql_admin -c "UPDATE billing.waooaw_schema_migrations SET migration_sha256 = repeat('0', 64) WHERE migration_name = '59-wc124-billing-authority.sql'" >/dev/null
run_migration > "$EVIDENCE_DIR/stale-digest-run.log" 2>&1 || { cat "$EVIDENCE_DIR/stale-digest-run.log" >&2; echo "stale-digest re-apply failed" >&2; exit 1; }
grep -q "migration digest changed, re-applying: 59-wc124-billing-authority.sql" "$EVIDENCE_DIR/stale-digest-run.log"

ledger_owner=$(psql_admin -c "SELECT pg_get_userbyid(relowner) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'billing' AND c.relname = 'waooaw_schema_migrations'")
ledger_entry=$(psql_admin -c "SELECT migration_sha256 FROM billing.waooaw_schema_migrations WHERE migration_name = '59-wc124-billing-authority.sql'")
expected_digest=$(sha256sum "$ROOT/infrastructure/postgres/init/59-wc124-billing-authority.sql" | cut -d' ' -f1)
foreign_owned=$(psql_admin -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'billing' AND c.relkind IN ('r','S') AND pg_get_userbyid(c.relowner) <> 'billing_owner'")
backend_identity=$(wc124_backend_identity billing_migrator)
# Demo run 40530276041: billing_migrator holds billing_owner without ADMIN OPTION; the file must
# neither grant nor revoke that standing membership.
migrator_membership=$(psql_admin -c "SELECT count(*) FROM pg_auth_members m WHERE m.member = 'billing_migrator'::regrole AND m.roleid = 'billing_owner'::regrole AND NOT m.admin_option")

test "$migrator_membership" = 1
# Provisioner path: a PostgreSQL 16 CREATEROLE admin holds the implicit ADMIN grant without SET.
# The file must grant itself settable membership for the transaction and revoke exactly that grant.
psql_admin >/dev/null <<'EOF'
CREATE ROLE wc124_local_provisioner LOGIN NOSUPERUSER CREATEROLE;
GRANT billing_owner TO wc124_local_provisioner WITH ADMIN OPTION, INHERIT FALSE, SET FALSE;
EOF
docker exec -i "$WC124_POSTGRES" psql -v ON_ERROR_STOP=1 -U wc124_local_provisioner -d waooaw -q \
  < "$ROOT/infrastructure/postgres/init/59-wc124-billing-authority.sql" > "$EVIDENCE_DIR/provisioner-run.log" 2>&1 \
  || { cat "$EVIDENCE_DIR/provisioner-run.log" >&2; echo "provisioner-path apply failed" >&2; exit 1; }
provisioner_grants=$(psql_admin -c "SELECT string_agg(format('%s/%s/%s', admin_option, inherit_option, set_option), ',') FROM pg_auth_members WHERE member = 'wc124_local_provisioner'::regrole AND roleid = 'billing_owner'::regrole")
test "$provisioner_grants" = "t/f/f"
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
    recorded_migration_sha256: $digest, idempotent_rerun: true, stale_digest_reapplied: true,
    migrator_membership_retained: true, provisioner_temporary_membership_revoked: true, status: "passed"}' \
  | tee "$EVIDENCE_DIR/result.json"

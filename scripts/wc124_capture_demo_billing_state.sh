#!/usr/bin/env bash
# Capture the real Demo Billing database state (read-only catalog queries) by running
# a one-off execution of the deployed Billing migration job with an overridden command.
# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9
# Constitutional basis: C-005 (Evidence First), C-059, C-080
set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-waooaw-demo-rg}"
JOB_NAME="${JOB_NAME:-job-demo-wc124-billing-migration}"
OUTPUT="${1:-wc124-demo-billing-state.json}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

cat > "$WORKDIR/snapshot.py" <<'EOF'
import asyncio, json, os, asyncpg
QUERIES = {
    "identity": "SELECT session_user, current_user, current_database()",
    "login_role": "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname = session_user",
    "memberships": "SELECT r.rolname AS member, g.rolname AS granted_role FROM pg_auth_members m JOIN pg_roles r ON r.oid = m.member JOIN pg_roles g ON g.oid = m.roleid WHERE r.rolname LIKE 'billing%' ORDER BY 1, 2",
    "schema": "SELECT nspname, pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname = 'billing'",
    "relations": "SELECT c.relname, pg_get_userbyid(c.relowner) AS owner, c.relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'billing' AND c.relkind = 'r' ORDER BY 1",
    "ledger_rows": "SELECT migration_name, migration_sha256 FROM billing.waooaw_schema_migrations ORDER BY 1",
}
async def main():
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    result = {}
    for name, query in QUERIES.items():
        try:
            result[name] = [dict(row) for row in await connection.fetch(query)]
        except Exception as error:
            result[name] = {"error": str(error)}
    print("WC124_SNAPSHOT_BEGIN")
    print(json.dumps(result, default=str))
    print("WC124_SNAPSHOT_END")
asyncio.run(main())
EOF

encoded=$(base64 -w0 "$WORKDIR/snapshot.py")
az containerapp job show --resource-group "$RESOURCE_GROUP" --name "$JOB_NAME" \
  --query 'properties.template.containers[0]' --output json > "$WORKDIR/container.json"
jq --arg code "$encoded" \
  '{containers: [(. + {command: ["python"], args: ["-c", ("import base64;exec(base64.b64decode(\"" + $code + "\"))")]})]}' \
  "$WORKDIR/container.json" > "$WORKDIR/start.json"
python3 -c 'import json,sys,yaml; yaml.safe_dump(json.load(open(sys.argv[1])), open(sys.argv[2], "w"))' \
  "$WORKDIR/start.json" "$WORKDIR/start.yaml"

execution=$(az containerapp job start --resource-group "$RESOURCE_GROUP" --name "$JOB_NAME" \
  --yaml "$WORKDIR/start.yaml" --query name --output tsv)
test -n "$execution"
echo "snapshot execution: $execution" >&2
status=
for _ in $(seq 1 60); do
  status=$(az containerapp job execution show --resource-group "$RESOURCE_GROUP" --name "$JOB_NAME" \
    --job-execution-name "$execution" --query properties.status --output tsv)
  case "$status" in Succeeded|Failed|Stopped) break ;; esac
  sleep 10
done
test "$status" = Succeeded || { echo "snapshot execution ended with status: $status" >&2; exit 1; }

container=$(jq -r '.name' "$WORKDIR/container.json")
az containerapp job logs show --resource-group "$RESOURCE_GROUP" --name "$JOB_NAME" \
  --execution "$execution" --container "$container" --tail 300 --format text 2>/dev/null \
  | sed -n '/WC124_SNAPSHOT_BEGIN/,/WC124_SNAPSHOT_END/p' | sed -E 's/^[0-9T:.Z-]+ stdout F //' | sed '1d;$d' \
  | jq --arg execution "$execution" '. + {schema: "waooaw.wc124-demo-billing-state/v1", execution: $execution}' > "$OUTPUT"
jq -c '{execution, schema_owner: .schema[0].owner, ledger_owner: (.relations[] | select(.relname == "waooaw_schema_migrations") | .owner), ledger_rows: (.ledger_rows | length)}' "$OUTPUT"

#!/usr/bin/env bash
# Implements: work-contracts/WC-168-operator-console-works-on-demo.md WC168-R003 and WC168-R004
# Constitutional basis: C-023 (evidence), C-049 (honest limits), C-063 (no secret in argv, logs or chat), C-065 (Founder authority), C-080 (Docker-only)
#
# Founder-authorized (2026-11-24) temporary read-only job. It runs ONE catalog query
# (infrastructure/postgres/operations/wc168-catalog-read.sql) against the Demo database with the Business Platform's own
# database credential, by reference, inside a read-only transaction: table owners, access lists and role memberships only.
# No business row and no secret is read, printed or stored. The job is deleted when the script ends, even on failure.
#
#   scripts/wc168_demo_db_catalog_read.sh run         create the job, run it, print its result, delete it
#   scripts/wc168_demo_db_catalog_read.sh dry-run     print what would be created; touches nothing in Azure
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AZ_IMAGE="${WC168_AZ_IMAGE:-mcr.microsoft.com/azure-cli:latest}"
AZ_CONFIG="${WC168_AZ_CONFIG:-$HOME/.waooaw-az}"
RESOURCE_GROUP="${WC168_RESOURCE_GROUP:-waooaw-demo-rg}"
ENVIRONMENT_NAME="${WC168_CONTAINER_ENVIRONMENT:-cae-waooaw-demo}"
APP_NAME="${WC168_SOURCE_APP:-ca-demo-business-platform}"
SECRET_NAME="${WC168_SOURCE_SECRET:-database-credential}"
WORKSPACE_ID="${WC168_WORKSPACE_ID:-8604586b-f914-46ab-8403-398b43186c0a}"
JOB_NAME="${WC168_JOB_NAME:-wc168-db-catalog-read}"
# The PostgreSQL image already pinned and pulled by the Demo Temporal pool sampler.
IMAGE="${WC168_IMAGE:-docker.io/library/postgres@sha256:0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab}"
SQL_FILE="$ROOT/infrastructure/postgres/operations/wc168-catalog-read.sql"

az_run() {
  docker run --rm -i -v "$AZ_CONFIG:/cfg" -e AZURE_CONFIG_DIR=/cfg "$AZ_IMAGE" az "$@"
}

# Runs inside the job. The connection string stays in one environment variable and is never echoed.
job_script() {
  cat <<'EOF'
set -eu
field() { printf '%s' "$DB_CONNECTION" | tr ';' '\n' | sed -n "s/^$1=//Ip" | head -n 1; }
PGHOST="$(field Host)"; PGPORT="$(field Port)"; PGDATABASE="$(field Database)"
PGUSER="$(field Username)"; PGPASSWORD="$(field Password)"
export PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD
export PGSSLMODE=prefer PGCONNECT_TIMEOUT=10
printf '%s' "$SQL_B64" | base64 -d > /tmp/catalog-read.sql
echo "WC168_CATALOG_READ_BEGIN"
psql -X -v ON_ERROR_STOP=1 -f /tmp/catalog-read.sql
echo "WC168_CATALOG_READ_END"
EOF
}

cleanup() {
  az_run containerapp job delete --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" --yes --output none < /dev/null 2>/dev/null || true
}

cmd_dry_run() {
  echo "job:       $JOB_NAME in $ENVIRONMENT_NAME ($RESOURCE_GROUP)"
  echo "image:     $IMAGE"
  echo "secret:    '$SECRET_NAME' of $APP_NAME, referenced with that app's identity (value never read here)"
  echo "sql:       ${SQL_FILE#"$ROOT"/} ($(wc -l < "$SQL_FILE") lines, read-only transaction)"
  echo "cleanup:   the job is deleted on exit"
}

cmd_run() {
  [ -f "$SQL_FILE" ] || { echo "Missing $SQL_FILE" >&2; exit 2; }
  az_run account show --query id -o tsv > /dev/null || { echo "Not signed in to Azure; run the login step first." >&2; exit 2; }

  secret_url="$(az_run containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.secrets[?name=='$SECRET_NAME'].keyVaultUrl | [0]" -o tsv)"
  identity_id="$(az_run containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.secrets[?name=='$SECRET_NAME'].identity | [0]" -o tsv)"
  [ -n "$secret_url" ] && [ -n "$identity_id" ] || { echo "The secret reference of $APP_NAME was not found." >&2; exit 1; }

  trap cleanup EXIT
  cleanup
  sql_b64="$(base64 -w0 < "$SQL_FILE")"
  script_b64="$(job_script | base64 -w0)"

  environment_id="$(az_run containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query properties.environmentId -o tsv)"
  location="$(az_run containerapp show --name "$APP_NAME" --resource-group "$RESOURCE_GROUP" --query location -o tsv)"
  spec_dir="$(mktemp -d)"
  chmod 700 "$spec_dir"
  trap 'rm -rf "$spec_dir"; cleanup' EXIT
  cat > "$spec_dir/job.yaml" <<YAML
location: $location
identity:
  type: UserAssigned
  userAssignedIdentities:
    "$identity_id": {}
properties:
  environmentId: $environment_id
  configuration:
    triggerType: Manual
    replicaTimeout: 300
    replicaRetryLimit: 0
    manualTriggerConfig:
      parallelism: 1
      replicaCompletionCount: 1
    secrets:
      - name: db
        keyVaultUrl: $secret_url
        identity: $identity_id
  template:
    containers:
      - name: catalog-read
        image: $IMAGE
        command: ["/bin/sh"]
        args: ['-c', 'printf "%s" "\$JOB_SCRIPT_B64" | base64 -d | sh']
        resources:
          cpu: 0.25
          memory: 0.5Gi
        env:
          - name: DB_CONNECTION
            secretRef: db
          - name: SQL_B64
            value: "$sql_b64"
          - name: JOB_SCRIPT_B64
            value: "$script_b64"
YAML
  docker run --rm -i -v "$AZ_CONFIG:/cfg" -v "$spec_dir:/spec:ro" -e AZURE_CONFIG_DIR=/cfg "$AZ_IMAGE" \
    az containerapp job create --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" --yaml /spec/job.yaml --output none

  execution="$(az_run containerapp job start --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" --query name -o tsv)"
  echo "execution: $execution"
  status=""
  for _ in $(seq 1 60); do
    status="$(az_run containerapp job execution show --name "$JOB_NAME" --resource-group "$RESOURCE_GROUP" \
      --job-execution-name "$execution" --query properties.status -o tsv)"
    case "$status" in Succeeded|Failed|Stopped) break ;; esac
    sleep 5
  done
  echo "status:    $status"

  # Console logs reach Log Analytics after a delay; each poll carries a unique comment because the service caches identical queries.
  for attempt in $(seq 1 40); do
    query="ContainerAppConsoleLogs_CL | where ContainerJobName_s == '$JOB_NAME' and ContainerGroupName_s startswith '$execution' | order by TimeGenerated asc | project Log_s // poll $attempt-$(date +%s%N)"
    out="$(az_run monitor log-analytics query --workspace "$WORKSPACE_ID" --analytics-query "$query" -o tsv 2>/dev/null || true)"
    if printf '%s\n' "$out" | grep -q "WC168_CATALOG_READ_END\|ERROR"; then
      printf '%s\n' "$out" | sed 's/\tPrimaryResult.*$//' | grep -E '^(WC168_|ROLE\||MEMBER\||NOSELECT\||PROVIDER\||OWNERS\||DEFACL\||RLS\||POLICY\||ERROR|psql:)' | sort
      break
    fi
    if [ "$attempt" = 40 ]; then
      echo "No complete result reached Log Analytics (status $status)." >&2
      printf '%s\n' "$out" | sed 's/\tPrimaryResult.*$//' >&2
      exit 1
    fi
    sleep 10
  done
  [ "$status" = "Succeeded" ] || exit 1
}

case "${1:-}" in
  run) cmd_run ;;
  dry-run) cmd_dry_run ;;
  *) echo "Usage: $0 run | dry-run" >&2; exit 2 ;;
esac

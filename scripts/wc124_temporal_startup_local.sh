#!/usr/bin/env bash
# Local qualification of job-demo-temporal-startup exactly as Terraform declares it.
# Both container scripts are read from the workload module and run in their pinned images as
# one replica sharing a network namespace, exactly like containers of one ACA replica: the
# containers exchange samples and exit signals only over loopback. A command missing from an
# image fails here, not in Azure (run 40542694439 exited 127: the Temporal image has no psql).
# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/wc124_local_stack.sh
. "$ROOT/scripts/lib/wc124_local_stack.sh"

WORKLOAD="$ROOT/infrastructure/terraform/phase2/modules/workload/main.tf"
EVIDENCE_DIR="${WC124_EVIDENCE_DIR:-$ROOT/test-results/wc124/temporal-startup-local}"
RUN_ID="wc124tsq$(date +%s)"
mkdir -p "$EVIDENCE_DIR"

wc124_stack_init "$RUN_ID"
CONTROLLER="$RUN_ID-temporal-startup-qualification"
SAMPLER="$RUN_ID-pool-sampler"
wc124_track "$CONTROLLER" "$SAMPLER"

# Emits the rendered script, image and command of one container of the startup job.
extract() {
  python3 - "$WORKLOAD" "$1" "$2" <<'PY'
import re, sys, textwrap
source, container, field = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(source, encoding="utf-8").read()
start = text.index('resource "azurerm_container_app_job" "temporal_startup_qualification"')
block = text[start:text.index("\nresource ", start + 1)]
match = re.search(
    r'container \{\n\s+name\s+= "' + re.escape(container) + r'"\n\s+image\s+= "([^"]+)"\n'
    r'(?:.*\n)*?\s+command = \[([^\]]*)\]\n\s+args = \[<<-EOT\n((?s:.*?))\n\s*EOT\n',
    block,
)
if match is None:
    raise SystemExit(f"container {container} not found in temporal_startup_qualification")
image, command, body = match.groups()
if field == "image":
    print(image)
elif field == "shell":
    print(re.findall(r'"([^"]+)"', command)[0])
else:
    script = textwrap.dedent(body).replace("$${", "${").replace("%%{", "%{")
    if re.search(r"\$\{(var|local)\.", script):
        raise SystemExit(f"container {container} script has unrendered Terraform interpolation")
    sys.stdout.write(script + "\n")
PY
}

CONTROLLER_IMAGE=$(extract temporal-startup-qualification image)
SAMPLER_IMAGE=$(extract pool-sampler image)
extract temporal-startup-qualification script > "$EVIDENCE_DIR/temporal-startup-qualification.sh"
extract pool-sampler script > "$EVIDENCE_DIR/pool-sampler.sh"
# The disposable PostgreSQL fixture has no TLS; Azure monitoring requires TLS.
sed -i 's/PGSSLMODE=require/PGSSLMODE=disable/' "$EVIDENCE_DIR/pool-sampler.sh"
CONTROLLER_SHELL=$(extract temporal-startup-qualification shell)
SAMPLER_SHELL=$(extract pool-sampler shell)

wc124_start_postgres "$ROOT"
wc124_provision_temporal_databases
wc124_start_pgbouncer temporal_runtime temporal_migrator

# Demo order: vendor (Temporal) schema migration by temporal_migrator directly on the instance.
docker run --rm --network "$WC124_NETWORK" -e SQL_PASSWORD="$WC124_ROLE_PASSWORD" -e POSTGRES_SEEDS="$WC124_POSTGRES" \
  --entrypoint /bin/bash "$CONTROLLER_IMAGE" -c '
    set -euo pipefail
    migrate() {
      temporal-sql-tool --plugin postgres12 --endpoint "$POSTGRES_SEEDS" --port 5432 --user temporal_migrator --database "$1" setup-schema --version 0.0
      temporal-sql-tool --plugin postgres12 --endpoint "$POSTGRES_SEEDS" --port 5432 --user temporal_migrator --database "$1" update-schema --schema-dir "$2"
    }
    migrate waooaw_temporal /etc/temporal/schema/postgresql/v12/temporal/versioned
    migrate waooaw_temporal_visibility /etc/temporal/schema/postgresql/v12/visibility/versioned
  ' > "$EVIDENCE_DIR/temporal-migration.log" 2>&1 || { cat "$EVIDENCE_DIR/temporal-migration.log" >&2; exit 1; }

# Reproduce a repeat deployment, not just an empty-environment cold start.
start_server() {
  wc124_track "$1"
  docker run -d --name "$1" --network "$WC124_NETWORK" \
    -e BIND_ON_IP=0.0.0.0 -e DB=postgres12 -e DB_PORT=5432 \
    -e DBNAME=waooaw_temporal -e VISIBILITY_DBNAME=waooaw_temporal_visibility \
    -e POSTGRES_USER=temporal_runtime -e POSTGRES_PWD="$WC124_ROLE_PASSWORD" -e POSTGRES_SEEDS="$WC124_PGBOUNCER" \
    -e SKIP_SCHEMA_SETUP=true -e SKIP_DB_CREATE=true -e SQL_MAX_CONNS=1 -e SQL_MAX_IDLE_CONNS=1 \
    -e SQL_VIS_MAX_CONNS=1 -e SQL_VIS_MAX_IDLE_CONNS=1 \
    --entrypoint /bin/bash "$CONTROLLER_IMAGE" -c \
    'export TEMPORAL_BROADCAST_ADDRESS="$(hostname -i | awk "{print \$1}")" TEMPORAL_ADDRESS=127.0.0.1:7233; exec /etc/temporal/entrypoint.sh autosetup' >/dev/null
}
incumbent="$RUN_ID-incumbent"
overlap="$RUN_ID-overlap"
start_server "$incumbent"
healthy=false
for attempt in $(seq 1 40); do
  if docker exec "$incumbent" temporal operator cluster health --address 127.0.0.1:7233 \
    > "$EVIDENCE_DIR/incumbent-health.log" 2>&1; then healthy=true; break; fi
  sleep 2
done
if [ "$healthy" != true ]; then docker logs "$incumbent" >&2; exit 1; fi
start_server "$overlap"
for attempt in $(seq 1 20); do
  docker exec -e PGPASSWORD="$WC124_ROLE_PASSWORD" "$WC124_POSTGRES" \
    psql --no-psqlrc --set ON_ERROR_STOP=1 -h "$WC124_PGBOUNCER" -U temporal_runtime -d pgbouncer \
    --csv -c 'SHOW POOLS;' >> "$EVIDENCE_DIR/overlap-pools.csv"
  if [ "$(docker inspect -f '{{.State.Running}}' "$overlap")" != true ]; then break; fi
  sleep 1
done
docker logs "$overlap" > "$EVIDENCE_DIR/overlap.log" 2>&1
test "$(docker inspect -f '{{.State.ExitCode}}' "$overlap")" = 1
grep -q 'unable to initialize system namespace: unable to initialize metadata manager: driver: bad connection' \
  "$EVIDENCE_DIR/overlap.log"
awk -F, '$1 == "waooaw_temporal" && $7 == 8 && $4 > 0 {seen=1} END {exit !seen}' \
  "$EVIDENCE_DIR/overlap-pools.csv"
docker logs "$WC124_PGBOUNCER" > "$EVIDENCE_DIR/overlap-pgbouncer.log" 2>&1
grep -q 'query_wait_timeout' "$EVIDENCE_DIR/overlap-pgbouncer.log"
start_qualification() {
  local controller="$1" sampler="$2"
  wc124_track "$controller" "$sampler"
  docker run -d --name "$controller" --network "$WC124_NETWORK" \
    -e BIND_ON_IP=0.0.0.0 -e DB=postgres12 -e DB_PORT=5432 \
    -e DBNAME=waooaw_temporal -e VISIBILITY_DBNAME=waooaw_temporal_visibility \
    -e POSTGRES_USER=temporal_runtime -e POSTGRES_PWD="$WC124_ROLE_PASSWORD" -e POSTGRES_SEEDS="$WC124_PGBOUNCER" \
    -e SKIP_SCHEMA_SETUP=true -e SKIP_DB_CREATE=true -e SQL_MAX_CONNS=1 -e SQL_MAX_IDLE_CONNS=1 \
    -e SQL_VIS_MAX_CONNS=1 -e SQL_VIS_MAX_IDLE_CONNS=1 \
    --entrypoint "$CONTROLLER_SHELL" "$CONTROLLER_IMAGE" -c "$(cat "$EVIDENCE_DIR/temporal-startup-qualification.sh")" >/dev/null
  docker run -d --name "$sampler" --network "container:$controller" \
    -e POSTGRES_PWD="$WC124_ROLE_PASSWORD" -e POSTGRES_SEEDS="$WC124_PGBOUNCER" \
    -e MONITOR_POSTGRES_HOST="$WC124_POSTGRES" \
    --entrypoint "$SAMPLER_SHELL" "$SAMPLER_IMAGE" -c "$(cat "$EVIDENCE_DIR/pool-sampler.sh")" >/dev/null
}

guard="$RUN_ID-guard"
guard_sampler="$RUN_ID-guard-sampler"
start_qualification "$guard" "$guard_sampler"
test "$(timeout 120 docker wait "$guard")" = 1
test "$(timeout 15 docker wait "$guard_sampler")" = 1
docker logs "$guard" > "$EVIDENCE_DIR/guard-controller.log" 2>&1
docker logs "$guard_sampler" > "$EVIDENCE_DIR/guard-sampler.log" 2>&1
grep -q 'refusing overlapping startup' "$EVIDENCE_DIR/guard-sampler.log"
! grep -q 'Build info' "$EVIDENCE_DIR/guard-controller.log"
docker stop --time 15 "$incumbent" >/dev/null
echo "WC-124 overlap reproduced and admission guard denied startup; incumbent now stopped."

start_qualification "$CONTROLLER" "$SAMPLER"

# Container Apps replica_timeout_in_seconds is 300 for this job.
controller_status=$(timeout 330 docker wait "$CONTROLLER" || echo timeout)
sampler_status=$(timeout 30 docker wait "$SAMPLER" || echo timeout)
docker logs "$CONTROLLER" > "$EVIDENCE_DIR/temporal-startup-qualification.log" 2>&1
docker logs "$SAMPLER" > "$EVIDENCE_DIR/pool-sampler.log" 2>&1
mkdir -p "$EVIDENCE_DIR/pool-samples"
docker cp "$SAMPLER:/tmp/pool-samples/." "$EVIDENCE_DIR/pool-samples"

if [ "$controller_status" != 0 ] || [ "$sampler_status" != 0 ]; then
  tail -40 "$EVIDENCE_DIR/temporal-startup-qualification.log" >&2
  tail -20 "$EVIDENCE_DIR/pool-sampler.log" >&2
  echo "Temporal startup qualification failed: controller=$controller_status sampler=$sampler_status" >&2
  exit 1
fi
result=$(grep -F '"schema":"waooaw.wc124-temporal-startup/v1"' "$EVIDENCE_DIR/temporal-startup-qualification.log" | tail -1)
test "$(grep -c '^WC124_POOL_SAMPLE ' "$EVIDENCE_DIR/temporal-startup-qualification.log")" = 60
printf '%s\n' "$result" | tee "$EVIDENCE_DIR/result.json"
echo "WC-124 Temporal startup qualification passed locally with the Terraform-declared scripts and images."

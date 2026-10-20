#!/usr/bin/env bash
# Fast local qualification of the Demo "Apply application activation" step.
# Boots the activated application images (constitutional-engine, business-platform,
# professional-runtime, web) with the Demo environment shape against ONE provisioned
# PostgreSQL instance reached through a per-role SCRAM PgBouncer in transaction mode.
# There is no database sidecar: each runtime connects only as its restricted runtime role
# and must pass the same startup/readiness probes Azure Container Apps evaluates.
# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §9
# Constitutional basis: C-005 (Evidence First), C-026, C-059, C-080
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=scripts/lib/wc124_local_stack.sh
. "$ROOT/scripts/lib/wc124_local_stack.sh"

SNAPSHOT="${WC124_DEMO_SNAPSHOT:-$ROOT/test-results/wc124/demo-billing-state.json}"
EVIDENCE_DIR="${WC124_EVIDENCE_DIR:-$ROOT/test-results/wc124/application-activation-local}"
RUN_ID="wc124act$(date +%s)"
REDIS_IMAGE="redis:7-alpine"
TEMPORAL_IMAGE="temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88"
STUB_IMAGE="nginx:alpine"
KEYCLOAK_IMAGE="quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
SECRET="wc124-local-activation-secret-32-bytes-min"
HMAC_KEY=$(printf 'wc124-activation-%s' "$RUN_ID" | sha256sum | cut -d' ' -f1)
SESSION_KEY_B64=$(printf '%s' "$HMAC_KEY" | head -c 32 | base64 -w0)
mkdir -p "$EVIDENCE_DIR"

declare -A IMAGES=(
  [constitutional-engine]="${WC124_IMAGE_CONSTITUTIONAL_ENGINE:-}"
  [business-platform]="${WC124_IMAGE_BUSINESS_PLATFORM:-}"
  [professional-runtime]="${WC124_IMAGE_PROFESSIONAL_RUNTIME:-}"
  [web]="${WC124_IMAGE_WEB:-}"
  [billing-engine]="${WC124_BILLING_IMAGE:-}"
)
declare -A DOCKERFILES=(
  [constitutional-engine]=src/constitutional-engine/Dockerfile
  [business-platform]=src/business-platform/Dockerfile
  [professional-runtime]=src/professional-runtime/Dockerfile
  [web]=web/Dockerfile
  [billing-engine]=src/billing-engine/Dockerfile
)
for component in "${!IMAGES[@]}"; do
  if [ -z "${IMAGES[$component]}" ]; then
    IMAGES[$component]="waooaw/$component:$RUN_ID"
    docker build --quiet --file "$ROOT/${DOCKERFILES[$component]}" --tag "${IMAGES[$component]}" "$ROOT" >/dev/null
  fi
done

wc124_stack_init "$RUN_ID"
wc124_start_postgres "$ROOT"
fixture_source=$(wc124_replay_billing_snapshot "$SNAPSHOT")
wc124_provision_temporal_databases
wc124_provision_keycloak_database
wc124_start_pgbouncer billing_migrator ce_runtime bp_runtime web_session_app temporal_runtime temporal_migrator

# Keycloak vendor migration exactly as job-demo-keycloak-migration runs it: the exact image,
# keycloak_migrator, directly on the instance (not through PgBouncer), with the bounded Agroal pool.
run_keycloak_migration() {
  local evidence="$1"
  docker run --rm --network "$WC124_NETWORK" \
    -e KC_DB=postgres -e KC_DB_URL_HOST="$WC124_POSTGRES" -e KC_DB_URL_PORT=5432 -e KC_DB_URL_DATABASE=waooaw_keycloak \
    -e KC_DB_URL_PROPERTIES="?prepareThreshold=0" -e KC_DB_USERNAME=keycloak_migrator -e KC_DB_PASSWORD="$WC124_ROLE_PASSWORD" \
    -e KC_DB_POOL_INITIAL_SIZE=1 -e KC_DB_POOL_MIN_SIZE=1 -e KC_DB_POOL_MAX_SIZE=5 \
    -e KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY=update -e KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY=true \
    --entrypoint /bin/bash "$KEYCLOAK_IMAGE" -c '
      printf "{\"realm\":\"waooaw\",\"enabled\":true}" > /tmp/waooaw-realm.json
      exec /opt/keycloak/bin/kc.sh import --file /tmp/waooaw-realm.json --override true
    ' > "$evidence" 2>&1
}

# Reproduce the Demo failure mode first: a stale Temporal revision with the image-default pools
# (20 per store per service) must be able to exhaust the usable slots and make Keycloak fail with
# "remaining connection slots are reserved"; retiring it must make the same migration succeed.
if [ "${WC124_REPRODUCE_STALE_POOLS:-1}" = 1 ]; then
  # Hold the usable slots the way the stale revision did: idle sessions as temporal_runtime.
  wc124_track "$RUN_ID-stale-temporal"
  docker run -d --name "$RUN_ID-stale-temporal" --network "$WC124_NETWORK" -e PGPASSWORD="$WC124_ROLE_PASSWORD" \
    --entrypoint bash "$WC124_POSTGRES_IMAGE" -c "
      for i in \$(seq 1 $WC124_PG_USABLE_CONNECTIONS); do
        psql -h $WC124_POSTGRES -U temporal_runtime -d waooaw_temporal -c 'SELECT pg_sleep(600)' >/dev/null 2>&1 &
      done
      wait" >/dev/null
  for attempt in $(seq 1 30); do
    held=$(psql_admin -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'temporal_runtime'")
    [ "$held" -ge $((WC124_PG_USABLE_CONNECTIONS - 1)) ] && break
    sleep 1
  done
  if run_keycloak_migration "$EVIDENCE_DIR/keycloak-migration-under-stale-pools.log"; then
    echo "Keycloak migration unexpectedly succeeded with $held temporal_runtime backends holding the usable slots" >&2; exit 1
  fi
  grep -q "remaining connection slots are reserved" "$EVIDENCE_DIR/keycloak-migration-under-stale-pools.log" \
    || { tail -20 "$EVIDENCE_DIR/keycloak-migration-under-stale-pools.log" >&2; echo "Keycloak failed for a reason other than slot exhaustion" >&2; exit 1; }
  docker rm -f "$RUN_ID-stale-temporal" >/dev/null
  psql_admin -c "SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity WHERE usename = 'temporal_runtime'" >/dev/null
  stale_reproduced=true
else
  stale_reproduced=false
fi

run_keycloak_migration "$EVIDENCE_DIR/keycloak-migration.log" \
  || { tail -30 "$EVIDENCE_DIR/keycloak-migration.log" >&2; echo "Keycloak migration failed with the connection budget restored" >&2; exit 1; }
grep -q "Realm 'waooaw' imported\|Import finished successfully" "$EVIDENCE_DIR/keycloak-migration.log" \
  || { tail -20 "$EVIDENCE_DIR/keycloak-migration.log" >&2; echo "Keycloak import did not report success" >&2; exit 1; }

# Demo order: vendor (Temporal) schema migration by temporal_migrator directly on the instance.
docker run --rm --network "$WC124_NETWORK" -e SQL_PASSWORD="$WC124_ROLE_PASSWORD" -e POSTGRES_SEEDS="$WC124_POSTGRES" \
  --entrypoint /bin/bash "$TEMPORAL_IMAGE" -c '
    set -euo pipefail
    migrate() {
      temporal-sql-tool --plugin postgres12 --endpoint "$POSTGRES_SEEDS" --port 5432 --user temporal_migrator --database "$1" setup-schema --version 0.0
      temporal-sql-tool --plugin postgres12 --endpoint "$POSTGRES_SEEDS" --port 5432 --user temporal_migrator --database "$1" update-schema --schema-dir "$2"
    }
    migrate waooaw_temporal /etc/temporal/schema/postgresql/v12/temporal/versioned
    migrate waooaw_temporal_visibility /etc/temporal/schema/postgresql/v12/visibility/versioned
  ' > "$EVIDENCE_DIR/temporal-migration.log" 2>&1 || { cat "$EVIDENCE_DIR/temporal-migration.log" >&2; exit 1; }

# Demo order: the Billing authority migration lands before application activation.
docker run --rm --network "$WC124_NETWORK" \
  -e DATABASE_URL="$(wc124_role_url billing_migrator)" \
  -e MIGRATION_PATTERN=59-wc124-billing-authority.sql -e MIGRATION_SCHEMA=billing \
  "${IMAGES[billing-engine]}" python migrate.py > "$EVIDENCE_DIR/billing-migration.log" 2>&1

# Dependencies that are not database components: auth Redis and the identity issuer.
# The issuer stub answers OIDC discovery only, which is all the readiness probes consult.
wc124_track "$RUN_ID-redis" "$RUN_ID-issuer"
docker run -d --name "$RUN_ID-redis" --network "$WC124_NETWORK" "$REDIS_IMAGE" >/dev/null
# Demo seeds the auth-abuse epoch when Redis starts and web readiness fails closed until the
# longest limiter window (3600 s) has elapsed. Seed a warmed epoch so the harness exercises the
# steady state; the cold-start hour is a documented Demo property, not a defect under test.
for attempt in $(seq 1 30); do docker exec "$RUN_ID-redis" redis-cli ping 2>/dev/null | grep -q PONG && break; sleep 1; done
docker exec "$RUN_ID-redis" redis-cli SET "waooaw:demo:auth-abuse:v1:epoch" "$(( ($(date +%s) - 3700) * 1000 ))" NX >/dev/null
mkdir -p "$WC124_WORKDIR/issuer/realms/waooaw/.well-known"
printf '{"issuer":"http://%s/realms/waooaw","jwks_uri":"http://%s/realms/waooaw/protocol/openid-connect/certs"}\n' \
  "$RUN_ID-issuer" "$RUN_ID-issuer" > "$WC124_WORKDIR/issuer/realms/waooaw/.well-known/openid-configuration"
printf '{"keys":[]}\n' > "$WC124_WORKDIR/issuer/realms/waooaw/certs"
chmod -R a+rX "$WC124_WORKDIR/issuer"
docker run -d --name "$RUN_ID-issuer" --network "$WC124_NETWORK" \
  -v "$WC124_WORKDIR/issuer:/usr/share/nginx/html:ro" "$STUB_IMAGE" >/dev/null
ISSUER="http://$RUN_ID-issuer/realms/waooaw"

# Temporal runtime as temporal_runtime through PgBouncer (session pools), schema setup skipped.
TEMPORAL="$RUN_ID-temporal"
wc124_track "$TEMPORAL"
docker run -d --name "$TEMPORAL" --network "$WC124_NETWORK" \
  -e DB=postgres12 -e DB_PORT=5432 -e DBNAME=waooaw_temporal -e VISIBILITY_DBNAME=waooaw_temporal_visibility \
  -e POSTGRES_USER=temporal_runtime -e POSTGRES_PWD="$WC124_ROLE_PASSWORD" -e POSTGRES_SEEDS="$WC124_PGBOUNCER" \
  -e SKIP_SCHEMA_SETUP=true -e SKIP_DB_CREATE=true -e SQL_MAX_CONNS=2 -e SQL_MAX_IDLE_CONNS=2 \
  "$TEMPORAL_IMAGE" >/dev/null

probe() {
  # probe NAME CONTAINER KIND TARGET  (KIND: tcp PORT | http URL)
  local name="$1" container="$2" kind="$3" target="$4" attempt
  for attempt in $(seq 1 60); do
    if [ "$(docker inspect -f '{{.State.Running}}' "$container")" != true ]; then
      docker logs "$container" > "$EVIDENCE_DIR/$name.log" 2>&1
      echo "$name exited before becoming ready" >&2
      tail -20 "$EVIDENCE_DIR/$name.log" >&2
      return 1
    fi
    if [ "$kind" = tcp ]; then
      if docker exec "$container" sh -c "exec 3<>/dev/tcp/127.0.0.1/$target" 2>/dev/null \
        || docker run --rm --network "$WC124_NETWORK" "$WC124_POSTGRES_IMAGE" bash -c "exec 3<>/dev/tcp/$container/$target" 2>/dev/null; then
        return 0
      fi
    else
      status=$(docker run --rm --network "$WC124_NETWORK" "$STUB_IMAGE" \
        curl -s -o /dev/null -w '%{http_code}' --max-time 3 "$target" 2>/dev/null || true)
      case "$status" in 200|204) return 0 ;; esac
    fi
    sleep 2
  done
  docker logs "$container" > "$EVIDENCE_DIR/$name.log" 2>&1
  echo "$name did not become ready ($kind $target)" >&2
  tail -20 "$EVIDENCE_DIR/$name.log" >&2
  return 1
}

CE="$RUN_ID-constitutional-engine"; BP="$RUN_ID-business-platform"; PR="$RUN_ID-professional-runtime"; WEB="$RUN_ID-web"
wc124_track "$CE" "$BP" "$PR" "$WEB"

docker run -d --name "$CE" --network "$WC124_NETWORK" \
  -e ASPNETCORE_URLS=http://+:5002 \
  -e CE_RUNTIME_CREDENTIAL="$SECRET" \
  -e ConnectionStrings__DefaultConnection="$(wc124_role_npgsql ce_runtime)" \
  "${IMAGES[constitutional-engine]}" >/dev/null
probe constitutional-engine "$CE" tcp 5002

docker run -d --name "$BP" --network "$WC124_NETWORK" \
  -e ASPNETCORE_ENVIRONMENT=Production -e ASPNETCORE_URLS=http://+:5001 \
  -e BP_SERVICE_JWT_SECRET="$SECRET" \
  -e ConnectionStrings__DefaultConnection="$(wc124_role_npgsql bp_runtime)" \
  -e WAOOAW_DEMO_DATABASE_BOOTSTRAP=false \
  -e ConstitutionalEngine__Address="http://$CE:5002" -e ConstitutionalEngine__GrpcUrl="http://$CE:5002" \
  -e Keycloak__Audience=waooaw-platform -e Keycloak__Authority="$ISSUER" -e Keycloak__RequireHttpsMetadata=false \
  -e Identity__Hmac__ActiveVersion=v1 -e Identity__Hmac__Key="$HMAC_KEY" \
  -e Conversation__CursorHmacKey="$HMAC_KEY" -e ChannelContinuity__EnvelopeHmacKey="$HMAC_KEY" \
  -e IdentitySecurityEvents__Ingest__SigningKey="$HMAC_KEY" \
  -e IdentityBrokerRead__Enabled=true -e IdentityBrokerRead__ActorIssuer="https://$RUN_ID-identity.internal/realms/waooaw" \
  -e IdentityBrokerRead__PrivateOrigin="https://$RUN_ID-keycloak.internal" -e IdentityBrokerRead__AllowedPrivateHosts__0="$RUN_ID-keycloak.internal" \
  -e IdentityBrokerRead__AllowedAuthorizedParties__0=waooaw-web -e IdentityBrokerRead__ClientId=waooaw-bp-identity-reader \
  -e IdentityBrokerRead__ClientSecret="$SECRET" \
  -e IdentityLifecycleWriter__Enabled=true -e IdentityLifecycleWriter__PrivateOrigin="https://$RUN_ID-keycloak.internal" \
  -e IdentityLifecycleWriter__AllowedPrivateHosts__0="$RUN_ID-keycloak.internal" -e IdentityLifecycleWriter__ClientId=waooaw-bp-identity-lifecycle-writer \
  -e IdentityLifecycleWriter__ClientSecret="$SECRET" \
  -e IdentityBrokerRead__Providers__google__ProviderNamespace=urn:waooaw:identity:demo:google:customer-login:v1 \
  -e IdentityBrokerRead__Providers__google__TrustConfigDigest="$HMAC_KEY" \
  -e IdentityBrokerRead__Providers__facebook__ProviderNamespace=urn:waooaw:identity:demo:facebook:customer-login:v1 \
  -e IdentityBrokerRead__Providers__facebook__TrustConfigDigest="$HMAC_KEY" \
  -e DMA_ADMISSION_CONTENT_DIGEST="$HMAC_KEY" -e DMA_ARTIFACT_DIGEST="sha256:$HMAC_KEY" \
  "${IMAGES[business-platform]}" >/dev/null
probe business-platform "$BP" http "http://$BP:5001/health/ready"

probe temporal "$TEMPORAL" tcp 7233
# Professional Runtime must only start once the default namespace is registered; the client
# otherwise stalls on an unknown namespace instead of retrying.
temporal_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$TEMPORAL")
for attempt in $(seq 1 60); do
  docker exec "$TEMPORAL" tctl --ad "$temporal_ip:7233" namespace describe default >/dev/null 2>&1 && break
  test "$attempt" != 60 || { echo "temporal default namespace never became available" >&2; exit 1; }
  sleep 2
done
docker run -d --name "$PR" --network "$WC124_NETWORK" \
  -e PR_SERVICE_JWT_SECRET="$SECRET" -e BP_SERVICE_JWT_SECRET="$SECRET" \
  -e CONSTITUTIONAL_ENGINE_ADDRESS="$CE:5002" \
  -e KEYCLOAK_AUDIENCE=waooaw-platform -e KEYCLOAK_ISSUER="$ISSUER" \
  -e KEYCLOAK_JWKS_URL="$ISSUER/protocol/openid-connect/certs" \
  -e AIR_TRANSCRIPTION_BASE_URL="http://$RUN_ID-air.invalid" -e DMA_ADAPTER_BASE_URL="http://$RUN_ID-dma.invalid" \
  -e TEMPORAL_ADDRESS="$TEMPORAL:7233" -e TEMPORAL_NAMESPACE=default \
  "${IMAGES[professional-runtime]}" >/dev/null
probe professional-runtime "$PR" http "http://$PR:5003/health"

docker run -d --name "$WEB" --network "$WC124_NETWORK" \
  -e NODE_ENV=production -e WAOOAW_ENVIRONMENT=demo -e WAOOAW_SERVER_SESSION_MODE=disabled \
  -e BUSINESS_PLATFORM_URL="http://$BP:5001" -e NEXTAUTH_URL="http://$WEB:3000" \
  -e KEYCLOAK_CLIENT_ID=waooaw-web -e KEYCLOAK_CLIENT_SECRET="$SECRET" -e KEYCLOAK_ISSUER="$ISSUER" \
  -e NEXTAUTH_SECRET="$SECRET" -e REDIS_URL="redis://$RUN_ID-redis:6379/0" \
  -e AUTH_ABUSE_DIGEST_KEY="$HMAC_KEY" \
  -e AUTH_ABUSE_LIMITS_JSON='{"AUTH_START":{"limit":20,"windowSeconds":600},"AUTH_CALLBACK":{"limit":30,"windowSeconds":600},"RECOVERY":{"limit":5,"windowSeconds":3600},"PROVIDER_LINK":{"limit":10,"windowSeconds":3600},"PROVIDER_UNLINK":{"limit":10,"windowSeconds":3600},"RESEND":{"limit":5,"windowSeconds":900},"CREDENTIAL":{"limit":10,"windowSeconds":3600}}' \
  -e IDENTITY_EVENT_SIGNING_KEY="$HMAC_KEY" \
  -e WEB_SESSION_DATABASE_URL="$(wc124_role_url web_session_app)" \
  -e WEB_SESSION_DATABASE_SSL_MODE=disable \
  -e SESSION_PROTOCOL_DIGEST_KEYS="{\"v1\":\"$SESSION_KEY_B64\"}" -e SESSION_TOKEN_ENVELOPE_KEYS="{\"v1\":\"$SESSION_KEY_B64\"}" \
  -e SESSION_PROTOCOL_DIGEST_WRITE_VERSION=v1 -e SESSION_TOKEN_ENVELOPE_WRITE_VERSION=v1 \
  -e WEB_SESSION_DEPLOY_VERSION=wc123-auth-session-v1 \
  "${IMAGES[web]}" >/dev/null
probe web-live "$WEB" http "http://$WEB:3000/api/health/live"
# Attribute web readiness dependencies individually before the composite probe.
probe issuer-discovery "$RUN_ID-issuer" http "$ISSUER/.well-known/openid-configuration"
test "$(docker exec "$RUN_ID-redis" redis-cli ping)" = PONG
test "$(wc124_backend_identity web_session_app)" = web_session_app
docker run --rm --network "$WC124_NETWORK" -e PGPASSWORD="$WC124_ROLE_PASSWORD" "$WC124_POSTGRES_IMAGE" \
  psql -h "$WC124_PGBOUNCER" -p 5432 -U web_session_app -d waooaw -At -c "SELECT web_session.schema_ready(1, 'wc123-auth-session-v1')" > "$EVIDENCE_DIR/web-session-access.log" 2>&1 \
  && grep -qx t "$EVIDENCE_DIR/web-session-access.log" \
  || { cat "$EVIDENCE_DIR/web-session-access.log" >&2; echo "web_session_app cannot verify the web_session schema" >&2; exit 1; }
probe web "$WEB" http "http://$WEB:3000/api/health/ready"

for name in constitutional-engine:$CE business-platform:$BP professional-runtime:$PR web:$WEB temporal:$TEMPORAL; do
  docker logs "${name#*:}" > "$EVIDENCE_DIR/${name%%:*}.log" 2>&1
done

# Every backend session on the instance must belong to a restricted runtime role.
backend_roles=$(psql_admin -c "SELECT string_agg(DISTINCT usename, ',' ORDER BY usename) FROM pg_stat_activity WHERE datname LIKE 'waooaw%' AND usename <> 'waooaw'")
# PgBouncer keeps the migration step's server connections pooled (idle, no client) after the job
# exits, so the migrator identities may linger idle; no runtime may hold an active one.
unexpected_roles=$(psql_admin -c "SELECT count(DISTINCT usename) FROM pg_stat_activity WHERE datname LIKE 'waooaw%' AND NOT (usename IN ('waooaw','ce_runtime','bp_runtime','web_session_app','temporal_runtime') OR (usename IN ('billing_migrator','temporal_migrator') AND state = 'idle'))")
test "$unexpected_roles" = 0
# Demo PgBouncer admits 40 clients and the server 40 backends; Temporal's session pools must leave headroom.
temporal_backends=$(psql_admin -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'temporal_runtime'")
# Upper bound: 4 internal services x 2 stores x SQL_MAX_CONNS=2.
test "$temporal_backends" -le 16 || { echo "temporal_runtime holds $temporal_backends backends (> 16)" >&2; exit 1; }
# The whole activated estate must leave Keycloak's bounded pool (5) spare within the usable slots.
total_backends=$(psql_admin -c "SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'client backend' AND usename <> 'waooaw'")
test $((WC124_PG_USABLE_CONNECTIONS - total_backends)) -ge 5 \
  || { echo "only $((WC124_PG_USABLE_CONNECTIONS - total_backends)) of $WC124_PG_USABLE_CONNECTIONS usable slots remain after activation" >&2; exit 1; }
test "$(wc124_backend_identity bp_runtime)" = bp_runtime
# Server-side connection footprint per role, to compare against the Demo PgBouncer limits.
backend_footprint=$(psql_admin -c "SELECT json_object_agg(usename, n) FROM (SELECT usename, count(*) AS n FROM pg_stat_activity WHERE datname LIKE 'waooaw%' AND usename <> 'waooaw' GROUP BY usename) s")

jq -n \
  --arg fixture "$fixture_source" --arg backend_roles "$backend_roles" --argjson backend_footprint "${backend_footprint:-{\}}" \
  --argjson usable "$WC124_PG_USABLE_CONNECTIONS" --argjson total "$total_backends" --argjson stale "$stale_reproduced" \
  --arg ce "${IMAGES[constitutional-engine]}" --arg bp "${IMAGES[business-platform]}" \
  --arg pr "${IMAGES[professional-runtime]}" --arg web "${IMAGES[web]}" --arg billing "${IMAGES[billing-engine]}" \
  '{schema: "waooaw.wc124-application-activation-local/v1", fixture: $fixture,
    route: "pgbouncer-scram-per-role", database_topology: "single-provisioned-instance",
    images: {constitutional_engine: $ce, business_platform: $bp, professional_runtime: $pr, web: $web, billing_engine: $billing},
    probes: {constitutional_engine: "tcp:5002", business_platform: "http:/health/ready",
             professional_runtime: "http:/health", temporal: "tcp:7233", web: ["http:/api/health/live", "http:/api/health/ready"]},
    observed_backend_roles: ($backend_roles | split(",")), backend_connections_by_role: $backend_footprint,
    pgbouncer_limits: {max_client_conn: 40, default_pool_size: 8, reserve_pool_size: 2},
    connection_budget: {usable_slots: $usable, backends_after_activation: $total, stale_pool_exhaustion_reproduced: $stale},
    status: "passed"}' \
  | tee "$EVIDENCE_DIR/result.json"

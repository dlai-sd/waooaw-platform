#!/bin/sh
set -eu

validation_output_directory=${WAOOAW_VALIDATION_OUTPUT_DIRECTORY:-$PWD/test-results}
host_validation_output_directory=${WAOOAW_HOST_VALIDATION_OUTPUT_DIRECTORY:-$validation_output_directory}
mkdir -p "$validation_output_directory"
build_manifest=$validation_output_directory/product-image-builds.txt
: > "$build_manifest"
workload_credentials=$validation_output_directory/rest-workload-identity
rm -rf "$workload_credentials"
python scripts/bootstrap_workload_identity.py \
    --registry infrastructure/workload-identity/registry.yaml \
    --environment ci \
    --output "$workload_credentials"
export WAOOAW_WORKLOAD_CREDENTIALS_HOST_PATH=$host_validation_output_directory/rest-workload-identity
compose_override=/tmp/rest-contract-workload-identity.override.yaml
cat > "$compose_override" <<'EOF'
services:
  business-platform:
    environment:
      WhatsApp__CallbackHost: whatsapp-callback
  professional-runtime:
    user: "1000:1000"
    environment:
      WAOOAW_WORKLOAD_CREDENTIALS: /run/waooaw/workload-identity
    volumes:
      - type: bind
        source: ${WAOOAW_WORKLOAD_CREDENTIALS_HOST_PATH:?}
        target: /run/waooaw/workload-identity
        read_only: true
EOF
compose="docker compose -f docker-compose.yml -f $compose_override"

scope_environment=/tmp/rest-contract-scope.env
python scripts/validation_control/rest_contract_scope.py \
    --changed-files "${WAOOAW_HOST_CHANGED_FILES_FILE:-${WAOOAW_CHANGED_FILES_FILE:-}}" \
    --output "$scope_environment"
. "$scope_environment"
export REST_BP_IDENTITY_REGEX REST_BP_PRODUCT_REGEX REST_BP_SERVICE_REGEX REST_PR_SERVICE_REGEX

if test "$REST_RUN_BP" = false && test "$REST_RUN_PR" = false; then
    printf 'REST contract gate not applicable: no REST runtime or contract inputs changed.\n'
    exit 0
fi

REST_START_BP=$REST_RUN_BP
if test "$REST_RUN_PR" = true; then
    REST_START_BP=true
fi

set -- constitutional-engine
printf '%s\n' constitutional-engine >> "$build_manifest"
if test "$REST_START_BP" = true; then
    set -- "$@" business-platform
    printf '%s\n' business-platform >> "$build_manifest"
fi
if test "$REST_RUN_PR" = true; then
    set -- "$@" professional-runtime
    printf '%s\n' professional-runtime >> "$build_manifest"
fi

export POSTGRES_HOST_PORT=0
export KEYCLOAK_HOST_PORT=0
export TEMPORAL_HOST_PORT=0
export CONSTITUTIONAL_ENGINE_HOST_PORT=0
export BUSINESS_PLATFORM_HOST_PORT=0
export PROFESSIONAL_RUNTIME_HOST_PORT=0

cleanup() {
    status=$?
    trap - EXIT
    set +e
    if test "$status" -ne 0; then
        $compose logs --no-color postgres business-platform professional-runtime \
            > "$validation_output_directory/rest-service-logs.txt" 2>&1
    fi
    $compose down --volumes --remove-orphans
    compose_status=$?
    rm -rf "$workload_credentials"
    rm -f "$compose_override"
    if test "$status" -ne 0; then
        exit "$status"
    fi
    exit "$compose_status"
}
trap cleanup EXIT

scripts/validation_control/run_docker_build.sh $compose build "$@"
$compose up --detach --no-build --wait --wait-timeout 180 \
    $(if test "$REST_RUN_BP" = true; then printf '%s ' business-platform; fi) \
    $(if test "$REST_RUN_PR" = true; then printf '%s ' professional-runtime; fi)

if test "$REST_RUN_BP" = true; then
    $compose --profile test-python run --rm --pull never \
        -e REST_BP_IDENTITY_REGEX -e REST_BP_PRODUCT_REGEX -e REST_BP_SERVICE_REGEX \
        --volume "$host_validation_output_directory:/workspace/test-results" test-runner-python \
        sh /workspace/scripts/validation_control/run_business_platform_contract_scope.sh
fi
if test "$REST_RUN_PR" = true; then
    $compose --profile test-python run --rm --pull never \
        -e REST_PR_SERVICE_REGEX \
        --volume "$host_validation_output_directory:/workspace/test-results" test-runner-python \
        sh /workspace/scripts/validation_control/run_professional_runtime_contract_scope.sh
fi

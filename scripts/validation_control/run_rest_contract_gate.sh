#!/bin/sh
set -eu

validation_output_directory=${WAOOAW_VALIDATION_OUTPUT_DIRECTORY:-$PWD/test-results}
mkdir -p "$validation_output_directory"

export POSTGRES_HOST_PORT=0
export KEYCLOAK_HOST_PORT=0
export TEMPORAL_HOST_PORT=0
export CONSTITUTIONAL_ENGINE_HOST_PORT=0
export BUSINESS_PLATFORM_HOST_PORT=0
export PROFESSIONAL_RUNTIME_HOST_PORT=0

cleanup() {
    docker compose down --volumes --remove-orphans
}
trap cleanup EXIT

docker compose build constitutional-engine business-platform professional-runtime
docker compose up --detach --no-build --wait --wait-timeout 180 business-platform professional-runtime
docker compose --profile test-python run --rm --pull never \
    --volume "$validation_output_directory:/workspace/test-results" test-runner-python \
    sh -c 'set -u
        customer_identity_path_regex="^/api/v1/identity(?:/|$)"
        customer_product_path_regex="^/api/v1/(acquisition/continuations(?:/|$)|customer-portal/interactions/portal/messages(?:/|$)|professionals/marketplace(?:/|$)|employment/relationships(?:$|/(?![^/]+/(?:transitions|offerability)(?:/|$))))"
        customer_path_regex="^/api/v1/(identity(?:/|$)|acquisition/continuations(?:/|$)|customer-portal/interactions/portal/messages(?:/|$)|professionals/marketplace(?:/|$)|employment/relationships(?:$|/(?![^/]+/(?:transitions|offerability)(?:/|$))))"
        python /workspace/scripts/validation_control/bootstrap_rest_identity.py \
        --identity-token-file /tmp/business-platform-identity-token \
        --service-token-file /tmp/business-platform-service-token
        identity_token=$(cat /tmp/business-platform-identity-token)
        service_token=$(cat /tmp/business-platform-service-token)
        customer_product_status=0
        customer_identity_status=0
        service_status=0
        rm -f /workspace/test-results/schemathesis-bp.xml
        cd /tmp && schemathesis --config-file /workspace/validation/schemathesis.toml run /workspace/architecture/reference/api-specs/business-platform.openapi.yaml \
        --url http://business-platform:5001 \
        --include-path-regex "$customer_product_path_regex" \
        -H "Authorization:Bearer $identity_token" \
        --checks all \
        --max-examples 100 \
        --suppress-health-check=filter_too_much \
        --report junit \
        --report-junit-path /workspace/test-results/schemathesis-bp-customer-product.xml || customer_product_status=$?
        cd /tmp && schemathesis --config-file /workspace/validation/schemathesis.toml run /workspace/architecture/reference/api-specs/business-platform.openapi.yaml \
        --url http://business-platform:5001 \
        --include-path-regex "$customer_identity_path_regex" \
        -H "Authorization:Bearer $identity_token" \
        --checks all \
        --max-examples 100 \
        --suppress-health-check=filter_too_much \
        --report junit \
        --report-junit-path /workspace/test-results/schemathesis-bp-customer-identity.xml || customer_identity_status=$?
        cd /tmp && schemathesis --config-file /workspace/validation/schemathesis.toml run /workspace/architecture/reference/api-specs/business-platform.openapi.yaml \
        --url http://business-platform:5001 \
        --exclude-path-regex "$customer_path_regex" \
        -H "Authorization:Bearer $service_token" \
        --checks all \
        --max-examples 100 \
        --suppress-health-check=filter_too_much \
        --report junit \
        --report-junit-path /workspace/test-results/schemathesis-bp-service.xml || service_status=$?
        if test "$customer_product_status" -eq 0 && \
           test "$customer_identity_status" -eq 0 && \
           test "$service_status" -eq 0; then
            python /workspace/scripts/validation_control/merge_junit_reports.py \
                --output /workspace/test-results/schemathesis-bp.xml \
                /workspace/test-results/schemathesis-bp-customer-product.xml \
                /workspace/test-results/schemathesis-bp-customer-identity.xml \
                /workspace/test-results/schemathesis-bp-service.xml
        else
            printf "Business Platform contract lanes failed: product=%s identity=%s service=%s\n" \
                "$customer_product_status" "$customer_identity_status" "$service_status" >&2
            false
        fi'
docker compose --profile test-python run --rm --pull never \
    --volume "$validation_output_directory:/workspace/test-results" test-runner-python \
    sh -c "cd /tmp && schemathesis --config-file /workspace/validation/schemathesis.toml run /workspace/architecture/reference/api-specs/professional-runtime.openapi.yaml \
        --url http://professional-runtime:5003 \
        --checks all \
        --max-examples 100 \
        --suppress-health-check=filter_too_much \
        --report junit \
        --report-junit-path /workspace/test-results/schemathesis-pr.xml"

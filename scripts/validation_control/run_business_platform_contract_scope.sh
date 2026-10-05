#!/bin/sh
set -eu

python /workspace/scripts/validation_control/bootstrap_rest_identity.py \
    --identity-token-file /tmp/business-platform-identity-token \
    --service-token-file /tmp/business-platform-service-token
identity_token=$(cat /tmp/business-platform-identity-token)
service_token=$(cat /tmp/business-platform-service-token)
export SCHEMATHESIS_HOOKS=/workspace/scripts/validation_control/schemathesis_hooks.py

runner=/workspace/scripts/validation_control/run_schemathesis_lane.sh
specification=/workspace/architecture/reference/api-specs/business-platform.openapi.yaml
base_url=http://business-platform:5001
identity_all='^/api/v1/identity(?:/|$)'
product_all='^/api/v1/(acquisition/continuations(?:/|$)|customer-portal/interactions/portal/messages(?:/|$)|professionals/marketplace(?:/|$)|employment/relationships(?:$|/(?![^/]+/(?:transitions|offerability)(?:/|$))))'
customer_all='^/api/v1/(identity(?:/|$)|acquisition/continuations(?:/|$)|customer-portal/interactions/portal/messages(?:/|$)|professionals/marketplace(?:/|$)|employment/relationships(?:$|/(?![^/]+/(?:transitions|offerability)(?:/|$))))'
service_all="^(?!${customer_all#^}).*"

rm -f /workspace/test-results/schemathesis-bp*.xml
identity_smoke_status=0
product_smoke_status=0
service_smoke_status=0
sh "$runner" /workspace/test-results/schemathesis-bp-customer-identity-smoke.xml \
    "$specification" "$base_url" "$identity_all" "$identity_token" smoke &
identity_smoke_pid=$!
sh "$runner" /workspace/test-results/schemathesis-bp-customer-product-smoke.xml \
    "$specification" "$base_url" "$product_all" "$identity_token" smoke &
product_smoke_pid=$!
sh "$runner" /workspace/test-results/schemathesis-bp-service-smoke.xml \
    "$specification" "$base_url" "$service_all" "$service_token" smoke &
service_smoke_pid=$!
wait "$identity_smoke_pid" || identity_smoke_status=$?
wait "$product_smoke_pid" || product_smoke_status=$?
wait "$service_smoke_pid" || service_smoke_status=$?
if test "$identity_smoke_status" -ne 0 || test "$product_smoke_status" -ne 0 || test "$service_smoke_status" -ne 0; then
    printf 'Business Platform smoke lanes failed: identity=%s product=%s service=%s\n' \
        "$identity_smoke_status" "$product_smoke_status" "$service_smoke_status" >&2
    exit 1
fi

reports='/workspace/test-results/schemathesis-bp-customer-identity-smoke.xml /workspace/test-results/schemathesis-bp-customer-product-smoke.xml /workspace/test-results/schemathesis-bp-service-smoke.xml'
identity_focused_status=0
product_focused_status=0
service_focused_status=0
identity_focused_pid=
product_focused_pid=
service_focused_pid=
if test -n "$REST_BP_IDENTITY_REGEX"; then
    sh "$runner" /workspace/test-results/schemathesis-bp-customer-identity-focused.xml \
        "$specification" "$base_url" "$REST_BP_IDENTITY_REGEX" "$identity_token" deep &
    identity_focused_pid=$!
    reports="$reports /workspace/test-results/schemathesis-bp-customer-identity-focused.xml"
fi
if test -n "$REST_BP_PRODUCT_REGEX"; then
    sh "$runner" /workspace/test-results/schemathesis-bp-customer-product-focused.xml \
        "$specification" "$base_url" "$REST_BP_PRODUCT_REGEX" "$identity_token" deep &
    product_focused_pid=$!
    reports="$reports /workspace/test-results/schemathesis-bp-customer-product-focused.xml"
fi
if test -n "$REST_BP_SERVICE_REGEX"; then
    sh "$runner" /workspace/test-results/schemathesis-bp-service-focused.xml \
        "$specification" "$base_url" "$REST_BP_SERVICE_REGEX" "$service_token" deep &
    service_focused_pid=$!
    reports="$reports /workspace/test-results/schemathesis-bp-service-focused.xml"
fi
if test -n "$identity_focused_pid"; then
    wait "$identity_focused_pid" || identity_focused_status=$?
fi
if test -n "$product_focused_pid"; then
    wait "$product_focused_pid" || product_focused_status=$?
fi
if test -n "$service_focused_pid"; then
    wait "$service_focused_pid" || service_focused_status=$?
fi
if test "$identity_focused_status" -ne 0 || test "$product_focused_status" -ne 0 || test "$service_focused_status" -ne 0; then
    printf 'Business Platform focused lanes failed: identity=%s product=%s service=%s\n' \
        "$identity_focused_status" "$product_focused_status" "$service_focused_status" >&2
    exit 1
fi

# Report paths are generated constants and contain no whitespace.
# shellcheck disable=SC2086
python /workspace/scripts/validation_control/merge_junit_reports.py \
    --output /workspace/test-results/schemathesis-bp.xml $reports
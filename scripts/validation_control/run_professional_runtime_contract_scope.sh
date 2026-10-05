#!/bin/sh
set -eu

runner=/workspace/scripts/validation_control/run_schemathesis_lane.sh
specification=/workspace/architecture/reference/api-specs/professional-runtime.openapi.yaml
base_url=http://professional-runtime:5003
service_all='^/(?!health$).*'
health='^/health$'

rm -f /workspace/test-results/schemathesis-pr*.xml
service_smoke_status=0
health_smoke_status=0
sh "$runner" /workspace/test-results/schemathesis-pr-service-smoke.xml \
    "$specification" "$base_url" "$service_all" - smoke &
service_smoke_pid=$!
sh "$runner" /workspace/test-results/schemathesis-pr-health-smoke.xml \
    "$specification" "$base_url" "$health" - smoke health &
health_smoke_pid=$!
wait "$service_smoke_pid" || service_smoke_status=$?
wait "$health_smoke_pid" || health_smoke_status=$?
if test "$service_smoke_status" -ne 0 || test "$health_smoke_status" -ne 0; then
    printf 'Professional Runtime smoke lanes failed: service=%s health=%s\n' \
        "$service_smoke_status" "$health_smoke_status" >&2
    exit 1
fi

reports='/workspace/test-results/schemathesis-pr-service-smoke.xml /workspace/test-results/schemathesis-pr-health-smoke.xml'
if test -n "$REST_PR_SERVICE_REGEX"; then
    sh "$runner" /workspace/test-results/schemathesis-pr-service-focused.xml \
        "$specification" "$base_url" "$REST_PR_SERVICE_REGEX" - deep
    reports="$reports /workspace/test-results/schemathesis-pr-service-focused.xml"
fi

# Report paths are generated constants and contain no whitespace.
# shellcheck disable=SC2086
python /workspace/scripts/validation_control/merge_junit_reports.py \
    --output /workspace/test-results/schemathesis-pr.xml $reports
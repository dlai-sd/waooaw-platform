#!/bin/sh
set -eu

cleanup() {
    docker compose down --volumes --remove-orphans
}
trap cleanup EXIT

docker compose build business-platform professional-runtime
docker compose up --detach --wait --wait-timeout 180 business-platform professional-runtime
docker compose --profile test-python run --rm --pull never test-runner-python \
    schemathesis run architecture/reference/api-specs/business-platform.openapi.yaml \
    --url http://business-platform:5001 \
    --checks all \
    --max-examples 100 \
    --report junit \
    --report-junit-path test-results/schemathesis-bp.xml
docker compose --profile test-python run --rm --pull never test-runner-python \
    schemathesis run architecture/reference/api-specs/professional-runtime.openapi.yaml \
    --url http://professional-runtime:5003 \
    --checks all \
    --max-examples 100 \
    --report junit \
    --report-junit-path test-results/schemathesis-pr.xml

#!/bin/sh
set -eu

scenario=${1:?acceptance scenario is required}
result=${2:?result identifier is required}
shift 2

pytest "$scenario" \
    -v --tb=short \
    --junit-xml="test-results/$result.xml" \
    "$@"

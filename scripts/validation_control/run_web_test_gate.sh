#!/bin/sh
set -eu

workspace=${VALIDATION_WORKSPACE:-/workspace}
output_directory=${VALIDATION_OUTPUT_DIRECTORY:-test-results}
case "$output_directory" in
    /*) ;;
    *) output_directory="$workspace/$output_directory" ;;
esac
coverage_directory="$output_directory/coverage/web"
result_file="$output_directory/web-test-results.json"
log_file="$output_directory/web-test.log"
run_directory=/tmp/web

mkdir -p "$coverage_directory"
rm -rf "$run_directory"
cp -a "$workspace/web" "$run_directory"
ln -s /opt/waooaw-web/node_modules "$run_directory/node_modules"
cd "$run_directory"

tsc --noEmit --incremental false
eslint . --max-warnings 0

set +e
jest --runInBand --coverage \
    --coverageDirectory="$coverage_directory" \
    --coverageThreshold='{"global":{"lines":90,"branches":80,"functions":90,"statements":90}}' \
    --json --outputFile="$result_file" >"$log_file" 2>&1
result=$?
set -e
cat "$log_file"
exit "$result"

#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: run_dotnet_test_gate.sh SERVICE TEST_PROJECT" >&2
    exit 2
fi

service=$1
test_project=$2
result_directory="/workspace/test-results/coverage/$service"
artifact_directory="/tmp/artifacts/$service"

rm -rf "$result_directory"
mkdir -p "$result_directory"
dotnet restore "$test_project" --artifacts-path "$artifact_directory"
dotnet build "$test_project" --no-restore -warnaserror --artifacts-path "$artifact_directory"
dotnet test "$test_project" \
    --no-build \
    --artifacts-path "$artifact_directory" \
    --settings tests/coverage.runsettings \
    --collect:"XPlat Code Coverage" \
    --results-directory "$result_directory"

coverage_file=$(find "$result_directory" -name coverage.cobertura.xml -print -quit)
if [ -z "$coverage_file" ]; then
    echo "Cobertura coverage report not found" >&2
    exit 1
fi
read -r line_rate branch_rate <<EOF
$(sed -n 's/.*<coverage line-rate="\([0-9.]*\)" branch-rate="\([0-9.]*\)".*/\1 \2/p' "$coverage_file" | head -n 1)
EOF
awk -v lines="$line_rate" -v branches="$branch_rate" 'BEGIN {
    printf "line_coverage=%.2f%% branch_coverage=%.2f%%\n", lines * 100, branches * 100
    exit !(lines >= 0.90 && branches >= 0.80)
}'
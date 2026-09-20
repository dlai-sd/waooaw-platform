#!/bin/sh
set -u

if [ "$#" -lt 4 ]; then
    echo "usage: run_python_test_gate.sh SERVICE SOURCE MYPY_PATH TEST_PATH..." >&2
    exit 2
fi

service=$1
source_path=$2
mypy_path=$3
shift 3
status=0
result_directory="/workspace/test-results/coverage/$service"

mkdir -p "$result_directory"
ruff check "$source_path" "$@" || status=1
ruff format --check "$source_path" "$@" || status=1
(
    cd /tmp
    MYPYPATH="$mypy_path" mypy --strict --explicit-package-bases \
        $(find "/workspace/$source_path" -name "*.py" -type f | sort) \
        --config-file /workspace/pyproject.toml \
        --cache-dir /tmp/mypy-cache
) || status=1
export COVERAGE_FILE=/tmp/.coverage
pytest "$@" \
    --cov="$source_path" \
    --cov-branch \
    --cov-report="xml:$result_directory/coverage.xml" \
    --cov-report="json:$result_directory/coverage.json" \
    --cov-fail-under=0 || status=1
python - "$service" "$result_directory/coverage.json" <<'PY' || status=1
import json
import sys

service_name, coverage_path = sys.argv[1:]
with open(coverage_path, encoding="utf-8") as coverage_file:
    totals = json.load(coverage_file)["totals"]
lines = totals["covered_lines"] * 100 / totals["num_statements"]
branches = 100 if totals["num_branches"] == 0 else totals["covered_branches"] * 100 / totals["num_branches"]
print(json.dumps({"service": service_name, "line_coverage": lines, "branch_coverage": branches,
                  "minimum_lines": 90, "minimum_branches": 80}))
raise SystemExit(0 if lines >= 90 and branches >= 80 else 1)
PY

exit "$status"
#!/bin/sh
set -eu

service=${1:?service path is required}
mypy_path=${2:?mypy path is required}

ruff check "$service" --output-format=github
ruff format --check "$service"
cd /tmp
MYPYPATH="$mypy_path" mypy --strict --explicit-package-bases \
    $(find "/workspace/$service" -name "*.py" -type f | sort) \
    --config-file /workspace/pyproject.toml
cd /workspace
bandit -r "$service" -c pyproject.toml -f json -o /tmp/bandit-results.json --exit-zero
python - <<'PY'
import json
import sys

with open("/tmp/bandit-results.json", encoding="utf-8") as results_file:
    results = json.load(results_file)
issues = [result for result in results.get("results", []) if result["issue_severity"] in ("HIGH", "CRITICAL")]
if issues:
    print(f"SECURITY GATE FAILED: {len(issues)} HIGH/CRITICAL finding(s)")
    sys.exit(1)
print("No HIGH/CRITICAL security findings")
PY
grep -rn "log.*prompt_text\|logger.*prompt_text\|print.*prompt_text" \
    "$service" --include="*.py" && {
    echo "SECURITY VIOLATION: prompt_text found in log/print statement - ADR-028"
    exit 1
} || echo "No prompt_text in log statements"
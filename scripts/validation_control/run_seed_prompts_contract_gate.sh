#!/bin/sh
set -eu

python scripts/seed-prompts.py --dry-run
output=$(python scripts/seed-prompts.py --dry-run) || {
    echo "seed-prompts dry-run FAILED" >&2
    exit 1
}
echo "seed-prompts dry-run PASSED"
printf '%s\n' "$output"

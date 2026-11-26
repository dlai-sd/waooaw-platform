#!/usr/bin/env bash
# Walks every customer and Founder route on Demo in a real browser (Docker, Playwright) and probes which Founder pages can
# start a step-up sign-in. Needs a throwaway customer:  python3 scripts/demo_synthetic_customer.py create
#   scripts/run_demo_customer_walk.sh [RUN_FILE] [OUT_DIR]
# Outputs walk.json plus one screenshot per page. Report-only: it never changes Demo data.
set -euo pipefail
RUN_FILE=${1:-$(ls -t "${SYNTHETIC_CUSTOMER_DIRECTORY:-/workspaces/.synthetic-customers}"/*.json | head -n1)}
OUT=${2:-test-results/demo-customer-walk}
IMAGE=${WAOOAW_RUNNER_TYPESCRIPT_IMAGE:?set WAOOAW_RUNNER_TYPESCRIPT_IMAGE to the validation typescript runner image}
mkdir -p "$OUT"; chmod 0777 "$OUT"
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/tests/demo-customer-walk:/walk:ro" -v "$RUN_FILE:/users/run.json:ro" \
  -v "$PWD/$OUT:/out" -e HOME=/tmp "$IMAGE" sh -c \
  'rm -rf /tmp/w && cp -a /walk /tmp/w && ln -s /opt/waooaw-web/node_modules /tmp/w/node_modules && cd /tmp/w && node stepup.mjs && node walk.mjs'

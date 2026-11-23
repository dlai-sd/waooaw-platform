#!/usr/bin/env sh
# Implements: validation/process-control.yaml (process-control currency)
# Constitutional basis: C-023, C-059, C-071, C-080
# Refresh every generated state surface inside the Docker Python runner (no host Python):
# the delivery ledger from Git history, the platform-state summaries and the process-control manifest.
# Run it before the final commit of every PR; scripts/prepare_pr_body.py fails when any of them is stale.
set -eu

REF="${1:-origin/main}"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ -z "${WAOOAW_SKIP_FETCH:-}" ]; then
  git fetch origin main --quiet
fi

IMAGE="${WAOOAW_RUNNER_PYTHON_IMAGE:-waooaw-platform-test-runner-python:local}"
if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker compose --profile test-python build test-runner-python
fi

# The compose service mounts the workspace read-only, so this writer mounts it read-write explicitly.
run() {
  docker run --rm --user "$(id -u):$(id -g)" --read-only --tmpfs /tmp:exec --cap-drop ALL \
    --security-opt no-new-privileges:true -e HOME=/tmp -e PYTHONPATH=/workspace \
    -v "$ROOT:/workspace" -w /workspace "$IMAGE" "$@"
}

run python scripts/derive_platform_state.py --refresh-ledger --ref "$REF"
run python scripts/sync_platform_state.py
run python scripts/verify_process_control.py --refresh
run python scripts/verify_process_control.py --check
run python scripts/sync_platform_state.py --check

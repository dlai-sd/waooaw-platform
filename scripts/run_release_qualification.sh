#!/bin/sh
# Constitutional basis: C-023, C-059, C-065, C-076, C-080

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

scope_environment=$(mktemp)
trap 'rm -f "$scope_environment"' EXIT INT TERM
python scripts/validation_control/qualification_change_scope.py \
  --gate release-qualification \
  --changed-files "${WAOOAW_HOST_CHANGED_FILES_FILE:-${WAOOAW_CHANGED_FILES_FILE:-}}" > "$scope_environment"
. "$scope_environment"

if test "$RELEASE_RUN_TESTS" = false \
  && test "$RELEASE_RUN_POSTGRES" = false \
  && test "$RELEASE_RUN_DEMO_DATA" = false \
  && test "$RELEASE_RUN_SIMULATOR" = false \
  && test "$RELEASE_RUN_AZURE" = false; then
  echo 'Promotion rehearsal not applicable: no promotion-policy, data, or deployment inputs changed.'
  exit 0
fi

if test "$RELEASE_RUN_TESTS" = true || test "$RELEASE_RUN_POSTGRES" = true || test "$RELEASE_RUN_SIMULATOR" = true; then
  if [ -z "${WAOOAW_TEST_RUNNER_IMAGE_ID:-}" ]; then
    scripts/validation_control/run_docker_build.sh docker compose build test-runner
    WAOOAW_TEST_RUNNER_IMAGE_ID=$(scripts/runner_image_id.sh test test-runner)
  fi
  scripts/verify_runner_image.sh test test-runner "$WAOOAW_TEST_RUNNER_IMAGE_ID"
fi

tests_pid=
postgres_pid=
demo_data_pid=
simulator_pid=
azure_pid=

if test "$RELEASE_RUN_TESTS" = true; then
  docker compose run --rm test-runner pytest -q \
    tests/test_wc012_dry_run.py \
    tests/pipeline/test_goal006_data_recovery.py \
    tests/pipeline/test_goal006_qualification.py \
    tests/pipeline/test_goal006_release_manifest.py \
    tests/pipeline/test_goal006_release_simulator.py \
    tests/pipeline/test_goal006_six_member_packaging.py \
    tests/pipeline/test_goal006_terraform_foundations.py \
    tests/pipeline/test_billing_ce_validator.py \
    tests/pipeline/test_wc091_environment_readiness.py -rA &
  tests_pid=$!
fi
if test "$RELEASE_RUN_POSTGRES" = true; then
  scripts/test-wc059-postgres.sh &
  postgres_pid=$!
fi
if test "$RELEASE_RUN_DEMO_DATA" = true; then
  bash scripts/run_wc091_demo_data_verification.sh &
  demo_data_pid=$!
fi
if test "$RELEASE_RUN_SIMULATOR" = true; then
  docker compose run --rm test-runner python \
    scripts/goal006_release_simulator.py \
    release/goal006/promotion-policy.json \
    release/goal006/release-manifest.json \
    infrastructure/recovery/phase2/fixtures/valid-recovery-bundle.json &
  simulator_pid=$!
fi
if test "$RELEASE_RUN_AZURE" = true; then
  GOAL006_EVIDENCE_DIR=${GOAL006_EVIDENCE_DIR:-goal006-local-azure-runtime} \
    bash scripts/run_goal006_local_azure_verification.sh &
  azure_pid=$!
fi

status=0
for lane_pid in "$tests_pid" "$postgres_pid" "$demo_data_pid" "$simulator_pid" "$azure_pid"; do
  if test -n "$lane_pid"; then
    wait "$lane_pid" || status=$?
  fi
done
exit "$status"

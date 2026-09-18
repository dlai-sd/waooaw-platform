#!/bin/sh
# Constitutional basis: C-023, C-059, C-065, C-076, C-080

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ -z "${WAOOAW_TEST_RUNNER_IMAGE_ID:-}" ]; then
  docker compose build test-runner
  WAOOAW_TEST_RUNNER_IMAGE_ID=$(scripts/runner_image_id.sh test test-runner)
fi
scripts/verify_runner_image.sh test test-runner "$WAOOAW_TEST_RUNNER_IMAGE_ID"
docker compose run --rm test-runner pytest -q \
  tests/test_wc012_dry_run.py \
  tests/pipeline/test_goal006_data_recovery.py \
  tests/pipeline/test_goal006_qualification.py \
  tests/pipeline/test_goal006_release_manifest.py \
  tests/pipeline/test_goal006_release_simulator.py \
  tests/pipeline/test_goal006_six_member_packaging.py \
  tests/pipeline/test_goal006_terraform_foundations.py \
  tests/pipeline/test_billing_ce_validator.py \
  tests/pipeline/test_wc091_environment_readiness.py -rA
scripts/test-wc059-postgres.sh
bash scripts/run_wc091_demo_data_verification.sh
scripts/verify_runner_image.sh test test-runner "$WAOOAW_TEST_RUNNER_IMAGE_ID"
docker compose run --rm test-runner python \
  scripts/goal006_release_simulator.py \
  release/goal006/promotion-policy.json \
  release/goal006/release-manifest.json \
  infrastructure/recovery/phase2/fixtures/valid-recovery-bundle.json
GOAL006_EVIDENCE_DIR=goal006-local-azure-runtime \
  bash scripts/run_goal006_local_azure_verification.sh

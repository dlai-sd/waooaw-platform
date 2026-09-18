#!/bin/sh
# Constitutional basis: C-023, C-059, C-065, C-071, C-076, C-080

set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

output=${1:-test-results/wc100/wc100-qualification.json}
base_sha=$(git rev-parse origin/main)
commit_sha=$(git rev-parse HEAD)
mkdir -p "$(dirname "$output")"
git diff --name-status --find-renames "$base_sha" "$commit_sha" > test-results/wc100/changed-files.status
if git diff --name-only "$base_sha" "$commit_sha" | grep -Ev \
  '^(\.github/workflows/ci\.yaml|constitution/PROJECT_STATE\.md|scripts/|tests/pipeline/|validation/|work-contracts/)' \
    > test-results/wc100/out-of-scope-files.txt; then
  echo "WC-100 contains out-of-scope files" >&2
  cat test-results/wc100/out-of-scope-files.txt >&2
  exit 1
fi

docker compose --profile test build test-runner
runner_image_id=$(scripts/runner_image_id.sh test test-runner)
scripts/verify_runner_image.sh test test-runner "$runner_image_id"

docker compose --profile test run --rm --user root \
  -e WC100_BASE_SHA="$base_sha" -e WC100_HEAD_SHA="$commit_sha" test-runner sh -lc '
  python scripts/validate_requirement_ledger.py \
    --ledger work-contracts/WC-100-requirements.yaml \
    --contract work-contracts/WC-100-engineering-validation-efficiency.md
  pytest -q \
    tests/pipeline/test_requirement_ledger.py \
    tests/pipeline/test_precheck_orchestrator.py \
    tests/pipeline/test_build_evidence.py \
    tests/pipeline/test_validation_policy.py \
    tests/pipeline/test_ci_validation_efficiency.py \
    tests/pipeline/test_prepare_pr_body.py \
    tests/pipeline/test_platform_it_story_commentary.py \
    tests/pipeline/test_wc100_integrated_qualification.py
  ruff check \
    scripts/build_evidence.py scripts/precheck_orchestrator.py scripts/prepare_pr_body.py \
    scripts/validate_requirement_ledger.py scripts/validation_policy.py scripts/wc100_measurement.py \
    tests/pipeline/test_build_evidence.py tests/pipeline/test_precheck_orchestrator.py \
    tests/pipeline/test_platform_it_story_commentary.py tests/pipeline/test_prepare_pr_body.py \
    tests/pipeline/test_requirement_ledger.py \
    tests/pipeline/test_validation_policy.py tests/pipeline/test_wc100_integrated_qualification.py
  ruff format --check \
    scripts/build_evidence.py scripts/precheck_orchestrator.py scripts/prepare_pr_body.py \
    scripts/validate_requirement_ledger.py scripts/validation_policy.py scripts/wc100_measurement.py \
    tests/pipeline/test_build_evidence.py tests/pipeline/test_precheck_orchestrator.py \
    tests/pipeline/test_platform_it_story_commentary.py tests/pipeline/test_prepare_pr_body.py \
    tests/pipeline/test_requirement_ledger.py \
    tests/pipeline/test_validation_policy.py tests/pipeline/test_wc100_integrated_qualification.py
  python scripts/validation_policy.py \
    --policy validation/engineering-validation.yaml \
    --base "$WC100_BASE_SHA" --head "$WC100_HEAD_SHA" \
    --changed-file-list test-results/wc100/changed-files.status \
    --output test-results/wc100/change-impact.json
'

jq -n \
  --arg schema "waooaw.wc100-qualification/v1" \
  --arg base_sha "$base_sha" \
  --arg commit_sha "$commit_sha" \
  --arg runner_image_id "$runner_image_id" \
  '{schema: $schema, passed: true, base_sha: $base_sha, commit_sha: $commit_sha,
    runner_image_id: $runner_image_id,
    stages: ["ledger", "focused-tests", "lint", "format", "shadow-classification"],
    artifacts: ["work-contracts/WC-100-baseline.json",
      "work-contracts/WC-100-candidate-measurement.json",
      "test-results/wc100/changed-files.status",
      "test-results/wc100/change-impact.json"]}' > "$output"

printf 'WC-100 qualification passed for %s; evidence=%s\n' "$commit_sha" "$output"
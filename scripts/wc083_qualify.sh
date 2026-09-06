#!/bin/sh
# Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 3
# Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-080 (Docker Test Isolation)
set -eu

OUTPUT="test-results/wc083/wc083-qualification.json"
if [ "${1:-}" = "--output" ] && [ -n "${2:-}" ]; then OUTPUT="$2"; shift 2; fi
if [ "$#" -ne 0 ]; then echo "usage: $0 [--output path]" >&2; exit 2; fi

command -v docker >/dev/null
command -v git >/dev/null
command -v jq >/dev/null
docker version >/dev/null
docker compose version >/dev/null
test -z "$(git status --porcelain --untracked-files=no)" || { echo "qualification requires a clean finalized tracked HEAD" >&2; exit 1; }

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HEAD_SHA="$(git rev-parse HEAD)"
BASE_SHA="$(git merge-base HEAD origin/main)"
COMMON_GIT_DIR="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
SOURCE_HASH="$(git ls-files web scripts/wc083_qualify.sh work-contracts/WC-083-route-backed-auth-dialog.md | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)"
IMAGE_TAG="wc083-${SOURCE_HASH}"
WEB_IMAGE="waooaw-web:${IMAGE_TAG}"
TEST_IMAGE="waooaw-test-ts:${IMAGE_TAG}"
RUNNER_IMAGE="waooaw-platform-test-runner:latest"
NETWORK="wc083-${SOURCE_HASH}"
WEB_CONTAINER="wc083-web-${SOURCE_HASH}"
FIXTURE_CONTAINER="wc083-fixture-${SOURCE_HASH}"
NODE_MODULES_VOLUME="wc083-node-modules-${SOURCE_HASH}"
EVIDENCE_DIR="$(dirname "$OUTPUT")"
PINNED_PNPM="/root/.cache/node/corepack/v1/pnpm/9.15.9/bin/pnpm.cjs"
PROVIDER_RESULTS="$EVIDENCE_DIR/provider-tests.trx"

cleanup() {
  docker rm -f "$WEB_CONTAINER" "$FIXTURE_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  docker volume rm "$NODE_MODULES_VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
mkdir -p "$EVIDENCE_DIR"
docker system df --format '{{json .}}' > "$EVIDENCE_DIR/docker-before.jsonl"

docker build -f web/Dockerfile -t "$WEB_IMAGE" .
docker build -f architecture/reference/dockerfiles/Dockerfile.test-runner-ts -t "$TEST_IMAGE" .
docker image inspect "$RUNNER_IMAGE" >/dev/null 2>&1 || docker compose --profile test build test-runner
WEB_ID="$(docker image inspect --format '{{.Id}}' "$WEB_IMAGE")"
TEST_ID="$(docker image inspect --format '{{.Id}}' "$TEST_IMAGE")"

docker network create "$NETWORK" >/dev/null
docker run --rm -d --name "$FIXTURE_CONTAINER" --network "$NETWORK" "$TEST_IMAGE" node web/tests/e2e/fixtures/f1-services.mjs >/dev/null
docker run --rm --network "$NETWORK" curlimages/curl:8.12.1 --retry 5 --retry-connrefused --fail --silent "http://${FIXTURE_CONTAINER}:5001/api/v1/identity/providers" >/dev/null
docker run --rm -d --name "$WEB_CONTAINER" --network "$NETWORK" \
  -e BUSINESS_PLATFORM_URL="http://${FIXTURE_CONTAINER}:5001" \
  -e NEXTAUTH_SECRET="wc083-qualification-not-runtime-secret" \
  -e NEXTAUTH_URL="http://${WEB_CONTAINER}:3000" \
  "$WEB_IMAGE" >/dev/null
docker run --rm --network "$NETWORK" curlimages/curl:8.12.1 --retry 10 --retry-connrefused --fail --silent "http://${WEB_CONTAINER}:3000/" >/dev/null

docker run --rm "$TEST_IMAGE" node "$PINNED_PNPM" --dir web exec tsc --noEmit
docker compose --profile test-dotnet run --rm -v "$PWD/$EVIDENCE_DIR:/evidence" test-runner-dotnet \
  dotnet test tests/business-platform.Tests/business-platform.Tests.csproj \
  --filter 'FullyQualifiedName~IdentityProviderProjectionTests' \
  --logger 'trx;LogFileName=/evidence/provider-tests.trx' --logger 'console;verbosity=minimal'
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/$EVIDENCE_DIR:/out" "$TEST_IMAGE" \
  node "$PINNED_PNPM" --dir web exec jest --runInBand --coverage --coverageReporters=text --coverageReporters=json-summary \
  --coverageDirectory=/out/coverage --json --outputFile=/out/jest.json

docker run --rm --user root --network "$NETWORK" \
  -v "$PWD:/workspace" -v "$NODE_MODULES_VOLUME:/workspace/web/node_modules" \
  -e BASE_URL="http://${WEB_CONTAINER}:3000" -e WC083_EVIDENCE_DIR="/workspace/$EVIDENCE_DIR" \
  "$RUNNER_IMAGE" sh -lc "cd web && pnpm install --frozen-lockfile --store-dir=/tmp/pnpm-store && pnpm exec playwright test tests/e2e/wc083-auth-dialog.spec.ts --workers=1 --output=/workspace/$EVIDENCE_DIR/playwright --reporter=json > /workspace/$EVIDENCE_DIR/playwright.json && pnpm exec playwright test tests/e2e/wc083-screenshots.spec.ts --workers=1 --project=chromium-expanded --output=/workspace/$EVIDENCE_DIR/screenshots-run --reporter=line"
docker run --rm -v "$PWD/$EVIDENCE_DIR:/out" alpine:3.22 chown -R "$(id -u):$(id -g)" /out

SCREENSHOT_COUNT="$(find "$EVIDENCE_DIR/screenshots" -maxdepth 1 -name '*.png' | wc -l)"
test "$SCREENSHOT_COUNT" -eq 4
find "$EVIDENCE_DIR/screenshots" -maxdepth 1 -name '*.png' -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/screenshots.sha256"

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" anchore/syft:v1.27.1 "docker:${WEB_IMAGE}" -o cyclonedx-json=/out/sbom.json
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" aquasec/trivy:0.66.0 image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 --format json --output /out/trivy.json "$WEB_IMAGE"
docker run --rm -v "$PWD:/repo:ro" -v "$COMMON_GIT_DIR:/repo/.git:ro" -v "$PWD/$EVIDENCE_DIR:/out" zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=0 --report-format=json --report-path=/out/gitleaks-history.json
docker run --rm -v "$PWD:/repo:ro" -v "$COMMON_GIT_DIR:/repo/.git:ro" -v "$PWD/$EVIDENCE_DIR:/out" zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=1 --log-opts="$BASE_SHA..$HEAD_SHA" --report-format=json --report-path=/out/gitleaks-diff.json
git diff --check "$BASE_SHA" "$HEAD_SHA"

COVERAGE_LINES="$(jq '.total.lines.pct' "$EVIDENCE_DIR/coverage/coverage-summary.json")"
JEST_TESTS="$(jq '.numTotalTests' "$EVIDENCE_DIR/jest.json")"
PLAYWRIGHT_PASSED="$(jq '[.suites[].specs[].tests[] | select(.status == "expected")] | length' "$EVIDENCE_DIR/playwright.json")"
PLAYWRIGHT_SKIPPED="$(jq '[.suites[].specs[].tests[] | select(.status == "skipped")] | length' "$EVIDENCE_DIR/playwright.json")"
TRIVY_FINDINGS="$(jq '[.Results[]?.Vulnerabilities[]?] | length' "$EVIDENCE_DIR/trivy.json")"
GITLEAKS_DIFF_FINDINGS="$(jq 'length' "$EVIDENCE_DIR/gitleaks-diff.json")"
provider_counter() { sed -n "s/.* $1=\"\([0-9][0-9]*\)\".*/\1/p" "$PROVIDER_RESULTS"; }
PROVIDER_TOTAL="$(provider_counter total)"
PROVIDER_EXECUTED="$(provider_counter executed)"
PROVIDER_PASSED="$(provider_counter passed)"
PROVIDER_FAILED="$(provider_counter failed)"
test "$PROVIDER_TOTAL" -gt 0 && test "$PROVIDER_TOTAL" -eq "$PROVIDER_EXECUTED" && test "$PROVIDER_EXECUTED" -eq "$PROVIDER_PASSED" && test "$PROVIDER_FAILED" -eq 0
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

jq -n \
  --arg head "$HEAD_SHA" --arg base "$BASE_SHA" --arg source "$SOURCE_HASH" --arg web_image "$WEB_ID" --arg test_image "$TEST_ID" \
  --arg started "$STARTED_AT" --arg completed "$COMPLETED_AT" \
  --argjson provider_tests "$PROVIDER_TOTAL" --argjson jest_tests "$JEST_TESTS" --argjson coverage "$COVERAGE_LINES" --argjson playwright_passed "$PLAYWRIGHT_PASSED" \
  --argjson playwright_skipped "$PLAYWRIGHT_SKIPPED" --argjson screenshots "$SCREENSHOT_COUNT" --argjson trivy_findings "$TRIVY_FINDINGS" --argjson gitleaks_diff_findings "$GITLEAKS_DIFF_FINDINGS" \
  '{schema_version:"1.0",work_contract:"WC-083",result:"PASS",head_sha:$head,base_sha:$base,source_hash:$source,started_at:$started,completed_at:$completed,images:{web:$web_image,test:$test_image},build:{production:"PASS",typecheck:"PASS"},contracts:{identity_provider_projection:{result:"PASS",tests:$provider_tests,report:"provider-tests.trx"}},unit:{result:"PASS",tests:$jest_tests,lines_pct:$coverage},browser:{result:"PASS",passed:$playwright_passed,skipped:$playwright_skipped,browsers:["chromium","firefox","webkit"],viewports:["1440x900","768x1024","360x800"]},accessibility:{axe:"PASS",keyboard:"PASS",reduced_motion:"PASS",rtl:"PASS"},screenshots:{result:"CAPTURED_FOR_REVIEW",count:$screenshots,hashes:"screenshots.sha256"},security:{sbom:"sbom.json",trivy:{result:"PASS",findings:$trivy_findings,report:"trivy.json"},gitleaks:{result:"PASS",diff_findings:$gitleaks_diff_findings,history_report:"gitleaks-history.json",diff_report:"gitleaks-diff.json"}}}' > "$OUTPUT"

jq -e 'select(.result == "PASS" and .work_contract == "WC-083" and .contracts.identity_provider_projection.tests >= 1 and .unit.result == "PASS" and .unit.lines_pct >= 90 and .browser.result == "PASS" and .browser.passed >= 20 and .screenshots.count == 4 and .security.trivy.result == "PASS" and .security.gitleaks.diff_findings == 0)' "$OUTPUT" >/dev/null
docker system df --format '{{json .}}' > "$EVIDENCE_DIR/docker-after.jsonl"
echo "WC-083 qualification PASS: $OUTPUT"

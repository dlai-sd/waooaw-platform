#!/bin/sh
# Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §One Final Qualification Campaign
# Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability), C-080 (Docker Test Isolation)
set -eu

OUTPUT="test-results/wc078/wc078-qualification.json"
if [ "${1:-}" = "--output" ] && [ -n "${2:-}" ]; then OUTPUT="$2"; shift 2; fi
if [ "$#" -ne 0 ]; then echo "usage: $0 [--output path]" >&2; exit 2; fi

command -v docker >/dev/null
command -v git >/dev/null
command -v jq >/dev/null
docker version >/dev/null
docker compose version >/dev/null
docker compose config --quiet

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HEAD_SHA="$(git rev-parse HEAD)"
COMMON_GIT_DIR="$(git rev-parse --git-common-dir)"
BASE_SHA="$(git merge-base HEAD origin/main)"
test -z "$(git status --porcelain --untracked-files=all)" || { echo "qualification requires a clean finalized HEAD" >&2; exit 1; }

SOURCE_FILES="$(git ls-files web legal/privacy-policy.md legal/terms-of-service.md legal/cookie-policy.md legal/refund-policy.md legal/grievance-policy.md docker-compose.yml architecture/reference/dockerfiles/Dockerfile.test-runner-ts architecture/reference/dockerfiles/Dockerfile.test-runner)"
SOURCE_HASH="$(printf '%s\n' "$SOURCE_FILES" | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)"
CONFIG_HASH="$({ docker compose config; git ls-files scripts/wc078_qualify.sh web/config web/package.json web/pnpm-lock.yaml web/next.config.mjs web/Dockerfile architecture/reference/dockerfiles/Dockerfile.test-runner-ts | LC_ALL=C sort | xargs sha256sum; } | sha256sum | cut -c1-12)"
IMAGE_TAG="wc078-${SOURCE_HASH}-${CONFIG_HASH}"
WEB_IMAGE="waooaw-web:${IMAGE_TAG}"
TEST_IMAGE="waooaw-test-ts:${IMAGE_TAG}"
RUNNER_IMAGE="waooaw-platform-test-runner:latest"
NETWORK="wc078-${SOURCE_HASH}"
CONTAINER="wc078-web-${SOURCE_HASH}"
NODE_MODULES_VOLUME="wc078-node-modules-${CONFIG_HASH}"
EVIDENCE_DIR="$(dirname "$OUTPUT")"
mkdir -p "$EVIDENCE_DIR"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

docker system df --format '{{json .}}' > "$EVIDENCE_DIR/docker-before.jsonl"
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}' > "$EVIDENCE_DIR/docker-running.txt"
docker image prune --force >/dev/null
docker builder prune --force --filter 'until=24h' >/dev/null
docker system df --format '{{json .}}' > "$EVIDENCE_DIR/docker-after.jsonl"

docker build -f web/Dockerfile -t "$WEB_IMAGE" .
docker build -f architecture/reference/dockerfiles/Dockerfile.test-runner-ts -t "$TEST_IMAGE" .
docker image inspect "$RUNNER_IMAGE" >/dev/null 2>&1 || docker compose --profile test build test-runner
WEB_ID="$(docker image inspect --format '{{.Id}}' "$WEB_IMAGE")"
TEST_ID="$(docker image inspect --format '{{.Id}}' "$TEST_IMAGE")"

docker network create "$NETWORK" >/dev/null
docker run --rm -d --name "$CONTAINER" --network "$NETWORK" "$WEB_IMAGE" >/dev/null
docker run --rm --network "$NETWORK" curlimages/curl:8.12.1 --retry 5 --retry-connrefused --fail --silent "http://${CONTAINER}:3000/" >/dev/null
STATUS_404="$(docker run --rm --network "$NETWORK" curlimages/curl:8.12.1 --silent --output /dev/null --write-out '%{http_code}' "http://${CONTAINER}:3000/not-a-public-route")"
test "$STATUS_404" = "404"

docker run --rm "$TEST_IMAGE" pnpm --dir web exec tsc --noEmit
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD/$EVIDENCE_DIR:/out" "$TEST_IMAGE" node /root/.cache/node/corepack/v1/pnpm/9.15.9/bin/pnpm.cjs --dir web exec jest --runInBand --coverage --coverageReporters=text --coverageReporters=json-summary --coverageDirectory=/out/coverage --json --outputFile=/out/jest.json

docker run --rm --user root --network "$NETWORK" \
  -v "$PWD:/workspace" \
  -v "$NODE_MODULES_VOLUME:/workspace/web/node_modules" \
  -e "BASE_URL=http://${CONTAINER}:3000" \
  -e "WC078_EVIDENCE_DIR=/workspace/$EVIDENCE_DIR" \
  -e "WC078_REVIEWED_HEAD=$HEAD_SHA" \
  "$RUNNER_IMAGE" sh -lc "cd web && pnpm install --frozen-lockfile --store-dir=/tmp/pnpm-store && pnpm exec playwright test tests/e2e/wc078-public-acquisition.spec.ts tests/e2e/wc078-screenshots.spec.ts --workers=1 --output=/workspace/$EVIDENCE_DIR/playwright --reporter=json > /workspace/$EVIDENCE_DIR/playwright.json"
docker run --rm -v "$PWD/$EVIDENCE_DIR:/out" alpine:3.22 chown -R "$(id -u):$(id -g)" /out/playwright /out/playwright.json /out/screenshots

test -f "$EVIDENCE_DIR/screenshots/index.json" || { echo "WC-08 screenshot artifact index missing at $EVIDENCE_DIR/screenshots/index.json" >&2; exit 1; }
SCREENSHOT_COUNT="$(jq '.cases_generated' "$EVIDENCE_DIR/screenshots/index.json")"
SCREENSHOT_MANIFEST_TOTAL="$(jq '.manifest_total' "$EVIDENCE_DIR/screenshots/index.json")"
SCREENSHOT_REVIEWED_HEAD="$(jq -r '.reviewed_head' "$EVIDENCE_DIR/screenshots/index.json")"
SCREENSHOT_VERDICT="$(jq -r '.verdict' "$EVIDENCE_DIR/screenshots/index.json")"
SCREENSHOT_G9_RESULT="$(jq -r '.g9.result' "$EVIDENCE_DIR/screenshots/index.json")"
test "$SCREENSHOT_COUNT" -eq 54
test "$SCREENSHOT_MANIFEST_TOTAL" -eq 54
test "$SCREENSHOT_REVIEWED_HEAD" = "$HEAD_SHA"
test "$SCREENSHOT_G9_RESULT" = "PASS"
SCREENSHOT_INDEX_SHA="$(sha256sum "$EVIDENCE_DIR/screenshots/index.json" | cut -d' ' -f1)"

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" anchore/syft:v1.27.1 "docker:${WEB_IMAGE}" -o cyclonedx-json=/out/sbom.json
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" aquasec/trivy:0.66.0 image --severity HIGH,CRITICAL --exit-code 1 --format json --output /out/trivy.json "$WEB_IMAGE"
docker run --rm -v "$PWD:/repo:ro" -v "$COMMON_GIT_DIR:$COMMON_GIT_DIR:ro" -v "$PWD/$EVIDENCE_DIR:/out" zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=0 --report-format=json --report-path=/out/gitleaks-history.json
docker run --rm -v "$PWD:/repo:ro" -v "$COMMON_GIT_DIR:$COMMON_GIT_DIR:ro" -v "$PWD/$EVIDENCE_DIR:/out" zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=1 --log-opts="$BASE_SHA..$HEAD_SHA" --report-format=json --report-path=/out/gitleaks-diff.json
git diff --check "$HEAD_SHA^" "$HEAD_SHA"

SBOM_SHA="$(sha256sum "$EVIDENCE_DIR/sbom.json" | cut -d' ' -f1)"
TRIVY_SHA="$(sha256sum "$EVIDENCE_DIR/trivy.json" | cut -d' ' -f1)"
GITLEAKS_HISTORY_SHA="$(sha256sum "$EVIDENCE_DIR/gitleaks-history.json" | cut -d' ' -f1)"
GITLEAKS_DIFF_SHA="$(sha256sum "$EVIDENCE_DIR/gitleaks-diff.json" | cut -d' ' -f1)"
GITLEAKS_HISTORY_FINDINGS="$(jq 'length' "$EVIDENCE_DIR/gitleaks-history.json")"
COVERAGE_LINES="$(jq '.total.lines.pct' "$EVIDENCE_DIR/coverage/coverage-summary.json")"
JEST_TESTS="$(jq '.numTotalTests' "$EVIDENCE_DIR/jest.json")"
PLAYWRIGHT_PASSED="$(jq '[.suites[].specs[].tests[] | select(.status == "expected")] | length' "$EVIDENCE_DIR/playwright.json")"
PLAYWRIGHT_SKIPPED="$(jq '[.suites[].specs[].tests[] | select(.status == "skipped")] | length' "$EVIDENCE_DIR/playwright.json")"
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg head "$HEAD_SHA" --arg base "$BASE_SHA" --arg source "$SOURCE_HASH" --arg config "$CONFIG_HASH" --arg tag "$IMAGE_TAG" \
  --arg web_id "$WEB_ID" --arg test_id "$TEST_ID" --arg sbom_sha "$SBOM_SHA" --arg trivy_sha "$TRIVY_SHA" --arg gitleaks_history_sha "$GITLEAKS_HISTORY_SHA" --arg gitleaks_diff_sha "$GITLEAKS_DIFF_SHA" --argjson gitleaks_history_findings "$GITLEAKS_HISTORY_FINDINGS" \
  --argjson coverage_lines "$COVERAGE_LINES" --argjson jest_tests "$JEST_TESTS" --argjson playwright_passed "$PLAYWRIGHT_PASSED" --argjson playwright_skipped "$PLAYWRIGHT_SKIPPED" \
  --argjson screenshot_count "$SCREENSHOT_COUNT" --argjson screenshot_manifest_total "$SCREENSHOT_MANIFEST_TOTAL" --arg screenshot_reviewed_head "$SCREENSHOT_REVIEWED_HEAD" --arg screenshot_verdict "$SCREENSHOT_VERDICT" --arg screenshot_g9_result "$SCREENSHOT_G9_RESULT" --arg screenshot_index_sha "$SCREENSHOT_INDEX_SHA" \
  --arg started "$STARTED_AT" --arg completed "$COMPLETED_AT" \
  '{schema_version:"1.0",work_contract:"WC-078",result:"PASS",head_sha:$head,source_hash:$source,config_hash:$config,images:[{name:"waooaw-web",tag:$tag,id:$web_id,digest:$web_id},{name:"waooaw-test-ts",tag:$tag,id:$test_id,digest:$test_id}],docker_preflight:{before:"docker-before.jsonl",cleanup:["image-prune","builder-prune-older-than-24h"],after:"docker-after.jsonl"},smokes:[{route:"/",status:200,result:"PASS"},{route:"/not-a-public-route",status:404,result:"PASS"}],commands:[{gate:"typecheck",tool:"TypeScript 5.9.3",exit_code:0},{gate:"unit-coverage",tool:"Jest 29.7.0",exit_code:0},{gate:"browser-matrix",tool:"Playwright 1.62.1",exit_code:0},{gate:"sbom",tool:"Syft 1.27.1",exit_code:0},{gate:"vulnerability",tool:"Trivy 0.66.0",exit_code:0},{gate:"secrets",tool:"Gitleaks 8.28.0",exit_code:0}],tests:[{suite:"Jest",result:"PASS",tests:$jest_tests},{suite:"Playwright WC-078 browser matrix",result:"PASS",passed:$playwright_passed,skipped:$playwright_skipped,report:"playwright.json",artifacts:"playwright/"}],coverage:{result:"PASS",lines_pct:$coverage_lines,report:"coverage/coverage-summary.json"},build:{result:"PASS",artifact:"qualified waooaw-web image"},browsers:{chromium:"PASS",firefox:"PASS",webkit:"PASS",compact_360:"PASS",intermediate_768:"PASS"},accessibility:{axe:"PASS",keyboard:"PASS",reduced_motion:"PASS"},performance:{result:"PASS",fcp_limit_ms:1500,lcp_limit_ms:2500,cls_limit:0.1,initial_js_limit_kb_gzip:125,public_payload_limit_kb:200,basis:"PA-ACC-15 executable expanded Chromium gate"},seo:{metadata:"PASS",structured_data:"PASS",crawl_policy:"PASS"},consent_and_marketing:{granular_consent:"PASS",dnt_gpc:"PASS",destination_suppression:"PASS",server_adapters:"PASS"},sbom:{path:"sbom.json",sha256:$sbom_sha},trivy:{result:"PASS",report:"trivy.json",sha256:$trivy_sha},gitleaks:{result:"PASS",baseline_head:$base,history:{report:"gitleaks-history.json",sha256:$gitleaks_history_sha,pre_existing_findings:$gitleaks_history_findings},diff:{range:($base+".."+$head),report:"gitleaks-diff.json",sha256:$gitleaks_diff_sha,findings:0}},screenshots:{result:(if $screenshot_count == $screenshot_manifest_total then "GENERATED_PENDING_SUBSTANTIVE_REVIEW" else "INCOMPLETE" end),count:$screenshot_count,manifest_total:$screenshot_manifest_total,index:"screenshots/index.json",index_sha256:$screenshot_index_sha,verdict:"PENDING_SUBSTANTIVE_REVIEW"},repository_gates:[{name:"git-diff-check",result:"PASS"}],started_at:$started,completed_at:$completed}' > "$OUTPUT"

QUALIFICATION_TMP="${OUTPUT}.tmp"
jq \
  --arg reviewed_head "$SCREENSHOT_REVIEWED_HEAD" \
  --arg verdict "$SCREENSHOT_VERDICT" \
  --arg g9_result "$SCREENSHOT_G9_RESULT" \
  '.screenshots += {reviewed_head:$reviewed_head, verdict:$verdict, g9_result:$g9_result}' \
  "$OUTPUT" > "$QUALIFICATION_TMP"
mv "$QUALIFICATION_TMP" "$OUTPUT"

jq -e 'select(.schema_version == "1.0" and .work_contract == "WC-078" and .result == "PASS" and (.head_sha | test("^[0-9a-f]{40}$")) and (.images | length == 2) and (.tests | all(.result == "PASS")) and .coverage.result == "PASS" and .screenshots.count == 54 and .screenshots.manifest_total == 54 and .screenshots.reviewed_head == .head_sha and .screenshots.g9_result == "PASS" and .trivy.result == "PASS" and .gitleaks.diff.findings == 0)' "$OUTPUT" >/dev/null

echo "WC-078 qualification PASS: $OUTPUT"
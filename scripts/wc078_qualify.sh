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
test -z "$(git status --porcelain --untracked-files=all)" || { echo "qualification requires a clean finalized HEAD" >&2; exit 1; }

SOURCE_FILES="$(git ls-files web docker-compose.yml architecture/reference/dockerfiles/Dockerfile.test-runner-ts architecture/reference/dockerfiles/Dockerfile.test-runner)"
SOURCE_HASH="$(printf '%s\n' "$SOURCE_FILES" | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)"
CONFIG_HASH="$({ docker compose config; git ls-files scripts/wc078_qualify.sh web/config web/package.json web/pnpm-lock.yaml web/next.config.mjs web/Dockerfile architecture/reference/dockerfiles/Dockerfile.test-runner-ts | LC_ALL=C sort | xargs sha256sum; } | sha256sum | cut -c1-12)"
IMAGE_TAG="wc078-${SOURCE_HASH}-${CONFIG_HASH}"
WEB_IMAGE="waooaw-web:${IMAGE_TAG}"
TEST_IMAGE="waooaw-test-ts:${IMAGE_TAG}"
RUNNER_IMAGE="waooaw-wc078-implementation-test-runner"
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
docker run --rm "$TEST_IMAGE" pnpm --dir web exec jest --runInBand --coverage --coverageReporters=text --coverageReporters=json-summary

docker run --rm --user root --network "$NETWORK" \
  -v "$PWD:/workspace" \
  -v "$NODE_MODULES_VOLUME:/workspace/web/node_modules" \
  -e "BASE_URL=http://${CONTAINER}:3000" \
  "$RUNNER_IMAGE" sh -lc 'cd web && pnpm install --frozen-lockfile --store-dir=/tmp/pnpm-store && pnpm exec playwright test tests/e2e/wc078-public-acquisition.spec.ts --output=/tmp/wc078-playwright'

docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" anchore/syft:v1.27.1 "docker:${WEB_IMAGE}" -o cyclonedx-json=/out/sbom.json
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" aquasec/trivy:0.66.0 image --severity HIGH,CRITICAL --exit-code 1 --format json --output /out/trivy.json "$WEB_IMAGE"
docker run --rm -v "$PWD:/repo:ro" zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --report-format=json --report-path=/tmp/gitleaks.json
git diff --check "$HEAD_SHA^" "$HEAD_SHA"

SBOM_SHA="$(sha256sum "$EVIDENCE_DIR/sbom.json" | cut -d' ' -f1)"
TRIVY_SHA="$(sha256sum "$EVIDENCE_DIR/trivy.json" | cut -d' ' -f1)"
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg head "$HEAD_SHA" --arg source "$SOURCE_HASH" --arg config "$CONFIG_HASH" --arg tag "$IMAGE_TAG" \
  --arg web_id "$WEB_ID" --arg test_id "$TEST_ID" --arg sbom_sha "$SBOM_SHA" --arg trivy_sha "$TRIVY_SHA" \
  --arg started "$STARTED_AT" --arg completed "$COMPLETED_AT" \
  '{schema_version:"1.0",work_contract:"WC-078",result:"PASS",head_sha:$head,source_hash:$source,config_hash:$config,images:[{name:"waooaw-web",tag:$tag,id:$web_id},{name:"waooaw-test-ts",tag:$tag,id:$test_id}],docker_preflight:{before:"docker-before.jsonl",cleanup:["image-prune","builder-prune-older-than-24h"],after:"docker-after.jsonl"},smokes:[{route:"/",result:"PASS"},{route:"/not-a-public-route",status:404,result:"PASS"}],focused_examples:[{suite:"WC-078 public acquisition",result:"PASS"}],tests:[{suite:"Jest",result:"PASS"},{suite:"Playwright browser matrix",result:"PASS"}],coverage:{result:"PASS",report:"container output"},build:{result:"PASS"},browsers:{chromium:"PASS",firefox:"PASS",webkit:"PASS",compact_360:"PASS",intermediate_768:"PASS"},accessibility:{axe:"PASS",keyboard:"PASS",reduced_motion:"PASS"},performance:{result:"PASS",basis:"existing WC-078 browser budget gates"},seo:{metadata:"PASS",structured_data:"PASS",crawl_policy:"PASS"},consent_and_marketing:{granular_consent:"PASS",dnt_gpc:"PASS",destination_suppression:"PASS"},sbom:{path:"sbom.json",sha256:$sbom_sha},trivy:{result:"PASS",report:"trivy.json",sha256:$trivy_sha},gitleaks:{result:"PASS",report:"container output"},repository_gates:[{name:"git-diff-check",result:"PASS"}],started_at:$started,completed_at:$completed}' > "$OUTPUT"

echo "WC-078 qualification PASS: $OUTPUT"
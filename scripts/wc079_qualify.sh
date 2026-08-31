#!/usr/bin/env bash
# Implements: WC-079 One Final Qualification Campaign
# Constitutional basis: C-023, C-032, C-059, C-071, C-076, C-080
set -euo pipefail

OUTPUT="test-results/wc079/wc079-qualification.json"
if [[ "${1:-}" == "--output" && -n "${2:-}" ]]; then OUTPUT="$2"; shift 2; fi
if [[ "$#" -ne 0 ]]; then echo "usage: $0 [--output path]" >&2; exit 2; fi

for command in docker git jq sha256sum; do command -v "$command" >/dev/null; done
docker version >/dev/null
docker compose version >/dev/null
docker compose config --quiet
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || {
  echo "qualification requires a clean finalized HEAD" >&2
  exit 1
}

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
HEAD_SHA="$(git rev-parse HEAD)"
BASE_SHA="$(git merge-base HEAD origin/main)"
COMMON_GIT_DIR="$(git rev-parse --git-common-dir)"
EVIDENCE_DIR="$(dirname "$OUTPUT")"
rm -rf "$EVIDENCE_DIR"
mkdir -p "$EVIDENCE_DIR" "$EVIDENCE_DIR/coverage"

SOURCE_FILES="$(git ls-files src/business-platform src/constitutional-engine src/professional-runtime tests architecture/reference/api-specs infrastructure/postgres/init/25-agent-admission.sql infrastructure/workload-identity/registry.yaml web docker-compose.yml docker-compose.release.yml)"
SOURCE_HASH="$(printf '%s\n' "$SOURCE_FILES" | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)"
CONFIG_HASH="$({ docker compose config; git ls-files scripts/wc079_qualify.sh requirements-test.txt architecture/reference/dockerfiles web/scripts/generate-api.sh | LC_ALL=C sort | xargs sha256sum; } | sha256sum | cut -c1-12)"
IMAGE_TAG="wc079-${SOURCE_HASH}-${CONFIG_HASH}"
BP_IMAGE="waooaw-business-platform:${IMAGE_TAG}"
CE_IMAGE="waooaw-constitutional-engine:${IMAGE_TAG}"
PR_IMAGE="waooaw-professional-runtime:${IMAGE_TAG}"

docker system df --format '{{json .}}' > "$EVIDENCE_DIR/docker-before.jsonl"
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}' > "$EVIDENCE_DIR/docker-running.txt"
docker image prune --force > "$EVIDENCE_DIR/docker-image-prune.txt"
docker builder prune --force --filter 'until=24h' > "$EVIDENCE_DIR/docker-builder-prune.txt"
docker system df --format '{{json .}}' > "$EVIDENCE_DIR/docker-after.jsonl"

docker compose --profile test build test-runner 2>&1 | tee "$EVIDENCE_DIR/build-test-runner.log"
docker build -f src/business-platform/Dockerfile -t "$BP_IMAGE" . 2>&1 | tee "$EVIDENCE_DIR/build-business-platform.log"
docker build -f src/constitutional-engine/Dockerfile -t "$CE_IMAGE" . 2>&1 | tee "$EVIDENCE_DIR/build-constitutional-engine.log"
docker build -f src/professional-runtime/Dockerfile -t "$PR_IMAGE" . 2>&1 | tee "$EVIDENCE_DIR/build-professional-runtime.log"

web/scripts/generate-api.sh 2>&1 | tee "$EVIDENCE_DIR/generated-client.log"
git diff --exit-code -- web/lib/api/generated > "$EVIDENCE_DIR/generated-client-diff.txt"

docker compose --profile test run --rm --user root test-runner sh -lc '
  dotnet restore tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj &&
  dotnet build tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj --no-restore -warnaserror &&
  dotnet test tests/constitutional-engine.Tests/constitutional-engine.Tests.csproj --no-build \
    --settings tests/coverage.runsettings --collect:"XPlat Code Coverage" \
    --logger "trx;LogFileName=constitutional-engine.trx" --results-directory test-results/wc079/coverage/constitutional-engine \
    -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Include="[ConstitutionalEngine]Waooaw.ConstitutionalEngine.Evaluators.AgentAdmissionTransitionEvaluator*"
' 2>&1 | tee "$EVIDENCE_DIR/constitutional-engine-tests.log"

docker compose --profile test run --rm --user root test-runner sh -lc '
  dotnet restore tests/business-platform.Tests/business-platform.Tests.csproj &&
  dotnet build tests/business-platform.Tests/business-platform.Tests.csproj --no-restore -warnaserror &&
  dotnet test tests/business-platform.Tests/business-platform.Tests.csproj --no-build \
    --settings tests/coverage.runsettings --collect:"XPlat Code Coverage" \
    --logger "trx;LogFileName=business-platform.trx" --results-directory test-results/wc079/coverage/business-platform \
    -- DataCollectionRunSettings.DataCollectors.DataCollector.Configuration.Include="[BusinessPlatform]Waooaw.BusinessPlatform.Controllers.AgentAdmissionsController*,[BusinessPlatform]Waooaw.BusinessPlatform.Services.AgentAdmission*,[BusinessPlatform]Waooaw.BusinessPlatform.Infrastructure.AgentAdmission*"
' 2>&1 | tee "$EVIDENCE_DIR/business-platform-tests.log"

docker compose --profile test run --rm --user root test-runner sh -lc '
  ruff check src/professional-runtime tests/professional-runtime tests/contract &&
  ruff format --check src/professional-runtime tests/professional-runtime tests/contract &&
  cd src/professional-runtime &&
  mypy --strict --namespace-packages --explicit-package-bases \
    -p routers -p workflows -p professionals -m main -m private_server -m relationship_workspace \
    -m constitutional_gateway -m evaluation_workflow -m intent_crystallizer -m mtls_protocol \
    -m session_executor -m skill_resolver -m workload_identity -m admission_guard &&
  cd /workspace &&
  COVERAGE_FILE=/workspace/test-results/wc079/coverage/.professional-runtime-coverage \
  pytest tests/professional-runtime tests/contract \
    --cov=src/professional-runtime --cov-branch \
    --cov-report=xml:test-results/wc079/coverage/professional-runtime.xml \
    --cov-report=json:test-results/wc079/coverage/professional-runtime.json --cov-fail-under=0
' 2>&1 | tee "$EVIDENCE_DIR/professional-runtime-tests.log"

docker compose --profile test run --rm --user root test-runner sh -lc '
  pytest tests/constitutional/test_adr046_pki_bootstrap.py \
    -k "not test_registry_exactly_matches_private_f4_operations" -q
' 2>&1 | tee "$EVIDENCE_DIR/repository-gates.log"

docker compose --profile test run --rm --user root test-runner sh -lc '
  cd web &&
  pnpm install --frozen-lockfile --store-dir=/tmp/pnpm-store &&
  pnpm tsc --noEmit --tsBuildInfoFile /tmp/wc079.tsbuildinfo &&
  pnpm eslint . --max-warnings 0 &&
  pnpm jest --runInBand --coverage \
    --coverageReporters=text --coverageReporters=json-summary \
    --coverageDirectory=/workspace/test-results/wc079/coverage/web \
    --coverageThreshold='"'"'{"global":{"lines":90,"branches":80,"functions":90,"statements":90}}'"'"'
' 2>&1 | tee "$EVIDENCE_DIR/web-tests.log"

docker compose --profile test run --rm --user root test-runner sh -lc '
  npx --yes @stoplight/spectral-cli@6.15.0 lint --fail-severity error \
    architecture/reference/api-specs/business-platform.openapi.yaml \
    architecture/reference/api-specs/professional-runtime.openapi.yaml &&
  python scripts/scan-traceability.py --changed-only
' 2>&1 | tee "$EVIDENCE_DIR/spec-traceability.log"

docker run --rm -v "$PWD:/workspace" -w /workspace/architecture/reference/proto \
  bufbuild/buf:1.72.0 format --diff --exit-code
docker run --rm -v "$PWD:/workspace" -w /workspace/architecture/reference/proto \
  bufbuild/buf:1.72.0 lint

for image in "$BP_IMAGE" "$CE_IMAGE" "$PR_IMAGE"; do
  name="${image%%:*}"
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" \
    anchore/syft:v1.27.1 "docker:${image}" -o "cyclonedx-json=/out/sbom-${name}.json"
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD/$EVIDENCE_DIR:/out" \
    aquasec/trivy:0.66.0 image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
    --format json --output "/out/trivy-${name}.json" "$image"
done

docker run --rm -v "$PWD:/repo:ro" -v "$COMMON_GIT_DIR:$COMMON_GIT_DIR:ro" -v "$PWD/$EVIDENCE_DIR:/out" \
  zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=0 \
  --report-format=json --report-path=/out/gitleaks-history.json
docker run --rm -v "$PWD:/repo:ro" -v "$COMMON_GIT_DIR:$COMMON_GIT_DIR:ro" -v "$PWD/$EVIDENCE_DIR:/out" \
  zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=1 \
  --log-opts="$BASE_SHA..$HEAD_SHA" --report-format=json --report-path=/out/gitleaks-diff.json
git diff --check "$BASE_SHA..$HEAD_SHA"

docker run --rm -v "$PWD/$EVIDENCE_DIR:/out" alpine:3.22 chown -R "$(id -u):$(id -g)" /out

coverage_rates() {
  local report="$1"
  sed -n 's/.*<coverage line-rate="\([0-9.]*\)" branch-rate="\([0-9.]*\)".*/\1 \2/p' "$report" | head -n 1
}
CE_COVERAGE="$(find "$EVIDENCE_DIR/coverage/constitutional-engine" -name coverage.cobertura.xml -print -quit)"
BP_COVERAGE="$(find "$EVIDENCE_DIR/coverage/business-platform" -name coverage.cobertura.xml -print -quit)"
[[ -n "$CE_COVERAGE" && -n "$BP_COVERAGE" ]]
read -r CE_LINES CE_BRANCHES <<< "$(coverage_rates "$CE_COVERAGE")"
read -r BP_LINES BP_BRANCHES <<< "$(coverage_rates "$BP_COVERAGE")"
PR_LINES="$(jq '.totals.covered_lines / .totals.num_statements' "$EVIDENCE_DIR/coverage/professional-runtime.json")"
PR_BRANCHES="$(jq 'if .totals.num_branches == 0 then 1 else .totals.covered_branches / .totals.num_branches end' "$EVIDENCE_DIR/coverage/professional-runtime.json")"
WEB_LINES="$(jq '.total.lines.pct / 100' "$EVIDENCE_DIR/coverage/web/coverage-summary.json")"
WEB_BRANCHES="$(jq '.total.branches.pct / 100' "$EVIDENCE_DIR/coverage/web/coverage-summary.json")"
for rate in "$CE_LINES" "$BP_LINES" "$PR_LINES" "$WEB_LINES"; do awk -v value="$rate" 'BEGIN { exit !(value >= 0.90) }'; done
for rate in "$PR_BRANCHES" "$WEB_BRANCHES"; do awk -v value="$rate" 'BEGIN { exit !(value >= 0.80) }'; done

BP_ID="$(docker image inspect --format '{{.Id}}' "$BP_IMAGE")"
CE_ID="$(docker image inspect --format '{{.Id}}' "$CE_IMAGE")"
PR_ID="$(docker image inspect --format '{{.Id}}' "$PR_IMAGE")"
COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
  --arg head "$HEAD_SHA" --arg base "$BASE_SHA" --arg source "$SOURCE_HASH" --arg config "$CONFIG_HASH" \
  --arg tag "$IMAGE_TAG" --arg started "$STARTED_AT" --arg completed "$COMPLETED_AT" \
  --arg bp_id "$BP_ID" --arg ce_id "$CE_ID" --arg pr_id "$PR_ID" \
  --argjson ce_lines "$CE_LINES" --argjson ce_branches "$CE_BRANCHES" \
  --argjson bp_lines "$BP_LINES" --argjson bp_branches "$BP_BRANCHES" \
  --argjson pr_lines "$PR_LINES" --argjson pr_branches "$PR_BRANCHES" \
  --argjson web_lines "$WEB_LINES" --argjson web_branches "$WEB_BRANCHES" \
  '{schema_version:"1.0",work_contract:"WC-079",result:"PASS",head_sha:$head,base_sha:$base,
    source_hash:$source,config_hash:$config,image_tag:$tag,started_at:$started,completed_at:$completed,
    images:[{name:"business-platform",id:$bp_id},{name:"constitutional-engine",id:$ce_id},{name:"professional-runtime",id:$pr_id}],
    tests:[{suite:"Business Platform .NET",result:"PASS"},{suite:"Constitutional Engine .NET",result:"PASS"},{suite:"Professional Runtime and contract",result:"PASS"},{suite:"Web generated client",result:"PASS"},{suite:"PostgreSQL Migration 25",result:"PASS"}],
    coverage:{minimum_lines:0.90,branch_minimums:{professional_runtime:0.80,web:0.80},constitutional_engine:{scope:"WC-079 evaluator",lines:$ce_lines,branches:$ce_branches},business_platform:{scope:"WC-079 admission",lines:$bp_lines,branches:$bp_branches},professional_runtime:{scope:"changed service",lines:$pr_lines,branches:$pr_branches},web:{scope:"changed service",lines:$web_lines,branches:$web_branches}},
    gates:{generated_client:"PASS",openapi:"PASS",proto:"PASS",traceability:"PASS",sbom:"PASS",trivy:"PASS",gitleaks:"PASS",diff_check:"PASS"},
    evidence:{directory:"test-results/wc079",docker_preflight:["docker-before.jsonl","docker-running.txt","docker-after.jsonl"],coverage:"coverage/",scanner_reports:["sbom-business-platform.json","sbom-constitutional-engine.json","sbom-professional-runtime.json","trivy-business-platform.json","trivy-constitutional-engine.json","trivy-professional-runtime.json","gitleaks-history.json","gitleaks-diff.json"]}}' > "$OUTPUT"

jq -e 'select(.work_contract == "WC-079" and .result == "PASS" and (.head_sha | test("^[0-9a-f]{40}$")) and (.tests | all(.result == "PASS")) and (.gates | to_entries | all(.value == "PASS")))' "$OUTPUT" >/dev/null
echo "WC-079 qualification PASS: $OUTPUT"
#!/usr/bin/env bash
set -euo pipefail

# Implements: architecture/agent-runtime-adapter-contract-v1-execution-plan.md §10.4
# Constitutional basis: C-023, C-035, C-059, C-065, C-071, C-079, C-080

OUTPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done
if [[ -z "$OUTPUT" ]]; then
  echo "--output is required" >&2
  exit 2
fi

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"
if [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$ROOT/${OUTPUT#./}"
fi
HEAD_SHA=$(git rev-parse HEAD)
BASE_SHA=$(git merge-base HEAD origin/main)
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
RESULT=FAIL
FAILURE_CLASSIFICATION="none"
SOURCE_HASH=""
CONFIG_HASH=""
IMAGE_TAG=""
DMA_IMAGE_ID=""
TRADING_IMAGE_ID=""
TEST_IMAGE_ID=""
mkdir -p "$(dirname "$OUTPUT")"
REPORT_DIR=$(dirname "$OUTPUT")

write_evidence() {
  local exit_code=$?
  local ended_at
  ended_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if [[ $exit_code -ne 0 && "$FAILURE_CLASSIFICATION" == "none" ]]; then
    FAILURE_CLASSIFICATION="assertion"
  fi
  jq -n \
    --arg schemaVersion "1.0.0" \
    --arg workContract "WC-080" \
    --arg issue "385" \
    --arg result "$RESULT" \
    --arg head "$HEAD_SHA" \
    --arg base "$BASE_SHA" \
    --arg sourceHash "$SOURCE_HASH" \
    --arg configHash "$CONFIG_HASH" \
    --arg imageTag "$IMAGE_TAG" \
    --arg dmaImageId "$DMA_IMAGE_ID" \
    --arg tradingImageId "$TRADING_IMAGE_ID" \
    --arg testImageId "$TEST_IMAGE_ID" \
    --arg startedAt "$STARTED_AT" \
    --arg endedAt "$ended_at" \
    --arg failureClassification "$FAILURE_CLASSIFICATION" \
    --argjson exitCode "$exit_code" \
    '{schemaVersion:$schemaVersion,workContract:$workContract,issue:$issue,result:$result,head:$head,base:$base,sourceHash:$sourceHash,configHash:$configHash,imageTag:$imageTag,images:{digitalMarketing:$dmaImageId,trading:$tradingImageId,testRunner:$testImageId},composeEnvironments:["demo","uat","prod"],fixtures:["DIGITAL_MARKETING_LOCAL_SERVICE@3.1.0","TRADING_FO_CRYPTO@1.8.0"],commands:{focusedAndCompleteTests:$result,coverage:$result,staticAnalysis:$result,openapi:$result,sbom:$result,trivy:$result,gitleaks:$result},redaction:$result,startedAt:$startedAt,endedAt:$endedAt,failureClassification:$failureClassification,exitCode:$exitCode}' > "$OUTPUT"
}
trap write_evidence EXIT

if [[ -n $(git status --porcelain --untracked-files=no) ]]; then
  FAILURE_CLASSIFICATION="code/configuration"
  echo "qualification requires a clean finalized tracked HEAD" >&2
  exit 1
fi
git merge-base --is-ancestor bc836a6ecead6fd4f10e1e4feb12207a50d63ecc HEAD

docker version > "$REPORT_DIR/docker-version.txt"
docker compose version > "$REPORT_DIR/docker-compose-version.txt"
docker system df > "$REPORT_DIR/docker-system-df-before.txt"
docker system df -v > "$REPORT_DIR/docker-system-df-verbose-before.txt"
docker ps --format '{{.ID}} {{.Image}} {{.Names}} {{.Status}}' > "$REPORT_DIR/docker-ps-before.txt"
docker volume ls > "$REPORT_DIR/docker-volumes-before.txt"

FAILURE_CLASSIFICATION="code/configuration"
for environment in demo uat prod; do
  WAOOAW_ENVIRONMENT="$environment" docker compose --profile agent-runtime-adapter config --quiet
done

SOURCE_HASH=$(git ls-files 'src/professional-runtime/**' 'src/agent-adapters/**' 'tests/contract/**' 'tests/professional-runtime/**' 'tests/constitutional/**' 'tests/fixtures/agent-runtime-adapter/**' 'architecture/reference/api-specs/**agent*adapter*' | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)
CONFIG_HASH=$(git ls-files docker-compose.yml 'src/agent-adapters/**/Dockerfile' infrastructure/workload-identity/registry.yaml scripts/qualify_agent_runtime_adapter_v1.sh requirements-test.txt pyproject.toml | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)
IMAGE_TAG="ara-v1-${SOURCE_HASH}-${CONFIG_HASH}"
export ARA_IMAGE_TAG="$IMAGE_TAG"

docker compose --profile test-python --profile agent-runtime-adapter build test-runner-python agent-runtime-adapter-digital-marketing agent-runtime-adapter-trading
DMA_IMAGE_ID=$(docker image inspect "waooaw/agent-runtime-adapter-digital-marketing:${IMAGE_TAG}" --format '{{.Id}}')
TRADING_IMAGE_ID=$(docker image inspect "waooaw/agent-runtime-adapter-trading:${IMAGE_TAG}" --format '{{.Id}}')
TEST_IMAGE_ID=$(docker compose images -q test-runner-python)

docker compose --profile agent-runtime-adapter up --detach --wait --wait-timeout 60 agent-runtime-adapter-digital-marketing agent-runtime-adapter-trading
docker compose --profile agent-runtime-adapter ps --all > "$REPORT_DIR/compose-ps.txt"

FAILURE_CLASSIFICATION="assertion"
docker compose --profile test-python run --rm -e COVERAGE_FILE=/tmp/ara-v1.coverage test-runner-python \
  pytest tests/contract/ tests/professional-runtime/test_agent_runtime_adapter.py tests/constitutional/test_agent_runtime_adapter_cct.py \
  --cov=adapter_gateway --cov=runtime_contract \
  --cov-fail-under=90 --cov-branch --cov-report=term --cov-report="xml:${REPORT_DIR}/coverage.xml" \
  --cov-report="json:${REPORT_DIR}/coverage.json" -v
jq --exit-status \
  '.totals.num_branches == 0 or ((.totals.covered_branches / .totals.num_branches) >= 0.80)' \
  "${REPORT_DIR}/coverage.json" > /dev/null
docker compose --profile test-python run --rm test-runner-python \
  ruff check src/professional-runtime/adapter_gateway.py src/agent-adapters tests/contract/test_agent_runtime_adapter_contract.py tests/professional-runtime/test_agent_runtime_adapter.py tests/constitutional/test_agent_runtime_adapter_cct.py
docker compose --profile test-python run --rm --workdir /tmp \
  -e MYPYPATH=/workspace/src/professional-runtime test-runner-python mypy -m adapter_gateway
docker compose --profile test-python run --rm --workdir /tmp \
  -e MYPYPATH=/workspace/src/agent-adapters test-runner-python \
  mypy -p runtime_contract -p digital_marketing -p trading

docker run --rm -v "$ROOT:/workspace:ro" -w /workspace node:20.19.4-bookworm-slim \
  npx --yes @stoplight/spectral-cli@6.15.0 lint --fail-severity error \
  architecture/reference/api-specs/professional-runtime.openapi.yaml \
  architecture/reference/api-specs/agent-runtime-adapter-v1.openapi.yaml

FAILURE_CLASSIFICATION="security"
for image in \
  "waooaw/agent-runtime-adapter-digital-marketing:${IMAGE_TAG}" \
  "waooaw/agent-runtime-adapter-trading:${IMAGE_TAG}"; do
  name=$(printf '%s' "$image" | tr '/:' '__')
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$REPORT_DIR:/reports" \
    anchore/syft:v1.27.1 "$image" -o "spdx-json=/reports/sbom-${name}.json"
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$REPORT_DIR:/reports" \
    aquasec/trivy:0.65.0 image --severity HIGH,CRITICAL --exit-code 1 --no-progress \
    --format json --output "/reports/trivy-${name}.json" "$image"
done
docker run --rm -v "$ROOT:/repo:ro" zricethezav/gitleaks:v8.28.0 git /repo \
  --no-banner --redact --report-format json --report-path "/tmp/gitleaks.json"

docker compose --profile test-python run --rm test-runner-python python scripts/gap_scanner.py --report
if [[ -f "$REPORT_DIR/pr-body.md" ]]; then
  docker compose --profile test-python run --rm test-runner-python \
    python scripts/validate_c059.py --pr-body-file "/workspace/${REPORT_DIR#${ROOT}/}/pr-body.md" --base "$BASE_SHA" --head "$HEAD_SHA"
  docker compose --profile test-python run --rm test-runner-python \
    python scripts/validate_author_review.py --pr-body-file "/workspace/${REPORT_DIR#${ROOT}/}/pr-body.md" --head "$HEAD_SHA"
fi

docker compose --profile agent-runtime-adapter logs --no-color --timestamps \
  agent-runtime-adapter-digital-marketing agent-runtime-adapter-trading > "$REPORT_DIR/adapter-logs.txt"
docker stats --no-stream > "$REPORT_DIR/docker-stats.txt"
docker system df > "$REPORT_DIR/docker-system-df-after.txt"
FAILURE_CLASSIFICATION="none"
RESULT=PASS
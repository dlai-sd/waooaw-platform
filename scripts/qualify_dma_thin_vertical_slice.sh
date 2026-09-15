#!/usr/bin/env bash
# Implements: WC-089 DMA-10, DMA-11; Issue #437 qualification contract
# Constitutional basis: C-001, C-023, C-032, C-059, C-065, C-071, C-079
set -euo pipefail

OUTPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output) OUTPUT="${2:-}"; shift 2 ;;
    *) echo "usage: $0 --output path" >&2; exit 2 ;;
  esac
done
[[ -n "$OUTPUT" ]] || { echo "--output is required" >&2; exit 2; }
for command in docker git jq sha256sum; do command -v "$command" >/dev/null; done

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
[[ "$OUTPUT" == /* ]] || OUTPUT="$ROOT/${OUTPUT#./}"
EVIDENCE_DIR="$(dirname "$OUTPUT")"
CONTAINER_EVIDENCE_DIR="/workspace/${EVIDENCE_DIR#"$ROOT"/}"
HEAD_SHA="$(git rev-parse HEAD)"
BASE_SHA="$(git merge-base HEAD origin/main)"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
COMMON_GIT_DIR="$(git rev-parse --path-format=absolute --git-common-dir)"
IMAGE_TAG="dma-release-1-${HEAD_SHA:0:12}"
IMAGE="waooaw/agent-runtime-adapter-digital-marketing:$IMAGE_TAG"
IMAGE_ID=""
RESULT="FAIL"
FAILURE_CLASSIFICATION="code/configuration"

mkdir -p "$EVIDENCE_DIR"
write_evidence() {
  local exit_code=$?
  local completed_at
  completed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  jq -n \
    --arg result "$RESULT" --arg head "$HEAD_SHA" --arg base "$BASE_SHA" \
    --arg image "$IMAGE" --arg image_id "$IMAGE_ID" \
    --arg started "$STARTED_AT" --arg completed "$completed_at" \
    --arg failure "$FAILURE_CLASSIFICATION" --argjson exit_code "$exit_code" \
    '{schemaVersion:"1.0.0",workContract:"WC-089",issue:437,result:$result,
      headSha:$head,baseSha:$base,releaseSequence:1,professionalVersion:"1.0.0",
      specificationRevision:"3.1",skills:["CUSTOMER_PROFILING","MARKET_RESEARCH","CONTENT_STRATEGY"],
      authority:{founderApprovalRef:"github-issue:437",sessionAuthorizationRef:"github-issue:437#authority",builderIdentity:"platform-it-expert"},
      image:{name:$image,id:$image_id},environment:"local-docker",startedAt:$started,completedAt:$completed,
      gates:{buildAuthority:$result,contracts:$result,skills:$result,runtimeIsolationReplayStop:$result,
        ownerAttribution:$result,openapi:$result,staticAnalysis:$result,sbom:$result,trivy:$result,gitleaksDiff:$result},
      prohibitedUntested:["provider calls","cloud mutation","deployment","DNS","UAT","Production","customer traffic"],
      failureClassification:$failure,exitCode:$exit_code}' > "$OUTPUT"
}
trap write_evidence EXIT

# Ignore only evidence outputs and the known unrelated user edit; every WC-089 tracked path must be clean.
if ! git diff --quiet HEAD -- . ':(exclude)tests/Foo.cs'; then
  echo "qualification requires finalized committed WC-089 tracked files" >&2
  exit 1
fi

docker version > "$EVIDENCE_DIR/docker-version.txt"
docker compose version > "$EVIDENCE_DIR/docker-compose-version.txt"
WAOOAW_ENVIRONMENT=demo docker compose --profile agent-runtime-adapter config --quiet

FAILURE_CLASSIFICATION="assertion"
docker compose --profile test-python build test-runner-python > "$EVIDENCE_DIR/build-test-runner.log" 2>&1
docker compose --profile test-python run --rm test-runner-python \
  python -B -m pytest tests/constitutional/test_dma_build_authority.py \
    tests/contract/test_agent_admission_schema.py \
    tests/professional-runtime/test_dma_release_1_skills.py \
    tests/professional-runtime/test_agent_runtime_adapter.py \
    tests/professional-runtime/test_relationship_workspace.py \
    tests/billing-engine/test_meter.py -q \
  | tee "$EVIDENCE_DIR/python-tests.log"

docker compose --profile test run --rm --user root test-runner \
  dotnet test tests/business-platform.Tests/business-platform.Tests.csproj \
  --filter 'FullyQualifiedName~ProfessionalsControllerTests|FullyQualifiedName~RelationshipWorkspaceControllerTests|FullyQualifiedName~OwnerGatewayCoverageTests|FullyQualifiedName~InfrastructureWorkflowCoverageTests.UnconfiguredWorkspaceOwners' \
  --logger 'console;verbosity=minimal' | tee "$EVIDENCE_DIR/business-platform-tests.log"

docker compose --profile test-python run --rm test-runner-python \
  ruff check src/agent-adapters tests/constitutional/test_dma_build_authority.py \
    tests/contract/test_agent_admission_schema.py tests/professional-runtime/test_dma_release_1_skills.py \
    tests/professional-runtime/test_agent_runtime_adapter.py tests/professional-runtime/test_relationship_workspace.py \
    tests/billing-engine/test_meter.py | tee "$EVIDENCE_DIR/ruff.log"

docker run --rm -v "$ROOT:/workspace:ro" -w /workspace node:20.19.4-bookworm-slim \
  npx --yes @stoplight/spectral-cli@6.15.0 lint --fail-severity error \
  architecture/reference/api-specs/agent-runtime-adapter-v1.openapi.yaml \
  architecture/reference/api-specs/professional-runtime.openapi.yaml \
  architecture/reference/api-specs/business-platform.openapi.yaml \
  > "$EVIDENCE_DIR/openapi.log"

FAILURE_CLASSIFICATION="build"
AUTHORITY_FILE="$EVIDENCE_DIR/build-authority-effective.json"
jq --arg head "$HEAD_SHA" --arg effective "$STARTED_AT" \
  --arg expires "$(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%SZ)" \
  '.sourceHead=$head | .effectiveAt=$effective | .expiresAt=$expires | .nonce=("wc089-final-" + $head)' \
  tests/fixtures/dma-release-1/build-authority-valid.json > "$AUTHORITY_FILE"

docker compose --profile test run --rm --user root \
  -e PYTHONPATH=/workspace/src/agent-adapters \
  -e WC089_HEAD="$HEAD_SHA" -e WC089_IMAGE="$IMAGE" -e WC089_AUTHORITY="$CONTAINER_EVIDENCE_DIR/build-authority-effective.json" \
  test-runner python3 -c '
import json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
from digital_marketing.build_authority import CandidateBuildAuthorityGate, run_candidate_build

authority = json.loads(Path(os.environ["WC089_AUTHORITY"]).read_text(encoding="utf-8"))
run_candidate_build(
    CandidateBuildAuthorityGate(), authority, source_head=os.environ["WC089_HEAD"],
    builder_identity="platform-it-expert", now=datetime.now(timezone.utc),
    output_directory=Path("/tmp/wc089-authorized-build"),
    build=lambda _: subprocess.run([
        "docker", "build", "--pull", "--file", "src/agent-adapters/digital_marketing/Dockerfile",
        "--tag", os.environ["WC089_IMAGE"], "src/agent-adapters"
    ], check=True),
)
' | tee "$EVIDENCE_DIR/build-dma-image.log"
IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$IMAGE")"
EXPECTED_IMAGE_ID="$(jq -r '.runtimeAdapter.artifactDigest' tests/fixtures/agent-admission/digital-marketing-local-service-v1.0.0.json)"
[[ "$IMAGE_ID" == "$EXPECTED_IMAGE_ID" ]] || {
  echo "admission artifactDigest must be replaced with final image ID: $IMAGE_ID" >&2
  exit 1
}

ADMISSION_DIGEST="sha256:$(sha256sum tests/fixtures/agent-admission/digital-marketing-local-service-v1.0.0.json | cut -d' ' -f1)"
docker run --rm --read-only --tmpfs /tmp:size=16m,mode=1770 \
  -e WAOOAW_ENVIRONMENT=demo -e DMA_ARTIFACT_DIGEST="$IMAGE_ID" \
  -e DMA_ADMISSION_CONTENT_DIGEST="$ADMISSION_DIGEST" "$IMAGE" \
  python -c 'from digital_marketing.adapter import create_adapter; d=create_adapter().describe(); assert d.professional_version == "1.0.0"; assert len(d.skill_versions) == 3' \
  > "$EVIDENCE_DIR/image-conformance.log"

FAILURE_CLASSIFICATION="security"
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$EVIDENCE_DIR:/out" \
  anchore/syft:v1.27.1 "docker:$IMAGE" -o cyclonedx-json=/out/sbom.json
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$EVIDENCE_DIR:/out" \
  aquasec/trivy:0.66.0 image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
  --format json --output /out/trivy.json "$IMAGE"
docker run --rm -v "$ROOT:/repo:ro" -v "$COMMON_GIT_DIR:$COMMON_GIT_DIR:ro" -v "$EVIDENCE_DIR:/out" \
  zricethezav/gitleaks:v8.28.0 detect --source=/repo --no-banner --redact --exit-code=1 \
  --log-opts="$BASE_SHA..$HEAD_SHA" --report-format=json --report-path=/out/gitleaks-diff.json

git diff --check "$BASE_SHA..$HEAD_SHA"
find "$EVIDENCE_DIR" -maxdepth 1 -type f \( -name '*.json' -o -name '*.log' \) \
  ! -name qualification.json -print0 | sort -z | xargs -0 sha256sum > "$EVIDENCE_DIR/report-hashes.sha256"
FAILURE_CLASSIFICATION="none"
RESULT="PASS"
echo "WC-089 qualification PASS: $OUTPUT"

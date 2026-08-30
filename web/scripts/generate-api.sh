#!/usr/bin/env sh
set -eu

# Implements: architecture/reference/components/conversation-core.md §3 and WC-034 F4 Public BP Contract
# Constitutional basis: C-032 (Spec Is Truth), C-059 (Implementation Traceability)

readonly GENERATOR_IMAGE="openapitools/openapi-generator-cli:v7.17.0"
readonly REPOSITORY_ROOT="$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd)"
readonly OUTPUT_PATH="$REPOSITORY_ROOT/web/lib/api/generated"
readonly SLICE_PATH="$(mktemp "$REPOSITORY_ROOT/sprint-context/.f3-web-openapi.XXXXXX.yaml")"
readonly CONTAINER_SLICE_PATH="/local${SLICE_PATH#"$REPOSITORY_ROOT"}"

chmod 0666 "$SLICE_PATH"

cleanup() {
  rm -f "$SLICE_PATH"
}
trap cleanup EXIT HUP INT TERM

cd "$REPOSITORY_ROOT"
docker compose --profile test run --rm --no-deps test-runner \
  python3 scripts/openapi_slice.py \
  --input architecture/reference/api-specs/business-platform.openapi.yaml \
  --output "${SLICE_PATH#"$REPOSITORY_ROOT/"}" \
  --tag Identity \
  --tag Conversation \
  --tag Employment \
  --tag Professionals \
  --tag "Relationship Workspace" \
  --tag "Voice Contributions" \
  --schema EmploymentRelationship \
  --schema RelationshipTimelineEntry

rm -rf "$OUTPUT_PATH"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "$REPOSITORY_ROOT:/local" \
  "$GENERATOR_IMAGE" generate \
  --input-spec "$CONTAINER_SLICE_PATH" \
  --generator-name typescript-fetch \
  --output /local/web/lib/api/generated \
  --global-property "apis=Identity:Conversation:Employment:Professionals:RelationshipWorkspace:VoiceContributions,models,supportingFiles=runtime.ts:models/index.ts:index.ts" \
  --additional-properties supportsES6=true,typescriptThreePlus=true,useSingleRequestParameter=true,hideGenerationTimestamp=true

docker compose --profile test run --rm --no-deps test-runner \
  sh -lc 'cd /workspace/web && pnpm install --frozen-lockfile --store-dir=/tmp/pnpm-store && pnpm exec prettier --write lib/api/generated'
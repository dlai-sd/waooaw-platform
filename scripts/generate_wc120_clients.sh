#!/usr/bin/env bash
# Implements: WC120-R021, WC120-R022, WC120-R034 deterministic client boundary
# Constitutional basis: C-023, C-026, C-059, C-065

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
generator_image="openapitools/openapi-generator-cli:v7.17.0"
bundled_spec_host="${repo_root}/test-results/wc120/codegen/channel-neutral-conversation-bundled.openapi.yaml"
spec="/local/test-results/wc120/codegen/channel-neutral-conversation-bundled.openapi.yaml"

cleanup() {
  rm -f "${bundled_spec_host}"
  rmdir "${repo_root}/test-results/wc120/codegen" 2>/dev/null || true
}
trap cleanup EXIT

docker compose --project-directory "${repo_root}" --profile test-python run --rm \
  test-runner-python python scripts/validation_control/bundle_wc120_openapi.py \
  --input architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml \
  --output test-results/wc120/codegen/channel-neutral-conversation-bundled.openapi.yaml

test -s "${bundled_spec_host}"

rm -rf \
  "${repo_root}/web/lib/api/generated/conversation-v1" \
  "${repo_root}/src/professional-runtime/clients/generated/conversation_compatibility"

generate() {
  docker run --rm --user "$(id -u):$(id -g)" -v "${repo_root}:/local" \
    "${generator_image}" generate "$@"
}

generate \
  -i "${spec}" \
  -g typescript-fetch \
  -o /local/web/lib/api/generated/conversation-v1 \
  --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false \
  --additional-properties=supportsES6=true,npmName=@waooaw/conversation-client,npmVersion=1.0.0-candidate.2,withInterfaces=true,useTags=true,useSingleRequestParameter=true,legacyDiscriminatorBehavior=false

generate \
  -i "${spec}" \
  -g python \
  -o /local/src/professional-runtime/clients/generated/conversation_compatibility \
  --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false \
  --additional-properties=packageName=conversation_compatibility_client,packageVersion=1.0.0-candidate.2,generateSourceCodeOnly=true

docker run --rm --user "$(id -u):$(id -g)" -v "${repo_root}:/workspace" -w /workspace \
  waooaw-platform-test-runner-python:local \
  python scripts/validation_control/normalize_generated_text.py \
  web/lib/api/generated/conversation-v1 \
  src/professional-runtime/clients/generated/conversation_compatibility

spec_sha256="$(sha256sum "${repo_root}/architecture/reference/api-specs/channel-neutral-conversation-business-platform.openapi.yaml" | cut -d' ' -f1)"
for output in \
  "${repo_root}/web/lib/api/generated/conversation-v1" \
  "${repo_root}/src/professional-runtime/clients/generated/conversation_compatibility"
do
  cat >"${output}/generation-manifest.json" <<EOF
{
  "generator": "openapi-generator-cli",
  "generatorImage": "${generator_image}",
  "generationInput": "deterministically-bundled",
  "compatibilityTransforms": ["command-kind-const-to-single-enum"],
  "specVersion": "1.0.0-candidate.2",
  "specSha256": "${spec_sha256}"
}
EOF
done

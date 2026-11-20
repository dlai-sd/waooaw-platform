#!/usr/bin/env bash
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-06
# Constitutional basis: C-023, C-026, C-059, C-065

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
generator_image="openapitools/openapi-generator-cli:v7.17.0"
runner_image="${WAOOAW_RUNNER_FULL_IMAGE:-waooaw-platform-test-runner-full:local}"
codegen_dir="${repo_root}/test-results/wc136/codegen"

cleanup() {
  rm -rf "${codegen_dir}"
  rmdir "${repo_root}/test-results/wc136" 2>/dev/null || true
}
trap cleanup EXIT

run_runner() {
  docker run --rm --user "$(id -u):$(id -g)" -v "${repo_root}:/workspace" -w /workspace \
    "${runner_image}" "$@"
}

generate() {
  docker run --rm --user "$(id -u):$(id -g)" -v "${repo_root}:/local" \
    "${generator_image}" generate "$@"
}

generate_slice() {
  local source_name="$1" output_name="$2" npm_name="$3"
  local bundled_host="${codegen_dir}/${output_name}.openapi.yaml"
  run_runner python scripts/validation_control/bundle_wc136_openapi.py \
    --input "architecture/reference/api-specs/${source_name}" \
    --output "test-results/wc136/codegen/${output_name}.openapi.yaml"
  test -s "${bundled_host}"
  rm -rf "${repo_root}/web/lib/api/generated/${output_name}"
  generate \
    -i "/local/test-results/wc136/codegen/${output_name}.openapi.yaml" \
    -g typescript-fetch \
    -o "/local/web/lib/api/generated/${output_name}" \
    --global-property apiTests=false,modelTests=false,apiDocs=false,modelDocs=false \
    --additional-properties="supportsES6=true,npmName=${npm_name},npmVersion=1.0.0,withInterfaces=true,useTags=true,useSingleRequestParameter=true,legacyDiscriminatorBehavior=false"
  local spec_sha256
  spec_sha256="$(sha256sum "${repo_root}/architecture/reference/api-specs/${source_name}" | cut -d' ' -f1)"
  cat >"${repo_root}/web/lib/api/generated/${output_name}/generation-manifest.json" <<EOF
{
  "generator": "openapi-generator-cli",
  "generatorImage": "${generator_image}",
  "generationInput": "deterministically-bundled",
  "specVersion": "1.0.0",
  "specSha256": "${spec_sha256}"
}
EOF
}

mkdir -p "${codegen_dir}"
generate_slice "agent-experience-workbench.openapi.yaml" "workbench-v1" "@waooaw/workbench-client"
generate_slice "pricing-admin-business-platform.openapi.yaml" "pricing-admin-v1" "@waooaw/pricing-admin-client"

run_runner python scripts/validation_control/normalize_generated_text.py \
  web/lib/api/generated/workbench-v1 web/lib/api/generated/pricing-admin-v1

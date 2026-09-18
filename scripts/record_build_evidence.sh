#!/bin/sh
# Constitutional basis: C-023, C-059, C-071, C-080

set -eu

if [ "$#" -ne 8 ]; then
  echo "usage: $0 <output> <component> <base-sha> <head-sha> <image-id> <registry-digest-or-empty> <consumers-json> <invalidation-reason>" >&2
  exit 2
fi

output=$1
component=$2
base_sha=$3
head_sha=$4
image_id=$5
registry_digest=$6
consumers_json=$7
invalidation_reason=$8

case "$image_id" in
  sha256:????????????????????????????????????????????????????????????????) ;;
  *) echo "image ID must be a complete sha256 digest" >&2; exit 1 ;;
esac
if [ -n "$registry_digest" ]; then
  case "$registry_digest" in
    sha256:????????????????????????????????????????????????????????????????) ;;
    *) echo "registry digest must be empty or a complete sha256 digest" >&2; exit 1 ;;
  esac
fi
printf '%s' "$consumers_json" | jq -e 'type == "array" and length > 0 and all(.[]; type == "string" and length > 0)' >/dev/null

input_identity=$(
  {
    git ls-files -z | LC_ALL=C sort -z | xargs -0 sha256sum
    printf 'component=%s\nplatform=%s\ngate_version=%s\n' "$component" "$(uname -m)" "wc100-build-v1"
  } | sha256sum | cut -d ' ' -f 1
)
trust_source=local-exact-image
if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
  trust_source=github-actions
fi
mkdir -p "$(dirname "$output")"
jq -n \
  --arg schema "waooaw.build-evidence/v1" \
  --arg status "PASS" \
  --arg trust_source "$trust_source" \
  --arg repository "${GITHUB_REPOSITORY:-local/waooaw-platform}" \
  --arg base_sha "$base_sha" \
  --arg head_sha "$head_sha" \
  --arg input_identity "$input_identity" \
  --arg image_id "$image_id" \
  --arg registry_digest "$registry_digest" \
  --arg builder "buildkit" \
  --arg platform "$(uname -m)" \
  --arg docker_version "$(docker version --format '{{.Client.Version}}')" \
  --arg buildkit_version "$(docker buildx version | awk '{print $2}')" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --argjson consumers "$consumers_json" \
  --arg output "$output" \
  --arg invalidation_reason "$invalidation_reason" \
  '{schema: $schema, status: $status, trust_source: $trust_source, repository: $repository,
    base_sha: $base_sha, head_sha: $head_sha, input_identity: $input_identity,
    input_groups: ["source", "tests", "fixtures", "dockerfile", "dependencies", "compose",
      "generated_contracts", "specifications", "build_arguments", "platform", "gate_version"],
    image_id: $image_id, registry_digest: $registry_digest, builder: $builder, platform: $platform,
    docker_version: $docker_version, buildkit_version: $buildkit_version,
    started_at: $timestamp, completed_at: $timestamp, consumers: $consumers,
    artifact_refs: [$output], cache_result: "workflow-cache-policy", invalidation_reason: $invalidation_reason}' \
  > "$output"

printf 'build_evidence=%s input_identity=%s\n' "$output" "$input_identity"
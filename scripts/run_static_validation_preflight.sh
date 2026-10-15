#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ACTIONLINT_IMAGE="rhysd/actionlint:1.7.7"

cd "$REPOSITORY_ROOT"

echo "[1/3] Linting GitHub Actions workflows"
base_sha=${BASE_SHA:-origin/main}
head_sha=${HEAD_SHA:-HEAD}
mapfile -t changed_files < <(
  {
    git diff --name-only --diff-filter=ACMR "$base_sha" "$head_sha"
    git diff --name-only --diff-filter=ACMR "$head_sha"
    git diff --cached --name-only --diff-filter=ACMR
  } | LC_ALL=C sort -u
)
declare -A changed_lookup=()
workflow_files=()
for path in "${changed_files[@]}"; do
  changed_lookup["$path"]=1
  if [[ "$path" == .github/workflows/*.yml || "$path" == .github/workflows/*.yaml ]]; then
    workflow_files+=("$path")
  fi
done
if ((${#workflow_files[@]})); then
  docker run --rm -v "$REPOSITORY_ROOT:/repo:ro" -w /repo "$ACTIONLINT_IMAGE" "${workflow_files[@]}"
else
  echo "  no workflow files changed"
fi

echo "[2/3] Rendering Docker Compose configuration"
compose_changed=false
for path in "${changed_files[@]}"; do
  if [[ "$path" == docker-compose*.yml || "$path" == docker-compose*.yaml || "$path" == .env.example ]]; then
    compose_changed=true
    break
  fi
done
if [[ "$compose_changed" == true ]]; then
  docker compose config --quiet
else
  echo "  no Compose graph inputs changed"
fi

echo "[3/3] Checking Dockerfiles without executing build layers"
check_all_dockerfiles=false
if [[ -n ${changed_lookup[".dockerignore"]+present} || -n ${changed_lookup["scripts/run_static_validation_preflight.sh"]+present} ]]; then
  check_all_dockerfiles=true
fi
checked_dockerfiles=0
while IFS=$'\t' read -r context dockerfile; do
  if [[ "$check_all_dockerfiles" != true && -z ${changed_lookup["$dockerfile"]+present} ]]; then
    continue
  fi
  echo "  checking $dockerfile"
  docker buildx build --check --file "$dockerfile" "$context"
  checked_dockerfiles=$((checked_dockerfiles + 1))
done <<'TARGETS'
.	architecture/reference/dockerfiles/Dockerfile.test-runner-python
.	architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet
.	architecture/reference/dockerfiles/Dockerfile.test-runner-ts
.	architecture/reference/dockerfiles/Dockerfile.test-runner
.	architecture/reference/dockerfiles/Dockerfile.test-runner-azure
.	src/constitutional-engine/Dockerfile
.	src/business-platform/Dockerfile
.	src/professional-runtime/Dockerfile
.	src/ai-runtime/Dockerfile
.	web/Dockerfile
.	src/billing-engine/Dockerfile
src	src/digital-marketing-agent/Dockerfile
TARGETS
if ((checked_dockerfiles == 0)); then
  echo "  no Dockerfile graph inputs changed"
fi

echo "Static validation preflight passed; no image was exported."
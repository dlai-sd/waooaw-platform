#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ACTIONLINT_IMAGE="rhysd/actionlint:1.7.7"

cd "$REPOSITORY_ROOT"

echo "[1/3] Linting GitHub Actions workflows"
base_sha=${BASE_SHA:-origin/main}
head_sha=${HEAD_SHA:-HEAD}
mapfile -t workflow_files < <(
  {
    git diff --name-only --diff-filter=ACMR "$base_sha" "$head_sha" -- '.github/workflows/*.yml' '.github/workflows/*.yaml'
    git diff --name-only --diff-filter=ACMR "$head_sha" -- '.github/workflows/*.yml' '.github/workflows/*.yaml'
    git diff --cached --name-only --diff-filter=ACMR -- '.github/workflows/*.yml' '.github/workflows/*.yaml'
  } | LC_ALL=C sort -u
)
if ((${#workflow_files[@]})); then
  docker run --rm -v "$REPOSITORY_ROOT:/repo:ro" -w /repo "$ACTIONLINT_IMAGE" "${workflow_files[@]}"
else
  echo "  no workflow files changed"
fi

echo "[2/3] Rendering Docker Compose configuration"
docker compose config --quiet

echo "[3/3] Checking Dockerfiles without executing build layers"
while IFS=$'\t' read -r context dockerfile; do
  echo "  checking $dockerfile"
  docker buildx build --check --file "$dockerfile" "$context"
done <<'TARGETS'
.	architecture/reference/dockerfiles/Dockerfile.test-runner-python
.	architecture/reference/dockerfiles/Dockerfile.test-runner-dotnet
.	architecture/reference/dockerfiles/Dockerfile.test-runner-ts
.	architecture/reference/dockerfiles/Dockerfile.test-runner
.	src/constitutional-engine/Dockerfile
.	src/business-platform/Dockerfile
.	src/professional-runtime/Dockerfile
.	src/ai-runtime/Dockerfile
.	web/Dockerfile
.	src/billing-engine/Dockerfile
src/agent-adapters	src/agent-adapters/digital_marketing/Dockerfile
TARGETS

echo "Static validation preflight passed; no image was exported."
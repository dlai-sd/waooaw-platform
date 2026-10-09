#!/bin/sh
set -eu

parent_container=${HOSTNAME:?HOSTNAME must identify the validation runner container}
repository_url=https://github.com/dlai-sd/waooaw-platform.git
scope_file=/tmp/spec-lint-openapi-paths.txt

python scripts/validation_control/spec_lint_scope.py \
    --repository /workspace \
    --changed-files "${WAOOAW_CHANGED_FILES_FILE:-/tmp/spec-lint-no-changes}" \
    > "$scope_file"

set --
while IFS= read -r spec_path; do
    test -n "$spec_path" || continue
    set -- "$@" "$spec_path"
done < "$scope_file"

test "$#" -gt 0

python scripts/validation_control/customer_forbidden_responses.py \
    --spec architecture/reference/api-specs/business-platform.openapi.yaml

for spec_path in "$@"; do
    docker run --rm --user 1000:1000 \
        --volumes-from "$parent_container":ro \
        -w /workspace \
        openapitools/openapi-generator-cli:v7.17.0 validate \
        -i "$spec_path"
done

docker run --rm --user 1000:1000 \
    --volumes-from "$parent_container":ro \
    -w /workspace \
    stoplight/spectral:6.15.0 lint \
    --fail-severity error \
    "$@"

docker run --rm \
    --volumes-from "$parent_container":ro \
    -w /workspace/architecture/reference/proto \
    bufbuild/buf:1.72.0 format --diff --exit-code
docker run --rm \
    --volumes-from "$parent_container":ro \
    -w /workspace/architecture/reference/proto \
    bufbuild/buf:1.72.0 lint
docker run --rm \
    --volumes-from "$parent_container":ro \
    -w /workspace/architecture/reference/proto \
    bufbuild/buf:1.72.0 breaking \
    --against "${repository_url}#branch=main,subdir=architecture/reference/proto"
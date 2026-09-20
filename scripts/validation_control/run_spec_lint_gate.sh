#!/bin/sh
set -eu

parent_container=${HOSTNAME:?HOSTNAME must identify the validation runner container}
repository_url=https://github.com/dlai-sd/waooaw-platform.git

docker run --rm --user 1000:1000 \
    --volumes-from "$parent_container":ro \
    -w /workspace \
    stoplight/spectral:6.15.0 lint \
    --fail-severity error \
    architecture/reference/api-specs/business-platform.openapi.yaml \
    architecture/reference/api-specs/professional-runtime.openapi.yaml

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
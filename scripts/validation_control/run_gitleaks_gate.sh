#!/bin/sh
set -eu

: "${BASE_SHA:?BASE_SHA is required}"
: "${HEAD_SHA:?HEAD_SHA is required}"
: "${GIT_COMMON_DIR:?GIT_COMMON_DIR is required}"
: "${REPOSITORY_ROOT:?REPOSITORY_ROOT is required}"

docker run --rm \
    -v "$REPOSITORY_ROOT:/repo:ro" \
    -v "$GIT_COMMON_DIR:$GIT_COMMON_DIR:ro" \
    zricethezav/gitleaks@sha256:cdbb7c955abce02001a9f6c9f602fb195b7fadc1e812065883f695d1eeaba854 \
    git /repo \
    --log-opts "$BASE_SHA..$HEAD_SHA" \
    --no-banner \
    --redact

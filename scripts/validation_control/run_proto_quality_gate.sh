#!/bin/sh
set -eu

cd /workspace/architecture/reference/proto
export BUF_CACHE_DIR=/tmp/buf-cache
buf lint
buf format --diff --exit-code
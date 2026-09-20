#!/bin/sh
set -eu

input_dir=/workspace/test-results/wc104/c059

read_sha() {
    value=$(cat "$1")
    case "$value" in
        *[!0-9a-fA-F]*|'')
            echo "invalid commit SHA in $1" >&2
            exit 2
            ;;
    esac
    if [ "${#value}" -ne 40 ]; then
        echo "invalid commit SHA length in $1" >&2
        exit 2
    fi
    printf '%s' "$value"
}

base_sha=$(read_sha "$input_dir/base-sha.txt")
head_sha=$(read_sha "$input_dir/head-sha.txt")

exec python scripts/validate_c059.py \
    --pr-body-file "$input_dir/pr-body.md" \
    --base "$base_sha" \
    --head "$head_sha"
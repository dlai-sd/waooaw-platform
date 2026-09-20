#!/bin/sh
set -eu

metadata_directory=${1:-test-results/wc104/metadata}
base_sha=$(cat "$metadata_directory/base-sha.txt")
head_sha=$(cat "$metadata_directory/head-sha.txt")

commitlint --from "$base_sha" --to "$head_sha" --verbose
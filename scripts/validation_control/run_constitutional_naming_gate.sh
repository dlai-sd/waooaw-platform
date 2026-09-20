#!/bin/sh
set -eu

metadata_directory=${1:-test-results/wc104/metadata}
base_sha=$(cat "$metadata_directory/base-sha.txt")
head_sha=$(cat "$metadata_directory/head-sha.txt")
changed=$(git diff --name-only "$base_sha" "$head_sha" | grep -E '\.(cs|py)$' | head -30 || true)

if [ -z "$changed" ]; then
    echo "No .cs/.py files changed"
    exit 0
fi

for file in $changed; do
    [ -f "$file" ] || continue
    if grep -qE 'class.*Manager|class.*Helper|class.*Util|class.*Misc' "$file"; then
        echo "WARNING: Generic class name in $file - consider constitutional naming (C-072)"
    fi
    if grep -qE '[^_a-zA-Z]250[^ms]|[^_]40[^m]' "$file" 2>/dev/null; then
        echo "INFO: Possible magic number in $file - ensure constitutional constants are named"
    fi
done
echo "Constitutional naming audit complete"
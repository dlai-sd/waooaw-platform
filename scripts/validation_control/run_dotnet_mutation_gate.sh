#!/bin/sh
set -eu

worktree=/tmp/constitutional-engine-mutation
mkdir -p "$worktree/src" "$worktree/tests"
cp -a src/constitutional-engine "$worktree/src/constitutional-engine"
cp -a tests/constitutional-engine.Tests "$worktree/tests/constitutional-engine.Tests"
cd "$worktree/tests/constitutional-engine.Tests"
dotnet-stryker \
    --project constitutional-engine.csproj \
    --threshold-high 80 --threshold-low 75 --break-at 65 \
    --reporter json --output /workspace/test-results/stryker-ce-results
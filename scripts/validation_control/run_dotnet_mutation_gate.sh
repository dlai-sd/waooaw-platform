#!/bin/sh
set -eu

scope_environment=/tmp/dotnet-mutation-scope.env
python_command=$(command -v python3 || command -v python)
"$python_command" scripts/validation_control/qualification_change_scope.py \
    --gate mutation:dotnet \
    --changed-files "${WAOOAW_CHANGED_FILES_FILE:-}" > "$scope_environment"
. "$scope_environment"
if test "$QUALIFICATION_GATE_APPLICABLE" = false; then
    echo 'Dotnet mutation not applicable: Constitutional Engine inputs did not change.'
    exit 0
fi

worktree=/tmp/constitutional-engine-mutation
rm -rf "$worktree"
mkdir -p "$worktree/src" "$worktree/tests"
cp -a src/constitutional-engine "$worktree/src/constitutional-engine"
cp -a tests/constitutional-engine.Tests "$worktree/tests/constitutional-engine.Tests"
cd "$worktree/tests/constitutional-engine.Tests"
dotnet-stryker \
    --project constitutional-engine.csproj \
    --threshold-high 80 --threshold-low 75 --break-at 65 \
    --reporter json --output /workspace/test-results/stryker-ce-results
#!/bin/sh
set -eu

scope_environment=/tmp/python-mutation-scope.env
python_command=$(command -v python3 || command -v python)
"$python_command" scripts/validation_control/qualification_change_scope.py \
    --gate mutation:python \
    --changed-files "${WAOOAW_CHANGED_FILES_FILE:-}" > "$scope_environment"
. "$scope_environment"
if test "$QUALIFICATION_GATE_APPLICABLE" = false; then
    echo 'Python mutation not applicable: AI Runtime and trust-layer inputs did not change.'
    exit 0
fi

worktree=/tmp/ai-runtime-mutation
rm -rf "$worktree"
mkdir -p "$worktree/tests"
cp -a src/ai-runtime/. "$worktree/"
cp -a src/trust-layer "$worktree/trust-layer"
cp -a tests/ai-runtime "$worktree/tests/ai-runtime"
cat > "$worktree/setup.cfg" <<'EOF'
[mutmut]
source_paths =
    main.py
    transcription.py
    pii
    providers
    pse
    rag
    skeleton
also_copy = trust-layer
pytest_add_cli_args_test_selection = tests/ai-runtime

[tool:pytest]
asyncio_mode = auto
EOF
cd "$worktree"
PYTHONPATH="$worktree/trust-layer:${PYTHONPATH:-}" mutmut run
mutmut results
mutmut export-cicd-stats
score=$(python -c 'import json; stats=json.load(open("mutants/mutmut-cicd-stats.json")); tested=stats["total"]-stats["skipped"]; print(0 if tested <= 0 else int((stats["killed"]+stats["timeout"])*100/tested))')
echo "Mutation score ${score}%"
if [ "${score:-0}" -lt 60 ]; then
    echo "Mutation score ${score:-0}% < 60% - C-072"
    exit 1
fi
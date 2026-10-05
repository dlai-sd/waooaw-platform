#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
    printf '%s\n' 'usage: run_docker_build.sh COMMAND [ARG ...]' >&2
    exit 2
fi

repository=$(git rev-parse --show-toplevel)
PYTHONPATH="$repository/scripts" python -c '
from pathlib import Path
from validation_control.execution_contract import cleanup_before_docker_build

for action in cleanup_before_docker_build(Path.cwd()):
    print(f"pre-build cleanup: {action}")
'
exec "$@"
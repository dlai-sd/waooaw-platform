#!/bin/sh
set -eu

gate=""
head_sha=""
base_sha=""
mode="focused"
changed_files=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --gate)
            gate=${2:?--gate requires a gate ID}
            shift 2
            ;;
        --head)
            head_sha=${2:?--head requires a commit}
            shift 2
            ;;
        --base)
            base_sha=${2:?--base requires a commit}
            shift 2
            ;;
        --mode)
            mode=${2:?--mode requires focused or qualification}
            shift 2
            ;;
        --changed-file)
            changed_files="${changed_files}
${2:?--changed-file requires a repository-relative path}"
            shift 2
            ;;
        *)
            printf 'unknown argument: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

if [ -z "$gate" ] || [ -z "$head_sha" ] || [ -z "$base_sha" ]; then
    printf 'usage: %s --gate GATE --head COMMIT --base COMMIT [--mode focused|qualification] --changed-file PATH [...]\n' "$0" >&2
    exit 2
fi
case "$mode" in
    focused|qualification) ;;
    *)
        printf '%s\n' '--mode must be focused or qualification' >&2
        exit 2
        ;;
esac

repository=$(realpath "$(git rev-parse --show-toplevel)")
git_common_dir=$(realpath "$(git -C "$repository" rev-parse --git-common-dir)")
docker_socket=${DOCKER_SOCKET:-/var/run/docker.sock}
mkdir -p "$repository/test-results"

set -- python scripts/validation_control/local_catalog_gate.py \
    --gate "$gate" \
    --head "$head_sha" \
    --base "$base_sha" \
    --git-common-dir "$git_common_dir" \
    --mode "$mode"
old_ifs=$IFS
IFS='
'
for changed_file in $changed_files; do
    [ -n "$changed_file" ] && set -- "$@" --changed-file "$changed_file"
done
IFS=$old_ifs

scripts/validation_control/run_with_docker_socket.sh \
    docker compose --project-directory "$repository" --profile test run --rm --no-deps \
    -v "$repository:$repository:ro" \
    -v "$repository/test-results:$repository/test-results" \
    -v "$git_common_dir:$git_common_dir:ro" \
    -v "$docker_socket:$docker_socket" \
    -w "$repository" \
    test-runner "$@"

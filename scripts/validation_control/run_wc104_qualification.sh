#!/bin/sh
set -eu

base_sha=""
output=""
handoff_evidence=""
resume=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --base)
            base_sha=${2:?--base requires a commit}
            shift 2
            ;;
        --output)
            output=${2:?--output requires a path}
            shift 2
            ;;
        --handoff-evidence)
            handoff_evidence=${2:?--handoff-evidence requires a path}
            shift 2
            ;;
        --resume)
            resume=1
            shift
            ;;
        *)
            printf 'unknown argument: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

if [ -z "$base_sha" ] || [ -z "$output" ] || [ -z "$handoff_evidence" ]; then
    printf 'usage: %s --base COMMIT --output test-results/PATH --handoff-evidence PATH [--resume]\n' "$0" >&2
    exit 2
fi
case "/$output/" in
    /test-results/*/)
        ;;
    *)
        printf '%s\n' '--output must be repository-relative below test-results' >&2
        exit 2
        ;;
esac
case "/$output/" in
    */../*)
        printf '%s\n' '--output must not traverse outside test-results' >&2
        exit 2
        ;;
esac
if [ -z "${GITHUB_TOKEN:-}" ]; then
    printf '%s\n' 'GITHUB_TOKEN is required for exact PR authority preflight' >&2
    exit 2
fi

repository=$(git rev-parse --show-toplevel)
repository=$(realpath "$repository")
git_common_dir=$(realpath "$(git -C "$repository" rev-parse --git-common-dir)")
docker_socket=/var/run/docker.sock
if [ ! -S "$docker_socket" ] || [ ! -r "$docker_socket" ] || [ ! -w "$docker_socket" ]; then
    printf '%s\n' 'Docker socket is required for qualification runner supply' >&2
    exit 2
fi
docker_gid=$(stat -c '%g' "$docker_socket")
mkdir -p "$repository/$(dirname "$output")"

DOCKER_GID=$docker_gid docker compose --project-directory "$repository" --profile test run --rm \
    -e GITHUB_TOKEN \
    -v "$repository:$repository:ro" \
    -v "$repository/test-results:$repository/test-results" \
    -v "$git_common_dir:$git_common_dir:ro" \
    -v "$docker_socket:$docker_socket" \
    -w "$repository" \
    test-runner sh -lc '
        export PYTHONPATH="$PWD/scripts"
        if [ "$4" = 1 ]; then
            exec python scripts/validation_control/wc104_rollback.py \
                --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3" \
                --handoff-evidence "$5" --execution-profile qualification --resume
        fi
        exec python scripts/validation_control/wc104_rollback.py \
            --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3" \
            --handoff-evidence "$5" --execution-profile qualification
    ' qualification "$base_sha" "$git_common_dir" "$output" "$resume" "$handoff_evidence"

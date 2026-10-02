#!/bin/sh
set -eu

base_sha=""
output=""
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

if [ -z "$base_sha" ] || [ -z "$output" ]; then
    printf 'usage: %s --base COMMIT --output test-results/PATH [--resume]\n' "$0" >&2
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
mkdir -p "$repository/$(dirname "$output")"

docker compose --project-directory "$repository" --profile test run --rm \
    -e GITHUB_TOKEN \
    -v "$repository:$repository:ro" \
    -v "$repository/test-results:$repository/test-results" \
    -v "$git_common_dir:$git_common_dir:ro" \
    -w "$repository" \
    test-runner sh -lc '
        export PYTHONPATH="$PWD/scripts"
        if [ "$4" = 1 ]; then
            exec python scripts/validation_control/wc104_rollback.py \
                --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3" --resume
        fi
        exec python scripts/validation_control/wc104_rollback.py \
            --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3"
    ' rollback "$base_sha" "$git_common_dir" "$output" "$resume"
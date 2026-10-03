#!/bin/sh
set -eu

base_sha=""
output=""
handoff_evidence=""
precheck_evidence=""
repair_context=""
repair_gate=""
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
        --precheck-evidence)
            precheck_evidence=${2:?--precheck-evidence requires a path}
            shift 2
            ;;
        --resume)
            resume=1
            shift
            ;;
        --repair-context)
            repair_context=${2:?--repair-context requires a path}
            shift 2
            ;;
        --repair-gate)
            repair_gate=${2:?--repair-gate requires a gate ID}
            shift 2
            ;;
        *)
            printf 'unknown argument: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

if [ -z "$base_sha" ] || [ -z "$output" ] || [ -z "$handoff_evidence" ] || [ -z "$precheck_evidence" ]; then
    printf 'usage: %s --base COMMIT --output test-results/PATH --handoff-evidence PATH --precheck-evidence PATH [--resume --repair-context PATH --repair-gate GATE]\n' "$0" >&2
    exit 2
fi
case "/$precheck_evidence/" in
    /test-results/*/) ;;
    *)
        printf '%s\n' '--precheck-evidence must be repository-relative below test-results' >&2
        exit 2
        ;;
esac
case "/$precheck_evidence/" in
    */../*)
        printf '%s\n' '--precheck-evidence must not traverse outside test-results' >&2
        exit 2
        ;;
esac
if { [ -n "$repair_context" ] || [ -n "$repair_gate" ]; } && \
    { [ "$resume" -ne 1 ] || [ -z "$repair_context" ] || [ -z "$repair_gate" ]; }; then
    printf '%s\n' '--repair-context and --repair-gate must be used together with --resume' >&2
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
if [ -n "$repair_context" ]; then
    case "/$repair_context/" in
        /test-results/*/)
            ;;
        *)
            printf '%s\n' '--repair-context must be repository-relative below test-results' >&2
            exit 2
            ;;
    esac
    case "/$repair_context/" in
        */../*)
            printf '%s\n' '--repair-context must not traverse outside test-results' >&2
            exit 2
            ;;
    esac
fi
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
mkdir -p "$repository/$(dirname "$output")"

scripts/validation_control/run_with_docker_socket.sh \
    docker compose --project-directory "$repository" --profile test run --rm \
    -e GITHUB_TOKEN \
    -v "$repository:$repository:ro" \
    -v "$repository/test-results:$repository/test-results" \
    -v "$git_common_dir:$git_common_dir:ro" \
    -v "$docker_socket:$docker_socket" \
    -w "$repository" \
    test-runner sh -lc '
        export PYTHONPATH="$PWD/scripts"
        if [ "$4" = 1 ]; then
            if [ -n "$6" ]; then
                exec python scripts/validation_control/wc104_rollback.py \
                    --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3" \
                    --handoff-evidence "$5" --precheck-evidence "$8" --execution-profile qualification --resume \
                    --repair-context "$6" --invalidate-gate "$7"
            fi
            exec python scripts/validation_control/wc104_rollback.py \
                --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3" \
                --handoff-evidence "$5" --precheck-evidence "$8" --execution-profile qualification --resume
        fi
        exec python scripts/validation_control/wc104_rollback.py \
            --repository "$PWD" --base "$1" --git-common-dir "$2" --output "$3" \
            --handoff-evidence "$5" --precheck-evidence "$8" --execution-profile qualification
    ' qualification "$base_sha" "$git_common_dir" "$output" "$resume" "$handoff_evidence" \
    "$repair_context" "$repair_gate" "$precheck_evidence"

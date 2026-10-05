#!/usr/bin/env bash
set -euo pipefail

repository_root="$(git rev-parse --show-toplevel)"
git_common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
docker_socket="${DOCKER_HOST:-}"
docker_socket="${docker_socket#unix://}"
docker_socket="${docker_socket:-/var/run/docker.sock}"

if [[ ! -S "$docker_socket" ]]; then
  printf 'PR body preparation failed: Docker socket not found at %s\n' "$docker_socket" >&2
  exit 1
fi

github_token="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$github_token" && " $* " != *" --preflight-only "* ]]; then
  github_token="$(gh auth token)"
fi

socket_gid="$(stat -c '%g' "$docker_socket")"
user_id="$(id -u)"

cd "$repository_root"
GH_TOKEN="$github_token" docker compose --profile test run --rm --no-deps \
  --user "$user_id:$socket_gid" \
  -e DOCKER_HOST="unix://$docker_socket" \
  -e GH_TOKEN \
  -e HOME=/tmp \
  -e GIT_CONFIG_COUNT=1 \
  -e GIT_CONFIG_KEY_0=safe.directory \
  -e GIT_CONFIG_VALUE_0="$repository_root" \
  -v "$docker_socket:$docker_socket" \
  -v "$repository_root:$repository_root" \
  -v "$git_common_dir:$git_common_dir" \
  -w "$repository_root" \
  test-runner python scripts/prepare_pr_body.py "$@"
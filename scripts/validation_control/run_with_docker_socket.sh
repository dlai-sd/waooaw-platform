#!/bin/sh
set -eu

docker_socket=${DOCKER_SOCKET:-/var/run/docker.sock}

if [ ! -S "$docker_socket" ] || [ ! -r "$docker_socket" ] || [ ! -w "$docker_socket" ]; then
    printf '%s\n' 'Docker socket is required and must be readable and writable' >&2
    exit 2
fi
if [ "$#" -eq 0 ]; then
    printf 'usage: %s COMMAND [ARG ...]\n' "$0" >&2
    exit 2
fi

DOCKER_GID=$(stat -c '%g' "$docker_socket")
DOCKER_SOCKET=$docker_socket
export DOCKER_GID DOCKER_SOCKET

exec "$@"
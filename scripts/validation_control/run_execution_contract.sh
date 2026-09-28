#!/bin/sh
set -eu

: "${WC106_EXECUTION_NAMESPACE:?execution namespace is required}"
: "${WC106_GATE_ID:?gate identity is required}"
: "${WC106_EVIDENCE_PATH:?host-visible evidence path is required}"
: "${WC106_EVIDENCE_TOKEN:?evidence token is required}"
: "${WC106_DOCKER_SOCKET_REQUIRED:?socket requirement is required}"
: "${HOME:?runner HOME is required}"

test "$(id -u)" = "${WC106_EXPECTED_UID:-1000}"
test -r /workspace/validation/engineering-validation.yaml
test -d /workspace/test-results
test -w /workspace/test-results
test -d /tmp
test -w /tmp
mkdir -p "$HOME"
test -w "$HOME"
home_probe="$HOME/.wc106-home-probe.$$"
printf '%s\n' "$WC106_EVIDENCE_TOKEN" > "$home_probe"
test "$(cat "$home_probe")" = "$WC106_EVIDENCE_TOKEN"
rm "$home_probe"

probe_root="/tmp/wc106-${WC106_EXECUTION_NAMESPACE}-${WC106_GATE_ID}"
cache_root="$probe_root/cache"
temporary="$probe_root/temporary"
host_probe_root="${WC106_EVIDENCE_PATH}.probe"
host_cache="$host_probe_root/cache"
host_temporary="$host_probe_root/temporary"
evidence_temporary="${WC106_EVIDENCE_PATH}.tmp.$$"
trap 'rm -rf "$probe_root" "$host_probe_root" "$evidence_temporary"' EXIT
mkdir -p "$cache_root" "$temporary"
printf '%s\n' "$WC106_EVIDENCE_TOKEN" > "$cache_root/probe.tmp"
mv "$cache_root/probe.tmp" "$cache_root/probe"
test "$(cat "$cache_root/probe")" = "$WC106_EVIDENCE_TOKEN"
mkdir -p "$host_cache" "$host_temporary"
printf '%s\n' "$WC106_EVIDENCE_TOKEN" > "$host_cache/probe.tmp"
mv "$host_cache/probe.tmp" "$host_cache/probe"
test "$(cat "$host_cache/probe")" = "$WC106_EVIDENCE_TOKEN"
printf '%s\n' "$WC106_EVIDENCE_TOKEN" > "$host_temporary/probe"
rm "$host_cache/probe" "$host_temporary/probe"
test ! -e "$host_cache/probe"
test ! -e "$host_temporary/probe"

if [ "$WC106_DOCKER_SOCKET_REQUIRED" = "1" ]; then
    test -S /var/run/docker.sock
    python3 -c 'import socket; connection = socket.socket(socket.AF_UNIX); connection.settimeout(3); connection.connect("/var/run/docker.sock"); connection.sendall(b"GET /_ping HTTP/1.0\r\nHost: docker\r\n\r\n"); response = connection.recv(1024); connection.close(); assert b"200 OK" in response and b"OK" in response'
fi

printf '%s\n' "$WC106_EVIDENCE_TOKEN" > "$evidence_temporary"
mv "$evidence_temporary" "$WC106_EVIDENCE_PATH"
test "$(cat "$WC106_EVIDENCE_PATH")" = "$WC106_EVIDENCE_TOKEN"

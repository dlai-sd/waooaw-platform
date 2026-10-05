#!/bin/sh
set -eu

report_path=$1
specification=$2
base_url=$3
path_regex=$4
authorization_token=$5
depth=$6
check_profile=${7:-standard}

set -- schemathesis --config-file /workspace/validation/schemathesis.toml run "$specification" \
    --url "$base_url" \
    --include-path-regex "$path_regex" \
    --checks all \
    --suppress-health-check=filter_too_much \
    --report junit \
    --report-junit-path "$report_path"

if test "$authorization_token" != "-"; then
    set -- "$@" -H "Authorization:Bearer $authorization_token"
fi
if test "$depth" = smoke; then
    set -- "$@" --phases coverage --max-examples 1
else
    set -- "$@" --max-examples 100
fi
if test "$check_profile" = health; then
    set -- "$@" --exclude-checks not_a_server_error
fi

cd /tmp
exec "$@"
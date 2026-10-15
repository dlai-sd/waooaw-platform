#!/bin/sh
set -eu

repository=$(realpath "$(git rev-parse --show-toplevel)")
suffix=$(printf '%s' "${VALIDATION_NAMESPACE:-$$}" | tr -cd 'a-zA-Z0-9' | tail -c 20)
project="wc123-session-${suffix:-contract}"

cleanup() {
    docker compose --project-directory "$repository" -p "$project" down --volumes >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

docker compose --project-directory "$repository" -p "$project" up -d --wait postgres
container=$(docker compose --project-directory "$repository" -p "$project" ps -q postgres)

if docker logs "$container" 2>&1 | grep -Eq 'ERROR|FATAL'; then
    docker logs "$container" >&2
    exit 1
fi

docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw <<'SQL'
DO $role$
DECLARE
    role_name TEXT;
BEGIN
    FOREACH role_name IN ARRAY ARRAY[
        'business_app',
        'constitutional_app',
        'runtime_app',
        'ai_runtime_app',
        'wbe_app',
        'domain_adapter_app',
        'web_session_app'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN NOBYPASSRLS', role_name);
        END IF;
    END LOOP;
END
$role$;
SQL

schema_present=$(
    docker compose --project-directory "$repository" -p "$project" exec -T postgres \
        psql -At -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
        -c "SELECT to_regclass('web_session.user_generations') IS NOT NULL"
)
if [ "$schema_present" != "t" ]; then
    docker compose --project-directory "$repository" -p "$project" exec -T postgres \
        psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
        < "$repository/infrastructure/postgres/init/55-wc123-web-session.sql"
fi

docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
    < "$repository/tests/postgres/wc123_web_session_contract.sql"

docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw <<'SQL' >/dev/null
SET ROLE web_session_app;
SELECT * FROM web_session.create_session(
    '20000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000002',
    '20000000-0000-0000-0000-000000000003',
    'https://identity.test/realms/waooaw',
    'subject-concurrency',
    'waooaw-web',
    'AAL2',
    clock_timestamp(),
    NULL,
    NULL,
    'envelope-v1',
    decode('0102', 'hex'),
    'handle-v1',
    decode(repeat('91', 32), 'hex'),
    clock_timestamp() + INTERVAL '30 minutes',
    clock_timestamp() + INTERVAL '8 hours',
    'wc123-auth-session-v1'
);
SQL

result_dir=$(mktemp -d)
docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
    -c "SET ROLE web_session_app; SELECT web_session.acquire_refresh_lease(
        '20000000-0000-0000-0000-000000000001', 1,
        '20000000-0000-0000-0000-000000000004', 15
    )" >"$result_dir/lease-one" &
lease_one_pid=$!
docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
    -c "SET ROLE web_session_app; SELECT web_session.acquire_refresh_lease(
        '20000000-0000-0000-0000-000000000001', 1,
        '20000000-0000-0000-0000-000000000005', 15
    )" >"$result_dir/lease-two" &
lease_two_pid=$!
wait "$lease_one_pid"
wait "$lease_two_pid"

lease_winners=$(grep -hxc t "$result_dir/lease-one" "$result_dir/lease-two" | awk '{total += $1} END {print total + 0}')
if [ "$lease_winners" -ne 1 ]; then
    printf 'expected exactly one refresh lease winner, got %s\n' "$lease_winners" >&2
    exit 1
fi

docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw <<'SQL' >/dev/null
SET ROLE web_session_app;
SELECT * FROM web_session.create_session(
    '20000000-0000-0000-0000-000000000010',
    '20000000-0000-0000-0000-000000000011',
    '20000000-0000-0000-0000-000000000012',
    'https://identity.test/realms/waooaw',
    'subject-rotate-revoke',
    'waooaw-web',
    'AAL2',
    clock_timestamp(),
    NULL,
    NULL,
    'envelope-v1',
    decode('0304', 'hex'),
    'handle-v1',
    decode(repeat('92', 32), 'hex'),
    clock_timestamp() + INTERVAL '30 minutes',
    clock_timestamp() + INTERVAL '8 hours',
    'wc123-auth-session-v1'
);
SQL

docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
    -c "SET ROLE web_session_app; SELECT web_session.rotate_handle(
        '20000000-0000-0000-0000-000000000010', 1,
        '20000000-0000-0000-0000-000000000011',
        '20000000-0000-0000-0000-000000000013',
        'handle-v1', decode(repeat('93', 32), 'hex'),
        clock_timestamp() + INTERVAL '30 minutes', NULL
    )" >"$result_dir/rotate" &
rotate_pid=$!
docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
    -c "SET ROLE web_session_app; SELECT web_session.revoke_family(
        '20000000-0000-0000-0000-000000000010',
        'SECURITY_EVENT',
        '20000000-0000-0000-0000-000000000014'
    )" >"$result_dir/revoke" &
revoke_pid=$!
wait "$rotate_pid"
wait "$revoke_pid"

converged=$(
    docker compose --project-directory "$repository" -p "$project" exec -T postgres \
        psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
        -c "SELECT state = 'REVOKED'
              AND token_envelope IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM web_session.session_handles
                   WHERE family_id = '20000000-0000-0000-0000-000000000010'
                     AND state = 'ACTIVE'
              )
              FROM web_session.session_families
             WHERE family_id = '20000000-0000-0000-0000-000000000010'"
)
rm -rf -- "$result_dir"
if [ "$converged" != "t" ]; then
    printf '%s\n' 'concurrent rotate and revoke did not converge to restrictive state' >&2
    exit 1
fi

backup_started_at=$(date +%s)
docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    pg_dump -Fc -U waooaw -d waooaw -f /tmp/wc123-session.dump
backup_completed_at=$(date +%s)
backup_age_seconds=$((backup_completed_at - backup_started_at))
if [ "$backup_age_seconds" -gt 300 ]; then
    printf 'session backup age exceeded RPO: %s seconds\n' "$backup_age_seconds" >&2
    exit 1
fi

docker compose --project-directory "$repository" -p "$project" restart postgres >/dev/null
docker compose --project-directory "$repository" -p "$project" up -d --wait postgres >/dev/null
persistent=$(
    docker compose --project-directory "$repository" -p "$project" exec -T postgres \
        psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
        -c "SELECT count(*) = 1
              FROM web_session.session_families
             WHERE family_id = '20000000-0000-0000-0000-000000000001'
               AND state = 'ACTIVE'"
)
if [ "$persistent" != "t" ]; then
    printf '%s\n' 'persistent UAT restart did not retain the active session row' >&2
    exit 1
fi

docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    createdb -U waooaw wc123_session_restore
docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    pg_restore -U waooaw -d wc123_session_restore /tmp/wc123-session.dump
docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d wc123_session_restore \
    -c "SELECT * FROM web_session.sanitize_restored_sessions(
        'RESTORE_EPOCH',
        '20000000-0000-0000-0000-000000000020',
        clock_timestamp()
    )" >/dev/null
restore_sanitized=$(
    docker compose --project-directory "$repository" -p "$project" exec -T postgres \
        psql -qAt -v ON_ERROR_STOP=1 -U waooaw -d wc123_session_restore \
        -c "SELECT count(*) = 0
              FROM web_session.session_families
             WHERE state = 'ACTIVE'
                OR token_envelope IS NOT NULL
                OR refresh_lease_owner IS NOT NULL"
)
if [ "$restore_sanitized" != "t" ]; then
    printf '%s\n' 'traffic-isolated restore retained active session authority' >&2
    exit 1
fi

if docker compose --project-directory "$repository" -p "$project" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw \
    -c 'SET ROLE web_session_app; SELECT family_id FROM web_session.session_families;' \
    >/dev/null 2>&1; then
    printf '%s\n' 'web_session_app unexpectedly read session_families directly' >&2
    exit 1
fi

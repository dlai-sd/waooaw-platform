#!/bin/sh
# Apply new additive init files as the WC-177 update principal through PgBouncer.
#
# Runs in the pinned postgres image (psql, sh, tar, base64, sha256sum) as job-<env>-wc124-database-update
# and in scripts/wc124_init_chain_local.sh against a local PgBouncer. Inputs (environment):
#   DATABASE_URL             postgresql:// URL of database_updater (Key Vault secret in the job)
#   UPDATE_PAYLOAD_B64       base64 gzip tar of the pending files
#   UPDATE_MANIFEST          sha256sum-format manifest (trailing newline removed)
#   UPDATE_MANIFEST_SHA256   digest of the manifest text, bound by the plan step
#   UPDATE_LOCK_RETRIES      attempts per file on a lock timeout (default 3)
#   UPDATE_LOCK_PAUSE_SECONDS pause between lock-timeout attempts (default 20)
# Each file and its ledger row commit in one transaction. A changed digest, a file not declared
# `-- wc177-apply: update` or any failure stops the job with a non-zero status and the reason.
# Constitutional basis: C-005 (Evidence First), C-026, C-059
set -eu

: "${DATABASE_URL:?}" "${UPDATE_PAYLOAD_B64:?}" "${UPDATE_MANIFEST:?}" "${UPDATE_MANIFEST_SHA256:?}"
LOCK_RETRIES="${UPDATE_LOCK_RETRIES:-3}"
LOCK_PAUSE="${UPDATE_LOCK_PAUSE_SECONDS:-20}"
LEDGER=wc124_provisioning.init_chain_ledger
EXPECTED_MEMBERSHIPS="bp_owner,wbe_owner"
started=$(date +%s)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

fail() {
  echo "WC177_UPDATE_REFUSED $1" >&2
  exit 1
}

value() {
  psql "$DATABASE_URL" --no-psqlrc -X -At --set ON_ERROR_STOP=1 -c "$1" < /dev/null
}

manifest_digest=$(printf '%s\n' "$UPDATE_MANIFEST" | sha256sum | cut -d ' ' -f 1)
[ "$manifest_digest" = "$UPDATE_MANIFEST_SHA256" ] || fail "manifest digest differs from the plan"
printf '%s\n' "$UPDATE_MANIFEST" > "$work/manifest"
LC_ALL=C sort -k 2 "$work/manifest" > "$work/manifest.sorted"
mkdir "$work/files"
printf '%s' "$UPDATE_PAYLOAD_B64" | base64 -d | tar -xzf - -C "$work/files"

expected_names=$(awk '{print $2}' "$work/manifest.sorted")
actual_names=$(cd "$work/files" && LC_ALL=C ls -1)
[ "$expected_names" = "$actual_names" ] || fail "payload files differ from the manifest"

while read -r digest name; do
  printf '%s' "$name" | grep -Eq '^[0-9A-Za-z._-]+[.]sql$' || fail "unsafe file name $name"
  actual=$(sha256sum "$work/files/$name" | cut -d ' ' -f 1)
  [ "$actual" = "$digest" ] || fail "$name digest differs from the manifest"
  header=$(grep -m 1 -v '^[[:space:]]*$' "$work/files/$name" || true)
  [ "$header" = "-- wc177-apply: update" ] || fail "$name is not declared '-- wc177-apply: update'"
done < "$work/manifest.sorted"

login_owned_objects() {
  value "SELECT (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                  JOIN pg_roles r ON r.oid = c.relowner
                  WHERE r.rolcanlogin AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'wc124_provisioning')
                    AND n.nspname !~ '^pg_')
              + (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                  JOIN pg_roles r ON r.oid = p.proowner
                  WHERE r.rolcanlogin AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'wc124_provisioning')
                    AND n.nspname !~ '^pg_')"
}

login=$(value "SELECT session_user")
owned_before=$(login_owned_objects)
applied=""
skipped=""
attempts_total=0

while read -r digest name; do
  recorded=$(value "SELECT sha256 FROM $LEDGER WHERE file_name = '$name'")
  if [ "$recorded" = "$digest" ]; then
    skipped="$skipped\"$name\","
    continue
  fi
  [ -z "$recorded" ] || fail "$name was applied with a different digest ($recorded)"
  attempt=1
  while :; do
    attempts_total=$((attempts_total + 1))
    if psql "$DATABASE_URL" --no-psqlrc -X -q --set ON_ERROR_STOP=1 --single-transaction \
      -f "$work/files/$name" \
      -c "RESET ROLE" \
      -c "INSERT INTO $LEDGER (file_name, sha256) VALUES ('$name', '$digest')" \
      > "$work/out" 2> "$work/err" < /dev/null; then
      break
    fi
    if grep -q 'lock timeout' "$work/err" && [ "$attempt" -lt "$LOCK_RETRIES" ]; then
      echo "WC177_UPDATE_LOCK_TIMEOUT $name attempt $attempt of $LOCK_RETRIES; retrying in ${LOCK_PAUSE}s" >&2
      attempt=$((attempt + 1))
      sleep "$LOCK_PAUSE"
      continue
    fi
    cat "$work/err" >&2
    echo "WC177_UPDATE_FAILED $name after $attempt attempt(s)" >&2
    # Best effort: only sessions the update principal may see are listed.
    value "SELECT pid, usename, state, left(regexp_replace(query, '[[:space:]]+', ' ', 'g'), 200)
           FROM pg_stat_activity
           WHERE datname = current_database() AND pid <> pg_backend_pid() AND state <> 'idle'" >&2 || true
    exit 1
  done
  applied="$applied\"$name\","
done < "$work/manifest.sorted"

# Read-only verification as the update principal (WC177-R008).
ledger_mismatches=0
while read -r digest name; do
  recorded=$(value "SELECT sha256 FROM $LEDGER WHERE file_name = '$name'")
  [ "$recorded" = "$digest" ] || ledger_mismatches=$((ledger_mismatches + 1))
done < "$work/manifest.sorted"
owned_after=$(login_owned_objects)
health_tables=$(value "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'identity' AND c.relkind = 'r'
    AND c.relname IN ('registrations','idempotency_ledger','accounts','login_methods','actor_bindings','memberships','lifecycle_operations','provider_link_projections')")
memberships=$(value "SELECT COALESCE(string_agg(r.rolname, ',' ORDER BY r.rolname), '') FROM pg_auth_members m
  JOIN pg_roles r ON r.oid = m.roleid WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = session_user)")
privileged=$(value "SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolbypassrls FROM pg_roles WHERE rolname = session_user")

[ "$ledger_mismatches" = 0 ] || fail "ledger rows differ from the repository digests"
[ "$owned_after" -le "$owned_before" ] || fail "objects owned by a login role increased from $owned_before to $owned_after"
[ "$health_tables" = 8 ] || fail "Business Platform identity object set is incomplete ($health_tables of 8)"
[ "$memberships" = "$EXPECTED_MEMBERSHIPS" ] || fail "update principal memberships are '$memberships'"
[ "$privileged" = f ] || fail "update principal holds superuser, CREATEROLE, CREATEDB or BYPASSRLS"

finished=$(date +%s)
echo "WC177_UPDATE_RESULT {\"schema\":\"waooaw.wc177-database-update-result/v1\",\"login\":\"$login\",\"applied\":[${applied%,}],\"skipped\":[${skipped%,}],\"attempts\":$attempts_total,\"login_owned_objects_before\":$owned_before,\"login_owned_objects_after\":$owned_after,\"identity_tables\":$health_tables,\"memberships\":\"$memberships\",\"seconds\":$((finished - started)),\"status\":\"passed\"}"

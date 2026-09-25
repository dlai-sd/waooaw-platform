#!/bin/sh
# Implements: architecture/reference/components/identity-boundary.md §12.1 Environment and deployment qualification
# Constitutional basis: C-023 (Evidence First), C-059 (Implementation Traceability)

set -eu

if [ -n "${POSTGRES_PASSWORD:-}" ]; then
  export ConnectionStrings__DefaultConnection="Host=localhost;Port=5432;Database=${POSTGRES_DB:-waooaw};Username=${POSTGRES_USER:-postgres};Password=$POSTGRES_PASSWORD"
fi

if [ "${WAOOAW_DEMO_DATABASE_BOOTSTRAP:-false}" = "true" ]; then
  : "${POSTGRES_USER:?POSTGRES_USER is required for Demo database bootstrap}"
  : "${POSTGRES_DB:?POSTGRES_DB is required for Demo database bootstrap}"
  export PGHOST="${PGHOST:-localhost}"
  export PGPORT="${PGPORT:-5432}"

  attempt=0
  until pg_isready --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
      echo "Demo PostgreSQL did not become ready for migration" >&2
      exit 1
    fi
    sleep 1
  done

  bundle_digest=$(
    for migration in /app/postgres-init/*; do
      sha256sum "$migration"
    done | sha256sum | cut -d ' ' -f 1
  )
  psql --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set ON_ERROR_STOP=1 --command "
      CREATE TABLE IF NOT EXISTS public.waooaw_demo_schema_bootstrap (
        singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
        bundle_digest char(64) NOT NULL,
        state text NOT NULL CHECK (state IN ('in_progress', 'complete')),
        applied_at timestamptz
      )" >/dev/null
  bootstrap_state=$(psql --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set ON_ERROR_STOP=1 --tuples-only --no-align \
    --command "SELECT bundle_digest || ':' || state FROM public.waooaw_demo_schema_bootstrap WHERE singleton")

  if [ "$bootstrap_state" = "$bundle_digest:complete" ]; then
    echo "Demo schema bundle already applied; skipping bootstrap"
  elif [ -n "$bootstrap_state" ]; then
    echo "Demo schema bootstrap state does not match this image; recreate the disposable Demo database" >&2
    exit 1
  else
    psql --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      --set ON_ERROR_STOP=1 --command "
        INSERT INTO public.waooaw_demo_schema_bootstrap (bundle_digest, state)
        VALUES ('$bundle_digest', 'in_progress')" >/dev/null

    for migration in /app/postgres-init/*; do
      case "$migration" in
        *.sql)
          psql --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" \
            --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1 --file "$migration" >/dev/null
          ;;
        *.sh)
          PGHOST="$PGHOST" PGPORT="$PGPORT" bash "$migration" >/dev/null
          ;;
      esac
    done

    psql --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
      --set ON_ERROR_STOP=1 --command "
        UPDATE public.waooaw_demo_schema_bootstrap
        SET state = 'complete', applied_at = now()
        WHERE singleton AND bundle_digest = '$bundle_digest'" >/dev/null
  fi

  psql --host "$PGHOST" --port "$PGPORT" --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set ON_ERROR_STOP=1 --tuples-only --no-align \
    --command "SELECT to_regclass('identity.idempotency_ledger') IS NOT NULL AND to_regclass('identity.accounts') IS NOT NULL" \
    | grep -qx t
fi

exec dotnet BusinessPlatform.dll
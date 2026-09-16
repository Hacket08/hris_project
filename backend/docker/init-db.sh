#!/usr/bin/env bash
# Runs once, automatically, the first time the Postgres container's data
# volume is initialized (docker-entrypoint-initdb.d convention). Creates the
# restricted application role with LOGIN + password from env vars, so the
# password never appears in a migration or in version control.
set -euo pipefail

: "${HRIS_APP_DB_USER:?HRIS_APP_DB_USER must be set}"
: "${HRIS_APP_DB_PASSWORD:?HRIS_APP_DB_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${HRIS_APP_DB_USER}') THEN
      CREATE ROLE ${HRIS_APP_DB_USER} WITH LOGIN PASSWORD '${HRIS_APP_DB_PASSWORD}';
    ELSE
      ALTER ROLE ${HRIS_APP_DB_USER} WITH LOGIN PASSWORD '${HRIS_APP_DB_PASSWORD}';
    END IF;
  END
  \$\$;

  GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO ${HRIS_APP_DB_USER};
  GRANT USAGE ON SCHEMA public TO ${HRIS_APP_DB_USER};
EOSQL

#!/usr/bin/env bash
set -e

echo "Creating Airflow database/user if necessary..."

psql \
  --username "$POSTGRES_USER" \
  --dbname postgres \
  --set=airflow_user="$AIRFLOW_DB_USER" \
  --set=airflow_password="$AIRFLOW_DB_PASSWORD" \
  --set=airflow_db="$AIRFLOW_DB_NAME" <<'EOSQL'

SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'airflow_user',
    :'airflow_password'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_roles
    WHERE rolname = :'airflow_user'
)
\gexec

SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'airflow_db',
    :'airflow_user'
)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = :'airflow_db'
)
\gexec

EOSQL

echo "Airflow database/user initialization complete."

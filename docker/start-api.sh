#!/bin/sh
# Start the API: bring the database schema up to date, then serve.
# Set RUN_MIGRATIONS=false to skip the migration step (for example when
# migrations are run separately before a deploy).
set -e

if [ "${RUN_MIGRATIONS:-true}" != "false" ]; then
    python -m app.db.migrate
fi

exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000

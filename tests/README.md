# Tests

The suite characterizes what the application does **today** so it can be
refactored safely: a change that alters behaviour shows up as a failing test or
a snapshot diff. Known defects are recorded as-is; see [KNOWN_BUGS.md](KNOWN_BUGS.md).

## Layout

| Directory | What it pins | Needs |
| --- | --- | --- |
| `contract/` | OpenAPI schema and routes, Celery task names, routes and beat schedule, ORM metadata, Alembic revision graph, configuration resolution, import-time behaviour of every module | nothing |
| `golden/` | Prompt text, LLM response parsing, analysis formatting and metrics, CSV parsing and validation, sync transforms | nothing |
| `unit/legacy/` | Hermetic tests carried over from `app/tests/` | nothing |
| `integration/` | Every HTTP endpoint, db_service and other services, analysis/import/sync pipelines, migrations, legacy Postgres suites | a disposable Postgres |

LLMs, Qdrant, Redis and SQL Server are always faked. Manual scripts that need
live services live in `scripts/manual/` and are not collected.

## Running

```bash
# Linux/macOS: pywin32 only ships Windows wheels
grep -v '^pywin32' requirements.txt > /tmp/requirements-linux.txt
pip install -r /tmp/requirements-linux.txt -r requirements-dev.txt

python -m pytest                      # integration tests are skipped
TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/scratch_db python -m pytest
```

`TEST_DATABASE_URL` must point at a **throwaway** database: integration tests
truncate every table, and the migration tests create and drop databases (the
user needs `CREATEDB`). Tests never read `.env` and never use the `DB_*`
settings of your shell.

Markers: `integration` (applied automatically), `live` and `sqlserver`
(deselected by default; select with `-m live` / `-m sqlserver`), and
`known_bug("Bn")`.

## Snapshots

Golden files live in `__snapshots__/` next to each test file. When a change is
*meant* to alter behaviour, regenerate and review the diff before committing:

```bash
python -m pytest path/to/test_file.py --snapshot-update
git diff -- '*__snapshots__*'
```

A missing snapshot fails the run, so CI never records a new baseline silently.

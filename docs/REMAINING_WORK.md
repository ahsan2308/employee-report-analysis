# Remaining work

What is left after the 4.x refactor, as of release 4.1.0 (2026-10-11).

The refactor itself is finished. Before writing this list, release 4.1.0 was
checked against the code before the refactor (commit `4c68392`):

- The full test suite passes (1062 tests, Python 3.12 and 3.13 in CI).
- Every snapshot that changed since `4c68392` (214 of 841) traces to a fix or
  feature in the [changelog](../CHANGELOG.md) or [tests/KNOWN_BUGS.md](../tests/KNOWN_BUGS.md).
- The whole app was run end to end: API, Celery worker, Redis, Postgres,
  vector store and a stand-in Ollama. Every endpoint was exercised: CSV
  imports, employees, reports, weekly/monthly/quarterly analysis,
  visualizations, sync and docs.

No regressions were found. The items below are improvements and loose ends.
None of them worked before the refactor either.

## 1. Defects worth fixing

### 1.1 Soft time limit ignores an overridden hard limit

The soft limit should be 60 s before the hard limit (B11). `config/config.yaml`
sets `task_soft_time_limit: 1740` explicitly, so `app/worker/celery_app.py`
never derives it. If only `CELERY_TASK_TIME_LIMIT` is overridden (for example
to 900), the soft limit stays 1740 and never fires. The worker is then
hard-killed, the run is not marked FAILED, and the task is only cleaned up
later as stale (B1).

**Fix:** remove `task_soft_time_limit` from `config.yaml` so it is derived
from the effective hard limit, or clamp it below the hard limit. Recorded in
`tests/contract/__snapshots__/config_full_overrides.json`.

### 1.2 Supervisor feedback dates given as numbers become 1970 dates

In `SupervisorFeedbackCSVRow` (`app/services/csv/row_models.py`), Pydantic
reads an integer `From`/`To` (such as `20240301`) as Unix epoch seconds.
`check_period_date` then accepts it as 1970-08-23. Before 4.1.0 this crashed.
Now it stores a wrong date.

- **CSV uploads:** not affected; they read every cell as text.
- **Sync:** affected only if a SQL Server source column holds dates as INT.

**Fix:** reject values that are neither text nor a date in
`check_period_date`. Recorded in
`tests/golden/imports_sync/__snapshots__/schema_supervisor_dates__From.json`
and `__To.json` (case `int`).

### 1.3 Invalid upload options return 500

`POST /imports/upload` with an unknown `file_format` or `processing_mode`
answers 500 "Error processing upload". It should answer 400 or 422 and list
the allowed values (`app/api/imports.py`).

## 2. Behaviour that could be improved

| Item | Today | Possible change |
| --- | --- | --- |
| Empty `Sub_Entities_Content` cell in vision data | The row is rejected ("Input should be a valid string") | Treat an empty cell as no sub-entities |
| Monthly/quarterly analysis with a missing field | `GET /analyses/monthly/...` and `/quarterly/...` return 500 if the stored JSON lacks a field the response model requires. The real LLM call is constrained by the schema, so this needs a malformed answer | Validate the LLM answer before storing it, or make the response fields optional |
| Import with `stop_on_error` | Valid rows in the chunk before the stop are saved, but the job reports 0 successful rows | Make it all-or-nothing, or count the saved rows |
| LLM answers that are a bare number or a list | Accepted as a result | Treat them as "no usable JSON" (like B6) |
| Weekly prompt sub-entity names that the main entity lacks | Shown as `Name: 1 ()` | Omit the empty `()` |

## 3. Documentation loose ends

- **CHANGELOG** has no entry for:
  - the B1–B3 status code changes;
  - the 500 messages that no longer include internal errors;
  - dispatch-failure handling;
  - ISO-year week labels;
  - the heatmap `employee_id`/`department` filters;
  - integer ratings scoring 0.5 instead of crashing.
- **Stale test comment** in `tests/integration/api/test_visualizations.py` (in
  `HEATMAP_FILTER_CASES`): it says heatmaps ignore `employee_id`/`department`,
  but they filter by them now.

## 4. Security (deferred)

- API key authentication on every endpoint.
- A decision on the CORS default: `CORS_ALLOW_ORIGINS` is `*` today
  (`app/api/main.py`).
- Make the SQL Server certificate check a setting. `TrustServerCertificate=yes`
  is hard-coded in `app/integrations/sqlserver/connector.py`.

## 5. Manual steps on GitHub and deployment

These need repository access that automation here does not have:

- **Tag the releases:**
  ```sh
  git tag v4.0.0 42a15ad && git tag v4.1.0 8f3c630 && git push origin v4.0.0 v4.1.0
  ```
- **Clean up branches:** delete the merged `claude/...` branches, then turn on
  *Settings → General → Automatically delete head branches*.
- **Deploy 4.1.0:** follow "Upgrading from 4.0.0" in the [changelog](../CHANGELOG.md).
  The API container now runs migrations on start unless `RUN_MIGRATIONS=false`.

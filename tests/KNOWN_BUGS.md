# Known bugs

Open defects are **locked in** by the characterization suite exactly as they
behave today. Each fix is a separate change that updates the affected snapshots
on purpose and moves the bug to the Fixed table.

Tests tied to an open bug carry `@pytest.mark.known_bug("Bn")`; find them with
`grep -rn 'known_bug("B8")' tests`. A strict `xfail` is used only where an existing
test asserted the correct behaviour (it flips red once the bug is fixed).

## Catalogue

None open. New defects found by the characterization suite get the next ID (B17).

## Fixed

| ID | Bug | Fix |
| --- | --- | --- |
| B1 | The duplicate-task guard marked every PENDING/RUNNING task FAILED when no analysis existed yet, so duplicates were never prevented | An in-flight task is returned and nothing new is dispatched. Only a task active for longer than twice the Celery hard time limit (at least an hour) is marked FAILED and replaced (`integration/services/test_task_service.py`, `integration/api/test_analyses.py`) |
| B2 | `GET /sync/history?is_full_sync=…` returned 500; an unknown `sort_by` returned 500 | The flag is compared as a JSON boolean, with a missing flag counted as incremental (as the response reports it). An unknown `sort_by` returns 400 listing the valid fields (`integration/api/test_sync.py`) |
| B3 | 404s were re-raised as 500 by a broad `except Exception` in the analyses and tasks routers; a missing task returned 422 from `/result` | HTTPExceptions pass through. A missing task returns 404 from both task endpoints; `TaskNotFoundError` subclasses `ValueError`, so existing callers still catch it (`integration/api/test_analyses.py`, `integration/api/test_tasks.py`) |
| B4 | The vision descriptions dict had 6 duplicate keys; later entries silently replaced earlier ones | Descriptions are kept per main entity (`SUB_ENTITY_DESCRIPTIONS_BY_ENTITY`) and looked up by the item's `main_entity`; the flat `SUB_ENTITY_DESCRIPTIONS` is unchanged for entities missing from the catalog and for callers that pass their own mapping (`golden/analysis/test_golden_additional_services.py`) |
| B5 | Quarterly defaults were typos (`"stble"`, `"mdium"`) that reached prompts; leftover debug `print()`s | `"stable"`/`"medium"`; the prints are gone (`golden/analysis/test_golden_quarterly_analysis_db_service.py`, `unit/legacy/test_quarterly_analysis_db_service.py`) |
| B6 | LLM providers swallowed errors and returned `""`/`None`, so retries never fired and empty or default analyses were stored as COMPLETED | Providers raise on transport and HTTP errors; `generate_text` retries them and raises the last one; an answer without usable JSON is an error. The weekly task now checks for it like the monthly and quarterly ones, so the run is FAILED and nothing is stored (`integration/pipelines/test_analysis_tasks.py`, `golden/prompts/test_llm_service.py`, `unit/test_llm_provider_errors.py`) |
| B7 | `setup_collection` deleted the Qdrant collection when the embedding probe failed, the vector size differed, or Qdrant could not describe the collection | It never deletes now: a mismatch or an unreachable embedding service returns False and leaves the collection untouched (`integration/pipelines/test_vector_store_service.py`) |
| B8 | `ConfigProvider.get(key, section=…)` read the env var named by the bare key, so `HOST`, `PORT`, `MODEL`, `MODE`, `TYPE`, `ENABLED` overrode Redis, Qdrant and LLM settings | With a section, the env var is the section path and key: `REDIS_HOST`, `VECTOR_DB_COLLECTION_NAME`, `VECTOR_DB_BATCH_PROCESSING_ENABLED`, `LLM_MODEL` (`ConfigProvider.env_var_name`); without one it is the key (`contract/test_config_contract.py`) |
| B9 | `hasattr(end, …)` tested the group end instead of `week_end`; a string `week_end` raised AttributeError | The check uses `week_end` (`golden/analysis/test_golden_additional_services.py`) |
| B10 | Chart annotation options were configured but the annotation plugin was never loaded | `visualizations.html` loads `chartjs-plugin-annotation` 3.0.1, the release for Chart.js 4 (the vendored 1.4.0 targeted Chart.js 3); the average lines render (checked in headless Chromium) |
| B11 | Celery `task_time_limit=300` hard-killed long LLM runs, leaving the BackgroundTask RUNNING forever | The hard limit is 30 minutes. A soft limit (default: 60 s earlier, `task_soft_time_limit` / `CELERY_TASK_SOFT_TIME_LIMIT`) raises inside the task, which marks the run FAILED. A task killed anyway is replaced as stale (B1) (`integration/pipelines/test_analysis_tasks.py`, `contract/test_config_contract.py`) |
| B12 | The shared Qdrant client was disconnected by any `with vector_store:` exit, so concurrent searches could lose it | Open `with` blocks are counted; the client is closed when the last one exits (`unit/test_qdrant_connection_sharing.py`) |
| B13 | Full prompts, which contain report text, were logged at INFO (and report text at DEBUG) | Only prompt lengths are logged; similar-report data and formatted vision data are no longer logged (`golden/prompts/test_llm_service.py`) |
| B14 | `ConfigProvider` converted env values `"1"`/`"0"` to booleans, so `PORT=1` became `True` | Only `true`/`false`/`yes`/`no` become booleans; `"1"`/`"0"` are numbers (`contract/test_config_contract.py`) |
| B15 | Every quarterly prompt build wrote `generated_quarterly_prompt.txt` into the working directory and printed to stdout | Removed, with the commented-out weekly and monthly equivalents (`golden/prompts/test_quarterly_prompt.py`, `integration/pipelines/test_analysis_tasks.py`) |
| B16 | `alembic upgrade head` could not build an empty database: the history assumes tables created outside migrations (and creates `sync_history` twice) | On an empty database, `upgrade head` creates the current schema and stamps head (Alembic's "from scratch" recipe, in `migrations/env.py`); databases with a version keep running the revisions (`integration/test_migrations.py`) |

## Other observations

Found while writing the characterization tests and snapshotted as-is. Open ones
are candidates for the bug-fix track; fixed ones are listed at the end.

**Analysis and visualizations**
- Quarterly `analyze_trend` reports "improving" for almost any series with positive values, including falling ones (`quarterly_analysis_db_service.py:250-271`).
- Week labels combine the calendar year with the ISO week, so 2024-12-30 is "2024-W1" (`visualization_service.py:89`). Vision data is grouped by ISO week without a year (`db_service.py:620`).
- Sentiment trends and heatmaps have no `ORDER BY`. Impact trends sort labels as text, so "2025-W10" comes before "2025-W2" (`visualization_service.py:122-175`, `:717`).
- Visualization results are cached for 5 minutes as shared mutable objects. Heatmaps ignore `employee_id` and `department`.
- The quarterly prompt builds weekly ranges with 7 days, the weekly prompt with 6. Weeks are matched to months by month number regardless of year (`structured_prompts.py:1959,1973`).
- `get_complete_reports_by_ids` returns rows in `set()` order, so the order of similar reports in prompts can vary (`db_service.py:28`).

**CSV import**
- One model-level validation error (From after To) raises IndexError and fails the whole chunk, valid rows included (`employee_report_processor.py:230`).
- A dry run still writes to the database and the vector store (`csv_import_service.py:412-414`).
- Row numbers drift after the first chunk (`start_row_number + idx` in all four processors). `processed_rows` stays 0 except for supervisor feedback.
- A failed vector upsert is reported as a successful import, and re-imports duplicate vectors and `qdrant_mappings` rows (`employee_report_processor.py:405`).
- Dates without `/` or `-` raise UnboundLocalError instead of a validation error, and date rules differ between the four row models (`csv_import_schema.py:187,611`).

**SQL Server connector**
- The password is put into the ODBC connection string unescaped. There is a hard-coded default password. Substring blocklists reject harmless names such as "LastUpdated" and hosts containing "sp_" (`sqlserver_connector.py:209,327,855`).

### Fixed observations

**Sync and API**
- A failed Celery dispatch marks the new sync rows (all four for a full sync) and import jobs FAILED with the reason, instead of leaving PENDING rows that blocked new triggers or never finished (`integration/api/test_sync.py`, `integration/api/test_imports.py`).
- An aborted sync keeps the row errors it collected (`error_details`, `error_count`). Single-type sync tasks report the real records queried and synced (they read `sync_metadata`, which holds only processor metrics) (`integration/pipelines/test_sync_pipeline.py`). Rows written before an abort stay, as before: the sync timestamp does not advance, so the next run upserts them again.
- 500 responses carry a fixed message; the exception (SQL, parameters, broker errors) is logged instead of returned (`integration/api/*`).
- An analysis task with the wrong task type is marked FAILED with the reason (`integration/pipelines/test_analysis_tasks.py`).
- `GET /imports/{id}` reports the stored error count without writing it back (`integration/api/test_imports.py`, `integration/services/test_csv_import_service.py`).

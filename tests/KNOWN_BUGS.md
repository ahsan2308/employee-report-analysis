# Known bugs (characterized, not fixed)

The refactor must not change behaviour, so these defects are **locked in** by the
characterization suite exactly as they behave today. Each fix is a separate,
individually approved change that updates the affected snapshots on purpose.

Tests tied to a catalogued bug carry `@pytest.mark.known_bug("Bn")`; find them with
`grep -rn 'known_bug("B5")' tests`. A strict `xfail` is used only where an existing
test asserted the correct behaviour (it flips red once the bug is fixed).

## Catalogue

| ID | Bug | Where | Characterized in |
| --- | --- | --- | --- |
| B1 | The duplicate-task guard marks every PENDING/RUNNING task FAILED when no analysis exists yet, which is always the case while it runs, so duplicates are never prevented | `app/services/task_service.py:18,48,89` | `integration/services/test_task_service.py`, `integration/api/test_analyses.py` |
| B2 | `GET /sync/history?is_full_sync=…` returns 500 (`dialect.BOOLEAN` does not exist); an unknown `sort_by` also returns 500 | `app/api/sync_routes.py:665,673` | `integration/api/test_sync.py` |
| B3 | 404s are re-raised as 500 by a broad `except Exception` in the analyses and tasks routers; a missing task returns 422 | `app/api/analyses.py`, `app/api/tasks.py` | `integration/api/test_analyses.py`, `integration/api/test_tasks.py` |
| B4 | The vision descriptions dict has 6 duplicate keys; later entries silently replace earlier ones | `app/services/additional_services.py:43` | `golden/analysis/test_golden_additional_services.py` |
| B5 | Quarterly defaults are typos (`"stble"`, `"mdium"`) that can reach prompts; leftover debug `print()`s | `app/services/quarterly_analysis_db_service.py:49-73,118` | `golden/analysis/test_golden_quarterly_analysis_db_service.py`, `unit/legacy/test_quarterly_analysis_db_service.py` (strict xfail) |
| B6 | LLM providers swallow errors and return `""`/`None`, so retries never fire and empty or default analyses are stored as COMPLETED | `app/model_host/ollama.py:66`, `app/model_host/vllm.py:124` | `integration/pipelines/test_analysis_tasks.py` |
| B7 | `setup_collection` can delete the Qdrant collection when the embedding probe fails or the vector size differs | `app/services/vector_store_service.py:57-98` | `integration/pipelines/test_vector_store_service.py` |
| B8 | `ConfigProvider.get(key, section=…)` reads the env var named by the bare key, so `HOST`, `PORT`, `MODEL`, `MODE`, `TYPE`, `ENABLED` override Redis, Qdrant and LLM settings | `app/core/config_provider.py:59` | `contract/test_config_contract.py` |
| B9 | `hasattr(end, …)` should test `week_end`; a string `week_end` raises AttributeError | `app/services/additional_services.py:1146` | `golden/analysis/test_golden_additional_services.py` |
| B10 | Chart annotation options are configured but the annotation plugin is never loaded | `frontend/js/visualizations.js` | not automated (frontend) |
| B11 | Celery `task_time_limit=300` hard-kills long LLM runs, leaving the BackgroundTask RUNNING forever | `config/config.yaml` | `contract/test_config_contract.py` (setting only) |
| B12 | The shared Qdrant client is disconnected by any `with vector_store:` exit, so concurrent searches can lose it | `app/vector_store/qdrant_provider.py:167` | not automated (concurrency) |
| B13 | Full prompts, which contain report text, are logged at INFO | `app/services/llm_service.py:290,364`, `app/tasks/analysis_tasks.py:132,396` | `golden/prompts/test_llm_service.py` |
| B14 | `ConfigProvider` converts env values `"1"`/`"0"` to booleans, so `PORT=1` becomes `True` | `app/core/config_provider.py` (`_convert_value`) | `contract/test_config_contract.py` |
| B15 | Every quarterly prompt build writes `generated_quarterly_prompt.txt` into the working directory and prints to stdout ("TODO: REMOVE") | `app/prompts/structured_prompts.py:3132-3140` | `golden/prompts/test_quarterly_prompt.py`, `integration/pipelines/test_analysis_tasks.py` |
| B16 | `alembic upgrade head` cannot build an empty database: the first revision references `employee_reports.reports`, which no migration creates | `migrations/versions/65a702f08ade_*.py` | `integration/test_migrations.py` |

## Other observations

Found while writing the characterization tests and snapshotted as-is. These are
candidates for the bug-fix track; none is fixed.

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
- `GET /imports/{id}` rewrites `error_count` in the database.

**Sync and API**
- If Celery dispatch fails, a PENDING sync row is left behind and blocks new triggers with 409 for 60 minutes; import jobs stay PENDING forever (`sync_routes.py:119-135`, `imports.py:121-137`).
- An aborted sync leaves its rows committed with FAILED status and discards its errors. Single-type sync tasks report 0 records queried and synced (`sync_service.py:944-946`, `sync_tasks.py:119,200,276`).
- Some 500 responses include raw SQL and parameters (`reports.py:61,111`, `imports.py:146-160`).
- An analysis task with the wrong task type leaves its BackgroundTask PENDING forever (`analysis_tasks.py:326,690`).

**SQL Server connector**
- The password is put into the ODBC connection string unescaped. There is a hard-coded default password. Substring blocklists reject harmless names such as "LastUpdated" and hosts containing "sp_" (`sqlserver_connector.py:209,327,855`).

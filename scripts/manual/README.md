# Manual scripts

These files used to live in `app/tests/`. They are kept for reference and ad-hoc
debugging, but they are **not** part of the automated suite (`pytest` only
collects `tests/`): most need live services, have no assertions, or depend on
hardcoded IDs. The automated characterization suite in `tests/` supersedes
their coverage.

Run one from the repository root, e.g. `python scripts/manual/test_providers.py`.

> **Warning: several scripts change or delete real data.** Point them only at a
> disposable environment.
>
> - `test_vector_store.py` deletes the whole `employee_reports` Qdrant collection.
> - `test_vector_store_grouping.py` deletes all reports of employee 3482.
> - `test_batch_operations.py` runs `DELETE FROM qdrant_mappings`.
> - `test_sync_api_endpoints.py` deletes every PENDING/RUNNING sync and recent sync history.
> - `test_jd_sync_with_real_sqlserver.py` deletes job-description data.
> - Most Postgres scripts insert rows and never clean up.

| Needs | Scripts |
| --- | --- |
| Postgres only | `test_create_tables.py`, `test_db_connection.py`, `test_employee_model.py`, `test_reports_postgres.py`, `test_import_models.py` (stale model fields), `test_sync_models.py`, `test_csv_imports_postgres.py`, `test_csv_autodetection.py` |
| Running API at `127.0.0.1:8000` | `test_api_employee.py`, `test_api_reports.py`, `test_csv_import.py`, `test_heatmap.py`, `test_monthly_analysis.py`, `test_jd_csv_upload.py`, `error_fetch_test.py` |
| Ollama / vLLM | `test_providers.py`, `test_structured_output.py`, `test_analysis_storage.py` |
| Qdrant | `test_vector_store.py`, `test_vector_store_grouping.py`, `test_batch_operations.py`, `test_date_filtering.py` |
| SQL Server | `test_sqlserver_connector.py`, `test_server_connectivity.py`, `test_local_sqlserver.py`, `test_jd_sync_service_integration.py`, `test_jd_sync_with_real_sqlserver.py`, `test_full_pipeline_tasks.py` |
| Postgres + Celery | `test_sync_api_endpoints.py` (uses `/trigger/employee-reports`; the real routes use underscores) |
| Nothing (prints output, no assertions) | `test_jd_integration.py`, `test_prompts_comprehensive.py`, `test_quarterly_analysis_prompt.py`, `test_quarterly_vision_data_flow_mock.py`, `test_prompt_generation.py` (expects an older prompt layout) |
| An employee ID argument | `test_quarterly_analysis.py` |

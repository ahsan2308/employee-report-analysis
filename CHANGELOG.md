# Changelog

All notable changes to the Employee Report Analysis System are documented in this file.

---

## Unreleased

### Changed: embedding batch size is applied; unused settings removed

`vector_db.batch_processing.embedding_batch_size` (50) was never read: every
chunk of an import went to the embedding provider in one call. Chunks are now
embedded in calls of at most that many. A failed call fails the whole batch of
reports, as before; a provider error no longer returns empty vectors.
`split_on_failure` and `min_batch_size`, which nothing implemented, are removed
from `config/config.yaml`.

### Changed: faster dry-run imports

A dry run validated each row with a new database session and processor, which
also re-read the existing employee IDs for every supervisor feedback row. It now
validates with the import's own processor, and the job records the detected CSV
type and metrics as a real import does.

### Changed: imports with some failed rows end as `partial`

An import job that imported some rows but had errors on others now ends with
status `partial`, as a sync in the same state does; it used to end as
`completed`. `completed` now means no errors, and `failed` still means errors
with nothing imported. `GET /imports/?status=partial` lists them. The database
check on the status column allows the new value: run `alembic upgrade head`
(revision `a7c3e91d4b52`).

### Fixed: synced rows for a new employee are no longer skipped

Employees are created from their reports, so a vision, job description or
supervisor feedback row for someone whose first report has not been synced yet
was rejected, and the next incremental sync started after it: the row was never
saved unless it changed at the source. Such a row is now read again by later
syncs until its employee exists, for as long as its source timestamp is less
than `SYNC_MISSING_EMPLOYEE_RETRY_DAYS` (default 14) days old. Older rows are
given up on, so an employee who never appears cannot hold syncs back for good.

### Changed: one way to add reports to the vector store

`add_report_to_vector_store` adds a single report and a list of reports the
same way. The one-chunk-at-a-time mode and its switch,
`vector_db.batch_processing.enabled`, are removed. Behaviour changes:

- A failed upsert batch is retried after a growing wait instead of
  immediately: `vector_db.batch_processing.retry.initial_wait_ms` (100) and
  `backoff_factor` (2), which `config.yaml` already listed, are now read.
  `max_attempts` (3) counts every attempt, the first one included.
- A report date is read like other report dates (`2025-03-07`, `03/07/2025`,
  `14/03/2025`, a trailing time). An unreadable date fails the call; it used to
  be stored as the current time, which put the report in the wrong week for
  date-filtered searches.
- A single report with no text is skipped and the call succeeds, as a report
  without text in a list already was; it used to fail the call.

### Fixed: rows a sync could not save are read again

A failed database write in an import or sync batch (or a failed vector store
write for reports) left its rows unsaved without reporting them: the processors
returned "0 saved" with no error, so a sync could finish as `completed`. Each
unsaved row is now reported as a database error, and the sync ends as `partial`
or `failed`. The next incremental sync starts again from the oldest of those
rows, instead of from just after the newest row read, so they are retried
rather than skipped for good. Rows rejected as invalid data still let the sync
move on: correcting one at the source gives it a newer timestamp.

Sync row numbers now follow the order SQL Server returned the rows. A row that
cannot be transformed is reported as a validation error under its own number
and counts toward the error threshold.

### Changed: SQL Server source tables are settings

Each sync reads the table named by its own setting:
`SQLSERVER_TABLE_EMPLOYEE_REPORTS`, `SQLSERVER_TABLE_VISION_DATA`,
`SQLSERVER_TABLE_JOB_DESCRIPTIONS` and `SQLSERVER_TABLE_SUPERVISOR_FEEDBACK`.
The defaults are the table names used so far. Before, each sync took the first
allowed table whose name contained a keyword ("report", "job", "feedback"...),
so adding a table such as `JobReports` to `SQLSERVER_ALLOWED_TABLES` could make
a sync read the wrong one. A configured table must be in
`SQLSERVER_ALLOWED_TABLES` (any letter case), which now defaults to the four
configured tables.

### Changed: vector index parameters in config

The HNSW parameters used when the Qdrant collection is created are now
`vector_db.index.hnsw_m` (32) and `vector_db.index.hnsw_ef_construct` (256) in
`config/config.yaml`. They apply to new collections only. The payload field
names that the indexes, the stored chunks and the search filters share are
defined once, in `app/integrations/vector_store/payload_fields.py`.

---

## [4.0.0] - 2026-10-11 - Restructuring and bug fixes

### Added: version in the API

The OpenAPI schema and `/docs` now show the release (`4.0.0`; was FastAPI's
default `0.1.0`). It is set once, as `__version__` in `app/__init__.py`.

### Changed: OpenAPI enum names

The sync enums in the OpenAPI schema are now named `SyncType` and
`SyncStatus` (were `SyncTypeEnum` and `SyncStatusEnum`): the API uses the
enums the database models define instead of copies. Their values are
unchanged, so requests and responses are the same.

### Changed: date and scoring rules in one place

The calendar and scoring rules that were copied across services, prompts,
repositories and tasks now live once in `app/domain` (`periods.py`,
`scoring.py`, `trends.py`). Where the copies disagreed, the shared version
keeps the more complete behaviour:

- Job description `Assigned_Date` / `End_Date` accept a trailing time
  ("2024-03-01 00:00:00"), as report dates already did.
- The monthly achievement impact average reads every impact format the
  charts read ("8/10", "7.5 (good)", a plain number) and leaves out
  achievements without an impact; they used to count as 0.
- An `impact_score` stored as text ("8") is read instead of stopping the
  monthly data gathering, a `None` weekly sentiment reads as neutral in the
  monthly prompt instead of failing, and a non-numeric month in quarterly
  progress trends is labelled as given instead of failing.

### Changed: settings in one place

Settings that several modules read separately now come from
`app/core/settings.py`: `SYNC_ENABLED`, `SYNC_ERROR_THRESHOLD_PERCENT`, the
Celery task time limit, the sync batch size, the 60-minute stale-sync timeout
and the weekly sync schedule (which `GET /sync/config` now describes from the
same values Celery beat uses). New: `CORS_ALLOW_ORIGINS`, a comma-separated
list of origins for CORS, default `*` as before.

### Changed: log level

The log level is now set by the `LOG_LEVEL` environment variable and defaults
to `INFO`; it was always `DEBUG` before. Set `LOG_LEVEL=DEBUG` for the old
output.

### Fixed: behaviour that differed between duplicated code

- `GET /sync/last-successful/{sync_type}` now counts partial syncs, as the
  incremental sync does when it picks its starting point. It could show an
  older sync than the one actually used.
- `GET /imports/` reports each job's error count from its stored errors, as
  `GET /imports/{job_id}` does; the two could disagree.
- An import that fails as a whole (for example, columns that match no CSV
  type) now stores the reason as a job-level error (row 0) instead of failing
  with no errors listed.
- The CSV type chosen at upload is used. It was stored but ignored: the type
  was always detected from the headers. A file without the chosen type's
  columns fails with a clear error.
- A job description dry run reports unknown employees, like a real import.
- `POST /reports/form` stores report text in the same format as CSV imports
  and syncs ("Tasks Completed: ...", "N/A" for blank fields).
- `GET /tasks/{task_id}/result` returns analyses in the same shape as the
  `/analyses` endpoints (it lacked `avg_sentiment_score` and the defaults for
  empty lists and missing sentiment), keeping `analysis_id`,
  `full_analysis_json` and, for quarterly analyses, `analysis_date`.
- Quarterly metrics score high/medium/low ratings one way everywhere: 3/2/1,
  any letter case, with unrecognised values left out. The three copies
  treated unknown values as 1, as 2, or skipped them.

### Fixed: report form "nothing to report"

`POST /reports/form` rejected every submission without `key_tasks_completed`,
even when `nothing_to_report_reason` was given. A reason alone is now accepted.

### Removed: old import paths

The modules moved during the restructuring no longer have compatibility
re-exports. Update imports as follows:

| Old path | New path |
| --- | --- |
| `app.database` (`get_database`) | `app.db.database` |
| `app.database.postgres_database` | `app.db.postgres` |
| `app.database.mssql_database` | `app.db.mssql` |
| `app.database.sqlserver_connector` | `app.integrations.sqlserver.connector` |
| `app.models.base` | `app.db.base` |
| `app.base.base_db` | `app.db.base_database` |
| `app.base.base_llm` | `app.integrations.llm.base` |
| `app.base.base_embedding` | `app.integrations.embeddings.base` |
| `app.base.base_vector_store` | `app.integrations.vector_store.base` |
| `app.base.base_csv_processor` | `app.services.csv.processors.base` |
| `app.model_host` | `app.integrations.providers` |
| `app.model_host.ollama`, `app.model_host.vllm` | `app.integrations.llm.ollama`, `app.integrations.llm.vllm` |
| `app.model_host.ollama_embedding`, `app.model_host.vllm_embedding` | `app.integrations.embeddings.ollama`, `app.integrations.embeddings.vllm` |
| `app.vector_store` | `app.integrations.vector_store` |
| `app.vector_store.qdrant_provider` | `app.integrations.vector_store.qdrant` |
| `app.services.monthly_analysis_db_service` | `app.services.analysis.monthly_context` |
| `app.services.quarterly_analysis_db_service` | `app.services.analysis.quarterly_context` |
| `app.services.analysis.jd_formatting` | `app.prompts.job_descriptions` |
| `app.services.analysis.vision_formatting` (`filter_vision_data`) | `app.domain.vision_catalog` |
| `app.services.analysis.vision_formatting` (`format_vision_data_for_*`) | `app.prompts.vision` |
| `app.services.db_service` | `app.repositories.reports`, `.vision_data`, `.analyses`, `.employees`, `.job_descriptions`, and `app.domain.periods` |
| `app.services.additional_services` | `app.services.analysis.jd_mapping`, `app.prompts.vision`, `app.prompts.job_descriptions` and `app.domain.vision_catalog` |
| CSV row models in `app.schemas.csv_import_schema` | `app.services.csv.row_models` |

Celery task names, API routes, environment variables and `config/config.yaml`
keys are unaffected by the moves.

---

## [3.1.0] - 2026-01-14 - Supervisor Feedback Data Pipeline

A supervisor feedback data pipeline enabling structured performance assessments with multi-metric rating forms and text responses to be used for employee evaluation.

### 🚀 **New Features**

#### Supervisor Feedback Data Pipeline

**Key Capabilities:**

**1. SQL Server Sync Support**
- Automated synchronization of supervisor feedback forms from SQL Server to PostgreSQL
- Incremental sync (only new/modified records since last sync)
- Full sync (complete data refresh)
- Real-time progress monitoring with detailed metrics

**2. File Import Support**
- Manual import of supervisor feedback evaluation data
- Auto-detection of supervisor feedback file format
- Bulk processing with configurable batch sizes (e.g. 1000 rows per batch)
- Comprehensive error tracking and validation

**3. 3-Table Normalized Database Structure**
- **SupervisorFeedbackForm**: Master/header table storing one record per employee per evaluation period
- **SupervisorFeedbackMetricDefinition**: Reusable metric templates (e.g., Communication Skills, Quality of Work, Team Collaboration)
- **SupervisorFeedbackResponse**: Individual metric ratings and text responses linked to forms and definitions
- JSONB cache for fast denormalized data retrieval
- Cascade delete support maintaining referential integrity

**4. Multi-Row Form Processing**
- Groups denormalized rows (one per metric) into normalized database structure
- Typical form has multiple metric rows with same RO_Form_ID
- Automatic form grouping and validation
- Hybrid response strategy: DELETE+INSERT for complete batches, upsert for split batches (batch idempotency protection)

**5. Dual Metric Types**
- **Rating Questions (Type "R")**: Predefined choices (e.g., "Poor, Fair, Good, Excellent")
- **Text Questions (Type "T")**: Free-form qualitative feedback
- Support for max_value calculation based on possible values count

#### Database Schema

**New Tables:**

**SupervisorFeedbackMetricDefinition:**
- Master data table for metric definitions
- Stores template/schema for each evaluable metric
- Eliminates redundancy across evaluations
- Fields: id (unqiue), section_id, section, metric_id, metric_name, metric_description, metric_type, possible_values, max_value

**SupervisorFeedbackForm:**
- Master/header table for evaluation forms
- One record per employee per evaluation period
- Fields: id (unqiue), ro_form_id (unique), employee_id (FK), from_date, to_date, feedback_cache (JSONB)
- Indexed for efficient querying by employee and date range

**SupervisorFeedbackResponse:**
- Detail table storing individual metric responses
- Links forms to metric definitions with actual values
- Fields: id (unqiue), l_ro_form_metric_id, form_id (FK), metric_definition_id (FK), metric_value
- Supports both rating values and text responses

**PostgreSQL Table Schemas:**

**supervisor_feedback_metric_definitions:**
```sql
CREATE TABLE employee_reports.supervisor_feedback_metric_definitions (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL,
    section VARCHAR(100) NOT NULL,
    metric_id INTEGER NOT NULL UNIQUE,
    metric_name VARCHAR(200) NOT NULL,
    metric_description TEXT,
    metric_type CHAR(1) NOT NULL CHECK (metric_type IN ('R', 'T')),
    possible_values VARCHAR(500),
    max_value INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_supervisor_feedback_metric_definitions_section_id 
ON employee_reports.supervisor_feedback_metric_definitions(section_id);
```

**supervisor_feedback_forms:**
```sql
CREATE TABLE employee_reports.supervisor_feedback_forms (
    id SERIAL PRIMARY KEY,
    ro_form_id INTEGER NOT NULL UNIQUE,
    employee_id INTEGER NOT NULL REFERENCES employee_reports.employees(id) ON DELETE CASCADE,
    from_date DATE NOT NULL,
    to_date DATE NOT NULL,
    feedback_cache JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_supervisor_feedback_forms_employee_id 
ON employee_reports.supervisor_feedback_forms(employee_id);

CREATE INDEX ix_supervisor_feedback_forms_date_range 
ON employee_reports.supervisor_feedback_forms(from_date, to_date);
```

**supervisor_feedback_responses:**
```sql
CREATE TABLE employee_reports.supervisor_feedback_responses (
    id SERIAL PRIMARY KEY,
    l_ro_form_metric_id INTEGER NOT NULL UNIQUE,
    form_id INTEGER NOT NULL REFERENCES employee_reports.supervisor_feedback_forms(id) ON DELETE CASCADE,
    metric_definition_id INTEGER NOT NULL REFERENCES employee_reports.supervisor_feedback_metric_definitions(id) ON DELETE CASCADE,
    text_response TEXT,
    numeric_rating INTEGER,
    max_value INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_supervisor_feedback_responses_form_id 
ON employee_reports.supervisor_feedback_responses(form_id);

CREATE INDEX ix_supervisor_feedback_responses_metric_definition_id 
ON employee_reports.supervisor_feedback_responses(metric_definition_id);
```

**Note:** No need to create these tables in PostgreSQL manually. They are automatically created upon app startup. For the other tables, either use Alembic or Manual Table Deletion followed by Manual Table Creation using app startup to cater for new fields/values & columns in the already existed tables.

**Key Design Decisions:**
- **Cascade Delete**: When an employee is deleted, all their feedback forms and responses are automatically removed
- **Cascade Delete on Forms**: When a form is deleted, all its responses are removed
- **Unique Constraints**: Prevent duplicate forms (ro_form_id) and responses (l_ro_form_metric_id)
- **JSONB Cache**: Stores denormalized form data for fast retrieval without joins
- **Indexed Lookups**: Optimized queries for employee forms, date ranges, and metric definitions
- **Check Constraint**: Ensures metric_type is only 'R' (rating) or 'T' (text)

#### Frontend Enhancements

**Sync Page:**
- New supervisor feedback sync card
- Incremental and full sync trigger buttons
- Last sync timestamp display
- Updated full sync description to include supervisor feedback

**Imports Page:**
- Supervisor feedback CSV type option in dropdown
- Template selector button with detailed column documentation
- Real-time metrics display showing:
  - Forms Created
  - Forms Updated
  - Responses Created
  - Metric Definitions Created
- Complete template section with 18-column definitions table
- Sample data generator with realistic examples (2 rating + 1 text metric)

#### Data Structure

**18 CSV Columns:**

**Form Header Fields** (repeated in every row):
- RO_Form_ID: Unique form identifier (integer)
- L_RO_Form_Metric_ID: Primary key for metric response (integer)
- Employee_ID: Foreign key to employees table (integer)
- Name: Employee name (reference only, not stored)
- Designation: Employee position (accepted but not stored in PostgreSQL)
- BPS: Basic Pay Scale (accepted but not stored in PostgreSQL)
- Office_Hierarchy: Office hierarchy path (accepted but not stored in PostgreSQL)
- Executive_Office: Executive office (accepted but not stored in PostgreSQL)
- From: Feedback period start date (YYYY-MM-DD)
- To: Feedback period end date (YYYY-MM-DD)

**Metric Definition Fields:**
- Section_ID: Section identifier for categorization (integer)
- Section: Section name (e.g., "Performance", "Communication", "Leadership")
- Metric_ID: Unique metric identifier (integer)
- Metric_Title: Metric display name (e.g., "Communication Skills")
- Instructions: Brief explanation/help text (optional)
- Metric_Type: "R" for rating or "T" for text
- Possible_Values: Comma-separated options for ratings (e.g., "Poor, Fair, Good, Excellent")

**Response Data:**
- Value: Supervisor's response (rating label or free text)

**Validation Rules:**
- **L_RO_Form_Metric_ID**: Must be unique across all forms (primary key for responses), positive integer
- **RO_Form_ID**: Positive integer, groups multiple metric rows into single form
- **Employee_ID**: Must reference an existing employee (validated before import)
- **Name**: Employee name for reference (accepted but not stored in PostgreSQL)
- **Designation**: Employee position (accepted but not stored in PostgreSQL)
- **BPS**: Basic Pay Scale (accepted but not stored in PostgreSQL)
- **Office_Hierarchy**: Office hierarchy path (accepted but not stored in PostgreSQL)
- **Executive_Office**: Executive office (accepted but not stored in PostgreSQL)
- **From**: Evaluation period start date, REQUIRED field, accepts formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY
- **To**: Evaluation period end date, REQUIRED field, same format requirements as From
- **Section_ID**: Positive integer for section categorization
- **Section**: Section name, minimum 2 characters
- **Metric_ID**: Positive integer, must be unique within a form
- **Metric_Title**: Metric display name, minimum 3 characters, maximum 200 characters
- **Instructions**: Optional help text, maximum 500 characters
- **Metric_Type**: Must be 'R' (rating) or 'T' (text)
- **Possible_Values**: For rating metrics (Type R), comma-separated options, maximum 500 characters
- **Value**: REQUIRED field, maximum 5000 characters for text responses

**Processing Features:**
- Automatic duplicate handling via upsert on unique constraints
- Bulk processing using PostgreSQL `INSERT ... ON CONFLICT DO UPDATE/NOTHING`
- Pre-validation of employee existence before bulk operations
- Detailed error reporting with row-level information

#### Sync Operations

**Features:**
- **Incremental Sync**: Queries LastModifiedDate column to detect changes since last successful sync
- **Full Sync**: Syncs all records regardless of modification date
- **Batch Processing**: Memory-efficient processing with configurable batch sizes
- **Employee Validation**: Verifies employee existence before processing (caches employee IDs for efficiency)
- **Form Ordering**: Orders by RO_Form_ID to prevent form splitting across batches
- **Error Handling**: Detailed error logging with row number, field name, and error message
- **Metrics Tracking**: Four specific metrics tracked:
  - forms_created: Number of new forms inserted
  - forms_updated: Number of existing forms updated
  - responses_created: Total metric responses created
  - metric_definitions_created: New metric definitions added

**Processing Strategy:**
1. Validate all rows with Pydantic schema
2. Filter for existing employees BEFORE bulk operations
3. Group rows by RO_Form_ID (multiple rows → 1 form)
4. Process metric definitions in bulk (INSERT ... ON CONFLICT DO NOTHING)
5. Process forms in bulk (INSERT ... ON CONFLICT DO UPDATE)
6. Process responses with DELETE+INSERT / UPDATE strategy per form
7. Generate JSONB caches for all forms

**Sync Security:**
- Table whitelisting (only configured tables can be queried)
- Column whitelisting for timestamp columns
- Parameterized queries preventing SQL injection
- Batch size limits preventing memory exhaustion
- Error threshold abort mechanism

#### SQL Server Table Requirements

```sql
CREATE TABLE SupervisorFeedback (
    RecordID INT IDENTITY(1,1) PRIMARY KEY,
    L_RO_Form_Metric_ID INT NOT NULL,
    RO_Form_ID INT NOT NULL,
    Employee_ID INT NOT NULL,
    Name NVARCHAR(100),
    Designation NVARCHAR(100),
    BPS NVARCHAR(20),
    Office_Hierarchy NVARCHAR(200),
    Executive_Office NVARCHAR(100),
    [From] DATE NOT NULL,
    [To] DATE NOT NULL,
    Section_ID INT NOT NULL,
    Section NVARCHAR(100) NOT NULL,
    Metric_ID INT NOT NULL,
    Metric_Title NVARCHAR(200) NOT NULL,
    Instructions NVARCHAR(500),
    Metric_Type CHAR(1) NOT NULL,
    Possible_Values NVARCHAR(500),
    Value NVARCHAR(MAX) NOT NULL,
    LastModifiedDate DATETIME DEFAULT GETDATE()
);

-- Index for efficient incremental sync
CREATE INDEX IX_SupervisorFeedback_LastModifiedDate 
ON SupervisorFeedback(LastModifiedDate);

-- Index for form grouping
CREATE INDEX IX_SupervisorFeedback_RO_Form_ID
ON SupervisorFeedback(RO_Form_ID);

-- Unique constraint for responses
CREATE UNIQUE INDEX UQ_SupervisorFeedback_L_RO_Form_Metric_ID
ON SupervisorFeedback(L_RO_Form_Metric_ID);
```

**Important Sync Notes:**
- Always update `LastModifiedDate` when records change for incremental sync to work
- All rows with same `RO_Form_ID` must have same `Employee_ID`, `From`, and `To` values
- `Metric_Type` must be 'R' or 'T'
- For rating metrics (Type R), `Possible_Values` should contain comma-separated options
- Order by `RO_Form_ID` in SQL Server queries to prevent form splitting across batches

### 🔄 **What's Changed**

#### Full Sync Expansion

**Before:**
- Full sync included 3 data types: employee_reports, vision_data, job_descriptions
- Response returned 3 sync_id values
- Description: "Full sync (employee reports, vision data, and job descriptions)"

**After:**
- Full sync includes 4 data types: employee_reports, vision_data, job_descriptions, **supervisor_feedback**
- Response returns 4 sync_id values (added supervisor_feedback_sync_id)
- Description: "Full sync (employee reports, vision data, job descriptions, and supervisor feedback)"
- Sequential processing updated to handle 4 sync operations

#### Import System Enhancement

**Processor Auto-Detection:**
- File/CSV type auto-detection now recognizes supervisor_feedback format
- ProcessorFactory updated with SupervisorFeedbackProcessor
- 14 required headers checked: L_RO_Form_Metric_ID, RO_Form_ID, Employee_ID, Name, From, To, Section_ID, Section, Metric_ID, Metric_Title, Instructions, Metric_Type, Possible_Values, Value

**CSV Type Options:**
- Added 'supervisor_feedback' to csv_type enum in API endpoints
- Import form dropdown includes new supervisor feedback option
- Template download supports supervisor feedback format

#### Metrics System

**New Metric Structure:**
Unlike standard CSV imports that track `records_created` and `records_updated`, supervisor feedback tracks form-specific metrics:
```json
{
  "forms_created": 2,
  "forms_updated": 0,
  "responses_created": 20,
  "metric_definitions_created": 10,
  "processed_rows": 30,
  "successful_rows": 20
}
```

**Rationale**: Multi-row forms require tracking at form level (not row level) plus metric definition creation.

### 📊 **Technical Details**

#### Processing Strategy

**Denormalized → Normalized Transformation:**
```
CSV (30 rows, same RO_Form_ID) → 1 Form + 10 Metric Definitions + 30 Responses
```

**Step-by-Step:**
1. **Grouping**: Rows with same RO_Form_ID grouped together
2. **Metric Definitions**: Extract unique metrics across all forms (INSERT ... ON CONFLICT DO NOTHING)
3. **Forms**: Upsert forms (INSERT ... ON CONFLICT DO UPDATE SET from_date, to_date)
4. **Responses**: Hybrid strategy for responses
   - **Complete batches or new forms**: DELETE existing responses + INSERT new (clean slate)
   - **Incomplete/split batches**: Detect via existing_count > incoming_count, use upsert strategy
   - **Batch idempotency**: Prevents data loss when forms span multiple batch imports
5. **Cache**: Generate JSONB cache with metric aggregations for fast retrieval

**Hybrid Response Strategy (DELETE+INSERT with Upsert Fallback):**
- **Primary approach (complete batches)**: DELETE+INSERT is cleaner for variable-length metric lists
  - Guarantees no orphaned responses from removed metrics
  - Better performance for typical form sizes (10-30 metrics)
  - Cleaner than individual upserts
- **Fallback approach (incomplete batches)**: Detects when incoming batch has fewer responses than existing form
  - Switches to upsert strategy to prevent data loss
  - Preserves data from previous batch imports
  - Example: Form with 25 metrics split across 3 imports (10 + 10 + 5 rows)
  - Without idempotency: 3rd batch would DELETE all 20 responses from batches 1-2
  - With idempotency: 3rd batch uses upsert, preserves existing data

#### Data Not Stored in PostgreSQL

**Fields Accepted But Not Persisted:**
- Designation
- BPS (Basic Pay Scale)
- Office_Hierarchy
- Executive_Office

**Rationale:**
- Employee master data maintained in Employee table
- Supervisor feedback focuses on performance metrics, not organizational structure
- Reduces data redundancy and update anomalies
- Simplifies sync logic and database schema

**Where These Fields Are Available:**
- Passed through CSV import validation
- Can be logged in error messages for debugging
- Available in SQL Server source system

#### Form Integrity Validation

**Multi-Row Form Checks:**
- All rows with same RO_Form_ID must have same Employee_ID
- All rows must have same From/To date range
- At least one response required per form
- Metric_ID uniqueness within form (no duplicate metrics)

**Employee Validation:**
- Employee_ID must exist in employees table before processing
- Cached lookup for efficiency (single query, used for all rows)
- Validation occurs BEFORE bulk processing begins

#### Bulk Operations

**Performance Optimizations:**
- Batch processing: 1000 rows per batch (configurable)
- Single query for all metric definitions per batch
- Single query for all forms per batch
- Hybrid response processing per form (DELETE+INSERT for complete, upsert for split batches)
- Batch idempotency detection via existing_count vs incoming_count comparison
- Cached employee ID lookups (avoid N+1 queries)
- Efficient form grouping algorithm (O(n) complexity)

**Memory Management:**
- Generator-based batch retrieval from SQL Server
- Streaming DataFrame processing
- Immediate commit after each batch
- No full-table loads into memory

### 🔒 **Security & Validation**

**Input Validation:**
- Pydantic schema validation for all 18 columns
- Date format parsing (YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY)
- Metric_Type validation (must be 'R' or 'T')
- Value length limits (5000 characters max)
- Numeric field range checks (IDs must be > 0)

**SQL Injection Prevention:**
- Parameterized queries throughout
- Table name whitelisting
- Column name whitelisting
- No dynamic SQL generation from user input

**Data Integrity:**
- Foreign key constraints (employee_id → employees.id)
- Unique constraints (ro_form_id, metric_id)
- NOT NULL constraints on critical fields
- Cascade delete for referential integrity

**Error Handling:**
- Validation errors don't stop sync (logged and skipped)
- Partial completion support (PARTIAL status)
- Error threshold check (abort if > 10% errors)
- Detailed error messages with row number and field name

### 📦 **Dependencies**

**No New External Dependencies Required**

---

## [3.0.0] - 2025-12-23 - Prompt System Overhaul & Intelligence Agency Alignment

This is a **major update** introducing federal intelligence agency context alignment, job description-based performance evaluation, restructured achievement data format, and enhanced credibility assessment framework. 

#### Achievement Data Structure Restructuring

**CRITICAL**: The achievement data format has changed from a single combined field to three separate fields.

**OLD Format:**
```json
{
  "description": "Completed quarterly analysis",
  "impact": "8 (Wing level impact, briefed to senior management)"
}
```

**NEW Format:**
```json
{
  "description": "Completed quarterly analysis",
  "impact_score": 8,
  "impact_reason": "Wing level impact, briefed to senior management",
  "vision_verification": "supported"
}
```

**Changed Fields:**
- **Removed**: `impact` (string combining score and reason)
- **Added**: `impact_score` (integer 1-10)
- **Added**: `impact_reason` (string, max 180 characters)
- **Added**: `vision_verification` (enum: "supported"/"contradicted"/"none")

**Affected Models:**
- `Achievement` (weekly analysis)
- `MonthlyAchievement` (monthly analysis)
- `AchievementTheme` (quarterly analysis)


#### Organizational Hierarchy Terminology Change

**CRITICAL**: Corporate terminology replaced with federal intelligence agency hierarchy.

**OLD Values:**
```
"individual" | "team" | "department" | "organization"
```

**NEW Values:**
```
"individual" | "cell" | "unit" | "section" | "wing" | "hq"
```

**Affected Fields:**
- `StrategicAlignment.organizational_impact` (quarterly analysis)
- Impact rating scale descriptions across all prompts

**Rationale**: Aligns with actual organizational structure:
- **Individual**: Single employee level
- **Cell**: Small team 
- **Unit**: Department subdivision 
- **Section**: Full department 
- **Wing**: Directorate/Division 
- **HQ**: Headquarters/Agency-wide level

#### Forward Planning Recommendations Schema Addition

**NEW Required Field**: `ownership`

All recommendation objects in quarterly analysis now require ownership assignment:
- `"employee"`: Actions employee can take independently
- `"manager"`: Manager intervention or approval required
- `"hr"`: HR resources, training programs, or policy support needed
- `"cross-team"`: Requires coordination with other Wings/Sections

**Affected Models:**
- `Recommendation` (used in `ForwardPlanning` for quarterly analysis)

**All recommendation arrays now include ownership:**
- `keep_doing[]`
- `improve[]`
- `start[]`
- `stop[]`
- `support_needed[]`

---

### 🚀 **New Features**

#### Job Description (JD) Integration & Role-Based Analysis

The analysis system now integrates employee job descriptions to provide role-aware performance evaluation, career progression tracking, and JD alignment assessment.

**Key Capabilities:**

**1. Performance Expectations Framework**

Evaluates performance relative to formal job responsibilities:
- **Exceeds Expectations**: Scope expansion beyond JD, innovation, leadership, measurable mission impact
- **Meets Expectations**: Completes all JD responsibilities reliably, handles appropriate challenges
- **Below Expectations**: Consistently misses deliverables, requires excessive support

**2. Role-Appropriate Assessment by Seniority**

Different expectations and challenge patterns for each BPS grade:

**Junior Roles (BPS-17 to 18):**
- Focus: Execution quality, learning agility, growth trajectory
- Expected challenges: Learning systems, needing guidance, time management
- Red flags: Basic skill gaps, inability to complete routine tasks independently

**Mid-Level Roles (BPS-19 to 20):**
- Focus: Section/wing coordination, process mastery, reliability
- Expected challenges: Cross-team coordination, resource constraints, competing priorities
- Red flags: Excessive need for guidance, inability to work independently

**Senior Roles (BPS-21 to 22):**
- Focus: Strategic thinking, leadership impact, organizational outcomes
- Expected challenges: Strategic ambiguity, organizational politics, change management
- Red flags: Struggling with tactical execution, requiring excessive guidance

**3. Role Transition Support**

Handles multiple concurrent roles and mid-period transitions:
- **Multiple Concurrent Roles**: Assesses achievements against combined responsibilities, evaluates workload distribution
- **Mid-Week/Mid-Month Transitions**: Split assessment with learning curve accommodation
- **Career Progression Tracking**: Tracks role evolution across time periods

**4. Authority & Autonomy Assessment**

Evaluates whether employees exercise appropriate decision-making authority:
- BPS-17 to 18: Work with guidance, escalate major decisions
- BPS-19 to 20: Make section/wing decisions independently
- BPS-21 to 22: Make strategic HQ-level decisions, represent organization externally

**NEW Schema Fields:**
```python
# StrategicAlignment (Quarterly Analysis)
role_alignment: Literal["strong", "partial", "weak"]
role_fit_assessment: str  # Detailed text assessment
```

**Integration Points:**
- Weekly analysis: JD context for achievement validation and performance rating
- Monthly analysis: Role alignment over time, skill gap identification
- Quarterly analysis: Strategic alignment, promotion readiness, career trajectory

**Usage:**
```python
# Pass formatted JD data to analysis prompts
formatted_jd_data = format_job_description_for_prompt(employee_jd)
prompt = employee_analysis_prompt(
    report_text=report_text,
    formatted_jd_data=formatted_jd_data  # NEW parameter
)
```

#### Enhanced Credibility Framework

A comprehensive, fair, and systematic approach to assessing report credibility with explicit scoring rules and fairness safeguards.

**Key Features:**

**1. Point-Based Scoring System**

Replace subjective assessment with objective criteria:
- **Critical Red Flags** (3 points each):
  - Contradiction between report sections
  - Vision data mismatch (when applicable)
  - Impossible timelines
- **Moderate Red Flags** (1 point each):
  - Excessive superlatives (5+ instances OR >20% of sentences)
  - Improbable absolutes (3+ instances OR >20% of sentences)
  - Disproportionate impact claims
  - Zero challenges with major achievements

**2. Clear Rating Thresholds**

- **0-1 points** = HIGH credibility (default for most reports)
- **2-4 points** = MEDIUM credibility (some concerns, needs verification)
- **5+ points** = LOW credibility (significant concerns)
- **Override Rule**: 2+ critical red flags = automatic LOW credibility

**3. Fairness Principles**

- **Default Position**: Assume reports are honest and accurate
- **Communication Style Neutrality**: Poor writing ≠ Low credibility; accommodates non-native speakers and cultural differences
- **Context Matters**: Not all superlatives or absolutes are red flags
- **Evidence Focus**: Logical contradictions and factual impossibilities, not writing style

**4. Impact on Analysis**

**Achievement Impact Score Discounts:**
- HIGH credibility: 0% discount (use calculated score)
- MEDIUM credibility: 15% discount (multiply by 0.85, round to nearest integer)
- LOW credibility: 40% discount (multiply by 0.6, round to nearest integer)
- Minimum score after discount: 1

**Risk Level Adjustments:**
- HIGH credibility: No adjustment
- MEDIUM credibility: Increase risk by one tier
- LOW credibility: Increase risk by two tiers

**Performance Rating Caps:**
- HIGH credibility: No cap
- MEDIUM credibility: HIGH rating requires strong evidence
- LOW credibility: Maximum rating is MEDIUM

**Qualifying Language:**
- HIGH: "The employee completed..."
- MEDIUM: "The employee reports..."
- LOW: "The employee claims..."

**5. Temporal Aggregation**

**Monthly Credibility:**
- Aggregates weekly ratings
- Tracks improvement/decline trajectory
- Applies timeframe-based evaluation

**Quarterly Credibility:**
- Synthesizes monthly patterns
- Identifies reporting quality trends
- Documents recurring exaggeration types

**Example Implementation:**
```python
# Step 1: Identify red flags
critical_flags = 1  # Vision data mismatch
moderate_flags = 2  # Excessive superlatives, zero challenges

# Step 2: Calculate points
total_points = (critical_flags * 3) + (moderate_flags * 1)  # = 5 points

# Step 3: Determine rating
credibility_rating = "low"  # 5 points ≥ 5 threshold

# Step 4: Apply discount
raw_impact_score = 8
adjusted_score = round(8 * 0.6)  # = 5 (40% discount for LOW)
```

#### Organizational Context Alignment

All analysis prompts now include federal intelligence agency context to ensure domain-appropriate language and evaluation criteria.

**Key Elements:**

**1. Mission-Focused Terminology**

Replace corporate/business terms with mission-appropriate language:
- ❌ "business impact" → ✅ "mission impact" or "operational impact"
- ❌ "business outcomes" → ✅ "mission achievements" or "operational outcomes"
- ❌ "customers" → ✅ "stakeholders" (State & citizens, federal leadership, LEAs)
- ❌ "quarterly targets" → ✅ "mission objectives" or "operational priorities"

**2. Organizational Structure**

Recognizes dual hierarchy system:
- **Rank-Based**: BPS grades 17-22 (Basic Pay Scale)
- **Functional**: Wings → Sections → Units → Cells → Individual

**3. Primary Stakeholders**

- State & citizens (ultimate beneficiaries)
- Federal government leadership (Prime Minister's Office, Cabinet Secretariat)
- Provincial authorities
- Partner law enforcement agencies (LEAs)

**4. Impact Classification**

Highest-tier achievements contribute to:
- National security objectives
- Federal security directives
- Multi-agency strategic partnerships
- Mission-critical operational successes

#### Security & OPSEC Boundaries

**NEW**: Mandatory operational security guidelines embedded in all prompts to prevent disclosure of sensitive information in analysis outputs.

**Prohibited Content (Never Include):**
- Specific collection methods, technical tools, or covert operational procedures
- Identifiers or sensitive selectors (phone numbers, IMEI/IMSI, network identifiers)
- Speculation about personal motives, beliefs, family circumstances, or political/sectarian affiliations
- Details that could compromise ongoing investigations or intelligence operations

**Required Approach:**
✓ Use neutral, professional language focused on work outputs and documented facts
✓ When referencing sensitive work, use approved substitutes:
  - "multi source corroboration"
  - "analytical product"
  - "validated intelligence requirement"
✓ If evidence is insufficient, state "insufficient evidence" rather than speculating

**Rationale**: Analysis outputs may be viewed by HR, senior management, and employees themselves. Violations could compromise operations or personnel safety.

#### Evidence Standards & Confidence Indicators

Explicit guidance on evidence quality and confidence levels for analysis conclusions.

**Evidence Hierarchy (Highest to Lowest Objectivity):**

1. **Analysis Detail & Specificity**: Detailed monthly/weekly analyses with measurable achievements and concrete outcomes (available for all employees)
2. **Internal Consistency**: Coherent patterns across analyses with no contradictions between months/weeks (available for all employees)
3. **Vision Data Validation**: Objective tracking data (ONLY available for applicable roles; absence is NORMAL)

**Critical Fairness Principle**: Vision data is NOT required for high confidence or high impact assessments. Detailed, consistent analyses with measurable outcomes provide sufficient evidence.

**Confidence Level Guidelines:**

**HIGH CONFIDENCE:**
- 3/3 months have detailed analyses with clear, measurable outcomes
- No contradictions between monthly/weekly assessments
- Vision data validation (when available and applicable) strengthens but is NOT required

**MEDIUM CONFIDENCE:**
- Only 2/3 months available OR analyses lack specificity
- Minor inconsistencies between months
- Vague achievement descriptions without measurable outcomes

**LOW CONFIDENCE:**
- Only 1 month of data OR significant contradictions between analyses
- Achievement status conflicts across months (e.g., complete in Month 1, ongoing in Month 3)
- Vision data contradicts claims (when applicable)

**Example Confidence Statements:**
```
✅ "High confidence based on consistent pattern across all three monthly analyses with specific, measurable outcomes"
✅ "High confidence due to detailed monthly analyses with coherent, verifiable achievement patterns"
✅ "Medium confidence due to incomplete data for Month 2"
✅ "Low confidence due to contradictions between monthly analyses"
```

#### Career Progression Evaluation

**NEW**: Quarterly analysis now includes explicit promotion readiness and career trajectory assessment.

**Evaluation Dimensions:**

**1. Role Mastery Assessment**
- How well did employee master each role's core competencies over the quarter?
- Track development of capabilities across multiple role contexts
- Identify systematic gaps between current role requirements and demonstrated capabilities

**2. Readiness for Advancement**
- Evaluate readiness for role expansion or advancement based on JD requirements
- Assess whether achievement themes demonstrate mastery beyond current role scope
- Determine if behavioral assessment patterns indicate promotion readiness

**3. Strategic Alignment**
- Assess how employee's contributions align with formal role responsibilities
- Identify work performed beyond role scope (innovation, leadership, cross-functional impact)
- Evaluate whether organizational impact matches role level expectations

**Integration in Strategic Alignment Section:**
- Role expectations baseline (what the JD requires)
- Performance relative to baseline (meets/exceeds/below with evidence)
- Role alignment rating (strong/partial/weak)
- Detailed role fit assessment (stretch contributions, gaps, evolution)
- Readiness indicators for advancement

---

### 🔄 **What's Changed**

#### Before This Update (v2.x)

**Analysis Context:**
- Generic corporate terminology used throughout
- No job description integration
- Credibility assessed subjectively without clear criteria
- Impact ratings lacked organizational context mapping
- No role-specific performance expectations

**Typical Analysis Output:**
```json
{
  "achievements": [
    {
      "description": "Completed data analysis project",
      "impact": "7 (Department-wide impact)"
    }
  ],
  "organizational_impact": "department"
}
```

**Issues:**
- Inconsistent credibility assessments across analysts
- Achievement impact not calibrated to role level
- Corporate language inappropriate for intelligence agency
- No systematic approach to fairness in evaluation

#### After This Update (v3.0)

**Analysis Context:**
- Federal intelligence agency terminology throughout
- Job description-based performance expectations
- Systematic point-based credibility framework
- Impact ratings mapped to organizational hierarchy (individual→cell→unit→section→wing→hq)
- Role-appropriate evaluation by BPS grade

**Typical Analysis Output:**
```json
{
  "achievements": [
    {
      "description": "Completed counter-terrorism threat assessment",
      "impact_score": 7,
      "impact_reason": "Wing level impact, briefed to senior management",
      "vision_verification": "supported"
    }
  ],
  "strategic_alignment": {
    "organizational_impact": "wing",
    "role_alignment": "strong",
    "role_fit_assessment": "Work consistently matches JD responsibilities with stretch contributions in cross-wing coordination"
  }
}
```

**Improvements:**
- Consistent, fair credibility assessments with documented criteria
- Achievement impact calibrated to role expectations
- Mission-appropriate terminology
- Systematic evidence standards
- Role-based career progression insights

#### Impact Rating Scale Evolution

**OLD Scale (Generic):**
```
1-10 scale with vague guidance:
- Low impact: 1-3
- Medium impact: 4-6
- High impact: 7-8
- Strategic impact: 9-10
```

**NEW Scale (Organizationally Mapped):**
```
1-3: Individual/Cell-level Impact
     - Routine task completion, personal skill development
     
4-6: Unit/Section-level Impact
     - Team value addition, process improvements within section
     
7-8: Wing-level Impact
     - Intelligence assessments briefed to senior management
     - Coordination with partner LEAs
     - Reports to provincial/federal authorities
     
9-10: HQ-level/Strategic Impact
     - Intelligence products briefed to PMO/Cabinet
     - Federal security directives
     - Mission-critical operational successes
```

**Benefits:**
- Clear organizational level mapping
- Role-appropriate impact expectations
- Consistent scoring across analysts
- Better alignment with mission priorities

#### Vision Data Handling Enhancements

**OLD Approach:**
- Vague guidance on when to use Vision data
- Unclear whether absence of Vision data is problematic
- No guidance on data truncation or interpretation

**NEW Approach:**

**1. Critical Fairness Principle**
```
"Many employees have NO vision tracking data (strategic, liaison, 
field, administrative roles). This is the NORMAL state. Vision data 
absence should NOT be mentioned or weighed negatively."
```

**2. Data Presentation Context**
```
"The Vision data displays detailed content items with a configured 
limit per entity. When you see 'and X more...', this indicates 
additional tracked items beyond those displayed. Truncated display 
≠ incomplete tracking."
```

**3. Cross-Verification (Monthly/Quarterly)**
```
"Independently verify key achievements against raw Vision System Data. 
Do not blindly trust weekly vision_verification values. Weekly LLM 
had more detailed data; monthly/quarterly views may be truncated."
```

**4. Verification Decision Rules**
- Set to "supported": ONLY when Vision data clearly confirms the achievement
- Set to "contradicted": ONLY when Vision data clearly conflicts
- Set to "none": When no Vision data exists OR not applicable (MOST COMMON)

**Impact**: Fairer, more accurate analysis for employees without Vision tracking

---

### 📊 **Schema & Model Updates**

#### Pydantic Model Changes (structured_models_llm.py)

**Achievement Model:**
```python
class Achievement(BaseModel):
    description: str = Field(
        description="Detailed description of the achievement"
    )
    # REMOVED: impact: str
    # ADDED:
    impact_score: int = Field(
        ge=1, le=10,
        description="Impact rating from 1 to 10, where 1-3 is individual level, 4-6 is section level, 7-8 is wing level, 9-10 is HQ strategic level"
    )
    impact_reason: str = Field(
        max_length=180,
        description="Brief reason for the impact rating (max 120 characters), explaining which organizational level was impacted"
    )
    vision_verification: Literal["supported", "contradicted", "none"] = Field(
        default="none",
        description="If vision data confirms this achievement, set to 'supported'. If vision data contradicts it, set to 'contradicted'. If NO vision data appears in your prompt or it does not exist for the specific achievement, set the key to 'none'"
    )
```

**MonthlyAchievement Model:**
```python
class MonthlyAchievement(BaseModel):
    description: str
    # REMOVED: impact: str
    # ADDED:
    impact_score: int = Field(ge=1, le=10, description="...")
    impact_reason: str = Field(max_length=180, description="...")
    vision_verification: Literal["supported", "contradicted", "none"] = Field(default="none", description="...")
```

**AchievementTheme Model:**
```python
class AchievementTheme(BaseModel):
    theme: str
    related_achievements: List[str] = Field(
        # UPDATED description to emphasize outcomes:
        description="List of specific achievements within this theme, including both activities performed and their outcomes. Each achievement should capture what was done and its measurable impact (e.g., 'Developed cross-reference methodology reducing discrepancies by 35%')."
    )
    # REMOVED: impact: str
    # ADDED:
    impact_score: int = Field(ge=1, le=10, description="...")
    impact_reason: str = Field(max_length=180, description="...")
    vision_verification: Literal["supported", "contradicted", "none"] = Field(default="none", description="...")
```

**StrategicAlignment Model:**
```python
class StrategicAlignment(BaseModel):
    # CHANGED values:
    organizational_impact: Literal["individual", "cell", "unit", "section", "wing", "hq"] = Field(
        description="Scope of impact the employee's work has had"
    )
    key_initiatives: List[KeyInitiative]
    # NEW FIELD:
    role_alignment: Literal["strong", "partial", "weak"] = Field(
        description="How well employee's work aligns with job description responsibilities across the quarter"
    )
    # NEW FIELD:
    role_fit_assessment: str = Field(
        description="Detailed assessment of Job Description fit, including stretch contributions beyond role scope and any gaps between role requirements and actual work patterns"
    )
```

**StakeholderImpact Model:**
```python
class StakeholderImpact(BaseModel):
    stakeholder: str
    # CHANGED values (lowercase_underscore → Title Case):
    collaboration_type: Literal[
        "Leading Initiative",
        "Contributing Expertise",
        "Mentoring",
        "Process Improvement"
    ] = Field(description="Type of collaboration...")
    impact: str
    evidence: str
```

**Recommendation Model:**
```python
class Recommendation(BaseModel):
    action: str = Field(description="The recommended action in clear, actionable language")
    priority: Literal["high", "medium", "low"]
    # NEW FIELD:
    ownership: Literal["employee", "manager", "hr", "cross-team"] = Field(
        description="Who is responsible for implementing this recommendation"
    )
```

#### API Response Schema Changes (analysis_schema.py)

All analysis response schemas updated to reflect new achievement structure:

```python
class AnalysisResponse(BaseModel):
    # ... existing fields ...
    achievements_json: Optional[List[Achievement]] = None  # Uses new Achievement model
    
class MonthlyAnalysisResponse(BaseModel):
    # ... existing fields ...
    monthly_achievements: List[MonthlyAchievement]  # Uses new MonthlyAchievement model
    
class QuarterlyAnalysisResponse(BaseModel):
    # ... existing fields ...
    achievement_themes: List[AchievementTheme]  # Uses new AchievementTheme model
    strategic_alignment: StrategicAlignment  # Uses updated StrategicAlignment model
```

#### Code Updates

**Update Achievement Parsing:**

```python
# OLD CODE:
achievement_impact = achievement.get("impact", "Unknown")
impact_score = int(achievement_impact.split(" ")[0])

# NEW CODE:
impact_score = achievement.get("impact_score", 0)
impact_reason = achievement.get("impact_reason", "")
vision_verification = achievement.get("vision_verification", "none")
```

---


#### Performance Considerations

**Prompt Length:**
- New prompts are longer due to comprehensive guidance
- Vision data may be truncated in monthly/quarterly to manage context length
- Consider using higher-context models for optimal results

**Processing Time:**
- More detailed analysis may increase LLM processing time
- JD integration adds 1-2 seconds for data fetching and formatting

#### Security Notes

**OPSEC Compliance:**
- All prompts now include mandatory security boundaries
- Outputs should be audited for prohibited content during initial rollout
- Consider adding post-processing filter to sanitize responses

**Sensitive Data:**
- Job descriptions may contain role-specific security clearance info
- Vision data may reveal sensitive work patterns
- Ensure appropriate access controls on analysis outputs

---

## [2.1.0] - 2025-12 - Job Description Management Update

This update introduces Job Description tracking and management capabilities, enabling role assignment history tracking and alignment of employee performance with formal job responsibilities.

### New Features

#### Job Description Data Management

The system now tracks current and historical job descriptions for employees, supporting role changes, promotions, and detailed assignment history.

**Key Capabilities:**

- **Multiple JDs per Employee**: Support for tracking multiple job descriptions over time (role changes, promotions, lateral moves)
- **Historical Tracking**: Complete history of job description assignments with start and end dates
- **Current Role Identification**: `is_current` flag marks the active job description
- **Role Change Management**: Automatically track when employees move to new roles
- **Source Traceability**: Maintain reference to original JD_ID from SQL Server for bidirectional mapping

**Supported Data Types:**
- Employee Reports (from `EmployeeReports` table)
- Vision Data (from `VisionEmployeeData` table)
- Job Descriptions (from `EmployeeJobDescriptions` table) ← **NEW**

#### CSV Import Support for Job Descriptions

Import job description data via CSV/TSV/TXT files with comprehensive validation.

**CSV Format:**
```csv
Employee_ID,JD_ID,Job_Description,Assigned_Date,Is_Current,End_Date
101,1001,"Responsible for analyzing employee performance data, generating insights, and presenting findings to management. Requires proficiency in data analysis tools and strong communication skills.",2024-01-15,true,
102,1002,"Coordinates project activities across multiple teams, manages timelines, and ensures deliverables meet quality standards. Acts as liaison between technical and business stakeholders.",2023-06-01,false,2024-05-31
```

**Validation Rules:**
- **Employee_ID**: Must reference an existing employee (validated before import)
- **JD_ID**: Numeric identifier (accepts int or string, stored as string)
- **Job_Description**: Minimum 50 characters, must contain meaningful content (no placeholders like "lorem ipsum", "TODO", etc.)
- **Assigned_Date**: REQUIRED field, accepts formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY (cannot be in future or before 1970)
- **Is_Current**: Boolean flag (accepts: true/false, 1/0, yes/no, or NULL-like values which default to true)
- **End_Date**: Optional, NULL for current roles (same format requirements as Assigned_Date)

**Processing Features:**
- Automatic duplicate handling via upsert on (employee_id, jd_id)
- Bulk processing using PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`
- Pre-validation of employee existence before bulk operations
- Detailed error reporting with row-level information

#### SQL Server Sync for Job Descriptions

Automated synchronization from SQL Server's `EmployeeJobDescriptions` table with the same security and reliability as existing sync types.

**Sync Modes:**
- **Incremental Sync**: Only transfers records modified since last successful sync
- **Full Sync**: Transfers all job description records

**SQL Server Table Requirements:**

```sql
CREATE TABLE JobDescriptions (
    RecordID INT IDENTITY(1,1) PRIMARY KEY,
    Employee_ID INT NOT NULL,
    JD_ID INT NOT NULL,
    Job_Description NVARCHAR(MAX) NOT NULL,
    Assigned_Date DATE NOT NULL,
    Is_Current BIT NOT NULL DEFAULT 1,
    End_Date DATE NULL,
    LastModifiedDate DATETIME DEFAULT GETDATE()
);

-- Index for efficient incremental sync
CREATE INDEX IX_JobDescriptions_LastModifiedDate 
ON JobDescriptions(LastModifiedDate);

-- Unique constraint to prevent duplicates
CREATE UNIQUE INDEX UQ_JobDescriptions_Employee_JD
ON JobDescriptions(Employee_ID, JD_ID);
```

**Important Sync Notes:**
- Always update `LastModifiedDate` when records change for incremental sync to work
- `Job_Description` must be at least 50 characters
- `Assigned_Date` is REQUIRED (no defaults, must be explicitly set)
- `Is_Current` should be `1` (true) for active roles, `0` (false) for ended roles
- `End_Date` should be NULL for current roles

#### Database Schema Enhancement

**New Table: `employee_job_descriptions`**

```sql
CREATE TABLE employee_reports.employee_job_descriptions (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employee_reports.employees(id) ON DELETE CASCADE,
    jd_id VARCHAR(50) NOT NULL,
    job_description TEXT NOT NULL,
    assigned_date DATE NOT NULL,
    end_date DATE,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint: one (employee_id, jd_id) combination
    CONSTRAINT uq_employee_jd_assignment UNIQUE (employee_id, jd_id)
);

-- Partial index for fast "current JD" lookups
CREATE INDEX ix_employee_jd_current 
ON employee_reports.employee_job_descriptions(employee_id) 
WHERE is_current = TRUE;

- No need to create the table in postgres. It is automatically created upon app startup. For the other tables, either use Alembic or Manual Table Deletion followed by Manual Table Creation using app startup to cater for new fields/values & columns in the already existed tables.

**Key Design Decisions:**
- **Cascade Delete**: When an employee is deleted, all their JD assignments are automatically removed
- **Unique Constraint**: Prevents duplicate (employee_id, jd_id) assignments
- **Partial Index**: Optimized queries for finding an employee's current job description
- **Flexible JD_ID**: Stored as VARCHAR to handle various identifier formats from different systems

### 🔄 What's Changed

#### Sync System Updates

**Before This Update:**
- Supported two sync types: Employee Reports and Vision Data
- Full sync triggered both types sequentially

**After This Update:**
- **Three sync types** supported: Employee Reports, Vision Data, and Job Descriptions
- Full sync now processes **all three types** sequentially
- Incremental sync schedule (Monday 2:00 AM) now includes Job Descriptions
- Each sync type tracked independently with separate `SyncHistory` records

**API Changes:**
1. **New Endpoint**: `POST /sync/trigger/job_descriptions`
   - Triggers JD sync (incremental or full)
   - Returns dedicated `sync_id` for tracking

2. **Updated Endpoint**: `POST /sync/trigger/full`
   - Now returns THREE sync_ids: `employee_reports_sync_id`, `vision_data_sync_id`, and `job_descriptions_sync_id`
   - Response message updated: "Full sync (employee reports, vision data, and job descriptions) started successfully"

3. **Updated Validation**: `/sync/last-successful/{sync_type}` now accepts `"job_descriptions"` as valid type

**CSV Import Updates:**
- `csv_type` parameter now accepts `"job_descriptions"` value
- Import metrics include `jd_records_created` and `jd_records_updated`
- Processor auto-detection recognizes JD CSV format (Employee_ID, JD_ID, Job_Description, Assigned_Date headers)

### 📋 Usage Examples

#### Importing Job Descriptions via CSV

**Using the Web Interface:**
1. Navigate to **Imports** page
2. Upload your JD CSV file
3. Select **job_descriptions** as CSV type (or let system auto-detect)
4. Choose processing mode: **bulk** (recommended for large files)
5. Monitor progress and review any errors

**Using the API:**
```bash
curl -X POST "http://localhost:8000/imports/upload" \
  -F "file=@job_descriptions.csv" \
  -F "csv_type=job_descriptions" \
  -F "processing_mode=bulk"
```

#### Syncing Job Descriptions from SQL Server

**Incremental Sync (Recommended for Regular Updates):**
```bash
curl -X POST "http://localhost:8000/sync/trigger/job_descriptions?is_full_sync=false"
```

**Full Sync (First-Time or Data Refresh):**
```bash
curl -X POST "http://localhost:8000/sync/trigger/job_descriptions?is_full_sync=true"
```

**Full System Sync (All Three Types):**
```bash
curl -X POST "http://localhost:8000/sync/trigger/full"
```

**Check Sync Status:**
```bash
curl "http://localhost:8000/sync/status/{sync_id}"
```

### 🐛 Common Issues and Solutions

**Issue: "Employee ID X does not exist in the database"**
- **Cause**: Attempting to import JD for non-existent employee
- **Solution**: Import or create employee record first, then import JD

**Issue: "Job description must be at least 50 characters long"**
- **Cause**: JD text too short or contains placeholder text
- **Solution**: Provide meaningful job description with at least 50 characters

**Issue: "Assigned_Date is required and cannot be empty"**
- **Cause**: Missing or NULL Assigned_Date in source data
- **Solution**: Ensure every JD record has a valid Assigned_Date

**Issue: Incremental sync not picking up changes**
- **Cause**: `LastModifiedDate` not updated in SQL Server
- **Solution**: Ensure triggers or application logic updates `LastModifiedDate` on changes

### ⬆️ Migration Notes

**From Version 2.0.0:**

1. **Database Migration**: Alembic migration or starting up FastAPI Server creates `employee_job_descriptions` table automatically. For the other tables, either use Alembic or Manual Table Deletion followed by Manual Table Creation using app startup to cater for new fields/values & columns in the already existed tables.
2. **No Data Loss**: Existing employee reports and vision data remain unchanged
3. **Backward Compatible**: All existing APIs and functionality continue to work
4. **First JD Sync**: Run a **Full Sync** for job descriptions to establish baseline

**Configuration Updates:**

```env
# Add JobDescriptions to allowed tables
SQLSERVER_ALLOWED_TABLES=EmployeeReports,VisionEmployeeData,EmployeeJobDescriptions

# Ensure sync is enabled
SYNC_ENABLED=true
```

### 📊 Technical Details

**Processing Pipeline:**
1. **SQL Server** → Query `EmployeeJobDescriptions` table (filtered by `LastModifiedDate` for incremental)
2. **Transformer** → Convert SQL Server types to Pydantic-compatible format
3. **Validator** → Validate with `JobDescriptionCSVRow` Pydantic schema
4. **Processor** → Bulk upsert using PostgreSQL `INSERT ... ON CONFLICT DO UPDATE`
5. **Tracker** → Update `SyncHistory` with metrics and timestamp

**Performance Optimizations:**
- Batch processing (1000 records per batch)
- Bulk PostgreSQL upsert (single SQL statement per batch)
- Employee ID caching (prevents N queries for existence checks)
- Pre-query for existing records (accurate create/update tracking)

**Metrics Tracked:**
- `jd_records_created`: Number of new JD assignments created
- `jd_records_updated`: Number of existing JD assignments updated
- `records_queried`: Total records from SQL Server
- `records_synced`: Successfully processed records
- `error_count`: Validation/processing errors
- `last_sync_timestamp`: Timestamp for next incremental sync (+1ms for SQL Server precision)

### 🔒 Security Considerations

- **Table Whitelisting**: Only approved tables can be synced
- **Column Whitelisting**: Timestamp columns validated against whitelist
- **SQL Injection Prevention**: All queries use parameterized statements
- **Input Validation**: Comprehensive Pydantic validation before database operations
- **Cascade Delete Protection**: Foreign key constraints prevent orphaned records

### 📚 Additional Resources

- **Full API Documentation**: Available at `/docs` when application is running
- **Detailed Setup Guide**: See `README.md`
- **API Reference**: See `api_documentation.md` → SQL Server Sync section
- **SQL Server Mapping**: See `docs/sqlserver_postgres_mapping.csv` for complete field mappings

---

## [2.0.0] - 2025-11 - Data Synchronization Update

This update introduces automated SQL Server synchronization and improved file import capabilities, significantly reducing manual data management overhead.

### 🚀 New Features

#### SQL Server Data Synchronization

A new **Sync** module has been added that enables direct data migration from SQL Server to PostgreSQL, eliminating the need for manual CSV exports and imports.

**Key Capabilities:**

- **Automated Sync**: Schedule weekly incremental syncs to automatically keep your PostgreSQL database up-to-date with SQL Server changes
- **Manual Sync Options**: Trigger syncs on-demand through the web interface or API
- **Two Sync Modes**:
  - **Incremental Sync**: Only transfers records modified since the last successful sync (faster, recommended for regular updates)
  - **Full Sync**: Transfers all records regardless of modification date (useful for initial setup or data refresh)
- **Real-Time Monitoring**: Track sync progress with live metrics including records queried, synced, created, updated, and any errors
- **Comprehensive Error Handling**: Detailed error tracking with row-level information for troubleshooting
- **Sync History**: Complete audit trail of all sync operations with filtering and search

**Supported Data Types:**
- Employee Reports (from `EmployeeReports` table)
- Vision Data (from `VisionEmployeeData` table)

#### Enhanced File Import Support

The CSV import functionality has been significantly improved to properly support multiple file formats:

- **TSV Files**: Tab-separated values now work correctly
- **TXT Files**: Text files with various delimiters are properly parsed
- **Improved Encoding Detection**: Better handling of different character encodings
- **Configurable Delimiters**: Specify custom delimiters when needed

### 🔄 What's Changed

#### Before This Update

Importing Vision data required a complex multi-step process:

1. Open a KNIME workflow
2. Import data to a temporary database table
3. Modify parameters in the workflow
4. Run a separate migration script from the `one_off_mg` folder
5. Manually verify the data transfer

This process was:
- Time-consuming
- Error-prone due to multiple manual steps
- Required technical knowledge of KNIME and SQL scripts
- Difficult to automate or schedule

#### After This Update

**Option 1: Automated Sync (Recommended)**
- Configure SQL Server connection once
- Data syncs automatically every Monday at 2:00 AM (can be set up using .env file)
- Or trigger manual sync with one click
- No external tools required

**Option 2: Improved File Import**
- Upload TSV/TXT files directly through the web interface
- System automatically detects format and processes data
- No KNIME workflow or scripts needed

### 📋 How to Use the New Sync Feature

#### Initial Setup

1. **Install ODBC Driver**

   Install Microsoft ODBC Driver 17 (or newer) for SQL Server on your system. Download from [Microsoft ODBC Driver for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server).

2. **Configure SQL Server Connection**

   Add the following to your `.env` file:

   ```env
   # SQL Server Connection
   SQLSERVER_HOST=your_server\SQLEXPRESS
   SQLSERVER_DATABASE=YourDatabaseName
   SQLSERVER_USERNAME=your_username
   SQLSERVER_PASSWORD=your_password
   
   # Sync Settings
   SYNC_ENABLED=true
   ```

3. **Verify Connection**

   Navigate to the **Sync** page in the web interface and click **Test Connection** to verify SQL Server connectivity.

4. **Set Up SQL Server Tables** (for sync functionality)

   Create the required tables in your SQL Server database:

   ```sql
   -- Employee Reports Table
   CREATE TABLE EmployeeReports (
       RecordID INT IDENTITY(1,1) PRIMARY KEY,
       Employee_ID INT NOT NULL,
       Name NVARCHAR(100),
       Designation NVARCHAR(100),
       BPS NVARCHAR(20),
       Office_Hierarchy NVARCHAR(200),
       [From] DATE NOT NULL,
       [To] DATE NOT NULL,
       Draft NVARCHAR(500),
       Tasks_Completed NVARCHAR(MAX),
       Impact NVARCHAR(MAX),
       Challenges NVARCHAR(MAX),
       Support_Required NVARCHAR(MAX),
       Tasks_Planned NVARCHAR(MAX),
       Confidence_Level NVARCHAR(50),
       NTR NVARCHAR(500),
       LastModifiedDate DATETIME DEFAULT GETDATE()
   );

   -- Vision Employee Data Table
   CREATE TABLE VisionEmployeeData (
       RecordID INT IDENTITY(1,1) PRIMARY KEY,
       Employee_ID INT NOT NULL,
       From_Date DATE NOT NULL,
       To_Date DATE NOT NULL,
       Main_Entity NVARCHAR(100),
       Sub_Entities NVARCHAR(MAX),
       Sub_Entities_Content NVARCHAR(MAX),
       LastModifiedDate DATETIME DEFAULT GETDATE()
   );

   -- Create indexes for timestamp columns (important for incremental sync)
   CREATE INDEX IX_EmployeeReports_LastModifiedDate ON EmployeeReports(LastModifiedDate);
   CREATE INDEX IX_VisionEmployeeData_LastModifiedDate ON VisionEmployeeData(LastModifiedDate);
   ```

5. **Verify Required Tables Exist**

   Your SQL Server database should have:
   - `EmployeeReports` table with a `LastModifiedDate` column (can be set using .env file)
   - `VisionEmployeeData` table with a `LastModifiedDate` column (can be set using .env file)

   These timestamp columns are essential for incremental sync to detect changes.

#### Running Your First Sync

1. Go to the **Sync** page in the web interface
2. Choose the data type to sync:
   - **Employee Reports**: Syncs employee weekly reports
   - **Vision Data**: Syncs vision/goals data
   - **Complete Sync**: Syncs both types
3. For first-time sync, click **Full Sync** to transfer all existing data
4. Monitor progress in the **Active Sync Monitor** section
5. Review results in **Sync History**

#### Ongoing Synchronization

**Automatic (Recommended):**
- With `SYNC_ENABLED=true`, incremental syncs run automatically every Monday at 2:00 AM
- Only new or modified records are transferred
- No manual intervention required

**Manual:**
- Use **Incremental Sync** for regular updates (faster)
- Use **Full Sync** only when needed (e.g., after schema changes)

#### Handling Errors

If a sync encounters errors:

1. Check the **Sync History** section for the failed sync
2. Click **Errors** to view detailed error information
3. Each error shows:
   - Row number in the source data
   - Field that caused the issue
   - Specific error message
4. Fix the source data in SQL Server
5. Re-run the sync

Common issues:
- **Employee ID not found**: The employee must exist in PostgreSQL before syncing their reports
- **Invalid date format**: Ensure dates in SQL Server are in a standard format
- **Missing required fields**: Check that all required columns have values

### 🗄️ SQL Server Table Requirements

#### EmployeeReports Table

```sql
CREATE TABLE EmployeeReports (
    RecordID INT IDENTITY(1,1) PRIMARY KEY,
    Employee_ID INT NOT NULL,
    Name NVARCHAR(100),
    Designation NVARCHAR(100),
    BPS NVARCHAR(20),
    Office_Hierarchy NVARCHAR(200),
    [From] DATE NOT NULL,
    [To] DATE NOT NULL,
    Draft NVARCHAR(500),
    Tasks_Completed NVARCHAR(MAX),
    Impact NVARCHAR(MAX),
    Challenges NVARCHAR(MAX),
    Support_Required NVARCHAR(MAX),
    Tasks_Planned NVARCHAR(MAX),
    Confidence_Level NVARCHAR(50),
    NTR NVARCHAR(500),
    LastModifiedDate DATETIME DEFAULT GETDATE()
);

-- Index for efficient incremental sync
CREATE INDEX IX_EmployeeReports_LastModifiedDate 
ON EmployeeReports(LastModifiedDate);
```

#### VisionEmployeeData Table

```sql
CREATE TABLE VisionEmployeeData (
    RecordID INT IDENTITY(1,1) PRIMARY KEY,
    Employee_ID INT NOT NULL,
    From_Date DATE NOT NULL,
    To_Date DATE NOT NULL,
    Main_Entity NVARCHAR(100),
    Sub_Entities NVARCHAR(MAX),
    Sub_Entities_Content NVARCHAR(MAX),
    LastModifiedDate DATETIME DEFAULT GETDATE()
);

-- Index for efficient incremental sync
CREATE INDEX IX_VisionEmployeeData_LastModifiedDate 
ON VisionEmployeeData(LastModifiedDate);
```

**Important:** Always update the `LastModifiedDate` or `ModifiedDate` column when records change. This ensures incremental sync captures all modifications.

### 🔧 Configuration Reference

| Setting | Description | Default |
|---------|-------------|---------|
| `SQLSERVER_HOST` | SQL Server hostname or instance | `localhost\SQLEXPRESS` |
| `SQLSERVER_DATABASE` | Database name | - |
| `SQLSERVER_USERNAME` | SQL Server login | - |
| `SQLSERVER_PASSWORD` | SQL Server password | - |
| `SQLSERVER_DRIVER` | ODBC driver (or `auto` for auto-detect) | `auto` |
| `SYNC_ENABLED` | Enable automatic scheduled sync | `true` |
| `SYNC_ERROR_THRESHOLD_PERCENT` | Max error % before aborting sync | `10.0` |

### 🛡️ Security Features

The sync system includes built-in security measures:

- **Table Whitelisting**: Only pre-approved tables can be queried
- **SQL Injection Prevention**: All queries use parameterized statements
- **Connection Encryption**: SSL/TLS enabled by default
- **Read-Only Access**: Sync only reads from SQL Server, never writes

### 📊 API Endpoints

New sync-related endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sync/trigger/employee_reports` | POST | Start employee reports sync |
| `/sync/trigger/vision_data` | POST | Start vision data sync |
| `/sync/trigger/full` | POST | Start full system sync |
| `/sync/status/{sync_id}` | GET | Get sync job status |
| `/sync/history` | GET | List sync history |
| `/sync/{sync_id}/errors` | GET | Get sync errors |
| `/sync/config` | GET | View sync configuration |
| `/sync/test-connection` | GET | Test SQL Server connection |

### ⬆️ Migration Notes

**From Previous Versions:**

1. No database migration required - new tables are created automatically
2. Existing imported data remains unchanged
3. The KNIME workflow and migration scripts are no longer needed but can be kept as backup
4. First sync should be a **Full Sync** to establish baseline

**Recommended Steps:**

1. Update your `.env` file with SQL Server connection details
2. Restart the application and Celery worker
3. Navigate to **Sync** page and test connection
4. Run a **Full Sync** for both data types
5. Verify data integrity
6. Enable automatic sync (`SYNC_ENABLED=true`)

### 📚 Additional Resources

- Full API documentation: `/docs` endpoint when application is running
- Detailed README: See `README.md` for complete setup instructions
- API reference: See `api_documentation.md` for endpoint details

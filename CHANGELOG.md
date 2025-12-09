# Changelog

All notable changes to the Employee Report Analysis System are documented in this file.

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

# Changelog

All notable changes to the Employee Report Analysis System are documented in this file.

---

## [2.0.0] - 2025-01 - Data Synchronization Update

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

---

## [1.x.x] - Previous Releases

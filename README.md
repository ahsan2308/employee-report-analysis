# 🧠 Employee Performance Analysis System

A AI-powered system for analyzing employee reports to extract valuable insights, identify trends, and facilitate data-driven management decisions through natural language processing.

---

## 📋 Overview

**Employee Performance Analysis** is an intelligent application that leverages **Large Language Models (LLMs)** and **vector search** to automatically analyze employee reports. The system extracts key information such as:

- Achievements and their impact
- Challenges and their severity
- Sentiment analysis
- Risk assessments with credibility-adjusted ratings
- **Point-based credibility evaluation** with fairness safeguards
- **Job description-aligned performance assessments**
- Career progression and promotion readiness indicators
- Recommended action items with ownership assignment

The system also performs **monthly analysis** across all reports from an employee to identify trends, recurring challenges, and growth indicators, as well as **quarterly analysis** for strategic alignment, achievement themes, role fit assessment, and long-term performance evaluation.

---

## ✨ Key Features

- **Weekly Report Analysis**: Extract structured insights from unstructured employee reports
- **Monthly Performance Analysis**: Analyze trends and patterns across all reports from a month
- **Quarterly Performance Analysis**: Evaluate strategic alignment, achievement themes, role fit, and behavioral assessments over a quarter
- **Job Description Integration**: Role-based analysis with JD alignment assessment, promotion readiness evaluation, and authority-appropriate expectations
- **Enhanced Credibility Framework**: Point-based assessment system with fairness safeguards, explicit scoring rules, and credibility-adjusted impact ratings
- **Achievement Tracking**: Structured impact data with separate score (1-10), reasoning, and data verification status
- **Evidence Standards**: Explicit confidence indicators based on analysis detail, consistency, and objective validation 
- **Security Boundaries**: Built-in OPSEC guidelines preventing disclosure of sensitive operational details in analysis outputs
- **Career Progression Evaluation**: Promotion readiness assessment, role mastery tracking, and strategic alignment evaluation
- **Supervisor Feedback Integeration**: Structured performance evaluations with rating and text metrics (from supervisor) incorporated in the analysis
- **Semantic Search**: Find relevant reports based on context, not just keywords
- **Risk Assessment**: Automatically identify potential issues with credibility-adjusted risk levels
- **Sentiment Analysis**: Track employee sentiment over time
- **Performance Rating**: Balanced assessments with role-appropriate expectations, strengths, and improvement areas
- **Historical Context**: Analyze reports with previous submissions for reference
- **Asynchronous Processing**: Background task processing for analysis requests
- **Direct URL Sharing**: Share analysis results via URL parameters
- **CSV Data Import**: Bulk import of employee data, historical reports, job descriptions, supervisor feedback evaluations, and other information
- **SQL Server Data Sync**: Automated synchronization from SQL Server to PostgreSQL with:
  - Incremental sync (only new/modified records)
  - Full sync (complete data refresh)
  - Real-time progress monitoring
  - Scheduled automatic sync
  - Comprehensive error tracking
  - Support for four data types: Employee Reports, Vision Data, Job Descriptions, and Supervisor Feedback
- **Task Management System**: Track and monitor long-running analysis processes
- **Interactive Visualizations**: Visual representation of key metrics including:
  - Sentiment trends over time
  - Impact score trends
  - Risk level trends
  - Credibility trends
  - Consistency trends
  - Performance trends
  - Multi-criteria comparative analysis
  - Department and employee heatmaps

---

## 🏗️ System Architecture

- **API Layer**: RESTful endpoints for employees, reports, analyses, tasks, visualizations, imports, and sync operations
- **Services Layer**: Business logic for report processing and analysis
- **Task Processing**: 
  - Celery for asynchronous task management
  - Task status tracking and result retrieval
  - Configurable processing options for long-running tasks
- **Storage**:
  - PostgreSQL for structured data
  - Qdrant for vector embeddings and semantic search
  - Redis for task queue management and caching
  - SQL Server as external data source (for sync operations)
- **LLM Integration**: Ollama & vLLM for natural language understanding and structured output generation
- **Frontend Layer**: HTML, CSS, and JavaScript for user interaction
- **Vector Store**:
  - Automatic vectorization of reports upon submission
  - Semantic similarity search
  - Context-based retrieval of relevant historical data
- **Sync Engine**:
  - SQL Server to PostgreSQL data migration
  - Incremental and full sync support
  - Batch processing with configurable chunk sizes
  - Error threshold management

---

## 🛠️ Technologies Used

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (primary), SQL Server (external source)
- **Vector Store**: Qdrant
- **Task Queue**: Celery with Redis
- **LLM Provider**: Ollama, vLLM
- **Embeddings**: Ollama, vLLM
- **Documentation**: Swagger / OpenAPI
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Containerization**: Docker for services (Redis, Qdrant, vLLM)
- **Database Connectivity**: pyodbc for SQL Server connections
- **UI Framework**: Custom responsive design

---

## 📦 Setup and Installation

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Docker Desktop (for Redis and Qdrant containers)
- Ollama
- ODBC Driver 17+ for SQL Server
- Visual C++ build tools *(Windows only)*

### Installation Steps

1. **Install Required Tools**

   - **Python**: Download Python 3.10+ from [python.org](https://www.python.org/downloads/)
     - During installation, check "Add Python to PATH"

   - **Visual Studio Build Tools** (Windows only):
     - Download from [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
     - During installation, select only:
       - C++ build tools
       - MSVC v14.x
       - Windows 10/11 SDK

   - **PostgreSQL**:
     - Download from [PostgreSQL Website](https://www.postgresql.org/download/)
     - Remember your password during installation
     - Create a new database named `employee_report_db`
     - Create a schema named `employee_reports`

   - **SQL Server** (for sync functionality):
     - Ensure access to a SQL Server instance (Express, Standard, or existing organizational server)
     - Install ODBC Driver 17 (or newer) for SQL Server from [Microsoft ODBC Driver](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
       - Available for Windows, Linux (Ubuntu, RHEL, SUSE), and macOS
     - Ensure the database contains the required tables: `EmployeeReports`, `VisionEmployeeData`, and `EmployeeJobDescriptions`

   - **Docker Desktop**:
     - Download from [Docker Website](https://www.docker.com/products/docker-desktop/)
     - Install and ensure it's running

   - **Ollama**:
     - Download from [Ollama.com](https://ollama.com/)
     - After installation, run: `ollama pull llama3.1`

2. **Set Up Docker Containers**

   - **Start Redis Container**:
     ```powershell
     docker run -d `
       --name redis-container `
       -p 6379:6379 `
       redis redis-server --bind 0.0.0.0
     ```

   - **Start Qdrant Container**:
     ```powershell
     # Create directory for data persistence
     New-Item -ItemType Directory -Path .\qdrant_data -Force

     # Run Qdrant container
     docker run -d `
       --name qdrant-server `
       -p 6333:6333 `
       -p 6334:6334 `
       -v ${PWD}/qdrant_data:/qdrant/storage `
       --restart unless-stopped `
       qdrant/qdrant:v1.13.3
     ```

   - **Verify Qdrant is running**:
     ```powershell
     (Invoke-WebRequest 'http://localhost:6333/collections' -UseBasicParsing).StatusCode  # Should return 200
     ```

   - **Set Up vLLM Containers**:
   
     - **Prerequisites for GPU + Docker**:
       - Install NVIDIA drivers and NVIDIA Container Toolkit to enable Docker to access GPUs
       - Verify GPU access in containers:
         ```powershell
         docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
         ```
       - You should see your GPU(s) listed in the output

     - **Pull the vLLM OpenAI-compatible image**:
       ```powershell
       docker pull vllm/vllm-openai:latest
       ```

     - **Start the LLM Server**:
       ```powershell
       # Optional: Set Hugging Face token for gated models
       $env:HF_TOKEN="your_hf_token_here"

       # Start vLLM container for LLM functionality
       docker run --rm `
         --name vllm-llm `
         --gpus all `
         --ipc=host `
         -p 8001:8000 `
         -e HUGGING_FACE_HUB_TOKEN=$env:HF_TOKEN `
         -v "${PWD}\hf-cache:/root/.cache/huggingface" `
         vllm/vllm-openai:latest `
         --model meta-llama/Meta-Llama-3.1-8B-Instruct `
         --dtype auto `
         --gpu-memory-utilization 0.9 `
         --tensor-parallel-size 2 `  # Adjust based on number of GPUs
         --api-key token-llm123
       ```

     - **Test the LLM Server**:
       ```powershell
       # List available models
       curl -H "Authorization: Bearer token-llm123" http://localhost:8001/v1/models

       # Create a request file (req.json)
       @'
       {
         "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
         "messages": [
           { "role": "user", "content": "Give me 2 facts about Karachi." }
         ],
         "max_tokens": 128
       }
       '@ > req.json

       # Test chat completion
       curl -s -X POST http://localhost:8001/v1/chat/completions `
         -H "Authorization: Bearer token-llm123" `
         -H "Content-Type: application/json" `
         -d "@req.json"
       ```

     - **Start the Embeddings Server**:
       ```powershell
       # Start vLLM container for embeddings functionality
       docker run -d `
         --name vllm-embed `
         --gpus all `
         --ipc=host `
         -p 8010:8000 `
         -e HUGGING_FACE_HUB_TOKEN=$env:HF_TOKEN `
         -v "${PWD}\hf-cache:/root/.cache/huggingface" `
         vllm/vllm-openai:latest `
         --model BAAI/bge-m3 `  # Recommended embedding model
         --task embed `
         --dtype auto `
         --gpu-memory-utilization 0.9 `
         --tensor-parallel-size 2 `  # Adjust based on number of GPUs
         --api-key token-emb123
       ```

       - **For Single-GPU Setups**:
         ```powershell
         # Use a specific GPU (e.g., GPU 0)
         $env:CUDA_VISIBLE_DEVICES=0
         docker run -d `
           --name vllm-embed `
           --gpus all `
           --ipc=host `
           -p 8010:8000 `
           -e HUGGING_FACE_HUB_TOKEN=$env:HF_TOKEN `
           -v "${PWD}\hf-cache:/root/.cache/huggingface" `
           vllm/vllm-openai:latest `
           --model BAAI/bge-m3 `
           --task embed `
           --dtype auto `
           --gpu-memory-utilization 0.9 `
           --api-key token-emb123
         ```

     - **Test the Embeddings Server**:
       ```powershell
       # Create a request file (embed.json)
       @'
       {
         "model": "BAAI/bge-m3",
         "input": ["Karachi is a coastal city in Pakistan.", "Lahore is known for its culture."]
       }
       '@ > embed.json

       # Test embeddings
       curl -s -X POST http://localhost:8010/v1/embeddings `
         -H "Authorization: Bearer token-emb123" `
         -H "Content-Type: application/json" `
         -d "@embed.json"
       ```

3. **Set Up the Application**

   - **Get the code**: 
     - Clone the repository or extract the zip file
     - Navigate to the directory in your terminal

   - **Create a virtual environment**:
     ```bash
     python -m venv venv
     venv\Scripts\activate  # On Windows
     source venv/bin/activate  # On Linux/Mac
     ```

   - **Install dependencies**:
     ```bash
     pip install -r requirements.txt
     ```

   - **Configure environment variables**:
     - Modify the existing `.env` file in the application root with the relevant parameters e.g.:
     ```
     # PostgreSQL Configuration
     DATABASE_URL=postgresql://username:password@localhost:5432/employee_report_db
     
     # Vector Store Configuration
     VECTOR_STORE_PORT=6333
     
     # LLM Configuration
     OLLAMA_BASE_URL=http://localhost:11434
     OLLAMA_MODEL=llama3.1
     
     # SQL Server Sync Configuration
     SQLSERVER_HOST=localhost\SQLEXPRESS
     SQLSERVER_DATABASE=EmployeeTestDB
     SQLSERVER_USERNAME=your_username
     SQLSERVER_PASSWORD=your_password
     SQLSERVER_DRIVER=auto
     SQLSERVER_USE_ENCRYPTION=true
     
     # Sync Security Configuration
     SQLSERVER_ALLOWED_TABLES=EmployeeReports,VisionEmployeeData,EmployeeJobDescriptions
     SQLSERVER_ALLOWED_TIMESTAMP_COLUMNS=LastModifiedDate,ModifiedDate,UpdatedAt
     SQLSERVER_MAX_BATCH_SIZE=10000
     
     # Sync Settings
     SYNC_ENABLED=true
     SYNC_ERROR_THRESHOLD_PERCENT=10.0
     ```

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

   -- Job Descriptions Table
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

   -- Supervisor Feedback Table
   CREATE TABLE SupervisorFeedback (
       RecordID INT IDENTITY(1,1) PRIMARY KEY,
       RO_Form_ID INT NOT NULL,
       L_RO_Form_Metric_ID INT NOT NULL,
       Employee_ID INT NOT NULL,
       Name NVARCHAR(500) NOT NULL,
       Designation NVARCHAR(200) NULL,
       BPS NVARCHAR(50) NULL,
       Office_Hierarchy NVARCHAR(500) NULL,
       Executive_Office NVARCHAR(200) NULL,
       [From] DATE NOT NULL,
       [To] DATE NOT NULL,
       Section_ID INT NOT NULL,
       Section NVARCHAR(200) NOT NULL,
       Metric_ID INT NOT NULL,
       Metric_Title NVARCHAR(200) NOT NULL,
       Instructions NVARCHAR(1000) NULL,
       Metric_Type CHAR(1) NOT NULL,  -- 'R' for rating, 'T' for text
       Possible_Values NVARCHAR(500) NULL,
       Value NVARCHAR(MAX) NULL,
       LastModifiedDate DATETIME DEFAULT GETDATE()
   );

   -- Create indexes for timestamp columns (important for incremental sync)
   CREATE INDEX IX_EmployeeReports_LastModifiedDate ON EmployeeReports(LastModifiedDate);
   CREATE INDEX IX_VisionEmployeeData_LastModifiedDate ON VisionEmployeeData(LastModifiedDate);
   CREATE INDEX IX_JobDescriptions_LastModifiedDate ON JobDescriptions(LastModifiedDate);
   CREATE INDEX IX_SupervisorFeedback_LastModifiedDate ON SupervisorFeedback(LastModifiedDate);
   
   -- Create unique constraint for JobDescriptions to prevent duplicates
   CREATE UNIQUE INDEX UQ_JobDescriptions_Employee_JD ON JobDescriptions(Employee_ID, JD_ID);
   
   -- Create indexes for efficient querying of supervisor feedback
   CREATE INDEX IX_SupervisorFeedback_Employee_ID ON SupervisorFeedback(Employee_ID);
   CREATE INDEX IX_SupervisorFeedback_RO_Form_ID ON SupervisorFeedback(RO_Form_ID);
   
   -- Ensure form metric responses are unique
   CREATE UNIQUE INDEX UQ_SupervisorFeedback_Metric_Response ON SupervisorFeedback(L_RO_Form_Metric_ID);
   ```

5. **Verify Required Tables Exist**

   Your SQL Server database should have:
   - `EmployeeReports` table with a `LastModifiedDate` column (can be changed using .env file)
   - `VisionEmployeeData` table with a `LastModifiedDate` column (can be changed using .env file)
   - `JobDescriptions` table with a `LastModifiedDate` column (can be changed using .env file)
   - `SupervisorFeedback` table with a `LastModifiedDate` column (can be changed using .env file)

   These timestamp columns are essential for incremental sync to detect changes.

6. **Start the Application**

   - **Start the backend server**:
     ```bash
     uvicorn app.main:app --reload
     ```
   
   - **Start the Celery worker** (in a separate terminal):
     
     For **manual syncs only** (no scheduled automation):
     ```bash
     celery -A app.worker.celery_app worker --pool=solo --loglevel=info --queues=default,sync,analysis,imports
     ```
     
     For **scheduled automatic syncs** (requires Celery Beat):
     ```bash
     # Terminal 1: Start the Celery worker
     celery -A app.worker.celery_app worker --pool=solo --loglevel=info --queues=default,sync,analysis,imports
     
     # Terminal 2: Start Celery Beat (scheduler)
     celery -A app.worker.celery_app beat --loglevel=info
     ```
     
     > **Note:** The `--pool=solo` flag is required on Windows. On Linux/Mac, you can omit it.
     > The `--queues` flag ensures the worker processes all task types (sync, analysis, imports).

   - **Access the frontend**:
     - Open `frontend/index.html` in your web browser, or
     - Start a simple HTTP server:
     ```bash
     cd frontend
     python -m http.server 8080
     ```
     - Then navigate to `http://localhost:8080` in your browser

---

## 🚀 Usage

### Using the Web Interface

- **Home Page**: Overview of the system's capabilities and getting started guide
- **Employees Page**: Create, view, and manage employee profiles
- **Reports Page**: Submit new employee reports with structured fields:
  - Tasks completed
  - Impact/outcome
  - Challenges faced
  - Support required
  - Tasks planned for next week
  - Confidence level
- **Analysis Page**: Three analysis modes:
  - **Weekly Analysis**: Analyze individual reports with detailed insights
  - **Monthly Analysis**: Analyze patterns across an entire month with:
    - Progress trends
    - Monthly achievements
    - Recurring challenges
    - Consistency assessment
    - Growth indicators
    - Focus areas
    - Risk assessment
    - Strategic recommendations
  - **Quarterly Analysis**: Comprehensive evaluation across three months with:
    - Strategic alignment with organizational goals
    - Achievement themes and business outcomes
    - Performance trajectory and consistency
    - Challenge patterns and adaptation effectiveness
    - Cross-functional impact assessment
    - Skill development evaluation
    - Behavioral assessment of key workplace behaviors
    - Forward planning recommendations
- **Visualizations Page**: Interactive charts showing:
  - Sentiment trends over time (by employee or department)
  - Impact score trends
  - Risk level trends
  - Credibility rating trends
  - Consistency score trends
  - Performance rating trends
  - Multi-criteria comparisons (combining any metrics)
  - Heatmaps for sentiment and impact (by department or employee)
- **Imports Page**: CSV, TSV, TXT data import functionality for:
  - Bulk employee data
  - Historical reports
  - Reference (Vision) data
  - Job descriptions
- **Sync Page**: SQL Server to PostgreSQL data synchronization with:
  - Manual sync triggers (incremental or full)
  - Real-time sync progress monitoring
  - Sync history and error tracking
  - Configuration overview

### Analysis Features

- **Weekly Analysis Provides**:
  - Key achievements with:
    - **Impact Score** (1-10 scale mapped to organizational levels)
    - **Impact Reason** (separate field explaining the rating)
    - **Data Verification** (supported/contradicted/none)
  - Challenges with severity assessment
  - Overall sentiment
  - Risk level and explanation (credibility-adjusted)
  - **Point-based credibility assessment** with:
    - Rating (high/medium/low)
    - Specific exaggeration flags
    - Consistency score
    - Impact score discounts applied (0%, 15%, 40%)
  - **Role-based performance assessment** with:
    - JD alignment evaluation
    - Designation appropriate expectations
    - Key strengths and improvement areas
  - Recommended action items with ownership assignment

- **Monthly Analysis Provides**:
  - Performance and sentiment trends with credibility trajectory
  - Most significant achievements across the month (with impact score, impact reason, data verification)
  - Recurring challenges and their resolution status
  - Performance consistency metrics (task completion, work quality, performance stability)
  - Professional growth indicators (skill development, confidence changes, challenge approach)
  - Key focus areas with time investment and priority assessment
  - Overall risk assessment with credibility adjustments and mitigation recommendations
  - Strategic recommendations with priority and ownership levels

- **Quarterly Analysis Provides**:
  - Strategic alignment with organizational mission priorities and **role fit assessment**:
    - Role alignment rating (strong/partial/weak)
    - Detailed JD fit evaluation
    - Stretch contributions beyond role scope
    - Gaps between role requirements and actual work
  - Achievement themes with mission outcome measurements (using impact_score/impact_reason structure)
  - Performance trajectory and notable shifts with consistency metrics
  - Challenge patterns and adaptation effectiveness
  - Cross-functional impact with **collaboration type classification**:
    - Leading Initiative
    - Contributing Expertise
    - Mentoring
    - Process Improvement
  - Skill development and proficiency assessment with learning agility and autonomy ratings
  - Behavioral assessments (ownership, collaboration, communication, problem-solving, quality standards)
  - **Quarterly credibility assessment** with monthly aggregation and vision data alignment
  - **Career progression evaluation** with promotion readiness indicators
  - Comprehensive forward planning with **ownership assignment** (employee/manager/hr/cross-team)
  - Executive summary of quarterly performance with confidence indicators

### Data Import System

- **CSV, TSV, TXT Import Capabilities**:
  - Import employee data (new employees, department updates)
  - Import historical reports (backfill data)
  - Import vision data
  - Import job descriptions
  - Import supervisor feedback evaluations

- **Import Features**:
  - Dry run validation (validate without committing to database)
  - Error threshold settings (set maximum acceptable error percentage)
  - Configurable processing modes (bulk or row-by-row)
  - Chunk processing for large files
  - Detailed error reporting and logs

- **Import Monitoring**:
  - Real-time status tracking
  - Error analysis and reporting
  - Import metrics (success rate, processing time)

### Vector Search System

- **Report Vectorization**: When reports are submitted, they are:
  - Automatically converted to vector embeddings
  - Stored in the Qdrant vector database
  - Indexed for semantic search

- **Search Capabilities**:
  - Semantic search across all reports
  - Context-based retrieval (not just keyword matching)
  - Relevance-ranked results
  - Topic-based clustering

- **Use Cases**:
  - Find similar past challenges
  - Identify recurring patterns
  - Search for specific types of achievements
  - Find reports discussing particular topics

### Task Management System

- **Background Processing**:
  - All analysis jobs run asynchronously
  - Monthly and quarterly analyses processed in the background
  - Import and sync jobs run as background tasks

- **Task Tracking**:
  - Real-time status updates
  - Progress monitoring
  - Completion notifications

- **Result Retrieval**:
  - Access completed task results
  - Error handling for failed tasks
  - Task history and audit trail


### SQL Server Data Sync

The sync functionality allows you to migrate data from SQL Server to PostgreSQL, either through scheduled automation or manual triggers.

#### Sync Types

- **Employee Reports Sync**: Synchronizes employee report data from the `EmployeeReports` table
- **Vision Data Sync**: Synchronizes vision/goal data from the `VisionEmployeeData` table
- **Job Descriptions Sync**: Synchronizes job description data from the `EmployeeJobDescriptions` table
- **Supervisor Feedback Sync**: Synchronizes performance evaluation data from the `SupervisorFeedback` table
- **Full System Sync**: Runs all four syncs sequentially

#### Sync Modes

- **Incremental Sync**: Only syncs records modified since the last successful sync
  - Uses timestamp columns (`LastModifiedDate`, `ModifiedDate`) to detect changes
  - Faster and more efficient for regular updates
  - Recommended for scheduled automation

- **Full Sync**: Syncs all records regardless of modification date
  - Useful for initial data migration or data refresh
  - Handles creates, updates, and ensures data consistency
  - Recommended for first-time sync or after schema changes

#### Sync Security Features

The sync system includes multiple security measures:

- **Table Whitelisting**: Only configured tables can be queried
- **Column Whitelisting**: Timestamp columns are validated against a whitelist
- **SQL Injection Prevention**: Parameterized queries and input validation
- **Connection Encryption**: SSL/TLS encryption enabled by default
- **Batch Size Limits**: Prevents memory exhaustion attacks
- **Error Threshold**: Aborts sync if error rate exceeds threshold

#### Sync Error Handling

- **Validation Errors**: Records failing validation are logged but don't stop the sync
- **Partial Completion**: If some records fail, sync completes with "partial" status
- **Error Details**: Each error includes row number, field name, and error message
- **Error Threshold**: Sync aborts if errors exceed configured percentage
- **Retry Support**: Failed syncs can be manually retried

### Using the API

The system provides a comprehensive REST API:

#### Employee Management
- `POST /employees/` - Create a new employee
- `GET /employees/` - Get all employees

#### Report Management
- `POST /reports/create` - Submit a new report
- `POST /reports/form` - Submit a structured report form
- `GET /reports/{employee_id}` - Get all reports for an employee

#### Analysis Endpoints
- `POST /analyses/analyze/{report_id}` - Request analysis of a specific report
- `GET /analyses/results/{report_id}` - Get analysis results for a report
- `GET /analyses/employee/{employee_id}` - Get all analyses for an employee
- `POST /analyses/monthly/analyze` - Request monthly analysis
- `GET /analyses/monthly/{analysis_id}` - Get monthly analysis by ID
- `POST /analyses/quarterly/analyze` - Request quarterly analysis
- `GET /analyses/quarterly/{analysis_id}` - Get quarterly analysis by ID

#### Visualization Endpoints
- `GET /visualizations/sentiment-trends` - Get sentiment trend data
- `GET /visualizations/impact-trends` - Get impact score trend data
- `GET /visualizations/risk-trends` - Get risk level trend data
- `GET /visualizations/credibility-trends` - Get credibility trend data
- `GET /visualizations/consistency-trends` - Get consistency trend data
- `GET /visualizations/performance-trends` - Get performance trend data
- `GET /visualizations/sentiment-heatmap` - Get sentiment heatmap data
- `GET /visualizations/impact-heatmap` - Get impact heatmap data
- `GET /visualizations/multi-criteria-trends` - Compare multiple metrics

#### Task Management Endpoints
- `GET /tasks/{task_id}` - Check status of a task
- `GET /tasks/{task_id}/result` - Get results of a completed task

#### Import Endpoints
- `POST /imports/upload` - Upload CSV file for import
- `GET /imports/{job_id}` - Get import job status
- `GET /imports/{job_id}/errors` - Get detailed import errors
- `GET /imports/` - List all import jobs

#### Sync Endpoints
- `POST /sync/trigger/employee_reports` - Trigger employee reports sync
- `POST /sync/trigger/vision_data` - Trigger vision data sync
- `POST /sync/trigger/job_descriptions` - Trigger job descriptions sync
- `POST /sync/trigger/supervisor_feedback` - Trigger supervisor feedback sync
- `POST /sync/trigger/full` - Trigger full system sync (all four types)
- `GET /sync/status/{sync_id}` - Get sync job status
- `GET /sync/last-successful/{sync_type}` - Get last successful sync info
- `GET /sync/history` - List sync history
- `GET /sync/{sync_id}/errors` - Get sync errors
- `GET /sync/config` - Get sync configuration
- `GET /sync/test-connection` - Test SQL Server connection


API documentation is available at `/docs` when running the application.

---

## 🔍 Troubleshooting

- **Database Connection Issues**: Verify PostgreSQL is running and credentials are correct
- **Ollama Issues**: Make sure Ollama is running (check system tray) and the LLaMA model is downloaded
- **Redis/Celery Issues**: Ensure Redis container is running (`docker ps`)
- **Qdrant Issues**: Verify Qdrant is accessible at http://localhost:6333/
- **Installation Errors**: Ensure Visual Studio Build Tools are properly installed on Windows
- **CSV Import Errors**: Check file format, encoding (UTF-8 recommended), and column headers
- **Task Processing Issues**: Verify Celery worker is running and properly connected to Redis

---

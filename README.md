# 🧠 Employee Report Analysis System

A AI-powered system for analyzing employee reports to extract valuable insights, identify trends, and facilitate data-driven management decisions through natural language processing.

---

## 📋 Overview

**Employee Report Analysis** is an intelligent application that leverages **Large Language Models (LLMs)** and **vector search** to automatically analyze employee reports. The system extracts key information such as:

- Achievements and their impact
- Challenges and their severity
- Sentiment analysis
- Risk assessments
- Credibility evaluation
- Performance assessments
- Recommended action items

The system also performs **monthly analysis** across all reports from an employee to identify trends, recurring challenges, and growth indicators, as well as **quarterly analysis** for strategic alignment, achievement themes, and long-term performance evaluation.

---

## ✨ Key Features

- **Weekly Report Analysis**: Extract structured insights from unstructured employee reports
- **Monthly Performance Analysis**: Analyze trends and patterns across all reports from a month
- **Quarterly Performance Analysis**: Evaluate strategic alignment, achievement themes, and behavioral assessments over a quarter
- **Semantic Search**: Find relevant reports based on context, not just keywords
- **Risk Assessment**: Automatically identify potential issues requiring attention
- **Sentiment Analysis**: Track employee sentiment over time
- **Credibility Evaluation**: Assess report credibility with specific exaggeration flags
- **Performance Rating**: Provide balanced performance assessments with strengths and improvement areas
- **Historical Context**: Analyze reports with previous submissions for reference
- **Asynchronous Processing**: Background task processing for analysis requests
- **Direct URL Sharing**: Share analysis results via URL parameters
- **CSV Data Import**: Bulk import of employee data, historical reports, and related information
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

- **API Layer**: RESTful endpoints for employees, reports, analyses, tasks, visualizations, and imports
- **Services Layer**: Business logic for report processing and analysis
- **Task Processing**: 
  - Celery for asynchronous task management
  - Task status tracking and result retrieval
  - Configurable processing options for long-running tasks
- **Storage**:
  - PostgreSQL for structured data
  - Qdrant for vector embeddings and semantic search
  - Redis for task queue management and caching
- **LLM Integration**: Ollama & vLLM for natural language understanding and structured output generation
- **Frontend Layer**: HTML, CSS, and JavaScript for user interaction
- **Vector Store**:
  - Automatic vectorization of reports upon submission
  - Semantic similarity search
  - Context-based retrieval of relevant historical data

---

## 🛠️ Technologies Used

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Vector Store**: Qdrant
- **Task Queue**: Celery with Redis
- **LLM Provider**: Ollama, vLLM
- **Embeddings**: Ollama, vLLM
- **Documentation**: Swagger / OpenAPI
- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Containerization**: Docker for services (Redis, Qdrant, vLLM)
- **UI Framework**: Custom responsive design

---

## 📦 Setup and Installation

### Prerequisites

- Python 3.10+
- PostgreSQL database
- Docker Desktop (for Redis and Qdrant containers)
- Ollama with the LLaMA 3.1 model
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
     DATABASE_URL=postgresql://username:password@localhost:5432/employee_report_db
     VECTOR_STORE_PORT=6333
     OLLAMA_BASE_URL=http://localhost:11434
     OLLAMA_MODEL=llama3.1
     ```

4. **Start the Application**

   - **Start the backend server**:
     ```bash
     uvicorn app.main:app --reload
     ```
   
   - **Start the Celery worker** (in a separate terminal):
     ```bash
     celery -A app.worker.worker worker --loglevel=info
     ```

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
- **Imports Page**: CSV data import functionality for:
  - Bulk employee data
  - Historical reports
  - Reference data

### Analysis Features

- **Weekly Analysis Provides**:
  - Key achievements with impact ratings
  - Challenges with severity assessment
  - Overall sentiment
  - Risk level and explanation
  - Credibility assessment with potential exaggeration flags
  - Performance assessment with strengths and improvement areas
  - Recommended action items

- **Monthly Analysis Provides**:
  - Performance and sentiment trends
  - Most significant achievements across the month
  - Recurring challenges and their resolution status
  - Performance consistency metrics
  - Professional growth indicators
  - Key focus areas for the employee
  - Overall risk assessment with mitigation recommendations
  - Strategic recommendations for management

- **Quarterly Analysis Provides**:
  - Strategic alignment with organizational priorities
  - Achievement themes with business outcome measurements
  - Performance trajectory and notable shifts
  - Challenge patterns and adaptation effectiveness
  - Cross-functional impact on stakeholders
  - Skill development and proficiency assessment
  - Behavioral assessments (ownership, collaboration, communication, etc.)
  - Credibility assessment with vision data alignment
  - Comprehensive forward planning (keep/improve/start/stop)
  - Executive summary of quarterly performance

### Data Import System

- **CSV Import Capabilities**:
  - Import employee data (new employees, department updates)
  - Import historical reports (backfill data)
  - Import reference data (organizational goals, KPIs)
  - Import vision data (for credibility assessment)

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
  - Import jobs run as background tasks

- **Task Tracking**:
  - Real-time status updates
  - Progress monitoring
  - Completion notifications

- **Result Retrieval**:
  - Access completed task results
  - Error handling for failed tasks
  - Task history and audit trail

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

## 📝 License

MIT License

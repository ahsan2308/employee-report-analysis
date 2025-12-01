# Employee Report Analysis API Documentation

## Overview

This document provides comprehensive documentation for the Employee Report Analysis API. The API allows for managing employees, submitting reports, analyzing performance, visualizing data trends, importing data through CSV files, and synchronizing data from SQL Server.


## Authentication

Authentication details to be determined. All endpoints currently accessible without authentication.


## Table of Contents

- [Employees](#employees)
- [Reports](#reports)
- [Analyses](#analyses)
  - [Report Analysis](#report-analysis)
  - [Monthly Analysis](#monthly-analysis)
  - [Quarterly Analysis](#quarterly-analysis)
- [Visualizations](#visualizations)
  - [Trend Visualizations](#trend-visualizations)
  - [Heatmap Visualizations](#heatmap-visualizations)
  - [Multi-criteria Trends](#multi-criteria-trends)
- [Background Tasks](#background-tasks)
- [CSV Imports](#csv-imports)
- [SQL Server Sync](#sql-server-sync)
  - [Trigger Endpoints](#trigger-endpoints)
  - [Status & Monitoring](#status--monitoring)
  - [History & Reporting](#history--reporting)
  - [Configuration](#configuration)
- [Schema Definitions](#schema-definitions)



<div style="page-break-after: always;"></div>

## Employees

Endpoints for managing employee records.

### Create Employee

Creates a new employee record.

**Endpoint:** `POST /employees/`

**Request Body:**
```json
{
  "name": "John Doe",
  "wing": "Technical",
  "position": "Software Engineer"
}
```

**Response:**
```json
{
  "message": "Employee added successfully",
  "employee": {
    "id": 1,
    "name": "John Doe",
    "wing": "Technical",
    "position": "Software Engineer"
  }
}
```

### Get All Employees

Retrieves a list of all employees.

**Endpoint:** `GET /employees/`

**Response:**
```json
[
  {
    "id": 1,
    "name": "John Doe",
    "wing": "Technical",
    "position": "Software Engineer"
  },
  {
    "id": 2,
    "name": "Jane Smith",
    "wing": "Management",
    "position": "Project Manager"
  }
]
```

<div style="page-break-after: always;"></div>

## Reports

Endpoints for managing employee reports.

### Create Report

Creates a new report with raw text.

**Endpoint:** `POST /reports/create`

**Request Body:**
```json
{
  "employee_id": 1,
  "report_date": "2023-04-15",
  "report_text": "This week I completed the API integration and fixed several bugs in the user authentication system."
}
```

**Response:**
```json
{
  "message": "Report added successfully",
  "report": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "employee_id": 1,
    "report_date": "2023-04-15",
    "report_text": "This week I completed the API integration and fixed several bugs in the user authentication system."
  }
}
```

### Submit Report Form

Submits a structured weekly report form.

**Endpoint:** `POST /reports/form`

**Request Body:**
```json
{
  "employee_id": 1,
  "key_tasks_completed": "Implemented the user authentication API",
  "impact_outcome": "Increased security and simplified the login process",
  "challenges_faced": "Integration with legacy systems was challenging",
  "support_required": "Need additional testing resources",
  "tasks_planned_next_week": "Implement password reset functionality",
  "confidence_level": 4,
  "nothing_to_report_reason": null
}
```

**Notes:**
- Either `key_tasks_completed` or `nothing_to_report_reason` must be provided
- `confidence_level` must be between 1 and 5

**Response:**
```json
{
  "message": "Report submitted successfully.",
  "report_id": "550e8400-e29b-41d4-a716-446655440000"
}
```
<div style="page-break-after: always;"></div>

### Get Employee Reports

Retrieves all reports for a specific employee.

**Endpoint:** `GET /reports/{employee_id}`

**Path Parameters:**
- `employee_id` (integer): ID of the employee

**Response:**
```json
{
  "employee_id": 1,
  "employee_name": "John Doe",
  "reports": [
    {
      "report_id": "550e8400-e29b-41d4-a716-446655440000",
      "employee_id": 1,
      "report_date": "2023-04-15",
      "report_text": "Key Tasks: Implemented the user authentication API\nImpact: Increased security..."
    }
  ]
}
```


<div style="page-break-after: always;"></div>


## Analyses

Endpoints for analyzing employee reports and performance.

### Weekly Report Analysis

#### Analyze Weekly Report

Submits a report for asynchronous analysis.

**Endpoint:** `POST /analyses/analyze/{report_id}`

**Path Parameters:**
- `report_id` (string): UUID of the report to analyze

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "pending",
  "created_at": "2023-04-15T14:30:00Z",
  "started_at": null,
  "completed_at": null,
  "is_complete": false
}
```
<div style="page-break-after: always;"></div>

#### Get Analysis Results

Retrieves analysis results for a specific report.

**Endpoint:** `GET /analyses/results/{report_id}`

**Path Parameters:**
- `report_id` (string): UUID of the analyzed report

**Response:**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "employee_name": "John Doe",
  "sentiment": 0.75,
  "sentiment_score": 0.75,
  "risk_level": "low",
  "risk_explanation": "No significant risks identified in this report.",
  "full_analysis_json": {
    "topics": ["Muharram Security", "Intelligence Reporting"],
    "sentiment": "positive",
    "challenges": "...."
  },
  "achievements_json": [
    {
      "description": "Implemented user authentication API",
      "impact": "8 (Improved security and user experience)"
    }
  ],
  "challenges_json": [
    {
      "description": "Integration with legacy systems",
      "severity": "medium"
    }
  ],
  "topics": ["authentication", "security", "api", "legacy integration"],
  "action_items": ["Complete password reset implementation", "Coordinate testing resources"],
  "credibility_assessment": {
    "rating": "high",
    "explanation": "Report details are specific and verifiable.",
    "exaggeration_flags": [],
    "consistency_score": "high"
  },
  "performance_assessment": {
    "rating": "high",
    "summary": "Strong performance with significant progress on key deliverables.",
    "key_strengths": ["Technical implementation", "Security focus"],
    "improvement_areas": ["Coordination with legacy systems"]
  }
}
```

<div style="page-break-after: always;"></div>

#### Get Employee Analyses

Retrieves a list of all analyses for a specific employee.

**Endpoint:** `GET /analyses/employee/{employee_id}`

**Path Parameters:**
- `employee_id` (integer): ID of the employee

**Response:**
```json
{
  "employee_id": 1,
  "employee_name": "John Doe",
  "analyses": [
    {
      "analysis_id": 1,
      "report_id": "550e8400-e29b-41d4-a716-446655440000",
      "report_date": "2023-04-15",
      "sentiment_score": 0.75,
      "risk_level": "low",
      "performance_rating": "high"
    }
  ]
}
```

#### Get Analysis by ID

Retrieves a specific analysis by its ID.

**Endpoint:** `GET /analyses/{analysis_id}`

**Path Parameters:**
- `analysis_id` (integer): ID of the analysis

**Response:**
Same as `GET /analyses/results/{report_id}`

<div style="page-break-after: always;"></div>

### Monthly Analysis

#### Analyze Monthly Reports

Submits a request for monthly analysis of an employee's reports.

**Endpoint:** `POST /analyses/monthly/analyze`

**Query Parameters:**
- `employee_id` (integer): ID of the employee
- `year` (integer): Year for analysis (2000-2100)
- `month` (integer): Month for analysis (1-12)

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "pending",
  "created_at": "2023-04-15T14:30:00Z",
  "started_at": null,
  "completed_at": null,
  "is_complete": false
}
```

#### Get Monthly Analysis

Retrieves a specific monthly analysis by ID.

**Endpoint:** `GET /analyses/monthly/{analysis_id}`

**Path Parameters:**
- `analysis_id` (integer): ID of the monthly analysis

**Response:**
```json
{
  "analysis_id": 1,
  "employee_id": 1,
  "employee_name": "John Doe",
  "year": 2023,
  "month": 4,
  "period_start": "2023-04-01",
  "period_end": "2023-04-30",
  "avg_sentiment_score": 0.72,
  "progress_trends": {
    "sentiment_trend": "improving",
    "performance_trend": "stable",
    "risk_level_pattern": "decreasing",
    "challenge_resolution_progress": "improved"
  },
  "monthly_achievements": [
    {
      "description": "Completed user authentication system",
      "impact": "8 (Significant impact on security posture)"
    }
  ],
  "recurring_challenges": [
    {
      "description": "Integration with legacy systems",
      "severity": "medium",
      "status": "ongoing"
    }
  ],
  "consistency_assessment": {
    "task_completion_reliability": "high",
    "work_quality_consistency": "medium",
    "performance_stability": "high",
    "notable_strengths": ["Delivers on time", "Maintains code quality"],
    "notable_weaknesses": ["Documentation could be improved"]
  },
  "growth_indicators": {
    "complexity_of_tasks": "increased",
    "skill_development_evidence": "high",
    "confidence_level_change": "increased",
    "approach_to_challenges": "more proactive"
  },
  "focus_areas": [
    {
      "project": "API Security",
      "time_investment": "high",
      "priority_level": "high"
    }
  ],
  "monthly_risk_assessment": {
    "overall_risk_level": "low",
    "risk_explanation": "Employee is performing well with minimal risks.",
    "significant_risks": ["Limited documentation"],
    "escalating_risks": ["No cross departmental collaboration"],
    "risk_mitigation_recommendations": ["Implement documentation standards"]
  },
  "strategic_recommendations": [
    {
      "action": "Provide mentoring opportunities",
      "priority": "medium"
    }
  ],
  "monthly_summary": "John Doe has shown strong performance throughout April, completing the authentication syste."
}
```

<div style="page-break-after: always;"></div>

#### Get Employee Monthly Analyses

Retrieves all monthly analyses for a specific employee.

**Endpoint:** `GET /analyses/monthly/employee/{employee_id}`

**Path Parameters:**
- `employee_id` (integer): ID of the employee

**Response:**
```json
[
  {
    "analysis_id": 1,
    "employee_id": 1,
    "year": 2023,
    "month": 4,
    "period_start": "2023-04-01",
    "period_end": "2023-04-30",
    "performance_trend": "stable",
    "sentiment_trend": "improving",
    "risk_level": "low",
    "achievement_count": 3,
    "challenge_count": 1,
    "monthly_summary": "John Doe has shown strong performance throughout April, completing the authentication system ahead of schedule."
  }
]
```

#### Get Employee Monthly Analysis by Period

Retrieves a specific monthly analysis for an employee by year and month.

**Endpoint:** `GET /analyses/monthly/employee/{employee_id}/{year}/{month}`

**Path Parameters:**
- `employee_id` (integer): ID of the employee
- `year` (integer): Year of the analysis
- `month` (integer): Month of the analysis (1-12)

**Response:**
Same as `GET /analyses/monthly/{analysis_id}`

<div style="page-break-after: always;"></div>

### Quarterly Analysis

#### Analyze Quarterly Reports

Submits a request for quarterly analysis of an employee's performance.

**Endpoint:** `POST /analyses/quarterly/analyze`

**Query Parameters:**
- `employee_id` (integer): ID of the employee
- `year` (integer): Year for analysis (2000-2100)
- `quarter` (integer): Quarter for analysis (1-4)

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "pending",
  "created_at": "2023-04-15T14:30:00Z",
  "started_at": null,
  "completed_at": null,
  "is_complete": false
}
```

#### Get Quarterly Analysis

Retrieves a specific quarterly analysis by ID.

**Endpoint:** `GET /analyses/quarterly/{analysis_id}`

**Path Parameters:**
- `analysis_id` (integer): ID of the quarterly analysis

**Response:**
```json
{
  "analysis_id": 1,
  "employee_id": 1,
  "employee_name": "John Doe",
  "year": 2023,
  "quarter": 2,
  "period_start": "2023-04-01",
  "period_end": "2023-06-30",
  "monthly_analysis_ids": [1, 2, 3],
  
  "organizational_impact": "team",
  "strategic_alignment": {
    "organizational_impact": "team",
    "key_initiatives": [
      {
        "initiative": "Security Enhancement Program",
        "alignment": "high",
        "outcomes": "Implemented authentication system"
      }
    ]
  },
  
  "performance_trend": "improving",
  "task_completion_reliability": "high",
  "work_quality_consistency": "high",
  "performance_stability": "high",
  "achievement_themes": [
    {
      "theme": "Security improvements",
      "related_achievements": ["Implemented authentication API", "Updated security protocols"],
      "impact": "8 (Significant impact on system security)",
      "business_outcome": "Reduced security vulnerabilities by 40%",
      "vision_verified": true
    }
  ],
  "performance_trajectory": {
    "trend": "improving",
    "consistency": {
      "task_completion_reliability": "high",
      "work_quality_consistency": "high",
      "performance_stability": "high"
    },
    "notable_shifts": [
      {
        "month": "May",
        "description": "Increased quality of deliverables",
        "factors": "Completion of advanced training"
      }
    ]
  },
  
  "collaboration_effectiveness": "high",
  "stakeholder_count": 5,
  "challenge_patterns": {
    "recurring_challenges": [
      {
        "description": "Legacy system integration",
        "type": "internal",
        "frequency": "constant",
        "resolution_status": "ongoing",
        "systemic": true
      }
    ],
    "adaptation_effectiveness": "high"
  },
  "cross_functional_impact": {
    "collaboration_effectiveness": "high",
    "stakeholder_impacts": [
      {
        "stakeholder": "Security Team",
        "impact": "Positive",
        "evidence": "Streamlined authentication workflows"
      }
    ],
    "knowledge_sharing": ["Conducted training sessions on new security protocols"]
  },
  "adaptation_effectiveness": "high",
  
  "risk_level": "low",
  "risk_trend": "decreasing",
  "risk_assessment": {
    "overall_risk_level": "low",
    "risk_trend": "decreasing",
    "key_risk_factors": ["Legacy system dependencies"],
    "mitigation_strategies": ["Incremental migration plan"]
  },
  
  "learning_agility": "high",
  "autonomy_level": "high",
  "development_focus": "Advanced security practices",
  "skill_development": {
    "key_capabilities": [
      {
        "skill": "API Security",
        "proficiency": "advanced",
        "growth": "improved"
      }
    ],
    "learning_agility": "high",
    "autonomy_level": "high",
    "development_focus": "Advanced security practices"
  },
  "behavioral_assessment": {
    "ownership": {
      "rating": "exceeds",
      "evidence": "Consistently takes initiative on security issues"
    },
    "collaboration": {
      "rating": "meets",
      "evidence": "Works well with security and development teams"
    },
    "communication": {
      "rating": "meets",
      "evidence": "Clear documentation of security protocols"
    },
    "problem_solving": {
      "rating": "exceeds",
      "evidence": "Creative solutions to legacy integration challenges"
    },
    "quality_standards": {
      "rating": "meets",
      "evidence": "Thorough testing of authentication implementations"
    }
  },
  
  "credibility_rating": "high",
  "vision_data_alignment": "high",
  "credibility_assessment": {
    "rating": "high",
    "explanation": "Consistently accurate reporting with verification from vision system",
    "vision_data_alignment": "high",
    "impact_on_evaluation": "High credibility strengthens positive performance assessment"
  },
  
  "forward_planning": {
    "keep_doing": ["API security improvements", "Cross-team collaboration"],
    "improve": ["Documentation processes"],
    "start": ["Mentoring junior developers"],
    "stop": ["Manual testing processes"],
    "support_needed": ["Advanced security certification"]
  },
  
  "quarterly_summary": "John Doe has demonstrated consistent high performance throughout Q2 with notable contributions."
}
```

#### Get Employee Quarterly Analysis by Period

Retrieves a specific quarterly analysis for an employee by year and quarter.

**Endpoint:** `GET /analyses/quarterly/employee/{employee_id}/{year}/{quarter}`

**Path Parameters:**
- `employee_id` (integer): ID of the employee
- `year` (integer): Year of the analysis
- `quarter` (integer): Quarter of the analysis (1-4)

**Response:**
Same as `GET /analyses/quarterly/{analysis_id}`

<div style="page-break-after: always;"></div>

## Visualizations

Endpoints for retrieving visualization data.

### Trend Visualizations

#### Sentiment Trends

Retrieves sentiment trend data for visualization.

**Endpoint:** `GET /visualizations/sentiment-trends`

**Query Parameters:**
- `employee_id` (integer, optional): Filter by specific employee ID
- `department` (string, optional): Filter by specific department/wing
- `start_date` (date, optional): Start date for analysis (YYYY-MM-DD)
- `end_date` (date, optional): End date for analysis (YYYY-MM-DD)
- `interval` (string, default: "month"): Time interval for grouping ('day', 'week', 'month', 'quarter', 'year')

**Response:**
```json
{
  "labels": ["2023-01", "2023-02", "2023-03", "2023-04"],
  "datasets": [
    {
      "label": "Average Sentiment",
      "data": [0.65, 0.70, 0.68, 0.75],
      "metadata": {
        "min": 0.65,
        "max": 0.75,
        "avg": 0.695
      }
    }
  ]
}
```

**Notes:**
- Time periods in `labels` use ISO-like format based on interval (e.g., "2023-01" for months, "2023-W01" for weeks)
- If no data is found, an empty structure is returned: `{"labels": [], "datasets": []}`

#### Impact Trends

Retrieves impact score trend data for visualization.

**Endpoint:** `GET /visualizations/impact-trends`

**Query Parameters:**
Same as for sentiment trends.

**Response:**
Same structure as sentiment trends response.

#### Risk Trends

Retrieves risk level trend data for visualization.

**Endpoint:** `GET /visualizations/risk-trends`

**Query Parameters:**
Same as for sentiment trends.

**Response:**
Same structure as sentiment trends response.

**Notes:**
- Risk levels ("low", "medium", "high") are converted to numeric scores (0.2, 0.5, 0.8) for visualization

<div style="page-break-after: always;"></div>

#### Credibility Trends

Retrieves credibility rating trend data for visualization.

**Endpoint:** `GET /visualizations/credibility-trends`

**Query Parameters:**
Same as for sentiment trends.

**Response:**
Same structure as sentiment trends response.

**Notes:**
- Credibility ratings ("low", "medium", "high") are converted to numeric scores (0.2, 0.5, 0.8) for visualization

#### Consistency Trends

Retrieves consistency score trend data for visualization.

**Endpoint:** `GET /visualizations/consistency-trends`

**Query Parameters:**
Same as for sentiment trends.

**Response:**
Same structure as sentiment trends response.

**Notes:**
- Consistency scores ("low", "medium", "high") are converted to numeric scores (0.2, 0.5, 0.8) for visualization

#### Performance Trends

Retrieves performance rating trend data for visualization.

**Endpoint:** `GET /visualizations/performance-trends`

**Query Parameters:**
Same as for sentiment trends.

**Response:**
Same structure as sentiment trends response.

**Notes:**
- Performance ratings ("low", "medium", "high") are converted to numeric scores (0.2, 0.5, 0.8) for visualization

<div style="page-break-after: always;"></div>

### Heatmap Visualizations

#### Sentiment Heatmap

Retrieves sentiment heatmap data for visualization.

**Endpoint:** `GET /visualizations/sentiment-heatmap`

**Query Parameters:**
- `dimension` (string, default: "department"): Dimension for y-axis (must be either 'department' or 'employee')
- `start_date` (date, optional): Start date for analysis (YYYY-MM-DD)
- `end_date` (date, optional): End date for analysis (YYYY-MM-DD)
- `interval` (string, default: "month"): Time interval for x-axis ('day', 'week', 'month', 'quarter', 'year')

**Response:**
```json
{
    "x_labels": ["2023-01", "2023-02", "2023-03", "2023-04"],
    "y_labels": ["Technical", "Management", "Sales"],
    "cells": [
        {"x": 0, "y": 0, "value": 0.72},
        {"x": 0, "y": 1, "value": 0.68},
        {"x": 0, "y": 2, "value": 0.75},
        {"x": 1, "y": 0, "value": 0.70},
        {"x": 1, "y": 1, "value": 0.65},
        {"x": 1, "y": 2, "value": 0.80}
    ],
    "metadata": {
        "min": 0.65,
        "max": 0.80,
        "avg": 0.72
    }
}
```

**Notes:**
- Time periods in `x_labels` use ISO-like format based on interval (e.g., "2023-01" for months, "2023-W01" for weeks)
- If no data is found, an empty structure is returned: `{"x_labels": [], "y_labels": [], "cells": [], "metadata": {"min": 0, "max": 0, "avg": 0}}`

#### Impact Heatmap

Retrieves impact score heatmap data for visualization.

**Endpoint:** `GET /visualizations/impact-heatmap`

**Query Parameters:**
Same as for sentiment heatmap.

**Response:**
Same structure as sentiment heatmap response.

<div style="page-break-after: always;"></div>

### Multi-criteria Trends

Retrieves trend data for multiple criteria for comparison visualization.

**Endpoint:** `GET /visualizations/multi-criteria-trends`

**Query Parameters:**
- `criteria` (array of strings): List of criteria to include (comma-separated list of: sentiment, risk, credibility, consistency, performance, impact)
- `employee_id` (integer, optional): Filter by specific employee ID
- `department` (string, optional): Filter by specific department/wing
- `start_date` (date, optional): Start date for analysis (YYYY-MM-DD)
- `end_date` (date, optional): End date for analysis (YYYY-MM-DD)
- `interval` (string, default: "month"): Time interval for grouping ('day', 'week', 'month', 'quarter', 'year')

**Response:**
```json
{
  "labels": ["2023-01", "2023-02", "2023-03", "2023-04"],
  "datasets": [
    {
      "label": "Sentiment Score",
      "data": [0.65, 0.70, 0.68, 0.75],
      "metadata": {
        "min": 0.65,
        "max": 0.75,
        "avg": 0.695
      },
      "backgroundColor": "rgba(255, 99, 132, 0.2)",
      "borderColor": "rgb(255, 99, 132)"
    },
    {
      "label": "Performance Rating",
      "data": [0.60, 0.65, 0.72, 0.78],
      "metadata": {
        "min": 0.60,
        "max": 0.78,
        "avg": 0.6875
      },
      "backgroundColor": "rgba(54, 162, 235, 0.2)",
      "borderColor": "rgb(54, 162, 235)"
    }
  ]
}
```

**Notes:**
- Time periods in `labels` use ISO-like format based on interval (e.g., "2023-01" for months, "2023-W01" for weeks)
- All categorical values (low, medium, high) are converted to numeric scores (0.2, 0.5, 0.8) for visualization
- `backgroundColor` and `borderColor` are only included for multi-criteria trends
- At least one criterion must be specified
- If no data is found, an empty structure is returned: `{"labels": [], "datasets": []}`

<div style="page-break-after: always;"></div>

## Background Tasks

Endpoints for managing background tasks.

### Get Task Status

Retrieves the current status of a background task.

**Endpoint:** `GET /tasks/{task_id}`

**Path Parameters:**
- `task_id` (UUID): ID of the task

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "celery_task_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "completed",
  "created_at": "2023-04-15T14:30:00Z",
  "started_at": "2023-04-15T14:30:05Z",
  "completed_at": "2023-04-15T14:31:00Z",
  "duration": 55.0,
  "is_complete": true
}
```

<div style="page-break-after: always;"></div>

### Get Task Result

Retrieves the result of a completed task.

**Endpoint:** `GET /tasks/{task_id}/result`

**Path Parameters:**
- `task_id` (UUID): ID of the task

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "analysis_id": 1,
    "report_id": "550e8400-e29b-41d4-a716-446655440002",
    "employee_name": "John Doe",
    "sentiment": 0.75,
    "sentiment_score": 0.75,
    "risk_level": "low",
    "risk_explanation": "No significant risks identified in this report.",
    "full_analysis_json": {},
    "achievements_json": [],
    "challenges_json": [],
    "topics": [],
    "action_items": [],
    "credibility_assessment": {
      "rating": "high",
      "explanation": "Report details are specific and verifiable.",
      "exaggeration_flags": [],
      "consistency_score": "high"
    },
    "performance_assessment": {
      "rating": "high",
      "summary": "Strong performance with significant progress on key deliverables.",
      "key_strengths": ["Technical implementation", "Security focus"],
      "improvement_areas": ["Coordination with legacy systems"]
    }
  },
  "error_message": null
}
```

**Notes:**
- The structure of the `result` field varies based on task type (report analysis, monthly analysis, or quarterly analysis)
- If task is not complete, returns 422 error
- If task failed, `error_message` will contain failure details

<div style="page-break-after: always;"></div>

## CSV Imports

Endpoints for importing data from CSV files.

### Upload CSV File

Uploads a CSV file for import and processing.

**Endpoint:** `POST /imports/upload`

**Form Data:**
- `file` (file): CSV file to upload
- `dry_run` (boolean, optional, default: false): Validate without writing to database
- `stop_on_error` (boolean, optional, default: false): Stop on first error
- `error_threshold_percent` (float, optional, default: 10.0): Maximum percentage of errors before aborting
- `chunk_size` (integer, optional, default: 1000): Number of rows to process in each chunk
- `processing_mode` (string, optional, default: "bulk"): Processing mode ("row_by_row" or "bulk")
- `csv_type` (string, optional): CSV type override (e.g., 'employee_report', 'vision_data')

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "employee_reports.csv",
  "status": "pending",
  "csv_type": "employee_report",
  "submitted_at": "2023-04-15T14:30:00Z",
  "started_at": null,
  "completed_at": null,
  "total_rows": 0,
  "processed_rows": 0,
  "successful_rows": 0,
  "error_count": 0,
  "metrics": {},
  "percent_complete": 0.0,
  "estimated_time_remaining": null
}
```
<div style="page-break-after: always;"></div>

### Get Import Job Status

Retrieves status and details for a specific import job.

**Endpoint:** `GET /imports/{job_id}`

**Path Parameters:**
- `job_id` (string): ID of the import job

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "employee_reports.csv",
  "status": "completed",
  "csv_type": "employee_report",
  "submitted_at": "2023-04-15T14:30:00Z",
  "started_at": "2023-04-15T14:30:05Z",
  "completed_at": "2023-04-15T14:35:00Z",
  "total_rows": 100,
  "processed_rows": 100,
  "successful_rows": 98,
  "error_count": 2,
  "metrics": {
    "employees_created": 10,
    "reports_created": 98
  },
  "percent_complete": 100.0,
  "estimated_time_remaining": null
}
```
<div style="page-break-after: always;"></div>

### Get Import Errors

Retrieves a paginated list of errors for a specific import job.

**Endpoint:** `GET /imports/{job_id}/errors`

**Path Parameters:**
- `job_id` (string): ID of the import job

**Query Parameters:**
- `page` (integer, default: 1): Page number
- `page_size` (integer, default: 100): Number of errors per page

**Response:**
```json
{
  "total": 2,
  "page": 1,
  "page_size": 100,
  "errors": [
    {
      "row_number": 15,
      "field_name": "From",
      "error_message": "Invalid date format: 15-April-2023. Please use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY format.",
      "row_data": {
        "Employee_ID": 5,
        "Name": "John Smith",
        "From": "15-April-2023"
      }
    },
    {
      "row_number": 42,
      "field_name": "Confidence_Level",
      "error_message": "Invalid confidence level format. Expected number between 1-5, got 'Very High'",
      "row_data": {
        "Employee_ID": 8,
        "Name": "Alice Johnson",
        "Confidence_Level": "Very High"
      }
    }
  ]
}
```

<div style="page-break-after: always;"></div>


### List Import Jobs

Lists all import jobs with optional filtering.

**Endpoint:** `GET /imports/`

**Query Parameters:**
- `status` (string, optional): Filter by status
- `csv_type` (string, optional): Filter by CSV type
- `limit` (integer, default: 50): Maximum number of jobs to return
- `offset` (integer, default: 0): Number of jobs to skip

**Response:**
```json
[
  {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "employee_reports.csv",
    "status": "completed",
    "csv_type": "employee_report",
    "submitted_at": "2023-04-15T14:30:00Z",
    "started_at": "2023-04-15T14:30:05Z",
    "completed_at": "2023-04-15T14:35:00Z",
    "total_rows": 100,
    "processed_rows": 100,
    "successful_rows": 98,
    "error_count": 2,
    "metrics": {
      "employees_created": 10,
      "reports_created": 98
    },
    "percent_complete": 100.0,
    "estimated_time_remaining": null
  },
  {
    "job_id": "550e8400-e29b-41d4-a716-446655440001",
    "filename": "vision_data.csv",
    "status": "processing",
    "csv_type": "vision_data",
    "submitted_at": "2023-04-16T10:00:00Z",
    "started_at": "2023-04-16T10:00:05Z",
    "completed_at": null,
    "total_rows": 200,
    "processed_rows": 100,
    "successful_rows": 98,
    "error_count": 2,
    "metrics": {},
    "percent_complete": 50.0,
    "estimated_time_remaining": "00:02:30"
  }
]
```

<div style="page-break-after: always;"></div>

## SQL Server Sync

Endpoints for synchronizing data from SQL Server to PostgreSQL. The sync system supports both incremental syncs (only new/modified records) and full syncs (all records).

### Trigger Endpoints

#### Trigger Employee Reports Sync

Triggers employee reports synchronization from SQL Server to PostgreSQL.

**Endpoint:** `POST /sync/trigger/employee_reports`

**Query Parameters:**
- `is_full_sync` (boolean, default: false): If true, perform full sync. If false, incremental sync.

**Response (202 Accepted):**
```json
{
  "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
  "task_id": "0030c389-1350-485c-b150-6e6a6e5cd210",
  "sync_type": "employee_reports",
  "status": "pending",
  "is_full_sync": false,
  "triggered_at": "2025-11-24T13:13:19Z",
  "message": "Employee reports sync (incremental) started successfully"
}
```

**Error Responses:**
- `409 Conflict`: Sync already in progress
```json
{
  "detail": "Employee reports sync already in progress (sync_id: c155260e-9177-4b53-bc14-e9f4d0e14cd2)"
}
```

**Notes:**
- This endpoint queues an asynchronous Celery task and returns immediately
- Use the returned `sync_id` to poll for status updates via `/sync/status/{sync_id}`
- Stale syncs (running > 60 minutes) are automatically cleared before checking for conflicts

<div style="page-break-after: always;"></div>

#### Trigger Vision Data Sync

Triggers vision data synchronization from SQL Server to PostgreSQL.

**Endpoint:** `POST /sync/trigger/vision_data`

**Query Parameters:**
- `is_full_sync` (boolean, default: false): If true, perform full sync. If false, incremental sync.

**Response (202 Accepted):**
```json
{
  "sync_id": "0c563781-7366-465d-931d-874b98af6277",
  "task_id": "1140d489-2461-596d-c261-7f7b7f6de321",
  "sync_type": "vision_data",
  "status": "pending",
  "is_full_sync": false,
  "triggered_at": "2025-11-24T13:15:00Z",
  "message": "Vision data sync (incremental) started successfully"
}
```

**Error Responses:**
- `409 Conflict`: Sync already in progress
```json
{
  "detail": "Vision data sync already in progress (sync_id: 0c563781-7366-465d-931d-874b98af6277)"
}
```

**Notes:**
- This endpoint queues an asynchronous Celery task and returns immediately
- Use the returned `sync_id` to poll for status updates via `/sync/status/{sync_id}`

<div style="page-break-after: always;"></div>

#### Trigger Full Sync

Triggers full synchronization of both employee reports and vision data.

**Endpoint:** `POST /sync/trigger/full`

**Response (202 Accepted):**
```json
{
  "sync_type": "full",
  "employee_reports_sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
  "vision_data_sync_id": "0c563781-7366-465d-931d-874b98af6277",
  "task_id": "full-sync-task-id",
  "status": "pending",
  "triggered_at": "2025-11-24T13:13:19Z",
  "message": "Full sync (both employee reports and vision data) started successfully"
}
```

**Error Responses:**
- `409 Conflict`: One or more sync types already in progress
```json
{
  "detail": "Sync already in progress for: employee_reports, vision_data"
}
```

**Notes:**
- This runs both sync types sequentially in a single Celery task
- Both syncs will be in FULL mode (all records, not incremental)
- Two separate `sync_id` values are returned - one for each sync type
- Use either `sync_id` to monitor progress via `/sync/status/{sync_id}`

<div style="page-break-after: always;"></div>

### Status & Monitoring

#### Get Sync Status

Retrieves the current status and metrics of a specific sync job.

**Endpoint:** `GET /sync/status/{sync_id}`

**Path Parameters:**
- `sync_id` (UUID): Sync job identifier

**Response:**
```json
{
  "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
  "sync_type": "employee_reports",
  "status": "completed",
  "is_full_sync": false,
  "started_at": "2025-11-24T13:13:19Z",
  "completed_at": "2025-11-24T13:13:24Z",
  "duration_seconds": 5.7,
  "progress": {
    "records_queried": 4,
    "records_synced": 4,
    "records_created": 3,
    "records_updated": 1,
    "records_skipped": 0,
    "error_count": 0,
    "percent_complete": 100.0
  },
  "metrics": {
    "employees_created": 0,
    "employees_updated": 4,
    "reports_created": 3,
    "reports_updated": 1
  },
  "last_sync_timestamp": "2025-11-17T10:53:11Z",
  "error_message": null
}
```

**Error Responses:**
- `404 Not Found`: Sync job not found
```json
{
  "detail": "Sync job c155260e-9177-4b53-bc14-e9f4d0e14cd2 not found"
}
```

**Notes:**
- Use this endpoint to poll for progress while a sync is running
- The `progress.percent_complete` field indicates sync progress (0-100)
- The `metrics` field contains type-specific metrics:
  - For `employee_reports`: `employees_created`, `employees_updated`, `reports_created`, `reports_updated`
  - For `vision_data`: `vision_records_created`, `vision_records_updated`
- Possible status values: `pending`, `running`, `completed`, `failed`, `partial`

<div style="page-break-after: always;"></div>

#### Get Last Successful Sync

Retrieves information about the last successful sync for a specific type.

**Endpoint:** `GET /sync/last-successful/{sync_type}`

**Path Parameters:**
- `sync_type` (string): Sync type - must be `employee_reports` or `vision_data`

**Response (with previous sync):**
```json
{
  "sync_type": "employee_reports",
  "last_successful_sync_id": "9a41f725-d963-4ea0-8d3c-9d0189d50a4d",
  "last_sync_timestamp": "2025-11-17T10:53:11Z",
  "records_synced": 234,
  "completed_at": "2025-11-24T12:23:59Z"
}
```

**Response (no previous sync):**
```json
{
  "sync_type": "employee_reports",
  "last_successful_sync_id": null,
  "last_sync_timestamp": null,
  "records_synced": null,
  "completed_at": null
}
```

**Error Responses:**
- `400 Bad Request`: Invalid sync type
```json
{
  "detail": "Invalid sync_type. Must be 'employee_reports' or 'vision_data'"
}
```

**Notes:**
- The `last_sync_timestamp` is used by incremental syncs to determine which records to fetch
- Returns null values if no successful sync has been performed for the given type

<div style="page-break-after: always;"></div>

### History & Reporting

#### List Sync History

Lists sync history with optional filtering, sorting, and pagination.

**Endpoint:** `GET /sync/history`

**Query Parameters:**
- `sync_type` (string, optional): Filter by sync type (`employee_reports` or `vision_data`)
- `status` (string, optional): Filter by status (`pending`, `running`, `completed`, `failed`, `partial`)
- `start_date` (datetime, optional): Filter syncs after this date
- `end_date` (datetime, optional): Filter syncs before this date
- `is_full_sync` (boolean, optional): Filter by sync mode
- `page` (integer, default: 1): Page number (minimum: 1)
- `page_size` (integer, default: 20): Items per page (1-100)
- `sort_by` (string, default: "started_at"): Sort field
- `sort_order` (string, default: "desc"): Sort order (`asc` or `desc`)

**Response:**
```json
{
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8,
  "items": [
    {
      "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
      "sync_type": "employee_reports",
      "status": "completed",
      "is_full_sync": false,
      "started_at": "2025-11-24T13:13:19Z",
      "completed_at": "2025-11-24T13:13:24Z",
      "duration_seconds": 5.7,
      "records_synced": 4,
      "error_count": 0,
      "last_sync_timestamp": "2025-11-17T10:53:11Z"
    },
    {
      "sync_id": "0c563781-7366-465d-931d-874b98af6277",
      "sync_type": "vision_data",
      "status": "partial",
      "is_full_sync": true,
      "started_at": "2025-11-23T10:00:00Z",
      "completed_at": "2025-11-23T10:05:30Z",
      "duration_seconds": 330.5,
      "records_synced": 95,
      "error_count": 5,
      "last_sync_timestamp": "2025-11-23T10:05:00Z"
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Invalid sync_type or status value

**Notes:**
- Use this endpoint to view past sync operations and their results
- Results are paginated - use `page` and `page_size` to navigate

<div style="page-break-after: always;"></div>

#### Get Sync Errors

Retrieves detailed errors for a specific sync job.

**Endpoint:** `GET /sync/{sync_id}/errors`

**Path Parameters:**
- `sync_id` (UUID): Sync job identifier

**Query Parameters:**
- `page` (integer, default: 1): Page number (minimum: 1)
- `page_size` (integer, default: 100): Errors per page (1-1000)

**Response:**
```json
{
  "sync_id": "c155260e-9177-4b53-bc14-e9f4d0e14cd2",
  "total_errors": 45,
  "page": 1,
  "page_size": 100,
  "errors": [
    {
      "row_number": 523,
      "field_name": "Employee_ID",
      "error_message": "Employee ID 9999 does not exist in database",
      "error_category": "validation",
      "row_data": {
        "Employee_ID": 9999,
        "Name": "John Doe",
        "From": "2025-01-01"
      }
    },
    {
      "row_number": 847,
      "field_name": "From_Date",
      "error_message": "Invalid date format: 15-April-2025",
      "error_category": "validation",
      "row_data": {
        "Employee_ID": 42,
        "From_Date": "15-April-2025"
      }
    }
  ]
}
```

**Error Responses:**
- `404 Not Found`: Sync job not found
```json
{
  "detail": "Sync job c155260e-9177-4b53-bc14-e9f4d0e14cd2 not found"
}
```

**Notes:**
- Only returns data if the sync job encountered errors
- Useful for debugging failed or partial syncs
- The `row_data` field contains the original SQL Server row that caused the error
- The `error_category` field indicates the type of error (e.g., "validation", "transformation")

<div style="page-break-after: always;"></div>

### Configuration

#### Get Sync Configuration

Retrieves the current sync service configuration.

**Endpoint:** `GET /sync/config`

**Response:**
```json
{
  "sql_server": {
    "host": "localhost\\SQLEXPRESS",
    "database": "EmployeeTestDB",
    "connection_status": "connected"
  },
  "allowed_tables": [
    "EmployeeReports",
    "VisionEmployeeData"
  ],
  "allowed_timestamp_columns": [
    "LastModifiedDate",
    "ModifiedDate",
    "UpdatedAt"
  ],
  "sync_settings": {
    "max_batch_size": 10000,
    "error_threshold_percent": 10.0,
    "default_chunk_size": 1000
  },
  "sync_schedule": {
    "incremental_sync": {
      "enabled": true,
      "schedule": "Monday 2:00 AM",
      "next_run": null
    },
    "full_sync": {
      "enabled": false,
      "schedule": "Manual trigger only"
    }
  },
  "sync_enabled": true
}
```

**Notes:**
- Returns read-only configuration information
- The `connection_status` field shows current SQL Server connectivity
- `allowed_tables` shows which SQL Server tables can be synced
- `allowed_timestamp_columns` shows which columns can be used for incremental sync detection
- `error_threshold_percent` indicates the maximum error percentage before sync aborts

<div style="page-break-after: always;"></div>

#### Test SQL Server Connection

Tests SQL Server connectivity without triggering a sync.

**Endpoint:** `GET /sync/test-connection`

**Response (successful connection):**
```json
{
  "status": "connected",
  "server": "localhost\\SQLEXPRESS",
  "database": "EmployeeTestDB",
  "available_tables": [
    "EmployeeReports",
    "VisionEmployeeData"
  ],
  "connection_time_ms": 45,
  "message": "Successfully connected to SQL Server"
}
```

**Response (failed connection):**
```json
{
  "status": "disconnected",
  "server": "localhost\\SQLEXPRESS",
  "database": "EmployeeTestDB",
  "available_tables": [],
  "connection_time_ms": 5000,
  "message": "Failed to connect to SQL Server"
}
```

**Response (error):**
```json
{
  "status": "error",
  "server": "unknown",
  "database": "unknown",
  "available_tables": [],
  "connection_time_ms": 0,
  "message": "Error: No suitable ODBC driver found for SQL Server"
}
```

**Notes:**
- Useful for diagnosing connection issues before attempting a sync
- The `connection_time_ms` field shows how long the connection attempt took
- Does not modify any data - purely a diagnostic endpoint

<div style="page-break-after: always;"></div>

## Schema Definitions

For detailed schema definitions, please refer to the following schema files:

- `employee_schema.py` - Employee-related schemas
- `reports_schema.py` - Report-related schemas
- `analysis_schema.py` - Analysis-related schemas (includes report, monthly, and quarterly analyses)
- `visualization_schema.py` - Visualization-related schemas (trend and heatmap data)
- `task_schema.py` - Background task-related schemas
- `csv_import_schema.py` - CSV import-related schemas
- `sync_schema.py` - SQL Server sync-related schemas

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `202 Accepted` - Request accepted for asynchronous processing
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., sync already in progress)
- `422 Unprocessable Entity` - Request validation error
- `500 Internal Server Error` - Server-side error

Error responses follow this format:

```json
{
  "detail": "Error message explaining what went wrong"
}
```

## Pagination

Endpoints that return collections of items support pagination using `limit` and `offset` or `page` and `page_size` query parameters, where applicable.

---



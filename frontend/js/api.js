/**
 * API client for the Employee Evaluation System backend.
 * 
 * This module provides functions for interacting with the backend APIs,
 * including CSV import operations.
 */

// Base URL for API endpoints. Defaults to the local API; a deployment can set
// window.API_BASE_URL in a script loaded before this one to point elsewhere.
const API_BASE_URL = window.API_BASE_URL || 'http://127.0.0.1:8000';

// Generic error handler for fetch operations
function handleErrors(response) {
    if (!response.ok) {
        return response.json().then(err => {
            throw new Error(err.detail || 'API Error: ' + response.statusText);
        });
    }
    return response.json();
}

// Generic fetch function with error handling
async function fetchApi(endpoint, options = {}) {
    try {
        console.log(`API Request: ${endpoint}`, options);
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        const result = await handleErrors(response);
        console.log(`API Response from ${endpoint}:`, result);
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Employee-related API functions
const employeeApi = {
    // Get all employees
    getAllEmployees: async () => {
        return await fetchApi('/employees/');
    },
    
    // Create a new employee
    createEmployee: async (employeeData) => {
        return await fetchApi('/employees/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(employeeData)
        });
    }
};

// Report-related API functions
const reportApi = {
    // Get reports for an employee
    getEmployeeReports: async (employeeId) => {
        return await fetchApi(`/reports/${employeeId}`);
    },
    
    // Create a new report
    createReport: async (reportData) => {
        return await fetchApi('/reports/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reportData)
        });
    },
    
    // Submit a structured report form
    submitReportForm: async (reportFormData) => {
        return await fetchApi('/reports/form', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reportFormData)
        });
    }
};

// Task-related API functions with improved error handling
const taskApi = {
    // Get the status of a task
    getTaskStatus: async (taskId) => {
        try {
            return await fetchApi(`/tasks/${taskId}`);
        } catch (error) {
            console.error(`Error fetching status for task ${taskId}:`, error);
            throw error;
        }
    },
    
    // Get the result of a completed task
    getTaskResult: async (taskId) => {
        try {
            return await fetchApi(`/tasks/${taskId}/result`);
        } catch (error) {
            // Handle 422 errors specifically (task not complete)
            if (error.message && error.message.includes('not yet complete')) {
                throw new Error('Task still processing. Please try again shortly.');
            }
            console.error(`Error fetching result for task ${taskId}:`, error);
            throw error;
        }
    }
};

// Analysis-related API functions
const analysisApi = {
    // Analyze a specific report - now returns a task instead of analysis
    analyzeReport: async (reportId) => {
        return await fetchApi(`/analyses/analyze/${reportId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    },
    
    // Get analysis results for a specific report
    getAnalysisResults: async (reportId) => {
        console.log(`Fetching analysis for report ID: ${reportId}`);
        try {
            const response = await fetchApi(`/analyses/results/${reportId}`);
            console.log('API Response:', response);
            return response;
        } catch (error) {
            console.error('Error in getAnalysisResults:', error);
            throw error;
        }
    },
    
    // Get all analyses for an employee
    getEmployeeAnalyses: async (employeeId) => {
        return await fetchApi(`/analyses/employee/${employeeId}`);
    },
    
    // Get detailed analysis by ID
    getAnalysisDetails: async (analysisId) => {
        return await fetchApi(`/analyses/${analysisId}`);
    },
    
    // Monthly analysis functions
    analyzeMonthlyReports: async (employeeId, year, month) => {
        return await fetchApi(`/analyses/monthly/analyze?employee_id=${employeeId}&year=${year}&month=${month}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    },
    
    getMonthlyAnalysisResults: async (employeeId, year, month) => {
        console.log(`Fetching monthly analysis for employee ID: ${employeeId}, ${year}-${month}`);
        try {
            const response = await fetchApi(`/analyses/monthly/employee/${employeeId}/${year}/${month}`);
            console.log('Monthly API Response:', response);
            return response;
        } catch (error) {
            console.error('Error in getMonthlyAnalysisResults:', error);
            throw error;
        }
    },
    
    // Get monthly analyses for an employee
    getEmployeeMonthlyAnalyses: async (employeeId) => {
        return await fetchApi(`/analyses/monthly/employee/${employeeId}`);
    },
    
    // Get detailed monthly analysis by ID
    getMonthlyAnalysisDetails: async (analysisId) => {
        return await fetchApi(`/analyses/monthly/${analysisId}`);
    },
    
    // Quarterly analysis functions
    analyzeQuarterlyReports: async (employeeId, year, quarter) => {
        return await fetchApi(`/analyses/quarterly/analyze?employee_id=${employeeId}&year=${year}&quarter=${quarter}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
    },
    
    getQuarterlyAnalysisResults: async (employeeId, year, quarter) => {
        console.log(`Fetching quarterly analysis for employee ID: ${employeeId}, ${year}-Q${quarter}`);
        try {
            const response = await fetchApi(`/analyses/quarterly/employee/${employeeId}/${year}/${quarter}`);
            console.log('Quarterly API Response:', response);
            return response;
        } catch (error) {
            console.error('Error in getQuarterlyAnalysisResults:', error);
            throw error;
        }
    },
    
    // Get detailed quarterly analysis by ID
    getQuarterlyAnalysisDetails: async (analysisId) => {
        return await fetchApi(`/analyses/quarterly/${analysisId}`);
    }
};

// Visualization-related API functions
const visualizationApi = {
    // Get sentiment trends data
    getSentimentTrends: async (employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/sentiment-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },
    
    // Get impact score trends data
    getImpactTrends: async (employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/impact-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },

    // Get risk level trends data
    getRiskTrends: async (employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/risk-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },
    
    // Get credibility rating trends data
    getCredibilityTrends: async (employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/credibility-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },
    
    // Get consistency score trends data
    getConsistencyTrends: async (employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/consistency-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },
    
    // Get performance rating trends data
    getPerformanceTrends: async (employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/performance-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },
    
    // Get multi-criteria trends data
    getMultiCriteriaTrends: async (criteria = ["sentiment"], employeeId = null, department = null, startDate = null, endDate = null, interval = "month") => {
        // Validate criteria input
        if (!Array.isArray(criteria) || criteria.length === 0) {
            throw new Error('Criteria must be a non-empty array');
        }
        
        // Build query parameters
        const params = new URLSearchParams();
        
        // Add each criterion as a separate query parameter with the same name
        criteria.forEach(criterion => {
            params.append('criteria', criterion);
        });
        
        // Add other parameters
        if (employeeId) params.append('employee_id', employeeId);
        if (department) params.append('department', department);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/multi-criteria-trends${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },

    // Get sentiment heatmap data
    getSentimentHeatmap: async (dimension = "department", startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (dimension) params.append('dimension', dimension);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/sentiment-heatmap${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    },
    
    // Get impact score heatmap data
    getImpactHeatmap: async (dimension = "department", startDate = null, endDate = null, interval = "month") => {
        // Build query parameters
        const params = new URLSearchParams();
        if (dimension) params.append('dimension', dimension);
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (interval) params.append('interval', interval);
        
        // Construct the query string
        const queryString = params.toString();
        const endpoint = `/visualizations/impact-heatmap${queryString ? '?' + queryString : ''}`;
        
        return await fetchApi(endpoint);
    }
};

// Import-related API functions
const importApi = {
    // Upload a CSV file for import
    uploadCSV: async (formData) => {
        return await fetch(`${API_BASE_URL}/imports/upload`, {
            method: 'POST',
            body: formData,
        }).then(handleErrors);
    },
    
    // Get status of an import job
    getJobStatus: async (jobId) => {
        return await fetchApi(`/imports/${jobId}`);
    },
    
    // Get paginated errors for an import job
    getJobErrors: async (jobId, page = 1, pageSize = 100) => {
        return await fetchApi(`/imports/${jobId}/errors?page=${page}&page_size=${pageSize}`);
    },
    
    // Get list of all import jobs
    getJobsList: async (status = null, csv_type = null, limit = 50, offset = 0) => {
        let url = `/imports/?limit=${limit}&offset=${offset}`;
        if (status) {
            url += `&status=${status}`;
        }
        if (csv_type) {
            url += `&csv_type=${csv_type}`;
        }
        return await fetchApi(url);
    }
};

// TaskManager - utilities for polling and managing async tasks
const TaskManager = {
    // Poll a task with exponential backoff until completion
    pollTaskUntilComplete: async function(taskId, options = {}) {
        const defaults = {
            initialDelay: 1000,             // Start with 1 second delay
            maxDelay: 10000,                // Max 10 seconds between polls
            maxAttempts: 30,                // Maximum polling attempts
            onStatusUpdate: null,           // Callback for status updates
            backoffFactor: 1.5              // Exponential backoff multiplier
        };
        
        const settings = {...defaults, ...options};
        let currentDelay = settings.initialDelay;
        
        for (let attempt = 0; attempt < settings.maxAttempts; attempt++) {
            try {
                // Get current status
                const status = await taskApi.getTaskStatus(taskId);
                
                // Call the status update callback if provided
                if (settings.onStatusUpdate && typeof settings.onStatusUpdate === 'function') {
                    settings.onStatusUpdate(status);
                }
                
                // If task is complete, get and return the result
                if (status.is_complete) {
                    const resultData = await taskApi.getTaskResult(taskId);
                    return resultData;
                }
                
                // Wait before trying again (with exponential backoff)
                await this.delay(currentDelay);
                
                // Increase delay for next attempt (with maximum cap)
                currentDelay = Math.min(currentDelay * settings.backoffFactor, settings.maxDelay);
            } catch (error) {
                console.error(`Error polling task ${taskId}:`, error);
                
                // For network errors, keep trying
                if (error.name === 'TypeError' && error.message.includes('network')) {
                    await this.delay(currentDelay);
                    continue;
                }
                
                throw error;
            }
        }
        
        throw new Error(`Task ${taskId} did not complete within the expected time.`);
    },
    
    // Simple delay promise utility
    delay: function(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
};

// ============================================================================
// SYNC API ENDPOINTS
// ============================================================================

const syncApi = {
    /**
     * Trigger a sync operation
     */
    triggerSync: async (syncType, isFullSync = false) => {
        const response = await fetch(`${API_BASE_URL}/sync/trigger/${syncType}?is_full_sync=${isFullSync}`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to trigger sync');
        }
        return response.json();
    },
    
    /**
     * Trigger full sync (both types)
     */
    triggerFullSync: async () => {
        const response = await fetch(`${API_BASE_URL}/sync/trigger/full`, {
            method: 'POST'
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to trigger full sync');
        }
        return response.json();
    },
    
    /**
     * Get sync status
     */
    getSyncStatus: async (syncId) => {
        const response = await fetch(`${API_BASE_URL}/sync/status/${syncId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get sync status');
        }
        return response.json();
    },
    
    /**
     * Get last successful sync
     */
    getLastSuccessfulSync: async (syncType) => {
        const response = await fetch(`${API_BASE_URL}/sync/last-successful/${syncType}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get last sync');
        }
        return response.json();
    },
    
    /**
     * List sync history with filters
     */
    listSyncHistory: async (filters = {}) => {
        const params = new URLSearchParams();
        if (filters.sync_type) params.append('sync_type', filters.sync_type);
        if (filters.status) params.append('status', filters.status);
        if (filters.sort_order) params.append('sort_order', filters.sort_order);
        if (filters.page) params.append('page', filters.page);
        if (filters.page_size) params.append('page_size', filters.page_size);
        
        const response = await fetch(`${API_BASE_URL}/sync/history?${params}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load sync history');
        }
        return response.json();
    },
    
    /**
     * Get sync errors
     */
    getSyncErrors: async (syncId, page = 1, pageSize = 10) => {
        const response = await fetch(`${API_BASE_URL}/sync/${syncId}/errors?page=${page}&page_size=${pageSize}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load sync errors');
        }
        return response.json();
    },
    
    /**
     * Get sync configuration
     */
    getSyncConfiguration: async () => {
        const response = await fetch(`${API_BASE_URL}/sync/config`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load sync configuration');
        }
        return response.json();
    },
    
    /**
     * Test SQL Server connection
     */
    testConnection: async () => {
        const response = await fetch(`${API_BASE_URL}/sync/test-connection`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to test connection');
        }
        return response.json();
    }
};

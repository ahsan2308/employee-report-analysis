// Base URL for API endpoints - ensure this always points to localhost
const API_BASE_URL = 'http://127.0.0.1:8000';

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
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        return await handleErrors(response);
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
        return await fetchApi(`/analyses/results/${reportId}`);
    },
    
    // Get all analyses for an employee
    getEmployeeAnalyses: async (employeeId) => {
        return await fetchApi(`/analyses/employee/${employeeId}`);
    },
    
    // Get detailed analysis by ID
    getAnalysisDetails: async (analysisId) => {
        return await fetchApi(`/analyses/${analysisId}`);
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
    }
};

// NEW: Import-related API functions
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
    getJobsList: async (status = null, limit = 50, offset = 0) => {
        let url = `/imports/?limit=${limit}&offset=${offset}`;
        if (status) {
            url += `&status=${status}`;
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

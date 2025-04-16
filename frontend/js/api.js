// Base URL for API endpoints
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

// Analysis-related API functions
const analysisApi = {
    // Analyze a specific report
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
    }
};

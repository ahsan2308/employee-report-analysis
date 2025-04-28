document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const departmentSelect = document.getElementById('departmentSelect');
    const employeeSelect = document.getElementById('employeeSelect');
    const intervalSelect = document.getElementById('intervalSelect');
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const noDataMessage = document.getElementById('noDataMessage');
    const statusMessage = document.getElementById('statusMessage');
    const sentimentTrendChart = document.getElementById('sentimentTrendChart');

    // Chart instance
    let chart = null;

    // Current filters state
    const filters = {
        department: '',
        employee_id: '',
        start_date: '',
        end_date: '',
        interval: 'month'
    };

    // Initialize the page
    init();

    // Initialize the page and load data
    async function init() {
        // Set default interval
        intervalSelect.value = filters.interval;
        
        // Set default dates (last 6 months)
        const today = new Date();
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(today.getMonth() - 6);
        
        startDateInput.value = formatDateForInput(sixMonthsAgo);
        endDateInput.value = formatDateForInput(today);
        
        filters.start_date = startDateInput.value;
        filters.end_date = endDateInput.value;
        
        // Add event listeners
        setupEventListeners();
        
        // Show loading indicator
        showLoading(true);
        showMessage('Loading initial data...', 'loading');
        
        try {
            // Load departments and employees
            await Promise.all([
                loadDepartments(),
                loadEmployees()
            ]);
            
            // Load initial data and render chart
            await fetchAndRenderChart();
            
            showMessage('Visualization loaded successfully', 'success');
        } catch (error) {
            console.error('Error initializing visualizations:', error);
            showError('Failed to initialize visualizations: ' + error.message);
        } finally {
            showLoading(false);
        }
    }

    // Set up event listeners
    function setupEventListeners() {
        // Department change - update employee dropdown
        departmentSelect.addEventListener('change', function() {
            filters.department = this.value;
            loadEmployees(this.value); // Reload employees filtered by department
        });
        
        // Employee change
        employeeSelect.addEventListener('change', function() {
            filters.employee_id = this.value;
        });
        
        // Interval change
        intervalSelect.addEventListener('change', function() {
            filters.interval = this.value;
        });
        
        // Date changes
        startDateInput.addEventListener('change', function() {
            filters.start_date = this.value;
        });
        
        endDateInput.addEventListener('change', function() {
            filters.end_date = this.value;
        });
        
        // Apply filters button
        applyFiltersBtn.addEventListener('click', function() {
            fetchAndRenderChart();
        });
        
        // Reset filters button
        resetFiltersBtn.addEventListener('click', resetFilters);
    }

    // Load departments for filter dropdown
    async function loadDepartments() {
        try {
            // Fetch all employees to extract unique departments
            const employees = await employeeApi.getAllEmployees();
            
            // Extract unique departments
            const departments = [...new Set(employees.map(emp => emp.wing))];
            
            // Clear existing options (keep the "All Departments" option)
            departmentSelect.innerHTML = '<option value="">All Departments</option>';
            
            // Add department options
            departments.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept;
                option.textContent = dept;
                departmentSelect.appendChild(option);
            });
            
        } catch (error) {
            console.error('Error loading departments:', error);
            showError('Could not load departments. Please try again later.');
            throw error; // Re-throw to be caught by caller
        }
    }

    // Load employees for filter dropdown
    async function loadEmployees(department = '') {
        try {
            // Fetch all employees
            const employees = await employeeApi.getAllEmployees();
            
            // Filter by department if specified
            const filteredEmployees = department 
                ? employees.filter(emp => emp.wing === department)
                : employees;
            
            // Clear existing options (keep the "All Employees" option)
            employeeSelect.innerHTML = '<option value="">All Employees</option>';
            
            // Add employee options
            filteredEmployees.forEach(emp => {
                const option = document.createElement('option');
                option.value = emp.id;
                option.textContent = `${emp.name} (${emp.position})`;
                employeeSelect.appendChild(option);
            });
            
        } catch (error) {
            console.error('Error loading employees:', error);
            showError('Could not load employees. Please try again later.');
            throw error; // Re-throw to be caught by caller
        }
    }

    // Fetch data and render chart
    async function fetchAndRenderChart() {
        try {
            showLoading(true);
            noDataMessage.style.display = 'none';
            showMessage('Fetching visualization data...', 'loading');
            
            // Validate date range
            if (filters.start_date && filters.end_date) {
                const start = new Date(filters.start_date);
                const end = new Date(filters.end_date);
                
                if (start > end) {
                    throw new Error('Start date cannot be after end date');
                }
            }
            
            // Fetch data from API
            const sentimentData = await visualizationApi.getSentimentTrends(
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            // Check if we have data
            if (!sentimentData || !sentimentData.labels || sentimentData.labels.length === 0) {
                noDataMessage.style.display = 'block';
                // Destroy existing chart if it exists
                if (chart) {
                    chart.destroy();
                    chart = null;
                }
                showMessage('No data available for the selected filters', 'info');
                showLoading(false);
                return;
            }
            
            // Render chart
            renderChart(sentimentData);
            showMessage('Chart updated successfully', 'success');
            
        } catch (error) {
            console.error('Error fetching sentiment data:', error);
            showError('Error loading visualization data: ' + error.message);
        } finally {
            showLoading(false);
        }
    }

    // Render sentiment trend chart
    function renderChart(data) {
        // Destroy existing chart if it exists
        if (chart) {
            chart.destroy();
        }
        
        // Define color palette based on sentiment
        const colorGradient = {
            backgroundColor: 'rgba(52, 152, 219, 0.2)',
            borderColor: 'rgba(52, 152, 219, 1)',
            pointBackgroundColor: data.datasets[0].data.map(value => {
                if (value > 0.7) return 'rgba(39, 174, 96, 1)';  // Positive
                if (value < 0.3) return 'rgba(231, 76, 60, 1)';  // Negative
                return 'rgba(243, 156, 18, 1)';                  // Neutral
            }),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(52, 152, 219, 1)'
        };
        
        // Apply colors to the dataset
        const datasets = data.datasets.map(dataset => ({
            ...dataset,
            ...colorGradient,
            tension: 0.2,  // Add slight curve to line
            pointRadius: 5,
            pointHoverRadius: 7
        }));
        
        // Get the trend metadata for annotations
        const metadata = data.datasets[0].metadata || { avg: 0.5 };  // Default if missing
        
        // Configure the chart
        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                let sentiment = 'Neutral';
                                
                                if (value > 0.7) sentiment = 'Positive';
                                else if (value < 0.3) sentiment = 'Negative';
                                
                                return `${label}: ${value.toFixed(2)} (${sentiment})`;
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            // Average line
                            avgLine: {
                                type: 'line',
                                yMin: metadata.avg,
                                yMax: metadata.avg,
                                borderColor: 'rgba(128, 128, 128, 0.5)',
                                borderWidth: 2,
                                borderDash: [6, 6],
                                label: {
                                    display: true,
                                    content: `Average: ${parseFloat(metadata.avg).toFixed(2)}`,
                                    position: 'end',
                                    backgroundColor: 'rgba(128, 128, 128, 0.7)'
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time Period'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 1,
                        title: {
                            display: true,
                            text: 'Sentiment Score'
                        },
                        ticks: {
                            callback: function(value) {
                                if (value === 0) return 'Negative';
                                if (value === 0.5) return 'Neutral';
                                if (value === 1) return 'Positive';
                                return value.toFixed(1);
                            }
                        }
                    }
                }
            }
        };
        
        // Create the chart
        chart = new Chart(sentimentTrendChart, config);
    }

    // Reset all filters to default
    function resetFilters() {
        // Reset department and employee selections
        departmentSelect.value = '';
        filters.department = '';
        
        // Reload all employees
        loadEmployees();
        
        // Reset interval
        intervalSelect.value = 'month';
        filters.interval = 'month';
        
        // Reset dates to last 6 months
        const today = new Date();
        const sixMonthsAgo = new Date();
        sixMonthsAgo.setMonth(today.getMonth() - 6);
        
        startDateInput.value = formatDateForInput(sixMonthsAgo);
        endDateInput.value = formatDateForInput(today);
        
        filters.start_date = startDateInput.value;
        filters.end_date = endDateInput.value;
        
        // Fetch data with reset filters
        fetchAndRenderChart();
        
        showMessage('Filters have been reset', 'info');
    }

    // Helper for loading indicator
    function showLoading(isLoading) {
        loadingIndicator.style.display = isLoading ? 'block' : 'none';
        // Disable/enable filter buttons during loading
        applyFiltersBtn.disabled = isLoading;
        resetFiltersBtn.disabled = isLoading;
    }

    // Helper for displaying error messages
    function showError(message) {
        statusMessage.innerHTML = `<div class="error-message">${message}</div>`;
    }

    // Helper for displaying success/info messages
    function showMessage(message, type = 'info') {
        statusMessage.innerHTML = `<div class="${type}-message">${message}</div>`;
        
        // Auto-hide after 4 seconds for success/info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                // Only clear if it's still the same message
                if (statusMessage.innerHTML === `<div class="${type}-message">${message}</div>`) {
                    statusMessage.innerHTML = '';
                }
            }, 4000);
        }
    }

    // Format date for input elements
    function formatDateForInput(date) {
        return date.toISOString().split('T')[0];
    }
});

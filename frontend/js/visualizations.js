document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const visualizationTypeSelect = document.getElementById('visualizationTypeSelect');
    const visualizationModeSelect = document.getElementById('visualizationModeSelect');
    const dimensionSelect = document.getElementById('dimensionSelect');
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
    
    // Multi-criteria related elements - update references
    const multiCriteriaContainer = document.getElementById('multiCriteriaVisualizationContainer');
    const multiCriteriaTrendChart = document.getElementById('multiCriteriaTrendChart');
    // Replace checkbox references with pill buttons
    const criteriaPills = document.querySelectorAll('.criteria-pill');
    const criteriaSelectionCount = document.querySelector('.criteria-selection-count');
    const selectAllCriteriaBtn = document.getElementById('selectAllCriteria');
    const clearAllCriteriaBtn = document.getElementById('clearAllCriteria');
    const multiCriteriaOnlyElements = document.querySelectorAll('.multi-criteria-only');
    
    // Trend Visualization containers
    const sentimentVisualizationContainer = document.getElementById('sentimentVisualizationContainer');
    const impactVisualizationContainer = document.getElementById('impactVisualizationContainer');
    
    // Heatmap Visualization containers
    const sentimentHeatmapContainer = document.getElementById('sentimentHeatmapContainer');
    const impactHeatmapContainer = document.getElementById('impactHeatmapContainer');
    
    // Chart canvases
    const sentimentTrendChart = document.getElementById('sentimentTrendChart');
    const impactTrendChart = document.getElementById('impactTrendChart');
    const sentimentHeatmapChart = document.getElementById('sentimentHeatmapChart');
    const impactHeatmapChart = document.getElementById('impactHeatmapChart');

    // Add references to the new DOM elements
    const riskVisualizationContainer = document.getElementById('riskVisualizationContainer');
    const credibilityVisualizationContainer = document.getElementById('credibilityVisualizationContainer');
    const consistencyVisualizationContainer = document.getElementById('consistencyVisualizationContainer');
    const performanceVisualizationContainer = document.getElementById('performanceVisualizationContainer');

    const riskTrendChart = document.getElementById('riskTrendChart');
    const credibilityTrendChart = document.getElementById('credibilityTrendChart');
    const consistencyTrendChart = document.getElementById('consistencyTrendChart');
    const performanceTrendChart = document.getElementById('performanceTrendChart');

    // Chart instances
    let sentimentChart = null;
    let impactChart = null;
    let sentimentHeatmap = null;
    let impactHeatmap = null;
    let multiCriteriaChart = null;
    let riskChart = null;
    let credibilityChart = null;
    let consistencyChart = null;
    let performanceChart = null;

    // Current filters state
    const filters = {
        visualizationType: 'sentiment', // sentiment or impact
        visualizationMode: 'trend',     // trend, heatmap, or multi-criteria
        dimension: 'department',        // department or employee (for heatmaps)
        department: '',
        employee_id: '',
        start_date: '',
        end_date: '',
        interval: 'month',
        criteria: ['sentiment']         // Default criteria for multi-criteria view
    };

    // Initialize the page
    init();

    // Initialize the page and load data
    async function init() {
        // Set default values
        intervalSelect.value = filters.interval;
        visualizationTypeSelect.value = filters.visualizationType;
        visualizationModeSelect.value = filters.visualizationMode;
        dimensionSelect.value = filters.dimension;
        
        // Enhance select dropdowns with consistent styling
        enhanceDropdowns();
        
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
        
        // Update UI based on initial mode
        updateVisibilityBasedOnMode();
        
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
            await fetchAndRenderCharts();
            
            showMessage('Visualization loaded successfully', 'success');
        } catch (error) {
            console.error('Error initializing visualizations:', error);
            showError('Failed to initialize visualizations: ' + error.message);
        } finally {
            showLoading(false);
        }
    }

    // Apply consistent styling to all dropdowns
    function enhanceDropdowns() {
        const dropdowns = [
            visualizationTypeSelect,
            visualizationModeSelect,
            dimensionSelect,
            departmentSelect,
            intervalSelect
        ];
        
        // Apply consistent styling to dropdowns
        dropdowns.forEach(dropdown => {
            if (!dropdown.hasAttribute('data-consistent-style')) {
                SearchableDropdown.enhanceSimple(dropdown);
                dropdown.setAttribute('data-consistent-style', 'true');
            }
        });
        
        // Make employee dropdown searchable
        if (!employeeSelect.hasAttribute('data-searchable')) {
            SearchableDropdown.enhance(employeeSelect);
            employeeSelect.setAttribute('data-searchable', 'true');
        }
    }

    // Set up event listeners
    function setupEventListeners() {
        // Visualization type change
        visualizationTypeSelect.addEventListener('change', function() {
            filters.visualizationType = this.value;
            updateVisibilityBasedOnType();
            fetchAndRenderCharts();
        });
        
        // Visualization mode change
        visualizationModeSelect.addEventListener('change', function() {
            filters.visualizationMode = this.value;
            updateVisibilityBasedOnMode();
            fetchAndRenderCharts();
        });
        
        // Remove the old criteria checkbox event listeners and add new pill button listeners
        criteriaPills.forEach(pill => {
            pill.addEventListener('click', function() {
                // Toggle active state
                this.classList.toggle('active');
                
                // Update selected criteria
                updateSelectedCriteria();
                
                // If multi-criteria mode is active, update the chart immediately
                if (filters.visualizationMode === 'multi-criteria') {
                    fetchAndRenderCharts();
                }
            });
        });
        
        // Add event listeners for Select All and Clear All buttons
        if (selectAllCriteriaBtn) {
            selectAllCriteriaBtn.addEventListener('click', function() {
                criteriaPills.forEach(pill => {
                    pill.classList.add('active');
                });
                updateSelectedCriteria();
                if (filters.visualizationMode === 'multi-criteria') {
                    fetchAndRenderCharts();
                }
            });
        }
        
        if (clearAllCriteriaBtn) {
            clearAllCriteriaBtn.addEventListener('click', function() {
                criteriaPills.forEach(pill => {
                    pill.classList.remove('active');
                });
                updateSelectedCriteria(); // This will ensure at least one is selected
                if (filters.visualizationMode === 'multi-criteria') {
                    fetchAndRenderCharts();
                }
            });
        }
        
        // Dimension change (for heatmaps)
        dimensionSelect.addEventListener('change', function() {
            filters.dimension = this.value;
            fetchAndRenderCharts();
        });
        
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
            fetchAndRenderCharts();
        });
        
        // Reset filters button
        resetFiltersBtn.addEventListener('click', resetFilters);
    }

    // Update the selected criteria based on pill button states
    function updateSelectedCriteria() {
        const selectedCriteria = [];
        
        criteriaPills.forEach(pill => {
            if (pill.classList.contains('active')) {
                selectedCriteria.push(pill.dataset.criteria);
            }
        });
        
        // Ensure at least one criterion is selected
        if (selectedCriteria.length === 0) {
            // Default to sentiment if nothing selected
            const sentimentPill = document.querySelector('.criteria-pill[data-criteria="sentiment"]');
            if (sentimentPill) {
                sentimentPill.classList.add('active');
                selectedCriteria.push('sentiment');
            }
            showMessage('At least one criterion must be selected', 'warning');
        }
        
        // Update the selection count
        if (criteriaSelectionCount) {
            criteriaSelectionCount.textContent = `${selectedCriteria.length} of ${criteriaPills.length} selected`;
        }
        
        filters.criteria = selectedCriteria;
        console.log('Selected criteria:', filters.criteria);
    }

    // Update chart visibility based on selected visualization type
    function updateVisibilityBasedOnType() {
        if (filters.visualizationMode === 'trend') {
            // Hide all trend visualizations first
            sentimentVisualizationContainer.style.display = 'none';
            impactVisualizationContainer.style.display = 'none';
            riskVisualizationContainer.style.display = 'none';
            credibilityVisualizationContainer.style.display = 'none';
            consistencyVisualizationContainer.style.display = 'none';
            performanceVisualizationContainer.style.display = 'none';
            
            // Show the appropriate trend chart based on selected type
            switch(filters.visualizationType) {
                case 'sentiment':
                    sentimentVisualizationContainer.style.display = 'block';
                    break;
                case 'impact':
                    impactVisualizationContainer.style.display = 'block';
                    break;
                case 'risk':
                    riskVisualizationContainer.style.display = 'block';
                    break;
                case 'credibility':
                    credibilityVisualizationContainer.style.display = 'block';
                    break;
                case 'consistency':
                    consistencyVisualizationContainer.style.display = 'block';
                    break;
                case 'performance':
                    performanceVisualizationContainer.style.display = 'block';
                    break;
            }
            
            // Hide all heatmap visualizations
            sentimentHeatmapContainer.style.display = 'none';
            impactHeatmapContainer.style.display = 'none';
            multiCriteriaContainer.style.display = 'none';
        } else if (filters.visualizationMode === 'multi-criteria') {
            // For multi-criteria, always show the multi-criteria container
            multiCriteriaContainer.style.display = 'block';
            
            // Hide all other visualizations
            sentimentVisualizationContainer.style.display = 'none';
            impactVisualizationContainer.style.display = 'none';
            sentimentHeatmapContainer.style.display = 'none';
            impactHeatmapContainer.style.display = 'none';
        } else {
            // Hide all trend visualizations
            sentimentVisualizationContainer.style.display = 'none';
            impactVisualizationContainer.style.display = 'none';
            
            // Hide multi-criteria container
            multiCriteriaContainer.style.display = 'none';
            
            // Show the appropriate heatmap
            if (filters.visualizationType === 'sentiment') {
                sentimentHeatmapContainer.style.display = 'block';
                impactHeatmapContainer.style.display = 'none';
            } else {
                sentimentHeatmapContainer.style.display = 'none';
                impactHeatmapContainer.style.display = 'block';
            }
        }
        
        noDataMessage.style.display = 'none';
    }
    
    // Update UI based on visualization mode
    function updateVisibilityBasedOnMode() {
        // Show/hide filters based on mode
        const trendOnlyElements = document.querySelectorAll('.trend-only');
        const heatmapOnlyElements = document.querySelectorAll('.heatmap-only');
        
        if (filters.visualizationMode === 'trend') {
            trendOnlyElements.forEach(el => el.style.display = 'block');
            heatmapOnlyElements.forEach(el => el.style.display = 'none');
            multiCriteriaOnlyElements.forEach(el => el.style.display = 'none');
            
            // Reset dropdown to show all options
            resetVisualizationTypeOptions();
            
            // Enable the visualization type dropdown
            visualizationTypeSelect.disabled = false;
            visualizationTypeSelect.parentElement.classList.remove('disabled-filter');
            
        } else if (filters.visualizationMode === 'heatmap') {
            trendOnlyElements.forEach(el => el.style.display = 'none');
            heatmapOnlyElements.forEach(el => el.style.display = 'block');
            multiCriteriaOnlyElements.forEach(el => el.style.display = 'none');
            
            // Limit dropdown to only sentiment and impact options
            limitVisualizationTypeOptions(['sentiment', 'impact']);
            
            // Enable the visualization type dropdown
            visualizationTypeSelect.disabled = false;
            visualizationTypeSelect.parentElement.classList.remove('disabled-filter');
            
        } else if (filters.visualizationMode === 'multi-criteria') {
            trendOnlyElements.forEach(el => el.style.display = 'block');
            heatmapOnlyElements.forEach(el => el.style.display = 'none');
            multiCriteriaOnlyElements.forEach(el => el.style.display = 'block');
            
            // Reset dropdown to show all options (but it will be disabled)
            resetVisualizationTypeOptions();
            
            // Disable the visualization type dropdown since it doesn't apply in multi-criteria mode
            visualizationTypeSelect.disabled = true;
            visualizationTypeSelect.parentElement.classList.add('disabled-filter');
            
            // Ensure criteria are initialized
            updateSelectedCriteria();
        }
        
        // Update chart visibility based on type
        updateVisibilityBasedOnType();
    }

    // Function to reset visualization type dropdown to show all options
    function resetVisualizationTypeOptions() {
        // Store current selection
        const currentValue = visualizationTypeSelect.value;
        
        // Clear the select element
        visualizationTypeSelect.innerHTML = '';
        
        // Add all options back
        const options = [
            { value: 'sentiment', text: 'Sentiment Scores' },
            { value: 'impact', text: 'Achievement Impact Scores' },
            { value: 'risk', text: 'Risk Level' },
            { value: 'credibility', text: 'Credibility Rating' },
            { value: 'consistency', text: 'Consistency Score' },
            { value: 'performance', text: 'Performance Rating' }
        ];
        
        options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.text;
            visualizationTypeSelect.appendChild(option);
        });
        
        // Restore the selection if possible
        visualizationTypeSelect.value = currentValue;
        
        // Re-apply SearchableDropdown enhancement
        SearchableDropdown.enhanceSimple(visualizationTypeSelect);
    }

    // Function to limit visualization type dropdown to specific options
    function limitVisualizationTypeOptions(allowedValues) {
        // Store current selection
        const currentValue = visualizationTypeSelect.value;
        
        // Clear the select element
        visualizationTypeSelect.innerHTML = '';
        
        // Add only allowed options
        const options = [
            { value: 'sentiment', text: 'Sentiment Scores' },
            { value: 'impact', text: 'Achievement Impact Scores' }
        ];
        
        options.forEach(opt => {
            if (allowedValues.includes(opt.value)) {
                const option = document.createElement('option');
                option.value = opt.value;
                option.textContent = opt.text;
                visualizationTypeSelect.appendChild(option);
            }
        });
        
        // Set a valid selection
        if (allowedValues.includes(currentValue)) {
            visualizationTypeSelect.value = currentValue;
        } else {
            visualizationTypeSelect.value = allowedValues[0];
            filters.visualizationType = allowedValues[0];
        }
        
        // Re-apply SearchableDropdown enhancement
        SearchableDropdown.enhanceSimple(visualizationTypeSelect);
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
            
            // Apply consistent styling after loading options
            if (!departmentSelect.hasAttribute('data-consistent-style')) {
                SearchableDropdown.enhanceSimple(departmentSelect);
                departmentSelect.setAttribute('data-consistent-style', 'true');
            }
            
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
            
            // Update dropdown styling
            if (!employeeSelect.hasAttribute('data-searchable')) {
                SearchableDropdown.enhance(employeeSelect);
            } else {
                SearchableDropdown.resetSearch(employeeSelect);
            }
            
        } catch (error) {
            console.error('Error loading employees:', error);
            showError('Could not load employees. Please try again later.');
            throw error;
        }
    }

    // Fetch data and render charts
    async function fetchAndRenderCharts() {
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
            
            // Update visibility based on selected type and mode
            updateVisibilityBasedOnMode();
            
            // Fetch and render based on mode and type
            if (filters.visualizationMode === 'trend') {
                switch(filters.visualizationType) {
                    case 'sentiment':
                        await fetchAndRenderSentimentTrend();
                        break;
                    case 'impact':
                        await fetchAndRenderImpactTrend();
                        break;
                    case 'risk':
                        await fetchAndRenderRiskTrend();
                        break;
                    case 'credibility':
                        await fetchAndRenderCredibilityTrend();
                        break;
                    case 'consistency':
                        await fetchAndRenderConsistencyTrend();
                        break;
                    case 'performance':
                        await fetchAndRenderPerformanceTrend();
                        break;
                }
            } else if (filters.visualizationMode === 'multi-criteria') {
                // Fetch and render multi-criteria visualization
                await fetchAndRenderMultiCriteriaTrend();
            } else {
                // Heatmap mode
                if (filters.visualizationType === 'sentiment') {
                    await fetchAndRenderSentimentHeatmap();
                } else {
                    await fetchAndRenderImpactHeatmap();
                }
            }
            
            showMessage('Chart updated successfully', 'success');
            
        } catch (error) {
            console.error('Error fetching visualization data:', error);
            showError('Error loading visualization data: ' + error.message);
        } finally {
            showLoading(false);
        }
    }

    // Fetch and render sentiment trend chart
    async function fetchAndRenderSentimentTrend() {
        try {
            // Get the container and no-data message for sentiment
            const noDataElement = sentimentVisualizationContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
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
                noDataElement.style.display = 'block';
                // Destroy existing chart if it exists
                if (sentimentChart) {
                    sentimentChart.destroy();
                    sentimentChart = null;
                }
                return;
            }
            
            // Render chart
            renderSentimentChart(sentimentData);
        } catch (error) {
            console.error('Error fetching sentiment data:', error);
            throw error; // Let the main function handle the error
        }
    }
    
    // Fetch and render impact trend chart
    async function fetchAndRenderImpactTrend() {
        try {
            // Get the container and no-data message for impact
            const noDataElement = impactVisualizationContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            // Fetch data from API
            const impactData = await visualizationApi.getImpactTrends(
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            // Check if we have data
            if (!impactData || !impactData.labels || impactData.labels.length === 0) {
                noDataElement.style.display = 'block';
                // Destroy existing chart if it exists
                if (impactChart) {
                    impactChart.destroy();
                    impactChart = null;
                }
                return;
            }
            
            // Render chart
            renderImpactChart(impactData);
        } catch (error) {
            console.error('Error fetching impact data:', error);
            throw error; // Let the main function handle the error
        }
    }
    
    // Fetch and render risk trend chart
    async function fetchAndRenderRiskTrend() {
        try {
            const noDataElement = riskVisualizationContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            const riskData = await visualizationApi.getRiskTrends(
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            if (!riskData || !riskData.labels || riskData.labels.length === 0) {
                noDataElement.style.display = 'block';
                if (riskChart) {
                    riskChart.destroy();
                    riskChart = null;
                }
                return;
            }
            
            renderRiskChart(riskData);
        } catch (error) {
            console.error('Error fetching risk data:', error);
            throw error;
        }
    }
    
    // Fetch and render credibility trend chart
    async function fetchAndRenderCredibilityTrend() {
        try {
            const noDataElement = credibilityVisualizationContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            const credibilityData = await visualizationApi.getCredibilityTrends(
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            if (!credibilityData || !credibilityData.labels || credibilityData.labels.length === 0) {
                noDataElement.style.display = 'block';
                if (credibilityChart) {
                    credibilityChart.destroy();
                    credibilityChart = null;
                }
                return;
            }
            
            renderCredibilityChart(credibilityData);
        } catch (error) {
            console.error('Error fetching credibility data:', error);
            throw error;
        }
    }
    
    // Fetch and render consistency trend chart
    async function fetchAndRenderConsistencyTrend() {
        try {
            const noDataElement = consistencyVisualizationContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            const consistencyData = await visualizationApi.getConsistencyTrends(
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            if (!consistencyData || !consistencyData.labels || consistencyData.labels.length === 0) {
                noDataElement.style.display = 'block';
                if (consistencyChart) {
                    consistencyChart.destroy();
                    consistencyChart = null;
                }
                return;
            }
            
            renderConsistencyChart(consistencyData);
        } catch (error) {
            console.error('Error fetching consistency data:', error);
            throw error;
        }
    }
    
    // Fetch and render performance trend chart
    async function fetchAndRenderPerformanceTrend() {
        try {
            const noDataElement = performanceVisualizationContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            const performanceData = await visualizationApi.getPerformanceTrends(
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            if (!performanceData || !performanceData.labels || performanceData.labels.length === 0) {
                noDataElement.style.display = 'block';
                if (performanceChart) {
                    performanceChart.destroy();
                    performanceChart = null;
                }
                return;
            }
            
            renderPerformanceChart(performanceData);
        } catch (error) {
            console.error('Error fetching performance data:', error);
            throw error;
        }
    }

    // Fetch and render sentiment heatmap
    async function fetchAndRenderSentimentHeatmap() {
        try {
            // Get the container and no-data message for sentiment heatmap
            const noDataElement = sentimentHeatmapContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            // Fetch data from API
            const heatmapData = await visualizationApi.getSentimentHeatmap(
                filters.dimension,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            // Check if we have data
            if (!heatmapData || !heatmapData.x_labels || heatmapData.x_labels.length === 0 || 
                !heatmapData.y_labels || heatmapData.y_labels.length === 0) {
                noDataElement.style.display = 'block';
                // Clear existing heatmap if it exists
                if (sentimentHeatmapChart) {
                    Plotly.purge(sentimentHeatmapChart);
                }
                return;
            }
            
            // Render heatmap
            renderSentimentHeatmap(heatmapData);
        } catch (error) {
            console.error('Error fetching sentiment heatmap data:', error);
            throw error;
        }
    }
    
    // Fetch and render impact heatmap
    async function fetchAndRenderImpactHeatmap() {
        try {
            // Get the container and no-data message for impact heatmap
            const noDataElement = impactHeatmapContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            // Fetch data from API
            const heatmapData = await visualizationApi.getImpactHeatmap(
                filters.dimension,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            // Check if we have data
            if (!heatmapData || !heatmapData.x_labels || heatmapData.x_labels.length === 0 || 
                !heatmapData.y_labels || heatmapData.y_labels.length === 0) {
                noDataElement.style.display = 'block';
                // Clear existing heatmap if it exists
                if (impactHeatmapChart) {
                    Plotly.purge(impactHeatmapChart);
                }
                return;
            }
            
            // Render heatmap
            renderImpactHeatmap(heatmapData);
        } catch (error) {
            console.error('Error fetching impact heatmap data:', error);
            throw error;
        }
    }

    // Render sentiment trend chart
    function renderSentimentChart(data) {
        // Destroy existing chart if it exists
        if (sentimentChart) {
            sentimentChart.destroy();
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
        sentimentChart = new Chart(sentimentTrendChart, config);
    }

    // Render impact score trend chart
    function renderImpactChart(data) {
        // Destroy existing chart if it exists
        if (impactChart) {
            impactChart.destroy();
        }
        
        // Define color palette for impact scores
        const colorGradient = {
            backgroundColor: 'rgba(142, 68, 173, 0.2)',
            borderColor: 'rgba(142, 68, 173, 1)',
            pointBackgroundColor: data.datasets[0].data.map(value => {
                // Assuming impact scores are typically on a scale of 1-10
                if (value > 7) return 'rgba(39, 174, 96, 1)';  // High impact
                if (value < 4) return 'rgba(231, 76, 60, 1)';  // Low impact
                return 'rgba(243, 156, 18, 1)';                // Medium impact
            }),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(142, 68, 173, 1)'
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
        const metadata = data.datasets[0].metadata || { avg: 5 };  // Default if missing
        
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
                                let impact = 'Medium';
                                
                                if (value > 7) impact = 'High';
                                else if (value < 4) impact = 'Low';
                                
                                return `${label}: ${value.toFixed(2)} (${impact} Impact)`;
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
                        suggestedMax: 10,  // Most impact scores are on a scale of 1-10
                        title: {
                            display: true,
                            text: 'Impact Score'
                        },
                        ticks: {
                            callback: function(value) {
                                // For impact scores, just show the number
                                return value.toFixed(0);
                            }
                                                        }

                        }
                    }
                }
            };
        
        // Create the chart
        impactChart = new Chart(impactTrendChart, config);
    }
    
    // Render risk trend chart
    function renderRiskChart(data) {
        // Destroy existing chart if it exists
        if (riskChart) {
            riskChart.destroy();
        }
        
        // Define color palette for risk scores
        const colorGradient = {
            backgroundColor: 'rgba(231, 76, 60, 0.2)',  // Light red
            borderColor: 'rgba(231, 76, 60, 1)',      // Red
            pointBackgroundColor: data.datasets[0].data.map(value => {
                // Assuming risk scores are typically on a scale of 1-10
                if (value > 7) return 'rgba(39, 174, 96, 1)';  // Low risk (green)
                if (value < 4) return 'rgba(231, 76, 60, 1)';  // High risk (red)
                return 'rgba(243, 156, 18, 1)';                // Medium risk (orange)
            }),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(231, 76, 60, 1)'
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
        const metadata = data.datasets[0].metadata || { avg: 5 };  // Default if missing
        
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
                                let risk = 'Medium';
                                
                                if (value > 7) risk = 'Low';
                                else if (value < 4) risk = 'High';
                                
                                return `${label}: ${value.toFixed(2)} (${risk} Risk)`;
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
                        suggestedMax: 10,  // Most risk scores are on a scale of 1-10
                        title: {
                            display: true,
                            text: 'Risk Score'
                        },
                        ticks: {
                            callback: function(value) {
                                // For risk scores, just show the number
                                return value.toFixed(0);
                            }
                        }
                    }
                }
            }
        };
        
        // Create the chart
        riskChart = new Chart(riskTrendChart, config);
    }
    
    // Render credibility trend chart
    function renderCredibilityChart(data) {
        // Destroy existing chart if it exists
        if (credibilityChart) {
            credibilityChart.destroy();
        }
        
        // Define color palette for credibility scores
        const colorGradient = {
            backgroundColor: 'rgba(52, 152, 219, 0.2)',  // Light blue
            borderColor: 'rgba(52, 152, 219, 1)',      // Blue
            pointBackgroundColor: data.datasets[0].data.map(value => {
                // Assuming credibility scores are typically on a scale of 0-1
                if (value > 0.7) return 'rgba(39, 174, 96, 1)';  // High credibility (green)
                if (value < 0.3) return 'rgba(231, 76, 60, 1)';  // Low credibility (red)
                return 'rgba(243, 156, 18, 1)';                // Medium credibility (orange)
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
                                let credibility = 'Medium';
                                
                                if (value > 0.7) credibility = 'High';
                                else if (value < 0.3) credibility = 'Low';
                                
                                return `${label}: ${value.toFixed(2)} (${credibility} Credibility)`;
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
                            text: 'Credibility Score'
                        },
                        ticks: {
                            callback: function(value) {
                                if (value === 0) return 'Low';
                                if (value === 0.5) return 'Medium';
                                if (value === 1) return 'High';
                                return value.toFixed(1);
                            }
                        }
                    }
                }
            }
        };
        
        // Create the chart
        credibilityChart = new Chart(credibilityTrendChart, config);
    }
    
    // Render consistency trend chart
    function renderConsistencyChart(data) {
        // Destroy existing chart if it exists
        if (consistencyChart) {
            consistencyChart.destroy();
        }
        
        // Define color palette for consistency scores
        const colorGradient = {
            backgroundColor: 'rgba(241, 196, 15, 0.2)',  // Light yellow
            borderColor: 'rgba(241, 196, 15, 1)',      // Yellow
            pointBackgroundColor: data.datasets[0].data.map(value => {
                // Assuming consistency scores are typically on a scale of 0-1
                if (value > 0.7) return 'rgba(39, 174, 96, 1)';  // High consistency (green)
                if (value < 0.3) return 'rgba(231, 76, 60, 1)';  // Low consistency (red)
                return 'rgba(243, 156, 18, 1)';                // Medium consistency (orange)
            }),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(241, 196, 15, 1)'
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
                                let consistency = 'Medium';
                                
                                if (value > 0.7) consistency = 'High';
                                else if (value < 0.3) consistency = 'Low';
                                
                                return `${label}: ${value.toFixed(2)} (${consistency} Consistency)`;
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
                            text: 'Consistency Score'
                        },
                        ticks: {
                            callback: function(value) {
                                if (value === 0) return 'Low';
                                if (value === 0.5) return 'Medium';
                                if (value === 1) return 'High';
                                return value.toFixed(1);
                            }
                        }
                    }
                }
            }
        };
        
        // Create the chart
        consistencyChart = new Chart(consistencyTrendChart, config);
    }
    
    // Render performance trend chart
    function renderPerformanceChart(data) {
        // Destroy existing chart if it exists
        if (performanceChart) {
            performanceChart.destroy();
        }
        
        // Define color palette for performance scores
        const colorGradient = {
            backgroundColor: 'rgba(46, 204, 113, 0.2)',  // Light green
            borderColor: 'rgba(46, 204, 113, 1)',      // Green
            pointBackgroundColor: data.datasets[0].data.map(value => {
                // Assuming performance scores are typically on a scale of 1-10
                if (value > 7) return 'rgba(39, 174, 96, 1)';  // High performance (green)
                if (value < 4) return 'rgba(231, 76, 60, 1)';  // Low performance (red)
                return 'rgba(243, 156, 18, 1)';                // Medium performance (orange)
            }),
            pointBorderColor: '#fff',
            pointHoverBackgroundColor: '#fff',
            pointHoverBorderColor: 'rgba(46, 204, 113, 1)'
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
        const metadata = data.datasets[0].metadata || { avg: 5 };  // Default if missing
        
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
                                let performance = 'Medium';
                                
                                if (value > 7) performance = 'High';
                                else if (value < 4) performance = 'Low';
                                
                                return `${label}: ${value.toFixed(2)} (${performance} Performance)`;
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
                        suggestedMax: 10,  // Most performance scores are on a scale of 1-10
                        title: {
                            display: true,
                            text: 'Performance Score'
                        },
                        ticks: {
                            callback: function(value) {
                                // For performance scores, just show the number
                                return value.toFixed(0);
                            }
                        }
                    }
                }
            }
        };
        
        // Create the chart
        performanceChart = new Chart(performanceTrendChart, config);
    }
    
    // Fetch and render multi-criteria trend chart
    async function fetchAndRenderMultiCriteriaTrend() {
        try {
            // Get the container and no-data message for multi-criteria
            const noDataElement = multiCriteriaContainer.querySelector('.no-data-message');
            noDataElement.style.display = 'none';
            
            // Ensure we have criteria selected
            if (!filters.criteria || filters.criteria.length === 0) {
                updateSelectedCriteria();
            }
            
            // Make sure impact is not included in multi-criteria view
            const filteredCriteria = filters.criteria.filter(criterion => criterion !== 'impact');
            
            // Ensure we still have at least one criterion after filtering
            if (filteredCriteria.length === 0) {
                // Default to sentiment if all criteria were removed
                filteredCriteria.push('sentiment');
                
                // Update the UI to show sentiment selected
                criteriaPills.forEach(pill => {
                    pill.classList.toggle('active', pill.dataset.criteria === 'sentiment');
                });
                
                // Update the selection count
                if (criteriaSelectionCount) {
                    criteriaSelectionCount.textContent = `1 of ${criteriaPills.length - 1} selected`;
                }
            }
            
            // Fetch data from API using filtered criteria
            const multiCriteriaData = await visualizationApi.getMultiCriteriaTrends(
                filteredCriteria,
                filters.employee_id,
                filters.department,
                filters.start_date,
                filters.end_date,
                filters.interval
            );
            
            // Check if we have data
            if (!multiCriteriaData || !multiCriteriaData.labels || multiCriteriaData.labels.length === 0 || 
                !multiCriteriaData.datasets || multiCriteriaData.datasets.length === 0) {
                noDataElement.style.display = 'block';
                // Destroy existing chart if it exists
                if (multiCriteriaChart) {
                    multiCriteriaChart.destroy();
                    multiCriteriaChart = null;
                }
                return;
            }
            
            // Render chart
            renderMultiCriteriaChart(multiCriteriaData);
        } catch (error) {
            console.error('Error fetching multi-criteria data:', error);
            throw error; // Let the main function handle the error
        }
    }
    
    // Render multi-criteria trend chart
    function renderMultiCriteriaChart(data) {
        // Destroy existing chart if it exists
        if (multiCriteriaChart) {
            multiCriteriaChart.destroy();
        }
        
        // Configure the chart
        const config = {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets.map(dataset => ({
                    ...dataset,
                    tension: 0.2,      // Add slight curve to line
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: false        // Don't fill area under the line for clarity
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',     // Show all values at the same x-index on hover
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,  // Use points instead of rectangles in legend
                            padding: 15           // Add padding between legend items
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                if (value === null || value === undefined) {
                                    return `${label}: No data`;
                                }
                                return `${label}: ${value.toFixed(2)}`;
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
                        max: 1,         // All criteria are normalized to 0-1 scale
                        title: {
                            display: true,
                            text: 'Score Value'
                        },
                        ticks: {
                            callback: function(value) {
                                if (value === 0) return 'Low (0.2)';
                                if (value === 0.5) return 'Medium (0.5)';
                                if (value === 1) return 'High (0.8)';
                                return value.toFixed(1);
                            }
                        }
                    }
                }
            }
        };
        
        // Create the chart
        multiCriteriaChart = new Chart(multiCriteriaTrendChart, config);
    }
    
    // Render sentiment heatmap using Plotly
    function renderSentimentHeatmap(data) {
        // Process data for Plotly format
        const plotlyData = processPlotlyHeatmapData(data, true); // true for sentiment
        
        // Calculate container width for responsive sizing
        const containerWidth = sentimentHeatmapChart.parentElement.offsetWidth;
        
        const layout = {
            title: `Sentiment Scores by ${filters.dimension === 'department' ? 'Department' : 'Employee'}`,
            xaxis: {
                title: 'Time Period',
                tickangle: 45,
                tickformat: '%b %Y', // Format to show month and year
                tickfont: {
                    size: 10
                },
                automargin: true
            },
            yaxis: {
                title: filters.dimension === 'department' ? 'Department' : 'Employee',
                automargin: true,
                tickfont: {
                    size: 11
                }
            },
            margin: {
                l: 180, // Increased left margin for y-axis labels
                r: 50,  // Right margin
                b: 120, // Increased bottom margin for x-axis labels
                t: 60   // Top margin for title
            },
            width: containerWidth - 40, // Dynamic width with padding
            height: Math.max(containerWidth * 0.6, 450), // Dynamic height based on width
            hovermode: 'closest',
            annotations: [{
                text: "Sentiment Scale: Red (Negative) to Green (Positive)",
                showarrow: false,
                xref: 'paper',
                yref: 'paper',
                x: 0,
                y: -0.2, // Moved down to avoid overlap
                font: {
                    size: 12
                }
            }]
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
        };

        // Clear existing chart if any
        Plotly.purge(sentimentHeatmapChart);
        
        // Create new chart
        Plotly.newPlot(sentimentHeatmapChart, [plotlyData], layout, config);
        
        // Store reference to the chart element (not the chart instance)
        sentimentHeatmap = sentimentHeatmapChart;

        // Add responsive behavior
        window.addEventListener('resize', function() {
            const newWidth = sentimentHeatmapChart.parentElement.offsetWidth - 40;
            Plotly.relayout(sentimentHeatmapChart, {
                width: newWidth,
                height: Math.max(newWidth * 0.6, 450)
            });
        });
    }
    
    // Render impact score heatmap using Plotly
    function renderImpactHeatmap(data) {
        // Process data for Plotly format
        const plotlyData = processPlotlyHeatmapData(data, false); // false for impact scores
        
        // Calculate container width for responsive sizing
        const containerWidth = impactHeatmapChart.parentElement.offsetWidth;
        
        const layout = {
            title: `Impact Scores by ${filters.dimension === 'department' ? 'Department' : 'Employee'}`,
            xaxis: {
                title: 'Time Period',
                tickangle: 45,
                tickformat: '%b %Y', // Format to show month and year
                tickfont: {
                    size: 10
                },
                automargin: true
            },
            yaxis: {
                title: filters.dimension === 'department' ? 'Department' : 'Employee',
                automargin: true,
                tickfont: {
                    size: 11
                }
            },
            margin: {
                l: 180, // Increased left margin for y-axis labels
                r: 50,  // Right margin
                b: 120, // Increased bottom margin for x-axis labels
                t: 60   // Top margin for title
            },
            width: containerWidth - 40, // Dynamic width with padding
            height: Math.max(containerWidth * 0.6, 450), // Dynamic height based on width
            hovermode: 'closest',
            annotations: [{
                text: "Impact Scale: Light (Low) to Dark (High)",
                showarrow: false,
                xref: 'paper',
                yref: 'paper',
                x: 0,
                y: -0.2, // Moved down to avoid overlap
                font: {
                    size: 12
                }
            }]
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
        };

        // Clear existing chart if any
        Plotly.purge(impactHeatmapChart);
        
        // Create new chart
        Plotly.newPlot(impactHeatmapChart, [plotlyData], layout, config);
        
        // Store reference to the chart element (not the chart instance)
        impactHeatmap = impactHeatmapChart;

        // Add responsive behavior
        window.addEventListener('resize', function() {
            const newWidth = impactHeatmapChart.parentElement.offsetWidth - 40;
            Plotly.relayout(impactHeatmapChart, {
                width: newWidth,
                height: Math.max(newWidth * 0.6, 450)
            });
        });
    }
    
    // Process heatmap data for Plotly format
    function processPlotlyHeatmapData(data, isSentiment = true) {
        // Extract data from the API response
        const xLabels = data.x_labels;
        const yLabels = data.y_labels;
        const cells = data.cells;
        const metadata = data.metadata;
        
        // Create a 2D array filled with nulls for z values
        const zValues = Array(yLabels.length).fill().map(() => Array(xLabels.length).fill(null));
        
        // Fill in the values from the cells
        cells.forEach(cell => {
            zValues[cell.y][cell.x] = cell.value;
        });
        
        // Set up color scale based on data type with more intermediate stops for subtle transitions
        let colorscale;
        if (isSentiment) {
            // Enhanced sentiment color scale with more intermediate stops (Red -> Yellow -> Green)
            colorscale = [
                [0, 'rgb(231, 76, 60)'],       // Negative (red)
                [0.15, 'rgb(237, 116, 58)'],   // Added intermediate
                [0.3, 'rgb(243, 156, 18)'],    // Neutral-low (orange)
                [0.4, 'rgb(242, 176, 16)'],    // Added intermediate
                [0.5, 'rgb(241, 196, 15)'],    // Neutral (yellow)
                [0.6, 'rgb(202, 200, 42)'],    // Added intermediate
                [0.7, 'rgb(142, 204, 57)'],    // Neutral-high (light green)
                [0.85, 'rgb(88, 189, 76)'],    // Added intermediate
                [1, 'rgb(39, 174, 96)']        // Positive (green)
            ];
        } else {
            // Enhanced impact color scale with more intermediate stops (purple gradient)
            colorscale = [
                [0, 'rgb(158, 118, 180)'],     // Low impact (light purple)
                [0.15, 'rgb(145, 97, 169)'],   // Added intermediate
                [0.3, 'rgb(123, 58, 150)'],    // Medium-low
                [0.5, 'rgb(109, 47, 141)'],    // Added intermediate
                [0.7, 'rgb(95, 37, 132)'],     // Medium-high
                [0.85, 'rgb(81, 30, 115)'],    // Added intermediate
                [1, 'rgb(68, 24, 98)']         // High impact (dark purple)
            ];
        }
        
        // Configure hover text format with better formatting
        let hovertemplate;
        if (isSentiment) {
            hovertemplate = 
                '<b>%{y}</b><br>' +
                'Time: %{x}<br>' +
                'Sentiment: %{z:.2f}<br>' +
                '<extra></extra>';
        } else {
            hovertemplate = 
                '<b>%{y}</b><br>' +
                'Time: %{x}<br>' +
                'Impact: %{z:.2f}<br>' +
                '<extra></extra>';
        }
        
        // Return Plotly heatmap trace
        return {
            type: 'heatmap',
            z: zValues,
            x: xLabels,
            y: yLabels,
            colorscale: colorscale,
            showscale: true,
            colorbar: {
                title: isSentiment ? 'Sentiment Score' : 'Impact Score',
                titleside: 'right',
                titlefont: {
                    size: 14
                },
                len: 0.9 // Adjusted length of colorbar
            },
            hovertemplate: hovertemplate,
            zmin: isSentiment ? 0 : metadata.min,
            zmax: isSentiment ? 1 : metadata.max
        };
    }

    // Reset all filters to default
    function resetFilters() {
        // Reset mode to trend
        visualizationModeSelect.value = 'trend';
        filters.visualizationMode = 'trend';
        
        // Reset visualization type to sentiment
        visualizationTypeSelect.value = 'sentiment';
        filters.visualizationType = 'sentiment';
        
        // Reset criteria pills to default (only sentiment checked)
        criteriaPills.forEach(pill => {
            if (pill.dataset.criteria === 'sentiment') {
                pill.classList.add('active');
            } else {
                pill.classList.remove('active');
            }
        });
        filters.criteria = ['sentiment'];
        updateSelectedCriteria();
        
        // Reset department and employee filters
        departmentSelect.value = '';
        filters.department = '';
        
        // Reset dimension to department
        dimensionSelect.value = 'department';
        filters.dimension = 'department';
        
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
        
        // Update UI based on visualization type
        updateVisibilityBasedOnMode();
        
        // Fetch data with reset filters
        fetchAndRenderCharts();
        
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

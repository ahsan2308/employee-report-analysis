document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const employeeSelect = document.getElementById('employeeSelect');
    const reportSelect = document.getElementById('reportSelect');
    const monthSelect = document.getElementById('monthSelect');
    const yearSelect = document.getElementById('yearSelect');
    const analyzeButton = document.getElementById('analyzeButton');
    const analysisResults = document.getElementById('analysisResults');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const statusMessage = document.getElementById('statusMessage');
    
    // Toggle elements
    const weeklyToggle = document.getElementById('weeklyToggle');
    const monthlyToggle = document.getElementById('monthlyToggle');
    const reportSelectGroup = document.getElementById('reportSelectGroup');
    const monthSelectGroup = document.getElementById('monthSelectGroup');
    const yearSelectGroup = document.getElementById('yearSelectGroup');
    
    // Analysis mode
    let currentMode = 'weekly';
    
    // Get URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const reportIdFromUrl = urlParams.get('report_id');
    const autoAnalyze = urlParams.get('auto_analyze');
    const modeFromUrl = urlParams.get('mode');
    
    // Month/year URL parameters
    const employeeIdFromUrl = urlParams.get('employee_id');
    const yearFromUrl = urlParams.get('year');
    const monthFromUrl = urlParams.get('month');
    
    // Track the current analysis task
    let currentTask = null;
    
    // Initialize mode from URL if present
    if (modeFromUrl && (modeFromUrl === 'weekly' || modeFromUrl === 'monthly')) {
        currentMode = modeFromUrl;
        if (modeFromUrl === 'monthly') {
            monthlyToggle.checked = true;
        } else {
            weeklyToggle.checked = true;
        }
    }
    
    // Initialize year dropdown with last 5 years
    populateYearDropdown();
    
    // Set default month and year to current month/year
    const currentDate = new Date();
    monthSelect.value = currentDate.getMonth() + 1; // JavaScript months are 0-based
    yearSelect.value = currentDate.getFullYear();
    
    // Apply current mode
    applyAnalysisMode(currentMode);
    
    // Event listeners
    loadEmployees();
    employeeSelect.addEventListener('change', handleEmployeeChange);
    reportSelect.addEventListener('change', toggleAnalyzeButton);
    monthSelect.addEventListener('change', toggleAnalyzeButton);
    yearSelect.addEventListener('change', toggleAnalyzeButton);
    analyzeButton.addEventListener('click', handleAnalyzeClick);
    
    // Mode toggle event listeners
    weeklyToggle.addEventListener('change', () => {
        if (weeklyToggle.checked) {
            currentMode = 'weekly';
            applyAnalysisMode(currentMode);
            updateUrlParameter('mode', 'weekly');
            
            // Clear results when switching modes
            if (analysisResults.style.display !== 'none') {
                analysisResults.style.display = 'none';
                analysisResults.innerHTML = '';
            }
        }
    });
    
    monthlyToggle.addEventListener('change', () => {
        if (monthlyToggle.checked) {
            currentMode = 'monthly';
            applyAnalysisMode(currentMode);
            updateUrlParameter('mode', 'monthly');
            
            // Clear results when switching modes
            if (analysisResults.style.display !== 'none') {
                analysisResults.style.display = 'none';
                analysisResults.innerHTML = '';
            }
        }
    });
    
    // If we have a report ID and auto_analyze is true, show loading immediately
    if ((reportIdFromUrl && autoAnalyze === 'true') || 
        (employeeIdFromUrl && yearFromUrl && monthFromUrl && autoAnalyze === 'true')) {
        showLoading(true);
        showMessage('Initializing analysis...', 'loading');
    }
    
    // Function to populate the year dropdown
    function populateYearDropdown() {
        const currentYear = new Date().getFullYear();
        yearSelect.innerHTML = '';
        
        // Add last 5 years
        for (let i = 0; i < 5; i++) {
            const year = currentYear - i;
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearSelect.appendChild(option);
        }
    }
    
    // Function to apply the current analysis mode
    function applyAnalysisMode(mode) {
        if (mode === 'weekly') {
            reportSelectGroup.style.display = 'block';
            monthSelectGroup.style.display = 'none';
            yearSelectGroup.style.display = 'none';
            analyzeButton.innerHTML = '<i class="fas fa-cogs"></i> Analyze Report';
        } else if (mode === 'monthly') {
            reportSelectGroup.style.display = 'none';
            monthSelectGroup.style.display = 'block';
            yearSelectGroup.style.display = 'block';
            analyzeButton.innerHTML = '<i class="fas fa-cogs"></i> Analyze Monthly Performance';
        }
        
        toggleAnalyzeButton();
    }
    
    // Handle employee change based on mode
    function handleEmployeeChange() {
        if (currentMode === 'weekly') {
            loadReportsForEmployee();
        } else {
            // For monthly mode, just check if employee is selected
            toggleAnalyzeButton();
        }
    }
    
    // Handle analyze button click based on mode
    function handleAnalyzeClick() {
        if (currentMode === 'weekly') {
            analyzeSelectedReport();
        } else {
            analyzeMonthlyPerformance();
        }
    }
    
    // Toggle analyze button based on current mode
    function toggleAnalyzeButton() {
        if (currentMode === 'weekly') {
            analyzeButton.disabled = !reportSelect.value;
        } else {
            analyzeButton.disabled = !employeeSelect.value;
        }
    }
    
    // Load employees from API
    async function loadEmployees() {
        try {
            const employees = await employeeApi.getAllEmployees();
            
            employeeSelect.innerHTML = '<option value="">Select Employee</option>';
            employees.forEach(employee => {
                const option = document.createElement('option');
                option.value = employee.id;
                option.textContent = `${employee.name} (${employee.position})`;
                employeeSelect.appendChild(option);
            });
            
            // Make the employee dropdown searchable
            if (!employeeSelect.hasAttribute('data-searchable')) {
                SearchableDropdown.enhance(employeeSelect);
            } else {
                SearchableDropdown.resetSearch(employeeSelect);
            }
            
            // Apply consistent styling to report dropdown (without search)
            if (!reportSelect.hasAttribute('data-consistent-style')) {
                SearchableDropdown.enhanceSimple(reportSelect);
                reportSelect.setAttribute('data-consistent-style', 'true');
            }
            
            // Apply consistent styling to month dropdown
            if (!monthSelect.hasAttribute('data-consistent-style')) {
                SearchableDropdown.enhanceSimple(monthSelect);
                monthSelect.setAttribute('data-consistent-style', 'true');
            }
            
            // Apply consistent styling to year dropdown
            if (!yearSelect.hasAttribute('data-consistent-style')) {
                SearchableDropdown.enhanceSimple(yearSelect);
                yearSelect.setAttribute('data-consistent-style', 'true');
            }
            
            // If we have parameters from URL, initialize accordingly
            if (modeFromUrl === 'monthly' && employeeIdFromUrl) {
                employeeSelect.value = employeeIdFromUrl;
                
                if (yearFromUrl) {
                    yearSelect.value = yearFromUrl;
                }
                
                if (monthFromUrl) {
                    monthSelect.value = monthFromUrl;
                }
                
                // Auto-analyze if requested
                if (autoAnalyze === 'true') {
                    analyzeMonthlyPerformance();
                }
            } else if (reportIdFromUrl) {
                console.log("Found report ID in URL:", reportIdFromUrl);
                await findAndSelectEmployeeForReport(reportIdFromUrl);
            }
        } catch (error) {
            console.error('Error loading employees:', error);
            showMessage('Could not load employees. Please try again later.', 'error');
        }
    }
    
    // Find and select the employee for a given report ID
    async function findAndSelectEmployeeForReport(reportId) {
        try {
            // First, try to get the analysis results which will include employee info
            const analysisData = await analysisApi.getAnalysisResults(reportId);
            console.log("Analysis data from API:", analysisData);
            
            if (analysisData && analysisData.employee_name) {
                console.log("Found employee for report:", analysisData.employee_name);
                
                // Find employee by name
                const employees = await employeeApi.getAllEmployees();
                const employee = employees.find(e => e.name === analysisData.employee_name);
                
                if (employee) {
                    // Select the employee
                    employeeSelect.value = employee.id;
                    
                    // Load reports for this employee
                    await loadReportsForEmployee();
                    
                    // Select the specific report
                    if (reportSelect.options.length > 0) {
                        for (let i = 0; i < reportSelect.options.length; i++) {
                            if (reportSelect.options[i].value === reportId) {
                                reportSelect.selectedIndex = i;
                                toggleAnalyzeButton();
                                break;
                            }
                        }
                    }
                    
                    // Auto-analyze if requested
                    if (autoAnalyze === 'true') {
                        analyzeSelectedReport();
                    }
                }
            } else {
                // Plan B: Try to fetch the report directly to get the employee ID
                try {
                    const response = await fetch(`${API_BASE_URL}/reports/single/${reportId}`);
                    const reportData = await response.json();
                    
                    if (reportData && reportData.employee_id) {
                        employeeSelect.value = reportData.employee_id;
                        await loadReportsForEmployee();
                        
                        // Select the specific report
                        for (let i = 0; i < reportSelect.options.length; i++) {
                            if (reportSelect.options[i].value === reportId) {
                                reportSelect.selectedIndex = i;
                                toggleAnalyzeButton();
                                
                                // Auto-analyze if requested
                                if (autoAnalyze === 'true') {
                                    analyzeSelectedReport();
                                }
                                break;
                            }
                        }
                    }
                } catch (reportError) {
                    console.error("Error fetching report details:", reportError);
                }
            }
        } catch (error) {
            console.error("Error finding employee for report:", error);
            // If we still have the report ID, offer a direct analyze option
            if (reportIdFromUrl && autoAnalyze === 'true') {
                analyzeReportDirectly(reportIdFromUrl);
            }
        }
    }
    
    // Directly analyze a report by ID without UI selection
    async function analyzeReportDirectly(reportId) {
        try {
            showLoading(true);
            
            // Start the analysis and get a task
            const taskData = await analysisApi.analyzeReport(reportId);
            currentTask = taskData.task_id;
            
            // If already complete (existing analysis), get results immediately
            if (taskData.is_complete) {
                const resultData = await taskApi.getTaskResult(taskData.task_id);
                displayAnalysisResults(resultData.result);
                showMessage('Analysis completed successfully', 'success');
            } else {
                // Show polling message
                showMessage('Analysis in progress, please wait...', 'loading');
                
                // Poll for completion with the TaskManager
                const resultData = await TaskManager.pollTaskUntilComplete(taskData.task_id, {
                    onStatusUpdate: updateLoadingStatus
                });
                
                if (resultData.error_message) {
                    throw new Error(resultData.error_message);
                }
                
                displayAnalysisResults(resultData.result);
                showMessage('Analysis completed successfully', 'success');
            }
        } catch (error) {
            console.error('Error in direct analysis:', error);
            showMessage('Analysis failed: ' + error.message, 'error');
        } finally {
            currentTask = null;
            showLoading(false);
        }
    }
    
    // Update loading message based on task status
    function updateLoadingStatus(status) {
        if (status.status === 'pending') {
            showMessage('Analysis queued, waiting to start...', 'loading');
        } else if (status.status === 'running') {
            showMessage('Processing analysis...', 'loading');
        } else if (status.status === 'failed') {
            showMessage('Analysis failed. Please try again.', 'error');
        }
    }
    
    // Load reports for selected employee
    async function loadReportsForEmployee() {
        const employeeId = employeeSelect.value;
        reportSelect.innerHTML = '<option value="">Select Report</option>';
        analyzeButton.disabled = true;
        
        if (!employeeId) return;
        
        try {
            showMessage('Loading reports...', 'loading');
            const response = await reportApi.getEmployeeReports(employeeId);
            let reports = response.reports || [];
            
            if (reports.length === 0) {
                reportSelect.innerHTML = '<option value="">No reports available</option>';
                showMessage('No reports found for this employee.', 'info');
                // Ensure the styling is maintained even with no options
                if (!reportSelect.hasAttribute('data-consistent-style')) {
                    SearchableDropdown.enhanceSimple(reportSelect);
                    reportSelect.setAttribute('data-consistent-style', 'true');
                }
                return;
            }
            
            // Sort reports by date (most recent first)
            reports.sort((a, b) => {
                const dateA = new Date(a.report_date || 0);
                const dateB = new Date(b.report_date || 0);
                return dateB - dateA; // Descending order (newest first)
            });
            
            reports.forEach(report => {
                const option = document.createElement('option');
                option.value = report.report_id;
                
                // Format the date in a more readable way
                const reportDate = new Date(report.report_date || new Date());
                const formattedDate = reportDate.toLocaleDateString(undefined, { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                });
                
                // Create a descriptive label with date
                option.textContent = `Report from ${formattedDate}`;
                reportSelect.appendChild(option);
            });
            
            // If we have a report ID from URL, select it
            if (reportIdFromUrl) {
                for (let i = 0; i < reportSelect.options.length; i++) {
                    if (reportSelect.options[i].value === reportIdFromUrl) {
                        reportSelect.selectedIndex = i;
                        toggleAnalyzeButton();
                        break;
                    }
                }
            }
            
            // Ensure consistent styling is maintained
            if (!reportSelect.hasAttribute('data-consistent-style')) {
                SearchableDropdown.enhanceSimple(reportSelect);
                reportSelect.setAttribute('data-consistent-style', 'true');
            }
            
            showMessage(`Loaded ${reports.length} reports.`, 'success');
        } catch (error) {
            console.error('Error loading reports:', error);
            showMessage('Could not load reports. Please try again later.', 'error');
        }
    }
    
    // Analyze selected report - modified to use the TaskManager
    async function analyzeSelectedReport() {
        const reportId = reportSelect.value || reportIdFromUrl;
        
        if (!reportId) {
            showMessage('Please select a report to analyze', 'error');
            return;
        }
        
        // Clear previous results
        if (analysisResults.style.display !== 'none') {
            analysisResults.style.display = 'none';
            analysisResults.innerHTML = '';
        }
        
        showLoading(true);
        
        try {
            // Start the analysis and get a task
            const taskData = await analysisApi.analyzeReport(reportId);
            currentTask = taskData.task_id;
            console.log('Task created:', taskData);
            
            // If already complete (existing analysis), get results immediately
            const resultData = taskData.is_complete
                ? await taskApi.getTaskResult(taskData.task_id)
                : await TaskManager.pollTaskUntilComplete(taskData.task_id, {
                    onStatusUpdate: updateLoadingStatus
                });
            
            if (resultData.error_message) {
                throw new Error(resultData.error_message);
            }
            
            displayAnalysisResults(resultData.result);
            showMessage('Analysis completed successfully', 'success');
            
            // Update URL without reload to include the report_id and mode
            if (window.history && window.history.pushState) {
                const url = new URL(window.location.href);
                url.searchParams.set('report_id', reportId);
                url.searchParams.set('mode', 'weekly');
                window.history.pushState({}, '', url.toString());
            }
        } catch (error) {
            console.error('Error analyzing report:', error);
            showMessage('Analysis failed: ' + error.message, 'error');
        } finally {
            currentTask = null;
            showLoading(false);
        }
    }
    
    // Analyze monthly performance
    async function analyzeMonthlyPerformance() {
        const employeeId = employeeSelect.value;
        const year = yearSelect.value;
        const month = monthSelect.value;
        
        if (!employeeId) {
            showMessage('Please select an employee', 'error');
            return;
        }
        
        // Clear previous results
        if (analysisResults.style.display !== 'none') {
            analysisResults.style.display = 'none';
            analysisResults.innerHTML = '';
        }
        
        showLoading(true);
        
        try {
            // Start the monthly analysis and get a task
            const taskData = await analysisApi.analyzeMonthlyReports(employeeId, year, month);
            currentTask = taskData.task_id;
            console.log('Monthly analysis task created:', taskData);
            
            // If already complete (existing analysis), get results immediately
            const resultData = taskData.is_complete
                ? await taskApi.getTaskResult(taskData.task_id)
                : await TaskManager.pollTaskUntilComplete(taskData.task_id, {
                    onStatusUpdate: updateLoadingStatus
                });
            
            if (resultData.error_message) {
                throw new Error(resultData.error_message);
            }
            
            displayMonthlyAnalysisResults(resultData.result);
            showMessage('Monthly analysis completed successfully', 'success');
            
            // Update URL without reload to include the parameters
            if (window.history && window.history.pushState) {
                const url = new URL(window.location.href);
                url.searchParams.set('mode', 'monthly');
                url.searchParams.set('employee_id', employeeId);
                url.searchParams.set('year', year);
                url.searchParams.set('month', month);
                window.history.pushState({}, '', url.toString());
            }
        } catch (error) {
            console.error('Error analyzing monthly performance:', error);
            showMessage('Analysis failed: ' + error.message, 'error');
        } finally {
            currentTask = null;
            showLoading(false);
        }
    }
    
    // Helper function to capitalize first letter
    function capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1).toLowerCase();
    }
    
    // Display monthly analysis results
    function displayMonthlyAnalysisResults(data) {
        // Clear previous results
        analysisResults.innerHTML = '';
        
        console.log("Full monthly analysis data received:", data);
        
        // Format month name
        const monthNames = ["January", "February", "March", "April", "May", "June",
                           "July", "August", "September", "October", "November", "December"];
        const monthName = monthNames[data.month - 1];
        
        // Create main analysis container
        const mainContainer = document.createElement('div');
        mainContainer.className = 'analysis-container';
        
        // Add header
        const header = document.createElement('div');
        header.className = 'analysis-header';
        
        // Create header with title
        const headerTitle = document.createElement('h3');
        headerTitle.textContent = `Monthly Analysis: ${monthName} ${data.year}`;
        header.appendChild(headerTitle);
        
        // Create meta info row
        const metaInfo = document.createElement('div');
        metaInfo.className = 'analysis-meta';
        
        // Add risk level badge
        const riskBadge = document.createElement('div');
        riskBadge.className = `risk-level risk-${data.monthly_risk_assessment.overall_risk_level.toLowerCase()}`;
        riskBadge.innerHTML = `<strong>Risk Level:</strong> ${capitalizeFirstLetter(data.monthly_risk_assessment.overall_risk_level)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Overall risk assessment for the month based on recurring challenges, escalating issues, and performance stability.</span></span>`;
        metaInfo.appendChild(riskBadge);
        
        // Add sentiment trend badge
        const sentimentTrendBadge = document.createElement('div');
        sentimentTrendBadge.className = `sentiment sentiment-${data.progress_trends.sentiment_trend.toLowerCase()}`;
        sentimentTrendBadge.innerHTML = `<strong>Sentiment:</strong> ${capitalizeFirstLetter(data.progress_trends.sentiment_trend)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Trend in report sentiment over the month.</span></span>`;
        metaInfo.appendChild(sentimentTrendBadge);
        
        // Add performance trend badge
        const performanceTrendBadge = document.createElement('div');
        performanceTrendBadge.className = `trend-indicator trend-${data.progress_trends.performance_trend.toLowerCase()}`;
        performanceTrendBadge.innerHTML = `<strong>Performance:</strong> ${capitalizeFirstLetter(data.progress_trends.performance_trend)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Overall trend in employee performance throughout the month.</span></span>`;
        metaInfo.appendChild(performanceTrendBadge);
        
        header.appendChild(metaInfo);
        mainContainer.appendChild(header);
        
        // Add monthly summary with improved styling
        if (data.monthly_summary) {
            const summarySection = document.createElement('div');
            summarySection.className = 'monthly-assessment-section monthly-summary-section';
            
            summarySection.innerHTML = `<h5>Monthly Summary
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Overall assessment of employee performance for the month.</span>
                </span>
            </h5>`;
            
            // Create the styled content container
            const summaryContent = document.createElement('div');
            summaryContent.className = 'summary-content';
            
            // Add the paragraph with summary text
            const summaryParagraph = document.createElement('p');
            summaryParagraph.textContent = data.monthly_summary;
            
            summaryContent.appendChild(summaryParagraph);
            summarySection.appendChild(summaryContent);
            mainContainer.appendChild(summarySection);
        }
        
        // Add progress trends section
        if (data.progress_trends) {
            const trendsSection = document.createElement('div');
            trendsSection.className = 'monthly-assessment-section progress-trends-section';
            
            trendsSection.innerHTML = `<h5>Progress Trends
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Patterns and changes in employee performance throughout the month.</span>
                </span>
            </h5>`;
            
            // Create a compact metrics container instead of a grid
            const trendsContainer = document.createElement('div');
            trendsContainer.className = 'compact-metrics-container';
            
            // Add performance trend metric
            const performanceTrendStatus = data.progress_trends.performance_trend.toLowerCase();
            const performanceIcon = performanceTrendStatus === 'improving' ? 'fa-arrow-trend-up' : 
                                  performanceTrendStatus === 'declining' ? 'fa-arrow-trend-down' : 'fa-minus';
            
            const performanceTrendMetric = document.createElement('div');
            performanceTrendMetric.className = `compact-metric metric-performance`;
            
            // Create wrapper for tooltip
            const performanceTooltipWrapper = document.createElement('div');
            performanceTooltipWrapper.className = 'tooltip-wrapper';
            performanceTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Overall trend in work performance throughout the month.
                </div>
            `;
            
            // Create content with improved layout (icon and title side-by-side)
            const performanceContent = document.createElement('div');
            performanceContent.className = 'metric-content-layout';
            performanceContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon performance">
                        <i class="fas ${performanceIcon}"></i>
                    </div>
                    <div class="metric-name">Performance Trend</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${performanceTrendStatus}"></span>
                    ${capitalizeFirstLetter(data.progress_trends.performance_trend)}
                </div>
            `;
            
            // Add content first, then tooltip
            performanceTrendMetric.appendChild(performanceContent);
            performanceTrendMetric.appendChild(performanceTooltipWrapper);
            trendsContainer.appendChild(performanceTrendMetric);
            
            // Update sentiment trend metric with improved layout
            const sentimentTrendStatus = data.progress_trends.sentiment_trend.toLowerCase();
            let sentimentClass = sentimentTrendStatus === 'positive' ? 'improving' : 
                                sentimentTrendStatus === 'negative' ? 'declining' : 'stable';
            const sentimentIcon = sentimentTrendStatus === 'positive' ? 'fa-face-smile' : 
                                sentimentTrendStatus === 'negative' ? 'fa-face-frown' : 'fa-face-meh';
            
            const sentimentTrendMetric = document.createElement('div');
            sentimentTrendMetric.className = `compact-metric metric-sentiment`;
            
            // Create wrapper for tooltip
            const sentimentTooltipWrapper = document.createElement('div');
            sentimentTooltipWrapper.className = 'tooltip-wrapper';
            sentimentTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Trend in report sentiment over the month.
                </div>
            `;
            
            // Create content with improved layout
            const sentimentContent = document.createElement('div');
            sentimentContent.className = 'metric-content-layout';
            sentimentContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon sentiment">
                        <i class="fas ${sentimentIcon}"></i>
                    </div>
                    <div class="metric-name">Sentiment Trend</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${sentimentClass}"></span>
                    ${capitalizeFirstLetter(data.progress_trends.sentiment_trend)}
                </div>
            `;
            
            // Add content first, then tooltip
            sentimentTrendMetric.appendChild(sentimentContent);
            sentimentTrendMetric.appendChild(sentimentTooltipWrapper);
            trendsContainer.appendChild(sentimentTrendMetric);
            
            // Update risk pattern metric with improved layout
            const riskPatternStatus = data.progress_trends.risk_level_pattern.toLowerCase();
            const riskIcon = riskPatternStatus === 'improving' ? 'fa-shield' : 
                           riskPatternStatus === 'declining' ? 'fa-triangle-exclamation' : 'fa-scale-balanced';
            
            const riskPatternMetric = document.createElement('div');
            riskPatternMetric.className = `compact-metric metric-risk`;
            
            // Create wrapper for tooltip
            const riskTooltipWrapper = document.createElement('div');
            riskTooltipWrapper.className = 'tooltip-wrapper';
            riskTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Pattern in risk assessment levels throughout the month.
                </div>
            `;
            
            // Create content with improved layout
            const riskContent = document.createElement('div');
            riskContent.className = 'metric-content-layout';
            riskContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon risk">
                        <i class="fas ${riskIcon}"></i>
                    </div>
                    <div class="metric-name">Risk Pattern</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${riskPatternStatus}"></span>
                    ${capitalizeFirstLetter(data.progress_trends.risk_level_pattern)}
                </div>
            `;
            
            // Add content first, then tooltip
            riskPatternMetric.appendChild(riskContent);
            riskPatternMetric.appendChild(riskTooltipWrapper);
            trendsContainer.appendChild(riskPatternMetric);
            
            // Update challenge resolution metric with improved layout
            const challengeProgressStatus = data.progress_trends.challenge_resolution_progress;
            let challengeClass = challengeProgressStatus === 'improved' ? 'improving' : 
                               challengeProgressStatus === 'declined' ? 'declining' : 'stable';
            const challengeIcon = challengeProgressStatus === 'improved' ? 'fa-circle-check' : 
                                challengeProgressStatus === 'declined' ? 'fa-circle-xmark' : 'fa-circle-pause';
            
            const challengeProgressMetric = document.createElement('div');
            challengeProgressMetric.className = `compact-metric metric-challenges`;
            
            // Create wrapper for tooltip
            const challengeTooltipWrapper = document.createElement('div');
            challengeTooltipWrapper.className = 'tooltip-wrapper';
            challengeTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Progress in resolving reported challenges.
                </div>
            `;
            
            // Create content with improved layout
            const challengeContent = document.createElement('div');
            challengeContent.className = 'metric-content-layout';
            challengeContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon challenges">
                        <i class="fas ${challengeIcon}"></i>
                    </div>
                    <div class="metric-name">Challenge Resolution</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${challengeClass}"></span>
                    ${capitalizeFirstLetter(data.progress_trends.challenge_resolution_progress)}
                </div>
            `;
            
            // Add content first, then tooltip
            challengeProgressMetric.appendChild(challengeContent);
            challengeProgressMetric.appendChild(challengeTooltipWrapper);
            trendsContainer.appendChild(challengeProgressMetric);
            
            trendsSection.appendChild(trendsContainer);
            mainContainer.appendChild(trendsSection);
        }
        
        // Add monthly achievements section
        if (data.monthly_achievements && data.monthly_achievements.length > 0) {
            const achievementsSection = document.createElement('div');
            achievementsSection.className = 'monthly-assessment-section monthly-achievements-section';
            
            achievementsSection.innerHTML = `<h5>Key Monthly Achievements
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Most significant accomplishments from the month with impact ratings.</span>
                </span>
            </h5>`;
            
            // Create a card-based container for achievements (similar to challenges)
            const achievementsContainer = document.createElement('div');
            achievementsContainer.className = 'monthly-achievements-container';
            
            data.monthly_achievements.forEach(achievement => {
                // Create card for each achievement
                const achievementCard = document.createElement('div');
                achievementCard.className = 'achievement-card';
                
                // Extract impact value and determine class
                let impactValue = achievement.impact;
                let impactClass = 'impact-medium';
                let numericImpact = 5; // Default medium value
                
                // Try to extract numeric part if available (for color coding)
                if (typeof impactValue === 'number') {
                    numericImpact = impactValue;
                } else if (typeof impactValue === 'string') {
                    // Extract numeric part if in format like "8 (high priority)"
                    const numericMatch = impactValue.match(/^(\d+)/);
                    if (numericMatch) {
                        numericImpact = parseInt(numericMatch[1]);
                    } else if (impactValue.toLowerCase().includes('high')) {
                        numericImpact = 8;
                    } else if (impactValue.toLowerCase().includes('low')) {
                        numericImpact = 3;
                    }
                }
                
                // Determine class based on numeric impact
                if (numericImpact >= 8) {
                    impactClass = 'impact-high';
                } else if (numericImpact >= 5) {
                    impactClass = 'impact-medium';
                } else {
                    impactClass = 'impact-low';
                }
                
                // Create achievement content with consistent layout
                let achievementContent = `
                    <div class="achievement-title">
                        ${achievement.description || achievement}
                    </div>
                    <div class="achievement-footer">
                        <div class="achievement-impact ${impactClass}">Impact: ${impactValue}</div>
                    </div>
                `;
                
                achievementCard.innerHTML = achievementContent;
                achievementsContainer.appendChild(achievementCard);
            });
            
            achievementsSection.appendChild(achievementsContainer);
            mainContainer.appendChild(achievementsSection);
        } else {
            // Create empty state for no achievements
            const achievementsSection = document.createElement('div');
            achievementsSection.className = 'monthly-assessment-section monthly-achievements-section';
            
            achievementsSection.innerHTML = `
                <h5>Key Monthly Achievements
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">Most significant accomplishments from the month with impact ratings.</span>
                    </span>
                </h5>
                <div class="no-achievements-message">
                    <i class="fas fa-info-circle"></i> No significant achievements recorded for this period.
                </div>
            `;
            
            mainContainer.appendChild(achievementsSection);
        }
        
        // Add recurring challenges section
        if (data.recurring_challenges && data.recurring_challenges.length > 0) {
            const challengesSection = document.createElement('div');
            challengesSection.className = 'monthly-assessment-section recurring-challenges-section';
            
            challengesSection.innerHTML = `<h5>Recurring Challenges
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Issues that appeared multiple times throughout the month with their current status and severity.</span>
                </span>
            </h5>`;
            
            // Create a card-based container for challenges
            const challengesContainer = document.createElement('div');
            challengesContainer.className = 'recurring-challenges-container';
            
            data.recurring_challenges.forEach(challenge => {
                const challengeCard = document.createElement('div');
                
                // Set status and appropriate class
                let statusClass = '';
                let statusText = '';
                
                if (challenge.status) {
                    statusClass = `status-${challenge.status.toLowerCase()}`;
                    statusText = challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1);
                } else {
                    statusClass = 'status-ongoing';
                    statusText = 'Ongoing';
                }
                
                // Set severity and appropriate class
                let severityClass = '';
                let severityText = '';
                
                if (challenge.severity) {
                    severityClass = `severity-${challenge.severity.toLowerCase()}`;
                    severityText = challenge.severity.charAt(0).toUpperCase() + challenge.severity.slice(1);
                } else {
                    severityClass = 'severity-medium';
                    severityText = 'Medium';
                }
                
                challengeCard.className = `challenge-card`;
                
                // Create challenge content with consistent layout
                let challengeContent = `
                    <div class="challenge-title">
                        ${challenge.description || challenge}
                    </div>
                    <div class="challenge-footer">
                        <div class="challenge-severity ${severityClass}"> Severity: ${severityText}</div>
                        <div class="challenge-severity ${statusClass}"> Status: ${statusText}</div>
                    </div>
                `;
                
                challengeCard.innerHTML = challengeContent;
                challengesContainer.appendChild(challengeCard);
            });
            
            challengesSection.appendChild(challengesContainer);
            mainContainer.appendChild(challengesSection);
        } else {
            // Create empty state for no challenges
            const challengesSection = document.createElement('div');
            challengesSection.className = 'monthly-assessment-section recurring-challenges-section';
            
            challengesSection.innerHTML = `
                <h5>Recurring Challenges
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">Issues that appeared multiple times throughout the month with their current status.</span>
                    </span>
                </h5>
                <div class="no-challenges-message">
                    <i class="fas fa-check-circle"></i> No recurring challenges identified for this period.
                </div>
            `;
            
            mainContainer.appendChild(challengesSection);
        }
        
        // Add consistency assessment section
        if (data.consistency_assessment) {
            const consistencySection = document.createElement('div');
            consistencySection.className = 'monthly-assessment-section consistency-assessment-section';
            
            consistencySection.innerHTML = `<h5>Consistency Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Evaluation of the employee's reliability and consistency throughout the month.</span>
                </span>
            </h5>`;
            
            // Create a compact metrics container instead of a grid
            const metricsContainer = document.createElement('div');
            metricsContainer.className = 'compact-metrics-container';
            
            // Task completion reliability
            const reliabilityStatus = data.consistency_assessment.task_completion_reliability.toLowerCase();
            const reliabilityIcon = 'fa-tasks';
            
            const reliabilityMetric = document.createElement('div');
            reliabilityMetric.className = `compact-metric metric-reliability`;
            
            // Create wrapper for tooltip
            const reliabilityTooltipWrapper = document.createElement('div');
            reliabilityTooltipWrapper.className = 'tooltip-wrapper';
            reliabilityTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Measure of how reliably the employee completes assigned tasks on time.
                </div>
            `;
            
            // Create content with improved layout
            const reliabilityContent = document.createElement('div');
            reliabilityContent.className = 'metric-content-layout';
            reliabilityContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon reliability">
                        <i class="fas ${reliabilityIcon}"></i>
                    </div>
                    <div class="metric-name">Task Completion Reliability</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${reliabilityStatus === 'high' ? 'improving' : 
                                                  reliabilityStatus === 'low' ? 'declining' : 'stable'}"></span>
                    ${capitalizeFirstLetter(data.consistency_assessment.task_completion_reliability)}
                </div>
            `;
            
            // Add content first, then tooltip
            reliabilityMetric.appendChild(reliabilityContent);
            reliabilityMetric.appendChild(reliabilityTooltipWrapper);
            metricsContainer.appendChild(reliabilityMetric);
            
            // Work quality consistency
            const qualityStatus = data.consistency_assessment.work_quality_consistency.toLowerCase();
            const qualityIcon = 'fa-star';
            
            const qualityMetric = document.createElement('div');
            qualityMetric.className = `compact-metric metric-quality`;
            
            // Create wrapper for tooltip
            const qualityTooltipWrapper = document.createElement('div');
            qualityTooltipWrapper.className = 'tooltip-wrapper';
            qualityTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Consistency in the quality of work delivered throughout the month.
                </div>
            `;
            
            // Create content with improved layout
            const qualityContent = document.createElement('div');
            qualityContent.className = 'metric-content-layout';
            qualityContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon quality">
                        <i class="fas ${qualityIcon}"></i>
                    </div>
                    <div class="metric-name">Work Quality Consistency</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${qualityStatus === 'high' ? 'improving' : 
                                                  qualityStatus === 'low' ? 'declining' : 'stable'}"></span>
                    ${capitalizeFirstLetter(data.consistency_assessment.work_quality_consistency)}
                </div>
            `;
            
            // Add content first, then tooltip
            qualityMetric.appendChild(qualityContent);
            qualityMetric.appendChild(qualityTooltipWrapper);
            metricsContainer.appendChild(qualityMetric);
            
            // Performance stability
            const stabilityStatus = data.consistency_assessment.performance_stability.toLowerCase();
            const stabilityIcon = 'fa-balance-scale';
            
            const stabilityMetric = document.createElement('div');
            stabilityMetric.className = `compact-metric metric-stability`;
            
            // Create wrapper for tooltip
            const stabilityTooltipWrapper = document.createElement('div');
            stabilityTooltipWrapper.className = 'tooltip-wrapper';
            stabilityTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Overall stability and predictability of the employee's performance.
                </div>
            `;
            
            // Create content with improved layout
            const stabilityContent = document.createElement('div');
            stabilityContent.className = 'metric-content-layout';
            stabilityContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon stability">
                        <i class="fas ${stabilityIcon}"></i>
                    </div>
                    <div class="metric-name">Performance Stability</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${stabilityStatus === 'high' ? 'improving' : 
                                                  stabilityStatus === 'low' ? 'declining' : 'stable'}"></span>
                    ${capitalizeFirstLetter(data.consistency_assessment.performance_stability)}
                </div>
            `;
            
            // Add content first, then tooltip
            stabilityMetric.appendChild(stabilityContent);
            stabilityMetric.appendChild(stabilityTooltipWrapper);
            metricsContainer.appendChild(stabilityMetric);
            
            consistencySection.appendChild(metricsContainer);
            
            // Keep the existing details container with strengths and weaknesses unchanged
            const detailsContainer = document.createElement('div');
            detailsContainer.className = 'consistency-details-container';
            
            // Add notable strengths with empty state handling
            const strengthsContainer = document.createElement('div');
            strengthsContainer.className = 'strengths-container';
            strengthsContainer.innerHTML = `<h6><i class="fas fa-plus-circle"></i> Notable Strengths</h6>`;
            
            const strengthsList = document.createElement('ul');
            strengthsList.className = 'strengths-list';
            
            if (data.consistency_assessment.notable_strengths && data.consistency_assessment.notable_strengths.length > 0) {
                data.consistency_assessment.notable_strengths.forEach(strength => {
                    const strengthItem = document.createElement('li');
                    strengthItem.textContent = strength;
                    strengthsList.appendChild(strengthItem);
                });
            } else {
                // Empty state message
                const emptyMessage = document.createElement('div');
                emptyMessage.className = 'empty-list-message';
                emptyMessage.textContent = 'No notable strengths identified for this period.';
                strengthsList.appendChild(emptyMessage);
            }
            
            strengthsContainer.appendChild(strengthsList);
            detailsContainer.appendChild(strengthsContainer);
            
            // Add areas for improvement (notable weaknesses) with empty state handling
            const weaknessesContainer = document.createElement('div');
            weaknessesContainer.className = 'weaknesses-container';
            weaknessesContainer.innerHTML = `<h6><i class="fas fa-lightbulb"></i> Areas for Improvement</h6>`;
            
            const weaknessesList = document.createElement('ul');
            weaknessesList.className = 'weaknesses-list';
            
            if (data.consistency_assessment.notable_weaknesses && data.consistency_assessment.notable_weaknesses.length > 0) {
                data.consistency_assessment.notable_weaknesses.forEach(weakness => {
                    const weaknessItem = document.createElement('li');
                    weaknessItem.textContent = weakness;
                    weaknessesList.appendChild(weaknessItem);
                });
            } else {
                // Empty state message
                const emptyMessage = document.createElement('div');
                emptyMessage.className = 'empty-list-message';
                emptyMessage.textContent = 'No specific areas for improvement identified for this period.';
                weaknessesList.appendChild(emptyMessage);
            }
            
            weaknessesContainer.appendChild(weaknessesList);
            detailsContainer.appendChild(weaknessesContainer);
            
            // Add the details container to the section
            consistencySection.appendChild(detailsContainer);
            
            mainContainer.appendChild(consistencySection);
        }
        
        // Add growth indicators section
        if (data.growth_indicators) {
            const growthSection = document.createElement('div');
            growthSection.className = 'monthly-assessment-section growth-indicators-section';
            
            growthSection.innerHTML = `<h5>Growth Indicators
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Measures of the employee's professional development and growth throughout the month.</span>
                </span>
            </h5>`;
            
            // Create a compact metrics container instead of a grid
            const growthContainer = document.createElement('div');
            growthContainer.className = 'compact-metrics-container';
            
            // Complexity of tasks
            const complexityTrendStatus = data.growth_indicators.complexity_of_tasks.toLowerCase();
            const complexityIcon = complexityTrendStatus === 'increased' ? 'fa-arrow-trend-up' : 
                                 complexityTrendStatus === 'decreased' ? 'fa-arrow-trend-down' : 'fa-layer-group';
            let complexityClass = complexityTrendStatus === 'increased' ? 'improving' : 
                                complexityTrendStatus === 'decreased' ? 'declining' : 'stable';
            
            const complexityMetric = document.createElement('div');
            complexityMetric.className = `compact-metric metric-complexity`;
            
            // Create wrapper for tooltip
            const complexityTooltipWrapper = document.createElement('div');
            complexityTooltipWrapper.className = 'tooltip-wrapper';
            complexityTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Changes in the complexity level of assigned tasks during this period.
                </div>
            `;
            
            // Create content with improved layout (icon and title side-by-side)
            const complexityContent = document.createElement('div');
            complexityContent.className = 'metric-content-layout';
            complexityContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon complexity">
                        <i class="fas ${complexityIcon}"></i>
                    </div>
                    <div class="metric-name">Task Complexity</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${complexityClass}"></span>
                    ${capitalizeFirstLetter(data.growth_indicators.complexity_of_tasks)}
                </div>
            `;
            
            // Add content first, then tooltip
            complexityMetric.appendChild(complexityContent);
            complexityMetric.appendChild(complexityTooltipWrapper);
            growthContainer.appendChild(complexityMetric);
            
            // Skill development evidence
            const skillStatus = data.growth_indicators.skill_development_evidence.toLowerCase();
            let skillIcon = 'fa-graduation-cap';
            
            const skillMetric = document.createElement('div');
            skillMetric.className = `compact-metric metric-skill`;
            
            // Create wrapper for tooltip
            const skillTooltipWrapper = document.createElement('div');
            skillTooltipWrapper.className = 'tooltip-wrapper';
            skillTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Evidence of new skills or improvement in existing skills during this period.
                </div>
            `;
            
            // Create content with improved layout
            const skillContent = document.createElement('div');
            skillContent.className = 'metric-content-layout';
            skillContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon skill">
                        <i class="fas ${skillIcon}"></i>
                    </div>
                    <div class="metric-name">Skill Development</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${skillStatus === 'high' || skillStatus === 'strong' ? 'improving' : 
                                                  skillStatus === 'low' || skillStatus === 'weak' ? 'declining' : 'stable'}"></span>
                    ${capitalizeFirstLetter(data.growth_indicators.skill_development_evidence)}
                </div>
            `;
            
            // Add content first, then tooltip
            skillMetric.appendChild(skillContent);
            skillMetric.appendChild(skillTooltipWrapper);
            growthContainer.appendChild(skillMetric);
            
            // Confidence level change
            const confidenceTrendStatus = data.growth_indicators.confidence_level_change.toLowerCase();
            const confidenceIcon = confidenceTrendStatus === 'increased' ? 'fa-arrow-trend-up' : 
                                 confidenceTrendStatus === 'decreased' ? 'fa-arrow-trend-down' : 'fa-chart-line';
            let confidenceClass = confidenceTrendStatus === 'increased' ? 'improving' : 
                                confidenceTrendStatus === 'decreased' ? 'declining' : 'stable';
            
            const confidenceMetric = document.createElement('div');
            confidenceMetric.className = `compact-metric metric-confidence`;
            
            // Create wrapper for tooltip
            const confidenceTooltipWrapper = document.createElement('div');
            confidenceTooltipWrapper.className = 'tooltip-wrapper';
            confidenceTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    Changes in how confidently the employee approaches tasks and challenges.
                </div>
            `;
            
            // Create content with improved layout
            const confidenceContent = document.createElement('div');
            confidenceContent.className = 'metric-content-layout';
            confidenceContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon confidence">
                        <i class="fas ${confidenceIcon}"></i>
                    </div>
                    <div class="metric-name">Confidence Level</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${confidenceClass}"></span>
                    ${capitalizeFirstLetter(data.growth_indicators.confidence_level_change)}
                </div>
            `;
            
            // Add content first, then tooltip
            confidenceMetric.appendChild(confidenceContent);
            confidenceMetric.appendChild(confidenceTooltipWrapper);
            growthContainer.appendChild(confidenceMetric);
            
            // Approach to challenges
            const approachTrendStatus = data.growth_indicators.approach_to_challenges.toLowerCase();
            let approachClass = approachTrendStatus.includes('proactive') ? 'improving' : 
                              approachTrendStatus.includes('reactive') ? 'declining' : 'stable';
            const approachIcon = approachClass === 'improving' ? 'fa-shield' : 
                               approachClass === 'declining' ? 'fa-triangle-exclamation' : 'fa-fire-extinguisher';
            
            const approachMetric = document.createElement('div');
            approachMetric.className = `compact-metric metric-approach`;
            
            // Create wrapper for tooltip
            const approachTooltipWrapper = document.createElement('div');
            approachTooltipWrapper.className = 'tooltip-wrapper';
            approachTooltipWrapper.innerHTML = `
                <div class="metric-tooltip">
                    How the employee addresses obstacles and challenges in their work.
                </div>
            `;
            
            // Create content with improved layout
            const approachContent = document.createElement('div');
            approachContent.className = 'metric-content-layout';
            approachContent.innerHTML = `
                <div class="title-row">
                    <div class="metric-icon approach">
                        <i class="fas ${approachIcon}"></i>
                    </div>
                    <div class="metric-name">Approach to Challenges</div>
                </div>
                <div class="metric-value">
                    <span class="status-indicator status-${approachClass}"></span>
                    ${capitalizeFirstLetter(data.growth_indicators.approach_to_challenges)}
                </div>
            `;
            
            // Add content first, then tooltip
            approachMetric.appendChild(approachContent);
            approachMetric.appendChild(approachTooltipWrapper);
            growthContainer.appendChild(approachMetric);
            
            growthSection.appendChild(growthContainer);
            mainContainer.appendChild(growthSection);
        }

        // Add focus areas section (NEW)
        if (data.focus_areas && data.focus_areas.length > 0) {
            const focusAreasSection = document.createElement('div');
            focusAreasSection.className = 'monthly-assessment-section focus-areas-section';

            focusAreasSection.innerHTML = `<h5>Focus Areas
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Key projects or responsibilities where the employee invested significant time and effort, with priority and time investment levels.</span>
                </span>
            </h5>`;

            const focusAreasList = document.createElement('ul');
            focusAreasList.className = 'focus-areas-list';

            data.focus_areas.forEach(area => {
                const item = document.createElement('li');
                item.className = 'focus-area-item';

                // Project name
                const name = document.createElement('span');
                name.className = 'focus-area-name';
                const focusIcon = document.createElement('i');
                focusIcon.className = 'fas fa-bullseye';
                focusIcon.style.color = '#8b5cf6';
                focusIcon.style.marginRight = '8px';
                name.appendChild(focusIcon);
                name.appendChild(document.createTextNode(area.project));
                

                // Priority badge
                const priority = document.createElement('span');
                let priorityClass = '';
                if (area.priority_level === 'high') priorityClass = 'priority-high';
                else if (area.priority_level === 'medium') priorityClass = 'priority-medium';
                else priorityClass = 'priority-low';
                priority.className = `focus-area-priority ${priorityClass}`;
                priority.textContent = `Priority: ${area.priority_level.charAt(0).toUpperCase() + area.priority_level.slice(1)}`;

                // Time investment badge
                const time = document.createElement('span');
                time.className = 'focus-area-time';
                let timeIcon = '<i class="fas fa-clock"></i>';
                if (area.time_investment === 'high') timeIcon = '<i class="fas fa-hourglass-start"></i>';
                else if (area.time_investment === 'medium') timeIcon = '<i class="fas fa-hourglass-half"></i>';
                else if (area.time_investment === 'low') timeIcon = '<i class="fas fa-hourglass-end"></i>';
                time.innerHTML = `${timeIcon} ${area.time_investment.charAt(0).toUpperCase() + area.time_investment.slice(1)} Time`;

                // Add to item
                item.appendChild(name);
                item.appendChild(priority);
                item.appendChild(time);

                focusAreasList.appendChild(item);
            });

            focusAreasSection.appendChild(focusAreasList);
            mainContainer.appendChild(focusAreasSection);
        } else {
            // Empty state for no focus areas
            const focusAreasSection = document.createElement('div');
            focusAreasSection.className = 'monthly-assessment-section focus-areas-section';
            focusAreasSection.innerHTML = `
                <h5>Focus Areas
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">Key projects or responsibilities where the employee invested significant time and effort, with priority and time investment levels.</span>
                    </span>
                </h5>
                <div class="no-focus-areas-message">
                    <i class="fas fa-info-circle"></i> No specific focus areas recorded for this period.
                </div>
            `;
            mainContainer.appendChild(focusAreasSection);
        }


        // Add strategic recommendations section with improved styling
        if (data.strategic_recommendations && data.strategic_recommendations.length > 0) {
            const recommendationsSection = document.createElement('div');
            recommendationsSection.className = 'monthly-assessment-section strategic-recommendations-section';
            
            recommendationsSection.innerHTML = `<h5>Strategic Recommendations
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Actionable suggestions for improvement and development based on monthly performance analysis.</span>
                </span>
            </h5>`;
            
            // Create container for recommendations with improved styling
            const recommendationsContainer = document.createElement('div');
            recommendationsContainer.className = 'recommendations-container';
            
            const recommendationsList = document.createElement('ul');
            recommendationsList.className = 'recommendations-list';
            
            data.strategic_recommendations.forEach(recommendation => {
                const recItem = document.createElement('li');
                
                if (typeof recommendation === 'string') {
                    // Create wrapper for text to apply flex styling properly
                    const textSpan = document.createElement('span');
                    textSpan.className = 'recommendation-text';
                    textSpan.textContent = recommendation;
                    recItem.appendChild(textSpan);
                } else {
                    // For structured recommendations with priority
                    const recommendationText = recommendation.action || recommendation;
                    
                    // Create wrapper for text portion
                    const textSpan = document.createElement('span');
                    textSpan.className = 'recommendation-text';
                    
                    if (typeof recommendationText === 'string') {
                        textSpan.textContent = recommendationText;
                    } else {
                        textSpan.textContent = JSON.stringify(recommendationText);
                    }
                    
                    recItem.appendChild(textSpan);
                    
                    // Add priority label if available - simplified to just show the priority level
                    if (recommendation.priority) {
                        let priorityClass = '';
                        let priorityValue = '';
                        
                        if (recommendation.priority.toLowerCase() === 'high') {
                            priorityClass = 'priority-high';
                            priorityValue = 'High';
                        } else if (recommendation.priority.toLowerCase() === 'medium') {
                            priorityClass = 'priority-medium';
                            priorityValue = 'Medium';
                        } else {
                            priorityClass = 'priority-low';
                            priorityValue = 'Low';
                        }
                        
                        const prioritySpan = document.createElement('span');
                        prioritySpan.className = `priority ${priorityClass}`;
                        prioritySpan.textContent = priorityValue;
                        recItem.appendChild(prioritySpan);
                    }
                }
                
                recommendationsList.appendChild(recItem);
            });
            
            recommendationsContainer.appendChild(recommendationsList);
            recommendationsSection.appendChild(recommendationsContainer);
            mainContainer.appendChild(recommendationsSection);
        }
        
        // Add to main results container
        analysisResults.appendChild(mainContainer);
        analysisResults.style.display = 'block';
        
        // Scroll to the results
        analysisResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Display weekly analysis results - existing function
    function displayAnalysisResults(data) {
        // Clear previous results
        analysisResults.innerHTML = '';
        
        console.log("Full analysis data received:", data);
        console.log("Credibility assessment:", data.credibility_assessment);
        console.log("Performance assessment:", data.performance_assessment);
        
        // Extract data from analysis result
        const { 
            full_analysis_json,
            sentiment_score, 
            risk_level, 
            risk_explanation,
            achievements_json,
            challenges_json,
            topics,
            action_items,
            credibility_assessment,
            performance_assessment
        } = data;
        
        // Determine sentiment text based on score
        let sentimentText = "Neutral";
        let sentimentClass = "sentiment-neutral";
        if (sentiment_score > 0.7) {
            sentimentText = "Positive";
            sentimentClass = "sentiment-positive";
        } else if (sentiment_score < 0.3) {
            sentimentText = "Negative";
            sentimentClass = "sentiment-negative";
        }
        
        // Create main analysis container
        const mainContainer = document.createElement('div');
        mainContainer.className = 'analysis-container';
        
        // Add header
        const header = document.createElement('div');
        header.className = 'analysis-header';
        
        // Create header with title
        const headerTitle = document.createElement('h3');
        headerTitle.textContent = 'Report Analysis';
        header.appendChild(headerTitle);
        
        // Create meta info row for sentiment, risk, credibility and consistency
        const metaInfo = document.createElement('div');
        metaInfo.className = 'analysis-meta';
        
        // Add performance rating badge if available - add this FIRST
        if (performance_assessment && performance_assessment.rating) {
            const performanceBadge = document.createElement('div');
            performanceBadge.className = `performance-rating performance-${performance_assessment.rating.toLowerCase()}`;
            performanceBadge.innerHTML = `<strong>Performance:</strong> ${capitalizeFirstLetter(performance_assessment.rating)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Overall assessment of employee performance based on task completion, impact, challenge management, and planning quality.</span></span>`;
            metaInfo.appendChild(performanceBadge);
        }
        
        // Add sentiment badge with tooltip
        const sentimentBadge = document.createElement('div');
        sentimentBadge.className = `sentiment ${sentimentClass.toLowerCase()}`;
        sentimentBadge.innerHTML = `<strong>Sentiment:</strong> ${sentimentText}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Overall tone of the report, derived from language used, confidence levels expressed, and balance between achievements and challenges.</span></span>`;
        metaInfo.appendChild(sentimentBadge);
        
        // Add risk level badge with tooltip
        const riskBadge = document.createElement('div');
        riskBadge.className = `risk-level risk-${risk_level.toLowerCase()}`;
        riskBadge.innerHTML = `<strong>Risk Level:</strong> ${capitalizeFirstLetter(risk_level)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Assessment of concerns requiring management attention. Considers unaddressed resource requests, low confidence levels, external challenges, and negative patterns.</span></span>`;
        metaInfo.appendChild(riskBadge);
        
        // Add credibility rating badge if available with tooltip - capitalize the rating
        if (credibility_assessment && credibility_assessment.rating) {
            const credibilityBadge = document.createElement('div');
            credibilityBadge.className = `credibility-level credibility-${credibility_assessment.rating.toLowerCase()}`;
            credibilityBadge.innerHTML = `<strong>Credibility:</strong> ${capitalizeFirstLetter(credibility_assessment.rating)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Measures how well-supported the claims in the report are with evidence. High credibility means claims are specific and realistic; low credibility indicates potential exaggeration.</span></span>`;
            metaInfo.appendChild(credibilityBadge);
            
            // Add consistency score badge alongside the other badges with tooltip - capitalize the score
            if (credibility_assessment.consistency_score) {
                const consistencyBadge = document.createElement('div');
                consistencyBadge.className = `consistency-level consistency-${credibility_assessment.consistency_score.toLowerCase()}`;
                consistencyBadge.innerHTML = `<strong>Consistency:</strong> ${capitalizeFirstLetter(credibility_assessment.consistency_score)}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Evaluates how well different sections of the report align with each other. High consistency indicates the report sections support each other; low consistency suggests contradictions between sections.</span></span>`;
                metaInfo.appendChild(consistencyBadge);
            }
        }
        
        header.appendChild(metaInfo);
        mainContainer.appendChild(header);

        // Add performance assessment section if available - NOW BEFORE credibility assessment
        if (performance_assessment) {
            const performanceSection = document.createElement('div');
            performanceSection.className = 'performance-assessment-section analysis-section';
            
            // Create section heading with icon and tooltip
            performanceSection.innerHTML = `<h5>Performance Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">An evaluation of the employee's overall performance based on task completion, impact, challenge management, and planning quality.</span>
                </span>
            </h5>`;
            
            // Add summary paragraph
            const summaryPara = document.createElement('p');
            summaryPara.textContent = performance_assessment.summary;
            performanceSection.appendChild(summaryPara);
            
            // Add key strengths if available
            if (performance_assessment.key_strengths && performance_assessment.key_strengths.length > 0) {
                const strengthsContainer = document.createElement('div');
                strengthsContainer.className = 'strengths-container';
                
                const strengthsTitle = document.createElement('h6');
                strengthsTitle.innerHTML = `Key Strengths:
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">Notable areas where the employee demonstrates strong performance and capabilities.</span>
                    </span>`;
                strengthsContainer.appendChild(strengthsTitle);
                
                const strengthsList = document.createElement('ul');
                strengthsList.className = 'strengths-list';
                
                performance_assessment.key_strengths.forEach(strength => {
                    const strengthItem = document.createElement('li');
                    strengthItem.className = 'flag-item';
                    strengthItem.innerHTML = `<i class="fas fa-check-circle"></i> ${strength}`;
                    strengthsList.appendChild(strengthItem);
                });
                
                strengthsContainer.appendChild(strengthsList);
                performanceSection.appendChild(strengthsContainer);
            }
            
            // Add improvement areas if available
            if (performance_assessment.improvement_areas && performance_assessment.improvement_areas.length > 0) {
                const improvementContainer = document.createElement('div');
                improvementContainer.className = 'improvement-areas-container';
                
                const improvementTitle = document.createElement('h6');
                improvementTitle.innerHTML = `Areas for Improvement:
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">Specific areas where the employee could enhance their performance and effectiveness.</span>
                    </span>`;
                improvementContainer.appendChild(improvementTitle);
                
                const improvementList = document.createElement('ul');
                improvementList.className = 'improvement-list';
                
                performance_assessment.improvement_areas.forEach(area => {
                    const areaItem = document.createElement('li');
                    areaItem.className = 'improvement-item';
                    areaItem.innerHTML = `<i class="fas fa-arrow-alt-circle-up"></i> ${area}`;
                    improvementList.appendChild(areaItem);
                });
                
                improvementContainer.appendChild(improvementList);
                performanceSection.appendChild(improvementContainer);
            }
            
            mainContainer.appendChild(performanceSection);
        }
        
        // Add credibility assessment section if available
        if (credibility_assessment) {
            const credibilitySection = document.createElement('div');
            credibilitySection.className = 'credibility-assessment-section analysis-section';
            
            // Create section heading with icon and tooltip
            credibilitySection.innerHTML = `<h5>Credibility Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">An evaluation of how well-supported the claims in the report are with evidence and how consistently different parts of the report align.</span>
                </span>
            </h5>`;
            
            // Add explanation paragraph
            const explanationPara = document.createElement('p');
            explanationPara.textContent = credibility_assessment.explanation;
            credibilitySection.appendChild(explanationPara);
            
            // Add exaggeration flags if any exist
            if (credibility_assessment.exaggeration_flags && credibility_assessment.exaggeration_flags.length > 0) {
                const flagsContainer = document.createElement('div');
                flagsContainer.className = 'exaggeration-flags';
                
                const flagsTitle = document.createElement('h6');
                flagsTitle.innerHTML = `Potential Exaggerations:
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">Statements identified as potentially exaggerated based on vague language, inflated impact claims, contradictions, or outcomes disproportionate to the described effort.</span>
                    </span>`;
                flagsContainer.appendChild(flagsTitle);
                
                const flagsList = document.createElement('ul');
                flagsList.className = 'flags-list';
                
                credibility_assessment.exaggeration_flags.forEach(flag => {
                    const flagItem = document.createElement('li');
                    flagItem.className = 'flag-item';
                    flagItem.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${flag}`;
                    flagsList.appendChild(flagItem);
                });
                
                flagsContainer.appendChild(flagsList);
                credibilitySection.appendChild(flagsContainer);
            }
            
            mainContainer.appendChild(credibilitySection);
        }
        
        // Add risk explanation
        if (risk_explanation) {
            const riskExplanation = document.createElement('div');
            riskExplanation.className = 'risk-explanation analysis-section';
            riskExplanation.innerHTML = `<h5>Risk Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Identifies concerns requiring management attention based on unfulfilled resource requests, confidence levels, and patterns across reports.</span>
                </span>
            </h5>
                <p>${risk_explanation}</p>`;
            mainContainer.appendChild(riskExplanation);
        }
        
        // Add topics section
        if (topics && topics.length > 0) {
            const topicsSection = document.createElement('div');
            topicsSection.className = 'topics-section analysis-section';
            topicsSection.innerHTML = `<h5>Key Topics
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Main themes, projects, and focus areas mentioned throughout the employee's report.</span>
                </span>
            </h5>`;
            
            const topicsContainer = document.createElement('div');
            topicsContainer.className = 'topics-container';
            
            topics.forEach(topic => {
                const topicTag = document.createElement('span');
                topicTag.className = 'topic-tag';
                topicTag.textContent = topic;
                topicsContainer.appendChild(topicTag);
            });
            
            topicsSection.appendChild(topicsContainer);
            mainContainer.appendChild(topicsSection);
        }
        
        // Add achievements section
        if (achievements_json && achievements_json.length > 0) {
            const achievementsSection = document.createElement('div');
            achievementsSection.className = 'achievements-section analysis-section';
            achievementsSection.innerHTML = `<h5>Achievements
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Key accomplishments reported by the employee with impact ratings where higher numbers represent greater positive effects on goals and outcomes.</span>
                </span>
            </h5>`;
            
            const achievementsList = document.createElement('ul');
            achievementsList.className = 'achievements-list';
            
            achievements_json.forEach(achievement => {
                const achievementItem = document.createElement('li');
                achievementItem.className = 'achievement-item';
                
                // Add description as before
                let achievementContent = `<div class="achievement-description">${achievement.description || achievement}</div>`;
                
                // Add impact with tooltip using an info icon instead of underlining the text
                if (achievement.impact) {
                    achievementContent += `
                        <div class="achievement-impact">
                            Impact: ${achievement.impact}
                            <span class="tooltip-trigger">
                                <i class="fas fa-question-circle"></i>
                                <span class="tooltip">Impact ratings range from 1-10, where 10 represents the highest impact and 1 represents minimal impact.</span>
                            </span>
                        </div>`;
                }
                
                achievementItem.innerHTML = achievementContent;
                achievementsList.appendChild(achievementItem);
            });
            
            achievementsSection.appendChild(achievementsList);
            mainContainer.appendChild(achievementsSection);
        }
        
        // Add challenges section
        if (challenges_json && challenges_json.length > 0) {
            const challengesSection = document.createElement('div');
            challengesSection.className = 'challenges-section analysis-section';
            challengesSection.innerHTML = `<h5>Challenges
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Obstacles or issues reported by the employee with severity ratings indicating their impact on work performance.</span>
                </span>
            </h5>`;
            
            const challengesList = document.createElement('ul');
            challengesList.className = 'challenges-list';
            
            challenges_json.forEach(challenge => {
                let challengeContent;
                let severityClass = '';
                
                if (typeof challenge === 'string') {
                    challengeContent = challenge;
                } else {
                    challengeContent = `<div class="challenge-description">${challenge.description || ''}</div>`;
                    
                    if (challenge.severity) {
                        severityClass = `severity-${challenge.severity.toLowerCase()}`;
                        // Add severity with tooltip using an info icon instead of underlining
                        challengeContent += `
                            <div class="challenge-severity">
                                Severity: ${challenge.severity}
                                <span class="tooltip-trigger">
                                    <i class="fas fa-question-circle"></i>
                                    <span class="tooltip">Severity indicates how much this challenge affects employee performance and intended outcomes. Low: minimal impact, Medium: moderate disruption, High: significant blocker.</span>
                                </span>
                            </div>`;
                    }
                }
                
                const challengeItem = document.createElement('li');
                challengeItem.className = `challenge-item ${severityClass}`;
                
                if (typeof challenge === 'string') {
                    challengeItem.textContent = challenge;
                } else {
                    challengeItem.innerHTML = challengeContent;
                }
                
                challengesList.appendChild(challengeItem);
            });
            
            challengesSection.appendChild(challengesList);
            mainContainer.appendChild(challengesSection);
        }
        
        // Add action items section
        if (action_items && action_items.length > 0) {
            const actionItemsSection = document.createElement('div');
            actionItemsSection.className = 'action-items-section analysis-section';
            actionItemsSection.innerHTML = `<h5>Recommended Actions
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Suggested follow-up items for both management and employees to address based on the report content, including resource needs, support requirements, and opportunities to build on achievements.</span>
                </span>
            </h5>`;
            
            const actionItemsList = document.createElement('ul');
            actionItemsList.className = 'action-items-list';
            
            action_items.forEach(actionItem => {
                const actionItemElement = document.createElement('li');
                actionItemElement.textContent = actionItem;
                actionItemsList.appendChild(actionItemElement);
            });
            
            actionItemsSection.appendChild(actionItemsList);
            mainContainer.appendChild(actionItemsSection);
        }
        
        // Add to main results container
        analysisResults.appendChild(mainContainer);
        analysisResults.style.display = 'block';
        
        // Scroll to the results
        analysisResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Helper functions
    function showMessage(message, type = 'info') {
        statusMessage.className = `${type}-message`;
        statusMessage.textContent = message;
        statusMessage.style.display = 'block';
        
        // Auto hide success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (statusMessage.textContent === message) {
                    statusMessage.style.display = 'none';
                }
            }, 5000);
        }
    }
    
    function showLoading(isLoading) {
        loadingIndicator.style.display = isLoading ? 'block' : 'none';
        analyzeButton.disabled = isLoading;
        if (isLoading) {
            showMessage('Initializing analysis...', 'loading');
        }
    }
    
    // Helper function to update URL parameters without page reload
    function updateUrlParameter(key, value) {
        if (window.history && window.history.pushState) {
            const url = new URL(window.location.href);
            url.searchParams.set(key, value);
            window.history.pushState({}, '', url.toString());
        }
    }
});
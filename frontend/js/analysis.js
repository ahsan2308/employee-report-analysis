document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const employeeSelect = document.getElementById('employeeSelect');
    const reportSelect = document.getElementById('reportSelect');
    const analyzeButton = document.getElementById('analyzeButton');
    const analysisResults = document.getElementById('analysisResults');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const statusMessage = document.getElementById('statusMessage');
    
    // Get URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const reportIdFromUrl = urlParams.get('report_id');
    const autoAnalyze = urlParams.get('auto_analyze');
    
    // Track the current analysis task
    let currentTask = null;
    
    // Event listeners
    loadEmployees();
    employeeSelect.addEventListener('change', loadReportsForEmployee);
    reportSelect.addEventListener('change', toggleAnalyzeButton);
    analyzeButton.addEventListener('click', analyzeSelectedReport);
    
    // If we have a report ID and auto_analyze is true, show loading immediately
    if (reportIdFromUrl && autoAnalyze === 'true') {
        showLoading(true);
        showMessage('Initializing analysis...', 'loading');
    }
    
    // Toggle analyze button based on report selection
    function toggleAnalyzeButton() {
        analyzeButton.disabled = !reportSelect.value;
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
            
            // If we have a report ID from URL, find the related employee and select them
            if (reportIdFromUrl) {
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
                    
                    // Auto-analyze if requested - do it right away
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
            showMessage('Processing report analysis...', 'loading');
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
            
            // Update URL without reload to include the report_id
            if (window.history && window.history.pushState) {
                const url = new URL(window.location.href);
                url.searchParams.set('report_id', reportId);
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
    
    // Display analysis results with enhanced data
    function displayAnalysisResults(data) {
        // Clear previous results
        analysisResults.innerHTML = '';
        
        // Extract data from analysis result
        const { 
            full_analysis_json,
            sentiment_score, 
            risk_level, 
            risk_explanation,
            achievements_json,
            challenges_json,
            topics,
            action_items
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
        header.innerHTML = `
            <h3>Report Analysis</h3>
            <div class="analysis-meta">
                <div class="sentiment ${sentimentClass.toLowerCase()}">
                    <strong>Sentiment:</strong> ${sentimentText}
                </div>
                <div class="risk-level risk-${risk_level.toLowerCase()}">
                    <strong>Risk Level:</strong> ${risk_level}
                </div>
            </div>
        `;
        mainContainer.appendChild(header);

        // Add risk explanation
        if (risk_explanation) {
            const riskExplanation = document.createElement('div');
            riskExplanation.className = 'risk-explanation analysis-section';
            riskExplanation.innerHTML = `
                <h5>Risk Assessment</h5>
                <p>${risk_explanation}</p>
            `;
            mainContainer.appendChild(riskExplanation);
        }
        
        // Add topics section
        if (topics && topics.length > 0) {
            const topicsSection = document.createElement('div');
            topicsSection.className = 'topics-section analysis-section';
            topicsSection.innerHTML = '<h5>Key Topics</h5>';
            
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
            achievementsSection.innerHTML = '<h5>Achievements</h5>';
            
            const achievementsList = document.createElement('ul');
            achievementsList.className = 'achievements-list';
            
            achievements_json.forEach(achievement => {
                const achievementItem = document.createElement('li');
                achievementItem.className = 'achievement-item';
                achievementItem.innerHTML = `
                    <div class="achievement-description">${achievement.description || achievement}</div>
                    ${achievement.impact ? `<div class="achievement-impact">Impact: ${achievement.impact}</div>` : ''}
                `;
                achievementsList.appendChild(achievementItem);
            });
            
            achievementsSection.appendChild(achievementsList);
            mainContainer.appendChild(achievementsSection);
        }
        
        // Add challenges section
        if (challenges_json && challenges_json.length > 0) {
            const challengesSection = document.createElement('div');
            challengesSection.className = 'challenges-section analysis-section';
            challengesSection.innerHTML = '<h5>Challenges</h5>';
            
            const challengesList = document.createElement('ul');
            challengesList.className = 'challenges-list';
            
            challenges_json.forEach(challenge => {
                let challengeContent;
                let severityClass = '';
                
                if (typeof challenge === 'string') {
                    challengeContent = challenge;
                } else {
                    challengeContent = challenge.description || '';
                    if (challenge.severity) {
                        severityClass = `severity-${challenge.severity.toLowerCase()}`;
                    }
                }
                
                const challengeItem = document.createElement('li');
                challengeItem.className = `challenge-item ${severityClass}`;
                
                if (typeof challenge === 'string') {
                    challengeItem.textContent = challenge;
                } else {
                    challengeItem.innerHTML = `
                        <div class="challenge-description">${challenge.description || ''}</div>
                        ${challenge.severity ? `<div class="challenge-severity">Severity: ${challenge.severity}</div>` : ''}
                    `;
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
            actionItemsSection.innerHTML = '<h5>Recommended Actions</h5>';
            
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
});
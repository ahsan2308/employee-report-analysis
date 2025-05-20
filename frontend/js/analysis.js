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
            console.log("Analysis data from API:", analysisData);
            console.log("Credibility assessment data:", analysisData.credibility_assessment);
            
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
        
        console.log("Full analysis data received:", data);
        console.log("Credibility assessment:", data.credibility_assessment);
        
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
            credibility_assessment
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
        
        // Add sentiment badge with tooltip
        const sentimentBadge = document.createElement('div');
        sentimentBadge.className = `sentiment ${sentimentClass.toLowerCase()}`;
        sentimentBadge.innerHTML = `<strong>Sentiment:</strong> ${sentimentText}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Overall tone of the report, derived from language used, confidence levels expressed, and balance between achievements and challenges.</span></span>`;
        metaInfo.appendChild(sentimentBadge);
        
        // Add risk level badge with tooltip - Fix by putting everything on one line without linebreaks
        const riskBadge = document.createElement('div');
        riskBadge.className = `risk-level risk-${risk_level.toLowerCase()}`;
        riskBadge.innerHTML = `<strong>Risk Level:</strong> ${risk_level}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Assessment of concerns requiring management attention. Considers unaddressed resource requests, low confidence levels, external challenges, and negative patterns.</span></span>`;
        metaInfo.appendChild(riskBadge);
        
        // Add credibility rating badge if available with tooltip
        if (credibility_assessment && credibility_assessment.rating) {
            const credibilityBadge = document.createElement('div');
            credibilityBadge.className = `credibility-level credibility-${credibility_assessment.rating.toLowerCase()}`;
            credibilityBadge.innerHTML = `<strong>Credibility:</strong> ${credibility_assessment.rating}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Measures how well-supported the claims in the report are with evidence. High credibility means claims are specific and realistic; low credibility indicates potential exaggeration.</span></span>`;
            metaInfo.appendChild(credibilityBadge);
            
            // Add consistency score badge alongside the other badges with tooltip
            if (credibility_assessment.consistency_score) {
                const consistencyBadge = document.createElement('div');
                consistencyBadge.className = `consistency-level consistency-${credibility_assessment.consistency_score.toLowerCase()}`;
                consistencyBadge.innerHTML = `<strong>Consistency:</strong> ${credibility_assessment.consistency_score}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Evaluates how well different sections of the report align with each other. High consistency indicates the report sections support each other; low consistency suggests contradictions between sections.</span></span>`;
                metaInfo.appendChild(consistencyBadge);
            }
        }
        
        header.appendChild(metaInfo);
        mainContainer.appendChild(header);

        // Add credibility assessment section if available (place before risk assessment)
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
});
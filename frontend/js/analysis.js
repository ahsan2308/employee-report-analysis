document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const employeeSelect = document.getElementById('employeeSelect');
    const reportSelect = document.getElementById('reportSelect');
    const analyzeButton = document.getElementById('analyzeButton');
    const analysisResults = document.getElementById('analysisResults');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const statusMessage = document.getElementById('statusMessage');
    
    // Monthly analysis elements
    const weeklyToggle = document.getElementById('weeklyToggle');
    const monthlyToggle = document.getElementById('monthlyToggle');
    const weeklyControls = document.querySelector('.weekly-controls');
    const monthlyControls = document.querySelector('.monthly-controls');
    const monthSelect = document.getElementById('monthSelect');
    const yearSelect = document.getElementById('yearSelect');
    
    // Analysis mode state
    let currentMode = 'weekly'; // 'weekly' or 'monthly'
    
    // Get URL parameters - enhance to support monthly parameters
    const urlParams = new URLSearchParams(window.location.search);
    const reportIdFromUrl = urlParams.get('report_id');
    const autoAnalyze = urlParams.get('auto_analyze');
    const analysisMode = urlParams.get('mode');
    const employeeIdFromUrl = urlParams.get('employee_id');
    const yearFromUrl = urlParams.get('year');
    const monthFromUrl = urlParams.get('month');
    
    // Track the current analysis task
    let currentTask = null;
    
    // Event listeners for analysis type toggle
    weeklyToggle.addEventListener('change', () => setAnalysisMode('weekly'));
    monthlyToggle.addEventListener('change', () => setAnalysisMode('monthly'));
    
    // Check if mode is specified in URL
    if (analysisMode === 'monthly') {
        setAnalysisMode('monthly');
        monthlyToggle.checked = true;
        
        // If we have employee, year, and month parameters, try to load and analyze that specific period
        if (employeeIdFromUrl && yearFromUrl && monthFromUrl) {
            // Handle direct monthly analysis link after employee data is loaded
            const directMonthlyLoad = async () => {
                // Wait for the employee dropdown to have options
                if (employeeSelect.options.length <= 1) {
                    setTimeout(directMonthlyLoad, 100);
                    return;
                }
                
                // Select the employee
                employeeSelect.value = employeeIdFromUrl;
                
                // Set the year and month values
                if (yearSelect.querySelector(`option[value="${yearFromUrl}"]`)) {
                    yearSelect.value = yearFromUrl;
                }
                monthSelect.value = monthFromUrl;
                
                // Enable analyze button
                toggleAnalyzeButton();
                
                // Auto-analyze if requested
                if (autoAnalyze === 'true') {
                    analyzeMonthlyPerformance();
                }
            };
            
            // Start the loading process
            directMonthlyLoad();
        }
    } else {
        weeklyToggle.checked = true; // Default to weekly
    }
    
    // Populate year dropdown with last 5 years and next 2 years
    populateYearDropdown();
    
    // Set current month and year as default
    const currentDate = new Date();
    monthSelect.value = currentDate.getMonth() + 1; // JavaScript months are 0-based
    if (yearSelect.querySelector(`option[value="${currentDate.getFullYear()}"]`)) {
        yearSelect.value = currentDate.getFullYear();
    }
    
    // Event listeners for original functionality
    loadEmployees();
    employeeSelect.addEventListener('change', loadReportsForEmployee);
    reportSelect.addEventListener('change', toggleAnalyzeButton);
    analyzeButton.addEventListener('click', handleAnalyzeButtonClick);
    
    // Monthly analysis specific listeners
    monthSelect.addEventListener('change', toggleAnalyzeButton);
    yearSelect.addEventListener('change', toggleAnalyzeButton);
    
    // If we have a report ID and auto_analyze is true, show loading immediately
    if (reportIdFromUrl && autoAnalyze === 'true') {
        showLoading(true);
        showMessage('Initializing analysis...', 'loading');
    }
    
    /**
     * Set the analysis mode and update UI accordingly
     */
    function setAnalysisMode(mode) {
        currentMode = mode;
        
        // Update UI based on mode
        if (mode === 'weekly') {
            weeklyControls.style.display = 'block';
            monthlyControls.style.display = 'none';
            analyzeButton.textContent = analyzeButton.getAttribute('data-weekly-text');
        } else { // monthly
            weeklyControls.style.display = 'none';
            monthlyControls.style.display = 'block';
            analyzeButton.textContent = analyzeButton.getAttribute('data-monthly-text');
        }
        
        // Clear any previous results
        if (analysisResults.style.display !== 'none') {
            analysisResults.style.display = 'none';
            analysisResults.innerHTML = '';
        }
        
        // Update URL parameter without reloading
        if (window.history && window.history.pushState) {
            const url = new URL(window.location.href);
            
            // Update mode parameter
            url.searchParams.set('mode', mode);
            
            // Clear parameters that aren't relevant to this mode
            if (mode === 'weekly') {
                url.searchParams.delete('year');
                url.searchParams.delete('month');
            } else {
                url.searchParams.delete('report_id');
            }
            
            window.history.pushState({mode: mode}, '', url.toString());
        }
        
        // Update button state
        toggleAnalyzeButton();
    }
    
    /**
     * Populate the year dropdown with relevant years
     */
    function populateYearDropdown() {
        const currentYear = new Date().getFullYear();
        const startYear = currentYear - 5; // 5 years back
        const endYear = currentYear + 2;   // 2 years ahead
        
        yearSelect.innerHTML = ''; // Clear existing options
        
        for (let year = startYear; year <= endYear; year++) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearSelect.appendChild(option);
        }
        
        // Set current year as default
        yearSelect.value = currentYear;
    }
    
    /**
     * Handle analyze button click based on current mode
     */
    function handleAnalyzeButtonClick() {
        if (currentMode === 'weekly') {
            analyzeSelectedReport();
        } else {
            analyzeMonthlyPerformance();
        }
    }
    
    /**
     * Analyze monthly performance for selected employee, year, and month
     */
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
            // Submit monthly analysis request
            const taskData = await analysisApi.analyzeMonthlyReports(employeeId, year, month);
            currentTask = taskData.task_id;
            console.log('Monthly analysis task created:', taskData);
            
            // If already complete (existing analysis), get results immediately
            const resultData = taskData.is_complete
                ? await taskApi.getTaskResult(taskData.task_id)
                : await TaskManager.pollTaskUntilComplete(taskData.task_id, {
                    onStatusUpdate: updateLoadingStatus,
                    initialDelay: 2000, // Start with 2 seconds since monthly analyses take longer
                    maxDelay: 15000     // Max 15 seconds between polls
                });
            
            if (resultData.error_message) {
                throw new Error(resultData.error_message);
            }
            
            displayMonthlyAnalysisResults(resultData.result);
            showMessage('Monthly analysis completed successfully', 'success');
            
            // Update URL without reload to include parameters
            if (window.history && window.history.pushState) {
                const url = new URL(window.location.href);
                url.searchParams.set('employee_id', employeeId);
                url.searchParams.set('year', year);
                url.searchParams.set('month', month);
                url.searchParams.set('mode', 'monthly');
                url.searchParams.set('auto_analyze', 'false');
                window.history.pushState(
                    {mode: 'monthly', employee_id: employeeId, year: year, month: month},
                    '',
                    url.toString()
                );
            }
        } catch (error) {
            console.error('Error analyzing monthly performance:', error);
            showMessage('Analysis failed: ' + error.message, 'error');
        } finally {
            currentTask = null;
            showLoading(false);
        }
    }
    
    /**
     * Display monthly analysis results with enhanced visualizations
     */
    function displayMonthlyAnalysisResults(data) {
        // Clear previous results
        analysisResults.innerHTML = '';
        
        console.log("Monthly analysis data received:", data);
        
        // Extract data from monthly analysis result
        const { 
            monthly_summary,
            progress_trends,
            monthly_achievements,
            recurring_challenges,
            consistency_assessment,
            growth_indicators,
            focus_areas,
            monthly_risk_assessment,
            strategic_recommendations
        } = data;
        
        // Create main analysis container
        const mainContainer = document.createElement('div');
        mainContainer.className = 'analysis-container';
        
        // Add header
        const header = document.createElement('div');
        header.className = 'analysis-header';
        
        // Create header with title and period
        const headerTitle = document.createElement('h3');
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December'];
        const monthName = monthNames[parseInt(data.month) - 1] || data.month;
        headerTitle.textContent = `Monthly Analysis: ${monthName} ${data.year}`;
        header.appendChild(headerTitle);
        
        // Create meta info row for trends and risk
        const metaInfo = document.createElement('div');
        metaInfo.className = 'analysis-meta';
        
        // Create visual badges for key trends
        const createTrendBadge = (label, value, trendType, tooltip) => {
            const badge = document.createElement('div');
            badge.className = `trend-badge trend-${value.toLowerCase()}`;
            badge.innerHTML = `<strong>${label}:</strong> ${value}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">${tooltip}</span></span>`;
            return badge;
        };
        
        // Add performance trend badge
        metaInfo.appendChild(createTrendBadge(
            'Performance', 
            progress_trends.performance_trend,
            'performance',
            'Overall trend in employee\'s performance during the month.'
        ));
        
        // Add sentiment trend badge
        metaInfo.appendChild(createTrendBadge(
            'Sentiment', 
            progress_trends.sentiment_trend,
            'sentiment',
            'Trend in the emotional tone of the employee\'s reports during the month.'
        ));
        
        // Add risk level badge with tooltip
        metaInfo.appendChild(createTrendBadge(
            'Risk', 
            monthly_risk_assessment.overall_risk_level,
            'risk',
            'Overall assessment of concerns requiring management attention for the month.'
        ));
        
        // Add challenge resolution badge
        metaInfo.appendChild(createTrendBadge(
            'Challenge Resolution', 
            progress_trends.challenge_resolution_progress,
            'resolution',
            'Progress in resolving challenges identified earlier in the month.'
        ));
        
        header.appendChild(metaInfo);
        mainContainer.appendChild(header);
        
        // Add monthly summary section - styled as a highlight
        const summarySection = document.createElement('div');
        summarySection.className = 'monthly-summary';
        summarySection.innerHTML = `<p>${monthly_summary}</p>`;
        mainContainer.appendChild(summarySection);
        
        // Create expandable section component
        const createExpandableSection = (title, content, iconClass, tooltip) => {
            const section = document.createElement('div');
            section.className = 'analysis-section expandable-section';
            
            const sectionHeader = document.createElement('div');
            sectionHeader.className = 'section-header';
            sectionHeader.innerHTML = `
                <h5>
                    <i class="fas ${iconClass}"></i> ${title}
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">${tooltip}</span>
                    </span>
                    <span class="expand-toggle"><i class="fas fa-chevron-down"></i></span>
                </h5>
            `;
            
            const sectionContent = document.createElement('div');
            sectionContent.className = 'section-content';
            sectionContent.appendChild(content);
            
            section.appendChild(sectionHeader);
            section.appendChild(sectionContent);
            
            // Add click event to toggle expansion
            sectionHeader.addEventListener('click', () => {
                section.classList.toggle('expanded');
                const toggleIcon = sectionHeader.querySelector('.expand-toggle i');
                toggleIcon.classList.toggle('fa-chevron-down');
                toggleIcon.classList.toggle('fa-chevron-up');
            });
            
            return section;
        };
        
        // Add progress trends visualization
        const trendsContent = document.createElement('div');
        trendsContent.className = 'trends-visualization';
        
        // Create trend visualization with visual indicators
        const createTrendVisualization = (label, value, type) => {
            const trendItem = document.createElement('div');
            trendItem.className = 'trend-item';
            
            // Determine appropriate icon and class based on trend value
            let iconClass = '';
            let trendClass = '';
            
            if (type === 'performance' || type === 'sentiment') {
                if (value === 'improving') {
                    iconClass = 'fa-arrow-up';
                    trendClass = 'trend-improving';
                } else if (value === 'declining') {
                    iconClass = 'fa-arrow-down';
                    trendClass = 'trend-declining';
                } else {
                    iconClass = 'fa-equals';
                    trendClass = 'trend-stable';
                }
            } else if (type === 'risk') {
                if (value === 'increasing') {
                    iconClass = 'fa-arrow-up';
                    trendClass = 'trend-declining'; // Increasing risk is negative
                } else if (value === 'decreasing') {
                    iconClass = 'fa-arrow-down';
                    trendClass = 'trend-improving'; // Decreasing risk is positive
                } else {
                    iconClass = 'fa-equals';
                    trendClass = 'trend-stable';
                }
            } else if (type === 'resolution') {
                if (value === 'improved') {
                    iconClass = 'fa-check-circle';
                    trendClass = 'trend-improving';
                } else if (value === 'declined') {
                    iconClass = 'fa-times-circle';
                    trendClass = 'trend-declining';
                } else {
                    iconClass = 'fa-minus-circle';
                    trendClass = 'trend-stable';
                }
            }
            
            trendItem.innerHTML = `
                <div class="trend-label">${label}:</div>
                <div class="trend-value ${trendClass}">
                    <i class="fas ${iconClass}"></i> ${value}
                </div>
            `;
            
            return trendItem;
        };
        
        // Add all trend visualizations
        trendsContent.appendChild(createTrendVisualization('Performance Trend', progress_trends.performance_trend, 'performance'));
        trendsContent.appendChild(createTrendVisualization('Sentiment Trend', progress_trends.sentiment_trend, 'sentiment'));
        trendsContent.appendChild(createTrendVisualization('Risk Level Pattern', progress_trends.risk_level_pattern, 'risk'));
        trendsContent.appendChild(createTrendVisualization('Challenge Resolution', progress_trends.challenge_resolution_progress, 'resolution'));
        
        // Add trends section to container
        mainContainer.appendChild(createExpandableSection(
            'Progress Trends', 
            trendsContent, 
            'fa-chart-line',
            'Trends in the employee\'s progress across the month.'
        ));
        
        // Add monthly achievements visualization
        if (monthly_achievements && monthly_achievements.length > 0) {
            const achievementsContent = document.createElement('div');
            achievementsContent.className = 'achievements-visualization';
            
            // Sort achievements by impact in descending order
            const sortedAchievements = [...monthly_achievements].sort((a, b) => {
                // Extract numeric impact value
                const getImpactValue = (str) => {
                    if (!str || typeof str !== 'string') return 0;
                    const match = str.match(/^(\d+)/);
                    return match ? parseInt(match[1]) : 0;
                };
                
                return getImpactValue(b.impact) - getImpactValue(a.impact);
            });
            
            // Create a special highlight for top achievement
            if (sortedAchievements.length > 0) {
                const topAchievement = sortedAchievements[0];
                const topAchievementEl = document.createElement('div');
                topAchievementEl.className = 'top-achievement';
                
                // Extract numeric impact for visualization
                const impactValue = parseInt(topAchievement.impact.split(' ')[0]) || 5;
                const impactWidth = (impactValue / 10) * 100; // Convert to percentage for visual bar
                
                topAchievementEl.innerHTML = `
                    <div class="achievement-header">
                        <span class="trophy-icon"><i class="fas fa-trophy"></i></span>
                        <span class="top-achievement-label">Top Achievement</span>
                    </div>
                    <div class="achievement-description">${topAchievement.description}</div>
                    <div class="achievement-impact-container">
                        <div class="impact-label">Impact: ${topAchievement.impact}</div>
                        <div class="impact-bar-container">
                            <div class="impact-bar" style="width: ${impactWidth}%"></div>
                        </div>
                    </div>
                `;
                
                achievementsContent.appendChild(topAchievementEl);
            }
            
            // Add remaining achievements
            const achievementsList = document.createElement('ul');
            achievementsList.className = 'achievements-list';
            
            // Skip the first one if we have a top achievement
            const startIndex = sortedAchievements.length > 0 ? 1 : 0;
            
            for (let i = startIndex; i < sortedAchievements.length; i++) {
                const achievement = sortedAchievements[i];
                const achievementItem = document.createElement('li');
                achievementItem.className = 'monthly-achievement-item';
                
                // Extract numeric impact for visualization
                const impactValue = parseInt(achievement.impact.split(' ')[0]) || 5;
                const impactClass = impactValue >= 8 ? 'high-impact' : 
                                  impactValue >= 5 ? 'medium-impact' : 'low-impact';
                
                achievementItem.innerHTML = `
                    <div class="achievement-description">${achievement.description}</div>
                    <div class="achievement-impact ${impactClass}">
                        Impact: ${achievement.impact}
                        <span class="tooltip-trigger">
                            <i class="fas fa-question-circle"></i>
                            <span class="tooltip">Impact ratings range from 1-10, where 10 represents the highest impact and 1 represents minimal impact.</span>
                        </span>
                    </div>
                `;
                
                achievementsList.appendChild(achievementItem);
            }
            
            achievementsContent.appendChild(achievementsList);
            
            // Add achievements section to container
            mainContainer.appendChild(createExpandableSection(
                'Key Monthly Achievements',
                achievementsContent,
                'fa-award',
                'The most significant achievements across the entire month.'
            ));
        }
        
        // Add recurring challenges visualization
        if (recurring_challenges && recurring_challenges.length > 0) {
            const challengesContent = document.createElement('div');
            challengesContent.className = 'challenges-visualization';
            
            // Group challenges by status
            const ongoingChallenges = recurring_challenges.filter(c => c.status === 'ongoing' || c.status === 'worsening');
            const resolvedChallenges = recurring_challenges.filter(c => c.status === 'resolved' || c.status === 'addressed');
            
            // Create tabbed interface for challenges
            const challengeTabs = document.createElement('div');
            challengeTabs.className = 'challenge-tabs';
            challengeTabs.innerHTML = `
                <button class="tab-button active" data-tab="ongoing">Ongoing Challenges (${ongoingChallenges.length})</button>
                <button class="tab-button" data-tab="resolved">Resolved Challenges (${resolvedChallenges.length})</button>
            `;
            
            const challengeTabContent = document.createElement('div');
            challengeTabContent.className = 'tab-content';
            
            // Create ongoing challenges tab
            const ongoingTab = document.createElement('div');
            ongoingTab.className = 'tab-pane active';
            ongoingTab.dataset.tab = 'ongoing';
            
            // Create resolved challenges tab
            const resolvedTab = document.createElement('div');
            resolvedTab.className = 'tab-pane';
            resolvedTab.dataset.tab = 'resolved';
            
            // Create challenge list for ongoing challenges
            if (ongoingChallenges.length > 0) {
                const ongoingList = document.createElement('ul');
                ongoingList.className = 'challenges-list';
                
                ongoingChallenges.forEach(challenge => {
                    const challengeItem = document.createElement('li');
                    challengeItem.className = 'recurring-challenge-item';
                    
                    const severityClass = `severity-${challenge.severity}`;
                    const statusClass = challenge.status === 'worsening' ? 'status-worsening' : 'status-ongoing';
                    
                    challengeItem.innerHTML = `
                        <div class="challenge-description">
                            <span class="challenge-severity ${severityClass}">
                                <i class="fas fa-exclamation-${challenge.severity === 'high' ? 'triangle' : 'circle'}"></i>
                            </span>
                            ${challenge.description}
                        </div>
                        <div class="challenge-meta">
                            <span class="severity ${severityClass}">
                                ${challenge.severity.charAt(0).toUpperCase() + challenge.severity.slice(1)} Severity
                            </span>
                            <span class="status ${statusClass}">
                                <i class="fas ${challenge.status === 'worsening' ? 'fa-arrow-up' : 'fa-clock'}"></i>
                                ${challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1)}
                            </span>
                        </div>
                    `;
                    
                    ongoingList.appendChild(challengeItem);
                });
                
                ongoingTab.appendChild(ongoingList);
            } else {
                ongoingTab.innerHTML = '<div class="empty-state">No ongoing challenges</div>';
            }
            
            // Create challenge list for resolved challenges
            if (resolvedChallenges.length > 0) {
                const resolvedList = document.createElement('ul');
                resolvedList.className = 'challenges-list';
                
                resolvedChallenges.forEach(challenge => {
                    const challengeItem = document.createElement('li');
                    challengeItem.className = 'recurring-challenge-item resolved';
                    
                    challengeItem.innerHTML = `
                        <div class="challenge-description">
                            <span class="challenge-status">
                                <i class="fas fa-check-circle"></i>
                            </span>
                            ${challenge.description}
                        </div>
                        <div class="challenge-meta">
                            <span class="status status-resolved">
                                <i class="fas fa-check"></i>
                                ${challenge.status.charAt(0).toUpperCase() + challenge.status.slice(1)}
                            </span>
                        </div>
                    `;
                    
                    resolvedList.appendChild(resolvedItem);
                });
                
                resolvedTab.appendChild(resolvedList);
            } else {
                resolvedTab.innerHTML = '<div class="empty-state">No resolved challenges</div>';
            }
            
            // Add tabs and content to challenges visualization
            challengeTabContent.appendChild(ongoingTab);
            challengeTabContent.appendChild(resolvedTab);
            challengesContent.appendChild(challengeTabs);
            challengesContent.appendChild(challengeTabContent);
            
            // Add tab switching functionality
            challengeTabs.addEventListener('click', (e) => {
                if (e.target.classList.contains('tab-button')) {
                    const tabName = e.target.dataset.tab;
                    
                    // Update active tab button
                    challengeTabs.querySelectorAll('.tab-button').forEach(btn => {
                        btn.classList.toggle('active', btn.dataset.tab === tabName);
                    });
                    
                    // Update active tab pane
                    challengeTabContent.querySelectorAll('.tab-pane').forEach(pane => {
                        pane.classList.toggle('active', pane.dataset.tab === tabName);
                    });
                }
            });
            
            // Add challenges section to container
            mainContainer.appendChild(createExpandableSection(
                'Recurring Challenges',
                challengesContent,
                'fa-exclamation-circle',
                'Challenges that appeared multiple times across the month.'
            ));
        }
        
        // Add consistency assessment visualization
        const consistencyContent = document.createElement('div');
        consistencyContent.className = 'consistency-visualization';
        
        // Create rating indicator component
        const createRatingIndicator = (label, value, tooltipText) => {
            const indicator = document.createElement('div');
            indicator.className = 'rating-indicator';
            
            const ratingClass = value === 'high' ? 'rating-high' : 
                              value === 'medium' ? 'rating-medium' : 'rating-low';
            
            indicator.innerHTML = `
                <div class="rating-label">${label}</div>
                <div class="rating-value ${ratingClass}">
                    <div class="rating-dots">
                        <span class="dot ${value === 'low' || value === 'medium' || value === 'high' ? 'active' : ''}"></span>
                        <span class="dot ${value === 'medium' || value === 'high' ? 'active' : ''}"></span>
                        <span class="dot ${value === 'high' ? 'active' : ''}"></span>
                    </div>
                    <div class="rating-text">${value.charAt(0).toUpperCase() + value.slice(1)}</div>
                </div>
                <div class="rating-tooltip">
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">${tooltipText}</span>
                    </span>
                </div>
            `;
            
            return indicator;
        };
        
        // Add consistency ratings
        consistencyContent.appendChild(createRatingIndicator(
            'Task Completion Reliability',
            consistency_assessment.task_completion_reliability,
            'How reliable the employee is in completing planned tasks as scheduled.'
        ));
        
        consistencyContent.appendChild(createRatingIndicator(
            'Work Quality Consistency',
            consistency_assessment.work_quality_consistency,
            'How consistent the quality of the employee\'s work remains throughout the month.'
        ));
        
        consistencyContent.appendChild(createRatingIndicator(
            'Performance Stability',
            consistency_assessment.performance_stability,
            'How stable the employee\'s overall performance is week-to-week.'
        ));
        
        // Add strengths and weaknesses
        if (consistency_assessment.notable_strengths && consistency_assessment.notable_strengths.length > 0) {
            const strengthsContainer = document.createElement('div');
            strengthsContainer.className = 'consistency-strengths';
            strengthsContainer.innerHTML = `<h6>Notable Strengths:</h6>`;
            
            const strengthsList = document.createElement('ul');
            consistency_assessment.notable_strengths.forEach(strength => {
                const item = document.createElement('li');
                item.innerHTML = `<i class="fas fa-check-circle"></i> ${strength}`;
                strengthsList.appendChild(item);
            });
            
            strengthsContainer.appendChild(strengthsList);
            consistencyContent.appendChild(strengthsContainer);
        }
        
        if (consistency_assessment.notable_weaknesses && consistency_assessment.notable_weaknesses.length > 0) {
            const weaknessesContainer = document.createElement('div');
            weaknessesContainer.className = 'consistency-weaknesses';
            weaknessesContainer.innerHTML = `<h6>Areas for Improvement:</h6>`;
            
            const weaknessesList = document.createElement('ul');
            consistency_assessment.notable_weaknesses.forEach(weakness => {
                const item = document.createElement('li');
                item.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${weakness}`;
                weaknessesList.appendChild(item);
            });
            
            weaknessesContainer.appendChild(weaknessesList);
            consistencyContent.appendChild(weaknessesContainer);
        }
        
        // Add consistency section to container
        mainContainer.appendChild(createExpandableSection(
            'Performance Consistency',
            consistencyContent,
            'fa-balance-scale',
            'Assessment of employee\'s consistency in performance throughout the month.'
        ));
        
        // Add growth indicators visualization
        const growthContent = document.createElement('div');
        growthContent.className = 'growth-visualization';
        
        // Create change indicator component
        const createChangeIndicator = (label, value, tooltipText) => {
            const indicator = document.createElement('div');
            indicator.className = 'change-indicator';
            
            // Determine appropriate icon and class based on value
            let iconClass = '';
            let changeClass = '';
            
            if (value === 'increased' || value === 'more proactive' || value === 'high') {
                iconClass = 'fa-arrow-up';
                changeClass = 'change-positive';
            } else if (value === 'decreased' || value === 'more reactive' || value === 'low') {
                iconClass = 'fa-arrow-down';
                changeClass = 'change-negative';
            } else {
                iconClass = 'fa-equals';
                changeClass = 'change-neutral';
            }
            
            indicator.innerHTML = `
                <div class="change-label">${label}</div>
                <div class="change-value ${changeClass}">
                    <i class="fas ${iconClass}"></i> ${value}
                </div>
                <div class="change-tooltip">
                    <span class="tooltip-trigger">
                        <i class="fas fa-info-circle"></i>
                        <span class="tooltip">${tooltipText}</span>
                    </span>
                </div>
            `;
            
            return indicator;
        };
        
        // Add growth indicators
        growthContent.appendChild(createChangeIndicator(
            'Task Complexity',
            growth_indicators.complexity_of_tasks,
            'How the complexity of tasks handled by the employee has changed during the month.'
        ));
        
        growthContent.appendChild(createChangeIndicator(
            'Skill Development',
            growth_indicators.skill_development_evidence,
            'Evidence of employee developing new skills or improving existing ones.'
        ));
        
        growthContent.appendChild(createChangeIndicator(
            'Confidence Level',
            growth_indicators.confidence_level_change,
            'How the employee\'s confidence in their work has changed during the month.'
        ));
        
        growthContent.appendChild(createChangeIndicator(
            'Approach to Challenges',
            growth_indicators.approach_to_challenges,
            'How the employee\'s approach to facing challenges has evolved.'
        ));
        
        // Add growth section to container
        mainContainer.appendChild(createExpandableSection(
            'Growth & Development',
            growthContent,
            'fa-seedling',
            'Signs of professional growth observed during the month.'
        ));
        
        // Add focus areas visualization
        if (focus_areas && focus_areas.length > 0) {
            const focusContent = document.createElement('div');
            focusContent.className = 'focus-areas-visualization';
            
            // Create visual representation of focus areas with time investment and priority
            focus_areas.forEach(area => {
                const focusItem = document.createElement('div');
                focusItem.className = 'focus-area-item';
                
                // Determine appropriate classes based on priority and time investment
                const priorityClass = `priority-${area.priority_level}`;
                const timeClass = `time-${area.time_investment}`;
                
                focusItem.innerHTML = `
                    <div class="focus-area-name">
                        <i class="fas fa-project-diagram"></i>
                        ${area.project}
                    </div>
                    <div class="focus-area-meta">
                        <span class="focus-level ${timeClass}">
                            <i class="fas fa-clock"></i> Time: ${area.time_investment}
                        </span>
                        <span class="focus-level ${priorityClass}">
                            <i class="fas fa-flag"></i> Priority: ${area.priority_level}
                        </span>
                    </div>
                `;
                
                focusContent.appendChild(focusItem);
            });
            
            // Add focus areas section to container
            mainContainer.appendChild(createExpandableSection(
                'Key Focus Areas',
                focusContent,
                'fa-bullseye',
                'Main projects and responsibilities the employee focused on during the month.'
            ));
        }
        
        // Add risk assessment visualization
        const riskContent = document.createElement('div');
        riskContent.className = 'risk-assessment-visualization';
        
        // Add risk explanation
        const riskExplanation = document.createElement('div');
        riskExplanation.className = 'risk-explanation';
        riskExplanation.innerHTML = `<p>${monthly_risk_assessment.risk_explanation}</p>`;
        riskContent.appendChild(riskExplanation);
        
        // Add significant risks
        if (monthly_risk_assessment.significant_risks && monthly_risk_assessment.significant_risks.length > 0) {
            const significantRisks = document.createElement('div');
            significantRisks.className = 'risk-section';
            significantRisks.innerHTML = `<h6><i class="fas fa-exclamation-triangle"></i> Significant Risks:</h6>`;
            
            const risksList = document.createElement('ul');
            risksList.className = 'risks-list';
            
            monthly_risk_assessment.significant_risks.forEach(risk => {
                const riskItem = document.createElement('li');
                riskItem.innerHTML = risk;
                risksList.appendChild(riskItem);
            });
            
            significantRisks.appendChild(risksList);
            riskContent.appendChild(significantRisks);
        }
        
        // Add escalating risks with alert styling
        if (monthly_risk_assessment.escalating_risks && monthly_risk_assessment.escalating_risks.length > 0) {
            const escalatingRisks = document.createElement('div');
            escalatingRisks.className = 'risk-section escalating';
            escalatingRisks.innerHTML = `<h6><i class="fas fa-arrow-up"></i> Escalating Risks:</h6>`;
            
            const risksList = document.createElement('ul');
            risksList.className = 'risks-list';
            
            monthly_risk_assessment.escalating_risks.forEach(risk => {
                const riskItem = document.createElement('li');
                riskItem.innerHTML = risk;
                risksList.appendChild(riskItem);
            });
            
            escalatingRisks.appendChild(risksList);
            riskContent.appendChild(escalatingRisks);
        }
        
        // Add risk mitigation recommendations
        if (monthly_risk_assessment.risk_mitigation_recommendations && monthly_risk_assessment.risk_mitigation_recommendations.length > 0) {
            const mitigationRecs = document.createElement('div');
            mitigationRecs.className = 'risk-section mitigation';
            mitigationRecs.innerHTML = `<h6><i class="fas fa-shield-alt"></i> Risk Mitigation Recommendations:</h6>`;
            
            const recsList = document.createElement('ul');
            recsList.className = 'risks-list';
            
            monthly_risk_assessment.risk_mitigation_recommendations.forEach(rec => {
                const recItem = document.createElement('li');
                recItem.innerHTML = rec;
                recsList.appendChild(recItem);
            });
            
            mitigationRecs.appendChild(recsList);
            riskContent.appendChild(mitigationRecs);
        }
        
        // Add risk assessment section to container
        mainContainer.appendChild(createExpandableSection(
            'Risk Assessment',
            riskContent,
            'fa-exclamation-triangle',
            'Assessment of concerns requiring management attention across the month.'
        ));
        
        // Add strategic recommendations visualization
        if (strategic_recommendations && strategic_recommendations.length > 0) {
            const recommendationsContent = document.createElement('div');
            recommendationsContent.className = 'recommendations-visualization';
            
            // Group recommendations by priority
            const highPriorityRecs = strategic_recommendations.filter(r => r.priority === 'high');
            const mediumPriorityRecs = strategic_recommendations.filter(r => r.priority === 'medium');
            const lowPriorityRecs = strategic_recommendations.filter(r => r.priority === 'low');
            
            // Helper function to create recommendation lists
            const createRecommendationList = (recommendations, priorityLabel, priorityClass) => {
                if (recommendations.length === 0) return null;
                
                const container = document.createElement('div');
                container.className = `recommendation-group ${priorityClass}`;
                container.innerHTML = `<h6>${priorityLabel} Priority</h6>`;
                
                const list = document.createElement('ul');
                list.className = 'recommendation-list';
                
                recommendations.forEach(rec => {
                    const item = document.createElement('li');
                    item.className = 'recommendation-item';
                    item.innerHTML = `
                        <div class="recommendation-content">
                            <i class="fas fa-caret-right"></i>
                            ${rec.action}
                        </div>
                    `;
                    list.appendChild(item);
                });
                
                container.appendChild(list);
                return container;
            };
            
            // Add high priority recommendations
            const highPriorityList = createRecommendationList(
                highPriorityRecs, 
                'High', 
                'priority-high'
            );
            if (highPriorityList) recommendationsContent.appendChild(highPriorityList);
            
            // Add medium priority recommendations
            const mediumPriorityList = createRecommendationList(
                mediumPriorityRecs, 
                'Medium', 
                'priority-medium'
            );
            if (mediumPriorityList) recommendationsContent.appendChild(mediumPriorityList);
            
            // Add low priority recommendations
            const lowPriorityList = createRecommendationList(
                lowPriorityRecs, 
                'Low', 
                'priority-low'
            );
            if (lowPriorityList) recommendationsContent.appendChild(lowPriorityList);
            
            // Add recommendations section to container
            mainContainer.appendChild(createExpandableSection(
                'Strategic Recommendations',
                recommendationsContent,
                'fa-lightbulb',
                'Recommended actions based on the monthly analysis.'
            ));
        }
        
        // Add to main results container
        analysisResults.appendChild(mainContainer);
        analysisResults.style.display = 'block';
        
        // Auto-expand the first two sections by default
        const sections = mainContainer.querySelectorAll('.expandable-section');
        if (sections.length > 0) {
            sections[0].classList.add('expanded');
            sections[0].querySelector('.expand-toggle i').classList.remove('fa-chevron-down');
            sections[0].querySelector('.expand-toggle i').classList.add('fa-chevron-up');
            
            if (sections.length > 1) {
                sections[1].classList.add('expanded');
                sections[1].querySelector('.expand-toggle i').classList.remove('fa-chevron-down');
                sections[1].querySelector('.expand-toggle i').classList.add('fa-chevron-up');
            }
        }
        
        // Scroll to the results
        analysisResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Handle browser back/forward navigation
    window.addEventListener('popstate', function(event) {
        // Get current URL parameters after navigation
        const params = new URLSearchParams(window.location.search);
        const mode = params.get('mode');
        const employeeId = params.get('employee_id');
        const reportId = params.get('report_id');
        const year = params.get('year');
        const month = params.get('month');
        const autoAnalyze = params.get('auto_analyze');
        
        // Update UI based on the new URL state
        if (mode === 'monthly') {
            // Switch to monthly mode if not already there
            if (currentMode !== 'monthly') {
                setAnalysisMode('monthly');
                monthlyToggle.checked = true;
            }
            
            // Set employee, year, month if available
            if (employeeId) {
                employeeSelect.value = employeeId;
                
                if (year && yearSelect.querySelector(`option[value="${year}"]`)) {
                    yearSelect.value = year;
                }
                
                if (month) {
                    monthSelect.value = month;
                }
                
                // Trigger analysis if auto_analyze is true
                if (autoAnalyze === 'true' && employeeId && year && month) {
                    analyzeMonthlyPerformance();
                }
            }
        } else {
            // Switch to weekly mode if not already there
            if (currentMode !== 'weekly') {
                setAnalysisMode('weekly');
                weeklyToggle.checked = true;
            }
            
            // Set employee and report if available
            if (employeeId) {
                employeeSelect.value = employeeId;
                
                // Load reports for this employee
                loadReportsForEmployee().then(() => {
                    // Select report if specified
                    if (reportId && reportSelect.querySelector(`option[value="${reportId}"]`)) {
                        reportSelect.value = reportId;
                        toggleAnalyzeButton();
                        
                        // Trigger analysis if auto_analyze is true
                        if (autoAnalyze === 'true' && reportId) {
                            analyzeSelectedReport();
                        }
                    }
                });
            }
        }
    });
    
    // Toggle analyze button based on selection
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
                url.searchParams.set('employee_id', employeeSelect.value);
                url.searchParams.set('mode', 'weekly');
                url.searchParams.set('auto_analyze', 'false');
                window.history.pushState(
                    {mode: 'weekly', report_id: reportId, employee_id: employeeSelect.value},
                    '',
                    url.toString()
                );
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
            performanceBadge.innerHTML = `<strong>Performance:</strong> ${performance_assessment.rating}<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">Overall assessment of employee performance based on task completion, impact, challenge management, and planning quality.</span></span>`;
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
});
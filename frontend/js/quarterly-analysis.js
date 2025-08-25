/**
 * Quarterly Analysis Display Module
 * Handles rendering of quarterly analysis data in the UI
 */

// Self-executing function to create module scope
(function() {
    // Helper function to capitalize first letter
    function capitalizeFirstLetter(string) {
        if (!string) return '';
        return string.charAt(0).toUpperCase() + string.slice(1).toLowerCase();
    }

    // Completely revised helper function to create standardized metric badges with icons
    function createMetricBadge(type, value, tooltip) {
        if (!value) return null;
        
        const badge = document.createElement('div');
        const badgeTypeClass = `${type}-badge`;
        const badgeValueClass = `${type}-${value.toLowerCase().replace(/\s+/g, '-')}`;
        
        badge.className = `quarterly-metric-badge ${badgeTypeClass} ${badgeValueClass}`;
        
        // Define icon based on metric type
        let iconClass = '';
        let metricLabel = '';
        
        switch (type) {
            case 'impact':
                iconClass = 'fa-building';
                metricLabel = 'IMPACT';
                break;
            case 'trend':
                iconClass = 'fa-chart-line';
                metricLabel = 'TREND';
                break;
            case 'risk':
                iconClass = 'fa-exclamation-triangle';
                metricLabel = 'RISK';
                break;
            case 'agility':
                iconClass = 'fa-bolt';
                metricLabel = 'AGILITY';
                break;
            case 'autonomy':
                iconClass = 'fa-user-check';
                metricLabel = 'AUTONOMY';
                break;
            case 'credibility':
                iconClass = 'fa-shield-alt';
                metricLabel = 'CREDIBILITY';
                break;
            case 'vision-alignment':
                iconClass = 'fa-eye';
                metricLabel = 'VISION ALIGNMENT';
                break;
            default:
                iconClass = 'fa-check-circle';
                metricLabel = capitalizeFirstLetter(type.replace(/-/g, ' ')).toUpperCase();
        }
        
        // Create badge header with label and tooltip
        const metricHeader = document.createElement('div');
        metricHeader.className = 'metric-header';
        
        // Add label
        const labelElement = document.createElement('div');
        labelElement.className = 'metric-label';
        labelElement.textContent = metricLabel;
        
        metricHeader.appendChild(labelElement);
        
        // Only add tooltip element if there's tooltip content
        if (tooltip) {
            const tooltipElement = document.createElement('span');
            tooltipElement.className = 'tooltip-trigger';
            tooltipElement.innerHTML = `<span class="tooltip">${tooltip}</span>`;
            metricHeader.appendChild(tooltipElement);
        }
        
        badge.appendChild(metricHeader);
        
        // Create value container with icon and value
        const valueContainer = document.createElement('div');
        valueContainer.className = 'metric-value-container';
        
        // Add icon
        const iconElement = document.createElement('div');
        iconElement.className = 'metric-icon';
        iconElement.innerHTML = `<i class="fas ${iconClass}"></i>`;
        valueContainer.appendChild(iconElement);
        
        // Add value
        const valueElement = document.createElement('div');
        valueElement.className = 'metric-value';
        valueElement.textContent = capitalizeFirstLetter(value);
        valueContainer.appendChild(valueElement);
        
        badge.appendChild(valueContainer);
        
        return badge;
    }

    // Old helper function kept for backward compatibility with other sections
    function createBadge(type, value, tooltip) {
        if (!value) return null;
        
        const badgeClass = `${type}-${value.toLowerCase().replace(/\s+/g, '-')}`;
        
        const badge = document.createElement('div');
        badge.className = `${type} ${badgeClass}`;
        badge.innerHTML = `<strong>${capitalizeFirstLetter(type.replace(/-/g, ' '))}:</strong> ${capitalizeFirstLetter(value)}`;
        
        if (tooltip) {
            badge.innerHTML += `<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">${tooltip}</span></span>`;
        }
        
        return badge;
    }

    // Helper function to safely parse JSON field
    function safelyParseJson(jsonField) {
        if (!jsonField) return null;
        
        if (typeof jsonField === 'string') {
            try {
                return JSON.parse(jsonField);
            } catch (e) {
                console.error('Error parsing JSON:', e);
                return null;
            }
        }
        
        return jsonField; // Already an object
    }
    
    // Add a helper function to ensure tooltips are properly positioned for heading tooltips
    function ensureTooltipVisibility() {
        // Select all tooltip triggers
        const tooltipTriggers = document.querySelectorAll('.tooltip-trigger');
        
        // Add a small delay to ensure DOM is fully rendered
        setTimeout(() => {
            tooltipTriggers.forEach(trigger => {
                const tooltip = trigger.querySelector('.tooltip');
                if (tooltip) {
                    // Skip tooltip repositioning for quarterly summary section
                    if (trigger.closest('.quarterly-summary-section')) {
                        return;
                    }
                    
                    // Ensure tooltip is not clipped by viewport top
                    const triggerRect = trigger.getBoundingClientRect();
                    const tooltipHeight = tooltip.offsetHeight;
                    
                    // If trigger is too close to the top of viewport, position tooltip below instead
                    if (triggerRect.top < tooltipHeight + 20) {
                        tooltip.style.bottom = 'auto';
                        tooltip.style.top = '125%';
                        
                        // Move the arrow to the top
                        tooltip.classList.add('tooltip-bottom');
                    }
                }
            });
        }, 500);
    }

    // Helper function to create a card-based component
    function createCard(className, title, content) {
        const card = document.createElement('div');
        card.className = className;
        
        if (title) {
            const heading = document.createElement('h6');
            heading.textContent = title;
            card.appendChild(heading);
        }
        
        if (content) {
            if (typeof content === 'string') {
                const paragraph = document.createElement('p');
                paragraph.textContent = content;
                card.appendChild(paragraph);
            } else {
                card.appendChild(content);
            }
        }
        
        return card;
    }

    // Display quarterly analysis results
    function displayQuarterlyAnalysisResults(data) {
        // Clear previous results
        const analysisResults = document.getElementById('analysisResults');
        analysisResults.innerHTML = '';
        
        console.log("Full quarterly analysis data received:", data);
        
        // Format quarter name
        const quarterName = `Q${data.quarter}`;
        
        // Create main analysis container
        const mainContainer = document.createElement('div');
        mainContainer.className = 'quarterly-container';
        
        // Add header
        const header = document.createElement('div');
        header.className = 'quarterly-header';
        
        // Create header with title
        const headerTitle = document.createElement('h3');
        headerTitle.textContent = `Quarterly Analysis: ${quarterName} ${data.year}`;
        header.appendChild(headerTitle);
        
        // Create meta info row
        const metaInfo = document.createElement('div');
        metaInfo.className = 'quarterly-meta';
        
        // // Add organizational impact badge using the new standardized badge system
        // if (data.organizational_impact) {
        //     const impactBadge = createMetricBadge('impact', data.organizational_impact, 
        //         "Scope of employee's impact within the organization: individual, team, department, or organization-wide.");
        //     metaInfo.appendChild(impactBadge);
        // }
        
        // // Add performance trend badge using the new standardized badge system
        // if (data.performance_trend) {
        //     const performanceTrendBadge = createMetricBadge('trend', data.performance_trend,
        //         "Overall trend in employee's performance throughout the quarter.");
        //     metaInfo.appendChild(performanceTrendBadge);
        // }
        
        // // Add risk level badge using the new standardized badge system
        // if (data.risk_level) {
        //     const riskBadge = createMetricBadge('risk', data.risk_level,
        //         "Overall risk assessment based on recurring challenges, performance stability, and emerging issues.");
        //     metaInfo.appendChild(riskBadge);
        // }
        
        // // Add risk trend badge using the new standardized badge system
        // if (data.risk_trend) {
        //     const riskTrendBadge = createMetricBadge('trend', data.risk_trend,
        //         "Direction of risk level changes throughout the quarter.");
        //     metaInfo.appendChild(riskTrendBadge);
        // }
        
        // // Add learning agility badge using the new standardized badge system
        // if (data.learning_agility) {
        //     const agilityBadge = createMetricBadge('agility', data.learning_agility,
        //         "Employee's demonstrated ability to learn and adapt to new situations.");
        //     metaInfo.appendChild(agilityBadge);
        // }
        
        // // Add autonomy level badge using the new standardized badge system
        // if (data.autonomy_level) {
        //     const autonomyBadge = createMetricBadge('autonomy', data.autonomy_level,
        //         "Level of independence the employee demonstrates in their work.");
        //     metaInfo.appendChild(autonomyBadge);
        // }
        
        // // Add credibility rating badge if available using the new standardized badge system
        // if (data.credibility_rating) {
        //     const credibilityBadge = createMetricBadge('credibility', data.credibility_rating,
        //         "Assessment of how well-supported the claims and achievements are with evidence.");
        //     metaInfo.appendChild(credibilityBadge);
        // }
        
        // // Add vision data alignment badge if available using the new standardized badge system
        // if (data.vision_data_alignment) {
        //     const visionAlignmentBadge = createMetricBadge('vision-alignment', data.vision_data_alignment,
        //         "How well employee's activities align with their stated vision and goals.");
        //     metaInfo.appendChild(visionAlignmentBadge);
        // }
        
        // header.appendChild(metaInfo);
        mainContainer.appendChild(header);
        
        // Add quarterly summary section
        if (data.quarterly_summary) {
            const summarySection = document.createElement('div');
            summarySection.className = 'quarterly-section quarterly-summary-section';
            
            summarySection.innerHTML = `<h5>Quarterly Summary
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Executive summary of the employee's performance over the quarter.</span>
                </span>
            </h5>`;
            
            // Create the content container with the new styling
            const summaryContent = document.createElement('div');
            summaryContent.className = 'summary-content';
            
            // Add the paragraph with summary text
            const summaryParagraph = document.createElement('p');
            summaryParagraph.textContent = data.quarterly_summary;
            
            summaryContent.appendChild(summaryParagraph);
            summarySection.appendChild(summaryContent);
            mainContainer.appendChild(summarySection);
        }
        
        // Add strategic alignment section
        const strategicAlignmentData = safelyParseJson(data.strategic_alignment_json) || data.strategic_alignment;
        if (strategicAlignmentData) {
            const alignmentSection = document.createElement('div');
            alignmentSection.className = 'quarterly-section strategic-alignment-section';
            
            alignmentSection.innerHTML = `<h5>Strategic Alignment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Assessment of how the employee's work aligns with organizational goals.</span>
                </span>
            </h5>`;
            
            // Add key initiatives if available
            const initiatives = strategicAlignmentData.key_initiatives || [];
            if (initiatives.length > 0) {
                const initiativesTitle = document.createElement('h6');
                initiativesTitle.textContent = 'Key Strategic Initiatives';
                alignmentSection.appendChild(initiativesTitle);
                
                // Create card grid for initiatives
                const initiativesGrid = document.createElement('div');
                initiativesGrid.className = 'initiatives-grid';
                
                initiatives.forEach(initiative => {
                    // Create initiative card
                    const initiativeCard = document.createElement('div');
                    initiativeCard.className = 'initiative-card';
                    
                    // Add initiative name/title
                    const initiativeName = document.createElement('h6');
                    initiativeName.textContent = initiative.initiative || initiative.name || initiative;
                    initiativeCard.appendChild(initiativeName);
                    
                    // Add outcomes if available - moved to top for better alignment
                    if (initiative.outcomes) {
                        const outcome = document.createElement('div');
                        outcome.className = 'initiative-outcome';
                        outcome.innerHTML = `<strong>Outcomes:</strong> ${initiative.outcomes}`;
                        initiativeCard.appendChild(outcome);
                    }
                    
                    // Add description if available
                    if (initiative.description) {
                        const description = document.createElement('p');
                        description.className = 'initiative-description';
                        description.textContent = initiative.description;
                        initiativeCard.appendChild(description);
                    }
                    
                    // Add alignment rating if available
                    if (initiative.alignment) {
                        const alignmentEl = document.createElement('div');
                        alignmentEl.className = `alignment-rating alignment-${initiative.alignment.toLowerCase()}`;
                        alignmentEl.textContent = `Alignment: ${capitalizeFirstLetter(initiative.alignment)}`;
                        initiativeCard.appendChild(alignmentEl);
                    }
                    
                    initiativesGrid.appendChild(initiativeCard);
                });
                
                alignmentSection.appendChild(initiativesGrid);
            }
            
            // Add organizational impact if available - styled to match screenshot
            if (strategicAlignmentData.organizational_impact || data.organizational_impact) {
                const impactValue = strategicAlignmentData.organizational_impact || data.organizational_impact;
                const impactDisplay = document.createElement('div');
                impactDisplay.className = 'organizational-impact';
                impactDisplay.innerHTML = `<i class="fas fa-building"></i> <strong>Organizational Impact Level:</strong> ${capitalizeFirstLetter(impactValue)}`;
                alignmentSection.appendChild(impactDisplay);
            }
            
            mainContainer.appendChild(alignmentSection);
        }
        
        // Add achievement themes section
        const achievementThemesData = safelyParseJson(data.achievement_themes_json) || data.achievement_themes;
        if (achievementThemesData && achievementThemesData.length > 0) {
            const themesSection = document.createElement('div');
            themesSection.className = 'quarterly-section achievement-themes-section';
            
            themesSection.innerHTML = `<h5>Achievement Themes
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Major themes in employee's achievements throughout the quarter.</span>
                </span>
            </h5>`;
            
            const themesContainer = document.createElement('div');
            themesContainer.className = 'themes-container';
            
            achievementThemesData.forEach(theme => {
                const themeItem = document.createElement('div');
                themeItem.className = 'achievement-theme';
                
                // Create theme header
                const themeHeader = document.createElement('h6');
                
                // Add the 'has-verification' class if the theme is verified
                if (theme.vision_verified) {
                    themeHeader.className = 'has-verification';
                }
                
                // Create a span for the title text to allow wrapping
                const titleTextSpan = document.createElement('span');
                titleTextSpan.className = 'theme-title-text';
                titleTextSpan.textContent = theme.theme || theme.name || 'Achievement Theme';
                themeHeader.appendChild(titleTextSpan);
                
                // If the theme is verified, add the badge to the header
                if (theme.vision_verified) {
                    const verifiedBadge = document.createElement('span');
                    verifiedBadge.className = 'vision-verified-badge';
                    verifiedBadge.innerHTML = '<i class="fas fa-check-circle"></i>Verified';
                    themeHeader.appendChild(verifiedBadge);
                }
                
                themeItem.appendChild(themeHeader);
                
                // Add theme description if available
                if (theme.description) {
                    const themeDesc = document.createElement('p');
                    themeDesc.className = 'theme-description';
                    themeDesc.textContent = theme.description;
                    themeItem.appendChild(themeDesc);
                }
                
                // Add related achievements if available
                if (theme.related_achievements || theme.achievements) {
                    const achievements = theme.related_achievements || theme.achievements;
                    if (achievements && achievements.length > 0) {
                        const achievementsList = document.createElement('ul');
                        achievementsList.className = 'theme-achievements';
                        
                        achievements.forEach(achievement => {
                            const achievementItem = document.createElement('li');
                            achievementItem.textContent = typeof achievement === 'string' ? achievement : achievement.description || JSON.stringify(achievement);
                            achievementsList.appendChild(achievementItem);
                        });
                        
                        themeItem.appendChild(achievementsList);
                    }
                }
                
                // Add impact if available
                if (theme.impact) {
                    const impactText = document.createElement('div');
                    impactText.className = 'theme-impact';
                    impactText.innerHTML = `<strong>Impact:</strong> ${theme.impact}`;
                    themeItem.appendChild(impactText);
                }
                
                // Add business outcome if available
                if (theme.business_outcome) {
                    const outcomeText = document.createElement('div');
                    outcomeText.className = 'theme-business-outcome';
                    outcomeText.innerHTML = `<strong>Outcome:</strong> ${theme.business_outcome}`;
                    themeItem.appendChild(outcomeText);
                }
                
                themesContainer.appendChild(themeItem);
            });
            
            themesSection.appendChild(themesContainer);
            mainContainer.appendChild(themesSection);
        }
        
        // Add performance trajectory section
        const trajectoryData = safelyParseJson(data.performance_trajectory_json) || data.performance_trajectory;
        if (trajectoryData || data.task_completion_reliability || data.work_quality_consistency || data.performance_stability) {
            const trajectorySection = document.createElement('div');
            trajectorySection.className = 'quarterly-section performance-trajectory-section';
            
            trajectorySection.innerHTML = `<h5>Performance Trajectory
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Analysis of performance trends and consistency throughout the quarter.</span>
                </span>
            </h5>`;
            
            // Add consistency metrics if available from either flattened fields or nested structure
            const consistencyData = trajectoryData?.consistency || {
                task_completion_reliability: data.task_completion_reliability,
                work_quality_consistency: data.work_quality_consistency,
                performance_stability: data.performance_stability
            };
            
            if (consistencyData.task_completion_reliability || 
                consistencyData.work_quality_consistency || 
                consistencyData.performance_stability) {
                
                const consistencyTitle = document.createElement('h6');
                consistencyTitle.textContent = 'Performance Consistency';
                trajectorySection.appendChild(consistencyTitle);
                
                // Add overall trend metric if available in a separate, centered container
                if (trajectoryData && trajectoryData.trend) {
                    const trendContainer = document.createElement('div');
                    trendContainer.className = 'overall-trend-container';
                    
                    const trendMetric = document.createElement('div');
                    trendMetric.className = 'metric';
                    
                    const metricName = document.createElement('div');
                    metricName.className = 'metric-name performance-trend';
                    metricName.textContent = 'Overall Trend';
                    
                    const metricValue = document.createElement('div');
                    metricValue.className = `metric-value ${trajectoryData.trend.toLowerCase()}`;
                    
                    // Add appropriate icon based on trend
                    let trendIcon = '';
                    if (trajectoryData.trend.toLowerCase() === 'improving') {
                        trendIcon = '<i class="fas fa-arrow-up"></i> ';
                    } else if (trajectoryData.trend.toLowerCase() === 'declining') {
                        trendIcon = '<i class="fas fa-arrow-down"></i> ';
                    } else if (trajectoryData.trend.toLowerCase() === 'stable') {
                        trendIcon = '<i class="fas fa-equals"></i> ';
                    } else {
                        trendIcon = '<i class="fas fa-random"></i> '; // For 'mixed'
                    }
                    
                    metricValue.innerHTML = trendIcon + capitalizeFirstLetter(trajectoryData.trend);
                    
                    trendMetric.appendChild(metricName);
                    trendMetric.appendChild(metricValue);
                    trendContainer.appendChild(trendMetric);
                    
                    trajectorySection.appendChild(trendContainer);
                }
                
                // Create metrics grid for consistency indicators
                const metricsGrid = document.createElement('div');
                metricsGrid.className = 'metrics-grid';
                
                // No longer add the trend metric to the grid - it's now in its own container above
                
                // Add each available metric
                if (consistencyData.task_completion_reliability) {
                    const reliabilityMetric = document.createElement('div');
                    reliabilityMetric.className = 'metric';
                    
                    const metricName = document.createElement('div');
                    metricName.className = 'metric-name task-completion';
                    metricName.style.textAlign = 'center';
                    metricName.textContent = 'Task Completion';
                    
                    const metricValue = document.createElement('div');
                    metricValue.className = `metric-value ${consistencyData.task_completion_reliability.toLowerCase()}`;
                    metricValue.textContent = capitalizeFirstLetter(consistencyData.task_completion_reliability);
                    
                    reliabilityMetric.appendChild(metricName);
                    reliabilityMetric.appendChild(metricValue);
                    metricsGrid.appendChild(reliabilityMetric);
                }
                
                if (consistencyData.work_quality_consistency) {
                    const qualityMetric = document.createElement('div');
                    qualityMetric.className = 'metric';
                    
                    const metricName = document.createElement('div');
                    metricName.className = 'metric-name work-quality';
                    metricName.style.textAlign = 'center';
                    metricName.textContent = 'Work Quality';
                    
                    const metricValue = document.createElement('div');
                    metricValue.className = `metric-value ${consistencyData.work_quality_consistency.toLowerCase()}`;
                    metricValue.textContent = capitalizeFirstLetter(consistencyData.work_quality_consistency);
                    
                    qualityMetric.appendChild(metricName);
                    qualityMetric.appendChild(metricValue);
                    metricsGrid.appendChild(qualityMetric);
                }
                
                if (consistencyData.performance_stability) {
                    const stabilityMetric = document.createElement('div');
                    stabilityMetric.className = 'metric';
                    
                    const metricName = document.createElement('div');
                    metricName.className = 'metric-name performance-stability';
                    metricName.style.textAlign = 'center';
                    metricName.textContent = 'Performance Stability';
                    
                    const metricValue = document.createElement('div');
                    metricValue.className = `metric-value ${consistencyData.performance_stability.toLowerCase()}`;
                    metricValue.textContent = capitalizeFirstLetter(consistencyData.performance_stability);
                    
                    stabilityMetric.appendChild(metricName);
                    stabilityMetric.appendChild(metricValue);
                    metricsGrid.appendChild(stabilityMetric);
                }
                
                trajectorySection.appendChild(metricsGrid);
            }
            
            // Add notable shifts if available
            if (trajectoryData && trajectoryData.notable_shifts && trajectoryData.notable_shifts.length > 0) {
                const shiftsContainer = document.createElement('div');
                shiftsContainer.className = 'notable-shifts';
                
                const shiftsTitle = document.createElement('h6');
                shiftsTitle.textContent = 'Notable Performance Shifts';
                shiftsContainer.appendChild(shiftsTitle);
                
                // Create a timeline container instead of a list
                const timelineContainer = document.createElement('div');
                timelineContainer.className = 'shifts-timeline-container';
                
                // Create the timeline element
                const timeline = document.createElement('div');
                timeline.className = 'shifts-timeline';
                
                // Get months in the quarter
                const quarterMonths = ["January", "February", "March", "April", "May", "June", 
                                       "July", "August", "September", "October", "November", "December"];
                const quarterStart = (data.quarter - 1) * 3;
                const monthsInQuarter = quarterMonths.slice(quarterStart, quarterStart + 3);
                
                // Add month markers to the timeline
                monthsInQuarter.forEach(month => {
                    const monthMarker = document.createElement('div');
                    monthMarker.className = 'timeline-month-marker';
                    
                    const monthLabel = document.createElement('span');
                    monthLabel.className = 'timeline-month-label';
                    monthLabel.textContent = month;
                    
                    monthMarker.appendChild(monthLabel);
                    timeline.appendChild(monthMarker);
                });
                
                // First collect the month data from all shifts to place markers
                const timelineEvents = [];
                
                trajectoryData.notable_shifts.forEach(shift => {
                    let monthText = "";
                    let monthIndex = 0;
                    
                    if (typeof shift === 'string') {
                        // Try to extract month from shift string
                        const monthMatch = shift.match(/^(January|February|March|April|May|June|July|August|September|October|November|December):/i);
                        if (monthMatch) {
                            monthText = monthMatch[1];
                            monthIndex = monthsInQuarter.findIndex(m => m.toLowerCase() === monthText.toLowerCase());
                            if (monthIndex < 0) monthIndex = 0; // Fallback if month is outside quarter
                        } else {
                            monthText = "Unspecified";
                            monthIndex = 1; // Default to middle of quarter
                        }
                    } else {
                        // Handle structured shift data
                        monthText = shift.month || "Unspecified";
                        monthIndex = monthsInQuarter.findIndex(m => m.toLowerCase() === monthText.toLowerCase());
                        if (monthIndex < 0) monthIndex = 1; // Default to middle if not found
                    }
                    
                    // Add to timeline events array
                    timelineEvents.push({
                        monthIndex: monthIndex,
                        position: `${monthIndex / (monthsInQuarter.length - 1) * 100}%`
                    });
                });
                
                // Add event markers to the timeline
                timelineEvents.forEach(event => {
                    const marker = document.createElement('div');
                    marker.className = 'timeline-event-marker';
                    marker.style.left = event.position;
                    timeline.appendChild(marker);
                });
                
                timelineContainer.appendChild(timeline);
                
                // Create and add shift cards 
                const shiftsCardsContainer = document.createElement('div');
                shiftsCardsContainer.className = 'timeline-shifts-container';
                
                trajectoryData.notable_shifts.forEach((shift, index) => {
                    // Create shift card
                    const shiftCard = document.createElement('div');
                    shiftCard.className = 'timeline-shift-card';
                    
                    // Create month badge at the top with calendar icon
                    const monthHeader = document.createElement('div');
                    monthHeader.className = 'shift-month';
                    monthHeader.innerHTML = `<i class="fas fa-calendar-alt"></i> `;
                    
                    // Determine month text and position on timeline
                    let monthText = "";
                    let monthIndex = 0;
                    
                    if (typeof shift === 'string') {
                        // Try to extract month from shift string
                        const monthMatch = shift.match(/^(January|February|March|April|May|June|July|August|September|October|November|December):/i);
                        if (monthMatch) {
                            monthText = monthMatch[1];
                            monthIndex = monthsInQuarter.findIndex(m => m.toLowerCase() === monthText.toLowerCase());
                            if (monthIndex < 0) monthIndex = 0; // Fallback if month is outside quarter
                        } else {
                            monthText = "Unspecified";
                            monthIndex = 1; // Default to middle of quarter
                        }
                    } else {
                        // Handle structured shift data
                        monthText = shift.month || "Unspecified";
                        monthIndex = monthsInQuarter.findIndex(m => m.toLowerCase() === monthText.toLowerCase());
                        if (monthIndex < 0) monthIndex = 1; // Default to middle if not found
                    }
                    
                    // Add month text to header
                    monthHeader.innerHTML += monthText;
                    shiftCard.appendChild(monthHeader);
                    
                    // Store timeline position (used for card grouping) but we don't need visual elements
                    shiftCard.style.setProperty('--timeline-position', `${monthIndex / (monthsInQuarter.length - 1) * 100}%`);
                    
                    // Create enhanced shift content container with better visual hierarchy
                    const shiftContentContainer = document.createElement('div');
                    shiftContentContainer.className = 'shift-content-container';
                    
                    // Determine if this is a positive or negative shift (for styling)
                    let shiftDirection = 'neutral';
                    const descriptionText = typeof shift === 'string' 
                        ? shift 
                        : (shift.description || shift.shift || '');
                        
                    if (descriptionText.toLowerCase().includes('improv') || 
                        descriptionText.toLowerCase().includes('increas') ||
                        descriptionText.toLowerCase().includes('better') ||
                        descriptionText.toLowerCase().includes('higher')) {
                        shiftDirection = 'positive';
                    } else if (descriptionText.toLowerCase().includes('declin') || 
                               descriptionText.toLowerCase().includes('decreas') ||
                               descriptionText.toLowerCase().includes('worse') ||
                               descriptionText.toLowerCase().includes('lower') ||
                               descriptionText.toLowerCase().includes('challeng')) {
                        shiftDirection = 'negative';
                    }
                    
                    // Create performance shift section with icon
                    const shiftSection = document.createElement('div');
                    shiftSection.className = `shift-description-section shift-${shiftDirection}`;
                    
                    // Add icon based on shift direction
                    const directionIcon = document.createElement('div');
                    directionIcon.className = 'shift-direction-icon';
                    if (shiftDirection === 'positive') {
                        directionIcon.innerHTML = '<i class="fas fa-arrow-up"></i>';
                    } else if (shiftDirection === 'negative') {
                        directionIcon.innerHTML = '<i class="fas fa-arrow-down"></i>';
                    } else {
                        directionIcon.innerHTML = '<i class="fas fa-arrows-alt-h"></i>';
                    }
                    shiftSection.appendChild(directionIcon);
                    
                    // Add shift description content
                    const descriptionContent = document.createElement('div');
                    descriptionContent.className = 'shift-description-content';
                    
                    // Add heading
                    const descriptionHeading = document.createElement('div');
                    descriptionHeading.className = 'shift-description-heading';
                    descriptionHeading.textContent = 'Performance Shift';
                    descriptionContent.appendChild(descriptionHeading);
                    
                    // Add the actual description text
                    const descriptionTextEl = document.createElement('div');
                    descriptionTextEl.className = 'shift-description-text';
                    
                    // Extract the text content
                    if (typeof shift === 'string') {
                        const monthMatch = shift.match(/^(January|February|March|April|May|June|July|August|September|October|November|December):/i);
                        if (monthMatch) {
                            descriptionTextEl.textContent = shift.substring(monthMatch[0].length).trim();
                        } else {
                            descriptionTextEl.textContent = shift;
                        }
                    } else {
                        descriptionTextEl.textContent = shift.description || shift.shift || '';
                    }
                    
                    descriptionContent.appendChild(descriptionTextEl);
                    shiftSection.appendChild(descriptionContent);
                    shiftContentContainer.appendChild(shiftSection);
                    
                    // Add factors as a separate section if available
                    if (typeof shift === 'object' && shift.factors) {
                        const factorsSection = document.createElement('div');
                        factorsSection.className = 'shift-factors-section';
                        
                        // Add factors icon
                        const factorsIcon = document.createElement('div');
                        factorsIcon.className = 'shift-factors-icon';
                        factorsIcon.innerHTML = '<i class="fas fa-puzzle-piece"></i>';
                        factorsSection.appendChild(factorsIcon);
                        
                        // Add factors content container
                        const factorsContent = document.createElement('div');
                        factorsContent.className = 'shift-factors-content';
                        
                        // Add factors heading
                        const factorsHeading = document.createElement('div');
                        factorsHeading.className = 'shift-factors-heading';
                        factorsHeading.textContent = 'Contributing Factors';
                        factorsContent.appendChild(factorsHeading);
                        
                        // Process factors text - check if it contains bullet points or multiple lines
                        const factorsText = shift.factors;
                        if (factorsText.includes('\n') || factorsText.includes('•') || factorsText.includes('-')) {
                            // Create a list of factors
                            const factorsList = document.createElement('ul');
                            factorsList.className = 'shift-factors-list';
                            
                            // Improved regex to avoid splitting words containing hyphens
                            // Only split on newlines, bullet points, or lines starting with hyphen+space
                            let factorsItems = [];
                            
                            // First split by newlines
                            const lines = factorsText.split('\n');
                            
                            lines.forEach(line => {
                                line = line.trim();
                                if (!line) return; // Skip empty lines
                                
                                // Check if line starts with bullet or hyphen+space
                                if (line.startsWith('• ') || line.startsWith('- ')) {
                                    factorsItems.push(line.substring(2).trim());
                                } else if (line.startsWith('•') || line.startsWith('-')) {
                                    factorsItems.push(line.substring(1).trim());
                                } else {
                                    // If no bullet/hyphen, treat as a single item
                                    factorsItems.push(line);
                                }
                            });
                            
                            // If we didn't successfully split into multiple items and the text contains
                            // hyphens or bullets in the middle, handle as a single item
                            if (factorsItems.length <= 1 && factorsText.trim().length > 0) {
                                factorsItems = [factorsText.trim()];
                            }
                            
                            factorsItems.forEach(item => {
                                const listItem = document.createElement('li');
                                listItem.textContent = item;
                                factorsList.appendChild(listItem);
                            });
                            
                            factorsContent.appendChild(factorsList);
                        } else {
                            // Just add as plain text
                            const factorsTextElement = document.createElement('div');
                            factorsTextElement.className = 'shift-factors-text';
                            factorsTextElement.textContent = factorsText;
                            factorsContent.appendChild(factorsTextElement);
                        }
                        
                        factorsSection.appendChild(factorsContent);
                        shiftContentContainer.appendChild(factorsSection);
                    }
                    
                    shiftCard.appendChild(shiftContentContainer);
                    
                    // No longer need to create connector
                    // const connector = document.createElement('div');
                    // connector.className = 'timeline-connector';
                    // shiftCard.appendChild(connector);
                    
                    shiftsCardsContainer.appendChild(shiftCard);
                });
                
                timelineContainer.appendChild(shiftsCardsContainer);
                shiftsContainer.appendChild(timelineContainer);
                trajectorySection.appendChild(shiftsContainer);
            }
            
            mainContainer.appendChild(trajectorySection);
        }
        
        // Add cross-functional impact section
        const impactData = safelyParseJson(data.cross_functional_impact_json) || data.cross_functional_impact;
        if (impactData || data.collaboration_effectiveness) {
            const impactSection = document.createElement('div');
            impactSection.className = 'quarterly-section cross-functional-section';
            
            impactSection.innerHTML = `<h5>Cross-Functional Impact
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Employee's impact across teams and departments.</span>
                </span>
            </h5>`;

            // Render stakeholder impacts if available
            const stakeholders = impactData?.stakeholder_impacts || impactData?.stakeholders || [];
            if (stakeholders.length > 0) {
                const stakeholdersTitle = document.createElement('h6');
                stakeholdersTitle.textContent = 'Stakeholder Impacts';
                impactSection.appendChild(stakeholdersTitle);

                const stakeholdersGrid = document.createElement('div');
                stakeholdersGrid.className = 'stakeholders-grid';

                stakeholders.forEach(stakeholder => {
                    const stakeholderCard = document.createElement('div');
                    stakeholderCard.className = 'stakeholder-card';

                    const nameEl = document.createElement('h6');
                    nameEl.textContent = stakeholder.stakeholder || stakeholder.name || stakeholder.title || 'Stakeholder';
                    stakeholderCard.appendChild(nameEl);

                    if (stakeholder.role) {
                        const roleEl = document.createElement('div');
                        roleEl.className = 'stakeholder-role';
                        roleEl.innerHTML = `<strong>Role:</strong> ${stakeholder.role}`;
                        stakeholderCard.appendChild(roleEl);
                    }

                    if (stakeholder.impact || stakeholder.description) {
                        const impactP = document.createElement('p');
                        impactP.textContent = stakeholder.impact || stakeholder.description;
                        stakeholderCard.appendChild(impactP);
                    }

                    if (stakeholder.evidence) {
                        const evidence = document.createElement('div');
                        evidence.className = 'theme-impact';
                        evidence.innerHTML = `<strong>Evidence:</strong> ${stakeholder.evidence}`;
                        stakeholderCard.appendChild(evidence);
                    }

                    stakeholdersGrid.appendChild(stakeholderCard);
                });

                impactSection.appendChild(stakeholdersGrid);
            }
            
            // Add knowledge sharing examples if available
            const knowledgeItems = impactData?.knowledge_sharing || [];
            if (knowledgeItems.length > 0) {
                const knowledgeTitle = document.createElement('h6');
                knowledgeTitle.textContent = 'Knowledge Sharing';
                impactSection.appendChild(knowledgeTitle);
                
                const knowledgeList = document.createElement('ul');
                knowledgeList.className = 'knowledge-sharing-list';
                
                knowledgeItems.forEach(item => {
                    const listItem = document.createElement('li');
                    listItem.textContent = item;
                    knowledgeList.appendChild(listItem);
                });
                
                impactSection.appendChild(knowledgeList);
            }
            
            // Add collaboration effectiveness if available
            const collaborationValue = impactData?.collaboration_effectiveness || data.collaboration_effectiveness;
            if (collaborationValue) {
                const collaborationMetric = document.createElement('div');
                collaborationMetric.className = `collaboration-metric collaboration-${collaborationValue.toLowerCase()}`;
                collaborationMetric.innerHTML = `</i> <strong>Collaboration Effectiveness:</strong> ${capitalizeFirstLetter(collaborationValue)}`;
                impactSection.appendChild(collaborationMetric);
            }
            
            mainContainer.appendChild(impactSection);
        }
        
        // Add challenge patterns section
        const challengeData = safelyParseJson(data.challenge_patterns_json) || data.challenge_patterns;
        if (challengeData && challengeData.recurring_challenges && challengeData.recurring_challenges.length > 0) {
            const challengeSection = document.createElement('div');
            challengeSection.className = 'quarterly-section challenge-patterns-section';
            
            challengeSection.innerHTML = `<h5>Challenge Patterns
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Recurring challenges and patterns in how the employee addresses them.</span>
                </span>
            </h5>`;
            
            // Add recurring challenges
            const challengesTitle = document.createElement('h6');
            challengesTitle.textContent = 'Recurring Challenges';
            challengeSection.appendChild(challengesTitle);
            
            // Create card grid for challenges
            const challengesGrid = document.createElement('div');
            challengesGrid.className = 'challenges-grid';
            
            challengeData.recurring_challenges.forEach(challenge => {
                // Create challenge card
                const challengeCard = document.createElement('div');
                challengeCard.className = 'challenge-card';
                
                if (typeof challenge === 'string') {
                    // Simple string case
                    const title = document.createElement('h6');
                    title.textContent = 'Challenge';
                    challengeCard.appendChild(title);
                    
                    const content = document.createElement('p');
                    content.textContent = challenge;
                    content.style.flex = '1';
                    challengeCard.appendChild(content);
                } else {
                    // Object with structured data
                    const challengeTitle = document.createElement('h6');
                    challengeTitle.textContent = challenge.description || 'Challenge';
                    challengeCard.appendChild(challengeTitle);
                    
                    // Create details list
                    const detailsList = document.createElement('ul');
                    detailsList.className = 'challenge-details';
                    
                    if (challenge.type) {
                        const typeItem = document.createElement('li');
                        typeItem.innerHTML = `<strong>Type:</strong> <span>${capitalizeFirstLetter(challenge.type)}</span>`;
                        detailsList.appendChild(typeItem);
                    }
                    
                    if (challenge.frequency) {
                        const frequencyItem = document.createElement('li');
                        frequencyItem.innerHTML = `<strong>Frequency:</strong> <span>${capitalizeFirstLetter(challenge.frequency)}</span>`;
                        detailsList.appendChild(frequencyItem);
                    }
                    
                    if (challenge.systemic !== undefined) {
                        const systemicItem = document.createElement('li');
                        systemicItem.innerHTML = `<strong>Systemic Issue:</strong> <span>${challenge.systemic ? 'Yes' : 'No'}</span>`;
                        detailsList.appendChild(systemicItem);
                    }
                    
                    challengeCard.appendChild(detailsList);
                    
                    // Add resolution status if available
                    if (challenge.resolution_status) {
                        const statusClass = `status-${challenge.resolution_status.toLowerCase().replace(/\s+/g, '-')}`;
                        const statusEl = document.createElement('div');
                        statusEl.className = `challenge-status ${statusClass}`;
                        statusEl.textContent = `Status: ${capitalizeFirstLetter(challenge.resolution_status)}`;
                        challengeCard.appendChild(statusEl);
                    }
                }
                
                challengesGrid.appendChild(challengeCard);
            });
            
            challengeSection.appendChild(challengesGrid);
            
            // Add adaptation effectiveness if available
            if (challengeData.adaptation_effectiveness || data.adaptation_effectiveness) {
                const adaptationValue = challengeData.adaptation_effectiveness || data.adaptation_effectiveness;
                const adaptationMetric = document.createElement('div');
                adaptationMetric.className = `adaptation-metric adaptation-${adaptationValue.toLowerCase()}`;
                adaptationMetric.innerHTML = `<i class="fas fa-sync-alt"></i> <strong>Adaptation Effectiveness:</strong> ${capitalizeFirstLetter(adaptationValue)}`;
                challengeSection.appendChild(adaptationMetric);
            }
            
            mainContainer.appendChild(challengeSection);
        }
        
        // Add risk assessment section
        const riskData = safelyParseJson(data.risk_assessment_json) || data.risk_assessment;
        if (riskData || data.risk_level) {
            const riskSection = document.createElement('div');
            riskSection.className = 'quarterly-section risk-assessment-section';
            
            riskSection.innerHTML = `<h5>Risk Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Comprehensive assessment of risks and mitigation strategies.</span>
                </span>
            </h5>`;
            
            // Add risk metrics title
            const riskMetricsTitle = document.createElement('h6');
            riskMetricsTitle.textContent = 'Risk Indicators';
            riskSection.appendChild(riskMetricsTitle);
            
            // Create metrics grid for risk indicators
            const riskMetricsGrid = document.createElement('div');
            riskMetricsGrid.className = 'metrics-grid';
            
            // Get risk level from either source
            const riskLevel = riskData?.overall_risk_level || data.risk_level || 'medium';
            
            // Add risk level metric
            const riskLevelMetric = document.createElement('div');
            riskLevelMetric.className = 'metric';
            
            const riskLevelName = document.createElement('div');
            riskLevelName.className = 'metric-name risk-level';
            riskLevelName.style.textAlign = 'center';
            riskLevelName.textContent = 'Overall Risk Level';
            
            const riskLevelValue = document.createElement('div');
            riskLevelValue.className = `metric-value ${riskLevel.toLowerCase()}`;
            riskLevelValue.textContent = capitalizeFirstLetter(riskLevel);
            
            riskLevelMetric.appendChild(riskLevelName);
            riskLevelMetric.appendChild(riskLevelValue);
            riskMetricsGrid.appendChild(riskLevelMetric);
            
            // Get risk trend from either source
            const riskTrend = riskData?.risk_trend || data.risk_trend || 'stable';
            
            // Add risk trend metric
            const riskTrendMetric = document.createElement('div');
            riskTrendMetric.className = 'metric';
            
            const riskTrendName = document.createElement('div');
            riskTrendName.className = 'metric-name risk-trend';
            riskTrendName.style.textAlign = 'center';
            riskTrendName.textContent = 'Risk Trend';
            
            const riskTrendValue = document.createElement('div');
            riskTrendValue.className = `metric-value trend-${riskTrend.toLowerCase()}`;
            riskTrendValue.textContent = capitalizeFirstLetter(riskTrend);
            
            // // Add appropriate icon based on trend
            // let trendIcon = '';
            // if (riskTrend.toLowerCase() === 'increasing') {
            //     trendIcon = '<i class="fas fa-arrow-up"></i> ';
            // } else if (riskTrend.toLowerCase() === 'decreasing') {
            //     trendIcon = '<i class="fas fa-arrow-down"></i> ';
            // } else {
            //     trendIcon = '<i class="fas fa-equals"></i> ';
            // }
            
            riskTrendValue.innerHTML =  " " + capitalizeFirstLetter(riskTrend);
            
            riskTrendMetric.appendChild(riskTrendName);
            riskTrendMetric.appendChild(riskTrendValue);
            riskMetricsGrid.appendChild(riskTrendMetric);
            
            riskSection.appendChild(riskMetricsGrid);
            
            // Add key risk factors if available
            if (riskData && riskData.key_risk_factors && riskData.key_risk_factors.length > 0) {
                const riskFactorsTitle = document.createElement('h6');
                riskFactorsTitle.textContent = 'Key Risk Factors';
                riskSection.appendChild(riskFactorsTitle);
                
                // Create list for risk factors
                const riskFactorsList = document.createElement('ul');
                riskFactorsList.className = 'risk-factors-list';
                
                riskData.key_risk_factors.forEach(factor => {
                    // Create risk factor list item
                    const factorItem = document.createElement('li');
                    factorItem.className = 'risk-factor-item';
                    
                    let factorText = '';
                    if (typeof factor === 'string') {
                        factorText = factor;
                    } else {
                        factorText = factor.description || factor.factor || JSON.stringify(factor);
                    }
                    
                    // Add factor content with icon
                    factorItem.innerHTML = `
                        <div class="risk-factor-content">
                            <i class="fas fa-exclamation-circle"></i>
                            <span>${factorText}</span>
                        </div>
                    `;
                    
                    riskFactorsList.appendChild(factorItem);
                });
                
                riskSection.appendChild(riskFactorsList);
            }
            
            // Add mitigation strategies if available
            if (riskData && riskData.mitigation_strategies && riskData.mitigation_strategies.length > 0) {
                const strategiesTitle = document.createElement('h6');
                strategiesTitle.textContent = 'Mitigation Strategies';
                riskSection.appendChild(strategiesTitle);
                
                // Create list for mitigation strategies
                const strategiesList = document.createElement('ul');
                strategiesList.className = 'mitigation-strategies-list';
                
                riskData.mitigation_strategies.forEach(strategy => {
                    // Create strategy list item
                    const strategyItem = document.createElement('li');
                    strategyItem.className = 'mitigation-strategy-item';
                    
                    let strategyText = '';
                    if (typeof strategy === 'string') {
                        strategyText = strategy;
                    } else {
                        strategyText = strategy.description || strategy.strategy || JSON.stringify(strategy);
                    }
                    
                    // Add strategy content with icon
                    strategyItem.innerHTML = `
                        <div class="mitigation-strategy-content">
                            <i class="fas fa-shield-alt"></i>
                            <span>${strategyText}</span>
                        </div>
                    `;
                    
                    strategiesList.appendChild(strategyItem);
                });
                
                riskSection.appendChild(strategiesList);
            }
            
            mainContainer.appendChild(riskSection);
        }
        
        // Add skill development section
        const skillData = safelyParseJson(data.skill_development_json) || data.skill_development;
        if (skillData || data.development_focus || data.learning_agility || data.autonomy_level) {
            const skillSection = document.createElement('div');
            skillSection.className = 'quarterly-section skill-development-section';
            
            skillSection.innerHTML = `<h5>Skill Development
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Assessment of skills demonstrated and developed during the quarter.</span>
                </span>
            </h5>`;
            
            // Add skill metrics grid for learning agility and autonomy level
            const learningAgility = skillData?.learning_agility || data.learning_agility;
            const autonomyLevel = skillData?.autonomy_level || data.autonomy_level;
            
            if (learningAgility || autonomyLevel) {
                const metricsTitle = document.createElement('h6');
                metricsTitle.textContent = 'Key Metrics';
                skillSection.appendChild(metricsTitle);
                
                // Create metrics grid for skill indicators
                const metricsGrid = document.createElement('div');
                metricsGrid.className = 'skills-metrics-grid';
                
                // Add learning agility metric if available
                if (learningAgility) {
                    const agilityMetric = document.createElement('div');
                    agilityMetric.className = 'skill-metric';
                    
                    const metricName = document.createElement('div');
                    metricName.className = 'skill-metric-name agility';
                    metricName.textContent = 'Learning Agility';
                    
                    const metricValue = document.createElement('div');
                    metricValue.className = `skill-metric-value ${learningAgility.toLowerCase()}`;
                    metricValue.textContent = capitalizeFirstLetter(learningAgility);
                    
                    agilityMetric.appendChild(metricName);
                    agilityMetric.appendChild(metricValue);
                    metricsGrid.appendChild(agilityMetric);
                }
                
                // Add autonomy level metric if available
                if (autonomyLevel) {
                    const autonomyMetric = document.createElement('div');
                    autonomyMetric.className = 'skill-metric';
                    
                    const metricName = document.createElement('div');
                    metricName.className = 'skill-metric-name autonomy';
                    metricName.textContent = 'Autonomy Level';
                    
                    const metricValue = document.createElement('div');
                    metricValue.className = `skill-metric-value ${autonomyLevel.toLowerCase()}`;
                    metricValue.textContent = capitalizeFirstLetter(autonomyLevel);
                    
                    autonomyMetric.appendChild(metricName);
                    autonomyMetric.appendChild(metricValue);
                    metricsGrid.appendChild(autonomyMetric);
                }
                
                skillSection.appendChild(metricsGrid);
            }
            
            // Add key capabilities if available
            if (skillData && skillData.key_capabilities && skillData.key_capabilities.length > 0) {
                const capabilitiesTitle = document.createElement('h6');
                capabilitiesTitle.textContent = 'Key Capabilities';
                skillSection.appendChild(capabilitiesTitle);
                
                // Create card grid for capabilities
                const capabilitiesGrid = document.createElement('div');
                capabilitiesGrid.className = 'quarterly-card-grid';
                
                skillData.key_capabilities.forEach(capability => {
                    // Create capability card
                    const capabilityCard = document.createElement('div');
                    capabilityCard.className = 'key-capability';
                    
                    if (typeof capability === 'string') {
                        // Simple string case
                        const capabilityName = document.createElement('h6');
                        capabilityName.textContent = capability;
                        capabilityCard.appendChild(capabilityName);
                        
                        // Add a placeholder proficiency when only string is provided
                        const placeholderDesc = document.createElement('div');
                        placeholderDesc.className = 'capability-evidence';
                        placeholderDesc.innerHTML = '<strong>Demonstrated:</strong> Throughout the quarter';
                        capabilityCard.appendChild(placeholderDesc);
                    } else {
                        // Object with structured data
                        const capabilityName = document.createElement('h6');
                        capabilityName.textContent = capability.skill || capability.name || 'Capability';
                        capabilityCard.appendChild(capabilityName);
                        
                        // Add proficiency level if available
                        if (capability.proficiency || capability.level) {
                            const proficiency = document.createElement('div');
                            proficiency.className = 'capability-proficiency';
                            proficiency.innerHTML = `<strong>Proficiency:</strong> ${capitalizeFirstLetter(capability.proficiency || capability.level)}`;
                            capabilityCard.appendChild(proficiency);
                        }
                        
                        // Add growth information if available
                        if (capability.growth) {
                            const growth = document.createElement('div');
                            growth.className = 'capability-growth';
                            growth.innerHTML = `<strong>Growth:</strong> ${capitalizeFirstLetter(capability.growth)}`;
                            capabilityCard.appendChild(growth);
                        }
                        
                        // Add evidence if available
                        if (capability.evidence || capability.examples) {
                            const evidence = document.createElement('div');
                            evidence.className = 'capability-evidence';
                            evidence.innerHTML = `<strong>Evidence:</strong> ${capability.evidence || capability.examples}`;
                            capabilityCard.appendChild(evidence);
                        }
                    }
                    
                    capabilitiesGrid.appendChild(capabilityCard);
                });
                
                skillSection.appendChild(capabilitiesGrid);
            }
            
            // Add development focus if available from either source
            const developmentFocus = skillData?.development_focus || data.development_focus;
            if (developmentFocus) {
                const focusContainer = document.createElement('div');
                focusContainer.className = 'development-focus';
                
                const focusTitle = document.createElement('h6');
                focusTitle.className = 'development-focus-title';
                focusTitle.textContent = 'Recommended Development Focus';
                focusContainer.appendChild(focusTitle);
                
                const focusText = document.createElement('p');
                focusText.textContent = developmentFocus;
                focusContainer.appendChild(focusText);
                
                skillSection.appendChild(focusContainer);
            }
            
            mainContainer.appendChild(skillSection);
        }
        
        // Add behavioral assessment section
        const behavioralData = safelyParseJson(data.behavioral_assessment_json) || data.behavioral_assessment;
        if (behavioralData) {
            const behavioralSection = document.createElement('div');
            behavioralSection.className = 'quarterly-section behavioral-assessment-section';
            
            behavioralSection.innerHTML = `<h5>Behavioral Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Analysis of key workplace behaviors and interaction patterns.</span>
                </span>
            </h5>`;
            
            // Create a grid for behaviors
            const behaviorsGrid = document.createElement('div');
            behaviorsGrid.className = 'behaviors-grid';
            
            // Helper function to create behavior card
            const createBehaviorCard = (title, type, behavior) => {
                if (!behavior) return null;
                
                const card = document.createElement('div');
                card.className = `quarterly-card behavior-card ${type}`;
                
                const cardTitle = document.createElement('h6');
                cardTitle.textContent = title;
                card.appendChild(cardTitle);
                
                if (behavior.rating) {
                    const ratingContainer = document.createElement('div');
                    ratingContainer.className = 'rating-container';
                    
                    const ratingLabel = document.createElement('span');
                    ratingLabel.className = 'rating-label';
                    ratingLabel.textContent = 'Rating: ';
                    
                    const rating = document.createElement('span');
                    rating.className = `behavior-rating ${behavior.rating.toLowerCase()}`;
                    rating.textContent = `${capitalizeFirstLetter(behavior.rating)} Expectations`;
                    
                    ratingContainer.appendChild(ratingLabel);
                    ratingContainer.appendChild(rating);
                    card.appendChild(ratingContainer);
                }
                
                if (behavior.evidence) {
                    const evidence = document.createElement('div');
                    evidence.className = 'behavior-evidence';
                    
                    const evidenceLabel = document.createElement('strong');
                    evidenceLabel.textContent = 'Evidence';
                    
                    const evidenceText = document.createElement('div');
                    evidenceText.textContent = behavior.evidence;
                    
                    evidence.appendChild(evidenceLabel);
                    evidence.appendChild(evidenceText);
                    card.appendChild(evidence);
                }
                
                return card;
            };
            
            // Add behavior cards
            if (behavioralData.ownership) {
                const ownershipCard = createBehaviorCard('Ownership & Accountability', 'ownership', behavioralData.ownership);
                if (ownershipCard) behaviorsGrid.appendChild(ownershipCard);
            }
            
            if (behavioralData.collaboration) {
                const collaborationCard = createBehaviorCard('Collaboration & Teamwork', 'collaboration', behavioralData.collaboration);
                if (collaborationCard) behaviorsGrid.appendChild(collaborationCard);
            }
            
            if (behavioralData.communication) {
                const communicationCard = createBehaviorCard('Communication', 'communication', behavioralData.communication);
                if (communicationCard) behaviorsGrid.appendChild(communicationCard);
            }
            
            if (behavioralData.problem_solving) {
                const problemSolvingCard = createBehaviorCard('Problem Solving', 'problem-solving', behavioralData.problem_solving);
                if (problemSolvingCard) behaviorsGrid.appendChild(problemSolvingCard);
            }
            
            if (behavioralData.quality_standards) {
                const qualityCard = createBehaviorCard('Quality Standards', 'quality-standards', behavioralData.quality_standards);
                if (qualityCard) behaviorsGrid.appendChild(qualityCard);
            }
            
            behavioralSection.appendChild(behaviorsGrid);
            mainContainer.appendChild(behavioralSection);
        }
        
        // Add credibility assessment section if available
        const credibilityData = safelyParseJson(data.credibility_assessment_json) || data.credibility_assessment;
        if (credibilityData && (credibilityData.rating || credibilityData.explanation)) {
            const credibilitySection = document.createElement('div');
            credibilitySection.className = 'quarterly-section credibility-assessment-section';
            
            credibilitySection.innerHTML = `<h5>Credibility Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Assessment of reporting credibility and alignment with vision data.</span>
                </span>
            </h5>`;
            
            // Add explanation if available
            if (credibilityData.explanation) {
                const explanation = document.createElement('div');
                explanation.className = 'credibility-explanation';
                explanation.textContent = credibilityData.explanation;
                credibilitySection.appendChild(explanation);
            }
            
            // Add ratings in a metrics grid
            const metricsGrid = document.createElement('div');
            metricsGrid.className = 'metrics-grid';
            
            // Add credibility rating metric
            if (credibilityData.rating) {
                const credibilityMetric = document.createElement('div');
                credibilityMetric.className = 'metric';
                
                const metricName = document.createElement('div');
                metricName.className = 'metric-name credibility-rating';
                metricName.style.textAlign = 'center';
                metricName.textContent = 'Credibility Rating';
                metricName.style.textAlign = 'center';
                
                const metricValue = document.createElement('div');
                metricValue.className = `metric-value ${credibilityData.rating.toLowerCase()}`;
                metricValue.textContent = capitalizeFirstLetter(credibilityData.rating);
                
                credibilityMetric.appendChild(metricName);
                credibilityMetric.appendChild(metricValue);
                metricsGrid.appendChild(credibilityMetric);
            }
            
            // Add vision data alignment metric
            if (credibilityData.vision_data_alignment) {
                const alignmentMetric = document.createElement('div');
                alignmentMetric.className = 'metric';
                
                const metricName = document.createElement('div');
                metricName.className = 'metric-name vision-alignment';
                metricName.textContent = 'Vision Data Alignment';
                
                const metricValue = document.createElement('div');
                metricValue.className = `metric-value ${credibilityData.vision_data_alignment.toLowerCase()}`;
                metricValue.textContent = capitalizeFirstLetter(credibilityData.vision_data_alignment);
                
                alignmentMetric.appendChild(metricName);
                alignmentMetric.appendChild(metricValue);
                metricsGrid.appendChild(alignmentMetric);
            }
            
            credibilitySection.appendChild(metricsGrid);
            
            // Add impact on evaluation if available
            if (credibilityData.impact_on_evaluation) {
                const impactSection = document.createElement('div');
                impactSection.className = 'impact-evaluation';
                const impactContent = document.createElement('div');
                impactContent.innerHTML = `<strong>Impact on Evaluation:</strong> ${credibilityData.impact_on_evaluation}`;
                impactSection.appendChild(impactContent);
                
                credibilitySection.appendChild(impactSection);
            }
            
            mainContainer.appendChild(credibilitySection);
        }
        
        // Add forward planning section
        const planningData = safelyParseJson(data.forward_planning_json) || data.forward_planning;
        if (planningData) {
            const planningSection = document.createElement('div');
            planningSection.className = 'quarterly-section forward-planning-section';
            
            planningSection.innerHTML = `<h5>Forward Planning
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Recommendations for activities to continue, improve, start, and stop.</span>
                </span>
            </h5>`;
            
            // Try to extract "continue" items from different possible structures
            let continueItems = [];
            if (planningData.keep_doing) {
                continueItems = planningData.keep_doing;
            } else if (planningData.continue) {
                continueItems = planningData.continue;
            } else if (planningData.activities_to_continue) {
                continueItems = planningData.activities_to_continue;
            } else if (Array.isArray(planningData)) {
                // If it's just an array, assume it contains all recommendations
                continueItems = planningData.filter(item => 
                    item.type === 'continue' || item.category === 'continue'
                );
            }
            
            // Add continue section
            const continueSectionTitle = document.createElement('h6');
            continueSectionTitle.textContent = 'Continue';
            planningSection.appendChild(continueSectionTitle);
            
            const continueList = document.createElement('ul');
            continueList.className = 'continue-list';
            
            if (continueItems.length > 0) {
                continueItems.forEach(item => {
                    const listItem = document.createElement('li');
                    if (typeof item === 'string') {
                        listItem.textContent = item;
                    } else {
                        listItem.textContent = item.description || item.recommendation || JSON.stringify(item);
                    }
                    continueList.appendChild(listItem);
                });
            } else {
                const emptyItem = document.createElement('li');
                emptyItem.className = 'empty-list';
                emptyItem.textContent = 'No specific activities to continue were identified.';
                continueList.appendChild(emptyItem);
            }
            
            planningSection.appendChild(continueList);
            
            // Try to extract "improve" items
            let improveItems = [];
            if (planningData.improve) {
                improveItems = planningData.improve;
            } else if (planningData.activities_to_improve) {
                improveItems = planningData.activities_to_improve;
            } else if (Array.isArray(planningData)) {
                improveItems = planningData.filter(item => 
                    item.type === 'improve' || item.category === 'improve'
                );
            }
            
            // Add improve section
            const improveSectionTitle = document.createElement('h6');
            improveSectionTitle.textContent = 'Improve';
            planningSection.appendChild(improveSectionTitle);
            
            const improveList = document.createElement('ul');
            improveList.className = 'improve-list';
            
            if (improveItems.length > 0) {
                improveItems.forEach(item => {
                    const listItem = document.createElement('li');
                    if (typeof item === 'string') {
                        listItem.textContent = item;
                    } else {
                        listItem.textContent = item.description || item.recommendation || JSON.stringify(item);
                    }
                    improveList.appendChild(listItem);
                });
            } else {
                const emptyItem = document.createElement('li');
                emptyItem.className = 'empty-list';
                emptyItem.textContent = 'No specific areas for improvement were identified.';
                improveList.appendChild(emptyItem);
            }
            
            planningSection.appendChild(improveList);
            
            // Add start items if available
            let startItems = [];
            if (planningData.start) {
                startItems = planningData.start;
            } else if (Array.isArray(planningData)) {
                startItems = planningData.filter(item => 
                    item.type === 'start' || item.category === 'start'
                );
            }
            
            if (startItems.length > 0) {
                const startSectionTitle = document.createElement('h6');
                startSectionTitle.textContent = 'Start';
                planningSection.appendChild(startSectionTitle);
                
                const startList = document.createElement('ul');
                startList.className = 'start-list'; // Use start-specific styling
                
                startItems.forEach(item => {
                    const listItem = document.createElement('li');
                    if (typeof item === 'string') {
                        listItem.textContent = item;
                    } else {
                        listItem.textContent = item.description || item.recommendation || JSON.stringify(item);
                    }
                    startList.appendChild(listItem);
                });
                
                planningSection.appendChild(startList);
            }
            
            // Add stop items if available
            let stopItems = [];
            if (planningData.stop) {
                stopItems = planningData.stop;
            } else if (Array.isArray(planningData)) {
                stopItems = planningData.filter(item => 
                    item.type === 'stop' || item.category === 'stop'
                );
            }
            
            if (stopItems.length > 0) {
                const stopSectionTitle = document.createElement('h6');
                stopSectionTitle.textContent = 'Stop';
                planningSection.appendChild(stopSectionTitle);
                
                const stopList = document.createElement('ul');
                stopList.className = 'stop-list'; // Use stop-specific styling
                
                stopItems.forEach(item => {
                    const listItem = document.createElement('li');
                    if (typeof item === 'string') {
                        listItem.textContent = item;
                    } else {
                        listItem.textContent = item.description || item.recommendation || JSON.stringify(item);
                    }
                    stopList.appendChild(listItem);
                });
                
                planningSection.appendChild(stopList);
            }
            
            // Add support needed items if available
            if (planningData.support_needed && planningData.support_needed.length > 0) {
                const supportSectionTitle = document.createElement('h6');
                supportSectionTitle.textContent = 'Support Needed';
                planningSection.appendChild(supportSectionTitle);
                
                const supportList = document.createElement('ul');
                supportList.className = 'support-list'; // Use support-specific styling
                
                planningData.support_needed.forEach(item => {
                    const listItem = document.createElement('li');
                    if (typeof item === 'string') {
                        listItem.textContent = item;
                    } else {
                        listItem.textContent = item.description || item.recommendation || JSON.stringify(item);
                    }
                    supportList.appendChild(listItem);
                });
                
                planningSection.appendChild(supportList);
            }
            
            mainContainer.appendChild(planningSection);
        }
        
        // Add to main results container
        analysisResults.appendChild(mainContainer);
        analysisResults.style.display = 'block';
        
        // Scroll to the results
            analysisResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // Ensure tooltips are properly positioned
        ensureTooltipVisibility();
    }
    
    // Export functions to global scope
    window.quarterlyAnalysis = {
        displayQuarterlyAnalysisResults: displayQuarterlyAnalysisResults
    };

    })();






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

    // Helper function to create a badge with the appropriate class
    function createBadge(type, value, tooltip) {
        const badgeClass = `${type}-${value.toLowerCase().replace(/\s+/g, '-')}`;
        
        const badge = document.createElement('div');
        badge.className = `${type} ${badgeClass}`;
        badge.innerHTML = `<strong>${capitalizeFirstLetter(type.replace(/-/g, ' '))}:</strong> ${capitalizeFirstLetter(value)}`;
        
        if (tooltip) {
            badge.innerHTML += `<span class="tooltip-trigger"><i class="fas fa-info-circle"></i><span class="tooltip">${tooltip}</span></span>`;
        }
        
        return badge;
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
        
        // Add organizational impact badge
        const impactBadge = createBadge('impact', data.organizational_impact, 
            "Scope of employee's impact within the organization: individual, team, department, or organization-wide.");
        metaInfo.appendChild(impactBadge);
        
        // Add performance trend badge
        const performanceTrendBadge = createBadge('trend', data.performance_trend,
            "Overall trend in employee's performance throughout the quarter.");
        metaInfo.appendChild(performanceTrendBadge);
        
        // Add risk level badge
        const riskBadge = createBadge('risk', data.risk_level,
            "Overall risk assessment based on recurring challenges, performance stability, and emerging issues.");
        metaInfo.appendChild(riskBadge);
        
        // Add risk trend badge
        const riskTrendBadge = createBadge('trend', data.risk_trend,
            "Direction of risk level changes throughout the quarter.");
        metaInfo.appendChild(riskTrendBadge);
        
        // Add learning agility badge
        const agilityBadge = createBadge('agility', data.learning_agility,
            "Employee's demonstrated ability to learn and adapt to new situations.");
        metaInfo.appendChild(agilityBadge);
        
        // Add autonomy level badge
        const autonomyBadge = createBadge('autonomy', data.autonomy_level,
            "Level of independence the employee demonstrates in their work.");
        metaInfo.appendChild(autonomyBadge);
        
        header.appendChild(metaInfo);
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
            
            // Create the content container
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
        if (data.strategic_alignment) {
            const alignmentSection = document.createElement('div');
            alignmentSection.className = 'quarterly-section strategic-alignment-section';
            
            alignmentSection.innerHTML = `<h5>Strategic Alignment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Assessment of how the employee's work aligns with organizational goals.</span>
                </span>
            </h5>`;
            
            const alignmentContent = document.createElement('div');
            alignmentContent.className = 'alignment-content';
            
            // Add key initiatives if available
            if (data.strategic_alignment.key_initiatives && data.strategic_alignment.key_initiatives.length > 0) {
                const initiativesTitle = document.createElement('h6');
                initiativesTitle.textContent = 'Key Strategic Initiatives';
                alignmentContent.appendChild(initiativesTitle);
                
                const initiativesList = document.createElement('ul');
                initiativesList.className = 'initiatives-list';
                
                data.strategic_alignment.key_initiatives.forEach(initiative => {
                    const item = document.createElement('li');
                    item.textContent = initiative.name ? initiative.name : initiative;
                    
                    // Add description if available
                    if (initiative.description) {
                        const description = document.createElement('p');
                        description.className = 'initiative-description';
                        description.textContent = initiative.description;
                        item.appendChild(description);
                    }
                    
                    initiativesList.appendChild(item);
                });
                
                alignmentContent.appendChild(initiativesList);
            }
            
            // Add alignment rating if available
            if (data.strategic_alignment.alignment_rating) {
                const ratingContainer = document.createElement('div');
                ratingContainer.className = 'alignment-rating';
                ratingContainer.innerHTML = `<strong>Alignment Rating:</strong> ${capitalizeFirstLetter(data.strategic_alignment.alignment_rating)}`;
                alignmentContent.appendChild(ratingContainer);
            }
            
            alignmentSection.appendChild(alignmentContent);
            mainContainer.appendChild(alignmentSection);
        }
        
        // Add achievement themes section
        if (data.achievement_themes && data.achievement_themes.length > 0) {
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
            
            data.achievement_themes.forEach(theme => {
                const themeItem = document.createElement('div');
                themeItem.className = 'achievement-theme';
                
                // Create theme header
                const themeHeader = document.createElement('h6');
                themeHeader.textContent = theme.theme || theme.name || 'Achievement Theme';
                themeItem.appendChild(themeHeader);
                
                // Add theme description if available
                if (theme.description) {
                    const themeDesc = document.createElement('p');
                    themeDesc.className = 'theme-description';
                    themeDesc.textContent = theme.description;
                    themeItem.appendChild(themeDesc);
                }
                
                // Add related achievements if available
                if (theme.achievements && theme.achievements.length > 0) {
                    const achievementsList = document.createElement('ul');
                    achievementsList.className = 'theme-achievements';
                    
                    theme.achievements.forEach(achievement => {
                        const achievementItem = document.createElement('li');
                        achievementItem.textContent = achievement;
                        achievementsList.appendChild(achievementItem);
                    });
                    
                    themeItem.appendChild(achievementsList);
                }
                
                // Add impact if available
                if (theme.impact) {
                    const impactText = document.createElement('div');
                    impactText.className = 'theme-impact';
                    impactText.innerHTML = `<strong>Impact:</strong> ${theme.impact}`;
                    themeItem.appendChild(impactText);
                }
                
                themesContainer.appendChild(themeItem);
            });
            
            themesSection.appendChild(themesContainer);
            mainContainer.appendChild(themesSection);
        }
        
        // Add performance trajectory section
        if (data.performance_trajectory) {
            const trajectorySection = document.createElement('div');
            trajectorySection.className = 'quarterly-section performance-trajectory-section';
            
            trajectorySection.innerHTML = `<h5>Performance Trajectory
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Analysis of performance trends and consistency throughout the quarter.</span>
                </span>
            </h5>`;
            
            const trajectoryContent = document.createElement('div');
            trajectoryContent.className = 'trajectory-content';
            
            // Add consistency metrics if available
            if (data.performance_trajectory.consistency) {
                const consistencyContainer = document.createElement('div');
                consistencyContainer.className = 'consistency-metrics';
                
                const consistencyTitle = document.createElement('h6');
                consistencyTitle.textContent = 'Performance Consistency';
                consistencyContainer.appendChild(consistencyTitle);
                
                const metrics = data.performance_trajectory.consistency;
                
                // Create metrics grid
                const metricsGrid = document.createElement('div');
                metricsGrid.className = 'metrics-grid';
                
                // Add each metric
                if (metrics.task_completion_reliability) {
                    const reliabilityMetric = document.createElement('div');
                    reliabilityMetric.className = 'metric';
                    reliabilityMetric.innerHTML = `<span class="metric-name">Task Completion:</span> 
                        <span class="metric-value ${metrics.task_completion_reliability.toLowerCase()}">${capitalizeFirstLetter(metrics.task_completion_reliability)}</span>`;
                    metricsGrid.appendChild(reliabilityMetric);
                }
                
                if (metrics.work_quality_consistency) {
                    const qualityMetric = document.createElement('div');
                    qualityMetric.className = 'metric';
                    qualityMetric.innerHTML = `<span class="metric-name">Work Quality:</span> 
                        <span class="metric-value ${metrics.work_quality_consistency.toLowerCase()}">${capitalizeFirstLetter(metrics.work_quality_consistency)}</span>`;
                    metricsGrid.appendChild(qualityMetric);
                }
                
                if (metrics.performance_stability) {
                    const stabilityMetric = document.createElement('div');
                    stabilityMetric.className = 'metric';
                    stabilityMetric.innerHTML = `<span class="metric-name">Stability:</span> 
                        <span class="metric-value ${metrics.performance_stability.toLowerCase()}">${capitalizeFirstLetter(metrics.performance_stability)}</span>`;
                    metricsGrid.appendChild(stabilityMetric);
                }
                
                consistencyContainer.appendChild(metricsGrid);
                trajectoryContent.appendChild(consistencyContainer);
            }
            
            // Add notable shifts if available
            if (data.performance_trajectory.notable_shifts && data.performance_trajectory.notable_shifts.length > 0) {
                const shiftsContainer = document.createElement('div');
                shiftsContainer.className = 'notable-shifts';
                
                const shiftsTitle = document.createElement('h6');
                shiftsTitle.textContent = 'Notable Performance Shifts';
                shiftsContainer.appendChild(shiftsTitle);
                
                const shiftsList = document.createElement('ul');
                shiftsList.className = 'shifts-list';
                
                data.performance_trajectory.notable_shifts.forEach(shift => {
                    const shiftItem = document.createElement('li');
                    if (typeof shift === 'string') {
                        shiftItem.textContent = shift;
                    } else {
                        shiftItem.textContent = shift.description || shift.shift || JSON.stringify(shift);
                    }
                    shiftsList.appendChild(shiftItem);
                });
                
                shiftsContainer.appendChild(shiftsList);
                trajectoryContent.appendChild(shiftsContainer);
            }
            
            trajectorySection.appendChild(trajectoryContent);
            mainContainer.appendChild(trajectorySection);
        }
        
        // Add cross-functional impact section
        if (data.cross_functional_impact) {
            const impactSection = document.createElement('div');
            impactSection.className = 'quarterly-section cross-functional-section';
            
            impactSection.innerHTML = `<h5>Cross-Functional Impact
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Employee's impact across teams and departments.</span>
                </span>
            </h5>`;
            
            const impactContent = document.createElement('div');
            impactContent.className = 'impact-content';
            
            // Add stakeholder impacts if available
            if (data.cross_functional_impact.stakeholder_impacts && data.cross_functional_impact.stakeholder_impacts.length > 0) {
                const stakeholdersTitle = document.createElement('h6');
                stakeholdersTitle.textContent = 'Stakeholder Impacts';
                impactContent.appendChild(stakeholdersTitle);
                
                const stakeholdersList = document.createElement('div');
                stakeholdersList.className = 'stakeholders-list';
                
                data.cross_functional_impact.stakeholder_impacts.forEach(stakeholder => {
                    const stakeholderItem = document.createElement('div');
                    stakeholderItem.className = 'stakeholder-impact';
                    
                    if (typeof stakeholder === 'string') {
                        stakeholderItem.textContent = stakeholder;
                    } else {
                        // Create stakeholder header if name exists
                        if (stakeholder.name || stakeholder.stakeholder) {
                            const stakeholderHeader = document.createElement('h6');
                            stakeholderHeader.textContent = stakeholder.name || stakeholder.stakeholder;
                            stakeholderItem.appendChild(stakeholderHeader);
                        }
                        
                        // Add impact description if available
                        if (stakeholder.impact || stakeholder.description) {
                            const impactDesc = document.createElement('p');
                            impactDesc.textContent = stakeholder.impact || stakeholder.description;
                            stakeholderItem.appendChild(impactDesc);
                        }
                    }
                    
                    stakeholdersList.appendChild(stakeholderItem);
                });
                
                impactContent.appendChild(stakeholdersList);
            }
            
            // Add collaboration effectiveness if available
            if (data.collaboration_effectiveness) {
                const collaborationMetric = document.createElement('div');
                collaborationMetric.className = 'collaboration-metric';
                collaborationMetric.innerHTML = `<strong>Collaboration Effectiveness:</strong> 
                    <span class="${data.collaboration_effectiveness.toLowerCase()}">${capitalizeFirstLetter(data.collaboration_effectiveness)}</span>`;
                impactContent.appendChild(collaborationMetric);
            }
            
            impactSection.appendChild(impactContent);
            mainContainer.appendChild(impactSection);
        }
        
        // Add risk assessment section
        if (data.risk_assessment) {
            const riskSection = document.createElement('div');
            riskSection.className = 'quarterly-section quarterly-risk-section';
            
            riskSection.innerHTML = `<h5>Risk Assessment
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Comprehensive assessment of risks and mitigation strategies.</span>
                </span>
            </h5>`;
            
            const riskContent = document.createElement('div');
            riskContent.className = 'risk-content';
            
            // Add key risk factors if available
            if (data.risk_assessment.key_risk_factors && data.risk_assessment.key_risk_factors.length > 0) {
                const riskFactorsTitle = document.createElement('h6');
                riskFactorsTitle.textContent = 'Key Risk Factors';
                riskContent.appendChild(riskFactorsTitle);
                
                const riskFactorsList = document.createElement('ul');
                riskFactorsList.className = 'risk-factors-list';
                
                data.risk_assessment.key_risk_factors.forEach(factor => {
                    const factorItem = document.createElement('li');
                    if (typeof factor === 'string') {
                        factorItem.textContent = factor;
                    } else {
                        factorItem.textContent = factor.description || factor.factor || JSON.stringify(factor);
                    }
                    riskFactorsList.appendChild(factorItem);
                });
                
                riskContent.appendChild(riskFactorsList);
            }
            
            // Add mitigation strategies if available
            if (data.risk_assessment.mitigation_strategies && data.risk_assessment.mitigation_strategies.length > 0) {
                const strategiesTitle = document.createElement('h6');
                strategiesTitle.textContent = 'Mitigation Strategies';
                riskContent.appendChild(strategiesTitle);
                
                const strategiesList = document.createElement('ul');
                strategiesList.className = 'strategies-list';
                
                data.risk_assessment.mitigation_strategies.forEach(strategy => {
                    const strategyItem = document.createElement('li');
                    if (typeof strategy === 'string') {
                        strategyItem.textContent = strategy;
                    } else {
                        strategyItem.textContent = strategy.description || strategy.strategy || JSON.stringify(strategy);
                    }
                    strategiesList.appendChild(strategyItem);
                });
                
                riskContent.appendChild(strategiesList);
            }
            
            riskSection.appendChild(riskContent);
            mainContainer.appendChild(riskSection);
        }
        
        // Add skill development section
        if (data.skill_development) {
            const skillSection = document.createElement('div');
            skillSection.className = 'quarterly-section skill-development-section';
            
            skillSection.innerHTML = `<h5>Skill Development
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Assessment of skills demonstrated and developed during the quarter.</span>
                </span>
            </h5>`;
            
            const skillContent = document.createElement('div');
            skillContent.className = 'skill-content';
            
            // Add key capabilities if available
            if (data.skill_development.key_capabilities && data.skill_development.key_capabilities.length > 0) {
                const capabilitiesTitle = document.createElement('h6');
                capabilitiesTitle.textContent = 'Key Capabilities';
                skillContent.appendChild(capabilitiesTitle);
                
                const capabilitiesList = document.createElement('div');
                capabilitiesList.className = 'capabilities-list';
                
                data.skill_development.key_capabilities.forEach(capability => {
                    const capabilityItem = document.createElement('div');
                    capabilityItem.className = 'key-capability';
                    
                    if (typeof capability === 'string') {
                        capabilityItem.textContent = capability;
                    } else {
                        // Create capability header if name exists
                        if (capability.name || capability.skill) {
                            const capabilityHeader = document.createElement('h6');
                            capabilityHeader.textContent = capability.name || capability.skill;
                            capabilityItem.appendChild(capabilityHeader);
                        }
                        
                        // Add proficiency level if available
                        if (capability.proficiency || capability.level) {
                            const proficiencyText = document.createElement('div');
                            proficiencyText.className = 'capability-proficiency';
                            proficiencyText.innerHTML = `<strong>Proficiency:</strong> ${capability.proficiency || capability.level}`;
                            capabilityItem.appendChild(proficiencyText);
                        }
                        
                        // Add evidence if available
                        if (capability.evidence || capability.examples) {
                            const evidenceText = document.createElement('div');
                            evidenceText.className = 'capability-evidence';
                            evidenceText.innerHTML = `<strong>Evidence:</strong> ${capability.evidence || capability.examples}`;
                            capabilityItem.appendChild(evidenceText);
                        }
                    }
                    
                    capabilitiesList.appendChild(capabilityItem);
                });
                
                skillContent.appendChild(capabilitiesList);
            }
            
            // Add development focus if available
            if (data.development_focus) {
                const focusContainer = document.createElement('div');
                focusContainer.className = 'development-focus';
                
                const focusTitle = document.createElement('h6');
                focusTitle.textContent = 'Recommended Development Focus';
                focusContainer.appendChild(focusTitle);
                
                const focusText = document.createElement('p');
                focusText.textContent = data.development_focus;
                focusContainer.appendChild(focusText);
                
                skillContent.appendChild(focusContainer);
            }
            
            skillSection.appendChild(skillContent);
            mainContainer.appendChild(skillSection);
        }
        
        // Add forward planning section
        if (data.forward_planning) {
            const planningSection = document.createElement('div');
            planningSection.className = 'quarterly-section forward-planning-section';
            
            planningSection.innerHTML = `<h5>Forward Planning
                <span class="tooltip-trigger">
                    <i class="fas fa-info-circle"></i>
                    <span class="tooltip">Recommendations for activities to continue, improve, start, and stop.</span>
                </span>
            </h5>`;
            
            const planningContent = document.createElement('div');
            planningContent.className = 'planning-content';
            
            // Handle different possible structures for forward planning
            const continueSectionTitle = document.createElement('h6');
            continueSectionTitle.textContent = 'Continue';
            planningContent.appendChild(continueSectionTitle);
            
            const continueList = document.createElement('ul');
            continueList.className = 'continue-list';
            
            // Try to extract "continue" items from different possible structures
            let continueItems = [];
            if (data.forward_planning.continue) {
                continueItems = data.forward_planning.continue;
            } else if (data.forward_planning.activities_to_continue) {
                continueItems = data.forward_planning.activities_to_continue;
            } else if (Array.isArray(data.forward_planning)) {
                // If it's just an array, assume it contains all recommendations
                continueItems = data.forward_planning.filter(item => 
                    item.type === 'continue' || item.category === 'continue'
                );
            }
            
            // Add continue items
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
            
            planningContent.appendChild(continueList);
            
            // Add improve section
            const improveSectionTitle = document.createElement('h6');
            improveSectionTitle.textContent = 'Improve';
            planningContent.appendChild(improveSectionTitle);
            
            const improveList = document.createElement('ul');
            improveList.className = 'improve-list';
            
            // Try to extract "improve" items
            let improveItems = [];
            if (data.forward_planning.improve) {
                improveItems = data.forward_planning.improve;
            } else if (data.forward_planning.activities_to_improve) {
                improveItems = data.forward_planning.activities_to_improve;
            } else if (Array.isArray(data.forward_planning)) {
                improveItems = data.forward_planning.filter(item => 
                    item.type === 'improve' || item.category === 'improve'
                );
            }
            
            // Add improve items
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
            
            planningContent.appendChild(improveList);
            
            // Add similar sections for start and stop items...
            
            planningSection.appendChild(planningContent);
            mainContainer.appendChild(planningSection);
        }
        
        // Add to main results container
        analysisResults.appendChild(mainContainer);
        analysisResults.style.display = 'block';
        
        // Scroll to the results
        analysisResults.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Export functions to global scope
    window.quarterlyAnalysis = {
        displayQuarterlyAnalysisResults: displayQuarterlyAnalysisResults
    };
})();

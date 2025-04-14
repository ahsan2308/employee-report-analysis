document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const analysisForm = document.getElementById('analysisForm');
    const analysisResultsSection = document.getElementById('analysisResultsSection');
    const loadingAnalysis = document.getElementById('loadingAnalysis');
    const analysisResults = document.getElementById('analysisResults');
    const statusMessage = document.getElementById('statusMessage');
    const reportIdField = document.getElementById('reportId');

    // Initially hide results section
    analysisResultsSection.style.display = 'none';
    loadingAnalysis.style.display = 'none';

    // Check if we have a report_id in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const reportIdFromUrl = urlParams.get('report_id');
    
    // If we have a report_id in the URL, set it in the form and trigger analysis
    if (reportIdFromUrl) {
        reportIdField.value = reportIdFromUrl;
        // Automatically trigger analysis if report_id is in URL
        analyzeReport(reportIdFromUrl);
    }

    // Add event listener for form submission
    analysisForm.addEventListener('submit', function(event) {
        event.preventDefault();

        // Get form data
        const reportId = reportIdField.value;

        // Trigger analysis
        analyzeReport(reportId);
    });

    // Analyze a specific report
    async function analyzeReport(reportId) {
        try {
            // Show analysis results section and loading indicator
            analysisResultsSection.style.display = 'block';
            loadingAnalysis.style.display = 'block';
            analysisResults.innerHTML = '';
            showStatus('Analyzing report...', 'loading');

            // Fetch analysis
            const analysis = await analysisApi.analyzeReport(reportId);

            // Hide loading
            loadingAnalysis.style.display = 'none';
            statusMessage.innerHTML = '';

            // Check if there's an error in the response
            if (analysis.error) {
                showError(`API Error: ${analysis.error}`);
                return;
            }

            // Display analysis results
            displayAnalysisResults(analysis, reportId);
            
            // Show success message after analysis is complete
            showSuccess('Analysis completed successfully!');

        } catch (error) {
            // Handle errors
            loadingAnalysis.style.display = 'none';
            showError('Error analyzing report: ' + error.message);
        }
    }

    // Display the analysis results in a formatted way
    function displayAnalysisResults(analysis, reportId) {
        console.log("Analysis response:", analysis); // Log the full response for debugging
        
        // Extract data from full_analysis_json if it exists, otherwise from the root object
        const fullAnalysis = analysis.full_analysis_json || analysis;
        
        // Safely get values from the analysis object with fallbacks
        const sentiment = (fullAnalysis.sentiment || "neutral").toLowerCase();
        const riskLevel = (fullAnalysis.risk_level || "low").toLowerCase();
        const riskExplanation = fullAnalysis.risk_explanation || 'No explanation provided';
        
        // Get topics from full_analysis_json
        const topics = fullAnalysis.topics || [];
        const achievements = fullAnalysis.achievements || [];
        const challenges = fullAnalysis.challenges || [];
        const actionItems = fullAnalysis.action_items || [];

        // Create a container for the results
        let resultsHTML = `
            <div class="analysis-container">
                <h4>Analysis Results for Report ID: ${reportId}</h4>
                <div class="analysis-section">
                    <h5>Overview</h5>
                    <p><strong>Sentiment:</strong> <span class="sentiment-${sentiment}">${capitalizeFirstLetter(sentiment)}</span></p>
                    <p><strong>Risk Level:</strong> <span class="risk-${riskLevel}">${capitalizeFirstLetter(riskLevel)}</span></p>
                    <p><strong>Risk Explanation:</strong> ${riskExplanation}</p>
                </div>
        `;

        // Add topics section if available
        if (topics && topics.length > 0) {
            resultsHTML += `
                <div class="analysis-section">
                    <h5>Key Topics</h5>
                    <div class="topics-container">
            `;
            
            topics.forEach(topic => {
                resultsHTML += `<span class="topic-tag">${topic}</span>`;
            });
            
            resultsHTML += `
                    </div>
                </div>
            `;
        }

        // Add achievements section if available
        if (achievements && achievements.length > 0) {
            resultsHTML += `
                <div class="analysis-section">
                    <h5>Achievements</h5>
                    <ul>
            `;
            
            achievements.forEach(achievement => {
                const description = achievement.description || 'No description';
                const impact = achievement.impact || 'Unknown impact';
                
                resultsHTML += `
                    <li>
                        <p><strong>${description}</strong></p>
                        <p>Impact: ${impact}</p>
                    </li>
                `;
            });
            
            resultsHTML += `
                    </ul>
                </div>
            `;
        }

        // Add challenges section if available
        if (challenges && challenges.length > 0) {
            resultsHTML += `
                <div class="analysis-section">
                    <h5>Challenges</h5>
                    <ul>
            `;
            
            challenges.forEach(challenge => {
                const description = challenge.description || 'No description';
                const severity = (challenge.severity || "medium").toLowerCase();
                
                resultsHTML += `
                    <li>
                        <p><strong>${description}</strong></p>
                        <p>Severity: <span class="severity-${severity}">${capitalizeFirstLetter(severity)}</span></p>
                    </li>
                `;
            });
            
            resultsHTML += `
                    </ul>
                </div>
            `;
        }

        // Add action items if available
        if (actionItems && actionItems.length > 0) {
            resultsHTML += `
                <div class="analysis-section">
                    <h5>Recommended Actions</h5>
                    <ul>
            `;
            
            actionItems.forEach(action => {
                resultsHTML += `<li>${action}</li>`;
            });
            
            resultsHTML += `
                    </ul>
                </div>
            `;
        }

        // Close the container
        resultsHTML += `</div>`;

        // Insert the results into the page
        analysisResults.innerHTML = resultsHTML;
    }

    // Helper function to capitalize the first letter of a string
    function capitalizeFirstLetter(string) {
        if (!string) return '';
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    // Helper functions for UI messages
    function showError(message) {
        statusMessage.innerHTML = `<div class="error-message">${message}</div>`;
    }

    function showSuccess(message) {
        statusMessage.innerHTML = `<div class="success-message">${message}</div>`;
        // Clear message after 3 seconds
        setTimeout(() => {
            statusMessage.innerHTML = '';
        }, 3000);
    }

    function showStatus(message, type) {
        statusMessage.innerHTML = `<div class="loading-message">${message}</div>`;
    }
});
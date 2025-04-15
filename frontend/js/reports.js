document.addEventListener('DOMContentLoaded', function() {
    // Get elements - sections
    const selectEmployeeSection = document.getElementById('selectEmployeeSection');
    const reportsSection = document.getElementById('reportsSection');
    const reportsListSection = document.getElementById('reportsListSection');
    
    // Get elements - interactive components
    const employeeSelect = document.getElementById('employeeSelect');
    const viewReportsBtn = document.getElementById('viewReportsBtn');
    const addReportBtn = document.getElementById('addReportBtn');
    const newReportBtn = document.getElementById('newReportBtn');
    const backToListBtn = document.getElementById('backToListBtn');
    const selectAnotherEmployeeBtn = document.getElementById('selectAnotherEmployeeBtn');
    
    // Get elements - content display
    const employeeInfo = document.getElementById('employeeInfo');
    const employeeInfoHeader = document.getElementById('employeeInfoHeader');
    const employeeIdField = document.getElementById('employeeId');
    const reportForm = document.getElementById('reportForm');
    const reportsTable = document.getElementById('reportsTable');
    const reportList = document.getElementById('reportList');
    const loadingReports = document.getElementById('loadingReports');
    const statusMessage = document.getElementById('statusMessage');

    // Track if reports have been loaded for the current employee
    let reportsLoaded = false;
    let currentEmployeeId = null;

    // Check if we have an employee_id in the URL
    const urlParams = new URLSearchParams(window.location.search);
    const employeeIdFromUrl = urlParams.get('employee_id');

    // Load all employees for the dropdown
    loadEmployees();
    
    // If we have an employee_id in the URL, directly show reports for that employee
    if (employeeIdFromUrl) {
        employeeIdField.value = employeeIdFromUrl;
        currentEmployeeId = employeeIdFromUrl;
        selectEmployeeSection.style.display = 'none';
        reportsListSection.style.display = 'block';
        loadReportsForEmployee(employeeIdFromUrl);
    }

    // Add event listeners for buttons
    viewReportsBtn.addEventListener('click', function() {
        const selectedEmployeeId = employeeSelect.value;
        if (selectedEmployeeId) {
            employeeIdField.value = selectedEmployeeId;
            currentEmployeeId = selectedEmployeeId;
            reportsLoaded = false; // Reset the reports loaded flag
            selectEmployeeSection.style.display = 'none';
            reportsListSection.style.display = 'block';
            reportsSection.style.display = 'none';
            loadReportsForEmployee(selectedEmployeeId);
        } else {
            alert('Please select an employee');
        }
    });

    addReportBtn.addEventListener('click', function() {
        const selectedEmployeeId = employeeSelect.value;
        if (selectedEmployeeId) {
            employeeIdField.value = selectedEmployeeId;
            currentEmployeeId = selectedEmployeeId;
            loadEmployeeInfo(selectedEmployeeId, employeeInfo);
            selectEmployeeSection.style.display = 'none';
            reportsListSection.style.display = 'none';
            reportsSection.style.display = 'block';
        } else {
            alert('Please select an employee');
        }
    });

    newReportBtn.addEventListener('click', function() {
        loadEmployeeInfo(currentEmployeeId, employeeInfo);
        reportsListSection.style.display = 'none';
        reportsSection.style.display = 'block';
    });

    backToListBtn.addEventListener('click', function() {
        reportsSection.style.display = 'none';
        reportsListSection.style.display = 'block';
        
        // Only reload reports if they haven't been loaded yet for this employee
        if (!reportsLoaded && currentEmployeeId) {
            loadReportsForEmployee(currentEmployeeId);
        }
    });

    selectAnotherEmployeeBtn.addEventListener('click', function() {
        reportsListSection.style.display = 'none';
        reportsSection.style.display = 'none';
        selectEmployeeSection.style.display = 'block';
        
        // Reset the dropdown to show no selection
        employeeSelect.value = "";
        
        // Clear the current employee flag
        currentEmployeeId = null;
        reportsLoaded = false;
    });

    // Add event listener for form submission
    reportForm.addEventListener('submit', function(event) {
        event.preventDefault();

        // Get form data for the structured report form
        const reportData = {
            employee_id: parseInt(employeeIdField.value, 10),
            key_tasks_completed: document.getElementById('keyTasksCompleted').value,
            impact_outcome: document.getElementById('impactOutcome').value,
            challenges_faced: document.getElementById('challengesFaced').value,
            support_required: document.getElementById('supportRequired').value,
            tasks_planned_next_week: document.getElementById('tasksPlannedNextWeek').value,
            confidence_level: parseInt(document.getElementById('confidenceLevel').value, 10),
            nothing_to_report_reason: document.getElementById('nothingToReportReason').value || null
        };

        // Create report using the form endpoint
        submitReportForm(reportData);
    });

    // Load all employees for the dropdown
    async function loadEmployees() {
        try {
            // Fetch employees
            const employees = await employeeApi.getAllEmployees();
            
            // Populate dropdown
            employees.forEach(employee => {
                const option = document.createElement('option');
                option.value = employee.id;
                option.textContent = `${employee.name} (${employee.position}, ${employee.wing})`;
                employeeSelect.appendChild(option);
            });
            
            // If we have an employee_id in the URL, select that employee in the dropdown
            if (employeeIdFromUrl) {
                employeeSelect.value = employeeIdFromUrl;
            }
        } catch (error) {
            console.error('Error loading employees:', error);
            alert('Error loading employees. Please try again later.');
        }
    }

    // Load employee info into a container
    async function loadEmployeeInfo(employeeId, container) {
        try {
            // Fetch employee details
            const employees = await employeeApi.getAllEmployees();
            const employeeDetails = employees.find(emp => emp.id == employeeId);
            if (employeeDetails) {
                container.innerHTML = `<h3>Employee: ${employeeDetails.name} (${employeeDetails.position}, ${employeeDetails.wing})</h3>`;
                return employeeDetails;
            }
        } catch (error) {
            console.error('Error loading employee details:', error);
        }
        return null;
    }

    // Load reports for a specific employee
    async function loadReportsForEmployee(employeeId) {
        try {
            // Show loading
            loadingReports.style.display = 'block';
            reportsTable.style.display = 'none';

            // Fetch employee details for the header
            const employeeDetails = await loadEmployeeInfo(employeeId, employeeInfoHeader);

            // Fetch reports
            const response = await reportApi.getEmployeeReports(employeeId);
            
            // Hide loading
            loadingReports.style.display = 'none';
            
            // Mark reports as loaded for this employee
            reportsLoaded = true;

            // Check if response contains a message (no reports found)
            if (response.message && response.message.includes("No reports found")) {
                reportList.innerHTML = `
                    <div class="no-reports-message">
                        <p>${response.message}</p>
                        <p>Click "Add New Report" to submit your first report for this employee.</p>
                    </div>
                `;
                return;
            }

            // Get the reports array from the response
            const reports = response.reports || [];

            // If no reports, show message
            if (reports.length === 0) {
                reportList.innerHTML = `
                    <div class="no-reports-message">
                        <p>No reports found for this employee.</p>
                        <p>Click "Add New Report" to submit your first report.</p>
                    </div>
                `;
                return;
            }

            // Populate table
            const tableBody = reportsTable.querySelector('tbody');
            tableBody.innerHTML = '';

            reports.forEach(report => {
                // Truncate report text for display
                const reportText = report.report_text || "No content";
                const truncatedText = reportText.length > 100 ? 
                    reportText.substring(0, 100) + '...' : 
                    reportText;
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${report.report_id}</td>
                    <td>${report.report_date || 'N/A'}</td>
                    <td>${truncatedText}</td>
                    <td>
                        <button class="button analyze-report" data-id="${report.report_id}">Analyze</button>
                    </td>
                `;
                tableBody.appendChild(row);
            });

            // Add event listeners to the analyze buttons
            document.querySelectorAll('.analyze-report').forEach(button => {
                button.addEventListener('click', analyzeReport);
            });

            // Show table
            reportsTable.style.display = 'table';

        } catch (error) {
            // Handle errors
            loadingReports.style.display = 'none';
            showError('Error loading reports: ' + error.message);
        }
    }

    // Submit a structured report form
    async function submitReportForm(reportData) {
        try {
            // Show status
            showStatus('Submitting report...', 'loading');
            
            // Submit report using the form endpoint
            const result = await reportApi.submitReportForm(reportData);
            
            // Show success
            showSuccess('Report submitted successfully!');
            
            // Clear form (only the content fields, not the employee ID)
            document.getElementById('keyTasksCompleted').value = '';
            document.getElementById('impactOutcome').value = '';
            document.getElementById('challengesFaced').value = '';
            document.getElementById('supportRequired').value = '';
            document.getElementById('tasksPlannedNextWeek').value = '';
            document.getElementById('confidenceLevel').value = 3; // Reset to moderate
            document.getElementById('nothingToReportReason').value = '';
            
            // Reset the reports loaded flag
            reportsLoaded = false;
            
            // Switch to reports list view
            reportsSection.style.display = 'none';
            reportsListSection.style.display = 'block';
            
            // Reload reports
            if (currentEmployeeId) {
                loadReportsForEmployee(currentEmployeeId);
            }
            
        } catch (error) {
            // Handle errors
            showError('Error submitting report: ' + error.message);
        }
    }

    // Analyze report
    async function analyzeReport(event) {
        const reportId = event.target.getAttribute('data-id');
        showStatus(`Initiating analysis for report ${reportId}...`, 'loading');
        
        try {
            // Immediately redirect to the analysis page with the report ID
            // We'll let the analysis page handle the API call
            window.location.href = `analysis.html?report_id=${reportId}&auto_analyze=true`;
        } catch (error) {
            console.error('Error redirecting to analysis:', error);
            showError('Failed to navigate to analysis page. Please try again later.');
        }
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
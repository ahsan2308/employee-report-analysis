document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements - Import Form
    const importForm = document.getElementById('importForm');
    const csvFileInput = document.getElementById('csvFile');
    const csvTypeSelect = document.getElementById('csvType');
    const dryRunOption = document.getElementById('dryRunOption');
    const stopOnErrorOption = document.getElementById('stopOnErrorOption');
    const errorThresholdOption = document.getElementById('errorThresholdOption');
    const chunkSizeOption = document.getElementById('chunkSizeOption');
    const processingModeOption = document.getElementById('processingModeOption');
    const submitImportBtn = document.getElementById('submitImportBtn');
    const downloadTemplateLink = document.getElementById('downloadTemplateLink');
    
    // DOM Elements - Sections
    const csvImportSection = document.getElementById('csvImportSection');
    const activeJobSection = document.getElementById('activeJobSection');
    const errorSection = document.getElementById('errorSection');
    const importHistorySection = document.getElementById('importHistorySection');
    
    // DOM Elements - Job Details
    const jobFilename = document.getElementById('jobFilename');
    const jobType = document.getElementById('jobType');
    const jobStatus = document.getElementById('jobStatus');
    const jobSubmitted = document.getElementById('jobSubmitted');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const progressBar = document.getElementById('progressBar');
    
    // DOM Elements - General Metrics
    const processedRows = document.getElementById('processedRows');
    const successfulRows = document.getElementById('successfulRows');
    const errorsCount = document.getElementById('errorsCount');
    
    // DOM Elements - Employee Report Metrics
    const metricContainerEmployeeReport = document.getElementById('metricContainerEmployeeReport');
    const employeesCreated = document.getElementById('employeesCreated');
    const employeesUpdated = document.getElementById('employeesUpdated');
    const reportsCreated = document.getElementById('reportsCreated');
    const reportsUpdated = document.getElementById('reportsUpdated');
    
    // DOM Elements - Vision Data Metrics
    const metricContainerVisionData = document.getElementById('metricContainerVisionData');
    const visionRecordsCreated = document.getElementById('visionRecordsCreated');
    const visionRecordsUpdated = document.getElementById('visionRecordsUpdated');
    
    // DOM Elements - Template Buttons
    const employeeReportTemplateBtn = document.getElementById('employeeReportTemplateBtn');
    const visionDataTemplateBtn = document.getElementById('visionDataTemplateBtn');
    const employeeReportTemplate = document.getElementById('employeeReportTemplate');
    const visionDataTemplate = document.getElementById('visionDataTemplate');
    const downloadEmployeeReportTemplate = document.getElementById('downloadEmployeeReportTemplate');
    const downloadVisionDataTemplate = document.getElementById('downloadVisionDataTemplate');
    
    // DOM Elements - Buttons
    const viewErrorsBtn = document.getElementById('viewErrorsBtn');
    const backToImportBtn = document.getElementById('backToImportBtn');
    const backToJobBtn = document.getElementById('backToJobBtn');
    const prevErrorsBtn = document.getElementById('prevErrorsBtn');
    const nextErrorsBtn = document.getElementById('nextErrorsBtn');
    
    // DOM Elements - Error Display
    const errorFilename = document.getElementById('errorFilename');
    const totalErrors = document.getElementById('totalErrors');
    const errorList = document.getElementById('errorList');
    const errorPagination = document.getElementById('errorPagination');
    
    // DOM Elements - Import History
    const loadingHistory = document.getElementById('loadingHistory');
    const jobsTable = document.getElementById('jobsTable');
    const noJobsMessage = document.getElementById('noJobsMessage');
    
    // DOM Elements - Status Message
    const statusMessage = document.getElementById('statusMessage');
    
    // DOM Elements - Modal
    const errorModal = document.getElementById('errorModal');
    const errorModalContent = document.getElementById('errorModalContent');
    const closeModalBtns = document.querySelectorAll('.close-modal');
    
    // State Variables
    let currentJobId = null;
    let pollingInterval = null;
    let errorCurrentPage = 1;
    let errorPageSize = 10;
    let errorTotalPages = 1;
    let jobCheckInterval = 2000; // 2 seconds

    // ------------- INITIALIZATION -------------
    
    // Load import history on page load
    loadImportHistory();
    
    // Check if job ID is in URL (for direct linking to a job)
    const urlParams = new URLSearchParams(window.location.search);
    const jobIdFromUrl = urlParams.get('job_id');
    
    if (jobIdFromUrl) {
        loadAndDisplayJob(jobIdFromUrl);
    }
    
    // ------------- EVENT LISTENERS -------------
    
    // CSV Type selector change
    csvTypeSelect.addEventListener('change', function() {
        updateTemplateLink();
    });
    
    // Template button clicks
    employeeReportTemplateBtn.addEventListener('click', function() {
        toggleTemplateSection('employee_report');
    });
    
    visionDataTemplateBtn.addEventListener('click', function() {
        toggleTemplateSection('vision_data');
    });
    
    // Download template links
    downloadEmployeeReportTemplate.addEventListener('click', function(event) {
        event.preventDefault();
        generateAndDownloadTemplate('employee_report');
    });
    
    downloadVisionDataTemplate.addEventListener('click', function(event) {
        event.preventDefault();
        generateAndDownloadTemplate('vision_data');
    });
    
    // Form submission
    importForm.addEventListener('submit', function(event) {
        event.preventDefault();
        if (validateForm()) {
            submitImport();
        }
    });
    
    // Navigation buttons
    backToImportBtn.addEventListener('click', function() {
        stopPolling();
        activeJobSection.style.display = 'none';
        csvImportSection.style.display = 'block';
        currentJobId = null;
        updateUrlWithoutReload(null);
    });
    
    viewErrorsBtn.addEventListener('click', function() {
        if (currentJobId) {
            loadErrors(currentJobId, 1);
            activeJobSection.style.display = 'none';
            errorSection.style.display = 'block';
        }
    });
    
    backToJobBtn.addEventListener('click', function() {
        errorSection.style.display = 'none';
        activeJobSection.style.display = 'block';
    });
    
    // Pagination controls
    prevErrorsBtn.addEventListener('click', function() {
        if (errorCurrentPage > 1) {
            loadErrors(currentJobId, errorCurrentPage - 1);
        }
    });
    
    nextErrorsBtn.addEventListener('click', function() {
        if (errorCurrentPage < errorTotalPages) {
            loadErrors(currentJobId, errorCurrentPage + 1);
        }
    });
    
    // Modal controls
    closeModalBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            errorModal.style.display = 'none';
        });
    });
    
    // Close modal when clicking outside of it
    window.addEventListener('click', function(event) {
        if (event.target === errorModal) {
            errorModal.style.display = 'none';
        }
    });
    
    // Download template link
    downloadTemplateLink.addEventListener('click', function(event) {
        event.preventDefault();
        generateAndDownloadTemplate();
    });
    
    // ------------- FUNCTIONS -------------
    
    // Toggle template section
    function toggleTemplateSection(type) {
        if (type === 'employee_report') {
            employeeReportTemplateBtn.classList.add('primary-button');
            employeeReportTemplateBtn.classList.remove('secondary-button');
            visionDataTemplateBtn.classList.add('secondary-button');
            visionDataTemplateBtn.classList.remove('primary-button');
            employeeReportTemplate.style.display = 'block';
            visionDataTemplate.style.display = 'none';
        } else {
            employeeReportTemplateBtn.classList.add('secondary-button');
            employeeReportTemplateBtn.classList.remove('primary-button');
            visionDataTemplateBtn.classList.add('primary-button');
            visionDataTemplateBtn.classList.remove('secondary-button');
            employeeReportTemplate.style.display = 'none';
            visionDataTemplate.style.display = 'block';
        }
    }
    
    // Update template link based on selected CSV type
    function updateTemplateLink() {
        const selectedType = csvTypeSelect.value;
        if (selectedType === 'vision_data') {
            downloadTemplateLink.setAttribute('data-type', 'vision_data');
            // Also update the template section
            toggleTemplateSection('vision_data');
        } else {
            // Default to employee_report for empty or employee_report
            downloadTemplateLink.setAttribute('data-type', 'employee_report');
            toggleTemplateSection('employee_report');
        }
    }
    
    // Form validation
    function validateForm() {
        // Check if a file is selected
        if (!csvFileInput.files || csvFileInput.files.length === 0) {
            showMessage('Please select a CSV file to import.', 'error');
            return false;
        }
        
        // Check if file is a CSV file
        const file = csvFileInput.files[0];
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showMessage('Selected file must be a CSV file.', 'error');
            return false;
        }
        
        // Check error threshold is between 0-100
        const threshold = parseInt(errorThresholdOption.value);
        if (isNaN(threshold) || threshold < 0 || threshold > 100) {
            showMessage('Error threshold must be between 0 and 100.', 'error');
            return false;
        }
        
        return true;
    }
    
    // Submit import
    async function submitImport() {
        showMessage('Preparing to upload file...', 'loading');
        submitImportBtn.disabled = true;
        
        try {
            const formData = new FormData(importForm);
            
            // Add checkbox values explicitly because FormData doesn't handle them well
            formData.set('dry_run', dryRunOption.checked);
            formData.set('stop_on_error', stopOnErrorOption.checked);
            
            // If CSV type is empty (auto-detect), remove it from the form data
            if (!csvTypeSelect.value) {
                formData.delete('csv_type');
            }
            
            // Send the form data
            const result = await importApi.uploadCSV(formData);
            
            // Show success message
            showMessage(`File uploaded successfully! Job ID: ${result.job_id}`, 'success');
            
            // Start monitoring the job
            currentJobId = result.job_id;
            updateUrlWithoutReload(currentJobId);
            displayJobDetails(result);
            startPolling(currentJobId);
            
            // Switch to active job view
            csvImportSection.style.display = 'none';
            activeJobSection.style.display = 'block';
            
        } catch (error) {
            console.error('Error uploading file:', error);
            showMessage(`Error uploading file: ${error.message || 'Unknown error'}`, 'error');
            submitImportBtn.disabled = false;
        }
    }
    
    // Start polling for job status
    function startPolling(jobId) {
        // Clear any existing interval
        stopPolling();
        
        // Set up new polling interval
        pollingInterval = setInterval(async function() {
            try {
                const jobDetails = await importApi.getJobStatus(jobId);
                updateJobDisplay(jobDetails);
                
                // If the job is complete, stop polling
                if (jobDetails.status === 'completed' || jobDetails.status === 'failed') {
                    stopPolling();
                    // Update import history
                    loadImportHistory();
                }
            } catch (error) {
                console.error('Error polling job status:', error);
                showMessage(`Error checking job status: ${error.message}`, 'error');
            }
        }, jobCheckInterval);
    }
    
    // Stop polling for job status
    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }
    
    // Update job details display
    function updateJobDisplay(jobDetails) {
        // Update status and details
        jobStatus.textContent = capitalizeFirst(jobDetails.status);
        jobStatus.className = `detail-value status-${jobDetails.status}`;
        
        // Update CSV type if available
        if (jobDetails.csv_type) {
            jobType.textContent = formatCsvType(jobDetails.csv_type);
            // Show appropriate metrics based on CSV type
            updateMetricsDisplay(jobDetails);
        } else {
            jobType.textContent = 'Auto-Detect';
        }
        
        // Update progress bar and text
        const percentComplete = jobDetails.percent_complete || 0;
        progressBar.style.width = `${percentComplete}%`;
        progressPercent.textContent = `${percentComplete}%`;
        progressText.textContent = `Processing: ${jobDetails.processed_rows}/${jobDetails.total_rows} rows`;
        
        // Update general metrics
        processedRows.textContent = jobDetails.processed_rows;
        successfulRows.textContent = jobDetails.successful_rows;
        errorsCount.textContent = jobDetails.error_count;
        
        // Show/hide error button based on error count
        if (jobDetails.error_count > 0) {
            viewErrorsBtn.style.display = 'inline-block';
        } else {
            viewErrorsBtn.style.display = 'none';
        }
        
        // Add appropriate styling based on status
        if (jobDetails.status === 'completed') {
            progressBar.classList.add('complete');
            progressBar.classList.remove('error');
        } else if (jobDetails.status === 'failed') {
            progressBar.classList.add('error');
            progressBar.classList.remove('complete');
        } else {
            progressBar.classList.remove('complete', 'error');
        }
    }
    
    // Format CSV type for display
    function formatCsvType(type) {
        if (!type) return 'Unknown';
        
        switch (type) {
            case 'employee_report':
                return 'Employee Reports';
            case 'vision_data':
                return 'Vision Data';
            default:
                return capitalizeFirst(type.replace('_', ' '));
        }
    }
    
    // Update metrics display based on CSV type
    function updateMetricsDisplay(jobDetails) {
        const metrics = jobDetails.metrics || {};
        
        if (jobDetails.csv_type === 'employee_report') {
            // Show Employee Report metrics
            metricContainerEmployeeReport.style.display = 'flex';
            metricContainerVisionData.style.display = 'none';
            
            // Update metrics values
            employeesCreated.textContent = metrics.employees_created || 0;
            employeesUpdated.textContent = metrics.employees_updated || 0;
            reportsCreated.textContent = metrics.reports_created || 0;
            reportsUpdated.textContent = metrics.reports_updated || 0;
        } 
        else if (jobDetails.csv_type === 'vision_data') {
            // Show Vision Data metrics
            metricContainerEmployeeReport.style.display = 'none';
            metricContainerVisionData.style.display = 'flex';
            
            // Update metrics values
            visionRecordsCreated.textContent = metrics.vision_records_created || 0;
            visionRecordsUpdated.textContent = metrics.vision_records_updated || 0;
        }
        else {
            // Hide specific metrics if type is unknown
            metricContainerEmployeeReport.style.display = 'none';
            metricContainerVisionData.style.display = 'none';
        }
    }
    
    // Display initial job details
    function displayJobDetails(jobDetails) {
        jobFilename.textContent = jobDetails.filename;
        jobSubmitted.textContent = formatDateTime(new Date(jobDetails.submitted_at));
        
        // Initial update of the job display
        updateJobDisplay(jobDetails);
    }
    
    // Load errors for a job
    async function loadErrors(jobId, page = 1) {
        errorList.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading errors...</p></div>';
        
        try {
            const errorData = await importApi.getJobErrors(jobId, page, errorPageSize);
            
            // Update error display
            errorFilename.textContent = jobsTable.querySelector(`[data-job-id="${jobId}"]`)?.dataset.filename || 'Unknown';
            totalErrors.textContent = errorData.total;
            
            // Update pagination
            errorCurrentPage = page;
            errorTotalPages = Math.ceil(errorData.total / errorPageSize);
            errorPagination.textContent = `Page ${errorCurrentPage} of ${errorTotalPages}`;
            
            // Enable/disable pagination buttons
            prevErrorsBtn.disabled = errorCurrentPage <= 1;
            nextErrorsBtn.disabled = errorCurrentPage >= errorTotalPages;
            
            // Display errors
            displayErrors(errorData.errors);
            
        } catch (error) {
            console.error('Error loading errors:', error);
            errorList.innerHTML = `<div class="error-message">Error loading errors: ${error.message}</div>`;
        }
    }
    
    // Display error list
    function displayErrors(errors) {
        if (!errors || errors.length === 0) {
            errorList.innerHTML = '<div class="info-message">No errors found.</div>';
            return;
        }
        
        let html = '';
        
        errors.forEach(error => {
            html += `
                <div class="error-item" data-row="${error.row_number}">
                    <div class="error-header">
                        <div class="error-row">Row ${error.row_number}</div>
                        <div class="error-field">${error.field_name || 'Row-level error'}</div>
                    </div>
                    <div class="error-message">${escapeHtml(error.error_message)}</div>
                    <div class="error-actions">
                        <button class="view-row-data-btn button small-button" data-row="${error.row_number}">
                            <i class="fas fa-eye"></i> View Row Data
                        </button>
                    </div>
                    <div class="row-data" style="display: none;">
                        ${formatRowData(error.row_data)}
                    </div>
                </div>
            `;
        });
        
        errorList.innerHTML = html;
        
        // Add event listeners to view row data buttons
        document.querySelectorAll('.view-row-data-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const rowNum = this.getAttribute('data-row');
                const rowDataDiv = this.closest('.error-item').querySelector('.row-data');
                
                if (rowDataDiv.style.display === 'none') {
                    rowDataDiv.style.display = 'block';
                    this.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Row Data';
                } else {
                    rowDataDiv.style.display = 'none';
                    this.innerHTML = '<i class="fas fa-eye"></i> View Row Data';
                }
            });
        });
    }
    
    // Format row data for display
    function formatRowData(rowData) {
        if (!rowData) return 'No row data available';
        
        let html = '<table class="row-data-table">';
        html += '<tr><th>Field</th><th>Value</th></tr>';
        
        Object.entries(rowData).forEach(([key, value]) => {
            html += `<tr>
                <td>${escapeHtml(key)}</td>
                <td>${escapeHtml(value !== null ? value : 'null')}</td>
            </tr>`;
        });
        
        html += '</table>';
        return html;
    }
    
    // Load import history
    async function loadImportHistory() {
        loadingHistory.style.display = 'block';
        jobsTable.style.display = 'none';
        noJobsMessage.style.display = 'none';
        
        try {
            const jobs = await importApi.getJobsList();
            
            if (!jobs || jobs.length === 0) {
                loadingHistory.style.display = 'none';
                noJobsMessage.style.display = 'block';
                return;
            }
            
            // Populate the table
            const tableBody = jobsTable.querySelector('tbody');
            tableBody.innerHTML = '';
            
            jobs.forEach(job => {
                const row = document.createElement('tr');
                row.setAttribute('data-job-id', job.job_id);
                row.setAttribute('data-filename', job.filename);
                
                row.innerHTML = `
                    <td>${job.filename}</td>
                    <td>${formatDateTime(new Date(job.submitted_at))}</td>
                    <td><span class="status-badge status-${job.status}">${capitalizeFirst(job.status)}</span></td>
                    <td>${job.successful_rows}/${job.total_rows}</td>
                    <td>${job.error_count > 0 ? `<span class="error-count">${job.error_count}</span>` : '0'}</td>
                    <td>
                        <button class="view-job-btn button small-button" data-job-id="${job.job_id}">
                            <i class="fas fa-eye"></i> View
                        </button>
                        ${job.error_count > 0 ? `
                        <button class="view-job-errors-btn button small-button" data-job-id="${job.job_id}">
                            <i class="fas fa-exclamation-triangle"></i> Errors
                        </button>
                        ` : ''}
                    </td>
                `;
                
                tableBody.appendChild(row);
            });
            
            // Add event listeners to view buttons
            document.querySelectorAll('.view-job-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const jobId = this.getAttribute('data-job-id');
                    loadAndDisplayJob(jobId);
                });
            });
            
            document.querySelectorAll('.view-job-errors-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const jobId = this.getAttribute('data-job-id');
                    currentJobId = jobId;
                    loadErrors(jobId, 1);
                    
                    // Navigate to errors section
                    csvImportSection.style.display = 'none';
                    activeJobSection.style.display = 'none';
                    errorSection.style.display = 'block';
                    updateUrlWithoutReload(jobId);
                });
            });
            
            // Show the table
            loadingHistory.style.display = 'none';
            jobsTable.style.display = 'table';
            
        } catch (error) {
            console.error('Error loading import history:', error);
            loadingHistory.style.display = 'none';
            showMessage(`Error loading import history: ${error.message}`, 'error');
        }
    }
    
    // Load and display job details
    async function loadAndDisplayJob(jobId) {
        try {
            const jobDetails = await importApi.getJobStatus(jobId);
            currentJobId = jobId;
            
            // Update URL with job ID without reloading the page
            updateUrlWithoutReload(jobId);
            
            // Display job details
            displayJobDetails(jobDetails);
            
            // Show active job section and hide others
            csvImportSection.style.display = 'none';
            activeJobSection.style.display = 'block';
            errorSection.style.display = 'none';
            
            // Start polling if the job is still in progress
            if (jobDetails.status === 'pending' || jobDetails.status === 'running') {
                startPolling(jobId);
            } else if (jobDetails.error_count > 0) {
                // Enable view errors button if there are errors
                viewErrorsBtn.style.display = 'inline-block';
            }
            
        } catch (error) {
            console.error('Error loading job:', error);
            showMessage(`Error loading job details: ${error.message}`, 'error');
        }
    }
    
    // Generate and download CSV template
    function generateAndDownloadTemplate(templateType = 'employee_report') {
        if (templateType === 'employee_report') {
            // Define template headers and a sample row for employee reports
            const headers = [
                'Employee_ID', 'Name', 'Designation', 'BPS', 'Office_Hierarchy',
                'From', 'To', 'Tasks_Completed', 'Impact', 'Challenges',
                'Support_Required', 'Tasks_Planned', 'Confidence_Level', 'NTR'
            ];
            
            const sampleRow = [
                '101', 'John Doe', 'Software Engineer', 'BS-17', 'Technology>Development',
                '2023-10-01', '2023-10-07', 'Completed API documentation', 'Improved developer onboarding',
                'Integration issues with legacy systems', 'More testing resources', 'Start on new authentication module', '4', ''
            ];
            
            // Create CSV content
            let csvContent = headers.join(',') + '\n' + sampleRow.join(',');
            downloadCSV(csvContent, 'employee_reports_template.csv');
        }
        else if (templateType === 'vision_data') {
            // Define template headers and a sample row for vision data
            const headers = [
                'Employee_ID', 'From_Date', 'To_Date', 'Main_Entity', 'Sub_Entities'
            ];
            
            const sampleRow = [
                '101', '2023-10-01', '2023-10-31', 'Tasks', 'Analysis:5, Reporting:3, Planning:2'
            ];
            
            // Create CSV content
            let csvContent = headers.join(',') + '\n' + sampleRow.join(',');
            downloadCSV(csvContent, 'vision_data_template.csv');
        }
    }
    
    // Download CSV helper
    function downloadCSV(csvContent, filename) {
        // Create download link
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.setAttribute('hidden', '');
        a.setAttribute('href', url);
        a.setAttribute('download', filename);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
    
    // Download template based on current selection
    downloadTemplateLink.addEventListener('click', function(event) {
        event.preventDefault();
        const templateType = downloadTemplateLink.getAttribute('data-type') || 
                            csvTypeSelect.value || 
                            'employee_report';
        generateAndDownloadTemplate(templateType);
    });
    
    // ------------- UTILITY FUNCTIONS -------------
    
    // Show message with appropriate styling
    function showMessage(message, type = 'info') {
        if (!statusMessage) return;
        
        if (type === 'loading') {
            statusMessage.innerHTML = `<div class="loading-message">${message}</div>`;
        } else if (type === 'error') {
            statusMessage.innerHTML = `<div class="error-message">${message}</div>`;
        } else if (type === 'success') {
            statusMessage.innerHTML = `<div class="success-message">${message}</div>`;
            
            // Auto-hide success messages after 5 seconds
            setTimeout(() => {
                if (statusMessage.querySelector('.success-message')) {
                    statusMessage.innerHTML = '';
                }
            }, 5000);
        } else { // info
            statusMessage.innerHTML = `<div class="info-message">${message}</div>`;
        }
    }
    
    // Format date-time for display
    function formatDateTime(date) {
        if (!(date instanceof Date) || isNaN(date)) return 'Invalid Date';
        
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return date.toLocaleDateString(undefined, options);
    }
    
    // Capitalize first letter
    function capitalizeFirst(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    // Escape HTML special characters
    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    }
    
    // Update URL without reloading the page
    function updateUrlWithoutReload(jobId) {
        if (window.history && window.history.pushState) {
            const url = new URL(window.location.href);
            
            if (jobId) {
                url.searchParams.set('job_id', jobId);
            } else {
                url.searchParams.delete('job_id');
            }
            
            window.history.pushState({}, '', url.toString());
        }
    }
    
    // Initialize template link
    updateTemplateLink();
});

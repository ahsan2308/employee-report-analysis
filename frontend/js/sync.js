/* filepath: c:\Users\mahsa\Desktop\AI Based Employee Evaluation Project Code\Code\employee-report-analysis\frontend\js\sync.js */

document.addEventListener('DOMContentLoaded', function() {
    // ============================================================================
    // DOM ELEMENT REFERENCES
    // ============================================================================
    
    // Schedule Status Elements
    const scheduleStatusBanner = document.getElementById('scheduleStatusBanner');
    const scheduleStatusElement = document.getElementById('scheduleStatus');
    const nextSyncTimeElement = document.getElementById('nextSyncTime');
    const refreshScheduleBtn = document.getElementById('refreshScheduleBtn');
    
    // Sync Trigger Elements
    const triggerSyncButtons = document.querySelectorAll('.trigger-sync-btn');
    const statusMessageDiv = document.getElementById('statusMessage');
    
    // Last Sync Info Elements
    const lastSyncEmployeeReports = document.getElementById('lastSyncEmployeeReports');
    const lastSyncVisionData = document.getElementById('lastSyncVisionData');
    const lastSyncJobDescriptions = document.getElementById('lastSyncJobDescriptions');
    
    // Active Sync Monitor Elements
    const activeSyncSection = document.getElementById('activeSyncSection');
    const activeSyncId = document.getElementById('activeSyncId');
    const activeSyncType = document.getElementById('activeSyncType');
    const activeSyncStatus = document.getElementById('activeSyncStatus');
    const activeSyncStarted = document.getElementById('activeSyncStarted');
    const activeSyncMode = document.getElementById('activeSyncMode');
    const activeSyncDuration = document.getElementById('activeSyncDuration');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const progressBar = document.getElementById('progressBar');
    const stopMonitoringBtn = document.getElementById('stopMonitoringBtn');
    const viewActiveSyncErrorsBtn = document.getElementById('viewActiveSyncErrorsBtn');
    
    // Metrics Elements
    const metricsRecordsQueried = document.getElementById('metricsRecordsQueried');
    const metricsRecordsSynced = document.getElementById('metricsRecordsSynced');
    const metricsRecordsCreated = document.getElementById('metricsRecordsCreated');
    const metricsRecordsUpdated = document.getElementById('metricsRecordsUpdated');
    const metricsRecordsSkipped = document.getElementById('metricsRecordsSkipped');
    const metricsErrorCount = document.getElementById('metricsErrorCount');
    const detailedMetricsContainer = document.getElementById('detailedMetricsContainer');
    const detailedMetricsContent = document.getElementById('detailedMetricsContent');
    
    // History Elements
    const historyTypeFilter = document.getElementById('historyTypeFilter');
    const historyStatusFilter = document.getElementById('historyStatusFilter');
    const historySortOrder = document.getElementById('historySortOrder');
    const applyHistoryFiltersBtn = document.getElementById('applyHistoryFiltersBtn');
    const resetHistoryFiltersBtn = document.getElementById('resetHistoryFiltersBtn');
    const historyLoadingIndicator = document.getElementById('historyLoadingIndicator');
    const historyTableBody = document.getElementById('historyTableBody');
    const noHistoryMessage = document.getElementById('noHistoryMessage');
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const paginationInfo = document.getElementById('paginationInfo');
    
    // Config Elements
    const configLoadingIndicator = document.getElementById('configLoadingIndicator');
    const configContent = document.getElementById('configContent');
    const configHost = document.getElementById('configHost');
    const configDatabase = document.getElementById('configDatabase');
    const configConnectionStatus = document.getElementById('configConnectionStatus');
    const allowedTablesContainer = document.getElementById('allowedTablesContainer');
    const configMaxBatchSize = document.getElementById('configMaxBatchSize');
    const configErrorThreshold = document.getElementById('configErrorThreshold');
    const configSyncEnabled = document.getElementById('configSyncEnabled');
    const configIncrementalSchedule = document.getElementById('configIncrementalSchedule');
    const configFullSchedule = document.getElementById('configFullSchedule');
    const testConnectionBtn = document.getElementById('testConnectionBtn');
    
    // Modal Elements
    const errorModal = document.getElementById('errorModal');
    const closeModalButtons = document.querySelectorAll('.close-modal');
    const modalSyncId = document.getElementById('modalSyncId');
    const modalTotalErrors = document.getElementById('modalTotalErrors');
    const modalErrorList = document.getElementById('modalErrorList');
    const modalPrevBtn = document.getElementById('modalPrevBtn');
    const modalNextBtn = document.getElementById('modalNextBtn');
    const modalPaginationInfo = document.getElementById('modalPaginationInfo');
    
    // ============================================================================
    // STATE MANAGEMENT
    // ============================================================================
    
    let currentSyncId = null;
    let pollingInterval = null;
    let currentPage = 1;
    let pageSize = 20;
    let totalPages = 1;
    let modalCurrentPage = 1;
    let modalPageSize = 10;
    let modalTotalPages = 1;
    let currentErrorSyncId = null;
    
    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    async function init() {
        await loadSyncConfiguration();
        await loadScheduleStatus();
        await loadLastSyncTimes();
        await loadSyncHistory();
        
        // Check if sync_id in URL (for direct linking)
        const urlParams = new URLSearchParams(window.location.search);
        const syncIdFromUrl = urlParams.get('sync_id');
        if (syncIdFromUrl) {
            await monitorSync(syncIdFromUrl);
        }
    }
    
    // ============================================================================
    // EVENT LISTENERS
    // ============================================================================
    
    // Refresh schedule button
    if (refreshScheduleBtn) {
        refreshScheduleBtn.addEventListener('click', async () => {
            await loadScheduleStatus();
            showMessage('Schedule status refreshed', 'success');
        });
    }
    
    // Sync trigger buttons
    triggerSyncButtons.forEach(button => {
        button.addEventListener('click', async () => {
            const syncType = button.getAttribute('data-sync-type');
            const isFullSync = button.getAttribute('data-full-sync') === 'true';
            await triggerSync(syncType, isFullSync);
        });
    });
    
    // Stop monitoring button
    if (stopMonitoringBtn) {
        stopMonitoringBtn.addEventListener('click', () => {
            stopPolling();
            activeSyncSection.style.display = 'none';
            showMessage('Stopped monitoring sync operation', 'info');
        });
    }
    
    // View active sync errors button
    if (viewActiveSyncErrorsBtn) {
        viewActiveSyncErrorsBtn.addEventListener('click', () => {
            if (currentSyncId) {
                openErrorModal(currentSyncId);
            }
        });
    }
    
    // History filters
    if (applyHistoryFiltersBtn) {
        applyHistoryFiltersBtn.addEventListener('click', () => {
            currentPage = 1;
            loadSyncHistory();
        });
    }
    
    if (resetHistoryFiltersBtn) {
        resetHistoryFiltersBtn.addEventListener('click', () => {
            historyTypeFilter.value = '';
            historyStatusFilter.value = '';
            historySortOrder.value = 'desc';
            currentPage = 1;
            loadSyncHistory();
        });
    }
    
    // Pagination
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                loadSyncHistory();
            }
        });
    }
    
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', () => {
            if (currentPage < totalPages) {
                currentPage++;
                loadSyncHistory();
            }
        });
    }
    
    // Test connection button
    if (testConnectionBtn) {
        testConnectionBtn.addEventListener('click', testConnection);
    }
    
    // Modal close buttons
    closeModalButtons.forEach(button => {
        button.addEventListener('click', () => {
            errorModal.style.display = 'none';
        });
    });
    
    // Modal pagination
    if (modalPrevBtn) {
        modalPrevBtn.addEventListener('click', () => {
            if (modalCurrentPage > 1) {
                modalCurrentPage--;
                loadErrorsForModal(currentErrorSyncId);
            }
        });
    }
    
    if (modalNextBtn) {
        modalNextBtn.addEventListener('click', () => {
            if (modalCurrentPage < modalTotalPages) {
                modalCurrentPage++;
                loadErrorsForModal(currentErrorSyncId);
            }
        });
    }
    
    // Close modal on outside click
    window.addEventListener('click', (event) => {
        if (event.target === errorModal) {
            errorModal.style.display = 'none';
        }
    });
    
    // ============================================================================
    // SCHEDULE STATUS
    // ============================================================================
    
    async function loadScheduleStatus() {
        try {
            const config = await syncApi.getSyncConfiguration();
            
            if (config.sync_enabled) {
                scheduleStatusElement.textContent = 'Enabled';
                scheduleStatusElement.className = 'schedule-status enabled';
                
                // Calculate next sync time based on schedule
                const nextSync = calculateNextSyncTime(config.sync_schedule);
                nextSyncTimeElement.textContent = `Next incremental sync: ${formatDateTime(nextSync)}`;
            } else {
                scheduleStatusElement.textContent = 'Disabled';
                scheduleStatusElement.className = 'schedule-status disabled';
                nextSyncTimeElement.textContent = 'Automatic sync is disabled';
            }
        } catch (error) {
            console.error('Error loading schedule status:', error);
            scheduleStatusElement.textContent = 'Unknown';
            scheduleStatusElement.className = 'schedule-status disabled';
            nextSyncTimeElement.textContent = 'Error loading schedule';
        }
    }
    
    function calculateNextSyncTime(schedule) {
        // Simplified calculation - in production, you'd parse the cron expression
        const now = new Date();
        const nextMonday = new Date(now);
        const daysUntilMonday = (1 + 7 - now.getDay()) % 7 || 7;
        nextMonday.setDate(now.getDate() + daysUntilMonday);
        nextMonday.setHours(2, 0, 0, 0);
        
        // If it's already past Monday 2 AM this week, go to next week
        if (nextMonday <= now) {
            nextMonday.setDate(nextMonday.getDate() + 7);
        }
        
        return nextMonday;
    }
    
    // ============================================================================
    // LAST SYNC TIMES
    // ============================================================================
    
    async function loadLastSyncTimes() {
        try {
            // Load last successful sync for employee reports
            const employeeReportsSync = await syncApi.getLastSuccessfulSync('employee_reports');
            if (employeeReportsSync && employeeReportsSync.last_sync_timestamp) {
                lastSyncEmployeeReports.textContent = `Last synced: ${formatDateTime(employeeReportsSync.last_sync_timestamp)}`;
            } else {
                lastSyncEmployeeReports.textContent = 'Never synced';
            }
            
            // Load last successful sync for vision data
            const visionDataSync = await syncApi.getLastSuccessfulSync('vision_data');
            if (visionDataSync && visionDataSync.last_sync_timestamp) {
                lastSyncVisionData.textContent = `Last synced: ${formatDateTime(visionDataSync.last_sync_timestamp)}`;
            } else {
                lastSyncVisionData.textContent = 'Never synced';
            }
            
            // Load last successful sync for job descriptions
            const jdSync = await syncApi.getLastSuccessfulSync('job_descriptions');
            if (jdSync && jdSync.last_sync_timestamp) {
                lastSyncJobDescriptions.textContent = `Last synced: ${formatDateTime(jdSync.last_sync_timestamp)}`;
            } else {
                lastSyncJobDescriptions.textContent = 'Never synced';
            }
        } catch (error) {
            console.error('Error loading last sync times:', error);
        }
    }
    
    // ============================================================================
    // SYNC TRIGGERING
    // ============================================================================
    
    async function triggerSync(syncType, isFullSync) {
        try {
            // Disable all trigger buttons
            triggerSyncButtons.forEach(btn => btn.disabled = true);
            
            showMessage('Starting sync...', 'info');
            
            let response;
            if (syncType === 'full') {
                response = await syncApi.triggerFullSync();
            } else {
                response = await syncApi.triggerSync(syncType, isFullSync);
            }
            
            showMessage(`Sync started successfully! Sync ID: ${response.sync_id || response.employee_reports_sync_id}`, 'success');
            
            // Start monitoring the sync
            if (syncType === 'full') {
                // For full sync, monitor the employee reports sync (you could monitor both)
                await monitorSync(response.employee_reports_sync_id);
            } else {
                await monitorSync(response.sync_id);
            }
            
            // Reload last sync times
            await loadLastSyncTimes();
            
        } catch (error) {
            console.error('Error triggering sync:', error);
            showMessage(`Error: ${error.message || 'Failed to start sync'}`, 'error');
        } finally {
            // Re-enable trigger buttons
            triggerSyncButtons.forEach(btn => btn.disabled = false);
        }
    }
    
    // ============================================================================
    // SYNC MONITORING
    // ============================================================================
    
    async function monitorSync(syncId) {
        currentSyncId = syncId;
        
        // Show active sync section
        activeSyncSection.style.display = 'block';
        activeSyncId.textContent = syncId;
        
        // Start polling
        await updateSyncStatus();
        pollingInterval = setInterval(updateSyncStatus, 2000); // Poll every 2 seconds
        
        // Scroll to active sync section
        activeSyncSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    async function updateSyncStatus() {
        if (!currentSyncId) return;
        
        try {
            const status = await syncApi.getSyncStatus(currentSyncId);
            
            // Update basic info
            activeSyncType.textContent = formatSyncType(status.sync_type);
            activeSyncStatus.textContent = status.status;
            activeSyncStatus.className = `detail-value status-badge status-${status.status}`;
            activeSyncStarted.textContent = formatDateTime(status.started_at);
            activeSyncMode.textContent = status.is_full_sync ? 'Full Sync' : 'Incremental Sync';
            
            // Update duration
            if (status.duration_seconds !== null) {
                activeSyncDuration.textContent = formatDuration(status.duration_seconds);
            } else {
                const started = new Date(status.started_at);
                const now = new Date();
                const seconds = Math.floor((now - started) / 1000);
                activeSyncDuration.textContent = formatDuration(seconds);
            }
            
            // Update progress
            const progress = status.progress;
            progressPercent.textContent = `${progress.percent_complete}%`;
            progressBar.style.width = `${progress.percent_complete}%`;
            
            // Update progress bar color based on status
            progressBar.className = 'progress-fill';
            if (status.status === 'completed') {
                progressBar.classList.add('complete');
            } else if (status.status === 'failed') {
                progressBar.classList.add('error');
            }
            
            // Update progress text
            if (status.status === 'pending') {
                progressText.textContent = 'Waiting to start...';
            } else if (status.status === 'running') {
                progressText.textContent = `Syncing records... (${progress.records_synced}/${progress.records_queried})`;
            } else if (status.status === 'completed') {
                progressText.textContent = 'Sync completed successfully!';
            } else if (status.status === 'failed') {
                progressText.textContent = 'Sync failed';
            } else if (status.status === 'partial') {
                progressText.textContent = 'Sync completed with errors';
            }
            
            // Update metrics
            metricsRecordsQueried.textContent = progress.records_queried;
            metricsRecordsSynced.textContent = progress.records_synced;
            metricsRecordsCreated.textContent = progress.records_created;
            metricsRecordsUpdated.textContent = progress.records_updated;
            metricsRecordsSkipped.textContent = progress.records_skipped;
            metricsErrorCount.textContent = progress.error_count;
            
            // Update detailed metrics
            updateDetailedMetrics(status.metrics, status.sync_type);
            
            // Show/hide error button
            if (progress.error_count > 0) {
                viewActiveSyncErrorsBtn.style.display = 'inline-block';
            } else {
                viewActiveSyncErrorsBtn.style.display = 'none';
            }
            
            // Stop polling if sync is complete
            if (['completed', 'failed', 'partial'].includes(status.status)) {
                stopPolling();
                // Reload sync history
                await loadSyncHistory();
                await loadLastSyncTimes();
            }
            
        } catch (error) {
            console.error('Error updating sync status:', error);
            stopPolling();
        }
    }
    
    function updateDetailedMetrics(metrics, syncType) {
        if (!metrics || Object.keys(metrics).length === 0) {
            detailedMetricsContainer.style.display = 'none';
            return;
        }
        
        detailedMetricsContainer.style.display = 'block';
        detailedMetricsContent.innerHTML = '';
        
        // Different metrics based on sync type
        if (syncType === 'employee_reports') {
            addDetailedMetric('Employees Created', metrics.employees_created || 0);
            addDetailedMetric('Employees Updated', metrics.employees_updated || 0);
            addDetailedMetric('Reports Created', metrics.reports_created || 0);
            addDetailedMetric('Reports Updated', metrics.reports_updated || 0);
        } else if (syncType === 'vision_data') {
            addDetailedMetric('Vision Records Created', metrics.vision_records_created || 0);
            addDetailedMetric('Vision Records Updated', metrics.vision_records_updated || 0);
        } else if (syncType === 'job_descriptions') {
            addDetailedMetric('JD Records Created', metrics.jd_records_created || 0);
            addDetailedMetric('JD Records Updated', metrics.jd_records_updated || 0);
        }
    }
    
    function addDetailedMetric(label, value) {
        const metricDiv = document.createElement('div');
        metricDiv.className = 'detailed-metric-item';
        metricDiv.innerHTML = `
            <span class="detailed-metric-label">${label}:</span>
            <span class="detailed-metric-value">${value}</span>
        `;
        detailedMetricsContent.appendChild(metricDiv);
    }
    
    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }
    
    // ============================================================================
    // SYNC HISTORY
    // ============================================================================
    
    async function loadSyncHistory() {
        try {
            historyLoadingIndicator.style.display = 'block';
            noHistoryMessage.style.display = 'none';
            
            const filters = {
                sync_type: historyTypeFilter.value || undefined,
                status: historyStatusFilter.value || undefined,
                sort_order: historySortOrder.value,
                page: currentPage,
                page_size: pageSize
            };
            
            const history = await syncApi.listSyncHistory(filters);
            
            historyLoadingIndicator.style.display = 'none';
            
            if (history.items.length === 0) {
                historyTableBody.innerHTML = '';
                noHistoryMessage.style.display = 'block';
                return;
            }
            
            // Update table
            renderHistoryTable(history.items);
            
            // Update pagination
            totalPages = history.pages;
            updatePagination();
            
        } catch (error) {
            console.error('Error loading sync history:', error);
            historyLoadingIndicator.style.display = 'none';
            showMessage('Error loading sync history', 'error');
        }
    }
    
    function renderHistoryTable(items) {
        historyTableBody.innerHTML = '';
        
        items.forEach(item => {
            const row = document.createElement('tr');
            
            // Sync ID (truncated)
            const syncIdCell = document.createElement('td');
            syncIdCell.innerHTML = `<span class="sync-id-cell" title="${item.sync_id}">${item.sync_id.substring(0, 8)}...</span>`;
            row.appendChild(syncIdCell);
            
            // Type
            const typeCell = document.createElement('td');
            const iconClass = getSyncTypeIcon(item.sync_type);
            typeCell.innerHTML = `<span class="sync-type-badge ${item.sync_type.replace('_', '-')}">
                <i class="fas ${iconClass}"></i>
                ${formatSyncType(item.sync_type)}
            </span>`;
            row.appendChild(typeCell);
            
            // Status
            const statusCell = document.createElement('td');
            statusCell.innerHTML = `<span class="status-badge status-${item.status}">${item.status}</span>`;
            row.appendChild(statusCell);
            
            // Started
            const startedCell = document.createElement('td');
            startedCell.textContent = formatDateTime(item.started_at);
            row.appendChild(startedCell);
            
            // Duration
            const durationCell = document.createElement('td');
            durationCell.innerHTML = `<span class="duration-text">${formatDuration(item.duration_seconds)}</span>`;
            row.appendChild(durationCell);
            
            // Records
            const recordsCell = document.createElement('td');
            recordsCell.innerHTML = `<span class="records-stat">
                <span class="records-fraction">${item.records_synced}/${item.records_queried}</span>
            </span>`;
            row.appendChild(recordsCell);
            
            // Errors
            const errorsCell = document.createElement('td');
            if (item.error_count > 0) {
                errorsCell.innerHTML = `<span class="error-count-badge">${item.error_count}</span>`;
            } else {
                errorsCell.textContent = '-';
            }
            row.appendChild(errorsCell);
            
            // Actions
            const actionsCell = document.createElement('td');
            actionsCell.className = 'sync-actions';
            
            // View details button
            const viewBtn = document.createElement('button');
            viewBtn.className = 'button small-button secondary-button';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i> View';
            viewBtn.onclick = () => monitorSync(item.sync_id);
            actionsCell.appendChild(viewBtn);
            
            // View errors button (if errors exist)
            if (item.error_count > 0) {
                const errorsBtn = document.createElement('button');
                errorsBtn.className = 'button small-button secondary-button';
                errorsBtn.innerHTML = '<i class="fas fa-bug"></i> Errors';
                errorsBtn.onclick = () => openErrorModal(item.sync_id);
                actionsCell.appendChild(errorsBtn);
            }
            
            row.appendChild(actionsCell);
            historyTableBody.appendChild(row);
        });
    }
    
    function updatePagination() {
        paginationInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        prevPageBtn.disabled = currentPage === 1;
        nextPageBtn.disabled = currentPage >= totalPages;
    }
    
    // ============================================================================
    // ERROR MODAL
    // ============================================================================
    
    async function openErrorModal(syncId) {
        currentErrorSyncId = syncId;
        modalCurrentPage = 1;
        modalSyncId.textContent = syncId;
        
        errorModal.style.display = 'block';
        
        await loadErrorsForModal(syncId);
    }
    
    async function loadErrorsForModal(syncId) {
        try {
            const errors = await syncApi.getSyncErrors(syncId, modalCurrentPage, modalPageSize);
            
            modalTotalErrors.textContent = errors.total_errors;
            modalTotalPages = Math.ceil(errors.total_errors / modalPageSize);
            
            renderErrorList(errors.errors);
            updateModalPagination();
            
        } catch (error) {
            console.error('Error loading sync errors:', error);
            modalErrorList.innerHTML = '<p>Error loading errors</p>';
        }
    }
    
    function renderErrorList(errors) {
        modalErrorList.innerHTML = '';
        
        if (errors.length === 0) {
            modalErrorList.innerHTML = '<p>No errors found</p>';
            return;
        }
        
        errors.forEach(error => {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-item-modal';
            
            errorDiv.innerHTML = `
                <div class="error-item-header">
                    <span class="error-row-number">Row ${error.row_number}</span>
                    <span class="error-category">${error.error_category || 'Error'}</span>
                </div>
                ${error.field_name ? `<div class="error-field">Field: <strong>${error.field_name}</strong></div>` : ''}
                <div class="error-message-text">${error.error_message}</div>
            `;
            
            modalErrorList.appendChild(errorDiv);
        });
    }
    
    function updateModalPagination() {
        modalPaginationInfo.textContent = `Page ${modalCurrentPage} of ${modalTotalPages}`;
        modalPrevBtn.disabled = modalCurrentPage === 1;
        modalNextBtn.disabled = modalCurrentPage >= modalTotalPages;
    }
    
    // ============================================================================
    // SYNC CONFIGURATION
    // ============================================================================
    
    async function loadSyncConfiguration() {
        try {
            const config = await syncApi.getSyncConfiguration();
            
            // SQL Server Connection
            configHost.textContent = config.sql_server.host;
            configDatabase.textContent = config.sql_server.database;
            configConnectionStatus.textContent = config.sql_server.connection_status;
            configConnectionStatus.className = `config-value status-badge status-${config.sql_server.connection_status === 'connected' ? 'completed' : 'failed'}`;
            
            // Allowed Tables
            allowedTablesContainer.innerHTML = '';
            config.allowed_tables.forEach(table => {
                const tag = document.createElement('span');
                tag.className = 'config-tag';
                tag.innerHTML = `<i class="fas fa-table"></i> ${table}`;
                allowedTablesContainer.appendChild(tag);
            });
            
            // Sync Settings
            configMaxBatchSize.textContent = config.sync_settings.max_batch_size;
            configErrorThreshold.textContent = `${config.sync_settings.error_threshold_percent}%`;
            configSyncEnabled.textContent = config.sync_enabled ? 'Yes' : 'No';
            
            // Sync Schedule
            configIncrementalSchedule.textContent = config.sync_schedule.incremental_sync.schedule || 'Not scheduled';
            configFullSchedule.textContent = config.sync_schedule.full_sync.schedule || 'Manual only';
            
            // Show config content
            configLoadingIndicator.style.display = 'none';
            configContent.style.display = 'block';
            
        } catch (error) {
            console.error('Error loading sync configuration:', error);
            configLoadingIndicator.innerHTML = '<p>Error loading configuration</p>';
        }
    }
    
    async function testConnection() {
        try {
            testConnectionBtn.disabled = true;
            testConnectionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
            
            const result = await syncApi.testConnection();
            
            if (result.status === 'connected') {
                showMessage(`Connection successful! ${result.available_tables.length} tables available`, 'success');
                configConnectionStatus.textContent = 'connected';
                configConnectionStatus.className = 'config-value status-badge status-completed';
            } else {
                showMessage(`Connection failed: ${result.message}`, 'error');
                configConnectionStatus.textContent = 'disconnected';
                configConnectionStatus.className = 'config-value status-badge status-failed';
            }
            
        } catch (error) {
            console.error('Error testing connection:', error);
            showMessage('Error testing connection', 'error');
        } finally {
            testConnectionBtn.disabled = false;
            testConnectionBtn.innerHTML = '<i class="fas fa-plug"></i> Test Connection';
        }
    }
    
    // ============================================================================
    // UTILITY FUNCTIONS
    // ============================================================================
    
    function showMessage(message, type = 'info') {
        statusMessageDiv.innerHTML = `
            <div class="message message-${type}">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'times-circle' : 'info-circle'}"></i>
                ${message}
            </div>
        `;
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            statusMessageDiv.innerHTML = '';
        }, 5000);
    }
    
    function formatDateTime(dateTimeStr) {
        if (!dateTimeStr) return '-';
        const date = new Date(dateTimeStr);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    function formatDuration(seconds) {
        if (seconds === null || seconds === undefined) return '-';
        
        if (seconds < 60) {
            return `${seconds.toFixed(1)}s`;
        } else if (seconds < 3600) {
            const minutes = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${minutes}m ${secs}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }
    
    function formatSyncType(syncType) {
        const typeMap = {
            'employee_reports': 'Employee Reports',
            'vision_data': 'Vision Data',
            'job_descriptions': 'Job Descriptions',
            'full': 'Full Sync'
        };
        return typeMap[syncType] || syncType;
    }
    
    function getSyncTypeIcon(syncType) {
        const iconMap = {
            'employee_reports': 'fa-file-alt',
            'vision_data': 'fa-eye',
            'job_descriptions': 'fa-briefcase',
            'full': 'fa-globe'
        };
        return iconMap[syncType] || 'fa-sync';
    }
    
    // ============================================================================
    // START APPLICATION
    // ============================================================================
    
    init();
});
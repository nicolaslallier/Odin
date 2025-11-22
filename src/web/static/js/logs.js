// Log Viewer JavaScript - Odin v1.2.0

class LogViewer {
    constructor() {
        this.apiBaseUrl = window.API_BASE_URL || 'http://localhost:8001';
        this.logs = [];
        this.selectedLogs = new Set();
        this.currentOffset = 0;
        this.currentLimit = 100;
        this.totalLogs = 0;
        this.autoRefreshInterval = null;
        this.currentLogDetail = null;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialFilters();
        this.loadLogs();
        this.loadStatistics();
        this.setupAutoRefresh();
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadLogs();
            this.loadStatistics();
        });

        // Auto-refresh toggle
        document.getElementById('autoRefresh').addEventListener('change', (e) => {
            this.setupAutoRefresh();
        });

        // Filter buttons
        document.getElementById('applyFilters').addEventListener('click', () => {
            this.currentOffset = 0;
            this.loadLogs();
        });

        document.getElementById('clearFilters').addEventListener('click', () => {
            this.clearFilters();
        });

        // Pagination
        document.getElementById('prevPage').addEventListener('click', () => {
            if (this.currentOffset > 0) {
                this.currentOffset = Math.max(0, this.currentOffset - this.currentLimit);
                this.loadLogs();
            }
        });

        document.getElementById('nextPage').addEventListener('click', () => {
            if (this.currentOffset + this.logs.length < this.totalLogs) {
                this.currentOffset += this.currentLimit;
                this.loadLogs();
            }
        });

        // Select all checkbox
        document.getElementById('selectAll').addEventListener('change', (e) => {
            const checkboxes = document.querySelectorAll('.log-checkbox');
            checkboxes.forEach(cb => {
                cb.checked = e.target.checked;
                const logId = parseInt(cb.dataset.logId);
                if (e.target.checked) {
                    this.selectedLogs.add(logId);
                } else {
                    this.selectedLogs.delete(logId);
                }
            });
            this.updateAnalyzeButton();
        });

        // Analyze button
        document.getElementById('analyzeBtn').addEventListener('click', () => {
            this.analyzeLogs();
        });

        // Export button
        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportLogs();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.closeModals();
            });
        });

        // Click outside modal to close
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModals();
                }
            });
        });

        // Correlate button in modal
        document.getElementById('correlateBtn').addEventListener('click', () => {
            if (this.currentLogDetail) {
                this.showCorrelatedLogs(this.currentLogDetail);
            }
        });

        // Limit input change
        document.getElementById('limitInput').addEventListener('change', (e) => {
            this.currentLimit = parseInt(e.target.value) || 100;
        });
    }

    loadInitialFilters() {
        if (window.INITIAL_LEVEL) {
            document.getElementById('levelFilter').value = window.INITIAL_LEVEL;
        }
        if (window.INITIAL_SERVICE) {
            document.getElementById('serviceFilter').value = window.INITIAL_SERVICE;
        }
        if (window.INITIAL_SEARCH) {
            document.getElementById('searchInput').value = window.INITIAL_SEARCH;
        }
        if (window.INITIAL_START_TIME) {
            document.getElementById('startTime').value = window.INITIAL_START_TIME.replace('Z', '');
        }
        if (window.INITIAL_END_TIME) {
            document.getElementById('endTime').value = window.INITIAL_END_TIME.replace('Z', '');
        }
    }

    clearFilters() {
        document.getElementById('levelFilter').value = '';
        document.getElementById('serviceFilter').value = '';
        document.getElementById('searchInput').value = '';
        document.getElementById('startTime').value = '';
        document.getElementById('endTime').value = '';
        document.getElementById('limitInput').value = '100';
        this.currentOffset = 0;
        this.currentLimit = 100;
        this.loadLogs();
    }

    getFilters() {
        const filters = {
            limit: this.currentLimit,
            offset: this.currentOffset
        };

        const level = document.getElementById('levelFilter').value;
        if (level) filters.level = level;

        const service = document.getElementById('serviceFilter').value;
        if (service) filters.service = service;

        const search = document.getElementById('searchInput').value.trim();
        if (search) filters.search = search;

        const startTime = document.getElementById('startTime').value;
        if (startTime) filters.start_time = new Date(startTime).toISOString();

        const endTime = document.getElementById('endTime').value;
        if (endTime) filters.end_time = new Date(endTime).toISOString();

        return filters;
    }

    async loadLogs() {
        const tbody = document.getElementById('logsTableBody');
        tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">Loading logs...</td></tr>';

        try {
            const filters = this.getFilters();
            const params = new URLSearchParams(filters);
            const response = await fetch(`${this.apiBaseUrl}/api/v1/logs?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.logs = data.logs || [];
            this.totalLogs = data.total || 0;

            this.renderLogs();
            this.updatePaginationInfo();
        } catch (error) {
            console.error('Failed to load logs:', error);
            tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Error loading logs: ${error.message}</td></tr>`;
        }
    }

    renderLogs() {
        const tbody = document.getElementById('logsTableBody');
        
        if (this.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="loading-cell">No logs found</td></tr>';
            return;
        }

        tbody.innerHTML = this.logs.map(log => this.renderLogRow(log)).join('');

        // Add event listeners to checkboxes
        tbody.querySelectorAll('.log-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const logId = parseInt(e.target.dataset.logId);
                if (e.target.checked) {
                    this.selectedLogs.add(logId);
                } else {
                    this.selectedLogs.delete(logId);
                }
                this.updateAnalyzeButton();
            });
        });

        // Add event listeners to detail buttons
        tbody.querySelectorAll('.detail-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const logId = parseInt(e.target.dataset.logId);
                const log = this.logs.find(l => l.id === logId);
                if (log) {
                    this.showLogDetail(log);
                }
            });
        });
    }

    renderLogRow(log) {
        const timestamp = new Date(log.timestamp).toLocaleString();
        const message = this.escapeHtml(log.message);
        const isSelected = this.selectedLogs.has(log.id);

        return `
            <tr class="${isSelected ? 'selected' : ''}">
                <td class="col-select">
                    <input type="checkbox" class="log-checkbox" data-log-id="${log.id}" ${isSelected ? 'checked' : ''}>
                </td>
                <td class="col-timestamp">${timestamp}</td>
                <td class="col-level">
                    <span class="log-level log-level-${log.level}">${log.level}</span>
                </td>
                <td class="col-service">${log.service}</td>
                <td class="col-message">
                    <div class="log-message" title="${message}">${message}</div>
                </td>
                <td class="col-actions">
                    <button class="action-btn detail-btn" data-log-id="${log.id}" title="View Details">👁️</button>
                </td>
            </tr>
        `;
    }

    showLogDetail(log) {
        this.currentLogDetail = log;
        const modal = document.getElementById('logModal');
        const modalBody = document.getElementById('logModalBody');

        modalBody.innerHTML = `
            <div class="log-detail-row">
                <div class="log-detail-label">ID</div>
                <div class="log-detail-value">${log.id}</div>
            </div>
            <div class="log-detail-row">
                <div class="log-detail-label">Timestamp</div>
                <div class="log-detail-value">${new Date(log.timestamp).toISOString()}</div>
            </div>
            <div class="log-detail-row">
                <div class="log-detail-label">Level</div>
                <div class="log-detail-value"><span class="log-level log-level-${log.level}">${log.level}</span></div>
            </div>
            <div class="log-detail-row">
                <div class="log-detail-label">Service</div>
                <div class="log-detail-value">${log.service}</div>
            </div>
            <div class="log-detail-row">
                <div class="log-detail-label">Logger</div>
                <div class="log-detail-value">${log.logger || 'N/A'}</div>
            </div>
            <div class="log-detail-row">
                <div class="log-detail-label">Message</div>
                <div class="log-detail-value">${this.escapeHtml(log.message)}</div>
            </div>
            ${log.exception ? `
            <div class="log-detail-row">
                <div class="log-detail-label">Exception</div>
                <div class="log-detail-value">${this.escapeHtml(log.exception)}</div>
            </div>
            ` : ''}
            ${log.request_id ? `
            <div class="log-detail-row">
                <div class="log-detail-label">Request ID</div>
                <div class="log-detail-value">${log.request_id}</div>
            </div>
            ` : ''}
            ${log.task_id ? `
            <div class="log-detail-row">
                <div class="log-detail-label">Task ID</div>
                <div class="log-detail-value">${log.task_id}</div>
            </div>
            ` : ''}
            ${log.user_id ? `
            <div class="log-detail-row">
                <div class="log-detail-label">User ID</div>
                <div class="log-detail-value">${log.user_id}</div>
            </div>
            ` : ''}
            <div class="log-detail-row">
                <div class="log-detail-label">Module / Function</div>
                <div class="log-detail-value">${log.module || 'N/A'} / ${log.function || 'N/A'} (line ${log.line || 'N/A'})</div>
            </div>
        `;

        modal.classList.add('active');
    }

    async showCorrelatedLogs(log) {
        if (!log.request_id && !log.task_id) {
            alert('No correlation IDs available for this log');
            return;
        }

        this.closeModals();

        // Set filters to show correlated logs
        if (log.request_id) {
            document.getElementById('searchInput').value = log.request_id;
        } else if (log.task_id) {
            document.getElementById('searchInput').value = log.task_id;
        }

        await this.loadLogs();
    }

    async loadStatistics() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/logs/stats`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const stats = await response.json();
            
            document.getElementById('statTotal').textContent = stats.total_logs || 0;
            document.getElementById('statDebug').textContent = stats.by_level?.DEBUG || 0;
            document.getElementById('statInfo').textContent = stats.by_level?.INFO || 0;
            document.getElementById('statWarning').textContent = stats.by_level?.WARNING || 0;
            document.getElementById('statError').textContent = stats.by_level?.ERROR || 0;
            document.getElementById('statCritical').textContent = stats.by_level?.CRITICAL || 0;
        } catch (error) {
            console.error('Failed to load statistics:', error);
        }
    }

    updatePaginationInfo() {
        const start = this.currentOffset + 1;
        const end = Math.min(this.currentOffset + this.logs.length, this.totalLogs);
        document.getElementById('paginationInfo').textContent = 
            `Showing ${start}-${end} of ${this.totalLogs}`;

        document.getElementById('prevPage').disabled = this.currentOffset === 0;
        document.getElementById('nextPage').disabled = this.currentOffset + this.logs.length >= this.totalLogs;
    }

    updateAnalyzeButton() {
        const btn = document.getElementById('analyzeBtn');
        btn.disabled = this.selectedLogs.size === 0;
        if (this.selectedLogs.size > 0) {
            btn.textContent = `🤖 Analyze ${this.selectedLogs.size} Logs`;
        } else {
            btn.textContent = '🤖 Analyze with AI';
        }
    }

    setupAutoRefresh() {
        // Clear existing interval
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }

        // Setup new interval if enabled
        const autoRefresh = document.getElementById('autoRefresh').checked;
        if (autoRefresh) {
            this.autoRefreshInterval = setInterval(() => {
                this.loadLogs();
                this.loadStatistics();
            }, 5000); // 5 seconds
        }
    }

    async analyzeLogs() {
        if (this.selectedLogs.size === 0) return;

        const modal = document.getElementById('analysisModal');
        const modalBody = document.getElementById('analysisModalBody');
        
        modalBody.innerHTML = '<div class="analysis-loading">Analyzing logs with AI...</div>';
        modal.classList.add('active');

        try {
            const logIds = Array.from(this.selectedLogs);
            const response = await fetch(`${this.apiBaseUrl}/api/v1/logs/analyze`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    log_ids: logIds,
                    analysis_type: 'root_cause',
                    max_logs: 50
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const analysis = await response.json();
            this.renderAnalysis(analysis);
        } catch (error) {
            console.error('Failed to analyze logs:', error);
            modalBody.innerHTML = `<div class="analysis-loading">Error: ${error.message}</div>`;
        }
    }

    renderAnalysis(analysis) {
        const modalBody = document.getElementById('analysisModalBody');
        
        let html = `
            <div class="analysis-section">
                <h3>📊 Analysis Summary</h3>
                <p>${this.escapeHtml(analysis.summary)}</p>
            </div>
        `;

        if (analysis.findings && analysis.findings.length > 0) {
            html += `
                <div class="analysis-section">
                    <h3>🔍 Key Findings</h3>
                    <ul>
                        ${analysis.findings.map(f => `<li>${this.escapeHtml(f)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        if (analysis.recommendations && analysis.recommendations.length > 0) {
            html += `
                <div class="analysis-section">
                    <h3>💡 Recommendations</h3>
                    <ul>
                        ${analysis.recommendations.map(r => `<li>${this.escapeHtml(r)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        if (analysis.full_analysis) {
            html += `
                <div class="analysis-section">
                    <h3>📝 Full Analysis</h3>
                    <div class="log-detail-value">${this.escapeHtml(analysis.full_analysis)}</div>
                </div>
            `;
        }

        modalBody.innerHTML = html;
    }

    exportLogs() {
        const filters = this.getFilters();
        const data = JSON.stringify(this.logs, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `logs-${new Date().toISOString()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('active');
        });
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new LogViewer();
});


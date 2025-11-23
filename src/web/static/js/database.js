// Database Management JavaScript

// Global state
let currentTable = null;
let currentPage = 1;
let currentQuery = null;
let tables = [];

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeEventListeners();
    loadTables();
});

// Tab Management
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            
            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
            
            // Load data for the active tab
            if (tabName === 'statistics') {
                loadStatistics();
            } else if (tabName === 'history') {
                loadHistory();
            }
        });
    });
}

// Event Listeners
function initializeEventListeners() {
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', function() {
        const activeTab = document.querySelector('.tab-btn.active').dataset.tab;
        if (activeTab === 'tables') {
            loadTables();
        } else if (activeTab === 'statistics') {
            loadStatistics();
        } else if (activeTab === 'history') {
            loadHistory();
        }
    });

    // Query editor
    document.getElementById('clear-query-btn').addEventListener('click', clearQuery);
    document.getElementById('execute-query-btn').addEventListener('click', executeQuery);
    document.getElementById('sql-editor').addEventListener('input', validateQuery);

    // Confirmation modal
    document.getElementById('confirm-execute-btn').addEventListener('click', function() {
        executeQuery(true);
        closeConfirmationModal();
    });

    // Table search
    document.getElementById('table-search').addEventListener('input', filterTables);
    
    // History search
    document.getElementById('history-search').addEventListener('input', searchHistory);

    // Pagination
    document.getElementById('prev-page-btn').addEventListener('click', () => navigatePage(-1));
    document.getElementById('next-page-btn').addEventListener('click', () => navigatePage(1));
}

// Load Tables
async function loadTables() {
    const container = document.getElementById('tables-list');
    container.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Loading tables...</p></div>';
    
    try {
        const response = await fetch('/database/tables');
        if (!response.ok) throw new Error('Failed to load tables');
        
        tables = await response.json();
        displayTables(tables);
        updateLastUpdated();
    } catch (error) {
        container.innerHTML = `<div class="empty-state">Error: ${error.message}</div>`;
    }
}

function displayTables(tablesToDisplay) {
    const container = document.getElementById('tables-list');
    
    if (tablesToDisplay.length === 0) {
        container.innerHTML = '<div class="empty-state">No tables found</div>';
        return;
    }

    container.innerHTML = tablesToDisplay.map(table => `
        <div class="table-card">
            <div class="table-card-header">
                <div class="table-name">${escapeHtml(table.table_name)}</div>
            </div>
            <div class="table-meta">
                <span>Schema: ${escapeHtml(table.schema_name)}</span>
                <span>Rows: ${formatNumber(table.row_count)}</span>
                <span>Size: ${formatBytes(table.size_bytes)}</span>
            </div>
            <div class="table-actions">
                <button class="btn-action" onclick="viewTableSchema('${escapeHtml(table.table_name)}')">Schema</button>
                <button class="btn-action" onclick="browseTableData('${escapeHtml(table.table_name)}')">Browse Data</button>
                <button class="btn-action" onclick="queryTable('${escapeHtml(table.table_name)}')">Query</button>
            </div>
        </div>
    `).join('');
}

function filterTables() {
    const searchTerm = document.getElementById('table-search').value.toLowerCase();
    const filtered = tables.filter(table => 
        table.table_name.toLowerCase().includes(searchTerm) ||
        table.schema_name.toLowerCase().includes(searchTerm)
    );
    displayTables(filtered);
}

// View Table Schema
async function viewTableSchema(tableName) {
    const modal = document.getElementById('table-schema-modal');
    const container = document.getElementById('schema-container');
    const title = document.getElementById('schema-modal-title');
    
    title.textContent = `Schema: ${tableName}`;
    container.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div></div>';
    modal.style.display = 'block';
    
    try {
        const response = await fetch(`/database/table/${encodeURIComponent(tableName)}`);
        if (!response.ok) throw new Error('Failed to load schema');
        
        const schema = await response.json();
        displaySchema(schema);
    } catch (error) {
        container.innerHTML = `<div class="empty-state">Error: ${error.message}</div>`;
    }
}

function displaySchema(schema) {
    const container = document.getElementById('schema-container');
    
    const html = `
        <table class="schema-table">
            <thead>
                <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Nullable</th>
                    <th>Constraints</th>
                    <th>Default</th>
                </tr>
            </thead>
            <tbody>
                ${schema.columns.map(col => `
                    <tr>
                        <td class="column-name">${escapeHtml(col.name)}</td>
                        <td class="column-type">${escapeHtml(col.type)}</td>
                        <td>${col.nullable ? 'Yes' : 'No'}</td>
                        <td>${col.constraint ? `<span class="constraint-badge">${escapeHtml(col.constraint)}</span>` : '-'}</td>
                        <td>${col.default ? escapeHtml(col.default) : '-'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function closeSchemaModal() {
    document.getElementById('table-schema-modal').style.display = 'none';
}

// Browse Table Data
async function browseTableData(tableName) {
    currentTable = tableName;
    currentPage = 1;
    
    const modal = document.getElementById('table-data-modal');
    const title = document.getElementById('table-modal-title');
    
    title.textContent = `Browse Data: ${tableName}`;
    modal.style.display = 'block';
    
    await loadTableData();
}

async function loadTableData() {
    const container = document.getElementById('table-data-container');
    container.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div></div>';
    
    try {
        const response = await fetch(`/database/table/${encodeURIComponent(currentTable)}/data?page=${currentPage}&page_size=50`);
        if (!response.ok) throw new Error('Failed to load data');
        
        const result = await response.json();
        displayTableData(result);
        updatePaginationControls(result.row_count);
    } catch (error) {
        container.innerHTML = `<div class="empty-state">Error: ${error.message}</div>`;
    }
}

function displayTableData(result) {
    const container = document.getElementById('table-data-container');
    
    if (!result.success || result.rows.length === 0) {
        container.innerHTML = '<div class="empty-state">No data found</div>';
        return;
    }

    const html = `
        <table class="result-table">
            <thead>
                <tr>
                    ${result.columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                </tr>
            </thead>
            <tbody>
                ${result.rows.map(row => `
                    <tr>
                        ${row.map(cell => `<td>${escapeHtml(String(cell ?? 'NULL'))}</td>`).join('')}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = html;
}

function updatePaginationControls(rowCount) {
    document.getElementById('page-info').textContent = `Page ${currentPage}`;
    document.getElementById('prev-page-btn').disabled = currentPage === 1;
    document.getElementById('next-page-btn').disabled = rowCount < 50;
}

function navigatePage(delta) {
    currentPage += delta;
    if (currentPage < 1) currentPage = 1;
    loadTableData();
}

function closeTableDataModal() {
    document.getElementById('table-data-modal').style.display = 'none';
    currentTable = null;
    currentPage = 1;
}

// Query Table
function queryTable(tableName) {
    // Switch to query tab
    document.querySelector('.tab-btn[data-tab="query"]').click();
    
    // Set query
    const query = `SELECT * FROM ${tableName} LIMIT 100`;
    document.getElementById('sql-editor').value = query;
    validateQuery();
}

// Validate Query
function validateQuery() {
    const sql = document.getElementById('sql-editor').value.trim();
    const validationEl = document.getElementById('query-validation');
    
    if (!sql) {
        validationEl.textContent = '';
        validationEl.className = '';
        return;
    }

    const upperSql = sql.toUpperCase();
    const destructiveKeywords = ['DELETE', 'DROP', 'TRUNCATE', 'ALTER'];
    const isDestructive = destructiveKeywords.some(keyword => upperSql.includes(keyword));

    if (isDestructive) {
        validationEl.textContent = '⚠️ Warning: This query may modify or delete data';
        validationEl.className = 'warning';
    } else {
        validationEl.textContent = '✓ Query appears safe';
        validationEl.className = 'safe';
    }
}

// Execute Query
async function executeQuery(confirmed = false) {
    const sql = document.getElementById('sql-editor').value.trim();
    
    if (!sql) {
        alert('Please enter a SQL query');
        return;
    }

    // Check if destructive and not confirmed
    const upperSql = sql.toUpperCase();
    const destructiveKeywords = ['DELETE', 'DROP', 'TRUNCATE', 'ALTER'];
    const isDestructive = destructiveKeywords.some(keyword => upperSql.includes(keyword));

    if (isDestructive && !confirmed) {
        showConfirmationModal(sql);
        return;
    }

    const resultsContainer = document.getElementById('query-results');
    resultsContainer.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Executing query...</p></div>';

    try {
        const response = await fetch('/database/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sql, confirmed })
        });

        const result = await response.json();
        
        if (response.status === 400) {
            // Validation error - might need confirmation
            showConfirmationModal(sql);
            return;
        }

        displayQueryResult(result);
    } catch (error) {
        resultsContainer.innerHTML = `
            <div class="query-error-message">
                <strong>Error:</strong> ${escapeHtml(error.message)}
            </div>
        `;
    }
}

function displayQueryResult(result) {
    const container = document.getElementById('query-results');
    
    if (!result.success) {
        container.innerHTML = `
            <div class="query-error-message">
                <strong>Query Failed:</strong> ${escapeHtml(result.error || 'Unknown error')}
            </div>
        `;
        return;
    }

    let html = `
        <div class="query-success-message">
            <strong>Query Executed Successfully</strong>
            <div class="query-execution-time">
                Rows affected: ${result.row_count} | 
                Execution time: ${result.execution_time_ms?.toFixed(2) || '?'} ms
            </div>
        </div>
    `;

    if (result.columns && result.columns.length > 0) {
        html += `
            <table class="result-table">
                <thead>
                    <tr>
                        ${result.columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${result.rows.map(row => `
                        <tr>
                            ${row.map(cell => `<td>${escapeHtml(String(cell ?? 'NULL'))}</td>`).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    container.innerHTML = html;
}

function clearQuery() {
    document.getElementById('sql-editor').value = '';
    document.getElementById('query-validation').textContent = '';
    document.getElementById('query-validation').className = '';
    document.getElementById('query-results').innerHTML = '<div class="empty-state">Execute a query to see results</div>';
}

// Confirmation Modal
function showConfirmationModal(sql) {
    const modal = document.getElementById('confirmation-modal');
    const preview = document.getElementById('modal-query-preview');
    
    preview.textContent = sql;
    modal.style.display = 'block';
}

function closeConfirmationModal() {
    document.getElementById('confirmation-modal').style.display = 'none';
}

// Load Statistics
async function loadStatistics() {
    const container = document.getElementById('stats-container');
    container.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Loading statistics...</p></div>';
    
    try {
        const response = await fetch('/database/stats');
        if (!response.ok) throw new Error('Failed to load statistics');
        
        const stats = await response.json();
        displayStatistics(stats);
        updateLastUpdated();
    } catch (error) {
        container.innerHTML = `<div class="empty-state">Error: ${error.message}</div>`;
    }
}

function displayStatistics(stats) {
    const container = document.getElementById('stats-container');
    
    const html = `
        <div class="stat-card">
            <div class="stat-label">Database Size</div>
            <div class="stat-value">${formatBytes(stats.database_size_bytes)}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">PostgreSQL Version</div>
            <div class="stat-value" style="font-size: 1.2rem;">${escapeHtml(stats.version.split(' ')[0] + ' ' + stats.version.split(' ')[1])}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Active Connections</div>
            <div class="stat-value">${stats.connection_count}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Tables</div>
            <div class="stat-value">${tables.length || 'N/A'}</div>
        </div>
    `;
    
    container.innerHTML = html;
}

// Load History
async function loadHistory(searchTerm = null) {
    const container = document.getElementById('history-list');
    container.innerHTML = '<div class="loading-state"><div class="loading-spinner"></div><p>Loading history...</p></div>';
    
    try {
        const url = searchTerm 
            ? `/database/history?limit=50&search=${encodeURIComponent(searchTerm)}`
            : '/database/history?limit=50';
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load history');
        
        const history = await response.json();
        displayHistory(history);
        updateLastUpdated();
    } catch (error) {
        container.innerHTML = `<div class="empty-state">Error: ${error.message}</div>`;
    }
}

function displayHistory(history) {
    const container = document.getElementById('history-list');
    
    if (history.length === 0) {
        container.innerHTML = '<div class="empty-state">No query history found</div>';
        return;
    }

    container.innerHTML = history.map(item => `
        <div class="history-item ${item.status}">
            <div class="history-header">
                <div class="history-time">${formatTimestamp(item.executed_at)}</div>
                <div class="history-status ${item.status}">${item.status}</div>
            </div>
            <div class="history-query">${escapeHtml(item.query_text)}</div>
            <div class="history-meta">
                ${item.row_count !== null ? `<span>Rows: ${item.row_count}</span>` : ''}
                ${item.execution_time_ms !== null ? `<span>Time: ${item.execution_time_ms.toFixed(2)} ms</span>` : ''}
                ${item.error_message ? `<span style="color: var(--error-color);">${escapeHtml(item.error_message)}</span>` : ''}
            </div>
            <div class="history-actions">
                <button class="btn-rerun" onclick="rerunQuery('${escapeHtml(item.query_text).replace(/'/g, "\\'")}')">Re-run</button>
            </div>
        </div>
    `).join('');
}

function searchHistory() {
    const searchTerm = document.getElementById('history-search').value.trim();
    loadHistory(searchTerm || null);
}

function rerunQuery(sql) {
    // Switch to query tab
    document.querySelector('.tab-btn[data-tab="query"]').click();
    
    // Set query
    document.getElementById('sql-editor').value = sql;
    validateQuery();
}

// Export Data
async function exportTableData(format) {
    if (!currentTable) return;
    
    try {
        const query = `SELECT * FROM ${currentTable}`;
        const url = `/database/export?query=${encodeURIComponent(query)}&format=${format}`;
        
        // Trigger download
        window.location.href = url;
    } catch (error) {
        alert(`Export failed: ${error.message}`);
    }
}

// Utility Functions
function updateLastUpdated() {
    document.getElementById('last-updated').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    return num.toLocaleString();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// Close modals on outside click
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
}


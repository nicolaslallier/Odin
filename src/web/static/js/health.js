/**
 * Health Dashboard Auto-Refresh Functionality
 * 
 * This script handles the auto-refresh functionality for the health monitoring
 * dashboard, including fetching updated data, updating the UI, and managing
 * user preferences.
 */

(function() {
    'use strict';

    // Configuration
    const REFRESH_INTERVAL = 30000; // 30 seconds
    const API_ENDPOINT = '/health/api';
    const HISTORY_ENDPOINT = '/health/api/history';
    const STORAGE_KEY = 'odin-health-auto-refresh';

    // State
    let autoRefreshEnabled = true;
    let refreshIntervalId = null;
    let isRefreshing = false;
    let currentTimeRange = '1h';

    // DOM Elements
    const refreshBtn = document.getElementById('refresh-btn');
    const refreshText = document.getElementById('refresh-text');
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    const lastUpdatedEl = document.getElementById('last-updated');
    const infrastructureGrid = document.getElementById('infrastructure-grid');
    const applicationGrid = document.getElementById('application-grid');
    const circuitBreakerGrid = document.getElementById('circuit-breaker-grid');

    /**
     * Initialize the dashboard
     */
    function init() {
        // Load saved preference from localStorage
        const savedPreference = localStorage.getItem(STORAGE_KEY);
        if (savedPreference !== null) {
            autoRefreshEnabled = savedPreference === 'true';
            autoRefreshToggle.checked = autoRefreshEnabled;
        }

        // Set up event listeners
        refreshBtn.addEventListener('click', handleManualRefresh);
        autoRefreshToggle.addEventListener('change', handleAutoRefreshToggle);

        // Set up time range selector listeners
        const timeRangeBtns = document.querySelectorAll('.time-range-btn');
        timeRangeBtns.forEach(btn => {
            btn.addEventListener('click', handleTimeRangeChange);
        });

        // Start auto-refresh if enabled
        if (autoRefreshEnabled) {
            startAutoRefresh();
        }

        // Load initial historical data
        fetchAndUpdateHistory(currentTimeRange);
    }

    /**
     * Handle manual refresh button click
     */
    async function handleManualRefresh() {
        if (isRefreshing) return;
        await fetchAndUpdateHealth();
    }

    /**
     * Handle auto-refresh toggle change
     */
    function handleAutoRefreshToggle(event) {
        autoRefreshEnabled = event.target.checked;
        localStorage.setItem(STORAGE_KEY, autoRefreshEnabled.toString());

        if (autoRefreshEnabled) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    }

    /**
     * Start auto-refresh timer
     */
    function startAutoRefresh() {
        if (refreshIntervalId) {
            clearInterval(refreshIntervalId);
        }
        refreshIntervalId = setInterval(fetchAndUpdateHealth, REFRESH_INTERVAL);
    }

    /**
     * Stop auto-refresh timer
     */
    function stopAutoRefresh() {
        if (refreshIntervalId) {
            clearInterval(refreshIntervalId);
            refreshIntervalId = null;
        }
    }

    /**
     * Fetch health data from API and update the UI
     */
    async function fetchAndUpdateHealth() {
        if (isRefreshing) return;

        isRefreshing = true;
        setRefreshingState(true);

        try {
            const response = await fetch(API_ENDPOINT);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            updateHealthUI(data);
            updateLastUpdatedTime();
        } catch (error) {
            console.error('Failed to fetch health data:', error);
            showError('Failed to refresh health data. Please try again.');
        } finally {
            isRefreshing = false;
            setRefreshingState(false);
        }
    }

    /**
     * Update UI to show refreshing state
     * @param {boolean} refreshing - Whether currently refreshing
     */
    function setRefreshingState(refreshing) {
        refreshBtn.disabled = refreshing;
        if (refreshing) {
            refreshText.innerHTML = '<span class="loading-spinner"></span> Refreshing...';
        } else {
            refreshText.textContent = 'Refresh Now';
        }
    }

    /**
     * Update the health UI with new data
     * @param {Object} data - Health data from API
     */
    function updateHealthUI(data) {
        // Update infrastructure services
        if (data.infrastructure) {
            updateServiceGrid(infrastructureGrid, data.infrastructure, 'infrastructure');
        }

        // Update application services
        if (data.application) {
            updateServiceGrid(applicationGrid, data.application, 'application');
        }

        // Update circuit breakers
        if (data.circuit_breakers) {
            updateCircuitBreakers(data.circuit_breakers);
        }
    }

    /**
     * Update a service grid with new health data
     * @param {HTMLElement} grid - The grid element to update
     * @param {Object} services - Service health data
     * @param {string} category - Service category
     */
    function updateServiceGrid(grid, services, category) {
        Object.entries(services).forEach(([serviceName, isHealthy]) => {
            const card = grid.querySelector(`[data-service="${serviceName}"][data-category="${category}"]`);
            if (!card) return;

            // Update card classes
            card.classList.remove('healthy', 'unhealthy', 'degraded');
            card.classList.add(isHealthy ? 'healthy' : 'unhealthy');

            // Update status badge
            const badge = card.querySelector('.status-badge');
            if (badge) {
                badge.classList.remove('healthy', 'unhealthy', 'degraded');
                badge.classList.add(isHealthy ? 'healthy' : 'unhealthy');
                badge.textContent = isHealthy ? 'Healthy' : 'Unhealthy';
            }
        });
    }

    /**
     * Update circuit breaker displays
     * @param {Object} breakers - Circuit breaker states
     */
    function updateCircuitBreakers(breakers) {
        if (!circuitBreakerGrid) return;

        Object.entries(breakers).forEach(([serviceName, state]) => {
            const card = circuitBreakerGrid.querySelector(`[data-service="${serviceName}"]`);
            if (!card) return;

            // Update card classes
            card.classList.remove('closed', 'open', 'half_open');
            card.classList.add(state);

            // Update state display
            const stateEl = card.querySelector('.circuit-state');
            if (stateEl) {
                stateEl.classList.remove('closed', 'open', 'half_open');
                stateEl.classList.add(state);
                stateEl.textContent = state;
            }
        });
    }

    /**
     * Update the last updated timestamp
     */
    function updateLastUpdatedTime() {
        if (!lastUpdatedEl) return;

        const now = new Date();
        const timeString = now.toLocaleTimeString();
        lastUpdatedEl.textContent = `Last updated: ${timeString}`;
    }

    /**
     * Show error message to user
     * @param {string} message - Error message to display
     */
    function showError(message) {
        // Could be enhanced with a toast notification system
        console.error(message);
    }

    /**
     * Handle time range button clicks
     */
    function handleTimeRangeChange(event) {
        const range = event.target.dataset.range;
        if (!range) return;

        currentTimeRange = range;

        // Update button states
        document.querySelectorAll('.time-range-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');

        // Fetch new historical data
        fetchAndUpdateHistory(range);
    }

    /**
     * Fetch and display historical health data
     */
    async function fetchAndUpdateHistory(timeRange) {
        const loadingEl = document.getElementById('history-loading');
        const chartsEl = document.getElementById('history-charts');
        const summaryEl = document.getElementById('history-summary');

        if (!loadingEl || !chartsEl || !summaryEl) return;

        // Show loading state
        loadingEl.style.display = 'flex';
        chartsEl.style.display = 'none';
        summaryEl.style.display = 'none';

        try {
            const response = await fetch(`${HISTORY_ENDPOINT}?time_range=${timeRange}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success && data.records && data.records.length > 0) {
                renderHistoricalCharts(data.records);
                renderHistorySummary(data.records);
                
                loadingEl.style.display = 'none';
                chartsEl.style.display = 'grid';
                summaryEl.style.display = 'grid';
            } else {
                loadingEl.innerHTML = '<p class="no-data">No historical data available for this time range</p>';
            }
        } catch (error) {
            console.error('Failed to fetch historical data:', error);
            loadingEl.innerHTML = '<p class="no-data">Failed to load historical data</p>';
        }
    }

    /**
     * Render historical charts for each service
     */
    function renderHistoricalCharts(records) {
        const chartsEl = document.getElementById('history-charts');
        if (!chartsEl) return;

        // Group records by service
        const serviceData = {};
        records.forEach(record => {
            if (!serviceData[record.service_name]) {
                serviceData[record.service_name] = [];
            }
            serviceData[record.service_name].push(record);
        });

        // Clear existing charts
        chartsEl.innerHTML = '';

        // Create chart for each service
        Object.entries(serviceData).forEach(([serviceName, data]) => {
            const chartHtml = createServiceChart(serviceName, data);
            chartsEl.innerHTML += chartHtml;
        });
    }

    /**
     * Create a chart for a specific service
     */
    function createServiceChart(serviceName, data) {
        // Sort by timestamp
        data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        // Calculate uptime percentage
        const totalChecks = data.length;
        const healthyChecks = data.filter(d => d.is_healthy).length;
        const uptimePercent = totalChecks > 0 ? ((healthyChecks / totalChecks) * 100).toFixed(1) : 0;

        // Determine badge class
        let badgeClass = '';
        if (uptimePercent >= 99) badgeClass = '';
        else if (uptimePercent >= 95) badgeClass = 'warning';
        else badgeClass = 'critical';

        // Create bars for chart
        const bars = data.map(record => {
            const healthClass = record.is_healthy ? '' : 'unhealthy';
            return `<div class="chart-bar ${healthClass}" title="${new Date(record.timestamp).toLocaleString()}: ${record.is_healthy ? 'Healthy' : 'Unhealthy'}"></div>`;
        }).join('');

        return `
            <div class="service-chart">
                <div class="chart-header">
                    <span class="chart-title">${serviceName}</span>
                    <span class="uptime-badge ${badgeClass}">${uptimePercent}% uptime</span>
                </div>
                <div class="chart-canvas">
                    <div class="chart-bar-container">
                        ${bars}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render history summary statistics
     */
    function renderHistorySummary(records) {
        const summaryEl = document.getElementById('history-summary');
        if (!summaryEl) return;

        // Calculate overall statistics
        const totalChecks = records.length;
        const healthyChecks = records.filter(r => r.is_healthy).length;
        const unhealthyChecks = totalChecks - healthyChecks;
        const overallUptime = totalChecks > 0 ? ((healthyChecks / totalChecks) * 100).toFixed(1) : 0;

        // Count unique services
        const uniqueServices = new Set(records.map(r => r.service_name)).size;

        // Find services with issues
        const serviceHealth = {};
        records.forEach(record => {
            if (!serviceHealth[record.service_name]) {
                serviceHealth[record.service_name] = { healthy: 0, unhealthy: 0 };
            }
            if (record.is_healthy) {
                serviceHealth[record.service_name].healthy++;
            } else {
                serviceHealth[record.service_name].unhealthy++;
            }
        });

        const servicesWithIssues = Object.values(serviceHealth).filter(s => s.unhealthy > 0).length;

        summaryEl.innerHTML = `
            <div class="summary-card">
                <div class="summary-value">${overallUptime}%</div>
                <div class="summary-label">Overall Uptime</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">${uniqueServices}</div>
                <div class="summary-label">Services Monitored</div>
            </div>
            <div class="summary-card">
                <div class="summary-value ${servicesWithIssues > 0 ? 'warning' : ''}">${servicesWithIssues}</div>
                <div class="summary-label">Services with Issues</div>
            </div>
            <div class="summary-card">
                <div class="summary-value ${unhealthyChecks > 0 ? 'critical' : ''}">${unhealthyChecks}</div>
                <div class="summary-label">Failed Checks</div>
            </div>
        `;
    }

    /**
     * Clean up when page is unloaded
     */
    function cleanup() {
        stopAutoRefresh();
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Clean up on page unload
    window.addEventListener('beforeunload', cleanup);

})();


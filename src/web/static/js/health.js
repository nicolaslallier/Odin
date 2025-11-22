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
    const STORAGE_KEY = 'odin-health-auto-refresh';

    // State
    let autoRefreshEnabled = true;
    let refreshIntervalId = null;
    let isRefreshing = false;

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

        // Start auto-refresh if enabled
        if (autoRefreshEnabled) {
            startAutoRefresh();
        }
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


/**
 * WebSocket client for real-time statistics updates
 * 
 * This module provides WebSocket connection management and handles
 * real-time updates from the API for Confluence statistics.
 */

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.currentReconnectDelay = this.reconnectDelay;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.isIntentionalClose = false;
        this.subscriptions = new Set();
        this.eventHandlers = {};
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        console.log('Connecting to WebSocket:', this.url);
        this.isIntentionalClose = false;

        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.currentReconnectDelay = this.reconnectDelay;
                this.reconnectAttempts = 0;
                this.emit('connected', {});

                // Re-subscribe to spaces
                this.subscriptions.forEach(spaceKey => {
                    this.subscribe(spaceKey);
                });
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', { error });
            };

            this.ws.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.emit('disconnected', { code: event.code, reason: event.reason });

                // Attempt to reconnect unless intentionally closed
                if (!this.isIntentionalClose && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };

        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        this.reconnectAttempts++;
        
        console.log(`Reconnecting in ${this.currentReconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.connect();
        }, this.currentReconnectDelay);

        // Exponential backoff
        this.currentReconnectDelay = Math.min(
            this.currentReconnectDelay * 2,
            this.maxReconnectDelay
        );
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        this.isIntentionalClose = true;
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    /**
     * Subscribe to statistics updates for a space
     */
    subscribe(spaceKey) {
        this.subscriptions.add(spaceKey);
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.send({
                type: 'subscribe',
                space_key: spaceKey
            });
        }
    }

    /**
     * Unsubscribe from statistics updates for a space
     */
    unsubscribe(spaceKey) {
        this.subscriptions.delete(spaceKey);
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.send({
                type: 'unsubscribe',
                space_key: spaceKey
            });
        }
    }

    /**
     * Send message to WebSocket server
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(message) {
        const { type } = message;

        switch (type) {
            case 'statistics_update':
                this.handleStatisticsUpdate(message);
                break;
            case 'subscribed':
                console.log('Subscribed to space:', message.space_key);
                this.emit('subscribed', message);
                break;
            case 'unsubscribed':
                console.log('Unsubscribed from space:', message.space_key);
                this.emit('unsubscribed', message);
                break;
            case 'pong':
                // Heartbeat response
                break;
            case 'error':
                console.error('Server error:', message.message);
                this.emit('server_error', message);
                break;
            default:
                console.warn('Unknown message type:', type);
        }
    }

    /**
     * Handle statistics update message
     */
    handleStatisticsUpdate(message) {
        const { space_key, job_id, status, statistics } = message;
        
        console.log('Statistics update received:', {
            space_key,
            job_id,
            status
        });

        // Emit custom event
        this.emit('statistics_update', {
            spaceKey: space_key,
            jobId: job_id,
            status,
            statistics
        });

        // Dispatch DOM event for easy integration
        const event = new CustomEvent('confluenceStatisticsUpdate', {
            detail: {
                spaceKey: space_key,
                jobId: job_id,
                status,
                statistics
            }
        });
        window.dispatchEvent(event);
    }

    /**
     * Register event handler
     */
    on(eventName, handler) {
        if (!this.eventHandlers[eventName]) {
            this.eventHandlers[eventName] = [];
        }
        this.eventHandlers[eventName].push(handler);
    }

    /**
     * Unregister event handler
     */
    off(eventName, handler) {
        if (!this.eventHandlers[eventName]) {
            return;
        }
        
        const index = this.eventHandlers[eventName].indexOf(handler);
        if (index !== -1) {
            this.eventHandlers[eventName].splice(index, 1);
        }
    }

    /**
     * Emit event to registered handlers
     */
    emit(eventName, data) {
        if (!this.eventHandlers[eventName]) {
            return;
        }
        
        this.eventHandlers[eventName].forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in event handler for ${eventName}:`, error);
            }
        });
    }

    /**
     * Send heartbeat ping
     */
    sendPing() {
        this.send({ type: 'ping' });
    }

    /**
     * Check connection status
     */
    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

// Create global WebSocket client instance
// URL will be determined based on current location
const getWebSocketUrl = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/api/ws`;
};

// Export for use in other scripts
window.ConfluenceWebSocketClient = WebSocketClient;
window.confluenceWS = new WebSocketClient(getWebSocketUrl());

// Auto-connect on page load
document.addEventListener('DOMContentLoaded', () => {
    window.confluenceWS.connect();
    
    // Setup heartbeat
    setInterval(() => {
        if (window.confluenceWS.isConnected()) {
            window.confluenceWS.sendPing();
        }
    }, 30000); // Ping every 30 seconds
});


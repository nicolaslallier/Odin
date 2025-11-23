/**
 * Health dashboard component showing current status.
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, Loading, StatusBadge, apiClient } from '@odin/shared';
import type { HealthStatusSummary, ServiceStatus } from '@odin/shared';

/**
 * Dashboard showing current health status of all services.
 */
export const HealthDashboard: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatusSummary>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadHealthStatus();
    const interval = setInterval(loadHealthStatus, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadHealthStatus = async () => {
    try {
      setLoading(true);
      const data = await apiClient.get<HealthStatusSummary>('/api/health/status/latest');
      setHealthStatus(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load health status');
    } finally {
      setLoading(false);
    }
  };

  if (loading && Object.keys(healthStatus).length === 0) {
    return <Loading message="Loading health status..." />;
  }

  if (error && Object.keys(healthStatus).length === 0) {
    return (
      <Card title="Health Monitoring">
        <div className="error-message">{error}</div>
      </Card>
    );
  }

  const healthyCount = Object.values(healthStatus).filter(status => status).length;
  const totalCount = Object.keys(healthStatus).length;

  return (
    <div className="health-dashboard">
      <h1>Health Monitoring Dashboard</h1>
      
      <div className="health-summary">
        <Card title="System Overview">
          <div className="health-stats">
            <div className="stat">
              <span className="stat-label">Total Services</span>
              <span className="stat-value">{totalCount}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Healthy</span>
              <span className="stat-value success">{healthyCount}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Unhealthy</span>
              <span className="stat-value danger">{totalCount - healthyCount}</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="services-grid">
        {Object.entries(healthStatus).map(([serviceName, isHealthy]) => (
          <Card key={serviceName} title={serviceName}>
            <div className="service-status">
              <StatusBadge status={isHealthy ? 'healthy' : 'unhealthy'} />
              <Link to={`/health/details/${serviceName}`} className="details-link">
                View Details
              </Link>
            </div>
          </Card>
        ))}
      </div>

      <div className="dashboard-actions">
        <Link to="/health/history" className="btn btn-primary">
          View History
        </Link>
      </div>
    </div>
  );
};


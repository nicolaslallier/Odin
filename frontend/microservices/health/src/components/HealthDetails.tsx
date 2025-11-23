/**
 * Health details component for a specific service.
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Card, Loading, StatusBadge, apiClient, formatDate, getDateRange } from '@odin/shared';
import type { HealthCheckRecord, HealthCheckQueryParams } from '@odin/shared';

/**
 * Detailed health information for a specific service.
 */
export const HealthDetails: React.FC = () => {
  const { serviceName } = useParams<{ serviceName: string }>();
  const [history, setHistory] = useState<HealthCheckRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (serviceName) {
      loadServiceHistory(serviceName);
    }
  }, [serviceName]);

  const loadServiceHistory = async (service: string) => {
    try {
      setLoading(true);
      const { startTime, endTime } = getDateRange(7);
      const params: HealthCheckQueryParams = {
        startTime,
        endTime,
        serviceNames: [service],
        limit: 500,
      };
      
      const data = await apiClient.get<HealthCheckRecord[]>('/api/health/history', params);
      setHistory(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load service history');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading message={`Loading details for ${serviceName}...`} />;
  }

  if (error) {
    return (
      <Card title={`Service Details: ${serviceName}`}>
        <div className="error-message">{error}</div>
        <Link to="/health">Back to Dashboard</Link>
      </Card>
    );
  }

  const latestRecord = history[0];
  const uptimeCount = history.filter(r => r.isHealthy).length;
  const uptimePercentage = history.length > 0 ? (uptimeCount / history.length) * 100 : 0;
  const avgResponseTime = history.length > 0
    ? history.reduce((sum, r) => sum + (r.responseTimeMs || 0), 0) / history.length
    : 0;

  return (
    <div className="health-details">
      <div className="details-header">
        <h1>{serviceName}</h1>
        <Link to="/health" className="btn btn-secondary">
          Back to Dashboard
        </Link>
      </div>

      {latestRecord && (
        <Card title="Current Status">
          <div className="status-info">
            <div className="info-row">
              <span className="label">Status:</span>
              <StatusBadge status={latestRecord.isHealthy ? 'healthy' : 'unhealthy'} />
            </div>
            <div className="info-row">
              <span className="label">Type:</span>
              <span>{latestRecord.serviceType}</span>
            </div>
            <div className="info-row">
              <span className="label">Last Check:</span>
              <span>{formatDate(latestRecord.timestamp)}</span>
            </div>
            {latestRecord.responseTimeMs && (
              <div className="info-row">
                <span className="label">Response Time:</span>
                <span>{latestRecord.responseTimeMs}ms</span>
              </div>
            )}
            {latestRecord.errorMessage && (
              <div className="info-row">
                <span className="label">Error:</span>
                <span className="error-text">{latestRecord.errorMessage}</span>
              </div>
            )}
          </div>
        </Card>
      )}

      <Card title="Statistics (Last 7 Days)">
        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-label">Uptime</span>
            <span className="stat-value">{uptimePercentage.toFixed(2)}%</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Avg Response Time</span>
            <span className="stat-value">{avgResponseTime.toFixed(0)}ms</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Total Checks</span>
            <span className="stat-value">{history.length}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Failures</span>
            <span className="stat-value">{history.length - uptimeCount}</span>
          </div>
        </div>
      </Card>

      <Card title="Recent History">
        <div className="history-list">
          {history.slice(0, 20).map((record, index) => (
            <div key={index} className="history-item">
              <span className="timestamp">{formatDate(record.timestamp)}</span>
              <StatusBadge status={record.isHealthy ? 'healthy' : 'unhealthy'} />
              {record.responseTimeMs && <span className="response-time">{record.responseTimeMs}ms</span>}
              {record.errorMessage && <span className="error-msg">{record.errorMessage}</span>}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};


/**
 * Health history component showing historical data.
 */

import React, { useEffect, useState } from 'react';
import { Card, Loading, apiClient, formatDate, getDateRange } from '@odin/shared';
import type { HealthCheckRecord, HealthCheckQueryParams } from '@odin/shared';
import { HealthChart } from './HealthChart';

/**
 * Historical health data visualization.
 */
export const HealthHistory: React.FC = () => {
  const [history, setHistory] = useState<HealthCheckRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(7);

  useEffect(() => {
    loadHistory();
  }, [days]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const { startTime, endTime } = getDateRange(days);
      const params: HealthCheckQueryParams = {
        startTime,
        endTime,
        limit: 1000,
      };
      
      const data = await apiClient.get<HealthCheckRecord[]>('/api/health/history', params);
      setHistory(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load health history');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <Loading message="Loading health history..." />;
  }

  if (error) {
    return (
      <Card title="Health History">
        <div className="error-message">{error}</div>
      </Card>
    );
  }

  return (
    <div className="health-history">
      <h1>Health History</h1>
      
      <div className="history-controls">
        <label>
          Time Range:
          <select value={days} onChange={e => setDays(Number(e.target.value))}>
            <option value={1}>Last 24 Hours</option>
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
        </label>
      </div>

      <Card title="Health Status Over Time">
        <HealthChart data={history} />
      </Card>

      <Card title="Recent Events">
        <div className="history-table">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Service</th>
                <th>Type</th>
                <th>Status</th>
                <th>Response Time</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(0, 50).map((record, index) => (
                <tr key={index}>
                  <td>{formatDate(record.timestamp)}</td>
                  <td>{record.serviceName}</td>
                  <td>{record.serviceType}</td>
                  <td>
                    <span className={`badge badge-${record.isHealthy ? 'success' : 'danger'}`}>
                      {record.isHealthy ? 'Healthy' : 'Unhealthy'}
                    </span>
                  </td>
                  <td>{record.responseTimeMs ? `${record.responseTimeMs}ms` : 'N/A'}</td>
                  <td className="error-cell">{record.errorMessage || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};


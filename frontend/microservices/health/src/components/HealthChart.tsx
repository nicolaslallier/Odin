/**
 * Chart component for visualizing health data.
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { HealthCheckRecord } from '@odin/shared';
import { formatDate } from '@odin/shared';

interface HealthChartProps {
  data: HealthCheckRecord[];
}

/**
 * Chart visualizing health status over time.
 */
export const HealthChart: React.FC<HealthChartProps> = ({ data }) => {
  // Group data by service and time
  const chartData = data.reduce((acc, record) => {
    const timestamp = new Date(record.timestamp).getTime();
    const existing = acc.find(d => d.timestamp === timestamp);
    
    if (existing) {
      existing[record.serviceName] = record.isHealthy ? 1 : 0;
    } else {
      acc.push({
        timestamp,
        time: formatDate(record.timestamp, false),
        [record.serviceName]: record.isHealthy ? 1 : 0,
      });
    }
    
    return acc;
  }, [] as any[]);

  // Sort by timestamp
  chartData.sort((a, b) => a.timestamp - b.timestamp);

  // Get unique service names
  const services = Array.from(new Set(data.map(r => r.serviceName)));

  const colors = [
    '#0066cc',
    '#28a745',
    '#dc3545',
    '#ffc107',
    '#6c757d',
    '#17a2b8',
    '#6610f2',
    '#e83e8c',
    '#fd7e14',
  ];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="time" />
        <YAxis domain={[0, 1]} ticks={[0, 1]} tickFormatter={v => (v === 1 ? 'Healthy' : 'Unhealthy')} />
        <Tooltip />
        <Legend />
        {services.map((service, index) => (
          <Line
            key={service}
            type="stepAfter"
            dataKey={service}
            stroke={colors[index % colors.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
};


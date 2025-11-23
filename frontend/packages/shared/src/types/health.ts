/**
 * Health monitoring types.
 */

import { ServiceType, ServiceStatus } from './common';

/**
 * Health check record from API.
 */
export interface HealthCheckRecord {
  id?: number;
  timestamp: string;
  serviceName: string;
  serviceType: ServiceType;
  isHealthy: boolean;
  responseTimeMs?: number;
  errorMessage?: string;
  metadata: Record<string, unknown>;
}

/**
 * Health check query parameters.
 */
export interface HealthCheckQueryParams {
  startTime: string;
  endTime: string;
  serviceNames?: string[];
  serviceType?: ServiceType;
  limit?: number;
}

/**
 * Latest health status summary.
 */
export interface HealthStatusSummary {
  [serviceName: string]: boolean;
}

/**
 * Health dashboard data.
 */
export interface HealthDashboardData {
  latestStatus: HealthStatusSummary;
  history: HealthCheckRecord[];
  uptimePercentage: Record<string, number>;
  averageResponseTime: Record<string, number>;
}


/**
 * Status badge component.
 */

import React from 'react';
import { ServiceStatus } from '../types/common';

export interface StatusBadgeProps {
  status: ServiceStatus;
  label?: string;
}

/**
 * Badge component for displaying service status.
 */
export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
  const statusColors: Record<ServiceStatus, string> = {
    healthy: 'success',
    unhealthy: 'danger',
    unknown: 'secondary',
    starting: 'warning',
  };

  const color = statusColors[status];
  const displayLabel = label || status;

  return <span className={`badge badge-${color}`}>{displayLabel}</span>;
};


/**
 * Route definitions for health micro-frontend.
 * Exported for portal integration.
 */

import { RouteConfig } from '@odin/shared';

export const routes: RouteConfig[] = [
  {
    path: '/health',
    title: 'Health Dashboard',
    icon: 'health',
    exact: true,
  },
  {
    path: '/health/history',
    title: 'Health History',
    icon: 'history',
  },
];


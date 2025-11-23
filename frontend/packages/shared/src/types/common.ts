/**
 * Common types used across the Odin platform.
 */

/**
 * Generic API response wrapper.
 */
export interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
  message?: string;
  status: number;
}

/**
 * Pagination parameters for list endpoints.
 */
export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

/**
 * Paginated response wrapper.
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasNext: boolean;
  hasPrev: boolean;
}

/**
 * Date range filter.
 */
export interface DateRange {
  startTime: string;
  endTime: string;
}

/**
 * Service status type.
 */
export type ServiceStatus = 'healthy' | 'unhealthy' | 'unknown' | 'starting';

/**
 * Service type classification.
 */
export type ServiceType = 'api' | 'database' | 'storage' | 'messaging' | 'infrastructure';

/**
 * Loading state for async operations.
 */
export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

/**
 * Micro-frontend manifest.
 */
export interface MicroFrontendManifest {
  name: string;
  version: string;
  remoteEntry: string;
  exposedModules: string[];
  routes?: RouteConfig[];
}

/**
 * Route configuration for micro-frontends.
 */
export interface RouteConfig {
  path: string;
  title: string;
  icon?: string;
  exact?: boolean;
}


/**
 * Shared constants.
 */

/**
 * API endpoints.
 */
export const API_ENDPOINTS = {
  HEALTH: '/api/health',
  DATA: '/api/data',
  CONFLUENCE: '/api/confluence',
  FILES: '/api/files',
  LLM: '/api/llm',
  LOGS: '/api/logs',
  SECRETS: '/api/secrets',
  MESSAGES: '/api/messages',
  IMAGE_ANALYSIS: '/api/image-analysis',
} as const;

/**
 * Micro-frontend remote entry points.
 */
export const MFE_REMOTES = {
  HEALTH: '/mfe/health/remoteEntry.js',
  DATA: '/mfe/data/remoteEntry.js',
  CONFLUENCE: '/mfe/confluence/remoteEntry.js',
  FILES: '/mfe/files/remoteEntry.js',
  LLM: '/mfe/llm/remoteEntry.js',
  LOGS: '/mfe/logs/remoteEntry.js',
  SECRETS: '/mfe/secrets/remoteEntry.js',
  MESSAGES: '/mfe/messages/remoteEntry.js',
  IMAGE_ANALYSIS: '/mfe/image-analysis/remoteEntry.js',
} as const;

/**
 * Storage keys.
 */
export const STORAGE_KEYS = {
  AUTH: 'odin_auth',
  THEME: 'odin_theme',
  PREFERENCES: 'odin_preferences',
} as const;

/**
 * Default pagination settings.
 */
export const DEFAULT_PAGE_SIZE = 20;
export const DEFAULT_PAGE = 1;

/**
 * Date range presets (in days).
 */
export const DATE_RANGES = {
  LAST_HOUR: 1 / 24,
  LAST_DAY: 1,
  LAST_WEEK: 7,
  LAST_MONTH: 30,
  LAST_YEAR: 365,
} as const;


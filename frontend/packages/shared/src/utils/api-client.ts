/**
 * Centralized API client using axios.
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { IApiClient, ApiError } from '../types/api';

/**
 * Create an API client instance with base configuration.
 */
export function createApiClient(baseURL: string = ''): IApiClient {
  const instance: AxiosInstance = axios.create({
    baseURL: baseURL || window.location.origin,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor for adding auth token
  instance.interceptors.request.use(
    config => {
      const token = localStorage.getItem('accessToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    error => Promise.reject(error)
  );

  // Response interceptor for error handling
  instance.interceptors.response.use(
    response => response.data,
    (error: AxiosError) => {
      const apiError: ApiError = {
        message: error.message,
        status: error.response?.status || 500,
        code: (error.response?.data as any)?.code,
        details: error.response?.data,
      };
      return Promise.reject(apiError);
    }
  );

  return {
    async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
      return instance.get(url, { params });
    },

    async post<T>(url: string, data?: unknown): Promise<T> {
      return instance.post(url, data);
    },

    async put<T>(url: string, data?: unknown): Promise<T> {
      return instance.put(url, data);
    },

    async patch<T>(url: string, data?: unknown): Promise<T> {
      return instance.patch(url, data);
    },

    async delete<T>(url: string): Promise<T> {
      return instance.delete(url);
    },
  };
}

/**
 * Default API client instance.
 */
export const apiClient = createApiClient();


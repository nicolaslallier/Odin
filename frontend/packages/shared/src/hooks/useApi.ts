/**
 * Hook for making API calls with loading and error states.
 */

import { useState, useCallback } from 'react';
import { apiClient } from '../utils/api-client';
import { ApiError } from '../types/api';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: () => Promise<void>;
  reset: () => void;
}

/**
 * Hook for executing API calls with loading and error state management.
 */
export function useApi<T>(
  apiCall: () => Promise<T>,
  immediate: boolean = false
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: immediate,
    error: null,
  });

  const execute = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await apiCall();
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState({
        data: null,
        loading: false,
        error: err as ApiError,
      });
    }
  }, [apiCall]);

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  // Execute immediately if requested
  useState(() => {
    if (immediate) {
      execute();
    }
  });

  return {
    ...state,
    execute,
    reset,
  };
}


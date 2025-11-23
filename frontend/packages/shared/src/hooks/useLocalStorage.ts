/**
 * Hook for using localStorage with React state.
 */

import { useState, useEffect, useCallback } from 'react';
import { saveToStorage, loadFromStorage } from '../utils/storage';

/**
 * Hook for syncing state with localStorage.
 */
export function useLocalStorage<T>(key: string, defaultValue: T): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => loadFromStorage(key, defaultValue));

  useEffect(() => {
    saveToStorage(key, value);
  }, [key, value]);

  const setStoredValue = useCallback(
    (newValue: T) => {
      setValue(newValue);
    },
    []
  );

  return [value, setStoredValue];
}


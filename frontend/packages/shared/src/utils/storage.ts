/**
 * Local storage utilities with type safety.
 */

/**
 * Save data to localStorage with JSON serialization.
 */
export function saveToStorage<T>(key: string, value: T): void {
  try {
    const serialized = JSON.stringify(value);
    localStorage.setItem(key, serialized);
  } catch (error) {
    console.error(`Failed to save to localStorage: ${error}`);
  }
}

/**
 * Load data from localStorage with JSON deserialization.
 */
export function loadFromStorage<T>(key: string, defaultValue: T): T {
  try {
    const serialized = localStorage.getItem(key);
    if (serialized === null) return defaultValue;
    return JSON.parse(serialized) as T;
  } catch (error) {
    console.error(`Failed to load from localStorage: ${error}`);
    return defaultValue;
  }
}

/**
 * Remove item from localStorage.
 */
export function removeFromStorage(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    console.error(`Failed to remove from localStorage: ${error}`);
  }
}

/**
 * Clear all items from localStorage.
 */
export function clearStorage(): void {
  try {
    localStorage.clear();
  } catch (error) {
    console.error(`Failed to clear localStorage: ${error}`);
  }
}


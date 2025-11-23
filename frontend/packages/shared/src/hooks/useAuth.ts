/**
 * Authentication hook.
 */

import { useState, useEffect, useCallback } from 'react';
import { AuthState, User, AuthTokens, LoginCredentials } from '../types/auth';
import { loadFromStorage, saveToStorage, removeFromStorage } from '../utils/storage';

const AUTH_STORAGE_KEY = 'odin_auth';

/**
 * Hook for managing authentication state.
 */
export function useAuth() {
  const [authState, setAuthState] = useState<AuthState>(() => {
    const stored = loadFromStorage<{ user: User | null; tokens: AuthTokens | null }>(
      AUTH_STORAGE_KEY,
      { user: null, tokens: null }
    );
    return {
      ...stored,
      isAuthenticated: !!stored.user,
      isLoading: false,
    };
  });

  // Persist auth state to localStorage
  useEffect(() => {
    if (authState.user && authState.tokens) {
      saveToStorage(AUTH_STORAGE_KEY, {
        user: authState.user,
        tokens: authState.tokens,
      });
    }
  }, [authState.user, authState.tokens]);

  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    setAuthState(prev => ({ ...prev, isLoading: true }));
    try {
      // TODO: Implement actual API call to login endpoint
      // For now, this is a placeholder
      const mockUser: User = {
        id: '1',
        username: credentials.username,
        email: `${credentials.username}@example.com`,
        roles: ['user'],
        permissions: ['read'],
      };
      const mockTokens: AuthTokens = {
        accessToken: 'mock-access-token',
        refreshToken: 'mock-refresh-token',
        expiresIn: 3600,
        tokenType: 'Bearer',
      };

      setAuthState({
        user: mockUser,
        tokens: mockTokens,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    setAuthState({
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
    });
    removeFromStorage(AUTH_STORAGE_KEY);
  }, []);

  const refreshToken = useCallback(async (): Promise<void> => {
    // TODO: Implement token refresh logic
    console.log('Token refresh not implemented yet');
  }, []);

  return {
    ...authState,
    login,
    logout,
    refreshToken,
  };
}


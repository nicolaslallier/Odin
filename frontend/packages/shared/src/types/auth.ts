/**
 * Authentication and authorization types.
 */

/**
 * User information.
 */
export interface User {
  id: string;
  username: string;
  email?: string;
  roles: string[];
  permissions: string[];
}

/**
 * Authentication tokens.
 */
export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
  expiresIn: number;
  tokenType: string;
}

/**
 * Login credentials.
 */
export interface LoginCredentials {
  username: string;
  password: string;
}

/**
 * Authentication state.
 */
export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

